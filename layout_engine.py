from __future__ import annotations

from cashbuild_spec import cashbuild_spec
from constraints import Rectangle, TARGET_AREAS_M2, score_layout, validate_layout

SIDES = ["north", "south", "east", "west"]
EPSILON = 1e-6

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
SIMPLIFIED_ROOM_SHARES = {
    "Passage": 0.18,
    "Cash Office": 0.22,
    "Male Toilets / Change": 0.20,
    "Female Toilets / Change": 0.20,
    "Canteen": 0.20,
}


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
    if entrance_side == "north":
        return Rectangle("Trading Area", 0.0, 0.0, building_width, building_depth - support_depth, True)
    if entrance_side == "south":
        return Rectangle("Trading Area", 0.0, support_depth, building_width, building_depth - support_depth, True)
    if entrance_side == "east":
        return Rectangle("Trading Area", 0.0, 0.0, building_width - support_depth, building_depth, True)
    return Rectangle("Trading Area", support_depth, 0.0, building_width - support_depth, building_depth, True)


def choose_admin_side(entrance_side: str, service_side: str, option: dict[str, object]) -> str:
    if entrance_side in {"north", "south"}:
        candidates = ["west", "east"]
    else:
        candidates = ["south", "north"]

    ordered = [side for side in candidates if side != service_side] + [side for side in candidates if side == service_side]
    if option["admin_side_priority"] == "far_end":
        ordered.reverse()
    return ordered[0]


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


def admin_strip_thickness(seed_rect: Rectangle, admin_side: str, option: dict[str, object]) -> float:
    target_area = admin_target_area()
    shape_factor = option["admin_shape_factor"]
    if admin_side in {"east", "west"}:
        thickness = (target_area / max(seed_rect.depth, 1.0)) * shape_factor
        return clamp(thickness, 4.2, max(4.2, seed_rect.width * 0.32))
    thickness = (target_area / max(seed_rect.width, 1.0)) * shape_factor
    return clamp(thickness, 4.2, max(4.2, seed_rect.depth * 0.32))


def receiving_strip_thickness(seed_rect: Rectangle, service_side: str, building_width: float, building_depth: float) -> float:
    target_area = receiving_target_area(building_width, building_depth)
    if service_side in {"north", "south"}:
        return clamp(target_area / max(seed_rect.width, 1.0), 4.0, max(4.0, seed_rect.depth * 0.22))
    return clamp(target_area / max(seed_rect.depth, 1.0), 4.0, max(4.0, seed_rect.width * 0.22))


def carve_edge(rectangle: Rectangle, side: str, thickness: float, label: str, internal: bool) -> tuple[Rectangle, Rectangle]:
    if side == "west":
        strip = Rectangle(label, rectangle.x, rectangle.y, thickness, rectangle.depth, internal)
        kept = Rectangle(rectangle.label, rectangle.x + thickness, rectangle.y, rectangle.width - thickness, rectangle.depth, rectangle.internal)
    elif side == "east":
        strip = Rectangle(label, rectangle.right - thickness, rectangle.y, thickness, rectangle.depth, internal)
        kept = Rectangle(rectangle.label, rectangle.x, rectangle.y, rectangle.width - thickness, rectangle.depth, rectangle.internal)
    elif side == "south":
        strip = Rectangle(label, rectangle.x, rectangle.y, rectangle.width, thickness, internal)
        kept = Rectangle(rectangle.label, rectangle.x, rectangle.y + thickness, rectangle.width, rectangle.depth - thickness, rectangle.internal)
    else:
        strip = Rectangle(label, rectangle.x, rectangle.top - thickness, rectangle.width, thickness, internal)
        kept = Rectangle(rectangle.label, rectangle.x, rectangle.y, rectangle.width, rectangle.depth - thickness, rectangle.internal)
    return kept, strip


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


