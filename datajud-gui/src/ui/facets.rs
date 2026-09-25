use std::collections::BTreeSet;

use eframe::egui::{self, CornerRadius, RichText, Sense};

use crate::app::View;
use crate::data::query::Facet;
use crate::data::store::{Dataset, Sym};
use crate::model::{ConflictCategory, Tribunal, fold, format_count, grau_label};
use crate::theme::{
    self, COLOR_BG_SUBTLE, COLOR_BORDER_STRONG, COLOR_PRIMARY, COLOR_TEXT_MUTED,
    COLOR_TEXT_SECONDARY, caption, category_color,
};

const LONG_LIST_PREVIEW: usize = 8;

pub fn show(ui: &mut egui::Ui, ds: &Dataset, view: &mut View) {
    egui::ScrollArea::vertical()
        .auto_shrink([false, false])
        .show(ui, |ui| {
            ui.spacing_mut().item_spacing.y = 2.0;

            section(ui, view, "Tribunal", Facet::Tribunal, |ui, view| {
                for t in Tribunal::ALL {
                    let checked = view.filters.tribunais.contains(&t);
                    let count = view.result.counts.tribunal[t as usize];
                    let label = format!("{} · {}", t.code(), t.description());
                    if theme::facet_option(ui, checked, &label, count, None).clicked() {
                        toggle(&mut view.filters.tribunais, t);
                        view.touch();
                    }
                }
            });

            section(ui, view, "Categoria", Facet::Categoria, |ui, view| {
                for cat in ConflictCategory::ALL {
                    let checked = view.filters.categorias.contains(&cat);
                    let count = view.result.counts.categoria[cat as usize];
                    let resp = theme::facet_option(
                        ui,
                        checked,
                        cat.short_label(),
                        count,
                        Some(category_color(cat)),
                    )
                    .on_hover_text(cat.label());
                    if resp.clicked() {
                        toggle(&mut view.filters.categorias, cat);
                        view.touch();
                    }
                }
            });

            section(ui, view, "Grau / instância", Facet::Grau, |ui, view| {
                let mut graus: Vec<(Sym, u32)> = ds
                    .graus
                    .iter()
                    .map(|&s| (s, view.result.counts.grau[s.index()]))
                    .collect();
                graus.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(&b.0)));
                for (sym, count) in graus {
                    let code = ds.str(sym);
                    let checked = view.filters.graus.contains(code);
                    if theme::facet_option(ui, checked, grau_label(code), count, None).clicked() {
                        toggle(&mut view.filters.graus, code.to_string());
                        view.touch();
                    }
                }
            });

            section(ui, view, "Ano de ajuizamento", Facet::Ano, |ui, view| {
                year_facet(ui, ds, view)
            });

            section(ui, view, "Município", Facet::Municipio, |ui, view| {
                long_list(
                    ui,
                    ds,
                    view,
                    "municipio",
                    &ds.municipios,
                    |v| &mut v.filters.municipios,
                    |v, s| v.result.counts.municipio[s.index()],
                );
            });

            section(ui, view, "Classe processual", Facet::Classe, |ui, view| {
                long_list(
                    ui,
                    ds,
                    view,
                    "classe",
                    &ds.classes,
                    |v| &mut v.filters.classes,
                    |v, s| v.result.counts.classe[s.index()],
                );
            });
        });
}

fn toggle<T: Ord>(set: &mut BTreeSet<T>, value: T) {
    if !set.remove(&value) {
        set.insert(value);
    }
}

fn section(
    ui: &mut egui::Ui,
    view: &mut View,
    title: &str,
    facet: Facet,
    body: impl FnOnce(&mut egui::Ui, &mut View),
) {
    ui.add_space(6.0);
    ui.horizontal(|ui| {
        ui.label(caption(title));
        if view.filters.facet_active(facet) {
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                if theme::link_button(ui, "limpar")
                    .on_hover_text("Remover este filtro")
                    .clicked()
                {
                    view.filters.clear_facet(facet);
                    view.touch();
                }
            });
        }
    });
    ui.add_space(2.0);
    body(ui, view);
    ui.add_space(8.0);
    ui.separator();
}

