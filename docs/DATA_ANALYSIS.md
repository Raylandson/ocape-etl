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

### ANEEL — Agência Nacional de Energia Elétrica (SIGEL)
* **Managing Body:** ANEEL / Ministry of Mines and Energy (MME).
* **Legal Basis:** Federal Law 9.427/1996, Decree-Law 3.365/1941 (Expropriation for Public Utility), and ANEEL Normative Resolution 740/2016.
* **Function:** Federal regulatory agency governing the Brazilian electric power sector. Operates SIGEL (Sistema de Informações Geográficas do Setor Elétrico), mapping power generation plants (wind, solar photovoltaic, thermal, hydroelectric), their parks, turbines, reservoirs and connection lines, and publishes the polygons of the Declarações de Utilidade Pública (DUP) it issues through Resoluções Autorizativas (REA). A DUP establishes a mandatory administrative servitude corridor (*servidão administrativa*) or an expropriation perimeter (*desapropriação*) over private and public lands. ANEEL also publishes the SIGA generation registry on its CKAN open-data portal.

### EPE — Empresa de Pesquisa Energética
* **Managing Body:** EPE, a federal public company linked to the Ministry of Mines and Energy (MME).
* **Legal Basis:** Federal Law 10.847/2004.
* **Function:** Responsible for power-sector expansion planning (transmission expansion programs and long-term plans). Its WebMap publishes the transmission lines and substations of the National Interconnected System (SIN), in operation and planned, with voltage, concessionaire and commissioning year. The project uses it instead of SIGEL's ONS-derived KML layers, which carry no structured attributes.

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
| **Unidades de Conservação (ICMBio)** | 10 | Polygon | Federal UCs in/intersecting PE<br>PARNA, REBIO, FLONA, APA, RESEX | Proteção Integral (Catimbau, Serra Negra, Saltinho, Pedra Talhada) & Uso Sustentável (Noronha, Costa dos Corais, Araripe, Negreiros, Acaú-Goiana) |
| **Áreas Embargadas (ICMBio)** | 246 | Polygon | Official Environmental Embargoes in PE | Legal restriction under Decree 6.514/2008 |
| **Autos de Infração (ICMBio)** | 861 | Point | Environmental Infraction Notices in PE | Administrative Sanctions & Fines |
| **Processos Judiciais (DataJud CNJ)** | 2,000 | Point | TJPE (1,000) & TRF5 PE (1,000)<br>6 Conflict Categories | Resolução CNJ 510/2023 & TPU (Posse, Reforma Agrária, Indígena/Quilombola, Terras Devolutas) |
| **Alertas de Desmatamento (MapBiomas)** | 12,395 | Polygon | Supressão de Vegetação em PE (2019-2026)<br>Agropecuária (85%), Expansão Urbana, Energia | Detecção validada por satélite (SAD Caatinga/Mata Atlântica, GLAD, PRODES) |
| **Imóveis CAR com Alertas (MapBiomas)** | 28,473 | Polygon | Imóveis SICAR em PE com alertas sobrepostos | Cruzamento espacial oficial MapBiomas com códigos `PE-` |
| **Assentamentos Rurais (INCRA SIPRA)** | 567 | MultiPolygon | Projetos de Reforma Agrária (PA, PDS, etc.) | Capacidade de famílias, códigos SIPRA e forma de obtenção |
| **UCs Estaduais (CPRH)** | 60 | MultiPolygon | Unidades de Conservação Estaduais em PE | APAs, Refúgios de Vida Silvestre (RVS), Parques e RPPNs estaduais |
| **Processos Minerários (ANM SIGMINE)** | 5,235 | Polygon | Concessões de lavra, autorizações e pesquisa | Substâncias (gipsita, calcário, água), titulares e fases da ANM |
| **Favelas e Comunidades (IBGE 2022)** | 2,381 | Polygon | Setores censitários de aglomerados urbanos em PE | Classificação oficial `CD_FCU` / `NM_FCU` do Censo Demográfico 2022 |
| **Setores Censitários Gerais (IBGE 2022)** | 19,578 | Polygon | Malha censitária intramunicipal de Pernambuco | Divisões territoriais e demográficas dos 185 municípios |
| **Despejo Zero (Comunidades Ameaçadas)** | 365 | Point | 43,585 famílias sob ameaça ativa de despejo<br>8,397 famílias removidas | Monitoramento comunitário da sociedade civil (FNDR, LabCidade, MST, CPT, MTST) |
| **DUP — Servidões e Desapropriações (ANEEL)** | 123 | MultiPolygon | 97 strips along lines (3,775 km; 20 m LD / 40 m LT median width)<br>26 areal (substations, APPs)<br>95 Servidão Administrativa · 28 Desapropriação | Resoluções Autorizativas (REA) 2012–2025 under REN 740/2016; 88 municipalities |
| **Rede Básica de Transmissão (EPE)** | 133 lines / 45 substations | MultiLineString / Point | 113 lines in operation (8,662 km)<br>20 planned (3,891 km); 230–600 kV | SIN concessions (CHESF, private transmitters) |
| **Eólicas (ANEEL SIGEL)** | 116 plants / 71 parks / 599 turbines | Point / MultiPolygon | 55 DRO, 46 in operation, 13 not started<br>Parks in operation: 26,118 ha | Generation grants (DRO, authorization) |
| **Solares Fotovoltaicas (ANEEL SIGEL)** | 355 plants / 45 parks | Point / MultiPolygon | 258 DRO, 46 in operation, 44 not started | Only 45 plants have a park polygon |
| **Termelétricas & Hidrelétricas (ANEEL SIGEL)** | 78 UTE / 27 AHE / 3 reservoirs | Point / MultiPolygon | Itaparica reservoir 86,356 ha; Moxotó 8,816 ha | Concessions and authorizations |
| **Energia × Territórios (derived)** | 143 | MultiPolygon | 90 servitude-strip crossings (588 km)<br>53 areal overlaps (parks, reservoirs, substations) | 49 settlements, 46 ITERPE glebas, 44 UCs, 3 Indigenous Lands, 1 quilombo |



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
* **Total Polygons Ingested:** 10 (Filtered to Pernambuco State territory from 347 nationwide)
* **Pernambuco Conservation Units:**
  * **Parque Nacional do Catimbau** (`PARNA` - Proteção Integral): 62,239.37 ha
  * **Área de Proteção Ambiental de Fernando de Noronha** (`APA` - Uso Sustentável): 154,365.88 ha
  * **Parque Nacional Marinho de Fernando de Noronha** (`PARNA` - Proteção Integral): 10,932.58 ha
  * **Floresta Nacional de Negreiros** (`FLONA` - Uso Sustentável): 2,967.42 ha
  * **Reserva Biológica de Serra Negra** (`REBIO` - Proteção Integral): 624.85 ha
  * **Reserva Biológica de Saltinho** (`REBIO` - Proteção Integral): 562.57 ha
  * **Reserva Biológica de Pedra Talhada** (`REBIO` - Proteção Integral): 4,382.00 ha (PE/AL)
  * **Área de Proteção Ambiental da Costa dos Corais** (`APA` - Uso Sustentável): 404,286.30 ha (PE/AL)
  * **Reserva Extrativista Acaú-Goiana** (`RESEX` - Uso Sustentável): 6,678.33 ha (PB/PE)
  * **Área de Proteção Ambiental da Chapada do Araripe** (`APA` - Uso Sustentável): 972,605.18 ha (PI/CE/PE)
