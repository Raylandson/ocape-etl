use eframe::egui::{
    self, Color32, CornerRadius, FontId, Rect, RichText, Sense, Stroke, TextStyle, TextWrapMode,
    Vec2, WidgetText,
};

use crate::model::{ConflictCategory, Tribunal};

pub const COLOR_BG_CANVAS: Color32 = Color32::from_rgb(248, 250, 252); // slate-50
pub const COLOR_BG_CARD: Color32 = Color32::from_rgb(255, 255, 255);
pub const COLOR_BG_SUBTLE: Color32 = Color32::from_rgb(241, 245, 249); // slate-100
pub const COLOR_BORDER: Color32 = Color32::from_rgb(226, 232, 240); // slate-200
pub const COLOR_BORDER_STRONG: Color32 = Color32::from_rgb(203, 213, 225); // slate-300
pub const COLOR_TEXT_PRIMARY: Color32 = Color32::from_rgb(15, 23, 42); // slate-900
pub const COLOR_TEXT_SECONDARY: Color32 = Color32::from_rgb(51, 65, 85); // slate-700
pub const COLOR_TEXT_MUTED: Color32 = Color32::from_rgb(100, 116, 139); // slate-500
pub const COLOR_TEXT_DISABLED: Color32 = Color32::from_rgb(148, 163, 184); // slate-400
pub const COLOR_PRIMARY: Color32 = Color32::from_rgb(15, 23, 42); // slate-900
pub const COLOR_SELECTION_BG: Color32 = Color32::from_rgb(226, 232, 240); // slate-200
pub const COLOR_DANGER: Color32 = Color32::from_rgb(185, 28, 28); // red-700
pub const COLOR_DANGER_BG: Color32 = Color32::from_rgb(254, 242, 242); // red-50

pub const ROW_HEIGHT: f32 = 28.0;

pub fn stroke(width: f32, color: Color32) -> Stroke {
    Stroke::new(width, color)
}

pub fn setup_institutional_theme(ctx: &egui::Context) {
    let mut visuals = egui::Visuals::light();

    visuals.override_text_color = Some(COLOR_TEXT_PRIMARY);
    visuals.panel_fill = COLOR_BG_CANVAS;
    visuals.window_fill = COLOR_BG_CARD;
    visuals.window_stroke = stroke(1.0, COLOR_BORDER);
    visuals.window_corner_radius = CornerRadius::same(8);
    visuals.menu_corner_radius = CornerRadius::same(6);
    visuals.faint_bg_color = COLOR_BG_CANVAS;
    visuals.extreme_bg_color = COLOR_BG_CARD;

    let w = &mut visuals.widgets;
    w.noninteractive.bg_fill = COLOR_BG_CARD;
    w.noninteractive.bg_stroke = stroke(1.0, COLOR_BORDER);
    w.noninteractive.corner_radius = CornerRadius::same(6);
    w.noninteractive.fg_stroke = stroke(1.0, COLOR_TEXT_PRIMARY);

    w.inactive.bg_fill = COLOR_BORDER_STRONG;
    w.inactive.weak_bg_fill = COLOR_BG_CARD;
    w.inactive.bg_stroke = stroke(1.0, COLOR_BORDER_STRONG);
    w.inactive.corner_radius = CornerRadius::same(6);
    w.inactive.fg_stroke = stroke(1.0, COLOR_TEXT_PRIMARY);

    w.hovered.bg_fill = COLOR_TEXT_DISABLED;
    w.hovered.weak_bg_fill = COLOR_BG_SUBTLE;
    w.hovered.bg_stroke = stroke(1.0, COLOR_TEXT_DISABLED);
    w.hovered.corner_radius = CornerRadius::same(6);
    w.hovered.fg_stroke = stroke(1.0, COLOR_TEXT_PRIMARY);

    w.active.bg_fill = COLOR_TEXT_MUTED;
    w.active.weak_bg_fill = COLOR_BORDER;
    w.active.bg_stroke = stroke(1.0, COLOR_TEXT_MUTED);
    w.active.corner_radius = CornerRadius::same(6);
    w.active.fg_stroke = stroke(1.0, COLOR_TEXT_PRIMARY);

    w.open = w.hovered;

    visuals.selection.bg_fill = COLOR_SELECTION_BG;
    visuals.selection.stroke = stroke(1.0, COLOR_TEXT_PRIMARY);
    visuals.text_cursor.stroke = stroke(1.5, COLOR_TEXT_PRIMARY);

    ctx.set_visuals(visuals);
    ctx.all_styles_mut(|style| {
        style.spacing.item_spacing = egui::vec2(8.0, 6.0);
        style.spacing.button_padding = egui::vec2(10.0, 5.0);
        style.spacing.interact_size.y = 26.0;
        style.spacing.scroll = egui::style::ScrollStyle {
            bar_inner_margin: 6.0,
            bar_outer_margin: 2.0,
            dormant_handle_opacity: 0.7,
            active_handle_opacity: 1.0,
            interact_handle_opacity: 1.0,
            ..egui::style::ScrollStyle::solid()
        };
        style
            .text_styles
            .insert(TextStyle::Body, FontId::proportional(13.0));
        style
            .text_styles
            .insert(TextStyle::Button, FontId::proportional(13.0));
        style
            .text_styles
            .insert(TextStyle::Small, FontId::proportional(11.0));
        style
            .text_styles
            .insert(TextStyle::Monospace, FontId::monospace(12.5));
        style
            .text_styles
            .insert(TextStyle::Heading, FontId::proportional(16.0));
    });
}

