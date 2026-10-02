# Feature Specification — Feature Visibility Control & Saved Filters with Bulk KML Export

> **Feature B (§5, saved filters) was superseded by [`2026-10-02-saved-selections.md`](2026-10-02-saved-selections.md).** Feature A is unchanged.

* **Status:** Approved — pending implementation.
* **Date:** 2026-10-01
* **Scope:** Two independent features, A and B. Feature A is frontend-only; Feature B spans
  PostGIS, the FastAPI service and the Angular client.
* **Related documents:** [`docs/DATA_SOURCES.md`](../DATA_SOURCES.md),
  [`docs/DATA_ANALYSIS.md`](../DATA_ANALYSIS.md), [`docs/CHANGELOG.md`](../CHANGELOG.md).

---

## 1. Problem Statement

### 1.1 Visual occlusion between overlapping layers

The platform renders 43 PostGIS layers as Martin vector tiles. Several overlap heavily, most
acutely the CAR registry (`area_imovel_1`, **433,105 polygons**, 8,502,855.26 ha declared).
Because CAR perimeters are self-declared and blanket the entire state, they visually bury the
territories they are most often in conflict with — Terras Indígenas, Quilombos and Unidades de
Conservação.

Two concrete gaps:

* **No per-feature visibility.** [`frontend/src/app/app.ts`](../../frontend/src/app/app.ts)
  offers only whole-layer on/off through `toggleLayer()` (`app.ts:2863-2884`), which flips the
  MapLibre `visibility` layout property. Turning CAR off to inspect a Terra Indígena also
  removes the 178 other CAR polygons the analyst wants to keep as context.
* **The overlap stack is computed and discarded.** The click dispatcher calls
  `queryRenderedFeatures()` (`app.ts:2719`), sorts the full stack by `priorityOrder`, and then
  uses **only `sorted[0]`** (`app.ts:2729`). Every other feature under the cursor is thrown
  away, so there is no way to learn what a polygon is covering.
* **No draw-order control.** Every data layer is registered with `beforeId = firstLabelId`
  (`app.ts:873-1040`), so array position fixes depth permanently: `tis_poligonais` (index 0)
  is the bottom of the stack and `area_imovel_1` (index 8) always draws above it.

### 1.2 No way to express, keep or extract an analytical question

The unified search bar ([`src/search_api.py`](../../src/search_api.py)) answers *"where is X"*
but cannot answer *"every CAR property with `ind_status = AT` over 100 ha that intersects a
Terra Indígena"*. Once such a set is identified there is no way to persist the question or
extract the result: KML export handles exactly one feature at a time, from the popup
(`app.ts:656-663`).

### 1.3 Latent defects uncovered during analysis

These are pre-existing and are fixed as part of Feature B.

| Defect | Evidence | Impact |
| :--- | :--- | :--- |
| Popup KML exports tile geometry | `activeSelectedFeatureItem` is fed from `queryRenderedFeatures` (`app.ts:2719`, assigned `:2736-2742`) | Exported parcel boundaries are **simplified and clipped at tile seams**, not the true PostGIS geometry |
| `MultiPoint` unsupported | `geometryToKml` (`kml-export.service.ts:173-217`) has no `MultiPoint` case | **861** `autos_infracao_icmbio` features export as empty `<Placemark>` |
| `GeometryCollection` unsupported | same, no `GeometryCollection` case | **4** `ucs_estaduais_cprh_pe` features export empty. Total silent data loss: **1,028 features** |
| Layer filters clobber each other | `applySigefFilter` (`app.ts:213-231`) calls `setFilter` directly | Any second filter source on `sigef_casos_analisados` overwrites the phase filter |

---

## 2. Scope

### 2.1 In scope

* **Feature A — Controle de Visibilidade e Empilhamento.** Hide/unhide individual features via
  an overlap-stack panel; reorder whole layers in the draw order. **Session-only, in-memory.**
* **Feature B — Filtros Salvos e Exportação KML em Lote.** A filter builder persisted to
  PostgreSQL and shared globally; server-side bulk KML export streamed as a ZIP; migration of
  the single-feature popup export to the same server path.

### 2.2 Non-goals

* **Authentication and per-user state.** The project has no user, session or auth concept
  anywhere, and none is introduced. Saved filters are a single global list.
* **Persisting hidden features or layer order.** Explicitly session-only by decision; the app
  uses no `localStorage`, `sessionStorage` or `indexedDB` today and will not start.
* **Per-feature draw-order changes.** MapLibre cannot reorder features within a single layer.
  Reordering operates on whole layers.
* **Writing exports to `data/exports/kml/`.** The `search` container mounts only `./src:ro`
  (`docker-compose.yml:47`) and has no writable `data/` mount. Exports stream to the browser.
* **Refactoring `app.ts` beyond what these features require.** The ~25 popup renderer closures
  (`app.ts:1117-2638`), the `renderPopupForLayer` if/else chain (`app.ts:2641-2694`) and the
  document-level `data-action` listener (`app.ts:654-692`) are left untouched.
* **Spatial relations beyond `intersects` / `not_intersects`.** `within` and `contains` are
  deferred; `dwithin` is rejected because it requires `::geography` and `search_index` carries
  only a geometry GIST index, so it would not be index-accelerated.

---

## 3. Verified Data Constraints

Every figure below was measured against the live `conflitos_agrarios` database, not estimated.
These constraints drive the design and must not be re-litigated during implementation.

### 3.1 Feature identity

* **Vector tiles carry no feature `id`.** Martin is configured with only `DATABASE_URL`
  (`docker-compose.yml:20-30`); there is no Martin config file anywhere in the repository and
  therefore no `id_column`. MapLibre `setFeatureState` and `promoteId` are unavailable.
  Identity must be derived from attributes.
* **Most tables have no primary key.** Single-column natural keys are frequently not unique:

  | Table | Candidate | Distinct / Total |
  | :--- | :--- | ---: |
  | `areas_de_quilombolas_pe` | `cd_quilomb` | 3 / 10 |
  | `areas_de_quilombolas_pe` | `cd_sipra` | 100 % NULL |
  | `ibge_favelas_comunidades_pe` | `cd_fcu` | 849 / 2,381 |
  | `car_with_alerts_and_intersections` | `codsicar` | 21,982 / 28,473 |
  | `imovel_certificado_snci_privado_pe` | `cod_imovel` | 79 / 81 |
  | `processos_minerarios_pe` | `id` | 5,224 / 5,235 |

  **Composite keys are mandatory.** A single-column probe chain is insufficient.
* **`area_imovel_1.cod_imovel` has 36 collisions** across 433,105 rows. Those duplicate rows
  are **byte-identical geometries at the same location** (verified:
  `count(DISTINCT md5(ST_AsBinary(geometry))) = 1` for every sampled duplicate code). They are
  ingestion duplicates stacked on themselves, so hiding by `cod_imovel` removes every copy of
  *the same polygon* — the desired behaviour.

### 3.2 `search_index` as the query backbone

Built by [`src/build_search_index.py`](../../src/build_search_index.py):

```sql
CREATE TABLE search_index (
  id bigserial PRIMARY KEY, layer_id text NOT NULL, layer_rank integer NOT NULL,
  label text NOT NULL, label_norm text NOT NULL, code text, place text,
  search_text text NOT NULL, codes text NOT NULL,
  props jsonb NOT NULL,              -- to_jsonb(t) - 'geometry'
  geometry geometry(Geometry,4326) NOT NULL );
```

* `props` keys are **exactly the source table's columns minus `geometry`**, with Postgres types
  preserved into JSONB (`text` → string, `double precision` → number).
* `layer_id` == PostGIS table name == frontend layer id == Martin source name.
* **The table is dropped and recreated on every build** (`build_search_index.py:199`), so
  `search_index.id` is **not stable across pipeline runs**. Saved filters must store
  **predicates, never row ids**.
