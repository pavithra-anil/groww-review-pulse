# Phase 4 — Edge Cases

## Goal
Document everything that could go wrong during report and email rendering.

---

## Edge Case 1: PulseSummary JSON File Missing

**Scenario:** Render command runs before summarize command

**Risk:** FileNotFoundError crashes the render step

**Handling:**
- Check if summary file exists before rendering
- If missing → raise clear error: "PulseSummary not found for run {run_id}. Run 'summarize' first."

---

## Edge Case 2: Theme Has No Quote

**Scenario:** Quote validation failed in Phase 3 and quote is empty string

**Risk:** Empty quote in rendered report looks unprofessional

**Handling:**
- Check if quote is empty before rendering
- If empty → use a fallback: "Users reported issues with this area of the app."
- Log warning so it can be investigated

---

## Edge Case 3: Very Long Theme Name

**Scenario:** LLM generated a theme name that is 80+ characters long

**Risk:** Heading overflows in Google Docs or email

**Handling:**
- Truncate theme names to 60 characters max during summarization
- Add "..." if truncated
- This was already handled in summarization.py

---

## Edge Case 4: Special Characters in Review Quotes

**Scenario:** Quote contains characters like `<`, `>`, `&` that break HTML

**Risk:** Email HTML renders incorrectly or shows raw HTML tags

**Handling:**
- HTML-escape all user-generated content before inserting into HTML template
- Use Jinja2's auto-escaping feature
- Test with quotes containing special characters

---

## Edge Case 5: Artifacts Directory Already Exists

**Scenario:** Render command run twice for same run_id

**Risk:** Old artifacts mixed with new ones

**Handling:**
- Overwrite existing files — don't append
- Use `open(path, 'w')` not `open(path, 'a')`
- This makes rendering idempotent

---

## Edge Case 6: Missing data/summaries Directory

**Scenario:** Fresh clone of repo — data/ folder doesn't exist

**Risk:** FileNotFoundError when trying to read summary

**Handling:**
- Check if directory exists before reading
- Clear error message pointing to correct setup steps

---

## Edge Case 7: Fewer Than 3 Themes

**Scenario:** Clustering only found 1-2 themes

**Risk:** Report looks sparse with fewer than 3 theme sections

**Handling:**
- Render whatever themes exist — don't fail
- If fewer than 3 themes → add note: "Only N themes found this week"
- Email subject uses first theme regardless of count

---

## Edge Case 8: Action Ideas List is Empty

**Scenario:** LLM failed to generate action ideas in Phase 3

**Risk:** Report has empty action ideas section

**Handling:**
- Check action_ideas list length before rendering
- If empty → use fallback generic ideas
- Log warning for investigation