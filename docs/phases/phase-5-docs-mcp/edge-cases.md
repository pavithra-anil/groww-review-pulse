# Phase 5 — Edge Cases (Google Docs MCP)

## Goal
Document everything that could go wrong during Google Docs delivery via MCP.

---

## Edge Case 1: MCP Server is Sleeping (Cold Start)

**Scenario:** Render free tier MCP server is asleep when agent calls it

**Risk:** First request times out after 50+ seconds

**Handling:**
- Set request timeout to 120 seconds
- If timeout → retry once after 30 seconds
- Log warning: "MCP server is waking up, retrying..."

---

## Edge Case 2: MCP Server Returns 500 Error

**Scenario:** Google Docs API call fails inside MCP server

**Risk:** Report not appended, no clear error message

**Handling:**
- Check response status code
- If 500 → log full error response for debugging
- Raise clear error: "MCP server failed to append to doc. Check MCP server logs."

---

## Edge Case 3: Google Doc Not Found

**Scenario:** GOOGLE_DOC_ID in .env points to wrong or deleted doc

**Risk:** MCP server returns 404 for the doc

**Handling:**
- Check response for "not found" error
- Raise clear error: "Google Doc not found. Check GOOGLE_DOC_ID in .env"
- Suggest creating a new doc and updating the ID

---

## Edge Case 4: No Edit Access to Google Doc

**Scenario:** The Google Doc exists but the authenticated user doesn't have edit access

**Risk:** MCP server returns 403

**Handling:**
- Check response for "permission denied" error
- Raise clear error: "No edit access to Google Doc. Make sure you own the doc or have edit permissions."

---

## Edge Case 5: Artifacts Not Found

**Scenario:** publish command runs before render command

**Risk:** doc_requests.json not found

**Handling:**
- Check if artifacts directory exists before calling MCP
- If missing → raise error: "Artifacts not found for run {run_id}. Run 'render' first."

---

## Edge Case 6: Token Expired on MCP Server

**Scenario:** Google OAuth token expires after 1 hour

**Risk:** MCP server returns 401 Unauthorized

**Handling:**
- The MCP server's auth.py handles token refresh automatically
- If refresh fails → MCP server returns clear error
- Solution: Re-run auth.py locally and update GOOGLE_TOKEN_JSON on Render

---

## Edge Case 7: Network Timeout

**Scenario:** Network is slow or unstable during MCP call

**Risk:** Request hangs indefinitely

**Handling:**
- Set 120 second timeout on all requests
- Retry once on timeout
- After 2 timeouts → fail with clear message