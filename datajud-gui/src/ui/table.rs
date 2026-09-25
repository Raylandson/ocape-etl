use eframe::egui::{self, RichText, Sense};
use egui_extras::{Column, TableBuilder};

use crate::app::View;
use crate::data::query::{Facet, SortColumn};
use crate::data::store::Dataset;
use crate::model::{format_count, format_date, grau_label};
use crate::theme::{
    self, COLOR_TEXT_MUTED, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, Direction, ROW_HEIGHT,
    category_dot, paint_triangle,
};
use crate::ui::states;

pub fn show(ui: &mut egui::Ui, ds: &Dataset, view: &mut View) {
    summary(ui, ds, view);
    ui.add_space(6.0);

    if view.result.visible.is_empty() {
        states::no_results(ui, view);
        return;
    }
    table(ui, ds, view);
}

fn summary(ui: &mut egui::Ui, ds: &Dataset, view: &mut View) {
    ui.horizontal_wrapped(|ui| {
        let shown = view.result.visible.len();
        let total = ds.rows.len();
        let text = if shown == total {
            format!("{} processos", format_count(total))
        } else {
            format!(
                "{} de {} processos",
                format_count(shown),
                format_count(total)
            )
        };
        ui.label(
            RichText::new(text)
                .size(13.5)
                .strong()
                .color(COLOR_TEXT_PRIMARY),
        );
        if view.text_edited_at.is_some() {
            ui.spinner();
        }

        if !view.filters.is_active() {
            return;
        }
        ui.add_space(6.0);

        let f = view.filters.clone();
        if !f.text.trim().is_empty()
            && theme::filter_chip(ui, &format!("Busca: \u{201c}{}\u{201d}", f.text.trim()))
        {
            view.filters.text.clear();
            view.text_edited_at = None;
            view.touch();
        }
        for t in &f.tribunais {
            if theme::filter_chip(ui, t.code()) {
                view.filters.tribunais.remove(t);
                view.touch();
            }
        }
        for c in &f.categorias {
            if theme::filter_chip(ui, c.short_label()) {
                view.filters.categorias.remove(c);
                view.touch();
            }
        }
        for g in &f.graus {
            if theme::filter_chip(ui, grau_label(g)) {
                view.filters.graus.remove(g);
                view.touch();
            }
        }
        if f.facet_active(Facet::Ano) {
            let (lo, hi) = ds.year_range;
            let (a, b) = (f.ano_min.unwrap_or(lo), f.ano_max.unwrap_or(hi));
            let label = if a == b {
                format!("Ano: {a}")
            } else {
                format!("Ano: {a}–{b}")
            };
            if theme::filter_chip(ui, &label) {
                view.filters.clear_facet(Facet::Ano);
                view.touch();
            }
        }
        for m in &f.municipios {
            if theme::filter_chip(ui, m) {
                view.filters.municipios.remove(m);
                view.touch();
            }
        }
        for c in &f.classes {
            if theme::filter_chip(ui, c) {
                view.filters.classes.remove(c);
                view.touch();
            }
        }
        if theme::link_button(ui, "Limpar filtros").clicked() {
            view.clear_filters();
        }
    });
}

const COLUMNS: [(&str, SortColumn); 6] = [
    ("Nº do processo (CNJ)", SortColumn::Numero),
    ("Tribunal", SortColumn::Tribunal),
    ("Categoria", SortColumn::Categoria),
    ("Classe", SortColumn::Classe),
    ("Município", SortColumn::Municipio),
    ("Ajuizamento", SortColumn::Ajuizamento),
];

