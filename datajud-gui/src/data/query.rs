use std::cmp::Ordering;
use std::collections::{BTreeSet, HashSet};
use std::time::{Duration, Instant};

use serde::{Deserialize, Serialize};

use crate::data::store::{Dataset, Lawsuit, Sym};
use crate::model::{ConflictCategory, Tribunal, date_year, fold};

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default)]
pub struct Filters {
    pub text: String,
    pub tribunais: BTreeSet<Tribunal>,
    pub categorias: BTreeSet<ConflictCategory>,
    pub graus: BTreeSet<String>,
    pub municipios: BTreeSet<String>,
    pub classes: BTreeSet<String>,
    pub ano_min: Option<u16>,
    pub ano_max: Option<u16>,
}

impl Filters {
    pub fn is_active(&self) -> bool {
        *self != Filters::default()
    }

    pub fn facet_active(&self, facet: Facet) -> bool {
        match facet {
            Facet::Tribunal => !self.tribunais.is_empty(),
            Facet::Categoria => !self.categorias.is_empty(),
            Facet::Grau => !self.graus.is_empty(),
            Facet::Ano => self.ano_min.is_some() || self.ano_max.is_some(),
            Facet::Municipio => !self.municipios.is_empty(),
            Facet::Classe => !self.classes.is_empty(),
        }
    }

