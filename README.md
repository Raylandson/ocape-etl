# Land Conflict Mapping Platform (Pernambuco, Brazil)

A spatial data platform for mapping, visualizing, and analyzing agrarian land conflicts in the State of Pernambuco, Brazil.

## Project Overview

The objective of this platform is to identify geographical overlaps (*overlappings*) between private properties (sourced from SIGEF and SNCI/CAR) and traditional lands (Indigenous Territories, Quilombola Communities) or Agrarian Reform Settlements. By intersecting these spatial datasets, the platform helps identify potential conflict areas and land tenure irregularities.

### Architecture
- **Database**: PostgreSQL with PostGIS extension (for spatial queries and indexing).
- **ETL**: Python with GeoPandas, SQLAlchemy, and GeoAlchemy2.
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
├── data/
│   ├── raw/                 # Untouched ZIP backups of source data [GIT IGNORED]
│   │   ├── Imóvel certificado SNCI Brasil_PE.zip
│   │   ├── Imóvel certificado SNCI Privado_PE.zip
│   │   ├── Imóvel certificado SNCI Público_PE.zip
│   │   ├── Sigef Brasil_PE.zip
│   │   ├── Sigef Privado_PE.zip
│   │   ├── Sigef Público_PE.zip
│   │   ├── tis_poligonais.zip
│   │   └── Áreas de Quilombolas_PE.zip
│   └── extracted/           # Extracted shapefiles used as ingestion input by the ETL
│       ├── areas_de_quilombolas_pe/
│       ├── imovel_certificado_snci_brasil_pe/
│       ├── imovel_certificado_snci_privado_pe/
│       ├── imovel_certificado_snci_publico_pe/
│       ├── sigef_brasil_pe/
│       ├── sigef_privado_pe/
│       ├── sigef_publico_pe/
│       └── tis_poligonais/
├── frontend/                # Angular Web Front-end with MapLibre GL JS
│   ├── src/                 # Angular source code (Map component integration)
│   ├── package.json         # Node package configuration
│   └── angular.json         # Angular build configuration (increased bundle budget for MapLibre)
└── src/
    ├── __init__.py
    ├── config.py            # Environment configurations and path parameters
    ├── database.py          # SQLAlchemy engine setup and PostGIS extension helper
    └── etl.py               # Main ETL pipeline (GeoPandas -> PostGIS)
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
This will automatically create a virtual environment (`.venv`) and install dependencies: `geopandas`, `sqlalchemy`, `geoalchemy2`, and `psycopg2-binary`.

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
Open `http://localhost:4200` in your web browser. You will see an interactive map with a glassmorphic layer control panel, serving vector tiles for all 6 main datasets (Indigenous Lands, Quilombola Territories, SIGEF Private/Public, and SNCI Private/Public) in distinct, custom-colored layers with toggle controls.

---

## ETL Pipeline Details

The pipeline (`src/etl.py`) automates the following steps for each dataset under `data/extracted/`:
1. **Database Initialization**: Connects to PostGIS and executes `CREATE EXTENSION IF NOT EXISTS postgis;`.
2. **File Ingestion**: Scans `data/extracted/` recursively to find `.shp` files and loads them into GeoPandas GeoDataFrames.
3. **Column Sanitization**: Standardizes all attribute columns to be SQL-friendly (lowercase, NFKD unicode normalized to strip accents, spaces/dashes replaced by `_`).
4. **Spatial Reprojection**: Detects the original Coordinate Reference System (CRS) and converts it to **EPSG:4326 (WGS84)**, the web standard.
5. **PostGIS Loading & Indexing**: Ingests the data using GeoPandas' `to_postgis()`, dropping/replacing tables of the same name and automatically creating a spatial **GIST index** on the `geometry` column to optimize spatial queries.

---

## Spatial Overlaps & Conflict Identification

The pipeline includes a spatial intersection calculator (`src/overlaps.py`) that executes automatically at the end of the ETL ingestion. It identifies and generates a dedicated table of overlaps (*overlappings*) where private properties intersect traditional territories.

This table is optimized with a spatial **GIST index** to allow the Martin vector tile server to serve the conflict areas instantaneously to the front-end.

* **Target Table**: `land_overlaps`
* **Sources Analyzed**:
  * Private Lands (`sigef_privado_pe`, `imovel_certificado_snci_privado_pe`)
  * Traditional Territories (`tis_poligonais`, `areas_de_quilombolas_pe`)

---

## Ingested Datasets

The ETL successfully manages and serves the following datasets:

| Target Table Name | Sources Description | Spatial CRS | Spatial Index Type |
| :--- | :--- | :--- | :--- |
| `areas_de_quilombolas_pe` | Quilombola traditional territories | EPSG:4326 | GIST |
| `imovel_certificado_snci_brasil_pe` | Certified private/public rural properties (SNCI - INCRA) | EPSG:4326 | GIST |
| `imovel_certificado_snci_privado_pe` | Private certified rural properties (SNCI - INCRA) | EPSG:4326 | GIST |
| `imovel_certificado_snci_publico_pe` | Public certified rural properties (SNCI - INCRA) | EPSG:4326 | GIST |
| `sigef_brasil_pe` | Land management system properties (SIGEF - INCRA) | EPSG:4326 | GIST |
| `sigef_privado_pe` | Private SIGEF properties | EPSG:4326 | GIST |
| `sigef_publico_pe` | Public SIGEF properties | EPSG:4326 | GIST |
| `tis_poligonais` | Indigenous traditional lands (FUNAI) | EPSG:4326 | GIST |
| `land_overlaps` | Spatial overlaps (conflicts) | EPSG:4326 | GIST |
