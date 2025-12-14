from __future__ import annotations

import re

# =============================================================================
# Equipment categorisation & parsing
# =============================================================================

# Regex rules used to categorise equipment by ware_id
CATEGORY_RULES = [
    ("Engines",   re.compile(r"^(engine|eng)_[a-z0-9_]+", re.IGNORECASE)),
    ("Thrusters", re.compile(r"^(thruster|thrust)_[a-z0-9_]+", re.IGNORECASE)),
    ("Shields",   re.compile(r"^(shield|shieldgen)_[a-z0-9_]+", re.IGNORECASE)),
    ("Weapons",   re.compile(r"^(weapon)_[a-z0-9_]+", re.IGNORECASE)),
    ("Turrets",   re.compile(r"^(turret)_[a-z0-9_]+", re.IGNORECASE)),
]

# Ordering used for sorting output
SIZE_ORDER = {
    "S": 0,
    "M": 1,
    "L": 2,
    "XL": 3,
}

# =============================================================================
# Equipment name overrides
# =============================================================================

# Unique in-game names that cannot be reliably auto-generated
UNIQUE_OVERRIDES = {
    # Story / special ships
    "shield_gen_m_yacht_01_mk1": "Astrid M Shield",
    "shield_pir_xl_battleship_01_standard_01_mk1": "Erlking XL Shield",
}

# =============================================================================
# Ship role inference (ships.xml)
# =============================================================================

# Priority order when inferring role from tags
ROLE_PRIORITY = [
    "carrier",
    "destroyer",
    "battleship",
    "frigate",
    "corvette",
    "bomber",
    "fighter",
    "scout",
    "miner",
    "trader",
    "freighter",
    "transport",
    "builder",
    "resupply",
    "gunboat",
    "yacht",
    "luxury",
    "envoy",
]

# =============================================================================
# Faction / race token mapping
# =============================================================================

# Mapping from ships.xml faction tokens to internal race codes
FACTION_TOKEN_TO_CODE = {
    "argon": "arg",
    "paranid": "par",
    "teladi": "tel",
    "split": "spl",
    "terran": "ter",
    "boron": "bor",
    "xenon": "xen",
    "vigor": "vig",
    "riptide": "rip",
    "antigone": "ant",
    "pioneers": "pio",
    "common": "gen",
    "commonwealth": "gen",
    "gen": "gen",
}

# Conversion to 3-letter race codes used in output
CODE_TO_RACE3 = {
    "arg": "ARG",
    "par": "PAR",
    "tel": "TEL",
    "spl": "SPL",
    "ter": "TER",
    "bor": "BOR",
    "xen": "XEN",
    "vig": "VIG",
    "rip": "RIP",
    "ant": "ANT",
    "pio": "PIO",
    "gen": "GEN",
}

FACTION_TOKENS = {
    "arg", "ant", "par", "hol", "tri",
    "tel", "min", "bor", "spl",
    "ter", "pio", "xen", "buc",
    "hat", "sca", "kha", "yak",
}

SHIPID_PREFIX_TO_FACTION = {
    "argon": "ARG",
    "antigone": "ANT",
    "paranid": "PAR",
    "holyorder": "HOP",
    "tri": "TRI",
    "teladi": "TEL",
    "ministry": "MIN",
    "split": "SPL",
    "zya": "ZYA",
    "frf": "FRF",
    "terran": "TER",
    "pioneer": "PIO",
    "vig": "VIG",
    "riptide": "RIP",
    "loanshark": "LOA",
    "kaori": "KAO",
    "xenon": "XEN"
    # add more as you encounter them
}

FACTION_TO_RACE = {
    "ARG": "ARG",
    "ANT": "ANT",
    "PAR": "PAR",
    "HOP": "PAR",
    "TRI": "PAR",
    "TEL": "TEL",
    "MIN": "TEL",
    "SPL": "SPL",
    "ZYA": "SPL",
    "FRF": "SPL",
    "TER": "TER",
    "PIO": "TER",
    "ATF": "TER",
    "VIG": "LOA", 
    "RIP": "LOA",
    "KAO": "KAO",
    "XEN": "XEN",
}

ALLOWED_RACES = {"ARG", "ANT", "PAR", "TEL", "SPL", "TER", "LOA", "XEN"}

ALLOWED_FACTIONS = {"ARG", "ANT", "PAR", "TEL", "SPL", "TER", "LOA", "XEN"}
# =============================================================================
# Macro matching helper
# =============================================================================

GENERIC_CLASS_TOKENS = {
    "fighter",
    "scout",
    "trader",
    "miner",
    "carrier",
    "destroyer",
    "frigate",
    "corvette",
    "gunboat",
    "resupplier",
    "builder",
}

# =============================================================================
# Equipment ID parsing helpers
# =============================================================================

# Used in equipment.parse
RACE_CODES = {
    "arg", "ant", "par", "tel", "spl", "ter",
    "pio", "yak", "hoc", "vig", "rip", "bor",
    "xen", "gen",
}

SIZE_CODES = {"s", "m", "l", "xl"}

# engine_par_m_allround_01_mk1 → prefix=engine, rest=par_m_allround_01_mk1
ID_PARTS_RE = re.compile(
    r"^(?P<prefix>engine|thruster|shield|weapon|turret)_(?P<rest>.+)$",
    re.IGNORECASE,
)

# Remove cosmetic numeric variant before Mk
# turret_par_m_shotgun_01_mk1 → turret_par_m_shotgun_mk1
ID_VARIANT_RE = re.compile(r"_(\d{2})_(mk\d+)$", re.IGNORECASE)

# Extract Mk number
MK_RE = re.compile(r"(?:^|_)mk(?P<mk>\d+)(?:_|$)", re.IGNORECASE)

# =============================================================================
# Descriptor normalisation (equipment names)
# =============================================================================

# Default descriptor mapping (best-effort)
DESCRIPTOR_MAP = {
    # Weapons / turrets
    "beam": "Beam Emitter",
    "laser": "Pulse Laser",
    "cannon": "Blast Mortar",
    "burst": "Burst Ray",
    "gatling": "Bolt Repeater",
    "shotgun": "Shard Battery",
    "ion": "Ion Blaster",
    "charge": "Muon Charger",
    "scrapbeam": "Tractor Beam",

    # Engines / thrusters
    "allround": "All-round",

    # Shields / misc
    "standard": "",
}

# Xenon-specific overrides
XENON_DESCRIPTOR_OVERRIDES = {
    "laser": "Impulse Projector",
    "beam": "Plasma Cutter Beam",
    "gatling": "Needler Gun",
}

# Boron-specific overrides
BORON_DESCRIPTOR_OVERRIDES = {
    "laser": "Phase Cannon",
    "beam": "Ion Projector",
    "railgun": "Ion Pulse Railgun",
    "flak": "Ion Atomiser",
}
