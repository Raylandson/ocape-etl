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

### August 2026: Comprehensive Data Documentation & Metadata Analysis
- **Documentation**: Created [`docs/DATA_ANALYSIS.md`](file:///home/raylandsoncesario/github/conflict-solver/docs/DATA_ANALYSIS.md) and updated [`README.md`](file:///home/raylandsoncesario/github/conflict-solver/README.md) with a dedicated conceptual framework defining SIGEF, SNCI, SICAR (CAR), FUNAI, and INCRA Quilombolas.
- **Empirical Metadata Analysis**: Extracted and compiled detailed 1-to-1 attribute statistical analyses for all `.dbf` metadata tables in [`data/extracted/`](file:///home/raylandsoncesario/github/conflict-solver/data/extracted), covering 433,105 CAR polygons, 24,013 SIGEF parcels, 16 Indigenous territories, 10 Quilombola areas, and 110 legacy SNCI properties with precise ownership, registration status, and legal condition percentages.
- **Full SICAR Environmental Integration**: Extracted, ingested, and spatial-indexed three new primary environmental shapefiles for Pernambuco:
  - `apps_1`: 273,296 Áreas de Preservação Permanente (APP) polygons.
  - `reserva_legal_1`: 239,388 Reserva Legal (RL) polygons.
  - `vegetacao_nativa_1`: 138,475 Remanescentes de Vegetação Nativa polygons.
- **Frontend Layer Controls**: Configured and integrated all 3 new SICAR layers into `frontend/src/app/app.ts` with custom themed colors (Cyan for APPs, Deep Forest Green for Reserva Legal, Light Green for Native Vegetation) and visibility toggle switches.


