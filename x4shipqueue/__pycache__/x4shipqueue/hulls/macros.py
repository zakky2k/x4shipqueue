from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, Set

import xml.etree.ElementTree as ET

from x4shipqueue.util.fs import effective_root


def find_ship_macro_files(x4_root: Path) -> list[Path]:
    """
    Finds ship macros under assets/units/size_*/macros (base + extensions).
    """
    root = effective_root(x4_root)
    out: list[Path] = []

    base_units = root / "assets" / "units"
    if base_units.exists():
        out.extend(base_units.glob("size_*/*/macros/*.xml"))
        out.extend(base_units.glob("size_*/macros/*.xml"))
        out.extend(base_units.glob("size_*/macros/**/*.xml"))

    ext_root = root / "extensions"
    if ext_root.exists():
        for ext in ext_root.iterdir():
            units = ext / "assets" / "units"
            if units.exists():
                out.extend(units.glob("size_*/*/macros/*.xml"))
                out.extend(units.glob("size_*/macros/*.xml"))
                out.extend(units.glob("size_*/macros/**/*.xml"))

    seen = set()
    uniq: list[Path] = []
    for p in out:
        rp = str(p.resolve())
        if rp not in seen and p.suffix.lower() == ".xml":
            seen.add(rp)
            uniq.append(p)

    return uniq


def macro_tokens(macro_id: str) -> Set[str]:
    return {
        p for p in macro_id.lower().split("_")
        if not p.isdigit() and p not in {"ship", "macro"}
    }


def derive_variant_label(macro_id: str) -> str:
    m = macro_id.lower()
    if "_01_a_" in m or m.endswith("_01_a_macro"):
        return "Vanguard"
    if "_01_b_" in m or m.endswith("_01_b_macro"):
        return "Sentinel"
    if "_02_a_" in m or m.endswith("_02_a_macro") or "_02_" in m:
        return "E"
    return ""


def is_real_ship_hull_macro(macro_id: str) -> bool:
    """
    True if this macro represents a real, player-buildable ship hull,
    not a drone, deployable, or sub-object.
    """
    mid = macro_id.lower()

    if "drone" in mid:
        return False
    if "terraform" in mid:
        return False
    if "drop" in mid:
        return False
    if "accelerator" in mid or "amplifier" in mid:
        return False
    if "storage" in mid:
        return False
    if "_ark_" in mid:
        return False

    return True


def parse_macro_identification_name(root: ET.Element) -> str:
    """
    Return the RAW in-game name reference for this hull.

    Under the new translation approach, we do NOT resolve via t-files here.
    The returned value is usually "{page,id}" and will be translated later.
    """
    ident = root.find(".//properties/identification")
    if ident is not None:
        raw = ident.get("name")
        if raw:
            return raw

    ident2 = root.find(".//identification")
    if ident2 is not None:
        raw = ident2.get("name")
        if raw:
            return raw

    return root.get("name") or ""


def parse_macro_properties(root: ET.Element) -> Tuple[int, int]:
    """
    Returns (crew_capacity, hull_hp).
    """
    crew = 0
    hull_hp = 0

    props = root.find(".//properties")
    if props is None:
        return (0, 0)

    people = props.find(".//people")
    if people is not None:
        try:
            crew = int(float(people.get("capacity", "0")))
        except Exception:
            crew = 0

    hull = props.find(".//hull")
    if hull is not None:
        for attr in ("max", "value", "hull"):
            if attr in hull.attrib:
                try:
                    hull_hp = int(float(hull.get(attr)))
                    break
                except Exception:
                    pass

    return (crew, hull_hp)


def resolve_component_root(
    x4_root: Path,
    macro_root: ET.Element,
    macro_file: Path,
) -> Optional[ET.Element]:
    """
    Resolve ship component XML referenced by a macro.
    """
    comp = macro_root.find(".//component")
    if comp is None:
        return None

    ref = comp.get("ref")
    if not ref:
        return None

    macro_name = macro_root.get("name", "").lower()
    size_token = None
    for s in ("xl", "l", "m", "s"):
        if f"_{s}_" in macro_name:
            size_token = s
            break

    if not size_token:
        return None

    units_dir = macro_file.parents[1]
    component_path = units_dir / f"{ref}.xml"

    if not component_path.exists():
        return None

    try:
        return ET.parse(component_path).getroot()
    except Exception:
        return None


def count_slots_from_component(root: ET.Element) -> Tuple[int, int, int, int, int]:
    """
    Returns:
      (engine_slots, shield_slots, weapon_slots, turret_m, turret_l)
    """
    eng = shd = wep = tur_m = tur_l = 0

    for conn in root.findall(".//connection"):
        name = (conn.get("name") or "").lower()
        tags = (conn.get("tags") or "").lower()
        blob = f"{name} {tags}"

        if "engine" in blob:
            eng += 1
            continue

        if "shieldgen" in name or " shield" in tags:
            shd += 1
            continue

        if "turret" in blob:
            if " large" in tags or "_l_" in name:
                tur_l += 1
            else:
                tur_m += 1
            continue

        if "weapon" in blob:
            wep += 1

    return eng, shd, wep, tur_m, tur_l
