# Phase 0 — Evaluations

## Goal
Prove that the project foundation is correctly set up — folder structure, database, config loading, and CLI all work before any business logic is added.

---

## Evaluation 1: CLI Help Works

**Test:** Run the CLI and check all subcommands are listed

**Command:**
```bash
python -m agent --help
```

**Expected output:**
```
Usage: agent [OPTIONS] COMMAND [ARGS]...

  Groww Weekly Review Pulse Agent

Options:
  --help  Show this message and exit.

Commands:
  init-db    Create SQLite database with all tables
  ingest     Fetch and store reviews from Play Store + App Store
  cluster    Cluster reviews into themes
  summarize  Generate LLM summary from clusters
  render     Render report and email artifacts
  publish    Deliver to Google Docs and Gmail via MCP
  run        Run the full pipeline end to end
```

**Pass criteria:** All 7 commands visible, no import errors

---

## Evaluation 2: Database Initialization

**Test:** Run init-db and verify all tables are created

**Command:**
```bash
python -m agent init-db
```

**Expected output:**
```
✓ Database created at data/pulse.sqlite
✓ Table created: products
✓ Table created: reviews
✓ Table created: review_embeddings
✓ Table created: runs
✓ Table created: themes
```

**Verification:**
```bash
python -c "import sqlite3; conn = sqlite3.connect('data/pulse.sqlite'); print([t[0] for t in conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()])"
```

**Expected:** `['products', 'reviews', 'review_embeddings', 'runs', 'themes']`

**Pass criteria:** All 5 tables exist, no errors

---

## Evaluation 3: Config Loading

**Test:** products.yaml loads correctly with Groww config

**Command:**
```bash
python -c "from agent.config import settings; print(settings.products)"
```

**Expected output:**
```
[Product(name='groww', play_store_id='com.nextbillion.groww', app_store_id='1413512952')]
```

**Pass criteria:** Groww product loads with correct store IDs

---

## Evaluation 4: ISO Week Helper

**Test:** time_utils returns correct ISO week for current date

**Command:**
```bash
python -c "from agent.time_utils import current_iso_week, week_date_range; print(current_iso_week()); print(week_date_range(current_iso_week()))"
```

**Expected output:**
```
2026-W17
(datetime(2026, 4, 20), datetime(2026, 4, 26))
```

**Pass criteria:** Correct ISO week string and date range returned

---

## Evaluation 5: Run ID is Deterministic

**Test:** Same product + week always produces same run_id

**Command:**
```bash
python -c "from agent.time_utils import make_run_id; print(make_run_id('groww', '2026-W17')); print(make_run_id('groww', '2026-W17'))"
```

**Expected output:**
```
a3f8c2d1e4b5...  (same hash both times)
a3f8c2d1e4b5...
```

**Pass criteria:** Both prints are identical

---

## Evaluation 6: Re-running init-db is Safe

**Test:** Running init-db twice does not error or wipe existing data

**Commands:**
```bash
python -m agent init-db
python -m agent init-db
```

**Expected:** Second run prints same success message, no errors, no data loss

**Pass criteria:** Idempotent — safe to run multiple times