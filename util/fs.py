from pathlib import Path
from typing import List


def effective_root(x4_root: Path) -> Path:
    return x4_root / "_unpacked" if (x4_root / "_unpacked").exists() else x4_root


def source_from_path(p: Path) -> str:
    if "extensions" in p.parts:
        return p.parts[p.parts.index("extensions") + 1]
    return "base"


def find_library_files(x4_root: Path, filename: str) -> List[Path]:
    root = effective_root(x4_root)
    out: List[Path] = []

    base = root / "libraries" / filename
    if base.exists():
        out.append(base)

    ext_root = root / "extensions"
    if ext_root.exists():
        for ext in sorted(ext_root.iterdir()):
            lib = ext / "libraries" / filename
            if lib.exists():
                out.append(lib)

    return out
