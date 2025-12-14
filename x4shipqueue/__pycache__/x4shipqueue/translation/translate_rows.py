from __future__ import annotations

import re
from typing import Dict, List, Tuple

from x4shipqueue.models import EquipmentRow, HullRow

# Matches "{20111,5011}" (whitespace tolerated)
_TREF_RE = re.compile(r"^\{\s*(\d+)\s*,\s*(\d+)\s*\}$")


def _try_parse_tref(value: str) -> Tuple[int, int] | None:
    m = _TREF_RE.match(value or "")
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)))


def translate_equipment_rows(
    equipment_by_category: Dict[str, List[EquipmentRow]],
    ttable: Dict[Tuple[int, int], str],
) -> None:
    """
    In-place translation:
    - EquipmentRow.equipment_name: "{page,id}" -> human text
    - Components list: each component name ref is translated too

    Anything not matching "{page,id}" is left unchanged.
    """
    for rows in equipment_by_category.values():
        for row in rows:
            # Translate equipment name
            tref = _try_parse_tref(row.equipment_name)
            if tref is not None:
                row.equipment_name = ttable.get(tref, row.equipment_name)

            # Translate component display names
            translated_components: list[tuple[str, float]] = []
            for comp_name, amount in row.components:
                comp_tref = _try_parse_tref(comp_name)
                if comp_tref is not None:
                    comp_name = ttable.get(comp_tref, comp_name)
                translated_components.append((comp_name, amount))
            row.components = translated_components


def translate_hull_rows(
    hulls: List[HullRow],
    ttable: Dict[Tuple[int, int], str],
) -> None:
    """
    In-place translation for hull rows.

    This assumes HullRow.hull_name may contain "{page,id}".
    If your hull extractor already sets a proper string, this becomes a no-op.
    """
    for h in hulls:
        tref = _try_parse_tref(h.hull_name)
        if tref is not None:
            h.hull_name = ttable.get(tref, h.hull_name)

def warn_untranslated(label: str, values: list[str]):
    bad = [v for v in values if v.startswith("{") and v.endswith("}")]
    if bad:
        logging.warning(
            "%s: %d untranslated text refs (check t-files)",
            label,
            len(bad),
        )