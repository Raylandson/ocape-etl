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
│   └── DATA_ANALYSIS.md     # Comprehensive Data Systems & Metadata Analysis
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
├── frontend/                # Angular Web Front-end with MapLibre GL JS
│   ├── src/                 # Angular source code (Map component integration)
│   ├── package.json         # Node package configuration
│   └── angular.json         # Angular build configuration
└── src/
    ├── __init__.py
    ├── config.py            # Environment configurations and path parameters
    ├── database.py          # SQLAlchemy engine setup and PostGIS extension helper
    ├── etl.py               # Main ETL pipeline with axis-swap & geometry correction
    └── overlaps.py          # Spatial conflict detection engine & DBSCAN clustering
```

---

## Prerequisites

Ensure you have the following installed on your machine:
- **Docker** and **Docker Compose**
- **uv** (Fast Python package installer and resolver by Astral)
- **Python 3.12+**

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

### 3. Run the ETL Pipeline
Run the ETL script to process all shapefiles and load them into PostGIS:
```bash
uv run python -m src.etl
```

### 4. Run the Front-end Application
Navigate to the frontend directory, install packages, and start the development server:
```bash
cd frontend
pnpm install
pnpm start
```
Open `http://localhost:4200` in your web browser. You will see an interactive map with a glassmorphic layer control panel, serving vector tiles for all key datasets (Indigenous Lands, Quilombola Territories, SIGEF Private/Public, SNCI, CAR, ICMBio Conservation Units, Embargoes, and Infraction Notices) with custom color themes, circle/symbol markers, and rich popup inspection cards.

---

## ETL Pipeline Details

The pipeline (`src/etl.py`) automates the following steps for each dataset under `data/extracted/`:
1. **Database Initialization**: Connects to PostGIS and executes `CREATE EXTENSION IF NOT EXISTS postgis;`.
2. **File Ingestion & Cleaning**: Scans `data/extracted/` recursively to find `.shp` files, removes non-finite sentinel coordinates, and loads them into GeoPandas GeoDataFrames.
3. **Coordinate Axis Rectification**: Detects inverted coordinate axes `(Lat, Lon)` (present in federal exports) and swaps them to standard `(Lon, Lat)`.
4. **Column Sanitization**: Standardizes all attribute columns to be SQL-friendly (lowercase, NFKD unicode normalized to strip accents, spaces/dashes replaced by `_`).
5. **Spatial Reprojection**: Converts CRS to **EPSG:4326 (WGS84)**.
6. **PostGIS Loading & Indexing**: Ingests the data using GeoPandas' `to_postgis()` and ensures spatial **GIST indexing** on the `geometry` column.

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
| `land_overlaps` | Spatial overlaps (conflicts) | MultiPolygon | GIST |
| `land_overlaps_points` | Center points (medians) of conflict areas | Point | GIST |

---

## Documentation & Data Analysis

Detailed documentation covering system definitions (SIGEF, SNCI, SICAR/CAR, FUNAI, INCRA Quilombolas, ICMBio), Shapefile `.dbf` metadata structure, coordinate rectification, and empirical statistical analyses is available in:

* 📄 **[Documentation & Data Analysis Report](file:///home/raylandsoncesario/github/conflict-solver/docs/DATA_ANALYSIS.md)** (`docs/DATA_ANALYSIS.md`)



