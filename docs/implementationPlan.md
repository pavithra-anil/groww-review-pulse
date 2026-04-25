# Implementation Plan

## Weekly Product Review Pulse — Groww

---

## Overview

The build is split into 6 phases. Each phase produces something independently testable and runnable via the CLI. Phases 1–4 are pure local code. Phases 5–6 introduce MCP calls for Google Workspace delivery.

**Guiding Principles:**
1. **One thing at a time** — each phase has a single clear goal
2. **Test before moving on** — every phase has exit criteria that must pass
3. **MCP boundary is sacred** — Google Docs and Gmail only touched in Phase 5 and 6
4. **No silent failures** — every error must be visible and clear

---

## Phase Summary

| Phase | Name | Key Deliverable |
|-------|------|----------------|
| 0 | Foundations & Scaffolding | Project structure, DB schema, CLI skeleton |
| 1 | Review Ingestion | Fetch and store Groww reviews from Play Store + App Store |
| 2 | Filtering, Embedding & Clustering | Group reviews into up to 5 themes |
| 3 | LLM Summarization | Named themes, validated quotes, action ideas |
| 4 | Report & Email Rendering | One-page pulse doc + email HTML on disk |
| 5 | MCP Delivery | Append to Google Docs + Send Gmail via MCP |

---

## Phase 0 — Foundations & Scaffolding

### Goal
Set up everything except business logic. Any later phase should only need to add files.

### Why this phase exists
> Before building walls, you lay the foundation. Phase 0 creates the project skeleton — folder structure, database, config loading, and CLI — so every future phase just adds to it without fighting the setup.

### What we build

**Project structure:**
```
agent/
├── __init__.py
├── __main__.py       ← CLI with subcommands: ingest, cluster, summarize, render, publish
├── config.py         ← loads products.yaml and .env
├── storage.py        ← creates SQLite tables
└── time_utils.py     ← ISO week math, IST timezone helpers
```

**SQLite tables:**
- `products` — product name, Play Store ID, App Store ID
- `reviews` — review text, rating, date, source, PII-scrubbed body
- `review_embeddings` — vector for each review
- `runs` — weekly run metadata (status, cost, delivery IDs)
- `themes` — clustered themes with names, quotes, actions

**Config files:**
- `products.yaml` — list of products and their store IDs
- `.env` — API keys (GROQ_API_KEY, etc.)
- `.env.example` — template showing what keys are needed

### Exit Criteria
- [ ] `python -m agent --help` prints all subcommands
- [ ] `python -m agent init-db` creates SQLite file with all tables
- [ ] `products.yaml` loads correctly with Groww config

### Files created this phase
- `agent/__init__.py`
- `agent/__main__.py`
- `agent/config.py`
- `agent/storage.py`
- `agent/time_utils.py`
- `products.yaml`
- `.env.example`
- `docs/phases/phase-0-foundations/evaluations.md`
- `docs/phases/phase-0-foundations/edge-cases.md`

---

## Phase 1 — Review Ingestion

### Goal
Reliably fetch and store 8–12 weeks of Groww reviews from both stores.

### Why this phase exists
> We need raw material before we can analyze anything. This phase is our data collection layer — fetching reviews from public sources, cleaning them, and storing them safely.

### What we build

