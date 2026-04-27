from __future__ import annotations

from cashbuild_spec import cashbuild_spec
from constraints import Rectangle, TARGET_AREAS_M2, score_layout, validate_layout

SIDES = ["north", "south", "east", "west"]
POSITIONS = ["left", "middle", "right"]
EPSILON = 1e-6
BAND_DEPTH_M = 6.23

SPACE_BY_NAME = {space["name"]: space for space in cashbuild_spec["spaces"]}

# The spec defines opening types and sizes but not exact frontage positions.
# For this MVP we keep a simple fixed frontage sequence so the existing
# Streamlit workflow and frontage drawing still work.
SIMPLIFIED_FRONTAGE_OPENINGS_MM = [
    {"label": "Door 01", "type": "customer entrance", "width_mm": 1700, "left_edge_mm": 1770},
    {"label": "Door 02", "type": "roller / opening", "width_mm": 2400, "left_edge_mm": 11160},
    {"label": "Door 03", "type": "roller / opening", "width_mm": 2400, "left_edge_mm": 16360},
    {"label": "Door 04", "type": "roller / opening", "width_mm": 4000, "left_edge_mm": 24560},
]
OPENING_CLEARANCE_DEPTH_M = 2.4
POS_ZONE_DEPTH_M = 2.4

# The schema leaves some room sizes open-ended. For the MVP we use a simple,
# readable split that respects adjacency intent without pretending to be a full
# building-code engine yet.
def mm_to_m(value_mm: float) -> float:
    return value_mm / 1000.0


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def align_offset(container_length: float, item_length: float, alignment: str) -> float:
    free_space = max(0.0, container_length - item_length)
    if alignment == "start":
        return 0.0
    if alignment == "end":
        return free_space
    return free_space / 2.0


def entrance_wall_length(building_width: float, building_depth: float, entrance_side: str) -> float:
    return building_width if entrance_side in {"north", "south"} else building_depth


def frontage_openings_m() -> list[dict[str, object]]:
    openings: list[dict[str, object]] = []
    for opening in SIMPLIFIED_FRONTAGE_OPENINGS_MM:
        left_edge_m = mm_to_m(opening["left_edge_mm"])
        width_m = mm_to_m(opening["width_mm"])
        openings.append(
            {
                **opening,
                "left_edge_m": left_edge_m,
                "width_m": width_m,
                "right_edge_m": left_edge_m + width_m,
            }
        )
    return openings


def frontage_gap_definitions() -> list[dict[str, object]]:
    openings = frontage_openings_m()
    gaps: list[dict[str, object]] = []
    for index in range(len(openings) - 1):
        previous = openings[index]
        following = openings[index + 1]
        gap_start = previous["right_edge_m"]
        gap_end = following["left_edge_m"]
        gaps.append({"label": f"POS Zone {index + 1}", "start_m": gap_start, "span_m": max(0.0, gap_end - gap_start)})
    return gaps


def project_linear_span(
    start_m: float,
    span_m: float,
    entrance_side: str,
    building_width: float,
    building_depth: float,
) -> dict[str, float | str]:
    if entrance_side == "north":
        return {
            "axis": "horizontal",
            "range_start_m": start_m,
            "range_end_m": start_m + span_m,
            "span_m": span_m,
            "draw_x1": clamp(start_m, 0.0, building_width),
            "draw_y1": building_depth,
            "draw_x2": clamp(start_m + span_m, 0.0, building_width),
            "draw_y2": building_depth,
        }
    if entrance_side == "south":
        range_start = building_width - start_m - span_m
        range_end = building_width - start_m
        return {
            "axis": "horizontal",
            "range_start_m": range_start,
            "range_end_m": range_end,
            "span_m": span_m,
            "draw_x1": clamp(range_start, 0.0, building_width),
            "draw_y1": 0.0,
            "draw_x2": clamp(range_end, 0.0, building_width),
            "draw_y2": 0.0,
        }
    if entrance_side == "east":
        range_start = building_depth - start_m - span_m
        range_end = building_depth - start_m
        return {
            "axis": "vertical",
            "range_start_m": range_start,
            "range_end_m": range_end,
            "span_m": span_m,
            "draw_x1": building_width,
            "draw_y1": clamp(range_start, 0.0, building_depth),
            "draw_x2": building_width,
            "draw_y2": clamp(range_end, 0.0, building_depth),
        }
    return {
        "axis": "vertical",
        "range_start_m": start_m,
        "range_end_m": start_m + span_m,
        "span_m": span_m,
        "draw_x1": 0.0,
        "draw_y1": clamp(start_m, 0.0, building_depth),
        "draw_x2": 0.0,
        "draw_y2": clamp(start_m + span_m, 0.0, building_depth),
    }