* Current size: **624,050 rows / 1017 MB** (688 MB heap + 301 MB indexes).

### 3.3 Query performance (measured)

| Pattern | Time |
| :--- | ---: |
| Correlated `EXISTS (SELECT 1 FROM search_index t WHERE … ST_Intersects(s.geometry, t.geometry))` | **13,960 ms** |
| Same, with `props @>` instead of `props->>` | 12,172 ms |
| **`MATERIALIZED` CTE on the target, joined from the target side** | **226 ms** |
| `props @> jsonb_build_object(k,v)` on `area_imovel_1` | 129 ms |
| `props ->> k = v` on `area_imovel_1` | 775 ms |
| Point-in-polygon `ST_DWithin(geometry, pt, 0)` + `layer_id` | **0.25 ms** |
| Natural-key lookup `props @> '{"cod_imovel": …}'` | 248 ms |

The correlated `EXISTS` makes the 433k-row layer the driving side and probes the shared GIST
index 429,750 times. **Fixing the row estimate does not fix it; only inverting the drive
direction does.** This is the single highest-risk item in the specification.

### 3.4 Geometry serialisation

* `ST_AsKML` **raises** on `GeometryCollection` (`lwgeom_to_kml2: 'GeometryCollection' geometry
  type not supported`) — 4 rows in `ucs_estaduais_cprh_pe`. One bad row aborts the entire
  export transaction, so a guard is mandatory.
* With the `ST_CollectionExtract` guard applied, `ST_AsKML` was run across **all 624,050 rows:
  zero errors**, 278 MB of KML geometry.

### 3.5 Other constraints

* **CORS is GET-only** (`search_api.py:28-33`); a POST preflight currently returns
  `400 Disallowed CORS method`.
* The `search` container runs `uv run --no-project --with fastapi --with uvicorn --with
  sqlalchemy --with psycopg2-binary` (`docker-compose.yml:38-41`), bypassing the project venv.
  **This specification introduces zero new runtime dependencies** — only stdlib `zipfile`,
  `xml.sax.saxutils` and `unicodedata` plus the already-present SQLAlchemy — so the `--with`
  list is untouched. `./src` is mounted whole, so new sibling modules need only
  `docker compose restart search`.
* `apps_1`, `reserva_legal_1` and `vegetacao_nativa_1` are rendered but **absent from
  `priorityOrder`** (`app.ts:127-172`), and the popup dispatcher has **no `else` branch**
  (`app.ts:2641-2694`). They are currently unclickable.
* Those three tables have **no `municipio` column** — their full column set is
  `cod_tema, nom_tema, cod_imovel, num_area, ind_status, des_condic, geometry`.
* `dat_criaca` / `dat_atuali` are `text` in `dd/mm/yyyy` format, not ISO dates.
* **The database is `conflitos_agrarios`** (`src/config.py:15`). `AGENTS.md:29` states
  `land_conflicts`, which is stale and corrected by this work.

---

## 4. Feature A — Controle de Visibilidade e Empilhamento

Frontend-only. No backend, database, Martin or ETL change.

### 4.1 Feature key derivation

A three-tier strategy resolved in a single function, so the JavaScript key and the MapLibre
expression can never drift apart.

* **Tier 0 — `feature.id`.** Probed unconditionally. Always `undefined` today; if Martin ever
  gains an `id_column`, hiding silently upgrades to a true stable id with no code change.
* **Tier 1 — per-layer `keyColumns: string[]`** declared on `LayerConfig`, required, authoritative.
  **All** listed columns are joined — not probed — because §3.1 proves composites are required.
  The separator is `\u001f` (UNIT SEPARATOR), which cannot occur in the data.

  ```
  js:       cols.map(c => props[c] == null ? '' : String(props[c])).join('\u001f')
  maplibre: ['concat', ['to-string', ['get', c1]], '\u001f', ['to-string', ['get', c2]]]
  ```

  `to-string` of null yields `''`, exactly matching the JavaScript branch. `coalesce` must
  **not** be used — it *skips* nulls and would desynchronise the two representations.

  **Key columns must be `text` or `integer`, never floating point.** `to-string(1.5)` and
  `String(1.5)` agree, but rounding diverges on other values. This is why `num_area` is
  excluded from `area_imovel_1`'s key despite reducing collisions from 36 to 32.
* **Tier 2 — dropped during implementation.** The original design made `keyColumns` optional
  and added a generic probe chain for layers declaring none. `keyColumns` was instead made a
  **required** field on `LayerConfig`, which forces a deliberate per-layer decision and makes
  the probe chain unreachable: a layer with no usable identity declares `keyColumns: []` and
  `keyStability: 'none'` explicitly. Dead code avoided; the required field is the stronger
  guarantee.

**Null guard (safety-critical).** If every key component resolves empty, the function returns
`null` and the UI **disables that row's hide button**. Without this, hiding one null-keyed
feature would set a filter matching *every* null-keyed feature in the layer.

#### `keyStability`

| Value | Layers | Behaviour |
| :--- | :--- | :--- |
| `unique` | 38 of the 40 clickable layers | Hide enabled, plain tooltip |
| `shared` | `area_imovel_1` (`[cod_imovel]`), `processos_minerarios_pe` (`[id]`) | Hide enabled; tooltip reads *"feições que compartilham este código são ocultadas em conjunto"* |
| `none` | `apps_1`, `reserva_legal_1`, `vegetacao_nativa_1` | Not in `priorityOrder`, so they never reach the stack UI. Declared for completeness |

Representative measured keys — the full table lives in `frontend/src/app/layers.config.ts`:

```
tis_poligonais                      [gid]                       unique  16/16
areas_de_quilombolas_pe             [nr_process, nm_comunid]    unique  10/10
sigef_privado_pe                    [parcela_co]                unique  21187/21187
imovel_certificado_snci_privado_pe  [cod_imovel, num_certif]    unique  81/81
car_with_alerts_and_intersections   [codsicar, alertcode]       unique  28473/28473
ibge_favelas_comunidades_pe         [cd_fcu, cd_setor]          unique  2381/2381
embargos_icmbio                     [ogc_fid]                   unique  246/246
area_imovel_1                       [cod_imovel]                SHARED  433069/433105
processos_minerarios_pe             [id]                        SHARED  5224/5235
aneel_* / epe_* / iterpe_* / moradia_*   [id]                   unique  (PK)
```

### 4.2 Hiding mechanism

The exclusion expression, applied across every rendered suffix (`_fill`, `_line`, `_circle`,
`_symbol`) via a shared helper mirroring the `toggleLayer` idiom (`app.ts:2866-2878`):

```ts
['!', ['in', KEY_EXPR(layerId), ['literal', keys]]]
```

A manually curated hide list stays well under ~50 entries, so no cap is required. Should one
ever be needed, `['match', KEY_EXPR, keys, false, true]` compiles to a hash lookup — valid here
because the key set is a `Set`, so `match` labels are guaranteed unique.

#### Filter composition — fixing the clobber

`applySigefFilter` (`app.ts:213-231`) and the hide filter both target
`sigef_casos_analisados_fill|_line`; today whichever runs last silently wins. A single composer
owns the final expression for every layer:

```ts
buildLayerFilter(layerId) {
  const parts = [];
  const domain = this.domainFilters.get(layerId);          // e.g. SIGEF fase
  if (domain) parts.push(domain);
  const keys = [...(this.hidden.get(layerId)?.keys() ?? [])];
  if (keys.length) parts.push(['!', ['in', this.keyExpression(layerId), ['literal', keys]]]);
  return parts.length === 0 ? null : parts.length === 1 ? parts[0] : ['all', ...parts];
}
```

