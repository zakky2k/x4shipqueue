# X4 Ship Queue – Data Processing Pipeline

This document describes the **end-to-end data pipeline** for the X4 Ship Queue
project, from raw Egosoft game files to derived outputs such as Excel exports
and build-queue material calculations.

The pipeline is explicitly structured to **separate discovery, canonicalisation,
and consumption**, minimising coupling and preventing data drift.

---

## 1. Pipeline overview

The pipeline consists of **four logical stages**:

1. **Discovery** – Parse raw X4 XML files
2. **Canonicalisation** – Build the Canonical Ware Production Model (CWPM)
3. **Derivation** – Produce schemas and views from CWPM
4. **Consumption** – Use derived data for exports and calculations

Once CWPM has been built, **no downstream stage may read XML directly**.

---

## 2. Stage 1 – Discovery (raw XML parsing)

### Purpose

- Discover *all* wares, production methods, and materials
- Handle base game and all extensions consistently
- Preserve game semantics without interpretation

### Inputs

- `libraries/wares.xml` (base game)
- `extensions/*/libraries/wares.xml` (all DLC and mods)

### Characteristics

- XML parsing only
- No translation
- No filtering by faction, race, or playability
- No aggregation
- No assumptions about gameplay rules

### Output

- In-memory representations used **only** by the CWPM builder

### Ownership

- This stage is implemented exclusively by:
  - `tools/build_ware_catalogue.py`

No other component is permitted to parse `wares.xml` for production data.

---
### Discovery vs Canonical Boundary (Hard Rule)

The discovery stage exists solely to observe and extract facts from raw game files.

Discovery must NOT:
- interpret gameplay rules
- infer buildability
- normalise production methods
- collapse or flatten data
- apply faction or player constraints

All interpretation, filtering, and decision-making occurs after CWPM has been built.

## 3. Stage 2 – Canonicalisation (CWPM)

### Purpose

- Convert discovered XML data into a **single, stable, canonical model**
- Merge base and injected production (Terran, Boron, Teladi, Closed Loop, etc.)
- Preserve all valid production methods without flattening or loss

### Output

- `x4shipqueue/data/ware_catalogue.json`

This file is the **single source of truth** for production data.

---

### 3.1 Canonical Ware Production Model (CWPM)

CWPM is defined in detail in:

- `docs/CWPM.md`
- `docs/DATA_CONTRACT.md`

At a high level:

- Top-level keys are `ware_id`
- Each ware contains:
  - exactly one transport block (`ship`, `equipment`, etc.)
  - optional price data
  - a `productionMethods` map (always present, may be empty)

CWPM explicitly distinguishes:
- **existence** vs **buildability**
- **production methods** vs **consumers’ choices**

---

### 3.2 Build behaviour

- CWPM is built by `build_ware_catalogue.py`
- The build process is deterministic
- Inline and injected production methods are merged
- Method collisions are treated as errors
- Non-buildable wares (e.g. research-only) are retained

### 3.3 Rebuild policy

Recommended behaviour:

- CWPM is built **only if missing**
- Rebuilds may be forced via CLI flags if required
- Downstream consumers must not modify CWPM

---

## 4. Stage 3 – Derivation (schemas and views)

### Purpose

- Derive *use-case-specific* structures from CWPM
- Prepare data for export and calculation
- Apply filtering, grouping, and interpretation

### Examples of derived artefacts

- Equipment material schemas
- Hull material schemas
- Build queue input models
- Aggregated material requirement tables

### Key rules

- All derivation logic reads **only from CWPM**
- No XML parsing is allowed
- Translation and localisation occur at this stage
- Consumer-specific rules are applied here

---

## 5. Stage 4 – Consumption

### Purpose

- Present or calculate data for end users
- Perform build queue calculations
- Export data to external formats

### Typical consumers

- Excel export (`.xlsx`)
- Build queue calculators
- Future UI / web tools

### Consumer responsibilities

- Explicitly select production methods
- Filter out non-buildable wares
- Handle multiple methods safely
- Ignore unknown or unsupported methods gracefully

---

## 6. Deprecated behaviour (explicit)

The following behaviours are **no longer permitted**:

- Parsing `wares.xml` outside `build_ware_catalogue.py`
- Hardcoding production recipes
- Assuming one production method per ware
- Inferring buildability from transport type
- Mixing discovery logic with consumption logic

These patterns caused duplication, drift, and regressions and are intentionally
removed from the pipeline.

---

## 7. Error handling and validation

### Validation stages

- Structural validation occurs during CWPM build
- Semantic validation occurs during derivation
- Consumer-level validation is responsibility of the consumer

### Failure policy

- CWPM build failures are fatal
- Derivation failures are context-dependent
- Consumers must fail loudly on invalid assumptions

---

## 8. Extensibility and future-proofing

The pipeline is designed to support:

- New DLC economies
- Modded production methods
- Additional ware transports
- New output formats
- New calculation models

No pipeline stage assumes a closed set of methods, wares, or materials.

---

## 9. Canonical rule

> If production data is not present in CWPM, it is not canonical.

Any system requiring production data must source it from CWPM or explicitly
document why it deviates.

---

## 10. Relationship to other documents

- `CWPM.md` – Canonical data model
- `DATA_CONTRACT.md` – Structural and semantic guarantees
- `PIPELINE.md` – Execution and responsibility boundaries

These three documents together define the **architectural contract** of the project.