def build_frontage_openings(building_width: float, building_depth: float, entrance_side: str) -> list[dict[str, object]]:
    return [
        {**opening, **project_linear_span(opening["left_edge_m"], opening["width_m"], entrance_side, building_width, building_depth)}
        for opening in frontage_openings_m()
    ]


def build_opening_clearance_rectangles(
    frontage_openings: list[dict[str, object]],
    entrance_side: str,
    building_width: float,
    building_depth: float,
    clearance_depth: float,
) -> list[Rectangle]:
    rectangles: list[Rectangle] = []
    for opening in frontage_openings:
        if entrance_side == "north":
            rectangle = Rectangle(f"{opening['label']} Clearance", opening["range_start_m"], building_depth - clearance_depth, opening["span_m"], clearance_depth, True)
        elif entrance_side == "south":
            rectangle = Rectangle(f"{opening['label']} Clearance", opening["range_start_m"], 0.0, opening["span_m"], clearance_depth, True)
        elif entrance_side == "east":
            rectangle = Rectangle(f"{opening['label']} Clearance", building_width - clearance_depth, opening["range_start_m"], clearance_depth, opening["span_m"], True)
        else:
            rectangle = Rectangle(f"{opening['label']} Clearance", 0.0, opening["range_start_m"], clearance_depth, opening["span_m"], True)
        rectangles.append(rectangle)
    return rectangles


def build_pos_zone_rectangles(
    building_width: float,
    building_depth: float,
    entrance_side: str,
    pos_zone_depth: float,
    frontage_fits: bool,
) -> list[Rectangle]:
    if not frontage_fits or pos_zone_depth <= EPSILON:
        return []

    rectangles: list[Rectangle] = []
    for gap in frontage_gap_definitions():
        if gap["span_m"] <= EPSILON:
            continue
        if entrance_side == "north":
            rectangle = Rectangle(gap["label"], gap["start_m"], building_depth - pos_zone_depth, gap["span_m"], pos_zone_depth, True)
        elif entrance_side == "south":
            rectangle = Rectangle(gap["label"], building_width - gap["start_m"] - gap["span_m"], 0.0, gap["span_m"], pos_zone_depth, True)
        elif entrance_side == "east":
            rectangle = Rectangle(gap["label"], building_width - pos_zone_depth, building_depth - gap["start_m"] - gap["span_m"], pos_zone_depth, gap["span_m"], True)
        else:
            rectangle = Rectangle(gap["label"], 0.0, gap["start_m"], pos_zone_depth, gap["span_m"], True)
        rectangles.append(rectangle)
    return rectangles


