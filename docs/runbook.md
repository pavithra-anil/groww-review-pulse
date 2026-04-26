# Runbook — Groww Review Pulse

This runbook covers how to diagnose and fix common issues with the weekly pipeline.

---

## 🔄 How to Re-run for a New Week

**Current week:**
```bash
python -m agent run --product groww --weeks 10
```

**Specific past week:**
```bash
python -m agent run --product groww --week 2026-W16
```

**Run individual phases:**
```bash
python -m agent ingest --product groww --weeks 10
python -m agent cluster --run-id <run_id>
python -m agent summarize --run-id <run_id>
python -m agent render --run-id <run_id>
python -m agent publish --run-id <run_id> --target both
```

**Get run_id for current week:**
```bash
python -c "from agent.time_utils import current_iso_week, make_run_id; print(make_run_id('groww', current_iso_week()))"
```

---

## 🚨 Issue: Email Not Sent

**Symptom:** Pipeline completes but no email in inbox or drafts

**Diagnosis:**
1. Check run status:
```bash
python -c "
import sqlite3
conn = sqlite3.connect('data/pulse.sqlite')
run = conn.execute('SELECT status, gmail_message_id FROM runs ORDER BY created_at DESC LIMIT 1').fetchone()
print(run)
"
```

2. Check if GMAIL_TO is set correctly in `.env`
3. Check if MCP server is alive: `curl https://pavithra-mcp-server.onrender.com/`

**Fix:**
- If status is not "published" → re-run publish:
```bash
python -m agent publish --run-id <run_id> --target gmail
```
- If CONFIRM_SEND=false → email is in Gmail Drafts, not sent

---

## 🚨 Issue: Duplicate Section in Google Doc

**Symptom:** Google Doc has two sections for the same week

**Diagnosis:** Idempotency check failed — anchor not detected

**Fix:**
1. Manually delete the duplicate section in Google Doc
2. The anchor `pulse-groww-YYYY-WNN` must be present in the heading
3. Re-run will skip if anchor is found

---

## 🚨 Issue: Ingestion Returns 0 Reviews

**Symptom:** `Too few reviews after filtering: 0`

**Diagnosis:**
1. Check internet connection
2. Play Store may be blocking: try again in 30 minutes
3. App Store RSS may be down

**Fix:**
```bash
# Try with more weeks
python -m agent ingest --product groww --weeks 12

# Check if Play Store is accessible
curl "https://play.google.com/store/apps/details?id=com.nextbillion.groww"
```

---

## 🚨 Issue: LLM Cost Spike

**Symptom:** Groq API returning 429 rate limit errors

**Diagnosis:** Too many retries or large batches hitting rate limit

**Fix:**
- Wait 60 seconds and retry
- Check Groq console for usage: `console.groq.com`
- Free tier: 6000 requests/day, 500K tokens/day

---

## 🚨 Issue: MCP Server Crash

**Symptom:** `Cannot connect to MCP server` error

**Diagnosis:**
1. Check if Render service is running: `https://dashboard.render.com`
2. Check MCP server logs on Render
3. Server may be sleeping (free tier)

**Fix:**
- Open `https://pavithra-mcp-server.onrender.com/docs` to wake it up
- Wait 60 seconds for cold start
- Re-run publish phase

---

## 🚨 Issue: Token Revoked / Google Auth Failed

**Symptom:** MCP server returns 401 Unauthorized

**Diagnosis:** Google OAuth token expired or revoked

**Fix:**
1. Go to `saksham-mcp-server` folder locally
2. Run: `python -c "from auth import get_creds; get_creds()"`
3. Login with Google in browser
4. Copy contents of new `token.json`
5. Update `GOOGLE_TOKEN_JSON` environment variable on Render
6. Redeploy MCP server

---

## 📊 Theme Legend

Themes are automatically discovered — not predefined. Common themes for Groww:

| Theme | What it captures |
|---|---|
| App Performance & Crashes | Lag, freezes, crashes during trading |
| User Interface & Experience | UI feedback, ease of use, navigation |
| Trading Features | Charts, order types, analytics tools |
| Charges & Fee Complaints | Hidden charges, brokerage, deductions |
| TradingView Integration | Chart integration, technical analysis |
| Customer Support | Response time, issue resolution |
| KYC & Onboarding | Account opening, document verification |

---

## 🔧 Useful Commands

```bash
# Check database status
python -c "
import sqlite3
conn = sqlite3.connect('data/pulse.sqlite')
print('Reviews:', conn.execute('SELECT COUNT(*) FROM reviews').fetchone()[0])
print('Themes:', conn.execute('SELECT COUNT(*) FROM themes').fetchone()[0])
print('Runs:', conn.execute('SELECT COUNT(*) FROM runs').fetchone()[0])
"

# List all runs
python -c "
import sqlite3
conn = sqlite3.connect('data/pulse.sqlite')
for r in conn.execute('SELECT id, iso_week, status, reviews_count FROM runs').fetchall():
    print(r)
"

# Check MCP server health
curl https://pavithra-mcp-server.onrender.com/
```