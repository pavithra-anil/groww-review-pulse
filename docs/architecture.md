# Architecture

## Weekly Product Review Pulse — Groww

---

## 1. System Overview

The system is a modular AI agent pipeline that runs weekly, collecting Groww app reviews, clustering them into themes, generating a one-page insight report, and delivering it via Google Docs and Gmail through MCP servers.

```
┌─────────────────────────────────────────────────────────────────┐
│                        AGENT PIPELINE                           │
│                                                                 │
│  [Play Store]  [App Store]                                      │
│       ↓              ↓                                          │
│    Phase 1: Review Ingestion                                    │
│       ↓                                                         │
│    Phase 2: Filter + Embed + Cluster                            │
│       ↓                                                         │
│    Phase 3: LLM Summarization                                   │
│       ↓                                                         │
│    Phase 4: Report + Email Rendering                            │
│       ↓                                                         │
│    Phase 5: Google Docs (via MCP)                               │
│       ↓                                                         │
│    Phase 6: Gmail (via MCP)                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Module Breakdown

### 2.1 Ingestion (`agent/ingestion/`)

**What it does:**
Fetches reviews from Play Store and App Store for the last 8–12 weeks.

**Why this approach:**
- Play Store: uses `google-play-scraper` library (public, no login needed)
- App Store: uses iTunes RSS feed (public API, no login needed)
- Both sources give us enough reviews to find meaningful patterns

**Key decisions:**
- Reviews are stored with a stable `id = sha1(source + external_id)` so re-running doesn't create duplicates
- Raw JSON snapshots saved to `data/raw/groww/` for audit trail
- PII scrubbing happens here BEFORE any storage

**Filters applied at ingestion:**
- Minimum 10 words in review text (filters "good", "nice", single emojis)
- English language only
- Reviews within the configured time window (8–12 weeks)
- No emoji-only reviews

### 2.2 Storage (`agent/storage.py`)

**What it does:**
Manages a local SQLite database that stores reviews, embeddings, clusters, and run metadata.

**Why SQLite:**
- Zero setup — no separate database server needed
- Portable — entire DB is one file (`data/pulse.sqlite`)
- Sufficient for weekly batch processing (not real-time)

**Tables:**

```
products       — product config (name, play_store_id, app_store_id)
reviews        — raw review text, rating, date, source
review_embeddings — vector representations of each review
runs           — metadata for each weekly run (status, cost, delivery IDs)
themes         — clustered themes with names, quotes, action ideas
```

### 2.3 Clustering (`agent/clustering.py`)

**What it does:**
Groups similar reviews together into themes using embeddings.

**Why this approach:**

Step 1 — **Embeddings**: Convert each review into a vector (list of numbers) that captures its meaning.
- Model: `sentence-transformers/all-MiniLM-L6-v2` (lightweight, local, no API cost)
- Think of it as: "The app crashes" and "App freezes on open" will have similar vectors because they mean similar things

Step 2 — **UMAP**: Reduces high-dimensional vectors to 15 dimensions
- Think of it as: compressing a 384-number description into a 15-number one while keeping the meaning

Step 3 — **HDBSCAN**: Groups nearby vectors into clusters
- Think of it as: finding natural "neighborhoods" in the compressed space
- Reviews that don't fit any cluster go to "noise" (discarded)

**Output:** Up to 5 clusters, each with:
- A list of review IDs belonging to it
- The most representative review (medoid)
- Key phrases describing the cluster

### 2.4 Summarization (`agent/summarization.py`)

**What it does:**
Uses an LLM to convert clusters into human-readable themes, quotes, and action ideas.

**Why Groq/Llama:**
- Free API tier available
- Fast inference
- Already used in LIP 2 project

**Key safety rule — Quote Validation:**
Every quote the LLM returns MUST be a verbatim substring of an actual review. If the LLM makes up a quote, we detect it and re-prompt once. This prevents hallucination.

**Output:** `PulseSummary` JSON containing:
```json
{
  "product": "groww",
  "week": "2026-W17",
  "themes": [
    {
      "name": "App Performance & Bugs",
      "review_count": 142,
      "quotes": ["The app freezes exactly when the market opens"],
      "action_idea": "Scale infra during market hours"
    }
  ]
}
```

### 2.5 Renderer (`agent/renderer/`)

**What it does:**
Converts `PulseSummary` JSON into:
1. A Google Docs batch update request tree (structured JSON for the Docs API)
2. An HTML + plain text email body

**Why separate rendering from delivery:**
> Rendering is pure logic (no network calls). Delivery is external (MCP calls). Keeping them separate means we can test rendering without needing Google credentials.

**Anchor system:**
Each weekly section gets a unique anchor: `pulse-groww-2026-W17`
This anchor is used to:
- Check if a section already exists (idempotency)
- Create a deep link in the email

### 2.6 MCP Client (`agent/mcp_client/`)

**What it does:**
Connects to the MCP server and calls its tools to write to Google Docs and send Gmail.

**Why MCP instead of direct Google API calls:**
> MCP acts as a secure middleman. Google credentials live in the MCP server, not in our code. Our agent just says "append this to the doc" and the MCP server handles authentication.

**MCP Server used:** `https://saksham-mcp-server.onrender.com/`

**Tools called:**
- `docs.get_document` — check if section already exists
- `docs.batch_update` — append new weekly section
- `gmail.create_draft` — create email draft
- `gmail.send_message` — send the email