def build_frontage_context(building_width: float, building_depth: float, entrance_side: str) -> dict[str, object]:
    frontage_spec = cashbuild_spec["known_constraints_for_generator"]
    opening_clearance_depth = OPENING_CLEARANCE_DEPTH_M
    openings = build_frontage_openings(building_width, building_depth, entrance_side)
    wall_length = entrance_wall_length(building_width, building_depth, entrance_side)
    required_frontage_length = max(opening["right_edge_m"] for opening in frontage_openings_m())
    frontage_fits = wall_length + EPSILON >= required_frontage_length

    normal_depth = building_depth if entrance_side in {"north", "south"} else building_width
    pos_zone_depth = min(POS_ZONE_DEPTH_M, max(0.0, normal_depth - opening_clearance_depth))
    pos_zones = build_pos_zone_rectangles(building_width, building_depth, entrance_side, pos_zone_depth, frontage_fits)

    return {
        "openings": openings,
        "opening_clearance_depth_m": opening_clearance_depth,
        "pos_zone_depth_m": pos_zone_depth,
        "support_depth_m": pos_zone_depth,
        "frontage_fits": frontage_fits,
        "entrance_wall_length_m": wall_length,
        "required_frontage_length_m": required_frontage_length,
        "pos_zone_count": len(pos_zones),
        "required_pos_zone_count": len(frontage_gap_definitions()),
        "front_loading_hardstand_min_m2": frontage_spec["front_loading_hardstand_min_m2"],
        "opening_clearance_rects": build_opening_clearance_rectangles(
            openings, entrance_side, building_width, building_depth, opening_clearance_depth
        ),
        "pos_zones": pos_zones,
    }


def base_internal_rect(building_width: float, building_depth: float, entrance_side: str, support_depth: float) -> Rectangle:
    return Rectangle("Trading Area", 0.0, 0.0, building_width, building_depth, True)


def trade_target_area() -> float:
    return cashbuild_spec["global_rules"]["structure"]["trading_floor_target_internal_area_m2"]


def trade_min_area() -> float:
    return cashbuild_spec["global_rules"]["structure"]["trading_floor_min_internal_area_m2"]


def admin_target_area() -> float:
    return cashbuild_spec["global_rules"]["admin_block"]["target_area_m2"]


def receiving_target_area(building_width: float, building_depth: float) -> float:
    # Schema says this is still an unknown to confirm, so the MVP uses a simple
    # practical placeholder based on the expected trading relationship.
    preferred = 90.0
    return min(preferred, max(70.0, 0.08 * building_width * building_depth))


def receiving_strip_thickness(seed_rect: Rectangle, service_side: str, building_width: float, building_depth: float) -> float:
    target_area = receiving_target_area(building_width, building_depth)
    if service_side in {"north", "south"}:
        return clamp(target_area / max(seed_rect.width, 1.0), 4.0, max(4.0, seed_rect.depth * 0.22))
    return clamp(target_area / max(seed_rect.depth, 1.0), 4.0, max(4.0, seed_rect.width * 0.22))


def wall_position_local_start(wall_length: float, item_length: float, position: str) -> float:
    free_space = max(0.0, wall_length - item_length)
    if position == "left":
        return 0.0
    if position == "right":
        return free_space
    return free_space / 2.0


def side_along_length(side: str, building_width: float, building_depth: float) -> float:
    return building_width if side in {"north", "south"} else building_depth


def preferred_trading_dimensions() -> tuple[float, float]:
    preferred = cashbuild_spec["global_rules"]["structure"]["trading_floor_preferred_dimensions_m"]
    return float(preferred[0]), float(preferred[1])


def local_start_to_world_offset(
    side: str,
    local_start: float,
    along_size: float,
    building_width: float,
    building_depth: float,
) -> float:
    if side == "north":
        return local_start
    if side == "south":
        return building_width - local_start - along_size
    if side == "east":
        return building_depth - local_start - along_size
    return local_start


def place_rectangle_outside_trading(
    label: str,
    side: str,
    local_start: float,
    band_depth: float,
    along_size: float,
    building_width: float,
    building_depth: float,
    internal: bool,
) -> Rectangle:
    if side == "north":
        x = local_start_to_world_offset(side, local_start, along_size, building_width, building_depth)
        return Rectangle(label, x, building_depth, along_size, band_depth, internal)
    if side == "south":
        x = local_start_to_world_offset(side, local_start, along_size, building_width, building_depth)
        return Rectangle(label, x, -band_depth, along_size, band_depth, internal)
    if side == "east":
        y = local_start_to_world_offset(side, local_start, along_size, building_width, building_depth)
        return Rectangle(label, building_width, y, band_depth, along_size, internal)
    y = local_start_to_world_offset(side, local_start, along_size, building_width, building_depth)
    return Rectangle(label, -band_depth, y, band_depth, along_size, internal)


