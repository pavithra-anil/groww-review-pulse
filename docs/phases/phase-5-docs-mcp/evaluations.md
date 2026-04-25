# Phase 5 — Evaluations (Google Docs MCP)

## Goal
Prove that the weekly report is correctly appended to Google Docs via the MCP server, and that re-running the same week does not create duplicates.

---

## Evaluation 1: Report Appended to Google Doc

**Test:** Run publish docs command and verify report appears in Google Doc

**Command:**
```bash
.venv\Scripts\python -m agent publish --run-id 44accf94abd53dc0d5d5438f269b7459060f8ba7 --target docs
```

**Expected output:**
```
📤 Publishing to Google Docs...
  ✓ Connected to MCP server
  ✓ Report appended to Google Doc
  ✓ Doc ID: 1Bgg7uJqsyziZyBVku-iTf1IIXICLE192F8cB7Z5mUqc
✅ Google Docs delivery complete!
```

**Manual verification:** Open the Google Doc and verify new section appears with:
- Heading: "Groww Weekly Review Pulse — 2026-W17"
- Top 3 themes listed
- Real user quotes
- Action ideas

**Pass criteria:** Section visible in Google Doc

---

## Evaluation 2: Idempotency — No Duplicate Sections

**Test:** Run publish docs command twice for same run_id

**Commands:**
```bash
.venv\Scripts\python -m agent publish --run-id 44accf94abd53dc0d5d5438f269b7459060f8ba7 --target docs
.venv\Scripts\python -m agent publish --run-id 44accf94abd53dc0d5d5438f269b7459060f8ba7 --target docs
```

**Expected output on second run:**
```
📤 Publishing to Google Docs...
  ✓ Section already exists for 2026-W17 — skipping
✅ Already published, no duplicate created
```

**Pass criteria:** Google Doc has only ONE section for 2026-W17

---

## Evaluation 3: MCP Server Connection Works

**Test:** Verify agent can connect to MCP server

**Check:**
```bash
.venv\Scripts\python -c "
import requests, os
from dotenv import load_dotenv
load_dotenv()
url = os.getenv('MCP_SERVER_URL')
response = requests.get(f'{url}/')
print(f'Status: {response.status_code}')
print(f'Response: {response.json()}')
"
```

**Expected:**
```
Status: 200
Response: {'message': 'Google MCP Server is running'}
```

**Pass criteria:** 200 response from MCP server

---

## Evaluation 4: Run Status Updated

**Test:** Verify runs table is updated after successful publish

**Check:**
```bash
.venv\Scripts\python -c "
import sqlite3
conn = sqlite3.connect('data/pulse.sqlite')
run = conn.execute(
    'SELECT status, gdoc_id FROM runs WHERE id = ?',
    ('44accf94abd53dc0d5d5438f269b7459060f8ba7',)
).fetchone()
print(f'Status: {run[0]}')
print(f'Doc ID: {run[1]}')
"
```

**Pass criteria:** Status is "published_docs" and gdoc_id is set