pub fn category_color(cat: ConflictCategory) -> Color32 {
    let [r, g, b] = cat.color_rgb();
    Color32::from_rgb(r, g, b)
}

pub fn caption(text: &str) -> RichText {
    RichText::new(text.to_uppercase())
        .size(11.0)
        .strong()
        .color(COLOR_TEXT_MUTED)
}

fn truncated(
    ui: &egui::Ui,
    text: impl Into<WidgetText>,
    width: f32,
) -> std::sync::Arc<egui::Galley> {
    text.into()
        .into_galley(ui, Some(TextWrapMode::Truncate), width, TextStyle::Body)
}

#[derive(Clone, Copy)]
pub enum Direction {
    Up,
    Down,
}

pub fn paint_triangle(
    painter: &egui::Painter,
    center: egui::Pos2,
    size: f32,
    dir: Direction,
    color: Color32,
) {
    let h = size * 0.5;
    let points = match dir {
        Direction::Up => vec![
            center + egui::vec2(-h, h * 0.6),
            center + egui::vec2(h, h * 0.6),
            center + egui::vec2(0.0, -h * 0.6),
        ],
        Direction::Down => vec![
            center + egui::vec2(-h, -h * 0.6),
            center + egui::vec2(h, -h * 0.6),
            center + egui::vec2(0.0, h * 0.6),
        ],
    };
    painter.add(egui::Shape::convex_polygon(points, color, Stroke::NONE));
}

pub fn paint_cross(painter: &egui::Painter, center: egui::Pos2, size: f32, color: Color32) {
    let a = size * 0.5;
    let stroke = stroke(1.4, color);
    painter.line_segment(
        [center + egui::vec2(-a, -a), center + egui::vec2(a, a)],
        stroke,
    );
    painter.line_segment(
        [center + egui::vec2(-a, a), center + egui::vec2(a, -a)],
        stroke,
    );
}

pub fn close_button(ui: &mut egui::Ui, tooltip: &str) -> egui::Response {
    let (rect, response) = ui.allocate_exact_size(Vec2::splat(22.0), Sense::click());
    let color = if response.hovered() {
        COLOR_TEXT_PRIMARY
    } else {
        COLOR_TEXT_MUTED
    };
    if response.hovered() {
        ui.painter()
            .rect_filled(rect, CornerRadius::same(4), COLOR_BG_SUBTLE);
        ui.ctx().set_cursor_icon(egui::CursorIcon::PointingHand);
    }
    paint_cross(ui.painter(), rect.center(), 8.0, color);
    response.on_hover_text(tooltip)
}