fn long_list(
    ui: &mut egui::Ui,
    ds: &Dataset,
    view: &mut View,
    key: &'static str,
    domain: &[Sym],
    selected: impl Fn(&mut View) -> &mut BTreeSet<String>,
    count: impl Fn(&View, Sym) -> u32,
) {
    let (expanded, search) = {
        let state = view.facet_lists.entry(key).or_default();
        (state.expanded, fold(state.search.trim()))
    };

    let mut items: Vec<(Sym, u32, bool)> = domain
        .iter()
        .map(|&s| (s, count(view, s), selected(view).contains(ds.str(s))))
        .collect();
    items.sort_by(|a, b| {
        b.2.cmp(&a.2)
            .then(b.1.cmp(&a.1))
            .then(ds.str(a.0).cmp(ds.str(b.0)))
    });

    if expanded {
        let state = view.facet_lists.get_mut(key).expect("facet list state");
        ui.add(
            egui::TextEdit::singleline(&mut state.search)
                .hint_text("Filtrar lista…")
                .desired_width(f32::INFINITY),
        );
        ui.add_space(2.0);
        if !search.is_empty() {
            let folded = ds.strings.folded();
            items.retain(|(s, _, checked)| *checked || folded[s.index()].contains(search.as_str()));
        }
    } else {
        let n_selected = items.iter().filter(|i| i.2).count();
        items.truncate(LONG_LIST_PREVIEW.max(n_selected));
    }

    let mut clicked: Option<Sym> = None;
    let mut render = |ui: &mut egui::Ui| {
        for &(sym, n, checked) in &items {
            if theme::facet_option(ui, checked, ds.str(sym), n, None).clicked() {
                clicked = Some(sym);
            }
        }
        if items.is_empty() {
            ui.label(
                RichText::new("Nenhum valor encontrado.")
                    .size(11.5)
                    .color(COLOR_TEXT_MUTED),
            );
        }
    };
    if expanded {
        egui::ScrollArea::vertical()
            .id_salt(("facet_list", key))
            .max_height(260.0)
            .auto_shrink([false, true])
            .show(ui, |ui| render(ui));
    } else {
        render(ui);
    }

    if let Some(sym) = clicked {
        toggle(selected(view), ds.str(sym).to_string());
        view.touch();
    }

    if domain.len() > LONG_LIST_PREVIEW {
        ui.add_space(2.0);
        let label = if expanded {
            "Mostrar menos".to_string()
        } else {
            format!("Mostrar todos ({})", format_count(domain.len()))
        };
        if theme::link_button(ui, &label).clicked() {
            let state = view.facet_lists.get_mut(key).expect("facet list state");
            state.expanded = !state.expanded;
            state.search.clear();
        }
    }
}

fn year_facet(ui: &mut egui::Ui, ds: &Dataset, view: &mut View) {
    let (lo, hi) = ds.year_range;
    if lo == 0 {
        ui.label(
            RichText::new("Sem datas na base.")
                .size(11.5)
                .color(COLOR_TEXT_MUTED),
        );
        return;
    }

    histogram(ui, ds, view);
    ui.add_space(4.0);

    let mut from = view.filters.ano_min.unwrap_or(lo);
    let mut to = view.filters.ano_max.unwrap_or(hi);
    let mut changed = false;
    ui.horizontal(|ui| {
        ui.label(RichText::new("De").size(12.0).color(COLOR_TEXT_SECONDARY));
        changed |= ui
            .add(egui::DragValue::new(&mut from).range(lo..=hi).speed(0.2))
            .changed();
        ui.label(RichText::new("até").size(12.0).color(COLOR_TEXT_SECONDARY));
        changed |= ui
            .add(egui::DragValue::new(&mut to).range(lo..=hi).speed(0.2))
            .changed();
    });
    if changed {
        if from > to {
            std::mem::swap(&mut from, &mut to);
        }
        set_year_range(view, ds, from, to);
    }

    ui.horizontal_wrapped(|ui| {
        let presets = [
            ("Últimos 5 anos", hi.saturating_sub(4)),
            ("Desde 2020", 2020),
            ("Desde 2010", 2010),
        ];
        for (label, start) in presets {
            if start >= lo && theme::link_button(ui, label).clicked() {
                set_year_range(view, ds, start, hi);
            }
        }
    });
}

