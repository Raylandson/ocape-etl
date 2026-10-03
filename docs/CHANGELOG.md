# Project Changelog & Architectural History

This document chronicles the architectural evolutions, dataset ingestions, and major engineering milestones of the Land Conflict Mapping Platform.

---

## Chronological Change Log

### October 2026: PPCAC Conflict Areas — Comprehensive Cross-Referencing (SIGEF, CAR, ITERPE, INCRA, DataJud & Despejo Zero)
- **Why**: Full cross-referencing between official state conflict mediation dossiers (`ppcac_conflitos_pe`), public and private land tenure polygons (SIGEF Privado/Público, ITERPE, INCRA), environmental rural registrations (CAR / SICAR), judicial lawsuits (DataJud TJPE/TRF5), and social community mappings (Despejo Zero).
- **Specification**: [`docs/superpowers/specs/2026-10-02-ppcac-filter-design.md`](superpowers/specs/2026-10-02-ppcac-filter-design.md); implementation plan: [`docs/superpowers/plans/2026-10-02-ppcac-filter.md`](superpowers/plans/2026-10-02-ppcac-filter.md).
- **Model**: PostGIS table `public.ppcac_conflitos_pe` containing 80 consolidated conflict areas across Pernambuco, with native arrays for judicial lawsuits (`processos_judiciais`), MPPE inquiries (`processos_mppe`), and SEI electronic files (`processos_sei`). Updated to `GEOMETRY(Geometry, 4326)` with metadata columns `fonte_geometria`, `tipo_geometria`, `sigef_codigos`, `car_codigos`, `iterpe_nomes`, `incra_projetos`, `total_car_imoveis`. Implements multi-tier spatial resolution:
  - **Tier 1 (SIGEF Casos Analisados)**: Polygons from `sigef_casos_analisados` (e.g. *Engenho Batateiras* in Maraial).
  - **Tier 2a (SIGEF Privado)**: 23 polygons from `sigef_privado_pe` matched by IBGE code, word-boundary regex on core name, and trigram similarity $\ge 0.35$ (*Roncadorzinho*, *Fervedouro*, *Paraguassu*, *Pau Amarelo*, *Humaitá*, *Jacaré*, *Megaó de Baixo*, *Novo São Paulo*, *São Francisco*, *Vila Real*, etc.).
  - **Tier 2b (SIGEF Público)**: Polygons from `sigef_publico_pe` (e.g. *Engenho São Pedro* in Jaboatão dos Guararapes).
  - **Tier 2c (ITERPE Glebas & Territórios Quilombolas)**: State tenure polygons from `iterpe_glebas_pe` (e.g. *Comunidade Quilombola Negros de Gilú* in Itacuruba, 103,71 ha).
  - **Tier 2d (INCRA Assentamentos)**: Federal settlement project polygons from `assentamentos_incra_pe`.
  - **Tier 3 (DataJud Judicial Points)**: 32 areas with precise coordinates from judicial lawsuit dockets (`processos_conflitos_judiciais`).
  - **Tier 4 (Despejo Zero Points)**: 8 community points from `despejo_zero_pe` (resolved via normalized core name matching).
  - **Tier 5 (Municipal Centroid Fallback)**: Dropped from 28 down to 14 areas without specific cartographic mapping (`jurisdicoes_pe_municipios`).
- **CAR Cross-Referencing**: Automated spatial intersection post-process against `area_imovel_1` and `car_casos_analisados`. **41 of 80 PPCAC areas** now have directly linked CAR properties, associating **562 distinct CAR parcels** (`car_codigos`) displayed in the popup and searchable globally.
- **ETL Pipeline** ([`src/etl_ppcac.py`](../src/etl_ppcac.py)): Parses `data/raw/Planilha_da_Relacao_Conflitos_09.02.2026.xlsx`, forward-fills merged cells, rectifies shifted columns, runs multi-tier spatial resolution, and calculates spatial intersections with CAR, ITERPE, and INCRA.
- **Unified Search** ([`src/build_search_index.py`](../src/build_search_index.py)): Indexed `sigef_codigos`, `car_codigos`, `iterpe_nomes`, and `incra_projetos` in `search_index`. Searching any CAR code, SIGEF parcel, or procedure immediately surfaces the PPCAC conflict area.
- **API Endpoints** ([`src/search_api.py`](../src/search_api.py)): `GET /ppcac/areas` returns all cross-referenced metadata (`car_codigos`, `iterpe_nomes`, `incra_projetos`, `total_car_imoveis`, `geometry_json`) and updated stats (`com_poligono: 26`, `com_car: 41`).
- **Frontend & Map Interaction** ([`frontend/src/app/ppcac-filter/`](../frontend/src/app/ppcac-filter/) and [`frontend/src/app/app.ts`](../frontend/src/app/app.ts)):
  - Badges distinguishing `Polígono SIGEF`, `Polígono ITERPE`, `Polígono INCRA`, `Judicial`, `Comunidade`, `Sede Mun.`, plus CAR parcel count tags (`CAR: {n}`).
  - Auto-activation of the corresponding vector tile layers (`sigef_casos_analisados`, `sigef_privado_pe`, `sigef_publico_pe`, `iterpe_glebas_pe`, `assentamentos_incra_pe`, `processos_conflitos_judiciais`, `despejo_zero_pe`) upon selection.
  - Institutional popup dossier displaying delimitation provenance, CAR property lists, territorial overlap notices, and procedural records.

### October 2026: Saved Selections (Replaces the Rule-Based Filter Builder)
- **Why**: The rule-based builder (layer blocks, conditions, spatial crossings) did not match the intent, which was named sets of hand-picked areas. Specification: [`docs/specs/2026-10-02-saved-selections.md`](specs/2026-10-02-saved-selections.md); plan: [`docs/superpowers/plans/2026-10-02-saved-selections.md`](superpowers/plans/2026-10-02-saved-selections.md).
- **Model**: `saved_selections` and `saved_selection_members` ([`src/saved_selections.py`](../src/saved_selections.py)). A member is a locator (layer, `md5(props::text)` fingerprint, `ST_PointOnSurface` anchor, string-attribute hint, note), not a `search_index.id`, because the index is rebuilt and its ids restart. Resolution is `exact`, `approximate` (attributes changed) or `missing` (kept, flagged, skipped on export). 500 areas per set.
- **API** ([`src/selections_api.py`](../src/selections_api.py)): CRUD, idempotent add-member (the server stores what the database says the feature is), `/geometry` (full simplified boundaries for drawing), `/export/kml` (one KML or a ZIP per area; notes become an *Observação* block), `/backup` import/export.
- **Frontend**: `SelectionService` (shared active set), the Filtros panel, a **+** button on each Sobreposições row and in the popup, and **Isolar no mapa** (`SelectionIsolationService`: layer snapshot and exact restore, overlay drawn with full boundaries and still clickable).
- **Removed**: the builder UI, `/filters`, the SQL compiler and catalog, `POST /export/kml`, `saved_filters.py` and their tests. The `saved_filters` table is left in place, unused. The CAR sub-layers (indexed but not searchable, with their own popup) from the previous iteration are kept.
- **Pipeline**: step `8b` (`--step saved_selections`) creates the tables if missing.

### October 2026: Saved Filters Completion (CAR Sub-Layers, Backup, Filter Management) — builder superseded by Saved Selections above
- **CAR Sub-Layers in the Index**: `apps_1` (273,296 rows), `reserva_legal_1` and `vegetacao_nativa_1` (138,475 rows) are added to `SEARCH_SOURCES` with `"searchable": False`. `search_index` grows from 624,050 to 1,275,209 rows and from 1,017 MB to 2,560 MB; a full rebuild takes about 4.5 minutes. `/search` skips non-searchable layers unless they are named in `?layers=`, so typing a CAR code still returns only the property. They are filterable and exportable (example: APPs and Reserva Legal intersecting INCRA settlements = 28,648 features).
- **Clicking the CAR Sub-Layers**: `apps_1_fill`, `reserva_legal_1_fill` and `vegetacao_nativa_1_fill` joined `PRIORITY_ORDER` ahead of `area_imovel_1_fill`, with a shared `renderCarSubLayerPopup` showing the theme, parent CAR code, area and status.
- **Filter Management UI**: Loading a saved filter left its name and blocks in place with no way to clear them, so a new filter could not be created (saving under the loaded name returned 409). The panel now has **Novo filtro**, **Atualizar** (PUT) versus **Salvar como novo**, and highlights the loaded filter.
- **Backup**: **Exportar JSON** / **Importar JSON** in the panel (`/filters/import`, upsert by name).
- **Pipeline**: `run_all_pipelines.py` gains step `8b. Saved Filters Table` (`--step saved_filters`), which only creates the table if missing.
- **Docs**: `README.md` documents saved filters and the `down -v` hazard; `AGENTS.md` lists the new modules and the user-data rule.

