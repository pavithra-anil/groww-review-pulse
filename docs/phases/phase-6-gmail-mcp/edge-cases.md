# Phase 6 — Edge Cases (Gmail MCP)

## Goal
Document everything that could go wrong during Gmail delivery via MCP.

---

## Edge Case 1: Gmail Draft vs Send

**Scenario:** CONFIRM_SEND=false means only draft is created, not sent

**Risk:** Stakeholder never receives email if nobody sends the draft

**Handling:**
- Default is draft-only (CONFIRM_SEND=false) for safety
- Set CONFIRM_SEND=true in .env to actually send
- Log clearly: "Draft created — set CONFIRM_SEND=true to send"

---

## Edge Case 2: Invalid Recipient Email

**Scenario:** GMAIL_TO in .env has a typo or invalid email

**Risk:** Draft created with wrong recipient

**Handling:**
- Validate email format before calling MCP
- If invalid → raise error: "Invalid email address in GMAIL_TO"

---

## Edge Case 3: Gmail API Quota Exceeded

**Scenario:** Too many Gmail API calls in a day

**Risk:** MCP server returns 429 rate limit error

**Handling:**
- Catch 429 response from MCP server
- Wait 60 seconds and retry once
- If still failing → raise error with clear message

---

## Edge Case 4: Email Body Too Large

**Scenario:** Report has very long theme descriptions or quotes

**Risk:** Gmail API rejects oversized email

**Handling:**
- Truncate theme descriptions to 200 chars
- Truncate quotes to 150 chars
- Keep email body under 10KB

---

## Edge Case 5: Doc Deep Link Not Available

**Scenario:** Phase 5 failed so no gdoc_heading_id exists

**Risk:** Email sent without working deep link

**Handling:**
- Check if gdoc_id exists in runs table before sending email
- If missing → use generic doc link instead of heading link
- Log warning: "No heading link available — using doc root link"

---

## Edge Case 6: MCP Server Token Expired

**Scenario:** Google OAuth token expires between Phase 5 and Phase 6

**Risk:** Gmail call fails with 401

**Handling:**
- Same as Phase 5 — MCP server handles refresh automatically
- If refresh fails → clear error message about updating token