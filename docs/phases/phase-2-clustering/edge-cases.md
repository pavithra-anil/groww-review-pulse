# Phase 2 — Edge Cases

## Goal
Document everything that could go wrong during embedding and clustering.

---

## Edge Case 1: Too Few Reviews for Clustering

**Scenario:** After ingestion, fewer than 30 reviews are available

**Risk:** HDBSCAN can't find meaningful clusters with very few points

**Handling:**
- Check review count before clustering
- If fewer than 30 reviews → raise error: "Too few reviews for clustering (got N, need ≥ 30)"
- Suggest running ingestion with more weeks

---

## Edge Case 2: All Reviews End Up as Noise

**Scenario:** HDBSCAN assigns every review to noise (-1 cluster)

**Risk:** No themes generated, pipeline fails in Phase 3

**Handling:**
- If 0 clusters found → reduce `min_cluster_size` and retry once
- If still 0 clusters → raise error: "No clusters found. Reviews may be too diverse or too few."
- Log HDBSCAN parameters used for debugging

---

## Edge Case 3: Only 1 Cluster Found

**Scenario:** All reviews are so similar that HDBSCAN puts them in one cluster

**Risk:** One-theme report is not useful

**Handling:**
- If only 1 cluster found → reduce `min_cluster_size` and retry
- Accept 1 cluster only as last resort
- Log warning: "Only 1 cluster found — report may lack diversity"

---

## Edge Case 4: Embedding Model Download Fails

**Scenario:** First run needs to download the MiniLM model (~90MB) but network is slow or offline

**Risk:** Embedding step hangs or fails

**Handling:**
- sentence-transformers handles retries automatically
- Show progress bar during download
- If download fails → clear error: "Could not download embedding model. Check internet connection."

---

## Edge Case 5: Memory Error During Embedding

**Scenario:** Embedding 600+ reviews at once uses too much RAM

**Risk:** Process crashes with MemoryError

**Handling:**
- Embed in batches of 64 reviews at a time
- This limits peak memory usage
- Log batch progress so user can see it's working

---

## Edge Case 6: UMAP Fails with Small Dataset

**Scenario:** Fewer reviews than UMAP's `n_neighbors` parameter

**Risk:** UMAP crashes with cryptic error

**Handling:**
- Set `n_neighbors = min(15, len(reviews) - 1)`
- This adapts UMAP to the dataset size automatically

---

## Edge Case 7: Re-running Cluster for Same Run ID

**Scenario:** Cluster command run twice for same run_id

**Risk:** Duplicate themes in database

**Handling:**
- Before clustering, delete existing themes for this run_id
- Then insert fresh clusters
- This makes clustering idempotent — safe to re-run

---

## Edge Case 8: Non-English Reviews Slip Through

**Scenario:** Some non-English reviews pass the language filter (langdetect can be wrong)

**Risk:** Non-English text creates garbage clusters

**Handling:**
- Language detection is best-effort — not 100% accurate
- HDBSCAN naturally handles outliers by marking them as noise
- Non-English reviews typically become noise, not clusters
- Acceptable trade-off for performance