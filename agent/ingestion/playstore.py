import hashlib
import time
import json
import os
from datetime import datetime, timezone
from agent.ingestion.models import RawReview
from agent.ingestion.pii import scrub_pii
from agent.ingestion.filters import passes_filters, count_words, normalize_datetime

MAX_REVIEWS = 500
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2


def fetch_playstore_reviews(
    product: str,
    app_id: str,
    cutoff: datetime,
    run_id: str,
    max_reviews: int = MAX_REVIEWS,
) -> list[RawReview]:
    """
    Fetch reviews from Google Play Store.
    Returns filtered, PII-scrubbed reviews within the time window.
    """
    from google_play_scraper import reviews, Sort

    print(f"  Fetching Play Store reviews for {app_id}...")

    all_reviews = []
    continuation_token = None

    # Normalize cutoff to naive UTC for comparison
    cutoff_naive = normalize_datetime(cutoff)

    while len(all_reviews) < max_reviews:
        result = None
        for attempt in range(RETRY_ATTEMPTS):
            try:
                result, continuation_token = reviews(
                    app_id,
                    lang="en",
                    country="in",
                    sort=Sort.NEWEST,
                    count=200,
                    continuation_token=continuation_token,
                )
                break
            except Exception as e:
                if attempt < RETRY_ATTEMPTS - 1:
                    print(f"  Retry {attempt + 1}/{RETRY_ATTEMPTS} after error: {e}")
                    time.sleep(RETRY_DELAY * (2 ** attempt))
                else:
                    raise RuntimeError(
                        f"Play Store blocked after {RETRY_ATTEMPTS} attempts. "
                        f"Error: {e}"
                    )

        if not result:
            break

        reached_cutoff = False
        for r in result:
            review_date = r.get("at")

            # Normalize review date to naive UTC
            if isinstance(review_date, datetime):
                review_date_naive = normalize_datetime(review_date)
            else:
                continue

            # Stop if we've gone past our time window
            if review_date_naive < cutoff_naive:
                reached_cutoff = True
                break

            body = r.get("content", "") or ""
            if not body.strip():
                continue

            # Check word count and language
            if not passes_filters(body, review_date, cutoff):
                continue

            body_clean = scrub_pii(body)
            if count_words(body_clean) < 10:
                continue

            external_id = r.get("reviewId", "")
            review_id = hashlib.sha1(
                f"playstore:{external_id}".encode()
            ).hexdigest()

            all_reviews.append(RawReview(
                id=review_id,
                product=product,
                source="playstore",
                rating=r.get("score", 0),
                title=r.get("reviewCreatedVersion", "") or "",
                body=body,
                body_clean=body_clean,
                word_count=count_words(body_clean),
                review_date=review_date,
            ))

            if len(all_reviews) >= max_reviews:
                break

        if reached_cutoff or len(all_reviews) >= max_reviews:
            break

        if not continuation_token:
            break

        time.sleep(1)

    # Save raw snapshot
    _save_raw_snapshot(all_reviews, product, run_id, "playstore")

    print(f"  ✓ {len(all_reviews)} Play Store reviews fetched")
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