`applySigefFilter` keeps computing exactly the expression it computes today — including the
`['==', ['get','fase'], '__none__']` sentinel for the empty case and `null` for all four phases
— but calls `setDomainFilter('sigef_casos_analisados', expr)` instead of its two `setFilter`
calls. Its existing call sites (`app.ts:1042`, `app.ts:2881`) continue to work unchanged.

Two behaviours fall out for free:

* `queryRenderedFeatures` **respects layer filters**, so hidden features vanish from the next
  click's stack automatically. *Hide the top one, click again, see what is underneath* requires
  no additional code.
* Hiding survives `toggleLayer` off/on, because the filter is independent of the `visibility`
  layout property. The hidden panel keeps listing them.

### 4.2b Interaction model: select vs. inspect

The detail popup is a 310 px card that frequently covers the very overlap being investigated.
Opening it on every click made the map hard to read, so the two actions are split:

| Gesture | Result |
| :--- | :--- |
| **Left click** | Fills the overlap panel with the features under the pointer. No popup; the map stays unobstructed. |
| **Right click** | Opens the detail popup for the top-priority feature, and refreshes the panel too. The browser context menu is suppressed via `originalEvent.preventDefault()`. |
| **"Abrir" in a panel row** | Same as right click, but for a specific row rather than the top-priority one. |

Both gestures run the same hit-test (`queryStackAt`), so the panel is consistent either way.
Because MapLibre popups default to `closeOnClick`, a left click also dismisses an open popup —
which reads naturally as "put the card away and pick something".

The search bar is unchanged: selecting a result still opens its popup, since the user asked
for that specific feature by name.

### 4.3 Overlap stack panel

**Decision: a dedicated Angular panel, not an extension of the popup.**

`openCustomPopup` (`app.ts:1088-1115`) is a single injection chokepoint and could technically
host the list, but it is rejected because:

1. The popup is a fixed 310 px raw-HTML surface (`app.css:303-318`) already carrying a title,
   badge, 3–8 sections and a KML button.
2. Every row action would need hand-escaped `data-action` attributes routed through the
   document-level listener (`app.ts:654-692`), with no Angular `@for`/`track`.
3. **Decisive:** the list must outlive the popup. Hiding the feature whose popup is open
   requires closing that popup — which is exactly when the user wants to hide the *next* one.

**Component:** `frontend/src/app/overlap-stack-panel/`, standalone, placed in
`.left-panels-stack` (`app.html:4-12`), following `sigef-batateiras-filter` exactly.
`.left-panels-stack` (`app.css:10-20`) gains `overflow-y: auto` since this becomes a 4th panel.

* **Row ordering: draw order, topmost first — not `priorityOrder`.** The user's problem is
  visual occlusion; `priorityOrder` is deliberately inverted hit-test ergonomics (points first
  so small targets stay clickable, `area_imovel_1` last). Ordering by it would bury CAR at the
  bottom of a list whose entire purpose is to say *"CAR is what you are looking at"*.
  The auto-opened popup still follows `priorityOrder`, so the active row is marked
  `.is-active` + `aria-current` to keep the correspondence unambiguous.
* **Deduplication on `${baseLayerId}\u001f${featureKey}` is required, not cosmetic.**
  `aneel_dup_pe` and `aneel_sobreposicoes_territorios_pe` each appear **twice** in
  `priorityOrder` (`_line` and `_fill`), and `queryRenderedFeatures` additionally returns one
  entry per tile for features crossing tile seams. Keep the first (highest-drawn) occurrence;
  fall back to positional dedupe for null-keyed features.
* **Duplicate fragments must be merged, not discarded.** `queryRenderedFeatures` clips each
  returned geometry to its tile, so a feature spanning tiles comes back as several partial
  shapes. Measured on `FAZENDA TABOADO (PARCELA 1)` / CAR `PE-2605707-75948D…` (498–512 ha,
  bbox `-38.5939,-8.5723 .. -38.5704,-8.5325`): **2 fragments at z12, 6 at z14, 15 at z15**.
  Keeping only the first fragment makes the hover preview and the stored hide-geometry show a
  clipped sliver instead of the parcel. `StackEntry.geometry` therefore holds the concatenation
  of every fragment as a Multi* geometry, and all highlighting reads that field rather than
  `feature.geometry`.
* **Row content:** colour chip (`.color-indicator`), layer name, feature title from the
  existing `KmlExportService.getFeatureTitle()` (`kml-export.service.ts:68-88`), and two
  actions — **Abrir** and **Ocultar**.
* **Abrir** reuses the proven `selectSearchResult` pattern (`app.ts:2754-2790`): close the
  popup, set `activeSelectedFeatureItem`, call `highlightFeature(entry.feature)`, then
  `renderPopupForLayer(entry.renderedLayerId, props, lngLat, underlyingSigefProps)`.
* **Ocultar** calls the visibility service, splices the entry out of the in-memory stack, and
  closes the popup if that entry was the active one.

### 4.4 Hidden-features section

A **second section inside the same component**, not a fifth panel — one toggle badge, one
count. Grouped by layer with a per-group header (colour chip, layer name, count, group-level
*Restaurar*), per-item restore, and a **Restaurar tudo** action that rebuilds every affected
layer's filter through `buildLayerFilter` so the SIGEF phase filter survives a global restore.
Feature titles are captured at hide time, so restoring never needs a re-query.

A persistent `.popup-detail-box-note` line states the shared-key caveat:
*"A ocultação é por código de identificação da feição; feições que compartilham o mesmo código
são ocultadas em conjunto."*

### 4.4b Hover preview

Pointing at any panel row — a stack row or a hidden row — outlines the corresponding area on
the map, so it is never ambiguous which feature a hide or restore will act on.

* A **separate** `hover-feature-source` with `hover-feature-{fill,line,circle}` layers, amber
  (`#f59e0b` / `#b45309`) against the blue selection highlight. A separate source is required:
  reusing `selected-feature-source` would clobber the click selection on every hover and need
  restoring on mouse-out.
* The hover layers are registered **before** the `selected-feature-*` layers, so the selection
  outline always draws on top of the preview.
* **This changes the reorder anchor.** `applyLayerOrder()` must anchor on the *lowest* overlay
  layer, now `hover-feature-fill`; anchoring on `selected-feature-fill` would move reordered
  data layers above the hover preview and bury it.
* Hidden features are no longer on the map, so `hide()` captures the feature's **geometry**
  alongside its label. The stored geometry is tile-simplified and may be clipped at a tile
  seam, which is acceptable for a transient cue — exports use exact PostGIS geometry.
* The preview is cleared on mouse-out, on leaving the panel body, on collapsing the panel, and
  whenever the hovered row disappears (hide, restore, restore-layer, restore-all).

### 4.5 Layer reordering

**`drawOrder: string[]` is decoupled from the `layers` array**, plus one idempotent reconciler.
The legend array is a *thematic* grouping (territórios tradicionais → SIGEF/SNCI → casos
analisados → CAR → ambiental → judicial → energia) and is **inverted** relative to the render
stack (index 0 draws at the bottom). Mutating it would scramble the thematic reading.

```ts
applyLayerOrder() {
  const anchor = this.map.getLayer('selected-feature-fill')
    ? 'selected-feature-fill' : this.firstLabelId;
  for (const layerId of this.drawOrder)                      // bottom → top
    for (const rid of renderedLayerIds(this.map, layerId))
      this.map.moveLayer(rid, anchor);
}
```

* `moveLayer(id, before)` inserts immediately below `before`. Iterating bottom→top against a
  **fixed top anchor** makes each successive layer land just under the anchor and therefore
  above everything moved before it. The final order is exactly `drawOrder`.
* **The anchor is `selected-feature-fill`, not `firstLabelId`.** The three `selected-feature-*`
  layers were added after the registration loop with `beforeId = firstLabelId`
  (`app.ts:1051`, `:1063`, `:1075`), so they already sit above all data. Anchoring at
  `firstLabelId` would push moved layers *over* the selection highlight.
