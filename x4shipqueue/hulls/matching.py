from __future__ import annotations

from typing import Set, Tuple
from x4shipqueue.config import (
    FACTION_TOKENS,
    GENERIC_CLASS_TOKENS 
    )

# ----------------------------------------------------------------------
# Matching configuration
# ----------------------------------------------------------------------


# Abstract / non-buildable modifiers
NON_BUILDABLE_MODIFIERS = {
    "mixed",
    "escort",
    "leader",
    "op",
    "specialops",
    "military",
    "envoy",
    "expeditionary",
    "cypher",
}

# Minimum overlap required for a plausible hull ↔ macro match
MIN_MATCH_SCORE = 3


# ----------------------------------------------------------------------
# Scoring & matching
# ----------------------------------------------------------------------

def score_macro_match(
    ship_tokens: Set[str],
    macro_tokens: Set[str],
) -> Tuple[int, Set[str], Set[str]]:
    """
    Score how well a ship macro matches a ships.xml archetype.

    Role tokens (trader, miner, etc.) are ignored because they do not
    exist in macro IDs.

    Returns:
        score   : number of shared meaningful tokens
        missing : tokens present on ship but not macro
        extra   : tokens present on macro but not ship
    """


    # Enforce faction compatibility if present
    ship_factions = ship_tokens & FACTION_TOKENS
    macro_factions = macro_tokens & FACTION_TOKENS

    if ship_factions and macro_factions and ship_factions.isdisjoint(macro_factions):
        return 0, set(), set()
        
  # Compute overlap
    matched = ship_tokens & macro_tokens

    # ---- NEW RULE ----
    # Remove generic class matches (fighter/scout/etc.)
    meaningful_matches = matched - GENERIC_CLASS_TOKENS

    # If we only matched on size + generic class, reject
    if not meaningful_matches:
        return 0, set(), set()

    missing = ship_tokens - macro_tokens
    extra = macro_tokens - ship_tokens

    score = len(matched)
    return score, missing, extra


# ----------------------------------------------------------------------
# Buildable hull filtering
# ----------------------------------------------------------------------

def is_buildable_hull(tokens: Set[str]) -> bool:
    """
    Determine whether a ships.xml archetype represents
    a buildable ship hull (i.e. should have a ship macro).

    Allows miners, traders, and civilian ships.
    Excludes abstract / job / story archetypes.
    """

    # Must have a physical size
    if not {"s", "m", "l", "xl"} & tokens:
        return False

    # Exclude abstract or synthetic archetypes
    if tokens & NON_BUILDABLE_MODIFIERS:
        return False

    # Exclude numbered job templates (e.g. transport_m_01)
    if any(t.isdigit() for t in tokens):
        return False

    return True