def subdivide_admin_block(admin_block: Rectangle, trading_side: str, receiving_side: str) -> list[Rectangle]:
    """
    Simple schema-driven admin packing:
    - create the passage spine first on the side that connects back into trading
    - attach the cash office near the receiving relationship
    - fill the remaining two-by-two support rooms tightly with no internal gaps
    """

    rectangles: list[Rectangle] = []
    shares = SIMPLIFIED_ROOM_SHARES

    if admin_block.width >= admin_block.depth:
        passage_depth = clamp(admin_block.depth * shares["Passage"], 1.5, admin_block.depth * 0.28)
        passage_y = admin_block.y if trading_side == "south" else admin_block.top - passage_depth
        passage = Rectangle("Passage", admin_block.x, passage_y, admin_block.width, passage_depth, True)
        rectangles.append(passage)

        usable_y = admin_block.y + passage_depth if trading_side == "south" else admin_block.y
        usable_depth = admin_block.depth - passage_depth

        cash_width = admin_block.width * 0.28
        canteen_width = admin_block.width * 0.28
        middle_width = admin_block.width - cash_width - canteen_width

        if receiving_side == "west":
            cash_x = admin_block.x
            middle_x = cash_x + cash_width
            canteen_x = middle_x + middle_width
        else:
            canteen_x = admin_block.x
            middle_x = canteen_x + canteen_width
            cash_x = middle_x + middle_width

        half_depth = usable_depth / 2.0
        rectangles.extend(
            [
                Rectangle("Cash Office", cash_x, usable_y, cash_width, usable_depth, True),
                Rectangle("Male Toilets / Change", middle_x, usable_y + half_depth, middle_width, usable_depth - half_depth, True),
                Rectangle("Female Toilets / Change", middle_x, usable_y, middle_width, half_depth, True),
                Rectangle("Canteen", canteen_x, usable_y, canteen_width, usable_depth, True),
            ]
        )
        return rectangles

    passage_width = clamp(admin_block.width * shares["Passage"], 1.5, admin_block.width * 0.30)
    passage_x = admin_block.x if trading_side == "west" else admin_block.right - passage_width
    passage = Rectangle("Passage", passage_x, admin_block.y, passage_width, admin_block.depth, True)
    rectangles.append(passage)

    usable_x = admin_block.x + passage_width if trading_side == "west" else admin_block.x
    usable_width = admin_block.width - passage_width

    cash_depth = admin_block.depth * 0.28
    canteen_depth = admin_block.depth * 0.28
    middle_depth = admin_block.depth - cash_depth - canteen_depth

    if receiving_side == "south":
        cash_y = admin_block.y
        middle_y = cash_y + cash_depth
        canteen_y = middle_y + middle_depth
    else:
        canteen_y = admin_block.y
        middle_y = canteen_y + canteen_depth
        cash_y = middle_y + middle_depth

    half_width = usable_width / 2.0
    rectangles.extend(
        [
            Rectangle("Cash Office", usable_x, cash_y, usable_width, cash_depth, True),
            Rectangle("Male Toilets / Change", usable_x + half_width, middle_y, usable_width - half_width, middle_depth, True),
            Rectangle("Female Toilets / Change", usable_x, middle_y, half_width, middle_depth, True),
            Rectangle("Canteen", usable_x, canteen_y, usable_width, canteen_depth, True),
        ]
    )
    return rectangles


def option_variants() -> list[dict[str, object]]:
    return [
        {
            "name": "Option 1",
            "summary": "Balanced admin edge with centered service yard.",
            "admin_side_priority": "near_end",
            "yard_alignment": "center",
            "offloading_alignment": "end",
            "parking_alignment": "center",
            "admin_shape_factor": 1.00,
            "parking_depth_m": 9.0,
        },
        {
            "name": "Option 2",
            "summary": "Admin block shifts to another edge and parking biases to one end.",
            "admin_side_priority": "far_end",
            "yard_alignment": "end",
            "offloading_alignment": "center",
            "parking_alignment": "start",
            "admin_shape_factor": 1.08,
            "parking_depth_m": 10.0,
        },
        {
            "name": "Option 3",
            "summary": "Tighter admin proportion with a more compact service cluster.",
            "admin_side_priority": "near_end",
            "yard_alignment": "start",
            "offloading_alignment": "start",
            "parking_alignment": "end",
            "admin_shape_factor": 0.92,
            "parking_depth_m": 8.5,
        },
    ]


