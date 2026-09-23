use std::collections::HashSet;
use std::fs::File;
use std::io::Write;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::mpsc::{channel, Receiver, Sender};
use std::sync::Arc;

use eframe::egui::{self, Color32, CornerRadius, Popup, PopupCloseBehavior, RichText, Stroke};

use crate::api::{spawn_fetch_worker, ApiMessage, QueryFilter, TribunalTarget};
use crate::model::{ConflictCategory, CsvExportRow, ProcessRecord};
use crate::theme::{
    render_cancel_button, render_category_badge, render_dropdown_filter_button,
    render_filter_item, render_search_button, render_tribunal_badge, COLOR_BG_CARD, COLOR_BORDER,
    COLOR_PRIMARY_BUTTON, COLOR_SUCCESS_BUTTON, COLOR_TEXT_MUTED, COLOR_TEXT_PRIMARY,
};

pub struct DataJudApp {
    // 1. DataJud API Query Settings (Pernambuco: TJPE + TRF5-JFPE)
    query_categories: HashSet<ConflictCategory>,
    query_assuntos: String,
    query_classes: String,
    query_wildcard: String,
    query_limit_unlimited: bool,
    query_limit: usize,
    accumulate_data: bool,

    // 2. Post-Fetch Table Filter Settings (Filters applied locally on downloaded data)
    filter_tribunals: HashSet<String>,
    filter_categories: HashSet<ConflictCategory>,
    filter_search_text: String,

    // 3. Client-Side Table Pagination
    page_size: usize,
    current_page: usize,

    // 4. Concurrency & State
    cancel_flag: Arc<AtomicBool>,
    is_fetching: bool,
    status_text: String,
    error_text: Option<String>,
    records: Vec<ProcessRecord>,
    selected_record: Option<ProcessRecord>,

    // Channel
    tx: Sender<ApiMessage>,
    rx: Receiver<ApiMessage>,
}

impl Default for DataJudApp {
    fn default() -> Self {
        let (tx, rx) = channel();

        let mut all_categories = HashSet::new();
        for cat in ConflictCategory::ALL {
            all_categories.insert(cat);
        }

        let mut app = Self {
            query_categories: all_categories.clone(),
            query_assuntos: String::new(),
            query_classes: String::new(),
            query_wildcard: String::new(),
            query_limit_unlimited: false,
            query_limit: 1000,
            accumulate_data: true,

            filter_tribunals: HashSet::from(["TJPE".to_string(), "TRF5".to_string()]),
            filter_categories: all_categories,
            filter_search_text: String::new(),

            page_size: 50,
            current_page: 0,

            cancel_flag: Arc::new(AtomicBool::new(false)),
            is_fetching: false,
            status_text: "Pronto para buscar. Configure os tribunais e clique em 'Iniciar Extração'.".to_string(),
            error_text: None,
            records: Vec::new(),
            selected_record: None,

            tx,
            rx,
        };

        app.sync_query_tpu_from_categories();
        app
    }
}

impl DataJudApp {
    /// Recalculates default TPU assunto and classe codes for the API query
    fn sync_query_tpu_from_categories(&mut self) {
        let mut assuntos = Vec::new();
        let mut classes = Vec::new();

        for cat in &self.query_categories {
            assuntos.extend_from_slice(cat.default_assunto_codes());
            classes.extend_from_slice(cat.default_classe_codes());
        }

        assuntos.sort_unstable();
        assuntos.dedup();
        classes.sort_unstable();
        classes.dedup();

        self.query_assuntos = assuntos
            .into_iter()
            .map(|c| c.to_string())
            .collect::<Vec<_>>()
            .join(", ");

        self.query_classes = classes
            .into_iter()
            .map(|c| c.to_string())
            .collect::<Vec<_>>()
            .join(", ");
    }

    /// Builds the list of tribunal targets to extract (Pernambuco: TJPE + TRF5-JFPE)
    fn build_tribunal_targets(&self) -> Vec<TribunalTarget> {
        let tjpe_wildcard = if self.query_wildcard.trim().is_empty() {
            None
        } else {
            Some(self.query_wildcard.trim().to_string())
        };

        vec![
            TribunalTarget {
                tribunal: "tjpe".to_string(),
                wildcard: tjpe_wildcard,
            },
            TribunalTarget {
                tribunal: "trf5".to_string(),
                wildcard: Some("*40583*".to_string()), // Pernambuco Federal Judicial Section (JFPE)
            },
        ]
    }

    fn start_search(&mut self) {
        let targets = self.build_tribunal_targets();
        if targets.is_empty() {
            self.error_text = Some("Selecione ao menos um tribunal para consultar.".to_string());
            return;
        }

        if !self.accumulate_data {
            self.records.clear();
            self.selected_record = None;
            self.current_page = 0;
        }

        self.error_text = None;
        self.is_fetching = true;

        let targets_names: Vec<String> = targets.iter().map(|t| t.tribunal.to_uppercase()).collect();
        self.status_text = format!(
            "Iniciando extração simultânea: {} (Limite: {})...",
            targets_names.join(", "),
            if self.query_limit_unlimited {
                "Sem limite".to_string()
            } else {
                format!("{} processos", self.query_limit)
            }
        );

        self.error_text = None;
        self.cancel_flag.store(false, Ordering::Relaxed);

        let assunto_codes = self
            .query_assuntos
            .split(',')
            .filter_map(|s| s.trim().parse::<i64>().ok())
            .collect();

        let classe_codes = self
            .query_classes
            .split(',')
            .filter_map(|s| s.trim().parse::<i64>().ok())
            .collect();

        let effective_limit = if self.query_limit_unlimited {
            usize::MAX
        } else {
            self.query_limit
        };

        let filter = QueryFilter {
            targets,
            assunto_codes,
            classe_codes,
            total_limit: effective_limit,
        };

        spawn_fetch_worker(filter, self.cancel_flag.clone(), self.tx.clone());
    }

