import json
import numpy as np
from datetime import datetime

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 64
UMAP_COMPONENTS = 15
UMAP_NEIGHBORS = 15
HDBSCAN_MIN_CLUSTER_SIZE = 15
MAX_CLUSTERS = 5
RANDOM_SEED = 42


def generate_embeddings(texts: list[str]) -> np.ndarray:
    """
    Convert review texts to vectors using MiniLM model.
    Processes in batches to avoid memory issues.
    """
    from sentence_transformers import SentenceTransformer

    print(f"  Loading embedding model ({EMBEDDING_MODEL})...")
    model = SentenceTransformer(EMBEDDING_MODEL)

    print(f"  Generating embeddings for {len(texts)} reviews (batch size {BATCH_SIZE})...")
    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    print(f"  ✓ Generated {len(embeddings)} embeddings")
    return embeddings


def reduce_dimensions(embeddings: np.ndarray) -> np.ndarray:
    """
    Reduce embedding dimensions using UMAP.
    Makes clustering faster and more accurate.
    """
    import umap

    n_neighbors = min(UMAP_NEIGHBORS, len(embeddings) - 1)
    print(f"  Running UMAP (components={UMAP_COMPONENTS}, neighbors={n_neighbors})...")

    reducer = umap.UMAP(
        n_components=UMAP_COMPONENTS,
        n_neighbors=n_neighbors,
        metric="cosine",
        random_state=RANDOM_SEED,
        low_memory=True,
    )
    reduced = reducer.fit_transform(embeddings)
    print(f"  ✓ Reduced to {UMAP_COMPONENTS} dimensions")
    return reduced


