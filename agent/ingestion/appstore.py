import hashlib
import time
import json
import os
import requests
from datetime import datetime
from agent.ingestion.models import RawReview
from agent.ingestion.pii import scrub_pii
from agent.ingestion.filters import passes_filters, count_words

MAX_REVIEWS = 500
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2
MAX_PAGES = 10


def fetch_appstore_reviews(
    product: str,
    app_id: str,
    country: str,
    cutoff: datetime,
    run_id: str,
    max_reviews: int = MAX_REVIEWS,
) -> list[RawReview]:
    """
    Fetch reviews from Apple App Store via iTunes RSS feed.
    Returns filtered, PII-scrubbed reviews within the time window.
    """
    print(f"  Fetching App Store reviews for {app_id}...")

    all_reviews = []

    for page in range(1, MAX_PAGES + 1):
        url = (
            f"https://itunes.apple.com/{country}/rss/customerreviews/"
            f"page={page}/id={app_id}/sortby=mostrecent/json"
        )

        data = None
        for attempt in range(RETRY_ATTEMPTS):
            try:
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    break
                else:
                    time.sleep(RETRY_DELAY * (2 ** attempt))
            except Exception as e:
                if attempt < RETRY_ATTEMPTS - 1:
                    print(f"  Retry {attempt + 1}/{RETRY_ATTEMPTS}: {e}")
                    time.sleep(RETRY_DELAY * (2 ** attempt))
                else:
                    print(f"  ⚠ App Store unavailable after {RETRY_ATTEMPTS} attempts")
                    return all_reviews

        if not data:
            break

        entries = data.get("feed", {}).get("entry", [])
        if not entries:
            break

        # Skip first entry — it's app metadata not a review
        if page == 1 and entries:
            entries = entries[1:]

        reached_cutoff = False
        for entry in entries:
            # Parse date
            date_str = entry.get("updated", {}).get("label", "")
            review_date = None
            try:
                review_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
            except Exception:
                try:
                    review_date = datetime.fromisoformat(date_str[:10])
                except Exception:
                    continue

            if review_date is None:
                continue

            body = entry.get("content", {}).get("label", "") or ""
            title = entry.get("title", {}).get("label", "") or ""

            if not passes_filters(body, review_date, cutoff):
                if review_date < cutoff.replace(tzinfo=None):
                    reached_cutoff = True
                continue

            body_clean = scrub_pii(body)
            if count_words(body_clean) < 10:
                continue

            external_id = entry.get("id", {}).get("label", "")
            review_id = hashlib.sha1(
                f"appstore:{external_id}".encode()
            ).hexdigest()

            rating_str = entry.get("im:rating", {}).get("label", "0")
            try:
                rating = int(rating_str)
            except ValueError:
                rating = 0

            all_reviews.append(RawReview(
                id=review_id,
                product=product,
                source="appstore",
                rating=rating,
                title=title,
                body=body,
                body_clean=body_clean,
                word_count=count_words(body_clean),
                review_date=review_date,
            ))

            if len(all_reviews) >= max_reviews:
                break

        if reached_cutoff or len(all_reviews) >= max_reviews:
            break

        time.sleep(1)

    # Save raw snapshot
    _save_raw_snapshot(all_reviews, product, run_id, "appstore")

    print(f"  ✓ {len(all_reviews)} App Store reviews fetched")
    return all_reviews


def _save_raw_snapshot(
    reviews: list[RawReview],
    product: str,
    run_id: str,
    source: str,
):
    """Save raw reviews to disk for audit trail"""
    os.makedirs(f"data/raw/{product}", exist_ok=True)
    path = f"data/raw/{product}/{run_id}_{source}.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for r in reviews:
            f.write(json.dumps(r.to_dict()) + "\n")