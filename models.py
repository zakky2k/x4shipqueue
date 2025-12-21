from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional, Set

#Use the below model to supercede any refernce to ship specific ShipProduction 
@dataclass
class Production:
    ware_id: str
    macro_id: str | None
    transport: str # "ship" | "equipment"
    price_min: int | None
    price_avg: int | None
    price_max: int | None
    build_time: float
    # Canonical recipe — applies to ALL wares
    components: list[tuple[str, int]]
    
    
@dataclass
class Ware:
    source: str
    ware_id: str
    name_raw: Optional[str]
    group: Optional[str]
    transport: Optional[str]
    tags: List[str]


@dataclass
class Recipe:
    product_ware_id: str
    method: str
    inputs: List[Tuple[str, int]]


@dataclass
class EquipmentRow:
    source: str
    equipment_id: str
    equipment_name: str
    race: str
    size: str
    mk: str
    production: Production


@dataclass
class ShipArchetype:
    source: str
    ship_id: str
    faction: str
    race: str
    size: str
    role: str
    tokens: set[str]
    # --- optional (defaults AFTER required) ---
    name_code: Optional[str] = None
    group: Optional[str] = None


@dataclass
class HullRow:
    # ship hull details from library/ships.xml and units/macro/macro xml
    source: str
    hull_id: str
    macro_id: str
    hull_name: str 
    faction: str 
    race: str
    size: str
    role: str
    variant: str
    crew: int | None
    hull_hp: int | None
    # slots calculate from shipxxx.xml 
    engine_slots: int | None
    shield_slots: int | None
    weapon_slots: int | None
    turret_m: int | None
    turret_l: int | None
    # ship production (from wares.xml)
    production: Production



@dataclass
class MacroInfo:
    source: str
    macro_id: str
    hull_name: str
    crew: int | None
    hull_hp: int | None
    engines: int | None
    shields: int | None
    weapons: int | None
    tur_m: int | None
    tur_l: int | None
    tokens: Set[str]
    