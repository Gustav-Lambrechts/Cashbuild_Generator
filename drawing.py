from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle as PatchRectangle

from constraints import Rectangle

COLORS = {
    "Trading Area": "#e7b24c",
    "Admin Block": "#4f7cac",
    "Goods Receiving": "#7f5539",
    "Yard": "#68a357",
    "Off-loading Yard": "#c96b4a",
    "Parking": "#9ea7b3",
    "Passage": "#d7e3f2",
    "Cash Office": "#88a9c3",
    "Male Toilets / Change": "#8fc1b5",
    "Female Toilets / Change": "#b7d7c8",
    "Canteen": "#f2c57c",
    "POS Zone": "#d8b56a",
    "Clear Strip": "#d9d9d9",
}


def draw_layout_option(
    rectangles: list[Rectangle],
    building_width: float,
    building_depth: float,
    title: str,
    frontage_openings: list[dict[str, object]] | None = None,
    pos_zones: list[Rectangle] | None = None,
    frontage_summary: dict[str, object] | None = None,
):
    figure, axis = plt.subplots(figsize=(10, 6))
    axis.add_patch(
        PatchRectangle(
            (0, 0),
            building_width,
            building_depth,
            fill=False,
            linewidth=2.0,
            edgecolor="#333333",
            linestyle="-",
        )
    )
    axis.text(
        0.6,
        building_depth - 0.6,
        "Building footprint",
        ha="left",
        va="top",
        fontsize=10,
        color="#333333",
    )

    frontage_summary = frontage_summary or {}
    frontage_openings = frontage_openings or []
    pos_zones = pos_zones or []

    for clearance in frontage_summary.get("opening_clearance_rects", []):
        axis.add_patch(
            PatchRectangle(
                (clearance.x, clearance.y),
                clearance.width,
                clearance.depth,
                facecolor=COLORS["Clear Strip"],
                edgecolor="none",
                alpha=0.35,
            )
        )

    for rectangle in rectangles:
        edge_color = "#1f1f1f"
        line_width = 1.5
        fill_alpha = 0.8
        if rectangle.label == "Admin Block":
            edge_color = "#27496d"
            line_width = 2.0
            fill_alpha = 0.25

        axis.add_patch(
            PatchRectangle(
                (rectangle.x, rectangle.y),
                rectangle.width,
                rectangle.depth,
                facecolor=COLORS.get(rectangle.label, "#cccccc"),
                edgecolor=edge_color,
                linewidth=line_width,
                alpha=fill_alpha,
            )
        )
        axis.text(
            rectangle.x + (rectangle.width / 2.0),
            rectangle.y + (rectangle.depth / 2.0),
            format_label(rectangle),
            ha="center",
            va="center",
            fontsize=9 if rectangle.label not in {"Passage", "Cash Office", "Male Toilets / Change", "Female Toilets / Change", "Canteen"} else 8,
            color="#111111",
            wrap=True,
        )

    for pos_zone in pos_zones:
        axis.add_patch(
            PatchRectangle(
                (pos_zone.x, pos_zone.y),
                pos_zone.width,
                pos_zone.depth,
                facecolor=COLORS["POS Zone"],
                edgecolor="#6f5b2a",
                linewidth=1.2,
                alpha=0.75,
            )
        )
        axis.text(
            pos_zone.x + (pos_zone.width / 2.0),
            pos_zone.y + (pos_zone.depth / 2.0),
            f"{pos_zone.label}\n{pos_zone.area:.1f} m²",
            ha="center",
            va="center",
            fontsize=8,
            color="#111111",
            wrap=True,
        )

    for opening in frontage_openings:
        axis.plot(
            [opening["draw_x1"], opening["draw_x2"]],
            [opening["draw_y1"], opening["draw_y2"]],
            color="#ffffff",
            linewidth=6,
            solid_capstyle="butt",
            zorder=5,
        )
        axis.plot(
            [opening["draw_x1"], opening["draw_x2"]],
            [opening["draw_y1"], opening["draw_y2"]],
            color="#222222",
            linewidth=1.2,
            solid_capstyle="butt",
            zorder=6,
        )
        label_x = (opening["draw_x1"] + opening["draw_x2"]) / 2.0
        label_y = (opening["draw_y1"] + opening["draw_y2"]) / 2.0
        axis.text(
            label_x,
            label_y,
            opening["label"],
            ha="center",
            va="bottom" if opening["axis"] == "horizontal" and opening["draw_y1"] >= building_depth / 2.0 else "top",
            fontsize=8,
            color="#111111",
            zorder=7,
        )

    min_x = min(0.0, *(rectangle.x for rectangle in rectangles))
    max_x = max(building_width, *(rectangle.right for rectangle in rectangles))
    min_y = min(0.0, *(rectangle.y for rectangle in rectangles))
    max_y = max(building_depth, *(rectangle.top for rectangle in rectangles))
    if pos_zones:
        min_x = min(min_x, *(rectangle.x for rectangle in pos_zones))
        max_x = max(max_x, *(rectangle.right for rectangle in pos_zones))
        min_y = min(min_y, *(rectangle.y for rectangle in pos_zones))
        max_y = max(max_y, *(rectangle.top for rectangle in pos_zones))
    padding_x = max(2.0, (max_x - min_x) * 0.08)
    padding_y = max(2.0, (max_y - min_y) * 0.08)
    axis.set_xlim(min_x - padding_x, max_x + padding_x)
    axis.set_ylim(min_y - padding_y, max_y + padding_y)
    axis.set_aspect("equal", adjustable="box")
    axis.set_title(title, fontsize=14)
    axis.set_xlabel("Width (m)")
    axis.set_ylabel("Depth (m)")
    axis.grid(True, linestyle="--", alpha=0.25)

    return figure


def format_label(rectangle: Rectangle) -> str:
    short_labels = {
        "Male Toilets / Change": "Male WC /\nChange",
        "Female Toilets / Change": "Female WC /\nChange",
        "Off-loading Yard": "Off-loading\nYard",
        "Goods Receiving": "Goods\nReceiving",
        "Cash Office": "Cash\nOffice",
    }
    label = short_labels.get(rectangle.label, rectangle.label)
    return f"{label}\n{rectangle.area:.1f} m²"
