# Phase 4 — Evaluations

## Goal
Prove that the PulseSummary JSON is correctly converted into a formatted Google Docs section and an HTML email that are ready for delivery.

---

## Evaluation 1: Render Command Produces Output Files

**Test:** Run render command and verify all output files are created

**Command:**
```bash
.venv\Scripts\python -m agent render --run-id 44accf94abd53dc0d5d5438f269b7459060f8ba7
```

**Expected output:**
```
📄 Starting render for run 44accf94...

Loading PulseSummary...
✓ Loaded summary for groww week 2026-W17

Rendering Google Docs section...
✓ doc_requests.json saved

Rendering email...
✓ email.html saved
✓ email.txt saved

✅ Render complete!
   Artifacts saved to data/artifacts/44accf94.../
```

**Pass criteria:** All 3 files created — `doc_requests.json`, `email.html`, `email.txt`

---

## Evaluation 2: Doc Requests JSON is Valid

**Test:** Verify doc_requests.json has correct Google Docs batchUpdate format

**Check:**
```bash
.venv\Scripts\python -c "
import json
with open('data/artifacts/44accf94abd53dc0d5d5438f269b7459060f8ba7/doc_requests.json') as f:
    data = json.load(f)

print('Type:', type(data))
print('Keys:', list(data.keys()))
print('Requests count:', len(data.get('requests', [])))
print('Anchor present:', any(
    'pulse-groww' in str(r) for r in data.get('requests', [])
))
"
```

**Expected:**
```
Type: <class 'dict'>
Keys: ['requests', 'anchor']
Requests count: 15+
Anchor present: True
```

**Pass criteria:** Valid JSON with requests array and anchor string

---

## Evaluation 3: Anchor is Correct Format

**Test:** Verify anchor follows the pattern `pulse-{product}-{iso_week}`

**Check:**
```bash
.venv\Scripts\python -c "
import json
with open('data/artifacts/44accf94abd53dc0d5d5438f269b7459060f8ba7/doc_requests.json') as f:
    data = json.load(f)
anchor = data.get('anchor', '')
print(f'Anchor: {anchor}')
is_valid = anchor.startswith('pulse-groww-') and 'W' in anchor
print('PASS' if is_valid else 'FAIL')
"
```

**Expected:**
```
Anchor: pulse-groww-2026-W17
PASS
```

**Pass criteria:** Anchor matches pattern `pulse-groww-YYYY-WNN`

---

## Evaluation 4: Email HTML Renders Correctly

**Test:** Open email.html in browser and verify it looks correct

**Steps:**
1. Open `data/artifacts/{run_id}/email.html` in your browser
2. Verify it shows:
   - Subject line with week and top theme
   - Top 3 themes listed as bullets
   - 3 action ideas
   - Placeholder `{DOC_DEEP_LINK}` visible (filled in Phase 5)
   - Disclaimer at bottom

**Pass criteria:** Email looks clean and professional in browser

---

## Evaluation 5: Plain Text Email has No HTML Tags

**Test:** Verify email.txt contains no HTML

**Check:**
```bash
.venv\Scripts\python -c "
with open('data/artifacts/44accf94abd53dc0d5d5438f269b7459060f8ba7/email.txt') as f:
    content = f.read()
has_html = '<' in content and '>' in content
print('HTML tags found:', has_html)
print('PASS' if not has_html else 'FAIL')
print()
print('Preview:')
print(content[:500])
"
```

**Pass criteria:** No HTML tags in plain text version

---

## Evaluation 6: Email Subject is Correct Format

**Test:** Verify email subject follows the required format

**Check:**
```bash
.venv\Scripts\python -c "
with open('data/artifacts/44accf94abd53dc0d5d5438f269b7459060f8ba7/email.txt') as f:
    lines = f.readlines()
subject_line = lines[0] if lines else ''
print(f'Subject: {subject_line}')
is_valid = '[Weekly Pulse]' in subject_line and 'Groww' in subject_line
print('PASS' if is_valid else 'FAIL')
"
```

**Expected:**
```
Subject: [Weekly Pulse] Groww — 2026-W17 — App Performance & Crashes
PASS
```

**Pass criteria:** Subject contains `[Weekly Pulse]`, product name, week, and top theme