* The satellite raster layers (`app.ts:802-871`) were added **before** the data loop, so they
  remain below by construction.
* The invariant **satellite < data < highlight < labels** is re-established on every call, so
  no drift accumulates across basemap switches.
* Cost: 74 `moveLayer` calls (31 × 2 fill+line, 2 line-only, 10 circle), one repaint.
  `moveLayer` only reorders `style._order`; no source refetch occurs.

**Controls** on each `.legend-item`, revealed on `:hover` / `:focus-within`:

| Control | Action | Label |
| :--- | :--- | :--- |
| `⤒` | move to end of `drawOrder` | Trazer para a frente |
| `↑` | swap with next | Avançar um nível |
| `↓` | swap with previous | Recuar um nível |
| `⤓` | move to index 0 | Enviar para o fundo |

Plus an always-visible `.layer-depth` badge showing `drawOrder.indexOf(id) + 1` (1 = backmost)
so the single-step controls give feedback. CDK drag-and-drop is rejected: `@angular/cdk` is not
installed, and 43 draggable rows in a 320 px scrolling thematically-ordered list is a poor
target. Every handler calls `$event.stopPropagation()` because `.legend-item` already carries
`(click)="toggleLayer(layer)"` (`app.html:84`); the precedent is `focusBatateiras($event)`.

**`priorityOrder` stays frozen.** Coupling depth to click precedence would make *"send a point
layer to the back"* render it unclickable — a strict regression. Once the stack panel exists,
click precedence no longer needs to change, because every feature under the cursor is
enumerated and individually selectable. A comment at its declaration records this.

### 4.6 File layout

| File | Change |
| :--- | :--- |
| `frontend/src/app/layers.config.ts` | **New.** `LayerConfig` (extended with `keyColumns?`, `keyStability?`), the 43 registry entries, `PRIORITY_ORDER`, `RENDERED_SUFFIXES`, `renderedLayerIds()`. Removes ~470 lines from `app.ts` |
| `frontend/src/app/services/feature-visibility.service.ts` | **New**, ~160 lines. `providedIn:'root'`, plain field mutation. Owns `attach(map, firstLabelId)`, the hidden map, domain filters, `drawOrder` and all key/filter/order methods |
| `frontend/src/app/overlap-stack-panel/` | **New.** Presentational component, injects both services |
| `frontend/src/app/app.ts` | Imports from `layers.config`; `applySigefFilter` delegates; publishes the stack from the already-computed `sorted[]`; two new handlers; `toggleLayer` loops `renderedLayerIds` |
| `frontend/src/app/app.html`, `app.css` | One new element; order controls; `overflow-y` on the panel stack |

`app.ts` keeps `layers = LAYERS.map(l => ({...l}))` — a **shallow copy, not an alias**, because
`toggleLayer` mutates `.visible`.

---

## 5. Feature B — Filtros Salvos e Exportação KML em Lote

### 5.1 `saved_filters` table

Owned by the new module `src/saved_filters.py`, which exposes `ensure_saved_filters_table(engine)`
plus CRUD helpers. Creation is invoked from three places so that any entry point produces a
working feature:

| Caller | Rationale |
| :--- | :--- |
| FastAPI lifespan startup in `src/search_api.py` | `docker compose up -d` alone must yield a working feature. Wrapped in `try/except` + `logger.warning` so a cold database never blocks API boot |
| A new step in `src/run_all_pipelines.py` | Matches the house convention that every table has an owning pipeline step. Costs ~5 ms |
| `if __name__ == "__main__":` guard | `uv run python -m src.saved_filters` for manual repair, matching `build_search_index.py:244-245` |

```sql
CREATE TABLE IF NOT EXISTS saved_filters (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text NOT NULL CHECK (btrim(name) <> ''),
    name_norm   text GENERATED ALWAYS AS (lower(btrim(name))) STORED,
    description text,
    definition  jsonb NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_saved_filters_name_norm  ON saved_filters (name_norm);
CREATE INDEX        IF NOT EXISTS idx_saved_filters_updated_at ON saved_filters (updated_at DESC);
```

* **`uuid` primary key**, not `bigserial` — ids reach the client, and an opaque identifier
  removes any enumeration temptation in a no-auth application. `gen_random_uuid()` is PostgreSQL
  13+ core; no `pgcrypto` extension is required.
* **`name_norm` generated + unique** rather than `UNIQUE(name)`, giving case- and
  whitespace-insensitive deduplication. It deliberately does **not** use `unaccent()`, which is
  `STABLE` rather than `IMMUTABLE` and is therefore rejected by PostgreSQL in a generated
  column. `lower()` and `btrim()` are both immutable.
* **No geometry column**, so Martin's auto-discovery ignores the table — the same rule that
  keeps `search_index` out of the tile catalog.
* **`CREATE TABLE IF NOT EXISTS` deliberately breaks** the `DROP TABLE … CREATE TABLE`
  full-rebuild convention used by `build_search_index.py:202-217` and the ETL scripts. The
  module carries an explicit comment explaining why, because it will otherwise look wrong.

#### Operational consequence

`saved_filters` becomes **the only table in the database that `run_all_pipelines.py` cannot
regenerate**. `docker compose down -v` destroys the `pgdata` volume and the filters with it.
Mitigations shipped with the feature:

1. `GET /filters` returns every filter with its full definition, and `POST /filters/import`
   upserts by `name_norm` — surfaced as **Exportar / Importar filtros (JSON)** in the panel
   footer.
2. `README.md` and `AGENTS.md` document the hazard plus a `pg_dump -t saved_filters` one-liner.
   Note that `.gitignore` already excludes `*.sql` and `*.dump`.

### 5.2 Filter definition schema

Versioned and **layer-block structured**. Blocks are OR-ed, compiled as `UNION ALL`.

```json
{
  "version": 1,
  "text": "batateira",
  "blocks": [
    {
      "layer": "area_imovel_1",
      "match": "all",
      "conditions": [
        { "field": "ind_status", "op": "eq",  "value": "AT" },
        { "field": "num_area",   "op": "gte", "value": 100 }
      ],
      "spatial": [
        { "relation": "intersects", "layer": "tis_poligonais" }
      ]
    }
  ]
}
```

**Why layer blocks rather than a flat `layers: []` with shared conditions:** a field such as
`ind_status` exists on `area_imovel_1` but not on `processos_conflitos_judiciais`. A flat shape
forces either *"silently matches nothing"* (a trap) or *"the field must exist in every layer"*
(useless). Blocks make field validation unambiguous, let each layer receive its own optimal
query plan, and map one-to-one onto both the per-layer ZIP grouping mode and the per-layer
`<Folder>` in the KML document.

#### Operators

| Group | `op` | Compiles to |
| :--- | :--- | :--- |
| Equality | `eq` | `props @> jsonb_build_object(:f, :v)` — the fast path |
| | `neq` | `NOT (props @> jsonb_build_object(:f, :v))` |
| | `in`, `not_in` | OR-chain of containment, preserving the fast path |
| Text | `contains`, `not_contains`, `starts_with` | `lower(unaccent(props->>:f)) LIKE …` |
| Presence | `is_null`, `is_not_null` | `props->:f IS NULL OR jsonb_typeof(props->:f) = 'null'` |
| Numeric | `gt`, `gte`, `lt`, `lte`, `between` | guarded accessor, §5.3 |
| Date | `date_gte`, `date_lte`, `date_between` | guarded dual-format accessor, §5.3 |
| Spatial | `intersects`, `not_intersects` | materialised CTE, §5.3 |

`match` is `"all"` (AND) or `"any"` (OR) within a block. The top-level `text` is global and
matched against `search_index.search_text` / `codes`, reusing the exact `search_api.py:60-62`
idiom (measured 2.5 ms via `idx_search_index_search_text`).

#### Worked examples

