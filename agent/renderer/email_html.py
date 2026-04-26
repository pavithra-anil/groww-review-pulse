import os
from jinja2 import Template

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #1a1a2e; background: #f5f5f5; }
        .wrapper { background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
        .header { background: linear-gradient(135deg, #00b386, #00d09c); color: white; padding: 28px 24px; }
        .header h1 { margin: 0 0 6px; font-size: 22px; font-weight: 700; }
        .header p { margin: 0; font-size: 13px; opacity: 0.9; }
        .badge { display: inline-block; background: rgba(255,255,255,0.2); padding: 3px 10px; border-radius: 999px; font-size: 11px; margin-top: 8px; }
        .content { padding: 24px; }
        .section-title { font-size: 13px; font-weight: 700; color: #00A87A; text-transform: uppercase; letter-spacing: 1px; margin: 24px 0 12px; }
        .theme-table { width: 100%; border-collapse: collapse; margin-bottom: 8px; }
        .theme-table th { background: #f9f9f9; padding: 10px 12px; text-align: left; font-size: 12px; color: #888; font-weight: 600; border-bottom: 2px solid #f0f0f0; }
        .theme-table td { padding: 12px; border-bottom: 1px solid #f5f5f5; font-size: 13px; vertical-align: top; }
        .theme-name { font-weight: 600; color: #1a1a2e; }
        .urgency-high { color: #e53e3e; font-weight: 700; }
        .urgency-mid { color: #dd6b20; font-weight: 700; }
        .urgency-low { color: #38a169; font-weight: 700; }
        .quote-box { background: #f9f9f9; border-left: 3px solid #00D09C; padding: 10px 14px; margin: 4px 0; border-radius: 0 6px 6px 0; font-style: italic; font-size: 12px; color: #555; line-height: 1.5; }
        .action-item { display: flex; gap: 12px; padding: 10px 0; border-bottom: 1px solid #f5f5f5; font-size: 13px; }
        .action-item:last-child { border-bottom: none; }
        .action-num { background: #00D09C; color: white; width: 22px; height: 22px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; flex-shrink: 0; }
        .cta { text-align: center; padding: 24px; }
        .cta a { background: #00D09C; color: white; padding: 12px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px; }
        .stats-row { display: flex; gap: 16px; margin-bottom: 20px; }
        .stat-box { flex: 1; background: #f9fffe; border: 1px solid #e0f5ef; border-radius: 8px; padding: 12px; text-align: center; }
        .stat-num { font-size: 24px; font-weight: 800; color: #00A87A; }
        .stat-label { font-size: 11px; color: #888; margin-top: 2px; }
        .footer { padding: 16px 24px; background: #f9f9f9; font-size: 11px; color: #999; text-align: center; line-height: 1.6; }
    </style>
</head>
<body>
<div class="wrapper">
    <div class="header">
        <h1>📊 Groww Weekly App Pulse</h1>
        <p>AI-powered review intelligence from Play Store + App Store</p>
        <span class="badge">Week {{ week }} · Auto-generated</span>
    </div>

    <div class="content">

        <!-- Stats Row -->
        <div class="stats-row">
            <div class="stat-box">
                <div class="stat-num">{{ total_reviews }}</div>
                <div class="stat-label">Reviews Analyzed</div>
            </div>
            <div class="stat-box">
                <div class="stat-num">{{ themes|length }}</div>
                <div class="stat-label">Themes Found</div>
            </div>
            <div class="stat-box">
                <div class="stat-num">{{ action_ideas|length }}</div>
                <div class="stat-label">Action Ideas</div>
            </div>
        </div>

        <!-- Top Themes Table -->
        <div class="section-title">🎯 Top Themes This Week</div>
        <table class="theme-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Theme</th>
                    <th>Reviews</th>
                    <th>Urgency</th>
                </tr>
            </thead>
            <tbody>
                {% for theme in themes %}
                <tr>
                    <td>{{ loop.index }}</td>
                    <td>
                        <div class="theme-name">{{ theme.name }}</div>
                        {% if theme.quote %}
                        <div class="quote-box">"{{ theme.quote }}"</div>
                        {% endif %}
                    </td>
                    <td>{{ theme.review_count }}</td>
                    <td>
                        {% if theme.urgency >= 8 %}
                        <span class="urgency-high">{{ theme.urgency }}/10</span>
                        {% elif theme.urgency >= 5 %}
                        <span class="urgency-mid">{{ theme.urgency }}/10</span>
                        {% else %}
                        <span class="urgency-low">{{ theme.urgency }}/10</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <!-- Action Ideas -->
        <div class="section-title">💡 Action Ideas</div>
        {% for idea in action_ideas %}
        <div class="action-item">
            <div class="action-num">{{ loop.index }}</div>
            <div>{{ idea }}</div>
        </div>
        {% endfor %}

        <!-- CTA -->
        <div class="cta">
            <a href="{{ doc_deep_link }}">📄 Read Full Report in Google Docs →</a>
        </div>
    </div>

    <div class="footer">
        ⚠️ This report is generated from public app store reviews for informational purposes only.<br>
        Facts only · No investment advice · No PII collected<br>
        Generated by Groww Review Pulse Agent · {{ week }}
    </div>
</div>
</body>
</html>"""

TEXT_TEMPLATE = """Subject: [Weekly Pulse] Groww — {{ week }} — {{ top_theme }}

Groww Weekly App Pulse
Week: {{ week }} | Reviews analyzed: {{ total_reviews }}

TOP THEMES THIS WEEK
{% for theme in themes %}{{ loop.index }}. {{ theme.name }} ({{ theme.review_count }} reviews | Urgency: {{ theme.urgency }}/10)
   "{{ theme.quote }}"

{% endfor %}
ACTION IDEAS
{% for idea in action_ideas %}{{ loop.index }}. {{ idea }}
{% endfor %}

Read full report: {{ doc_deep_link }}

---
Facts only. No investment advice. No PII collected.
Generated by Groww Review Pulse Agent.
"""


def calculate_urgency(review_count: int, max_count: int) -> float:
    """Calculate urgency score 1-10 based on review volume"""
    if max_count == 0:
        return 5.0
    score = round((review_count / max_count) * 10, 1)
    return max(1.0, min(9.5, score))


def render_email(
    summary: dict,
    doc_deep_link: str = "{DOC_DEEP_LINK}",
) -> tuple[str, str]:
    """
    Render HTML and plain text email from PulseSummary.
    Returns (html_content, text_content)
    """
    themes = summary.get("themes", [])
    action_ideas = summary.get("action_ideas", [])
    week = summary.get("week", "")
    total_reviews = summary.get("total_reviews_analyzed", 0)
    top_theme = themes[0]["name"] if themes else "Weekly Update"

    # Calculate urgency scores
    max_count = max((t["review_count"] for t in themes), default=1)
    for theme in themes:
        theme["urgency"] = calculate_urgency(theme["review_count"], max_count)

    # Render HTML
    html_tmpl = Template(HTML_TEMPLATE)
    html_content = html_tmpl.render(
        week=week,
        total_reviews=total_reviews,
        themes=themes[:3],
        action_ideas=action_ideas,
        doc_deep_link=doc_deep_link,
    )

    # Render plain text
    text_tmpl = Template(TEXT_TEMPLATE)
    text_content = text_tmpl.render(
        week=week,
        total_reviews=total_reviews,
        themes=themes[:3],
        action_ideas=action_ideas,
        doc_deep_link=doc_deep_link,
        top_theme=top_theme,
    )

    return html_content, text_content


def get_email_subject(summary: dict) -> str:
    """Generate email subject line"""
    week = summary.get("week", "")
    themes = summary.get("themes", [])
    top_theme = themes[0]["name"] if themes else "Weekly Update"
    return f"[Weekly Pulse] Groww — {week} — {top_theme}"