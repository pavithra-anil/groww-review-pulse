# Phase 7 — Evaluations (Orchestration, Scheduling & Hardening)

## Goal
Prove that the full pipeline runs weekly, unattended, with proper scheduling, and handles failures gracefully.

---

## Evaluation 1: Full Pipeline Runs with One Command

**Test:** Run the complete pipeline end to end

**Command:**
```bash
python -m agent run --product groww --weeks 10
```

**Expected output:**
```
🚀 Running full pipeline for groww — 2026-W17
✅ Phase 1: 619 reviews ingested
✅ Phase 2: Clustering complete
✅ Phase 3: Summarization complete
✅ Phase 4: Render complete
✅ Phase 5: Google Docs complete
✅ Phase 6: Gmail complete
🎉 Full pipeline complete for groww — 2026-W17!
```

**Pass criteria:** All 6 phases complete without errors

---

## Evaluation 2: Backfill Works for Past Weeks

**Test:** Run pipeline for a specific past week

**Command:**
```bash
python -m agent run --product groww --week 2026-W16
```

**Expected:** Pipeline runs for week 16, creates separate run_id from week 17

**Pass criteria:** Different run_id, no conflicts with current week data

---

## Evaluation 3: Re-running Same Week is Safe

**Test:** Run pipeline twice for same week

**Commands:**
```bash
python -m agent run --product groww --weeks 10
python -m agent run --product groww --weeks 10
```

**Expected:** Second run completes without errors, no duplicate Doc sections, no duplicate Gmail drafts

**Pass criteria:** Google Doc has exactly one section for the week

---

## Evaluation 4: GitHub Actions Workflow is Valid

**Test:** Verify workflow file syntax is correct

**Check:**
```bash
cat .github/workflows/weekly-pulse.yml
```

**Expected:** Valid YAML with cron schedule, correct commands

**Pass criteria:** Workflow file exists and has correct structure

---

## Evaluation 5: Run Status Tracked in Database

**Test:** Verify run metadata is saved after pipeline completes

**Check:**
```bash
.venv\Scripts\python -c "
import sqlite3
conn = sqlite3.connect('data/pulse.sqlite')
runs = conn.execute('SELECT id, product, iso_week, status, reviews_count, clusters_count FROM runs').fetchall()
for r in runs:
    print(f'Run: {r[0][:8]}... | {r[1]} | {r[2]} | {r[3]} | {r[4]} reviews | {r[5]} clusters')
"
```

**Pass criteria:** All runs have status "published" and non-zero review/cluster counts