from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email         = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name     = db.Column(db.String(120))
    role          = db.Column(db.String(20), default='user')   # 'admin' | 'user'
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    last_login    = db.Column(db.DateTime)
    uploads       = db.relationship('Upload', backref='owner', lazy='dynamic',
                                    cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Upload(db.Model):
    __tablename__ = 'uploads'
    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    original_name   = db.Column(db.String(255), nullable=False)
    stored_name     = db.Column(db.String(255), nullable=False)
    record_count    = db.Column(db.Integer, default=0)
    total_amount    = db.Column(db.Float, default=0.0)
    unique_customers= db.Column(db.Integer, default=0)
    unique_products = db.Column(db.Integer, default=0)
    unique_invoices = db.Column(db.Integer, default=0)
    date_from       = db.Column(db.String(20))
    date_to         = db.Column(db.String(20))
    uploaded_at     = db.Column(db.DateTime, default=datetime.utcnow)
    is_active       = db.Column(db.Boolean, default=True)
    records         = db.relationship('SalesRecord', backref='upload', lazy='dynamic',
                                      cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Upload {self.original_name}>'


class SalesRecord(db.Model):
    __tablename__ = 'sales_records'
    id            = db.Column(db.Integer, primary_key=True)
    upload_id     = db.Column(db.Integer, db.ForeignKey('uploads.id'), nullable=False)
    sale_date     = db.Column(db.Date, index=True)
    month_key     = db.Column(db.String(7), index=True)        # 'YYYY-MM'
    party_name    = db.Column(db.String(255), index=True)
    invoice_no    = db.Column(db.String(50), index=True)
    product       = db.Column(db.String(500))
    category      = db.Column(db.String(100), index=True)
    quantity      = db.Column(db.Float, default=0)
    unit          = db.Column(db.String(20))
    price_per_unit= db.Column(db.Float, default=0)
    amount        = db.Column(db.Float, default=0, index=True)

    def to_dict(self):
        return {
            'id':           self.id,
            'date':         self.sale_date.strftime('%d-%m-%Y') if self.sale_date else '',
            'party':        self.party_name,
            'invoice':      self.invoice_no,
            'product':      self.product,
            'category':     self.category,
            'quantity':     self.quantity,
            'unit':         self.unit,
            'amount':       round(self.amount, 2)
        }
