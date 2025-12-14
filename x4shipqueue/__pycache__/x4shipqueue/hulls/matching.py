from __future__ import annotations

from typing import Set

from x4shipqueue.config import token_to_faction_code


def _faction_codes_from_tokens(tokens: Set[str]) -> Set[str]:
    codes: Set[str] = set()
    for t in tokens:
        c = token_to_faction_code(t)
        if c:
            codes.add(c)
    return codes


def macro_matches_ship(
    *,
    ship_id: str,
    ship_tokens: Set[str],
    ship_size: str,
    macro_id: str,
    macro_tokens: Set[str],
) -> bool:
    """
    Deterministic hull ↔ macro matcher.

    Required to match:
      1) size token
      2) faction compatibility (when both sides contain faction signals)
      3) family/core token subset match
    """

    # 1) Size must match
    if ship_size.lower() not in macro_tokens:
        return False

    # 2) Faction compatibility (if both provide signals)
    ship_factions = _faction_codes_from_tokens(ship_tokens)
    macro_factions = _faction_codes_from_tokens(macro_tokens)

    if ship_factions and macro_factions:
        if ship_factions.isdisjoint(macro_factions):
            return False

    # 3) Family match (ID-based, not role-based)
    ship_core = set(ship_id.lower().split("_")[1:])
    macro_core = set(macro_id.lower().replace("_macro", "").split("_")[1:])

    # Remove obvious noise
    noise = {"s", "m", "l", "xl", "ship", "macro"}
    ship_core -= noise
    macro_core -= noise

    # Remove numeric tokens
    ship_core = {t for t in ship_core if not t.isdigit()}
    macro_core = {t for t in macro_core if not t.isdigit()}

    return ship_core.issubset(macro_core)
