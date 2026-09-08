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
- **Documentation**: Updated [`docs/DATA_ANALYSIS.md`](file:///home/raylandsoncesario/github/conflict-solver/docs/DATA_ANALYSIS.md) with the ICMBio legal framework (Law 9.985/2000 SNUC, Decree 6.514/2008) and comprehensive metadata attribute statistics.

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
- **Left-Side Positioning & Glassmorphism**: Placed on the upper left (`left: 20px; top: 20px`) with blur backdrop filtering, smooth slide transitions, and a minimized floating pill badge (`⚖️ Legenda DataJud`).
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
- **Anti-AI Slop Cleanup**: Eliminated emojis (`⚖️`, `🌲`, `🚫`, `⚡`, `⚠️`, `🌾`, etc.), neon colored glow shadows (`box-shadow` glows), and saturated background badges across all interactive map popups (DataJud, ICMBio UCs, Embargoes, Autos de Infração, MapBiomas Alertas/CAR, and Land Overlaps).
- **Removal of Colored Left Stripes**: Replaced colored vertical border stripes (`border-left: 3px solid ...`) on mini cards with neutral, structured `.popup-detail-box` containers styled with subtle borders (`1px solid #e2e8f0`) and clean background shading (`#f8fafc`).
- **Typography & Institutional Design**: Standardized card hierarchy with dark neutral titles (`#0f172a`), subtle metadata badges (`.popup-badge`), monospace codes (`.popup-value-code`), clean key-value pairs, and neutral institutional action buttons (`.popup-btn`).
- **DataJud Legend Component**: Replaced floating button emoji with a minimalist scales SVG icon.








