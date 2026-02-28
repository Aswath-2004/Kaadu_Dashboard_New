import re
from datetime import date, timedelta, datetime

import pandas as pd


# ─────────────────────────────────────────────────
# COLUMN ALIASES
# Broad list — covers Kaadu's own exports + any
# standard accounting / billing CSV format
# ─────────────────────────────────────────────────
COL_ALIASES = {
    'date': [
        'date', 'sale date', 'invoice date', 'transaction date',
        'dt', 'trans_date', 'sale_date', 'bill date', 'order date',
    ],
    'party_name': [
        'party name', 'party', 'customer', 'customer name',
        'buyer', 'client', 'party_name', 'client name', 'sold to',
    ],
    'invoice_no': [
        'invoice no', 'invoice no.', 'invoice', 'inv no', 'inv_no',
        'invoice_no', 'bill no', 'bill_no', 'receipt no', 'order no',
        'invoice number', 'bill number',
    ],
    'product': [
        'product', 'item', 'product name', 'description',
        'item name', 'goods', 'item description', 'product description',
        'particulars', 'name', 'service', 'service name',
    ],
    'quantity': [
        'quantity', 'qty', 'units', 'quantity sold', 'no of units',
        'nos', 'pcs', 'pieces',
    ],
    'unit': [
        'unit', 'uom', 'unit of measure', 'measure', 'unit name',
    ],
    'price_per_unit': [
        'price per unit', 'price/unit', 'price / unit', 'unit price',
        'price', 'rate', 'mrp', 'price_per_unit', 'selling price',
        'sp', 'cost', 'cost price',
    ],
    'amount': [
        'amount', 'total', 'total amount', 'value', 'net amount',
        'sales amount', 'net', 'net_amount', 'total_amount',
        'sale amount', 'gross amount', 'taxable amount', 'line total',
        'subtotal', 'sub total', 'invoice amount', 'bill amount',
    ],
}


def _detect_column(df_cols, aliases):
    """Return first df column that matches any alias (case-insensitive)."""
    df_lower = {str(c).lower().strip(): c for c in df_cols}
    for alias in aliases:
        if alias in df_lower:
            return df_lower[alias]
    return None


# ─────────────────────────────────────────────────
# HEADER ROW AUTO-DETECTION
# Some exports prepend metadata rows (e.g. "Username / All Users").
# Scan up to the first 10 rows for the true header.
# ─────────────────────────────────────────────────
_HEADER_KEYWORDS = {
    'amount', 'total', 'date', 'party', 'customer', 'invoice',
    'product', 'item', 'qty', 'quantity', 'price', 'rate',
}

def _find_header_row(filepath: str, ext: str) -> int:
    """
    Returns the 0-based row index of the true header row.
    Scans the first 10 rows and picks the one whose cells have
    the most matches against known column keywords.
    Returns 0 if nothing better is found (standard files).
    """
    try:
        if ext == 'csv':
            raw = pd.read_csv(filepath, header=None, nrows=10,
                              encoding='utf-8', on_bad_lines='skip')
        else:
            raw = pd.read_excel(filepath, header=None, nrows=10,
                                engine='openpyxl' if ext == 'xlsx' else 'xlrd')
    except Exception:
        return 0

    best_row, best_score = 0, 0
    for idx, row in raw.iterrows():
        cells = [str(v).lower().strip() for v in row if pd.notna(v) and str(v).strip()]
        score = sum(
            1 for cell in cells
            if any(kw in cell for kw in _HEADER_KEYWORDS)
        )
        if score > best_score:
            best_score, best_row = score, idx

    return int(best_row)


# ─────────────────────────────────────────────────
# DATE PARSING  (handles 10+ common formats)
# ─────────────────────────────────────────────────
_DATE_FMTS = (
    '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%m/%d/%Y',
    '%d.%m.%Y', '%Y/%m/%d', '%d %b %Y', '%d %B %Y',
    '%Y%m%d',   '%d-%b-%Y', '%d %b %y', '%d/%m/%y',
)

def _excel_serial_to_date(val):
    try:
        return date(1899, 12, 30) + timedelta(days=int(float(val)))
    except Exception:
        return None

