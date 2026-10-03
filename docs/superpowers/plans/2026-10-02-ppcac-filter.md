# PPCAC (Programa de Prevenção de Conflitos Agrários Coletivos) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ingest the official PPCAC conflict relations spreadsheet (`data/raw/Planilha_da_Relacao_Conflitos_09.02.2026.xlsx`), normalize 80 conflict areas into PostGIS (`ppcac_conflitos_pe`), link them to DataJud lawsuits and municipal boundaries, integrate into the unified search index, expose REST endpoints, and implement an interactive institutional filter panel in Angular with map isolation and fly-to navigation.

**Architecture:** Python ETL pipeline (`src/etl_ppcac.py`) rectifies column shifts and forward-fills merged cells to create `public.ppcac_conflitos_pe` in PostGIS. The unified search index denormalizes PPCAC records for global search. FastAPI (`src/search_api.py`) exposes `/ppcac/areas` and `/ppcac/filter-keys`. The Angular frontend introduces `PpcacFilterComponent` inside `.left-panels-stack` with instant search, status pills, MapLibre filter-based layer isolation, and fly-to navigation.

**Tech Stack:** Python 3.12 (openpyxl, psycopg2, shapely), PostgreSQL 17 + PostGIS 3.5, FastAPI / SQLAlchemy, Angular 20 Standalone, MapLibre GL JS.

