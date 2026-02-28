from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import func

from models import db, Upload, SalesRecord

api_bp = Blueprint('api', __name__)


def _get_active_upload():
    return Upload.query.filter_by(user_id=current_user.id, is_active=True).first()


def _apply_filters(q, upload_id):
    """Apply category, product, date_from, date_to from request args."""
    q = q.filter(SalesRecord.upload_id == upload_id)

    cat = request.args.get('category', 'all')
    if cat and cat != 'all':
        q = q.filter(SalesRecord.category == cat)

    product = request.args.get('product', 'all')
    if product and product != 'all':
        q = q.filter(SalesRecord.product == product)

    date_from = request.args.get('date_from', '').strip()
    date_to   = request.args.get('date_to',   '').strip()
    if date_from:
        q = q.filter(SalesRecord.sale_date >= date_from)
    if date_to:
        q = q.filter(SalesRecord.sale_date <= date_to)

    return q


@api_bp.route('/stats')
@login_required
def stats():
    upload = _get_active_upload()
    if not upload:
        return jsonify({'error': 'No active upload'}), 404

    q = _apply_filters(SalesRecord.query, upload.id)
    row = q.with_entities(
        func.sum(SalesRecord.amount),
        func.count(SalesRecord.id),
        func.count(func.distinct(SalesRecord.party_name)),
        func.count(func.distinct(SalesRecord.product)),
        func.count(func.distinct(SalesRecord.invoice_no)),
        func.min(SalesRecord.sale_date),
        func.max(SalesRecord.sale_date),
    ).one()

    total, rec, cust, prod, inv, dmin, dmax = row
    total = total or 0
    return jsonify({
        'total_amount':     round(total, 2),
        'record_count':     rec or 0,
        'unique_customers': cust or 0,
        'unique_products':  prod or 0,
        'unique_invoices':  inv or 0,
        'date_from':        dmin.strftime('%d-%m-%Y') if dmin else 'N/A',
        'date_to':          dmax.strftime('%d-%m-%Y') if dmax else 'N/A',
        'avg_invoice':      round(total / max(inv or 1, 1), 2),
        'filename':         upload.original_name,
    })


@api_bp.route('/monthly')
@login_required
def monthly():
    upload = _get_active_upload()
    if not upload:
        return jsonify([])
    q = _apply_filters(SalesRecord.query, upload.id)
    rows = (q.filter(SalesRecord.month_key.isnot(None), SalesRecord.month_key != 'Unknown')
             .with_entities(SalesRecord.month_key, func.sum(SalesRecord.amount).label('total'))
             .group_by(SalesRecord.month_key)
             .order_by(SalesRecord.month_key)
             .all())
    return jsonify([{'month': r.month_key, 'amount': round(r.total, 2)} for r in rows])


@api_bp.route('/categories')
@login_required
def categories():
    upload = _get_active_upload()
    if not upload:
        return jsonify([])
    # categories endpoint ignores 'category' filter but respects date + product
    q = SalesRecord.query.filter(SalesRecord.upload_id == upload.id)
    date_from = request.args.get('date_from', '').strip()
    date_to   = request.args.get('date_to',   '').strip()
    if date_from:
        q = q.filter(SalesRecord.sale_date >= date_from)
    if date_to:
        q = q.filter(SalesRecord.sale_date <= date_to)
    rows = (q.with_entities(SalesRecord.category,
                            func.sum(SalesRecord.amount).label('total'),
                            func.count(SalesRecord.id).label('cnt'))
             .group_by(SalesRecord.category)
             .order_by(func.sum(SalesRecord.amount).desc())
             .all())
    grand = sum(r.total for r in rows) or 1
    return jsonify([{
        'category': r.category,
        'amount':   round(r.total, 2),
        'count':    r.cnt,
        'pct':      round(r.total / grand * 100, 1)
    } for r in rows])


