import os
import uuid
from datetime import date, timedelta

import pandas as pd
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, current_app, jsonify, session)
from flask_login import login_required, current_user

from models import db, Upload, SalesRecord
from utils.parser import parse_sales_file, categorize_product

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    from flask_login import current_user
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    uploads = (Upload.query
               .filter_by(user_id=current_user.id)
               .order_by(Upload.uploaded_at.desc())
               .all())
    active_upload = next((u for u in uploads if u.is_active), None)
    return render_template('dashboard/index.html',
                           uploads=uploads,
                           active_upload=active_upload)


@main_bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        flash('No file selected.', 'error')
        return redirect(url_for('main.dashboard'))

    file = request.files['file']
    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('main.dashboard'))

    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in current_app.config['ALLOWED_EXTENSIONS']:
        flash('Unsupported file type. Please upload CSV or Excel.', 'error')
        return redirect(url_for('main.dashboard'))

    # Save file
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    save_path   = os.path.join(current_app.config['UPLOAD_FOLDER'], stored_name)
    file.save(save_path)

    try:
        result = parse_sales_file(save_path, ext)
    except Exception as e:
        os.remove(save_path)
        flash(f'Error parsing file: {str(e)}', 'error')
        return redirect(url_for('main.dashboard'))

    if not result['records']:
        os.remove(save_path)
        flash('No valid sales records found in the file.', 'error')
        return redirect(url_for('main.dashboard'))

    # Deactivate previous uploads
    Upload.query.filter_by(user_id=current_user.id, is_active=True)\
                .update({'is_active': False})

    # Create upload record
    upload = Upload(
        user_id         = current_user.id,
        original_name   = file.filename,
        stored_name     = stored_name,
        record_count    = result['record_count'],
        total_amount    = result['total_amount'],
        unique_customers= result['unique_customers'],
        unique_products = result['unique_products'],
        unique_invoices = result['unique_invoices'],
        date_from       = result['date_from'],
        date_to         = result['date_to'],
        is_active       = True
    )
    db.session.add(upload)
    db.session.flush()

    # Bulk insert records
    db.session.bulk_insert_mappings(SalesRecord, [
        {**r, 'upload_id': upload.id} for r in result['records']
    ])
    db.session.commit()

    flash(f'✅ Success! Processed {result["record_count"]:,} records from "{file.filename}"', 'success')
    return redirect(url_for('main.dashboard'))


@main_bp.route('/switch-upload/<int:upload_id>')
@login_required
def switch_upload(upload_id):
    upload = Upload.query.filter_by(id=upload_id, user_id=current_user.id).first_or_404()
    Upload.query.filter_by(user_id=current_user.id, is_active=True)\
                .update({'is_active': False})
    upload.is_active = True
    db.session.commit()
    flash(f'Switched to "{upload.original_name}"', 'success')
    return redirect(url_for('main.dashboard'))


@main_bp.route('/delete-upload/<int:upload_id>', methods=['POST'])
@login_required
def delete_upload(upload_id):
    upload = Upload.query.filter_by(id=upload_id, user_id=current_user.id).first_or_404()
    stored = os.path.join(current_app.config['UPLOAD_FOLDER'], upload.stored_name)
    if os.path.exists(stored):
        os.remove(stored)
    db.session.delete(upload)
    db.session.commit()
    flash('Upload deleted.', 'info')
    return redirect(url_for('main.dashboard'))
