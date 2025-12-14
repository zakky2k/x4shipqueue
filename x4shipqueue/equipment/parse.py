from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple

from x4shipqueue.models import Ware, Recipe, ShipProduction
from x4shipqueue.util.fs import find_library_files
from x4shipqueue.config import (
    CATEGORY_RULES,
    RACE_CODES,
    SIZE_CODES,
    ID_PARTS_RE,
    ID_VARIANT_RE,
    MK_RE,
    DESCRIPTOR_MAP,
    XENON_DESCRIPTOR_OVERRIDES,
    BORON_DESCRIPTOR_OVERRIDES,
)


# =============================================================================
# Basic helpers
# =============================================================================

def safe_float(v: str) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0


# =============================================================================
# Equipment categorisation
# =============================================================================

def detect_category(ware_id: str) -> str | None:
    """
    Determine equipment category from ware_id.
    """
    for cat, rx in CATEGORY_RULES:
        if rx.match(ware_id):
            return cat
    return None


def canonical_equipment_id(ware_id: str) -> str:
    """
    Remove cosmetic numeric variant before Mk.

    Example:
        turret_par_m_shotgun_01_mk1
        -> turret_par_m_shotgun_mk1
    """
    return ID_VARIANT_RE.sub(r"_\2", ware_id)


# =============================================================================
# ID parsing & name construction
# =============================================================================

def parse_id_parts(ware_id: str) -> Tuple[str, str, str, str]:
    """
    Parse a ware_id into (race, size, mk, variant).

    Returns:
        race: 'ARG', 'TEL', ...
        size: 'S', 'M', 'L', 'XL'
        mk:   'Mk1', 'Mk2', ...
        variant: best-effort descriptor string
    """
    m = ID_PARTS_RE.match(ware_id)
    if not m:
        return ("", "", "", "")

    rest = m.group("rest").lower()
    parts = rest.split("_")

    race = ""
    size = ""
    mk = ""
    variant_parts: List[str] = []

    for p in parts:
        if not race and p in RACE_CODES:
            race = p.upper()
        if not size and p in SIZE_CODES:
            size = p.upper()

    mk_m = MK_RE.search(rest)
    if mk_m:
        mk = f"Mk{mk_m.group('mk')}"

    idx_size = None
    idx_mk = None

    for i, p in enumerate(parts):
        if idx_size is None and p in SIZE_CODES:
            idx_size = i
        if idx_mk is None and p.startswith("mk") and p[2:].isdigit():
            idx_mk = i

    start = idx_size + 1 if idx_size is not None else 0
    end = idx_mk if idx_mk is not None else len(parts)

    for p in parts[start:end]:
        if p in RACE_CODES or p in SIZE_CODES:
            continue
        if p.startswith("mk") and p[2:].isdigit():
            continue
        variant_parts.append(p)

    variant = " ".join(v.capitalize() for v in variant_parts) if variant_parts else ""
    return (race, size, mk, variant)


def extract_descriptors(ware_id: str, race: str) -> List[str]:
    """
    Extract descriptor tokens used to build equipment display names.
    """
    tokens = ware_id.lower().split("_")
    descriptors: List[str] = []

    for t in tokens:
        if race == "BOR" and t in BORON_DESCRIPTOR_OVERRIDES:
            descriptors.append(BORON_DESCRIPTOR_OVERRIDES[t])
        elif race == "XEN" and t in XENON_DESCRIPTOR_OVERRIDES:
            descriptors.append(XENON_DESCRIPTOR_OVERRIDES[t])
        elif t in DESCRIPTOR_MAP:
            descriptors.append(DESCRIPTOR_MAP[t])
        elif t.isalpha() and t not in RACE_CODES and t not in SIZE_CODES:
            descriptors.append(t.capitalize())

    return descriptors


def normalize_descriptors(descriptors: List[str]) -> List[str]:
    """
    Remove duplicates while preserving order.
    """
    seen = set()
    out: List[str] = []
    for d in descriptors:
        if d and d not in seen:
            seen.add(d)
            out.append(d)
    return out


def build_equipment_name(
    ware_id: str,
    race: str,
    size: str,
    mk: str,
    descriptors: List[str],
) -> str:
    """
    Construct a fallback equipment name if no translation exists.
    """
    faction = race
    parts = [faction, size, *descriptors, mk]
    return " ".join(p for p in parts if p)


# =============================================================================
# wares.xml parsing
# =============================================================================

def parse_wares_from_wares_xml(path: Path, source: str) -> Dict[str, Ware]:
    wares: Dict[str, Ware] = {}

    try:
        root = ET.parse(path).getroot()
    except Exception:
        return wares

    for w in root.findall(".//ware"):
        ware_id = w.get("id")
        if not ware_id:
            continue

        name_raw = w.get("name")
        group = w.get("group")
        transport = w.get("transport")

        tags = [t.get("name") for t in w.findall(".//tags/tag") if t.get("name")]
        if not tags:
            tags = [t.get("name") for t in w.findall(".//tag") if t.get("name")]

        wares[ware_id] = Ware(
            source=source,
            ware_id=ware_id,
            name_raw=name_raw,
            group=group,
            transport=transport,
            tags=[t for t in tags if t],
        )

    return wares


