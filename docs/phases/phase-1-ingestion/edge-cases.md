# Phase 1 — Edge Cases

## Goal
Document everything that could go wrong during review ingestion and how we handle each case.

---

## Edge Case 1: Play Store Blocks the Scraper

**Scenario:** Google detects scraping and returns a 403 or empty response

**Risk:** Zero reviews fetched, pipeline fails silently

**Handling:**
- Retry up to 3 times with exponential backoff (wait 2s, 4s, 8s between retries)
- If all retries fail → raise clear error: "Play Store blocked. Try again later."
- Log the failure with timestamp for debugging

---

## Edge Case 2: App Store RSS Feed is Down

**Scenario:** iTunes RSS API returns 500 or times out

**Risk:** App Store reviews missing from analysis

**Handling:**
- Retry up to 3 times
- If App Store fails but Play Store succeeds → continue with Play Store only
- Log warning: "App Store unavailable — using Play Store reviews only"
- Don't fail the entire pipeline for one source

---

## Edge Case 3: All Reviews are Filtered Out

**Scenario:** Every fetched review is either too short, non-English, or outside the time window

**Risk:** Empty database, clustering fails in Phase 2

**Handling:**
- After filtering, check if at least 20 reviews remain
- If fewer than 20 → raise error: "Too few reviews after filtering (got N). Check filter settings."
- Suggest relaxing the minimum word count or extending the time window

---

## Edge Case 4: Review Text is Empty or None

**Scenario:** Some reviews have no text — just a star rating with no comment

**Risk:** Empty strings cause errors in embedding or filtering

**Handling:**
- Skip reviews where `body` is None or empty string
- These are valid ratings but useless for theme analysis
- Log count of skipped empty reviews

---

## Edge Case 5: Review Contains Only Emojis

**Scenario:** Review body is "👍👍👍🔥🔥" with no real words

**Risk:** Word count check passes (emojis count as characters) but text is useless

**Handling:**
- Strip emojis before counting words
- If word count after emoji strip is < 10 → filter out
- Use regex to remove emoji characters before word count check

---

## Edge Case 6: Duplicate Reviews from Both Sources

**Scenario:** Same user posts identical review on both Play Store and App Store

**Risk:** Duplicate content inflates theme counts

**Handling:**
- Review ID is `sha1(source + external_id)` — source is part of the ID
- Play Store and App Store reviews are always treated as different even if text matches
- This is acceptable — same complaint from two platforms is still valid signal

---

## Edge Case 7: Network Timeout

**Scenario:** Scraper hangs because network is slow or unreliable

**Risk:** Pipeline hangs indefinitely

**Handling:**
- Set request timeout to 30 seconds
- If timeout → retry with backoff
- After 3 timeouts → fail with clear message

---

## Edge Case 8: Very Large Number of Reviews

**Scenario:** Groww has millions of reviews — scraper tries to fetch all of them

**Risk:** Takes hours, uses too much memory

**Handling:**
- Hard cap at 500 reviews per source per run
- Time window filter (last 10 weeks) naturally limits volume
- Stop pagination once we have 500 reviews or reach the time boundary

---

## Edge Case 9: Play Store App ID Changes

**Scenario:** Groww changes their Play Store app ID

**Risk:** Scraper fetches wrong app or returns empty

**Handling:**
- App ID is configured in `products.yaml` — easy to update
- If zero reviews returned → log warning with the app ID used
- Document in README how to find the correct app ID

---

## Edge Case 10: PII Scrubbing Removes Too Much Text

**Scenario:** A review is mostly phone numbers or emails — after scrubbing, barely any text remains

**Risk:** Very short body_clean causes issues in filtering/embedding

**Handling:**
- After PII scrubbing, re-check word count on `body_clean`
- If `body_clean` has < 10 words after scrubbing → filter out the review
- Log count of reviews filtered due to excessive PII