use std::time::Instant;

use eframe::egui::{self, Popup, RichText};

use crate::app::{Action, View};
use crate::data::export::ExportFormat;
use crate::data::store::Dataset;
use crate::model::format_count;
use crate::theme::{self, COLOR_BG_CARD, COLOR_TEXT_MUTED, COLOR_TEXT_PRIMARY};

pub fn show(ctx: &egui::Context, ds: Option<&Dataset>, view: &mut View) {
    egui::TopBottomPanel::top("top_bar")
        .frame(
            egui::Frame::NONE
                .fill(COLOR_BG_CARD)
                .inner_margin(egui::Margin::symmetric(16, 10)),
        )
        .show(ctx, |ui| {
            ui.horizontal(|ui| {
                ui.vertical(|ui| {
                    ui.spacing_mut().item_spacing.y = 1.0;
                    ui.label(
                        RichText::new("DataJud · Pernambuco")
                            .size(15.0)
                            .strong()
                            .color(COLOR_TEXT_PRIMARY),
                    );
                    let subtitle = match ds {
                        Some(ds) => format!(
                            "{} processos fundiários · TJPE e TRF5{}",
                            format_count(ds.rows.len()),
                            ds.meta
                                .generated_at
                                .as_deref()
                                .map(|g| format!(" · base de {}", format_snapshot_date(g)))
                                .unwrap_or_default()
                        ),
                        None => "Processos fundiários · TJPE e TRF5".to_string(),
                    };
                    ui.label(RichText::new(subtitle).size(11.5).color(COLOR_TEXT_MUTED));
                });

                ui.add_space(16.0);

                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    base_menu(ui, ds, view);
                    if let Some(ds) = ds {
                        export_menu(ui, ds, view);
                        ui.add_space(4.0);
                        search_field(ui, view);
                    }
                });
            });
        });
}

fn format_snapshot_date(iso: &str) -> String {
    match (iso.get(0..4), iso.get(5..7), iso.get(8..10)) {
        (Some(y), Some(m), Some(d)) => format!("{d}/{m}/{y}"),
        _ => iso.to_string(),
    }
}

fn search_field(ui: &mut egui::Ui, view: &mut View) {
    let width = (ui.available_width() - 8.0).clamp(160.0, 640.0);
    let clear_width = if view.filters.text.is_empty() {
        0.0
    } else {
        26.0
    };

    ui.allocate_ui_with_layout(
        egui::vec2(width, 32.0),
        egui::Layout::left_to_right(egui::Align::Center),
        |ui| {
            ui.spacing_mut().item_spacing.x = 2.0;
            let edit = egui::TextEdit::singleline(&mut view.filters.text)
                .id(egui::Id::new("search_field"))
                .hint_text("Buscar número CNJ, classe, assunto, município…")
                .margin(egui::Margin::symmetric(10, 7))
                .desired_width(width - clear_width - 4.0);
            let response = ui
                .add(edit)
                .on_hover_text("Busca sem acentos em número CNJ, classe, assuntos, órgão julgador e município (Ctrl+F)");

            if view.focus_search {
                response.request_focus();
                view.focus_search = false;
            }
            if response.changed() {
                view.text_edited_at = Some(Instant::now());
            }
            if response.has_focus() && ui.input(|i| i.key_pressed(egui::Key::Escape)) {
                view.filters.text.clear();
                view.text_edited_at = None;
                view.touch();
            }
            if response.lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter)) {
                view.text_edited_at = None;
                view.touch();
            }
            if !view.filters.text.is_empty() && theme::close_button(ui, "Limpar busca").clicked() {
                view.filters.text.clear();
                view.text_edited_at = None;
                view.touch();
            }
        },
    );
}

fn export_menu(ui: &mut egui::Ui, ds: &Dataset, view: &mut View) {
    let n = view.result.visible.len();
    let enabled = n > 0;
    let response = theme::dropdown_button(ui, "Exportar", enabled);
    let response = if enabled {
        response.on_hover_text(format!("Exporta os {} processos listados", format_count(n)))
    } else {
        response.on_hover_text("Nenhum processo listado para exportar")
    };
    if !enabled {
        return;
    }

    let filtered_note = if n < ds.rows.len() {
        " (filtrados)"
    } else {
        ""
    };
    Popup::menu(&response).show(|ui| {
        ui.set_min_width(220.0);
        ui.label(
            RichText::new(format!("{} processos{}", format_count(n), filtered_note))
                .size(11.5)
                .color(COLOR_TEXT_MUTED),
        );
        ui.separator();
        if ui.button("Planilha CSV").clicked() {
            view.actions.push(Action::Export(ExportFormat::Csv));
            ui.close();
        }
        if ui.button("Arquivo JSON").clicked() {
            view.actions.push(Action::Export(ExportFormat::Json));
            ui.close();
        }
    });
}

fn base_menu(ui: &mut egui::Ui, ds: Option<&Dataset>, view: &mut View) {
    let response = theme::dropdown_button(ui, "Base", true);
    Popup::menu(&response).show(|ui| {
        ui.set_min_width(200.0);
        if ui.button("Abrir outra base…").clicked() {
            view.actions.push(Action::OpenBase);
            ui.close();
        }
        if ui.button("Recarregar base").clicked() {
            view.actions.push(Action::Reload);
            ui.close();
        }
        if ds.is_some() && ui.button("Sobre a base").clicked() {
            view.about_open = true;
            ui.close();
        }
    });
}
