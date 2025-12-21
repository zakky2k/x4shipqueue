from __future__ import annotations

import html
from typing import Dict, Optional, Tuple

# Type alias for {page,id} references in t-files
TextRef = Tuple[int, int]


def clean_x4_display_name(text: str) -> str:
    """
    Normalize X4 display strings to human-readable form.

    Handles all known Egosoft/X4 quirks:
    - HTML/XML entities (e.g. &amp;)
    - Backslash-escaped parentheses: \\( \\)
    - Trailing {page,id} references
    - Surrounding parentheses

    Examples:
        '(Tethys \\(Mineral\\)){20101,32501}' -> 'Tethys (Mineral)'
        '(Theseus Sentinel){20101,31501}'     -> 'Theseus Sentinel'
        'M'                                  -> 'M'
    """
    if not text:
        return ""

    # Unescape XML / HTML entities
    text = html.unescape(text)

    # Unescape Egosoft-style backslash escapes
    text = text.replace(r"\(", "(").replace(r"\)", ")")

    # Remove trailing {page,id} references
    text = text.split("{", 1)[0].strip()

    # Remove surrounding parentheses
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1].strip()

    return text


def parse_text_ref(raw: Optional[str]) -> Optional[TextRef]:
    """
    Parse a string of the form '{page,id}' into a tuple (page, id).

    Returns None if the string is not a valid text reference.
    """
    if not raw:
        return None

    s = raw.strip()
    if not (s.startswith("{") and s.endswith("}")):
        return None

    try:
        page, tid = s[1:-1].split(",", 1)
        return int(page), int(tid)
    except Exception:
        return None


def resolve_display_name(
    raw: Optional[str],
    ttable: Dict[TextRef, str],
    fallback: str = "",
) -> str:
    """
    Resolve an X4 display name to a final, human-readable string.

    Resolution order:
      1) {page,id} lookup in translation table
      2) Inline literal string (cleaned)
      3) Fallback value

    This function is intentionally used everywhere names are displayed
    to guarantee consistent output across equipment, hulls, and components.
    """
    ref = parse_text_ref(raw)
    if ref and ref in ttable:
        return ttable[ref]

    if raw and not raw.strip().startswith("{"):
        return clean_x4_display_name(raw)

    return fallback
