use std::collections::HashMap;
use std::time::{Duration, Instant};

use rusqlite::Connection;

use crate::data::source::{self, Source};
use crate::model::{ConflictCategory, Tribunal, fold, parse_date};

pub const SUPPORTED_SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Default)]
pub struct Sym(pub u32);

impl Sym {
    pub const EMPTY: Sym = Sym(0);

    pub fn index(self) -> usize {
        self.0 as usize
    }
}

pub struct Interner {
    strings: Vec<Box<str>>,
    folded: Vec<Box<str>>,
    index: HashMap<Box<str>, Sym>,
}

impl Default for Interner {
    fn default() -> Self {
        let mut interner = Self {
            strings: Vec::new(),
            folded: Vec::new(),
            index: HashMap::new(),
        };
        interner.intern("");
        interner
    }
}

impl Interner {
    pub fn intern(&mut self, value: &str) -> Sym {
        let value = value.trim();
        if let Some(&sym) = self.index.get(value) {
            return sym;
        }
        let sym = Sym(self.strings.len() as u32);
        self.strings.push(value.into());
        self.folded.push(fold(value).into());
        self.index.insert(value.into(), sym);
        sym
    }

    pub fn get(&self, sym: Sym) -> &str {
        &self.strings[sym.index()]
    }

    pub fn len(&self) -> usize {
        self.strings.len()
    }

    pub fn folded(&self) -> &[Box<str>] {
        &self.folded
    }
}

#[derive(Debug, Clone)]
pub struct Lawsuit {
    pub id: Box<str>,
    pub numero: Box<str>,
    pub tribunal: Tribunal,
    pub grau: Sym,
    pub categoria: ConflictCategory,
    pub ajuizamento: Option<u32>,
    pub classe_codigo: Option<i32>,
    pub classe: Sym,
    pub assuntos: Box<[(i32, Sym)]>,
    pub orgao_codigo: Option<i32>,
    pub orgao: Sym,
    pub municipio_ibge: Option<i32>,
    pub municipio: Sym,
    pub comarca_sede: Sym,
    pub comarca_sede_ibge: Option<i32>,
    pub municipios_abrangidos: Sym,
    pub tipo_jurisdicao: Sym,
    pub ultimo_mov: Sym,
    pub ultimo_mov_data: Option<u32>,
    pub total_mov: u32,
    pub url: Sym,
    pub lat: Option<f32>,
    pub lon: Option<f32>,
}

#[derive(Debug, Clone, Default)]
pub struct SnapshotMeta {
    pub generated_at: Option<String>,
    pub source_table: Option<String>,
}

pub struct Dataset {
    pub rows: Vec<Lawsuit>,
    pub strings: Interner,
    pub meta: SnapshotMeta,
    pub source: Source,
    pub siblings: HashMap<Box<str>, Vec<u32>>,
    pub year_range: (u16, u16),
    pub graus: Vec<Sym>,
    pub municipios: Vec<Sym>,
    pub classes: Vec<Sym>,
    pub load_time: Duration,
}

impl Dataset {
    pub fn str(&self, sym: Sym) -> &str {
        self.strings.get(sym)
    }

    pub fn siblings_of(&self, row: u32) -> impl Iterator<Item = u32> + '_ {
        self.siblings
            .get(&self.rows[row as usize].numero)
            .into_iter()
            .flatten()
            .copied()
            .filter(move |&r| r != row)
    }
}

const SELECT_SQL: &str = "SELECT id, numero_processo, tribunal, grau, data_ajuizamento, categoria_conflito, \
    classe_codigo, classe_nome, assuntos_codigos, assuntos_nomes, orgao_julgador_codigo, orgao_julgador_nome, \
    municipio_ibge, municipio_nome, ultimo_movimento, data_ultimo_movimento, total_movimentos, url_consulta_publica, \
    comarca_sede_nome, comarca_sede_ibge, municipios_abrangidos, tipo_jurisdicao, lat, lon FROM lawsuits";

fn read_meta(conn: &Connection) -> Result<SnapshotMeta, String> {
    let mut stmt = conn
        .prepare("SELECT key, value FROM meta")
        .map_err(|e| format!("Arquivo não é uma base DataJud válida (tabela meta ausente): {e}"))?;
    let pairs: HashMap<String, String> = stmt
        .query_map([], |r| Ok((r.get::<_, String>(0)?, r.get::<_, String>(1)?)))
        .map_err(|e| e.to_string())?
        .filter_map(Result::ok)
        .collect();

    let version: u32 = pairs
        .get("schema_version")
        .and_then(|v| v.parse().ok())
        .unwrap_or(0);
    if version != SUPPORTED_SCHEMA_VERSION {
        return Err(format!(
            "Versão de esquema não suportada ({version}); esperado {SUPPORTED_SCHEMA_VERSION}. \
             Gere a base novamente com src/export_datajud_sqlite.py."
        ));
    }

    Ok(SnapshotMeta {
        generated_at: pairs.get("generated_at").cloned(),
        source_table: pairs.get("source_table").cloned(),
    })
}

fn parse_json_array<T: serde::de::DeserializeOwned>(raw: Option<String>) -> Vec<T> {
    raw.and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_default()
}

