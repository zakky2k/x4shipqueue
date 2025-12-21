# Data Contract – X4 Ship Queue

This document defines the **data contracts, guarantees, and invariants** for the
X4 Ship Queue project.

It describes what data structures exist, how they are produced, what guarantees
they provide, and how consumers are expected to interact with them.

This document is normative.

---

## 1. Purpose

The data contract exists to:

- Prevent ambiguity about data ownership and responsibility
- Define canonical sources of truth
- Enable safe refactoring and extension
- Prevent consumers from making invalid assumptions
- Ensure consistency across tools, exports, and calculations

If a behaviour or structure is not documented here, it must not be relied upon.

---

## 2. Canonical data sources

### 2.1 Raw game data (non-canonical)

Raw X4 XML files are considered **discovery inputs only**.

Examples:
- libraries/wares.xml
- extensions/*/libraries/wares.xml

Rules:
- Raw XML may change between game versions
- Raw XML must not be consumed directly by application logic
- Raw XML parsing is restricted to the discovery phase

---

### 2.2 Canonical Ware Production Model (CWPM)

The CWPM is the **single canonical representation** of production data.

File:
- x4shipqueue/data/ware_catalogue.json

Built by:
- tools/build_ware_catalogue.py

Rules:
- CWPM is the only approved source for production data
- All downstream consumers must read from CWPM
- CWPM is deterministic and reproducible
- CWPM merges base and extension data

Detailed specification is defined in:
- docs/CWPM.md

---

## 3. CWPM guarantees

CWPM guarantees the following invariants:

- Each ware_id appears exactly once
- Each ware has exactly one transport block
- productionMethods always exists (may be empty)
- Production resources are expressed as ware IDs
- Resource quantities are integers
- Production methods preserve XML semantics
- Injected production is merged, not flattened
- No translation or localisation is applied

---

## 4. Buildability contract

CWPM explicitly separates **existence** from **buildability**.

Definitions:

- A ware exists if it appears in CWPM
- A ware is buildable only if productionMethods is non-empty

Rules:

- Consumers must explicitly filter non-buildable wares
- Consumers must not infer buildability from:
  - transport type
  - component presence
  - price presence
- Research, unlock, and non-player wares are valid CWPM entries

---

## 5. Production method contract

Production methods are defined per ware.

Rules:

- Method names are preserved exactly as defined in XML
- Consumers must explicitly select a production method
- No implicit fallback between methods is allowed
- Consumers must assume multiple methods may exist
- Unknown methods must not cause failures

Examples of method names include:
- default
- terran
- teladi
- closedloop
- xenon

---

## 6. Resource contract

Production resources follow strict rules:

- Resource keys are always ware IDs
- Resource quantities are always integers
- No unit conversion occurs at the CWPM level
- No translation of resource names occurs at the CWPM level

Consumers are responsible for:
- Aggregation
- Presentation
- Translation
- Unit interpretation (if any)

---

## 7. Price contract

Price data is optional and informational.

Rules:

- Price data may be missing
- Price data does not affect production calculations
- Consumers must not rely on price presence
- Prices must not be used to infer buildability

---

## 8. Transport contract

Transport is encoded structurally, not as a field.

Rules:

- Transport is represented by a single top-level key
- There must be exactly one transport block per ware
- Transport values are not normalised
- Consumers must not assume a closed set of transport values

---

## 9. Consumer responsibilities

All consumers of CWPM must:

- Treat CWPM as read-only
- Avoid parsing raw XML
- Explicitly select production methods
- Explicitly filter buildable wares
- Handle unknown methods and transports gracefully
- Avoid hardcoding material or method lists

Violations of these rules are considered contract breaches.

---

## 10. Validation and error handling

Validation occurs at multiple levels:

- Structural validation during CWPM build
- Semantic validation during schema derivation
- Context-specific validation during consumption

Rules:

- CWPM build failures are fatal
- Derivation failures must be explicit
- Silent data corruption is not acceptable

---

## 11. Extensibility guarantees

The data contract is designed to support:

- New DLC economies
- Modded production methods
- New ware transports
- New resource types
- New consumers and outputs

No consumer may assume:
- A fixed set of methods
- A fixed set of resources
- A fixed set of transports

---

## 12. Relationship to other documents

This document must be read alongside:

- CWPM.md – canonical production model
- PIPELINE.md – execution and responsibility boundaries

Together, these documents define the architectural contract of the project.

---

## 13. Canonical statement

If data is not present in CWPM, it is not canonical production data.

Any deviation from this contract must be explicitly documented and justified.


## Source Game Files samples- read only by build_ware_catalogue.py

- wares.xml
  - Defines wares (ships, equipment, materials) and their production recipes.
  - Production recipes live under:
    <ware ...>
      <production ...>
        <primary>
          <ware ware="material_id" amount="N" />
        </primary>
      </production>
      <component ref="some_macro_id" />
    </ware>

- ships.xml
  - Defines ship archetypes: id, group, tags, faction list, and size.

- assets/units/.../macros/*.xml
  - Defines macro files referenced by wares.xml <component ref="..."> and used for hull matching.

- t/*.xml (t-files)
- Translation table for {page,id} references.

## Source Game Files Samples
a) wares.xml

	a.1) ship hulls ware
		a.1.1) TER - fighter - Terrran - player buildable - path: _unpacked\extensions\ego_dlc_terran\libraries
			<ware id="ship_ter_s_fighter_01_a" name="{20101,62201}" description="{20101,62211}" transport="ship" volume="1" tags="ship">
			  <price min="327573" average="385380" max="443187" />
			  <production time="12" amount="1" method="default" name="{20206,901}">
				<primary>
				  <ware ware="computronicsubstrate" amount="9" />
				  <ware ware="energycells" amount="66" />
				  <ware ware="metallicmicrolattice" amount="30" />
				</primary>
			  </production>
			  <component ref="ship_ter_s_fighter_01_a_macro" />
			  <restriction licence="militaryship" />
			  <owner faction="pioneers" />
			  <owner faction="terran" />
			</ware>
			
		a.1.2) TEL - miner - Teladi - Player buildable - path: _unpacked\libraries 
			<ware id="ship_tel_l_miner_liquid_02_a" name="{20101,20907}" description="{20101,20917}" transport="ship" volume="1" tags="ship">
				<price min="1537750" average="1922187" max="2306625" />
				<production time="115" amount="1" method="default" name="{20206,101}">
				  <primary>
					<ware ware="energycells" amount="650" />
					<ware ware="hullparts" amount="1720" />
				  </primary>
				</production>
				<component ref="ship_tel_l_miner_liquid_02_a_macro" />
				<restriction licence="generaluseship" />
				<owner faction="hatikvah" />
				<owner faction="ministry" />
				<owner faction="teladi" />
			</ware>
		
	a.2) equipment ware
		<ware id="engine_ter_m_allround_01_mk3" name="{20107,2744}" description="{20107,2742}" transport="equipment" volume="1" tags="engine equipment">
		  <price min="690560" average="767289" max="844018" />
		  <production time="15" amount="1" method="default" name="{20206,901}">
			<primary>
			  <ware ware="computronicsubstrate" amount="31" />
			  <ware ware="energycells" amount="600" />
			  <ware ware="metallicmicrolattice" amount="193" />
			  <ware ware="siliconcarbide" amount="31" />
			</primary>
		  </production>
		  <component ref="engine_ter_m_allround_01_mk3_macro" />
		  <restriction licence="generaluseequipment" />
		  <use threshold="0.7" />
		  <owner faction="pioneers" />
		  <owner faction="terran" />
		</ware>

b) ships.xml

b.1) ARG - Argon - basegame - player buildable 

  <ship id="argon_builder_xl" group="arg_builder_xl">
    <category tags="[builder, mission]" faction="[argon, hatikvah]" size="ship_xl"/>
    <pilot>
      <select faction="argon" tags="traderpilot"/>
    </pilot>
    <drop ref="ship_large_civilian"/>
    <people ref="argon_freighter_crew"/>
  </ship>
  
b.2) BOR - Boron - _unpacked\extensions\ego_dlc_boron\libraries - player buildable

  <ship id="boron_miner_solid_l" group="bor_miner_solid_l">
    <category tags="[miner, solid, mission]" faction="boron" size="ship_l" />
    <pilot>
      <select faction="boron" tags="traderpilot" />
    </pilot>
    <basket basket="minerals" />
    <drop ref="ship_large_civilian" />
    <people ref="boron_freighter_crew" />
  </ship>
  
c) ship macros 

	c.1) ARG - Argon - Tranport - base game - Player Buildable - path: _unpacked\assets\units\size_l\macros\ship_arg_l_trans_container_01_a_macro.xml
	<macros>
	  <macro name="ship_arg_l_trans_container_01_a_macro" class="ship_l">
		<component ref="ship_arg_l_trans_container_01" />
		<properties>
		  <identification name="{20101,11202}" basename="{20101,11201}" makerrace="argon" description="{20101,11212}" variation="{20111,1101}" shortvariation="{20111,1103}" icon="ship_l_freighter_01" />
		  <software>
			<software ware="software_dockmk2" compatible="1" />
			<software ware="software_flightassistmk1" default="1" />
			<software ware="software_scannerlongrangemk1" default="1" />
			<software ware="software_scannerlongrangemk2" compatible="1" />
			<software ware="software_scannerobjectmk1" default="1" />
			<software ware="software_scannerobjectmk2" compatible="1" />
			<software ware="software_targetmk1" compatible="1" />
			<software ware="software_trademk1" default="1" />
		  </software>
		  <jerk>
			<forward accel="0.2" decel="0.8" ratio="3" />
			<forward_boost accel="0.2" ratio="3" />
			<forward_travel accel="0.4" decel="0.9" ratio="3" />
			<strafe value="0.4" />
			<angular value="0.25" />
		  </jerk>
		  <explosiondamage value="800" shield="4000" />
		  <storage missile="30" unit="10" />
		  <hull max="57000" />
		  <secrecy level="1" />
		  <steeringcurve>
			<point position="1.01" value="1" />
			<point position="1.2" value="0.9" />
			<point position="1.5" value="0.8" />
			<point position="2.1" value="0.45" />
			<point position="2.4" value="0.28" />
			<point position="2.7" value="0.2" />
		  </steeringcurve>
		  <purpose primary="trade" />
		  <people capacity="110" />
		  <sounds>
			<shipdetail ref="shipdetail_ship_l_01" />
		  </sounds>
		  <physics mass="440.933">
			<inertia pitch="175.799" yaw="175.799" roll="140.64" />
			<drag forward="120" reverse="350" horizontal="65" vertical="65" pitch="135" yaw="135" roll="100" />
			<accfactors forward="0.75" reverse="0.75" horizontal="0.85" vertical="0.85" />
		  </physics>
		  <thruster tags="large" />
		  <ship type="freighter" />
		</properties>
		<connections>
		  <connection ref="con_cockpit">
			<macro ref="bridge_arg_l_01_macro" connection="con_cockpit" />
		  </connection>
		  <connection ref="con_dockarea_arg_s_ship_01">
			<macro ref="dockarea_arg_s_ship_01_macro" connection="Connection01" />
		  </connection>
		  <connection ref="con_dock_xs">
			<macro ref="dock_gen_xs_ship_01_macro" connection="Connection_component" />
		  </connection>
		  <connection ref="con_shipstorage_s_01">
			<macro ref="shipstorage_gen_s_three_macro" connection="object" />
		  </connection>
		  <connection ref="con_shipstorage_xs_01">
			<macro ref="shipstorage_gen_xs_01_macro" connection="object" />
		  </connection>
		  <connection ref="con_storage01">
			<macro ref="storage_arg_l_trans_container_01_a_macro" connection="ShipConnection" />
		  </connection>
		</connections>
	  </macro>
	</macros>
	
	c.2) SPL - Split - builder - split extension - player buildable - path: _unpacked\extensions\ego_dlc_split\assets\units\size_xl\macros\ship_spl_xl_builder_01_a_macro.xml
	
		<?xml version="1.0" encoding="utf-8"?>
		<!--Exported by: Michael (192.168.3.53) on 2024-11-18 15:23:35-->
		<macros>
		  <macro name="ship_spl_xl_builder_01_a_macro" class="ship_xl">
			<component ref="ship_spl_xl_builder_01" />
			<properties>
			  <identification name="{20101,40501}" basename="{20101,40501}" makerrace="split" description="{20101,40511}" icon="ship_xl_builder_01" />
			  <software>
				<software ware="software_dockmk2" compatible="1" />
				<software ware="software_flightassistmk1" default="1" />
				<software ware="software_scannerlongrangemk1" default="1" />
				<software ware="software_scannerlongrangemk2" compatible="1" />
				<software ware="software_scannerobjectmk1" default="1" />
				<software ware="software_scannerobjectmk2" compatible="1" />
				<software ware="software_targetmk1" compatible="1" />
				<software ware="software_trademk1" default="1" />
			  </software>
			  <jerk>
				<forward accel="0.3" decel="0.7" ratio="3" />
				<forward_boost accel="0.5" ratio="3" />
				<forward_travel accel="0.3" decel="0.7" ratio="3" />
				<strafe value="0.3" />
				<angular value="0.15" />
			  </jerk>
			  <explosiondamage value="1200" shield="6000" />
			  <storage missile="40" unit="130" />
			  <hull max="181000" />
			  <secrecy level="2" />
			  <steeringcurve>
				<point position="1.01" value="1" />
				<point position="1.2" value="0.9" />
				<point position="1.6" value="0.8" />
				<point position="2.1" value="0.45" />
				<point position="2.4" value="0.3" />
				<point position="2.7" value="0.25" />
			  </steeringcurve>
			  <purpose primary="build" />
			  <people capacity="182" />
			  <physics mass="1151.849">
				<inertia pitch="2000" yaw="2000" roll="1350" />
				<drag forward="151.305" reverse="605.221" horizontal="280" vertical="280" pitch="930.37" yaw="930.37" roll="930.37" />
			  </physics>
			  <thruster tags="extralarge" />
			  <ship type="builder" />
			</properties>
			<connections>
			  <connection ref="con_cockpit">
				<macro ref="bridge_spl_xl_01_macro" connection="con_cockpit" />
			  </connection>
			  <connection ref="con_dock_xs">
				<macro ref="dock_gen_xs_ship_01_macro" connection="Connection_component" />
			  </connection>
			  <connection ref="con_shipstorage_m_01">
				<macro ref="shipstorage_gen_m_two_macro" connection="object" />
			  </connection>
			  <connection ref="con_shipstorage_s_01">
				<macro ref="shipstorage_gen_s_two_macro" connection="object" />
			  </connection>
			  <connection ref="con_shipstorage_xs_01">
				<macro ref="shipstorage_gen_xs_01_macro" connection="object" />
			  </connection>
			  <connection ref="con_storage01">
				<macro ref="storage_arg_xl_builder_01_a_macro" connection="ShipConnection" />
			  </connection>
			  <connection ref="con_test_argon_dockarea_m_04">
				<macro ref="dockarea_arg_xl_builder_01_macro" connection="Connection01" />
			  </connection>
			</connections>
		  </macro>
		</macros>

	d) tfile - english 0001-l044.xml - path: _unpacked\t
		d.1) energy cells sdample from files
			<t id="701">Energy Cells</t>

## Canonical Ware Production Model (CWPM)

This document defines the **Canonical Ware Production Model (CWPM)**, the single
authoritative representation of production data extracted from X4: Foundations
game files.

CWPM is generated by `build_ware_catalogue.py` and is the **only approved source**
of ware production data for downstream consumers.

This document is normative.

---

## 1. Top-level structure

The CWPM is a single JSON object keyed by `ware_id`.


{
  "<ware_id>": { ... },
  "<ware_id>": { ... }
}

Invariants

ware_id is unique across the entire catalogue

All lookups are ware-centric, not transport-centric

No XML access is required once the CWPM has been built

CWPM is deterministic (same inputs → same output)

2. CWPM entry schema (per ware)

Each ware entry may contain three sections:

{
  "<transport>": { ... },
  "price": { ... },              // optional
  "productionMethods": { ... }   // always present (may be empty)
}

3. Transport block (required, exactly one)

Each ware must contain exactly one transport block, keyed by the transport name
as defined in wares.xml.

Observed transport values include (not exhaustive):

"ship"

"equipment"

"container"

"inventory"

"liquid"

"solid"

"other"

Transport block schema
"<transport>": {
  "name": "{page,id}",
  "description": "{page,id}",
  "group": "string | null",
  "volume": int,
  "tags": [ "string", ... ],

  // optional, transport-specific
  "component": "macro_id",
  "licence": "string",
  "owners": [ "faction", ... ]
}
Rules

Transport is implicit via the key name

No "transport": "ship" duplication exists anywhere

Transport-specific metadata lives only inside this block

Unknown or unused fields are allowed and ignored downstream


4. Price block (optional)

Present only when a <price> element exists in XML.

"price": {
  "min": int,
  "average": int,
  "max": int
}

Rules

Prices are informational only

Prices do not affect production calculations

Missing price data is valid (e.g. research wares)

5. productionMethods block (required)

This block is always present, but may be empty.

"productionMethods": {
  "<method>": { ... },
  "<method>": { ... }
}

Method keys

Method names are preserved exactly as defined in XML, including:

"default"

"terran"

"teladi"

"closedloop"

"xenon"

additional methods introduced by DLC or mods

⚠️ No renaming or normalisation is performed.

6. Production method schema
"<method>": {
  "time": int,
  "amount": int,
  "name": "{page,id}",
  "resources": {
    "<ware_id>": int,
    "<ware_id>": int
  },

  // optional
  "tags": [ "string", ... ]
}

Rules

resources keys are ware IDs

Resource amounts are always integers

No resource translation occurs at this level

tags may include:

"noplayerbuild"

other method-specific flags

7. Buildable vs non-buildable wares

CWPM explicitly distinguishes existence from buildability.

Buildable ware
"productionMethods": {
  "default": { ... }
}

Non-buildable ware (research, unlocks, etc.)
"productionMethods": {}

Rules

Empty productionMethods is valid

Filtering happens in schemas and calculators

CWPM retains all wares for completeness and future extensibility

8. Injected production (DLC / extensions)

Injected production (via <add><production>) is merged, not flattened.

Example:

"productionMethods": {
  "default": { ... },
  "terran": { ... },
  "closedloop": { ... }
}

Rules

Injected methods must not overwrite existing methods

Method collisions raise errors during catalogue build

Source file location is irrelevant once merged into CWPM

9. CWPM Consumer Rules (Normative)

All consumers of CWPM must comply with the following rules.

9.1 Source of truth

CWPM is the only approved source for:

production resources

production times

production methods

Consumers must not parse wares.xml directly

9.2 Buildability

A ware is buildable only if productionMethods is non-empty

Consumers must explicitly filter non-buildable wares

Consumers must not assume:

transport == ship implies buildable

presence of a component implies buildable

9.3 Resource handling

Consumers must treat resource keys as opaque ware IDs

Translation and localisation occur only at display/export time

Resource quantities must be treated as integers

9.4 Method selection

Consumers must explicitly choose a production method

No implicit fallback between methods is allowed

"default" is not guaranteed to exist for all wares

9.5 Extension safety

Consumers must assume new methods may appear

Unknown methods must not cause failures

Filtering of methods (e.g. excluding "xenon") is a consumer concern

10. Relationship to PIPELINE.md

CWPM corresponds to the following pipeline stages:

PIPELINE.md → Discovery & Normalisation

CWPM is the output of the discovery phase

PIPELINE.md → Schema Derivation

Equipment and hull schemas are derived from CWPM

PIPELINE.md → Build Queue Calculation

All material aggregation operates on CWPM

No pipeline stage downstream of CWPM should require XML access.

11. What CWPM intentionally excludes

CWPM does not include:

localisation text

UI labels

Excel column layouts

build queue totals

faction logic

research unlock rules

These are derived concerns handled by consumers.

12. Canonical statement

If a value cannot be derived from CWPM, it is not canonical production data.

Any deviation from this document must be explicitly documented and justified.


---




### Production
Represents a production recipe parsed from wares.xml.

Fields:
- ware_id: str
  - The <ware id="..."> value.

- macro_id: str | None
  - The <component ref="..."> value if present for this ware.

- transport: str
  - Lowercased <ware transport="..."> (commonly "ship" or "equipment").

- price_min/avg/max: int
  - Parsed from <price min/average/max>.

- build_time: float
  - Parsed from <production time="...">.

- components: list[tuple[str, int]]
  - List of (material_ware_id, amount).
  - NOTE: amount is integer.

Canonical invariant:
- Production.components always stores material ware IDs, not translated names.

### EquipmentRow
Represents an equipment ware joined with a Production recipe.

Fields:
- source: str
  - Origin (base game or extension), derived from file path.

- equipment_id: str
  - Ware ID.

- equipment_name: str
  - Raw in-game name reference (often "{page,id}") or fallback.

- race: str
  - Canonical race/faction code (project-defined).

- size: str
  - Canonical internal size token (recommended: lowercase "s|m|l|xl").

- mk: str
  - "Mk1", "Mk2", etc.

- production: Production
  - Production recipe from wares.xml for this ware.

### HullRow
Represents a ship archetype matched to a macro and joined with Production.

Fields:
- source: str
  - Origin (base game or extension).

- macro_id: str
  - Macro filename stem (e.g. ship_arg_s_scout_01_a_macro).

- hull_id: str
  - Ware ID or archetype ID (project-defined; must remain stable).

- hull_name: str
  - Raw name ref "{page,id}" or fallback.

- faction: str
  - Canonical faction code.

- size: str
  - Canonical internal size token (recommended lowercase).

- production: Production
  - Production recipe joined by macro_id from prod_by_macro.

## Translation Contract

Translation tables:
- load_translation_table() returns Dict[(page_id, t_id), string].

Display name resolution:
- resolve_display_name(raw, ttable, fallback) -> str
  - If raw is "{page,id}", looks up in ttable.
  - Otherwise cleans literal strings.
  - Otherwise returns fallback.

Canonical rule:
- Extractors do not translate; export does.

## Export Contract (Excel)

- export/excel.py writes:
  - One sheet per equipment category.
  - One sheet for hulls.
- MATERIAL_SCHEMAS defines the output columns (should live under export/schema.py).
- Material amounts are mapped into columns by matching material display names
  (after translation/normalization).
