import argparse
import logging
from pathlib import Path

from x4shipqueue.translation.t_files import load_translation_table
from x4shipqueue.equipment.extract import extract_equipment
from x4shipqueue.hulls.extract import extract_hulls
from x4shipqueue.export.excel import export_to_excel
from x4shipqueue.util.fs import effective_root


def main() -> int:
    logging.basicConfig(level=logging.INFO)

    ap = argparse.ArgumentParser()
    ap.add_argument("--x4-root", required=True)
    ap.add_argument("--out", default="x4_extract.xlsx")
    ap.add_argument("--language", type=int, default=44)
    ap.add_argument("--include-all-sheet", action="store_true")
    ap.add_argument("--max-components", type=int, default=8)
    args = ap.parse_args()

    x4_root = Path(args.x4_root).resolve()
    ttable = load_translation_table(x4_root, args.language)

    equipment = extract_equipment(x4_root, ttable)
    hulls = extract_hulls(x4_root, ttable)

    export_to_excel(
        Path(args.out),
        equipment,
        hulls,
        args.include_all_sheet,
        args.max_components,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