fn set_year_range(view: &mut View, ds: &Dataset, from: u16, to: u16) {
    let (lo, hi) = ds.year_range;
    view.filters.ano_min = (from > lo).then_some(from);
    view.filters.ano_max = (to < hi).then_some(to);
    view.touch();
}

fn histogram(ui: &mut egui::Ui, ds: &Dataset, view: &mut View) {
    let (lo, hi) = ds.year_range;
    let counts = &view.result.counts.ano;
    let max = counts.iter().copied().max().unwrap_or(0).max(1) as f32;
    let width = ui.available_width();
    let height = 44.0;
    let (rect, response) = ui.allocate_exact_size(egui::vec2(width, height), Sense::click());
    let painter = ui.painter_at(rect);
    painter.rect_filled(rect, CornerRadius::same(4), COLOR_BG_SUBTLE);

    let n = counts.len().max(1);
    let bar_w = rect.width() / n as f32;
    let sel_lo = view.filters.ano_min.unwrap_or(lo);
    let sel_hi = view.filters.ano_max.unwrap_or(hi);
    let hover_year = response
        .hover_pos()
        .map(|p| lo + (((p.x - rect.min.x) / bar_w).floor() as usize).min(n - 1) as u16);

    for (i, &c) in counts.iter().enumerate() {
        let year = lo + i as u16;
        let h = if c == 0 {
            0.0
        } else {
            ((c as f32 / max).sqrt() * (height - 4.0)).max(1.5)
        };
        let x0 = rect.min.x + i as f32 * bar_w;
        let bar = egui::Rect::from_min_max(
            egui::pos2(x0 + 0.5, rect.max.y - 2.0 - h),
            egui::pos2(x0 + bar_w - 0.5, rect.max.y - 2.0),
        );
        let in_range = year >= sel_lo && year <= sel_hi;
        let color = if hover_year == Some(year) {
            COLOR_TEXT_SECONDARY
        } else if in_range {
            COLOR_PRIMARY
        } else {
            COLOR_BORDER_STRONG
        };
        painter.rect_filled(bar, CornerRadius::ZERO, color);
    }

    if let Some(year) = hover_year {
        ui.ctx().set_cursor_icon(egui::CursorIcon::PointingHand);
        let c = counts.get((year - lo) as usize).copied().unwrap_or(0);
        response.clone().on_hover_text(format!(
            "{year}: {} processos\nClique para filtrar este ano · Shift+clique para estender",
            format_count(c as usize)
        ));
    }
    if response.clicked()
        && let Some(year) = hover_year
    {
        let extend = ui.input(|i| i.modifiers.shift) && view.filters.facet_active(Facet::Ano);
        if extend {
            set_year_range(view, ds, sel_lo.min(year), sel_hi.max(year));
        } else if view.filters.ano_min == Some(year) && view.filters.ano_max == Some(year) {
            view.filters.clear_facet(Facet::Ano);
            view.touch();
        } else {
            view.filters.ano_min = Some(year);
            view.filters.ano_max = Some(year);
            view.touch();
        }
    }
    ui.horizontal(|ui| {
        ui.label(
            RichText::new(lo.to_string())
                .size(10.5)
                .color(COLOR_TEXT_MUTED),
        );
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
            ui.label(
                RichText::new(hi.to_string())
                    .size(10.5)
                    .color(COLOR_TEXT_MUTED),
            );
        });
    });
}
