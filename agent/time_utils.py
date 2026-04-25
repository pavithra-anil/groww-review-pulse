import hashlib
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def current_iso_week() -> str:
    """Returns current ISO week string e.g. '2026-W17'"""
    now = datetime.now(IST)
    year, week, _ = now.isocalendar()
    return f"{year}-W{week:02d}"


def week_date_range(iso_week: str) -> tuple[datetime, datetime]:
    """Returns (start, end) datetime for a given ISO week string"""
    year, week = iso_week.split("-W")
    start = datetime.fromisocalendar(int(year), int(week), 1).replace(tzinfo=IST)
    end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return start, end


def weeks_ago_date(weeks: int) -> datetime:
    """Returns naive UTC datetime N weeks ago from now"""
    return datetime.now(timezone.utc) - timedelta(weeks=weeks)


def make_run_id(product: str, iso_week: str) -> str:
    """Creates deterministic run ID from product + week"""
    raw = f"{product}:{iso_week}"
    return hashlib.sha1(raw.encode()).hexdigest()