    fn cancel_search(&mut self) {
        self.cancel_flag.store(true, Ordering::Relaxed);
        self.is_fetching = false;
        self.error_text = None;
        self.status_text = "Busca cancelada pelo usuário.".to_string();
    }

    fn clear_all_records(&mut self) {
        self.records.clear();
        self.selected_record = None;
        self.current_page = 0;
        self.filter_tribunals = HashSet::from(["TJPE".to_string(), "TRF5".to_string()]);
        self.status_text = "Base de processos limpa.".to_string();
    }

    /// Adds new records, deduplicating by process number
    fn append_records(&mut self, new_records: Vec<ProcessRecord>) {
        let was_empty = self.records.is_empty();
        let mut existing_numbers: HashSet<String> =
            self.records.iter().map(|r| r.numero_processo.clone()).collect();

        for rec in new_records {
            if !existing_numbers.contains(&rec.numero_processo) {
                existing_numbers.insert(rec.numero_processo.clone());
                if was_empty {
                    self.filter_tribunals.insert(rec.tribunal.to_uppercase());
                }
                self.records.push(rec);
            }
        }
    }

    /// Returns list of distinct tribunals currently present in the loaded dataset
    fn distinct_tribunals(&self) -> Vec<String> {
        let mut tribs: Vec<String> = self
            .records
            .iter()
            .map(|r| r.tribunal.to_uppercase())
            .collect::<HashSet<_>>()
            .into_iter()
            .collect();
        tribs.sort();
        tribs
    }

    fn export_csv(&mut self, records_to_export: &[ProcessRecord]) {
        if records_to_export.is_empty() {
            return;
        }

        let default_name = format!(
            "datajud_export_{}_processos.csv",
            records_to_export.len()
        );

        let file_path = rfd::FileDialog::new()
            .set_file_name(&default_name)
            .add_filter("Planilha CSV (*.csv)", &["csv"])
            .save_file();

        if let Some(path) = file_path {
            match File::create(&path) {
                Ok(file) => {
                    let mut writer = csv::Writer::from_writer(file);
                    let mut count = 0;
                    for rec in records_to_export {
                        let export_row = CsvExportRow::from(rec);
                        if writer.serialize(export_row).is_ok() {
                            count += 1;
                        }
                    }
                    let _ = writer.flush();
                    self.status_text =
                        format!("Exportados {} processos para CSV com sucesso.", count);
                }
                Err(err) => {
                    self.error_text = Some(format!("Erro ao criar arquivo CSV: {err}"));
                }
            }
        }
    }

    fn export_json(&mut self, records_to_export: &[ProcessRecord]) {
        if records_to_export.is_empty() {
            return;
        }

        let default_name = format!(
            "datajud_export_{}_processos.json",
            records_to_export.len()
        );

        let file_path = rfd::FileDialog::new()
            .set_file_name(&default_name)
            .add_filter("Arquivo JSON (*.json)", &["json"])
            .save_file();

        if let Some(path) = file_path {
            match File::create(&path) {
                Ok(mut file) => {
                    match serde_json::to_string_pretty(&records_to_export) {
                        Ok(json_str) => {
                            if file.write_all(json_str.as_bytes()).is_ok() {
                                self.status_text = format!(
                                    "Exportados {} processos para JSON com sucesso.",
                                    records_to_export.len()
                                );
                            } else {
                                self.error_text =
                                    Some("Erro ao gravar dados no arquivo JSON.".to_string());
                            }
                        }
                        Err(err) => {
                            self.error_text = Some(format!("Erro ao converter para JSON: {err}"));
                        }
                    }
                }
                Err(err) => {
                    self.error_text = Some(format!("Erro ao criar arquivo JSON: {err}"));
                }
            }
        }
    }
}

