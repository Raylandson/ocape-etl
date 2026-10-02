# Feature Specification — Saved Selections (Hand-Picked Area Sets)

**Status:** draft for review · **Date:** 2026-10-02
**Supersedes:** Feature B of [`2026-10-01-feature-visibility-and-saved-filters.md`](2026-10-01-feature-visibility-and-saved-filters.md) (§5, "Filtros Salvos e Exportação KML em Lote"). Feature A of that spec (visibility, overlap stack) is unchanged and this feature builds on it.

---

## 1. Problem

Feature B was built as a **rule-based query builder**: layer blocks, attribute conditions, spatial crossings, a SQL compiler. That is not what was wanted. The intended "filter" is a **set of areas the user picks by hand** — for example a handful of specific imóveis found while inspecting the map — that can be named, saved, reopened, shown on its own, annotated and exported.

### 1.1 Agreed understanding

| Said by the user | Taken as an assumption |
| :--- | :--- |
| A filter is a named set of areas the user selects, not a rule query across layers | A set may mix layers (a CAR imóvel next to a SIGEF parcel next to a Terra Indígena) |
| Areas are added with a button on each **Sobreposições** row and a button in the **detail popup** | Drawing a box/polygon, bulk add from search results and sharing a set with other people are not wanted now |
| A saved set can be **shown on its own on the map**, **exported to KML**, and carry a **note per area** | There is no authentication, so sets are global like the former saved filters |
| The rule-based builder is **removed** | The existing `saved_filters` table is left untouched |

### 1.2 Non-goals

* Drawing a box or polygon to select features.
* Adding results straight from the search bar (the search result already opens the popup, which has the add button).
* Sharing, permissions, or per-user sets.
* Per-area styling. Each area keeps its layer's colours.
* Reordering areas inside a set.

---

## 2. Design Summary

A **selection** is a named set of **members**. A member is one map feature, remembered by a **locator** rather than a database id:

```
layer_id      e.g. "area_imovel_1"
label         the title shown in the panel (search_index.label)
fingerprint   md5(props::text) of the search_index row at the time it was added
anchor        a point inside the feature (ST_PointOnSurface), lng/lat
hint          the row's string-valued properties, for ranking on fallback
note          free text, optional
```

### 2.1 Why a locator (approach C)

Map tiles carry no feature ids and most tables have no primary key. Remembering the `search_index.id` is not safe, because `build_search_index.py` drops and recreates the table (`bigserial` ids restart), and that has already happened once during this work. A stale id would not fail — it would silently point at a **different feature**.

The locator resolves in the database, not from an id:

```sql
SELECT id, layer_id, label, props, geometry, md5(props::text) = :fingerprint AS exact
FROM search_index
WHERE layer_id = :layer
  AND ST_DWithin(geometry, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), :tol)
ORDER BY exact DESC,
         (props @> CAST(:hint AS jsonb)) DESC,
         ST_Distance(geometry, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)) ASC,
         ST_Area(geometry) ASC
LIMIT 1
```

* The GIST index narrows the candidates by position first, so `md5` runs on a handful of rows (the same cost profile as the existing single-feature KML export, 0.25 ms).
* `exact = true` means the same attributes were found at that position. `exact = false` means the position matched but attributes changed (an ETL re-ingest): the member still resolves and the panel marks it **aproximada**.
* No row near the anchor: the member resolves to `null`, is shown as **não encontrada**, and keeps its note. It can be removed. It is never silently dropped.
* `:tol` is `1e-6` degrees (≈0.1 m) for every geometry type. The anchor is `ST_PointOnSurface`, so it lies inside a polygon at distance 0 either way.
* Byte-identical stacked rows (e.g. 4 CAR rows with one code) share a fingerprint and anchor, so they are **one member**. This matches the panel's existing "shared key" caveat.

---

## 3. Data Model

Owned by a new module `src/saved_selections.py`. Both tables use `CREATE TABLE IF NOT EXISTS`, like `saved_filters`, because they hold user data that no pipeline can regenerate.

