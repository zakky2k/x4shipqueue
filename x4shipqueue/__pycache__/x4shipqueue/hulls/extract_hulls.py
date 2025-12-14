from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import xml.etree.ElementTree as ET

from x4shipqueue.models import HullRow, MacroInfo
from x4shipqueue.equipment.parse import extract_ship_production
from x4shipqueue.config import SIZE_ORDER, ALLOWED_FACTIONS, ALLOWED_RACES
from x4shipqueue.util.fs import source_from_path

from x4shipqueue.hulls.archetypes import (
    extract_ship_archetypes,
    ship_tokens,
    is_buildable_hull,
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

from x4shipqueue.hulls.matching import macro_matches_ship

print("[DEBUG] extract_hulls() entered")
# ----------------------------------------------------------------------
# Canonical component mapping (ware-id -> display label used in Excel schema)
# ----------------------------------------------------------------------

_WARE_TO_MATERIAL = {
    # Commonwealth
    "energycells": "Energy Cells",
    "hullparts": "Hull Parts",

    # Terran economy stack
    "computronicsubstrate": "Computronic Substrate",
    "metallicmicrolattice": "Metallic Microlattice",
    "siliconcarbide": "Silicon Carbide",

    # Edge cases (e.g. Xenon)
    "ore": "Ore",
    "silicon": "Silicon",
}


def _add_component(components: List[Tuple[str, int]], name: str, amount: int | None) -> None:
    if amount is None:
        return
    try:
        amt = int(amount)
    except Exception:
        return
    if amt <= 0:
        return
    components.append((name, amt))


def _components_from_production(prod) -> List[Tuple[str, int]]:
    """
    Build canonical components list from whatever ShipProduction currently exposes.

    This is intentionally defensive:
    - Some builds expose explicit fields (energycells, hullparts, ...)
    - Some future builds may expose a generic list/dict.
    """
    components: List[Tuple[str, int]] = []

    if not prod:
        return components

    # --- Preferred: explicit known fields (current approach in your project) ---
    _add_component(components, "Energy Cells", getattr(prod, "energycells", None))
    _add_component(components, "Hull Parts", getattr(prod, "hullparts", None))

    # Terran stack
    _add_component(components, "Computronic Substrate", getattr(prod, "computronicsubstrate", None))
    _add_component(components, "Metallic Microlattice", getattr(prod, "metallicmicrolattice", None))
    _add_component(components, "Silicon Carbide", getattr(prod, "siliconcarbide", None))

    # Edge cases
    _add_component(components, "Ore", getattr(prod, "ore", None))
    _add_component(components, "Silicon", getattr(prod, "silicon", None))

    # --- Optional: if a generic structure exists, merge it in safely ---
    # e.g. prod.components = [("energycells", 10), ...] or {"energycells": 10, ...}
    generic = getattr(prod, "components", None)
    if generic:
        if isinstance(generic, dict):
            items = list(generic.items())
        else:
            items = list(generic)

        for ware_id, amount in items:
            if not ware_id:
                continue
            key = str(ware_id).lower()
            label = _WARE_TO_MATERIAL.get(key, str(ware_id))
            _add_component(components, label, amount)

    # Deduplicate by summing (in case both explicit + generic exist)
    summed: Dict[str, int] = {}
    for name, amt in components:
        summed[name] = summed.get(name, 0) + int(amt)

    return [(k, v) for k, v in summed.items() if v > 0]


# ----------------------------------------------------------------------
# Main extraction
# ----------------------------------------------------------------------

def extract_hulls(x4_root: Path) -> List[HullRow]:
    """
    Extract buildable ship hulls by deterministically matching ships.xml archetypes
    to ship hull macros.

    Canonical output:
    - HullRow.hull_name is RAW "{page,id}" where possible (translated later)
    - HullRow.components is canonical [(material_name, amount)] derived from wares.xml
    - No economy transform logic is applied here (Global/Terran/Closed-loop handled later)
    """

    # Step 1: archetypes + production (wares.xml)
    archetypes = extract_ship_archetypes(x4_root)
    ship_production = extract_ship_production(x4_root)
    print("[DEBUG] archetypes:", len(archetypes))
    print("[DEBUG] ship_production:", len(ship_production))
    
    # Step 2: parse hull macros
    macros: List[MacroInfo] = []

    for mf in find_ship_macro_files(x4_root):
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

        print("[DEBUG] macro:", macro_id)
        if not is_real_ship_hull_macro(macro_id):
            continue

        # RAW name ref (translated later)
        hull_name_raw = parse_macro_identification_name(root) or macro_id

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
                hull_name=hull_name_raw,
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

    # Step 3: deterministic archetype ↔ macro matching
    hull_rows_by_macro: Dict[str, HullRow] = {}
    unmatched: List[Tuple[str, str, List[str]]] = []

    for ship_id, arch in archetypes.items():
        stoks = ship_tokens(ship_id)

        # IMPORTANT: your current signature is is_buildable_hull(size, tokens) :contentReference[oaicite:3]{index=3}
        if not is_buildable_hull(arch.size, stoks):
            continue

        if arch.race not in ALLOWED_RACES:
            continue
        if arch.faction not in ALLOWED_FACTIONS:
            continue

        matched_macros: List[MacroInfo] = []
        for m in macros:
            if macro_matches_ship(
                ship_id=ship_id,
                ship_tokens=stoks,
                ship_size=arch.size,
                macro_id=m.macro_id,
                macro_tokens=m.tokens,
            ):
                matched_macros.append(m)

        if not matched_macros:
            unmatched.append((ship_id, arch.source, sorted(stoks)))
            continue

        multiple_variants = len(matched_macros) > 1

        for m in matched_macros:
            # Enforce 1 row per physical macro
            if m.macro_id in hull_rows_by_macro:
                continue

            variant = derive_variant_label(m.macro_id) if multiple_variants else ""
            prod = ship_production.get(m.macro_id)

            components = _components_from_production(prod)

            hull_rows_by_macro[m.macro_id] = HullRow(
                source=arch.source,
                hull_id=ship_id,
                macro_id=m.macro_id,
                hull_name=m.hull_name,  # RAW ref here (translated later)
                faction=arch.faction,
                race=arch.race,
                size=arch.size,
                role=arch.role or "Unknown",
                variant=variant,
                crew=m.crew,
                hull_hp=m.hull_hp,
                engine_slots=m.engines,
                shield_slots=m.shields,
                weapon_slots=m.weapons,
                turret_m=m.tur_m,
                turret_l=m.tur_l,
                price_min=getattr(prod, "price_min", None) if prod else None,
                price_avg=getattr(prod, "price_avg", None) if prod else None,
                price_max=getattr(prod, "price_max", None) if prod else None,
                build_time=int(getattr(prod, "build_time", 0)) if prod and getattr(prod, "build_time", None) else None,
                components=components,
            )

    # Diagnostics (optional)
    if unmatched:
        print("\n[WARN] Unmatched buildable hull archetypes:")
        for ship_id, source, toks in unmatched:
            print(f"  - {ship_id} ({source}) tokens={toks}")

    # Friendly sorting
    hull_rows = list(hull_rows_by_macro.values())
    hull_rows.sort(key=_sort_key)
    return hull_rows


def _sort_key(h: HullRow) -> Tuple[int, str, int, str]:
    source_rank = 0 if h.source == "base" else 1
    size_rank = SIZE_ORDER.get(h.size, 99)
    return (source_rank, h.source, size_rank, h.hull_name)
