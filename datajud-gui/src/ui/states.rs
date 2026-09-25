use eframe::egui::{self, RichText};

use crate::app::{Action, Notice, View};
use crate::data::source::{SNAPSHOT_FILE_NAME, Source};
use crate::data::store::Dataset;
use crate::model::format_count;
use crate::theme::{
    self, COLOR_BG_CARD, COLOR_BORDER, COLOR_DANGER, COLOR_DANGER_BG, COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, caption,
};

const EXPORT_COMMAND: &str = "uv run python src/export_datajud_sqlite.py";

fn centered(ui: &mut egui::Ui, add_contents: impl FnOnce(&mut egui::Ui)) {
    ui.vertical_centered(|ui| {
        ui.add_space((ui.available_height() * 0.28).max(24.0));
        ui.set_max_width(520.0);
        add_contents(ui);
    });
}

pub fn loading(ui: &mut egui::Ui, source: &Source) {
    centered(ui, |ui| {
        ui.spinner();
        ui.add_space(8.0);
        ui.label(
            RichText::new("Carregando base de processos…")
                .size(14.0)
                .strong(),
        );
        ui.label(
            RichText::new(source.describe())
                .size(11.5)
                .color(COLOR_TEXT_MUTED),
        );
    });
}

pub fn missing(ui: &mut egui::Ui, view: &mut View) {
    centered(ui, |ui| {
        ui.label(
            RichText::new("Nenhuma base de processos encontrada")
                .size(15.0)
                .strong(),
        );
        ui.add_space(6.0);
        ui.label(
            RichText::new(format!(
                "Gere o arquivo {SNAPSHOT_FILE_NAME} a partir do PostgreSQL, na raiz do repositório:"
            ))
            .color(COLOR_TEXT_SECONDARY),
        );
        ui.add_space(4.0);
        command_box(ui, EXPORT_COMMAND);
        ui.add_space(4.0);
        ui.label(
            RichText::new("Ou coloque o arquivo ao lado do executável, ou use --db <caminho>.")
                .size(11.5)
                .color(COLOR_TEXT_MUTED),
        );
        ui.add_space(12.0);
        ui.horizontal(|ui| {
            ui.add_space((ui.available_width() - 240.0).max(0.0) / 2.0);
            if theme::primary_button(ui, "Abrir base…").clicked() {
                view.actions.push(Action::OpenBase);
            }
            if ui.button("Tentar novamente").clicked() {
                view.actions.push(Action::Reload);
            }
        });
    });
}

pub fn failed(ui: &mut egui::Ui, err: &str, view: &mut View) {
    centered(ui, |ui| {
        ui.label(
            RichText::new("Não foi possível carregar a base")
                .size(15.0)
                .strong()
                .color(COLOR_DANGER),
        );
        ui.add_space(6.0);
        ui.label(RichText::new(err).color(COLOR_TEXT_SECONDARY));
        ui.add_space(12.0);
        ui.horizontal(|ui| {
            ui.add_space((ui.available_width() - 240.0).max(0.0) / 2.0);
            if theme::primary_button(ui, "Abrir outra base…").clicked() {
                view.actions.push(Action::OpenBase);
            }
            if ui.button("Tentar novamente").clicked() {
                view.actions.push(Action::Reload);
            }
        });
    });
}

pub fn no_results(ui: &mut egui::Ui, view: &mut View) {
    centered(ui, |ui| {
        ui.label(
            RichText::new("Nenhum processo corresponde aos filtros")
                .size(14.0)
                .strong(),
        );
        ui.add_space(4.0);
        ui.label(
            RichText::new("Remova algum filtro ou altere o texto da busca.")
                .color(COLOR_TEXT_MUTED),
        );
        ui.add_space(10.0);
        if theme::primary_button(ui, "Limpar filtros").clicked() {
            view.clear_filters();
        }
    });
}

fn command_box(ui: &mut egui::Ui, command: &str) {
    egui::Frame::NONE
        .fill(COLOR_BG_CARD)
        .stroke(theme::stroke(1.0, COLOR_BORDER))
        .corner_radius(6)
        .inner_margin(egui::Margin::symmetric(10, 6))
        .show(ui, |ui| {
            ui.horizontal(|ui| {
                ui.label(RichText::new(command).monospace().color(COLOR_TEXT_PRIMARY));
                if ui.small_button("Copiar").clicked() {
                    ui.ctx().copy_text(command.to_string());
                }
            });
        });
}

pub fn notice_bar(ctx: &egui::Context, notice: &Notice) -> bool {
    let (fill, fg) = if notice.is_error {
        (COLOR_DANGER_BG, COLOR_DANGER)
    } else {
        (theme::COLOR_BG_SUBTLE, COLOR_TEXT_SECONDARY)
    };
    let mut dismissed = false;
    egui::TopBottomPanel::top("notice_bar")
        .frame(
            egui::Frame::NONE
                .fill(fill)
                .inner_margin(egui::Margin::symmetric(16, 6)),
        )
        .show(ctx, |ui| {
            ui.horizontal(|ui| {
                let prefix = if notice.is_error { "Erro: " } else { "" };
                ui.label(RichText::new(format!("{prefix}{}", notice.text)).color(fg));
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    dismissed = theme::close_button(ui, "Dispensar").clicked();
                });
            });
        });
    dismissed
}

pub fn about_window(ctx: &egui::Context, ds: &Dataset, view: &mut View) {
    let mut open = view.about_open;
    egui::Window::new("Sobre a base")
        .open(&mut open)
        .collapsible(false)
        .resizable(false)
        .anchor(egui::Align2::CENTER_CENTER, egui::Vec2::ZERO)
        .show(ctx, |ui| {
            ui.set_min_width(420.0);
            egui::Grid::new("about_grid").num_columns(2).spacing([16.0, 6.0]).show(ui, |ui| {
                let mut row = |k: &str, v: String| {
                    ui.label(RichText::new(k).color(COLOR_TEXT_MUTED));
                    ui.add(egui::Label::new(v).wrap());
                    ui.end_row();
                };
                row("Origem", ds.source.describe());
                row("Tabela", ds.meta.source_table.clone().unwrap_or_else(|| "—".into()));
                row("Gerada em", ds.meta.generated_at.clone().unwrap_or_else(|| "—".into()));
                row("Processos", format_count(ds.rows.len()));
                row("Números distintos", format_count(ds.rows.len() - ds.siblings.values().map(|v| v.len() - 1).sum::<usize>()));
                row("Período", format!("{}–{}", ds.year_range.0, ds.year_range.1));
                row("Carregamento", format!("{} ms", ds.load_time.as_millis()));
                row("Última consulta", format!("{:.1} ms", view.result.elapsed.as_secs_f64() * 1000.0));
            });
            ui.add_space(8.0);
            ui.label(caption("Atualização"));
            ui.label(
                RichText::new("Os dados vêm do pipeline Python (src/etl_datajud.py). Após uma nova ingestão, gere a base novamente:")
                    .size(12.0)
                    .color(COLOR_TEXT_SECONDARY),
            );
            command_box(ui, EXPORT_COMMAND);
        });
    view.about_open = open;
}