* **Key Attributes:** `nomeuc`, `categoria_`, `sigla_cate`, `grupouc`, `areahaalb`, `esferaadm`, `criacaoano`.

---

### 7. Áreas Embargadas — ICMBio (`embargos_icmbio`)
* **Total Polygons Ingested:** 246 (Filtered to Pernambuco State territory from 14,375 nationwide)
* **Function:** Spatial boundaries of properties or regions under federal embargo due to environmental infractions (deforestation, fires, unauthorized commercial exploration).
* **Key Attributes:** `numero_emb`, `autuado`, `cpf_cnpj`, `tipo_infra`, `nome_uc`, `municipio`, `uf`, `ano`, `processo`.

---

### 8. Autos de Infração Ambiental — ICMBio (`autos_infracao_icmbio`)
* **Total Features Ingested (Points):** 861 (Filtered to Pernambuco State territory from 41,728 nationwide)
* **Function:** Georeferenced enforcement notices issued by federal environmental inspectors in Pernambuco.
* **Key Attributes:** `numero_ai`, `valor_mult`, `autuado`, `cpf_cnpj`, `tipo_infra`, `nome_uc`, `municipio`, `uf`, `ano`, `desc_ai_1`.

---

### 9. Processos Judiciais de Conflitos Fundiários — DataJud CNJ (`processos_conflitos_judiciais`)
* **Managing Body:** Conselho Nacional de Justiça (CNJ), Tribunal de Justiça de Pernambuco (TJPE) e Tribunal Regional Federal da 5ª Região (TRF5).
* **Legal Basis:** Resolução CNJ nº 510/2023 (Comissões de Soluções Fundiárias), Código de Processo Civil (CPC/2015), Lei da Reforma Agrária (Lei 8.629/1993), e Lei da Usucapião Especial Rural (Lei 6.969/1981).
* **Total Records Ingested:** 93,680 processos judiciais georreferenciados em Pernambuco (84.545 números de processo CNJ únicos), abrangendo o acervo completo do TJPE (88.834 processos, 1968–2026) e TRF5 (4.846 processos, 1989–2026).
* **Conflict Categorization Breakdown:**
  * **Reintegração e Conflito de Posse:** 50.286 processos (TJPE: 47.772 | TRF5: 2.514)
  * **Usucapião e Regularização de Posse:** 29.475 processos (TJPE: 28.735 | TRF5: 740)
  * **Outros Conflitos Fundiários:** 8.205 processos (TJPE: 7.328 | TRF5: 877)
  * **Reforma Agrária & Desapropriação:** 3.744 processos (TJPE: 3.215 | TRF5: 529)
  * **Terras Devolutas & Ações Discriminatórias:** 1.782 processos (TJPE: 1.749 | TRF5: 33)
  * **Povos Indígenas & Territórios Quilombolas:** 113 processos (TJPE: 6 | TRF5: 107)
  * **Conflito Coletivo Rural & Agrário:** 75 processos (TJPE: 29 | TRF5: 46)
