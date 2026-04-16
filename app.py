from __future__ import annotations

import streamlit as st

from drawing import draw_layout_option
from layout_engine import generate_layout_options

DEFAULT_WIDTH_MM = 30260
DEFAULT_DEPTH_MM = 46850
SIDES = ["north", "south", "east", "west"]


def mm_to_m(value_mm: float) -> float:
    return value_mm / 1000.0


st.set_page_config(page_title="Cashbuild Layout Generator MVP", layout="wide")

st.title("Cashbuild Layout Generator MVP")
st.write(
    "Generate three rectangular concept layouts for a Cashbuild-style building footprint with attached external support spaces."
)

with st.sidebar:
    st.header("Inputs")
    width_mm = st.number_input("Shop width (mm)", min_value=10000, value=DEFAULT_WIDTH_MM, step=100)
    depth_mm = st.number_input("Shop depth (mm)", min_value=10000, value=DEFAULT_DEPTH_MM, step=100)
    entrance_side = st.selectbox("Entrance side", SIDES, index=0)
    service_side = st.selectbox("Service side", SIDES, index=2)

building_width_m = mm_to_m(width_mm)
building_depth_m = mm_to_m(depth_mm)

st.caption(
    f"Using a building footprint of {building_width_m:.2f} m x {building_depth_m:.2f} m. "
    "Trading Area and Offices are internal. Yard and Off-loading Yard are external."
)

options = generate_layout_options(
    building_width_m=building_width_m,
    building_depth_m=building_depth_m,
    entrance_side=entrance_side,
    service_side=service_side,
)

for option in options:
    st.markdown(f"## {option['name']}  |  Score: {option['score']:.1f}")

    figure = draw_layout_option(
        rectangles=option["rectangles"],
        building_width=building_width_m,
        building_depth=building_depth_m,
        title=f"{option['name']} plan",
    )
    st.pyplot(figure, clear_figure=True)

    internal_summary = option["internal_summary"]
    st.table(
        [
            {
                "Building footprint area (m²)": f"{internal_summary['building_footprint_area_m2']:.1f}",
                "Requested internal area (m²)": f"{internal_summary['requested_internal_area_m2']:.1f}",
                "Actual generated internal area (m²)": f"{internal_summary['actual_generated_internal_area_m2']:.1f}",
                "Internal fit efficiency (%)": f"{internal_summary['internal_fit_efficiency_percent']:.1f}",
            }
        ]
    )

    summary_rows = [
        {
            "Space": rectangle.label,
            "Type": "Internal" if rectangle.internal else "External",
            "Area (m²)": f"{rectangle.area:.1f}",
            "Position": f"x={rectangle.x:.1f}, y={rectangle.y:.1f}",
            "Size": f"{rectangle.width:.1f} x {rectangle.depth:.1f} m",
        }
        for rectangle in option["rectangles"]
    ]
    st.table(summary_rows)

    validation_rows = [
        {
            "Rule": check["rule"],
            "Pass": "Yes" if check["passed"] else "No",
            "Category": check["category"].title(),
            "Detail": check["detail"],
        }
        for check in option["checks"]
    ]
    st.table(validation_rows)
    st.divider()
