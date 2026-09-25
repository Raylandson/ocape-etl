#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod app;
mod data;
mod model;
mod theme;
mod ui;

use app::DataJudApp;
use eframe::egui;
use theme::setup_institutional_theme;

fn main() -> eframe::Result<()> {
    let native_options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_title("DataJud · Pernambuco — Processos Fundiários")
            .with_inner_size([1360.0, 820.0])
            .with_min_inner_size([960.0, 560.0]),
        ..Default::default()
    };

    eframe::run_native(
        "datajud-gui",
        native_options,
        Box::new(|cc| {
            setup_institutional_theme(&cc.egui_ctx);
            Ok(Box::new(DataJudApp::new(cc)))
        }),
    )
}