* **Key Attributes:** `numero_processo`, `tribunal`, `grau`, `data_ajuizamento`, `categoria_conflito`, `classe_nome`, `assuntos_str`, `orgao_julgador_nome`, `municipio_nome`, `municipio_ibge`, `ultimo_movimento`, `data_ultimo_movimento`, `total_movimentos`, `url_consulta_publica`.

---

### 10. Alertas de Supressão e Desmatamento — MapBiomas Alerta (`alerts_with_intersections` e `car_with_alerts_and_intersections`)
* **Managing Body:** Iniciativa MapBiomas (Consórcio de ONGs, Universidades e Empresas de Tecnologia - TNC, Imazon, ISA, WRI Brasil, Lapig/UFG).
* **Legal & Technical Basis:** Validação de alertas de alta resolução por imagens de satélite Planet (3m) e Sentinel-2 (10m) cruzados com bases públicas fundiárias e ambientais (SICAR, SIGEF, SNCI, FUNAI, INCRA, ICMBio).
* **Total Records Ingested (PE):**
  * `alerts_with_intersections`: **12,395 alertas validados** (102.482,3 ha suprimidos entre 2019 e 2026).
  * `car_with_alerts_and_intersections`: **28,473 registros** de imóveis rurais do CAR com alertas incidentes.
* **Biome Breakdown:**
  * **Caatinga:** 12,197 alertas (98.40% dos registros | 101.700 ha).
  * **Mata Atlântica:** 198 alertas (1.60% dos registros | 782 ha).
