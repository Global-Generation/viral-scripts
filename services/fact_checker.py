"""Fact-checking service — verifies facts using 3 sources: Tavily, Claude, Perplexity."""
import json
import logging
import anthropic
import httpx
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, TAVILY_API_KEY, PERPLEXITY_API_KEY

logger = logging.getLogger(__name__)


def extract_facts(script_text: str) -> list[dict]:
    """Use Claude to extract factual claims from a script."""
    if not ANTHROPIC_API_KEY:
        return []

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": f"""Extract all factual claims from this script that can be verified.
For each claim, output a JSON array of objects with "claim" field.
Only include verifiable facts (numbers, dates, company info, product features, etc.).
Do NOT include opinions, predictions, or subjective statements.
Output ONLY the JSON array, no other text.

Script:
{script_text}"""}],
    )
    text = response.content[0].text.strip()
    # Parse JSON from response
    try:
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        facts = json.loads(text)
        return facts if isinstance(facts, list) else []
    except (json.JSONDecodeError, IndexError):
        logger.error(f"Failed to parse facts JSON: {text[:200]}")
        return []


def verify_with_tavily(claim: str) -> dict:
    """Verify a claim using Tavily search."""
    if not TAVILY_API_KEY:
        return {"source": "tavily", "status": "skipped", "detail": "No API key"}
    try:
        resp = httpx.post(
            "https://api.tavily.com/search",
            json={"api_key": TAVILY_API_KEY, "query": claim, "max_results": 3},
            timeout=15,
        )
        data = resp.json()
        results = data.get("results", [])
        if not results:
            return {"source": "tavily", "status": "no_results", "detail": "No results found"}
        snippets = [{"title": r.get("title", ""), "url": r.get("url", ""),
                      "snippet": r.get("content", "")[:200]} for r in results[:3]]
        return {"source": "tavily", "status": "found", "results": snippets}
    except Exception as e:
        logger.error(f"Tavily verify error: {e}")
        return {"source": "tavily", "status": "error", "detail": str(e)[:200]}


def verify_with_claude(claim: str) -> dict:
    """Verify a claim using Claude's knowledge."""
    if not ANTHROPIC_API_KEY:
        return {"source": "claude", "status": "skipped", "detail": "No API key"}
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": f"""Fact-check this claim. Is it accurate?
Reply with a JSON object: {{"verdict": "true"|"false"|"partially_true"|"uncertain", "explanation": "brief explanation", "correction": "corrected version if false, else null"}}
Output ONLY the JSON, no other text.

Claim: {claim}"""}],
        )
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text)
        return {"source": "claude", "status": "found", "result": result}
    except Exception as e:
        logger.error(f"Claude verify error: {e}")
        return {"source": "claude", "status": "error", "detail": str(e)[:200]}


def verify_with_perplexity(claim: str) -> dict:
    """Verify a claim using Perplexity API (OpenAI-compatible)."""
    if not PERPLEXITY_API_KEY:
        return {"source": "perplexity", "status": "skipped", "detail": "No API key"}
    try:
        from openai import OpenAI
        client = OpenAI(api_key=PERPLEXITY_API_KEY, base_url="https://api.perplexity.ai")
        response = client.chat.completions.create(
            model="sonar",
            messages=[
                {"role": "system", "content": "You are a fact-checker. Verify the claim and provide sources."},
                {"role": "user", "content": f"Is this claim accurate? Provide a brief verdict and any corrections needed:\n\n{claim}"},
            ],
            max_tokens=512,
        )
        text = response.choices[0].message.content
        return {"source": "perplexity", "status": "found", "result": text}
    except Exception as e:
        logger.error(f"Perplexity verify error: {e}")
        return {"source": "perplexity", "status": "error", "detail": str(e)[:200]}


def fact_check_script(script_text: str) -> dict:
    """Full fact-check pipeline: extract facts, verify each with 3 sources, return report.

    Returns dict:
    {
        "facts": [
            {
                "claim": "...",
                "verdict": "verified|false|partial|unverifiable",
                "sources": [tavily_result, claude_result, perplexity_result],
                "correction": "suggested fix if false, else null"
            }
        ],
        "summary": {"verified": N, "false": N, "partial": N, "unverifiable": N}
    }
    """
    facts = extract_facts(script_text)
    if not facts:
        return {"facts": [], "summary": {"verified": 0, "false": 0, "partial": 0, "unverifiable": 0}}

    results = []
    summary = {"verified": 0, "false": 0, "partial": 0, "unverifiable": 0}

    for fact_obj in facts:
        claim = fact_obj.get("claim", "")
        if not claim:
            continue

        # Query all 3 sources
        tavily = verify_with_tavily(claim)
        claude = verify_with_claude(claim)
        perplexity = verify_with_perplexity(claim)

        # Determine overall verdict based on Claude's analysis (primary)
        claude_verdict = "unverifiable"
        correction = None
        if claude.get("status") == "found" and isinstance(claude.get("result"), dict):
            cv = claude["result"].get("verdict", "uncertain")
            correction = claude["result"].get("correction")
            if cv == "true":
                claude_verdict = "verified"
            elif cv == "false":
                claude_verdict = "false"
            elif cv == "partially_true":
                claude_verdict = "partial"

        # Count sources that found results
        source_count = sum(1 for s in [tavily, claude, perplexity] if s.get("status") == "found")
        if source_count == 0:
            claude_verdict = "unverifiable"

        summary[claude_verdict] = summary.get(claude_verdict, 0) + 1

        results.append({
            "claim": claim,
            "verdict": claude_verdict,
            "sources": [tavily, claude, perplexity],
            "correction": correction,
        })

    return {"facts": results, "summary": summary}
