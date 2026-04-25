# Phase 0 — Edge Cases

## Goal
Document all the things that could go wrong during foundation setup and how we handle them.

---

## Edge Case 1: Missing .env File

**Scenario:** Developer runs the CLI without creating a `.env` file

**Risk:** App crashes with cryptic `KeyError` or `None` value errors

**Handling:**
- `config.py` uses `pydantic-settings` which shows a clear error listing which variables are missing
- `.env.example` is provided so developers know exactly what to create

**Expected behavior:**
```
Error: Missing required environment variables:
  - GROQ_API_KEY (required for LLM summarization)
Please copy .env.example to .env and fill in the values.
```

---

## Edge Case 2: data/ Folder Doesn't Exist

**Scenario:** Someone clones the repo fresh — `data/` folder is in `.gitignore` so it's missing

**Risk:** Database creation fails with `FileNotFoundError`

**Handling:**
- `storage.py` creates `data/` and `data/raw/groww/` directories automatically before creating the SQLite file
- Uses `os.makedirs(exist_ok=True)` so no error if folder already exists

---

## Edge Case 3: SQLite File Already Exists

**Scenario:** Developer runs `init-db` twice

**Risk:** Error saying "table already exists"

**Handling:**
- All `CREATE TABLE` statements use `CREATE TABLE IF NOT EXISTS`
- Second run is a no-op — no error, no data loss

---

## Edge Case 4: Wrong Python Version

**Scenario:** Developer uses Python 3.9 or 3.10 instead of 3.11

**Risk:** Syntax errors or missing features

**Handling:**
- `.python-version` file pins to `3.11`
- `pyproject.toml` specifies `requires-python = ">=3.11"`
- uv will warn if wrong version is used

---

## Edge Case 5: products.yaml is Missing or Malformed

**Scenario:** products.yaml file is deleted or has invalid YAML

**Risk:** Config loading fails silently or with confusing error

**Handling:**
- `config.py` raises a clear `FileNotFoundError` with message pointing to the missing file
- Pydantic validates the structure so malformed YAML shows field-level errors

---

## Edge Case 6: Disk Full

**Scenario:** SQLite database can't be created because disk is full

**Risk:** Partial database creation, corrupted file

**Handling:**
- SQLite handles this gracefully with an `OperationalError`
- We catch it and print a clear message: "Disk full — cannot create database"
- No partial file left behind

---

## Edge Case 7: Import Errors from Missing Dependencies

**Scenario:** Developer forgot to run `uv sync` or `pip install`

**Risk:** `ModuleNotFoundError` on startup

**Handling:**
- README clearly states setup steps
- `pyproject.toml` lists all dependencies
- Error message points to setup instructions