* **Pressure Drivers & Classes (`alertclass` / `VPRESSAO`):**
  * `agriculture` (Agropecuária): **10,634 alertas** (85.79% | 85.723,8 ha) — expansão de pastagens e lavouras.
  * `others` (Outros / Transição Não Consolidada): **1,617 alertas** (13.05% | 13.590,6 ha).
  * `urban_expansion` (Expansão Urbana): **111 alertas** (0.90% | 1.042,3 ha).
  * `renewable_energy_project` (Parques Eólicos e Solares): **24 alertas** (0.19% | 2.053,9 ha) — megaprojetos fotovoltaicos e eólicos (São José do Belmonte, Terra Nova, Saloá, Caetés, Flores).
  * `ilegal_mining` (Garimpo Ilegal): **3 alertas** (0.02% | 17,8 ha) — Custódia, Petrolina, Betânia.
  * `mining` (Mineração Industrial): **3 alertas** (0.02% | 34,5 ha) — Belmonte, Petrolina, Caruaru.
  * `natural_cause` (Causa Natural): **3 alertas** (0.02% | 20,1 ha).
* **Direct Agrarian Conflict Intersections:**
  * **Terras Indígenas (`tis_poligonais`):** 133 alertas (569,1 ha) — Xukuru (100 alertas, 383,3 ha), Atikum (12 alertas), Pankará (8 alertas), Fulni-ô (5 alertas), Pipipã (4 alertas), Entre Serras (3 alertas), Kapinawá (1 alerta).
  * **Territórios Quilombolas (`areas_de_quilombolas_pe`):** 9 alertas (33,2 ha) — Conceição das Crioulas (5 alertas, 15,5 ha), Águas do Velho Chico, Contendas, Fazenda Santana, Feijão e Posse.
  * **Assentamentos de Reforma Agrária INCRA (`settlname`):** 395 alertas (2.215,8 ha) em 134 Projetos de Assentamento (PA Cachoeira I, PA São Lourenço, PA Nossa Senhora Aparecida, PA Taboleiro, PA Rosário, PA Terra Livre, etc.).
  * **Polígonos de Sobreposição Litigiosa (`land_overlaps`):** 371 alertas incidem diretamente sobre zonas de conflito mapeadas na plataforma (310 em UCs Federais, 43 em embargos ambientais, 37 em TIs e 10 em Quilombos).
  * **Correlação com Conflitos Judiciais:** Alta co-ocorrência em Serra Talhada (717 alertas | 81 processos), Petrolina (460 alertas | 111 processos), Salgueiro (165 alertas | 32 processos), Ouricuri/Araripe (>2.000 alertas) e Pesqueira (302 alertas | 96 em TIs).

---

### 10. Campanha Nacional Despejo Zero (`despejo_zero_pe`)
* **Managing Body:** Articulação Nacional da Campanha Despejo Zero (Fórum Nacional de Reforma Urbana - FNRU, LabCidade FAU-USP, Observatório de Remoções, Habitat para a Humanidade Brasil, Movimento dos Trabalhadores Rurais Sem Terra - MST, Comissão Pastoral da Terra - CPT, Movimento dos Trabalhadores Sem Teto - MTST).
* **Legal & Human Rights Framework:**
  * Pacto Internacional dos Direitos Econômicos, Sociais e Culturais (PIDESC / Comentário Geral nº 7 da ONU).
  * Arguição de Descumprimento de Preceito Fundamental nº 828 (ADPF 828 / STF).
  * Resolução CNJ nº 510/2023 (Criação de Comissões Regionais de Soluções Fundiárias e diretrizes para cumprimento de mandados de reintegração de posse).
* **Total Georeferenced Conflicts in Pernambuco:** **365 casos ativos e documentados**.
* **Family Impact Totals:**
  * **Famílias Ameaçadas (Risco Ativo de Despejo):** **43,585 famílias**.
  * **Famílias Despejadas (Remoções Já Executadas):** **8,397 famílias**.
  * **Famílias com Ordens Suspensas / Conflitos Sanados:** **3,400 famílias**.
  * **Impacto Total Consolidado:** **55,382 famílias** atingidas em Pernambuco.