@api_bp.route('/top-products')
@login_required
def top_products():
    upload = _get_active_upload()
    if not upload:
        return jsonify([])
    limit = int(request.args.get('limit', 15))
    q = _apply_filters(SalesRecord.query, upload.id)
    rows = (q.with_entities(
                SalesRecord.product, SalesRecord.category,
                func.sum(SalesRecord.amount).label('total'),
                func.sum(SalesRecord.quantity).label('qty'),
                func.count(func.distinct(SalesRecord.invoice_no)).label('inv'))
             .group_by(SalesRecord.product, SalesRecord.category)
             .order_by(func.sum(SalesRecord.amount).desc())
             .limit(limit).all())
    grand_q = SalesRecord.query.filter(SalesRecord.upload_id == upload.id)
    date_from = request.args.get('date_from', '').strip()
    date_to   = request.args.get('date_to',   '').strip()
    if date_from: grand_q = grand_q.filter(SalesRecord.sale_date >= date_from)
    if date_to:   grand_q = grand_q.filter(SalesRecord.sale_date <= date_to)
    grand = grand_q.with_entities(func.sum(SalesRecord.amount)).scalar() or 1
    return jsonify([{
        'product':  r.product, 'category': r.category,
        'amount':   round(r.total, 2), 'qty': round(r.qty or 0, 2),
        'invoices': r.inv, 'pct': round(r.total / grand * 100, 1)
    } for r in rows])


@api_bp.route('/top-customers')
@login_required
def top_customers():
    upload = _get_active_upload()
    if not upload:
        return jsonify([])
    limit = int(request.args.get('limit', 10))
    q = _apply_filters(SalesRecord.query, upload.id)
    rows = (q.with_entities(
                SalesRecord.party_name,
                func.sum(SalesRecord.amount).label('total'),
                func.count(func.distinct(SalesRecord.invoice_no)).label('inv'),
                func.count(func.distinct(SalesRecord.product)).label('prods'))
             .group_by(SalesRecord.party_name)
             .order_by(func.sum(SalesRecord.amount).desc())
             .limit(limit).all())
    grand = _apply_filters(SalesRecord.query, upload.id)\
                .with_entities(func.sum(SalesRecord.amount)).scalar() or 1
    return jsonify([{
        'customer': r.party_name, 'amount': round(r.total, 2),
        'invoices': r.inv, 'products': r.prods,
        'pct': round(r.total / grand * 100, 1)
    } for r in rows])


@api_bp.route('/product-breakdown')
@login_required
def product_breakdown():
    """All products within a category (or all), filtered by date."""
    upload = _get_active_upload()
    if not upload:
        return jsonify([])
    limit = int(request.args.get('limit', 25))
    q = SalesRecord.query.filter(SalesRecord.upload_id == upload.id)
    cat = request.args.get('category', 'all')
    date_from = request.args.get('date_from', '').strip()
    date_to   = request.args.get('date_to',   '').strip()
    if cat and cat != 'all':
        q = q.filter(SalesRecord.category == cat)
    if date_from: q = q.filter(SalesRecord.sale_date >= date_from)
    if date_to:   q = q.filter(SalesRecord.sale_date <= date_to)
    rows = (q.with_entities(
                SalesRecord.product,
                func.sum(SalesRecord.amount).label('total'),
                func.sum(SalesRecord.quantity).label('qty'),
                func.count(func.distinct(SalesRecord.invoice_no)).label('inv'),
                func.count(func.distinct(SalesRecord.party_name)).label('custs'))
             .group_by(SalesRecord.product)
             .order_by(func.sum(SalesRecord.amount).desc())
             .limit(limit).all())
    grand = q.with_entities(func.sum(SalesRecord.amount)).scalar() or 1
    return jsonify([{
        'product':   r.product, 'amount': round(r.total, 2),
        'qty':       round(r.qty or 0, 1), 'invoices': r.inv,
        'customers': r.custs, 'pct': round(r.total / grand * 100, 1)
    } for r in rows])


