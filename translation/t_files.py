import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Tuple

from x4shipqueue.util.fs import effective_root
from x4shipqueue.util.naming import clean_x4_display_name


def load_translation_table(x4_root: Path, language_id: int = 44) -> Dict[Tuple[int, int], str]:
    table: Dict[Tuple[int, int], str] = {}

    def ingest(p: Path) -> None:
        try:
            root = ET.parse(p).getroot()
            langs = (
                [root]
                if root.tag == "language" and root.get("id") == str(language_id)
                else root.findall(f".//language[@id='{language_id}']")
            )

            for lang in langs:
                for page in lang.findall("page"):
                    pid = page.get("id")
                    if not pid or not pid.isdigit():
                        continue
                    for t in page.findall("t"):
                        tid = t.get("id")
                        if tid and tid.isdigit() and t.text:
                            table[(int(pid), int(tid))] = clean_x4_display_name(t.text.strip())
        except Exception:
            return

    root = effective_root(x4_root)

    for f in (root / "t").glob("*.xml"):
        ingest(f)

    ext_root = root / "extensions"
    if ext_root.exists():
        for tdir in ext_root.glob("*/t"):
            for f in tdir.glob("*.xml"):
                ingest(f)

    return table