def _parse_date(val):
    if val is None:
        return None
    if isinstance(val, float) and pd.isna(val):
        return None
    if isinstance(val, (datetime, pd.Timestamp)):
        return val.date() if not pd.isnull(val) else None
    if isinstance(val, date):
        return val

    s = str(val).strip()
    if not s or s.lower() in ('nan', 'none', 'nat', ''):
        return None

    # Pure 5-digit Excel serial (e.g. 45295)
    if re.fullmatch(r'\d{5}', s):
        return _excel_serial_to_date(s)

    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass

    # Last resort: pandas
    try:
        return pd.to_datetime(s, dayfirst=True).date()
    except Exception:
        return None


# ─────────────────────────────────────────────────
# CATEGORIZATION
# ─────────────────────────────────────────────────
CATEGORY_RULES = [
    (['jaggery', 'sarkarai', 'vellam', 'nattu sarkarai',
      'palm jaggery', 'urundai', 'karupatti'],              'Jaggery Products'),
    (['rice', 'idly', 'ponni', 'seeraga', 'thooyamalli',
      'kichali', 'kullakar', 'aathur', 'mappillai',
      'kavuni', 'sornavari', 'kattuyanam'],                 'Rice'),
    (['oil', 'groundnut oil', 'sesame oil',
      'coconut oil', 'gingelly'],                           'Oils'),
    (['dal', 'dals', 'rajma', 'urad', 'channa',
      'horsegram', 'kollu', 'moong', 'toor',
      'green peas', 'pattani', 'black urad'],               'Dals & Pulses'),
    (['millet', 'ragi', 'kambu', 'thinai', 'varagu',
      'saamai', 'kuthiraivali', 'barnyard',
      'foxtail', 'kodo', 'proso', 'little millet'],         'Millets'),
    (['flour', 'maavu', 'rava', 'sooji',
      'semolina', 'idiyappam', 'puttu'],                    'Flours'),
    (['coffee'],                                            'Coffee'),
    (['moringa', 'health mix', 'mooligai',
      'herbal', 'sathumaavu'],                              'Health Products'),
    (['honey'],                                             'Honey'),
    (['ghee', 'butter'],                                    'Ghee & Butter'),
    (['turmeric', 'pepper', 'chilli', 'coriander',
      'cumin', 'jeera', 'ginger', 'cardamom', 'mustard',
      'fenugreek', 'asafoetida', 'hing', 'spice', 'masala',
      'tamarind', 'dry ginger'],                            'Spices'),
    (['coconut'],                                           'Coconut'),
    (['aval', 'poha', 'beaten rice'],                       'Aval (Poha)'),
    (['banana', 'mango', 'malai', 'fruit',
      'vegetables', 'veggie'],                              'Fresh Produce'),
    (['laddu', 'sweet', 'candy', 'chocolate'],              'Sweets'),
    (['pickle', 'thokku', 'chutney', 'pachadi'],            'Pickles'),
    (['tea', 'green tea', 'herbal tea'],                    'Tea'),
]

def categorize_product(product: str) -> str:
    if not product:
        return 'Other'
    p = product.lower()
    for keywords, category in CATEGORY_RULES:
        if any(kw in p for kw in keywords):
            return category
    return 'Other'


# ─────────────────────────────────────────────────
# AMOUNT CLEANER
# ─────────────────────────────────────────────────
def _clean_amount(series: pd.Series) -> pd.Series:
    """
    Strip currency symbols, commas, spaces.
    Also handles cases where the value is already numeric.
    """
    return (
        series.astype(str)
              .str.replace(r'[₹$€£,\s]', '', regex=True)   # currency & commas
              .str.replace(r'\(.*\)', '', regex=True)        # e.g. "(15.0%)" suffix
              .str.strip()
              .pipe(pd.to_numeric, errors='coerce')
              .fillna(0)
    )


