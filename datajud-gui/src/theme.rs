use eframe::egui::{self, Color32, CornerRadius, Stroke};

use crate::model::ConflictCategory;

/// Colors inspired by the Land Conflict Mapping Platform (Angular frontend)
pub const COLOR_BG_CANVAS: Color32 = Color32::from_rgb(248, 250, 252); // slate-50
pub const COLOR_BG_CARD: Color32 = Color32::from_rgb(255, 255, 255);   // white
pub const COLOR_BORDER: Color32 = Color32::from_rgb(226, 232, 240);    // slate-200
pub const COLOR_TEXT_PRIMARY: Color32 = Color32::from_rgb(15, 23, 42); // slate-900
pub const COLOR_TEXT_MUTED: Color32 = Color32::from_rgb(100, 116, 139); // slate-500
pub const COLOR_PRIMARY_BUTTON: Color32 = Color32::from_rgb(15, 23, 42); // slate-900
pub const COLOR_SUCCESS_BUTTON: Color32 = Color32::from_rgb(5, 150, 105); // emerald-600

pub fn setup_institutional_theme(ctx: &egui::Context) {
    let mut visuals = egui::Visuals::light();

    visuals.override_text_color = Some(COLOR_TEXT_PRIMARY);
    visuals.panel_fill = COLOR_BG_CANVAS;
    visuals.window_fill = COLOR_BG_CARD;
    visuals.window_stroke = Stroke::new(1.0, COLOR_BORDER);
    visuals.window_corner_radius = CornerRadius::same(10);

    // Non-interactive widgets
    visuals.widgets.noninteractive.bg_fill = COLOR_BG_CARD;
    visuals.widgets.noninteractive.bg_stroke = Stroke::new(1.0, COLOR_BORDER);
    visuals.widgets.noninteractive.corner_radius = CornerRadius::same(6);
    visuals.widgets.noninteractive.fg_stroke = Stroke::new(1.0, COLOR_TEXT_PRIMARY);

    // Inactive buttons / text inputs
    visuals.widgets.inactive.bg_fill = COLOR_BG_CARD;
    visuals.widgets.inactive.bg_stroke = Stroke::new(1.0, COLOR_BORDER);
    visuals.widgets.inactive.corner_radius = CornerRadius::same(6);
    visuals.widgets.inactive.fg_stroke = Stroke::new(1.0, COLOR_TEXT_PRIMARY);

    // Hovered widgets
    visuals.widgets.hovered.bg_fill = Color32::from_rgb(241, 245, 249);
    visuals.widgets.hovered.bg_stroke = Stroke::new(1.0, Color32::from_rgb(203, 213, 225));
    visuals.widgets.hovered.corner_radius = CornerRadius::same(6);
    visuals.widgets.hovered.fg_stroke = Stroke::new(1.0, COLOR_TEXT_PRIMARY);

    // Active widgets
    visuals.widgets.active.bg_fill = Color32::from_rgb(226, 232, 240);
    visuals.widgets.active.bg_stroke = Stroke::new(1.0, Color32::from_rgb(148, 163, 184));
    visuals.widgets.active.corner_radius = CornerRadius::same(6);
    visuals.widgets.active.fg_stroke = Stroke::new(1.0, COLOR_TEXT_PRIMARY);

    // Selection
    visuals.selection.bg_fill = Color32::from_rgb(226, 232, 240);
    visuals.selection.stroke = Stroke::new(1.0, COLOR_TEXT_PRIMARY);

    ctx.set_visuals(visuals);
}

/// Renders a category badge pill inspired by the Angular legend
pub fn render_category_badge(ui: &mut egui::Ui, category: ConflictCategory) {
    let [r, g, b] = category.color_rgb();
    let bg_color = Color32::from_rgba_premultiplied(r, g, b, 28);
    let border_color = Color32::from_rgb(r, g, b);
    let text_color = Color32::from_rgb(r, g, b);

    egui::Frame::NONE
        .fill(bg_color)
        .stroke(Stroke::new(1.0, border_color))
        .corner_radius(CornerRadius::same(12))
        .inner_margin(egui::Margin::symmetric(8, 2))
        .show(ui, |ui| {
            ui.label(
                egui::RichText::new(category.display_name())
                    .color(text_color)
                    .size(11.0)
                    .strong(),
            );
        });
}

