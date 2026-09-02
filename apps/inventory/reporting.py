import calendar
from datetime import date, timedelta

QUICK_RANGE_LABELS = {
    "today": "Today",
    "yesterday": "Yesterday",
    "this_week": "This Week",
    "last_week": "Last Week",
    "this_month": "This Month",
    "last_month": "Last Month",
    "this_year": "This Year",
}


def get_quick_range(key, today=None):
    """Return (start_date, end_date) for a named quick filter, or (None, None)
    if the key isn't recognized. Weeks run Monday-Sunday. Correctly handles
    month/year boundaries since everything is computed from `today`, never
    hardcoded."""
    today = today or date.today()

    if key == "today":
        return today, today
    if key == "yesterday":
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    if key == "this_week":
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=6)
    if key == "last_week":
        this_week_start = today - timedelta(days=today.weekday())
        start = this_week_start - timedelta(days=7)
        return start, start + timedelta(days=6)
    if key == "this_month":
        start = today.replace(day=1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        return start, today.replace(day=last_day)
    if key == "last_month":
        first_of_this_month = today.replace(day=1)
        last_month_end = first_of_this_month - timedelta(days=1)
        return last_month_end.replace(day=1), last_month_end
    if key == "this_year":
        return date(today.year, 1, 1), date(today.year, 12, 31)

    return None, None


def month_range(year, month):
    """Return (start_date, end_date) spanning the given calendar month."""
    start = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    return start, date(year, month, last_day)


def format_period_label(date_from, date_to):
    if not date_from and not date_to:
        return "All time"
    if date_from and date_to and date_from == date_to:
        return date_from.strftime("%b %d, %Y")
    if date_from and date_to:
        return f"{date_from.strftime('%b %d, %Y')} – {date_to.strftime('%b %d, %Y')}"
    if date_from:
        return f"From {date_from.strftime('%b %d, %Y')}"
    return f"Through {date_to.strftime('%b %d, %Y')}"