```sql
CREATE TABLE IF NOT EXISTS saved_selections (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text NOT NULL CHECK (btrim(name) <> ''),
    name_norm   text GENERATED ALWAYS AS (lower(btrim(name))) STORED,
    description text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_saved_selections_name_norm ON saved_selections (name_norm);

CREATE TABLE IF NOT EXISTS saved_selection_members (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    selection_id uuid NOT NULL REFERENCES saved_selections(id) ON DELETE CASCADE,
    layer_id     text NOT NULL,
    label        text NOT NULL,
    fingerprint  text NOT NULL,
    anchor_lng   double precision NOT NULL,
    anchor_lat   double precision NOT NULL,
    hint         jsonb NOT NULL DEFAULT '{}'::jsonb,
    note         text,
    added_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (selection_id, layer_id, fingerprint, anchor_lng, anchor_lat)
);
CREATE INDEX IF NOT EXISTS idx_saved_selection_members_selection
    ON saved_selection_members (selection_id, added_at);
```

* Neither table has a geometry column, so Martin ignores them.
* `ensure_saved_selections_tables(engine)` is called from API startup (try/except + warning, as today), from `run_all_pipelines.py` (step `8b`, replacing the saved-filters step), and from `python -m src.saved_selections`.
* **Cap:** 500 members per selection, enforced by the API (409 with `{cap}`), so a set stays cheap to draw and export in one request.
* **Backup hazard:** these are the only tables the pipelines cannot regenerate, and `docker compose down -v` destroys them. The JSON export/import in §5.4 is the mitigation, and `README.md`/`AGENTS.md` keep their existing warning, reworded for selections.
* The legacy `saved_filters` table is **not dropped or migrated**. It is no longer read by anything.

---

## 4. API

New `src/selections_api.py` (router, included from `search_api.py`). `src/saved_selections.py` holds the SQL and is import-safe for tests.

| Method | Path | Behaviour |
| :--- | :--- | :--- |
| `GET` | `/selections` | `[{id, name, description, member_count, updated_at}]`, newest first |
| `POST` | `/selections` | `{name, description?}` → 201; **409** on `name_norm` clash |
| `PUT` | `/selections/{id}` | rename / describe; 409 / 404 |
| `DELETE` | `/selections/{id}` | 204; members cascade |
| `GET` | `/selections/{id}` | selection plus members `{id, layer_id, label, note, anchor, resolved: "exact" \| "approximate" \| "missing"}` |
| `POST` | `/selections/{id}/members` | add one feature; see below |
| `PUT` | `/selections/{id}/members/{member_id}` | `{note}` |
| `DELETE` | `/selections/{id}/members/{member_id}` | 204 |
| `GET` | `/selections/{id}/geometry` | GeoJSON `FeatureCollection` of every resolved member for drawing; see below |
| `POST` | `/selections/{id}/export/kml` | `{grouping: "set" \| "feature", style}` → `.kml` or `.zip` |
| `GET` | `/selections/backup` | all selections with members, for the JSON export |
| `POST` | `/selections/backup` | import; upsert by `name_norm`, merging members by locator |

### 4.1 Adding a member

Request: `{layer, lng, lat, zoom, tolerance_px, props, search_index_id?}` — the same shape the popup's KML button already sends, so the frontend reuses `buildFeatureRef`. The server resolves the feature with the existing locator (`_locate_feature` in `export_api.py`, reused unmodified, with the fingerprint and anchor returned through its `geometry_sql`), then stores the **canonical** values read from the database: label, fingerprint, `ST_PointOnSurface` anchor, and the string-valued props as `hint`. It stores what the database says the feature is, not what the tile said.

* Not found → **404**, nothing stored.
* Already present (unique key) → **200** with the existing member, so the button is idempotent.
* Over 500 → **409**.

### 4.2 Geometry for drawing

Each member is resolved with the §2.1 query and returned with its full boundary, simplified to about half a pixel at the requested `zoom`, as in `/feature/geometry`. Feature `properties` are the row's props plus `__layer` (the layer id), `__label`, `__note` and `__resolved`. The client adds colours from its registry, because layer colours live only in the frontend.

Large sets are bounded: 500 members, simplified, one request.

### 4.3 KML export

`kml_writer.KmlItem` gains an optional `note`. `html_description` renders it as an **Observação** row above the attribute table, escaped like every other value.

* `grouping: "set"` — one `.kml` for the whole selection, one `<Folder>` per layer (existing `build_document`). Filename `conflitos_pe_<nome>_<YYYYMMDD>.kml`.
* `grouping: "feature"` — a ZIP with one KML per member (existing `stream_archive` naming with the `_<n>` suffix), plus `LEIAME.txt` listing the set name, the members and any that could not be resolved.