**Play Store ingestion (`agent/ingestion/playstore.py`):**
- Uses `google-play-scraper` library
- Fetches reviews for `com.nextbillion.groww` (Groww's app ID)
- Paginates until we have reviews from the last 10 weeks

**App Store ingestion (`agent/ingestion/appstore.py`):**
- Uses iTunes RSS feed (free public API)
- URL: `https://itunes.apple.com/in/rss/customerreviews/id=1413512952/json`
- Fetches up to 10 pages of reviews

**Filters applied (`agent/ingestion/filters.py`):**
- Minimum 10 words in review body
- English language only (detected via `langdetect`)
- No emoji-only reviews
- Within the configured time window (8–12 weeks)

**PII scrubbing (`agent/ingestion/pii.py`):**
- Emails → `[email]`
- Phone numbers → `[phone]`
- Aadhaar patterns → `[id]`
- Applied BEFORE storing to database

**Review model (`agent/ingestion/models.py`):**
```python
class RawReview:
    id: str           # sha1(source + external_id)
    source: str       # "playstore" or "appstore"
    rating: int       # 1-5
    title: str
    body: str         # original text
    body_clean: str   # PII-scrubbed text
    date: datetime
    word_count: int
```

**CLI command:**
```bash
python -m agent ingest --product groww --weeks 10
```

### Exit Criteria
- [ ] Running ingest for Groww returns ≥ 50 reviews
- [ ] Reviews with < 10 words are excluded
- [ ] Re-running the same command is a no-op (no duplicate inserts)
- [ ] PII patterns are scrubbed from body_clean

### Files created this phase
- `agent/ingestion/__init__.py`
- `agent/ingestion/models.py`
- `agent/ingestion/filters.py`
- `agent/ingestion/pii.py`
- `agent/ingestion/playstore.py`
- `agent/ingestion/appstore.py`
- `docs/phases/phase-1-ingestion/evaluations.md`
- `docs/phases/phase-1-ingestion/edge-cases.md`

---

## Phase 2 — Filtering, Embedding & Clustering

### Goal
Turn a pile of reviews into up to 5 coherent theme clusters.

### Why this phase exists
> Raw reviews are noisy and unstructured. This phase finds the natural patterns — grouping "app crashes", "freezes on login", and "slow loading" into one "Performance" theme automatically, without manual tagging.

### What we build

**Embeddings:**
- Model: `sentence-transformers/all-MiniLM-L6-v2` (local, free)
- Each review body → 384-dimensional vector
- Cached on disk so re-runs don't recompute

**Dimensionality reduction (UMAP):**
- Reduces 384 dimensions → 15 dimensions
- Makes clustering faster and more accurate
- Fixed random seed for deterministic results

**Clustering (HDBSCAN):**
- Groups similar reviews into clusters
- Reviews that don't fit any cluster → noise (discarded)
- Maximum 5 clusters enforced

**Per cluster output:**
- Representative review (medoid — closest to cluster center)
- Top keyphrases (via KeyBERT)
- All review IDs in the cluster

**CLI command:**
```bash
python -m agent cluster --run <run_id>
```

### Exit Criteria
- [ ] On real Groww reviews, produces 3–5 meaningful clusters
- [ ] Noise ratio < 40% (most reviews assigned to a cluster)
- [ ] Same seed → same clusters (deterministic)
- [ ] Clusters saved to SQLite themes table

### Files created this phase
- `agent/clustering.py`
- `docs/phases/phase-2-clustering/evaluations.md`
- `docs/phases/phase-2-clustering/edge-cases.md`

---

## Phase 3 — LLM Summarization

### Goal
Convert numeric clusters into named themes, real quotes, and action ideas using an LLM.

### Why this phase exists
> Clusters are just groups of numbers. This phase gives them meaning — "these 142 reviews are about Performance Issues" — and extracts the most useful quotes and recommendations.

### What we build

**Theme naming:**
- Send cluster keyphrases + representative review to Groq LLM
- LLM returns a short theme name (e.g. "App Performance & Bugs")

**Quote selection:**
- LLM selects 1 verbatim quote per theme
- **Validation:** every quote must be a substring of a real review body
- If LLM hallucinates a quote → re-prompt once → drop if still invalid

**Action ideas:**
- LLM generates 3 action ideas based on top themes
- Kept to 1 sentence each

**PulseSummary output:**
```json
{
  "product": "groww",
  "week": "2026-W17",
  "run_id": "abc123",
  "themes": [
    {
      "rank": 1,
      "name": "App Performance & Bugs",
      "review_count": 142,
      "quote": "The app freezes exactly when the market opens.",
      "action_idea": "Scale infrastructure during market hours"
    }
  ],
  "generated_at": "2026-04-25T07:00:00+05:30"
}
```

**CLI command:**
```bash
python -m agent summarize --run <run_id>
```

### Exit Criteria
- [ ] 3 themes produced with names, quotes, and action ideas
- [ ] All quotes pass verbatim validation
- [ ] PulseSummary JSON saved to `data/summaries/{run_id}.json`
- [ ] LLM cost tracked in runs table

### Files created this phase
- `agent/summarization.py`
- `docs/phases/phase-3-summarization/evaluations.md`
- `docs/phases/phase-3-summarization/edge-cases.md`

---

## Phase 4 — Report & Email Rendering

### Goal
Convert PulseSummary JSON into a formatted Google Docs section and an HTML email.

### Why this phase exists
> The data is ready but needs to be packaged for delivery. This phase is like a printing press — it takes our structured data and formats it into the final documents that humans will read.

### What we build

**Google Docs renderer (`agent/renderer/docs_tree.py`):**
- Converts PulseSummary → list of Google Docs batchUpdate requests
- Includes: Heading 1 (week label), theme sections, quotes in italics, action ideas as bullets
- Embeds anchor: `pulse-groww-2026-W17` in the heading for idempotency

**Email renderer (`agent/renderer/email_html.py`):**
- Jinja2 template → HTML email + plain text version
- Subject: `[Weekly Pulse] Groww — 2026-W17 — App Performance & Bugs`
- Includes placeholder `{DOC_DEEP_LINK}` filled in Phase 5

**Output files saved to disk:**
```
data/artifacts/{run_id}/
├── doc_requests.json    ← Google Docs batch update payload
├── email.html           ← HTML email body
└── email.txt            ← Plain text email body
```

**CLI command:**
```bash
python -m agent render --run <run_id>
```

### Exit Criteria
- [ ] `doc_requests.json` is valid Google Docs batchUpdate format
- [ ] `email.html` renders correctly in a browser
- [ ] Anchor `pulse-groww-{week}` present in doc requests
- [ ] Plain text version has no HTML tags

### Files created this phase
- `agent/renderer/__init__.py`
- `agent/renderer/docs_tree.py`
- `agent/renderer/email_html.py`
- `templates/email.html.j2`
- `docs/phases/phase-4-renderer/evaluations.md`
- `docs/phases/phase-4-renderer/edge-cases.md`

---

## Phase 5 & 6 — MCP Delivery

### Goal
Deliver the report to Google Docs and send the stakeholder email via MCP server.

### Why MCP exists
> Instead of putting Google credentials in our code (security risk), we use an MCP server as a trusted middleman. Our agent says "write this to Docs" and the MCP server handles authentication securely.

### MCP Server
URL: `https://saksham-mcp-server.onrender.com/`

### Setup steps (one-time):
1. Clone MCP server repo
2. Generate `credentials.json` from Google Cloud Console
3. Run locally to get `token.json`
4. Add both to Render environment
5. Deploy MCP server on Render

### Phase 5 — Google Docs

**What it does:**
1. Checks if anchor `pulse-groww-{week}` already exists in the Doc → skip if yes
2. Appends the new weekly section using `docs.batch_update`
3. Retrieves the heading ID for the deep link
4. Saves `gdoc_heading_id` to runs table

**CLI command:**
```bash
python -m agent publish --run <run_id> --target docs
```

### Phase 6 — Gmail

**What it does:**
1. Searches Gmail for `X-Pulse-Run-Id:{run_id}` → skip if found
2. Creates email draft with deep link from Phase 5
3. Sends email (only if `CONFIRM_SEND=true` in .env)
4. Saves `gmail_message_id` to runs table

**CLI command:**
```bash
python -m agent publish --run <run_id> --target gmail
python -m agent publish --run <run_id> --target both
```

### Exit Criteria
- [ ] Report appears as new section in Google Doc
- [ ] Re-running same week → no duplicate section
- [ ] Email arrives in inbox with working deep link
- [ ] Re-running same week → no duplicate email

### Files created this phase
- `agent/mcp_client/__init__.py`
- `agent/mcp_client/session.py`
- `agent/mcp_client/docs_ops.py`
- `agent/mcp_client/gmail_ops.py`
- `docs/phases/phase-5-docs-mcp/evaluations.md`
- `docs/phases/phase-5-docs-mcp/edge-cases.md`
- `docs/phases/phase-6-gmail-mcp/evaluations.md`
- `docs/phases/phase-6-gmail-mcp/edge-cases.md`

---

## Full Pipeline Command

Once all phases are complete, the entire pipeline runs with one command:

```bash
python -m agent run --product groww --weeks 10
```

This chains all phases automatically:
`ingest → cluster → summarize → render → publish`

---

## Dependencies

```toml
[project]
dependencies = [
    "typer",                          # CLI
    "pydantic",                       # data validation
    "pydantic-settings",              # config from .env
    "python-dotenv",                  # .env loading
    "google-play-scraper",            # Play Store reviews
    "requests",                       # App Store RSS fetch
    "langdetect",                     # language detection
    "sentence-transformers",          # embeddings
    "umap-learn",                     # dimensionality reduction
    "hdbscan",                        # clustering
    "keybert",                        # keyphrases
    "groq",                           # LLM API
    "jinja2",                         # email templating
    "mcp",                            # MCP client
    "structlog",                      # structured logging
]
```