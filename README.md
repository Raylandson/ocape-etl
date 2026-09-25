# Land Conflict Mapping Platform (Pernambuco, Brazil)

A spatial data platform for mapping, visualizing, and analyzing agrarian land conflicts in the State of Pernambuco, Brazil.

## Project Overview

The objective of this platform is to identify geographical overlaps (*overlappings*) between private properties (sourced from SIGEF and SNCI/CAR) and traditional lands (Indigenous Territories, Quilombola Communities) or Agrarian Reform Settlements. By intersecting these spatial datasets, the platform helps identify potential conflict areas and land tenure irregularities.

### Architecture
- **Database**: PostgreSQL with PostGIS extension (for spatial queries and indexing).
- **ETL**: Python with GeoPandas, SQLAlchemy, GeoAlchemy2, and Shapely (with automatic coordinate-axis rectification).
- **Vector Tile Server**: Martin (Rust-based MVT server running via Docker on port 3000).
- **Front-end**: Angular 20 + MapLibre GL JS (interactive map running on port 4200).

---

## Directory Structure

```
conflict-solver/
├── docker-compose.yml       # PostgreSQL 17 + PostGIS 3.5 + Martin Tile Server containers
├── pyproject.toml           # Project dependencies managed by uv
├── README.md                # Project documentation (this file)
├── AGENTS.md                # AI Agent guidelines and rules
├── docs/
│   ├── CHANGELOG.md         # Project change log and architectural evolution
│   ├── DATA_ANALYSIS.md     # Comprehensive Data Systems & Metadata Analysis
│   ├── DATA_SOURCES.md      # Ecosystem Inventory: Current Imported vs Future Data Sources Roadmap
│   └── PHASE_1_DATA_DOWNLOADS.md # Direct uncut URLs and batch download commands for Phase 1 data sources
├── data/
│   ├── raw/                 # Untouched ZIP backups of source data [GIT IGNORED]
│   │   ├── autos_infracao_icmbio.zip
│   │   ├── embargos_icmbio.zip
│   │   ├── limiteucsfederais_a_icmbio.zip
│   │   ├── Imóvel certificado SNCI Brasil_PE.zip
│   │   ├── Sigef Brasil_PE.zip
│   │   ├── APP_SICAR.zip
│   │   ├── AREA_IMOVEL_SICAR.zip
│   │   ├── RESERVA_LEGAL_SICAR.zip
│   │   ├── VEGETACAO_NATIVA_SICAR.zip
│   │   ├── tis_poligonais.zip
│   │   └── Áreas de Quilombolas_PE.zip
│   └── extracted/           # Extracted shapefiles used as ingestion input by the ETL
│       ├── autos_infracao_icmbio/
│       ├── embargos_icmbio/
│       ├── limiteucsfederais_a/
│       ├── areas_de_quilombolas_pe/
│       ├── imovel_certificado_snci_brasil_pe/
│       ├── sigef_brasil_pe/
│       ├── apps_sicar/
│       ├── area_imovel_sicar/
│       ├── reserva_legal_sicar/
│       ├── vegetacao_nativa_sicar/
│       └── tis_poligonais/
│   └── exports/             # Exported application data, analysis deliverables, and reports (KML, GeoJSON, CSV)
│       ├── kml/
│       └── datajud/datajud_pe.sqlite # Offline lawsuit snapshot consumed by datajud-gui
├── datajud-gui/             # Rust (egui) offline desktop explorer for the DataJud lawsuits
├── frontend/                # Angular Web Front-end with MapLibre GL JS
│   ├── src/                 # Angular source code (Map component integration)
│   ├── package.json         # Node package configuration
│   └── angular.json         # Angular build configuration
└── src/
    ├── __init__.py
    ├── config.py            # Environment configurations and path parameters
    ├── database.py          # SQLAlchemy engine setup and PostGIS extension helper
    ├── etl.py               # Main ETL pipeline with axis-swap & geometry correction
    ├── etl_datajud.py       # DataJud CNJ pipeline for TJPE and TRF5 land conflict lawsuits
    ├── export_datajud_sqlite.py # Exports the lawsuits table to the SQLite snapshot for datajud-gui
    ├── import_sigef_historico.py # Historical georeferencing evolution importer (Batateiras)
    └── overlaps.py          # Spatial conflict detection engine & DBSCAN clustering
```

