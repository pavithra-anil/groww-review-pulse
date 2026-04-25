import typer
from typing import Optional
import json
import os

app = typer.Typer(
    name="agent",
    help="Groww Weekly Review Pulse Agent",
    add_completion=False,
)


@app.command()
def init_db():
    """Create SQLite database with all tables"""
    from agent.storage import init_db as _init_db
    _init_db()


@app.command()
def ingest(
    product: str = typer.Option("groww", help="Product name from products.yaml"),
    weeks: int = typer.Option(10, help="Number of weeks to fetch reviews for"),
):
    """Fetch and store reviews from Play Store + App Store"""
    from agent.config import settings
    from agent.storage import create_run, save_reviews, update_run_status
    from agent.time_utils import current_iso_week, make_run_id, weeks_ago_date
    from agent.ingestion.playstore import fetch_playstore_reviews
    from agent.ingestion.appstore import fetch_appstore_reviews

    product_config = settings.get_product(product)
    iso_week = current_iso_week()
    run_id = make_run_id(product, iso_week)
    cutoff = weeks_ago_date(weeks)

    typer.echo(f"\n🚀 Starting ingestion for {product_config.display_name}")
    typer.echo(f"   Week: {iso_week} | Run ID: {run_id[:8]}...")
    typer.echo(f"   Fetching reviews from last {weeks} weeks\n")

    create_run(run_id, product, iso_week)

    all_reviews = []

    try:
        ps_reviews = fetch_playstore_reviews(
            product=product,
            app_id=product_config.play_store_id,
            cutoff=cutoff,
            run_id=run_id,
        )
        all_reviews.extend(ps_reviews)
    except Exception as e:
        typer.echo(f"  ⚠ Play Store error: {e}")

    try:
        as_reviews = fetch_appstore_reviews(
            product=product,
            app_id=product_config.app_store_id,
            country=product_config.app_store_country,
            cutoff=cutoff,
            run_id=run_id,
        )
        all_reviews.extend(as_reviews)
    except Exception as e:
        typer.echo(f"  ⚠ App Store error: {e}")

    if len(all_reviews) < 20:
        typer.echo(f"\n❌ Too few reviews after filtering: {len(all_reviews)}")
        typer.echo("   Try increasing --weeks or check your internet connection")
        update_run_status(run_id, "failed")
        raise typer.Exit(1)

    inserted = save_reviews(all_reviews)
    update_run_status(run_id, "ingested", reviews_count=len(all_reviews))

    typer.echo(f"\n✅ Ingestion complete!")
    typer.echo(f"   Total reviews: {len(all_reviews)}")
    typer.echo(f"   New inserts: {inserted}")
    typer.echo(f"   Run ID: {run_id}")


@app.command()
def cluster(
    run_id: str = typer.Option(..., "--run-id", help="Run ID to cluster reviews for"),
    product: str = typer.Option("groww", help="Product name"),
    weeks: int = typer.Option(10, help="Number of weeks used during ingestion"),
):
    """Cluster reviews into themes using embeddings"""
    from agent.clustering import run_clustering
    run_clustering(run_id=run_id, product=product, weeks=weeks)


@app.command()
def summarize(
    run_id: str = typer.Option(..., "--run-id", help="Run ID to summarize"),
    product: str = typer.Option("groww", help="Product name"),
):
    """Generate LLM summary from clusters"""
    from agent.summarization import run_summarization
    run_summarization(run_id=run_id, product=product)


@app.command()
def render(
    run_id: str = typer.Option(..., "--run-id", help="Run ID to render report for"),
):
    """Render report and email artifacts to disk"""
    from agent.renderer.docs_tree import build_doc_requests
    from agent.renderer.email_html import render_email, get_email_subject
    from agent.storage import update_run_status

    typer.echo(f"\n📄 Starting render for run {run_id[:8]}...\n")

    summary_path = f"data/summaries/{run_id}.json"
    if not os.path.exists(summary_path):
        typer.echo(f"❌ PulseSummary not found at {summary_path}")
        typer.echo("   Run 'summarize' first.")
        raise typer.Exit(1)

    with open(summary_path, encoding="utf-8") as f:
        summary = json.load(f)

    typer.echo(f"  ✓ Loaded summary for {summary['product']} week {summary['week']}")

    artifacts_dir = f"data/artifacts/{run_id}"
    os.makedirs(artifacts_dir, exist_ok=True)

    typer.echo("\n  Rendering Google Docs section...")
    doc_data = build_doc_requests(summary)
    doc_path = f"{artifacts_dir}/doc_requests.json"
    with open(doc_path, "w", encoding="utf-8") as f:
        json.dump(doc_data, f, indent=2, ensure_ascii=False)
    typer.echo(f"  ✓ doc_requests.json saved")

    typer.echo("\n  Rendering email...")
    html_content, text_content = render_email(summary)
    subject = get_email_subject(summary)

    html_path = f"{artifacts_dir}/email.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    typer.echo(f"  ✓ email.html saved")

    text_path = f"{artifacts_dir}/email.txt"
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(f"Subject: {subject}\n\n{text_content}")
    typer.echo(f"  ✓ email.txt saved")

    update_run_status(run_id, "rendered")

    typer.echo(f"\n✅ Render complete!")
    typer.echo(f"   Artifacts saved to {artifacts_dir}/")
    typer.echo(f"   Subject: {subject}")


