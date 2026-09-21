#!/usr/bin/env python3
"""
Script to import the historical georeferencing evolution of FAZENDA 2 IRMÃOS (Engenho Batateiras - Matrícula 73 de Maraial/PE).
Imports the 3 KML phases from data/raw/:
  - AV-17-73 (08/07/2020) - 917,8092 ha (Primeiro georreferenciamento certificado)
  - AV-19-73 (08/09/2020) - 940,4493 ha (1ª retificação: +22,64 ha)
  - AV-23-73 (04/02/2021) - 977,7794 ha (2ª retificação: +37,33 ha)
Plus the active registered SIGEF parcel from sigef_privado_pe:
  - SIGEF Atual (19/05/2021 / 14/06/2021) - 978,9348 ha (Certificação definitiva INCRA)
Creates public.sigef_casos_analisados with spatial GIST index for Martin vector tile publishing.
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import psycopg2
from shapely.geometry import Polygon
import shapely.wkt
import geopandas as gpd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import BASE_DIR, RAW_DATA_DIR, DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME


def parse_kml_polygon(file_path: Path):
    tree = ET.parse(file_path)
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    root = tree.getroot()
    coords_elem = root.find('.//kml:coordinates', ns)
    if coords_elem is None or not coords_elem.text:
        raise ValueError(f"No coordinates found in {file_path}")
    
    pts = []
    for item in coords_elem.text.strip().split():
        parts = item.split(',')
        if len(parts) >= 2:
            pts.append((float(parts[0]), float(parts[1])))
    return Polygon(pts)


def main():
    print("=" * 70)
    print("IMPORTING SIGEF HISTORICAL PHASES - FAZENDA 2 IRMÃOS (MARAIAL/PE)")
    print("=" * 70)

    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT
    )
    conn.autocommit = True
    cur = conn.cursor()

    # Query current registered SIGEF parcel
    cur.execute("""
        SELECT ST_AsText(geometry)
        FROM sigef_privado_pe
        WHERE codigo_imo = '9510994953100'
        LIMIT 1;
    """)
    sigef_row = cur.fetchone()
    if not sigef_row:
        raise RuntimeError("Could not find parcel 9510994953100 in sigef_privado_pe!")

    sigef_geom_wkt = sigef_row[0]
    sigef_geom = shapely.wkt.loads(sigef_geom_wkt)

    # 3 KML files in data/raw
    kml_phases = [
        {
            "fase": "AV-17-73",
            "titulo_fase": "AV-17-73 (08/07/2020) - 1º Georreferenciamento Certificado",
            "ordem_cronologica": 1,
            "data_averbacao": "08/07/2020",
            "nome_imovel": "FAZENDA 2 IRMÃOS (Engenho Batateiras)",
            "codigo_imo": "9510994953100",
            "matricula_cartorio": "Matrícula nº 73 (Livro 02, RGI Maraial)",
            "num_area": 917.8092,
            "perimetro_m": 12751.03,
            "variacao_area_ha": 0.0,
            "variacao_descricao": "Marco inicial (georreferenciamento originário certificado)",
            "proprietaria": "SIMARCO - Administração e Participação Ltda.",
            "responsavel_tecnico": "Certificado INCRA",
            "art": "Certificação Inicial",
            "parcela_codigo": "",
            "situacao": "HISTÓRICO (Substituído por Retificação)",
            "municipio": "Maraial",
            "uf": "PE",
            "conflito_judicial": "TJPE Maraial 0000263-83.2026.8.17.2940 (Reintegração de Posse)",
            "sobreposicao_car_ha": 144.62,
            "sobreposicao_car_info": "Sobreposição total (100%) sobre 7 posses rurais familiares (Sítios Batateira, Flora Clara, Saputi, Batateirinha e Riachão)",
            "descricao": "Primeiro georreferenciamento certificado do imóvel Matrícula 73 (Engenho Batateiras). Proprietária na época: SIMARCO - Administração e Participação Ltda.",
            "cor_hex": "#3b82f6",
            "arquivo_origem": "Engenho_Batateiras_AV-17-73_2020_917ha.kml",
            "polygon": parse_kml_polygon(RAW_DATA_DIR / "Engenho_Batateiras_AV-17-73_2020_917ha.kml")
        },
        {
            "fase": "AV-19-73",
            "titulo_fase": "AV-19-73 (08/09/2020) - 1ª Retificação de Área (+22,64 ha)",
            "ordem_cronologica": 2,
            "data_averbacao": "08/09/2020",
            "nome_imovel": "FAZENDA 2 IRMÃOS (Engenho Batateiras)",
            "codigo_imo": "9510994953100",
            "matricula_cartorio": "Matrícula nº 73 (Livro 02, RGI Maraial)",
            "num_area": 940.4493,
            "perimetro_m": 13302.54,
            "variacao_area_ha": 22.6401,
            "variacao_descricao": "+22,64 ha vs AV-17-73 (expansão a sudoeste e sul)",
            "proprietaria": "IC Consultoria e Empreendimentos Imobiliários Ltda.",
            "responsavel_tecnico": "Certificado INCRA",
            "art": "1ª Retificação",
            "parcela_codigo": "",
            "situacao": "HISTÓRICO (Substituído por Retificação)",
            "municipio": "Maraial",
            "uf": "PE",
            "conflito_judicial": "TJPE Maraial 0000263-83.2026.8.17.2940 (Reintegração de Posse)",
            "sobreposicao_car_ha": 144.62,
            "sobreposicao_car_info": "Sobreposição total (100%) sobre 7 posses rurais familiares (Sítios Batateira, Flora Clara, Saputi, Batateirinha e Riachão)",
            "descricao": "1ª retificação do georreferenciamento (+22,64 ha vs AV-17-73). Proprietária na época: IC Consultoria e Empreendimentos Imobiliários Ltda.",
            "cor_hex": "#f59e0b",
            "arquivo_origem": "Engenho_Batateiras_AV-19-73_2020_940ha.kml",
            "polygon": parse_kml_polygon(RAW_DATA_DIR / "Engenho_Batateiras_AV-19-73_2020_940ha.kml")
        },
        {
            "fase": "AV-23-73",
            "titulo_fase": "AV-23-73 (04/02/2021) - 2ª Retificação de Área (+37,33 ha)",
            "ordem_cronologica": 3,
            "data_averbacao": "04/02/2021",
            "nome_imovel": "FAZENDA 2 IRMÃOS (Engenho Batateiras)",
            "codigo_imo": "9510994953100",
            "matricula_cartorio": "Matrícula nº 73 (Livro 02, RGI Maraial)",
            "num_area": 977.7794,
            "perimetro_m": 13956.20,
            "variacao_area_ha": 59.9702,
            "variacao_descricao": "+37,33 ha vs AV-19-73 (+59,97 ha acumulados vs AV-17-73; expansão ao norte e noroeste)",
            "proprietaria": "IR Agropecuária Fazenda 2 Irmãos Ltda.",
            "responsavel_tecnico": "Certificado INCRA",
            "art": "2ª Retificação",
            "parcela_codigo": "",
            "situacao": "HISTÓRICO (Base para Certificação Atual)",
            "municipio": "Maraial",
            "uf": "PE",
            "conflito_judicial": "TJPE Maraial 0000263-83.2026.8.17.2940 (Reintegração de Posse)",
            "sobreposicao_car_ha": 144.62,
            "sobreposicao_car_info": "Sobreposição total (100%) sobre 7 posses rurais familiares (Sítios Batateira, Flora Clara, Saputi, Batateirinha e Riachão)",
            "descricao": "2ª retificação do georreferenciamento (+37,33 ha vs AV-19-73; +59,97 ha vs AV-17-73). Proprietária: IR Agropecuária Fazenda 2 Irmãos Ltda.",
            "cor_hex": "#ef4444",
            "arquivo_origem": "Engenho_Batateiras_AV-23-73_2021_04_977ha.kml",
            "polygon": parse_kml_polygon(RAW_DATA_DIR / "Engenho_Batateiras_AV-23-73_2021_04_977ha.kml")
        },
        {
            "fase": "SIGEF Atual",
            "titulo_fase": "SIGEF Oficial / Ativo INCRA (19/05/2021 - 14/06/2021) - 978,93 ha",
            "ordem_cronologica": 4,
            "data_averbacao": "14/06/2021",
            "nome_imovel": "FAZENDA 2 IRMÃOS - FAZENDA 2 IRMÃOS",
            "codigo_imo": "9510994953100",
            "matricula_cartorio": "Matrícula nº 73 (Livro 02, RGI Maraial)",
            "num_area": 978.9348,
            "perimetro_m": 14133.65,
            "variacao_area_ha": 61.1256,
            "variacao_descricao": "+1,15 ha vs AV-23-73 (+61,13 ha total acumulado vs AV-17-73)",
            "proprietaria": "IR Agropecuária Fazenda 2 Irmãos Ltda.",
            "responsavel_tecnico": "RT: CCWB",
            "art": "PE20210624725-PE",
            "parcela_codigo": "21971a92-35e1-4f18-bda1-85bd31ccb13b",
            "situacao": "REGISTRADA (Vigente)",
            "municipio": "Maraial",
            "uf": "PE",
            "conflito_judicial": "TJPE Maraial 0000263-83.2026.8.17.2940 (Reintegração de Posse)",
            "sobreposicao_car_ha": 144.62,
            "sobreposicao_car_info": "Sobreposição total (100%) sobre 7 posses rurais familiares (Sítios Batateira, Flora Clara, Saputi, Batateirinha e Riachão)",
            "descricao": "Certificação cadastrada e aprovada no SIGEF/INCRA em 19/05/2021 e averbada na Matrícula 73 em 14/06/2021.",
            "cor_hex": "#8b5cf6",
            "arquivo_origem": "sigef_privado_pe (Banco Oficial INCRA)",
            "polygon": sigef_geom
        }
    ]

    # Recreate public.sigef_casos_analisados
    cur.execute("DROP TABLE IF EXISTS public.sigef_casos_analisados CASCADE;")
    cur.execute("""
        CREATE TABLE public.sigef_casos_analisados (
            id SERIAL PRIMARY KEY,
            fase VARCHAR(50) NOT NULL,
            titulo_fase VARCHAR(200) NOT NULL,
            ordem_cronologica INTEGER NOT NULL,
            data_averbacao VARCHAR(30) NOT NULL,
            nome_imovel VARCHAR(200) NOT NULL,
            codigo_imo VARCHAR(50) NOT NULL,
            matricula_cartorio VARCHAR(150) NOT NULL,
            num_area DOUBLE PRECISION NOT NULL,
            perimetro_m DOUBLE PRECISION NOT NULL,
            variacao_area_ha DOUBLE PRECISION NOT NULL,
            variacao_descricao TEXT,
            proprietaria VARCHAR(250) NOT NULL,
            responsavel_tecnico VARCHAR(150),
            art VARCHAR(100),
            parcela_codigo VARCHAR(100),
            situacao VARCHAR(100),
            municipio VARCHAR(100) NOT NULL,
            uf VARCHAR(10) NOT NULL,
            conflito_judicial TEXT,
            sobreposicao_car_ha DOUBLE PRECISION,
            sobreposicao_car_info TEXT,
            descricao TEXT,
            cor_hex VARCHAR(20) NOT NULL,
            arquivo_origem VARCHAR(150) NOT NULL,
            geometry GEOMETRY(Polygon, 4326) NOT NULL
        );
    """)

    insert_sql = """
        INSERT INTO public.sigef_casos_analisados (
            fase, titulo_fase, ordem_cronologica, data_averbacao, nome_imovel,
            codigo_imo, matricula_cartorio, num_area, perimetro_m, variacao_area_ha,
            variacao_descricao, proprietaria, responsavel_tecnico, art, parcela_codigo,
            situacao, municipio, uf, conflito_judicial, sobreposicao_car_ha,
            sobreposicao_car_info, descricao, cor_hex, arquivo_origem, geometry
        ) VALUES (
            %(fase)s, %(titulo_fase)s, %(ordem_cronologica)s, %(data_averbacao)s, %(nome_imovel)s,
            %(codigo_imo)s, %(matricula_cartorio)s, %(num_area)s, %(perimetro_m)s, %(variacao_area_ha)s,
            %(variacao_descricao)s, %(proprietaria)s, %(responsavel_tecnico)s, %(art)s, %(parcela_codigo)s,
            %(situacao)s, %(municipio)s, %(uf)s, %(conflito_judicial)s, %(sobreposicao_car_ha)s,
            %(sobreposicao_car_info)s, %(descricao)s, %(cor_hex)s, %(arquivo_origem)s,
            ST_Force2D(ST_SetSRID(ST_GeomFromText(%(wkt)s), 4326))
        );
    """

    for p in kml_phases:
        wkt_str = p["polygon"].wkt
        params = {
            "fase": p["fase"],
            "titulo_fase": p["titulo_fase"],
            "ordem_cronologica": p["ordem_cronologica"],
            "data_averbacao": p["data_averbacao"],
            "nome_imovel": p["nome_imovel"],
            "codigo_imo": p["codigo_imo"],
            "matricula_cartorio": p["matricula_cartorio"],
            "num_area": p["num_area"],
            "perimetro_m": p["perimetro_m"],
            "variacao_area_ha": p["variacao_area_ha"],
            "variacao_descricao": p["variacao_descricao"],
            "proprietaria": p["proprietaria"],
            "responsavel_tecnico": p["responsavel_tecnico"],
            "art": p["art"],
            "parcela_codigo": p["parcela_codigo"],
            "situacao": p["situacao"],
            "municipio": p["municipio"],
            "uf": p["uf"],
            "conflito_judicial": p["conflito_judicial"],
            "sobreposicao_car_ha": p["sobreposicao_car_ha"],
            "sobreposicao_car_info": p["sobreposicao_car_info"],
            "descricao": p["descricao"],
            "cor_hex": p["cor_hex"],
            "arquivo_origem": p["arquivo_origem"],
            "wkt": wkt_str
        }
        cur.execute(insert_sql, params)
        print(f"Inserted phase: {p['fase']} ({p['data_averbacao']}) - {p['num_area']:.2f} ha [{p['proprietaria']}]")

    # Spatial GIST Index
    cur.execute("CREATE INDEX sigef_casos_analisados_geom_gist ON public.sigef_casos_analisados USING gist (geometry);")
    cur.execute("CREATE INDEX sigef_casos_analisados_codigo_imo_idx ON public.sigef_casos_analisados (codigo_imo);")

    cur.execute("SELECT count(*) FROM public.sigef_casos_analisados;")
    cnt = cur.fetchone()[0]
    print(f"\nSUCCESS: Table public.sigef_casos_analisados populated with {cnt} historical records.")

    # Import CAR analyzed properties (Batateiras 7 smallholder parcels)
    import_car_casos_analisados(cur)

    cur.close()
    conn.close()


def import_car_casos_analisados(cur):
    print("\n" + "=" * 70)
    print("IMPORTING BATATEIRAS CAR ANALYZED PROPERTIES")
    print("=" * 70)

    cur.execute("DROP TABLE IF EXISTS public.car_casos_analisados CASCADE;")
    cur.execute("""
        CREATE TABLE public.car_casos_analisados (
            cod_imovel text NOT NULL,
            nome_imovel text,
            declarante text,
            cpf_declarante text,
            codigo_protocolo text,
            data_cadastro text,
            origem_documento text,
            num_area double precision,
            mod_fiscal double precision,
            ind_status text,
            ind_tipo text,
            des_condic text,
            municipio text,
            cod_estado text,
            sobreposicao_sigef text,
            matricula_cartorio text,
            conflito_judicial text,
            geometry public.geometry(Geometry,4326)
        );
    """)

    car_data = [
        ("PE-2609204-791D8AA9F2B14CD5A5BC5F051A4AEA63", "Sítio Flora Clara", "José Manoel da Silva", "***.584.094-**", "2609204.437149.791D8AA9F2B14CD5A5BC5F051A4AEA63", "28/11/2017", "CAR José Manoel.pdf", 20.8694, 1.3043, "AT", "IRU", "Aguardando análise", "Maraial", "PE", "FAZENDA 2 IRMÃOS (INCRA 9510994953100) - Matrícula 73", "Posse Histórica / Matrícula 73", "TJPE Maraial 0000263-83.2026.8.17.2940 (Reintegração de Posse)"),
        ("PE-2609204-691BBA8767C14AAFB43E205CEDBA4E43", "Sítio Batateiras", "Cícera Maria da Conceição / Francisco Zeferino", "***.793.184-**", "2609204.436952.691BBA8767C14AAFB43E205CEDBA4E43", "28/11/2017", "CAR Francisco Zeferino.pdf", 19.9698, 1.2481, "AT", "IRU", "Aguardando análise", "Maraial", "PE", "FAZENDA 2 IRMÃOS (INCRA 9510994953100) - Matrícula 73", "Posse Histórica / Matrícula 73", "TJPE Maraial 0000263-83.2026.8.17.2940 (Reintegração de Posse)"),
        ("PE-2609204-F2B44463BC594543B17A9ABA928157F9", "Sítio Batateira", "Odílio Severino Nogueira", "***.080.494-**", "2609204.437135.F2B44463BC594543B17A9ABA928157F9", "28/11/2017", "CAR - Odílio.pdf", 21.301, 1.3313, "AT", "IRU", "Aguardando análise", "Maraial", "PE", "FAZENDA 2 IRMÃOS (INCRA 9510994953100) - Matrícula 73", "Posse Histórica / Matrícula 73", "TJPE Maraial 0000263-83.2026.8.17.2940 (Reintegração de Posse)"),
        ("PE-2609204-C26EA32D98EC43E3A35991D594FF27C2", "Sítio Saputi", "Joselito Nogueira", "***.080.304-**", "2609204.437145.C26EA32D98EC43E3A35991D594FF27C2", "28/11/2017", "CAR Joselito.pdf", 15.9493, 0.9968, "AT", "IRU", "Aguardando análise", "Maraial", "PE", "FAZENDA 2 IRMÃOS (INCRA 9510994953100) - Matrícula 73", "Posse Histórica / Matrícula 73", "TJPE Maraial 0000263-83.2026.8.17.2940 (Reintegração de Posse)"),
        ("PE-2609204-7B3D2CC5D90C406B968CB72C195793A8", "Sítio Riachão", "José Joaquim Antonio Wanderley / Severino Wanderley", "***.888.764-**", "2609204.437141.7B3D2CC5D90C406B968CB72C195793A8", "28/11/2017", "CAR Severino Wanderley.pdf", 28.8551, 1.8034, "AT", "IRU", "Aguardando análise", "Maraial", "PE", "FAZENDA 2 IRMÃOS (INCRA 9510994953100) - Matrícula 73", "Posse Histórica / Matrícula 73", "TJPE Maraial 0000263-83.2026.8.17.2940 (Reintegração de Posse)"),
        ("PE-2609204-F07F205EA4CE4657A77D0BDD2BE9B890", "Sítio Batateirinha", "Luiz Cândido da Silva / Kleiton", "***.361.344-**", "2609204.437153.F07F205EA4CE4657A77D0BDD2BE9B890", "28/11/2017", "CAR Kleiton.pdf", 20.457, 1.2785, "AT", "IRU", "Aguardando análise", "Maraial", "PE", "FAZENDA 2 IRMÃOS (INCRA 9510994953100) - Matrícula 73", "Posse Histórica / Matrícula 73", "TJPE Maraial 0000263-83.2026.8.17.2940 (Reintegração de Posse)"),
        ("PE-2609204-AFDF317B8B3B4F00B25E9F067BE40CD2", "Sítio Batateiras", "Edvania Maria Cordeiro da Silva / José Carlos Cordeiro da Silva", "***.407.494-**", "2609204.484214.AFDF317B8B3B4F00B25E9F067BE40CD2", "27/03/2018", "CAR - Sítio Batateiras (Março de 2018).pdf", 17.2185, 1.0761, "AT", "IRU", "Aguardando análise", "Maraial", "PE", "FAZENDA 2 IRMÃOS (INCRA 9510994953100) - Matrícula 73", "Posse Histórica / Matrícula 73", "TJPE Maraial 0000263-83.2026.8.17.2940 (Reintegração de Posse)")
    ]

    for item in car_data:
        cur.execute("""
            INSERT INTO public.car_casos_analisados (
                cod_imovel, nome_imovel, declarante, cpf_declarante, codigo_protocolo,
                data_cadastro, origem_documento, num_area, mod_fiscal, ind_status,
                ind_tipo, des_condic, municipio, cod_estado, sobreposicao_sigef,
                matricula_cartorio, conflito_judicial, geometry
            )
            SELECT %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, geometry
            FROM public.area_imovel_1
            WHERE cod_imovel = %s;
        """, (*item, item[0]))
        print(f"Inserted analyzed CAR: {item[1]} ({item[0]}) - {item[7]} ha [{item[2]}]")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_car_casos_analisados_geometry ON public.car_casos_analisados USING GIST (geometry);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_car_casos_analisados_cod ON public.car_casos_analisados (cod_imovel);")
    cur.execute("SELECT count(*) FROM public.car_casos_analisados;")
    cnt = cur.fetchone()[0]
    print(f"SUCCESS: Table public.car_casos_analisados populated with {cnt} records.")


if __name__ == "__main__":
    main()
