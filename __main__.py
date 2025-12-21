import argparse
import logging
from pathlib import Path

from x4shipqueue.translation.t_files import load_translation_table
from x4shipqueue.equipment.extract_equipment import extract_equipment
from x4shipqueue.hulls.extract_hulls import extract_hulls
from x4shipqueue.export.excel import export_to_excel
from x4shipqueue.util.fs import effective_root
from x4shipqueue.translation.translate_rows import (
    translate_equipment_rows,
    translate_hull_rows,
    warn_untranslated
)
import x4shipqueue.hulls.extract_hulls as eh

def main() -> int:
    

    ap = argparse.ArgumentParser()
    ap.add_argument("--x4-root", required=True)
    ap.add_argument("--out", default="x4_extract.xlsx")
    ap.add_argument("--language", type=int, default=44)
    ap.add_argument("--include-all-sheet", action="store_true")
    ap.add_argument("--log-level", default="INFO")
    args = ap.parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s %(name)s: %(message)s",
        )
    x4_root = Path(args.x4_root).resolve()
    ttable = load_translation_table(x4_root, args.language)

    equipment = extract_equipment(x4_root)
    hulls = extract_hulls(x4_root)

    # NEW: perform translation
    translate_equipment_rows(equipment, ttable)
    translate_hull_rows(hulls, ttable)
    
    warn_untranslated(
        "Equipment",
        [r.equipment_name for rows in equipment.values() for r in rows],
    )
    warn_untranslated(
        "Hulls",
        [r.hull_name for r in hulls],
    )
    
    export_to_excel(
        Path(args.out),
        equipment,
        hulls,
        args.include_all_sheet,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