    pub fn clear_facet(&mut self, facet: Facet) {
        match facet {
            Facet::Tribunal => self.tribunais.clear(),
            Facet::Categoria => self.categorias.clear(),
            Facet::Grau => self.graus.clear(),
            Facet::Ano => {
                self.ano_min = None;
                self.ano_max = None;
            }
            Facet::Municipio => self.municipios.clear(),
            Facet::Classe => self.classes.clear(),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Facet {
    Tribunal,
    Categoria,
    Grau,
    Ano,
    Municipio,
    Classe,
}

impl Facet {
    fn bit(self) -> u8 {
        1 << (self as u8)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
pub enum SortColumn {
    Numero,
    Tribunal,
    Categoria,
    Classe,
    Municipio,
    #[default]
    Ajuizamento,
    UltimoMovimento,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct Sort {
    pub column: SortColumn,
    pub descending: bool,
}

impl Default for Sort {
    fn default() -> Self {
        Self {
            column: SortColumn::Ajuizamento,
            descending: true,
        }
    }
}

impl Sort {
    pub fn toggled(self, column: SortColumn) -> Self {
        if self.column == column {
            Self {
                column,
                descending: !self.descending,
            }
        } else {
            let descending = matches!(
                column,
                SortColumn::Ajuizamento | SortColumn::UltimoMovimento
            );
            Self { column, descending }
        }
    }
}

#[derive(Debug, Clone, Default)]
pub struct FacetCounts {
    pub tribunal: [u32; Tribunal::ALL.len()],
    pub categoria: [u32; ConflictCategory::ALL.len()],
    pub grau: Vec<u32>,
    pub municipio: Vec<u32>,
    pub classe: Vec<u32>,
    pub ano: Vec<u32>,
}

#[derive(Debug, Clone, Default)]
pub struct QueryResult {
    pub visible: Vec<u32>,
    pub counts: FacetCounts,
    pub elapsed: Duration,
}

struct Token {
    raw: String,
    digits: Option<String>,
    number: Option<i32>,
    sym_match: Vec<bool>,
}

fn tokenize(dataset: &Dataset, text: &str) -> Vec<Token> {
    fold(text)
        .split_whitespace()
        .map(|raw| {
            let is_numeric = raw
                .chars()
                .all(|c| c.is_ascii_digit() || c == '-' || c == '.')
                && raw.chars().any(|c| c.is_ascii_digit());
            let digits =
                is_numeric.then(|| raw.chars().filter(char::is_ascii_digit).collect::<String>());
            let number = digits.as_ref().and_then(|d| d.parse().ok());
            let sym_match = dataset
                .strings
                .folded()
                .iter()
                .map(|s| s.contains(raw))
                .collect();
            Token {
                raw: raw.to_string(),
                digits,
                number,
                sym_match,
            }
        })
        .collect()
}

fn digits_contain(haystack: &str, needle: &str) -> bool {
    let mut buf = [0u8; 32];
    let mut len = 0;
    for b in haystack.bytes().filter(u8::is_ascii_digit) {
        if len == buf.len() {
            break;
        }
        buf[len] = b;
        len += 1;
    }
    let needle = needle.as_bytes();
    needle.len() <= len && buf[..len].windows(needle.len()).any(|w| w == needle)
}

fn row_matches_token(row: &Lawsuit, tok: &Token) -> bool {
    let m = &tok.sym_match;
    let hit = |s: Sym| m[s.index()];
    if hit(row.classe)
        || hit(row.orgao)
        || hit(row.municipio)
        || hit(row.comarca_sede)
        || hit(row.municipios_abrangidos)
        || row.assuntos.iter().any(|&(_, s)| hit(s))
        || row.numero.contains(tok.raw.as_str())
    {
        return true;
    }
    if let Some(n) = tok.number
        && (row.classe_codigo == Some(n) || row.assuntos.iter().any(|&(c, _)| c == n))
    {
        return true;
    }
    tok.digits
        .as_deref()
        .is_some_and(|d| d.len() >= 4 && digits_contain(&row.numero, d))
}

fn resolve_syms(dataset: &Dataset, values: &BTreeSet<String>) -> HashSet<Sym> {
    let wanted: HashSet<&str> = values.iter().map(String::as_str).collect();
    (0..dataset.strings.len() as u32)
        .map(Sym)
        .filter(|&s| wanted.contains(dataset.str(s)))
        .collect()
}

pub fn compute(dataset: &Dataset, filters: &Filters, sort: Sort) -> QueryResult {
    let started = Instant::now();
    let tokens = tokenize(dataset, &filters.text);
    let graus = resolve_syms(dataset, &filters.graus);
    let municipios = resolve_syms(dataset, &filters.municipios);
    let classes = resolve_syms(dataset, &filters.classes);
    let (year_lo, year_hi) = dataset.year_range;

    let n_syms = dataset.strings.len();
    let mut counts = FacetCounts {
        grau: vec![0; n_syms],
        municipio: vec![0; n_syms],
        classe: vec![0; n_syms],
        ano: vec![0; (year_hi.saturating_sub(year_lo) as usize) + 1],
        ..Default::default()
    };
    let mut visible = Vec::with_capacity(dataset.rows.len());

    for (idx, row) in dataset.rows.iter().enumerate() {
        if !tokens.iter().all(|t| row_matches_token(row, t)) {
            continue;
        }

        let year = row.ajuizamento.map(date_year);
        let mut failed = 0u8;
        if !filters.tribunais.is_empty() && !filters.tribunais.contains(&row.tribunal) {
            failed |= Facet::Tribunal.bit();
        }
        if !filters.categorias.is_empty() && !filters.categorias.contains(&row.categoria) {
            failed |= Facet::Categoria.bit();
        }
        if !graus.is_empty() && !graus.contains(&row.grau) {
            failed |= Facet::Grau.bit();
        }
        let year_ok = match year {
            Some(y) => {
                filters.ano_min.is_none_or(|lo| y >= lo) && filters.ano_max.is_none_or(|hi| y <= hi)
            }
            None => filters.ano_min.is_none() && filters.ano_max.is_none(),
        };
        if !year_ok {
            failed |= Facet::Ano.bit();
        }
        if !municipios.is_empty() && !municipios.contains(&row.municipio) {
            failed |= Facet::Municipio.bit();
        }
        if !classes.is_empty() && !classes.contains(&row.classe) {
            failed |= Facet::Classe.bit();
        }

        if failed.count_ones() > 1 {
            continue;
        }
        let counts_for = |f: Facet| failed == 0 || failed == f.bit();

        if counts_for(Facet::Tribunal) {
            counts.tribunal[row.tribunal as usize] += 1;
        }
        if counts_for(Facet::Categoria) {
            counts.categoria[row.categoria as usize] += 1;
        }
        if counts_for(Facet::Grau) {
            counts.grau[row.grau.index()] += 1;
        }
        if counts_for(Facet::Ano)
            && let Some(y) = year
            && y >= year_lo
            && let Some(c) = counts.ano.get_mut((y - year_lo) as usize)
        {
            *c += 1;
        }
        if counts_for(Facet::Municipio) {
            counts.municipio[row.municipio.index()] += 1;
        }
        if counts_for(Facet::Classe) {
            counts.classe[row.classe.index()] += 1;
        }
        if failed == 0 {
            visible.push(idx as u32);
        }
    }
    sort_rows(dataset, &mut visible, sort);

    QueryResult {
        visible,
        counts,
        elapsed: started.elapsed(),
    }
}

pub fn sym_ranks(dataset: &Dataset) -> Vec<u32> {
    let folded = dataset.strings.folded();
    let mut order: Vec<u32> = (0..folded.len() as u32).collect();
    order.sort_by(|&a, &b| folded[a as usize].cmp(&folded[b as usize]));
    let mut ranks = vec![0u32; folded.len()];
    for (rank, sym) in order.into_iter().enumerate() {
        ranks[sym as usize] = rank as u32;
    }
    ranks
}

type RowCmp = Box<dyn Fn(&Lawsuit, &Lawsuit) -> Ordering>;

pub fn sort_rows(dataset: &Dataset, visible: &mut [u32], sort: Sort) {
    let rows = &dataset.rows;
    let cmp_primary: RowCmp = match sort.column {
        SortColumn::Numero => Box::new(|a, b| a.numero.cmp(&b.numero)),
        SortColumn::Tribunal => {
            let ranks = sym_ranks(dataset);
            Box::new(move |a, b| {
                (a.tribunal, ranks[a.grau.index()]).cmp(&(b.tribunal, ranks[b.grau.index()]))
            })
        }
        SortColumn::Categoria => Box::new(|a, b| a.categoria.cmp(&b.categoria)),
        SortColumn::Classe => {
            let ranks = sym_ranks(dataset);
            Box::new(move |a, b| ranks[a.classe.index()].cmp(&ranks[b.classe.index()]))
        }
        SortColumn::Municipio => {
            let ranks = sym_ranks(dataset);
            Box::new(move |a, b| ranks[a.municipio.index()].cmp(&ranks[b.municipio.index()]))
        }
        SortColumn::Ajuizamento => Box::new(|a, b| a.ajuizamento.cmp(&b.ajuizamento)),
        SortColumn::UltimoMovimento => Box::new(|a, b| a.ultimo_mov_data.cmp(&b.ultimo_mov_data)),
    };

    visible.sort_unstable_by(|&a, &b| {
        let primary = cmp_primary(&rows[a as usize], &rows[b as usize]);
        let primary = if sort.descending {
            primary.reverse()
        } else {
            primary
        };
        primary.then(a.cmp(&b))
    });
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::data::store::test_support::Builder;
    use ConflictCategory::*;
    use Tribunal::*;

    fn sample() -> Dataset {
        let mut b = Builder::new();
        b.add(
            "0000199-33.2026.8.17.3600",
            Tjpe,
            "G1",
            ReintegracaoPosse,
            "2026-06-04",
            "Reintegração de Posse",
            "Recife",
            "Esbulho / Turbação / Ameaça",
        )
        .add(
            "0000199-33.2026.8.17.3600",
            Tjpe,
            "G2",
            ReintegracaoPosse,
            "2026-07-01",
            "Apelação Cível",
            "Recife",
            "Esbulho / Turbação / Ameaça",
        )
        .add(
            "0800001-10.2020.4.05.8300",
            Trf5,
            "G1",
            Usucapiao,
            "2020-01-15",
            "Usucapião",
            "Petrolina",
            "Usucapião Extraordinária",
        )
        .add(
            "0000001-02.2007.8.17.1550",
            Tjpe,
            "G1",
            Outros,
            "2007-11-27",
            "Procedimento Comum",
            "Venturosa",
            "Propriedade",
        )
        .add(
            "0000500-00.2015.8.17.0001",
            Tjpe,
            "JE",
            Usucapiao,
            "2015-05-05",
            "Usucapião",
            "Recife",
            "Usucapião Especial",
        );
        b.build()
    }

    fn run(ds: &Dataset, f: &Filters) -> Vec<u32> {
        compute(
            ds,
            f,
            Sort {
                column: SortColumn::Numero,
                descending: false,
            },
        )
        .visible
    }

    #[test]
    fn empty_filters_show_everything() {
        let ds = sample();
        assert_eq!(run(&ds, &Filters::default()).len(), 5);
    }

    #[test]
    fn outros_category_is_filterable() {
        let ds = sample();
        let f = Filters {
            categorias: [Outros].into(),
            ..Default::default()
        };
        assert_eq!(run(&ds, &f), vec![3]);
    }

    #[test]
    fn disjunctive_facet_counts() {
        let ds = sample();
        let f = Filters {
            categorias: [Usucapiao].into(),
            tribunais: [Tjpe].into(),
            ..Default::default()
        };
        let r = compute(&ds, &f, Sort::default());
        assert_eq!(r.visible, vec![4]);
        assert_eq!(r.counts.categoria[ReintegracaoPosse as usize], 2);
        assert_eq!(r.counts.categoria[Usucapiao as usize], 1);
        assert_eq!(r.counts.categoria[Outros as usize], 1);
        assert_eq!(r.counts.tribunal[Tjpe as usize], 1);
        assert_eq!(r.counts.tribunal[Trf5 as usize], 1);
    }

    #[test]
    fn text_search_is_accent_insensitive_and_multi_token() {
        let ds = sample();
        let f = Filters {
            text: "reintegracao".into(),
            ..Default::default()
        };
        assert_eq!(run(&ds, &f), vec![0]);
        let f = Filters {
            text: "USUCAPIAO recife".into(),
            ..Default::default()
        };
        assert_eq!(run(&ds, &f), vec![4]);
    }

    #[test]
    fn cnj_number_matches_masked_and_unmasked() {
        let ds = sample();
        for q in ["0000199-33.2026", "00001993320268173600", "0800001"] {
            let f = Filters {
                text: q.into(),
                ..Default::default()
            };
            assert!(!run(&ds, &f).is_empty(), "query {q}");
        }
        let f = Filters {
            text: "00001993320268173600".into(),
            ..Default::default()
        };
        assert_eq!(run(&ds, &f), vec![0, 1]);
    }

    #[test]
    fn year_range_and_string_facets() {
        let ds = sample();
        let f = Filters {
            ano_min: Some(2015),
            ano_max: Some(2020),
            ..Default::default()
        };
        let mut v = run(&ds, &f);
        v.sort();
        assert_eq!(v, vec![2, 4]);
        let f = Filters {
            municipios: ["Recife".to_string()].into(),
            graus: ["G1".to_string()].into(),
            ..Default::default()
        };
        assert_eq!(run(&ds, &f), vec![0]);
    }

    #[test]
    fn sort_is_stable_and_reversible() {
        let ds = sample();
        let asc = compute(
            &ds,
            &Filters::default(),
            Sort {
                column: SortColumn::Ajuizamento,
                descending: false,
            },
        )
        .visible;
        assert_eq!(asc, vec![3, 4, 2, 0, 1]);
        let by_mun = compute(
            &ds,
            &Filters::default(),
            Sort {
                column: SortColumn::Municipio,
                descending: false,
            },
        )
        .visible;
        assert_eq!(by_mun, vec![2, 0, 1, 4, 3]);
    }

    #[test]
    #[ignore]
    fn real_snapshot_performance() {
        let src = crate::data::source::resolve().expect("snapshot not found");
        let ds = crate::data::store::load(src).expect("load");
        println!(
            "loaded {} rows, {} strings in {:?}",
            ds.rows.len(),
            ds.strings.len(),
            ds.load_time
        );
        let cases = [
            Filters::default(),
            Filters {
                text: "reintegracao recife".into(),
                ..Default::default()
            },
            Filters {
                text: "0000199-33.2026".into(),
                ..Default::default()
            },
            Filters {
                categorias: [Outros].into(),
                ano_min: Some(2020),
                ..Default::default()
            },
        ];
        for f in &cases {
            let r = compute(&ds, f, Sort::default());
            println!(
                "{:>7} rows in {:>8.2?}  ({:?})",
                r.visible.len(),
                r.elapsed,
                f.text
            );
            assert!(r.elapsed < Duration::from_millis(50));
        }
        let all = compute(&ds, &Filters::default(), Sort::default());
        assert_eq!(all.visible.len(), ds.rows.len());
        assert_eq!(all.counts.categoria[Outros as usize], 8205);
        for col in [
            SortColumn::Numero,
            SortColumn::Classe,
            SortColumn::Municipio,
            SortColumn::Tribunal,
        ] {
            let mut v = all.visible.clone();
            let t = Instant::now();
            sort_rows(
                &ds,
                &mut v,
                Sort {
                    column: col,
                    descending: false,
                },
            );
            println!("sort {col:?}: {:?}", t.elapsed());
        }
    }

    #[test]
    fn siblings_share_numero() {
        let ds = sample();
        assert_eq!(ds.siblings_of(0).collect::<Vec<_>>(), vec![1]);
        assert_eq!(ds.siblings_of(2).count(), 0);
    }
}