@api_bp.route('/product-trend')
@login_required
def product_trend():
    """Monthly trend filtered by category + product + date."""
    upload = _get_active_upload()
    if not upload:
        return jsonify([])
    q = _apply_filters(SalesRecord.query, upload.id)
    rows = (q.filter(SalesRecord.month_key.isnot(None), SalesRecord.month_key != 'Unknown')
             .with_entities(
                SalesRecord.month_key,
                func.sum(SalesRecord.amount).label('total'),
                func.sum(SalesRecord.quantity).label('qty'))
             .group_by(SalesRecord.month_key)
             .order_by(SalesRecord.month_key)
             .all())
    return jsonify([{
        'month': r.month_key,
        'amount': round(r.total, 2),
        'qty':    round(r.qty or 0, 1)
    } for r in rows])


@api_bp.route('/category-list')
@login_required
def category_list():
    upload = _get_active_upload()
    if not upload:
        return jsonify([])
    rows = (SalesRecord.query.filter_by(upload_id=upload.id)
             .with_entities(SalesRecord.category, func.sum(SalesRecord.amount).label('total'))
             .group_by(SalesRecord.category)
             .order_by(func.sum(SalesRecord.amount).desc())
             .all())
    return jsonify([{'category': r.category, 'total': round(r.total, 2)} for r in rows])


@api_bp.route('/product-list')
@login_required
def product_list():
    upload = _get_active_upload()
    if not upload:
        return jsonify([])
    cat = request.args.get('category', 'all')
    q = SalesRecord.query.filter_by(upload_id=upload.id)
    if cat and cat != 'all':
        q = q.filter(SalesRecord.category == cat)
    rows = (q.with_entities(SalesRecord.product)
             .distinct().order_by(SalesRecord.product).all())
    return jsonify([r.product for r in rows])


@api_bp.route('/transactions')
@login_required
def transactions():
    upload = _get_active_upload()
    if not upload:
        return jsonify({'records': [], 'total': 0, 'pages': 0})
    page     = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    search   = request.args.get('search', '').strip()
    sort_by  = request.args.get('sort', 'amount')
    q = _apply_filters(SalesRecord.query, upload.id)
    if search:
        like = f'%{search}%'
        q = q.filter(db.or_(
            SalesRecord.party_name.ilike(like),
            SalesRecord.product.ilike(like),
            SalesRecord.invoice_no.ilike(like),
            SalesRecord.category.ilike(like),
        ))
    sort_map = {'amount': SalesRecord.amount.desc(), 'date': SalesRecord.sale_date.desc(),
                'party': SalesRecord.party_name.asc(), 'product': SalesRecord.product.asc()}
    q = q.order_by(sort_map.get(sort_by, SalesRecord.amount.desc()))
    total   = q.count()
    records = q.offset((page - 1) * per_page).limit(per_page).all()
    return jsonify({
        'records': [r.to_dict() for r in records],
        'total': total, 'pages': (total + per_page - 1) // per_page, 'page': page,
    })


@api_bp.route('/date-bounds')
@login_required
def date_bounds():
    upload = _get_active_upload()
    if not upload:
        return jsonify({})
    row = (SalesRecord.query
           .filter(SalesRecord.upload_id == upload.id, SalesRecord.sale_date.isnot(None))
           .with_entities(func.min(SalesRecord.sale_date), func.max(SalesRecord.sale_date))
           .one())
    return jsonify({
        'min': row[0].strftime('%Y-%m-%d') if row[0] else '',
        'max': row[1].strftime('%Y-%m-%d') if row[1] else '',
    })


@api_bp.route('/uploads')
@login_required
def uploads():
    rows = (Upload.query.filter_by(user_id=current_user.id)
             .order_by(Upload.uploaded_at.desc()).all())
    return jsonify([{
        'id': u.id, 'name': u.original_name,
        'records': u.record_count, 'amount': round(u.total_amount, 2),
        'uploaded_at': u.uploaded_at.strftime('%d %b %Y, %H:%M'),
        'is_active': u.is_active,
    } for u in rows])
