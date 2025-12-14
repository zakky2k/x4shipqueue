from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from x4shipqueue.models import Ware, Recipe, EquipmentRow
from x4shipqueue.config import (
    CATEGORY_RULES,
    SIZE_ORDER,
    UNIQUE_OVERRIDES,
   )
from x4shipqueue.util.fs import find_library_files, source_from_path
from x4shipqueue.util.naming import resolve_display_name

from x4shipqueue.equipment.parse import (
    parse_wares_from_wares_xml,
    parse_inline_recipes_from_wares_xml,
    parse_recipes_from_modules_xml,
    merge_wares,
    build_recipe_map,
    detect_category,
    canonical_equipment_id,
    parse_id_parts,
    extract_descriptors,
    normalize_descriptors,
    build_equipment_name,
)


def extract_equipment(
    x4_root: Path,
    ttable: Dict[Tuple[int, int], str],
) -> Dict[str, List[EquipmentRow]]:
    """
    Extract equipment production recipes from wares.xml + modules.xml
    (base game + extensions), grouped into UI-relevant categories.

    Returns:
        Dict[str, List[EquipmentRow]] keyed by category:
        Engines, Thrusters, Shields, Weapons, Turrets
    """

    # ------------------------------------------------------------------
    # Discover relevant library files
    # ------------------------------------------------------------------

    wares_files = find_library_files(x4_root, "wares.xml")
    modules_files = find_library_files(x4_root, "modules.xml")

    all_wares: Dict[str, Ware] = {}
    all_recipes: List[Recipe] = []

    # ------------------------------------------------------------------
    # Parse wares.xml (definitions + inline recipes)
    # ------------------------------------------------------------------

    for f in wares_files:
        source = source_from_path(f)

        new_wares = parse_wares_from_wares_xml(f, source)
        merge_wares(all_wares, new_wares)

        all_recipes.extend(parse_inline_recipes_from_wares_xml(f))

    # ------------------------------------------------------------------
    # Parse modules.xml (additional production recipes)
    # ------------------------------------------------------------------

    for f in modules_files:
        all_recipes.extend(parse_recipes_from_modules_xml(f))

    recipe_map = build_recipe_map(all_recipes)

    # ------------------------------------------------------------------
    # Prepare output structure
    # ------------------------------------------------------------------

    equipment_by_category: Dict[str, List[EquipmentRow]] = {
        "Engines": [],
        "Thrusters": [],
        "Shields": [],
        "Weapons": [],
        "Turrets": [],
    }

    # Used to deduplicate cosmetic numeric variants (_01, _02, etc.)
    seen_equipment: set[tuple[str, str]] = set()

    # ------------------------------------------------------------------
    # Main extraction loop
    # ------------------------------------------------------------------

    for ware_id, ware in all_wares.items():
        category = detect_category(ware_id)
        if not category:
            continue

        recipe = recipe_map.get(ware_id)
        if not recipe:
            continue

        # ---- Parse structural parts from ID ----
        race, size, mk, _variant = parse_id_parts(ware_id)

        # Fallback race detection (Xenon / Generic)
        if not race and "_xen_" in ware_id:
            race = "XEN"
        elif not race and "_gen_" in ware_id:
            race = "GEN"

        # ---- Descriptor handling ----
        descriptors = normalize_descriptors(
            extract_descriptors(ware_id, race)
        )

        # ---- Resolve in-game name ----
        equipment_name = resolve_display_name(
            ware.name_raw,
            ttable,
            fallback=ware.ware_id,
        )

        # ---- Hard overrides (unique ships / story assets) ----
        if ware_id in UNIQUE_OVERRIDES:
            equipment_name = UNIQUE_OVERRIDES[ware_id]

        # ---- Auto-generated fallback name ----
        elif equipment_name == ware.ware_id:
            equipment_name = build_equipment_name(
                ware_id=ware_id,
                race=race,
                size=size,
                mk=mk,
                descriptors=descriptors,
            )

        # ---- Canonical ID for de-duplication ----
        canonical_id = canonical_equipment_id(ware_id)
        dedupe_key = (category, canonical_id)
        if dedupe_key in seen_equipment:
            continue
        seen_equipment.add(dedupe_key)

        # ---- Resolve component names ----
        components: List[Tuple[str, float]] = []
        for comp_id, amount in recipe.inputs:
            comp_ware = all_wares.get(comp_id)
            comp_name = resolve_display_name(
                comp_ware.name_raw if comp_ware else None,
                ttable,
                fallback=comp_id,
            )
            components.append((comp_name, amount))

        # ---- Final row ----
        equipment_by_category[category].append(
            EquipmentRow(
                source=ware.source,
                equipment_id=canonical_id,
                equipment_name=equipment_name,
                race=race,
                size=size,
                mk=mk,
                components=components,
            )
        )

    # ------------------------------------------------------------------
    # Stable sorting (UI-friendly)
    # ------------------------------------------------------------------

    def sort_key(row: EquipmentRow) -> Tuple[int, str, int, str, str]:
        source_rank = 0 if row.source == "base" else 1
        size_rank = SIZE_ORDER.get(row.size, 99)
        return (
            source_rank,
            row.source,
            size_rank,
            row.mk,
            row.equipment_name,
        )

    for cat in equipment_by_category:
        equipment_by_category[cat].sort(key=sort_key)

    return equipment_by_category
