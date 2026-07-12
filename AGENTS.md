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