/// Renders a distinctive tribunal pill badge
pub fn render_tribunal_badge(ui: &mut egui::Ui, tribunal: &str) {
    let t_upper = tribunal.to_uppercase();
    let (bg, border, fg) = match t_upper.as_str() {
        "TJPE" => (Color32::from_rgb(238, 242, 255), Color32::from_rgb(165, 180, 252), Color32::from_rgb(67, 56, 202)), // Indigo
        "TRF5" => (Color32::from_rgb(239, 246, 255), Color32::from_rgb(147, 197, 253), Color32::from_rgb(29, 78, 216)), // Blue
        "TJSP" => (Color32::from_rgb(240, 253, 250), Color32::from_rgb(153, 246, 228), Color32::from_rgb(15, 118, 110)), // Teal
        "TJMG" => (Color32::from_rgb(254, 242, 242), Color32::from_rgb(254, 202, 202), Color32::from_rgb(185, 28, 28)),  // Red
        "TRF1" => (Color32::from_rgb(254, 243, 199), Color32::from_rgb(252, 211, 77), Color32::from_rgb(180, 83, 9)),   // Amber
        _ => (Color32::from_rgb(241, 245, 249), Color32::from_rgb(203, 213, 225), Color32::from_rgb(51, 65, 85)),        // Slate
    };

    egui::Frame::NONE
        .fill(bg)
        .stroke(Stroke::new(1.0, border))
        .corner_radius(CornerRadius::same(5))
        .inner_margin(egui::Margin::symmetric(6, 2))
        .show(ui, |ui| {
            ui.label(
                egui::RichText::new(&t_upper)
                    .color(fg)
                    .size(11.0)
                    .strong(),
            );
        });
}

/// Renders a crisp vector magnifying glass search icon using egui painter (zero emojis)
pub fn paint_search_icon(painter: &egui::Painter, center: egui::Pos2, size: f32, color: Color32) {
    let stroke = Stroke::new(1.8, color);
    let radius = size * 0.35;
    let circle_center = center - egui::vec2(radius * 0.3, radius * 0.3);
    painter.circle_stroke(circle_center, radius, stroke);

    let cos45 = std::f32::consts::FRAC_1_SQRT_2;
    let handle_start = circle_center + egui::vec2(radius * cos45, radius * cos45);
    let handle_end = handle_start + egui::vec2(radius * 0.75, radius * 0.75);
    painter.line_segment([handle_start, handle_end], stroke);
}

/// Renders a prominent button with a vector search icon and text
pub fn render_search_button(
    ui: &mut egui::Ui,
    text: &str,
    fill_color: Color32,
    text_color: Color32,
    height: f32,
    width: Option<f32>,
) -> egui::Response {
    let desired_width = width.unwrap_or_else(|| ui.available_width());
    let (rect, response) = ui.allocate_exact_size(
        egui::vec2(desired_width, height),
        egui::Sense::click(),
    );

    if ui.is_rect_visible(rect) {
        let bg_color = if response.is_pointer_button_down_on() {
            Color32::from_rgb(51, 65, 85)
        } else if response.hovered() {
            Color32::from_rgb(30, 41, 59)
        } else {
            fill_color
        };

        ui.painter().rect_filled(
            rect,
            CornerRadius::same(7),
            bg_color,
        );

        let icon_size = 14.0;
        let font_id = egui::FontId::proportional(13.5);
        let galley = ui.painter().layout_no_wrap(text.to_string(), font_id, text_color);
        let gap = 8.0;
        let total_content_width = icon_size + gap + galley.size().x;

        let content_left = rect.center().x - (total_content_width / 2.0);
        let icon_center = egui::pos2(content_left + (icon_size / 2.0), rect.center().y);
        paint_search_icon(ui.painter(), icon_center, icon_size, text_color);

        let text_pos = egui::pos2(
            content_left + icon_size + gap,
            rect.center().y - (galley.size().y / 2.0),
        );
        ui.painter().galley(text_pos, galley, text_color);
    }

    response
}