### October 2026: Highlight Geometry Fix (Clipped Selections)
- **Root Cause**: Selecting, hover-previewing and hiding a feature used the geometry from `queryRenderedFeatures`, which at a single point returns only the fragment in the tile under the cursor. The earlier "merge tile fragments" step therefore never had more than one fragment, and any parcel crossing a tile seam was highlighted as a clipped shape with straight edges. Measured on CAR parcel `PE-2600104-79F46616…`: the highlight covered x −37.6536…−37.6388, y −7.8576…−7.8413, against a real extent of −37.6621…−37.6252, −7.8576…−7.8273.
- **Fix**: New `POST /feature/geometry` ([`src/export_api.py`](../src/export_api.py)) returns the whole boundary as GeoJSON, simplified to about half a pixel at the caller's zoom. It shares the point-in-polygon locator with the single-feature KML export, now factored into `_locate_feature`. The frontend (`loadFullGeometries` in `app.ts`) replaces each overlap-stack entry's fragment with this geometry as soon as it arrives, then redraws the active highlight; the fragment is kept as a fallback if the request fails. Point features are skipped. After the change the same parcel's highlight matches the database extent exactly.
- **Deployment**: The `search` container has no auto-reload; run `docker compose restart search` to pick up the new endpoint.

### October 2026: Floating Panel Layout (Alignment, Spacing, Mobile)
- **Misalignment Root Cause**: The `top/right: 20px` offsets of the right-hand `.legend-panel` / `.panel-toggle-badge` in `app.css` also applied to the left-column panels (`position: relative`), shifting the DataJud legend, SIGEF history and Filtros toggle 20px left of the search bar. Previously fixed only inside the overlap panel; now reset once for the whole `.left-panels-stack`.
- **Overflow Root Cause**: The stack capped its height but nothing scrolled, so with many panels open the column overlapped itself and ran under the bottom-left basemap switcher. The search bar stays pinned and the other panels live in a new `.left-panels-scroll` container that scrolls, keeps a constant 12px gap, ends above the basemap switcher, and skips panels that render nothing (previously each empty host still added a 12px flex gap).
- **Width Alignment**: Left-column components use `width: 100%` of the stack (320px on desktop), so the search bar and every panel share one width and edge.
- **Mobile (≤ 640px)**: The stack spans the viewport with 12px margins. The Camadas panel becomes a full-width sheet starting closed, and its toggle moves to the bottom row beside the basemap switcher instead of covering the search bar.
- **Filter Builder**: Inputs use `box-sizing: border-box` so "Busca livre" no longer overflows the panel and triggers a horizontal scrollbar.