impl eframe::App for DataJudApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        // Poll incoming messages from API worker thread
        while let Ok(msg) = self.rx.try_recv() {
            match msg {
                ApiMessage::Progress {
                    tribunal,
                    count,
                    page,
                    total_so_far,
                } => {
                    self.status_text = format!(
                        "Recebendo {} (Pág. {}): {} registros obtidos | Total acumulado: {}",
                        tribunal, page, count, total_so_far
                    );
                }
                ApiMessage::Records(new_records) => {
                    self.append_records(new_records);
                }
                ApiMessage::Finished { total } => {
                    self.is_fetching = false;
                    if !self.cancel_flag.load(Ordering::Relaxed) {
                        self.status_text = format!(
                            "Concluído! {} processos recebidos nesta extração. Total na base: {}.",
                            total,
                            self.records.len()
                        );
                    }
                }
                ApiMessage::Error(err) => {
                    self.is_fetching = false;
                    if !self.cancel_flag.load(Ordering::Relaxed) {
                        self.error_text = Some(err);
                    }
                }
            }
        }

        // ================= TOP HEADER PANEL =================
        egui::TopBottomPanel::top("header_panel")
            .frame(
                egui::Frame::NONE
                    .fill(COLOR_BG_CARD)
                    .stroke(Stroke::new(1.0, COLOR_BORDER))
                    .inner_margin(egui::Margin::symmetric(20, 12)),
            )
            .show(ctx, |ui| {
                ui.horizontal(|ui| {
                    ui.vertical(|ui| {
                        ui.label(
                            RichText::new("DATAJUD CNJ — EXTRATOR DE PROCESSOS FUNDIÁRIOS")
                                .size(15.5)
                                .strong()
                                .color(COLOR_TEXT_PRIMARY),
                        );
                        ui.label(
                            RichText::new("Extração e análise multi-tribunal de conflitos de terras (TJPE, TRF5-JFPE, TJSP, etc.)")
                                .size(11.5)
                                .color(COLOR_TEXT_MUTED),
                        );
                    });

                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        // Total count badge
                        egui::Frame::NONE
                            .fill(COLOR_PRIMARY_BUTTON)
                            .corner_radius(CornerRadius::same(6))
                            .inner_margin(egui::Margin::symmetric(10, 4))
                            .show(ui, |ui| {
                                ui.label(
                                    RichText::new(format!("{} Processos na Base", self.records.len()))
                                        .color(Color32::WHITE)
                                        .size(12.0)
                                        .strong(),
                                );
                            });

                        // Active courts in dataset badge
                        let distinct = self.distinct_tribunals();
                        let courts_str = if distinct.is_empty() {
                            "Nenhum".to_string()
                        } else {
                            distinct.join(", ")
                        };

                        egui::Frame::NONE
                            .fill(Color32::from_rgb(241, 245, 249))
                            .stroke(Stroke::new(1.0, COLOR_BORDER))
                            .corner_radius(CornerRadius::same(6))
                            .inner_margin(egui::Margin::symmetric(10, 4))
                            .show(ui, |ui| {
                                ui.label(
                                    RichText::new(format!("Tribunais Carregados: {}", courts_str))
                                        .color(COLOR_TEXT_PRIMARY)
                                        .size(11.5)
                                        .strong(),
                                );
                            });
                    });
                });
            });

        // ================= LEFT CONTROLS PANEL (API QUERY) =================
        egui::SidePanel::left("query_panel")
            .resizable(false)
            .exact_width(330.0)
            .frame(
                egui::Frame::NONE
                    .fill(COLOR_BG_CARD)
                    .stroke(Stroke::new(1.0, COLOR_BORDER))
                    .inner_margin(egui::Margin::symmetric(16, 14)),
            )
            .show(ctx, |ui| {
                egui::ScrollArea::vertical()
                    .auto_shrink([false, false])
                    .show(ui, |ui| {
                        ui.label(
                            RichText::new("ÂMBITO TERRITORIAL")
                                .size(11.0)
                                .strong()
                                .color(COLOR_TEXT_MUTED),
                        );
                        ui.add_space(4.0);

                        egui::Frame::NONE
                            .fill(Color32::from_rgb(243, 244, 246))
                            .stroke(Stroke::new(1.0, Color32::from_rgb(229, 231, 235)))
                            .corner_radius(CornerRadius::same(6))
                            .inner_margin(egui::Margin::symmetric(10, 8))
                            .show(ui, |ui| {
                                ui.label(
                                    RichText::new("Pernambuco (TJPE + TRF5-JFPE)")
                                        .size(11.5)
                                        .strong()
                                        .color(COLOR_TEXT_PRIMARY),
                                );
                                ui.add_space(2.0);
                                ui.label(
                                    RichText::new("Extração simultânea estadual e federal vinculada a PE.")
                                        .size(10.5)
                                        .color(COLOR_TEXT_MUTED),
                                );
                            });

                        ui.add_space(8.0);
                        ui.separator();
                        ui.add_space(6.0);

                        // 1. Categorias de conflito fundiário
                        ui.label(
                            RichText::new("1. CATEGORIAS DE CONFLITO FUNDIÁRIO")
                                .size(11.5)
                                .strong()
                                .color(COLOR_TEXT_MUTED),
                        );
                        ui.add_space(4.0);

                        ui.horizontal(|ui| {
                            ui.label(RichText::new("Categorias para Buscar:").size(12.0).strong());
                            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                                if ui.small_button("Todas").clicked() {
                                    for cat in ConflictCategory::ALL {
                                        self.query_categories.insert(cat);
                                    }
                                    self.sync_query_tpu_from_categories();
                                }
                            });
                        });
                        ui.add_space(2.0);

                        let mut q_changed = false;
                        for cat in ConflictCategory::ALL {
                            let mut is_sel = self.query_categories.contains(&cat);
                            let [r, g, b] = cat.color_rgb();
                            let label_col = Color32::from_rgb(r, g, b);

                            ui.horizontal(|ui| {
                                if ui.checkbox(&mut is_sel, "").changed() {
                                    if is_sel {
                                        self.query_categories.insert(cat);
                                    } else {
                                        self.query_categories.remove(&cat);
                                    }
                                    q_changed = true;
                                }
                                ui.label(
                                    RichText::new(cat.display_name())
                                        .size(11.0)
                                        .color(label_col)
                                        .strong(),
                                );
                            });
                        }

                        if q_changed {
                            self.sync_query_tpu_from_categories();
                        }

                        ui.add_space(8.0);
                        ui.separator();
                        ui.add_space(6.0);

                        // 2. Filtros Adicionais de Busca (TPU)
                        ui.label(
                            RichText::new("2. FILTROS ADICIONAIS DE BUSCA (TPU)")
                                .size(11.5)
                                .strong()
                                .color(COLOR_TEXT_MUTED),
                        );
                        ui.add_space(4.0);
                        ui.label(RichText::new("Códigos TPU Assuntos:").size(11.0).color(COLOR_TEXT_MUTED));
                        ui.add(
                            egui::TextEdit::multiline(&mut self.query_assuntos)
                                .desired_rows(2)
                                .desired_width(f32::INFINITY),
                        );

                        ui.add_space(2.0);
                        ui.label(RichText::new("Códigos TPU Classes:").size(11.0).color(COLOR_TEXT_MUTED));
                        ui.add(
                            egui::TextEdit::singleline(&mut self.query_classes)
                                .desired_width(f32::INFINITY),
                        );

                        ui.add_space(8.0);
                        ui.separator();
                        ui.add_space(6.0);

                        // 3. Limites e Extração
                        ui.label(
                            RichText::new("3. LIMITES E EXTRAÇÃO")
                                .size(11.5)
                                .strong()
                                .color(COLOR_TEXT_MUTED),
                        );
                        ui.add_space(4.0);
                        ui.label(RichText::new("Limite Total da Busca (distribuído entre tribunais):").size(12.0).strong());
                        ui.checkbox(&mut self.query_limit_unlimited, "Sem limite (baixar todos disponíveis)");

                        if !self.query_limit_unlimited {
                            ui.horizontal(|ui| {
                                ui.add(egui::DragValue::new(&mut self.query_limit).range(10..=200000).speed(100));
                                ui.label("processos no total");
                            });

                            ui.horizontal_wrapped(|ui| {
                                for val in [500, 1000, 5000, 10000, 50000] {
                                    if ui.small_button(format!("{val}")).clicked() {
                                        self.query_limit = val;
                                    }
                                }
                            });
                        }

                        ui.add_space(6.0);
                        ui.checkbox(&mut self.accumulate_data, "Acumular processos (não apagar anteriores)");

                        ui.add_space(10.0);

                        // Start / Cancel button
                        if !self.is_fetching {
                            let btn = render_search_button(
                                ui,
                                "Iniciar Extração DataJud",
                                COLOR_PRIMARY_BUTTON,
                                Color32::WHITE,
                                42.0,
                                None,
                            );

                            if btn.clicked() {
                                self.start_search();
                            }
                        } else {
                            let cancel_btn = render_cancel_button(
                                ui,
                                "Cancelar Extração",
                                42.0,
                                None,
                            );

                            if cancel_btn.clicked() {
                                self.cancel_search();
                            }
                        }

                        ui.add_space(8.0);
                        if !self.records.is_empty()
                            && !self.is_fetching
                            && ui.button("Limpar Base Carregada").clicked()
                        {
                            self.clear_all_records();
                        }
                    });
            });

        // ================= BOTTOM DETAILS DRAWER =================
        if let Some(ref selected) = self.selected_record.clone() {
            egui::TopBottomPanel::bottom("detail_panel")
                .resizable(true)
                .default_height(220.0)
                .frame(
                    egui::Frame::NONE
                        .fill(COLOR_BG_CARD)
                        .stroke(Stroke::new(1.0, COLOR_BORDER))
                        .inner_margin(egui::Margin::symmetric(18, 12)),
                )
                .show(ctx, |ui| {
                    ui.horizontal(|ui| {
                        ui.label(
                            RichText::new("DETALHES DO PROCESSO:")
                                .size(13.0)
                                .strong()
                                .color(COLOR_TEXT_PRIMARY),
                        );
                        ui.monospace(
                            RichText::new(&selected.numero_processo)
                                .size(13.0)
                                .strong(),
                        );

                        render_tribunal_badge(ui, &selected.tribunal);
                        render_category_badge(ui, selected.categoria);

                        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                            if ui.small_button("Fechar").clicked() {
                                self.selected_record = None;
                            }

                            if ui.small_button("Copiar Número").clicked() {
                                ctx.copy_text(selected.numero_processo.clone());
                                self.status_text = format!("Número copiado: {}", selected.numero_processo);
                            }
                        });
                    });

                    ui.separator();
                    ui.add_space(4.0);

                    egui::ScrollArea::vertical().show(ui, |ui| {
                        ui.horizontal(|ui| {
                            ui.label(RichText::new("Tribunal:").strong().size(12.0));
                            ui.label(&selected.tribunal);

                            ui.add_space(16.0);
                            ui.label(RichText::new("Grau:").strong().size(12.0));
                            ui.label(&selected.grau);

                            ui.add_space(16.0);
                            ui.label(RichText::new("Data de Ajuizamento:").strong().size(12.0));
                            ui.label(&selected.data_ajuizamento);
                        });

                        ui.horizontal(|ui| {
                            ui.label(RichText::new("Classe Processual:").strong().size(12.0));
                            ui.label(format!(
                                "{} (código {})",
                                selected.classe_nome,
                                selected.classe_codigo.unwrap_or(0)
                            ));
                        });

                        ui.horizontal(|ui| {
                            ui.label(RichText::new("Órgão Julgador:").strong().size(12.0));
                            ui.label(&selected.orgao_julgador);
                            if let Some(ibge) = selected.municipio_ibge {
                                ui.weak(format!("(IBGE: {})", ibge));
                            }
                        });

                        ui.add_space(4.0);
                        ui.label(RichText::new("Assuntos TPU Vinculados:").strong().size(12.0));
                        for (i, nome) in selected.assuntos_nomes.iter().enumerate() {
                            let cod = selected.assuntos_codigos.get(i).copied().unwrap_or(0);
                            ui.horizontal(|ui| {
                                ui.monospace(format!("  • [{}]", cod));
                                ui.label(nome);
                            });
                        }
                    });
                });
        }

        // ================= CENTRAL PANEL: POST-FETCH FILTER & DATA TABLE =================
        egui::CentralPanel::default()
            .frame(
                egui::Frame::NONE
                    .fill(COLOR_BG_CARD)
                    .inner_margin(egui::Margin::symmetric(16, 14)),
            )
            .show(ctx, |ui| {
                // Status / Error Banner
                ui.horizontal(|ui| {
                    if self.is_fetching {
                        ui.spinner();
                    }

                    if let Some(ref err) = self.error_text {
                        ui.label(
                            RichText::new(format!("[Erro] {}", err))
                                .color(Color32::from_rgb(220, 38, 38))
                                .strong(),
                        );
                    } else {
                        ui.label(RichText::new(&self.status_text).color(COLOR_TEXT_MUTED));
                    }
                });

                ui.add_space(6.0);

                // --- 2. POST-FETCH FILTER BAR (CONTEXT MENUS & BIG SEARCH BAR) ---
                let mut filter_changed = false;

                egui::Frame::NONE
                    .fill(Color32::from_rgb(248, 250, 252))
                    .stroke(Stroke::new(1.0, COLOR_BORDER))
                    .corner_radius(CornerRadius::same(8))
                    .inner_margin(egui::Margin::symmetric(14, 12))
                    .show(ui, |ui| {
                        // Top row: Context Menu Dropdowns for Tribunal & Categorias, plus Reset button
                        ui.allocate_ui_with_layout(
                            egui::vec2(ui.available_width(), 32.0),
                            egui::Layout::left_to_right(egui::Align::Center),
                            |ui| {
                                ui.label(
                                    RichText::new("Filtros:")
                                        .size(12.5)
                                        .strong()
                                        .color(COLOR_TEXT_PRIMARY),
                                );

                                ui.add_space(4.0);

                                // 1. Tribunal Context Dropdown (Stays open on item click, closes only on click outside)
                                let distinct_tribs = self.distinct_tribunals();
                                let active_trib_count = distinct_tribs
                                    .iter()
                                    .filter(|t| self.filter_tribunals.iter().any(|ft| ft.eq_ignore_ascii_case(t)))
                                    .count();

                                let trib_title = if distinct_tribs.is_empty() {
                                    "Tribunal".to_string()
                                } else if active_trib_count == distinct_tribs.len() {
                                    format!("Tribunal: {}", distinct_tribs.join(", "))
                                } else if active_trib_count == 1 {
                                    let active_name = distinct_tribs
                                        .iter()
                                        .find(|t| self.filter_tribunals.iter().any(|ft| ft.eq_ignore_ascii_case(t)))
                                        .unwrap();
                                    format!("Tribunal: {}", active_name)
                                } else if active_trib_count == 0 {
                                    "Tribunal: (Nenhum)".to_string()
                                } else {
                                    format!(
                                        "Tribunal: ({}/{})",
                                        active_trib_count,
                                        distinct_tribs.len()
                                    )
                                };

                                let trib_btn = render_dropdown_filter_button(ui, &trib_title, 0.0)
                                    .on_hover_text("Clique para filtrar tribunais");

                                let trib_popup = Popup::from_toggle_button_response(&trib_btn)
                                    .close_behavior(PopupCloseBehavior::CloseOnClickOutside)
                                    .width(260.0);

                                trib_popup.show(|ui| {
                                    ui.set_min_width(240.0);
                                    ui.horizontal(|ui| {
                                        ui.label(RichText::new("Filtrar por Tribunal").strong().size(12.0));
                                        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                                            if !distinct_tribs.is_empty() {
                                                if ui.small_button("Marcar Todos").clicked() {
                                                    for t in &distinct_tribs {
                                                        self.filter_tribunals.insert(t.clone());
                                                    }
                                                    filter_changed = true;
                                                }
                                                if ui.small_button("Desmarcar").clicked() {
                                                    self.filter_tribunals.clear();
                                                    filter_changed = true;
                                                }
                                            }
                                        });
                                    });
                                    ui.separator();

                                    if distinct_tribs.is_empty() {
                                        ui.add_space(4.0);
                                        ui.label(
                                            RichText::new("Nenhum tribunal carregado ainda.")
                                                .size(11.5)
                                                .color(COLOR_TEXT_MUTED),
                                        );
                                        ui.label(
                                            RichText::new("Os tribunais aparecerão aqui ao iniciar a extração.")
                                                .size(10.5)
                                                .color(COLOR_TEXT_MUTED),
                                        );
                                        ui.add_space(4.0);
                                    } else {
                                        for t in &distinct_tribs {
                                            let count = self
                                                .records
                                                .iter()
                                                .filter(|r| r.tribunal.eq_ignore_ascii_case(t))
                                                .count();
                                            let is_active = self
                                                .filter_tribunals
                                                .iter()
                                                .any(|ft| ft.eq_ignore_ascii_case(t));

                                            if render_filter_item(ui, is_active, t, count, None) {
                                                if is_active {
                                                    self.filter_tribunals.retain(|ft| !ft.eq_ignore_ascii_case(t));
                                                } else {
                                                    self.filter_tribunals.insert(t.clone());
                                                }
                                                filter_changed = true;
                                            }
                                        }
                                    }
                                });

                                ui.add_space(8.0);

                                // 2. Categories Context Dropdown (Stays open on item click, closes only on click outside)
                                let active_cat_count = self.filter_categories.len();
                                let cat_title = if active_cat_count == ConflictCategory::ALL.len() {
                                    "Categorias: Todas (6)".to_string()
                                } else {
                                    format!(
                                        "Categorias: ({}/{})",
                                        active_cat_count,
                                        ConflictCategory::ALL.len()
                                    )
                                };

                                let cat_btn = render_dropdown_filter_button(ui, &cat_title, 0.0)
                                    .on_hover_text("Clique para filtrar categorias");

                                let cat_popup = Popup::from_toggle_button_response(&cat_btn)
                                    .close_behavior(PopupCloseBehavior::CloseOnClickOutside)
                                    .width(320.0);

                                cat_popup.show(|ui| {
                                    ui.set_min_width(300.0);
                                    ui.horizontal(|ui| {
                                        ui.label(RichText::new("Filtrar Categorias").strong().size(12.0));
                                        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                                            if ui.small_button("Marcar Todas").clicked() {
                                                for c in ConflictCategory::ALL {
                                                    self.filter_categories.insert(c);
                                                }
                                                filter_changed = true;
                                            }
                                            if ui.small_button("Desmarcar").clicked() {
                                                self.filter_categories.clear();
                                                filter_changed = true;
                                            }
                                        });
                                    });
                                    ui.separator();

                                    for cat in ConflictCategory::ALL {
                                        let is_sel = self.filter_categories.contains(&cat);
                                        let count = self.records.iter().filter(|r| r.categoria == cat).count();
                                        let [r, g, b] = cat.color_rgb();
                                        let color = Color32::from_rgb(r, g, b);

                                        if render_filter_item(ui, is_sel, cat.display_name(), count, Some(color)) {
                                            if is_sel {
                                                self.filter_categories.remove(&cat);
                                            } else {
                                                self.filter_categories.insert(cat);
                                            }
                                            filter_changed = true;
                                        }
                                    }
                                });

                                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                                    if ui.button(RichText::new("Restaurar Filtros").size(11.5)).clicked() {
                                        let distinct = self.distinct_tribunals();
                                        if distinct.is_empty() {
                                            self.filter_tribunals = HashSet::from(["TJPE".to_string(), "TRF5".to_string()]);
                                        } else {
                                            self.filter_tribunals = distinct.into_iter().collect();
                                        }
                                        self.filter_search_text.clear();
                                        for c in ConflictCategory::ALL {
                                            self.filter_categories.insert(c);
                                        }
                                        filter_changed = true;
                                    }
                                });
                            },
                        );

                        ui.add_space(8.0);

                        // Second row: Bigger Search Input (Vertically centered) & Big Filter Button with Search Icon
                        ui.allocate_ui_with_layout(
                            egui::vec2(ui.available_width(), 36.0),
                            egui::Layout::left_to_right(egui::Align::Center),
                            |ui| {
                                ui.label(
                                    RichText::new("Buscar:")
                                        .size(13.0)
                                        .strong()
                                        .color(COLOR_TEXT_PRIMARY),
                                );

                                ui.add_space(4.0);

                                let search_edit = egui::TextEdit::singleline(&mut self.filter_search_text)
                                    .hint_text("Filtrar por número, classe, comarca, município ou assunto...")
                                    .font(egui::FontId::proportional(13.5))
                                    .vertical_align(egui::Align::Center)
                                    .horizontal_align(egui::Align::Min)
                                    .margin(egui::Margin::symmetric(10, 8))
                                    .min_size(egui::vec2(ui.available_width() - 180.0, 36.0));

                                let search_resp = ui.add(search_edit);
                                if search_resp.changed() {
                                    filter_changed = true;
                                }

                                let filter_btn = render_search_button(
                                    ui,
                                    "Filtrar",
                                    COLOR_PRIMARY_BUTTON,
                                    Color32::WHITE,
                                    36.0,
                                    Some(95.0),
                                );
                                if filter_btn.clicked() {
                                    filter_changed = true;
                                }

                                if !self.filter_search_text.is_empty() {
                                    let clear_btn = egui::Button::new(RichText::new("Limpar").size(12.0))
                                        .min_size(egui::vec2(60.0, 36.0));
                                    if ui.add(clear_btn).clicked() {
                                        self.filter_search_text.clear();
                                        filter_changed = true;
                                    }
                                }
                            },
                        );
                    });

                if filter_changed {
                    self.current_page = 0;
                }

                ui.add_space(8.0);

                // Compute filtered records indices
                let search_q = self.filter_search_text.trim().to_lowercase();
                let filtered_indices: Vec<usize> = self
                    .records
                    .iter()
                    .enumerate()
                    .filter(|(_, r)| {
                        // 1. Tribunal filter
                        if !self
                            .filter_tribunals
                            .iter()
                            .any(|t| t.eq_ignore_ascii_case(&r.tribunal))
                        {
                            return false;
                        }

                        // 2. Category filter
                        if !self.filter_categories.contains(&r.categoria) {
                            return false;
                        }

                        // 3. Text search
                        if !search_q.is_empty() {
                            let match_num = r.numero_processo.contains(&search_q);
                            let match_orgao = r.orgao_julgador.to_lowercase().contains(&search_q);
                            let match_classe = r.classe_nome.to_lowercase().contains(&search_q);
                            let match_assunto = r
                                .assuntos_nomes
                                .iter()
                                .any(|a| a.to_lowercase().contains(&search_q));
                            let match_trib = r.tribunal.to_lowercase().contains(&search_q);

                            if !match_num && !match_orgao && !match_classe && !match_assunto && !match_trib {
                                return false;
                            }
                        }

                        true
                    })
                    .map(|(i, _)| i)
                    .collect();

                let total_records = self.records.len();
                let total_filtered = filtered_indices.len();

                // Compute Pagination Boundaries
                let effective_page_size = if self.page_size == 0 {
                    total_filtered.max(1)
                } else {
                    self.page_size
                };

                let total_pages = if total_filtered == 0 {
                    1
                } else {
                    total_filtered.div_ceil(effective_page_size)
                };

                if self.current_page >= total_pages {
                    self.current_page = total_pages.saturating_sub(1);
                }

                let start_idx = self.current_page * effective_page_size;
                let end_idx = (start_idx + effective_page_size).min(total_filtered);
                let current_page_indices = if total_filtered == 0 {
                    &[][..]
                } else {
                    &filtered_indices[start_idx..end_idx]
                };

                // Results Summary & Export Bar
                ui.horizontal(|ui| {
                    ui.label(
                        RichText::new(format!(
                            "Exibindo {} a {} de {} processos filtrados (Total na base: {})",
                            if total_filtered == 0 { 0 } else { start_idx + 1 },
                            end_idx,
                            total_filtered,
                            total_records
                        ))
                        .size(12.5)
                        .strong()
                        .color(COLOR_TEXT_PRIMARY),
                    );

                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        let has_filtered = !filtered_indices.is_empty();

                        let json_btn = ui.add_enabled(
                            has_filtered,
                            egui::Button::new(
                                RichText::new("Exportar JSON")
                                    .size(12.0)
                                    .color(if has_filtered { COLOR_TEXT_PRIMARY } else { COLOR_TEXT_MUTED }),
                            )
                            .corner_radius(CornerRadius::same(6)),
                        );

                        if json_btn.clicked() {
                            let export_subset: Vec<ProcessRecord> =
                                filtered_indices.iter().map(|&i| self.records[i].clone()).collect();
                            self.export_json(&export_subset);
                        }

                        let csv_btn = ui.add_enabled(
                            has_filtered,
                            egui::Button::new(
                                RichText::new("Exportar CSV (Filtrados)")
                                    .size(12.0)
                                    .strong()
                                    .color(if has_filtered { Color32::WHITE } else { COLOR_TEXT_MUTED }),
                            )
                            .fill(COLOR_SUCCESS_BUTTON)
                            .corner_radius(CornerRadius::same(6)),
                        );

                        if csv_btn.clicked() {
                            let export_subset: Vec<ProcessRecord> =
                                filtered_indices.iter().map(|&i| self.records[i].clone()).collect();
                            self.export_csv(&export_subset);
                        }
                    });
                });

                ui.add_space(4.0);

                // --- PAGINATION CONTROLS BAR ---
                ui.horizontal(|ui| {
                    ui.label(RichText::new("Página:").size(12.0).strong());

                    let prev_btn = ui.add_enabled(self.current_page > 0, egui::Button::new("Anterior"));
                    if prev_btn.clicked() {
                        self.current_page = self.current_page.saturating_sub(1);
                    }

                    ui.label(
                        RichText::new(format!("{} de {}", self.current_page + 1, total_pages))
                            .size(12.0)
                            .strong()
                            .color(COLOR_PRIMARY_BUTTON),
                    );

                    let next_btn = ui.add_enabled(
                        self.current_page + 1 < total_pages,
                        egui::Button::new("Próxima"),
                    );
                    if next_btn.clicked() {
                        self.current_page += 1;
                    }

                    ui.add_space(16.0);
                    ui.label(RichText::new("Registros por página:").size(11.5).color(COLOR_TEXT_MUTED));

                    for sz in [25, 50, 100, 250] {
                        let is_sel = self.page_size == sz;
                        let btn = egui::Button::new(
                            RichText::new(format!("{sz}"))
                                .color(if is_sel { Color32::WHITE } else { COLOR_TEXT_PRIMARY }),
                        )
                        .fill(if is_sel { COLOR_PRIMARY_BUTTON } else { Color32::from_rgb(241, 245, 249) })
                        .corner_radius(CornerRadius::same(4));

                        if ui.add(btn).clicked() {
                            self.page_size = sz;
                            self.current_page = 0;
                        }
                    }

                    let all_sel = self.page_size == 0;
                    let all_btn = egui::Button::new(
                        RichText::new("Todos")
                            .color(if all_sel { Color32::WHITE } else { COLOR_TEXT_PRIMARY }),
                    )
                    .fill(if all_sel { COLOR_PRIMARY_BUTTON } else { Color32::from_rgb(241, 245, 249) })
                    .corner_radius(CornerRadius::same(4));

                    if ui.add(all_btn).clicked() {
                        self.page_size = 0;
                        self.current_page = 0;
                    }
                });

                ui.add_space(4.0);
                ui.separator();
                ui.add_space(2.0);

                // Table View with Horizontal & Vertical Scrolling
                egui::ScrollArea::both()
                    .auto_shrink([false, false])
                    .show(ui, |ui| {
                        if filtered_indices.is_empty() {
                            ui.add_space(50.0);
                            ui.vertical_centered(|ui| {
                                if self.records.is_empty() {
                                    ui.label(
                                        RichText::new("Nenhum processo carregado na base.")
                                            .size(13.5)
                                            .strong()
                                            .color(COLOR_TEXT_PRIMARY),
                                    );
                                    ui.label(
                                        RichText::new("Selecione os tribunais desejados (ex: TJPE + TRF5) e clique em 'Iniciar Extração DataJud'.")
                                            .color(COLOR_TEXT_MUTED)
                                            .size(12.0),
                                    );
                                } else {
                                    ui.label(
                                        RichText::new("Nenhum processo corresponde aos filtros selecionados.")
                                            .size(13.5)
                                            .strong()
                                            .color(COLOR_TEXT_PRIMARY),
                                    );
                                    ui.label(
                                        RichText::new("Tente alterar o filtro de tribunal, marcar mais categorias ou limpar o texto de busca.")
                                            .color(COLOR_TEXT_MUTED)
                                            .size(12.0),
                                    );
                                }
                            });
                        } else {
                            egui::Grid::new("datajud_process_grid")
                                .striped(true)
                                .spacing([14.0, 7.0])
                                .min_col_width(50.0)
                                .show(ui, |ui| {
                                    // Headers
                                    ui.label(RichText::new("#").strong().size(11.5));
                                    ui.label(RichText::new("Tribunal").strong().size(11.5));
                                    ui.label(RichText::new("Número do Processo (CNJ)").strong().size(11.5));
                                    ui.label(RichText::new("Categoria").strong().size(11.5));
                                    ui.label(RichText::new("Classe Processual").strong().size(11.5));
                                    ui.label(RichText::new("Órgão Julgador / Município").strong().size(11.5));
                                    ui.label(RichText::new("Data Ajuizamento").strong().size(11.5));
                                    ui.label(RichText::new("Ação").strong().size(11.5));
                                    ui.end_row();

                                    // Rows (Only current page slice!)
                                    for (page_offset, &real_idx) in current_page_indices.iter().enumerate() {
                                        let display_num = start_idx + page_offset + 1;
                                        let rec = &self.records[real_idx];

                                        let is_selected = self
                                            .selected_record
                                            .as_ref()
                                            .is_some_and(|s| s.numero_processo == rec.numero_processo);

                                        let row_id = ui.id().with(("lawsuit_row", real_idx));
                                        let bg_shape_idx = ui.painter().add(egui::Shape::Noop);
                                        let row_top = ui.cursor().min.y;

                                        // 1. #
                                        ui.label(
                                            RichText::new(format!("{:4}", display_num))
                                                .color(COLOR_TEXT_MUTED)
                                                .size(11.0),
                                        );

                                        // 2. Tribunal Badge
                                        render_tribunal_badge(ui, &rec.tribunal);

                                        // 3. Process Number (Clickable to inspect)
                                        let num_label = if is_selected {
                                            RichText::new(&rec.numero_processo)
                                                .monospace()
                                                .size(12.0)
                                                .strong()
                                                .color(Color32::from_rgb(67, 56, 202))
                                        } else {
                                            RichText::new(&rec.numero_processo)
                                                .monospace()
                                                .size(12.0)
                                                .strong()
                                                .color(COLOR_TEXT_PRIMARY)
                                        };
                                        ui.label(num_label);

                                        // 4. Category Badge
                                        render_category_badge(ui, rec.categoria);

                                        // 5. Procedural Class
                                        ui.label(
                                            RichText::new(&rec.classe_nome)
                                                .size(11.5)
                                                .color(COLOR_TEXT_PRIMARY),
                                        );

                                        // 6. Court Unit / Comarca
                                        let orgao_display = if let Some(ibge) = rec.municipio_ibge {
                                            format!("{} ({})", rec.orgao_julgador, ibge)
                                        } else {
                                            rec.orgao_julgador.clone()
                                        };
                                        ui.label(
                                            RichText::new(orgao_display)
                                                .size(11.5)
                                                .color(COLOR_TEXT_PRIMARY),
                                        );

                                        // 7. Filing Date
                                        let date_short = if rec.data_ajuizamento.len() >= 10 {
                                            &rec.data_ajuizamento[0..10]
                                        } else {
                                            &rec.data_ajuizamento
                                        };
                                        ui.label(
                                            RichText::new(date_short)
                                                .color(COLOR_TEXT_MUTED)
                                                .size(11.5),
                                        );

                                        // 8. Action button
                                        let ver_btn = ui.add(
                                            egui::Button::new(
                                                RichText::new("Ver")
                                                    .size(11.0)
                                                    .strong()
                                                    .color(if is_selected { Color32::WHITE } else { COLOR_PRIMARY_BUTTON }),
                                            )
                                            .fill(if is_selected { COLOR_PRIMARY_BUTTON } else { Color32::from_rgb(238, 242, 255) })
                                            .corner_radius(CornerRadius::same(4)),
                                        );
                                        if ver_btn.clicked() {
                                            self.selected_record = Some((*rec).clone());
                                        }

                                        // Entire row clickable & hover effect
                                        let row_bottom = ui.min_rect().max.y;
                                        let row_left = ui.min_rect().min.x - 4.0;
                                        let row_right = ui.min_rect().max.x.max(ui.cursor().max.x) + 4.0;
                                        let row_rect = egui::Rect::from_min_max(
                                            egui::pos2(row_left, row_top - 3.0),
                                            egui::pos2(row_right, row_bottom + 3.0),
                                        );

                                        let row_resp = ui.interact(row_rect, row_id, egui::Sense::click());
                                        if row_resp.hovered() {
                                            ui.ctx().set_cursor_icon(egui::CursorIcon::PointingHand);
                                        }
                                        if row_resp.clicked() {
                                            self.selected_record = Some((*rec).clone());
                                        }

                                        if is_selected {
                                            ui.painter().set(
                                                bg_shape_idx,
                                                egui::Shape::rect_filled(
                                                    row_rect,
                                                    CornerRadius::same(4),
                                                    Color32::from_rgb(224, 231, 255), // Indigo highlight for selected
                                                ),
                                            );
                                        } else if row_resp.hovered() {
                                            ui.painter().set(
                                                bg_shape_idx,
                                                egui::Shape::rect_filled(
                                                    row_rect,
                                                    CornerRadius::same(4),
                                                    Color32::from_rgb(241, 245, 249), // Slate gray hover style
                                                ),
                                            );
                                        }

                                        ui.end_row();
                                    }
                                });
                        }
                    });
            });

        if self.is_fetching {
            ctx.request_repaint();
        }
    }
}