def package_option(
    name: str,
    summary: str,
    rectangles: list[Rectangle],
    pos_zones: list[Rectangle],
    frontage_openings: list[dict[str, object]],
    frontage_summary: dict[str, object],
    building_width: float,
    building_depth: float,
    entrance_side: str,
    service_side: str,
    requested_internal_area: float,
    reduction_reason: str,
) -> dict[str, object]:
    actual_internal_area = sum(
        rectangle.area
        for rectangle in rectangles
        if rectangle.internal and rectangle.label not in SIMPLIFIED_ROOM_SHARES
    )
    building_area = building_width * building_depth
    fit_efficiency = (actual_internal_area / requested_internal_area) * 100.0 if requested_internal_area else 0.0
    checks = validate_layout(
        rectangles,
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
        "rectangles": rectangles,
        "pos_zones": pos_zones,
        "frontage_openings": frontage_openings,
        "frontage_summary": frontage_summary,
        "score": score_layout(rectangles, checks, entrance_side),
        "checks": checks,
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
    option: dict[str, object],
    frontage_context: dict[str, object],
) -> dict[str, object]:
    requested_internal_area = trade_target_area() + admin_target_area() + receiving_target_area(building_width, building_depth)

    # Schema-driven planning order:
    # 1. dominant trading rectangle
    # 2. admin block attached to one side
    # 3. goods receiving as hinge to yard/off-loading
    # 4. site zones outside the envelope
    # 5. packed admin-room subdivision
    internal_seed = base_internal_rect(building_width, building_depth, entrance_side, frontage_context["support_depth_m"])
    admin_side = choose_admin_side(entrance_side, service_side, option)
    trading_side_for_admin = "east" if admin_side == "west" else "west" if admin_side == "east" else "north" if admin_side == "south" else "south"
    admin_thickness = admin_strip_thickness(internal_seed, admin_side, option)
    trading_seed, admin_block = carve_edge(internal_seed, admin_side, admin_thickness, "Admin Block", True)

    receiving_thickness = receiving_strip_thickness(trading_seed, service_side, building_width, building_depth)
    trading_area, goods_receiving = carve_edge(trading_seed, service_side, receiving_thickness, "Goods Receiving", True)

    yard = build_site_rectangle("Yard", goods_receiving, service_side, TARGET_AREAS_M2["Yard"], option["yard_alignment"])
    offloading = build_site_rectangle(
        "Off-loading Yard",
        yard,
        service_side,
        TARGET_AREAS_M2["Off-loading Yard"],
        option["offloading_alignment"],
    )
    parking = build_parking(building_width, building_depth, entrance_side, option)
    admin_rooms = subdivide_admin_block(admin_block, trading_side_for_admin, service_side)

    reduction_reason = (
        "The schema leaves some support-room sizes open-ended, so the MVP uses a packed rectangular "
        "admin arrangement and a practical receiving band sized from the overall shell."
    )

    return package_option(
        name=option["name"],
        summary=option["summary"],
        rectangles=[trading_area, admin_block, goods_receiving, yard, offloading, parking, *admin_rooms],
        pos_zones=frontage_context["pos_zones"],
        frontage_openings=frontage_context["openings"],
        frontage_summary=frontage_context,
        building_width=building_width,
        building_depth=building_depth,
        entrance_side=entrance_side,
        service_side=service_side,
        requested_internal_area=requested_internal_area,
        reduction_reason=reduction_reason,
    )


def generate_layout_options(
    building_width_m: float,
    building_depth_m: float,
    entrance_side: str,
    service_side: str,
) -> list[dict[str, object]]:
    frontage_context = build_frontage_context(building_width_m, building_depth_m, entrance_side)
    options = [
        build_candidate(building_width_m, building_depth_m, entrance_side, service_side, option, frontage_context)
        for option in option_variants()
    ]
    return sorted(options, key=lambda option: option["score"], reverse=True)
