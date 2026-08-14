# Land Conflict Mapping Platform — Data Systems & Metadata Analysis

This document provides a comprehensive overview of the spatial data systems, ESRI Shapefile metadata structures, and statistical analysis for all land boundary datasets used in the Land Conflict Mapping Platform.

---

## 1. Conceptual Framework: Data Systems Overview

### SIGEF — Sistema de Gestão Fundiária (INCRA)
* **Managing Body:** INCRA (Instituto Nacional de Colonização e Reforma Agrária).
* **Legal Basis:** Law 10.267/2001 & Decrees 4.449/2002 and 5.570/2005.
* **Function:** SIGEF is the official digital platform operated by INCRA for receiving, validating, organizing, and certifying georeferenced rural property boundaries across Brazil. It covers both private holdings and public lands/settlements. Certification in SIGEF proves that a property's perimeter does not overlap with any other previously certified parcel in the national database.

### SNCI — Sistema Nacional de Cadastro Imobiliário (INCRA Legacy)
* **Managing Body:** INCRA.
* **Function:** SNCI is INCRA's legacy database system utilized for rural property registration and certification prior to the implementation of the modern web-based SIGEF platform. SNCI records are preserved for historical verification and overlap analysis with legacy titles.

### SICAR / CAR — Cadastro Ambiental Rural (MMA)
* **Managing Body:** Ministry of the Environment (MMA) & State Environmental Agencies.
* **Legal Basis:** Brazilian Forest Code (Law 12.651/2012).
* **Function:** Mandatory public electronic registry for all rural properties in Brazil. SICAR integrates environmental information on rural properties, including Legal Reserves (RL), Permanent Preservation Areas (APP), consolidated agricultural areas, and vegetation cover.

### FUNAI — Terras Indígenas (TIs)
* **Managing Body:** FUNAI (Fundação Nacional dos Povos Indígenas).
* **Legal Basis:** Federal Constitution of 1988 (Art. 231) & Decree 1775/1996.
* **Function:** Spatial database mapping traditional Indigenous lands across Brazil. It tracks the administrative demarcation stages (Delimited, Declared, Sent for Registration, Regularized) and ethnic community identification.

### INCRA Quilombolas — Territórios Quilombolas
* **Managing Body:** INCRA.
* **Legal Basis:** Federal Constitution of 1988 (Art. 68 ADCT) & Decree 4887/2003.
* **Function:** Official spatial database mapping Quilombola traditional community territories undergoing land regularisation and titling by INCRA.

---

## 2. Spatial File Architecture & `.dbf` Metadata Role

All raw datasets in `data/raw` and extracted datasets in `data/extracted` are formatted as **ESRI Shapefiles**. 

Every record in a dBase attribute table (`.dbf`) corresponds **1-to-1** with an individual spatial polygon feature in the `.shp` file:

* **`.shp`**: Geometry storage (polygon coordinates, boundaries, and spatial vertices).
* **`.dbf`**: Attribute database table storing alphanumeric metadata (names, IDs, process numbers, status, family counts, dates).
* **`.shx`**: Shape geometry index file for rapid positional lookup.
* **`.prj`**: Coordinate Reference System specification (**EPSG:4674 - SIRGAS 2000**).
* **`.cst` / `.cpg`**: Character set encoding (e.g. UTF-8 / Windows-1252) for text attributes.
* **`.fix`**: Feature spatial lookup index for high-density datasets (SICAR).

---

## 3. Empirical Metadata Analysis & Statistical Counts

### Summary Overview Table

| Dataset | Total Polygons | Total Area (ha) | Key Sub-Types / Ownership | Primary Legal Status / Certification |
| :--- | :--- | :--- | :--- | :--- |
| **SIGEF (Pernambuco)** | 24,013 | ~890,000 | 88.23% Private (21,187)<br>11.77% Public/Settlement (2,826) | 91.77% Registered (`REGISTRADA`)<br>93.87% With Notary Book ID |
| **CAR / SICAR (Pernambuco)** | 433,105 | 8,502,855 | 99.76% Private (`IRU`)<br>0.22% Settlement (`AST`)<br>0.03% Traditional (`PCT`) | 99.23% Active status (`AT`)<br>97.12% Pending Environmental Analysis |
| **Terras Indígenas (FUNAI)** | 16 | 202,288 | 62.5% Traditionally Occupied<br>37.5% Indigenous Reserve | 62.5% Regularized (10)<br>18.8% Sent as Reserve (3)<br>12.5% Declared (2) |
| **Territórios Quilombolas (INCRA)** | 10 | 35,683 | 1,276 Registered Families | 60.0% RTID Phase (6)<br>20.0% Partial Title (2)<br>10.0% Presidential Decree (1) |
| **SNCI Legado (INCRA)** | 110 | ~105,000 | 73.64% Private (81)<br>26.36% Public/Settlement (29) | Legacy INCRA Certifications |