Members that resolve to `missing` are skipped and listed in `LEIAME.txt`; they never produce an empty placemark. Geometry comes from `ST_AsKML` with the same `GEOMETRYCOLLECTION` guard as today.

---

## 5. Frontend

### 5.1 Layout

```
frontend/src/app/selections-panel/        replaces filter-builder/
  selections-panel.component.{ts,html,css}
frontend/src/app/services/
  selection.service.ts                    HTTP + the shared "active selection" state
  export.service.ts                       keeps featureGeometry / exportFeature; drops exportFilter
```

`SelectionService` is a root service, because three places need the active set: the panel, the Sobreposições rows, and the popup button in `app.ts`. It exposes the active selection id, its members (as a signal), and `add(ref)` / `remove(memberId)` / `has(ref)`.

### 5.2 The panel (Filtros)

Standalone component in `.left-panels-stack`, 320 px wide, same toggle and card styling as its neighbours (AGENTS.md §3: institutional, no emojis, monospace codes, key-value hierarchy).

* **List of sets** with name, member count and the active one highlighted. **Novo conjunto** creates one by name; rename and delete per row; a duplicate name shows the 409 message inline.
* **Active set**: its members, each with the layer colour chip, layer name, label, a **zoom to** button, a **remove** button, and a collapsible **note** textarea saved on blur (debounced). `aproximada` and `não encontrada` badges appear here.
* **Isolar** toggle (§5.3) and **Exportar KML** with the two grouping options; both disabled when the set is empty.
* **Exportar JSON / Importar JSON** in the footer (§5.4).

With no active set, the add buttons are disabled with the tooltip *"Escolha ou crie um conjunto em Filtros"*, and the panel shows a one-line hint. Adding never creates a set implicitly.

### 5.3 Adding areas

1. **Sobreposições row** (`overlap-stack-panel`): a third icon button, *Adicionar ao conjunto*. Pressing it on a feature already in the active set does not duplicate it: the panel shows *Já está no conjunto* (removal is done from the panel). It emits a new `featureAddToSelection` output; `app.ts` builds the `ActiveFeatureRef` with the same `buildFeatureRef` the KML button uses.
2. **Detail popup**: a button beside **Baixar KML** (`data-action="add-to-selection"`), wired through the same document-level click handler already used for `export-single-kml`, using `activeFeatureRef`.

Both call `SelectionService.add`, which POSTs to §4.1 and updates the member list. Hidden features (Ocultar) can still be added.

### 5.4 Backup

**Exportar JSON** downloads `GET /selections/backup`; **Importar JSON** posts a chosen file to `POST /selections/backup` and reports `{imported, skipped}`. The JSON stores locators only (no geometry), so a backup stays valid across index rebuilds.

### 5.5 Showing only a set ("Isolar")

* Turning **Isolar** on snapshots each layer's `visible` flag, hides every data layer (`renderedLayerIds` + `visibility: none`), fetches §4.2 and draws the result into a `selection-members-source` with `selection-fill`, `selection-line` and `selection-circle` layers (data-driven `fill-color` / `line-color` from `__fill` / `__border`). They are registered below the `hover-feature-*` anchor so the existing invariant satellite < data < highlight < labels still holds, and the map fits to the set's bounds.
* Turning it off restores the snapshot and clears the source. The basemap and place labels are never touched.
* While isolated, the layer panel shows a banner *"Isolamento ativo — N áreas"*, and the checkboxes stay usable; the restore on exit applies the snapshot taken at entry.
* **Clicking works while isolated.** `queryStackAt` also queries the three selection layers; because their feature props are the original props, the existing `renderPopupForLayer` is called with `${__layer}_fill` (or `_circle` / `_line` per geometry), so popups and the overlap stack behave as usual.
* Adding or removing a member while isolated refreshes the drawn source.

---

## 6. Removal

Removed in this change (all remain in git history):

* `frontend/src/app/filter-builder/`, `frontend/src/app/services/filter.service.ts`
* `src/filters_api.py`, `src/filter_compiler.py`, `src/filter_catalog.py`, and the `filters_router` include in `search_api.py`
* `tests/test_filter_compiler.py`, and the compiler fixtures in `tests/conftest.py`
* `POST /export/kml` (rule-based bulk export) and `ExportService.exportFilter`
* `src/saved_filters.py`; its pipeline step is replaced by the selections step

