from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import xml.etree.ElementTree as ET

from x4shipqueue.models import ShipArchetype
from x4shipqueue.util.fs import find_library_files, source_from_path
from x4shipqueue.config import (
    ROLE_PRIORITY,
    FACTION_TOKEN_TO_CODE,
    CODE_TO_RACE3,
    SHIPID_PREFIX_TO_FACTION,
    FACTION_TO_RACE,
    ALLOWED_RACES
)


def parse_list_attr(value: Optional[str]) -> List[str]:
    """
    Parses attributes like "[argon, hatikvah]" into ["argon", "hatikvah"].
    """
    if not value:
        return []
    s = value.strip()
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        return [x.strip() for x in inner.split(",") if x.strip()]
    return [s]


def normalize_ship_size(size_attr: Optional[str]) -> str:
    """
    ships.xml uses size="ship_l" etc.
    """
    if not size_attr:
        return ""
    s = size_attr.strip().lower()
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
    tags = [t.strip().lower() for t in parse_list_attr(tags_attr)]

    noise = {
        "military", "civilian", "mission",
        "small", "medium", "large", "xl",
        "ship",
    }
    tags = [t for t in tags if t and t not in noise]

    for pri in ROLE_PRIORITY:
        if pri in tags:
            return pri.capitalize()

    return tags[0].capitalize() if tags else ""


def infer_race_from_ship_id(ship_id: str, factions: List[str]) -> str:
    """
    Best-effort: prefer faction list, fallback to ship_id prefix.
    Returns ARG / TEL / etc.
    """
    if factions:
        f0 = factions[0].lower()
        code = FACTION_TOKEN_TO_CODE.get(f0)
        if code:
            return CODE_TO_RACE3.get(code, code.upper())

    tok0 = ship_id.split("_", 1)[0].lower()
    code = FACTION_TOKEN_TO_CODE.get(tok0, tok0[:3])
    return CODE_TO_RACE3.get(code, code.upper())

def ship_tokens(ship_id: str) -> set[str]:
    """
    Token set used for macro matching.
    """
    parts = ship_id.lower().split("_")
    toks = set()

    has_atf = "atf" in parts

    for p in parts:
        # Drop parent faction token when ATF is present
        if has_atf and p == "terran":
            continue

        if p in FACTION_TOKEN_TO_CODE:
            toks.add(FACTION_TOKEN_TO_CODE[p])
        else:
            toks.add(p)

    return toks

def extract_ship_archetypes(x4_root: Path) -> Dict[str, ShipArchetype]:
    """
    Reads ships.xml (base + extensions) and extracts buildable ship archetypes.
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

            # Exclude mass traffic
            if ship_id.lower().startswith("masstraffic_"):
                continue

            cat = ship.find("./category")
            tags_attr = cat.get("tags") if cat is not None else None
            faction_attr = cat.get("faction") if cat is not None else None
            size_attr = cat.get("size") if cat is not None else None

            factions = [x.lower() for x in parse_list_attr(faction_attr)]
            size = normalize_ship_size(size_attr)
            role = infer_role_from_tags(tags_attr)
            #race = infer_race_from_ship_id(ship_id, factions)
            faction = infer_faction_from_shipid(ship_id, factions)
            race = faction_to_race(faction) 
            
            # Preserve first definition if duplicated
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
    
def infer_faction_from_shipid(ship_id: str, factions_from_xml: list[str]) -> str:
    # 1) prefer ship_id prefix (most reliable for HOP/MIN/ZYA/FRF distinctions)
    tok0 = ship_id.split("_", 1)[0].lower()
    if tok0 in SHIPID_PREFIX_TO_FACTION:
        return SHIPID_PREFIX_TO_FACTION[tok0]

    # 2) fallback to ships.xml faction list (e.g. "terran", "argon", etc.)
    if factions_from_xml:
        f0 = factions_from_xml[0].lower()
        # normalize to your same mapping keys if needed
        if f0 in SHIPID_PREFIX_TO_FACTION:
            return SHIPID_PREFIX_TO_FACTION[f0]

    # 3) last resort: first 3 letters
    return tok0[:3].upper()

def faction_to_race(faction_code: str) -> str:
    return FACTION_TO_RACE.get(faction_code, faction_code)