**A — "CAR pendentes sobre Terras Indígenas"** is the JSON above with `ind_status = 'PE'`.
Measured **750 features**, and the plan verified as the fast shape: `CTE Scan on t0_0` (16 rows)
driving `Index Scan using idx_search_index_geometry` over 16 loops, **12.6 ms execution**.
This is the canonical acceptance case.

It is also the one worth running first analytically. Measured across the whole registry:
**53.3 % of all pending CAR registrations (750 of 1,406) overlap an Indigenous Land**, against
7.7 % of cancelled ones (150 of 1,949) and 0.004 % of active ones (16 of 429,750). The same
filter with `ind_status = 'AT'` returns only 15 features — a corner of the data, not a
representative case.

**B — "APPs e Reserva Legal em assentamentos do INCRA"** uses two blocks, each with only a
spatial condition against `assentamentos_incra_pe`. The equivalent single-block query against
`area_imovel_1` measured **436 ms / 17,856 matches** — the realistic scale ceiling.

**C — "Autos de infração do ICMBio fora de UCs federais"** combines `nome_uc is_null` with
`not_intersects limiteucsfederais_a`. It is also the regression case for the `MultiPoint`
defect: all 861 rows currently export with empty geometry.

### 5.3 Filter → SQL compiler

`src/filter_compiler.py` is **pure**: no database connection, no `src.database` import, no I/O.
The column catalog is injected, which is what makes it testable without a database.

```python
class FilterError(ValueError): ...

@dataclass(frozen=True)
class CompiledFilter:
    sql: str
    params: dict[str, Any]
    layers: tuple[str, ...]

def compile_filter(definition, catalog, *, select="count", limit=None) -> CompiledFilter
```

`select` ∈ `count | count_by_layer | features | ids`.

#### Injection safety — three independent layers

1. **Field names are bound parameters, not SQL identifiers.** Because every condition reads
   `search_index.props`, the field name is a *value*: `props -> :f0`,
   `jsonb_build_object(:f0, :v0)`. The layer is likewise bound as `layer_id = :l0`. **There is
   no user-controlled SQL identifier anywhere in the generated statement.** This property falls
   out of building on `search_index` rather than on source tables, and is the single largest
   de-risking decision in the design.
2. **Syntactic validation** — `re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", name)` for both fields
   and layer ids, rejected before any catalog lookup.
3. **Catalog membership** — the layer must be in the catalog and the field in that layer's
   column set, raising `FilterError` naming the offending value. The catalog is built from
   `information_schema.columns` **intersected with** `{s["table"] for s in SEARCH_SOURCES}`, so
   a user can never target a table that is not an indexed layer.

The only structural interpolation is the comparison symbol, drawn from a frozen `dict[str, str]`.

#### Numeric and date accessors

A bare `(props->>'f')::numeric` raises on any non-numeric row. An `AND`-chained `jsonb_typeof`
guard is **also unsafe**, because the planner may reorder `AND` operands. `CASE` is the
documented-safe construct — its arms evaluate only when the `WHEN` holds:

```sql
CASE
  WHEN jsonb_typeof(props -> :f0) = 'number'
    THEN (props ->> :f0)::numeric
  WHEN jsonb_typeof(props -> :f0) = 'string'
       AND props ->> :f0 ~ '^\s*-?[0-9]+([.,][0-9]+)?\s*$'
    THEN replace(btrim(props ->> :f0), ',', '.')::numeric
END > :v0
```

The second arm covers text columns holding numerals, including pt-BR decimal commas. A `NULL`
result makes the comparison `NULL`, so the row is excluded — the desired semantics. Measured
365 ms on `area_imovel_1`.

Dates use the analogous dual-format accessor required by §3.5:

```sql
CASE
  WHEN props ->> :f0 ~ '^[0-9]{2}/[0-9]{2}/[0-9]{4}$' THEN to_date(props ->> :f0, 'DD/MM/YYYY')
  WHEN props ->> :f0 ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}'  THEN substring(props ->> :f0, 1, 10)::date
END
```

#### Spatial compilation — mandatory form

Per §3.3 the correlated `EXISTS` form is 62× slower and **must never be emitted**. The compiler
always produces:

```sql
WITH t0 AS MATERIALIZED (
    SELECT geometry AS g FROM search_index WHERE layer_id = :t0_layer
),
m0 AS (
    SELECT DISTINCT s.id
    FROM t0
    JOIN search_index s
      ON s.geometry && t0.g
     AND ST_Intersects(s.geometry, t0.g)
    WHERE s.layer_id = :l0
      AND <attribute predicates pushed down here>
)
SELECT s.id, s.layer_id, s.label, s.place, s.props, s.geometry
FROM search_index s JOIN m0 ON m0.id = s.id
```

Three elements make the GIST index work and all three are required:

* the **explicit `&&`** before `ST_Intersects`, keeping the index condition visible if the
  planner reshapes the function call;
* **`AS MATERIALIZED`** — without it PostgreSQL inlines the CTE and reverts to the 14 s plan;
* **driving from the small side**, so the target layer (16 rows for `tis_poligonais`) leads.

Verified plan: `CTE Scan on t0 (16 rows)` → `Index Scan using idx_search_index_geometry
(16 loops)`. Attribute predicates are pushed inside `m0` so the `DISTINCT` deduplicates fewer
rows. `not_intersects` compiles as an **anti-join against the materialised positive set**, never
as a correlated `NOT EXISTS`. Multiple spatial conditions produce one `tN`/`mN` pair each,
intersected by `id`.

Every preview query runs under `SET LOCAL statement_timeout = '20s'`.

#### Known scale limits

* Attribute-only filters on `area_imovel_1` always sequential-scan (~129 ms with `@>`, ~365 ms
  numeric). The planner correctly rejects `idx_search_index_layer_id` because that layer is
  69 % of the table. Acceptable for a preview.
* `not_intersects` with no attribute conditions on `area_imovel_1` legitimately returns
  ~415,000 features. The compiler must not refuse it; the export endpoint enforces the caps.

### 5.4 API surface

New `src/filters_api.py` (CRUD, catalog, preview) and `src/export_api.py` (KML/ZIP), each
exposing an `APIRouter`. `src/search_api.py` gains `include_router` calls and the CORS change.
`search_api.py` is 118 lines and deliberately single-purpose; this feature adds ~450.
No `docker-compose.yml` change is needed — `./src` is mounted whole and the entrypoint is
`src.search_api:app`, so `docker compose restart search` picks up new sibling modules.

| Method | Path | Request / Response |
| :--- | :--- | :--- |
| `GET` | `/filters` | `[{id, name, description, definition, created_at, updated_at}]` |
| `POST` | `/filters` | `{name, description?, definition}` → 201; **409** on `name_norm` conflict |
| `GET` | `/filters/{id}` | record; 404 |
| `PUT` | `/filters/{id}` | partial update, `updated_at = now()`; 409 / 404 |
| `DELETE` | `/filters/{id}` | 204 |
| `POST` | `/filters/import` | `[records]` → `{imported, skipped}`, upsert by `name_norm` |
| `GET` | `/filters/catalog` | `{layers: [{id, fields: [{name, data_type, kind}]}]}` |
| `GET` | `/filters/catalog/{layer}/fields/{field}/values` | `?limit=200` → `{values: [{value, count}], truncated}` |
| `POST` | `/filters/preview` | `{definition}` → `{total, by_layer, sample}` |
| `POST` | `/export/kml` | `{definition \| saved_filter_id, grouping, style}` → streaming ZIP |
| `POST` | `/export/kml/feature` | §5.6 → single `.kml` |

**Field catalog uses `information_schema.columns`, not `jsonb_object_keys`.** Both would work —
`to_jsonb(t)` guarantees keys equal columns — but `information_schema` additionally returns
**`data_type`**, which the UI needs to offer the correct operators and the compiler needs to
select the numeric, date or text accessor. It is one query for all layers and is already the
project idiom (`build_search_index.py:133-140`). `column_name = 'geometry'` is filtered out, and
the result is cached in a module-level dict with a short TTL since it changes only on a pipeline
run.