@app.command()
def publish(
    run_id: str = typer.Option(..., "--run-id", help="Run ID to publish"),
    target: str = typer.Option("both", help="Target: docs, gmail, or both"),
):
    """Deliver to Google Docs and Gmail via MCP"""
    from agent.mcp_client.docs_ops import publish_to_docs
    from agent.mcp_client.gmail_ops import publish_to_gmail

    summary_path = f"data/summaries/{run_id}.json"
    if not os.path.exists(summary_path):
        typer.echo(f"❌ PulseSummary not found. Run 'summarize' first.")
        raise typer.Exit(1)

    with open(summary_path, encoding="utf-8") as f:
        summary = json.load(f)

    doc_url = ""

    if target in ("docs", "both"):
        typer.echo(f"\n📤 Publishing to Google Docs...")
        try:
            doc_url = publish_to_docs(run_id=run_id, summary=summary)
            typer.echo(f"✅ Google Docs delivery complete!")
        except Exception as e:
            typer.echo(f"❌ Google Docs failed: {e}")
            if target == "docs":
                raise typer.Exit(1)

    if target in ("gmail", "both"):
        typer.echo(f"\n📧 Publishing to Gmail...")
        try:
            publish_to_gmail(run_id=run_id, summary=summary, doc_url=doc_url)
            typer.echo(f"✅ Gmail delivery complete!")
        except Exception as e:
            typer.echo(f"❌ Gmail failed: {e}")
            raise typer.Exit(1)


@app.command()
def run(
    product: str = typer.Option("groww", help="Product name from products.yaml"),
    weeks: int = typer.Option(10, help="Number of weeks to fetch reviews for"),
    week: Optional[str] = typer.Option(None, help="Specific ISO week e.g. 2026-W17"),
):
    """Run the full pipeline end to end"""
    from agent.time_utils import current_iso_week, make_run_id
    iso_week = week or current_iso_week()
    run_id = make_run_id(product, iso_week)
    typer.echo(f"\n🚀 Running full pipeline for {product} — {iso_week}")
    typer.echo(f"   Run ID: {run_id}\n")

    # Run all phases
    from agent.config import settings
    from agent.storage import create_run, save_reviews, update_run_status
    from agent.time_utils import weeks_ago_date
    from agent.ingestion.playstore import fetch_playstore_reviews
    from agent.ingestion.appstore import fetch_appstore_reviews
    from agent.clustering import run_clustering
    from agent.summarization import run_summarization
    from agent.renderer.docs_tree import build_doc_requests
    from agent.renderer.email_html import render_email, get_email_subject
    from agent.mcp_client.docs_ops import publish_to_docs
    from agent.mcp_client.gmail_ops import publish_to_gmail
    import json

    product_config = settings.get_product(product)
    cutoff = weeks_ago_date(weeks)

    # Phase 1: Ingest
    create_run(run_id, product, iso_week)
    all_reviews = []
    try:
        all_reviews.extend(fetch_playstore_reviews(
            product=product, app_id=product_config.play_store_id,
            cutoff=cutoff, run_id=run_id,
        ))
    except Exception as e:
        typer.echo(f"  ⚠ Play Store: {e}")
    try:
        all_reviews.extend(fetch_appstore_reviews(
            product=product, app_id=product_config.app_store_id,
            country=product_config.app_store_country,
            cutoff=cutoff, run_id=run_id,
        ))
    except Exception as e:
        typer.echo(f"  ⚠ App Store: {e}")

    save_reviews(all_reviews)
    update_run_status(run_id, "ingested", reviews_count=len(all_reviews))
    typer.echo(f"✅ Phase 1: {len(all_reviews)} reviews ingested")

    # Phase 2: Cluster
    run_clustering(run_id=run_id, product=product, weeks=weeks)
    typer.echo(f"✅ Phase 2: Clustering complete")

    # Phase 3: Summarize
    summary = run_summarization(run_id=run_id, product=product)
    typer.echo(f"✅ Phase 3: Summarization complete")

    # Phase 4: Render
    artifacts_dir = f"data/artifacts/{run_id}"
    os.makedirs(artifacts_dir, exist_ok=True)
    html_content, text_content = render_email(summary)
    subject = get_email_subject(summary)
    with open(f"{artifacts_dir}/email.html", "w") as f:
        f.write(html_content)
    with open(f"{artifacts_dir}/email.txt", "w") as f:
        f.write(f"Subject: {subject}\n\n{text_content}")
    update_run_status(run_id, "rendered")
    typer.echo(f"✅ Phase 4: Render complete")

    # Phase 5: Publish to Docs
    doc_url = publish_to_docs(run_id=run_id, summary=summary)
    typer.echo(f"✅ Phase 5: Google Docs complete")

    # Phase 6: Publish to Gmail
    publish_to_gmail(run_id=run_id, summary=summary, doc_url=doc_url)
    typer.echo(f"✅ Phase 6: Gmail complete")

    typer.echo(f"\n🎉 Full pipeline complete for {product} — {iso_week}!")
    typer.echo(f"   Doc: {doc_url}")


if __name__ == "__main__":
    app()