def cluster_reviews(reduced: np.ndarray) -> np.ndarray:
    """
    Group similar reviews into clusters using HDBSCAN.
    Returns array of cluster labels (-1 = noise).
    """
    import hdbscan

    min_size = HDBSCAN_MIN_CLUSTER_SIZE
    labels = None

    # Try with default min_size, reduce if too few clusters found
    for attempt in range(3):
        print(f"  Running HDBSCAN (min_cluster_size={min_size})...")
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_size,
            metric="euclidean",
            cluster_selection_method="eom",
        )
        labels = clusterer.fit_predict(reduced)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)

        if n_clusters >= 3:
            break
        elif n_clusters == 0:
            min_size = max(5, min_size // 2)
            print(f"  No clusters found, retrying with min_size={min_size}...")
        else:
            break

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    noise_count = list(labels).count(-1)
    noise_ratio = noise_count / len(labels) * 100

    print(f"  ✓ {n_clusters} clusters found")
    print(f"  Noise ratio: {noise_ratio:.1f}% ({noise_count} reviews unassigned)")

    if n_clusters == 0:
        raise RuntimeError(
            "No clusters found. Reviews may be too diverse or too few. "
            "Try ingesting more reviews."
        )

    return labels


def get_keyphrases(texts: list[str], kw_model=None, top_n: int = 5) -> list[str]:
    """Extract key phrases from a list of texts using KeyBERT"""
    from keybert import KeyBERT

    if kw_model is None:
        kw_model = KeyBERT(model=EMBEDDING_MODEL)
    
    combined_text = " ".join(texts[:50])  # Use up to 50 reviews

    try:
        keywords = kw_model.extract_keywords(
            combined_text,
            keyphrase_ngram_range=(1, 2),
            stop_words="english",
            top_n=top_n,
        )
        return [kw[0] for kw in keywords]
    except Exception:
        return []


def get_medoid_review(
    cluster_embeddings: np.ndarray,
    cluster_indices: list[int],
    all_embeddings: np.ndarray,
) -> int:
    """
    Find the most representative review in a cluster.
    The medoid is the review closest to the cluster center.
    """
    cluster_embs = all_embeddings[cluster_indices]
    centroid = cluster_embs.mean(axis=0)
    distances = np.linalg.norm(cluster_embs - centroid, axis=1)
    closest_idx = np.argmin(distances)
    return cluster_indices[closest_idx]


def run_clustering(run_id: str, product: str, weeks: int = 10):
    """
    Main clustering function — runs full pipeline:
    embeddings → UMAP → HDBSCAN → keyphrases → save to DB
    """
    from agent.storage import get_connection
    from agent.time_utils import weeks_ago_date

    print(f"\n🔍 Starting clustering for run {run_id[:8]}...\n")

    # Load reviews from database
    conn = get_connection()
    cutoff = weeks_ago_date(weeks).isoformat()
    rows = conn.execute(
        """
        SELECT id, body_clean FROM reviews
        WHERE product = ? AND review_date >= ?
        ORDER BY review_date DESC
        """,
        (product, cutoff),
    ).fetchall()
    conn.close()

    if len(rows) < 30:
        raise RuntimeError(
            f"Too few reviews for clustering (got {len(rows)}, need ≥ 30). "
            "Run ingestion with more weeks."
        )

    review_ids = [r[0] for r in rows]
    texts = [r[1] for r in rows]

    print(f"  ✓ {len(texts)} reviews loaded from database")

    # Generate embeddings
    embeddings = generate_embeddings(texts)

    # Reduce dimensions
    reduced = reduce_dimensions(embeddings)

    # Cluster
    labels = cluster_reviews(reduced)

    # Get unique cluster IDs (excluding noise = -1)
    unique_clusters = sorted(set(labels))
    if -1 in unique_clusters:
        unique_clusters.remove(-1)

    # Limit to MAX_CLUSTERS
    if len(unique_clusters) > MAX_CLUSTERS:
        # Keep largest clusters
        cluster_sizes = {
            c: list(labels).count(c) for c in unique_clusters
        }
        unique_clusters = sorted(
            unique_clusters,
            key=lambda c: cluster_sizes[c],
            reverse=True
        )[:MAX_CLUSTERS]

    print(f"\n  Extracting keyphrases for {len(unique_clusters)} clusters...")

    # Delete existing themes for this run (idempotency)
    conn = get_connection()
    conn.execute("DELETE FROM themes WHERE run_id = ?", (run_id,))
    conn.commit()

    # Initialize KeyBERT model once
    from keybert import KeyBERT
    kw_model = KeyBERT(model=EMBEDDING_MODEL)

    # Build and save themes
    themes = []
    for rank, cluster_id in enumerate(unique_clusters, 1):
        # Get indices of reviews in this cluster
        cluster_indices = [
            i for i, label in enumerate(labels)
            if label == cluster_id
        ]
        cluster_review_ids = [review_ids[i] for i in cluster_indices]
        cluster_texts = [texts[i] for i in cluster_indices]

        # Get keyphrases
        keyphrases = get_keyphrases(cluster_texts, kw_model=kw_model)

        # Get medoid (most representative review)
        medoid_idx = get_medoid_review(
            embeddings[cluster_indices],
            cluster_indices,
            embeddings,
        )
        medoid_review_id = review_ids[medoid_idx]
        medoid_text = texts[medoid_idx]

        theme = {
            "run_id": run_id,
            "rank": rank,
            "name": f"Theme {rank}",  # LLM will name it in Phase 3
            "review_count": len(cluster_review_ids),
            "review_ids_json": json.dumps(cluster_review_ids),
            "keyphrases_json": json.dumps(keyphrases),
            "medoid_review_id": medoid_review_id,
            "medoid_text": medoid_text,
        }
        themes.append(theme)

        print(f"  Theme {rank}: {len(cluster_review_ids)} reviews | keyphrases: {keyphrases[:3]}")

    # Save to database
    for theme in themes:
        conn.execute(
            """
            INSERT INTO themes
            (run_id, rank, name, review_count, review_ids_json, keyphrases_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                theme["run_id"],
                theme["rank"],
                theme["name"],
                theme["review_count"],
                theme["review_ids_json"],
                theme["keyphrases_json"],
            ),
        )

    conn.commit()
    conn.close()

    # Update run status
    from agent.storage import update_run_status
    update_run_status(run_id, "clustered", clusters_count=len(themes))

    print(f"\n✅ Clustering complete!")
    print(f"   {len(themes)} themes saved to database")
    print(f"   Run ID: {run_id}")

    return themes