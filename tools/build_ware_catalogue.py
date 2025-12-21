#usage: python -m x4shipqueue.tools.build_ware_catalogue --x4-root C:\Users\zakfo\Documents\Egosoft\_unpacked --log-level INFO
from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import xml.etree.ElementTree as ET

from x4shipqueue.util.fs import find_library_files


# ---------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------

Catalogue = Dict[str, Dict[str, Any]]  # ware_id -> entry


@dataclass(frozen=True)
class ProductionMethod:
    method: str
    time: int
    amount: int
    name: Optional[str]
    tags: List[str]
    resources: Dict[str, int]


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _safe_load_xml(path: Path) -> Optional[ET.Element]:
    try:
        return ET.parse(path).getroot()
    except Exception as e:
        logging.debug("Skipping %s (%s)", path, e)
        return None


def _parse_int(value: Optional[str], *, default: int = 0) -> int:
    if not value:
        return default
    return int(float(value))


def _parse_tags(attr_value: Optional[str]) -> List[str]:
    if not attr_value:
        return []
    s = attr_value.strip()
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1]
        return [p.strip() for p in s.split(",") if p.strip()]
    return [p for p in s.split() if p]


def _parse_primary_resources(prod: ET.Element) -> Dict[str, int]:
    primary = prod.find("primary")
    if primary is None:
        return {}
    resources: Dict[str, int] = {}
    for w in primary.findall("ware"):
        ware_id = w.get("ware")
        amount = _parse_int(w.get("amount"), default=0)
        if ware_id:
            resources[ware_id] = amount
    return resources


def _parse_production(prod: ET.Element) -> ProductionMethod:
    method = prod.get("method") or "default"
    time = _parse_int(prod.get("time"), default=0)
    amount = _parse_int(prod.get("amount"), default=1)
    name = prod.get("name")
    tags = _parse_tags(prod.get("tags"))
    resources = _parse_primary_resources(prod)

    return ProductionMethod(
        method=method,
        time=time,
        amount=amount,
        name=name,
        tags=tags,
        resources=resources,
    )


# ---------------------------------------------------------------------
# Pass 0 — discovery
# ---------------------------------------------------------------------

def discover_wares_files(x4_root: Path) -> List[Path]:
    files = [Path(p) for p in find_library_files(x4_root, "wares.xml")]
    return sorted(files, key=lambda p: str(p).lower())


# ---------------------------------------------------------------------
# Pass 1 — base wares
# ---------------------------------------------------------------------

def pass1_base_wares(roots: Iterable[ET.Element]) -> Catalogue:
    catalogue: Catalogue = {}

    for root in roots:
        for ware in root.findall(".//ware"):
            ware_id = ware.get("id")
            if not ware_id:
                continue

            if ware_id in catalogue:
                continue  # first definition wins

            transport = ware.get("transport") or "other"

            entry: Dict[str, Any] = {
                transport: {
                    "name": ware.get("name"),
                    "description": ware.get("description"),
                    "group": ware.get("group"),
                    "volume": _parse_int(ware.get("volume"), default=0),
                    "tags": _parse_tags(ware.get("tags")),
                },
                "productionMethods": {},
            }

            price = ware.find("price")
            if price is not None:
                entry["price"] = {
                    "min": _parse_int(price.get("min")),
                    "average": _parse_int(price.get("average")),
                    "max": _parse_int(price.get("max")),
                }

            # ship-specific extras (safe to include; ignored elsewhere)
            comp = ware.find("component")
            if comp is not None:
                entry[transport]["component"] = comp.get("ref")

            restriction = ware.find("restriction")
            if restriction is not None:
                entry[transport]["licence"] = restriction.get("licence")

            owners = [o.get("faction") for o in ware.findall("owner") if o.get("faction")]
            if owners:
                entry[transport]["owners"] = owners

            catalogue[ware_id] = entry

    return catalogue


# ---------------------------------------------------------------------
# Pass 2 — inline production
# ---------------------------------------------------------------------

def pass2_inline_production(roots: Iterable[ET.Element], catalogue: Catalogue) -> None:
    for root in roots:
        for ware in root.findall(".//ware"):
            ware_id = ware.get("id")
            if not ware_id or ware_id not in catalogue:
                continue

            pm = catalogue[ware_id]["productionMethods"]

            for prod in ware.findall("production"):
                parsed = _parse_production(prod)

                if parsed.method in pm:
                    raise AssertionError(
                        f"Duplicate inline production method '{parsed.method}' for ware '{ware_id}'"
                    )

                pm[parsed.method] = {
                    "time": parsed.time,
                    "amount": parsed.amount,
                    "name": parsed.name,
                    "resources": parsed.resources,
                }
                if parsed.tags:
                    pm[parsed.method]["tags"] = parsed.tags


