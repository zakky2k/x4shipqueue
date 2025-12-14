from __future__ import annotations

import re
from typing import Dict, Set

# Canonical rule:
# - All factions/races stored in models are UPPERCASE
# - All parsing inputs are lowercase
# - Normalisation happens exactly once (in archetype extraction)

# =============================================================================
# Role categorisation
# =============================================================================

CANONICAL_ROLES = {
    # Combat
    "fighter",
    "heavyfighter",
    "scout",
    "gunboat",
    "corvette",
    "frigate",
    "destroyer",
    "carrier",
    "battleship",
    # Economy
    "trader",
    "miner",
    "builder",
    "resupplier",
}

# =============================================================================
# Equipment categorisation
# =============================================================================

CATEGORY_RULES = [
    ("Engines",   re.compile(r"^(engine|eng)_[a-z0-9_]+", re.IGNORECASE)),
    ("Thrusters", re.compile(r"^(thruster|thrust)_[a-z0-9_]+", re.IGNORECASE)),
    ("Shields",   re.compile(r"^(shield|shieldgen)_[a-z0-9_]+", re.IGNORECASE)),
    ("Weapons",   re.compile(r"^(weapon)_[a-z0-9_]+", re.IGNORECASE)),
    ("Turrets",   re.compile(r"^(turret)_[a-z0-9_]+", re.IGNORECASE)),
]

SIZE_ORDER = {"S": 0, "M": 1, "L": 2, "XL": 3}

# =============================================================================
# Equipment name overrides
# =============================================================================

UNIQUE_OVERRIDES = {
    "shield_gen_m_yacht_01_mk1": "Astrid M Shield",
    "shield_pir_xl_battleship_01_standard_01_mk1": "Erlking XL Shield",
}

# =============================================================================
# Ship identity & matching
# =============================================================================

SIZE_CODES = {"s", "m", "l", "xl"}

SHIP_CLASS_TOKENS = {
    "fighter",
    "heavyfighter",
    "scout",
    "miner",
    "container",
    "trader",
    "gunboat",
    "corvette",
    "frigate",
    "destroyer",
    "carrier",
    "battleship",
    "resupplier",
    "builder",
}

# -----------------------------------------------------------------------------
# Faction → Race normalisation (single source of truth)
# -----------------------------------------------------------------------------

FACTION_ALIASES: Dict[str, str] = {
    # Argon family
    "argon": "ARG",
    "antigone": "ARG",
    "hatikvah": "ARG",

    # Boron family
    "boron": "BOR",

    # Paranid family
    "paranid": "PAR",
    "holyorder": "PAR",
    "tri": "PAR",

    # Teladi family
    "teladi": "TEL",
    "ministry": "TEL",

    # Split family
    "split": "SPL",
    "zya": "SPL",
    "frf": "SPL",
    "court": "SPL",
    "fallensplit": "SPL",

    # Terran family
    "terran": "TER",
    "pioneer": "TER",
    "atf": "TER",

    # Pirate / criminal factions
    "loanshark": "LOA",
    "vigor": "LOA",
    "riptide": "LOA",

    # Edge cases / special
    "yaki": "YAK",
    "xenon": "XEN",
}

# IMPORTANT:
# "FACTION_TOKENS" must represent the *words that can appear in IDs*.
# These are lowercase tokens extracted from ship_id / macro_id.
FACTION_TOKENS: Set[str] = set(FACTION_ALIASES.keys()) | {
    # common 3-letter prefixes found in IDs
    "arg", "ant", "hat",
    "bor",
    "par", "tri", "hol",
    "tel", "min",
    "spl", "zya", "frf",
    "ter", "pio", "atf",
    "yak",
    "xen",
    "vig", "rip", "loa",
}

FACTION_CODES: Set[str] = set(FACTION_ALIASES.values())

ALLOWED_FACTIONS = {
    "ARG",
    "BOR",
    "LOA",
    "PAR",
    "SPL",
    "TEL",
    "TER",
    "XEN",
    "YAK",
}

# If you conceptually treat "race" == canonical faction family in output:
ALLOWED_RACES = ALLOWED_FACTIONS

# =============================================================================
# Equipment ID parsing helpers
# =============================================================================

