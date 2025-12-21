from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from x4shipqueue.config import FACTION_ALIASES
from x4shipqueue.hulls.archetypes import extract_ship_archetypes
from x4shipqueue.hulls.macros import find_ship_macro_files, macro_tokens
from x4shipqueue.hulls.matching import find_matching_macro_id, MATCH_STATS
from x4shipqueue.production.extract_production import extract_production
from x4shipqueue.models import HullRow, Production
from x4shipqueue.util.fs import source_from_path

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------

def tokenise_identifier(value: str) -> Set[str]:
    """
    Canonical tokeniser for ship/macro identifiers.
    - lowercases
    - splits on underscores
    - drops empty segments
    """
    return {t for t in value.lower().split("_") if t}


def _normalise_ship_tokens(tokens: Set[str]) -> Set[str]:
    """
    Apply known canonical normalisations without inventing new config structures.

    Key fix: macros use 'trans' to signify traders/transport.
      - ships.xml archetypes tend to use 'trader' (+ optional 'container')
      - macros use 'trans' (+ optional 'container')
    We allow matching by adding the equivalent role token.
    """
    out = set(tokens)

    # If either side is a transport/trader style ship, make sure both role tokens can exist.
    if "trans" in out:
        out.add("trader")
    if "trader" in out:
        out.add("trans")

    # We intentionally do NOT require/force container/liquid/solid to match.
    # Miners already match fine; traders should match on (race, size, role) primarily.

    return out


def _is_physical_ship_size(tokens: Set[str]) -> bool:
    """
    Filter out non-physical ship sizes (xs, etc).
    In your dataset, physical sizes are S/M/L/XL tokens in identifiers.
    """
    return bool(tokens & {"s", "m", "l", "xl"})


def _looks_non_buildable(tokens: Set[str]) -> bool:
    """
    Conservative exclusion filter for things that are very commonly *not*
    player buildable hulls (drones, suits, plot/story variants, station/ark parts, etc.).
    This is intentionally small to avoid dropping valid ships.

    NOTE: Race gating + role/size gating does most of the heavy lifting.
    """
    non_buildable_markers = {
        "masstraffic",
        "spacesuit",
        "board", "boardingpod",
        "fightingdrone", "miningdrone", "cargodrone", "repairdrone",
        "lasertower",
        "distressbeacon",
        "escapepod",
        "damagebody",
        "part", "struct", "storage", "hab", "prod",
        "story", "plot", "scenario",
    }
    if tokens & non_buildable_markers:
        return True

    # numeric-only tokens are usually variant indices; we do NOT exclude "01" etc here
    # because macros and ships often contain them. So no digit filter.

    return False


# ---------------------------------------------------------------------
# Wares name helper (for translation later)
# ---------------------------------------------------------------------

def _load_name_codes(x4_root: Path) -> Dict[str, str]:
    """
    Map ware_id -> raw name attribute (e.g. "{20101,21601}") for any item parse all wares.xml in libraries.

    This is reusable for:
    - ship wares
    - equipment wares
    - material wares (energycells, hullparts, etc.)

    Translation into human-readable strings is handled later.
    Map ware_id -> name attribute (e.g. "{20101,21601}") for ship name.
    """
    from x4shipqueue.util.fs import find_library_files
    from x4shipqueue.util.xml import parse_xml

    name_by_ware: Dict[str, str] = {}

    for wares_path in find_library_files(x4_root, "wares.xml"):
        root = parse_xml(wares_path).getroot()
        for ware in root.findall(".//ware"):
            ware_id = ware.get("id")
            if not ware_id:
                continue
            name_by_ware[ware_id] = ware.get("name", "") or ""

    return name_by_ware


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------

