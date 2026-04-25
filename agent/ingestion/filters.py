import re
from datetime import datetime, timezone

# Emoji pattern
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F9FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE
)

MIN_WORD_COUNT = 10


def strip_emojis(text: str) -> str:
    """Remove emojis from text"""
    return EMOJI_PATTERN.sub("", text).strip()


def count_words(text: str) -> int:
    """Count words after stripping emojis"""
    clean = strip_emojis(text)
    return len(clean.split())


def is_english(text: str) -> bool:
    """Check if text is English using langdetect"""
    try:
        from langdetect import detect
        return detect(text) == "en"
    except Exception:
        return False


def normalize_datetime(dt: datetime) -> datetime:
    """Convert any datetime to naive UTC for comparison"""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def is_within_window(review_date: datetime, cutoff: datetime) -> bool:
    """Check if review is within the time window"""
    return normalize_datetime(review_date) >= normalize_datetime(cutoff)


def passes_filters(text: str, review_date: datetime, cutoff: datetime) -> bool:
    """
    Returns True if review passes all quality filters:
    - Minimum 10 words (after stripping emojis)
    - English language
    - Within time window
    """
    if not text or not text.strip():
        return False
    if count_words(text) < MIN_WORD_COUNT:
        return False
    if not is_within_window(review_date, cutoff):
        return False
    if not is_english(text):
        return False
    return True