---

## Prerequisites

Ensure you have the following installed on your machine:
- **Docker** and **Docker Compose**
- **uv** (Fast Python package installer and resolver by Astral)
- **Python 3.12+**
- **Rust stable** (optional, only to build the `datajud-gui` desktop explorer)

---

## Getting Started

### 1. Run the Database & Tile Server
Initialize the Docker services (PostGIS and Martin Vector Tile Server):
```bash
docker compose up -d
```
*Notes:*
- *The database runs on host port `5433` by default.*
- *The Martin Tile Server runs on host port `3000`.*
- *You can verify Martin is running by accessing its catalog at `http://localhost:3000/catalog`.*

### 2. Set Up Python Environment
Install the dependencies using `uv`:
```bash
uv sync
```
This will automatically create a virtual environment (`.venv`) and install dependencies: `geopandas`, `sqlalchemy`, `geoalchemy2`, `psycopg2-binary`, and `shapely`.

### 3. Run the Ingestion & Analysis Pipelines

You can run the entire end-to-end pipeline (unpacking, shapefile ingestion, spatial overlaps, jurisdictions, DataJud lawsuits, Batateiras historical analysis, Moradia Legal, and Despejo Zero) with **a single command**:

```bash
uv run python -m src.run_all_pipelines
```

> **Options**:
> - `--skip-unpack`: Skip uncompressing archives from `data/raw/` if already extracted.
> - `--force-unpack`: Re-extract all archives even if target directories already exist.
> - `--step <name>`: Execute only an individual step (`unpack`, `etl`, `jurisdicoes`, `datajud`, `datajud_sqlite`, `sigef_historico`, `moradia_iterpe`, `despejo_zero`).
> - `--no-restart-martin`: Skip restarting the Martin vector tile server container.

Alternatively, individual pipeline steps can be executed separately:

1. **Ingest Spatial Shapefiles & Calculate Overlaps**:
   ```bash
   uv run python -m src.etl
   ```
   > Processes all shapefiles and GeoJSONs under `data/extracted/`, cleans and rectifies geometries, filters data to the State of Pernambuco, loads them into PostGIS, and **automatically executes `src/overlaps.py`** at the end to compute spatial conflict zones (`land_overlaps`) and conflict center points (`land_overlaps_points`).

2. **Process Territorial Jurisdictions & Comarcas/Termos (TJPE & JFPE DOCX)**:
   ```bash
   uv run python -m src.process_jurisdicoes
   ```
   > Parses official TJPE and JFPE `.docx` documents from `data/raw/`, normalizes names against all 185 IBGE municipalities, exports structured CSVs to `data/extracted/jurisdicoes/`, and loads spatial tables `jurisdicao_tjpe`, `jurisdicao_jfpe`, and `jurisdicoes_pe_municipios`.

3. **Ingest Judicial Conflict Lawsuits (DataJud - CNJ TJPE & TRF5) & Enrich Jurisdictions**:
   ```bash
   uv run python -m src.etl_datajud
   ```
   > Fetches land conflict lawsuits from the official CNJ DataJud API, categorizes them according to CNJ TPUs, formats lawsuit numbers with standard CNJ punctuation (`NNNNNNN-DD.YYYY.J.TR.OOOO`), geolocates comarcas across Pernambuco, links them to territorial jurisdictions (including daughter municipalities/termos), and updates `processos_conflitos_judiciais` and `processos_conflitos_municipios`.

   Then refresh the offline snapshot used by the desktop explorer (also run automatically by the unified runner as step `datajud_sqlite`):
   ```bash
   uv run python src/export_datajud_sqlite.py
   ```
   > Writes `data/exports/datajud/datajud_pe.sqlite` (~50 MB, all 93,680 lawsuits; geometry exported as `lat`/`lon`).

4. **Import SIGEF Historical Georeferencing Retifications (Batateiras Case Analysis)**:
   ```bash
   uv run python -m src.import_sigef_historico
   ```
   > Parses official KML boundaries for Engenho Batateiras (Matrícula 73 - Maraial) across historical retifications (AV-17, AV-19, AV-23, and current SIGEF 9510994953100), populating `public.sigef_casos_analisados` with spatial GIST indexes.