RACE_CODES = {
    "arg", "ant", "bor", "par", "tel", "spl", "ter",
    "pio", "yak", "vig", "rip", "xen", "gen",
}

ID_PARTS_RE = re.compile(
    r"^(?P<prefix>engine|thruster|shield|weapon|turret)_(?P<rest>.+)$",
    re.IGNORECASE,
)

ID_VARIANT_RE = re.compile(r"_(\d{2})_(mk\d+)$", re.IGNORECASE)
MK_RE = re.compile(r"(?:^|_)mk(?P<mk>\d+)(?:_|$)", re.IGNORECASE)

# =============================================================================
# Descriptor normalisation (equipment names)
# =============================================================================

DESCRIPTOR_MAP = {
    "beam": "Beam Emitter",
    "laser": "Pulse Laser",
    "cannon": "Blast Mortar",
    "burst": "Burst Ray",
    "gatling": "Bolt Repeater",
    "shotgun": "Shard Battery",
    "ion": "Ion Blaster",
    "charge": "Muon Charger",
    "scrapbeam": "Tractor Beam",
    "allround": "All-round",
    "standard": "",
}

XENON_DESCRIPTOR_OVERRIDES = {
    "laser": "Impulse Projector",
    "beam": "Plasma Cutter Beam",
    "gatling": "Needler Gun",
}

BORON_DESCRIPTOR_OVERRIDES = {
    "laser": "Phase Cannon",
    "beam": "Ion Projector",
    "railgun": "Ion Pulse Railgun",
    "flak": "Ion Atomiser",
}

# =============================================================================
# Equipment materials Global + TER
# =============================================================================

MATERIAL_SCHEMAS = {
    "Engines": [
        "Energy Cells",
        "Engine Parts",
        "Antimatter Converters",
        # Terran stack
        "Computronic Substrate",
        "Metallic Microlattice",
        "Silicon Carbide",
    ],

    "Thrusters": [
        "Energy Cells",
        "Engine Parts",
        "Antimatter Converters",
        # Terran stack
        "Computronic Substrate",
        "Metallic Microlattice",
        "Silicon Carbide",
    ],

    "Shields": [
        "Energy Cells",
        "Shield Components",
        "Antimatter Converters",
        "Field Coils",
        # Terran stack
        "Computronic Substrate",
        "Metallic Microlattice",
        "Silicon Carbide",
    ],

    "Weapons": [
        "Energy Cells",
        "Weapon Components",
        "Advanced Electronics",
        "Advanced Composites",
        # Terran stack
        "Computronic Substrate",
        "Metallic Microlattice",
        "Silicon Carbide",
        # Edge cases
        "Ore",
        "Silicon",
    ],

    "Turrets": [
        "Energy Cells",
        "Turret Components",
        "Advanced Electronics",
        "Advanced Composites",
        # Terran stack
        "Computronic Substrate",
        "Metallic Microlattice",
        "Silicon Carbide",
        # Edge cases
        "Ore",
        "Silicon",
    ],
    
    "Hulls": [
        "Energy Cells",
        "Hull Parts",
        # Terran stack
        "Computronic Substrate",
        "Metallic Microlattice",
        "Silicon Carbide",
        # Edge cases
        "Ore",
        "Silicon",
    ],
}


# =============================================================================
# Canonical token → faction mapping helper
# =============================================================================

def token_to_faction_code(token: str) -> str | None:
    """
    Convert a lowercase token found in IDs into a canonical faction code.
    This is intentionally conservative: returns None when unknown.
    """
    t = (token or "").lower()

    if t in FACTION_ALIASES:
        return FACTION_ALIASES[t]

    # 3-letter prefixes used in many IDs
    prefix_map = {
        "arg": "ARG",
        "ant": "ARG",
        "hat": "ARG",
        "bor": "BOR",
        "par": "PAR",
        "tri": "PAR",
        "hol": "PAR",
        "tel": "TEL",
        "min": "TEL",
        "spl": "SPL",
        "zya": "SPL",
        "frf": "SPL",
        "ter": "TER",
        "pio": "TER",
        "atf": "TER",
        "vig": "LOA",
        "rip": "LOA",
        "loa": "LOA",
        "yak": "YAK",
        "xen": "XEN",
    }
    return prefix_map.get(t)
