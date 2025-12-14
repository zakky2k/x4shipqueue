from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Set

import xml.etree.ElementTree as ET

from x4shipqueue.models import ShipArchetype
from x4shipqueue.util.fs import find_library_files, source_from_path
from x4shipqueue.config import CANONICAL_ROLES, token_to_faction_code

# Physical, buildable ship sizes (XS deliberately excluded)
PHYSICAL_SHIP_SIZES = {"S", "M", "L", "XL"}

# Modifiers that indicate abstract, AI-only, or non-buildable archetypes
NON_BUILDABLE_MODIFIERS = {
    "mixed",
    "escort",
    "leader",
    "op",
    "specialops",
    "military",
}

ROLE_NOISE = {
    "military",
    "civilian",
    "mission",
    "ship",
    "small",
    "medium",
    "large",
    "xl",
    "selection",
    "police",
    "plunder",
    "smuggler",
}

ROLE_SPECIALISATIONS = {
    "solid",
    "liquid",
    "container",
}


def parse_list_attr(value: Optional[str]) -> List[str]:
    """
    Parse ships.xml attributes like "[argon, hatikvah]" into lowercase tokens.
    """
    if not value:
        return []

    s = value.strip()
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1]
        return [x.strip().lower() for x in inner.split(",") if x.strip()]

    return [s.lower()]


def normalize_ship_size(size_attr: Optional[str]) -> str:
    """
    Normalize ships.xml size attribute into canonical size codes.
    """
    if not size_attr:
        return ""

    s = size_attr.strip().lower()

    if s.endswith("_xs"):
        return "XS"
    if s.endswith("_s"):
        return "S"
    if s.endswith("_m"):
        return "M"
    if s.endswith("_l"):
        return "L"
    if s.endswith("_xl"):
        return "XL"

    return ""


def infer_role_from_tags(tags_attr: Optional[str]) -> str:
    """
    Infer the canonical semantic ROLE of a ship.
    """
    tags = parse_list_attr(tags_attr)
    meaningful = [t for t in tags if t not in ROLE_NOISE]

    for role in sorted(CANONICAL_ROLES, key=len, reverse=True):
        if role in meaningful:
            return role.capitalize()

    if "miner" in meaningful:
        return "Miner"
    if "trader" in meaningful:
        return "Trader"

    return "Unknown"


def ship_tokens(ship_id: str) -> Set[str]:
    """
    Token set derived from ship_id (lowercase). Used for matching only.
    """
    return set(ship_id.lower().split("_"))


def is_buildable_hull(tokens: Set[str], size: str) -> bool:
    """
    True if this ships.xml archetype represents a physical, buildable hull.
    """
    if size not in PHYSICAL_SHIP_SIZES:
        return False
    if tokens & NON_BUILDABLE_MODIFIERS:
        return False
    if any(t.isdigit() for t in tokens):
        return False
    return True


def infer_faction_from_shipid(ship_id: str, factions_from_xml: List[str]) -> str:
    """
    Determine canonical FACTION code for a ship archetype.

    Priority:
      1) ship_id prefix
      2) ships.xml faction list
      3) fallback prefix-derived
    """
    prefix = ship_id.split("_", 1)[0].lower()
    code = token_to_faction_code(prefix)
    if code:
        return code

    if factions_from_xml:
        code2 = token_to_faction_code(factions_from_xml[0].lower())
        if code2:
            return code2

    return prefix[:3].upper()


def faction_to_race(faction_code: str) -> str:
    """
    In this project, we treat 'race' as the canonical faction family code.
    """
    return faction_code


def extract_ship_archetypes(x4_root: Path) -> Dict[str, ShipArchetype]:
    """
    Read ships.xml (base + extensions) and extract canonical ship archetypes.
    """
    ships_files = find_library_files(x4_root, "ships.xml")
    archetypes: Dict[str, ShipArchetype] = {}

    for f in ships_files:
        source = source_from_path(f)

        try:
            root = ET.parse(f).getroot()
        except Exception:
            continue

        for ship in root.findall(".//ship"):
            ship_id = ship.get("id")
            if not ship_id:
                continue

            cat = ship.find("./category")
            tags_attr = cat.get("tags") if cat is not None else None
            faction_attr = cat.get("faction") if cat is not None else None
            size_attr = cat.get("size") if cat is not None else None

            factions = parse_list_attr(faction_attr)
            size = normalize_ship_size(size_attr)
            role = infer_role_from_tags(tags_attr)

            faction = infer_faction_from_shipid(ship_id, factions)
            race = faction_to_race(faction)

            tokens = ship_tokens(ship_id)
            if not is_buildable_hull(tokens, size):
                continue

            # Preserve first definition across base + DLC
            if ship_id not in archetypes:
                archetypes[ship_id] = ShipArchetype(
                    source=source,
                    ship_id=ship_id,
                    faction=faction,
                    race=race,
                    size=size,
                    role=role,
                )

    return archetypes
