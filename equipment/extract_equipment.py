from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple
import logging

from x4shipqueue.models import Ware, EquipmentRow, Production
from x4shipqueue.production.extract_production import  extract_production
from x4shipqueue.config import SIZE_ORDER, UNIQUE_OVERRIDES
from x4shipqueue.util.fs import find_library_files, source_from_path

from x4shipqueue.equipment.parse import (
    parse_wares_from_wares_xml,
    merge_wares,
    detect_category,
    canonical_equipment_id,
    parse_id_parts,
    extract_descriptors,
    normalize_descriptors,
    build_equipment_name,
)

log = logging.getLogger(__name__)

def extract_equipment(
    x4_root: Path,
) -> Dict[str, List[EquipmentRow]]:
    """
    Production data comes ONLY from extract_production()
    (base game + extensions)

    NEW APPROACH:
    - This extractor DOES NOT translate to human-readable strings.
    - It emits raw in-game text refs (e.g. "{20111,5011}") in the name fields.
    - A separate translator step should later replace those raw refs with
      localised human-readable strings using the ttable.

    Returns:
        Dict[str, List[EquipmentRow]] keyed by category:
        Engines, Thrusters, Shields, Weapons, Turrets
    """
    # ------------------------------------------------------------------
    # Load canonical production data (ONCE)
    # ------------------------------------------------------------------
    prod_by_ware, _ = extract_production(x4_root)
    log.debug("Loaded production entries: %d", len(prod_by_ware))

    # ------------------------------------------------------------------
    # Parse wares.xml (definitions only)
    # ------------------------------------------------------------------
    wares_files = find_library_files(x4_root, "wares.xml")

    all_wares: Dict[str, Ware] = {}
    for f in wares_files:
        source = source_from_path(f)
        merge_wares(all_wares, parse_wares_from_wares_xml(f, source))

    # ------------------------------------------------------------------
    # Output buckets
    # ------------------------------------------------------------------
    equipment_by_category: Dict[str, List[EquipmentRow]] = {
        "Engines": [],
        "Thrusters": [],
        "Shields": [],
        "Weapons": [],
        "Turrets": [],
    }

    seen_equipment: set[tuple[str, str]] = set()

     # ------------------------------------------------------------------
    # Main extraction loop
    # ------------------------------------------------------------------
    for ware_id, ware in all_wares.items():
        category = detect_category(ware_id)
        if not category:
            continue

        prod = prod_by_ware.get(ware_id)
        if not prod or prod.transport != "equipment":
            continue

        # ---- Parse ID structure ----
        race, size, mk, _variant = parse_id_parts(ware_id)

        if not race and "_xen_" in ware_id:
            race = "XEN"
        elif not race and "_gen_" in ware_id:
            race = "GEN"

        descriptors = normalize_descriptors(extract_descriptors(ware_id, race))

        # ---- Name handling (RAW refs only) ----
        equipment_name = ware.name_raw or ware.ware_id

        if ware_id in UNIQUE_OVERRIDES:
            equipment_name = UNIQUE_OVERRIDES[ware_id]
        elif equipment_name == ware.ware_id:
            equipment_name = build_equipment_name(
                ware_id=ware_id,
                race=race,
                size=size,
                mk=mk,
                descriptors=descriptors,
            )

        canonical_id = canonical_equipment_id(ware_id)
        dedupe_key = (category, canonical_id)
        if dedupe_key in seen_equipment:
            continue
        seen_equipment.add(dedupe_key)

        # ------------------------------------------------------------------
        # Convert Production.components → RAW name refs
        # ------------------------------------------------------------------
        components: List[Tuple[str, int]] = []
        
        '''
        #removing to bring consistency to components naming based on ware id 
        for mat_id, amount in prod.components:
            mat_ware = all_wares.get(mat_id)
            mat_name = (
                mat_ware.name_raw
                if mat_ware and mat_ware.name_raw
                else mat_id
            )
            components.append((mat_name, amount))
        '''
        # remove following line if above naming is to be reverted.
        components = list(prod.components)
        
        production = Production(
            ware_id=prod.ware_id,
            macro_id=prod.macro_id,
            transport=prod.transport,
            price_min=prod.price_min,
            price_avg=prod.price_avg,
            price_max=prod.price_max,
            build_time=prod.build_time,
            components=components,
        )

        equipment_by_category[category].append(
            EquipmentRow(
                source=ware.source,
                equipment_id=canonical_id,
                equipment_name=equipment_name,
                race=race,
                size=size,
                mk=mk,
                production=production,
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