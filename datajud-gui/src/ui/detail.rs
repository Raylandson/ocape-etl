use eframe::egui::{self, RichText};

use crate::app::{Action, View};
use crate::data::export::row_json;
use crate::data::store::{Dataset, Lawsuit};
use crate::model::{format_count, format_date, grau_label};
use crate::theme::{
    self, COLOR_TEXT_MUTED, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, caption, category_badge,
    tribunal_badge,
};

pub fn show(ui: &mut egui::Ui, ds: &Dataset, view: &mut View) {
    let Some(idx) = view.selected else { return };
    let r = &ds.rows[idx as usize];

    header(ui, ds, view, r);
    ui.add_space(8.0);

    egui::ScrollArea::vertical()
        .auto_shrink([false, false])
        .show(ui, |ui| {
            ui.spacing_mut().item_spacing.y = 4.0;

            ui.label(caption("Dados do processo"));
            theme::detail_box(ui, |ui| {
                ui.spacing_mut().item_spacing.y = 7.0;
                kv(ui, "Classe", ds.str(r.classe), r.classe_codigo);
                kv(ui, "Órgão julgador", ds.str(r.orgao), r.orgao_codigo);
                kv(ui, "Jurisdição", ds.str(r.tipo_jurisdicao), None);
                kv(ui, "Município", ds.str(r.municipio), r.municipio_ibge);
                kv(
                    ui,
                    "Comarca sede",
                    ds.str(r.comarca_sede),
                    r.comarca_sede_ibge,
                );
                let abrangidos = ds.str(r.municipios_abrangidos);
                if !abrangidos.is_empty() && abrangidos != ds.str(r.comarca_sede) {
                    kv(ui, "Abrange", abrangidos, None);
                }
                kv(ui, "Ajuizamento", &format_date(r.ajuizamento), None);
                let ultimo = match (r.ultimo_mov_data, ds.str(r.ultimo_mov)) {
                    (None, "") => "—".to_string(),
                    (d, "") => format_date(d),
                    (None, m) => m.to_string(),
                    (d, m) => format!("{} · {m}", format_date(d)),
                };
                kv(ui, "Último movimento", &ultimo, None);
                kv(ui, "Movimentos", &format_count(r.total_mov as usize), None);
                if let (Some(lat), Some(lon)) = (r.lat, r.lon) {
                    kv(ui, "Coordenadas", &format!("{lat:.5}, {lon:.5}"), None);
                }
            });

            ui.add_space(10.0);
            ui.label(caption(&format!("Assuntos ({})", r.assuntos.len())));
            theme::detail_box(ui, |ui| {
                if r.assuntos.is_empty() {
                    ui.label(RichText::new("Nenhum assunto informado.").color(COLOR_TEXT_MUTED));
                }
                for &(code, name) in r.assuntos.iter() {
                    ui.horizontal_top(|ui| {
                        let code = if code == 0 {
                            "—".to_string()
                        } else {
                            code.to_string()
                        };
                        ui.add_sized(
                            [52.0, 16.0],
                            egui::Label::new(
                                RichText::new(code)
                                    .monospace()
                                    .size(11.5)
                                    .color(COLOR_TEXT_MUTED),
                            ),
                        );
                        ui.add(egui::Label::new(RichText::new(ds.str(name)).size(12.5)).wrap());
                    });
                }
            });

            let siblings: Vec<u32> = ds.siblings_of(idx).collect();
            if !siblings.is_empty() {
                ui.add_space(10.0);
                ui.label(caption(&format!(
                    "Outras instâncias do mesmo número ({})",
                    siblings.len()
                )));
                theme::detail_box(ui, |ui| {
                    for s in siblings {
                        if sibling_row(ui, ds, &ds.rows[s as usize]).clicked() {
                            view.select(Some(s), true);
                        }
                    }
                });
            }

            ui.add_space(12.0);
            ui.horizontal_wrapped(|ui| {
                if ui
                    .button("Copiar JSON")
                    .on_hover_text("Copia todos os campos deste processo")
                    .clicked()
                {
                    ui.ctx().copy_text(row_json(ds, idx));
                    view.actions
                        .push(Action::Notify("JSON do processo copiado.".to_string()));
                }
                let url = ds.str(r.url);
                if !url.is_empty()
                    && ui
                        .button("Consulta pública (PJe)")
                        .on_hover_text(
                            "Copia o número e abre a consulta pública do tribunal no navegador",
                        )
                        .clicked()
                {
                    ui.ctx().copy_text(r.numero.to_string());
                    ui.ctx().open_url(egui::OpenUrl::new_tab(url));
                    view.actions.push(Action::Notify(format!(
                        "Número {} copiado; cole-o na consulta pública.",
                        r.numero
                    )));
                }
            });
        });
}

fn header(ui: &mut egui::Ui, ds: &Dataset, view: &mut View, r: &Lawsuit) {
    ui.horizontal(|ui| {
        ui.label(caption("Processo"));
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
            if theme::close_button(ui, "Fechar (Esc)").clicked() {
                view.select(None, false);
            }
        });
    });
    ui.horizontal(|ui| {
        ui.label(
            RichText::new(&*r.numero)
                .monospace()
                .size(15.0)
                .strong()
                .color(COLOR_TEXT_PRIMARY),
        );
        if ui
            .small_button("Copiar")
            .on_hover_text("Copiar número do processo")
            .clicked()
        {
            ui.ctx().copy_text(r.numero.to_string());
            view.actions
                .push(Action::Notify(format!("Número {} copiado.", r.numero)));
        }
    });
    ui.horizontal_wrapped(|ui| {
        tribunal_badge(ui, r.tribunal);
        ui.label(
            RichText::new(grau_label(ds.str(r.grau)))
                .size(12.0)
                .color(COLOR_TEXT_SECONDARY),
        );
        category_badge(ui, r.categoria);
    });
}

fn kv(ui: &mut egui::Ui, key: &str, value: &str, code: Option<i32>) {
    const KEY_WIDTH: f32 = 112.0;
    ui.horizontal_top(|ui| {
        ui.allocate_ui_with_layout(
            egui::vec2(KEY_WIDTH, 0.0),
            egui::Layout::top_down(egui::Align::Min),
            |ui| {
                ui.set_width(KEY_WIDTH);
                ui.label(RichText::new(key).size(12.0).color(COLOR_TEXT_MUTED));
            },
        );
        let mut job = egui::text::LayoutJob::default();
        let body = egui::TextFormat {
            font_id: egui::FontId::proportional(12.5),
            color: COLOR_TEXT_PRIMARY,
            ..Default::default()
        };
        job.append(if value.is_empty() { "—" } else { value }, 0.0, body);
        if let Some(code) = code {
            let mono = egui::TextFormat {
                font_id: egui::FontId::monospace(11.0),
                color: COLOR_TEXT_MUTED,
                valign: egui::Align::Center,
                ..Default::default()
            };
            job.append(&code.to_string(), 8.0, mono);
        }
        ui.add(egui::Label::new(job).wrap());
    });
}

fn sibling_row(ui: &mut egui::Ui, ds: &Dataset, r: &Lawsuit) -> egui::Response {
    let text = format!(
        "{} · {} · {} · {}",
        r.tribunal.code(),
        grau_label(ds.str(r.grau)),
        format_date(r.ajuizamento),
        ds.str(r.classe)
    );
    let response = ui.selectable_label(
        false,
        RichText::new(text).size(12.5).color(COLOR_TEXT_SECONDARY),
    );
    if response.hovered() {
        ui.ctx().set_cursor_icon(egui::CursorIcon::PointingHand);
    }
    response.on_hover_text("Abrir esta instância")
}
