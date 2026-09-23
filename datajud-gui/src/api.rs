use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::mpsc::Sender;
use std::sync::Arc;
use std::thread;
use std::time::Duration;

use reqwest::header::{HeaderMap, HeaderValue, AUTHORIZATION, CONTENT_TYPE};
use serde_json::{json, Value};

use crate::model::{classify_lawsuit, format_cnj_mask, ProcessRecord};

pub const DATAJUD_API_KEY: &str =
    "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw==";

#[derive(Debug, Clone)]
pub struct TribunalTarget {
    pub tribunal: String,
    pub wildcard: Option<String>,
}

#[derive(Debug, Clone)]
pub struct QueryFilter {
    pub targets: Vec<TribunalTarget>,
    pub assunto_codes: Vec<i64>,
    pub classe_codes: Vec<i64>,
    pub total_limit: usize,
}

#[derive(Debug)]
pub enum ApiMessage {
    Progress {
        tribunal: String,
        count: usize,
        page: usize,
        total_so_far: usize,
    },
    Records(Vec<ProcessRecord>),
    Finished { total: usize },
    Error(String),
}

struct TribunalCursor {
    tribunal: String,
    wildcard: Option<String>,
    search_after: Option<Vec<Value>>,
    page: usize,
    fetched: usize,
    exhausted: bool,
}

/// Executes a single page search query against DataJud for a specific court
fn fetch_single_page(
    client: &reqwest::blocking::Client,
    cursor: &TribunalCursor,
    assunto_codes: &[i64],
    classe_codes: &[i64],
    batch_size: usize,
    cancel_flag: &AtomicBool,
) -> Result<Value, String> {
    if cancel_flag.load(Ordering::Relaxed) {
        return Err("Cancelado pelo usuário".to_string());
    }

    let tribunal = &cursor.tribunal;
    let url = format!(
        "https://api-publica.datajud.cnj.jus.br/api_publica_{}/_search",
        tribunal.to_lowercase()
    );

    let mut should_clauses = Vec::new();
    if !assunto_codes.is_empty() {
        should_clauses.push(json!({
            "terms": { "assuntos.codigo": assunto_codes }
        }));
    }
    if !classe_codes.is_empty() {
        should_clauses.push(json!({
            "terms": { "classe.codigo": classe_codes }
        }));
    }

    let mut must_clauses = Vec::new();
    if let Some(ref w) = cursor.wildcard
        && !w.trim().is_empty() {
            must_clauses.push(json!({
                "wildcard": { "numeroProcesso": w.trim() }
            }));
        }

    let mut bool_query = json!({});
    if !must_clauses.is_empty() {
        bool_query["must"] = json!(must_clauses);
    }
    if !should_clauses.is_empty() {
        bool_query["should"] = json!(should_clauses);
        bool_query["minimum_should_match"] = json!(1);
    }

    let mut body = json!({
        "size": batch_size,
        "query": { "bool": bool_query },
        "sort": [
            { "dataAjuizamento": { "order": "desc" } },
            { "id.keyword": { "order": "asc" } }
        ]
    });

    if let Some(ref sa) = cursor.search_after {
        body["search_after"] = json!(sa);
    }

    let mut attempts = 0;
    let max_attempts = 2;
    let response = loop {
        attempts += 1;
        match client.post(&url).json(&body).send() {
            Ok(resp) => break resp,
            Err(err) => {
                if cancel_flag.load(Ordering::Relaxed) {
                    return Err("Cancelado pelo usuário".to_string());
                }
                if attempts < max_attempts {
                    thread::sleep(Duration::from_millis(1500));
                    continue;
                }
                return Err(format!("Erro de rede no tribunal '{tribunal}': {err}"));
            }
        }
    };

    if cancel_flag.load(Ordering::Relaxed) {
        return Err("Cancelado pelo usuário".to_string());
    }

    if !response.status().is_success() {
        let status = response.status();
        let text = response
            .text()
            .unwrap_or_else(|_| "sem mensagem de erro".to_string());
        return Err(format!(
            "API ({tribunal}) retornou status HTTP {status}: {text}"
        ));
    }

    response
        .json::<Value>()
        .map_err(|err| format!("Erro ao processar JSON ({tribunal}): {err}"))
}

