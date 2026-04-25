import json
import os
from groq import Groq
from agent.storage import get_connection, update_run_status

MODEL = "llama-3.1-8b-instant"
MAX_RETRIES = 3


def get_groq_client() -> Groq:
    """Initialize Groq client from environment"""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY not found. Check your .env file."
        )
    return Groq(api_key=api_key)


def call_llm(client: Groq, prompt: str, retries: int = MAX_RETRIES) -> str:
    """Call Groq LLM with retry on rate limit"""
    import time
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if "429" in str(e) and attempt < retries - 1:
                print(f"  Rate limit hit, waiting 60s... (attempt {attempt + 1})")
                time.sleep(60)
            elif attempt < retries - 1:
                time.sleep(5)
            else:
                raise RuntimeError(f"LLM call failed after {retries} attempts: {e}")


def name_theme(client: Groq, keyphrases: list[str], sample_reviews: list[str]) -> str:
    """Ask LLM to give a descriptive name to a theme"""
    reviews_text = "\n".join([f"- {r[:200]}" for r in sample_reviews[:10]])
    keyphrases_text = ", ".join(keyphrases)

    prompt = f"""You are analyzing app store reviews for Groww (an Indian fintech app).

Here are key phrases from a group of similar reviews: {keyphrases_text}

Sample reviews from this group:
{reviews_text}

Give this group a SHORT descriptive name (3-6 words) that captures what users are talking about.
Return ONLY the theme name, nothing else. No quotes, no explanation.

Examples of good names:
- App Performance & Crashes
- Customer Support Issues  
- KYC & Onboarding Problems
- Trading Features Request
- Charges & Fee Complaints"""

    name = call_llm(client, prompt)
    # Clean up any quotes or extra text
    name = name.strip('"\'').strip()
    return name[:60]  # Max 60 chars


def select_quote(
    client: Groq,
    theme_name: str,
    sample_reviews: list[str],
    all_reviews: list[str],
) -> str:
    """Ask LLM to select a verbatim quote, then validate it exists"""
    reviews_text = "\n".join([f"- {r[:300]}" for r in sample_reviews[:15]])

    prompt = f"""You are selecting a representative user quote for the theme: "{theme_name}"

Here are real user reviews:
{reviews_text}

Select ONE short quote (1-2 sentences max) that best represents this theme.
The quote MUST be copied EXACTLY word-for-word from one of the reviews above.
Return ONLY the quote text, nothing else.
Do not add quotation marks."""

    for attempt in range(2):
        quote = call_llm(client, prompt)
        quote = quote.strip('"\'').strip()

        # Validate quote exists in real reviews
        is_valid = any(
            quote.lower() in review.lower()
            for review in all_reviews
            if review
        )

        if is_valid:
            return quote
        elif attempt == 0:
            print(f"  ⚠ Quote not found verbatim, retrying...")
            prompt += "\n\nIMPORTANT: Copy the quote EXACTLY as written in the reviews. Do not paraphrase."

    # Fallback: use medoid review text directly
    print(f"  ⚠ Using fallback quote from medoid review")
    return sample_reviews[0][:200] if sample_reviews else ""


def generate_action_ideas(
    client: Groq,
    themes: list[dict],
) -> list[str]:
    """Generate 3 actionable ideas based on top themes"""
    themes_text = "\n".join([
        f"{i+1}. {t['name']} ({t['review_count']} reviews)"
        for i, t in enumerate(themes[:3])
    ])

    prompt = f"""You are a product manager analyzing user feedback for Groww (Indian fintech app).

Top themes from user reviews this week:
{themes_text}

Generate exactly 3 specific, actionable ideas to address these themes.
Each idea should be 1-2 sentences and mention a specific feature or improvement.

Return ONLY a JSON array of 3 strings like this:
["Action idea 1", "Action idea 2", "Action idea 3"]

No other text, just the JSON array."""

    for attempt in range(MAX_RETRIES):
        response = call_llm(client, prompt)
        try:
            # Clean up response
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            ideas = json.loads(response)
            if isinstance(ideas, list) and len(ideas) >= 3:
                return ideas[:3]
        except json.JSONDecodeError:
            if attempt < MAX_RETRIES - 1:
                print(f"  ⚠ JSON parse failed, retrying...")
                continue

    # Fallback generic ideas
    return [
        "Investigate and fix the most reported app performance issues",
        "Review and improve the customer support response time",
        "Analyze trading feature requests and prioritize top ones",
    ]


