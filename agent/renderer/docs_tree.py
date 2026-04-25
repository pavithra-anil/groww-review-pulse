import json
from typing import Any


def build_doc_requests(summary: dict) -> dict:
    """
    Convert PulseSummary into Google Docs batchUpdate request tree.
    Returns dict with 'requests' list and 'anchor' string.
    """
    product = summary["product"]
    week = summary["week"]
    themes = summary["themes"]
    action_ideas = summary.get("action_ideas", [])
    total_reviews = summary.get("total_reviews_analyzed", 0)

    anchor = f"pulse-{product}-{week}"
    requests = []

    def insert_text(text: str, style: str = "NORMAL_TEXT") -> list:
        """Helper to create insert + style requests"""
        reqs = []
        reqs.append({
            "insertText": {
                "location": {"index": 1},
                "text": text
            }
        })
        if style != "NORMAL_TEXT":
            reqs.append({
                "updateParagraphStyle": {
                    "range": {
                        "startIndex": 1,
                        "endIndex": len(text) + 1
                    },
                    "paragraphStyle": {
                        "namedStyleType": style
                    },
                    "fields": "namedStyleType"
                }
            })
        return reqs

    # Build document content (inserted in reverse order for index 1 insertion)
    sections = []

    # Disclaimer
    sections.append(("⚠️ This report is generated from public app store reviews. "
                     "Facts only, no investment advice.\n\n", "NORMAL_TEXT"))

    # Action Ideas section
    sections.append(("Action Ideas\n", "HEADING_3"))
    for i, idea in enumerate(action_ideas, 1):
        sections.append((f"{i}. {idea}\n", "NORMAL_TEXT"))
    sections.append(("\n", "NORMAL_TEXT"))

    # Themes section
    sections.append(("Top Themes\n", "HEADING_2"))
    for theme in themes[:3]:
        sections.append((f"{theme['rank']}. {theme['name']} "
                         f"({theme['review_count']} reviews)\n", "HEADING_3"))
        quote = theme.get("quote", "")
        if quote:
            sections.append((f'"{quote}"\n\n', "NORMAL_TEXT"))

    # Summary stats
    sections.append((
        f"Reviews analyzed: {total_reviews} | "
        f"Themes found: {len(themes)}\n\n",
        "NORMAL_TEXT"
    ))

    # Section heading with anchor
    sections.append((
        f"[{anchor}] Groww Weekly Review Pulse — {week}\n",
        "HEADING_1"
    ))

    # Separator
    sections.append(("\n---\n\n", "NORMAL_TEXT"))

    # Build requests from sections
    for text, style in sections:
        requests.extend(insert_text(text, style))

    return {
        "anchor": anchor,
        "requests": requests,
        "metadata": {
            "product": product,
            "week": week,
            "total_reviews": total_reviews,
            "themes_count": len(themes),
        }
    }


def get_anchor(product: str, week: str) -> str:
    """Get the anchor string for a given product and week"""
    return f"pulse-{product}-{week}"