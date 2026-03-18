import re


def extract_dialogue(prompt_text: str) -> str:
    """Extract all dialogue from a video prompt.

    Pulls text from double-quoted strings (the spoken dialogue)
    and joins them into a single clean subtitle text.

    Example input:
        He speaks: "Some dialogue here."
        CUT TO wide...
        "More dialogue continues."

    Returns: "Some dialogue here. More dialogue continues."
    """
    if not prompt_text:
        return ""

    # Match text inside double quotes (non-greedy)
    matches = re.findall(r'"([^"]+)"', prompt_text)
    if not matches:
        return ""

    # Clean up each fragment and join
    fragments = []
    for m in matches:
        text = m.strip()
        if text:
            fragments.append(text)

    return " ".join(fragments)
