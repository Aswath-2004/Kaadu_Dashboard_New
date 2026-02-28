# 🌿 Kaadu Organic Sales Dashboard

A professional full-stack web application for analyzing and visualizing organic farm sales data. Upload any CSV or Excel file and get instant interactive analytics.

---

## 🚀 Quick Start

---

## 📁 Project Structure

```
kaadu/
├── app.py                  # Flask application entry point
├── config.py               # Configuration (dev/prod)
├── models.py               # SQLAlchemy database models
├── requirements.txt        # Python dependencies
├── routes/
│   ├── auth.py             # Login, Register, Logout
│   ├── main.py             # Dashboard & file upload
│   └── api.py              # JSON API endpoints for charts
├── utils/
│   └── parser.py           # CSV/Excel parser with auto column detection
├── templates/
│   ├── base.html
│   ├── auth/
│   │   ├── login.html
│   │   └── register.html
│   └── dashboard/
│       └── index.html      # Main dashboard
├── static/
│   ├── css/main.css
│   └── js/main.js
├── uploads/                # Uploaded files stored here
└── instance/
    └── kaadu.db            # SQLite database (auto-created)
```

---

## 📊 Features

### Authentication
- User registration & login
- Bcrypt-hashed passwords
- Remember me / session management
- Per-user data isolation

### File Upload
- Drag & drop or file picker
- Supports CSV, XLSX, XLS
- Up to 16MB file size
- **Auto-detects column names** — works with any column format
- Multiple uploads per user with ability to switch active dataset

### Dashboard Analytics
- **KPI Cards**: Total Revenue, Invoices, Customers, Products, Avg Invoice
- **Monthly Revenue Bar Chart**
- **Category Distribution Pie Chart**
- **Top 10 Products Horizontal Bar**
- **Top 10 Customers Table** with revenue bars
- **Category Comparison Column Chart**
- **Revenue Trend Lines** (top 3 categories)
- **Month × Category Heatmap**
- **Category Doughnut** breakdown
- **Full Products Table** with ranking

### Transactions
- Paginated full transaction history (50 per page)
- Search by customer, product, invoice number
- Filter by category
- Sort by amount, date, customer, or product

### Upload History
- View all uploaded files
- Switch between datasets
- Delete uploads (removes records from DB)

---

## 🗃️ Database Schema

### Users
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| username | String | Unique login name |
| email | String | Unique email |
| password_hash | String | Bcrypt hash |
| full_name | String | Display name |
| role | String | 'admin' or 'user' |

### Uploads
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| user_id | Integer | Owner (FK) |
| original_name | String | Uploaded filename |
| record_count | Integer | Parsed row count |
| total_amount | Float | Sum of all amounts |
| is_active | Boolean | Currently selected |

### SalesRecord
| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| upload_id | Integer | Parent upload (FK) |
| sale_date | Date | Parsed date |
| month_key | String | 'YYYY-MM' for grouping |
| party_name | String | Customer |
| invoice_no | String | Invoice identifier |
| product | String | Product name |
| category | String | Auto-categorized |
| quantity | Float | Qty sold |
| amount | Float | Transaction amount |

---

## 📋 Supported CSV Column Names

The parser auto-detects columns using aliases. These column names (case-insensitive) are all recognized:

| Field | Accepted Column Names |
|-------|-----------------------|
| Date | date, sale date, invoice date, transaction date |
| Customer | party name, customer, buyer, client |
| Invoice | invoice no, invoice no., inv no, bill no |
| Product | product, item, product name, description |
| Quantity | quantity, qty, units |
| Unit | unit, uom, unit of measure |
| Price | price per unit, price, rate, unit price |
| Amount | amount, total, value, net amount, sales amount |

---

## 🌿 Product Categories (Auto-Detected)

- Jaggery Products
- Rice
- Oils
- Dals & Pulses
- Millets
- Spices
- Flours
- Coffee
- Health Products
- Honey
- Ghee & Butter
- Coconut
- Aval (Poha)
- Fresh Produce
- Sweets & Pickles

---



## 📦 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10+ / Flask 3.0 |
| Database | SQLite (SQLAlchemy ORM) |
| Auth | Flask-Login + Werkzeug bcrypt |
| File Parsing | pandas + openpyxl |
| Frontend | HTML5 + CSS3 + Vanilla JS |
| Charts | Chart.js 4.4 |
| Fonts | Google Fonts (Playfair Display + DM Sans) |


