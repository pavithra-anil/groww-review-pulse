# 📊 Groww Review Pulse

> An AI agent that transforms 8–12 weeks of Groww app store reviews into a weekly one-page insight report — automatically delivered to Google Docs and Gmail via MCP.

Built for the **NextLeap LIP Challenge — Milestone 3**

---

## 🎯 What It Does

Every week, Groww receives thousands of user reviews on Play Store and App Store. This agent:

1. **Scrapes** reviews from Play Store + App Store automatically
2. **Clusters** them into up to 5 meaningful themes using embeddings + HDBSCAN
3. **Summarizes** each theme with real user quotes and action ideas using Groq LLM
4. **Delivers** a one-page weekly pulse to Google Docs and Gmail via MCP server

**One command does it all:**
```bash
python -m agent run --product groww --weeks 10
```

---

## 🏗️ Architecture

```
Play Store + App Store
        ↓
Phase 1: Review Ingestion (google-play-scraper + iTunes RSS)
        ↓
Phase 2: Filter + Embed + Cluster (MiniLM + UMAP + HDBSCAN)
        ↓
Phase 3: LLM Summarization (Groq / Llama 3.1)
        ↓
Phase 4: Report + Email Rendering (Jinja2)
        ↓
Phase 5: Google Docs (via MCP server)
        ↓
Phase 6: Gmail Draft (via MCP server)
```

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11 |
| Package manager | uv |
| Database | SQLite |
| Play Store | google-play-scraper |
| App Store | iTunes RSS API |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 |
| Dimensionality reduction | UMAP |
| Clustering | HDBSCAN |
| LLM | Groq (llama-3.1-8b-instant) |
| Templating | Jinja2 |
| MCP Delivery | Custom MCP server (Google Docs + Gmail) |
| CLI | Typer |

---

## 📁 Project Structure

```
groww-review-pulse/
├── agent/
│   ├── __main__.py          ← CLI entry point
│   ├── config.py            ← Configuration loader
│   ├── storage.py           ← SQLite database
│   ├── time_utils.py        ← ISO week helpers
│   ├── clustering.py        ← Embeddings + UMAP + HDBSCAN
│   ├── summarization.py     ← LLM theme naming + quotes
│   ├── ingestion/
│   │   ├── playstore.py     ← Play Store scraper
│   │   ├── appstore.py      ← App Store RSS fetcher
│   │   ├── filters.py       ← Quality filters
│   │   └── pii.py           ← PII scrubber
│   ├── renderer/
│   │   ├── docs_tree.py     ← Google Docs formatter
│   │   └── email_html.py    ← HTML email renderer
│   └── mcp_client/
│       ├── session.py       ← MCP connection
│       ├── docs_ops.py      ← Google Docs operations
│       └── gmail_ops.py     ← Gmail operations
├── docs/
│   ├── architecture.md
│   ├── implementationPlan.md
│   ├── problemStatement.md
│   └── phases/              ← Per-phase evaluations + edge cases
├── data/                    ← Created at runtime (gitignored)
├── products.yaml            ← Product configuration
├── .env.example             ← Environment variables template
└── pyproject.toml
```

---

## 🚀 Setup

### Prerequisites
- Python 3.11+
- uv package manager
- Groq API key
- MCP server deployed (see below)

### 1. Clone and install

```bash
git clone https://github.com/pavithra-anil/groww-review-pulse
cd groww-review-pulse
uv sync
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:
```bash
GROQ_API_KEY=your_groq_api_key
MCP_SERVER_URL=your_mcp_server_url
GOOGLE_DOC_ID=your_google_doc_id
GMAIL_TO=your_email@gmail.com
CONFIRM_SEND=false
```

### 3. Initialize database

```bash
python -m agent init-db
```

### 4. Run the full pipeline

```bash
python -m agent run --product groww --weeks 10
```

---

## 📋 CLI Commands

```bash
# Initialize database
python -m agent init-db

# Run individual phases
python -m agent ingest --product groww --weeks 10
python -m agent cluster --run-id <run_id>
python -m agent summarize --run-id <run_id>
python -m agent render --run-id <run_id>
python -m agent publish --run-id <run_id> --target docs
python -m agent publish --run-id <run_id> --target gmail
python -m agent publish --run-id <run_id> --target both

# Run full pipeline
python -m agent run --product groww --weeks 10
```

---

## 🔄 How to Re-run for a New Week

The pipeline is **idempotent** — re-running the same week never creates duplicates.

To run for the current week:
```bash
python -m agent run --product groww --weeks 10
```

To run for a specific past week:
```bash
python -m agent run --product groww --week 2026-W16
```

Each run gets a unique `run_id = sha1(product + iso_week)` — same week always produces the same ID, preventing duplicate sections in Google Docs or duplicate Gmail drafts.

---

## 🗂️ Theme Legend

Themes are discovered automatically by clustering — they are not predefined. However, based on Groww's review history, common themes include:

| Theme | What it captures |
|---|---|
| App Performance & Crashes | Reports of lag, freezes, crashes during trading hours |
| User Interface & Experience | UI feedback, ease of use, navigation |
| Trading Features | Trading tools, charts, order types, analytics |
| Charges & Fee Complaints | Hidden charges, brokerage fees, unexpected deductions |
| TradingView Integration | Chart integration feedback, technical analysis tools |
| Customer Support | Response time, issue resolution, support quality |
| KYC & Onboarding | Account opening, document verification, first-time setup |

> Note: Actual themes vary each week based on what users are talking about. The LLM names each cluster based on the reviews it contains.

---

## 🔐 MCP Server Setup

This project uses an MCP server for secure Google Workspace delivery.

1. Fork: `https://github.com/saksham20189575/saksham-mcp-server`
2. Set up Google Cloud credentials (Docs API + Gmail API)
3. Run `auth.py` locally to generate `token.json`
4. Deploy on Render with `GOOGLE_TOKEN_JSON` environment variable
5. Update `MCP_SERVER_URL` in your `.env`

---

## 📊 Sample Output

**Week: 2026-W17 | Reviews analyzed: 632**

**Top Themes:**
1. App Performance & Crashes (110 reviews)
   > "worst work stoploss doesn't work on this app also very glitches happened."

2. User Interface and Ease of Use (60 reviews)
   > "Simple, Fast & Reliable."

3. Trading App Features (54 reviews)
   > "So far the experience has been good. However, you guys don't update data regularly."

**Action Ideas:**
1. Implement crash reporting to identify and fix performance issues
2. Redesign onboarding flow for better first-time user experience
3. Enhance trading analytics with more detailed portfolio insights

---

## ⚠️ Key Constraints

- **Public sources only** — no login-gated scraping
- **No PII** — all review text scrubbed before LLM and storage
- **Max 5 themes** per weekly run
- **≤250 words** in the weekly note
- **Idempotent** — same week = no duplicates
- **MCP boundary** — Google Workspace only via MCP server

---

## 📄 Disclaimer

This tool analyzes publicly available app store reviews for informational purposes only. No personal data is stored. All outputs are facts-only — no investment advice.

---

*Built for NextLeap LIP Challenge — Milestone 3*
*Product: Groww | By: Pavithra Anil*