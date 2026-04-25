# Phase 1 — Evaluations

## Goal
Prove that review ingestion works correctly — fetching reviews from both Play Store and App Store, filtering low quality ones, scrubbing PII, and storing them without duplicates.

---

## Evaluation 1: Play Store Ingestion Returns Reviews

**Test:** Run ingest command and verify Play Store reviews are fetched

**Command:**
```bash
python -m agent ingest --product groww --weeks 10
```

**Expected output:**
```
Fetching Play Store reviews for com.nextbillion.groww...
✓ Fetched 300 reviews from Play Store
Fetching App Store reviews for 1413512952...
✓ Fetched 100 reviews from App Store
Applying filters...
✓ 280 reviews passed filters (removed 120 short/non-english)
Storing reviews...
✓ 280 reviews stored in database
Run ID: 44accf94abd53dc0d5d5438f269b7459060f8ba7
```

**Pass criteria:** At least 50 reviews fetched and stored

---

## Evaluation 2: Short Reviews are Filtered Out

**Test:** Verify reviews with less than 10 words are excluded

**Check:**
```bash
.venv\Scripts\python -c "
import sqlite3
conn = sqlite3.connect('data/pulse.sqlite')
short = conn.execute('SELECT COUNT(*) FROM reviews WHERE word_count < 10').fetchone()[0]
print(f'Reviews with < 10 words in DB: {short}')
print('PASS' if short == 0 else 'FAIL')
"
```

**Expected output:**
```
Reviews with < 10 words in DB: 0
PASS
```

**Pass criteria:** Zero reviews with less than 10 words stored

---

## Evaluation 3: Non-English Reviews are Filtered Out

**Test:** Verify only English reviews are stored

**Check:**
```bash
.venv\Scripts\python -c "
import sqlite3
conn = sqlite3.connect('data/pulse.sqlite')
reviews = conn.execute('SELECT body FROM reviews LIMIT 5').fetchall()
for r in reviews:
    print(r[0][:100])
"
```

**Expected:** All printed reviews are in English

**Pass criteria:** No Hindi, Tamil, or other language reviews in database

---

## Evaluation 4: PII is Scrubbed

**Test:** Verify emails and phone numbers are removed from review text

**Check:**
```bash
.venv\Scripts\python -c "
import sqlite3, re
conn = sqlite3.connect('data/pulse.sqlite')
reviews = conn.execute('SELECT body_clean FROM reviews').fetchall()
email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
phone_pattern = r'[6-9]\d{9}'
violations = 0
for r in reviews:
    if re.search(email_pattern, r[0] or '') or re.search(phone_pattern, r[0] or ''):
        violations += 1
print(f'PII violations found: {violations}')
print('PASS' if violations == 0 else 'FAIL')
"
```

**Expected output:**
```
PII violations found: 0
PASS
```

**Pass criteria:** Zero PII patterns in body_clean field

---

## Evaluation 5: No Duplicate Reviews

**Test:** Run ingest twice and verify no duplicates are created

**Commands:**
```bash
python -m agent ingest --product groww --weeks 10
python -m agent ingest --product groww --weeks 10
```

**Check count before and after second run:**
```bash
.venv\Scripts\python -c "
import sqlite3
conn = sqlite3.connect('data/pulse.sqlite')
count = conn.execute('SELECT COUNT(*) FROM reviews').fetchone()[0]
print(f'Total reviews: {count}')
"
```

**Expected:** Same count both times — second run is a no-op

**Pass criteria:** Review count does not increase on second run

---

## Evaluation 6: Raw Snapshot Saved

**Test:** Verify raw JSON snapshot is saved to disk for audit

**Check:**
```bash
dir data\raw\groww\
```

**Expected:** At least one `.jsonl` file present

**Pass criteria:** Raw snapshot file exists in `data/raw/groww/`

---

## Evaluation 7: Reviews Within Time Window

**Test:** Verify all stored reviews are within the last 10 weeks

**Check:**
```bash
.venv\Scripts\python -c "
import sqlite3
from datetime import datetime, timedelta
conn = sqlite3.connect('data/pulse.sqlite')
cutoff = (datetime.now() - timedelta(weeks=10)).strftime('%Y-%m-%d')
old = conn.execute('SELECT COUNT(*) FROM reviews WHERE review_date < ?', (cutoff,)).fetchone()[0]
print(f'Reviews older than 10 weeks: {old}')
print('PASS' if old == 0 else 'FAIL')
"
```

**Pass criteria:** Zero reviews older than the configured time window