`kind` is derived from `data_type`: `double precision|numeric|integer|bigint|real` → `number`;
`date|timestamp*` → `date`; a `text` column whose first sampled non-null value matches
`^\d{2}/\d{2}/\d{4}$` → `date` (this is how `dat_criaca` receives correct operators despite
being stored as text); otherwise `text`.

The **value catalog** needs a cardinality guard: `municipio` on `area_imovel_1` is 184 distinct
(294 ms, fine) but `cod_imovel` is 433,069 distinct. The query runs
`GROUP BY … ORDER BY count DESC LIMIT :limit + 1`; if `limit + 1` rows return it reports
`truncated: true` and the UI falls back to a free-text input instead of a dropdown.

**CORS** (`search_api.py:28-33`) becomes:

```python
allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
allow_headers=["*"],
expose_headers=["Content-Disposition"],
```

`expose_headers` is **mandatory and easy to miss** — without it the browser hides
`Content-Disposition` from the `HttpClient` blob response and downloads receive a random
filename. `allow_origins` is unchanged.

### 5.5 Python KML writer

`src/kml_writer.py` ports `frontend/src/app/services/kml-export.service.ts` function for
function, preserving output semantics: `hex_to_kml_color` (`:20-38`), `escape_xml` (`:43-51`),
`sanitize_filename` (`:56-63`, via `unicodedata.normalize('NFD', …)`), `feature_title` (all 16
rungs, `:68-88`), `html_description` (`:93-146`, CDATA table with pt-BR `ha` and date
formatting and the *"Plataforma de Mapeamento de Conflitos Agrários • PE"* footer),
`extended_data` (`:151-159`), `placemark` (`:222-238`) and `document` (`:243-310`, style
deduplication per `layerId + fill + border`, one `<Folder>` per layer named `"<Nome> (<n>)"`).

**Geometry serialisation is NOT ported.** The SELECT uses PostGIS `ST_AsKML(geom, 7)`, which is
shape-compatible with the TypeScript output and additionally handles `MultiPoint` correctly,
fixing the 861-feature defect for free. The guard required by §3.4:

```sql
ST_AsKML(
  CASE WHEN GeometryType(geometry) = 'GEOMETRYCOLLECTION'
       THEN ST_CollectionExtract(geometry)
       ELSE geometry END,
  7) AS geom_kml
```

`ST_CollectionExtract` with no type argument (PostGIS 3.2+) returns the highest-dimension
components, converting the 4 `ucs_estaduais_cprh_pe` collections into clean `MultiPolygon`.
Delegating geometry to PostGIS also keeps `kml_writer.py` pure — the fragment arrives as a
string — so the module is fully testable with no database.

**Style and layer-name metadata are client-supplied.** `LayerConfig.fillColor`, `borderColor`
and `name` live only in `app.ts:233-647`; mirroring 43 entries server-side would guarantee drift
the first time a layer is recoloured. The request carries
`style: {"<layer_id>": {"name", "fill", "border"}}`; the server falls back to `#3b82f6` /
`#1d4ed8` / `layer_id` and **validates every colour against `^#[0-9a-fA-F]{3,8}$`** before it
reaches the XML.

**Streaming, never buffered.** A small unseekable sink exposing `write` / `tell` / `flush` is
wrapped by `zipfile.ZipFile(sink, 'w', ZIP_DEFLATED)` and driven by a generator feeding
`StreamingResponse`; Python's `zipfile` supports non-seekable output by writing data
descriptors. On the database side `conn.execution_options(stream_results=True, yield_per=1000)`
keeps 17k rows out of memory. Peak RSS stays at roughly one KML document. This also sidesteps
§3.5 — the container has no writable data mount, so a temp-file design would have failed.

| Mode | Cap | Reasoning |
| :--- | ---: | :--- |
| `layer` | 50,000 features | ~430 B `ST_AsKML` + 339 B–1.2 kB props, ~3 kB per placemark with description and `ExtendedData` → ~150 MB raw, ~15 MB deflated. Split into `<layer>_parteNN.kml` at 25,000, well before Google Earth becomes unusable. Realistic worst case (CAR ∩ assentamentos = 17,856) sits comfortably inside |
| `feature` | 2,000 features | Each entry repeats the ~700 B `<kml><Document><Style>` envelope and costs a ZIP central-directory record. Beyond this the mode is a misuse |

Per-feature entries are named `<layer-slug>/<title-slug>_<rownum>.kml`. **The `_<rownum>`
suffix is not optional** — `area_imovel_1` has 36 duplicate `cod_imovel` values and `apps_1`
holds 273,296 rows over 47,005 distinct codes, so titles collide massively. Every archive
includes `LEIAME.txt` with the filter name, the definition JSON, per-layer counts and an ISO
timestamp. Exceeding a cap returns **413** with `{total, cap, grouping}`; the UI previews first,
so this is normally caught client-side. Archive filename:
`conflitos_pe_<filtro-slug>_<YYYYMMDD>.zip`.

### 5.6 Retiring `kml-export.service.ts`

The hard sub-problem is locating the exact PostGIS geometry for a feature clicked in a tile,
given no MVT feature id and no primary key on most tables. Both candidates were measured:

| Strategy | Time |
| :--- | ---: |
| Natural key — `props @> '{"cod_imovel": …}'` | 248 ms (sequential scan; no index on `props`) |
| **Point-in-polygon — `ST_DWithin(geometry, pt, 0)` + `layer_id`** | **0.25 ms** (GIST index scan) |

Point-in-polygon wins by roughly 1000× and requires no hand-curated per-layer natural-key
catalog, which does not exist and would need maintaining for 43 layers.

`POST /export/kml/feature` accepts
`{layer, lng, lat, zoom, tolerance_px, props, search_index_id?, style}` and resolves:

```sql
SELECT id, layer_id, label, props,
       ST_AsKML(CASE WHEN GeometryType(geometry) = 'GEOMETRYCOLLECTION'
                     THEN ST_CollectionExtract(geometry) ELSE geometry END, 7) AS geom_kml
FROM search_index
WHERE layer_id = :layer
  AND ST_DWithin(geometry, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), :tol)
ORDER BY (props @> :hint::jsonb) DESC,
         ST_Distance(geometry, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)) ASC,
         ST_Area(geometry) ASC
LIMIT 1
```

* **`:tol`** is `0` for `_fill` layers — `ST_DWithin(…, 0)` is equivalent to `ST_Intersects` and
  still uses the index — and `360 / (512 * 2**zoom) * tolerance_px` degrees for `_circle` and
  `_line` layers.
* **`:hint`** is the tile's properties filtered server-side to **string-valued keys only**,
  because MVT rounds numbers and omits nulls. It is a **ranking** term, never a filter, so a
  mismatch degrades gracefully to *"nearest, smallest"* instead of returning nothing.
* **`ST_Area ASC`** breaks ties toward the smallest containing polygon — an APP inside a CAR
  inside a municipality is what the user visually clicked.
* **`search_index_id` short-circuit:** search-bar selections already carry the exact
  `search_index.id` (`search_api.py:105`), so the spatial lookup is skipped entirely. The
  server verifies `layer_id` matches and falls back to the spatial query otherwise, which also
  neutralises the id-instability risk from §3.2 if a pipeline runs mid-session.
* A 404 surfaces an inline error in the popup. The client must **never** silently download an
  empty file.