def opposite_position(position: str) -> str:
    if position == "left":
        return "right"
    if position == "right":
        return "left"
    return "middle"


def choose_receiving_position(service_side: str, admin_side: str, admin_position: str, option: dict[str, object]) -> list[str]:
    preferred = option["receiving_position"]
    if service_side != admin_side:
        return [preferred, "middle", "left", "right"]
    opposite = opposite_position(admin_position)
    return [opposite, preferred, "middle", "left", "right"]


def build_admin_and_receiving_band(
    building_width: float,
    building_depth: float,
    admin_side: str,
    admin_position: str,
) -> tuple[Rectangle, Rectangle]:
    wall_length = side_along_length(admin_side, building_width, building_depth)
    admin_length = min(wall_length, admin_target_area() / BAND_DEPTH_M)
    admin_local_start = wall_position_local_start(wall_length, admin_length, admin_position)

    admin_block = place_rectangle_outside_trading(
        "Admin Block",
        admin_side,
        admin_local_start,
        BAND_DEPTH_M,
        admin_length,
        building_width,
        building_depth,
        True,
    )

    receiving_target_length = receiving_target_area(building_width, building_depth) / BAND_DEPTH_M
    left_space = admin_local_start
    right_space = max(0.0, wall_length - admin_local_start - admin_length)

    if admin_position == "left":
        preferred_side = "right"
    elif admin_position == "right":
        preferred_side = "left"
    else:
        preferred_side = "right" if right_space >= left_space else "left"

    candidate_sides = [preferred_side, "left" if preferred_side == "right" else "right"]
    receiving_local_start = 0.0
    receiving_length = 0.0

    for side_name in candidate_sides:
        available = right_space if side_name == "right" else left_space
        if available <= EPSILON:
            continue
        receiving_length = max(4.0, min(receiving_target_length, available))
        if receiving_length > available + EPSILON:
            receiving_length = available
        if side_name == "right":
            receiving_local_start = admin_local_start + admin_length
        else:
            receiving_local_start = admin_local_start - receiving_length
        break

    if receiving_length <= EPSILON:
        fallback_length = max(4.0, min(receiving_target_length, wall_length))
        receiving_length = min(wall_length, fallback_length)
        receiving_local_start = wall_position_local_start(wall_length, receiving_length, "middle")

    goods_receiving = place_rectangle_outside_trading(
        "Goods Receiving",
        admin_side,
        receiving_local_start,
        BAND_DEPTH_M,
        receiving_length,
        building_width,
        building_depth,
        True,
    )
    return admin_block, goods_receiving


def trading_preference_summary(trading_area: Rectangle) -> str:
    preferred_width, preferred_depth = preferred_trading_dimensions()
    return (
        f"Trading Area uses the entered shop size directly at {trading_area.width:.2f} m x {trading_area.depth:.2f} m. "
        f"The preferred proportion is {preferred_width:.0f} m x {preferred_depth:.0f} m where possible."
    )


def choose_service_alignment_from_admin(
    service_side: str,
    admin_side: str,
    admin_position: str,
    fallback_alignment: str,
) -> str:
    if service_side == admin_side:
        return fallback_alignment

    if service_side in {"north", "south"} and admin_side in {"north", "south"}:
        return fallback_alignment
    if service_side in {"east", "west"} and admin_side in {"east", "west"}:
        return fallback_alignment

    if admin_position == "middle":
        return "center"
    if admin_position == "left":
        return "start"
    return "end"


def build_site_rectangle(label: str, anchor: Rectangle, side: str, area: float, alignment: str, fixed_depth: float | None = None) -> Rectangle:
    if side in {"north", "south"}:
        width = anchor.width if label == "Parking" else max(6.0, anchor.width * 0.90)
        if label == "Off-loading Yard":
            width = max(6.0, anchor.width * 0.72)
        depth = fixed_depth or max(4.0, area / max(width, 1.0))
        x = anchor.x + align_offset(anchor.width, width, alignment)
        y = anchor.top if side == "north" else anchor.y - depth
        return Rectangle(label, x, y, width, depth, False)

    depth = anchor.depth if label == "Parking" else max(6.0, anchor.depth * 0.90)
    if label == "Off-loading Yard":
        depth = max(6.0, anchor.depth * 0.72)
    width = fixed_depth or max(4.0, area / max(depth, 1.0))
    x = anchor.right if side == "east" else anchor.x - width
    y = anchor.y + align_offset(anchor.depth, depth, alignment)
    return Rectangle(label, x, y, width, depth, False)


