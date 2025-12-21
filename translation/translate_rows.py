from __future__ import annotations

import logging
import re
from typing import Dict, List, Tuple

from x4shipqueue.models import EquipmentRow, HullRow

# Matches "{20111,5011}" (whitespace tolerated)
_TREF_RE = re.compile(r"^\{\s*(\d+)\s*,\s*(\d+)\s*\}$")


def _try_parse_tref(value: str) -> Tuple[int, int] | None:
    """
    Parse an X4 text reference like "{20111,5011}" into (page, id).
    Returns None if the string is not a text ref.
    """
    m = _TREF_RE.match(value or "")
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)))


def translate_text(value: str, ttable: Dict[Tuple[int, int], str]) -> str:
    """
    Translate a single string if it is an X4 text reference "{page,id}".
    Otherwise return the original string unchanged.
    """
    tref = _try_parse_tref(value)
    if tref is None:
        return value
    return ttable.get(tref, value)


def translate_components(
    components: List[Tuple[str, int]],
    ttable: Dict[Tuple[int, int], str],
) -> List[Tuple[str, int]]:
    """
    Translate the 'name' part of production components in a stable way.
    """
    return [(translate_text(name, ttable), amount) for name, amount in components]


def translate_equipment_rows(
    equipment_by_category: Dict[str, List[EquipmentRow]],
    ttable: Dict[Tuple[int, int], str],
) -> None:
    """
    In-place translation for equipment rows:
    - EquipmentRow.equipment_name
    - Production.components material names
    """
    for rows in equipment_by_category.values():
        for row in rows:
            row.equipment_name = translate_text(row.equipment_name, ttable)
            #row.production.components = translate_components(row.production.components, ttable)


def translate_hull_rows(
    hulls: List[HullRow],
    ttable: Dict[Tuple[int, int], str],
) -> None:
    """
    In-place translation for hull rows:
    - HullRow.hull_name
    - Production.components material names
    """
    for h in hulls:
        h.hull_name = translate_text(h.hull_name, ttable)
        #h.production.components = translate_components(h.production.components, ttable)


def warn_untranslated(label: str, values: List[str]) -> None:
    """
    Warn if any values still look like "{page,id}" after translation.
    """
    bad = [v for v in values if _try_parse_tref(v) is not None]
    if bad:
        logging.warning(
            "%s: %d untranslated text refs (check t-files)",
            label,
            len(bad),
        )
