A0 – Correcting two factual points you raised
A0.1 “extract_production vs extract_equipment difference”

You’re correct that both are ultimately sourcing components from wares.xml production blocks like your example. In the current code:

extract_production() parses <production><primary><ware ware="X" amount="Y"/></primary></production> into Production.components. 

extract_production

extract_equipment() does not re-parse components itself; it loads prod_by_ware from extract_production() and attaches the returned Production to rows. 

extract_equipment

So the “difference” I previously described is not “equipment does its own component lookup”; it doesn’t. The only current inconsistency is that hull extraction performs an additional mapping step on production components (see A3 below). 

extract_hulls

A0.2 “no naming.py / NON_BUILDABLE_MACRO_TOKENS”

There is x4shipqueue/util/naming.py in your uploaded project and it is used by translation/t_files.py. 

naming

 

t_files

I also confirm NON_BUILDABLE_MACRO_TOKENS does not appear in the files surfaced here; your config uses NON_BUILDABLE_TOKENS and hull filtering is implemented locally in extract_hulls.py. 

archetypes

 

extract_hulls

A1 – Logging refactor (Debug → logging framework)
A1.1 Adopt stdlib logging (best practice for Python CLIs)

You already started doing this in extract_equipment.py (log = logging.getLogger(__name__)). 

extract_equipment


But extract_hulls.py still uses print() in multiple places (and mixes log.debug + prints). 

extract_hulls

 

extract_hulls

What to implement (minimal, production-friendly)

Action A1.1

In __main__.py, configure logging once:

--log-level {WARNING,INFO,DEBUG}

optional --log-file path (nice-to-have)

Replace all print("[DEBUG] ...") with log.debug(...) across modules.

Action A1.2

Standard log pattern:

module-level log = logging.getLogger(__name__)

never call basicConfig except in entrypoint (__main__.py)

Action A1.3

