# Phase 6 — Evaluations (Gmail MCP)

## Goal
Prove that the stakeholder email is correctly created as a draft in Gmail via MCP, and that re-running does not create duplicate emails.

---

## Evaluation 1: Email Draft Created in Gmail

**Test:** Run publish gmail command and verify draft appears in Gmail

**Command:**
```bash
.venv\Scripts\python -m agent publish --run-id 44accf94abd53dc0d5d5438f269b7459060f8ba7 --target gmail
```

**Expected output:**
```
📧 Publishing to Gmail...
  ✓ Connected to MCP server
  ✓ Email draft created in Gmail
  Subject: [Weekly Pulse] Groww — 2026-W17 — App Performance & Crashes
✅ Gmail delivery complete!
```

**Manual verification:** Open Gmail → Drafts → verify email draft exists with:
- Correct subject line
- Top 3 themes in body
- "Read Full Report" link

**Pass criteria:** Draft visible in Gmail Drafts folder

---

## Evaluation 2: Idempotency — No Duplicate Emails

**Test:** Run publish gmail command twice

**Commands:**
```bash
.venv\Scripts\python -m agent publish --run-id 44accf94abd53dc0d5d5438f269b7459060f8ba7 --target gmail
.venv\Scripts\python -m agent publish --run-id 44accf94abd53dc0d5d5438f269b7459060f8ba7 --target gmail
```

**Expected output on second run:**
```
📧 Publishing to Gmail...
  ✓ Email already sent for this run — skipping
✅ Already published, no duplicate created
```

**Pass criteria:** Only ONE draft in Gmail for this week

---

## Evaluation 3: Email Content is Correct

**Manual check:** Open the Gmail draft and verify:
- Subject: `[Weekly Pulse] Groww — 2026-W17 — App Performance & Crashes`
- Body contains top 3 themes
- Body contains 3 action ideas
- No PII in email body
- Disclaimer at bottom

**Pass criteria:** All content checks pass

---

## Evaluation 4: Run Status Updated

**Check:**
```bash
.venv\Scripts\python -c "
import sqlite3
conn = sqlite3.connect('data/pulse.sqlite')
run = conn.execute(
    'SELECT status, gmail_message_id FROM runs WHERE id = ?',
    ('44accf94abd53dc0d5d5438f269b7459060f8ba7',)
).fetchone()
print(f'Status: {run[0]}')
print(f'Gmail Message ID: {run[1]}')
"
```

**Pass criteria:** Status is "published" and gmail_message_id is set