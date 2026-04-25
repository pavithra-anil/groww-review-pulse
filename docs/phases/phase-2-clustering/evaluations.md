# Phase 2 — Evaluations

## Goal
Prove that reviews are correctly grouped into meaningful clusters using embeddings, UMAP, and HDBSCAN.

---

## Evaluation 1: Clustering Produces 3-5 Themes

**Test:** Run cluster command and verify meaningful clusters are produced

**Command:**
```bash
.venv\Scripts\python -m agent cluster --run-id 44accf94abd53dc0d5d5438f269b7459060f8ba7
```

**Expected output:**
```
Loading reviews from database...
✓ 626 reviews loaded
Generating embeddings...
✓ 626 embeddings generated
Running UMAP dimensionality reduction...
✓ Reduced to 15 dimensions
Running HDBSCAN clustering...
✓ 4 clusters found
Noise ratio: 22% (138 reviews unassigned)
Extracting keyphrases...
✓ Clusters saved to database
```

**Pass criteria:** Between 3 and 5 clusters produced

---

## Evaluation 2: Noise Ratio is Acceptable

**Test:** Verify less than 40% of reviews are unassigned (noise)

**Check:**
```bash
.venv\Scripts\python -c "
import sqlite3
conn = sqlite3.connect('data/pulse.sqlite')
total = conn.execute('SELECT COUNT(*) FROM reviews').fetchone()[0]
themes = conn.execute('SELECT SUM(review_count) FROM themes').fetchone()[0] or 0
noise_ratio = (total - themes) / total * 100
print(f'Total reviews: {total}')
print(f'Assigned to clusters: {themes}')
print(f'Noise ratio: {noise_ratio:.1f}%')
print('PASS' if noise_ratio < 40 else 'FAIL')
"
```

**Pass criteria:** Noise ratio < 40%

---

## Evaluation 3: Clusters are Saved to Database

**Test:** Verify themes table has entries after clustering

**Check:**
```bash
.venv\Scripts\python -c "
import sqlite3
conn = sqlite3.connect('data/pulse.sqlite')
themes = conn.execute('SELECT rank, name, review_count, keyphrases_json FROM themes').fetchall()
for t in themes:
    print(f'Rank {t[0]}: {t[1]} ({t[2]} reviews)')
    print(f'  Keyphrases: {t[3][:100]}')
"
```

**Expected:** 3-5 themes with names and keyphrases

**Pass criteria:** At least 3 themes in database

---

## Evaluation 4: Deterministic Results

**Test:** Running cluster twice produces same number of clusters

**Commands:**
```bash
.venv\Scripts\python -m agent cluster --run-id 44accf94abd53dc0d5d5438f269b7459060f8ba7
.venv\Scripts\python -m agent cluster --run-id 44accf94abd53dc0d5d5438f269b7459060f8ba7
```

**Check cluster count both times:**
```bash
.venv\Scripts\python -c "
import sqlite3
conn = sqlite3.connect('data/pulse.sqlite')
count = conn.execute('SELECT COUNT(*) FROM themes').fetchone()[0]
print(f'Theme count: {count}')
"
```

**Pass criteria:** Same theme count both times (idempotent)

---

## Evaluation 5: Each Cluster has a Representative Review

**Test:** Every theme has a medoid (most representative review)

**Check:**
```bash
.venv\Scripts\python -c "
import sqlite3, json
conn = sqlite3.connect('data/pulse.sqlite')
themes = conn.execute('SELECT name, review_ids_json FROM themes').fetchall()
for t in themes:
    ids = json.loads(t[1])
    print(f'{t[0]}: {len(ids)} reviews')
"
```

**Pass criteria:** Every theme has at least 5 review IDs