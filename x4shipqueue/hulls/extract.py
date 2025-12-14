from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import xml.etree.ElementTree as ET

from x4shipqueue.models import HullRow, MacroInfo
from x4shipqueue.equipment.parse import extract_ship_production
from x4shipqueue.config import (SIZE_ORDER, ALLOWED_RACES,  ALLOWED_FACTIONS)
from x4shipqueue.util.fs import source_from_path
from x4shipqueue.util.naming import resolve_display_name
from x4shipqueue.hulls.archetypes import (
    extract_ship_archetypes,
    ship_tokens,
)

from x4shipqueue.hulls.macros import (
    find_ship_macro_files,
    parse_macro_identification_name,
    parse_macro_properties,
    resolve_component_root,
    count_slots_from_component,
    macro_tokens,
    derive_variant_label,
    is_real_ship_hull_macro,
)

from x4shipqueue.hulls.matching import (
    score_macro_match,
    is_buildable_hull,
    MIN_MATCH_SCORE,
)


def extract_hulls(
    x4_root: Path,
    ttable: Dict[Tuple[int, int], str],
) -> List[HullRow]:
    """
    Extract buildable ship hulls by joining ships.xml archetypes
    with ship macro definitions.

    Returns one row per ship *variant* (Vanguard / Sentinel / etc).
    """

    # ------------------------------------------------------------------
    # Step 1: Load ship archetypes and production details
    # ------------------------------------------------------------------

    archetypes = extract_ship_archetypes(x4_root)
    ship_production = extract_ship_production(x4_root)

    # ------------------------------------------------------------------
    # Step 2: Parse ship macro XML files
    # ------------------------------------------------------------------

    macro_files = find_ship_macro_files(x4_root)
    macros: List[MacroInfo] = []

    for mf in macro_files:
        source = source_from_path(mf)

        try:
            root = ET.parse(mf).getroot()
        except Exception:
            continue

        macro_id = root.get("name")

        # Some files wrap <macro> inside another root
        if not macro_id:
            macro = root.find(".//macro")
            if macro is not None:
                macro_id = macro.get("name")
                root = macro

        if not macro_id or not macro_id.lower().startswith("ship_"):
            continue
        
        if not is_real_ship_hull_macro(macro_id):
            continue
        
        hull_name = parse_macro_identification_name(root, ttable)
        hull_name = resolve_display_name(hull_name, ttable, fallback=macro_id)

        crew, hull_hp = parse_macro_properties(root)

        component_root = resolve_component_root(x4_root, root, mf)
        if component_root is not None:
            eng, shd, wep, tur_m, tur_l = count_slots_from_component(component_root)
        else:
            eng = shd = wep = tur_m = tur_l = 0

        macros.append(
            MacroInfo(
                source=source,
                macro_id=macro_id,
                hull_name=hull_name,
                crew=crew,
                hull_hp=hull_hp,
                engines=eng,
                shields=shd,
                weapons=wep,
                tur_m=tur_m,
                tur_l=tur_l,
                tokens=macro_tokens(macro_id),
            )
        )

    # ------------------------------------------------------------------
    # Step 3: Join archetypes to macros (scored)
    # ------------------------------------------------------------------

    hull_rows_by_macro: Dict[str, HullRow] = {}
    unmatched: List[Tuple[str, str, List[str]]] = []

    for ship_id, arch in archetypes.items():
        stoks = ship_tokens(ship_id)

        # Skip non-buildable archetypes early
        if not is_buildable_hull(stoks):
            continue
            
        # Skip races we do not want to include
        if arch.race not in ALLOWED_RACES:
            continue
            
        # Skip factions we do not want to include
        if arch.faction not in ALLOWED_FACTIONS:
            continue
    
        scored_matches: List[Tuple[int, MacroInfo]] = []

        for m in macros:
            score, _, _ = score_macro_match(stoks, m.tokens)
            if score >= MIN_MATCH_SCORE:
                scored_matches.append((score, m))

        if not scored_matches:
            unmatched.append((ship_id, arch.source, sorted(stoks)))
            continue

        # Best matches first (stable)
        scored_matches.sort(
            key=lambda x: (-x[0], x[1].macro_id.lower())
        )

        matched_macros = [m for _, m in scored_matches]
        multiple_variants = len(matched_macros) > 1
        prod = ship_production.get(m.macro_id)
        
        for m in matched_macros:
            variant = derive_variant_label(m.macro_id) if multiple_variants else ""

            if m.macro_id not in hull_rows_by_macro:
                hull_rows_by_macro[m.macro_id] = HullRow(
                    source=arch.source,
                    hull_id=ship_id,
                    macro_id=m.macro_id,
                    hull_name=m.hull_name or m.macro_id,
                    faction=arch.faction,
                    race=arch.race,
                    size=arch.size,
                    role = arch.role if arch.role else "Unknown",
                    variant=variant,
                    crew=m.crew,
                    hull_hp=m.hull_hp,
                    engine_slots=m.engines,
                    shield_slots=m.shields,
                    weapon_slots=m.weapons,
                    turret_m=m.tur_m,
                    turret_l=m.tur_l,
                    price_min=prod.price_min if prod else None,
                    price_avg=prod.price_avg if prod else None,
                    price_max=prod.price_max if prod else None,
                    build_time=prod.build_time if prod else None,
                    energycells=prod.energycells if prod else None,
                    hullparts=prod.hullparts if prod else None,
                )

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    if unmatched:
        print("\n[WARN] Unmatched buildable hull archetypes:")
        for ship_id, source, toks in unmatched:
            print(f"  - {ship_id} ({source}) tokens={toks}")

    # ------------------------------------------------------------------
    # Step 4: Friendly sorting
    # ------------------------------------------------------------------

    hull_rows = list(hull_rows_by_macro.values())
    hull_rows.sort(key=sort_key)
    return hull_rows

def sort_key(h: HullRow) -> Tuple[int, str, str, str]:
    source_rank = 0 if h.source == "base" else 1
    size_rank = SIZE_ORDER.get(h.size, 99)
    return (source_rank, h.source, size_rank, h.hull_name)