5. **Ingest Moradia Legal (TJPE) & Acervo Fundiário (ITERPE)**:
   ```bash
   uv run python -m src.etl_moradia_iterpe
   ```
   > Parses official TJPE Moradia Legal KMZ/KML (104 REURB community perimeters and 12,965 usucapião judicial cases) and ITERPE GERAF KMLs (9 state macro-glebas and 7,549 smallholder possession parcels with RGI matrículas and decrees), loading `moradia_legal_pe`, `moradia_legal_processos_pe`, `iterpe_glebas_pe`, and `iterpe_malha_posses_pe`.

6. **Ingest Campanha Nacional Despejo Zero (Community Eviction Risks)**:
   ```bash
   uv run python -m src.etl_despejo_zero
   ```
   > Fetches 365 community conflicts under threat or execution of eviction in Pernambuco from the official Despejo Zero API, applies deterministic micro-jittering to coincident municipal coordinates, and loads `public.despejo_zero_pe`.

7. **Reload Tile Server (Martin)**:
   ```bash
   docker compose restart martin
   ```
   > Restarting Martin ensures it instantly detects all newly generated tables and refreshes its MVT vector tile endpoints at `http://localhost:3000/catalog`.

---

### Resetting the Database / Full Re-import

To completely wipe the database and re-import everything from scratch:

```bash
# 1. Wipe database volume and recreate containers
docker compose down -v
docker compose up -d

# 2. Re-run spatial shapefiles ingestion & overlaps calculation
uv run python -m src.etl

# 3. Process territorial jurisdictions (TJPE & JFPE)
uv run python -m src.process_jurisdicoes

# 4. Re-run judicial conflict lawsuit ingestion & enrichment
uv run python -m src.etl_datajud

# 5. Import SIGEF historical georeferencing retifications (Batateiras)
uv run python -m src.import_sigef_historico

# 6. Ingest Moradia Legal (TJPE) & Acervo Fundiário (ITERPE)
uv run python -m src.etl_moradia_iterpe

# 7. Ingest Campanha Nacional Despejo Zero
uv run python -m src.etl_despejo_zero

# 8. Restart Martin tile server
docker compose restart martin
```

---

### 4. Run the Front-end Application
Navigate to the frontend directory, install packages, and start the development server:
```bash
cd frontend
pnpm install
pnpm start
```
Open `http://localhost:4200` in your web browser. You will see an interactive map with a glassmorphic layer control panel (right) and a dedicated DataJud Judicial Categories Legend (left), serving vector tiles for all key datasets (Indigenous Lands, Quilombola Territories, SIGEF Private/Public, SNCI, CAR, ICMBio Conservation Units, Embargoes, Infraction Notices, MapBiomas Deforestation Alerts/CAR, and DataJud Lawsuits) with custom color themes, circle/symbol markers, and rich popup inspection cards.

### 5. DataJud Desktop Explorer (`datajud-gui`)

A standalone Rust/egui desktop app for browsing the full lawsuit dataset offline (no database, network or API access at runtime). Requires a Rust toolchain (`rustup default stable`).

```bash
uv run python src/export_datajud_sqlite.py   # generate the snapshot (once per ingestion)
cd datajud-gui
cargo run --release                          # finds ../data/exports/datajud/datajud_pe.sqlite
cargo run --release -- --db /path/to/datajud_pe.sqlite
cargo build --release --features embedded-snapshot   # bakes the snapshot into the binary (standalone .exe)
```

> Snapshot lookup order: `--db <path>` → `DATAJUD_DB` env var → `datajud_pe.sqlite` next to the executable → `data/exports/datajud/` in the repo → embedded copy (when built with `embedded-snapshot`). The whole dataset is loaded into memory (~45 MB, ~0.2 s) and every filter runs locally in a few milliseconds.
>
> Layout: faceted filters with live counts (tribunal, categoria, grau, ano with histogram, município, classe), a virtualized sortable table, and a detail pane (assuntos, órgão, comarca, other instances of the same CNJ number, copy/JSON/PJe actions). Shortcuts: <kbd>Ctrl</kbd>+<kbd>F</kbd> search, <kbd>↑</kbd>/<kbd>↓</kbd> move selection, <kbd>Esc</kbd> close detail/clear search. Filtered rows export to CSV or JSON.