/// Renders a crisp vector filter funnel icon using egui painter (zero emojis)
pub fn paint_funnel_icon(painter: &egui::Painter, center: egui::Pos2, color: Color32) {
    let top_y = center.y - 5.0;
    let neck_y = center.y - 0.5;
    let bottom_y = center.y + 5.0;

    let p_lt = egui::pos2(center.x - 5.5, top_y);
    let p_rt = egui::pos2(center.x + 5.5, top_y);
    let p_rn = egui::pos2(center.x + 1.4, neck_y);
    let p_ln = egui::pos2(center.x - 1.4, neck_y);
    let p_rb = egui::pos2(center.x + 1.4, bottom_y);
    let p_lb = egui::pos2(center.x - 1.4, bottom_y);

    let stroke = Stroke::new(1.2, color);

    // Fill top trapezoid & stem
    painter.add(egui::Shape::convex_polygon(
        vec![p_lt, p_rt, p_rn, p_ln],
        color,
        stroke,
    ));
    painter.add(egui::Shape::convex_polygon(
        vec![p_ln, p_rn, p_rb, p_lb],
        color,
        stroke,
    ));
}

/// Renders a dropdown filter button with a vector funnel icon and clean title
pub fn render_dropdown_filter_button(
    ui: &mut egui::Ui,
    title: &str,
    min_width: f32,
) -> egui::Response {
    let font_id = egui::FontId::proportional(12.5);
    let galley = ui.painter().layout_no_wrap(title.to_string(), font_id, COLOR_TEXT_PRIMARY);

    let left_pad = 10.0;
    let icon_width = 11.0;
    let gap = 7.0;
    let right_pad = 10.0;
    let content_width = left_pad + icon_width + gap + galley.size().x + right_pad;
    let desired_width = min_width.max(content_width);

    let (rect, response) = ui.allocate_exact_size(
        egui::vec2(desired_width, 32.0),
        egui::Sense::click(),
    );

    if response.hovered() {
        ui.ctx().set_cursor_icon(egui::CursorIcon::PointingHand);
    }

    if ui.is_rect_visible(rect) {
        let is_hovered = response.hovered();
        let bg_color = if response.is_pointer_button_down_on() {
            Color32::from_rgb(226, 232, 240)
        } else if is_hovered {
            Color32::from_rgb(241, 245, 249)
        } else {
            Color32::from_rgb(248, 250, 252)
        };

        let stroke_color = if is_hovered {
            Color32::from_rgb(203, 213, 225)
        } else {
            COLOR_BORDER
        };

        ui.painter().rect(
            rect,
            CornerRadius::same(6),
            bg_color,
            Stroke::new(1.0, stroke_color),
            egui::StrokeKind::Inside,
        );

        // Funnel icon on the left
        let icon_center = egui::pos2(rect.min.x + left_pad + (icon_width / 2.0), rect.center().y);
        paint_funnel_icon(ui.painter(), icon_center, COLOR_TEXT_PRIMARY);

        // Title text
        let text_left = rect.min.x + left_pad + icon_width + gap;
        let text_pos = egui::pos2(text_left, rect.center().y - (galley.size().y / 2.0));
        ui.painter().galley(text_pos, galley, COLOR_TEXT_PRIMARY);
    }

    response
}

/// Renders a centered prominent button with a vector "X" cancel icon and centered text
pub fn render_cancel_button(
    ui: &mut egui::Ui,
    text: &str,
    height: f32,
    width: Option<f32>,
) -> egui::Response {
    let desired_width = width.unwrap_or_else(|| ui.available_width());
    let (rect, response) = ui.allocate_exact_size(
        egui::vec2(desired_width, height),
        egui::Sense::click(),
    );

    if response.hovered() {
        ui.ctx().set_cursor_icon(egui::CursorIcon::PointingHand);
    }

    if ui.is_rect_visible(rect) {
        let base_color = Color32::from_rgb(220, 38, 38); // Red-600
        let bg_color = if response.is_pointer_button_down_on() {
            Color32::from_rgb(153, 27, 27) // Red-800
        } else if response.hovered() {
            Color32::from_rgb(185, 28, 28) // Red-700
        } else {
            base_color
        };

        ui.painter().rect_filled(
            rect,
            CornerRadius::same(7),
            bg_color,
        );

        let icon_size = 12.0;
        let font_id = egui::FontId::proportional(13.5);
        let galley = ui.painter().layout_no_wrap(text.to_string(), font_id, Color32::WHITE);
        let gap = 8.0;
        let total_content_width = icon_size + gap + galley.size().x;

        let content_left = rect.center().x - (total_content_width / 2.0);
        let icon_center = egui::pos2(content_left + (icon_size / 2.0), rect.center().y);

        // Crisp vector "X" cancel icon
        let stroke = Stroke::new(2.0, Color32::WHITE);
        let arm = icon_size * 0.35;
        let p1_start = icon_center - egui::vec2(arm, arm);
        let p1_end = icon_center + egui::vec2(arm, arm);
        let p2_start = egui::pos2(icon_center.x - arm, icon_center.y + arm);
        let p2_end = egui::pos2(icon_center.x + arm, icon_center.y - arm);
        ui.painter().line_segment([p1_start, p1_end], stroke);
        ui.painter().line_segment([p2_start, p2_end], stroke);

        let text_pos = egui::pos2(
            content_left + icon_size + gap,
            rect.center().y - (galley.size().y / 2.0),
        );
        ui.painter().galley(text_pos, galley, Color32::WHITE);
    }

    response
}

