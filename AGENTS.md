# Agent Guidelines & Rules

This document outlines the operational rules, core architecture, and reference pointers for AI coding agents working on the Land Conflict Mapping Platform.

---

## 1. Core Rules

1. **Documentation Protocol**:
   - AI agents **must NOT** append change history, changelogs, or task logs to `AGENTS.md`. Keep this file lean and focused on rules and necessary references.
   - Architectural updates, milestone details, and historical records must be documented in [`docs/CHANGELOG.md`](docs/CHANGELOG.md).
   - Dataset metadata, legal schemas, and sources must be documented in [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) and [`docs/DATA_ANALYSIS.md`](docs/DATA_ANALYSIS.md).
   - User-facing setup, stack overview, and prerequisites are documented in [`README.md`](README.md).
   - When an agent makes a change, read the relevant documents in `docs/` first, and update them accordingly upon completion.

2. **Git Commits**:
   - **Never** execute `git commit` unless the user explicitly requests a commit.

3. **UI/UX & Design Guidelines**:
   - Maintain a minimalist, institutional design.
   - Avoid decorative emojis, neon glows, or high-saturation elements in popups, legends, and cards.
   - Use clean typography, structured neutral boxes (`.popup-detail-box`), monospace codes, and clear key-value hierarchy.

---

## 2. Essential System Architecture & Stack

- **Database**: PostgreSQL 17 + PostGIS 3.5
  - Port: `5433` | Database: `land_conflicts` | User: `postgres`
  - All spatial layers must use `EPSG:4326`, 2D geometries (`shapely.force_2d`, `shapely.make_valid`), and spatial GIST indexes (`idx_{table}_geometry`).
- **Vector Tile Server**: Martin (Rust MVT server via Docker)
  - Port: `3000` | Catalog: `http://localhost:3000/catalog`
  - PostGIS tables with geometry columns are served automatically. Restart Martin (`docker compose restart martin`) after creating or altering spatial tables so the catalog refreshes.
- **Python / ETL**: Python 3.12+ managed via Astral `uv`
  - Run commands with `uv run python src/<script>.py`.
  - Core pipelines:
    - `src/etl.py`: Main shapefile/GeoJSON ingestion with coordinate-axis rectification and Pernambuco boundary filtering.
    - `src/etl_datajud.py`: CNJ DataJud judicial lawsuits extraction (TJPE & TRF5).
    - `src/overlaps.py`: Spatial conflict detection engine & DBSCAN clustering (`land_overlaps`, `land_overlaps_points`).
    - `src/etl_moradia_iterpe.py`: Programa Moradia Legal (TJPE) and Acervo Fundiário (ITERPE) ingestion.
- **Frontend**: Angular 20 Standalone + MapLibre GL JS
  - Directory: `frontend/` | Port: `4200`
  - MapLibre style: Carto Positron. City and municipal place labels are dynamically styled to sit with proper contrast above spatial polygons and point circles.
- **Data Directory Hierarchy**:
  - `data/raw/`: Untouched upstream source archives/zips.
  - `data/extracted/`: Extracted input source datasets for ETL ingestion. Never place exported/output data here.
  - `data/exports/`: Outputs, custom analysis layers, and exported deliverables produced by the app/scripts (e.g. `data/exports/kml/`).

---

## 3. Documentation Map (`docs/`)

When you need specific domain or implementation details, consult the appropriate file in `docs/`:

| Document | Purpose |
| :--- | :--- |
| [`docs/CHANGELOG.md`](docs/CHANGELOG.md) | Chronological log of major architectural changes, bug fixes, and feature implementations. |
| [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) | Inventory of imported datasets vs. roadmap datasets (Layer 1 topological + Layer 2 socio-legal). |
| [`docs/DATA_ANALYSIS.md`](docs/DATA_ANALYSIS.md) | Comprehensive legal framework (SNUC, CNJ Res. 510/2023, TPU), metadata attributes, and stats. |
| [`docs/PHASE_1_DATA_DOWNLOADS.md`](docs/PHASE_1_DATA_DOWNLOADS.md) | Direct download URLs, WFS endpoints, and batch ingestion commands for Phase 1 data. |
| [`README.md`](README.md) | Project introduction, directory tree, local setup, and execution instructions. |