# =============================================================================
# Recipe parsing
# =============================================================================

def parse_inline_recipes_from_wares_xml(path: Path) -> List[Recipe]:
    recipes: List[Recipe] = []

    try:
        root = ET.parse(path).getroot()
    except Exception:
        return recipes

    for w in root.findall(".//ware"):
        product_id = w.get("id")
        if not product_id:
            continue

        for prod in w.findall(".//production"):
            method = prod.get("method") or "primary"

            primary = prod.find(".//primary")
            if primary is not None:
                inputs = []
                for inp in primary.findall(".//ware"):
                    wid = inp.get("ware")
                    amt = inp.get("amount")
                    if wid and amt:
                        inputs.append((wid, safe_float(amt)))
                if inputs:
                    recipes.append(Recipe(product_ware_id=product_id, method="primary", inputs=inputs))
                continue

            inputs = []
            for inp in prod.findall(".//ware"):
                wid = inp.get("ware")
                amt = inp.get("amount")
                if wid and amt:
                    inputs.append((wid, safe_float(amt)))
                if inputs:
                    recipes.append(
                        Recipe(
                            product_ware_id=product_id,
                            method=method,
                            inputs=inputs,
                        )
                    )

    return recipes


def parse_recipes_from_modules_xml(path: Path) -> List[Recipe]:
    """
    Parse production recipes from modules.xml.
    """
    recipes: List[Recipe] = []

    try:
        root = ET.parse(path).getroot()
    except Exception:
        return recipes

    for prod in root.findall(".//production"):
        product = prod.get("ware") or prod.get("product") or prod.get("id")
        if not product:
            continue

        primary = prod.find(".//primary")
        if primary is not None:
            inputs = []
            for inp in primary.findall(".//ware"):
                wid = inp.get("ware")
                amt = inp.get("amount")
                if wid and amt:
                    inputs.append((wid, safe_float(amt)))
            if inputs:
                recipes.append(
                    Recipe(
                        product_ware_id=product,
                        method="primary",
                        inputs=inputs,
                    )
                )
            continue

        inputs = []
        for inp in prod.findall(".//ware"):
            wid = inp.get("ware")
            amt = inp.get("amount")
            if wid and amt:
                inputs.append((wid, safe_float(amt)))

        if inputs:
            recipes.append(
                Recipe(
                    product_ware_id=product,
                    method=prod.get("method") or "unknown",
                    inputs=inputs,
                )
            )

    return recipes


def merge_wares(all_wares: Dict[str, Ware], new_wares: Dict[str, Ware]) -> None:
    """
    Merge wares in an X4-accurate way:
      - preserve original source
      - allow later libraries to override attributes
    """
    for wid, new in new_wares.items():
        if wid not in all_wares:
            all_wares[wid] = new
        else:
            old = all_wares[wid]
            all_wares[wid] = Ware(
                source=old.source,
                ware_id=new.ware_id,
                name_raw=new.name_raw or old.name_raw,
                group=new.group or old.group,
                transport=new.transport or old.transport,
                tags=new.tags if new.tags else old.tags,
            )


def build_recipe_map(recipes: List[Recipe]) -> Dict[str, Recipe]:
    """
    Prefer primary recipes if multiple exist.
    """
    out: Dict[str, Recipe] = {}

    for r in recipes:
        if r.product_ware_id not in out:
            out[r.product_ware_id] = r
        else:
            if out[r.product_ware_id].method != "primary" and r.method == "primary":
                out[r.product_ware_id] = r

    return out

def extract_ship_production(x4_root: Path) -> dict[str, ShipProduction]:
    ship_production: dict[str, ShipProduction] = {}

    for wares_file in find_library_files(x4_root, "wares.xml"):
        try:
            root = ET.parse(wares_file).getroot()
        except Exception:
            continue

        for ware in root.findall(".//ware"):
            if ware.get("transport") != "ship":
                continue

            ware_id = ware.get("id")
            if not ware_id:
                continue

            price = ware.find("price")
            production = ware.find("production")
            component = ware.find("component")

            if price is None or production is None or component is None:
                continue

            macro_id = component.get("ref")
            if not macro_id:
                continue

            # Defaults (explicit, no assumptions)
            ecells = 0
            hullparts = 0

            primary = production.find("primary")
            if primary is not None:
                for w in primary.findall("ware"):
                    if w.get("ware") == "energycells":
                        ecells = int(w.get("amount", 0))
                    elif w.get("ware") == "hullparts":
                        hullparts = int(w.get("amount", 0))

            ship_production[macro_id] = ShipProduction(
                ware_id=ware_id,
                macro_id=macro_id,
                price_min=int(price.get("min", 0)),
                price_avg=int(price.get("average", 0)),
                price_max=int(price.get("max", 0)),
                build_time=float(production.get("time", 0)),
                energycells=ecells,
                hullparts=hullparts,
            )

    return ship_production
