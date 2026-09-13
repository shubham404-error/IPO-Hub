import pandas as pd
from datetime import datetime

# ---------- Formatting ----------

def is_missing(value):
    return value is None or pd.isna(value)

def money(value, decimals=0):
    if is_missing(value):
        return "—"
    value = float(value)
    return f"₹{value:,.{decimals}f}" if decimals else f"₹{value:,.0f}"

def price_band(row):
    low = row.get("price_low")
    high = row.get("price_high")
    if is_missing(low):
        return "—"
    if is_missing(high):
        return money(low)
    return f"{money(low)}–{money(high)}"

def multiple(value):
    if is_missing(value):
        return "—"
    return f"{float(value):,.2f}x"

def applications(value):
    if is_missing(value):
        return "—"
    return f"{int(float(value)):,}"

def clean_text(value):
    if is_missing(value):
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "n/a", "na"}:
        return None
    return text

def format_date(value, with_time=False):
    value = clean_text(value)
    if not value:
        return "—"
    if with_time:
        for fmt in ["%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"]:
            try:
                dt = datetime.strptime(value, fmt)
                return dt.strftime("%d %b %Y, %H:%M")
            except ValueError:
                pass
    for fmt in ["%b %d, %Y", "%d %b %Y", "%Y-%m-%d"]:
        try:
            return datetime.strptime(value[:10], fmt).strftime("%d %b %Y")
        except ValueError:
            pass
    return value

# ---------- Status ----------

LIVE_STATUSES = {"live", "open", "pre-apply"}
CLOSED_STATUSES = {"closed", "allotment out", "allotment awaited"}

def normalized_status(row):
    raw = clean_text(row.get("status"))
    if raw:
        value = raw.lower()
        if value in LIVE_STATUSES:
            return "Live"
        if value in CLOSED_STATUSES:
            if value == "allotment out":
                return "Allotment Out"
            if value == "allotment awaited":
                return "Allotment Awaited"
            return "Closed"
        if value in {"tentative dates", "drhp approved"}:
            return "Upcoming"

    open_date = pd.to_datetime(row.get("open_date"), errors="coerce")
    close_date = pd.to_datetime(row.get("close_date"), errors="coerce")
    today = pd.Timestamp.now().normalize()

    if pd.notna(open_date) and pd.notna(close_date):
        if open_date.normalize() <= today <= close_date.normalize():
            return "Live"
        if today < open_date.normalize():
            return "Upcoming"
        if today > close_date.normalize():
            return "Closed"
    return "Upcoming"

def score_color(s):
    if s is None: return "⚪"
    if s >= 75: return "🟢"
    if s >= 50: return "🟡"
    return "🔴"

def format_score(score):
    if score >= 75: return f"🟢 STRONG · {score}/100"
    if score >= 50: return f"🟡 SELECTIVE · {score}/100"
    return f"🔴 LOW · {score}/100"
