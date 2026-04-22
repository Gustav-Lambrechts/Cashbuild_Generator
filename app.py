from __future__ import annotations

import streamlit as st

from dxf_parser import inspect_dxf_bytes
from drawing import draw_layout_option
from layout_engine import generate_layout_options

DEFAULT_WIDTH_MM = 30260
DEFAULT_DEPTH_MM = 46850
SIDES = ["north", "south", "east", "west"]


def mm_to_m(value_mm: float) -> float:
    return value_mm / 1000.0


def get_dxf_report(uploaded_dxf):
    if uploaded_dxf is None:
        return None

    try:
        return inspect_dxf_bytes(uploaded_dxf.getvalue())
    except Exception as error:
        st.error(f"Could not inspect DXF file: {error}")
        return None


def render_dxf_inspection(uploaded_dxf, report) -> None:
    st.subheader("DXF Inspection")

    if uploaded_dxf is None or report is None:
        st.info("Upload a .dxf file to inspect layers, entity counts, and STORE_ENVELOPE polylines.")
        return

    st.write(f"File: **{uploaded_dxf.name}**")

    selected_envelope = report.get("selected_store_envelope")
    if selected_envelope:
        st.success(
            "Using STORE_ENVELOPE to size the building footprint: "
            f"{selected_envelope['width']:.0f} mm x {selected_envelope['depth']:.0f} mm"
        )

    entrance_door = report.get("entrance_door")
    service_door = report.get("service_door")
    left_col, right_col = st.columns(2)
    with left_col:
        st.write("Layers")
        st.table([{"Layer": layer_name} for layer_name in report["layers"]])
    with right_col:
        st.write("Entities By Layer")
        st.table(
            [
                {"Layer": row["layer"], "Entity Count": row["entity_count"]}
                for row in report["entity_counts"]
            ]
        )

    st.write("STORE_ENVELOPE Polylines")
    if report["store_envelopes"]:
        st.table(
            [
                {
                    "Handle": row["handle"],
                    "Entity Type": row["entity_type"],
                    "Closed": "Yes" if row["closed"] else "No",
                    "Width (mm)": f"{row['width']:.0f}",
                    "Depth (mm)": f"{row['depth']:.0f}",
                }
                for row in report["store_envelopes"]
            ]
        )
    else:
        st.info("No STORE_ENVELOPE polylines were found.")

    st.write("Side Detection Status")
    st.table(
        [
            {
                "Input": "Entrance",
                "Detected DXF Side": entrance_door["side"].title() if entrance_door else "Not found",
                "Fallback Manual Side Used": "No" if entrance_door else "Yes",
            },
            {
                "Input": "Service",
                "Detected DXF Side": service_door["side"].title() if service_door else "Not found",
                "Fallback Manual Side Used": "No" if service_door else "Yes",
            },
        ]
    )

    if not entrance_door:
        st.warning("No valid DXF entrance side was found. The app is using the manual entrance side fallback.")
    if not service_door:
        st.warning("No valid DXF service side was found. The app is using the manual service side fallback.")

    st.write("Detected Doors / Openings Used For Sides")
    detected_rows = []
    for label, row in [("Entrance", entrance_door), ("Service", service_door)]:
        if row:
            detected_rows.append(
                {
                    "Use": label,
                    "Layer": row["layer"],
                    "Entity Type": row["entity_type"],
                    "Side": row["side"].title(),
                    "X (mm)": f"{row['x']:.0f}",
                    "Y (mm)": f"{row['y']:.0f}",
                }
            )
    if detected_rows:
        st.table(detected_rows)
    else:
        st.info("No door/opening geometry was confidently detected for entrance or service sides.")


st.set_page_config(page_title="Cashbuild Layout Generator MVP", layout="wide")

st.title("Cashbuild Layout Generator MVP")
st.write(
    "Generate three rectangular concept layouts for a Cashbuild-style building footprint using a schema-driven trading, admin, receiving, and site-planning flow."
)

with st.sidebar:
    st.header("Inputs")
    width_mm = st.number_input("Shop width (mm)", min_value=10000, value=DEFAULT_WIDTH_MM, step=100)
    depth_mm = st.number_input("Shop depth (mm)", min_value=10000, value=DEFAULT_DEPTH_MM, step=100)
    entrance_side = st.selectbox("Entrance side", SIDES, index=0)
    service_side = st.selectbox("Service side", SIDES, index=2)
    st.divider()
    st.subheader("DXF Inspection")
    uploaded_dxf = st.file_uploader("Upload DXF", type=["dxf"])

dxf_report = get_dxf_report(uploaded_dxf)
selected_envelope = dxf_report.get("selected_store_envelope") if dxf_report else None
entrance_door = dxf_report.get("entrance_door") if dxf_report else None
service_door = dxf_report.get("service_door") if dxf_report else None
detected_entrance_side = entrance_door["side"] if entrance_door else None
detected_service_side = service_door["side"] if service_door else None

effective_width_mm = selected_envelope["width"] if selected_envelope else width_mm
effective_depth_mm = selected_envelope["depth"] if selected_envelope else depth_mm
effective_entrance_side = detected_entrance_side or entrance_side
effective_service_side = detected_service_side or service_side

building_width_m = mm_to_m(effective_width_mm)
building_depth_m = mm_to_m(effective_depth_mm)

st.caption(
    f"Using a building footprint of {building_width_m:.2f} m x {building_depth_m:.2f} m. "
    f"Entrance side: {effective_entrance_side}. Service side: {effective_service_side}. "
    "Trading Area, Admin Block, and Goods Receiving are internal. Yard, Off-loading Yard, and Parking are external. "
    "Frontage openings stay fixed in mm from the left inside wall of the entrance side, and POS sits in the frontage gaps."
)

render_dxf_inspection(uploaded_dxf, dxf_report)

options = generate_layout_options(
    building_width_m=building_width_m,
    building_depth_m=building_depth_m,
    entrance_side=effective_entrance_side,
    service_side=effective_service_side,
)

for option in options:
    st.markdown(f"## {option['name']}  |  Score: {option['score']:.1f}")
    if option.get("summary"):
        st.caption(option["summary"])

    figure = draw_layout_option(
        rectangles=option["rectangles"],
        building_width=building_width_m,
        building_depth=building_depth_m,
        title=f"{option['name']} plan",
        frontage_openings=option["frontage_openings"],
        pos_zones=option["pos_zones"],
        frontage_summary=option["frontage_summary"],
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

    frontage_summary = option["frontage_summary"]
    st.table(
        [
            {
                "Entrance wall length (m)": f"{frontage_summary['entrance_wall_length_m']:.2f}",
                "Required frontage length (m)": f"{frontage_summary['required_frontage_length_m']:.2f}",
                "Opening clearance depth (m)": f"{frontage_summary['opening_clearance_depth_m']:.2f}",
                "POS zone depth (m)": f"{frontage_summary['pos_zone_depth_m']:.2f}",
                "POS zones placed": f"{frontage_summary['pos_zone_count']}/{frontage_summary['required_pos_zone_count']}",
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

    if option["pos_zones"]:
        pos_rows = [
            {
                "POS Zone": rectangle.label,
                "Area (m²)": f"{rectangle.area:.1f}",
                "Position": f"x={rectangle.x:.1f}, y={rectangle.y:.1f}",
                "Size": f"{rectangle.width:.1f} x {rectangle.depth:.1f} m",
            }
            for rectangle in option["pos_zones"]
        ]
        st.table(pos_rows)

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