def build_parking(building_width: float, building_depth: float, entrance_side: str, option: dict[str, object]) -> Rectangle:
    depth = option["parking_depth_m"]
    if entrance_side == "north":
        return Rectangle("Parking", 0.0, building_depth, building_width, depth, False)
    if entrance_side == "south":
        return Rectangle("Parking", 0.0, -depth, building_width, depth, False)
    if entrance_side == "east":
        return Rectangle("Parking", building_width, 0.0, depth, building_depth, False)
    return Rectangle("Parking", -depth, 0.0, depth, building_depth, False)


def option_variants() -> list[dict[str, object]]:
    return [
        {
            "name": "Option 1",
            "summary": "Balanced admin edge with centered service yard.",
            "yard_alignment": "center",
            "offloading_alignment": "end",
            "parking_alignment": "center",
            "receiving_position": "middle",
            "parking_depth_m": 9.0,
        },
        {
            "name": "Option 2",
            "summary": "Admin block shifts to another edge and parking biases to one end.",
            "yard_alignment": "end",
            "offloading_alignment": "center",
            "parking_alignment": "start",
            "receiving_position": "left",
            "parking_depth_m": 10.0,
        },
        {
            "name": "Option 3",
            "summary": "Tighter admin proportion with a more compact service cluster.",
            "yard_alignment": "start",
            "offloading_alignment": "start",
            "parking_alignment": "end",
            "receiving_position": "right",
            "parking_depth_m": 8.5,
        },
    ]


def package_option(
    name: str,
    summary: str,
    macro_rectangles: list[Rectangle],
    pos_zones: list[Rectangle],
    frontage_openings: list[dict[str, object]],
    frontage_summary: dict[str, object],
    building_width: float,
    building_depth: float,
    entrance_side: str,
    service_side: str,
    admin_block_side: str,
    admin_block_position: str,
    requested_internal_area: float,
    reduction_reason: str,
) -> dict[str, object]:
    actual_internal_area = sum(rectangle.area for rectangle in macro_rectangles if rectangle.internal)
    building_area = building_width * building_depth
    fit_efficiency = (actual_internal_area / requested_internal_area) * 100.0 if requested_internal_area else 0.0
    checks = validate_layout(
        macro_rectangles,
        pos_zones,
        frontage_openings,
        frontage_summary,
        building_width,
        building_depth,
        entrance_side,
        service_side,
        requested_internal_area=requested_internal_area,
        reduction_reason=reduction_reason,
    )
    return {
        "name": name,
        "summary": summary,
        "rectangles": macro_rectangles,
        "macro_rectangles": macro_rectangles,
        "controls": {
            "admin_block_side": admin_block_side,
            "admin_block_position": admin_block_position,
        },
        "pos_zones": pos_zones,
        "frontage_openings": frontage_openings,
        "frontage_summary": frontage_summary,
        "score": score_layout(macro_rectangles, checks, entrance_side),
        "checks": checks,
        "stage": "Stage 1",
        "stage_name": "Macro Layout Generator",
        "stage_2_seed": {
            "ready": True,
            "message": "Future Stage 2 can place micro layouts inside the internal macro zones.",
            "micro_layout_parent_zones": ["Trading Area", "Admin Block", "Goods Receiving"],
        },
        "internal_summary": {
            "building_footprint_area_m2": round(building_area, 1),
            "requested_internal_area_m2": round(requested_internal_area, 1),
            "actual_generated_internal_area_m2": round(actual_internal_area, 1),
            "internal_fit_efficiency_percent": round(fit_efficiency, 1),
            "areas_reduced": actual_internal_area + EPSILON < requested_internal_area,
            "reason": reduction_reason,
        },
    }