* **Geographic Distribution & Hotspots:**
  * **Recife:** 93 conflitos (comunidades nas bacias do Beberibe, Tejipió e Capibaribe, beira-trilhos do Metrô/CBTU e ocupações históricas do centro e zona norte).
  * **Jaboatão dos Guararapes:** 30 conflitos (Muribeca, Prazeres, Cavaleiro, Curado).
  * **Olinda:** 28 conflitos (Peixinhos, Passarinho, Rio Doce).
  * **Goiana:** 18 conflitos (pressão de polo industrial, cana-de-açúcar e pesca artesanal).
  * **Cabo de Santo Agostinho:** 15 conflitos (pressão do Complexo Industrial Portuário de Suape e conflitos em comunidades tradicionais e posseiros).
  * **Camaragibe:** 12 conflitos.
  * **Caruaru:** 10 conflitos.
  * **Petrolina:** 9 conflitos (assentamentos de irrigação, beira do Rio São Francisco).
  * **Outros Municípios:** Timbaúba (6), Vitória de Santo Antão (4), Tamandaré (3), Moreno (3), Ipojuca (3), Paulista (3), São Lourenço da Mata (3), Sertânia (2), Tupanatinga (1).
* **Primary Conflict Causes (`causa_conflito`):**
  * *Ação de Reintegração de Posse* (Violação alegada de posse/propriedade): ~78% dos casos.
  * *Impacto de Obras Públicas / Projetos de Urbanização*: ~12% dos casos (ferrovias, drenagem, anéis viários, Suape).
  * *Alegação de Área de Risco Geológico/Hidrológico*: ~7% dos casos (encostas e margens de rios).
  * *Conflito em Área de Proteção Ambiental*: ~3% dos casos (restingas, manguezais, UCs).
* **Judicial Representation:**
  * Defensoria Pública do Estado (DPPE) e Defensoria Pública da União (DPU) acompanham mais de 65% dos casos formalizados.
  * Assessorias jurídicas populares (CPT, FNDR, advogados voluntários) cobrem 25% dos casos rurais.

### 11. Energy Infrastructure — ANEEL / SIGEL & EPE (`aneel_*_pe`, `epe_*_pe`)
Full source, endpoint, methodology and limitation notes: [`docs/DATA_SOURCES.md` § m](DATA_SOURCES.md). Pipeline: [`src/etl_aneel.py`](../src/etl_aneel.py). Snapshot collected on 2026-09-25.

* **Declarações de Utilidade Pública (`aneel_dup_pe`) — 123 polygons intersecting PE:**
  * **Shape (`forma`):** **97 strips** (`faixa`) — the servitude corridor buffered around the line axis at a constant width — and **26 areas** (`area`: 19 substations, 7 APPs of PCH Manopla). Strips are sub-pixel at state scale and read as lines on the map.
  * **Strip widths (`largura_m`, maximum inscribed circle):** Linhas de Distribuição median 20 m (3.5–58; 54 strips, 736 km); Linhas de Transmissão median 40 m (15–73; 39 strips, 2,998 km); Linhas de Interesse Restrito 20 m (4 strips, 41 km). Exact values dominate (20 m ×24, 40 m ×17, 15 m ×6, 60 m ×3 for 500 kV), confirming buffered centerlines. Narrowest: 69 kV urban lines in Recife (3.5–5 m).
  * **By modality:** Servidão Administrativa **95** (17,003.6 ha) · Desapropriação **28** (181.4 ha).
  * **By object:** Linhas de Distribuição 54 · Linhas de Transmissão 39 · Subestação 19 · Área de Preservação Permanente 7 (PCH Manopla) · Linhas de Interesse Restrito 4.
  * **By registry UF:** PE 113 · PI 4 · CE 3 · AL 1 · PB 1 · RS 1 (cross-border records kept because they intersect PE).
  * **Status:** Autorizado 117 · Registrado 6. DUP years range from 2012 to 2025 (peak: 2018).
  * **Largest corridors:** LT 500 kV São João do Piauí – Milagres II C2 / Luiz Gonzaga – Milagres II C2 (REA 5418/2015, 3,696 ha ≈ 616 km × 60 m); LT 500 kV Bom Nome II – Campo Formoso II C1 (REA 1594/2025 and REA 15946/2025, 2,090 ha ≈ 376 km); LT 500 kV Milagres II – Queimada Nova II (1,817 ha).
  * **Shared geometry:** 10 records in 5 groups share an identical polygon (`grupo_geometria`). Three groups are the same strip declared by two REAs. Two are **source errors** (`erro_origem`): the polygon of an out-of-state project (Pecém–Cumbuco/CE, REA 4797/2014; Santa Rosa–Três de Maio/RS, REA 5716/2016) is a copy of a PE line's polygon.
  * **Excluded source errors:** OBJECTID 3857 (UF=PE, located in Teresina/PI) and OBJECTID 2566 (SE Pau Ferro, geometry displaced ~40 km into PI).
