import re

# PII patterns to scrub
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_PATTERN = re.compile(r'\b[6-9]\d{9}\b')
AADHAAR_PATTERN = re.compile(r'\b\d{4}\s?\d{4}\s?\d{4}\b')
PAN_PATTERN = re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b')


def scrub_pii(text: str) -> str:
    """Remove PII from review text before storage and LLM calls"""
    if not text:
        return text
    text = EMAIL_PATTERN.sub("[email]", text)
    text = PHONE_PATTERN.sub("[phone]", text)
    text = AADHAAR_PATTERN.sub("[id]", text)
    text = PAN_PATTERN.sub("[pan]", text)
    return text