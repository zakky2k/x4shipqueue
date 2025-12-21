from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple

from x4shipqueue.models import Ware, Recipe, Production
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
# Equipment categorisation
# =============================================================================

def detect_category(ware_id: str) -> str | None:
    """
    Determine equipment category from ware_id.

    CATEGORY_RULES is authoritative and expected to be
    a list of (category_name, compiled_regex).
    """
    for cat, rx in CATEGORY_RULES:
        if rx.match(ware_id):
            return cat
    return None


def canonical_equipment_id(ware_id: str) -> str:
    """
    Remove cosmetic numeric variant before Mk.

    Example:
        turret_par_m_shotgun_01_mk1 -> turret_par_m_shotgun_mk1
    """
    return ID_VARIANT_RE.sub(r"_\2", ware_id)


# =============================================================================
# ID parsing & name construction
# =============================================================================

def parse_id_parts(ware_id: str) -> Tuple[str, str, str, str]:
    """
    Parse a ware_id into (race, size, mk, variant).

    IMPORTANT:
    This function is AUTHORITATIVE for race, size and mk.
    Callers are expected to overwrite prior values with its output.

    Returns:
        race: 'ARG', 'TEL', ...
        size: 'S', 'M', 'L', 'XL'
        mk:   'Mk1', 'Mk2', ...
        variant: best-effort descriptor string (currently informational)
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
    Extract descriptor tokens used to build fallback equipment names
    when translation refs are missing.
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
    """Remove duplicates while preserving order."""
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
    """Construct a fallback equipment name if no translation ref exists."""
    parts = [race, size, *descriptors, mk]
    return " ".join(p for p in parts if p)


# =============================================================================
# wares.xml parsing
# =============================================================================

def parse_wares_from_wares_xml(path: Path, source: str) -> Dict[str, Ware]:
    """
    Parse wares.xml into Ware objects.

    NOTE:
    Ware.name_raw is preserved verbatim (often "{page,id}").
    Translation is performed later.
    """
    wares: Dict[str, Ware] = {}

    try:
        root = ET.parse(path).getroot()
    except Exception:
        return wares

    for w in root.findall(".//ware"):
        ware_id = w.get("id")
        if not ware_id:
            continue

        wares[ware_id] = Ware(
            source=source,
            ware_id=ware_id,
            name_raw=w.get("name"),
            group=w.get("group"),
            transport=w.get("transport"),
            tags=[t.get("name") for t in w.findall(".//tag") if t.get("name")],
        )

    return wares


def merge_wares(all_wares: Dict[str, Ware], new_wares: Dict[str, Ware]) -> None:
    """
    Merge wares allowing later libraries (DLCs/mods) to override attributes,
    while preserving original source.
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
                tags=new.tags or old.tags,
            )