* **Transmission (`epe_linhas_transmissao_pe`, `epe_subestacoes_pe`):** 133 lines (230 kV: 101 · 500 kV: 31 · 600 kV: 1), 113 in operation and 20 planned; 45 substations (42 in operation, 3 planned).
* **Wind (`aneel_eol_*_pe`):** 116 plants (DRO 55 · Operação 46 · Construção não iniciada 13 · Revogada 1 · Desativada 1); 71 park polygons (Operação 54, 26,118 ha · Construção não iniciada 16, 3,496 ha · Construção 1); 599 turbines; 64 interference regions (112,201 ha, a regulatory wake-protection criterion, not an impact footprint); 17 restricted-interest lines (592 km).
* **Solar (`aneel_ufv_*_pe`):** 355 plants (DRO 258 · Operação 46 · Construção não iniciada 44 · Revogada 6 · Anulado 1); 45 park polygons; 45 panel-array polygons (3,599 ha); 8 plant substations; 13 restricted-interest lines (82 km).
* **Thermal & Hydro:** 78 thermal plants (65 in operation); 27 hydro sites (CGH 14 · PCH 10 · UHE 3, including inventoried axes); 3 reservoirs at maximum flood level — Luiz Gonzaga/Itaparica (86,356 ha), Apolônio Sales/Moxotó (8,816 ha), Amarají (8.6 ha).
* **SIGA registry (`aneel_siga_empreendimentos_pe`):** 274 generation units (UFV 129 · UTE 69 · EOL 61 · CGH 10 · PCH 4 · UHE 1); joins SIGEL layers through `ceg_nucleo` (59 of the 116 wind plants match).
* **Energy × territory overlaps (`aneel_sobreposicoes_territorios_pe`) — 143 intersections:**
  * **Nature:** 90 are servitude-strip crossings (588 km of corridor inside territories, measured as `extensao_travessia_km` = overlap area / strip width); 53 are areal overlaps (wind/solar parks, reservoirs, substations, APPs). Shared DUP polygons are counted once (the earlier version double-counted 8 rows / 758 ha) and the two erroneous DUPs are excluded.
  * **Rural settlements (INCRA SIPRA):** 49 over 37 settlements — 42 strip crossings (71.5 km, 321 ha) and 7 by the Itaparica reservoir (197 ha; 9.5% of PA Angicos, 8.5% of PA Lago Azul).
  * **ITERPE state glebas:** 46 — 25 strip crossings (188.9 km, 706 ha) and 21 areal overlaps (2,441 ha: solar parks 1,008 ha, reservoirs 1,409 ha).
  * **Conservation units:** 20 federal (APA Chapada do Araripe: 14 wind parks, 2,513 ha, 93 turbines, plus 268 km of transmission corridors, including 144.5 km of LT 230 kV Chapada III – Crato II; PARNA do Catimbau: 1 wind park, 21 ha) and 24 state (16 strip crossings, 54.5 km).
  * **Indigenous Lands:** Fazenda Cristo Rei — 5.5 km of the 60 m LT 500 kV Paulo Afonso IV – Luiz Gonzaga C2 strip (33 ha) and 20 ha of the Moxotó reservoir; Entre Serras — Pedra do Gerônimo wind park (1.8 ha).
  * **Quilombola territories:** Castainho — the LD 69 kV Mundaú – Brejão strip only touches the edge (10 m, 0.02 ha).
  * **Sliver filtering:** 105 edge fragments (2.71 ha, 102 of them from reservoirs vs. river-margin boundaries) were discarded (areal footprints: parts < 0.1 ha or < 10 m wide; strips: parts < 100 m²). They are recorded per row in `partes_descartadas` / `area_descartada_ha`.