# ---------------------------------------------------------------------
# Pass 3 — injected production (<add>)
# ---------------------------------------------------------------------

def pass3_injected_production(roots: Iterable[ET.Element], catalogue: Catalogue) -> None:
    for root in roots:
        for add in root.findall(".//add"):
            productions = add.findall("production")
            if not productions:
                continue

            sel = add.get("sel")
            if not sel or "[@id='" not in sel:
                continue

            ware_id = sel.split("[@id='", 1)[1].split("']", 1)[0]
            if ware_id not in catalogue:
                logging.warning("Injected production for unknown ware '%s'", ware_id)
                continue

            pm = catalogue[ware_id]["productionMethods"]

            for prod in productions:
                parsed = _parse_production(prod)

                if parsed.method in pm:
                    raise AssertionError(
                        f"Injected production overrides existing method "
                        f"'{parsed.method}' for ware '{ware_id}'"
                    )

                pm[parsed.method] = {
                    "time": parsed.time,
                    "amount": parsed.amount,
                    "name": parsed.name,
                    "resources": parsed.resources,
                }
                if parsed.tags:
                    pm[parsed.method]["tags"] = parsed.tags


# ---------------------------------------------------------------------
# Pass 4 — validation
# ---------------------------------------------------------------------

def pass4_validate(catalogue: Catalogue) -> None:
    for ware_id, ware in catalogue.items():
        transport_keys = [k for k in ware if k not in ("price", "productionMethods")]
        if len(transport_keys) != 1:
            raise AssertionError(
                f"Ware '{ware_id}' must have exactly one transport block, found {transport_keys}"
            )

        pm = ware.get("productionMethods")
        if pm is None:
            raise AssertionError(f"Ware '{ware_id}' missing productionMethods block")

        if not pm:
            # Valid: research-only / non-buildable ware
            logging.debug(
                "Ware '%s' has no productionMethods (non-buildable, retained in catalogue)",
                ware_id,
            )
            continue

        for method, data in pm.items():
            if not isinstance(method, str):
                raise AssertionError(f"Invalid method key for ware '{ware_id}'")

            for r, amt in data.get("resources", {}).items():
                if not isinstance(amt, int):
                    raise AssertionError(
                        f"Non-integer resource amount for '{ware_id}:{method}:{r}'"
                    )


# ---------------------------------------------------------------------
# Pass 5 — normalization & output
# ---------------------------------------------------------------------

def normalize_for_output(catalogue: Catalogue) -> Catalogue:
    out: Catalogue = {}

    for ware_id in sorted(catalogue):
        ware = catalogue[ware_id]
        entry: Dict[str, Any] = {}

        for k in sorted(k for k in ware if k not in ("price", "productionMethods")):
            entry[k] = ware[k]

        if "price" in ware:
            entry["price"] = ware["price"]

        pm_out: Dict[str, Any] = {}
        for method in sorted(ware["productionMethods"]):
            m = ware["productionMethods"][method]
            pm_out[method] = {
                **{k: v for k, v in m.items() if k != "resources"},
                "resources": {rk: m["resources"][rk] for rk in sorted(m["resources"])},
            }

        entry["productionMethods"] = pm_out
        out[ware_id] = entry

    return out


# ---------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------

def build_ware_catalogue(x4_root: Path, out_path: Path) -> None:
    files = discover_wares_files(x4_root)
    roots = [r for f in files if (r := _safe_load_xml(f))]

    logging.info("Parsed %d wares.xml files", len(roots))

    catalogue = pass1_base_wares(roots)
    logging.info("Pass 1: %d base wares", len(catalogue))

    pass2_inline_production(roots, catalogue)
    logging.info("Pass 2: inline production")

    pass3_injected_production(roots, catalogue)
    logging.info("Pass 3: injected production")

    pass4_validate(catalogue)
    logging.info("Pass 4: validation OK")

    normalized = normalize_for_output(catalogue)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(normalized, indent=2), encoding="utf-8")

    logging.info("Catalogue written to %s", out_path)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build canonical X4 ware catalogue")
    ap.add_argument("--x4-root", required=True)
    ap.add_argument(
        "--out",
        default="x4shipqueue/data/ware_catalogue.json",
    )
    ap.add_argument("--log-level", default="INFO")
    args = ap.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(levelname)s %(message)s",
    )

    build_ware_catalogue(Path(args.x4_root), Path(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
