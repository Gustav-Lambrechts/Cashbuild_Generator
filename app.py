from __future__ import annotations

import streamlit as st

from dxf_parser import inspect_dxf_bytes
from drawing import draw_layout_option
from layout_engine import generate_best_layout

DEFAULT_WIDTH_MM = 30260
DEFAULT_DEPTH_MM = 46850
SIDES = ["north", "south", "east", "west"]
POSITIONS = ["left", "middle", "right"]


def mm_to_m(value_mm: float) -> float:
    return value_mm / 1000.0


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(246, 244, 239, 0.95), rgba(255, 255, 255, 1) 40%),
                linear-gradient(180deg, #fbfaf8 0%, #ffffff 100%);
            color: #111111;
            font-family: "Avenir Next", "Segoe UI", sans-serif;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2.5rem;
            max-width: 1380px;
        }
        .eyebrow {
            font-size: 0.82rem;
            letter-spacing: 0.24rem;
            text-transform: uppercase;
            color: #8a847a;
            margin-bottom: 0.6rem;
        }
        .hero-title {
            font-size: 3.4rem;
            line-height: 1.02;
            font-weight: 650;
            letter-spacing: -0.06em;
            margin: 0;
            color: #111111;
        }
        .hero-subtitle {
            font-size: 1.2rem;
            line-height: 1.7;
            color: #6a655d;
            max-width: 58rem;
            margin-top: 1rem;
        }
        .panel-title {
            font-size: 0.9rem;
            letter-spacing: 0.16rem;
            text-transform: uppercase;
            color: #9c968c;
            margin-bottom: 0.6rem;
        }
        .section-title {
            font-size: 2rem;
            line-height: 1.12;
            font-weight: 620;
            letter-spacing: -0.04em;
            color: #111111;
            margin: 0 0 1.1rem 0;
        }
        .soft-copy {
            color: #6f6a63;
            font-size: 1.02rem;
            line-height: 1.6;
        }
        .preview-blank {
            min-height: 640px;
            border: 1px dashed #ddd7cd;
            border-radius: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(255, 255, 255, 0.72);
            text-align: center;
            padding: 2rem;
        }
        .preview-blank h2 {
            font-size: 3rem;
            line-height: 1.05;
            margin: 0 0 0.9rem 0;
            letter-spacing: -0.05em;
        }
        .preview-blank p {
            margin: 0;
            color: #817c74;
            font-size: 1.16rem;
            line-height: 1.7;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: 1fr auto;
            gap: 0.85rem 1rem;
            font-size: 1rem;
            color: #26231f;
        }
        .summary-grid .label {
            color: #7d776e;
        }
        .summary-grid .value {
            font-weight: 600;
            text-align: right;
        }
        .placeholder-shell {
            min-height: 620px;
            border: 1px solid #ece7de;
            border-radius: 28px;
            background: rgba(255, 255, 255, 0.82);
            padding: 3rem;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
        }
        .placeholder-shell h2 {
            font-size: 2.4rem;
            line-height: 1.1;
            margin-bottom: 1rem;
            letter-spacing: -0.05em;
        }
        .placeholder-shell ul {
            list-style: none;
            padding: 0;
            margin: 1.4rem 0 0 0;
            color: #6f6a63;
            line-height: 1.9;
            font-size: 1.05rem;
        }
        .home-card {
            border: 1px solid #ece7de;
            border-radius: 28px;
            padding: 2rem 2rem 1.8rem 2rem;
            background: rgba(255, 255, 255, 0.8);
        }
        .review-spacer {
            height: 1.35rem;
        }
        div[data-testid="stButton"] button {
            border-radius: 999px;
            min-height: 3.15rem;
            font-weight: 600;
            border: 1px solid #d8d2c7;
        }
        div[data-testid="stButton"] button[kind="primary"] {
            background: #111111;
            border-color: #111111;
            color: #ffffff;
        }
        div[data-testid="stButton"] button[kind="secondary"] {
            background: #ffffff;
            color: #111111;
        }
        div[data-testid="stFileUploader"] section {
            border-radius: 22px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    defaults = {
        "screen": "home",
        "width_mm": DEFAULT_WIDTH_MM,
        "depth_mm": DEFAULT_DEPTH_MM,
        "entrance_side": "north",
        "service_side": "east",
        "admin_block_side": "east",
        "admin_block_position": "middle",
        "generated_layout": None,
        "generated_inputs": None,
        "generated_dxf_report": None,
        "generated_dxf_name": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_dxf_report(uploaded_dxf):
    if uploaded_dxf is None:
        return None

    try:
        return inspect_dxf_bytes(uploaded_dxf.getvalue())
    except Exception as error:
        st.error(f"Could not inspect DXF file: {error}")
        return None


def render_dxf_inspection(report, file_name: str | None = None) -> None:
    if report is None:
        st.info("Upload a `.dxf` file to inspect layers, entity counts, and detected STORE_ENVELOPE geometry.")
        return

    if file_name:
        st.write(f"File: **{file_name}**")

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
        st.warning("No valid DXF entrance side was found. The app will use the manual entrance side.")
    if not service_door:
        st.warning("No valid DXF service side was found. The app will use the manual service side.")

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
    st.write("Detected Doors / Openings Used For Side Logic")
    if detected_rows:
        st.table(detected_rows)
    else:
        st.info("No door/opening geometry was confidently detected for entrance or service sides.")


def resolve_effective_inputs(
    width_mm: float,
    depth_mm: float,
    entrance_side: str,
    service_side: str,
    dxf_report,
) -> dict[str, float | str]:
    selected_envelope = dxf_report.get("selected_store_envelope") if dxf_report else None
    entrance_door = dxf_report.get("entrance_door") if dxf_report else None
    service_door = dxf_report.get("service_door") if dxf_report else None

    effective_width_mm = selected_envelope["width"] if selected_envelope else width_mm
    effective_depth_mm = selected_envelope["depth"] if selected_envelope else depth_mm
    effective_entrance_side = entrance_door["side"] if entrance_door else entrance_side
    effective_service_side = service_door["side"] if service_door else service_side

    return {
        "raw_width_mm": width_mm,
        "raw_depth_mm": depth_mm,
        "raw_entrance_side": entrance_side,
        "raw_service_side": service_side,
        "admin_block_side": st.session_state.admin_block_side,
        "admin_block_position": st.session_state.admin_block_position,
        "effective_width_mm": effective_width_mm,
        "effective_depth_mm": effective_depth_mm,
        "effective_entrance_side": effective_entrance_side,
        "effective_service_side": effective_service_side,
        "building_width_m": mm_to_m(effective_width_mm),
        "building_depth_m": mm_to_m(effective_depth_mm),
    }


def generate_macro_layout(uploaded_dxf, dxf_report) -> None:
    inputs = resolve_effective_inputs(
        width_mm=float(st.session_state.width_mm),
        depth_mm=float(st.session_state.depth_mm),
        entrance_side=st.session_state.entrance_side,
        service_side=st.session_state.service_side,
        dxf_report=dxf_report,
    )

    st.session_state.generated_layout = generate_best_layout(
        building_width_m=inputs["building_width_m"],
        building_depth_m=inputs["building_depth_m"],
        entrance_side=inputs["effective_entrance_side"],
        service_side=inputs["effective_service_side"],
        admin_block_side=inputs["admin_block_side"],
        admin_block_position=inputs["admin_block_position"],
    )
    st.session_state.generated_inputs = inputs
    st.session_state.generated_dxf_report = dxf_report
    st.session_state.generated_dxf_name = uploaded_dxf.name if uploaded_dxf else None
    st.session_state.screen = "review"


def regenerate_existing_layout() -> None:
    inputs = st.session_state.generated_inputs
    if not inputs:
        st.session_state.screen = "inputs"
        return

    st.session_state.generated_layout = generate_best_layout(
        building_width_m=inputs["building_width_m"],
        building_depth_m=inputs["building_depth_m"],
        entrance_side=inputs["effective_entrance_side"],
        service_side=inputs["effective_service_side"],
        admin_block_side=inputs["admin_block_side"],
        admin_block_position=inputs["admin_block_position"],
    )


def build_stage1_warnings(layout: dict[str, object]) -> list[str]:
    rectangle_map = {rectangle.label: rectangle for rectangle in layout["rectangles"]}
    trading = rectangle_map["Trading Area"]
    admin = rectangle_map["Admin Block"]
    yard = rectangle_map["Yard"]
    offloading = rectangle_map["Off-loading Yard"]

    warnings: list[str] = []
    if trading.area < 1080.0:
        warnings.append(f"Trading Area is {trading.area:.1f} m², below the 1080 m² minimum.")
    if yard.area < 900.0:
        warnings.append(f"Yard is {yard.area:.1f} m², below the 900 m² minimum.")
    if offloading.area < 450.0:
        warnings.append(f"Off-loading Yard is {offloading.area:.1f} m², below the 450 m² minimum.")
    if abs(admin.area - 130.0) > 20.0:
        warnings.append(f"Admin Block is {admin.area:.1f} m², which differs noticeably from the 130 m² target.")

    failed_rules = {check["rule"] for check in layout["checks"] if not check["passed"]}
    if "Rectangles do not overlap" in failed_rules:
        warnings.append("One or more macro zones overlap.")
    if (
        "Admin Block sits outside Trading Area and touches it" in failed_rules
        or "Admin Block touches Goods Receiving" in failed_rules
        or "Admin Block stays clear of Trading Area and Yard" in failed_rules
    ):
        warnings.append("Admin Block conflicts badly with Trading Area, Goods Receiving, or the service yard.")

    return warnings


def render_summary_grid(rows: list[tuple[str, str]]) -> None:
    markup = ["<div class='summary-grid'>"]
    for label, value in rows:
        markup.append(f"<div class='label'>{label}</div><div class='value'>{value}</div>")
    markup.append("</div>")
    st.markdown("".join(markup), unsafe_allow_html=True)


def render_home_screen() -> None:
    st.markdown("<div class='eyebrow'>Homepage</div>", unsafe_allow_html=True)
    st.markdown("<h1 class='hero-title'>Generate a store plan from a few decisions.</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='hero-subtitle'>Cashbuild Macro Layout Generator is a rule-based retail layout generator. "
        "Start with the major zones, keep the planning logic visible, and move into detailing only once the macro zoning is trustworthy.</p>",
        unsafe_allow_html=True,
    )
    st.write("")

    left_spacer, center_col, right_spacer = st.columns([0.18, 0.64, 0.18])
    with center_col:
        with st.container(border=True):
            st.markdown(
                """
                <div class="home-card">
                    <div class="panel-title">Dashboard</div>
                    <div class="section-title">Cashbuild Macro Layout Generator</div>
                    <p class="soft-copy">
                        Create a new Stage 1 macro zoning study from width, depth, entrance side, service side,
                        and an optional DXF footprint.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.write("")
            if st.button("New Layout", type="primary", use_container_width=True):
                st.session_state.screen = "inputs"
                st.rerun()


def render_macro_inputs_screen() -> None:
    st.markdown("<div class='eyebrow'>Stage 1</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Define the macro zoning inputs.</div>", unsafe_allow_html=True)
    st.markdown(
        "<p class='soft-copy'>Set the building footprint, access sides, and optional DXF reference. "
        "The preview stays blank until you generate the macro layout.</p>",
        unsafe_allow_html=True,
    )

    left_col, right_col = st.columns([0.92, 1.7], gap="large")

    with left_col:
        with st.container(border=True):
            st.number_input("Shop width (mm)", min_value=10000, step=100, key="width_mm")
            st.number_input("Shop depth (mm)", min_value=10000, step=100, key="depth_mm")
            st.selectbox("Entrance side", SIDES, index=SIDES.index(st.session_state.entrance_side), key="entrance_side")
            st.selectbox("Service side", SIDES, index=SIDES.index(st.session_state.service_side), key="service_side")
            st.selectbox("Admin Block side", SIDES, index=SIDES.index(st.session_state.admin_block_side), key="admin_block_side")
            st.selectbox(
                "Admin Block position",
                POSITIONS,
                index=POSITIONS.index(st.session_state.admin_block_position),
                key="admin_block_position",
            )
            st.caption("Left / middle / right are read from the viewpoint of someone facing the selected Admin Block wall.")
            uploaded_dxf = st.file_uploader("Optional DXF upload", type=["dxf"], key="uploaded_dxf")
            dxf_report = get_dxf_report(uploaded_dxf)

            st.write("")
            if st.button("Generate Macro Layout", type="primary", use_container_width=True):
                generate_macro_layout(uploaded_dxf, dxf_report)
                st.rerun()

            if st.button("Back to Home", use_container_width=True):
                st.session_state.screen = "home"
                st.rerun()

        with st.container(border=True):
            st.markdown("<div class='panel-title'>Macro Zones</div>", unsafe_allow_html=True)
            st.markdown(
                """
                <p class="soft-copy">
                    Stage 1 generates only the major planning blocks:
                    Trading Area, Admin Block, Goods Receiving, Yard, Off-loading Yard, and Parking.
                    You can also steer the Admin Block by wall side and left / middle / right placement.
                </p>
                """,
                unsafe_allow_html=True,
            )

        with st.expander("DXF Inspection", expanded=False):
            render_dxf_inspection(dxf_report, uploaded_dxf.name if uploaded_dxf else None)

    with right_col:
        with st.container(border=True):
            st.markdown("<div class='panel-title'>Stage 1 Preview</div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div class="preview-blank">
                    <div>
                        <h2>Ready to generate.</h2>
                        <p>No drawing appears here until you click <strong>Generate Macro Layout</strong>.</p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_rule_feedback(checks: list[dict[str, object]]) -> None:
    hard_failures = [check for check in checks if check["category"] == "hard" and not check["passed"]]
    quality_notes = [check for check in checks if check["category"] == "quality"][:3]

    if hard_failures:
        st.error(f"{len(hard_failures)} hard rule checks still need attention.")
        for check in hard_failures[:4]:
            st.write(f"- {check['rule']}: {check['detail']}")
    else:
        st.success("Hard rule checks passed for this macro layout.")

    st.markdown("**Rule Feedback**")
    for check in quality_notes:
        status = "Pass" if check["passed"] else "Watch"
        st.write(f"- {status}: {check['rule']}")


def render_macro_review_screen() -> None:
    layout = st.session_state.generated_layout
    inputs = st.session_state.generated_inputs
    if layout is None or inputs is None:
        st.session_state.screen = "inputs"
        st.rerun()

    st.markdown("<div class='eyebrow'>Stage 1 Review</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Review the generated macro layout.</div>", unsafe_allow_html=True)
    st.markdown(
        "<p class='soft-copy'>This review stays at macro zoning level only. POS, doors, frontage detail, and micro rooms remain hidden until the future detailed stage.</p>",
        unsafe_allow_html=True,
    )

    left_col, right_col = st.columns([0.95, 1.75], gap="large")

    with left_col:
        with st.container(border=True):
            st.markdown("<div class='panel-title'>Layout Summary</div>", unsafe_allow_html=True)
            render_summary_grid(
                [
                    ("Envelope", f"{inputs['building_width_m']:.2f} m x {inputs['building_depth_m']:.2f} m"),
                    ("Entrance", str(inputs["effective_entrance_side"]).title()),
                    ("Service", str(inputs["effective_service_side"]).title()),
                    ("Admin side", str(inputs["admin_block_side"]).title()),
                    ("Admin position", str(inputs["admin_block_position"]).title()),
                    ("Status", "Generated"),
                    ("Score", f"{layout['score']:.1f}"),
                ]
            )

        with st.container(border=True):
            render_rule_feedback(layout["checks"])
            for warning_message in build_stage1_warnings(layout):
                st.warning(warning_message)

        st.markdown("<div class='review-spacer'></div>", unsafe_allow_html=True)
        if st.button("Regenerate Macro Layout", type="primary", use_container_width=True):
            regenerate_existing_layout()
            st.rerun()

        st.markdown("<div class='review-spacer'></div>", unsafe_allow_html=True)
        if st.button("Proceed to Detailed Layout", use_container_width=True):
            st.session_state.screen = "detail"
            st.rerun()

        st.markdown("<div class='review-spacer'></div>", unsafe_allow_html=True)
        if st.button("Back to Macro Inputs", use_container_width=True):
            st.session_state.screen = "inputs"
            st.rerun()

    with right_col:
        with st.container(border=True):
            st.markdown("<div class='panel-title'>Generated Macro Plan</div>", unsafe_allow_html=True)
            figure = draw_layout_option(
                rectangles=layout["rectangles"],
                building_width=inputs["building_width_m"],
                building_depth=inputs["building_depth_m"],
                title="Stage 1 macro layout",
                frontage_openings=layout["frontage_openings"],
                pos_zones=layout["pos_zones"],
                frontage_summary=layout["frontage_summary"],
                show_frontage_details=False,
                show_pos_zones=False,
            )
            st.pyplot(figure, clear_figure=True)

    st.write("")
    st.write("")

    with st.expander("Technical Tables", expanded=False):
        internal_summary = layout["internal_summary"]
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

        frontage_summary = layout["frontage_summary"]
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

        st.table(
            [
                {
                    "Current stage": layout["stage"],
                    "Generator": layout["stage_name"],
                    "Future Stage 2 ready": "Yes" if layout["stage_2_seed"]["ready"] else "No",
                    "Future parent zones": ", ".join(layout["stage_2_seed"]["micro_layout_parent_zones"]),
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
            for rectangle in layout["rectangles"]
        ]
        st.table(summary_rows)

    with st.expander("Validation Details", expanded=False):
        validation_rows = [
            {
                "Rule": check["rule"],
                "Pass": "Yes" if check["passed"] else "No",
                "Category": check["category"].title(),
                "Detail": check["detail"],
            }
            for check in layout["checks"]
        ]
        st.table(validation_rows)

    with st.expander("DXF Inspection", expanded=False):
        render_dxf_inspection(st.session_state.generated_dxf_report, st.session_state.generated_dxf_name)


def render_detail_placeholder_screen() -> None:
    st.markdown("<div class='eyebrow'>Stage 2</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Detailed Layout</div>", unsafe_allow_html=True)
    st.markdown(
        "<p class='soft-copy'>Stage 2 is reserved for finer planning inside the macro zones. The engine is not built yet, so this screen stays as a clean placeholder.</p>",
        unsafe_allow_html=True,
    )

    left_col, right_col = st.columns([0.92, 1.7], gap="large")
    with left_col:
        with st.container(border=True):
            st.markdown("<div class='panel-title'>Status</div>", unsafe_allow_html=True)
            st.write("Detailed layout generation coming next.")
            st.write("")
            st.write("Future stage will generate:")
            st.write("- POS")
            st.write("- Racking")
            st.write("- Admin rooms")
            st.write("- Doors")
            st.write("- Detailed receiving layout")

        if st.button("Back to Macro Review", type="primary", use_container_width=True):
            st.session_state.screen = "review"
            st.rerun()

        if st.button("Back to Home", use_container_width=True):
            st.session_state.screen = "home"
            st.rerun()

    with right_col:
        st.markdown(
            """
            <div class="placeholder-shell">
                <div>
                    <h2>Detailed layout generation coming next.</h2>
                    <p class="soft-copy">Future stage will generate:</p>
                    <ul>
                        <li>POS</li>
                        <li>Racking</li>
                        <li>Admin rooms</li>
                        <li>Doors</li>
                        <li>Detailed receiving layout</li>
                    </ul>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


st.set_page_config(page_title="Cashbuild Macro Layout Generator", layout="wide")
inject_styles()
init_state()

st.markdown("<div class='eyebrow'>Cashbuild Macro Layout Generator</div>", unsafe_allow_html=True)
st.caption("Rule-based retail layout generator")

current_screen = st.session_state.screen
if current_screen == "home":
    render_home_screen()
elif current_screen == "inputs":
    render_macro_inputs_screen()
elif current_screen == "review":
    render_macro_review_screen()
else:
    render_detail_placeholder_screen()