Kept: `kml_writer.py` and its tests, `export_api.py`'s single-feature KML and `/feature/geometry`, the CAR sub-layers in `SEARCH_SOURCES` (with their popups), `feature-title.ts`, and the `saved_filters` table's data.

---

## 7. Testing

Pure modules only, as in the existing suite (no DB at import):

* `kml_writer`: `note` renders as **Observação**, is escaped (`<script>`), and is omitted when empty.
* `saved_selections`: name normalisation, the 500 cap decision, and the backup merge logic, written so these are testable without a connection (the SQL stays in thin functions).

Database-level checks, run by hand against the live API (a planner or data bug cannot be caught by a unit test):

* Resolve a CAR member, rebuild `search_index`, resolve again → still `exact`.
* Change an attribute of the source row, rebuild → `approximate`.
* Delete the source row, rebuild → `missing`, note kept.
* A 500-member set returns geometry in one request in under a second.

---

## 8. Acceptance Criteria

1. With no active set, both add buttons are disabled with the explanatory tooltip. Creating a set named `Fazenda X` makes it active; creating `fazenda x ` shows the duplicate-name message.
2. Left-click a point over CAR + SIGEF, press *Adicionar ao conjunto* on the CAR row: the panel lists it with its layer colour and label. Pressing it again leaves one member and shows *Já está no conjunto*.
3. Right-click a feature, press the popup's add button: it joins the active set. Adding the same feature twice stores one member.
4. Notes survive a hard reload and a rename of the set.
5. **Isolar** hides every data layer and draws exactly the members' **full** boundaries (a parcel crossing tile seams is not clipped), in their layer colours, and fits the map to them. Turning it off restores the previous layer visibility exactly.
6. Right-clicking a member while isolated opens the same popup as before.
7. **Exportar KML → conjunto** downloads one `.kml` with a folder per layer; each placemark's balloon shows the note. **→ por feição** downloads a ZIP with one KML per member and a `LEIAME.txt`.
8. After `python -m src.build_search_index`, members still resolve (`exact`); a member whose source row was removed shows **não encontrada**, keeps its note, and is listed in `LEIAME.txt` instead of exporting an empty placemark.
9. **Exportar JSON** then deleting a set then **Importar JSON** restores its members and notes.
10. A 501st member returns 409 and the panel says so.
11. The old builder UI, `/filters` and `POST /export/kml` are gone; `uv run pytest` passes; `saved_filters` still exists in the database untouched.

---

## 9. Implementation Sequence

| Phase | Steps |
| :--- | :--- |
| **1. Backend core** | `saved_selections.py` (DDL, CRUD, resolve) with tests → extend `_locate_feature` to return fingerprint/anchor → `selections_api.py` (CRUD, members, geometry) → `KmlItem.note` + export endpoint → backup endpoints → pipeline step |
| **2. Frontend** | `selection.service.ts` → `selections-panel` (sets, members, notes) → add buttons (Sobreposições, popup) → Isolar → export and JSON backup |
| **3. Removal** | Delete the builder UI, `/filters`, compiler, catalog, `saved_filters.py`, `POST /export/kml` and their tests, after Phase 2 works |
| **4. Docs** | `README.md` section rewrite, `AGENTS.md` module list and the user-data warning, `docs/CHANGELOG.md` entry, and a note on the old spec marking Feature B superseded |

Removal is last so the app stays working while the replacement is built.

---

## 10. Risks and Open Points

* **Identical-attribute neighbours.** Two different features with the same props and the same anchor would collapse into one member. Anchors come from `ST_PointOnSurface` of different geometries, so this needs identical geometry as well; accepted.
* **Re-ingest changes attributes.** Handled by `approximate` resolution, but a member can then point at a neighbouring feature if the original was removed and another covers the anchor. The `aproximada` badge is the user-visible signal; making this stricter (reject if the layer's label also changed) is possible if it proves noisy.
* **Isolate and draw order.** The selection layers sit below the hover anchor, so they draw above data layers regardless of user reordering; that is intended while isolated.
* **Colours on the server.** The geometry endpoint returns no colours, so the client must attach them before drawing.
