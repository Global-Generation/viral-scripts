import re


def extract_dialogue(prompt_text: str) -> str:
    """Extract all spoken dialogue from a video prompt/script.

    Strategy: try quoted text first. If too few words (< 10), fall back
    to extracting all spoken lines by stripping stage directions,
    markdown formatting, and metadata.
    """
    if not prompt_text:
        return ""

    # 1) Try quoted dialogue (original approach)
    matches = re.findall(r'"([^"]+)"', prompt_text)
    quoted = " ".join(m.strip() for m in matches if m.strip())
    if len(quoted.split()) >= 10:
        return quoted

    # 2) Fallback: extract all spoken text (strip stage directions + metadata)
    # Cut off metadata section after ---
    text = re.split(r'\n---\n', prompt_text)[0]

    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        # Skip stage directions: **[...]** or [...]
        if re.match(r'^\*{0,2}\[.*\]\*{0,2}$', line):
            continue
        # Skip markdown headers
        if re.match(r'^#+\s', line):
            continue
        # Skip lines that are purely asterisk-wrapped (italic/bold metadata)
        if re.match(r'^\*[^*]+\*$', line):
            continue
        # Skip common prefixes like "Here's the rewritten script:"
        if re.match(r"^here'?s the (rewritten|revised|edited)", line, re.IGNORECASE):
            continue
        lines.append(line)

    result = " ".join(lines)
    # Clean up remaining markdown bold/italic markers
    result = re.sub(r'\*{1,2}', '', result)
    # Remove inline stage directions [like this]
    result = re.sub(r'\[.*?\]', '', result)
    # Remove stray quotes
    result = re.sub(r'["""\u201c\u201d]', '', result)
    # Collapse whitespace
    result = re.sub(r'\s+', ' ', result).strip()
    return result
