#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod api;
mod app;
mod model;
mod theme;

use app::DataJudApp;
use eframe::egui;
use theme::setup_institutional_theme;

fn main() -> eframe::Result<()> {
    let native_options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_title("DataJud CNJ — Extrator de Processos Fundiários")
            .with_inner_size([1020.0, 700.0])
            .with_min_inner_size([760.0, 520.0]),
        ..Default::default()
    };

    eframe::run_native(
        "DataJud CNJ — Extrator Fundiário",
        native_options,
        Box::new(|cc| {
            setup_institutional_theme(&cc.egui_ctx);
            Ok(Box::new(DataJudApp::default()))
        }),
    )
}
