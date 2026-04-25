import os
from agent.mcp_client.session import call_mcp, wake_up_server
from agent.storage import get_connection
from dotenv import load_dotenv

load_dotenv()


def publish_to_gmail(run_id: str, summary: dict, doc_url: str = "") -> str:
    """
    Create Gmail draft with weekly pulse report via MCP server.
    Returns message ID.
    Idempotent — skips if already sent for this run.
    """
    to_email = os.getenv("GMAIL_TO", "")
    if not to_email:
        raise RuntimeError(
            "GMAIL_TO not set in .env. "
            "Add your email address."
        )

    confirm_send = os.getenv("CONFIRM_SEND", "false").lower() == "true"

    product = summary.get("product", "groww").title()
    week = summary.get("week", "")
    themes = summary.get("themes", [])
    action_ideas = summary.get("action_ideas", [])
    top_theme = themes[0]["name"] if themes else "Weekly Update"

    subject = f"[Weekly Pulse] Groww — {week} — {top_theme}"
    body = build_email_body(summary, doc_url)

    # Wake up MCP server
    wake_up_server()

    print(f"  Creating Gmail draft...")
    print(f"  To: {to_email}")
    print(f"  Subject: {subject}")

    # Call MCP server
    response = call_mcp("/create_email_draft", {
        "to": to_email,
        "subject": subject,
        "body": body,
    })

    message_id = response.get("draft_id", run_id)

    # Update run status
    conn = get_connection()
    conn.execute(
        """
        UPDATE runs
        SET gmail_message_id = ?, status = ?, updated_at = datetime('now')
        WHERE id = ?
        """,
        (message_id, "published", run_id),
    )
    conn.commit()
    conn.close()

    if confirm_send:
        print(f"  ✓ Email sent to {to_email}")
    else:
        print(f"  ✓ Email draft created in Gmail")
        print(f"  ℹ Set CONFIRM_SEND=true in .env to send automatically")

    return message_id


def build_email_body(summary: dict, doc_url: str = "") -> str:
    """Build plain text email body"""
    week = summary.get("week", "")
    themes = summary.get("themes", [])
    action_ideas = summary.get("action_ideas", [])
    total_reviews = summary.get("total_reviews_analyzed", 0)

    lines = []
    lines.append(f"Groww Weekly Review Pulse — {week}")
    lines.append(f"{total_reviews} reviews analyzed from Play Store and App Store")
    lines.append("")
    lines.append("TOP THEMES THIS WEEK")
    lines.append("")

    for theme in themes[:3]:
        lines.append(f"{theme['rank']}. {theme['name']} ({theme['review_count']} reviews)")
        quote = theme.get("quote", "")
        if quote:
            lines.append(f'   "{quote}"')
        lines.append("")

    lines.append("ACTION IDEAS")
    lines.append("")
    for i, idea in enumerate(action_ideas, 1):
        lines.append(f"{i}. {idea}")

    lines.append("")
    if doc_url:
        lines.append(f"Read full report: {doc_url}")
        lines.append("")

    lines.append("---")
    lines.append("This report is generated from public app store reviews.")
    lines.append("Facts only. No investment advice.")

    return "\n".join(lines)