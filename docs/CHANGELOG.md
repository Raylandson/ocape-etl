# Project Changelog & Architectural History

This document chronicles the architectural evolutions, dataset ingestions, and major engineering milestones of the Land Conflict Mapping Platform.

---

## Chronological Change Log

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