---

### Detailed Statistical Analysis by Dataset

### 1. SIGEF — Sistema de Gestão Fundiária (`sigef_*_pe`)
* **Total Polygons:** 24,013
* **Ownership Breakdown:**
  * **Private Imóveis (`sigef_privado_pe`):** 21,187 (88.23%)
  * **Public Lands & Settlements (`sigef_publico_pe`):** 2,826 (11.77%)
* **Legal Land Situation (`situacao_i`):**
  * `REGISTRADA` (Title registered in Notary Registry Office): **22,037** (91.77%)
  * `NAO_TITULADA` (Georeferenced but without final title): **1,268** (5.28%)
  * `TITULADA_NAO_REGISTRADA` (Title issued by INCRA, pending notary registration): **708** (2.95%)
* **SIGEF Certification Status (`status`):**
  * `CERTIFICADA` (Technical survey certified): **15,993** (66.60%)
  * `REGISTRADA` (Fully registered process): **8,020** (33.40%)
* **Cartorial Registration Integration:** **93.87%** (22,541 parcels) have notary registry book numbers (`registro_m`) explicitly recorded.

---

### 2. CAR / SICAR — Cadastro Ambiental Rural (`area_imovel_sicar`, `apps_sicar`, `reserva_legal_sicar`, `vegetacao_nativa_sicar`)

#### A. Perímetros de Imóveis (`area_imovel_1`)
* **Total Polygons:** 433,105
* **Total Declared Area:** 8,502,855.26 ha
* **Property Classification (`ind_tipo`):**
  * `IRU` (Private Rural Property): **432,052** (99.76%)
  * `AST` (Agrarian Reform Settlement Area): **932** (0.22%)
  * `PCT` (Traditional Peoples & Communities): **121** (0.03%)
* **Registry Status (`ind_status`):**
  * `AT` (Active): **429,750** (99.23%)
  * `CA` (Cancelled): **1,949** (0.45%)
  * `PE` (Pending): **1,406** (0.32%)
* **Environmental Code Condition (`des_condic`):**
  * *Aguardando análise* (Awaiting analysis): **420,619** (97.12%)
  * *Analisado, em conformidade com a Lei nº 12.651/2012* (Analyzed and compliant): **9,746** (2.25%)
  * *Cancelado por decisão administrativa* (Cancelled): **1,649** (0.38%)
  * *Analisado com ativos ambientais*: **419** (0.10%)

#### B. Áreas de Preservação Permanente — APPs (`apps_1`)
* **Total Polygons:** 273,296
* **Function:** Identifies declared environmental preservation zones (riparian forests, hilltops, steep slopes, springs).
* **Integration:** Spatial GIST indexed and served via Martin Vector Tiles.

#### C. Reserva Legal (`reserva_legal_1`)
* **Total Polygons:** 239,388
* **Function:** Identifies rural property legal reserve declarations required by Law 12.651/2012.
* **Integration:** Spatial GIST indexed and served via Martin Vector Tiles.

#### D. Remanescentes de Vegetação Nativa (`vegetacao_nativa_1`)
* **Total Polygons:** 138,475
* **Function:** Declared native vegetation coverage across rural properties.
* **Integration:** Spatial GIST indexed and served via Martin Vector Tiles.

---

### 3. Terras Indígenas — FUNAI (`tis_poligonais`)
* **Total Polygons:** 16
* **Total Area:** 202,288.00 ha
* **Administrative Demarcation Phase (`fase_ti`):**
  * *Regularizada*: **10** (62.5%)
  * *Encaminhada RI*: **3** (18.8%)
  * *Declarada*: **2** (12.5%)
  * *Delimitada*: **1** (6.2%)
* **Land Modality (`modalidade`):**
  * *Tradicionalmente ocupada*: **10** (62.5%)
  * *Reserva Indígena*: **6** (37.5%)

---

### 4. Territórios Quilombolas — INCRA (`areas_de_quilombolas_pe`)
* **Total Polygons:** 10
* **Total Area:** 35,682.80 ha
* **Registered Families:** 1,276 families
* **Demarcation Phase (`fase`):**
  * *RTID* (Relatório Técnico de Identificação e Delimitação): **6** (60.0%)
  * *TITULO PARCIAL* (Partially Titled): **2** (20.0%)
  * *DECRETO* (Presidential Decree issued): **1** (10.0%)

---

### 5. SNCI — Sistema Legado INCRA (`imovel_certificado_snci_*_pe`)
* **Total Polygons:** 110
* **Distribution:**
  * **Private Certified Holdings (`imovel_certificado_snci_privado_pe`):** 81 (73.64%)
  * **Public & Settlement Certified Holdings (`imovel_certificado_snci_publico_pe`):** 29 (26.36%)
