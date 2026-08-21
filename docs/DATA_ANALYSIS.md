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

### ICMBio — Instituto Chico Mendes de Conservação da Biodiversidade
* **Managing Body:** ICMBio / Ministry of the Environment (MMA).
* **Legal Basis:** Federal Law 11.516/2007, SNUC (Federal Law 9.985/2000), and Federal Decree 6.514/2008.
* **Function:** Federal autarchy responsible for creating, managing, protecting, and monitoring Federal Conservation Units (UCs), enforcing biodiversity protection laws, enacting administrative embargoes on degraded lands, and issuing official infraction notices (Autos de Infração) against environmental crimes.

---

## 2. Spatial File Architecture & `.dbf` Metadata Role

All raw datasets in `data/raw` and extracted datasets in `data/extracted` are formatted as **ESRI Shapefiles**. 

Every record in a dBase attribute table (`.dbf`) corresponds **1-to-1** with an individual spatial feature in the `.shp` file:

* **`.shp`**: Geometry storage (polygon boundaries, multipoints, and coordinate vertices).
* **`.dbf`**: Attribute database table storing alphanumeric metadata (names, IDs, process numbers, status, penalties, dates).
* **`.shx`**: Shape geometry index file for rapid positional lookup.
* **`.prj`**: Coordinate Reference System specification (**EPSG:4674 - SIRGAS 2000**).
* **`.cst` / `.cpg`**: Character set encoding (e.g. UTF-8 / Windows-1252) for text attributes.
* **`.fix`**: Feature spatial lookup index for high-density datasets (SICAR).

> [!NOTE]
> **Coordinate Axis Rectification**: Raw ICMBio shapefiles exported by federal systems contained inverted coordinate axes `(Latitude, Longitude)` with X in `[-35, +6]` and Y in `[-75, -30]`. The ETL pipeline automatically detects this condition and rectifies geometry coordinates to standard `(Longitude, Latitude)` EPSG:4326 during ingestion.

---

## 3. Empirical Metadata Analysis & Statistical Counts

### Summary Overview Table

| Dataset | Total Features | Spatial Type | Key Sub-Types / Ownership | Primary Legal Status / Coverage |
| :--- | :--- | :--- | :--- | :--- |
| **SIGEF (Pernambuco)** | 24,013 | Polygon | 88.23% Private (21,187)<br>11.77% Public/Settlement (2,826) | 91.77% Registered (`REGISTRADA`)<br>93.87% With Notary Book ID |
| **CAR / SICAR (Pernambuco)** | 433,105 | Polygon | 99.76% Private (`IRU`)<br>0.22% Settlement (`AST`)<br>0.03% Traditional (`PCT`) | 99.23% Active status (`AT`)<br>97.12% Pending Analysis |
| **Terras Indígenas (FUNAI)** | 16 | Polygon | 62.5% Traditionally Occupied<br>37.5% Indigenous Reserve | 62.5% Regularized (10)<br>18.8% Sent as Reserve (3) |
| **Territórios Quilombolas (INCRA)** | 10 | Polygon | 1,276 Registered Families | 60.0% RTID Phase (6)<br>20.0% Partial Title (2) |
| **SNCI Legado (INCRA)** | 110 | Polygon | 73.64% Private (81)<br>26.36% Public/Settlement (29) | Legacy INCRA Certifications |
| **Unidades de Conservação (ICMBio)** | 347 | Polygon | Federal UCs (7 in PE)<br>PARNA, REBIO, FLONA, APA | Proteção Integral (Catimbau, Serra Negra, Saltinho) & Uso Sustentável |
| **Áreas Embargadas (ICMBio)** | 14,375 | Polygon | Official Environmental Embargoes<br>251 in Pernambuco | Legal restriction under Decree 6.514/2008 |
| **Autos de Infração (ICMBio)** | 41,728 | Point | Environmental Infraction Notices<br>839 in Pernambuco | Administrative Sanctions & Fines |
| **Processos Judiciais (DataJud CNJ)** | 2,000 | Point | TJPE (1,000) & TRF5 PE (1,000)<br>6 Conflict Categories | Resolução CNJ 510/2023 & TPU (Posse, Reforma Agrária, Indígena/Quilombola, Terras Devolutas) |


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

