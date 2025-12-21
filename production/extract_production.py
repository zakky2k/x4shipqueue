from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple
import xml.etree.ElementTree as ET

from x4shipqueue.models import Production
from x4shipqueue.util.fs import find_library_files
from x4shipqueue.util.xml import safe_int

def extract_production(x4_root: Path):

    """
    Extract production recipes from wares.xml (base + extensions).

    Returns:
        prod_by_ware : ware_id -> Production
        macro_to_ware: macro_id -> ware_id

    Notes:
    - Production is defined ONLY in wares.xml
    - Macro IDs are resolved explicitly via <component ref="...">
    - Canonical invariants 
    -   components = ware IDs, int amounts
    -   float build_time
    -   
    """
    prod_by_ware: dict[str, Production] = {}
    prod_by_macro: dict[str, Production] = {}
    macro_to_ware: Dict[str, str] = {}

    for wares_file in find_library_files(x4_root, "wares.xml"):
        try:
            root = ET.parse(wares_file).getroot()
        except Exception:
            continue

        for ware in root.findall(".//ware"):
            ware_id = ware.get("id")
            transport = (ware.get("transport") or "").lower()

            if not ware_id or transport not in {"ship", "equipment"}:
                continue

            price = ware.find("price")
            production = ware.find("production")
            component = ware.find("component")

            if price is None or production is None:
                continue

            macro_id = component.get("ref") if component is not None else None
            if macro_id:
                macro_to_ware[macro_id] = ware_id

            # ------------------------------
            # Parse production components
            # ------------------------------
            components: list[tuple[str, int]] = []

            primary = production.find("primary")
            if primary is not None:
                for w in primary.findall("ware"):
                    mat_id = w.get("ware")
                    amt = safe_int(w.get("amount"))
                    if mat_id and amt:
                        try:
                            components.append((mat_id, int(amt)))
                        except ValueError:
                            continue

            prod = Production(
                ware_id=ware_id,
                macro_id=macro_id,
                transport=transport,
                price_min=int(price.get("min", 0)),
                price_avg=int(price.get("average", 0)),
                price_max=int(price.get("max", 0)),
                build_time=float(production.get("time", 0)),
                components=components,
            )
            
            prod_by_ware[ware_id] = prod
            if macro_id:
                prod_by_macro[macro_id] = prod
            
    return prod_by_ware, prod_by_macro