`KmlExportItem` is replaced by
`ActiveFeatureRef {layerId, layerName, fillColor, borderColor, lng, lat, zoom, props, searchIndexId?}`.
Touch points: `app.ts:2736-2742` (click path, no `searchIndexId`), `app.ts:2781-2787` (search
path, `searchIndexId: result.id`), and `app.ts:656-663` (handler, now asynchronous — the button
is disabled and relabelled *"Gerando…"* while in flight). The popup markup at `app.ts:1090-1098`
is unchanged, as is `clearFeatureHighlight()`.

**`frontend/src/app/services/kml-export.service.ts` is deleted.** Nothing functional survives
except the ~10-line blob-download helper (`:315-326`), which moves into the new
`export.service.ts` because `HttpClient` with `responseType: 'blob'` still needs it. One
exception: `getFeatureTitle()` is still used by Feature A's stack panel, so if Feature A ships
first it is relocated to a small shared helper rather than deleted outright.

### 5.7 `SEARCH_SOURCES` additions

Appended after `area_imovel_1` (`build_search_index.py:117`). All three tables share the exact
column set `cod_tema, nom_tema, cod_imovel, num_area, ind_status, des_condic, geometry`, so
`place` is `[]` per §3.5:

```python
{"table": "apps_1", "label": ["cod_imovel"], "codes": ["cod_imovel"],
 "text": ["nom_tema", "des_condic"], "place": [], "searchable": False},
{"table": "reserva_legal_1", "label": ["cod_imovel"], "codes": ["cod_imovel"],
 "text": ["nom_tema", "des_condic"], "place": [], "searchable": False},
{"table": "vegetacao_nativa_1", "label": ["cod_imovel"], "codes": ["cod_imovel"],
 "text": ["nom_tema", "des_condic"], "place": [], "searchable": False},
```

**Measured impact:** `search_index` grows from 624,050 to **1,275,209 rows (+104 %)** and from
**1017 MB to approximately 2.0–2.2 GB**. The three source tables total 1,134 MB. Step 8 of the
pipeline roughly doubles in duration, dominated by the two GIN trigram index builds
(`build_search_index.py:231-232`). **This is the principal cost of the feature and must be
accepted deliberately before the rebuild is run.**

**The search bar continues to exclude them.** `apps_1` holds 273,296 rows over only 47,005
distinct `cod_imovel`, and that code identifies the *parent* property rather than the feature,
so typing a CAR code would return dozens of visually identical rows. A `searchable: False` flag
plus a ~4-line exclusion around `search_api.py:62-67` keeps them out of search unless explicitly
named in `?layers=`, while leaving them fully filterable and exportable because the compiler
reads `search_index` directly.

**Blocking prerequisite.** Per §3.5 these layers are currently unclickable. Before they become
selectable, `frontend/src/app/app.ts` needs the three `_fill` ids appended to `priorityOrder`
(`:127-172`) and a `renderCarSubLayerPopup` branch in the dispatcher (`:2641-2694`), which has
no `else` and would otherwise open nothing. One renderer covers all three, since they share the
same six attributes, and it links back to the parent `cod_imovel`.

### 5.8 Filter builder UI

```
frontend/src/app/filter-builder/
  filter-builder.component.{ts,html,css}   — panel shell, saved-filter list, export dialog
  filter-block.component.{ts,html,css}     — one layer block: layer picker, conditions, spatial
  condition-row.component.{ts,html,css}    — field / operator / value, operators driven by `kind`
frontend/src/app/services/
  filter.service.ts                        — CRUD, catalog, preview
  export.service.ts                        — KML / ZIP download
```

Standalone components following the `search-bar/` and `sigef-batateiras-filter/` precedent
exactly. `filter.service.ts` **reuses `SEARCH_API_URL` from `search.service.ts:5`** — a second
base-url constant must not be introduced. `FormsModule` / `ngModel` is used for the dynamic
value inputs: `@angular/forms` is already a declared dependency and currently unused, so it
costs no install, and hand-rolling `(input)` bindings for a dynamic condition list is far worse.

The panel is appended to `.left-panels-stack` (`app.html:4-12`) after
`<app-sigef-batateiras-filter>`, at the stack's standard **320 px** width with the `isOpen`
toggle pattern from `sigef-batateiras-filter.component.ts:24,66-68`, and is wired with
`[layerMeta]="searchLayerMeta"` (reusing the existing map at `app.ts:650-652`).

Design language per `AGENTS.md` §1.3 — `rgba(255,255,255,0.92)` with `backdrop-filter: blur(12px)`,
`border-radius: 10px` and the two-layer shadow from `app.css:141-147`; `.popup-detail-box`
neutrals (`app.css:481-511`) for condition rows; monospace for codes; Angular 20 `@if` / `@for …
track`; pt-BR strings; **SVG stroke icons only, no decorative emojis**.

The **export dialog** first calls `POST /filters/preview` (debounced 400 ms using the
`search-bar.component.ts:49-76` pattern) and shows the total with a per-layer breakdown. Two
radio cards offer **Um KML por camada** (cap 50,000) and **Um KML por feição** (cap 2,000); the
option over its cap renders **disabled with the reason inline**, so a 413 is never a surprise.
Confirming posts to `/export/kml` with the `grouping` and the `style` map built from
`this.layers`, shows progress on the button, then triggers the blob download.

---

## 6. Testing Strategy

The repository has **no test framework, linter or CI** today. This specification introduces
`pytest` for the two new pure modules only — it does not retrofit tests across the codebase.

```toml
[dependency-groups]
dev = ["pytest>=8.4"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
addopts = "-q"
```

`src` is a PEP 420 namespace package (there is no `src/__init__.py`), so `pythonpath = ["."]`
is sufficient — pytest's built-in equivalent of the manual `sys.path` prepend every script
performs (`build_search_index.py:16-18`, `search_api.py:15-17`). No `conftest.py` path hack is
needed.

**Hard constraint:** tests import `src.filter_compiler` and `src.kml_writer` **only**, never
`src.search_api`, which calls `get_engine()` at import time (`search_api.py:35`). Both new
modules must therefore avoid importing `src.database` at module scope. Run with
`uv run --group dev pytest`. The Docker `search` service is untouched; pytest never enters a
container.

```
tests/conftest.py              # FAKE_CATALOG fixture mirroring the real column sets
tests/test_filter_compiler.py
tests/test_kml_writer.py
```

### 6.1 Compiler cases

| # | Case |
| :-- | :--- |
| 1–2 | Unknown layer and unknown field raise `FilterError` naming the offending value |
| 3 | Hostile field names (`a"b`, `a;DROP`, `' OR 1=1--`) are rejected **and** appear nowhere in `compiled.sql` |
| 4 | Each operator produces the expected `params`; literal values never appear in the SQL string |
| 5 | Numeric operators emit `CASE WHEN jsonb_typeof(` and **never** a bare `)::numeric` outside a `CASE` |
| 6 | Date operators emit both the `DD/MM/YYYY` and ISO branches |
| 7 | **Regression guard for the 14 s plan:** spatial conditions emit `AS MATERIALIZED` and `compiled.sql` must not contain `EXISTS (SELECT 1 FROM search_index` |
| 8 | `not_intersects` emits the anti-join against the materialised set, not a correlated `NOT EXISTS` |
| 9–10 | Multi-block definitions produce one `UNION ALL` branch per block; `match` maps to `AND` / `OR` |
| 11–13 | Empty conditions yield a valid layer-only SELECT; all four `select` shapes; `version: 2` raises |
| 14 | **Parameter-name uniqueness** across blocks and spatial CTEs — `len(params) == len(set(params))`, and every `:name` in the SQL is bound |

### 6.2 KML writer cases