pub fn spawn_fetch_worker(
    filter: QueryFilter,
    cancel_flag: Arc<AtomicBool>,
    sender: Sender<ApiMessage>,
) {
    thread::spawn(move || {
        let mut headers = HeaderMap::new();
        match HeaderValue::from_str(&format!("APIKey {}", DATAJUD_API_KEY)) {
            Ok(v) => {
                headers.insert(AUTHORIZATION, v);
            }
            Err(e) => {
                let _ = sender.send(ApiMessage::Error(format!("Invalid auth header: {e}")));
                return;
            }
        }
        headers.insert(CONTENT_TYPE, HeaderValue::from_static("application/json"));

        let client = match reqwest::blocking::Client::builder()
            .default_headers(headers)
            .timeout(Duration::from_secs(60))
            .build()
        {
            Ok(c) => c,
            Err(e) => {
                let _ = sender.send(ApiMessage::Error(format!("Client error: {e}")));
                return;
            }
        };

        // Initialize state cursors for all selected courts
        let mut cursors: Vec<TribunalCursor> = filter
            .targets
            .iter()
            .map(|t| TribunalCursor {
                tribunal: t.tribunal.trim().to_lowercase(),
                wildcard: t.wildcard.clone(),
                search_after: None,
                page: 0,
                fetched: 0,
                exhausted: false,
            })
            .collect();

        let grand_total = Arc::new(AtomicUsize::new(0));

        // Interleaved concurrent rounds across all active tribunals:
        // Round 1: 100 from TJPE, 100 from TRF5, etc., in parallel
        // Round 2: next 100 from TJPE, next 100 from TRF5, in parallel
        // Continues until total_limit is satisfied or all courts are exhausted
        while grand_total.load(Ordering::Relaxed) < filter.total_limit {
            if cancel_flag.load(Ordering::Relaxed) {
                break;
            }

            let any_active = cursors.iter().any(|c| !c.exhausted);
            if !any_active {
                break;
            }

            std::thread::scope(|scope| {
                for cursor in cursors.iter_mut().filter(|c| !c.exhausted) {
                    let client = &client;
                    let cancel_flag = cancel_flag.clone();
                    let grand_total = grand_total.clone();
                    let sender = sender.clone();
                    let assunto_codes = &filter.assunto_codes;
                    let classe_codes = &filter.classe_codes;
                    let total_limit = filter.total_limit;

                    scope.spawn(move || {
                        if cancel_flag.load(Ordering::Relaxed) {
                            return;
                        }

                        let current_grand = grand_total.load(Ordering::Relaxed);
                        if current_grand >= total_limit {
                            return;
                        }

                        let batch_size = 100.min(total_limit.saturating_sub(current_grand));
                        if batch_size == 0 {
                            return;
                        }

                        cursor.page += 1;
                        let page = cursor.page;
                        let tribunal_name = cursor.tribunal.clone();

                        match fetch_single_page(
                            client,
                            cursor,
                            assunto_codes,
                            classe_codes,
                            batch_size,
                            &cancel_flag,
                        ) {
                            Ok(json_val) => {
                                let hits = json_val["hits"]["hits"].as_array();
                                match hits {
                                    Some(records) if !records.is_empty() => {
                                        let mut batch = Vec::with_capacity(records.len());
                                        for hit in records {
                                            if grand_total.load(Ordering::Relaxed) >= total_limit
                                                || cancel_flag.load(Ordering::Relaxed)
                                            {
                                                break;
                                            }

                                            let src = &hit["_source"];
                                            let raw_num = src["numeroProcesso"]
                                                .as_str()
                                                .unwrap_or("")
                                                .trim();
                                            let numero_processo = format_cnj_mask(raw_num);

                                            let classe_codigo = src["classe"]["codigo"].as_i64();
                                            let classe_nome = src["classe"]["nome"]
                                                .as_str()
                                                .unwrap_or("")
                                                .trim()
                                                .to_string();

                                            let mut assuntos_codigos = Vec::new();
                                            let mut assuntos_nomes = Vec::new();

                                            if let Some(assuntos_arr) = src["assuntos"].as_array() {
                                                for ass in assuntos_arr {
                                                    if let Some(c) = ass["codigo"].as_i64() {
                                                        assuntos_codigos.push(c);
                                                    }
                                                    if let Some(n) = ass["nome"].as_str() {
                                                        assuntos_nomes.push(n.trim().to_string());
                                                    }
                                                }
                                            }

                                            let orgao_julgador = src["orgaoJulgador"]["nome"]
                                                .as_str()
                                                .unwrap_or("")
                                                .trim()
                                                .to_string();

                                            let municipio_ibge =
                                                src["orgaoJulgador"]["codigoMunicipioIBGE"].as_i64();

                                            let data_ajuizamento = src["dataAjuizamento"]
                                                .as_str()
                                                .unwrap_or("")
                                                .trim()
                                                .to_string();

                                            let grau =
                                                src["grau"].as_str().unwrap_or("").trim().to_string();

                                            let categoria = classify_lawsuit(
                                                &assuntos_codigos,
                                                classe_codigo,
                                                &assuntos_nomes,
                                                &classe_nome,
                                            );

                                            let raw_json =
                                                serde_json::to_string_pretty(src).unwrap_or_default();

                                            batch.push(ProcessRecord {
                                                numero_processo,
                                                classe_codigo,
                                                classe_nome,
                                                assuntos_codigos,
                                                assuntos_nomes,
                                                orgao_julgador,
                                                municipio_ibge,
                                                data_ajuizamento,
                                                grau,
                                                tribunal: tribunal_name.to_uppercase(),
                                                categoria,
                                                raw_json,
                                            });

                                            cursor.fetched += 1;
                                            grand_total.fetch_add(1, Ordering::Relaxed);
                                        }

                                        if let Some(last_hit) = records.last() {
                                            if let Some(sort_val) = last_hit["sort"].as_array() {
                                                cursor.search_after = Some(sort_val.clone());
                                            } else {
                                                cursor.exhausted = true;
                                            }
                                        } else {
                                            cursor.exhausted = true;
                                        }

                                        if !batch.is_empty() {
                                            let _ = sender.send(ApiMessage::Records(batch));
                                            let _ = sender.send(ApiMessage::Progress {
                                                tribunal: tribunal_name.to_uppercase(),
                                                count: cursor.fetched,
                                                page,
                                                total_so_far: grand_total.load(Ordering::Relaxed),
                                            });
                                        }
                                    }
                                    _ => {
                                        cursor.exhausted = true;
                                    }
                                }
                            }
                            Err(err) => {
                                if !cancel_flag.load(Ordering::Relaxed) && err != "Cancelado pelo usuário" {
                                    let _ = sender.send(ApiMessage::Error(err));
                                }
                                cursor.exhausted = true;
                            }
                        }
                    });
                }
            });
        }

        let _ = sender.send(ApiMessage::Finished {
            total: grand_total.load(Ordering::Relaxed),
        });
    });
}