/// Renders an interactive filter item row with hover highlight, full-row clickability,
/// vector checkmark box, label, badge color (optional), and process count.
pub fn render_filter_item(
    ui: &mut egui::Ui,
    is_checked: bool,
    label: &str,
    count: usize,
    badge_color: Option<Color32>,
) -> bool {
    let desired_height = 30.0;
    let available_w = ui.available_width();
    let (rect, response) = ui.allocate_exact_size(
        egui::vec2(available_w, desired_height),
        egui::Sense::click(),
    );

    if response.hovered() {
        ui.ctx().set_cursor_icon(egui::CursorIcon::PointingHand);
    }

    if ui.is_rect_visible(rect) {
        let is_hovered = response.hovered();
        let bg_color = if is_hovered {
            Color32::from_rgb(241, 245, 249) // Slate-100 hover
        } else if is_checked {
            Color32::from_rgb(248, 250, 252)
        } else {
            Color32::TRANSPARENT
        };

        if bg_color != Color32::TRANSPARENT {
            ui.painter().rect_filled(rect, CornerRadius::same(5), bg_color);
        }

        // Checkbox box (15x15)
        let box_size = 15.0;
        let box_rect = egui::Rect::from_min_size(
            egui::pos2(rect.min.x + 8.0, rect.center().y - (box_size / 2.0)),
            egui::vec2(box_size, box_size),
        );

        if is_checked {
            ui.painter().rect_filled(box_rect, CornerRadius::same(3), COLOR_PRIMARY_BUTTON);
            // Draw crisp vector checkmark
            let stroke = Stroke::new(1.8, Color32::WHITE);
            let p1 = egui::pos2(box_rect.min.x + 3.0, box_rect.center().y);
            let p2 = egui::pos2(box_rect.min.x + 6.0, box_rect.max.y - 3.5);
            let p3 = egui::pos2(box_rect.max.x - 3.0, box_rect.min.y + 4.0);
            ui.painter().line_segment([p1, p2], stroke);
            ui.painter().line_segment([p2, p3], stroke);
        } else {
            ui.painter().rect_stroke(
                box_rect,
                CornerRadius::same(3),
                Stroke::new(1.2, COLOR_BORDER),
                egui::StrokeKind::Inside,
            );
        }

        // Label & badge
        let text_left = box_rect.max.x + 10.0;
        if let Some(c) = badge_color {
            let dot_size = 8.0;
            let dot_center = egui::pos2(text_left + 4.0, rect.center().y);
            ui.painter().circle_filled(dot_center, dot_size / 2.0, c);

            let label_pos = egui::pos2(text_left + 14.0, rect.center().y - 7.5);
            ui.painter().text(
                label_pos,
                egui::Align2::LEFT_TOP,
                label,
                egui::FontId::proportional(12.0),
                c,
            );
        } else {
            let label_pos = egui::pos2(text_left, rect.center().y - 7.5);
            ui.painter().text(
                label_pos,
                egui::Align2::LEFT_TOP,
                label,
                egui::FontId::proportional(12.0),
                COLOR_TEXT_PRIMARY,
            );
        }

        // Count on right
        let count_str = format!("({count})");
        let count_pos = egui::pos2(rect.max.x - 8.0, rect.center().y - 7.5);
        ui.painter().text(
            count_pos,
            egui::Align2::RIGHT_TOP,
            count_str,
            egui::FontId::proportional(11.5),
            COLOR_TEXT_MUTED,
        );
    }

    response.clicked()
}

