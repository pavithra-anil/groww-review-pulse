# Problem Statement

## Weekly Product Review Pulse — Groww

### Overview

Groww receives thousands of user reviews every week on Google Play Store and Apple App Store. Product managers, support teams, and leadership currently have no automated way to understand what users are saying at scale. Reading reviews manually is time-consuming, inconsistent, and impossible to do weekly across hundreds of new reviews.

We are building an **automated weekly pulse agent** that:
1. Collects recent Groww app reviews from Play Store and App Store
2. Groups them into meaningful themes using AI
3. Generates a concise one-page insight report
4. Delivers it to stakeholders via Google Docs and Gmail — using MCP (Model Context Protocol) for secure, structured delivery

---

### Problem Being Solved

| Who | Pain Today | What They Need |
|-----|-----------|----------------|
| Product Team | Manually reads reviews to find patterns | Automated weekly theme summary |
| Support Team | Unaware of repeating complaints | Early warning on recurring issues |
| Leadership | No quick health pulse on user sentiment | One-page weekly snapshot |

---

### What We Are Building

An AI agent pipeline with the following capabilities:

**1. Review Ingestion**
- Collect reviews from the last 8–12 weeks from Google Play Store and Apple App Store
- Store them in a local SQLite database
- Scrub any PII (emails, phone numbers) before storage

**2. Theme Clustering**
- Use embeddings to group similar reviews together
- Identify up to 5 distinct themes (e.g. performance, KYC, payments, support, UX)
- Select representative quotes from real review text

**3. LLM Summarization**
- Use an LLM (Groq/Llama) to name each theme
- Generate 3 action ideas based on the themes
- Validate that all quotes come from actual review text

**4. Report Generation**
- Produce a clean one-page weekly pulse note containing:
  - Top 3 themes
  - 3 real user quotes
  - 3 action ideas
- Format it for Google Docs and email delivery

**5. MCP-based Delivery**
- Append the weekly report to a running Google Doc (one doc per product, new section each week)
- Send a short stakeholder email with a deep link to the new section
- All Google Workspace interactions go through MCP servers — no hardcoded credentials

---

### Key Constraints

- **Public sources only** — no login-gated scraping
- **No PII** — all review text scrubbed before LLM and before publishing
- **Max 5 themes** per weekly run
- **≤250 words** in the weekly note
- **Idempotent** — re-running the same week must not create duplicate docs or emails
- **MCP boundary** — Google Docs and Gmail are only accessed via MCP servers

---

### Success Criteria

- End-to-end pipeline runs for Groww and produces a grounded one-page pulse
- Report is appended to Google Docs and email is sent with a working deep link
- Re-running the same week produces no duplicates
- All quotes in the report are verbatim from actual reviews

---

### Non-Goals

- No real-time streaming or live dashboard
- No social media sources (Twitter, Reddit) in initial scope
- No storing Google credentials in agent code

---

### Sample Output

**Groww — Weekly Review Pulse**
**Period:** Last 8–12 weeks (rolling window)

**Top Themes**
1. App performance & bugs — Lag, crashes during trading hours; login/session timeouts
2. Customer support friction — Slow responses; unresolved tickets
3. UX & feature gaps — Confusing navigation; missing advanced analytics

**Real User Quotes**
- "The app freezes exactly when the market opens, very frustrating."
- "Support takes days to reply and doesn't solve the issue."
- "Good for beginners but lacks detailed analysis tools."

**Action Ideas**
1. Stabilize peak-time performance — Scale infra during market hours
2. Improve support SLA visibility — Show expected response time in-app
3. Enhance power-user features — Advanced portfolio analytics

---

*Built for NextLeap LIP Challenge — Milestone 3*
*Product: Groww | AMC scope: All user-facing app features*