---

### 6. Unidades de Conservação Federais — ICMBio (`limiteucsfederais_a`)
* **Total Polygons:** 347 (National scope; 7 units in Pernambuco)
* **Pernambuco Conservation Units:**
  * **Parque Nacional do Catimbau** (`PARNA` - Proteção Integral): 62,239.37 ha
  * **Área de Proteção Ambiental de Fernando de Noronha** (`APA` - Uso Sustentável): 154,365.88 ha
  * **Reserva Biológica do Atol das Rocas** (`REBIO` - Proteção Integral): 35,186.77 ha
  * **Parque Nacional Marinho de Fernando de Noronha** (`PARNA` - Proteção Integral): 10,932.58 ha
  * **Floresta Nacional de Negreiros** (`FLONA` - Uso Sustentável): 2,967.42 ha
  * **Reserva Biológica de Serra Negra** (`REBIO` - Proteção Integral): 624.85 ha
  * **Reserva Biológica de Saltinho** (`REBIO` - Proteção Integral): 562.57 ha
* **Key Attributes:** `nomeuc`, `categoria_`, `sigla_cate`, `grupouc`, `areahaalb`, `esferaadm`, `criacaoano`.

---

### 7. Áreas Embargadas — ICMBio (`embargos_icmbio`)
* **Total Polygons:** 14,375 (251 in Pernambuco)
* **Function:** Spatial boundaries of properties or regions under federal embargo due to environmental infractions (deforestation, fires, unauthorized commercial exploration).
* **Key Attributes:** `numero_emb`, `autuado`, `cpf_cnpj`, `tipo_infra`, `nome_uc`, `municipio`, `uf`, `ano`, `processo`.

---

### 8. Autos de Infração Ambiental — ICMBio (`autos_infracao_icmbio`)
* **Total Features (Points):** 41,728 (839 in Pernambuco)
* **Function:** Georeferenced enforcement notices issued by federal environmental inspectors.
* **Key Attributes:** `numero_ai`, `valor_mult`, `autuado`, `cpf_cnpj`, `tipo_infra`, `nome_uc`, `municipio`, `uf`, `ano`, `desc_ai_1`.

---

### 9. Processos Judiciais de Conflitos Fundiários — DataJud CNJ (`processos_conflitos_judiciais`)
* **Managing Body:** Conselho Nacional de Justiça (CNJ), Tribunal de Justiça de Pernambuco (TJPE) e Tribunal Regional Federal da 5ª Região (TRF5).
* **Legal Basis:** Resolução CNJ nº 510/2023 (Comissões de Soluções Fundiárias), Código de Processo Civil (CPC/2015), Lei da Reforma Agrária (Lei 8.629/1993), e Lei da Usucapião Especial Rural (Lei 6.969/1981).
* **Total Records Ingested:** 2,000 processos ativos georreferenciados em Pernambuco.
* **Conflict Categorization Breakdown:**
  * **Reintegração e Conflito de Posse:** 1,079 processos (TJPE: 663 | TRF5: 416)
  * **Usucapião e Regularização de Posse:** 414 processos (TJPE: 242 | TRF5: 172)
  * **Reforma Agrária & Desapropriação:** 145 processos (TJPE: 16 | TRF5: 129)
  * **Povos Indígenas & Territórios Quilombolas:** 30 processos (TJPE: 1 | TRF5: 29)
  * **Terras Devolutas & Ações Discriminatórias:** 28 processos (TJPE: 15 | TRF5: 13)
  * **Conflito Coletivo Rural & Agrário:** 3 processos (TRF5: 3)
  * **Outros Conflitos Fundiários:** 301 processos (TJPE: 63 | TRF5: 238)
* **Key Attributes:** `numero_processo`, `tribunal`, `grau`, `data_ajuizamento`, `categoria_conflito`, `classe_nome`, `assuntos_str`, `orgao_julgador_nome`, `municipio_nome`, `municipio_ibge`, `ultimo_movimento`, `data_ultimo_movimento`, `total_movimentos`, `url_consulta_publica`.