# ─────────────────────────────────────────────────
# MAIN PARSER  — called from routes/main.py
# ─────────────────────────────────────────────────
def parse_sales_file(filepath: str, ext: str) -> dict:
    """
    Robustly parse a CSV or Excel sales file.

    Handles:
    - Extra metadata rows at the top (auto-detects real header row)
    - Any recognised column naming convention
    - Excel serial dates, DD/MM/YYYY, YYYY-MM-DD, etc.
    - Amount values as strings, with symbols or percentage suffixes
    """

    # ── 1. Find the real header row ────────────────
    header_row = _find_header_row(filepath, ext)

    # ── 2. Load file with correct header ───────────
    read_kwargs = dict(
        header     = header_row,
        dtype      = str,          # read everything as string first
        na_values  = ['', 'NA', 'N/A', 'null', 'NULL', 'None', '-'],
        keep_default_na = False,
    )

    if ext == 'csv':
        try:
            df = pd.read_csv(filepath, encoding='utf-8', **read_kwargs)
        except UnicodeDecodeError:
            df = pd.read_csv(filepath, encoding='latin-1', **read_kwargs)
        except Exception:
            df = pd.read_csv(filepath, encoding='utf-8',
                             on_bad_lines='skip', **read_kwargs)
    else:
        engine = 'openpyxl' if ext == 'xlsx' else 'xlrd'
        df = pd.read_excel(filepath, engine=engine, **read_kwargs)

    # Strip column names
    df.columns = [str(c).strip() for c in df.columns]

    # Drop completely empty rows
    df.dropna(how='all', inplace=True)

    # ── 3. Map columns ─────────────────────────────
    col_map = {
        field: _detect_column(df.columns, aliases)
        for field, aliases in COL_ALIASES.items()
    }

    amount_col = col_map.get('amount')
    if not amount_col:
        raise ValueError(
            f"Could not detect an 'Amount' column.\n"
            f"Columns found: {list(df.columns)}\n"
            f"Please ensure your file has a column named one of: "
            f"{COL_ALIASES['amount']}"
        )

    # ── 4. Clean & filter by amount ────────────────
    df['_amount'] = _clean_amount(df[amount_col])
    df = df[df['_amount'] > 0].copy()

    if df.empty:
        raise ValueError(
            "No rows with a positive Amount value found after parsing. "
            "Check that the Amount column contains numeric sales figures."
        )

    # ── 5. Build records ───────────────────────────
    records     = []
    dates_found = []

    def gcol(row, field):
        """Safely get a cell value, returning None for NaN / missing."""
        c = col_map.get(field)
        if not c or c not in row.index:
            return None
        v = row[c]
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        s = str(v).strip()
        return s if s and s.lower() not in ('nan', 'none', 'nat') else None

    for _, row in df.iterrows():
        sale_date = _parse_date(gcol(row, 'date'))
        month_key = (
            f"{sale_date.year}-{sale_date.month:02d}"
            if sale_date else 'Unknown'
        )
        if sale_date:
            dates_found.append(sale_date)

        product_val = (gcol(row, 'product') or '').strip()
        category    = categorize_product(product_val)

        try:
            qty = float(gcol(row, 'quantity') or 0)
        except (ValueError, TypeError):
            qty = 0.0

        try:
            ppu_raw = gcol(row, 'price_per_unit') or '0'
            ppu = float(re.sub(r'[^\d.]', '', ppu_raw) or 0)
        except (ValueError, TypeError):
            ppu = 0.0

        records.append({
            'sale_date':     sale_date,
            'month_key':     month_key,
            'party_name':    (gcol(row, 'party_name') or 'Unknown')[:255],
            'invoice_no':    (gcol(row, 'invoice_no') or '')[:50],
            'product':       product_val[:500],
            'category':      category,
            'quantity':      qty,
            'unit':          (gcol(row, 'unit') or '')[:20],
            'price_per_unit': ppu,
            'amount':        float(row['_amount']),
        })

    # ── 6. Compute summary stats ───────────────────
    total     = sum(r['amount'] for r in records)
    customers = len({r['party_name'] for r in records
                     if r['party_name'] not in ('Unknown', '')})
    products  = len({r['product'] for r in records if r['product']})
    invoices  = len({r['invoice_no'] for r in records if r['invoice_no']})
    date_from = min(dates_found).strftime('%d-%m-%Y') if dates_found else 'N/A'
    date_to   = max(dates_found).strftime('%d-%m-%Y') if dates_found else 'N/A'

    return {
        'records':           records,
        'record_count':      len(records),
        'total_amount':      round(total, 2),
        'unique_customers':  customers,
        'unique_products':   products,
        'unique_invoices':   invoices,
        'date_from':         date_from,
        'date_to':           date_to,
    }