---

## ETL Pipeline Details

The pipeline (`src/etl.py`) automates the following steps for each dataset under `data/extracted/`:
1. **Database Initialization**: Connects to PostGIS and executes `CREATE EXTENSION IF NOT EXISTS postgis;`.
2. **File Ingestion & Cleaning**: Scans `data/extracted/` recursively to find `.shp` files, removes non-finite sentinel coordinates, and loads them into GeoPandas GeoDataFrames.
3. **Coordinate Axis Rectification**: Detects inverted coordinate axes `(Lat, Lon)` (present in federal exports) and swaps them to standard `(Lon, Lat)`.
4. **Pernambuco Territorial Filtering**: References the official IBGE state boundary (`src/pe_boundary.geojson`) to filter nationwide datasets (ICMBio UCs, Embargoes, Infraction Notices) strictly to features situated within or intersecting the territory of Pernambuco (including Fernando de Noronha).
5. **Column Sanitization**: Standardizes all attribute columns to be SQL-friendly (lowercase, NFKD unicode normalized to strip accents, spaces/dashes replaced by `_`).
6. **Spatial Reprojection**: Converts CRS to **EPSG:4326 (WGS84)**.
7. **PostGIS Loading & Indexing**: Ingests the data using GeoPandas' `to_postgis()` and ensures spatial **GIST indexing** on the `geometry` column.

---

## Spatial Overlaps & Conflict Identification

The pipeline includes a spatial intersection calculator (`src/overlaps.py`) that executes automatically at the end of the ETL ingestion. It identifies and generates dedicated tables of overlaps (*overlappings*) and their geographical center points where private properties intersect traditional territories or federal environmental protection areas.

To prevent inflation from duplicate registry entries and neighboring pieces, the pipeline performs a spatial clustering and dissolve step:
1. **DBSCAN Clustering**: Groups intersecting polygons that touch or are within a very small distance (~11 meters, `eps := 0.0001` degrees) using PostGIS `ST_ClusterDBSCAN`.
2. **Dissolve (ST_Union)**: Merges clustered geometries into contiguous multi-polygons.
3. **Attribute Aggregation**: Semicolon-delimits (`string_agg`) all property names, codes, and sources for each dissolved area.

* **Target Tables**: 
  * `land_overlaps` (the overlapping polygon areas)
  * `land_overlaps_points` (the center points of conflict areas via PostGIS `ST_PointOnSurface`)
* **Sources Analyzed**:
  * Private Lands (`sigef_brasil_pe`, `imovel_certificado_snci_brasil_pe`, `area_imovel_1` - CAR)
  * Traditional Territories & Environmental Areas (`tis_poligonais`, `areas_de_quilombolas_pe`, `limiteucsfederais_a`, `embargos_icmbio`)

---

## Ingested Datasets

The ETL successfully manages and serves the following datasets:

