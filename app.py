"""
Real Estate Management Dashboard
================================
A single-file Streamlit application for real estate agencies.

Modules: Dashboard, Properties, Customers, Agents, Inquiries & Viewings,
Sales & Transactions, Rentals, Payments, Reports & Analytics, About & Help.

Storage: records are kept in Streamlit Session State and saved to a local JSON
file (realestate_data.json) after every successful change.
NOTE: on Streamlit Community Cloud this local file is NOT guaranteed to survive
restarts or redeployments - use the backup download in "About & Help".

Run locally:  streamlit run app.py
"""

import calendar
import html
import json
import math
import re
from datetime import date, time as dtime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import streamlit as st

# set_page_config must be the first Streamlit command
st.set_page_config(page_title="Real Estate Management Dashboard", page_icon="🏠", layout="wide")

# =============================================================================
# 1. CONSTANTS
# =============================================================================
DATA_FILE = Path("realestate_data.json")
TABLES = ["properties", "customers", "agents", "inquiries", "transactions", "rentals", "payments"]
ID_PREFIX = {"properties": "PRP", "customers": "CUS", "agents": "AGT", "inquiries": "INQ",
             "transactions": "TXN", "rentals": "RNT", "payments": "PAY"}

PROPERTY_TYPES = ["House", "Apartment", "Residential Plot", "Commercial Plot", "Shop", "Office", "Farmhouse"]
LISTING_TYPES = ["For Sale", "For Rent"]
AREA_UNITS = ["Marla", "Kanal", "Square Feet", "Square Yards"]
PROPERTY_STATUSES = ["Available", "Under Negotiation", "Sold", "Rented"]
CUSTOMER_TYPES = ["Buyer", "Seller", "Tenant", "Landlord"]
EMPLOYMENT_STATUSES = ["Active", "On Leave", "Resigned"]
CONTACT_METHODS = ["Phone", "WhatsApp", "Email", "In Person"]
INQUIRY_STATUSES = ["New", "Contacted", "Viewing Scheduled", "Negotiation", "Converted", "Closed"]
TXN_STATUSES = ["Pending", "Completed", "Cancelled"]
RENTAL_STATUSES = ["Active", "Expired", "Terminated"]
PAYMENT_TYPES = ["Sale Payment", "Monthly Rent", "Security Deposit", "Commission", "Other"]
PAYMENT_METHODS = ["Cash", "Bank Transfer", "Other"]
PAYMENT_STATUSES = ["Paid", "Pending", "Partially Paid", "Overdue"]

STATUS_ICONS = {
    "Available": "🟢", "Under Negotiation": "🟡", "Sold": "🔴", "Rented": "🔵",
    "Paid": "🟢", "Pending": "🟡", "Partially Paid": "🟠", "Overdue": "🔴", "Unpaid": "🔴",
    "Completed": "🟢", "Cancelled": "⚫", "Active": "🟢", "Expired": "⚪", "Terminated": "🔴",
    "New": "🔵", "Contacted": "🟣", "Viewing Scheduled": "🟡", "Negotiation": "🟠",
    "Converted": "🟢", "Closed": "⚫", "On Leave": "🟡", "Resigned": "🔴",
}
BADGE_COLORS = {
    "Available": "#0b6e4f", "Under Negotiation": "#b7791f", "Sold": "#c53030", "Rented": "#2b6cb0",
    "For Sale": "#0b2545", "For Rent": "#2c7a7b",
}

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[0-9\-\s()]{7,20}$")

CUSTOM_CSS = """
<style>
.block-container {padding-top: 1.5rem;}
.page-title {font-size: 1.9rem; font-weight: 700; margin-bottom: 0; border-left: 6px solid #0b6e4f; padding-left: 12px;}
.page-sub {opacity: .75; margin: 4px 0 1rem 18px;}
.kpi-card {background:#ffffff; border:1px solid #e3e8ef; border-left:5px solid #0b6e4f; border-radius:10px;
           padding:12px 16px; box-shadow:0 1px 3px rgba(16,24,40,.08); margin-bottom:10px;}
.kpi-label {color:#5b6b7f; font-size:.78rem;}
.kpi-value {color:#0b2545; font-size:1.45rem; font-weight:700; word-break:break-word;}
.prop-card {background:#ffffff; border:1px solid #e3e8ef; border-radius:12px; overflow:hidden;
            box-shadow:0 1px 4px rgba(16,24,40,.08); margin-bottom:8px;}
.img-box {position:relative; width:100%; background:linear-gradient(135deg,#dbeafe,#d1fae5);
          display:flex; align-items:center; justify-content:center; overflow:hidden;}
.img-ph {font-size:3rem; opacity:.55;}
.prop-body {padding:10px 14px 12px 14px; color:#1a202c;}
.prop-title {font-weight:700; font-size:1rem; color:#0b2545; min-height:2.5em; line-height:1.25;}
.prop-price {color:#0b6e4f; font-weight:700; font-size:1.1rem;}
.prop-meta {color:#4a5568; font-size:.84rem; margin:2px 0;}
.badge {display:inline-block; color:#ffffff; border-radius:999px; padding:2px 10px; font-size:.72rem; margin:5px 4px 0 0;}
</style>
"""


# =============================================================================
# 2. SMALL HELPER FUNCTIONS
# =============================================================================
def esc(x):
    """HTML-escape any value (used before inserting text into HTML)."""
    return html.escape("" if x is None else str(x))


def txt(x):
    """Convert None to empty string, everything else to str."""
    return "" if x is None else str(x)


def num(x, default=0.0):
    """Safely convert to float (handles None, text and NaN)."""
    try:
        v = float(x)
        return v if v == v else default
    except (TypeError, ValueError):
        return default


def money(x):
    """Format a number as Pakistani Rupees, e.g. PKR 1,250,000."""
    return f"PKR {num(x):,.0f}"


def short_money(x):
    """Short PKR label using Lac / Crore (used for chart labels)."""
    x = num(x)
    if abs(x) >= 1e7:
        return f"{x / 1e7:.2f} Cr"
    if abs(x) >= 1e5:
        return f"{x / 1e5:.1f} Lac"
    return f"{x:,.0f}"


def parse_date(value):
    """Convert 'YYYY-MM-DD' text to a date, or None if invalid."""
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def safe_index(options, value):
    """Index of value in options, or 0 when missing (for selectbox defaults)."""
    return options.index(value) if value in options else 0


def valid_url(u):
    try:
        p = urlparse(txt(u).strip())
        return p.scheme in ("http", "https") and bool(p.netloc)
    except ValueError:
        return False


def badge(text):
    color = BADGE_COLORS.get(text, "#4a5568")
    return f'<span class="badge" style="background:{color}">{esc(text)}</span>'


def kpi_row(items):
    """Show a row of KPI cards. items = [(label, value, accent_color), ...]"""
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        label, value = item[0], item[1]
        accent = item[2] if len(item) > 2 else "#0b6e4f"
        col.markdown(
            f'<div class="kpi-card" style="border-left-color:{accent}">'
            f'<div class="kpi-label">{esc(label)}</div><div class="kpi-value">{esc(value)}</div></div>',
            unsafe_allow_html=True)


def page_header(title, subtitle=""):
    st.markdown(f'<div class="page-title">{esc(title)}</div><div class="page-sub">{esc(subtitle)}</div>',
                unsafe_allow_html=True)


def show_table(df, money_cols=(), status_cols=(), hide=(), empty_msg="No records found."):
    """Display a DataFrame nicely: PKR formatting, status icons, hidden helper columns."""
    if df is None or df.empty:
        st.info(empty_msg)
        return
    out = df.drop(columns=[c for c in hide if c in df.columns]).copy()
    for c in money_cols:
        if c in out.columns:
            out[c] = out[c].map(money)
    for c in status_cols:
        if c in out.columns:
            out[c] = out[c].map(lambda s: f"{STATUS_ICONS.get(s, '⚪')} {s}")
    out = out.rename(columns=lambda c: c.replace(" (PKR)", ""))
    st.dataframe(out, hide_index=True)


def csv_bytes(df):
    """CSV with BOM so Excel opens it correctly."""
    return df.to_csv(index=False).encode("utf-8-sig")


# =============================================================================
# 3. DATA STORAGE (JSON file + Session State)
# =============================================================================
def clean_loaded(raw):
    """Keep only valid dict records with unique IDs. Ignores corrupted rows."""
    data = {t: [] for t in TABLES}
    if not isinstance(raw, dict):
        raise ValueError("Data file must contain a JSON object.")
    for t in TABLES:
        rows = raw.get(t, [])
        seen = set()
        if isinstance(rows, list):
            for r in rows:
                if isinstance(r, dict) and r.get("id") and str(r["id"]) not in seen:
                    r["id"] = str(r["id"])
                    seen.add(r["id"])
                    data[t].append(r)
    return data


def load_data():
    """Load saved data. Returns (data, warning_message_or_None)."""
    empty = {t: [] for t in TABLES}
    if not DATA_FILE.exists():
        return empty, None
    try:
        return clean_loaded(json.loads(DATA_FILE.read_text(encoding="utf-8"))), None
    except (OSError, ValueError) as exc:
        # Keep the unreadable file as a backup so nothing is silently overwritten
        try:
            DATA_FILE.replace(DATA_FILE.with_suffix(".corrupted.json"))
        except OSError:
            pass
        return empty, (f"The saved data file could not be read ({exc}). It was kept as "
                       f"'{DATA_FILE.with_suffix('.corrupted.json').name}' and the app started empty.")