def run_summarization(run_id: str, product: str = "groww"):
    """
    Main summarization function:
    - Names each theme using LLM
    - Selects verbatim quotes
    - Generates action ideas
    - Saves PulseSummary JSON
    """
    from dotenv import load_dotenv
    load_dotenv()

    print(f"\n🧠 Starting summarization for run {run_id[:8]}...\n")

    # Load themes from database
    conn = get_connection()
    theme_rows = conn.execute(
        """
        SELECT id, rank, name, review_count, review_ids_json, keyphrases_json
        FROM themes
        WHERE run_id = ?
        ORDER BY rank
        """,
        (run_id,),
    ).fetchall()

    if not theme_rows:
        raise RuntimeError(
            f"No themes found for run {run_id}. Run 'cluster' first."
        )

    # Load all review bodies for quote validation
    all_review_bodies = [
        r[0] for r in conn.execute(
            "SELECT body_clean FROM reviews WHERE product = ?",
            (product,),
        ).fetchall()
        if r[0]
    ]

    conn.close()

    client = get_groq_client()
    named_themes = []

    print("Naming themes and selecting quotes...")

    for row in theme_rows:
        theme_id = row[0]
        rank = row[1]
        review_count = row[3]
        review_ids = json.loads(row[4])
        keyphrases = json.loads(row[5])

        # Get sample review texts for this theme
        conn = get_connection()
        sample_reviews = [
            r[0] for r in conn.execute(
                f"""
                SELECT body_clean FROM reviews
                WHERE id IN ({','.join(['?' for _ in review_ids[:20]])})
                """,
                review_ids[:20],
            ).fetchall()
            if r[0]
        ]
        conn.close()

        # Name the theme
        theme_name = name_theme(client, keyphrases, sample_reviews)
        print(f"  Theme {rank} ({review_count} reviews): \"{theme_name}\"")

        # Select a quote
        quote = select_quote(client, theme_name, sample_reviews, all_review_bodies)
        print(f"  Quote: \"{quote[:80]}...\"" if len(quote) > 80 else f"  Quote: \"{quote}\"")

        # Update theme name in database
        conn = get_connection()
        conn.execute(
            "UPDATE themes SET name = ?, quote = ? WHERE id = ?",
            (theme_name, quote, theme_id),
        )
        conn.commit()
        conn.close()

        named_themes.append({
            "rank": rank,
            "name": theme_name,
            "review_count": review_count,
            "quote": quote,
            "keyphrases": keyphrases,
        })

    # Generate action ideas
    print("\nGenerating action ideas...")
    action_ideas = generate_action_ideas(client, named_themes)
    for i, idea in enumerate(action_ideas, 1):
        print(f"  Action {i}: {idea[:80]}...")

    # Build PulseSummary
    from agent.time_utils import current_iso_week
    pulse_summary = {
        "product": product,
        "week": current_iso_week(),
        "run_id": run_id,
        "themes": named_themes,
        "action_ideas": action_ideas,
        "total_reviews_analyzed": sum(t["review_count"] for t in named_themes),
    }

    # Save to disk
    os.makedirs("data/summaries", exist_ok=True)
    summary_path = f"data/summaries/{run_id}.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(pulse_summary, f, indent=2, ensure_ascii=False)

    # Update run status
    update_run_status(run_id, "summarized")

    print(f"\n✅ Summarization complete!")
    print(f"   {len(named_themes)} themes named")
    print(f"   3 action ideas generated")
    print(f"   PulseSummary saved to {summary_path}")

    return pulse_summary