| Target Table Name | Sources Description | Spatial Geometry | Spatial Index Type |
| :--- | :--- | :--- | :--- |
| `limiteucsfederais_a` | Unidades de Conservação Federais (ICMBio - PARNA, REBIO, APA, FLONA) | MultiPolygon | GIST |
| `embargos_icmbio` | Áreas Embargadas por infrações ambientais (ICMBio) | MultiPolygon | GIST |
| `autos_infracao_icmbio` | Autos de Infração Ambiental (ICMBio) | MultiPoint | GIST |
| `area_imovel_1` | Cadastro Ambiental Rural (CAR - SICAR) properties | MultiPolygon | GIST |
| `apps_1` | Áreas de Preservação Permanente declaradas (CAR - SICAR) | MultiPolygon | GIST |
| `reserva_legal_1` | Reserva Legal declarada/averbada (CAR - SICAR) | MultiPolygon | GIST |
| `vegetacao_nativa_1` | Remanescentes de Vegetação Nativa (CAR - SICAR) | MultiPolygon | GIST |
| `areas_de_quilombolas_pe` | Quilombola traditional territories (INCRA) | MultiPolygon | GIST |
| `imovel_certificado_snci_brasil_pe` | Certified private/public rural properties (SNCI - INCRA) | MultiPolygon | GIST |
| `imovel_certificado_snci_privado_pe` | Private certified rural properties (SNCI - INCRA) | MultiPolygon | GIST |
| `imovel_certificado_snci_publico_pe` | Public certified rural properties (SNCI - INCRA) | MultiPolygon | GIST |
| `sigef_brasil_pe` | Land management system properties (SIGEF - INCRA) | MultiPolygon | GIST |
| `sigef_privado_pe` | Private SIGEF properties | MultiPolygon | GIST |
| `sigef_publico_pe` | Public SIGEF properties | MultiPolygon | GIST |
| `tis_poligonais` | Indigenous traditional lands (FUNAI) | MultiPolygon | GIST |
| `alerts_with_intersections` | Alertas de Desmatamento e Supressão Validados (MapBiomas Alerta 2019–2026) | MultiPolygon | GIST |
| `car_with_alerts_and_intersections` | Imóveis Rurais (CAR) com sobreposição a alertas de desmatamento (MapBiomas) | MultiPolygon | GIST |
| `land_overlaps` | Spatial overlaps (conflicts) | MultiPolygon | GIST |
| `land_overlaps_points` | Center points (medians) of conflict areas | Point | GIST |
| `jurisdicao_tjpe` | Comarcas estaduais e municípios abrangidos (TJPE) | Point | GIST |
| `jurisdicao_jfpe` | Subseções judiciárias e municípios abrangidos (TRF5/JFPE) | Point | GIST |
| `jurisdicoes_pe_municipios` | Mapeamento territorial unificado dos 185 municípios de PE | Point | GIST |
| `processos_conflitos_judiciais` | Processos Judiciais de Conflito Agrário (DataJud - TJPE & TRF5) | Point | GIST |
| `processos_conflitos_municipios` | Agregação Municipal de Conflitos na Justiça (185 municípios de PE) | Point | GIST |
| `assentamentos_incra_pe` | Assentamentos de Reforma Agrária Federais (INCRA SIPRA) | MultiPolygon | GIST |
| `ucs_estaduais_cprh_pe` | Unidades de Conservação Estaduais (CPRH / MMA) | MultiPolygon | GIST |
| `processos_minerarios_pe` | Concessões e Processos Minerários Ativos (ANM SIGMINE) | MultiPolygon | GIST |
| `ibge_favelas_comunidades_pe` | Favelas e Comunidades Urbanas Censo 2022 (IBGE) | MultiPolygon | GIST |
| `moradia_legal_pe` | Perímetros Comunitários REURB Moradia Legal (TJPE) | MultiPolygon | GIST |
| `moradia_legal_processos_pe` | Processos de Regularização Fundiária Moradia Legal (TJPE) | Point | GIST |
| `iterpe_glebas_pe` | Macro-glebas Estaduais e Territórios Quilombolas (ITERPE) | MultiPolygon | GIST |
| `iterpe_malha_posses_pe` | Posses Rurais da Agricultura Familiar (ITERPE) | MultiPolygon | GIST |
| `despejo_zero_pe` | Comunidades sob Risco ou Ordem de Despejo (Campanha Despejo Zero) | Point | GIST |
| `car_casos_analisados` | Imóveis Rurais CAR com OCR e verificação analítica (Batateiras) | MultiPolygon | GIST |
| `sigef_casos_analisados` | Evolução histórica do georreferenciamento SIGEF (Batateiras - AV-17, AV-19, AV-23, Atual) | MultiPolygon | GIST |

---

## Documentation & Data Analysis

Detailed documentation covering system definitions (SIGEF, SNCI, SICAR/CAR, FUNAI, INCRA Quilombolas, ICMBio), Shapefile `.dbf` metadata structure, coordinate rectification, and empirical statistical analyses is available in:

* 📄 **[Documentation & Data Analysis Report](file:///home/raylandsoncesario/github/conflict-solver/docs/DATA_ANALYSIS.md)** (`docs/DATA_ANALYSIS.md`)



