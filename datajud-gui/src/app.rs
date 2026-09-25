use std::collections::HashMap;
use std::sync::mpsc::{Receiver, channel};
use std::time::{Duration, Instant};

use eframe::egui;
use serde::{Deserialize, Serialize};

use crate::data::export::{self, ExportFormat};
use crate::data::query::{self, Filters, QueryResult, Sort};
use crate::data::source::{self, Source};
use crate::data::store::{self, Dataset};
use crate::model::format_count;
use crate::theme::COLOR_BG_CARD;
use crate::ui;

const SEARCH_DEBOUNCE: Duration = Duration::from_millis(150);
const INFO_NOTICE_TTL: Duration = Duration::from_secs(5);

pub enum LoadState {
    Loading(Source),
    Missing,
    Failed(String),
    Ready(Box<Dataset>),
}

pub enum Action {
    OpenBase,
    Reload,
    Export(ExportFormat),
    Notify(String),
}

pub struct Notice {
    pub text: String,
    pub is_error: bool,
    pub shown_at: Instant,
}

#[derive(Default)]
pub struct FacetListUi {
    pub expanded: bool,
    pub search: String,
}

#[derive(Default)]
pub struct View {
    pub filters: Filters,
    pub sort: Sort,
    pub result: QueryResult,
    pub dirty: bool,
    pub resort: bool,
    pub text_edited_at: Option<Instant>,
    pub selected: Option<u32>,
    pub scroll_to_selected: bool,
    pub focus_search: bool,
    pub about_open: bool,
    pub facet_lists: HashMap<&'static str, FacetListUi>,
    pub actions: Vec<Action>,
}

impl View {
    pub fn touch(&mut self) {
        self.dirty = true;
    }

    pub fn clear_filters(&mut self) {
        self.filters = Filters::default();
        self.text_edited_at = None;
        self.dirty = true;
    }

    pub fn select(&mut self, row: Option<u32>, scroll: bool) {
        self.selected = row;
        self.scroll_to_selected = scroll && row.is_some();
    }

    fn move_selection(&mut self, delta: isize) {
        let visible = &self.result.visible;
        if visible.is_empty() {
            return;
        }
        let pos = self
            .selected
            .and_then(|s| visible.iter().position(|&r| r == s))
            .map(|p| (p as isize + delta).clamp(0, visible.len() as isize - 1) as usize)
            .unwrap_or(0);
        self.select(Some(visible[pos]), true);
    }
}

#[derive(Serialize, Deserialize, Default)]
#[serde(default)]
struct Prefs {
    filters: Filters,
    sort: Sort,
}

pub struct DataJudApp {
    state: LoadState,
    loader: Option<Receiver<Result<Dataset, String>>>,
    view: View,
    notice: Option<Notice>,
}

impl DataJudApp {
    pub fn new(cc: &eframe::CreationContext<'_>) -> Self {
        let prefs: Prefs = cc
            .storage
            .and_then(|s| eframe::get_value(s, eframe::APP_KEY))
            .unwrap_or_default();

        let mut app = Self {
            state: LoadState::Missing,
            loader: None,
            view: View {
                filters: prefs.filters,
                sort: prefs.sort,
                ..Default::default()
            },
            notice: None,
        };
        if let Some(src) = source::resolve() {
            app.start_load(&cc.egui_ctx, src);
        }
        app
    }

    fn start_load(&mut self, ctx: &egui::Context, src: Source) {
        let (tx, rx) = channel();
        let ctx = ctx.clone();
        let thread_src = src.clone();
        std::thread::spawn(move || {
            let _ = tx.send(store::load(thread_src));
            ctx.request_repaint();
        });
        self.loader = Some(rx);
        self.state = LoadState::Loading(src);
    }

    fn poll_loader(&mut self) {
        let Some(rx) = &self.loader else { return };
        let Ok(result) = rx.try_recv() else { return };
        self.loader = None;
        match result {
            Ok(ds) => {
                self.view.selected = None;
                self.view.dirty = true;
                self.state = LoadState::Ready(Box::new(ds));
            }
            Err(err) => self.state = LoadState::Failed(err),
        }
    }

    fn notify(&mut self, text: String, is_error: bool) {
        self.notice = Some(Notice {
            text,
            is_error,
            shown_at: Instant::now(),
        });
    }

    fn refresh_results(&mut self, ctx: &egui::Context) {
        let LoadState::Ready(ds) = &self.state else {
            return;
        };
        let view = &mut self.view;

        if let Some(at) = view.text_edited_at {
            let waited = at.elapsed();
            if waited >= SEARCH_DEBOUNCE {
                view.text_edited_at = None;
                view.dirty = true;
            } else {
                ctx.request_repaint_after(SEARCH_DEBOUNCE - waited);
            }
        }

        if view.dirty {
            view.result = query::compute(ds, &view.filters, view.sort);
            view.dirty = false;
            view.resort = false;
        } else if view.resort {
            let started = Instant::now();
            query::sort_rows(ds, &mut view.result.visible, view.sort);
            view.result.elapsed = started.elapsed();
            view.resort = false;
        }
    }

