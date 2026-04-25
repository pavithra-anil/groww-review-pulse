from dataclasses import dataclass
from datetime import datetime


@dataclass
class RawReview:
    id: str              # sha1(source + external_id)
    product: str         # e.g. "groww"
    source: str          # "playstore" or "appstore"
    rating: int          # 1-5
    title: str
    body: str            # original text
    body_clean: str      # PII-scrubbed text
    word_count: int      # word count of body_clean
    review_date: datetime

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product": self.product,
            "source": self.source,
            "rating": self.rating,
            "title": self.title,
            "body": self.body,
            "body_clean": self.body_clean,
            "word_count": self.word_count,
            "review_date": self.review_date.isoformat(),
        }