# Phase 3 — Evaluations

## Goal
Prove that the LLM correctly names themes, selects real verbatim quotes, and generates useful action ideas.

---

## Evaluation 1: Summarization Produces 3 Named Themes

**Test:** Run summarize command and verify themes get proper names

**Command:**
```bash
.venv\Scripts\python -m agent summarize --run-id 44accf94abd53dc0d5d5438f269b7459060f8ba7
```

**Expected output:**
```
🧠 Starting summarization for run 44accf94...

Naming themes...
  Theme 1 (113 reviews): "App Performance & Notification Issues"
  Theme 2 (66 reviews): "Positive User Experience"
  Theme 3 (58 reviews): "Trading Features & Charts"
  Theme 4 (55 reviews): "Charges & Brokerage Complaints"
  Theme 5 (49 reviews): "TradingView Integration"

Selecting quotes...
  ✓ Quote validated for Theme 1
  ✓ Quote validated for Theme 2
  ✓ Quote validated for Theme 3

Generating action ideas...
  ✓ 3 action ideas generated

✅ Summarization complete!
   PulseSummary saved to data/summaries/44accf94.json
```

**Pass criteria:** At least 3 themes named, quotes selected, action ideas generated

---

## Evaluation 2: All Quotes are Verbatim

**Test:** Verify every quote exists in actual review text

**Check:**
```bash
.venv\Scripts\python -c "
import json, sqlite3
with open('data/summaries/44accf94abd53dc0d5d5438f269b7459060f8ba7.json') as f:
    summary = json.load(f)

conn = sqlite3.connect('data/pulse.sqlite')
all_bodies = [r[0] for r in conn.execute('SELECT body_clean FROM reviews').fetchall()]

for theme in summary['themes']:
    quote = theme.get('quote', '')
    found = any(quote.lower() in body.lower() for body in all_bodies if body)
    status = 'PASS' if found else 'FAIL'
    print(f'{status}: {theme[\"name\"]} — \"{quote[:60]}...\"')
"
```

**Expected:** All themes show PASS

**Pass criteria:** Every quote is a substring of a real review

---

## Evaluation 3: PulseSummary JSON is Valid

**Test:** Verify the output JSON has correct structure

**Check:**
```bash
.venv\Scripts\python -c "
import json
with open('data/summaries/44accf94abd53dc0d5d5438f269b7459060f8ba7.json') as f:
    summary = json.load(f)

print('product:', summary.get('product'))
print('week:', summary.get('week'))
print('themes count:', len(summary.get('themes', [])))
print('action ideas count:', len(summary.get('action_ideas', [])))

for t in summary['themes'][:3]:
    print(f'  - {t[\"name\"]} ({t[\"review_count\"]} reviews)')
    print(f'    Quote: {t[\"quote\"][:80]}...')

for i, a in enumerate(summary.get('action_ideas', []), 1):
    print(f'  Action {i}: {a[:80]}')
"
```

**Pass criteria:**
- `product` = "groww"
- `week` = current ISO week
- At least 3 themes
- Exactly 3 action ideas

---

## Evaluation 4: Theme Names are Meaningful

**Test:** Verify theme names are descriptive (not "Theme 1", "Theme 2")

**Check:**
```bash
.venv\Scripts\python -c "
import json
with open('data/summaries/44accf94abd53dc0d5d5438f269b7459060f8ba7.json') as f:
    summary = json.load(f)

for theme in summary['themes']:
    name = theme['name']
    is_generic = name.lower().startswith('theme ')
    status = 'FAIL' if is_generic else 'PASS'
    print(f'{status}: {name}')
"
```

**Pass criteria:** No theme named "Theme N" — all have descriptive names

---

## Evaluation 5: Action Ideas are Actionable

**Test:** Verify action ideas are specific and actionable (not generic)

**Manual check:** Open `data/summaries/{run_id}.json` and verify:
- Each action idea mentions a specific feature or improvement
- Ideas are 1-2 sentences max
- Ideas are relevant to the themes found

**Pass criteria:** 3 action ideas that a PM could actually implement