pub fn dropdown_button(ui: &mut egui::Ui, text: &str, enabled: bool) -> egui::Response {
    let fg = if enabled {
        COLOR_TEXT_PRIMARY
    } else {
        COLOR_TEXT_DISABLED
    };
    let galley = truncated(ui, RichText::new(text).color(fg), f32::INFINITY);
    let size = egui::vec2(galley.size().x + 36.0, 30.0);
    let sense = if enabled {
        Sense::click()
    } else {
        Sense::hover()
    };
    let (rect, response) = ui.allocate_exact_size(size, sense);

    let (bg, border) = if enabled && response.hovered() {
        (COLOR_BG_SUBTLE, COLOR_TEXT_DISABLED)
    } else {
        (COLOR_BG_CARD, COLOR_BORDER_STRONG)
    };
    ui.painter().rect(
        rect,
        CornerRadius::same(6),
        bg,
        stroke(1.0, border),
        egui::StrokeKind::Inside,
    );
    let text_pos = egui::pos2(rect.min.x + 12.0, rect.center().y - galley.size().y / 2.0);
    ui.painter().galley(text_pos, galley, fg);
    paint_triangle(
        ui.painter(),
        egui::pos2(rect.max.x - 14.0, rect.center().y),
        8.0,
        Direction::Down,
        fg,
    );
    if enabled && response.hovered() {
        ui.ctx().set_cursor_icon(egui::CursorIcon::PointingHand);
    }
    response
}

pub fn primary_button(ui: &mut egui::Ui, text: &str) -> egui::Response {
    ui.add(
        egui::Button::new(RichText::new(text).color(Color32::WHITE).strong())
            .fill(COLOR_PRIMARY)
            .stroke(Stroke::NONE)
            .min_size(egui::vec2(0.0, 30.0)),
    )
}

pub fn category_badge(ui: &mut egui::Ui, category: ConflictCategory) {
    egui::Frame::NONE
        .fill(COLOR_BG_SUBTLE)
        .corner_radius(CornerRadius::same(10))
        .inner_margin(egui::Margin::symmetric(8, 2))
        .show(ui, |ui| {
            ui.spacing_mut().item_spacing.x = 6.0;
            category_dot(ui, category);
            ui.label(
                RichText::new(category.short_label())
                    .size(11.5)
                    .color(COLOR_TEXT_SECONDARY),
            );
        });
}

pub fn category_dot(ui: &mut egui::Ui, category: ConflictCategory) {
    let (rect, _) = ui.allocate_exact_size(Vec2::splat(8.0), Sense::hover());
    ui.painter()
        .circle_filled(rect.center(), 4.0, category_color(category));
}

pub fn tribunal_badge(ui: &mut egui::Ui, tribunal: Tribunal) {
    egui::Frame::NONE
        .stroke(stroke(1.0, COLOR_BORDER_STRONG))
        .corner_radius(CornerRadius::same(4))
        .inner_margin(egui::Margin::symmetric(6, 1))
        .show(ui, |ui| {
            ui.label(
                RichText::new(tribunal.code())
                    .monospace()
                    .size(11.0)
                    .color(COLOR_TEXT_SECONDARY),
            );
        });
}