fn table(ui: &mut egui::Ui, ds: &Dataset, view: &mut View) {
    let visible = std::mem::take(&mut view.result.visible);
    let mut clicked: Option<u32> = None;

    egui::ScrollArea::horizontal()
        .id_salt("lawsuits_hscroll")
        .show(ui, |ui| {
            let mut builder = TableBuilder::new(ui)
                .id_salt("lawsuits_table")
                .striped(true)
                .resizable(true)
                .sense(Sense::click())
                .cell_layout(egui::Layout::left_to_right(egui::Align::Center))
                .column(Column::initial(190.0).at_least(170.0).clip(true))
                .column(Column::initial(110.0).at_least(70.0).clip(true))
                .column(Column::initial(160.0).at_least(90.0).clip(true))
                .column(Column::initial(180.0).at_least(90.0).clip(true))
                .column(Column::initial(130.0).at_least(80.0).clip(true))
                .column(Column::initial(90.0).at_least(80.0))
                .column(Column::remainder().at_least(140.0).clip(true))
                .min_scrolled_height(0.0);

            if view.scroll_to_selected {
                if let Some(pos) = view
                    .selected
                    .and_then(|s| visible.iter().position(|&r| r == s))
                {
                    builder = builder.scroll_to_row(pos, None);
                }
                view.scroll_to_selected = false;
            }

            builder
                .header(30.0, |mut header| {
                    for (label, column) in COLUMNS {
                        header.col(|ui| sort_header(ui, label, column, view));
                    }
                    header.col(|ui| {
                        sort_header(ui, "Último movimento", SortColumn::UltimoMovimento, view)
                    });
                })
                .body(|body| {
                    body.rows(ROW_HEIGHT, visible.len(), |mut row| {
                        let idx = visible[row.index()];
                        let r = &ds.rows[idx as usize];
                        row.set_selected(view.selected == Some(idx));

                        row.col(|ui| {
                            ui.label(
                                RichText::new(&*r.numero)
                                    .monospace()
                                    .color(COLOR_TEXT_PRIMARY),
                            );
                        });
                        row.col(|ui| {
                            ui.label(
                                RichText::new(r.tribunal.code())
                                    .monospace()
                                    .size(11.5)
                                    .color(COLOR_TEXT_SECONDARY),
                            );
                            ui.label(
                                RichText::new(grau_label(ds.str(r.grau)))
                                    .size(12.0)
                                    .color(COLOR_TEXT_MUTED),
                            );
                        });
                        row.col(|ui| {
                            ui.spacing_mut().item_spacing.x = 6.0;
                            category_dot(ui, r.categoria);
                            ui.label(RichText::new(r.categoria.short_label()).size(12.5))
                                .on_hover_text(r.categoria.label());
                        });
                        row.col(|ui| {
                            ui.label(RichText::new(ds.str(r.classe)).size(12.5));
                        });
                        row.col(|ui| {
                            ui.label(RichText::new(ds.str(r.municipio)).size(12.5));
                        });
                        row.col(|ui| {
                            ui.label(
                                RichText::new(format_date(r.ajuizamento))
                                    .size(12.5)
                                    .color(COLOR_TEXT_SECONDARY),
                            );
                        });
                        row.col(|ui| {
                            if r.ultimo_mov_data.is_some() {
                                ui.label(
                                    RichText::new(format_date(r.ultimo_mov_data))
                                        .size(12.5)
                                        .color(COLOR_TEXT_SECONDARY),
                                );
                            }
                            ui.label(
                                RichText::new(ds.str(r.ultimo_mov))
                                    .size(12.0)
                                    .color(COLOR_TEXT_MUTED),
                            );
                        });

                        let response = row.response();
                        if response.hovered() {
                            response.ctx.set_cursor_icon(egui::CursorIcon::PointingHand);
                        }
                        if response.clicked() {
                            clicked = Some(idx);
                        }
                    });
                });
        });

    view.result.visible = visible;
    if let Some(idx) = clicked {
        let next = (view.selected != Some(idx)).then_some(idx);
        view.select(next, false);
    }
}

fn sort_header(ui: &mut egui::Ui, label: &str, column: SortColumn, view: &mut View) {
    let active = view.sort.column == column;
    let color = if active {
        COLOR_TEXT_PRIMARY
    } else {
        COLOR_TEXT_MUTED
    };
    let response = ui
        .add(
            egui::Label::new(RichText::new(label).size(12.0).strong().color(color))
                .sense(Sense::click()),
        )
        .on_hover_text("Ordenar por esta coluna");
    if active {
        let (rect, _) = ui.allocate_exact_size(egui::vec2(10.0, 10.0), Sense::hover());
        let dir = if view.sort.descending {
            Direction::Down
        } else {
            Direction::Up
        };
        paint_triangle(ui.painter(), rect.center(), 8.0, dir, COLOR_TEXT_PRIMARY);
    }
    if response.hovered() {
        ui.ctx().set_cursor_icon(egui::CursorIcon::PointingHand);
    }
    if response.clicked() {
        view.sort = view.sort.toggled(column);
        view.resort = true;
    }
}