def build_candidate(
    building_width: float,
    building_depth: float,
    entrance_side: str,
    service_side: str,
    admin_block_side: str,
    admin_block_position: str,
    option: dict[str, object],
    frontage_context: dict[str, object],
) -> dict[str, object]:
    requested_internal_area = building_width * building_depth

    # Schema-driven planning order:
    # 1. lock Trading Area to the entered shop width and depth
    # 2. attach an Admin + Goods Receiving band outside the selected wall
    # 3. place Yard on the service side without reducing Trading Area
    # 4. attach Off-loading Yard to Yard
    # Stage 1 stops here and leaves micro-layout subdivision for a future Stage 2.
    trading_area = base_internal_rect(building_width, building_depth, entrance_side, 0.0)
    admin_block, goods_receiving = build_admin_and_receiving_band(
        building_width=building_width,
        building_depth=building_depth,
        admin_side=admin_block_side,
        admin_position=admin_block_position,
    )

    yard_anchor = trading_area
    yard_alignment = choose_service_alignment_from_admin(
        service_side=service_side,
        admin_side=admin_block_side,
        admin_position=admin_block_position,
        fallback_alignment=option["yard_alignment"],
    )
    yard = build_site_rectangle("Yard", yard_anchor, service_side, TARGET_AREAS_M2["Yard"], yard_alignment)
    offloading = build_site_rectangle(
        "Off-loading Yard",
        yard,
        service_side,
        TARGET_AREAS_M2["Off-loading Yard"],
        option["offloading_alignment"],
    )
    parking = build_parking(building_width, building_depth, entrance_side, option)

    reduction_reason = (
        "Stage 1 uses the entered shop width and depth as the Trading Area itself. "
        "Admin Block, Goods Receiving, Yard, and Off-loading attach around that anchor geometry."
    )

    macro_rectangles = [trading_area, admin_block, goods_receiving, yard, offloading, parking]

    return package_option(
        name=option["name"],
        summary=option["summary"],
        macro_rectangles=macro_rectangles,
        pos_zones=frontage_context["pos_zones"],
        frontage_openings=frontage_context["openings"],
        frontage_summary=frontage_context,
        building_width=building_width,
        building_depth=building_depth,
        entrance_side=entrance_side,
        service_side=service_side,
        admin_block_side=admin_block_side,
        admin_block_position=admin_block_position,
        requested_internal_area=requested_internal_area,
        reduction_reason=reduction_reason,
    )


def generate_layout_options(
    building_width_m: float,
    building_depth_m: float,
    entrance_side: str,
    service_side: str,
    admin_block_side: str | None = None,
    admin_block_position: str | None = None,
) -> list[dict[str, object]]:
    selected_admin_side = admin_block_side if admin_block_side in SIDES else service_side
    selected_admin_position = admin_block_position if admin_block_position in POSITIONS else "middle"
    frontage_context = build_frontage_context(building_width_m, building_depth_m, entrance_side)
    options = [
        build_candidate(
            building_width_m,
            building_depth_m,
            entrance_side,
            service_side,
            selected_admin_side,
            selected_admin_position,
            option,
            frontage_context,
        )
        for option in option_variants()
    ]
    return sorted(options, key=lambda option: option["score"], reverse=True)


def generate_best_layout(
    building_width_m: float,
    building_depth_m: float,
    entrance_side: str,
    service_side: str,
    admin_block_side: str | None = None,
    admin_block_position: str | None = None,
) -> dict[str, object]:
    """
    Keep the existing ranked option logic, but return only the best macro layout
    for the simplified MVP flow.
    """

    best_option = generate_layout_options(
        building_width_m=building_width_m,
        building_depth_m=building_depth_m,
        entrance_side=entrance_side,
        service_side=service_side,
        admin_block_side=admin_block_side,
        admin_block_position=admin_block_position,
    )[0]
    return {
        **best_option,
        "name": "Best Macro Layout",
    }