pub fn facet_option(
    ui: &mut egui::Ui,
    checked: bool,
    label: &str,
    count: u32,
    dot: Option<Color32>,
) -> egui::Response {
    let width = ui.available_width();
    let (rect, response) = ui.allocate_exact_size(egui::vec2(width, 26.0), Sense::click());
    if !ui.is_rect_visible(rect) {
        return response;
    }

    let dim = count == 0 && !checked;
    let text_color = if dim {
        COLOR_TEXT_DISABLED
    } else {
        COLOR_TEXT_PRIMARY
    };
    let painter = ui.painter();

    if response.hovered() {
        painter.rect_filled(rect, CornerRadius::same(4), COLOR_BG_SUBTLE);
        ui.ctx().set_cursor_icon(egui::CursorIcon::PointingHand);
    }

    let box_rect = Rect::from_center_size(
        egui::pos2(rect.min.x + 12.0, rect.center().y),
        Vec2::splat(14.0),
    );
    if checked {
        painter.rect_filled(box_rect, CornerRadius::same(3), COLOR_PRIMARY);
        let stroke = stroke(1.6, Color32::WHITE);
        let p1 = egui::pos2(box_rect.min.x + 3.0, box_rect.center().y);
        let p2 = egui::pos2(box_rect.min.x + 5.8, box_rect.max.y - 3.5);
        let p3 = egui::pos2(box_rect.max.x - 3.0, box_rect.min.y + 3.5);
        painter.line_segment([p1, p2], stroke);
        painter.line_segment([p2, p3], stroke);
    } else {
        painter.rect_stroke(
            box_rect,
            CornerRadius::same(3),
            stroke(
                1.0,
                if response.hovered() {
                    COLOR_TEXT_MUTED
                } else {
                    COLOR_BORDER_STRONG
                },
            ),
            egui::StrokeKind::Inside,
        );
    }

    let mut x = box_rect.max.x + 8.0;
    if let Some(color) = dot {
        painter.circle_filled(
            egui::pos2(x + 4.0, rect.center().y),
            4.0,
            if dim { COLOR_BORDER_STRONG } else { color },
        );
        x += 14.0;
    }

    let count_text = crate::model::format_count(count as usize);
    let count_galley = truncated(
        ui,
        RichText::new(count_text).size(11.5).color(COLOR_TEXT_MUTED),
        f32::INFINITY,
    );
    let count_pos = egui::pos2(
        rect.max.x - 6.0 - count_galley.size().x,
        rect.center().y - count_galley.size().y / 2.0,
    );

    let label_width = (count_pos.x - x - 8.0).max(10.0);
    let label_galley = truncated(ui, RichText::new(label).color(text_color), label_width);
    let label_pos = egui::pos2(x, rect.center().y - label_galley.size().y / 2.0);
    let label_truncated = label_galley.elided;

    let painter = ui.painter();
    painter.galley(label_pos, label_galley, text_color);
    painter.galley(count_pos, count_galley, COLOR_TEXT_MUTED);

    if label_truncated {
        response.on_hover_text(label)
    } else {
        response
    }
}

pub fn filter_chip(ui: &mut egui::Ui, text: &str) -> bool {
    let galley = truncated(
        ui,
        RichText::new(text).size(12.0).color(COLOR_TEXT_SECONDARY),
        260.0,
    );
    let size = egui::vec2(galley.size().x + 32.0, 24.0);
    let (rect, response) = ui.allocate_exact_size(size, Sense::click());
    let hovered = response.hovered();
    ui.painter().rect(
        rect,
        CornerRadius::same(12),
        if hovered {
            COLOR_BORDER
        } else {
            COLOR_BG_SUBTLE
        },
        stroke(1.0, COLOR_BORDER),
        egui::StrokeKind::Inside,
    );
    ui.painter().galley(
        egui::pos2(rect.min.x + 10.0, rect.center().y - galley.size().y / 2.0),
        galley,
        COLOR_TEXT_SECONDARY,
    );
    paint_cross(
        ui.painter(),
        egui::pos2(rect.max.x - 12.0, rect.center().y),
        6.0,
        if hovered {
            COLOR_TEXT_PRIMARY
        } else {
            COLOR_TEXT_MUTED
        },
    );
    if hovered {
        ui.ctx().set_cursor_icon(egui::CursorIcon::PointingHand);
    }
    response.on_hover_text("Remover filtro").clicked()
}

pub fn link_button(ui: &mut egui::Ui, text: &str) -> egui::Response {
    let response = ui.add(
        egui::Label::new(
            RichText::new(text)
                .size(11.5)
                .color(COLOR_TEXT_MUTED)
                .underline(),
        )
        .extend()
        .sense(Sense::click()),
    );
    if response.hovered() {
        ui.ctx().set_cursor_icon(egui::CursorIcon::PointingHand);
    }
    response
}

pub fn detail_box<R>(ui: &mut egui::Ui, add_contents: impl FnOnce(&mut egui::Ui) -> R) -> R {
    egui::Frame::NONE
        .fill(COLOR_BG_CANVAS)
        .stroke(stroke(1.0, COLOR_BORDER))
        .corner_radius(CornerRadius::same(6))
        .inner_margin(egui::Margin::same(10))
        .show(ui, |ui| {
            ui.set_width(ui.available_width());
            add_contents(ui)
        })
        .inner
}