def save_data():
    """Write the database to disk safely (temp file, then replace)."""
    try:
        tmp = DATA_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(st.session_state.db, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(DATA_FILE)
        return True
    except OSError:
        st.session_state.save_failed = True
        return False


def db():
    return st.session_state.db


def flash(msg, kind="success"):
    """Queue a message that is shown after the next rerun."""
    st.session_state.setdefault("flash", []).append((kind, msg))


def show_flash():
    for kind, msg in st.session_state.pop("flash", []):
        getattr(st, kind)(msg)


def finish(msg, kind="success"):
    """Finish an action: queue message, refresh form widgets and rerun the page."""
    flash(msg, kind)
    if st.session_state.pop("save_failed", False):
        flash("The data file could not be written, so changes exist only in this session. "
              "Download a backup from 'About & Help'.", "warning")
    st.session_state.nonce += 1
    st.rerun()


def init_state():
    if "db" not in st.session_state:
        data, warning = load_data()
        st.session_state.db = data
        if warning:
            flash(warning, "warning")
    st.session_state.setdefault("nonce", 0)


def K(name):
    """Widget key that changes after each successful save, which resets form fields."""
    return f"{name}_{st.session_state.nonce}"


# ----- record helpers -----
def get_rec(table, rid):
    return next((r for r in db()[table] if r.get("id") == rid), None)


def next_id(table):
    prefix = ID_PREFIX[table]
    existing = {r["id"].lower() for r in db()[table]}
    highest = 0
    for rid in existing:
        m = re.fullmatch(prefix.lower() + r"-(\d+)", rid)
        if m:
            highest = max(highest, int(m.group(1)))
    n = highest + 1
    while f"{prefix}-{n:04d}".lower() in existing:
        n += 1
    return f"{prefix}-{n:04d}"


def resolve_id(table, custom):
    """Return (new_id, error). Empty custom ID -> auto-generated unique ID."""
    custom = txt(custom).strip()
    if not custom:
        return next_id(table), None
    if not re.fullmatch(r"[A-Za-z0-9_-]{3,24}", custom):
        return None, "Custom ID may only contain letters, digits, '-' and '_' (3 to 24 characters)."
    if any(r["id"].lower() == custom.lower() for r in db()[table]):
        return None, f"ID '{custom}' already exists. Please choose a different ID."
    return custom, None


def add_record(table, rec):
    db()[table].append(rec)
    save_data()


def update_record(table, rid, changes):
    rec = get_rec(table, rid)
    if rec is None:
        return False
    rec.update(changes)
    save_data()
    return True


def delete_record(table, rid):
    db()[table] = [r for r in db()[table] if r.get("id") != rid]
    save_data()


def field_of(table, rid, field, default=""):
    r = get_rec(table, rid)
    return txt(r.get(field, default)) if r else default


def agent_name(aid):
    return field_of("agents", aid, "name")


def cust_name(cid):
    return field_of("customers", cid, "name")


def prop_title(pid):
    return field_of("properties", pid, "title")


def related_property_id(related_id):
    """Property linked to a transaction or rental agreement."""
    for table in ("transactions", "rentals"):
        r = get_rec(table, related_id)
        if r:
            return r.get("property_id", "")
    return ""


def label_of(table, rid):
    """Readable label for selectboxes."""
    if not rid:
        return "— None —"
    r = get_rec(table, rid)
    if not r:
        return f"{rid} (missing)"
    if table == "properties":
        return f"{rid} · {r.get('title', '')}"
    if table in ("customers", "agents"):
        return f"{rid} · {r.get('name', '')}"
    suffix = " [Cancelled]" if r.get("status") == "Cancelled" else ""
    if table == "payments":
        return f"{rid} · {r.get('payment_type', '')} · {money(r.get('amount'))}"
    return f"{rid} · {prop_title(r.get('property_id'))}{suffix}"


def select_id(label, table, key, allow_none=False, default=None, filter_fn=None):
    """Selectbox of record IDs with readable labels. Returns the chosen ID (or None if no options)."""
    ids = [r["id"] for r in db()[table] if filter_fn is None or filter_fn(r)]
    if allow_none:
        ids = [""] + ids
    if not ids:
        return None
    return st.selectbox(label, ids, index=safe_index(ids, default), format_func=lambda x: label_of(table, x), key=key)


# which tables point to a record (used to block unsafe deletes)
REFERENCES = {
    "properties": [("transactions", "property_id"), ("rentals", "property_id"), ("inquiries", "property_id")],
    "customers": [("inquiries", "customer_id"), ("transactions", "buyer_id"), ("transactions", "seller_id"),
                  ("rentals", "tenant_id"), ("rentals", "landlord_id"), ("payments", "customer_id")],
    "agents": [("properties", "agent_id"), ("inquiries", "agent_id"), ("transactions", "agent_id")],
    "transactions": [("payments", "related_id")],
    "rentals": [("payments", "related_id")],
}


def references_to(table, rid):
    msgs = []
    for other, field in REFERENCES.get(table, []):
        n = sum(1 for r in db()[other] if r.get(field) == rid)
        if n:
            msgs.append(f"{n} record(s) in {other} ({field.replace('_', ' ')})")
    return msgs


def delete_panel(table, entity):
    """Reusable delete section with confirmation and relationship checks."""
    if not db()[table]:
        st.info(f"There are no {entity} records to delete.")
        return
    rid = select_id(f"Select {entity} to delete", table, K(f"del_{table}"))
    refs = references_to(table, rid)
    if refs:
        st.warning(f"This {entity} cannot be deleted because it is used by: " + "; ".join(refs) +
                   ". Remove or reassign those records first.")
        return
    st.error(f"You are about to permanently delete **{label_of(table, rid)}**.")
    ok = st.checkbox("Yes, I understand this cannot be undone.", key=K(f"delok_{table}"))
    if st.button(f"Delete {entity}", type="primary", disabled=not ok, key=K(f"delbtn_{table}")):
        delete_record(table, rid)
        finish(f"{entity.capitalize()} {rid} deleted.")


# =============================================================================
# 4. BUSINESS LOGIC (status rules, totals, schedules)
# =============================================================================
def derived_property_status(pid):
    """Property status is always derived from transactions, rentals and inquiries."""
    d = db()
    if any(t.get("property_id") == pid and t.get("status") == "Completed" for t in d["transactions"]):
        return "Sold"
    if any(r.get("property_id") == pid and r.get("status") == "Active" for r in d["rentals"]):
        return "Rented"
    if any(t.get("property_id") == pid and t.get("status") == "Pending" for t in d["transactions"]):
        return "Under Negotiation"
    if any(i.get("property_id") == pid and i.get("status") == "Negotiation" for i in d["inquiries"]):
        return "Under Negotiation"
    return "Available"


def sync_data():
    """Keep derived fields consistent: expire rentals, flag overdue payments, update property status."""
    changed = False
    today = date.today()
    for r in db()["rentals"]:
        end = parse_date(r.get("end_date"))
        if r.get("status") == "Active" and end and end < today:
            r["status"] = "Expired"
            changed = True
    for p in db()["payments"]:
        due = parse_date(p.get("due_date"))
        if p.get("status") == "Pending" and due and due < today:
            p["status"] = "Overdue"
            changed = True
    for prop in db()["properties"]:
        new = derived_property_status(prop["id"])
        if prop.get("status") != new:
            prop["status"] = new
            changed = True
    if changed:
        save_data()


def valid_payments():
    """Payments that count in totals (payments of cancelled transactions are excluded)."""
    cancelled = {t["id"] for t in db()["transactions"] if t.get("status") == "Cancelled"}
    return [p for p in db()["payments"] if p.get("related_id") not in cancelled]


def balance_of(p):
    return max(num(p.get("amount")) - num(p.get("amount_paid")), 0.0)


def total_sales_revenue():
    return sum(num(t.get("sale_price")) for t in db()["transactions"] if t.get("status") == "Completed")


def total_rental_income():
    """Rental income = rent actually received (Monthly Rent payments). Deposits are not income."""
    return sum(num(p.get("amount_paid")) for p in valid_payments() if p.get("payment_type") == "Monthly Rent")


def total_outstanding():
    return sum(balance_of(p) for p in valid_payments() if p.get("status") in ("Pending", "Partially Paid", "Overdue"))


def txn_received(tid):
    return sum(num(p.get("amount_paid")) for p in db()["payments"]
               if p.get("related_id") == tid and p.get("payment_type") == "Sale Payment")


def txn_payment_status(t):
    paid = txn_received(t["id"])
    if paid <= 0:
        return "Unpaid"
    return "Paid" if paid >= num(t.get("sale_price")) - 0.01 else "Partially Paid"


def agent_stats(aid):
    d = db()
    sales = [t for t in d["transactions"] if t.get("agent_id") == aid and t.get("status") == "Completed"]
    my_props = {p["id"] for p in d["properties"] if p.get("agent_id") == aid}
    rentals = [r for r in d["rentals"] if r.get("property_id") in my_props and r.get("status") in ("Active", "Expired")]
    return {
        "assigned": len(my_props),
        "sales": len(sales),
        "rentals": len(rentals),
        "completed": len(sales) + len(rentals),
        "commission": sum(num(t.get("commission_amount")) for t in sales),
        "revenue": sum(num(t.get("sale_price")) for t in sales),
    }


def sale_eligible(p):
    """A property can be sold only if it is For Sale, not sold/rented and has no open or completed transaction."""
    if p.get("listing_type") != "For Sale" or p.get("status") in ("Sold", "Rented"):
        return False
    return not any(t.get("property_id") == p["id"] and t.get("status") in ("Pending", "Completed")
                   for t in db()["transactions"])


def rental_overlap(pid, start, end, ignore_id=None):
    """Return the first non-terminated agreement of the property overlapping start..end, or None."""
    for r in db()["rentals"]:
        if r.get("property_id") != pid or r.get("id") == ignore_id or r.get("status") == "Terminated":
            continue
        s, e = parse_date(r.get("start_date")), parse_date(r.get("end_date"))
        if s and e and start <= e and s <= end:
            return r
    return None


def generate_rent_schedule(rid):
    """Create Pending 'Monthly Rent' payments (and a security deposit) for an agreement. Skips duplicates."""
    r = get_rec("rentals", rid)
    if not r:
        return 0
    start, end = parse_date(r.get("start_date")), parse_date(r.get("end_date"))
    if not start or not end:
        return 0
    due_day = max(1, min(int(num(r.get("due_day"), 1)), 28))
    existing = {(p.get("related_id"), p.get("payment_type"), p.get("due_date")) for p in db()["payments"]}
    created, today = 0, date.today()
    y, m = start.year, start.month

    def new_payment(ptype, amount, due):
        rec = {"id": next_id("payments"), "related_type": "Rental Agreement", "related_id": rid,
               "customer_id": r.get("tenant_id", ""), "payment_type": ptype, "amount": float(amount),
               "amount_paid": 0.0, "payment_date": "", "due_date": due.isoformat(), "method": "Cash",
               "status": "Overdue" if due < today else "Pending", "reference": "",
               "notes": "Auto-generated from rent schedule"}
        db()["payments"].append(rec)

    if num(r.get("security_deposit")) > 0 and (rid, "Security Deposit", start.isoformat()) not in existing \
            and not any(p.get("related_id") == rid and p.get("payment_type") == "Security Deposit" for p in db()["payments"]):
        new_payment("Security Deposit", num(r.get("security_deposit")), start)
        created += 1
    while date(y, m, 1) <= end and created < 240:
        due = date(y, m, min(due_day, calendar.monthrange(y, m)[1]))
        if start <= due <= end and (rid, "Monthly Rent", due.isoformat()) not in existing:
            new_payment("Monthly Rent", num(r.get("monthly_rent")), due)
            created += 1
        m += 1
        if m > 12:
            m, y = 1, y + 1
    save_data()
    return created


# =============================================================================
# 5. DATAFRAME BUILDERS (readable tables used by pages, reports and CSV export)
# =============================================================================
PROP_COLS = ["Property ID", "Title", "Type", "Listing", "Price (PKR)", "City", "Area", "Address", "Bedrooms",
             "Bathrooms", "Covered Area", "Unit", "Owner", "Owner Contact", "Agent ID", "Agent", "Listing Date",
             "Status", "Image URL", "Description"]
CUST_COLS = ["Customer ID", "Name", "Phone", "Email", "City", "Address", "Type", "Registered", "Notes"]
AGENT_COLS = ["Agent ID", "Name", "Phone", "Email", "Office", "Joining Date", "Commission %", "Assigned Properties",
              "Completed Transactions", "Total Commission Earned (PKR)", "Status"]
INQ_COLS = ["Inquiry ID", "Customer ID", "Customer", "Property ID", "Property", "Property Type", "City", "Agent ID",
            "Agent", "Date", "Contact Method", "Status", "Viewing Date", "Viewing Time", "Viewing Outcome", "Notes"]
TXN_COLS = ["Transaction ID", "Property ID", "Property", "Property Type", "City", "Buyer ID", "Buyer", "Seller ID",
            "Seller", "Agent ID", "Agent", "Sale Price (PKR)", "Commission %", "Commission (PKR)", "Date",
            "Payment Status", "Received (PKR)", "Status"]
RENT_COLS = ["Agreement ID", "Property ID", "Property", "Property Type", "City", "Tenant ID", "Tenant", "Landlord ID",
             "Landlord", "Agent ID", "Agent", "Monthly Rent (PKR)", "Security Deposit (PKR)", "Start Date",
             "End Date", "Duration (months)", "Due Day", "Status", "Days Left", "Notes"]
PAY_COLS = ["Payment ID", "Related ID", "Related To", "Customer ID", "Customer", "Type", "Amount (PKR)", "Paid (PKR)",
            "Balance (PKR)", "Payment Date", "Due Date", "Report Date", "Method", "Status", "Reference", "Notes",
            "Property Type", "City", "Agent ID"]


def df_properties():
    rows = []
    for p in db()["properties"]:
        rows.append([p["id"], txt(p.get("title")), txt(p.get("property_type")), txt(p.get("listing_type")),
                     num(p.get("price")), txt(p.get("city")), txt(p.get("area")), txt(p.get("address")),
                     int(num(p.get("bedrooms"))), int(num(p.get("bathrooms"))), num(p.get("covered_area")),
                     txt(p.get("area_unit")), txt(p.get("owner_name")), txt(p.get("owner_contact")),
                     txt(p.get("agent_id")), agent_name(p.get("agent_id")), txt(p.get("listing_date")),
                     txt(p.get("status") or "Available"), txt(p.get("image_url")), txt(p.get("description"))])
    return pd.DataFrame(rows, columns=PROP_COLS)


def df_customers():
    rows = [[c["id"], txt(c.get("name")), txt(c.get("phone")), txt(c.get("email")), txt(c.get("city")),
             txt(c.get("address")), txt(c.get("customer_type")), txt(c.get("registration_date")),
             txt(c.get("notes"))] for c in db()["customers"]]
    return pd.DataFrame(rows, columns=CUST_COLS)


def df_agents():
    rows = []
    for a in db()["agents"]:
        s = agent_stats(a["id"])
        rows.append([a["id"], txt(a.get("name")), txt(a.get("phone")), txt(a.get("email")), txt(a.get("office")),
                     txt(a.get("joining_date")), num(a.get("commission_pct")), s["assigned"], s["completed"],
                     s["commission"], txt(a.get("status"))])
    return pd.DataFrame(rows, columns=AGENT_COLS)


def df_inquiries():
    rows = []
    for i in db()["inquiries"]:
        p = get_rec("properties", i.get("property_id")) or {}
        rows.append([i["id"], txt(i.get("customer_id")), cust_name(i.get("customer_id")), txt(i.get("property_id")),
                     txt(p.get("title")), txt(p.get("property_type")), txt(p.get("city")), txt(i.get("agent_id")),
                     agent_name(i.get("agent_id")), txt(i.get("date")), txt(i.get("contact_method")),
                     txt(i.get("status")), txt(i.get("viewing_date")), txt(i.get("viewing_time")),
                     txt(i.get("viewing_outcome")), txt(i.get("notes"))])
    return pd.DataFrame(rows, columns=INQ_COLS)


def df_transactions():
    rows = []
    for t in db()["transactions"]:
        p = get_rec("properties", t.get("property_id")) or {}
        rows.append([t["id"], txt(t.get("property_id")), txt(p.get("title")), txt(p.get("property_type")),
                     txt(p.get("city")), txt(t.get("buyer_id")), cust_name(t.get("buyer_id")),
                     txt(t.get("seller_id")), cust_name(t.get("seller_id")), txt(t.get("agent_id")),
                     agent_name(t.get("agent_id")), num(t.get("sale_price")), num(t.get("commission_pct")),
                     num(t.get("commission_amount")), txt(t.get("date")), txn_payment_status(t),
                     txn_received(t["id"]), txt(t.get("status"))])
    return pd.DataFrame(rows, columns=TXN_COLS)


def df_rentals():
    rows, today = [], date.today()
    for r in db()["rentals"]:
        p = get_rec("properties", r.get("property_id")) or {}
        s, e = parse_date(r.get("start_date")), parse_date(r.get("end_date"))
        months = round(((e - s).days + 1) / 30.44, 1) if s and e else 0.0
        rows.append([r["id"], txt(r.get("property_id")), txt(p.get("title")), txt(p.get("property_type")),
                     txt(p.get("city")), txt(r.get("tenant_id")), cust_name(r.get("tenant_id")),
                     txt(r.get("landlord_id")), cust_name(r.get("landlord_id")), txt(p.get("agent_id")),
                     agent_name(p.get("agent_id")), num(r.get("monthly_rent")), num(r.get("security_deposit")),
                     txt(r.get("start_date")), txt(r.get("end_date")), months, int(num(r.get("due_day"), 1)),
                     txt(r.get("status")), (e - today).days if e else 0, txt(r.get("notes"))])
    return pd.DataFrame(rows, columns=RENT_COLS)


def df_payments(valid_only=False):
    rows = []
    pays = valid_payments() if valid_only else db()["payments"]
    for p in pays:
        pid = related_property_id(p.get("related_id"))
        prop = get_rec("properties", pid) or {}
        txn = get_rec("transactions", p.get("related_id"))
        agent_id = txn.get("agent_id", "") if txn else prop.get("agent_id", "")
        rel_label = label_of("transactions", p["related_id"]) if txn else (
            label_of("rentals", p["related_id"]) if get_rec("rentals", p.get("related_id")) else "General")
        pdate, ddate = txt(p.get("payment_date")), txt(p.get("due_date"))
        rows.append([p["id"], txt(p.get("related_id")), rel_label, txt(p.get("customer_id")),
                     cust_name(p.get("customer_id")), txt(p.get("payment_type")), num(p.get("amount")),
                     num(p.get("amount_paid")), balance_of(p), pdate, ddate, pdate or ddate,
                     txt(p.get("method")), txt(p.get("status")), txt(p.get("reference")), txt(p.get("notes")),
                     txt(prop.get("property_type")), txt(prop.get("city")), txt(agent_id)])
    return pd.DataFrame(rows, columns=PAY_COLS)


def monthly_sum(df, date_col, value_col):
    """Sum value_col by calendar month (YYYY-MM) using date_col."""
    if df.empty:
        return pd.Series(dtype=float)
    d = df.copy()
    d["Month"] = pd.to_datetime(d[date_col], errors="coerce").dt.strftime("%Y-%m")
    d = d.dropna(subset=["Month"])
    return d.groupby("Month")[value_col].sum()


# =============================================================================
# 6. PROPERTIES PAGE
# =============================================================================
def image_block(url, height=170):
    """Image area. Shows a house placeholder behind the image, so a missing/broken URL still looks neat."""
    img = ""
    if valid_url(url):
        img = (f'<img src="{html.escape(txt(url).strip(), quote=True)}" alt="" loading="lazy" '
               f'style="position:absolute;top:0;left:0;width:100%;height:100%;object-fit:cover;">')
    return f'<div class="img-box" style="height:{height}px"><span class="img-ph">🏠</span>{img}</div>'


def property_card_html(p):
    rent = p.get("listing_type") == "For Rent"
    price = money(p.get("price")) + (" / month" if rent else "")
    return (f'<div class="prop-card">{image_block(p.get("image_url"))}<div class="prop-body">'
            f'<div class="prop-title">{esc(p.get("title"))}</div><div class="prop-price">{esc(price)}</div>'
            f'<div class="prop-meta">📍 {esc(p.get("area"))}, {esc(p.get("city"))}</div>'
            f'<div class="prop-meta">🛏 {int(num(p.get("bedrooms")))} &nbsp; 🛁 {int(num(p.get("bathrooms")))} '
            f'&nbsp; 📐 {num(p.get("covered_area")):g} {esc(p.get("area_unit"))}</div>'
            f'<div>{badge(p.get("status", "Available"))}{badge(p.get("listing_type"))}{badge(p.get("property_type"))}</div>'
            f'</div></div>')


def property_details(p):
    st.markdown(image_block(p.get("image_url"), 220), unsafe_allow_html=True)
    rent = p.get("listing_type") == "For Rent"
    c1, c2 = st.columns(2)
    c1.markdown(
        f"**Property ID:** {p['id']}  \n**Type:** {p.get('property_type')}  \n**Listing:** {p.get('listing_type')}  \n"
        f"**{'Monthly rent' if rent else 'Price'}:** {money(p.get('price'))}  \n"
        f"**Status:** {STATUS_ICONS.get(p.get('status'), '⚪')} {p.get('status')}  \n"
        f"**Listing date:** {p.get('listing_date')}")
    c2.markdown(
        f"**Location:** {p.get('area')}, {p.get('city')}  \n**Address:** {p.get('address')}  \n"
        f"**Bedrooms / Bathrooms:** {int(num(p.get('bedrooms')))} / {int(num(p.get('bathrooms')))}  \n"
        f"**Covered area:** {num(p.get('covered_area')):g} {p.get('area_unit')}  \n"
        f"**Owner:** {p.get('owner_name')} ({p.get('owner_contact')})  \n"
        f"**Agent:** {agent_name(p.get('agent_id')) or 'Not assigned'}")
    if txt(p.get("description")).strip():
        st.markdown("**Description:** " + txt(p.get("description")))


def property_fields(d, prefix):
    """Draw the property input widgets (used by Add and Edit forms) and return the entered values."""
    k = lambda n: K(f"{prefix}_{n}")
    c1, c2 = st.columns(2)
    title = c1.text_input("Property title *", d.get("title", ""), key=k("title"))
    ptype = c2.selectbox("Property type *", PROPERTY_TYPES, index=safe_index(PROPERTY_TYPES, d.get("property_type")), key=k("type"))
    c1, c2, c3 = st.columns(3)
    listing = c1.selectbox("Listing type *", LISTING_TYPES, index=safe_index(LISTING_TYPES, d.get("listing_type")), key=k("listing"))
    price = c2.number_input("Price / monthly rent (PKR) *", min_value=0.0, value=num(d.get("price")), step=10000.0, format="%.0f", key=k("price"))
    listing_date = c3.date_input("Listing date *", value=parse_date(d.get("listing_date")) or date.today(), key=k("ldate"))
    c1, c2 = st.columns(2)
    city = c1.text_input("City *", d.get("city", ""), key=k("city"))
    area = c2.text_input("Area / locality *", d.get("area", ""), key=k("area"))
    address = st.text_input("Property address *", d.get("address", ""), key=k("address"))
    c1, c2, c3, c4 = st.columns(4)
    beds = c1.number_input("Bedrooms", min_value=0, max_value=50, value=int(num(d.get("bedrooms"))), step=1, key=k("beds"))
    baths = c2.number_input("Bathrooms", min_value=0, max_value=50, value=int(num(d.get("bathrooms"))), step=1, key=k("baths"))
    covered = c3.number_input("Covered area *", min_value=0.0, value=num(d.get("covered_area")), step=1.0, key=k("covered"))
    unit = c4.selectbox("Area unit", AREA_UNITS, index=safe_index(AREA_UNITS, d.get("area_unit")), key=k("unit"))
    c1, c2, c3 = st.columns(3)
    owner = c1.text_input("Owner name *", d.get("owner_name", ""), key=k("owner"))
    contact = c2.text_input("Owner contact number *", d.get("owner_contact", ""), key=k("contact"))
    agent_ids = [""] + [a["id"] for a in db()["agents"]]
    agent = c3.selectbox("Assigned agent", agent_ids, index=safe_index(agent_ids, d.get("agent_id", "")),
                         format_func=lambda x: label_of("agents", x), key=k("agent"))
    image = st.text_input("Image URL (optional)", d.get("image_url", ""), key=k("image"))
    desc = st.text_area("Description", d.get("description", ""), key=k("desc"))
    return {"title": title.strip(), "property_type": ptype, "listing_type": listing, "price": float(price),
            "city": city.strip(), "area": area.strip(), "address": address.strip(), "bedrooms": int(beds),
            "bathrooms": int(baths), "covered_area": float(covered), "area_unit": unit,
            "owner_name": owner.strip(), "owner_contact": contact.strip(), "agent_id": agent,
            "listing_date": listing_date.isoformat(), "image_url": image.strip(), "description": desc.strip()}


def validate_property(v):
    errs = []
    if not v["title"]:
        errs.append("Property title is required.")
    if v["price"] <= 0:
        errs.append("Price / rent must be greater than zero.")
    for key, name in (("city", "City"), ("area", "Area"), ("address", "Address"), ("owner_name", "Owner name")):
        if not v[key]:
            errs.append(f"{name} is required.")
    if not PHONE_RE.match(v["owner_contact"]):
        errs.append("Enter a valid owner contact number (7 to 20 digits, e.g. 0300-1234567).")
    if v["covered_area"] <= 0:
        errs.append("Covered area must be greater than zero.")
    if v["image_url"] and not valid_url(v["image_url"]):
        errs.append("Image URL must start with http:// or https:// (or leave it empty).")
    return errs


SORT_OPTIONS = ["Newest first", "Oldest first", "Price: low to high", "Price: high to low", "Location (A-Z)"]


def property_browse_tab():
    df = df_properties()
    if df.empty:
        st.info("No properties yet. Open the 'Add Property' tab to create your first listing.")
        return
    c1, c2, c3, c4 = st.columns(4)
    search = c1.text_input("Search (title, city, area or ID)", key="pf_search")
    ptypes = c2.multiselect("Property type", PROPERTY_TYPES, key="pf_type")
    listing = c3.selectbox("Listing type", ["All"] + LISTING_TYPES, key="pf_listing")
    status = c4.selectbox("Status", ["All"] + PROPERTY_STATUSES, key="pf_status")
    c5, c6, c7, c8 = st.columns(4)
    pmin = c5.number_input("Min price (PKR)", min_value=0.0, value=0.0, step=100000.0, format="%.0f", key="pf_min")
    pmax = c6.number_input("Max price (PKR, 0 = no limit)", min_value=0.0, value=0.0, step=100000.0, format="%.0f", key="pf_max")
    sort = c7.selectbox("Sort by", SORT_OPTIONS, key="pf_sort")
    view = c8.radio("View as", ["Cards", "Table"], horizontal=True, key="pf_view")

    f = df
    if search.strip():
        s = search.strip().lower()
        f = f[f["Title"].str.lower().str.contains(s, regex=False) | f["City"].str.lower().str.contains(s, regex=False)
              | f["Area"].str.lower().str.contains(s, regex=False) | f["Property ID"].str.lower().str.contains(s, regex=False)]
    if ptypes:
        f = f[f["Type"].isin(ptypes)]
    if listing != "All":
        f = f[f["Listing"] == listing]
    if status != "All":
        f = f[f["Status"] == status]
    f = f[f["Price (PKR)"] >= pmin]
    if pmax > 0:
        f = f[f["Price (PKR)"] <= pmax]
    if sort == "Newest first":
        f = f.sort_values("Listing Date", ascending=False)
    elif sort == "Oldest first":
        f = f.sort_values("Listing Date")
    elif sort == "Price: low to high":
        f = f.sort_values("Price (PKR)")
    elif sort == "Price: high to low":
        f = f.sort_values("Price (PKR)", ascending=False)
    else:
        f = f.sort_values(["City", "Area"], key=lambda col: col.str.lower())

    st.caption(f"Showing {len(f)} of {len(df)} properties")
    if f.empty:
        st.info("No properties match your filters. Try clearing some filters.")
        return
    if view == "Table":
        show_table(f, money_cols=["Price (PKR)"], status_cols=["Status"], hide=["Image URL", "Description", "Agent ID"])
        return
    page_size = 9
    pages = max(1, math.ceil(len(f) / page_size))
    page = st.selectbox("Page", list(range(1, pages + 1))) if pages > 1 else 1
    ids = f["Property ID"].tolist()[(page - 1) * page_size: page * page_size]
    for i in range(0, len(ids), 3):
        cols = st.columns(3)
        for col, pid in zip(cols, ids[i:i + 3]):
            p = get_rec("properties", pid)
            with col:
                st.markdown(property_card_html(p), unsafe_allow_html=True)
                with st.expander("View details"):
                    property_details(p)


def property_add_tab():
    st.subheader("Add a new property")
    with st.form(K("add_property")):
        custom_id = st.text_input("Property ID (optional - leave empty to auto-generate)", key=K("padd_id"))
        v = property_fields({}, "padd")
        submitted = st.form_submit_button("Save property", type="primary")
    if submitted:
        errs = validate_property(v)
        pid, err = resolve_id("properties", custom_id)
        if err:
            errs.append(err)
        if errs:
            for e in errs:
                st.error(e)
            return
        add_record("properties", {"id": pid, **v, "status": "Available"})
        finish(f"Property {pid} added successfully.")


def property_edit_tab():
    st.subheader("Edit a property")
    if not db()["properties"]:
        st.info("There are no properties to edit yet.")
        return
    pid = select_id("Select property", "properties", K("pedit_sel"))
    p = get_rec("properties", pid)
    st.caption(f"Status: {p.get('status')} (status updates automatically from sales, rentals and negotiations).")
    with st.form(K(f"edit_property_{pid}")):
        v = property_fields(p, f"pedit_{pid}")
        submitted = st.form_submit_button("Update property", type="primary")
    if submitted:
        errs = validate_property(v)
        if errs:
            for e in errs:
                st.error(e)
            return
        update_record("properties", pid, v)
        finish(f"Property {pid} updated.")


def page_properties():
    page_header("Property Management", "Browse, add, edit and remove property listings")
    tabs = st.tabs(["🏘️ Browse", "➕ Add Property", "✏️ Edit Property", "🗑️ Delete Property"])
    with tabs[0]:
        property_browse_tab()
    with tabs[1]:
        property_add_tab()
    with tabs[2]:
        property_edit_tab()
    with tabs[3]:
        delete_panel("properties", "property")


# =============================================================================
# 7. CUSTOMERS PAGE
# =============================================================================
def customer_fields(d, prefix):
    k = lambda n: K(f"{prefix}_{n}")
    c1, c2, c3 = st.columns(3)
    name = c1.text_input("Full name *", d.get("name", ""), key=k("name"))
    phone = c2.text_input("Phone number *", d.get("phone", ""), key=k("phone"))
    email = c3.text_input("Email address", d.get("email", ""), key=k("email"))
    c1, c2, c3 = st.columns(3)
    city = c1.text_input("City *", d.get("city", ""), key=k("city"))
    ctype = c2.selectbox("Customer type *", CUSTOMER_TYPES, index=safe_index(CUSTOMER_TYPES, d.get("customer_type")), key=k("type"))
    reg = c3.date_input("Registration date", value=parse_date(d.get("registration_date")) or date.today(), key=k("reg"))
    address = st.text_input("Address", d.get("address", ""), key=k("addr"))
    notes = st.text_area("Notes / preferences", d.get("notes", ""), key=k("notes"))
    return {"name": name.strip(), "phone": phone.strip(), "email": email.strip(), "city": city.strip(),
            "customer_type": ctype, "registration_date": reg.isoformat(), "address": address.strip(),
            "notes": notes.strip()}


def validate_customer(v):
    errs = []
    if not v["name"]:
        errs.append("Full name is required.")
    if not PHONE_RE.match(v["phone"]):
        errs.append("Enter a valid phone number (7 to 20 digits).")
    if v["email"] and not EMAIL_RE.match(v["email"]):
        errs.append("Email address looks invalid (example: name@example.com).")
    if not v["city"]:
        errs.append("City is required.")
    return errs


def customer_profile(cid):
    """Show all records connected to one customer."""
    c = get_rec("customers", cid)
    st.markdown(f"**{c.get('name')}** · {c.get('customer_type')} · {c.get('phone')} · {c.get('email') or 'no email'}")
    if txt(c.get("notes")):
        st.caption("Notes: " + txt(c.get("notes")))
    t1, t2, t3, t4 = st.tabs(["Inquiries", "Transactions", "Rental agreements", "Payment history"])
    with t1:
        d = df_inquiries()
        show_table(d[d["Customer ID"] == cid], status_cols=["Status"], hide=["Customer ID", "Customer", "Agent ID"],
                   empty_msg="No inquiries recorded for this customer.")
    with t2:
        d = df_transactions()
        show_table(d[(d["Buyer ID"] == cid) | (d["Seller ID"] == cid)], money_cols=["Sale Price (PKR)", "Commission (PKR)", "Received (PKR)"],
                   status_cols=["Status", "Payment Status"], hide=["Buyer ID", "Seller ID", "Agent ID"],
                   empty_msg="No transactions for this customer.")
    with t3:
        d = df_rentals()
        show_table(d[(d["Tenant ID"] == cid) | (d["Landlord ID"] == cid)], money_cols=["Monthly Rent (PKR)", "Security Deposit (PKR)"],
                   status_cols=["Status"], hide=["Tenant ID", "Landlord ID", "Agent ID"], empty_msg="No rental agreements for this customer.")
    with t4:
        d = df_payments()
        show_table(d[d["Customer ID"] == cid], money_cols=["Amount (PKR)", "Paid (PKR)", "Balance (PKR)"], status_cols=["Status"],
                   hide=["Customer ID", "Customer", "Report Date", "Property Type", "City", "Agent ID", "Related ID"],
                   empty_msg="No payments for this customer.")


def customer_browse_tab():
    df = df_customers()
    if df.empty:
        st.info("No customers yet. Open the 'Register Customer' tab to add one.")
        return
    c1, c2, c3 = st.columns(3)
    search = c1.text_input("Search (name, phone, email or ID)", key="cf_search")
    ctype = c2.selectbox("Customer type", ["All"] + CUSTOMER_TYPES, key="cf_type")
    cities = sorted({c for c in df["City"] if c})
    city = c3.selectbox("City", ["All"] + cities, key="cf_city")
    f = df
    if search.strip():
        s = search.strip().lower()
        f = f[f["Name"].str.lower().str.contains(s, regex=False) | f["Phone"].str.contains(s, regex=False)
              | f["Email"].str.lower().str.contains(s, regex=False) | f["Customer ID"].str.lower().str.contains(s, regex=False)]
    if ctype != "All":
        f = f[f["Type"] == ctype]
    if city != "All":
        f = f[f["City"] == city]
    st.caption(f"Showing {len(f)} of {len(df)} customers")
    show_table(f, empty_msg="No customers match your filters.")
    st.markdown("##### Customer profile")
    cid = select_id("Select a customer to view inquiries, transactions, rentals and payments", "customers", K("cprofile_sel"))
    if cid:
        customer_profile(cid)


def customer_add_tab():
    st.subheader("Register a new customer")
    with st.form(K("add_customer")):
        custom_id = st.text_input("Customer ID (optional - leave empty to auto-generate)", key=K("cadd_id"))
        v = customer_fields({}, "cadd")
        submitted = st.form_submit_button("Save customer", type="primary")
    if submitted:
        errs = validate_customer(v)
        cid, err = resolve_id("customers", custom_id)
        if err:
            errs.append(err)
        if errs:
            for e in errs:
                st.error(e)
            return
        add_record("customers", {"id": cid, **v})
        finish(f"Customer {cid} registered successfully.")


def customer_edit_tab():
    st.subheader("Edit a customer")
    if not db()["customers"]:
        st.info("There are no customers to edit yet.")
        return
    cid = select_id("Select customer", "customers", K("cedit_sel"))
    with st.form(K(f"edit_customer_{cid}")):
        v = customer_fields(get_rec("customers", cid), f"cedit_{cid}")
        submitted = st.form_submit_button("Update customer", type="primary")
    if submitted:
        errs = validate_customer(v)
        if errs:
            for e in errs:
                st.error(e)
            return
        update_record("customers", cid, v)
        finish(f"Customer {cid} updated.")


def page_customers():
    page_header("Customer Management", "Buyers, sellers, tenants and landlords")
    tabs = st.tabs(["👥 Browse", "➕ Register Customer", "✏️ Edit Customer", "🗑️ Delete Customer"])
    with tabs[0]:
        customer_browse_tab()
    with tabs[1]:
        customer_add_tab()
    with tabs[2]:
        customer_edit_tab()
    with tabs[3]:
        delete_panel("customers", "customer")


# =============================================================================
# 8. AGENTS PAGE
# =============================================================================
def agent_fields(d, prefix):
    k = lambda n: K(f"{prefix}_{n}")
    c1, c2, c3 = st.columns(3)
    name = c1.text_input("Full name *", d.get("name", ""), key=k("name"))
    phone = c2.text_input("Phone number *", d.get("phone", ""), key=k("phone"))
    email = c3.text_input("Email address *", d.get("email", ""), key=k("email"))
    c1, c2, c3, c4 = st.columns(4)
    office = c1.text_input("Office location *", d.get("office", ""), key=k("office"))
    joined = c2.date_input("Joining date", value=parse_date(d.get("joining_date")) or date.today(), key=k("join"))
    pct = c3.number_input("Commission % *", min_value=0.0, max_value=100.0, value=num(d.get("commission_pct"), 2.0), step=0.25, key=k("pct"))
    status = c4.selectbox("Employment status", EMPLOYMENT_STATUSES, index=safe_index(EMPLOYMENT_STATUSES, d.get("status")), key=k("status"))
    return {"name": name.strip(), "phone": phone.strip(), "email": email.strip(), "office": office.strip(),
            "joining_date": joined.isoformat(), "commission_pct": float(pct), "status": status}


def validate_agent(v):
    errs = []
    if not v["name"]:
        errs.append("Full name is required.")
    if not PHONE_RE.match(v["phone"]):
        errs.append("Enter a valid phone number (7 to 20 digits).")
    if not EMAIL_RE.match(v["email"]):
        errs.append("Enter a valid email address.")
    if not v["office"]:
        errs.append("Office location is required.")
    if not 0 <= v["commission_pct"] <= 100:
        errs.append("Commission % must be between 0 and 100.")
    return errs


def agent_browse_tab():
    df = df_agents()
    if df.empty:
        st.info("No agents yet. Open the 'Add Agent' tab to create one.")
        return
    c1, c2, c3 = st.columns(3)
    search = c1.text_input("Search (name, email, phone or ID)", key="af_search")
    status = c2.selectbox("Employment status", ["All"] + EMPLOYMENT_STATUSES, key="af_status")
    offices = sorted({o for o in df["Office"] if o})
    office = c3.selectbox("Office", ["All"] + offices, key="af_office")
    f = df
    if search.strip():
        s = search.strip().lower()
        f = f[f["Name"].str.lower().str.contains(s, regex=False) | f["Email"].str.lower().str.contains(s, regex=False)
              | f["Phone"].str.contains(s, regex=False) | f["Agent ID"].str.lower().str.contains(s, regex=False)]
    if status != "All":
        f = f[f["Status"] == status]
    if office != "All":
        f = f[f["Office"] == office]
    st.caption("Commission is calculated only on Completed sales (never on cancelled or pending transactions), once per transaction.")
    show_table(f, money_cols=["Total Commission Earned (PKR)"], status_cols=["Status"], empty_msg="No agents match your filters.")
    if not f.empty:
        st.markdown("##### Agent performance")
        c1, c2 = st.columns(2)
        chart = f.set_index("Name")
        c1.caption("Completed transactions (sales + rentals)")
        c1.bar_chart(chart[["Completed Transactions"]])
        c2.caption("Commission earned (PKR)")
        c2.bar_chart(chart[["Total Commission Earned (PKR)"]])


def agent_add_tab():
    st.subheader("Add a new agent")
    with st.form(K("add_agent")):
        custom_id = st.text_input("Agent ID (optional - leave empty to auto-generate)", key=K("aadd_id"))
        v = agent_fields({}, "aadd")
        submitted = st.form_submit_button("Save agent", type="primary")
    if submitted:
        errs = validate_agent(v)
        aid, err = resolve_id("agents", custom_id)
        if err:
            errs.append(err)
        if errs:
            for e in errs:
                st.error(e)
            return
        add_record("agents", {"id": aid, **v})
        finish(f"Agent {aid} added successfully.")


def agent_edit_tab():
    st.subheader("Edit an agent")
    if not db()["agents"]:
        st.info("There are no agents to edit yet.")
        return
    aid = select_id("Select agent", "agents", K("aedit_sel"))
    with st.form(K(f"edit_agent_{aid}")):
        v = agent_fields(get_rec("agents", aid), f"aedit_{aid}")
        submitted = st.form_submit_button("Update agent", type="primary")
    if submitted:
        errs = validate_agent(v)
        if errs:
            for e in errs:
                st.error(e)
            return
        update_record("agents", aid, v)
        finish(f"Agent {aid} updated. (Existing transactions keep their original commission.)")


def agent_assign_tab():
    st.subheader("Assign properties to an agent")
    if not db()["agents"] or not db()["properties"]:
        st.info("You need at least one agent and one property to assign properties.")
        return
    aid = select_id("Select agent", "agents", K("assign_agent"))
    all_ids = [p["id"] for p in db()["properties"]]
    current = [p["id"] for p in db()["properties"] if p.get("agent_id") == aid]
    fmt = lambda pid: f"{label_of('properties', pid)}  (agent: {agent_name(field_of('properties', pid, 'agent_id')) or 'none'})"
    chosen = st.multiselect("Properties handled by this agent", all_ids, default=current, format_func=fmt,
                            key=K(f"assign_props_{aid}"))
    st.caption("Properties you remove from this list become unassigned. Properties you add are moved from their previous agent.")
    if st.button("Save assignments", type="primary", key=K("assign_btn")):
        for p in db()["properties"]:
            if p["id"] in chosen:
                p["agent_id"] = aid
            elif p.get("agent_id") == aid:
                p["agent_id"] = ""
        save_data()
        finish(f"Assignments saved for {agent_name(aid)}: {len(chosen)} propert{'y' if len(chosen) == 1 else 'ies'}.")


def page_agents():
    page_header("Agent Management", "Agents, assignments, commissions and performance")
    tabs = st.tabs(["🧑‍💼 Browse & Performance", "➕ Add Agent", "✏️ Edit Agent", "🔗 Assign Properties", "🗑️ Delete Agent"])
    with tabs[0]:
        agent_browse_tab()
    with tabs[1]:
        agent_add_tab()
    with tabs[2]:
        agent_edit_tab()
    with tabs[3]:
        agent_assign_tab()
    with tabs[4]:
        delete_panel("agents", "agent")


# =============================================================================
# 9. INQUIRIES & VIEWINGS PAGE
# =============================================================================
def inquiry_browse_tab():
    df = df_inquiries()
    total = len(df)
    converted = int((df["Status"] == "Converted").sum()) if total else 0
    rate = (converted / total * 100) if total else 0.0
    upcoming = df[(df["Status"] == "Viewing Scheduled") & (df["Viewing Date"] >= date.today().isoformat())] if total else df
    kpi_row([("Total inquiries", total), ("Converted", converted, "#2b6cb0"), ("Conversion rate", f"{rate:.1f}%", "#0b2545"),
             ("Upcoming viewings", len(upcoming), "#b7791f")])
    if df.empty:
        st.info("No inquiries yet. Use the 'Register Inquiry' tab to record the first one.")
        return
    c1, c2, c3 = st.columns(3)
    search = c1.text_input("Search (customer, property or ID)", key="if_search")
    status = c2.selectbox("Status", ["All"] + INQUIRY_STATUSES, key="if_status")
    agents = c3.selectbox("Agent", ["All"] + [a["id"] for a in db()["agents"]], format_func=lambda x: "All" if x == "All" else label_of("agents", x), key="if_agent")
    f = df
    if search.strip():
        s = search.strip().lower()
        f = f[f["Customer"].str.lower().str.contains(s, regex=False) | f["Property"].str.lower().str.contains(s, regex=False)
              | f["Inquiry ID"].str.lower().str.contains(s, regex=False) | f["Property ID"].str.lower().str.contains(s, regex=False)]
    if status != "All":
        f = f[f["Status"] == status]
    if agents != "All":
        f = f[f["Agent ID"] == agents]
    st.caption(f"Showing {len(f)} of {total} inquiries")
    show_table(f.sort_values("Date", ascending=False), status_cols=["Status"], hide=["Customer ID", "Agent ID", "Property Type", "City"],
               empty_msg="No inquiries match your filters.")
    st.markdown("##### Upcoming viewings")
    show_table(upcoming.sort_values(["Viewing Date", "Viewing Time"]), status_cols=["Status"],
               hide=["Customer ID", "Agent ID", "Property Type", "City", "Notes", "Viewing Outcome"],
               empty_msg="No viewings are scheduled.")


def inquiry_register_tab():
    st.subheader("Register a new inquiry")
    if not db()["customers"] or not db()["properties"]:
        st.info("Register at least one customer and one property before recording inquiries.")
        return
    pid = select_id("Property *", "properties", K("iadd_prop"))
    prop = get_rec("properties", pid)
    with st.form(K(f"add_inquiry_{pid}")):
        c1, c2 = st.columns(2)
        with c1:
            cid = select_id("Customer *", "customers", K(f"iadd_cust_{pid}"))
        with c2:
            aid = select_id("Assigned agent (defaults to the property's agent)", "agents", K(f"iadd_agent_{pid}"),
                            allow_none=True, default=prop.get("agent_id", ""))
        c1, c2, c3 = st.columns(3)
        idate = c1.date_input("Inquiry date", value=date.today(), key=K(f"iadd_date_{pid}"))
        method = c2.selectbox("Preferred contact method", CONTACT_METHODS, key=K(f"iadd_method_{pid}"))
        status = c3.selectbox("Status", INQUIRY_STATUSES, key=K(f"iadd_status_{pid}"))
        notes = st.text_area("Notes", key=K(f"iadd_notes_{pid}"))
        submitted = st.form_submit_button("Save inquiry", type="primary")
    if submitted:
        errs = []
        if not get_rec("customers", cid):
            errs.append("Please select a valid customer.")
        if not get_rec("properties", pid):
            errs.append("Please select a valid property.")
        if aid and not get_rec("agents", aid):
            errs.append("The selected agent does not exist.")
        if errs:
            for e in errs:
                st.error(e)
            return
        iid = next_id("inquiries")
        add_record("inquiries", {"id": iid, "customer_id": cid, "property_id": pid, "agent_id": aid or "",
                                 "date": idate.isoformat(), "contact_method": method, "status": status,
                                 "notes": notes.strip(), "viewing_date": "", "viewing_time": "", "viewing_outcome": ""})
        finish(f"Inquiry {iid} registered.")


def inquiry_update_tab():
    st.subheader("Update status and schedule viewings")
    if not db()["inquiries"]:
        st.info("There are no inquiries to update yet.")
        return
    iid = select_id("Select inquiry", "inquiries", K("iupd_sel"))
    q = get_rec("inquiries", iid)
    st.caption(f"Customer: {cust_name(q.get('customer_id'))} · Property: {prop_title(q.get('property_id'))} · "
               f"Current status: {q.get('status')}")
    vd = parse_date(q.get("viewing_date")) or date.today()
    try:
        vt = dtime.fromisoformat(q.get("viewing_time") or "10:00")
    except ValueError:
        vt = dtime(10, 0)
    with st.form(K(f"upd_inquiry_{iid}")):
        c1, c2 = st.columns(2)
        status = c1.selectbox("New status", INQUIRY_STATUSES, index=safe_index(INQUIRY_STATUSES, q.get("status")), key=K(f"iu_status_{iid}"))
        schedule = c2.checkbox("Schedule / reschedule a viewing", key=K(f"iu_sched_{iid}"))
        c1, c2 = st.columns(2)
        vdate = c1.date_input("Viewing date", value=vd, key=K(f"iu_vd_{iid}"))
        vtime = c2.time_input("Viewing time", value=vt, key=K(f"iu_vt_{iid}"))
        outcome = st.text_area("Viewing outcome", q.get("viewing_outcome", ""), key=K(f"iu_out_{iid}"))
        notes = st.text_area("Notes", q.get("notes", ""), key=K(f"iu_notes_{iid}"))
        submitted = st.form_submit_button("Save changes", type="primary")
    if submitted:
        changes = {"status": status, "viewing_outcome": outcome.strip(), "notes": notes.strip()}
        if schedule or status == "Viewing Scheduled":
            changes.update({"viewing_date": vdate.isoformat(), "viewing_time": vtime.strftime("%H:%M")})
            if schedule and status in ("New", "Contacted"):
                changes["status"] = "Viewing Scheduled"
        update_record("inquiries", iid, changes)
        finish(f"Inquiry {iid} updated (status: {changes['status']}).")


def page_inquiries():
    page_header("Inquiries & Viewings", "Track leads, schedule viewings and measure conversion")
    tabs = st.tabs(["📋 Browse", "➕ Register Inquiry", "📅 Update / Schedule Viewing", "🗑️ Delete Inquiry"])
    with tabs[0]:
        inquiry_browse_tab()
    with tabs[1]:
        inquiry_register_tab()
    with tabs[2]:
        inquiry_update_tab()
    with tabs[3]:
        delete_panel("inquiries", "inquiry")


# =============================================================================
# 10. SALES & TRANSACTIONS PAGE
# =============================================================================
def txn_summary_text(tid):
    t = get_rec("transactions", tid)
    received = txn_received(tid)
    lines = [f"TRANSACTION SUMMARY - {tid}", "=" * 44,
             f"Property      : {label_of('properties', t.get('property_id'))}",
             f"Buyer         : {label_of('customers', t.get('buyer_id'))}",
             f"Seller        : {label_of('customers', t.get('seller_id'))}",
             f"Agent         : {label_of('agents', t.get('agent_id'))}",
             f"Date          : {t.get('date')}", f"Status        : {t.get('status')}",
             f"Sale price    : {money(t.get('sale_price'))}",
             f"Commission    : {num(t.get('commission_pct')):g}% = {money(t.get('commission_amount'))}",
             f"Payment status: {txn_payment_status(t)}",
             f"Received      : {money(received)}", f"Balance       : {money(max(num(t.get('sale_price')) - received, 0))}"]
    pays = [p for p in db()["payments"] if p.get("related_id") == tid]
    if pays:
        lines += ["", "Related payments:"]
        lines += [f" - {p['id']} | {p.get('payment_type')} | {money(p.get('amount'))} | paid {money(p.get('amount_paid'))} | {p.get('status')}" for p in pays]
    if t.get("status") == "Cancelled":
        lines += ["", "NOTE: Cancelled - excluded from revenue and commission."]
    return "\n".join(lines)


def txn_overview_tab():
    df = df_transactions()
    completed = df[df["Status"] == "Completed"] if not df.empty else df
    pending = df[df["Status"] == "Pending"] if not df.empty else df
    kpi_row([("Completed sales", len(completed)), ("Sales revenue", money(completed["Sale Price (PKR)"].sum()), "#0b2545"),
             ("Pending transactions", f"{len(pending)} ({short_money(pending['Sale Price (PKR)'].sum())})", "#b7791f"),
             ("Commission earned", money(completed["Commission (PKR)"].sum()), "#2b6cb0")])
    if df.empty:
        st.info("No transactions yet. Open 'New Transaction' to record a sale.")
        return
    c1, c2, c3, c4 = st.columns(4)
    search = c1.text_input("Search (ID, property, buyer, seller)", key="tf_search")
    status = c2.selectbox("Transaction status", ["All"] + TXN_STATUSES, key="tf_status")
    pstat = c3.selectbox("Payment status", ["All", "Unpaid", "Partially Paid", "Paid"], key="tf_pay")
    agent = c4.selectbox("Agent", ["All"] + [a["id"] for a in db()["agents"]], format_func=lambda x: "All" if x == "All" else label_of("agents", x), key="tf_agent")
    f = df
    if search.strip():
        s = search.strip().lower()
        f = f[f["Transaction ID"].str.lower().str.contains(s, regex=False) | f["Property"].str.lower().str.contains(s, regex=False)
              | f["Buyer"].str.lower().str.contains(s, regex=False) | f["Seller"].str.lower().str.contains(s, regex=False)]
    if status != "All":
        f = f[f["Status"] == status]
    if pstat != "All":
        f = f[f["Payment Status"] == pstat]
    if agent != "All":
        f = f[f["Agent ID"] == agent]
    st.caption("Cancelled transactions are shown for history but never counted in revenue or commission.")
    show_table(f.sort_values("Date", ascending=False), money_cols=["Sale Price (PKR)", "Commission (PKR)", "Received (PKR)"],
               status_cols=["Status", "Payment Status"], hide=["Property ID", "Property Type", "City", "Buyer ID", "Seller ID", "Agent ID"],
               empty_msg="No transactions match your filters.")
    st.markdown("##### Transaction summary")
    tid = select_id("Select a transaction", "transactions", K("tsum_sel"))
    if tid:
        text = txn_summary_text(tid)
        st.code(text, language=None)
        st.download_button("Download summary (.txt)", text, file_name=f"{tid}_summary.txt", mime="text/plain", key=K("tsum_dl"))


def txn_new_tab():
    st.subheader("Record a new sale")
    if not any(sale_eligible(p) for p in db()["properties"]):
        st.info("No properties are available for sale. A property must be 'For Sale', not sold or rented, and have no open transaction.")
        return
    if len(db()["customers"]) < 2:
        st.info("Register at least two customers (a buyer and a seller) first.")
        return
    if not db()["agents"]:
        st.info("Add at least one agent first.")
        return
    pid = select_id("Property *", "properties", K("tadd_prop"), filter_fn=sale_eligible)
    prop = get_rec("properties", pid)
    default_agent = prop.get("agent_id") or ""
    default_pct = num((get_rec("agents", default_agent) or {}).get("commission_pct"), 2.0)
    with st.form(K(f"add_txn_{pid}")):
        c1, c2, c3 = st.columns(3)
        with c1:
            buyer = select_id("Buyer *", "customers", K(f"tb_{pid}"))
        with c2:
            seller = select_id("Seller *", "customers", K(f"ts_{pid}"))
        with c3:
            agent = select_id("Agent *", "agents", K(f"ta_{pid}"), default=default_agent)
        c1, c2, c3, c4 = st.columns(4)
        price = c1.number_input("Sale price (PKR) *", min_value=0.0, value=num(prop.get("price")), step=10000.0, format="%.0f", key=K(f"tp_{pid}"))
        pct = c2.number_input("Commission % *", min_value=0.0, max_value=100.0, value=default_pct, step=0.25, key=K(f"tc_{pid}"))
        tdate = c3.date_input("Transaction date", value=date.today(), key=K(f"td_{pid}"))
        status = c4.selectbox("Transaction status", ["Pending", "Completed"], key=K(f"tst_{pid}"))
        st.caption("Commission = sale price x commission %. Choose 'Completed' only when the sale is confirmed - "
                   "the property then becomes Sold.")
        submitted = st.form_submit_button("Save transaction", type="primary")
    if submitted:
        errs = []
        if not sale_eligible(get_rec("properties", pid) or {"id": pid}):
            errs.append("This property is not available for sale (already sold, rented or has an open transaction).")
        if not get_rec("customers", buyer):
            errs.append("A valid buyer is required.")
        if not get_rec("customers", seller):
            errs.append("A valid seller is required.")
        if buyer == seller:
            errs.append("Buyer and seller must be different customers.")
        if not get_rec("agents", agent):
            errs.append("A valid agent is required.")
        if price <= 0:
            errs.append("Sale price must be greater than zero.")
        if errs:
            for e in errs:
                st.error(e)
            return
        tid = next_id("transactions")
        add_record("transactions", {"id": tid, "property_id": pid, "buyer_id": buyer, "seller_id": seller, "agent_id": agent,
                                    "sale_price": float(price), "commission_pct": float(pct),
                                    "commission_amount": round(price * pct / 100, 2), "date": tdate.isoformat(), "status": status})
        finish(f"Transaction {tid} saved ({status}). Commission: {money(price * pct / 100)}.")


def can_activate(t):
    """Can a Cancelled/Completed transaction be moved to Pending/Completed without creating a duplicate sale?"""
    for x in db()["transactions"]:
        if x["id"] != t["id"] and x.get("property_id") == t.get("property_id") and x.get("status") in ("Pending", "Completed"):
            return False, f"Property already has another {x.get('status').lower()} transaction ({x['id']})."
    if any(r.get("property_id") == t.get("property_id") and r.get("status") == "Active" for r in db()["rentals"]):
        return False, "The property currently has an active rental agreement."
    return True, ""


def txn_update_tab():
    st.subheader("Update a transaction")
    if not db()["transactions"]:
        st.info("There are no transactions to update yet.")
        return
    tid = select_id("Select transaction", "transactions", K("tupd_sel"))
    t = get_rec("transactions", tid)
    cur = t.get("status")
    st.caption(f"Property: {prop_title(t.get('property_id'))} · Current status: {cur}. "
               "Price and commission can only be edited while a transaction is Pending.")
    with st.form(K(f"upd_txn_{tid}")):
        c1, c2, c3, c4 = st.columns(4)
        new_status = c1.selectbox("Status", TXN_STATUSES, index=safe_index(TXN_STATUSES, cur), key=K(f"tu_st_{tid}"))
        price = c2.number_input("Sale price (PKR)", min_value=0.0, value=num(t.get("sale_price")), step=10000.0, format="%.0f",
                                disabled=cur != "Pending", key=K(f"tu_pr_{tid}"))
        pct = c3.number_input("Commission %", min_value=0.0, max_value=100.0, value=num(t.get("commission_pct")), step=0.25,
                              disabled=cur != "Pending", key=K(f"tu_pc_{tid}"))
        tdate = c4.date_input("Date", value=parse_date(t.get("date")) or date.today(), key=K(f"tu_dt_{tid}"))
        submitted = st.form_submit_button("Save changes", type="primary")
    if submitted:
        errs = []
        if cur != "Pending":
            price, pct = num(t.get("sale_price")), num(t.get("commission_pct"))
        if new_status in ("Pending", "Completed") and new_status != cur:
            ok, msg = can_activate(t)
            if not ok:
                errs.append(msg)
        if price <= 0:
            errs.append("Sale price must be greater than zero.")
        due_total = sum(num(p.get("amount")) for p in db()["payments"] if p.get("related_id") == tid and p.get("payment_type") == "Sale Payment")
        if price < due_total - 0.01:
            errs.append(f"Sale price cannot be lower than the sale payments already recorded ({money(due_total)}).")
        if errs:
            for e in errs:
                st.error(e)
            return
        update_record("transactions", tid, {"status": new_status, "sale_price": float(price), "commission_pct": float(pct),
                                            "commission_amount": round(price * pct / 100, 2), "date": tdate.isoformat()})
        finish(f"Transaction {tid} updated to {new_status}. Property status refreshed automatically.")


def page_sales():
    page_header("Sales & Transactions", "Record sales, track commissions and prevent duplicate sales")
    tabs = st.tabs(["💼 History & Summary", "➕ New Transaction", "🔄 Update / Cancel", "🗑️ Delete Transaction"])
    with tabs[0]:
        txn_overview_tab()
    with tabs[1]:
        txn_new_tab()
    with tabs[2]:
        txn_update_tab()
    with tabs[3]:
        delete_panel("transactions", "transaction")


# =============================================================================
# 11. RENTAL MANAGEMENT PAGE
# =============================================================================
def rental_overview_tab():
    df = df_rentals()
    active = df[df["Status"] == "Active"] if not df.empty else df
    pays = df_payments(valid_only=True)
    rent_pays = pays[(pays["Type"] == "Monthly Rent") & (pays["Status"].isin(["Pending", "Partially Paid", "Overdue"]))]
    kpi_row([("Active agreements", len(active)), ("Expired", int((df["Status"] == "Expired").sum()) if not df.empty else 0, "#718096"),
             ("Terminated", int((df["Status"] == "Terminated").sum()) if not df.empty else 0, "#c53030"),
             ("Monthly rent roll", money(active["Monthly Rent (PKR)"].sum()), "#0b2545"),
             ("Outstanding rent", money(rent_pays["Balance (PKR)"].sum()), "#b7791f")])
    if df.empty:
        st.info("No rental agreements yet. Open 'New Agreement' to create one.")
        return
    st.markdown("##### Upcoming expirations (next 60 days)")
    soon = active[(active["Days Left"] >= 0) & (active["Days Left"] <= 60)].sort_values("Days Left")
    show_table(soon, money_cols=["Monthly Rent (PKR)", "Security Deposit (PKR)"], status_cols=["Status"],
               hide=["Property ID", "Property Type", "City", "Tenant ID", "Landlord ID", "Agent ID", "Notes"],
               empty_msg="No active agreements expire in the next 60 days.")
    st.markdown("##### All agreements")
    c1, c2 = st.columns(2)
    search = c1.text_input("Search (ID, property, tenant, landlord)", key="rf_search")
    status = c2.selectbox("Agreement status", ["All"] + RENTAL_STATUSES, key="rf_status")
    f = df
    if search.strip():
        s = search.strip().lower()
        f = f[f["Agreement ID"].str.lower().str.contains(s, regex=False) | f["Property"].str.lower().str.contains(s, regex=False)
              | f["Tenant"].str.lower().str.contains(s, regex=False) | f["Landlord"].str.lower().str.contains(s, regex=False)]
    if status != "All":
        f = f[f["Status"] == status]
    show_table(f.sort_values("Start Date", ascending=False), money_cols=["Monthly Rent (PKR)", "Security Deposit (PKR)"], status_cols=["Status"],
               hide=["Property ID", "Property Type", "City", "Tenant ID", "Landlord ID", "Agent ID"], empty_msg="No agreements match your filters.")
    st.markdown("##### Agreement payments")
    rid = select_id("Select an agreement to see its rent payments", "rentals", K("rdet_sel"))
    if rid:
        r = get_rec("rentals", rid)
        pdf = df_payments()
        pdf = pdf[pdf["Related ID"] == rid]
        paid = pdf["Paid (PKR)"].sum()
        outstanding = pdf[pdf["Status"].isin(["Pending", "Partially Paid", "Overdue"])]["Balance (PKR)"].sum()
        kpi_row([("Duration", f"{df[df['Agreement ID'] == rid]['Duration (months)'].iloc[0]} months"),
                 ("Received so far", money(paid), "#2b6cb0"), ("Outstanding", money(outstanding), "#c53030")])
        show_table(pdf.sort_values("Due Date"), money_cols=["Amount (PKR)", "Paid (PKR)", "Balance (PKR)"], status_cols=["Status"],
                   hide=["Related ID", "Related To", "Customer ID", "Report Date", "Property Type", "City", "Agent ID"],
                   empty_msg="No payments yet for this agreement. Generate the rent schedule below.")
        st.caption(f"Rent is due on day {int(num(r.get('due_day'), 1))} of each month. Late payments are flagged 'Overdue' automatically.")
        if st.button("Generate rent schedule (adds missing monthly rent + deposit records)", key=K("gen_sched")):
            n = generate_rent_schedule(rid)
            finish(f"{n} payment record(s) created for {rid}." if n else "The schedule is already complete - nothing new to add.",
                   "success" if n else "info")


def rental_new_tab():
    st.subheader("Create a rental agreement")
    if not any(p.get("listing_type") == "For Rent" for p in db()["properties"]):
        st.info("No properties are listed 'For Rent'. Add a rental property first.")
        return
    if len(db()["customers"]) < 2:
        st.info("Register at least two customers (a tenant and a landlord) first.")
        return
    pid = select_id("Property *", "properties", K("radd_prop"), filter_fn=lambda p: p.get("listing_type") == "For Rent")
    prop = get_rec("properties", pid)
    with st.form(K(f"add_rent_{pid}")):
        c1, c2 = st.columns(2)
        with c1:
            tenant = select_id("Tenant *", "customers", K(f"rt_{pid}"))
        with c2:
            landlord = select_id("Landlord *", "customers", K(f"rl_{pid}"))
        c1, c2, c3 = st.columns(3)
        rent = c1.number_input("Monthly rent (PKR) *", min_value=0.0, value=num(prop.get("price")), step=1000.0, format="%.0f", key=K(f"rr_{pid}"))
        deposit = c2.number_input("Security deposit (PKR)", min_value=0.0, value=num(prop.get("price")), step=1000.0, format="%.0f", key=K(f"rd_{pid}"))
        due_day = c3.number_input("Payment due day (1-28)", min_value=1, max_value=28, value=1, step=1, key=K(f"rdd_{pid}"))
        c1, c2 = st.columns(2)
        start = c1.date_input("Agreement start date", value=date.today(), key=K(f"rs_{pid}"))
        end = c2.date_input("Agreement end date", value=date.today() + timedelta(days=365), key=K(f"re_{pid}"))
        notes = st.text_area("Notes", key=K(f"rn_{pid}"))
        sched = st.checkbox("Also generate the monthly rent schedule (pending payment records)", value=True, key=K(f"rg_{pid}"))
        submitted = st.form_submit_button("Save agreement", type="primary")
    if submitted:
        errs = []
        if not get_rec("customers", tenant) or not get_rec("customers", landlord):
            errs.append("A valid tenant and landlord are required.")
        if tenant == landlord:
            errs.append("Tenant and landlord must be different customers.")
        if rent <= 0:
            errs.append("Monthly rent must be greater than zero.")
        if end <= start:
            errs.append("End date must be after the start date.")
        if prop.get("status") == "Sold":
            errs.append("A sold property cannot be rented.")
        clash = rental_overlap(pid, start, end) if end > start else None
        if clash:
            errs.append(f"Dates overlap with agreement {clash['id']} ({clash.get('start_date')} to {clash.get('end_date')}) for this property.")
        if errs:
            for e in errs:
                st.error(e)
            return
        rid = next_id("rentals")
        add_record("rentals", {"id": rid, "property_id": pid, "tenant_id": tenant, "landlord_id": landlord, "monthly_rent": float(rent),
                               "security_deposit": float(deposit), "start_date": start.isoformat(), "end_date": end.isoformat(),
                               "due_day": int(due_day), "status": "Expired" if end < date.today() else "Active", "notes": notes.strip()})
        extra = ""
        if sched:
            extra = f" {generate_rent_schedule(rid)} payment record(s) generated."
        finish(f"Rental agreement {rid} created.{extra}")


def rental_update_tab():
    st.subheader("Update, extend or terminate an agreement")
    if not db()["rentals"]:
        st.info("There are no rental agreements yet.")
        return
    rid = select_id("Select agreement", "rentals", K("rupd_sel"))
    r = get_rec("rentals", rid)
    with st.form(K(f"upd_rent_{rid}")):
        c1, c2, c3 = st.columns(3)
        status = c1.selectbox("Agreement status", RENTAL_STATUSES, index=safe_index(RENTAL_STATUSES, r.get("status")), key=K(f"ru_st_{rid}"))
        end = c2.date_input("End date", value=parse_date(r.get("end_date")) or date.today(), key=K(f"ru_end_{rid}"))
        due_day = c3.number_input("Payment due day (1-28)", min_value=1, max_value=28, value=max(1, min(28, int(num(r.get("due_day"), 1)))), step=1, key=K(f"ru_dd_{rid}"))
        c1, c2 = st.columns(2)
        rent = c1.number_input("Monthly rent (PKR)", min_value=0.0, value=num(r.get("monthly_rent")), step=1000.0, format="%.0f", key=K(f"ru_rent_{rid}"))
        deposit = c2.number_input("Security deposit (PKR)", min_value=0.0, value=num(r.get("security_deposit")), step=1000.0, format="%.0f", key=K(f"ru_dep_{rid}"))
        notes = st.text_area("Notes", r.get("notes", ""), key=K(f"ru_notes_{rid}"))
        submitted = st.form_submit_button("Save changes", type="primary")
    if submitted:
        errs, start = [], parse_date(r.get("start_date"))
        if not start or end <= start:
            errs.append("End date must be after the start date.")
        if rent <= 0:
            errs.append("Monthly rent must be greater than zero.")
        if status == "Active" and end < date.today():
            errs.append("An agreement whose end date has passed cannot be Active. Extend the end date or choose Expired/Terminated.")
        if status == "Expired" and end >= date.today():
            errs.append("'Expired' needs an end date before today. Use 'Terminated' to end an agreement early.")
        if status != "Terminated" and start and end > start:
            clash = rental_overlap(r.get("property_id"), start, end, ignore_id=rid)
            if clash:
                errs.append(f"These dates overlap with agreement {clash['id']} for the same property.")
        if errs:
            for e in errs:
                st.error(e)
            return
        update_record("rentals", rid, {"status": status, "end_date": end.isoformat(), "due_day": int(due_day),
                                       "monthly_rent": float(rent), "security_deposit": float(deposit), "notes": notes.strip()})
        finish(f"Agreement {rid} updated. Property availability refreshed ({status}).")


def page_rentals():
    page_header("Rental Management", "Agreements, expirations and rent tracking")
    tabs = st.tabs(["🔑 Agreements & Rent", "➕ New Agreement", "✏️ Update / Terminate", "🗑️ Delete Agreement"])
    with tabs[0]:
        rental_overview_tab()
    with tabs[1]:
        rental_new_tab()
    with tabs[2]:
        rental_update_tab()
    with tabs[3]:
        delete_panel("rentals", "rental agreement")


# =============================================================================
# 12. PAYMENT MANAGEMENT PAGE
# =============================================================================
def payment_fields(d, prefix, types, default_customer=""):
    k = lambda n: K(f"{prefix}_{n}")
    c1, c2, c3 = st.columns(3)
    ptype = c1.selectbox("Payment type *", types, index=safe_index(types, d.get("payment_type")), key=k("type"))
    with c2:
        cust = select_id("Customer / tenant *", "customers", k("cust"), default=d.get("customer_id") or default_customer)
    amount = c3.number_input("Total amount due (PKR) *", min_value=0.0, value=num(d.get("amount")), step=1000.0, format="%.0f", key=k("amount"))
    c1, c2, c3 = st.columns(3)
    status = c1.selectbox("Payment status *", PAYMENT_STATUSES, index=safe_index(PAYMENT_STATUSES, d.get("status")), key=k("status"))
    paid = c2.number_input("Amount paid so far (PKR)", min_value=0.0, value=num(d.get("amount_paid")), step=1000.0, format="%.0f", key=k("paid"))
    pdate = c3.date_input("Payment date", value=parse_date(d.get("payment_date")) or date.today(), key=k("pdate"))
    c1, c2, c3 = st.columns(3)
    has_due = c1.checkbox("This payment has a due date", value=bool(d.get("due_date")), key=k("hasdue"))
    due = c2.date_input("Due date", value=parse_date(d.get("due_date")) or date.today(), key=k("due"))
    method = c3.selectbox("Payment method", PAYMENT_METHODS, index=safe_index(PAYMENT_METHODS, d.get("method")), key=k("method"))
    ref = st.text_input("Reference number (optional, must be unique)", d.get("reference", ""), key=k("ref"))
    notes = st.text_area("Notes", d.get("notes", ""), key=k("notes"))
    st.caption("Paid = full amount received. Partially Paid = enter the amount received so far. Pending / Overdue = nothing received yet.")
    return {"payment_type": ptype, "customer_id": cust or "", "amount": float(amount), "amount_paid": float(paid),
            "status": status, "payment_date": pdate.isoformat(), "due_date": due.isoformat() if has_due else "",
            "method": method, "reference": ref.strip(), "notes": notes.strip()}


def validate_payment(v, existing_id=None):
    """Validate and normalise a payment dict (v needs related_type and related_id too). Returns error list."""
    errs = []
    amount, paid, status = v["amount"], v["amount_paid"], v["status"]
    if amount <= 0:
        errs.append("Amount must be greater than zero.")
    if status == "Paid":
        v["amount_paid"] = amount
    elif status == "Partially Paid":
        if not 0 < paid < amount:
            errs.append("For 'Partially Paid', the amount paid must be more than 0 and less than the total amount.")
    else:
        v["amount_paid"] = 0.0
    if status not in ("Paid", "Partially Paid"):
        v["payment_date"] = ""
    if not get_rec("customers", v["customer_id"]):
        errs.append("A valid customer / tenant is required.")
    others = [p for p in db()["payments"] if p["id"] != existing_id]
    if v["reference"] and any(txt(p.get("reference")).strip().lower() == v["reference"].lower() for p in others):
        errs.append(f"Reference number '{v['reference']}' is already used by another payment.")
    if v["payment_type"] == "Monthly Rent" and v["due_date"] and any(
            p.get("related_id") == v["related_id"] and p.get("payment_type") == "Monthly Rent" and p.get("due_date") == v["due_date"] for p in others):
        errs.append("A monthly rent payment for this agreement and due date already exists.")
    if v["related_type"] == "Transaction":
        t = get_rec("transactions", v["related_id"])
        if not t:
            errs.append("The related transaction does not exist.")
        elif t.get("status") == "Cancelled":
            errs.append("Payments cannot be recorded against a cancelled transaction.")
        else:
            limit = {"Sale Payment": num(t.get("sale_price")), "Commission": num(t.get("commission_amount"))}.get(v["payment_type"])
            if limit is not None:
                already = sum(num(p.get("amount")) for p in others if p.get("related_id") == v["related_id"] and p.get("payment_type") == v["payment_type"])
                if already + amount > limit + 0.01:
                    errs.append(f"Total {v['payment_type']} amounts ({money(already + amount)}) would exceed the allowed {money(limit)}.")
    elif v["related_type"] == "Rental Agreement" and not get_rec("rentals", v["related_id"]):
        errs.append("The related rental agreement does not exist.")
    return errs


def payment_overview_tab():
    df = df_payments()
    vdf = df_payments(valid_only=True)
    received = vdf["Paid (PKR)"].sum()
    outstanding = vdf[vdf["Status"].isin(["Pending", "Partially Paid", "Overdue"])]["Balance (PKR)"].sum()
    overdue = vdf[vdf["Status"] == "Overdue"]["Balance (PKR)"].sum()
    kpi_row([("Total received", money(received), "#2b6cb0"), ("Outstanding balance", money(outstanding), "#b7791f"),
             ("Overdue amount", money(overdue), "#c53030"), ("Payment records", len(df), "#0b2545")])
    if df.empty:
        st.info("No payments yet. Use 'Record Payment', or generate a rent schedule from the Rentals page.")
        return
    st.caption("Totals exclude payments that belong to cancelled transactions.")
    c1, c2, c3, c4 = st.columns(4)
    search = c1.text_input("Search (ID, customer, reference, related record)", key="payf_search")
    ptype = c2.selectbox("Type", ["All"] + PAYMENT_TYPES, key="payf_type")
    status = c3.selectbox("Status", ["All"] + PAYMENT_STATUSES, key="payf_status")
    method = c4.selectbox("Method", ["All"] + PAYMENT_METHODS, key="payf_method")
    f = df
    if search.strip():
        s = search.strip().lower()
        f = f[f["Payment ID"].str.lower().str.contains(s, regex=False) | f["Customer"].str.lower().str.contains(s, regex=False)
              | f["Reference"].str.lower().str.contains(s, regex=False) | f["Related To"].str.lower().str.contains(s, regex=False)]
    if ptype != "All":
        f = f[f["Type"] == ptype]
    if status != "All":
        f = f[f["Status"] == status]
    if method != "All":
        f = f[f["Method"] == method]
    show_table(f.sort_values("Report Date", ascending=False), money_cols=["Amount (PKR)", "Paid (PKR)", "Balance (PKR)"], status_cols=["Status"],
               hide=["Customer ID", "Related ID", "Report Date", "Property Type", "City", "Agent ID"], empty_msg="No payments match your filters.")
    st.markdown("##### Payment summary by type")
    if not vdf.empty:
        summ = vdf.groupby("Type").agg(Payments=("Payment ID", "count"), Amount=("Amount (PKR)", "sum"),
                                       Paid=("Paid (PKR)", "sum"), Balance=("Balance (PKR)", "sum")).reset_index()
        show_table(summ, money_cols=["Amount", "Paid", "Balance"])
    st.markdown("##### Payment history by customer")
    cid = select_id("Select a customer", "customers", K("payhist_sel"))
    if cid:
        h = vdf[vdf["Customer ID"] == cid]
        kpi_row([("Paid by this customer", money(h["Paid (PKR)"].sum()), "#2b6cb0"),
                 ("Outstanding", money(h[h["Status"].isin(["Pending", "Partially Paid", "Overdue"])]["Balance (PKR)"].sum()), "#b7791f")])
        show_table(h.sort_values("Report Date", ascending=False), money_cols=["Amount (PKR)", "Paid (PKR)", "Balance (PKR)"], status_cols=["Status"],
                   hide=["Customer ID", "Customer", "Related ID", "Report Date", "Property Type", "City", "Agent ID"],
                   empty_msg="This customer has no payments.")


def payment_record_tab():
    st.subheader("Record a payment")
    if not db()["customers"]:
        st.info("Register a customer before recording payments.")
        return
    kind = st.radio("This payment is for", ["Sale transaction", "Rental agreement", "Other / general"], horizontal=True, key=K("padd_kind"))
    related_id, default_cust = "", ""
    if kind == "Sale transaction":
        related_type, types = "Transaction", ["Sale Payment", "Commission", "Other"]
        related_id = select_id("Transaction *", "transactions", K("padd_rt"), filter_fn=lambda t: t.get("status") != "Cancelled")
        if not related_id:
            st.info("There are no open transactions. Record a sale first.")
            return
        default_cust = get_rec("transactions", related_id).get("buyer_id", "")
    elif kind == "Rental agreement":
        related_type, types = "Rental Agreement", ["Monthly Rent", "Security Deposit", "Other"]
        related_id = select_id("Rental agreement *", "rentals", K("padd_rr"))
        if not related_id:
            st.info("There are no rental agreements. Create one first.")
            return
        default_cust = get_rec("rentals", related_id).get("tenant_id", "")
    else:
        related_type, types = "General", ["Other"]
    with st.form(K(f"add_payment_{kind}_{related_id}")):
        v = payment_fields({}, f"payadd_{kind}_{related_id}", types, default_cust)
        submitted = st.form_submit_button("Save payment", type="primary")
    if submitted:
        v.update({"related_type": related_type, "related_id": related_id})
        errs = validate_payment(v)
        if errs:
            for e in errs:
                st.error(e)
            return
        pid = next_id("payments")
        add_record("payments", {"id": pid, **v})
        finish(f"Payment {pid} recorded ({v['status']}, {money(v['amount_paid'])} received of {money(v['amount'])}).")


def payment_update_tab():
    st.subheader("Update a payment")
    if not db()["payments"]:
        st.info("There are no payments to update yet.")
        return
    pid = select_id("Select payment", "payments", K("payupd_sel"))
    p = get_rec("payments", pid)
    st.caption(f"Related to: {p.get('related_type')} {p.get('related_id') or ''} · Balance now: {money(balance_of(p))}")
    with st.form(K(f"upd_payment_{pid}")):
        v = payment_fields(p, f"payupd_{pid}", [p.get("payment_type", "Other")])
        submitted = st.form_submit_button("Update payment", type="primary")
    if submitted:
        v.update({"related_type": p.get("related_type", "General"), "related_id": p.get("related_id", "")})
        errs = validate_payment(v, existing_id=pid)
        if errs:
            for e in errs:
                st.error(e)
            return
        update_record("payments", pid, v)
        finish(f"Payment {pid} updated. Remaining balance: {money(max(v['amount'] - v['amount_paid'], 0))}.")


def page_payments():
    page_header("Payment Management", "Sale payments, rent, deposits, commissions and outstanding balances")
    tabs = st.tabs(["💳 Payments & Balances", "➕ Record Payment", "✏️ Update Payment", "🗑️ Delete Payment"])
    with tabs[0]:
        payment_overview_tab()
    with tabs[1]:
        payment_record_tab()
    with tabs[2]:
        payment_update_tab()
    with tabs[3]:
        delete_panel("payments", "payment")


# =============================================================================
# 13. DASHBOARD PAGE
# =============================================================================
def page_dashboard():
    page_header("Dashboard Overview", f"Live summary of your agency · {date.today():%d %B %Y}")
    props = df_properties()
    if not any(db()[t] for t in TABLES):
        st.info("Your database is empty. Add data from the sidebar pages, or load a small sample data set to explore the app.")
        if st.button("Load sample data", type="primary", key="dash_sample"):
            load_sample_data()
            finish("Sample data loaded. Explore every page, then delete it from 'About & Help' when you are done.")
    counts = props["Status"].value_counts() if not props.empty else pd.Series(dtype=int)
    kpi_row([("Total properties", len(props)), ("Available", int(counts.get("Available", 0)), "#0b6e4f"),
             ("Sold", int(counts.get("Sold", 0)), "#c53030"), ("Rented", int(counts.get("Rented", 0)), "#2b6cb0"),
             ("Under negotiation", int(counts.get("Under Negotiation", 0)), "#b7791f")])
    kpi_row([("Registered customers", len(db()["customers"]), "#0b2545"), ("Registered agents", len(db()["agents"]), "#0b2545"),
             ("Total sales revenue", money(total_sales_revenue()), "#0b6e4f"), ("Total rental income", money(total_rental_income()), "#2b6cb0"),
             ("Pending payments", money(total_outstanding()), "#c53030")])

    st.markdown("#### Property distribution")
    c1, c2 = st.columns(2)
    if props.empty:
        c1.info("Charts appear once you add properties.")
    else:
        c1.caption("By property type and status")
        c1.bar_chart(pd.crosstab(props["Type"], props["Status"]).reindex(columns=PROPERTY_STATUSES, fill_value=0))
        c2.caption("By listing type")
        c2.bar_chart(props["Listing"].value_counts())

    st.markdown("#### Monthly sales and rental income")
    txns, pays = df_transactions(), df_payments(valid_only=True)
    sales = monthly_sum(txns[txns["Status"] == "Completed"], "Date", "Sale Price (PKR)")
    rent = pays[(pays["Type"] == "Monthly Rent") & (pays["Paid (PKR)"] > 0)]
    rent = monthly_sum(rent, "Payment Date", "Paid (PKR)")
    c1, c2 = st.columns(2)
    if sales.empty:
        c1.info("Monthly sales revenue appears after the first completed sale.")
    else:
        c1.caption("Sales revenue (PKR) - completed sales only")
        c1.bar_chart(sales.sort_index().tail(12).rename("Sales revenue"))
    if rent.empty:
        c2.info("Monthly rental income appears after the first rent payment is recorded.")
    else:
        c2.caption("Rental income (PKR) - rent actually received")
        c2.bar_chart(rent.sort_index().tail(12).rename("Rental income"))

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Recent property listings")
        show_table(props.sort_values("Listing Date", ascending=False).head(5)[["Property ID", "Title", "Type", "Listing", "Price (PKR)", "City", "Status"]]
                   if not props.empty else props, money_cols=["Price (PKR)"], status_cols=["Status"], empty_msg="No properties listed yet.")
    with c2:
        st.markdown("#### Recent transactions")
        show_table(txns.sort_values("Date", ascending=False).head(5)[["Transaction ID", "Property", "Buyer", "Sale Price (PKR)", "Date", "Status"]]
                   if not txns.empty else txns, money_cols=["Sale Price (PKR)"], status_cols=["Status"], empty_msg="No transactions yet.")


# =============================================================================
# 14. REPORTS & ANALYTICS PAGE
# =============================================================================
def report_filters():
    d, dates = db(), []
    for table, key in [("properties", "listing_date"), ("transactions", "date"), ("rentals", "start_date"), ("inquiries", "date"),
                       ("payments", "payment_date"), ("payments", "due_date"), ("customers", "registration_date")]:
        dates += [parse_date(r.get(key)) for r in d[table]]
    dates = [x for x in dates if x]
    start_default = min(dates) if dates else date.today() - timedelta(days=365)
    end_default = max(dates + [date.today()])
    with st.expander("Report filters", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        rng = c1.date_input("Date range", value=(start_default, end_default), key="rep_range")
        types = c2.multiselect("Property type", PROPERTY_TYPES, key="rep_types")
        cities = c3.multiselect("City", sorted({p.get("city") for p in d["properties"] if p.get("city")}), key="rep_cities")
        agents = c4.multiselect("Agent", [a["id"] for a in d["agents"]], format_func=lambda x: label_of("agents", x), key="rep_agents")
    if isinstance(rng, (tuple, list)) and len(rng) == 2:
        start, end = rng
    else:
        start = rng[0] if isinstance(rng, (tuple, list)) else rng
        end = end_default
        st.caption("Pick an end date to complete the date range.")
    return {"start": start, "end": end, "types": types, "cities": cities, "agents": agents}


def apply_common(df, f, date_col=None, type_col="Property Type", city_col="City", agent_col="Agent ID"):
    """Apply date-range, property-type, city and agent filters to a report table."""
    out = df
    if date_col:
        dts = pd.to_datetime(out[date_col], errors="coerce")
        out = out[(dts >= pd.Timestamp(f["start"])) & (dts <= pd.Timestamp(f["end"]))]
    if f["types"] and type_col:
        out = out[out[type_col].isin(f["types"])]
    if f["cities"] and city_col:
        out = out[out[city_col].isin(f["cities"])]
    if f["agents"] and agent_col:
        out = out[out[agent_col].isin(f["agents"])]
    return out


def price_distribution(prices, bins=8):
    """Bucket prices into ranges (labels are numbered so charts keep the order)."""
    s = pd.Series(prices).dropna()
    if s.empty:
        return None
    if s.nunique() == 1:
        return pd.DataFrame({"Properties": [len(s)]}, index=[f"01. {short_money(s.iloc[0])}"])
    counts = pd.cut(s, bins=min(bins, s.nunique())).value_counts(sort=False)
    labels = [f"{n + 1:02d}. {short_money(i.left)} - {short_money(i.right)}" for n, i in enumerate(counts.index)]
    return pd.DataFrame({"Properties": counts.values}, index=labels)


def page_reports():
    page_header("Reports & Analytics", "Charts and tables built from your real records and the filters below")
    f = report_filters()
    props = apply_common(df_properties(), f, "Listing Date", type_col="Type")
    custs = apply_common(df_customers(), f, "Registered", type_col=None, city_col=None, agent_col=None)
    agents = df_agents()
    if f["agents"]:
        agents = agents[agents["Agent ID"].isin(f["agents"])]
    txns = apply_common(df_transactions(), f, "Date")
    rents = apply_common(df_rentals(), f, "Start Date")
    inqs = apply_common(df_inquiries(), f, "Date")
    pays = apply_common(df_payments(valid_only=True), f, "Report Date")
    st.caption("Date filters use: listing date (properties), registration date (customers), transaction date, agreement start date, "
               "inquiry date, and payment date (or due date when unpaid). Customers and agents are not filtered by property type or city.")
    tabs = st.tabs(["🏘️ Properties", "💼 Sales & Commission", "🔑 Rentals & Payments", "🧑‍💼 Agents", "📋 Inquiries", "⬇️ Export CSV"])

    with tabs[0]:
        if props.empty:
            st.info("No properties match the selected filters.")
        else:
            sale_prices = props[props["Listing"] == "For Sale"]["Price (PKR)"]
            kpi_row([("Properties", len(props)), ("Available", int((props["Status"] == "Available").sum()), "#0b6e4f"),
                     ("Sold", int((props["Status"] == "Sold").sum()), "#c53030"), ("Rented", int((props["Status"] == "Rented").sum()), "#2b6cb0"),
                     ("Average sale price", money(sale_prices.mean()) if len(sale_prices) else "n/a", "#0b2545")])
            c1, c2 = st.columns(2)
            c1.markdown("**Properties by type**")
            c1.bar_chart(props["Type"].value_counts())
            c2.markdown("**Properties by city**")
            c2.bar_chart(props["City"].value_counts())
            c1.markdown("**Properties by listing status**")
            c1.bar_chart(pd.crosstab(props["Type"], props["Status"]).reindex(columns=PROPERTY_STATUSES, fill_value=0))
            c2.markdown("**Properties by area**")
            c2.dataframe(props.groupby(["City", "Area"]).size().reset_index(name="Properties").sort_values("Properties", ascending=False), hide_index=True)
            st.markdown("**Property price distribution**")
            c1, c2 = st.columns(2)
            for col, listing in ((c1, "For Sale"), (c2, "For Rent")):
                dist = price_distribution(props[props["Listing"] == listing]["Price (PKR)"])
                col.caption(f"{listing} (PKR; Lac = 100,000, Cr = 10,000,000)")
                if dist is None:
                    col.info(f"No '{listing}' properties in this selection.")
                else:
                    col.bar_chart(dist)

    with tabs[1]:
        completed = txns[txns["Status"] == "Completed"]
        kpi_row([("Sales revenue", money(completed["Sale Price (PKR)"].sum()), "#0b6e4f"), ("Completed", len(completed)),
                 ("Pending", int((txns["Status"] == "Pending").sum()), "#b7791f"), ("Cancelled", int((txns["Status"] == "Cancelled").sum()), "#718096"),
                 ("Commission earned", money(completed["Commission (PKR)"].sum()), "#2b6cb0")])
        if txns.empty:
            st.info("No transactions match the selected filters.")
        else:
            c1, c2 = st.columns(2)
            rev = monthly_sum(completed, "Date", "Sale Price (PKR)")
            c1.markdown("**Monthly sales revenue (completed only)**")
            if rev.empty:
                c1.info("No completed sales in this selection.")
            else:
                c1.bar_chart(rev.sort_index().rename("Sales revenue"))
            t2 = txns.copy()
            t2["Month"] = pd.to_datetime(t2["Date"], errors="coerce").dt.strftime("%Y-%m")
            c2.markdown("**Transaction counts by month**")
            c2.bar_chart(pd.crosstab(t2["Month"], t2["Status"]))
            st.markdown("**Commission summary by agent** (earned = completed sales only; paid = 'Commission' payments recorded)")
            if completed.empty:
                st.info("No completed sales, so no commission has been earned.")
            else:
                comm = completed.groupby(["Agent ID", "Agent"]).agg(Sales=("Transaction ID", "count"), Revenue=("Sale Price (PKR)", "sum"),
                                                                    Earned=("Commission (PKR)", "sum")).reset_index()
                paid_comm = pays[pays["Type"] == "Commission"].groupby("Agent ID")["Paid (PKR)"].sum()
                comm["Paid"] = comm["Agent ID"].map(paid_comm).fillna(0.0)
                comm["Outstanding"] = comm["Earned"] - comm["Paid"]
                show_table(comm.drop(columns=["Agent ID"]), money_cols=["Revenue", "Earned", "Paid", "Outstanding"])

    with tabs[2]:
        rent_paid = pays[(pays["Type"] == "Monthly Rent") & (pays["Paid (PKR)"] > 0)]
        out = pays[pays["Status"].isin(["Pending", "Partially Paid", "Overdue"]) & (pays["Balance (PKR)"] > 0)]
        kpi_row([("Rental income received", money(rent_paid["Paid (PKR)"].sum()), "#2b6cb0"), ("Rental agreements", len(rents)),
                 ("Outstanding payments", money(out["Balance (PKR)"].sum()), "#b7791f"),
                 ("Overdue", money(out[out["Status"] == "Overdue"]["Balance (PKR)"].sum()), "#c53030")])
        c1, c2 = st.columns(2)
        c1.markdown("**Monthly rental income (rent received)**")
        inc = monthly_sum(rent_paid, "Payment Date", "Paid (PKR)")
        if inc.empty:
            c1.info("No rent payments received in this selection.")
        else:
            c1.bar_chart(inc.sort_index().rename("Rental income"))
        c2.markdown("**Rental agreement status**")
        if rents.empty:
            c2.info("No rental agreements in this selection.")
        else:
            c2.bar_chart(rents["Status"].value_counts())
        st.markdown("**Outstanding payment report**")
        show_table(out.sort_values("Due Date"), money_cols=["Amount (PKR)", "Paid (PKR)", "Balance (PKR)"], status_cols=["Status"],
                   hide=["Customer ID", "Related ID", "Report Date", "Property Type", "City", "Agent ID"], empty_msg="No outstanding payments in this selection.")
        if not out.empty:
            by_cust = out.groupby("Customer")["Balance (PKR)"].sum().reset_index().sort_values("Balance (PKR)", ascending=False)
            st.markdown("**Outstanding balance by customer**")
            show_table(by_cust, money_cols=["Balance (PKR)"])
        if not pays.empty:
            st.markdown("**Payment summary by status**")
            summ = pays.groupby("Status").agg(Payments=("Payment ID", "count"), Amount=("Amount (PKR)", "sum"),
                                              Paid=("Paid (PKR)", "sum"), Balance=("Balance (PKR)", "sum")).reset_index()
            show_table(summ, money_cols=["Amount", "Paid", "Balance"], status_cols=["Status"])

    with tabs[3]:
        if agents.empty:
            st.info("No agents to report on.")
        else:
            show_table(agents, money_cols=["Total Commission Earned (PKR)"], status_cols=["Status"])
            done = txns[txns["Status"] == "Completed"]
            st.markdown("**Agent performance in the selected period (completed sales)**")
            if done.empty:
                st.info("No completed sales in this selection.")
            else:
                perf = done.groupby("Agent").agg(Sales=("Transaction ID", "count"), Revenue=("Sale Price (PKR)", "sum"), Commission=("Commission (PKR)", "sum"))
                c1, c2 = st.columns(2)
                c1.caption("Sales revenue by agent (PKR)")
                c1.bar_chart(perf[["Revenue"]])
                c2.caption("Commission by agent (PKR)")
                c2.bar_chart(perf[["Commission"]])

    with tabs[4]:
        total = len(inqs)
        conv = int((inqs["Status"] == "Converted").sum()) if total else 0
        kpi_row([("Inquiries", total), ("Converted", conv, "#0b6e4f"), ("Conversion rate", f"{(conv / total * 100) if total else 0:.1f}%", "#0b2545")])
        if inqs.empty:
            st.info("No inquiries match the selected filters.")
        else:
            c1, c2 = st.columns(2)
            c1.markdown("**Inquiries by status**")
            c1.bar_chart(inqs["Status"].value_counts().reindex(INQUIRY_STATUSES, fill_value=0))
            rate = inqs.assign(Converted=(inqs["Status"] == "Converted").astype(int)).groupby("Property Type").agg(
                Inquiries=("Inquiry ID", "count"), Converted=("Converted", "sum")).reset_index()
            rate["Conversion %"] = (rate["Converted"] / rate["Inquiries"] * 100).round(1)
            c2.markdown("**Conversion rate by property type**")
            c2.dataframe(rate, hide_index=True)
            by_agent = inqs.assign(Converted=(inqs["Status"] == "Converted").astype(int), Agent=inqs["Agent"].replace("", "Unassigned")).groupby("Agent").agg(
                Inquiries=("Inquiry ID", "count"), Converted=("Converted", "sum")).reset_index()
            by_agent["Conversion %"] = (by_agent["Converted"] / by_agent["Inquiries"] * 100).round(1)
            st.markdown("**Conversion rate by agent**")
            st.dataframe(by_agent, hide_index=True)

    with tabs[5]:
        st.caption("Downloads contain the records that match the filters above (all columns, UTF-8 CSV that opens in Excel).")
        exports = [("Properties", props), ("Customers", custs), ("Agents", agents), ("Transactions", txns),
                   ("Rental agreements", rents), ("Inquiries", inqs), ("Payments", pays)]
        cols = st.columns(3)
        for i, (name, data) in enumerate(exports):
            with cols[i % 3]:
                st.download_button(f"Download {name} ({len(data)} rows)", csv_bytes(data),
                                   file_name=f"{name.lower().replace(' ', '_')}.csv", mime="text/csv", key=f"dl_{name}")


# =============================================================================
# 15. ABOUT & HELP PAGE (+ data management)
# =============================================================================
def load_sample_data():
    """Fill an EMPTY database with a small, consistent demo data set."""
    today = date.today()
    iso = lambda days: (today + timedelta(days=days)).isoformat()
    d = db()
    d["agents"] = [
        {"id": "AGT-0001", "name": "Ayesha Khan", "phone": "0300-1112233", "email": "ayesha@example.com", "office": "Peshawar", "joining_date": iso(-700), "commission_pct": 2.0, "status": "Active"},
        {"id": "AGT-0002", "name": "Bilal Ahmad", "phone": "0311-2223344", "email": "bilal@example.com", "office": "Islamabad", "joining_date": iso(-500), "commission_pct": 1.5, "status": "Active"},
        {"id": "AGT-0003", "name": "Sana Malik", "phone": "0322-3334455", "email": "sana@example.com", "office": "Lahore", "joining_date": iso(-300), "commission_pct": 2.5, "status": "Active"}]
    people = [("Usman Tariq", "Buyer", "Peshawar"), ("Hira Noor", "Seller", "Lahore"), ("Kamran Shah", "Tenant", "Peshawar"),
              ("Farhan Ali", "Landlord", "Peshawar"), ("Zainab Iqbal", "Buyer", "Lahore"), ("Imran Khattak", "Seller", "Peshawar")]
    d["customers"] = [{"id": f"CUS-{i + 1:04d}", "name": n, "phone": f"030{i}-555010{i}", "email": f"{n.split()[0].lower()}@example.com", "city": c,
                       "address": f"House {10 + i}, {c}", "customer_type": t, "registration_date": iso(-200 + i * 10), "notes": ""} for i, (n, t, c) in enumerate(people)]

    def prop(n, title, ptype, listing, price, city, area, beds, baths, size, unit, owner, agent, days):
        return {"id": f"PRP-{n:04d}", "title": title, "property_type": ptype, "listing_type": listing, "price": float(price), "city": city,
                "area": area, "address": f"{area}, {city}", "bedrooms": beds, "bathrooms": baths, "covered_area": float(size), "area_unit": unit,
                "owner_name": owner, "owner_contact": "0300-7654321", "agent_id": agent, "listing_date": iso(days), "image_url": "",
                "description": f"{title} - a well located property.", "status": "Available"}
    d["properties"] = [
        prop(1, "Modern 10 Marla House, DHA Phase 6", "House", "For Sale", 38500000, "Lahore", "DHA Phase 6", 5, 5, 10, "Marla", "Hira Noor", "AGT-0003", -90),
        prop(2, "2-Bed Apartment near University Town", "Apartment", "For Rent", 55000, "Peshawar", "University Town", 2, 2, 1100, "Square Feet", "Farhan Ali", "AGT-0001", -110),
        prop(3, "1 Kanal Residential Plot, Hayatabad", "Residential Plot", "For Sale", 21000000, "Peshawar", "Hayatabad Phase 5", 0, 0, 1, "Kanal", "Imran Khattak", "AGT-0001", -30),
        prop(4, "Commercial Shop on Saddar Road", "Shop", "For Sale", 14500000, "Rawalpindi", "Saddar", 0, 1, 450, "Square Feet", "Imran Khattak", "AGT-0002", -20),
        prop(5, "Executive Office, Blue Area", "Office", "For Rent", 180000, "Islamabad", "Blue Area", 0, 2, 2200, "Square Feet", "Farhan Ali", "AGT-0002", -15),
        prop(6, "Farmhouse on Bedian Road", "Farmhouse", "For Sale", 95000000, "Lahore", "Bedian Road", 6, 7, 4, "Kanal", "Hira Noor", "AGT-0003", -10),
        prop(7, "5 Marla House, Gulberg Greens", "House", "For Sale", 17800000, "Islamabad", "Gulberg Greens", 3, 3, 5, "Marla", "Imran Khattak", "AGT-0002", -5)]

    def inq(n, cust, p, agent, status, days, method, vdate="", vtime="", outcome=""):
        return {"id": f"INQ-{n:04d}", "customer_id": cust, "property_id": p, "agent_id": agent, "date": iso(days), "contact_method": method,
                "status": status, "notes": "", "viewing_date": vdate, "viewing_time": vtime, "viewing_outcome": outcome}
    d["inquiries"] = [
        inq(1, "CUS-0001", "PRP-0003", "AGT-0001", "Negotiation", -12, "Phone", iso(-8), "11:00", "Liked the plot, negotiating price."),
        inq(2, "CUS-0005", "PRP-0006", "AGT-0003", "Viewing Scheduled", -4, "WhatsApp", iso(3), "15:30"),
        inq(3, "CUS-0005", "PRP-0001", "AGT-0003", "Converted", -60, "Email"),
        inq(4, "CUS-0003", "PRP-0002", "AGT-0001", "Converted", -105, "Phone"),
        inq(5, "CUS-0001", "PRP-0007", "AGT-0002", "New", -2, "In Person"),
        inq(6, "CUS-0003", "PRP-0004", "AGT-0002", "Closed", -18, "Phone")]
    d["transactions"] = [
        {"id": "TXN-0001", "property_id": "PRP-0001", "buyer_id": "CUS-0005", "seller_id": "CUS-0002", "agent_id": "AGT-0003", "sale_price": 38500000.0,
         "commission_pct": 2.5, "commission_amount": 962500.0, "date": iso(-45), "status": "Completed"},
        {"id": "TXN-0002", "property_id": "PRP-0003", "buyer_id": "CUS-0001", "seller_id": "CUS-0006", "agent_id": "AGT-0001", "sale_price": 21000000.0,
         "commission_pct": 2.0, "commission_amount": 420000.0, "date": iso(-5), "status": "Pending"}]
    d["rentals"] = [{"id": "RNT-0001", "property_id": "PRP-0002", "tenant_id": "CUS-0003", "landlord_id": "CUS-0004", "monthly_rent": 55000.0,
                     "security_deposit": 110000.0, "start_date": iso(-100), "end_date": iso(265), "due_day": 5, "status": "Active", "notes": "One-year agreement."}]

    def pay(n, rel_type, rel, cust, ptype, amount, paid, status, pdate, method, ref):
        return {"id": f"PAY-{n:04d}", "related_type": rel_type, "related_id": rel, "customer_id": cust, "payment_type": ptype, "amount": float(amount),
                "amount_paid": float(paid), "payment_date": pdate, "due_date": "", "method": method, "status": status, "reference": ref, "notes": ""}
    d["payments"] = [
        pay(1, "Transaction", "TXN-0001", "CUS-0005", "Sale Payment", 38500000, 38500000, "Paid", iso(-40), "Bank Transfer", "BT-1001"),
        pay(2, "Transaction", "TXN-0001", "CUS-0005", "Commission", 962500, 500000, "Partially Paid", iso(-35), "Bank Transfer", "CM-2001"),
        pay(3, "Transaction", "TXN-0002", "CUS-0001", "Sale Payment", 2000000, 2000000, "Paid", iso(-4), "Cash", "")]
    generate_rent_schedule("RNT-0001")
    for p in d["payments"]:  # mark older rent as received so the demo shows income and some overdue rent
        due = parse_date(p.get("due_date"))
        if p.get("related_id") == "RNT-0001" and due and due < today - timedelta(days=20):
            p.update({"status": "Paid", "amount_paid": p["amount"], "payment_date": p["due_date"], "method": "Bank Transfer"})
    save_data()


def page_about():
    page_header("About & Help", "How the dashboard works and how to manage your data")
    st.markdown("""
**Real Estate Management Dashboard** helps an agency manage properties, customers, agents, inquiries, sales, rentals and payments.
All amounts are in Pakistani Rupees (PKR).

##### Quick start
1. **Agents** - add your agents (with commission %).
2. **Customers** - register buyers, sellers, tenants and landlords.
3. **Properties** - add listings and assign an agent.
4. **Inquiries** - record leads and schedule viewings.
5. **Sales** or **Rentals** - record a sale, or create a rental agreement.
6. **Payments** - record money received; the dashboard and reports update automatically.

##### Business rules built into the app
- **Property status is automatic**: *Sold* (completed sale), *Rented* (active agreement), *Under Negotiation* (pending sale or inquiry in 'Negotiation'), otherwise *Available*.
- A property can **never be sold twice**, and sold, rented or already-pending properties cannot get a new sale.
- **Revenue** counts only *Completed* sales. Cancelled and pending sales are excluded.
- **Commission** = sale price x commission %, calculated once per transaction, only for completed sales (cancelled ones earn nothing). Rentals count as completed deals for agent statistics but carry no automatic commission.
- **Rental income** is the rent actually *received* (Monthly Rent payments). Security deposits and the property value are not income.
- Rental agreements for the same property **cannot overlap**. Agreements expire automatically after their end date.
- Unpaid payments past their due date become **Overdue** automatically. Remaining balance = amount due - amount paid.
- Records that are still referenced elsewhere (for example a customer with a transaction) cannot be deleted.
""")
    st.markdown("##### Data management")
    st.warning("Data is saved in a local file (realestate_data.json). On Streamlit Community Cloud this file is **not guaranteed** to survive app restarts or redeployments. "
               "Download a backup regularly.")
    st.download_button("Download full backup (.json)", json.dumps(db(), indent=2, ensure_ascii=False), file_name="realestate_backup.json",
                       mime="application/json", key=K("backup_dl"))
    up = st.file_uploader("Restore from a backup file (.json)", type=["json"], key=K("restore_up"))
    if up is not None:
        try:
            restored = clean_loaded(json.loads(up.getvalue().decode("utf-8")))
            st.info("Backup contains: " + ", ".join(f"{len(restored[t])} {t}" for t in TABLES))
            ok = st.checkbox("I understand this replaces ALL current data.", key=K("restore_ok"))
            if st.button("Restore backup", disabled=not ok, type="primary", key=K("restore_btn")):
                st.session_state.db = restored
                save_data()
                finish("Backup restored successfully.")
        except (ValueError, UnicodeDecodeError):
            st.error("That file is not a valid backup. Please upload a .json file created by this app.")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Sample data**")
        empty = not any(db()[t] for t in TABLES)
        if st.button("Load sample data", disabled=not empty, key=K("sample_btn")):
            load_sample_data()
            finish("Sample data loaded.")
        if not empty:
            st.caption("Sample data can only be loaded into an empty database (so nothing is overwritten).")
    with c2:
        st.markdown("**Erase everything**")
        word = st.text_input("Type DELETE to enable the erase button", key=K("erase_word"))
        if st.button("Erase all data", disabled=word != "DELETE", type="primary", key=K("erase_btn")):
            st.session_state.db = {t: [] for t in TABLES}
            save_data()
            finish("All data erased.")


# =============================================================================
# 16. MAIN APP (sidebar navigation)
# =============================================================================
PAGES = {
    "📊 Dashboard": page_dashboard,
    "🏘️ Properties": page_properties,
    "👥 Customers": page_customers,
    "🧑‍💼 Agents": page_agents,
    "📋 Inquiries & Viewings": page_inquiries,
    "💼 Sales & Transactions": page_sales,
    "🔑 Rentals": page_rentals,
    "💳 Payments": page_payments,
    "📈 Reports & Analytics": page_reports,
    "ℹ️ About & Help": page_about,
}


def main():
    init_state()
    sync_data()
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    with st.sidebar:
        st.markdown("## 🏠 EstatePro")
        st.caption("Real Estate Management Dashboard")
        page = st.radio("Navigation", list(PAGES), label_visibility="collapsed", key="nav")
        st.divider()
        st.caption(f"{len(db()['properties'])} properties · {len(db()['customers'])} customers · {len(db()['agents'])} agents")
        st.caption("Data file: realestate_data.json (see About & Help for backup)")
    show_flash()
    PAGES[page]()


main()