Add a structured “debug bundle” switch later (ties into your Support Doc #4): --dump-debug out_dir/ (see A8).

A2 – Production parsing: fix correctness issues without changing behaviour

Your strongest “production-risk” area is extract_production.py.

A2.1 Remove the duplicate dict declarations and the None macro key risk

Right now:

prod_by_ware and prod_by_macro are defined twice,

prod_by_macro[macro_id] = prod happens even when macro_id is None. 

extract_production

Action A2.1

Keep exactly:

prod_by_ware: Dict[str, Production]

prod_by_macro: Dict[str, Production]

Only write prod_by_macro[macro_id] if macro_id is truthy.

This is a safe refactor with zero intended output change.

A2.2 Amounts must be integers (your rule) – make that explicit

You’re right to insist: the game’s ware amounts are integral in practice. Your code currently parses amounts as floats (float(amt)), so the type and model are currently lying about domain rules. 

extract_production

Action A2.2

Change parsing to int:

amount = safe_int(w.get("amount")) using your existing util/xml.py helper. 

xml

Update Production.components typing in models.py accordingly (see A4).

This is also safe and should not change output except the type (e.g., 60.0 → 60).

A3 – Hull vs equipment component handling consistency

Right now, hull extraction re-writes production components from (ware_id, amount) into (name_ref, amount) using _load_name_codes() and then creates a new Production. 

extract_hulls

 

extract_hulls

Equipment extraction does not do this conversion; it keeps Production as returned by extract_production(). 

extract_equipment

This is the real “drift”:

equipment rows: components = ware IDs

hull rows: components = name refs (or fallback)

Action A3
Pick one canonical internal rule and apply it to both:

Recommended (for maintainability):

Canonical internal: Production.components always (ware_id, int_amount)

Translation/display step resolves ware IDs to names for Excel columns, using wares.xml name refs + ttable.

That would let you delete the hull-only “convert components to name refs” block entirely and centralise display resolution in export.

If you prefer the opposite (canonical = “name refs”), we can do that too — but it makes category-level aggregation and comparisons harder later. Your call as domain expert; I’m happy to follow your chosen invariant.

A4 – Data model alignment (types and invariants)
A4.1 Fix component typing mismatch in Excel export

export/excel.py expects List[Tuple[str, int]] already. 

excel


But extract_production.py currently emits floats. 

extract_production

Once A2.2 is done, this becomes consistent.

Action A4.1

Ensure models.Production.components is list[tuple[str, int]].

Ensure every parser uses int.

A5 – Canonical “size” policy (lowercase internally, uppercase for display)

You proposed: “adopt everything lowercase until final export/display.” That’s sensible as long as the canonical contract is explicit.

Currently, sizes are mixed:

archetypes.normalize_ship_size() returns "S"|"M"|"L"|"XL". 

archetypes

extract_hulls.py often works with lowercase token sets ({"s","m","l","xl"}) for matching. 

extract_hulls

equipment parse_id_parts() returns uppercase size. 

parse

Action A5

Define a canonical internal representation:

size_token_internal: "s"|"m"|"l"|"xl" (lowercase)

export: convert to "S"|"M"|"L"|"XL" when writing Excel or user-facing output.

This is a “wide touch” change but straightforward if done in one controlled pass:

archetypes: return lowercase

equipment parse: return lowercase

Excel export: size.upper() (or map xl -> XL)

A6 – Export schema move out of config

Yes: I mean MATERIAL_SCHEMAS is tightly tied to the Excel export columns. Right now export/excel.py imports it from config.py. 

excel

 

config

Action A6

Move MATERIAL_SCHEMAS to export/schema.py (or export_schema.py if you prefer).

Update export/excel.py import accordingly.

Your request: “full assurance nothing else depends on it”

From the files visible here, MATERIAL_SCHEMAS is used in export/excel.py and defined in config.py. I don’t see other references surfaced in this snapshot. 

excel

 

config


When you do the change, a repo-wide grep confirms it in seconds.

A7 – Readability upgrades
A7.1 Module docstrings: what I mean + concrete suggestions

Examples based on current codebase:

Action A7.1.a production/extract_production.py
Add a module docstring stating:

“Parses production recipes from wares.xml for transport in {ship,equipment}”

“Components are always (ware_id, int_amount)”

“macro_id comes from <component ref=…> and is optional”

(Your existing inline comment block is close, but move it to the top and make it precise.) 

extract_production

Action A7.1.b hulls/extract_hulls.py
Docstring should clearly state:

hull matching pipeline (ships.xml archetypes → macro matching → prod_by_macro join)

invariant about production components (whether ware IDs or name refs)

Your function docstring is already good; it just needs to state the data invariants clearly. 

extract_hulls

Action A7.1.c export/excel.py
State:

which schemas exist (Engines, Thrusters, …, Hulls)

how materials are mapped into columns (by display name equality)

Right now it’s readable but implicit. 

excel

A7.2 pathlib.Path: what’s missing + what change looks like

You’re actually already using Path widely. 

extract_equipment

 

archetypes

 

extract_production

Two improvements:

util/xml.parse_xml(path: str) could accept Path | str to reduce conversions. 

xml

Anywhere you join paths as strings (less common in your current snapshot) should be Path operations for safety.

Action A7.2

Update parse_xml(path: str) → parse_xml(path: str | Path).

A8 – Tooling (why + how to adopt)

You said you don’t know the tools; here’s the practical, minimal set:

Action A8.1 – Ruff (lint + formatting)

Why: prevents drift (unused imports, inconsistent formatting, obvious bugs).

How: add pyproject.toml config and run ruff check . + ruff format ..

Action A8.2 – Pytest (smoke tests)

Why: you’re “in production”; tests prevent regressions during refactors A2–A6.

How: add tests/test_smoke.py with tiny fixture XMLs (your support doc #3).

Action A8.3 – (Optional) mypy

Why: will catch type mismatches like the float/int issue early.

Only after A2.2/A4 are done, otherwise it’ll be noisy.

A9 – Support documents: generated drafts

You asked me to generate (1) data contract and (2) pipeline doc based on the latest attached files. Here are ready-to-drop-in drafts.

(1) docs/DATA_CONTRACT.md (draft)
# Data Contract (x4shipqueue)

This document defines the canonical data model and invariants for the project.

## Source Game Files

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

## Core Types

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


This aligns to the modules you currently have (translation/t_files.py, util/naming.py, export/excel.py, etc.). 

t_files

 

naming

 

excel

(2) docs/PIPELINE.md (draft)
# Pipeline Overview (x4shipqueue)

## High-level flow

1) Discover game library files
   - wares.xml (base + extensions)
   - ships.xml (base + extensions)
   - ship macro xmls (assets/units/.../macros)
   - t-files (t/*.xml and extensions/*/t/*.xml)

2) Load translation table (optional for extraction; required for display/export)
   - translation/t_files.py: load_translation_table()

3) Extract production recipes (authoritative source: wares.xml)
   - production/extract_production.py: extract_production()
   - Output:
     - prod_by_ware: ware_id -> Production
     - prod_by_macro: macro_id -> Production (only if macro_id exists)

4) Extract equipment (wares definitions + production join)
   - equipment/extract_equipment.py: extract_equipment()
   - Steps:
     - Parse equipment wares from wares.xml
     - Detect category and parse race/size/mk from ware_id
     - Join Production via prod_by_ware[ware_id]
     - Emit EquipmentRow objects (raw name refs retained)

5) Extract hulls (ships archetypes + macro matching + production join)
   - hulls/archetypes.py: extract_ship_archetypes() from ships.xml
   - hulls/macros.py: find_ship_macro_files() and tokenisation helpers
   - hulls/matching.py: match ship archetype tokens to macro tokens
   - hulls/extract_hulls.py: extract_hulls()
   - Join Production via prod_by_macro[macro_id]
   - Emit HullRow objects (raw name refs retained)

6) Translate for display (recommended at export)
   - util/naming.py: resolve_display_name()

7) Export
   - export/excel.py:
     - write_equipment_sheet() per category
     - write_hulls_sheet()
     - column schemas from export/schema.py (recommended move)


This matches your structure.txt layout. 

structure

Next step proposal (so we don’t break production)

If you want the safest order of operations, I’d do this sequence:

A2.1 (extract_production cleanup + avoid None macro key)

A2.2 + A4 (int amounts end-to-end)

A1 (logging + remove prints)

A6 (move schema out of config)

A3 (canonical components rule: ware IDs vs name refs)

A5 (size canonicalisation)

Each step is independently testable and reversible.

One thing I need from you (domain confirmation, not “clarification for its own sake”)

To lock the “canonical components rule” (A3): do you want the internal Production.components to remain ware IDs (recommended), with export responsible for converting to translated names — or do you want Production.components to become “name refs” everywhere? Your earlier comments suggest you care about correctness and stability more than internal purity, so I’ll follow your preference, but we should pick one invariant.

If you answer that in one sentence, I’ll adapt A3/A6/A9 to it cleanly.