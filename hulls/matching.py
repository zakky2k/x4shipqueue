from __future__ import annotations

from typing import Set

from x4shipqueue.config import token_to_faction_code



XS_TOKENS = {"xs"}

def is_buildable_ship_macro(tokens: set[str]) -> bool:
    """
    True if this macro represents a physical, buildable ship hull.
    """
    # Must be physical size
    if not tokens.intersection({"s", "m", "l", "xl"}):
        return False

    # Explicitly exclude XS (drones, pods, suits)
    if tokens.intersection(XS_TOKENS):
        return False

    # Exclude structural / story / damage parts
    if tokens.intersection(NON_BUILDABLE_MACRO_TOKENS):
        return False

    return True


def _faction_codes_from_tokens(tokens: Set[str]) -> Set[str]:
    codes: Set[str] = set()
    for t in tokens:
        c = token_to_faction_code(t)
        if c:
            codes.add(c)
    return codes

def find_matching_macro_id(
    *,
    ship_id: str,
    ship_tokens: Set[str],
    ship_size: str,
    macro_token_map: dict[str, Set[str]],
) -> str | None:
    """
    Return the first macro_id that matches this ship archetype.
    """
    for macro_id, macro_tokens in macro_token_map.items():
        if match_ship_to_macro(
            ship_id=ship_id,
            ship_tokens=ship_tokens,
            ship_size=ship_size,
            macro_id=macro_id,
            macro_tokens=macro_tokens,
        ):
            return macro_id
    return None
    
def match_ship_to_macro(
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
        MATCH_STATS["size_fail"] += 1
        return False

    # 2) Faction compatibility (if both provide signals)
    ship_factions = _faction_codes_from_tokens(ship_tokens)
    macro_factions = _faction_codes_from_tokens(macro_tokens)

    if ship_factions and macro_factions:
        if ship_factions.isdisjoint(macro_factions):
            MATCH_STATS["faction_fail"] += 1
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
    
    # --- Role normalisation (critical fix as macros refer tyo trans and ships refer to traders ) ---
    if "trader" in ship_core:
        ship_core.add("trans")
    if "trans" in macro_core:
        macro_core.add("trader")

    if not ship_core.issubset(macro_core):
        MATCH_STATS["core_fail"] += 1
        return False

    MATCH_STATS["success"] += 1
    return True
    
# --- temporary debug instrumentation ---
MATCH_STATS = {
    "size_fail": 0,
    "faction_fail": 0,
    "core_fail": 0,
    "success": 0,
}