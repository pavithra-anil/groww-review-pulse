# Phase 7 — Edge Cases (Orchestration, Scheduling & Hardening)

## Goal
Document everything that could go wrong during scheduled weekly runs and how we handle each case.

---

## Edge Case 1: Pipeline Fails Mid-way

**Scenario:** Pipeline crashes after ingestion but before clustering

**Risk:** Partial data in database, run status stuck at "ingesting"

**Handling:**
- Each phase updates `runs.status` on completion
- On next run, check status and resume from last successful phase
- If status is "ingesting" → skip ingestion, go straight to clustering
- Log which phase was resumed from

---

## Edge Case 2: No New Reviews This Week

**Scenario:** Ingestion returns 0 new reviews (all already in DB from previous run)

**Risk:** Clustering fails with too few reviews

**Handling:**
- Ingestion uses `INSERT OR IGNORE` — duplicates are skipped
- Clustering pulls all reviews within the time window regardless
- Even if 0 new inserts, enough reviews exist for clustering
- Log: "0 new reviews inserted, using existing reviews for clustering"

---

## Edge Case 3: GitHub Actions Runner Has No Credentials

**Scenario:** GitHub Actions tries to run pipeline but GROQ_API_KEY or MCP_SERVER_URL is not set

**Risk:** Pipeline fails silently or with cryptic error

**Handling:**
- Store secrets in GitHub Actions Secrets (not in code)
- Workflow reads from `${{ secrets.GROQ_API_KEY }}`
- If secret is missing → clear error in Actions log

---

## Edge Case 4: MCP Server is Down During Scheduled Run

**Scenario:** Render MCP server is crashed when GitHub Actions runs Monday morning

**Risk:** Phases 5 & 6 fail, report never delivered

**Handling:**
- MCP client retries twice with 30s delay
- If still failing → pipeline marks status as "failed_delivery"
- Report is still saved locally in `data/artifacts/`
- Can manually re-run just publish: `python -m agent publish --run-id <id> --target both`

---

## Edge Case 5: Google Token Expires

**Scenario:** OAuth token expires after 7 days of no use

**Risk:** MCP server returns 401, delivery fails

**Handling:**
- Google refresh tokens last longer — MCP server auto-refreshes
- If refresh fails → update GOOGLE_TOKEN_JSON in Render environment
- Documented in runbook.md under "token revoked"

---

## Edge Case 6: LLM Cost Spike

**Scenario:** Groq API usage spikes unexpectedly (many retries, large clusters)

**Risk:** High token usage, potential rate limiting

**Handling:**
- max_tokens=500 per LLM call limits cost
- Temperature=0.3 reduces token waste
- Cost tracked in runs.llm_cost_usd (future improvement)
- Groq free tier: 6000 req/day — well within limits for weekly runs

---

## Edge Case 7: Play Store Blocks Scraper

**Scenario:** Google detects scraping pattern and blocks requests

**Risk:** 0 Play Store reviews, thin analysis

**Handling:**
- Retry with exponential backoff (3 attempts)
- If all fail → continue with App Store reviews only
- Log warning: "Play Store unavailable — using App Store only"
- Set minimum to 20 reviews to proceed