### October 2026: Per-Feature Visibility Control & Layer Draw-Order Reordering
- **Specification ([`docs/specs/2026-10-01-feature-visibility-and-saved-filters.md`](specs/2026-10-01-feature-visibility-and-saved-filters.md))**: First entry in a new `docs/specs/` folder. Covers this feature and the planned Saved Filters / bulk KML export work, including the measured data constraints both rest on.
- **Layer Registry Extraction ([`frontend/src/app/layers.config.ts`](../frontend/src/app/layers.config.ts))**: The 43-entry `LayerConfig` array and `PRIORITY_ORDER` moved out of `app.ts` into a dedicated module (−469 lines; the file ends at 2,641 after this feature's own additions), alongside `RENDERED_SUFFIXES` and `renderedLayerIds()`, which centralises the `_fill`/`_line`/`_circle`/`_symbol` suffix convention. Each layer now declares `keyColumns` and `keyStability`.
- **Feature Identity**: Martin publishes no MVT feature ids (verified: 3,892 features in an `area_imovel_1` tile, none carrying one), so identity is derived from attributes. Every key was measured against the live database: 38 of the 40 clickable layers are 1:1, and two are not — `area_imovel_1` (`cod_imovel`, 433,069 distinct of 433,105) and `processos_minerarios_pe` (`id`, 5,224 of 5,235). Several layers need composite keys (`areas_de_quilombolas_pe` is `nr_process + nm_comunid`; `cd_quilomb` is 3 distinct across 10 rows and `cd_sipra` is entirely NULL). Key columns are restricted to text and integer types, because `String()` and MapLibre `to-string` agree on those but diverge on floats.
- **Visibility Service ([`frontend/src/app/services/feature-visibility.service.ts`](../frontend/src/app/services/feature-visibility.service.ts))**: Owns the hidden set, draw order and all filter composition. `buildLayerFilter()` ANDs every active filter source for a layer, fixing a real collision: `applySigefFilter` and any second filter on `sigef_casos_analisados` previously both called `setFilter` directly, so whichever ran last silently wiped the other. `setFilter` now has exactly one call site in the codebase.
- **Overlap Stack Panel ([`frontend/src/app/overlap-stack-panel/`](../frontend/src/app/overlap-stack-panel/))**: The click dispatcher already computed the full stack of features under the cursor and discarded all but the top one; it is now published to a left-hand panel. Rows are ordered by draw order (topmost first), not `PRIORITY_ORDER`, because the panel explains visual occlusion while `PRIORITY_ORDER` is deliberately the inverse. Hiding is a toggle the row survives, and a second section lists everything hidden with per-item, per-layer and global restore.
- **Hover Preview**: Pointing at any row outlines that feature on the map through a dedicated `hover-feature-source` (amber), separate from the blue selection highlight so hovering never clobbers the click selection. Hidden rows keep the geometry captured at hide time, so an area can be previewed before being restored. Tile fragments are merged: `queryRenderedFeatures` clips geometry per tile, and the parcel used for testing splits into 2 fragments at z12, 6 at z14 and 15 at z15 — highlighting only the first drew a clipped sliver.
- **Select vs. Inspect**: Left click now fills the panel without opening the detail popup, and right click opens the popup; both run the same hit-test. The 310 px popup card was covering the overlaps being investigated.
- **Layer Draw Order**: A `drawOrder` list decoupled from the legend's thematic ordering, reconciled by a single idempotent `applyLayerOrder()` that walks bottom-to-top against a fixed top anchor. The anchor is the lowest overlay layer (`hover-feature-fill`), since anchoring higher would push reordered data layers over the highlight layers. `PRIORITY_ORDER` stays frozen: coupling depth to click precedence would make a backmost point layer unclickable.
- **Bug Fixes**: The left panel stack's fixed-width children were being clipped horizontally, because `.legend-panel` sets `top`/`right` for the right-hand panel and the left-panel variant overrode `position` without resetting those offsets — on a relatively-positioned element `right: 20px` shifts the box 20px left.
- **Docs**: `README.md` gains a "Map Interaction: Select vs. Inspect" section.

### October 2026: Unified Search Bar (All Layers, All Identifying Fields)
- **Search Index ([`src/build_search_index.py`](../src/build_search_index.py))**: A declarative `SEARCH_SOURCES` list maps each of the 40 displayed layers to label, code, free-text and municipality columns. Missing tables and columns are skipped through `information_schema`. One `INSERT … SELECT` per layer fills `public.search_index` (624,050 rows) with accent/case-folded `search_text`, punctuation-stripped `codes` (so CNJ numbers, CPF/CNPJ and CAR codes match with or without dots and dashes), the feature's full attributes (`props jsonb`) and its geometry. Indexes: GIN trigram on `search_text` and `codes`. Enables `pg_trgm` and `unaccent`. Registered as step `search_index` in [`src/run_all_pipelines.py`](../src/run_all_pipelines.py), after all ingestion steps.
- **Search API ([`src/search_api.py`](../src/search_api.py))**: FastAPI `GET /search?q=&limit=&layers=` on port 7055, with CORS for the dev server. Every query token must match `search_text`, or the whole query must match an identifier in `codes`. Ranking: exact code, code prefix, exact/prefix/substring title, then trigram similarity and layer order. Requires at least 3 alphanumeric characters. Each hit returns attributes, GeoJSON geometry, bbox and an on-surface anchor point. Typical latency is 5–70 ms, up to ~200 ms for very broad 3-letter queries. It runs as the `search` service in `docker-compose.yml`: the `uv` Python 3.12 image, with `src/` mounted read-only, only the API's dependencies (no geopandas), and a `uvcache` volume so restarts take about 1 s.
- **Frontend**: New standalone `app-search-bar` ([`frontend/src/app/search-bar/`](../frontend/src/app/search-bar/)) at the top of the left panel stack, so it stays visible when the layer panel is closed. It has a 300 ms debounced autocomplete, results grouped by layer with color swatches, monospace codes and municipality, and keyboard navigation (<kbd>↑</kbd>/<kbd>↓</kbd>/<kbd>Enter</kbd>/<kbd>Esc</kbd>). Pressing Enter before the debounce fires selects the top hit of the typed query, not stale results. [`SearchService`](../frontend/src/app/services/search.service.ts) uses `HttpClient`, now provided in `app.config.ts`. Selecting a result turns the layer on, zooms to the feature, highlights it, sets it as the KML export target, and opens the layer's regular popup.
- **Popup Dispatcher Refactor ([`frontend/src/app/app.ts`](../frontend/src/app/app.ts))**: The per-layer if/else popup chain moved out of the map click handler into `renderPopupForLayer`, shared by map clicks and search results. Map-click behaviour is unchanged. Only one popup stays open: a new selection closes the previous one.
- **Bug Fixes**: The selection highlight layers (`selected-feature-fill`/`-line`) were never added, because MapLibre rejects `'MultiPolygon'` as a legacy `$type` filter value; the filters now use `Polygon`/`LineString`, which match multi geometries too. `highlightFeature` now sends plain GeoJSON to the source; passing MapLibre rendered-feature instances failed with "can't serialize object of unregistered class".

### September 2026: ANEEL DUP Strip Geometry, Duplicate Acts & Overlap Sliver Filtering
- **Analysis**: 97 of the 123 DUP polygons are servitude strips buffered around line centerlines at constant widths (20 m LD, 40 m LT, 60 m for 500 kV, down to 3.5–5 m for 69 kV lines in Recife), not areas. Their hectare figures come from length (e.g. 616 km × 60 m = 3,696 ha), and they render as sub-pixel lines at state zoom. 100 of the previous 154 energy × territory rows were strip crossings.
- **DUP Enrichment (`enrich_dup()` in [`src/etl_aneel.py`](../src/etl_aneel.py))**: New `largura_m` (maximum inscribed circle, UTM 24S/25S by centroid), `forma` (`faixa`/`area`, from the object type with an elongation fallback), `extensao_km`, `grupo_geometria`, `geometria_compartilhada`, `atos_mesma_geometria` and `erro_origem`.
- **Source Errors Detected**: Two DUPs of out-of-state projects carry a copy of a PE line's polygon: REA 4797/2014 (Pecém–Cumbuco, CE → Santa Brígida VII–Garanhuns II polygon) and REA 5716/2016 (Santa Rosa–Três de Maio, RS → UFV São Pedro e Paulo I–Flores polygon). They are flagged through the curated `DUP_SOURCE_ERRORS` list and excluded from overlaps. The flag applies only while the geometry stays shared. This also explains the RS-registered DUP that appeared to intersect PE.
- **Overlap Engine ([`src/overlaps.py`](../src/overlaps.py))**: `ENERGY_FOOTPRINTS` is now a map of per-source SELECTs. DUPs enter once per `grupo_geometria` with names and acts merged, which removes 8 duplicated rows / 758 ha of double counting. New columns: `forma`, `largura_faixa_m`, `extensao_travessia_km` (overlap area / strip width), `partes`, `partes_descartadas` and `area_descartada_ha`. Intersections are split into parts: areal footprints drop parts < 0.1 ha or < 10 m wide (reservoir shoreline slivers, up to 127 per row before), strips drop only parts < 100 m². Result: 143 rows (90 strip crossings totaling 588 km, 53 areal overlaps), with 105 slivers / 2.71 ha discarded.
- **Frontend**: DUP and overlap outlines keep a minimum width at low zoom (2.4 px at z6, down to 1.2 px at z13) with the fill fading in from z9. Outlines are clickable. DUP outlines are colored by modality. Popups show strip width and length, acts sharing the same strip, crossing length for overlaps, discarded fragments and the source-error warning.
- **Docs**: [`docs/DATA_SOURCES.md` § m](DATA_SOURCES.md) gained a strips-vs-areas section, the new columns, the overlap methodology and updated results. [`docs/DATA_ANALYSIS.md`](DATA_ANALYSIS.md) statistics were updated.

### September 2026: ANEEL / SIGEL & EPE Energy Infrastructure Ingestion
- **New ETL ([`src/etl_aneel.py`](../src/etl_aneel.py))**: Fully API-driven ingestion (no manual downloads, no credentials) from three public sources: ANEEL SIGEL ArcGIS REST, the EPE WebMap ArcGIS REST, and the ANEEL CKAN open-data portal (SIGA CSV). Registered as step `aneel` in [`src/run_all_pipelines.py`](../src/run_all_pipelines.py). Supports `--offline` (replay from cache) and `--only <table…>`.
- **Extraction**: Server-side PE bounding-box queries returning GeoJSON in EPSG:4326, `OBJECTID`-ordered offset pagination, adaptive page halving on HTTP 500 (SIGEL's response to oversized pages), exponential backoff on network errors, and a one-feature page size for reservoirs (the Xingó polygon alone has ~374k vertices). Every response is cached with its layer metadata under `data/raw/aneel/`.
- **16 Tables Loaded**: `aneel_dup_pe` (123 DUPs: 95 servidões, 28 desapropriações), `aneel_eol_usinas_pe` (116), `aneel_eol_parques_pe` (71), `aneel_eol_aerogeradores_pe` (599), `aneel_eol_interferencia_pe` (64), `aneel_lt_interesse_restrito_pe` (30), `aneel_ufv_usinas_pe` (355), `aneel_ufv_parques_pe` (45), `aneel_ufv_paineis_pe` (45), `aneel_ufv_subestacoes_pe` (8), `aneel_ute_usinas_pe` (78), `aneel_hidro_aproveitamentos_pe` (27), `aneel_hidro_reservatorios_pe` (3), `epe_linhas_transmissao_pe` (133), `epe_subestacoes_pe` (45) and the non-spatial `aneel_siga_empreendimentos_pe` (274).
- **Standardization**: PE-boundary intersection filter (instead of the unreliable `UF` field), `make_valid`/`force_2d`/Multi* coercion, snake_case columns, epoch-ms dates converted to timestamps, SIGEL's literal `"<Null>"` placeholders nulled, geodesic `area_ha`/`comprimento_km`, provenance columns (`fonte_orgao`, `fonte_camada`, `fonte_url`, `data_coleta`), a normalized 6-digit `ceg_nucleo` join key across SIGEL and SIGA, and municipality attribution (`municipios_ibge`, `municipios`) from IBGE 2022 census tracts for DataJud correlation. Exact republished duplicates are dropped (3 reservoir copies).
- **Source Decisions**: Transmission lines and substations come from EPE because SIGEL's ONS layers carry only KML names and HTML popups. Duplicate SIGEL services, attribute-less layers (BDIT ADS), layers with no PE features and distribution/consumer layers are documented and skipped. Servitude areas use only the official DUP polygons; no voltage-based buffer is generated.
- **Energy × Territory Overlaps ([`src/overlaps.py`](../src/overlaps.py))**: New `calculate_energy_overlaps()` builds `aneel_sobreposicoes_territorios_pe` (154 intersections) between DUPs, wind/solar parks, solar substations and reservoirs and Indigenous Lands, quilombos, INCRA settlements, ITERPE glebas/posses and federal/state UCs, with overlap area, share of the territory and turbine count. The existing `land_overlaps` table is unchanged.
- **Frontend ([`frontend/src/app/app.ts`](../frontend/src/app/app.ts))**: `LayerConfig` gained an optional `geometry` (`fill` / `line` / `circle`) so line and point layers render without id-specific branches. Added 16 ANEEL/EPE layers (DUP shaded by modality, transmission lines weighted by voltage with planned lines lighter), click priority entries, and a single key-value popup renderer with HTML escaping, monospace legal acts/CEG codes and a source/collection-date note.
- **Documentation**: [`docs/DATA_SOURCES.md` § m](DATA_SOURCES.md) moved from roadmap to integrated sources, with endpoints, table inventory, methodology, CEG join, overlap results, skipped layers and known source errors (e.g. two `UF = 'PE'` DUPs located in Piauí). [`docs/DATA_ANALYSIS.md`](DATA_ANALYSIS.md) gained the EPE framework entry, summary rows and a statistics section. The rows previously documented for the DUP layer ("115 polígonos em PE") counted the `UF` field; the loaded count, based on spatial intersection, is 123.

### September 2026: `datajud-gui` Redesign — Offline Explorer over the Full Lawsuit Snapshot
- **Offline Data Access (API client removed)**: The desktop app no longer queries the CNJ DataJud API. It loads the complete dataset (93,680 lawsuits) from a SQLite snapshot into memory at startup (~0.2 s, ~45 MB with string interning — 2,172 distinct strings across classes, órgãos, municípios and assuntos). Removed `src/api.rs`, `reqwest` and the in-GUI TPU/limit query panel; ingestion stays in `src/etl_datajud.py`.
- **SQLite Snapshot Exporter ([`src/export_datajud_sqlite.py`](../src/export_datajud_sqlite.py))**: Dumps `public.processos_conflitos_judiciais` to `data/exports/datajud/datajud_pe.sqlite` (tables `lawsuits` + `meta`, schema version 1, atomic write). Registered as step `datajud_sqlite` in `src/run_all_pipelines.py`.
- **Snapshot Resolution & Embedding**: `--db <path>` → `DATAJUD_DB` → next to the executable → repo `data/exports/datajud/` → optional embedded copy (`cargo build --features embedded-snapshot`; `build.rs` zlib-compresses the snapshot into the binary, ~9 MB, opened via `rusqlite` `deserialize`). "Base ▸ Abrir outra base…" switches files at runtime.
- **In-Memory Query Engine (`src/data/query.rs`)**: Single-pass filtering with disjunctive facet counts (each facet counted with every other filter applied), accent-insensitive multi-token search over classe/assuntos/órgão/município/comarca, and CNJ number matching in masked or digits-only form. Recomputed only on change (150 ms search debounce): 2–16 ms per query and 11–26 ms per sort over 93k rows. Covered by unit tests plus an opt-in benchmark against the real snapshot.
- **New Layout (facets · table · detail)**:
  - Left facet panel: Tribunal, Categoria (all 7, including the previously unreachable *Outros* — 8,205 lawsuits), Grau/instância, Ano de ajuizamento (clickable per-year histogram + range + presets), Município and Classe (top 8 with "Mostrar todos" and inline search). An empty selection means "no filter"; zero-count options are dimmed; per-section "limpar".
  - Center: result count with removable filter chips and "Limpar filtros", followed by a virtualized `egui_extras` table (no pagination) with resizable, click-to-sort columns and keyboard navigation (<kbd>↑</kbd>/<kbd>↓</kbd>, <kbd>Esc</kbd>).
  - Right detail pane: key-value box, assuntos with TPU codes, "Outras instâncias do mesmo número" navigation, and actions (Copiar número, Copiar JSON, Consulta pública PJe).
  - Top bar: single search field (<kbd>Ctrl</kbd>+<kbd>F</kbd>), one "Exportar" menu (CSV/JSON of the filtered rows) and a "Base" menu (open, reload, about). Dismissible notice bar for confirmations and errors, and dedicated loading/missing/failed/no-results states.
- **Redundancy Removed**: duplicated category selectors, header count badges, the no-op "Filtrar" button, the per-row "Ver" button, pagination controls and differently styled export buttons.
- **Model Alignment**: Category labels now map exactly to the database strings (`ConflictCategory::from_db`), with short labels for compact UI; the GUI no longer re-classifies lawsuits or re-masks CNJ numbers.
- **Persistence**: Filters, sort, panel sizes and column widths persist across restarts (eframe `persistence`).

### September 2026: Roadmap Specification for ANEEL / SIGEL Energy Infrastructure & Servitude Layers
- **ANEEL Geospatial Research & Catalog Mapping**: Researched and documented the federal geospatial data infrastructure of the Agência Nacional de Energia Elétrica (ANEEL), specifically SIGEL (`https://sigel.aneel.gov.br/arcgis/rest/services`).
- **Data Sources Documentation Update ([`docs/DATA_SOURCES.md`](DATA_SOURCES.md))**:
  - Integrated layer code **`m`** (*Infraestrutura Energética & Servidões - SIGEL*) into Camada 1 (Cruzamentos Topológicos Espaciais) as high priority.
  - Specified key endpoints and layers: DUP (*Declarações de Utilidade Pública* — 115 polygons verified in Pernambuco under `DadosAbertos/DUP/MapServer/0`), Transmission Lines & Substations (ONS / `PORTAL/Transmissão/MapServer`), Wind Farm polygons & interference zones (`PORTAL/Camadas_Downloads/MapServer/7` & `PORTAL/Parques_Eólicos/MapServer/1`), and Photovoltaic Solar complexes (`PORTAL/UFV/MapServer/2`).
  - Documented specific land conflict dynamics in Pernambuco: forced administrative servitudes (*non aedificandi*), judicial expropriations (Decreto-Lei nº 3.365/1941) intersecting family agriculture and INCRA agrarian settlements, asymmetric long-term wind/solar land leases in Agreste and Sertão (Caetés, Venturosa, Pedra, Araripina, etc.), and historical hydroelectric displacements along the São Francisco basin.
  - Formulated the target PostGIS table schema (`aneel_dup_pe`, `aneel_linhas_transmissao_pe`, `aneel_geracao_poligonos_pe`, `aneel_geracao_pontos_pe`) and planned ETL pipeline (`src/etl_aneel.py`).
  - Updated multi-layer crossing architecture diagram to include ANEEL.
- **Conceptual Framework Update ([`docs/DATA_ANALYSIS.md`](DATA_ANALYSIS.md))**:
  - Added ANEEL regulatory overview and legal framework (Federal Law 9.427/1996, Decree-Law 3.365/1941, and Normative Resolution 740/2016).

### September 2026: DataJud Full Streaming Ingestion & Interleaved Round-Robin Concurrency
- **Interleaved Round-Robin Multi-Tribunal Engine**: Refactored [`src/etl_datajud.py`](../src/etl_datajud.py) to ingest lawsuits across courts in an alternating round-robin pattern (1 page TJPE $\rightarrow$ 1 page TRF5 $\rightarrow$ 1 page TJPE...). Because each court queries a separate Elasticsearch index and cluster node on Elastic Cloud, the active request time on one court (~20–30s) acts as a natural cooldown period for the other, preventing threadpool saturation (`es_rejected_execution_exception`) without requiring lengthy artificial idle sleeps.
- **Per-Attempt Round-Robin Yielding**: Decoupled HTTP retry loops from individual courts. If a court encounters a 429 (`es_rejected_execution_exception`) or 504 timeout due to peak-hour CNJ cluster load, it logs a brief warning, sets an individual cooldown timer, and **immediately yields its turn** to the alternate court. This completely eliminates previous stalls where a single failing court trapped the execution in a 20-minute synchronous retry loop.
- **Adaptive Batch Sizing**: Dynamically throttles request batch sizes from 100 down to 50 (or 25) when CNJ's Elasticsearch threadpool queue reaches full capacity (1000/1000 tasks queued). Reducing batch size relieves deserialization overhead during Elasticsearch's `fetch` phase, allowing queries to slip through congested queues. Batch sizes automatically restore to 100 after 3 consecutive successful pages.
- **Coordinated Cluster Cooldown**: When both courts are concurrently waiting out threadpool saturation spikes during national peak hours (11:30–13:30 BRT), the scheduler calculates the minimum remaining wait time across all active courts and performs a single unified pause before initiating the next round-robin cycle.
- **Deep Cursor Pagination (`search_after`)**: Paginates through Elasticsearch clusters using document cursors, eliminating artificial page limits and enabling full ingestion of ~90,000+ matching lawsuits.
- **`_source` Field Projection**: Optimized queries to fetch only the 12 essential fields needed for geolocation and categorization, slashing payload sizes by ~98% (from ~5 MB down to ~86 KB) and reducing serialization overhead on CNJ's shared clusters.
- **Resumable State Checkpoints (`datajud_checkpoints.json`)**:
  - Persists extraction cursor (`search_after`), pages completed, and record tallies to [`data/extracted/datajud_checkpoints.json`](../data/extracted/datajud_checkpoints.json) immediately upon completing each page.
  - Full support for graceful interrupts (<kbd>Ctrl</kbd> + <kbd>C</kbd>): progress is safe, and running the script resumes instantly from the exact next page.
- **Streamed Database Ingestion**:
  - Replaced in-memory accumulation with streamed batch upserts (`ON CONFLICT (id) DO UPDATE`) into `public.processos_conflitos_judiciais`, keeping memory footprint negligible regardless of dataset size.
- **Automated Territorial Enrichment**: Automatically triggers comarca jurisdiction mapping and municipal summary table refresh (`public.processos_conflitos_municipios`) upon completion or interrupt.
- **Full Ingestion Milestone (93,680 Lawsuits)**: Concluded 100% extraction of historical and active land conflict lawsuits for Pernambuco across both state and federal jurisdictions (1968–2026). Ingested **88,834 processos** from TJPE (1,036 pages) and **4,846 processos** from TRF5 (78 pages), yielding 93,680 georeferenced records (84,545 unique CNJ process numbers) with 100% valid geometries in EPSG:4326. Comarca jurisdiction mapping and municipal summaries were rebuilt across all 185 municipalities of Pernambuco. Martin vector tile catalog was refreshed.

### September 2026: DataJud Standalone Desktop GUI (`datajud-gui`)
- **Standalone Rust Desktop Application**: Built `datajud-gui` using `eframe` (0.33) and `egui`, allowing researchers and legal analysts to search, filter, preview, and export judicial lawsuits directly from the CNJ DataJud Public API without requiring the main PostgreSQL/PostGIS database or web stack.
- **Institutional UI/UX Alignment**: Designed the interface following the Land Conflict Mapping Platform's Angular frontend design language:
  - Clean light institutional theme with neutral slate cards (`#ffffff`, `#f8fafc`, `#e2e8f0`).
  - Strict color parity with the frontend legend badges (`frontend/src/app/datajud-legend/datajud-legend.component.ts`) for all 6 land conflict categories: Reintegração de Posse (`#8b5cf6`), Reforma Agrária (`#f59e0b`), Povos Indígenas & Quilombolas (`#ef4444`), Terras Devolutas (`#3b82f6`), Usucapião (`#10b981`), and Conflito Coletivo (`#ec4899`).
- **Concurrent Round-Robin Multi-Tribunal Engine**:
  - Replaced sequential court processing with concurrent interleaved execution using `std::thread::scope`. When multiple courts are selected (e.g. TJPE and TRF5), each round queries 100 records from each court in parallel, streaming balanced results across all selected courts into the UI from the very first second until the total target quota is satisfied.
- **Permanent Pernambuco Territorial Scope & Streamlined Query Panel**:
  - Replaced manual court selection (`SELEÇÃO DE TRIBUNAIS`) with a permanent territorial focus on Pernambuco: every search automatically queries both the state judiciary (**TJPE**) and the federal judiciary restricted to the Pernambuco Section (**TRF5-JFPE**, `*40583*`) concurrently in round-robin batches.
  - Simplified the left configuration panel with a clean institutional territorial badge (`ÂMBITO TERRITORIAL: Pernambuco (TJPE + TRF5-JFPE)`) and organized remaining controls into clearly numbered sections (`1. CATEGORIAS DE CONFLITO FUNDIÁRIO`, `2. FILTROS ADICIONAIS DE BUSCA (TPU)`, `3. LIMITES E EXTRAÇÃO`).
- **UI/UX Refinements & Institutional Design**:
  - Removed all decorative emojis across UI elements, status banners, and pagination controls.
  - **Symmetric Filter Button Padding (`render_dropdown_filter_button`)**: Eliminated excessive right-side empty space by calculating snug, symmetric horizontal padding (`10.0px` left, `10.0px` right) around the funnel icon and label.
  - **Dynamic Tribunal Button & Popup**:
    - Before extraction, the button cleanly displays `"Tribunal"` (no misleading `"Todos"` when zero records are loaded), and the popup explains that tribunals will appear once extraction begins.
    - Upon extraction, the loaded tribunals appear automatically in the popup and on the button (e.g. `"Tribunal: TJPE, TRF5"` or active subset).
    - Removed redundant `"Todos os Tribunais"` row from the popup list in favor of standard `"Marcar Todos"` and `"Desmarcar"` header actions.
  - **Network Error Resilience & Cancellation Suppression**:
    - Increased HTTP client timeout from 35s to 60s to accommodate complex Elasticsearch leading wildcard queries (`*40583*`) on the TRF5 DataJud cluster.
    - Added automated 1-retry with backoff for transient network glitches.
    - Strictly suppressed network error alerts (`[Erro]`) when cancellation is triggered by the user via `"Cancelar Extração"`.
  - **Centered Cancel Button (`render_cancel_button`)**: Created a dedicated cancel action with both the vector "X" icon and text mathematically centered horizontally in the middle of the button and vertically across the entire panel width.
  - **Vertical Label Centering**: Aligned `"Filtros:"` and `"Buscar:"` text labels to the exact vertical center of their respective rows using `allocate_ui_with_layout` with `Layout::left_to_right(Align::Center)`.
  - **Persistent Multi-Select Filter Popups**: Converted Tribunal and Categorias dropdowns to `egui::Popup` with `PopupCloseBehavior::CloseOnClickOutside`. Popups now stay open while toggling multiple options, closing only when clicking outside.
  - **Interactive Filter Rows (`render_filter_item`)**: The entire row area of each filter item is hoverable (slate-100 `#f1f5f9`), displays a pointing hand cursor, and can be clicked anywhere on the row to toggle. Features crisp vector checkmarks and category color dots.
  - **Vertically Centered Search Box**: Aligned text and hint text vertically to the center (`vertical_align(Align::Center)`) while preserving left alignment (`horizontal_align(Align::Min)`).
  - **Full-Row Interactive Lawsuit Table**: Made the entire row of each process in the table clickable to open the detail drawer. Added slate gray hover highlight (`#f1f5f9`), pointing hand cursor, and persistent indigo selection highlight (`#e0e7ff`).
  - **Vector Search Icon**: Implemented crisp vector search magnifying glass (`paint_search_icon`) drawn directly via egui's vector `Painter` across extraction and filter buttons.
  - Zero-warning code quality enforced via `cargo check` and `cargo clippy -- -D warnings` on both native Linux and Windows GNU cross-compilation targets.
- **Client-Side Table Pagination**:
  - Implemented pagination engine supporting page size choices (`25`, `50`, `100`, `250`, `Todos`) and smooth page navigation (`Anterior`, `Próxima`, `X de Y`). Enables 60 FPS rendering and instant responsiveness even with 10,000+ records in memory.
- **Masked CNJ Process Number Formatting**:
  - Standardized all process numbers into the official CNJ mask `NNNNNNN-DD.YYYY.J.TR.OOOO` (matching `format_cnj` in `src/etl_datajud.py`).
- **Post-Fetch Multidimensional Filtering**:
  - Dedicated post-fetch filter bar allowing researchers to filter *after* downloading all data: filter by tribunal, category chips with live count, and real-time text search across process numbers, classes, court units, and subjects.
  - Multi-court dataset accumulation: queries across multiple tribunals are merged with automatic deduplication by process number.
- **Limit Flexibility & Deep Pagination**:
  - Removed arbitrary limits: users can query specific limits (e.g. 10 to 200,000+) or check "Sem limite (baixar todos disponíveis)" using Elasticsearch `search_after` deep pagination.
- **Table Grid & Detailed Inspection**:
  - Clear columns with court badges (`render_tribunal_badge`), monospace process numbers, category pills, classes, comarcas/municipalities, filing dates, and "Ver" detail actions.
  - Detail drawer with 1-click clipboard copy for process number and full TPU subject breakdown.
- **Data Export**: Integrated native file dialogs (`rfd`) for direct export of filtered or full records to spreadsheet-ready CSV and JSON formats.
- **Cross-Compilation (Linux & Windows)**: Verified zero-warning compilation for both native Linux (`datajud-gui`) and Windows (`x86_64-pc-windows-gnu` generating `datajud-gui.exe` with `windows_subsystem = "windows"`).


- **Repository Isolation (Option B)**: Untracked all legacy extracted shapefiles and CSVs (~74 MB) from Git, isolating `data/extracted/` entirely via `.gitignore`. The remote repository is now purely source code, infrastructure configs, and documentation.
- **Automated Unpacker (`src/unpack_raw.py`)**: Built an automated unpacking engine that safely decompresses `.zip`, `.kmz`, and `.geojson` raw archives from `data/raw/` into their standardized `data/extracted/` target directories.
- **Unified Pipeline Runner (`src/run_all_pipelines.py`)**: Orchestrates all data ingestion, enrichment, and spatial processing pipelines with a single command (`uv run python -m src.run_all_pipelines`), complete with per-step timing, individual step filters (`--step`), unpack controls (`--skip-unpack`, `--force-unpack`), and Martin tile server reload.
- **Database Full Reset & End-to-End Re-import Verification**:
  - Successfully executed a full database purge (`docker compose down -v && docker compose up -d`) and ran all 6 ingestion pipelines sequentially (`src.etl`, `src.process_jurisdicoes`, `src.etl_datajud`, `src.import_sigef_historico`, `src.etl_moradia_iterpe`, `src.etl_despejo_zero`).
  - Audited all 37 database tables against a pre-reset baseline backup (`data/raw/backup_conflitos_agrarios_pre_reset.sql.gz`), achieving a 100% exact row count match across all 37 tables.
- **Bug Fixes**:
  - `src/etl_datajud.py`: Added missing `import re` required for CNJ process number masking.
  - `src/import_sigef_historico.py`: Rectified `sigef_privado_pe` geometry query, corrected KML filename reference (`Engenho_Batateiras_AV-23-73_2021_04_977ha.kml`), and integrated automated creation of `public.car_casos_analisados` (7 Batateiras smallholder parcels).
- **Documentation**: Updated `README.md` with the unified runner command, complete pipeline execution sequence, full re-import commands, and all 37 ingested datasets.

### September 2026: Campanha Nacional Despejo Zero Integration (Community Eviction Risks)
- **Direct API Extraction & ETL**: Developed `src/etl_despejo_zero.py` extracting directly from the official Despejo Zero REST API (`mapa.despejozero.org.br/wp-json/conflitosurbanos/v1/busca`).
- **Territorial Filtering & Spatial Georeferencing**: Filtered national conflict dataset to Pernambuco using official IBGE boundary polygon (`src/pe_boundary.geojson`) and territorial taxonomies. Processed **365 active georeferenced community conflicts** in Pernambuco, covering **43,585 threatened families** and **8,397 evicted families** (55,382 total impacted families).
- **Deterministic Micro-Jittering**: Applied deterministic spatial micro-jittering for coincident municipal coordinates, ensuring that multiple community conflicts in the same municipality (e.g. 93 in Recife, 30 in Jaboatão dos Guararapes, 28 in Olinda, 18 in Goiana, 15 in Cabo de Santo Agostinho) remain individually visible and clickable.
- **PostGIS Layer & GIST Index**: Created table `public.despejo_zero_pe` (EPSG:4326 Point) with spatial GIST and municipal B-tree indexes, alongside clean GeoJSON export in `data/extracted/despejo_zero_pe/despejo_zero_pe.geojson`.
- **Vector Tile Server (Martin)**: Published `public.despejo_zero_pe` automatically via Martin vector tile server (`http://localhost:3000/despejo_zero_pe`).
- **Frontend Map Layer & Institutional Popups**:
  - Added `despejo_zero_pe` circle layer in `frontend/src/app/app.ts` with status-based dynamic color markers (Crimson `#991b1b` for total eviction executed, Red `#dc2626` for active threat, Orange `#ea580c` for partial removal, Amber `#f59e0b` for temporary stay, Emerald `#10b981` for permanent suspension/resolution).
  - Implemented interactive popup cards displaying community title, municipality, total families impacted breakdown, conflict status, primary cause (Reintegração de Posse, Obras Públicas, Área de Risco), promoter agent, legal defense assistance, full case narrative, and direct link to the Despejo Zero platform.
- **Documentation**: Updated `docs/DATA_SOURCES.md`, `docs/DATA_ANALYSIS.md`, and `docs/PHASE_1_DATA_DOWNLOADS.md`.

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
- **Documentation**: Updated `docs/DATA_ANALYSIS.md` with the ICMBio legal framework (Law 9.985/2000 SNUC, Decree 6.514/2008) and comprehensive metadata attribute statistics.

### August 2026: DataJud Judicial Conflicts Integration (TJPE & TRF5)
- **DataJud CNJ API Integration**: Developed `src/etl_datajud.py` to connect directly to the official Conselho Nacional de Justiça (CNJ) DataJud Elasticsearch REST API for both the state court of Pernambuco (`api_publica_tjpe`) and the 5th regional federal court (`api_publica_trf5`).
- **Conflict Taxonomy Classification**: Mapped and categorized judicial cases into 6 major conflict categories based on CNJ Tabelas Processuais Unificadas (TPU) subjects and classes:
  1. *Reintegração e Conflito de Posse* (TPU 10100, 10434, 10444, 10445, 10446, 7640, 3425; Classe 1707, 1709).
  2. *Reforma Agrária & Desapropriação* (TPU 10124, 11873, 5995, 10185; Classe 91, 90).
  3. *Povos Indígenas & Territórios Quilombolas* (TPU 12031, 10104, 15114, 3647).
  4. *Terras Devolutas & Ações Discriminatórias* (TPU 10094, 10451, 10453, 10105; Classe 96, 34).
  5. *Usucapião e Regularização de Posse* (TPU 10500 - Lei 6.969/81, 10457, 10460, 10458, 10459; Classe 49).
  6. *Conflito Coletivo Rural & Agrário* (TPU 11412, 11413, 9985).
- **PostGIS Geolocation & Jitter**: Automated geocoding using 185 Pernambuco IBGE municipal centroids (calculated dynamically from SIGEF parcels) and federal sub-section court jurisdictions (`40583XX`). Applied deterministic micro-jittering per lawsuit ID so multiple lawsuits within the same comarca do not stack invisibly on a single point.
- **PostGIS Storage**: Created `public.processos_conflitos_judiciais` (with spatial GIST and B-Tree indexes) and aggregated summary table `public.processos_conflitos_municipios`.
- **Frontend Map Layer & Interactive Popups**: Added `processos_conflitos_judiciais` layer in `frontend/src/app/app.ts` with category-driven dynamic color styling, custom size interpolation, and rich inspection popup cards featuring CNJ lawsuit numbers, court/comarca details, procedural classes, TPU subjects, filing dates, last movements, and 1-click consultation links to TJPE / TRF5 PJe portals.
- **Documentation**: Updated `README.md` and `docs/DATA_ANALYSIS.md` with system architecture, legal basis (CNJ Res. 510/2023), and statistical counts.

### August 2026: DataJud Legend Component (Interactive Categories & Knowings Panel)
- **Component Architecture**: Built `DatajudLegendComponent` (`frontend/src/app/datajud-legend/`) as an Angular 20 Standalone Component.
- **Left-Side Positioning & Glassmorphism**: Placed on the upper left (`left: 20px; top: 20px`) with blur backdrop filtering, smooth slide transitions, and a minimized floating pill badge.
- **Dynamic Layer Visibility Link**: Component automatically displays when the `processos_conflitos_judiciais` layer is enabled and disappears when disabled.
- **Taxonomy & Legal Concepts ("Knowings")**: Outlines all 6 judicial conflict categories (Reintegração de Posse, Reforma Agrária, Povos Indígenas/Quilombolas, Terras Devolutas, Usucapião Rural, Conflito Coletivo, and Outros) with matching color swatches, statutory foundations (CPC/2015, Law 8.629/93, Law 6.969/81, Law 6.383/76, CNJ Res. 510/2023), and TPU procedural class codes.

### August 2026: ICMBio Pernambuco Territorial Filtering
- **Pernambuco Spatial Boundary Reference**: Bundled official IBGE Pernambuco state boundary (`src/pe_boundary.geojson`) covering mainland Pernambuco and the Fernando de Noronha archipelago.
- **Automated Territorial Filtering in ETL**: Updated `src/etl.py` with `filter_to_pernambuco(gdf, filename, pe_geom)` to automatically filter nationwide datasets before loading into PostgreSQL/PostGIS:
  - `limiteucsfederais_a`: Filtered from 347 nationwide UCs to **10 Conservation Units** intersecting Pernambuco.
  - `embargos_icmbio`: Filtered from 14,375 nationwide polygons to **246 embargo areas** inside Pernambuco.
  - `autos_infracao_icmbio`: Filtered from 41,728 nationwide points to **861 infraction notices** inside Pernambuco (discarding out-of-state points and administrative headquarters noise).
- **Overlaps Recalculation**: Recomputed `public.land_overlaps` and `public.land_overlaps_points` ensuring all conflict polygons and center pins (792 conflict zones) are clean, fast, and strictly within Pernambuco.

### August 2026: Basemap Label Z-Index & Highlighting Optimization
- **MapLibre GL Layer Ordering**: Dynamically resolved the first symbol/label layer from the Carto Positron basemap style (`watername_*`, `place_*`, `roadname_*`, `poi_*`).
- **Label Preservation Above Data**: Added all custom polygons (CAR, SIGEF, SNCI, TIs, Quilombolas, ICMBio UCs, Embargoes, Overlaps) and point circles (`autos_infracao_icmbio`, `processos_conflitos_judiciais`) before the basemap's first label layer (`firstLabelId`).
- **City & Road Name Visibility & Highlighting**: Enhanced all `place_*` layers with high-contrast text color (`#0f172a`), solid white halos (`#ffffff`), increased halo width (`2.5px`), and halo blur (`0.5px`). This ensures that municipal city names (e.g. Palmares, Recife, Caruaru, Barreiras, Gameleira, etc.) stand out prominently and legibly directly over dense clusters of DataJud points and environmental layers.

### September 2026: Centralized Data Sources & Future Ingestion Roadmap Documentation
- **Centralized Inventory (`docs/DATA_SOURCES.md`)**: Created comprehensive documentation categorizing data sources into Spatial Topological Crossings (Layer 1) and Socio-Legal Crossings (Layer 2).
- **Imported vs. Roadmap Breakdown**: Cataloged currently ingested datasets (SIGEF, CAR, FUNAI TIs, Quilombolas, ICMBio UCs/Embargoes/Autos, and DataJud CNJ) alongside technical ingestion blueprints, access prerequisites, and integration requirements for future datasets (MapBiomas, SIPRA INCRA, Moradia Legal TJPE, Acervo Fundiário ITERPE, DespejoZero, and ONR).
- **Multi-layer Topological Architecture**: Documented database multi-layer intersection architecture (ST_Intersects / ST_Intersection) and socio-legal attribution flows.

### September 2026: MapBiomas Ingestion & Interactive Inspection Layers
- **Dual Layer ETL Ingestion (`src/etl.py`)**: Integrated official MapBiomas September 2026 releases:
  - `alerts_with_intersections`: 12,395 validated deforestation and vegetation suppression alerts in Pernambuco (2019–2026), tracking pressure drivers (agriculture, urban expansion, renewable energy, mining), affected areas, biomes, and detection timelines.
  - `car_with_alerts_and_intersections`: 28,473 SICAR property boundaries with overlapping deforestation alerts, enabling granular property-level compliance and tenure liability audits.
- **Deforestation & Agrarian Conflict Cross-Analysis**: Cross-referenced MapBiomas deforestation polygons with traditional territories, agrarian reform settlements, conflict overlap clusters, and judicial lawsuits, identifying 133 alerts in Indigenous Lands (notably TI Xukuru), 9 in Quilombos (Conceição das Crioulas), 395 in INCRA settlements, and 371 directly inside active conflict zones (`land_overlaps`).

### September 2026: Judicial Territorial Jurisdictions & Comarcas/Termos Parsing (TJPE & JFPE)
- **DOCX Extraction & IBGE Normalization (`src/process_jurisdicoes.py`)**: Extracted and normalized territorial jurisdictions from raw official court documents in `data/raw/`:
  - `TJPE (Justiça Estadual) - Comarcas e municípios abrangidos.docx`: Parsed 136 state comarcas covering all 185 Pernambuco municipalities. Resolved 47 comarcas with multi-municipal jurisdiction (50 daughter municipalities / termos judiciários without their own comarca, e.g. Iguaracy -> Afogados da Ingazeira, Dormentes -> Afrânio, Casinhas -> Surubim). Handled cell XML runs, line breaks (`w:br`), and orthographic variations.
  - `JFPE (Justiça Federal) - Seções judiciárias e municípios abrangidos.docx`: Parsed 12 Federal Subseções (Recife Sede, Arcoverde, Cabo de Santo Agostinho, Caruaru, Garanhuns, Goiana, Jaboatão, Ouricuri, Palmares, Petrolina, Salgueiro, Serra Talhada) covering all 185 municipalities. Mapped competent federal varas (`1ª` to `38ª`). Protected compound names ("Abreu e Lima") during tokenization.
- **CSV & PostGIS Ingestion**:
  - Exported structured CSVs into `data/extracted/jurisdicoes/` (`tjpe_comarcas_municipios.csv`, `jfpe_subsecoes_municipios.csv`, and `jurisdicoes_pe_completo.csv`).
  - Created PostGIS spatial tables: `public.jurisdicao_tjpe`, `public.jurisdicao_jfpe`, and `public.jurisdicoes_pe_municipios` (with spatial GIST indexes and IBGE municipal centroids).
- **DataJud Conflict Enrichment (`src/enrich_judicial_data.py` & `src/etl_datajud.py`)**:
  - Enriched `public.processos_conflitos_judiciais` with `comarca_sede_nome`, `comarca_sede_ibge`, `municipios_abrangidos`, `total_municipios_abrangidos`, `tem_municipios_filhos`, and `tipo_jurisdicao`.
  - Rebuilt `public.processos_conflitos_municipios` to comprehensively cover all 185 municipalities of Pernambuco, properly attributing judicial dispute volumes to both comarca seats and child terms (`termos judiciários`).
- **Frontend Map Popups**:
  - Updated MapLibre interactive popups in `frontend/src/app/app.ts` to display comarca headquarters, territorial jurisdiction badges, and explicit lists of covered municipalities without their own comarca.

### September 2026: UI/UX Minimalist Redesign of Popups & Cards
- **Anti-AI Slop Cleanup**: Eliminated emojis, neon colored glow shadows, and saturated background badges across all interactive map popups (DataJud, ICMBio UCs, Embargoes, Autos de Infração, MapBiomas Alertas/CAR, and Land Overlaps).
- **Removal of Colored Left Stripes**: Replaced colored vertical border stripes on mini cards with neutral, structured `.popup-detail-box` containers styled with subtle borders (`1px solid #e2e8f0`) and clean background shading (`#f8fafc`).
- **Typography & Institutional Design**: Standardized card hierarchy with dark neutral titles (`#0f172a`), subtle metadata badges (`.popup-badge`), monospace codes (`.popup-value-code`), clean key-value pairs, and neutral institutional action buttons (`.popup-btn`).
- **DataJud Legend Component**: Replaced floating button emoji with a minimalist scales SVG icon.

### September 2026: CAR OCR Extraction & Batateiras Tenure Overlap Analysis
- **OCR Pipeline & Code Recovery**: Executed automated Optical Character Recognition using `RapidOCR` across 8 raw PDF documents in `data/raw/` (Maraial/PE). Successfully extracted all CAR registration numbers (`Registro no CAR`), protocol numbers, declarant names/CPFs, and declared areas.
- **Database Verification (`area_imovel_1`)**: Verified a 100% match in the PostGIS database. All 7 CAR rural declarations (Odílio, Francisco Zeferino, Joselito, José Manoel, Kleiton, Severino Wanderley, and Edvania Cordeiro) are officially stored and active (`AT` - Aguardando análise).
- **Spatial Overlap on Certified Land**: Spatially intersected the 7 CAR parcels against `sigef_brasil_pe`, discovering that 99.86% of their collective perimeter (144.41 ha) lies directly within the certified macro-property `FAZENDA 2 IRMÃOS` (SIGEF `9510994953100`, 978.93 ha, Matrícula 73 de Maraial).
- **Dedicated PostGIS Table & Tile Service**: Created `public.car_casos_analisados` with spatial GIST index, storing geometry and consolidated PDF OCR metadata, served as vector tiles via Martin (`http://localhost:3000/car_casos_analisados`).
- **Frontend Layer Filter & Interactive Popups**: Added a clean layer filter in `frontend/src/app/app.ts` (`CAR - Casos Analisados (Batateiras)`) with auto-pan/flyTo capability and focus button (`.layer-focus-btn`). Implemented enriched click popups (`setupCarPopup`) for both `car_casos_analisados` and `area_imovel_1` showing declarant names, CPFs, declared property names, protocols, SICAR status, and tenure/dispute links (SIGEF Matrícula 73 and TJPE Maraial lawsuit).

### September 2026: Interactive Inspection Popups for All SIGEF and SNCI Properties
- **PostGIS Attribute Enrichment**: Computed and enriched real-time geodesic areas (`num_area` in hectares) and normalized municipality names (`municipio_nome`) across `sigef_privado_pe` (21,187 parcels), `sigef_publico_pe` (2,826 parcels), `imovel_certificado_snci_privado_pe` (81 parcels), and `imovel_certificado_snci_publico_pe` (29 parcels).
- **Martin Vector Tile Catalog Sync**: Reloaded Martin daemon with the enhanced schema fields, delivering instant attribute availability across zoom levels.
- **Frontend Click Handlers (`app.ts`)**:
  - `setupSigefPopup`: Enabled interactive popups on `sigef_privado_pe` and `sigef_publico_pe`. Displays property name, INCRA/SIGEF code, certified area (ha), municipality name, cartorial registry (`Matrícula RGI` and date), approval/submission dates, technical responsibility (RT/ART), direct 1-click consultation link to the official SIGEF INCRA parcel portal (`sigef.incra.gov.br/consultar/parcela/<UUID>`), and automated cross-conflict detection (highlighting the Batateiras tenure dispute on `FAZENDA 2 IRMÃOS - Matrícula 73`).
  - `setupSnciPopup`: Enabled interactive popups on `imovel_certificado_snci_privado_pe` and `imovel_certificado_snci_publico_pe`. Displays property name, SNCI code, certified area, INCRA Regional Superintendency (SR-03 Petrolina / SR-29 Recife), certification number (`num_certif`), administrative process number, and date of certification.

### September 2026: SIGEF Historical Evolution & Georeferencing Retifications (Batateiras)
- **KML Ingestion Pipeline (`src/import_sigef_historico.py`)**: Parsed 3 historical georeferencing boundary versions of Engenho Batateiras (Matrícula 73 - CRI Maraial) from `data/raw/`:
  - `AV-17-73 (08/07/2020)`: 917.81 ha (12,751.03 m perimeter), SIMARCO - Administração e Participação Ltda. (original certification).
  - `AV-19-73 (08/09/2020)`: 940.45 ha (+22.64 ha expansion, 13,302.54 m perimeter), IC Consultoria e Empreendimentos Imobiliários Ltda.
  - `AV-23-73 (04/02/2021)`: 977.78 ha (+37.33 ha expansion / +59.97 ha accumulated vs origin, 13,956.20 m perimeter), IR Agropecuária Fazenda 2 Irmãos Ltda.
  - Connected with current active registered SIGEF parcel (19/05/2021 - 14/06/2021) with 978.93 ha (total expansion of +61.13 ha), Parcela UUID `21971a92-35e1-4f18-bda1-85bd31ccb13b`, RT CCWB / ART PE20210624725-PE.
- **Dedicated PostGIS Table & Spatial Index**: Created `public.sigef_casos_analisados` with spatial GIST index and metadata on chronological order, variation descriptions, area, perimeters, cartorial registrations, and tenure overlaps.
- **Martin Vector Tile Layer**: Served through Martin as `http://localhost:3000/sigef_casos_analisados`.
- **Frontend Layer Filter & Interactive Popups**: Added `SIGEF - Casos Analisados (Batateiras)` layer filter in `frontend/src/app/app.ts` and `app.html` with focus button (`.layer-focus-btn`), data-driven perimeter border coloring (`#3b82f6` for AV-17, `#f59e0b` for AV-19, `#ef4444` for AV-23, and `#8b5cf6` for SIGEF Atual), and interactive chronological comparison popups (`renderSigefHistoricoPopup`) highlighting territorial expansion and overlap onto family farming smallholdings.

### September 2026: Interactive SIGEF Historical Phases Filter Panel (Left Side Minimalist Redesign)
- **Component Architecture**: Developed `SigefBatateirasFilterComponent` (`frontend/src/app/sigef-batateiras-filter/`) as an Angular 20 Standalone Component matching the DataJud glassmorphism aesthetic (`width: 320px`).
- **Left-Side Vertical Stack**: Integrated inside `.left-panels-stack` in `frontend/src/app/app.html` and `app.css` to cleanly host and stack both `app-datajud-legend` and `app-sigef-batateiras-filter` without collisions.
- **Minimalist UX Refinement**: Streamlined to mirror DataJud's visual clarity:
  - Header: *Histórico SIGEF - Fazenda 2 Irmãos*
  - List items: Checkbox + Color Indicator + Phase Code (`AV-17-73`, `AV-19-73`, `AV-23-73`, `SIGEF Atual`) + Date (`08/07/2020`, `08/09/2020`, `04/02/2021`, `14/06/2021`).
  - Removed extraneous textual noise from the left panel.
  - Maintained data precision regarding family farming possession disputes and Maraial lawsuit nº 0000263-83.2026.8.17.2940.
- **MapLibre GL Dynamic Filtering**: Applies real-time MapLibre filter expressions (`setFilter`) across both fill and line layers (`sigef_casos_analisados_fill` and `sigef_casos_analisados_line`) based on selected checkboxes.

### September 2026: Phase 1 Data Sources Catalog & Direct Download Pipeline
- **Direct Download Inventory (`docs/PHASE_1_DATA_DOWNLOADS.md`)**: Cataloged raw, uncut, verified URLs, WFS GeoJSON endpoints, and direct download links for immediate Phase 1 spatial layers:
  - **INCRA SIPRA Assentamentos**: Direct WFS GeoJSON endpoint returning 567 official agrarian reform settlements in Pernambuco (`CMR-PUBLICO:lim_assentamento_rural_a`).
  - **CPRH / CNUC Unidades de Conservação Estaduais**: Direct WFS GeoJSON endpoint returning 60 state conservation units in Pernambuco (`CMR-PUBLICO:lim_cnuc_2024_02_estadual_a`) and direct MMA CKAN shapefile zip (`shp_cnuc_2025_08.zip`).
  - **ANM SIGMINE Processos Minerários**: Daily updated direct shapefile zip download for Pernambuco (`https://dadosabertos.anm.gov.br/SIGMINE/PROCESSOS_MINERARIOS/PE.zip`).
  - **IBGE Favelas e Comunidades Urbanas (Censo 2022)**: Direct shapefile zip download covering intramunicipal census sectors for Pernambuco (`PE_setores_CD2022.zip`) with `CD_AGLOM` and `NM_AGLOM` classification.
  - **Campanha Despejo Zero**: Portal and open datasets links for grassroots monitoring of eviction threats.

### September 2026: CNJ Standard Punctuation Mask & 1-Click Copy in Map Popups
- **CNJ Mask Standardization (`NNNNNNN-DD.YYYY.J.TR.OOOO`)**:
  - Normalized all 2,000 judicial lawsuit records in `public.processos_conflitos_judiciais` to the standard CNJ mask (Resolução CNJ nº 65/2008), solving compatibility breakage when pasting process numbers into TJPE and TRF5 PJe portal search forms.
  - Updated `src/etl_datajud.py` with `format_cnj()` to ensure all future extractions from CNJ DataJud API are formatted with standard punctuation.
- **Frontend Formatting & One-Click Copy**:
  - Enriched `frontend/src/app/app.ts` with `formatCNJ()` and event-delegated copy functionality with clipboard fallback (`fallbackCopyText`).
  - Added modern `.popup-copy-btn` with visual confirmation ("Copiado!") and `select-all` CSS behavior in `frontend/src/app/app.css`, allowing users to copy the punctuated CNJ code with a single click or mouse selection without breaking court portal queries.
  - Added copy action to Batateiras judicial dispute cards in CAR and SIGEF map popups.

### September 2026: Phase 1 Datasets Ingestion & Frontend Integration
- **ETL Multi-Format Expansion (`src/etl.py`)**:
  - Added automatic dual-format discovery for both `.shp` and `.geojson` files, automatically prioritizing GeoJSON when available to preserve complete attribute names.
  - Integrated automated `shapely.make_valid` and `shapely.force_2d` to sanitize geometries and convert 3D/measured coordinates (ANM SIGMINE) into standard 2D MultiPolygons/Polygons in EPSG:4326.
  - Added explicit spatial GIST index creation (`idx_{table_name}_geometry`) and transaction commits.
- **PostGIS Ingestion Summary**:
  - `public.assentamentos_incra_pe`: 567 official INCRA agrarian reform settlements (PA, PDS, etc.).
  - `public.ucs_estaduais_cprh_pe`: 60 state-administered conservation units (CPRH).
  - `public.processos_minerarios_pe`: 5,235 ANM active mineral concessions and research permits.
  - `public.ibge_favelas_comunidades_pe`: 2,381 census sectors classified as Favelas e Comunidades Urbanas (Censo 2022).
  - `public.pe_setores_cd2022`: 19,578 complete census sectors of Pernambuco.
- **Martin Vector Tile Server Sync**:
  - Reloaded Martin daemon with the new tables, publishing all 5 new tile services on port 3000.
- **Frontend Map & Popups (`frontend/src/app/app.ts`)**:
  - Added 4 interactive toggle layers in `LayerConfig`: INCRA Assentamentos, CPRH UCs Estaduais, ANM Processos Minerários, and IBGE Favelas e Comunidades.
  - Added rich custom popup cards (`renderAssentamentoPopup`, `renderUcsEstadualPopup`, `renderMineracaoPopup`, `renderFavelasPopup`) and integrated them into the unified priority click dispatcher.

### September 2026: Moradia Legal (TJPE) & Acervo Fundiário (ITERPE) Ingestion
- **Pipeline Implementation (`src/etl_moradia_iterpe.py`)**:
  - Built dedicated ETL pipeline to parse and ingest both Programa Moradia Legal (TJPE) and Acervo Fundiário (ITERPE).
  - Sanitized multi-format geometries (Polygons, MultiPolygons, GeometryCollections) using `shapely.make_valid`, `shapely.force_2d`, and flat MultiPolygon collection unifiers.
- **Moradia Legal (TJPE / NUREF / Corregedoria)**:
  - Extracted from official live TJPE Google GIS panel (`Moradia Legal TJPE 2025.kmz`).
  - `public.moradia_legal_pe`: 104 community & urban/rural REURB perimeters across Pernambuco.
  - `public.moradia_legal_processos_pe`: 12,965 usucapião and land regularization judicial cases geocoded with deterministic micro-jittering across 185 Pernambuco municipal centroids, with masked CNJ process codes, court details, addresses, and ZEIS flags.
- **Acervo Fundiário do ITERPE (GERAF)**:
  - Extracted from official GIS repository (`iterpegeo.org` / `iterpe.pe.gov.br`).
  - Solved source CAD mesh artifact in `gleba_saojoao_03_finalizada.kml`, isolating genuine Gleba Taquari in São João (13,470 ha).
  - `public.iterpe_glebas_pe`: 9 state macro-glebas and quilombos.
  - `public.iterpe_malha_posses_pe`: 7,549 smallholder possession parcels tracking cartorial land registry records and state allocation decrees.
- **Martin Vector Tiles & Frontend Integration**:
  - Martin tile server synchronized on port 3000 for all 4 new layers.
  - Added 4 interactive toggle layers in `frontend/src/app/app.ts` (`moradia_legal_pe`, `moradia_legal_processos_pe`, `iterpe_glebas_pe`, `iterpe_malha_posses_pe`).
  - Implemented 4 custom rich popup cards with 1-click CNJ copy actions and PJe portal links.

### September 2026: Satellite Vision & Basemap Switcher (ESRI World Imagery)
- **High-Resolution Satellite Layer**:
  - Integrated ESRI World Imagery raster tile service (`https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`) into MapLibre GL JS as a dedicated raster source (`satellite-source`) and layer (`satellite-layer`).
  - Positioned the satellite raster layer immediately below custom data layers and label symbols (`firstLabelId`), preserving the visibility of all thematic polygon layers (CAR, SIGEF, Quilombolas, Terras Indígenas, ICMBio, ITERPE, Moradia Legal) and point circles (DataJud, infractions) directly over high-resolution satellite photography.
- **Reference Overlays & High-Contrast Typography**:
  - Maintained vector city, municipal, and road labels (`place_*`, `roadname_*`) above the satellite imagery with 2.5px white halos for high contrast across diverse rural, forest, and urban terrain.
  - Added dynamic state (`satellite-boundary-state`) and municipal (`satellite-boundary-county`) reference boundary overlays using dashed white lines (`carto` source, `boundary` layer) that activate in satellite mode.
- **Compact Attribution Control ('i')**:
  - Configured MapLibre GL `AttributionControl({ compact: true })` at the bottom-right corner and enforced closed-by-default behavior through overridden `_updateCompact` lifecycle management and strict CSS rules (`:not(.maplibregl-compact-show)`). The information badge ('i') now stays neatly collapsed by default at 26x26px without displaying the expanded text banner, expanding only upon explicit user click.

### September 2026: KML Export Engine & Popup Styling
- **Dedicated KML 2.2 Serialization Service (`frontend/src/app/services/kml-export.service.ts`)**:
  - Engineered client-side zero-dependency OGC KML 2.2 XML serializer supporting Point, Polygon, MultiPolygon, LineString, and MultiLineString geometries.
  - Implemented AABBGGRR color hex translation for vector styling (fill, outline, and point placemarks).
  - Implemented **Hybrid Metadata Packaging**:
    - `<ExtendedData>` with `<Data name="...">`: Machine-readable key-value pairs formatted for GIS software attribute tables (QGIS, ArcGIS, Google Earth).
    - `<description>` with formatted HTML CDATA: Institutional metadata inspection cards (key properties, titles, badges, and attributes) optimized for Google Earth Pro and Google Earth Web balloon viewers.
  - Added hierarchical `<Folder>` organization grouping selected features by thematic layer name.
  - Integrated client-side file download streaming via `Blob` and dynamic anchor generation.
- **1-Click KML Export in Map Popups**:
  - Standardized `.popup-btn-kml` export action button across all 19 inspection popup cards (CAR, SIGEF, SNCI, Terras Indígenas, Quilombolas, ICMBio UCs, ICMBio Embargoes, DataJud Judicial Lawsuits, CPRH UCs, ANM Mining, Moradia Legal, ITERPE Glebas/Posses, Settlements, Overlaps, etc.).
  - Configured `ViewEncapsulation.None` in `frontend/src/app/app.ts` so all MapLibre dynamically injected popup DOM elements receive their styles from `app.css`.
  - Styled `.popup-btn-kml` as a full-bleed footer button filling the popup card's width edge-to-edge (`width: calc(100% + 32px)` with negative margins) and matching bottom tip anchor color, while keeping the download icon and label centered.
  - Refined `.popup-title` with `padding-right: 26px`, flex-shrink protection on `.popup-badge`, and standardized close button bounds (`24x24px`) to prevent badges from colliding with the popup close button.
  - Added dynamic single-feature highlight ring and instant KML download named with standard conventions (e.g. `SIGEF_Privado_<codigo>.kml`).
- **Area Selection Tool Deactivation**:
  - Deactivated the experimental bounding-box tool and cleaned up mouse drag listeners to prevent map pan/drag locking.
- **Batateiras Focus Decoupling**:
  - Removed automatic camera `flyTo` from `toggleLayer` for both 'CAR - Casos Analisados (Batateiras)' and 'SIGEF - Casos Analisados (Batateiras)'.
  - Camera centering/zoom now triggers strictly upon clicking the explicit "Focar" button in the layer list or the "Histórico SIGEF" filter panel header.
