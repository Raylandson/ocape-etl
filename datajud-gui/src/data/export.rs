use std::fs::File;
use std::io::{BufWriter, Write};
use std::path::Path;

use serde::Serialize;

use crate::data::store::{Dataset, Lawsuit};
use crate::model::{format_date_iso, grau_label};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ExportFormat {
    Csv,
    Json,
}

impl ExportFormat {
    pub fn extension(self) -> &'static str {
        match self {
            Self::Csv => "csv",
            Self::Json => "json",
        }
    }

    pub fn filter_name(self) -> &'static str {
        match self {
            Self::Csv => "Planilha CSV",
            Self::Json => "Arquivo JSON",
        }
    }
}

#[derive(Debug, Serialize)]
pub struct ExportRow<'a> {
    pub id: &'a str,
    pub numero_processo: &'a str,
    pub tribunal: &'a str,
    pub grau: &'a str,
    pub grau_descricao: &'a str,
    pub data_ajuizamento: String,
    pub categoria_conflito: &'a str,
    pub classe_codigo: Option<i32>,
    pub classe_nome: &'a str,
    pub assuntos_str: String,
    pub orgao_julgador_codigo: Option<i32>,
    pub orgao_julgador_nome: &'a str,
    pub municipio_ibge: Option<i32>,
    pub municipio_nome: &'a str,
    pub comarca_sede_nome: &'a str,
    pub comarca_sede_ibge: Option<i32>,
    pub municipios_abrangidos: &'a str,
    pub tipo_jurisdicao: &'a str,
    pub ultimo_movimento: &'a str,
    pub data_ultimo_movimento: String,
    pub total_movimentos: u32,
    pub url_consulta_publica: &'a str,
    pub lat: Option<f32>,
    pub lon: Option<f32>,
}

impl<'a> ExportRow<'a> {
    pub fn new(ds: &'a Dataset, r: &'a Lawsuit) -> Self {
        let grau = ds.str(r.grau);
        Self {
            id: &r.id,
            numero_processo: &r.numero,
            tribunal: r.tribunal.code(),
            grau,
            grau_descricao: grau_label(grau),
            data_ajuizamento: format_date_iso(r.ajuizamento),
            categoria_conflito: r.categoria.label(),
            classe_codigo: r.classe_codigo,
            classe_nome: ds.str(r.classe),
            assuntos_str: assuntos_str(ds, r),
            orgao_julgador_codigo: r.orgao_codigo,
            orgao_julgador_nome: ds.str(r.orgao),
            municipio_ibge: r.municipio_ibge,
            municipio_nome: ds.str(r.municipio),
            comarca_sede_nome: ds.str(r.comarca_sede),
            comarca_sede_ibge: r.comarca_sede_ibge,
            municipios_abrangidos: ds.str(r.municipios_abrangidos),
            tipo_jurisdicao: ds.str(r.tipo_jurisdicao),
            ultimo_movimento: ds.str(r.ultimo_mov),
            data_ultimo_movimento: format_date_iso(r.ultimo_mov_data),
            total_movimentos: r.total_mov,
            url_consulta_publica: ds.str(r.url),
            lat: r.lat,
            lon: r.lon,
        }
    }
}

pub fn assuntos_str(ds: &Dataset, r: &Lawsuit) -> String {
    r.assuntos
        .iter()
        .map(|&(code, name)| match (code, ds.str(name)) {
            (0, n) => n.to_string(),
            (c, "") => c.to_string(),
            (c, n) => format!("{c}: {n}"),
        })
        .collect::<Vec<_>>()
        .join("; ")
}

pub fn row_json(ds: &Dataset, row: u32) -> String {
    serde_json::to_string_pretty(&ExportRow::new(ds, &ds.rows[row as usize])).unwrap_or_default()
}

pub fn write(
    ds: &Dataset,
    rows: &[u32],
    format: ExportFormat,
    path: &Path,
) -> Result<usize, String> {
    let file = File::create(path).map_err(|e| format!("Não foi possível criar o arquivo: {e}"))?;
    let mut out = BufWriter::new(file);
    let iter = rows
        .iter()
        .map(|&i| ExportRow::new(ds, &ds.rows[i as usize]));

    match format {
        ExportFormat::Csv => {
            let mut writer = csv::Writer::from_writer(&mut out);
            for row in iter {
                writer
                    .serialize(row)
                    .map_err(|e| format!("Erro ao gravar CSV: {e}"))?;
            }
            writer
                .flush()
                .map_err(|e| format!("Erro ao gravar CSV: {e}"))?;
        }
        ExportFormat::Json => {
            let all: Vec<ExportRow> = iter.collect();
            serde_json::to_writer_pretty(&mut out, &all)
                .map_err(|e| format!("Erro ao gravar JSON: {e}"))?;
        }
    }
    out.flush()
        .map_err(|e| format!("Erro ao gravar arquivo: {e}"))?;
    Ok(rows.len())
}
