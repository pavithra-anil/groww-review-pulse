import sqlite3
import os
from datetime import datetime

DB_PATH = "data/pulse.sqlite"


def get_connection() -> sqlite3.Connection:
    """Get a database connection"""
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables if they don't exist"""
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/raw/groww", exist_ok=True)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            play_store_id TEXT,
            app_store_id TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS reviews (
            id TEXT PRIMARY KEY,
            product TEXT NOT NULL,
            source TEXT NOT NULL,
            rating INTEGER,
            title TEXT,
            body TEXT,
            body_clean TEXT,
            word_count INTEGER,
            review_date TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS review_embeddings (
            review_id TEXT PRIMARY KEY,
            embedding BLOB,
            model TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (review_id) REFERENCES reviews(id)
        );

        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,
            product TEXT NOT NULL,
            iso_week TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            reviews_count INTEGER DEFAULT 0,
            clusters_count INTEGER DEFAULT 0,
            llm_cost_usd REAL DEFAULT 0.0,
            gdoc_id TEXT,
            gdoc_heading_id TEXT,
            gmail_message_id TEXT,
            metrics_json TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS themes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            rank INTEGER,
            name TEXT,
            review_count INTEGER,
            quote TEXT,
            action_idea TEXT,
            review_ids_json TEXT,
            keyphrases_json TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (run_id) REFERENCES runs(id)
        );
    """)

    conn.commit()
    conn.close()
    print("✓ Database created at", DB_PATH)
    print("✓ Tables created: products, reviews, review_embeddings, runs, themes")


def create_run(run_id: str, product: str, iso_week: str):
    """Create a new run record"""
    conn = get_connection()
    conn.execute(
        """
        INSERT OR IGNORE INTO runs (id, product, iso_week, status)
        VALUES (?, ?, ?, 'ingesting')
        """,
        (run_id, product, iso_week),
    )
    conn.commit()
    conn.close()


def update_run_status(run_id: str, status: str, **kwargs):
    """Update run status and optional fields"""
    conn = get_connection()
    fields = ["status = ?", "updated_at = datetime('now')"]
    values = [status]
    for key, val in kwargs.items():
        fields.append(f"{key} = ?")
        values.append(val)
    values.append(run_id)
    conn.execute(
        f"UPDATE runs SET {', '.join(fields)} WHERE id = ?",
        values,
    )
    conn.commit()
    conn.close()


def save_reviews(reviews: list) -> int:
    """
    Save reviews to database using upsert.
    Returns number of new reviews inserted.
    """
    conn = get_connection()
    inserted = 0
    for r in reviews:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO reviews
            (id, product, source, rating, title, body, body_clean, word_count, review_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                r.id,
                r.product,
                r.source,
                r.rating,
                r.title,
                r.body,
                r.body_clean,
                r.word_count,
                r.review_date.isoformat() if isinstance(r.review_date, datetime) else r.review_date,
            ),
        )
        inserted += cursor.rowcount
    conn.commit()
    conn.close()
    return inserted


def get_reviews_for_run(product: str, cutoff_date: str) -> list:
    """Get all reviews for a product after a cutoff date"""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT * FROM reviews
        WHERE product = ? AND review_date >= ?
        ORDER BY review_date DESC
        """,
        (product, cutoff_date),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]