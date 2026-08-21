# Agent Guidelines & Rules

This document outlines the guidelines and protocols that AI coding agents must strictly adhere to when working on the Land Conflict Mapping Platform repository.

## Rules

### 1. Maintain and Update Documentation
* **Rule**: AI agents MUST update the repository documentation (such as `README.md` and this file) every time an important change, new component, architectural update, or configuration change is made.
* **Objective**: Ensure that the codebase's documentation remains perfectly aligned with its current state, making onboarding and collaboration seamless.

---

## Change Log & Architectural Updates

### July 2026: Conflict Center Pins & Interactive Popups
- **Postgres/PostGIS**: Modified `src/overlaps.py` to compute conflict region medians/centers using PostGIS `ST_PointOnSurface(geometry)`. This generates the `public.land_overlaps_points` table (which is indexed with a spatial GIST index) for Martin vector tile server to publish automatically.
- **Spatial Clustering & Dissolving**: Integrated PostGIS DBSCAN spatial clustering (`ST_ClusterDBSCAN` with `eps := 0.0001`) and geometry unioning (`ST_Union`) in `src/overlaps.py` to group and merge neighboring/overlapping conflict polygons. Semicolon-delimited aggregates (`string_agg`) are created for property name, code, and source attributes. The Angular frontend popup logic was updated to parse these lists and display individual property entries cleanly in a scrollable container.
- **Frontend Symbol Layer**: Added `land_overlaps_points` to `frontend/src/app/app.ts` layers. Configured a MapLibre `symbol` layer with `'icon-image': 'red-pin'` and `'icon-anchor': 'bottom'` to position pins correctly.
- **Canvas-drawn Pin**: Implemented a programmatically drawn canvas-based vector pin icon with drop-shadows and borders inside `app.ts` so that it stays same-sized independent of zoom levels.
- **Interactive Detail Popups**: Implemented custom MapLibre `Popup` cards on clicking both the conflict polygons and conflict center pins, displaying detailed conflict information (Indigenous/Quilombola land names, private property details, and property codes) with premium styling in `app.css`.
- **CAR/SICAR Integration**: Integrated the Cadastro Ambiental Rural (CAR) dataset (`area_imovel_1` table) into the overlaps and conflicts calculation script (`src/overlaps.py`). Updated the frontend popup logic to label these properties as "CAR" and added the CAR layers to the MapLibre configuration in `app.ts` (hidden by default to protect map performance due to its large size of 433k properties).

### August 2026: Full ICMBio Environmental Ingestion & Conflict Expansion
- **ICMBio Ingestion & Axis Rectification**: Integrated three new national/state ICMBio datasets from `data/raw/`:
  - `limiteucsfederais_a`: 347 Federal Conservation Units (7 in Pernambuco: Parque Nacional do Catimbau, Fernando de Noronha, Serra Negra, Saltinho, Negreiros, etc.).
  - `embargos_icmbio`: 14,375 official environmental embargo boundaries (251 in Pernambuco).
  - `autos_infracao_icmbio`: 41,728 environmental infraction notice points (839 in Pernambuco).
- **Coordinate Inversion Resolution**: Implemented automated detection and axis rectification in `src/etl.py` to swap inverted `(Latitude, Longitude)` geometries to standard `(Longitude, Latitude)` EPSG:4326 and filter non-finite sentinel coordinates.
- **Overlaps Calculation Expansion**: Extended `src/overlaps.py` to identify spatial overlaps between certified properties (SIGEF/SNCI/CAR) and Federal Conservation Units as well as ICMBio Embargo Areas, expanding total conflict zones to 804 with DBSCAN spatial clustering and center pinpoints (`land_overlaps_points`).
- **Frontend Map & Popups**: Added `limiteucsfederais_a`, `embargos_icmbio`, and `autos_infracao_icmbio` layers to `frontend/src/app/app.ts` with custom themed colors, circle layer support for infraction notice points, and interactive rich detail popups for all ICMBio features and expanded conflict categories.
- **Scrollable & Collapsible Layer Panel**: Refactored the frontend layer list to be scrollable with custom sleek scrollbars and constrained viewport heights (`max-height: calc(100vh - 40px)`). Added an interactive minimize / close control in the panel header and a floating toggle badge button showing the active layer count when collapsed.
- **Documentation**: Updated [`docs/DATA_ANALYSIS.md`](file:///home/raylandsoncesario/github/conflict-solver/docs/DATA_ANALYSIS.md) with the ICMBio legal framework (Law 9.985/2000 SNUC, Decree 6.514/2008) and comprehensive metadata attribute statistics.