pub fn load(source: Source) -> Result<Dataset, String> {
    let started = Instant::now();
    let conn = source::open(&source)?;
    let meta = read_meta(&conn)?;

    let mut strings = Interner::default();
    let mut rows: Vec<Lawsuit> = Vec::with_capacity(100_000);

    let mut stmt = conn.prepare(SELECT_SQL).map_err(|e| e.to_string())?;
    let mut cursor = stmt.query([]).map_err(|e| e.to_string())?;

    while let Some(r) = cursor.next().map_err(|e| e.to_string())? {
        let get_str = |i: usize| -> String {
            r.get::<_, Option<String>>(i)
                .ok()
                .flatten()
                .unwrap_or_default()
        };
        let get_int = |i: usize| -> Option<i32> {
            r.get::<_, Option<i64>>(i).ok().flatten().map(|v| v as i32)
        };
        let get_f32 = |i: usize| -> Option<f32> {
            r.get::<_, Option<f64>>(i).ok().flatten().map(|v| v as f32)
        };

        let Some(tribunal) = Tribunal::from_db(&get_str(2)) else {
            continue;
        };

        let codes: Vec<i64> = parse_json_array(r.get(8).ok().flatten());
        let names: Vec<String> = parse_json_array(r.get(9).ok().flatten());
        let assuntos: Box<[(i32, Sym)]> = (0..codes.len().max(names.len()))
            .map(|i| {
                let code = codes.get(i).copied().unwrap_or(0) as i32;
                let name = names
                    .get(i)
                    .map(|n| strings.intern(n))
                    .unwrap_or(Sym::EMPTY);
                (code, name)
            })
            .collect();

        rows.push(Lawsuit {
            id: get_str(0).into(),
            numero: get_str(1).into(),
            tribunal,
            grau: strings.intern(&get_str(3)),
            ajuizamento: parse_date(&get_str(4)),
            categoria: ConflictCategory::from_db(&get_str(5)),
            classe_codigo: get_int(6),
            classe: strings.intern(&get_str(7)),
            assuntos,
            orgao_codigo: get_int(10),
            orgao: strings.intern(&get_str(11)),
            municipio_ibge: get_int(12),
            municipio: strings.intern(&get_str(13)),
            ultimo_mov: strings.intern(&get_str(14)),
            ultimo_mov_data: parse_date(&get_str(15)),
            total_mov: get_int(16).unwrap_or(0).max(0) as u32,
            url: strings.intern(&get_str(17)),
            comarca_sede: strings.intern(&get_str(18)),
            comarca_sede_ibge: get_int(19),
            municipios_abrangidos: strings.intern(&get_str(20)),
            tipo_jurisdicao: strings.intern(&get_str(21)),
            lat: get_f32(22),
            lon: get_f32(23),
        });
    }

    if rows.is_empty() {
        return Err("A base não contém processos.".to_string());
    }
    rows.shrink_to_fit();

    let mut dataset = finalize(rows, strings, meta, source);
    dataset.load_time = started.elapsed();
    Ok(dataset)
}

fn distinct(rows: &[Lawsuit], key: impl Fn(&Lawsuit) -> Sym) -> Vec<Sym> {
    let mut values: Vec<Sym> = rows.iter().map(key).collect();
    values.sort_unstable();
    values.dedup();
    values.retain(|&s| s != Sym::EMPTY);
    values
}

fn finalize(rows: Vec<Lawsuit>, strings: Interner, meta: SnapshotMeta, source: Source) -> Dataset {
    let mut siblings: HashMap<Box<str>, Vec<u32>> = HashMap::new();
    for (i, row) in rows.iter().enumerate() {
        siblings
            .entry(row.numero.clone())
            .or_default()
            .push(i as u32);
    }
    siblings.retain(|_, v| v.len() > 1);

    let years = rows
        .iter()
        .filter_map(|r| r.ajuizamento)
        .map(crate::model::date_year);
    let (lo, hi) = years.fold((u16::MAX, 0), |(lo, hi), y| (lo.min(y), hi.max(y)));
    let year_range = if lo > hi { (0, 0) } else { (lo, hi) };

    Dataset {
        graus: distinct(&rows, |r| r.grau),
        municipios: distinct(&rows, |r| r.municipio),
        classes: distinct(&rows, |r| r.classe),
        rows,
        strings,
        meta,
        source,
        siblings,
        year_range,
        load_time: Duration::ZERO,
    }
}

#[cfg(test)]
pub mod test_support {
    use super::*;

    pub struct Builder {
        pub rows: Vec<Lawsuit>,
        pub strings: Interner,
    }

    impl Builder {
        pub fn new() -> Self {
            Self {
                rows: Vec::new(),
                strings: Interner::default(),
            }
        }

        #[allow(clippy::too_many_arguments)]
        pub fn add(
            &mut self,
            numero: &str,
            tribunal: Tribunal,
            grau: &str,
            categoria: ConflictCategory,
            date: &str,
            classe: &str,
            municipio: &str,
            assunto: &str,
        ) -> &mut Self {
            let s = &mut self.strings;
            self.rows.push(Lawsuit {
                id: format!("{}_{}", numero, self.rows.len()).into(),
                numero: numero.into(),
                tribunal,
                grau: s.intern(grau),
                categoria,
                ajuizamento: parse_date(date),
                classe_codigo: None,
                classe: s.intern(classe),
                assuntos: vec![(1, s.intern(assunto))].into(),
                orgao_codigo: None,
                orgao: s.intern("VARA ÚNICA"),
                municipio_ibge: None,
                municipio: s.intern(municipio),
                comarca_sede: s.intern(municipio),
                comarca_sede_ibge: None,
                municipios_abrangidos: Sym::EMPTY,
                tipo_jurisdicao: Sym::EMPTY,
                ultimo_mov: Sym::EMPTY,
                ultimo_mov_data: None,
                total_mov: 0,
                url: Sym::EMPTY,
                lat: None,
                lon: None,
            });
            self
        }

        pub fn build(self) -> Dataset {
            finalize(
                self.rows,
                self.strings,
                SnapshotMeta::default(),
                Source::Embedded,
            )
        }
    }
}
