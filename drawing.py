from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle as PatchRectangle

from constraints import Rectangle

COLORS = {
    "Trading Area": "#e7b24c",
    "Offices": "#4f7cac",
    "Yard": "#68a357",
    "Off-loading Yard": "#c96b4a",
}


def draw_layout_option(
    rectangles: list[Rectangle],
    building_width: float,
    building_depth: float,
    title: str,
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

    for rectangle in rectangles:
        axis.add_patch(
            PatchRectangle(
                (rectangle.x, rectangle.y),
                rectangle.width,
                rectangle.depth,
                facecolor=COLORS[rectangle.label],
                edgecolor="#1f1f1f",
                linewidth=1.5,
                alpha=0.8,
            )
        )
        axis.text(
            rectangle.x + (rectangle.width / 2.0),
            rectangle.y + (rectangle.depth / 2.0),
            f"{rectangle.label}\n{rectangle.area:.1f} m²",
            ha="center",
            va="center",
            fontsize=10,
            color="#111111",
            wrap=True,
        )

    min_x = min(0.0, *(rectangle.x for rectangle in rectangles))
    max_x = max(building_width, *(rectangle.right for rectangle in rectangles))
    min_y = min(0.0, *(rectangle.y for rectangle in rectangles))
    max_y = max(building_depth, *(rectangle.top for rectangle in rectangles))
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