    fn handle_shortcuts(&mut self, ctx: &egui::Context) {
        let typing = ctx.wants_keyboard_input();
        let (find, esc, up, down) = ctx.input(|i| {
            (
                i.modifiers.command && i.key_pressed(egui::Key::F),
                i.key_pressed(egui::Key::Escape),
                i.key_pressed(egui::Key::ArrowUp),
                i.key_pressed(egui::Key::ArrowDown),
            )
        });
        if find {
            self.view.focus_search = true;
        }
        if typing {
            return;
        }
        if esc && self.view.selected.is_some() {
            self.view.select(None, false);
        }
        if up {
            self.view.move_selection(-1);
        }
        if down {
            self.view.move_selection(1);
        }
    }

    fn run_actions(&mut self, ctx: &egui::Context) {
        for action in std::mem::take(&mut self.view.actions) {
            match action {
                Action::OpenBase => {
                    let picked = rfd::FileDialog::new()
                        .set_title("Abrir base DataJud")
                        .add_filter("Base SQLite", &["sqlite", "db", "sqlite3"])
                        .pick_file();
                    if let Some(path) = picked {
                        self.start_load(ctx, Source::File(path));
                    }
                }
                Action::Reload => {
                    let src = match &self.state {
                        LoadState::Ready(ds) => Some(ds.source.clone()),
                        _ => source::resolve(),
                    };
                    match src {
                        Some(src) => self.start_load(ctx, src),
                        None => self.state = LoadState::Missing,
                    }
                }
                Action::Export(format) => self.export(format),
                Action::Notify(text) => self.notify(text, false),
            }
        }
    }

    fn export(&mut self, format: ExportFormat) {
        let LoadState::Ready(ds) = &self.state else {
            return;
        };
        let rows = &self.view.result.visible;
        if rows.is_empty() {
            return;
        }
        let default_name = format!("datajud_pe_{}_processos.{}", rows.len(), format.extension());
        let Some(path) = rfd::FileDialog::new()
            .set_file_name(&default_name)
            .add_filter(format.filter_name(), &[format.extension()])
            .save_file()
        else {
            return;
        };
        match export::write(ds, rows, format, &path) {
            Ok(n) => self.notify(
                format!(
                    "{} processos exportados para {}",
                    format_count(n),
                    path.display()
                ),
                false,
            ),
            Err(err) => self.notify(err, true),
        }
    }

    fn show_notice(&mut self, ctx: &egui::Context) {
        let Some(notice) = &self.notice else { return };
        if !notice.is_error {
            let age = notice.shown_at.elapsed();
            if age >= INFO_NOTICE_TTL {
                self.notice = None;
                return;
            }
            ctx.request_repaint_after(INFO_NOTICE_TTL - age);
        }
        if ui::states::notice_bar(ctx, notice) {
            self.notice = None;
        }
    }
}

impl eframe::App for DataJudApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        self.poll_loader();
        self.handle_shortcuts(ctx);
        self.refresh_results(ctx);

        let ds = match &self.state {
            LoadState::Ready(ds) => Some(ds.as_ref()),
            _ => None,
        };

        ui::top_bar::show(ctx, ds, &mut self.view);
        self.show_notice(ctx);

        match &self.state {
            LoadState::Ready(ds) => {
                egui::SidePanel::left("facets")
                    .resizable(true)
                    .default_width(270.0)
                    .width_range(220.0..=420.0)
                    .frame(panel_frame())
                    .show(ctx, |ui| ui::facets::show(ui, ds, &mut self.view));

                if self.view.selected.is_some() {
                    egui::SidePanel::right("detail")
                        .resizable(true)
                        .default_width(380.0)
                        .width_range(300.0..=640.0)
                        .frame(panel_frame())
                        .show(ctx, |ui| ui::detail::show(ui, ds, &mut self.view));
                }

                egui::CentralPanel::default()
                    .frame(
                        egui::Frame::NONE
                            .fill(COLOR_BG_CARD)
                            .inner_margin(egui::Margin {
                                left: 16,
                                right: 2,
                                top: 12,
                                bottom: 12,
                            }),
                    )
                    .show(ctx, |ui| ui::table::show(ui, ds, &mut self.view));

                ui::states::about_window(ctx, ds, &mut self.view);
            }
            LoadState::Loading(src) => {
                egui::CentralPanel::default().show(ctx, |ui| ui::states::loading(ui, src));
            }
            LoadState::Missing => {
                egui::CentralPanel::default()
                    .show(ctx, |ui| ui::states::missing(ui, &mut self.view));
            }
            LoadState::Failed(err) => {
                let err = err.clone();
                egui::CentralPanel::default()
                    .show(ctx, |ui| ui::states::failed(ui, &err, &mut self.view));
            }
        }

        self.run_actions(ctx);
        if self.view.dirty || self.view.resort {
            ctx.request_repaint();
        }
    }

    fn save(&mut self, storage: &mut dyn eframe::Storage) {
        let prefs = Prefs {
            filters: self.view.filters.clone(),
            sort: self.view.sort,
        };
        eframe::set_value(storage, eframe::APP_KEY, &prefs);
    }
}

fn panel_frame() -> egui::Frame {
    egui::Frame::NONE
        .fill(COLOR_BG_CARD)
        .inner_margin(egui::Margin {
            left: 14,
            right: 0,
            top: 12,
            bottom: 12,
        })
}
