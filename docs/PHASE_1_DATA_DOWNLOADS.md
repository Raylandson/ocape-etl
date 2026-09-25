# Catálogo de Download Direto — Fontes de Dados Fase 1

Este documento reúne os links diretos e não truncados para download e replicação das bases de dados territoriais da Fase 1 integradas à plataforma.

---

## 1. Assentamentos Rurais Federais (INCRA SIPRA)
* **Órgão:** Instituto Nacional de Colonização e Reforma Agrária (INCRA) / GeoServer FUNAI (CMR)
* **Camada:** `CMR-PUBLICO:lim_assentamento_rural_a`
* **Formato:** GeoJSON (WFS)
* **Filtro Aplicado:** `sg_uf='PE'` (Pernambuco)
* **URL Direta:**
  ```text
  https://cmr.funai.gov.br/geoserver/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=CMR-PUBLICO:lim_assentamento_rural_a&cql_filter=sg_uf=%27PE%27&outputFormat=application/json
  ```
* **Comando de Download:**
  ```bash
  curl -L -k -o data/extracted/assentamentos_incra_pe/assentamentos_incra_pe.geojson \
    "https://cmr.funai.gov.br/geoserver/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=CMR-PUBLICO:lim_assentamento_rural_a&cql_filter=sg_uf=%27PE%27&outputFormat=application/json"
  ```

---

## 2. Unidades de Conservação Estaduais (CPRH / CNUC)
* **Órgão:** Agência Estadual de Meio Ambiente de Pernambuco (CPRH) / MMA CNUC
* **Camada:** `CMR-PUBLICO:lim_cnuc_2024_02_estadual_a`
* **Formato:** GeoJSON (WFS) e Shapefile (MMA)
* **Filtro Aplicado:** `sg_uf='PE'` (Pernambuco)
* **URL Direta WFS:**
  ```text
  https://cmr.funai.gov.br/geoserver/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=CMR-PUBLICO:lim_cnuc_2024_02_estadual_a&cql_filter=sg_uf=%27PE%27&outputFormat=application/json
  ```
* **URL Direta Shapefile (Nacional CNUC):**
  ```text
  https://dados.mma.gov.br/dataset/unidades-de-conservacao-do-brasil/resource/shp_cnuc_2025_08.zip
  ```
* **Comando de Download:**
  ```bash
  curl -L -k -o data/extracted/ucs_estaduais_cprh_pe/ucs_estaduais_cprh_pe.geojson \
    "https://cmr.funai.gov.br/geoserver/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=CMR-PUBLICO:lim_cnuc_2024_02_estadual_a&cql_filter=sg_uf=%27PE%27&outputFormat=application/json"
  ```

---

## 3. Processos Minerários e Concessões de Lavra (ANM SIGMINE)
* **Órgão:** Agência Nacional de Mineração (ANM) / SIGMINE
* **Formato:** Shapefile (ZIP)
* **Abrangência:** Estado de Pernambuco (atualização diária)
* **URL Direta:**
  ```text
  https://dadosabertos.anm.gov.br/SIGMINE/PROCESSOS_MINERARIOS/PE.zip
  ```
* **Comando de Download & Descompactação:**
  ```bash
  curl -L -k -o /tmp/PE_minerarios.zip "https://dadosabertos.anm.gov.br/SIGMINE/PROCESSOS_MINERARIOS/PE.zip"
  unzip -o /tmp/PE_minerarios.zip -d data/extracted/processos_minerarios_pe/
  ```

---

## 4. Favelas e Comunidades Urbanas / Setores Censitários (IBGE Censo 2022)
* **Órgão:** Instituto Brasileiro de Geografia e Estatística (IBGE)
* **Formato:** Shapefile (ZIP)
* **Abrangência:** Setores Censitários Intramunicipais de Pernambuco (Censo 2022)
* **URL Direta:**
  ```text
  https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_de_setores_censitarios__divisoes_intramunicipais/censo_2022/setores/shp/PE/PE_setores_CD2022.zip
  ```