| # | Case |
| :-- | :--- |
| 1 | `hex_to_kml_color('#84cc16') == 'ff16cc84'`; 3-char, 8-char, no `#`, empty → `'ff000000'`; the `'66'` translucent-fill default |
| 2–3 | `escape_xml` over `& < > " '` and non-string inputs; `sanitize_filename('Sítio Batateiras nº 1')` accent-stripped and lowercased |
| 4 | `feature_title` — one case per rung of the 16-rung chain, including `"CAR {cod_imovel}"` and the final `"{layer} (ID: …)"` fallback |
| 5 | `html_description` emits `<![CDATA[`, skips the excluded keys, formats `num_area` as `"1.234,5678 ha"`, and escapes a value containing `<script>` |
| 6–7 | `extended_data` JSON-serialises dict/list values; `document()` deduplicates identical styles and emits one `<Folder>` per layer named `"<Nome> (<n>)"` |
| 8 | **Well-formedness:** every generated document is parsed with `xml.etree.ElementTree.fromstring` — a bug class the TypeScript implementation could never catch |
| 9 | ZIP assembly — per-layer entry naming and the 25,000 split; three features with identical titles produce three distinct entry names; `LEIAME.txt` present; `ZipFile.testzip() is None` |
| 10 | Streaming — 5,000 synthetic placemarks keep the sink's peak buffer bounded by the chunk size |

### 6.3 Database-level verification

The compiler's generated SQL is additionally verified by hand against the live database, because
no unit test can catch a planner regression:

```bash
docker exec conflitos_agrarios_db psql -U postgres -d conflitos_agrarios \
  -c "EXPLAIN (ANALYZE) <compiled sql>"
# PASS: "CTE Scan on t0" + "Index Scan using idx_search_index_geometry", < 1000 ms
# FAIL: "Parallel Seq Scan on search_index s" feeding a Semi Join   (= the 14 s plan)
```

---

## 7. Acceptance Criteria

### 7.1 Feature A — canonical case: CAR over Terra Indígena Fulni-ô

Verified reference data: 179 `area_imovel_1` polygons intersect this TI; `tis_poligonais.gid =
130`; municipalities Itaíba and Águas Belas; centroid `-37.1108, -9.1137`.

1. Searching `Fulni` and selecting the Terra Indígena flies the map there and auto-enables the
   layer; the polygon is visible.
2. Enabling **CAR - Imóveis Cadastrados** smothers it under a dense mesh — the condition being
   fixed.
3. Clicking `-37.14253, -9.11794` (a verified interior point of a CAR ∩ Fulni-ô overlap) lists
   the CAR polygon as row 1 of the stack panel, with the TI row marked `.is-active`.
4. **Abrir** on the CAR row switches the popup, the dashed highlight and the KML target.
5. **Ocultar** removes that polygon, closes the popup, clears the highlight, and adds it to
   *Ocultas (1)*.
6. Clicking the same point again no longer returns the hidden polygon; repeating reveals
   progressively deeper features.
7. **Enviar para o fundo** on CAR makes the TI read cleanly through the 0.4-opacity CAR fill;
   its depth badge reads `1`.
8. **Boundary invariants hold:** the `selected-feature-*` highlight still paints above all data;
   the satellite basemap still paints beneath it; place labels still paint on top.
9. **Filter-composition regression:** with SIGEF Casos Analisados enabled and two phases
   unchecked, hiding one remaining polygon removes it **and leaves the two unchecked phases
   hidden**. Re-checking all four restores everything except the individually hidden feature.
   Before this change, one filter silently wiped the other.
10. **Shared-key honesty:** at `-39.90206, -8.16738` the CAR code
    `PE-2610400-F74BDA7174B041B893CFF097FAB0B12A` has 4 byte-identical stacked rows; hiding it
    removes all four in one action, consistent with the panel's stated caveat.
11. A hard reload returns everything to registry defaults — the session-only guarantee.

### 7.2 Feature B

12. Building `ind_status = PE` + intersects **Terras Indígenas** on CAR settles the preview at
    **750 feições**; the same filter with `ind_status = AT` and `num_area ≥ 100` returns **15**.
    Both verified against hand-written SQL.
13. Saving as `CAR ativos em TI` succeeds; saving again under the same name reports a duplicate
    (409 from `idx_saved_filters_name_norm`).
14. Reloading the browser keeps the filter listed — it lives in PostgreSQL, not `localStorage`.
15. **Carregar** reconstructs every block, condition and spatial clause, and the preview
    re-counts to 18.
16. **Exportar KML → Um KML por camada** downloads
    `conflitos_pe_car-ativos-em-ti_<data>.zip` containing `area_imovel_1.kml` and `LEIAME.txt`;
    Google Earth shows 18 polygons in a `CAR - Imóveis Cadastrados (18)` folder with the
    client-supplied fill and the pt-BR balloon.
17. **Um KML por feição** produces 18 entries named `area_imovel_1/<título>_<n>.kml`.
18. **Cap enforcement:** an unconditioned `apps_1` filter (273,296 rows) renders the per-feição
    card disabled with the 2,000 limit explained; forcing it via `curl` returns **413**.
19. **Geometry-bug regression:** clicking a CAR polygon and exporting produces a coordinate ring
    that matches `SELECT ST_AsKML(geometry, 7) FROM search_index WHERE …` **exactly**. Before
    this change it would not.
20. **MultiPoint regression:** an `autos_infracao_icmbio` export contains
    `<MultiGeometry><Point>`; previously it emitted an empty `<Placemark>`.
21. **GeometryCollection regression:** an unconditioned `ucs_estaduais_cprh_pe` export returns
    all 60 features without a 500.
22. The POST preflight `OPTIONS /filters` returns 200 where it returns `400 Disallowed CORS
    method` today.

---

## 8. Implementation Sequence

Feature A and Feature B are independent and may be reviewed and merged separately.

| Phase | Steps |
| :--- | :--- |
| **A** | Extract `layers.config.ts` → `feature-visibility.service.ts` (keys, filter composition, reroute `applySigefFilter`) → publish the overlap stack → panel with *Feições neste ponto* → hide + *Ocultas* → layer reordering |
| **B.1** | pytest scaffold → `kml_writer.py` (pure, then ZIP and streaming) → `filter_compiler.py` (attributes, then spatial, verified with `EXPLAIN ANALYZE`) → `saved_filters.py` |
| **B.2** | CORS, lifespan hook and router registration → `filters_api.py` → `/filters/preview` → `export_api.py` → `/export/kml/feature` |
| **B.3** | `priorityOrder` + popup branch for the CAR sub-layers → `SEARCH_SOURCES` entries → rebuild the index (**doubles the database**) → register the pipeline step |
| **B.4** | `filter.service.ts` + `export.service.ts` → rewire the popup button and delete `kml-export.service.ts` → `condition-row` + `filter-block` → `filter-builder` shell → export dialog |
| **Docs** | `docs/CHANGELOG.md` entry, `README.md` section, and the `AGENTS.md:29` correction plus the `down -v` warning |

---

## 9. Follow-up Work (explicitly deferred)

* **`place` for the CAR sub-layers.** Deriving `municipio` requires a
  `cod_imovel → area_imovel_1.municipio` join, which `_build_insert`
  (`build_search_index.py:143-190`) does not support — it offers only the `ibge` lookup pattern
  at `:157-160`. Shipping `place: []` in v1.
* **Spatial relations `within` / `contains`.** Trivial additions, deferred until a confirmed
  requirement exists.
* **`dwithin` in metres.** Requires a `::geography` index that `search_index` does not have.
* **A CAR × `limiteucsfederais_a` pair in `src/overlaps.py`.** SIGEF and SNCI each have one
  (branches `7` and `9` of `calculate_overlaps()`) but CAR does not — a genuine gap in the overlap matrix, unrelated
  to this specification but worth recording.
* **Area and dominance metrics on `land_overlaps`.** The table carries no area, percentage or
  z-order information; `calculate_energy_overlaps()` (`overlaps.py:340-351`,
  `area_sobreposicao_ha` / `pct_territorio`) is the in-repository precedent if this is ever
  needed.
* **Persisting hidden features or layer order**, should the session-only decision be revisited.
