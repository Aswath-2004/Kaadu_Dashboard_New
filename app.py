import os
import uuid
from datetime import datetime, date, timedelta
from collections import defaultdict

import pandas as pd

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, session, abort
)
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)
from sqlalchemy import func, text

from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from config import config
from models import db, User, Upload, SalesRecord


# ─────────────────────────────────────────────────
# App factory
# ─────────────────────────────────────────────────
def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # ✅ Ensure required folders exist
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)
    os.makedirs('instance', exist_ok=True)

    # ✅ Fix silent 400 on multipart parsing (common with CSV uploads)
    # Increase form memory and parts limits (Werkzeug/Flask 2.3+)
    app.config["MAX_FORM_MEMORY_SIZE"] = 32 * 1024 * 1024  # 32MB in-memory form buffer
    app.config["MAX_FORM_PARTS"] = 2000  # max form parts/fields

    # Optional overall request limit (if your config has MAX_CONTENT_LENGTH you can remove this)
    # app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB

    # ✅ Better error messages for upload failures
    @app.errorhandler(BadRequest)
    def handle_bad_request(e):
        # This catches multipart/form-data parsing errors and shows real reason
        app.logger.exception("BadRequest (400): %s", getattr(e, "description", str(e)))
        return f"Bad Request (400): {getattr(e, 'description', str(e))}", 400

    @app.errorhandler(RequestEntityTooLarge)
    def handle_too_large(e):
        # If MAX_CONTENT_LENGTH triggers
        app.logger.exception("Request too large: %s", str(e))
        return "File too large (413). Try a smaller CSV or increase MAX_CONTENT_LENGTH.", 413

    db.init_app(app)

    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access the dashboard.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        # SQLAlchemy 2.0: Query.get is legacy but still works
        return User.query.get(int(user_id))

    # ✅ Helpful logging specifically for /upload requests (no code change in blueprint required)
    @app.before_request
    def debug_upload_request():
        # Only log for upload endpoint to avoid noisy logs
        if request.path == "/upload" and request.method == "POST":
            try:
                app.logger.info("UPLOAD DEBUG: content_type=%s", request.content_type)
                app.logger.info("UPLOAD DEBUG: files_keys=%s", list(request.files.keys()))
                app.logger.info("UPLOAD DEBUG: form_keys=%s", list(request.form.keys()))
            except Exception:
                # Don’t crash logging
                app.logger.exception("UPLOAD DEBUG: failed to log request info")

    # Register blueprints
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')

    with app.app_context():
        db.create_all()
        _seed_admin(app)

    return app


def _seed_admin(app):
    """Create default admin if none exists."""
    with app.app_context():
        if not User.query.filter_by(role='admin').first():
            admin = User(
                username='admin',
                email='admin@kaadu.in',
                full_name='Kaadu Admin',
                role='admin'
            )
            admin.set_password('kaadu@2024')
            db.session.add(admin)
            db.session.commit()
            print('✅ Default admin created → admin ')


app = create_app()

if __name__ == '__main__':
    # ✅ More stable dev run config
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)