def extract_hulls(x4_root: Path) -> List[HullRow]:
    """
    Extract buildable hulls by matching ships.xml archetypes to ship _macro.xml files,
    then decorating with ship production info (wares.xml production costs).

    This function is intentionally "canonical":
    - tokens derive from identifiers
    - race gating uses config.FACTION_ALIASES / token_to_faction_code
    - actual matching is delegated to matching.match_ship_to_macro
    - macro enumeration/tokenisation is delegated to macros.find_ship_macro_files / macros.macro_tokens
    - no translation from name codes or materials ware id performed here
    - macro matching is deterministic
    - production recipes are authoritative from wares.xml
    """
    log.debug("[DEBUG] extract_hulls() entered")
    log.debug("extract_hulls loaded from: %s", __file__)

    # 1) Load archetypes (ships.xml)
    archetypes = extract_ship_archetypes(x4_root)
    log.debug("[DEBUG] archetypes: %d", len(archetypes))

    # 2) Load production (wares.xml production)
    _, prod_by_macro = extract_production(x4_root)
    
    ship_macro_hits = [
    k for k, v in prod_by_macro.items()
    #if v.transport == "ship"
]

    log.debug("[DEBUG] ship macro count in prod_by_macro:", len(ship_macro_hits))
    log.debug("[DEBUG] sample ship macros:")
    for k in ship_macro_hits[:10]:
        log.debug("  ", k)
    
    log.debug("[DEBUG] ship_production: %d", len(prod_by_macro))
    log.debug("[DEBUG] prod_by_macro sample keys:")
    for k in list(prod_by_macro.keys())[:10]:
        log.debug("  ", k)

    # 3) Load ship-ware name codes for later translation
    name_by_ware = _load_name_codes(x4_root)

    # 4) Index macros once (no O(N*M) rescans during matching)
    macro_paths = find_ship_macro_files(x4_root)
    macro_token_map: Dict[str, Set[str]] = {}
           
    for mp in macro_paths:
        try:
            # Macro ID is normally the filename stem, e.g. ship_arg_l_destroyer_01_a_macro
            macro_id = mp.stem
            rawToks = macro_tokens(macro_id)
            normToks = _normalise_ship_tokens(rawToks)
            
            #log.debug(f"[DEBUG] macro_id={macro_id}")
            #log.debug(f"[DEBUG] RawToks contents: rawToks{rawToks}")
            #log.debug(f"[DEBUG] NormToks contents: normToks{normToks}")
            
            macro_token_map[macro_id] = normToks
            
        except Exception as e:
            log.debug("Skipping macro file %s due to parse error: %s", mp, e)

    rows: List[HullRow] = []
    
    log.debug(f"[DEBUG] macro candidates={len(macro_token_map)}")
    
    for arch in archetypes.values():
        # Tokenise ship archetype id/group; group is often more “semantic”
        ship_id = arch.ship_id
        ship_group = arch.group or ""
        ship_tokens = tokenise_identifier(ship_group or ship_id)
        ship_tokens = _normalise_ship_tokens(ship_tokens)
        
        #log.debug(f"[DEBUG] trying ship={ship_id} size={arch.size} tokens={ship_tokens}")
       
        
        # Must have a physical size token
        if not _is_physical_ship_size(ship_tokens):
            continue

        # Conservative non-buildable filter
        if _looks_non_buildable(ship_tokens):
            continue

        # Ensure race token is present (some ships.xml IDs use names like "antigone")
        # We *do not* hard-fail here; match_ship_to_macro still gates by FACTION_ALIASES overlap.
        # But we improve the chance of correct matching by injecting race tokens derived
        # from arch.race when available.
        if arch.race:
            # arch.race is typically a 3-letter code (ARG/TEL/TER/...)
            # Convert to known token(s) via FACTION_ALIASES inversion.
            race_code = arch.race.upper()
            for tok, code in FACTION_ALIASES.items():
                if code == race_code:
                    ship_tokens.add(tok)

        # 5) Match this ship to a macro
        ''' log.debug(
            f"[DEBUG] CALL matcher ship={ship_id} "
            f"size={arch.size} "
            f"tokens={ship_tokens} "
            f"macros={len(macro_token_map)}"
        )
        '''
        macro_id = find_matching_macro_id(
            ship_id=arch.ship_id,
            ship_tokens=ship_tokens,
            ship_size=arch.size,
            macro_token_map=macro_token_map,
        )
        if not macro_id:
            continue

        prod = prod_by_macro.get(macro_id)
        
        log.debug(f"[DEBUG] PROD {prod}")
        
        if prod and prod.transport == "ship":
            if not prod.components:
                log.debug(f"[DEBUG] HULL PROD HAS NO COMPONENTS macro={macro_id} ware={prod.ware_id}")
            else:
                log.debug(f"[DEBUG] HULL PROD COMPONENTS macro={macro_id} sample={prod.components[:5]}")
        # Not buildable in shipyard or wrong transport type
        if not prod or prod.transport != "ship":
            continue
            
        '''
        # Removing to bring consistency to components naming based on ware id     
        # Convert production components from ware IDs → name refs
        
        components = []
        for mat_id, amount in prod.components:
            mat_name = name_by_ware.get(mat_id, mat_id)
            components.append((mat_name, amount))
        '''
        components = list(prod.components)
        
        prod = Production(
            ware_id=prod.ware_id,
            macro_id=prod.macro_id,
            transport=prod.transport,
            price_min=prod.price_min,
            price_avg=prod.price_avg,
            price_max=prod.price_max,
            build_time=prod.build_time,
            components=components,
            )

        # 6) Build row (keep numeric fields stable; translation will happen later)
        # Determine size from tokens (prefer XL over L over M over S).
        #if "xl" in ship_tokens:
        #    size = "XL"
        #elif "l" in ship_tokens:
        #    size = "L"
        #elif "m" in ship_tokens:
        #    size = "M"
        #else:
        #    size = "S"

        # Role is not always explicit in ships.xml (e.g., envoy),
        # but matching uses tokens, so we record a best-effort label.
        #role = "Unknown"
        #for candidate in (
        #    "trader", "miner", "fighter", "heavyfighter", "bomber",
         #   "corvette", "frigate", "destroyer", "carrier", "battleship",
        #    "gunboat", "builder", "resupplier", "scout"
        #):
        #    if candidate in ship_tokens:
        #        role = candidate.title() if candidate != "heavyfighter" else "HeavyFighter"
        #        break

        # Variant: keep it simple (often "a"/"b" in macro id)
        variant = ""
        for v in ("a", "b", "c", "d"):
            if f"_{v}_" in f"_{macro_id}_":
                variant = v.upper()
                break

        hull_name_code = name_by_ware.get(prod.ware_id, "") if hasattr(prod, "ware_id") else ""

        rows.append(
            HullRow(
                source=arch.source,
                hull_id=ship_id,
                macro_id=macro_id,
                hull_name=hull_name_code or "Unknown Ship",
                faction=(arch.faction or arch.race or "").upper(),
                race=(arch.race or "").upper(),
                size=arch.size,
                role=arch.role or "Unknown",
                variant=variant,
                crew=0,
                hull_hp=0,
                engine_slots=0,
                shield_slots=0,
                weapon_slots=0,
                turret_m=0,
                turret_l=0,
                production=prod,
                )
        )
    log.debug("[DEBUG] Hull↔Macro match statistics:")
    for k, v in MATCH_STATS.items():
        log.debug(f"  {k}: {v}")
    return rows