* **Comando de Download & Descompactação:**
  ```bash
  curl -L -k -o /tmp/PE_setores_CD2022.zip "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_de_setores_censitarios__divisoes_intramunicipais/censo_2022/setores/shp/PE/PE_setores_CD2022.zip"
  unzip -o /tmp/PE_setores_CD2022.zip -d data/extracted/pe_setores_cd2022/
  ```
* **Nota de Filtragem:** Os setores de favelas e comunidades urbanas foram extraídos a partir da condição `CD_FCU IS NOT NULL` / `NM_FCU IS NOT NULL` (ou classificação equivalente do Censo 2022) e gravados em `public.ibge_favelas_comunidades_pe`.

---

## 5. Campanha Nacional Despejo Zero (Monitoramento Popular de Conflitos)
* **Órgão / Entidade:** Campanha Despejo Zero (Articulação da Sociedade Civil / MST / MTST / CPT / FNDR / LabCidade)
* **Portal / Repositório:** `https://campanhadespejozero.org/` | Mapa Interativo: `https://mapa.despejozero.org.br/`
* **Endpoint da API Aberta:**
  ```text
  https://mapa.despejozero.org.br/wp-json/conflitosurbanos/v1/busca
  ```
* **Comando de Download & Ingestão:**
  ```bash
  uv run python src/etl_despejo_zero.py
  ```
* **Arquivos Gerados:**
  - `data/raw/despejo_zero_brasil.json` (Base nacional completa)
  - `data/extracted/despejo_zero_pe/despejo_zero_pe.geojson` (365 comunidades em PE)
* **Tabela PostGIS:** `public.despejo_zero_pe` (indexada com GIST)
* **Visualização:** Servida via Martin Vector Tiles (`http://localhost:3000/despejo_zero_pe`) e renderizada na camada *Campanha Despejo Zero (Comunidades sob Risco)*.

---

## 6. Infraestrutura Energética & Servidões (ANEEL SIGEL / EPE / ANEEL Dados Abertos)
* **Órgãos:** Agência Nacional de Energia Elétrica (ANEEL) e Empresa de Pesquisa Energética (EPE).
* **Download manual:** **não é necessário.** As três fontes são APIs públicas, sem autenticação, consultadas pelo pipeline.
* **Endpoints:**
  ```text
  https://sigel.aneel.gov.br/arcgis/rest/services                                    # ANEEL SIGEL (ArcGIS REST 11.5)
  https://gisepeprd2.epe.gov.br/arcgis/rest/services/WMS_Webmap_EPE_Data/MapServer   # EPE WebMap (linhas e subestações da Rede Básica)
  https://dadosabertos.aneel.gov.br/api/3/action/package_show?id=siga-sistema-de-informacoes-de-geracao-da-aneel   # SIGA (CSV)
  ```
* **Exemplo de consulta (DUPs que tocam PE, GeoJSON em EPSG:4326):**
  ```text
  https://sigel.aneel.gov.br/arcgis/rest/services/DadosAbertos/DUP/MapServer/0/query?where=1%3D1&geometry=-41.36,-9.49,-34.80,-7.15&geometryType=esriGeometryEnvelope&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&outSR=4326&f=geojson
  ```
* **Comando de Download & Ingestão:**
  ```bash
  uv run python -m src.etl_aneel            # consulta as APIs (≈2–3 min), grava o cache e carrega no PostGIS
  uv run python -m src.etl_aneel --offline  # recarrega só a partir do cache
  ```
* **Arquivos Gerados:** `data/raw/aneel/*.geojson` (uma resposta por camada, com bloco `metadata`) e `data/raw/aneel/siga-empreendimentos-geracao.csv` (~116 MB no total, 107 MB só dos reservatórios).
* **Tabelas PostGIS:** `aneel_dup_pe`, `aneel_eol_*_pe`, `aneel_ufv_*_pe`, `aneel_lt_interesse_restrito_pe`, `aneel_ute_usinas_pe`, `aneel_hidro_*_pe`, `epe_linhas_transmissao_pe`, `epe_subestacoes_pe`, `aneel_siga_empreendimentos_pe` e a derivada `aneel_sobreposicoes_territorios_pe`. Inventário completo em [`DATA_SOURCES.md` § m](DATA_SOURCES.md).
