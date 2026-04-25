# Phase 3 — Edge Cases

## Goal
Document everything that could go wrong during LLM summarization and how we handle each case.

---

## Edge Case 1: LLM Returns Hallucinated Quote

**Scenario:** LLM returns a quote that doesn't exist in any review

**Risk:** Report contains fabricated user feedback — major credibility issue

**Handling:**
- After LLM returns a quote, check if it's a substring of any real review body
- If not found → re-prompt LLM once asking for a real verbatim quote
- If second attempt also fails → use the medoid review text directly (guaranteed real)
- Log every quote validation attempt

---

## Edge Case 2: GROQ API Rate Limit Hit

**Scenario:** Too many LLM calls in a short time — Groq returns 429 error

**Risk:** Summarization fails halfway through

**Handling:**
- Catch 429 errors and wait 60 seconds before retrying
- Retry up to 3 times
- If all retries fail → raise clear error: "Groq API rate limit exceeded. Try again in a few minutes."

---

## Edge Case 3: GROQ API Key Invalid or Missing

**Scenario:** GROQ_API_KEY in .env is wrong or expired

**Risk:** All LLM calls fail immediately

**Handling:**
- `config.py` validates key exists at startup
- First API call failure → clear error: "Invalid Groq API key. Check your .env file."
- Don't retry on auth errors — fail fast

---

## Edge Case 4: LLM Returns Invalid JSON

**Scenario:** LLM doesn't follow the JSON format we asked for

**Risk:** JSON parsing fails, summarization crashes

**Handling:**
- Use structured prompts that explicitly ask for JSON
- Wrap JSON parsing in try/except
- If parsing fails → retry once with stronger instruction: "Return ONLY valid JSON, no other text"
- If second attempt fails → raise error with raw LLM response for debugging

---

## Edge Case 5: No Themes in Database

**Scenario:** Summarize command runs before cluster command

**Risk:** No themes to summarize → crashes or empty output

**Handling:**
- Check if themes exist for this run_id before calling LLM
- If no themes → raise error: "No clusters found for this run. Run 'cluster' first."

---

## Edge Case 6: Theme Has Very Few Reviews

**Scenario:** A cluster has only 5-10 reviews — not enough context for good summary

**Risk:** LLM generates vague or generic theme name

**Handling:**
- Still process small clusters — minimum viable
- Include all available reviews in the prompt
- Accept that small clusters may have less specific names
- Log warning if cluster has < 10 reviews

---

## Edge Case 7: LLM Generates Duplicate Theme Names

**Scenario:** LLM names two different themes the same thing

**Risk:** Confusing report with duplicate section headers

**Handling:**
- After naming all themes, check for duplicates
- If duplicates found → append rank number: "App Issues (1)", "App Issues (2)"
- This is rare but handled gracefully

---

## Edge Case 8: Action Ideas are Too Generic

**Scenario:** LLM generates generic advice like "improve the app" with no specifics

**Risk:** Report is not useful for product team

**Handling:**
- Prompt explicitly asks for specific, actionable ideas tied to the themes
- Prompt includes the theme names and keyphrases as context
- Manual review in evaluations catches this — re-run if needed
- Future improvement: add a validation step for action idea specificity