---

## 3. Data Flow

```
Week starts (Monday 7 AM IST)
        ↓
Generate run_id = sha1("groww" + "2026-W17")
        ↓
Fetch reviews from Play Store + App Store (last 10 weeks)
        ↓
Filter: min 10 words, English only, no emoji-only
        ↓
Scrub PII (emails, phone numbers, Aadhaar patterns)
        ↓
Store in SQLite reviews table
        ↓
Generate embeddings for each review
        ↓
UMAP → HDBSCAN → up to 5 clusters
        ↓
LLM: name themes, select quotes, generate action ideas
        ↓
Validate quotes are verbatim from real reviews
        ↓
Render: Doc section JSON + Email HTML
        ↓
MCP → Google Docs: check anchor → append if not exists
        ↓
MCP → Gmail: check run_id header → send if not sent
        ↓
Log delivery IDs to SQLite runs table
```

---

## 4. Idempotency

**Problem:** If the agent runs twice for the same week (e.g. due to a bug), we must not create duplicate Doc sections or send duplicate emails.

**Solution:**
- `run_id = sha1(product + iso_week)` — same week always produces same ID
- Before appending to Docs: check if anchor `pulse-groww-{week}` exists → skip if yes
- Before sending email: search Gmail for `X-Pulse-Run-Id:{run_id}` header → skip if found

---

## 5. PII Scrubbing

Applied at two points:
1. **Before storage** — in ingestion module
2. **Before LLM call** — in summarization module

Patterns scrubbed:
- Email addresses
- Indian phone numbers (10 digits starting with 6-9)
- Aadhaar-like patterns (12 digits)
- PAN card patterns

---

## 6. Project Structure

```
LIP 3/
├── agent/
│   ├── __init__.py
│   ├── __main__.py          ← CLI entry point
│   ├── config.py            ← loads config from products.yaml + .env
│   ├── storage.py           ← SQLite setup and queries
│   ├── time_utils.py        ← ISO week math, IST-aware
│   ├── clustering.py        ← embeddings + UMAP + HDBSCAN
│   ├── summarization.py     ← LLM theme naming + quote selection
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── appstore.py      ← iTunes RSS scraper
│   │   ├── playstore.py     ← google-play-scraper wrapper
│   │   ├── models.py        ← RawReview pydantic model
│   │   ├── filters.py       ← min words, language, PII scrub
│   │   └── pii.py           ← PII regex scrubber
│   ├── renderer/
│   │   ├── __init__.py
│   │   ├── docs_tree.py     ← PulseSummary → Docs batch update JSON
│   │   └── email_html.py    ← PulseSummary → HTML + plain text email
│   └── mcp_client/
│       ├── __init__.py
│       ├── session.py       ← MCP connection management
│       ├── docs_ops.py      ← Google Docs MCP operations
│       └── gmail_ops.py     ← Gmail MCP operations
├── data/
│   ├── raw/groww/           ← raw review snapshots (JSONL)
│   └── pulse.sqlite         ← main database
├── docs/
│   ├── problemStatement.md
│   ├── architecture.md
│   ├── implementationPlan.md
│   └── phases/
│       ├── phase-0-foundations/
│       │   ├── evaluations.md
│       │   └── edge-cases.md
│       ├── phase-1-ingestion/
│       │   ├── evaluations.md
│       │   └── edge-cases.md
│       ├── phase-2-clustering/
│       │   ├── evaluations.md
│       │   └── edge-cases.md
│       ├── phase-3-summarization/
│       │   ├── evaluations.md
│       │   └── edge-cases.md
│       ├── phase-4-renderer/
│       │   ├── evaluations.md
│       │   └── edge-cases.md
│       ├── phase-5-docs-mcp/
│       │   ├── evaluations.md
│       │   └── edge-cases.md
│       └── phase-6-gmail-mcp/
│           ├── evaluations.md
│           └── edge-cases.md
├── tests/
│   └── fixtures/            ← golden test data
├── products.yaml            ← product configuration
├── pyproject.toml           ← project dependencies
├── .env.example             ← environment variables template
└── README.md
```

---

## 7. Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Language | Python 3.11 | Ecosystem for AI/ML |
| Package manager | uv | Fast, modern |
| Database | SQLite | Zero setup, portable |
| Play Store scraping | google-play-scraper | Public, no login |
| App Store scraping | iTunes RSS API | Public, free |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 | Local, no API cost |
| Dimensionality reduction | UMAP | Best for text clustering |
| Clustering | HDBSCAN | Handles noise well |
| LLM | Groq/Llama 3.1 | Free tier, fast |
| Data validation | Pydantic | Type safety |
| CLI | Typer | Simple, clean |
| Templating | Jinja2 | HTML email rendering |
| MCP delivery | saksham-mcp-server | Google Docs + Gmail |

---

## 8. Key Design Principles

1. **MCP boundary is sacred** — Google Docs and Gmail are ONLY accessed via MCP. No direct API calls.
2. **Idempotency from day one** — same week = same run_id = no duplicates
3. **PII scrubbing at two layers** — before storage AND before LLM
4. **Quote validation** — LLM quotes must exist verbatim in real reviews
5. **Modular phases** — each phase is independently testable
6. **Fail loud** — errors are raised clearly, never silently swallowed