**Spec:** [`docs/superpowers/specs/2026-10-02-ppcac-filter-design.md`](file:///home/raylenda/github/personal/ocape-etl/docs/superpowers/specs/2026-10-02-ppcac-filter-design.md)

## Global Constraints
- Python scripts run with `uv run python src/<script>.py`.
- Tests run with `uv run pytest tests/...`.
- Frontend lives in `frontend/` and builds with `pnpm build`.
- **Never execute `git commit`** unless explicitly requested by the user (`AGENTS.md` Rule 2).
- Follow minimalist institutional UI/UX: no decorative emojis, neutral boxes, monospace codes (`AGENTS.md` Rule 3).
- Spatial layers use `EPSG:4326`, 2D geometries, and GIST indexes (`AGENTS.md` Section 2).

## Review Focus
1. **Column-Shifted Rows (104–120)**: Rows where missing owners/movements pushed CNJ/MPPE/SEI codes into wrong columns must be correctly routed by regex.
2. **Merged Cells (Rows 14–16)**: Multi-row process blocks (e.g. *Engenho Congaçari*) must forward-fill property name and municipality.
3. **Multi-Value Cell Parsing**: Cells containing multiple newline-separated codes or textual noise (e.g. `"numero errado"`) must be cleaned into distinct array elements.
4. **Tiered Spatial Resolution**: Areas without DataJud matches must gracefully fall back to municipal centroids and bounding boxes with `tem_geometria_exata = False`.
5. **Cold Database / Missing Table Resilience**: The search API and frontend must handle a clean or unpopulated database without crashing.

---

### Task 1: ETL Pipeline & PostGIS Schema (`src/etl_ppcac.py`)

**Files:**
- Create: `src/etl_ppcac.py`
- Test: `tests/test_etl_ppcac.py`

**Interfaces:**
- Produces: Table `public.ppcac_conflitos_pe` with 80 consolidated rows, GIST index, and arrays for `processos_judiciais`, `processos_mppe`, `processos_sei`.
- Functions: `parse_ppcac_spreadsheet(filepath: str) -> List[Dict]`, `ingest_ppcac(conn_str: Optional[str] = None) -> int`.

- [ ] **Step 1: Write failing tests for Excel parser & regex rectification**
  In `tests/test_etl_ppcac.py`, test:
  - `test_parse_ppcac_extracts_80_areas`: Reads the spreadsheet and verifies exactly 80 unique consolidated areas.
  - `test_rectify_shifted_columns`: Verifies that row 104 (Fazenda Boa Vista dos Mocós) correctly assigns judicial process `0009683-52.2017.8.17.2480` and SEI `3900032476.000009/2020-62`, and row 108 correctly extracts `ARQUIVADO`.
  - `test_merged_cell_forward_fill`: Verifies that Engenho Congaçari captures all 3 judicial processes across rows 14-16.

- [ ] **Step 2: Run test to verify failure**
  Run: `uv run pytest tests/test_etl_ppcac.py -v`
  Expected: FAIL with `ModuleNotFoundError: No module named 'src.etl_ppcac'`

- [ ] **Step 3: Implement `src/etl_ppcac.py`**
  - Implement `parse_ppcac_spreadsheet(filepath)` using `openpyxl`:
    - Handle forward-fill for empty area/municipality from merged cells.
    - Classify cell contents using regex for CNJ (`\d{4,7}-?\d{2}\.?\d{4}\.?\d\.?\d{2}\.?\d{4}`), MPPE (`02\d{3}\.\d{3}\.\d{3}/\d{4}`), and SEI (`\d{10}\.\d{6}/\d{4}-\d{2}` | `OF\.` | `37000` | `39000` | `22000` | `00312`).
    - Consolidate by unique `(nome_area, municipio)`.
  - Implement `ingest_ppcac()`:
    - Create `ppcac_conflitos_pe` table with schema defined in Spec §3.1.
    - Match `processos_conflitos_judiciais` to extract coordinates (`ST_X`, `ST_Y`) for Tier 1.
    - Match `jurisdicoes_pe_municipios` for Tier 2 municipal fallback (`centroid`, `bbox`).
    - Insert records with `Point` geometry and GIST index.

- [ ] **Step 4: Run tests to verify they pass**
  Run: `uv run pytest tests/test_etl_ppcac.py -v`
  Expected: PASS

- [ ] **Step 5: Execute ingestion in database**
  Run: `uv run python src/etl_ppcac.py`
  Expected: Output logging 80 records inserted into `public.ppcac_conflitos_pe`.

---

### Task 2: Search Index Integration (`src/build_search_index.py` & Runner)

**Files:**
- Modify: `src/build_search_index.py:37-130`
- Modify: `src/run_all_pipelines.py`
- Test: `tests/test_search_index_ppcac.py`

**Interfaces:**
- Consumes: Table `public.ppcac_conflitos_pe`.
- Produces: `search_index` entries with `layer_id = 'ppcac_conflitos_pe'` containing area names, judicial/MPPE/SEI codes, and `"ppcac"`.

- [ ] **Step 1: Write test for PPCAC search index entries**
  In `tests/test_search_index_ppcac.py`, query `search_index` for `layer_id = 'ppcac_conflitos_pe'` and ensure `"ppcac"`, `"Barro Branco"`, and CNJ/MPPE codes match.

- [ ] **Step 2: Run test to verify failure**
  Run: `uv run pytest tests/test_search_index_ppcac.py -v`
  Expected: FAIL (no PPCAC in `search_index`).

- [ ] **Step 3: Update `src/build_search_index.py` and `src/run_all_pipelines.py`**
  - In `SEARCH_SOURCES`, add `ppcac_conflitos_pe` config:
    ```python
    {"table": "ppcac_conflitos_pe", "label": ["nome_area"],
     "codes": ["processos_judiciais", "processos_mppe", "processos_sei"],
     "text": ["proprietario", "movimento_social", "situacao"], "place": ["municipio"],
     "ibge": ["municipio_ibge"], "searchable": True}
    ```
  - Support array unnesting / formatting in `_build_insert()` if necessary so array columns are indexed into `search_text` and `codes`.
  - In `src/run_all_pipelines.py`, add `--step ppcac` and invoke `etl_ppcac.py`.

- [ ] **Step 4: Rebuild search index and verify test**
  Run: `uv run python src/build_search_index.py`
  Run: `uv run pytest tests/test_search_index_ppcac.py -v`
  Expected: PASS

---

### Task 3: Backend REST Endpoints in `src/search_api.py`

**Files:**
- Modify: `src/search_api.py`
- Test: `tests/test_ppcac_api.py`

**Interfaces:**
- Produces: `GET /ppcac/areas`, `GET /ppcac/filter-keys`.

- [ ] **Step 1: Write failing tests for `/ppcac/areas` and `/ppcac/filter-keys`**
  In `tests/test_ppcac_api.py` using FastAPI `TestClient`:
  - `test_get_ppcac_areas_returns_80`: verifies HTTP 200, `total == 80`, and stats block.
  - `test_get_ppcac_areas_filter_situacao`: verifies filtering by `situacao=ATIVO` and `situacao=ARQUIVADO`.
  - `test_get_ppcac_filter_keys`: verifies returned dictionary contains lists of CNJ lawsuit numbers.

- [ ] **Step 2: Run test to verify failure**
  Run: `uv run pytest tests/test_ppcac_api.py -v`
  Expected: FAIL with 404 Not Found.

- [ ] **Step 3: Implement endpoints in `src/search_api.py`**
  - Implement route `@app.get("/ppcac/areas")` with optional params `situacao: Optional[str]`, `q: Optional[str]`, `municipio: Optional[str]`.
  - Implement route `@app.get("/ppcac/filter-keys")` returning distinct non-null judicial and community IDs.

- [ ] **Step 4: Run tests to verify they pass**
  Run: `uv run pytest tests/test_ppcac_api.py -v`
  Expected: PASS

---

### Task 4: Frontend Service & Models (`frontend/src/app/services/ppcac.service.ts`)

**Files:**
- Create: `frontend/src/app/services/ppcac.service.ts`
- Test: `frontend/src/app/services/ppcac.service.spec.ts`

**Interfaces:**
- Produces: `PpcacService` with `getAreas()`, `getFilterKeys()`, and TypeScript models `PpcacArea`, `PpcacStats`, `PpcacResponse`.

- [ ] **Step 1: Write test for `PpcacService`**
  In `frontend/src/app/services/ppcac.service.spec.ts`, test HTTP GET calls and response transformations using `HttpTestingController`.

- [ ] **Step 2: Implement `PpcacService`**
  - Define interfaces `PpcacArea`, `PpcacStats`, `PpcacResponse`, `PpcacFilterKeys`.
  - Inject `HttpClient` and implement `getAreas(situacao?: string, query?: string)` and `getFilterKeys()`.

- [ ] **Step 3: Run frontend tests**
  Run: `pnpm --dir frontend test -- --watch=false` (or run angular cli test).

---

### Task 5: Frontend UI Component (`frontend/src/app/ppcac-filter/`)

**Files:**
- Create: `frontend/src/app/ppcac-filter/ppcac-filter.component.ts`
- Create: `frontend/src/app/ppcac-filter/ppcac-filter.component.html`
- Create: `frontend/src/app/ppcac-filter/ppcac-filter.component.css`
- Test: `frontend/src/app/ppcac-filter/ppcac-filter.component.spec.ts`

**Interfaces:**
- Consumes: `PpcacService`.
- Outputs: `@Output() areaSelected = new EventEmitter<PpcacArea>()`, `@Output() isolationToggled = new EventEmitter<boolean>()`.

- [ ] **Step 1: Write component unit test**
  In `ppcac-filter.component.spec.ts`, test:
  - Initial load populates areas list.
  - Text search filters the displayed cards.
  - Clicking an area emits `areaSelected`.
  - Toggling "Isolar no Mapa" emits `isolationToggled`.

- [ ] **Step 2: Implement Component HTML, CSS, and TypeScript**
  - Minimalist institutional styling: neutral borders, clean typography, badge counters, status pills.
  - Implement collapsible panel toggle.
  - Implement search filter input and status pills (`Todos`, `Ativos`, `Arquivados`).
  - Implement "Isolar no Mapa" toggle switch.
  - Render area cards with metadata (Landowner, Movement, counts of Jud/MPPE/SEI).

- [ ] **Step 3: Verify tests pass**
  Run component tests.

---

### Task 6: Map Integration & Layer Isolation (`frontend/src/app/app.ts` & `app.html`)

**Files:**
- Modify: `frontend/src/app/app.html:4-25`
- Modify: `frontend/src/app/app.ts`
- Modify: `frontend/src/app/app.css`

**Interfaces:**
- Consumes: `PpcacFilterComponent`.
- Coordinates: MapLibre `fitBounds`, layer filtering on `processos_conflitos_judiciais`, and dossier popup display.

- [ ] **Step 1: Embed `app-ppcac-filter` in `app.html`**
  Add `<app-ppcac-filter (areaSelected)="onPpcacAreaSelected($event)" (isolationToggled)="onPpcacIsolationToggled($event)"></app-ppcac-filter>` inside `.left-panels-scroll`.

- [ ] **Step 2: Implement Map Actions in `app.ts`**
  - `onPpcacAreaSelected(area: PpcacArea)`:
    - If `area.bbox` is available, execute `map.fitBounds(area.bbox, { padding: 80, maxZoom: 15 })`.
    - If `area.tem_geometria_exata` is true, trigger selection/highlight on matching DataJud point.
    - If `area.tem_geometria_exata` is false, show institutional banner notifying that exact polygon delimitation is pending.
  - `onPpcacIsolationToggled(active: boolean)`:
    - If active, query `ppcacService.getFilterKeys()` and set MapLibre filter expression on layer `processos_conflitos_judiciais` (`['in', ['get', 'numero_processo'], ['literal', cnjList]]`).
    - If inactive, remove filter expression to restore all judicial points.

- [ ] **Step 3: Verify Angular Build**
  Run: `pnpm --dir frontend build`
  Expected: Clean build without errors or type mismatches.

---

### Task 7: Documentation Updates (`docs/DATA_SOURCES.md`, `docs/CHANGELOG.md`)

**Files:**
- Modify: `docs/DATA_SOURCES.md`
- Modify: `docs/CHANGELOG.md`

- [ ] **Step 1: Document PPCAC in `docs/DATA_SOURCES.md`**
  Add PPCAC under Camada 2 (Cruzamentos Sociojurídicos e Processuais) detailing legal basis (Lei 18.441/2023), table structure (`ppcac_conflitos_pe`), 80 conflict areas, and tiered resolution.

- [ ] **Step 2: Update `docs/CHANGELOG.md`**
  Record the addition of the PPCAC pipeline, REST API endpoints, search index integration, and frontend filter component.
