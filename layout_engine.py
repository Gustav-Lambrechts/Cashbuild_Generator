from __future__ import annotations

from constraints import Rectangle, TARGET_AREAS_M2, score_layout, validate_layout

SIDES = ["north", "south", "east", "west"]
EPSILON = 1e-6
REQUESTED_TRADING_AREA = TARGET_AREAS_M2["Trading Area"]
REQUESTED_OFFICES_AREA = TARGET_AREAS_M2["Offices"]
REQUESTED_INTERNAL_AREA = REQUESTED_TRADING_AREA + REQUESTED_OFFICES_AREA

OPENING_CLEARANCE_DEPTH_M = 2.4
POS_ZONE_DEPTH_M = 2.4

FRONTAGE_OPENINGS_MM = [
    {
        "label": "Door 01",
        "type": "customer entrance",
        "width_mm": 1700,
        "left_edge_mm": 1770,
        "movable": True,
        "allowed_range_mm": (1770, 2380),
    },
    {
        "label": "Door 02",
        "type": "roller / opening",
        "width_mm": 2400,
        "left_edge_mm": 11160,
        "movable": True,
        "allowed_range_mm": (11160, 11500),
    },
    {
        "label": "Door 03",
        "type": "roller / opening",
        "width_mm": 2400,
        "left_edge_mm": 16360,
        "movable": True,
        "allowed_range_mm": (16360, 16495),
    },
    {
        "label": "Door 04",
        "type": "roller / opening",
        "width_mm": 4000,
        "left_edge_mm": 24560,
        "movable": True,
        "allowed_range_mm": (24560, 24700),
    },
]


def mm_to_m(value_mm: float) -> float:
    return value_mm / 1000.0


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def opposite_side(side: str) -> str:
    return {"north": "south", "south": "north", "east": "west", "west": "east"}[side]


def side_axis(side: str) -> str:
    return "horizontal" if side in {"north", "south"} else "vertical"


def align_offset(container_length: float, item_length: float, alignment: str) -> float:
    free_space = container_length - item_length
    if alignment == "start":
        return 0.0
    if alignment == "end":
        return free_space
    return free_space / 2.0


def office_dimensions(area: float, shape_factor: float) -> tuple[float, float]:
    width = max(4.0, (area * shape_factor) ** 0.5)
    depth = max(4.0, area / width)
    return width, depth


def fits_inside(rectangle: Rectangle, building_width: float, building_depth: float) -> bool:
    return (
        rectangle.x >= -EPSILON
        and rectangle.y >= -EPSILON
        and rectangle.right <= building_width + EPSILON
        and rectangle.top <= building_depth + EPSILON
    )


def entrance_wall_length(building_width: float, building_depth: float, entrance_side: str) -> float:
    return building_width if entrance_side in {"north", "south"} else building_depth


def frontage_openings_m() -> list[dict[str, object]]:
    openings: list[dict[str, object]] = []
    for opening in FRONTAGE_OPENINGS_MM:
        left_edge_m = mm_to_m(opening["left_edge_mm"])
        width_m = mm_to_m(opening["width_mm"])
        openings.append(
            {
                **opening,
                "left_edge_m": left_edge_m,
                "width_m": width_m,
                "right_edge_m": left_edge_m + width_m,
                "allowed_range_m": (
                    mm_to_m(opening["allowed_range_mm"][0]),
                    mm_to_m(opening["allowed_range_mm"][1]),
                ),
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
        gaps.append(
            {
                "label": f"POS Zone {index + 1}",
                "start_m": gap_start,
                "span_m": max(0.0, gap_end - gap_start),
            }
        )
    return gaps


def project_linear_span(
    start_m: float,
    span_m: float,
    entrance_side: str,
    building_width: float,
    building_depth: float,
) -> dict[str, float | str]:
    if entrance_side == "north":
        range_start = start_m
        range_end = start_m + span_m
        return {
            "axis": "horizontal",
            "range_start_m": range_start,
            "range_end_m": range_end,
            "span_m": span_m,
            "draw_x1": clamp(range_start, 0.0, building_width),
            "draw_y1": building_depth,
            "draw_x2": clamp(range_end, 0.0, building_width),
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
    range_start = start_m
    range_end = start_m + span_m
    return {
        "axis": "vertical",
        "range_start_m": range_start,
        "range_end_m": range_end,
        "span_m": span_m,
        "draw_x1": 0.0,
        "draw_y1": clamp(range_start, 0.0, building_depth),
        "draw_x2": 0.0,
        "draw_y2": clamp(range_end, 0.0, building_depth),
    }


def build_frontage_openings(
    building_width: float,
    building_depth: float,
    entrance_side: str,
) -> list[dict[str, object]]:
    projected_openings: list[dict[str, object]] = []
    for opening in frontage_openings_m():
        projection = project_linear_span(
            opening["left_edge_m"],
            opening["width_m"],
            entrance_side,
            building_width,
            building_depth,
        )
        projected_openings.append({**opening, **projection})
    return projected_openings


def build_opening_clearance_rectangles(
    frontage_openings: list[dict[str, object]],
    entrance_side: str,
    building_width: float,
    building_depth: float,
    clearance_depth: float,
) -> list[Rectangle]:
    clearance_rectangles: list[Rectangle] = []
    for opening in frontage_openings:
        if entrance_side == "north":
            rectangle = Rectangle(
                f"{opening['label']} Clearance",
                opening["range_start_m"],
                building_depth - clearance_depth,
                opening["span_m"],
                clearance_depth,
                True,
            )
        elif entrance_side == "south":
            rectangle = Rectangle(
                f"{opening['label']} Clearance",
                opening["range_start_m"],
                0.0,
                opening["span_m"],
                clearance_depth,
                True,
            )
        elif entrance_side == "east":
            rectangle = Rectangle(
                f"{opening['label']} Clearance",
                building_width - clearance_depth,
                opening["range_start_m"],
                clearance_depth,
                opening["span_m"],
                True,
            )
        else:
            rectangle = Rectangle(
                f"{opening['label']} Clearance",
                0.0,
                opening["range_start_m"],
                clearance_depth,
                opening["span_m"],
                True,
            )
        clearance_rectangles.append(rectangle)
    return clearance_rectangles


def build_pos_zone_rectangles(
    building_width: float,
    building_depth: float,
    entrance_side: str,
    pos_zone_depth: float,
    frontage_fits: bool,
) -> list[Rectangle]:
    if not frontage_fits or pos_zone_depth <= EPSILON:
        return []

    pos_zones: list[Rectangle] = []
    for gap in frontage_gap_definitions():
        if gap["span_m"] <= EPSILON:
            continue
        if entrance_side == "north":
            rectangle = Rectangle(
                gap["label"],
                gap["start_m"],
                building_depth - pos_zone_depth,
                gap["span_m"],
                pos_zone_depth,
                True,
            )
        elif entrance_side == "south":
            rectangle = Rectangle(
                gap["label"],
                building_width - gap["start_m"] - gap["span_m"],
                0.0,
                gap["span_m"],
                pos_zone_depth,
                True,
            )
        elif entrance_side == "east":
            rectangle = Rectangle(
                gap["label"],
                building_width - pos_zone_depth,
                building_depth - gap["start_m"] - gap["span_m"],
                pos_zone_depth,
                gap["span_m"],
                True,
            )
        else:
            rectangle = Rectangle(
                gap["label"],
                0.0,
                gap["start_m"],
                pos_zone_depth,
                gap["span_m"],
                True,
            )
        pos_zones.append(rectangle)
    return pos_zones


def build_frontage_context(
    building_width: float,
    building_depth: float,
    entrance_side: str,
) -> dict[str, object]:
    openings = build_frontage_openings(building_width, building_depth, entrance_side)
    wall_length = entrance_wall_length(building_width, building_depth, entrance_side)
    required_frontage_length = max(opening["right_edge_m"] for opening in frontage_openings_m())
    frontage_fits = wall_length + EPSILON >= required_frontage_length

    normal_depth = building_depth if entrance_side in {"north", "south"} else building_width
    available_for_pos = max(0.0, normal_depth - OPENING_CLEARANCE_DEPTH_M)
    pos_zone_depth = min(POS_ZONE_DEPTH_M, available_for_pos)
    opening_clearances = build_opening_clearance_rectangles(
        openings,
        entrance_side,
        building_width,
        building_depth,
        OPENING_CLEARANCE_DEPTH_M,
    )
    pos_zones = build_pos_zone_rectangles(
        building_width,
        building_depth,
        entrance_side,
        pos_zone_depth,
        frontage_fits,
    )

    return {
        "openings": openings,
        "opening_clearance_depth_m": OPENING_CLEARANCE_DEPTH_M,
        "pos_zone_depth_m": pos_zone_depth,
        "support_depth_m": pos_zone_depth,
        "frontage_fits": frontage_fits,
        "entrance_wall_length_m": wall_length,
        "required_frontage_length_m": required_frontage_length,
        "pos_zone_count": len(pos_zones),
        "required_pos_zone_count": len(frontage_gap_definitions()),
        "opening_clearance_rects": opening_clearances,
        "pos_zones": pos_zones,
    }


def place_adjacent(
    label: str,
    internal: bool,
    base: Rectangle,
    side: str,
    width: float,
    depth: float,
    alignment: str = "center",
) -> Rectangle:
    if side == "north":
        x = base.x + align_offset(base.width, width, alignment)
        y = base.top
    elif side == "south":
        x = base.x + align_offset(base.width, width, alignment)
        y = base.y - depth
    elif side == "east":
        x = base.right
        y = base.y + align_offset(base.depth, depth, alignment)
    elif side == "west":
        x = base.x - width
        y = base.y + align_offset(base.depth, depth, alignment)
    else:
        raise ValueError(f"Unsupported side: {side}")
    return Rectangle(label=label, x=x, y=y, width=width, depth=depth, internal=internal)


def build_office(
    trading: Rectangle,
    entrance_side: str,
    office_area: float,
    building_width: float,
    building_depth: float,
    variant_index: int,
) -> Rectangle:
    candidate_sides = [opposite_side(entrance_side)]
    candidate_sides.extend(side for side in SIDES if side not in candidate_sides and side != entrance_side)
    preferred_width, preferred_depth = office_dimensions(office_area, [0.95, 1.05, 1.15][variant_index])
    alignments = [
        ["start", "center", "end"],
        ["center", "end", "start"],
        ["end", "start", "center"],
    ][variant_index]

    for side in candidate_sides:
        if side == "north":
            available_depth = building_depth - trading.top
            if available_depth < 4.0:
                continue
            depth = min(preferred_depth, available_depth)
            width = office_area / depth
        elif side == "south":
            available_depth = trading.y
            if available_depth < 4.0:
                continue
            depth = min(preferred_depth, available_depth)
            width = office_area / depth
        elif side == "east":
            available_width = building_width - trading.right
            if available_width < 4.0:
                continue
            width = min(preferred_width, available_width)
            depth = office_area / width
        else:
            available_width = trading.x
            if available_width < 4.0:
                continue
            width = min(preferred_width, available_width)
            depth = office_area / width

        if width <= building_width + EPSILON:
            width = min(width, building_width)
        if depth <= building_depth + EPSILON:
            depth = min(depth, building_depth)
        if width < 4.0 or depth < 4.0 or width > building_width or depth > building_depth:
            continue

        for alignment in alignments:
            office = place_adjacent("Offices", True, trading, side, width, depth, alignment=alignment)
            if fits_inside(office, building_width, building_depth):
                return office

    return Rectangle("Offices", 0.0, 0.0, 4.0, 4.0, True)


def build_trading_rectangle(
    area: float,
    office_area: float,
    building_width: float,
    building_depth: float,
    entrance_side: str,
    service_side: str,
    variant_index: int,
    support_depth: float,
) -> Rectangle:
    usable_x_min = support_depth if entrance_side == "west" else 0.0
    usable_x_max = building_width - support_depth if entrance_side == "east" else building_width
    usable_y_min = support_depth if entrance_side == "south" else 0.0
    usable_y_max = building_depth - support_depth if entrance_side == "north" else building_depth

    usable_width = usable_x_max - usable_x_min
    usable_depth = usable_y_max - usable_y_min

    if entrance_side in {"north", "south"}:
        office_reserve = max(4.0, office_area / max(usable_width, 1.0))
        max_depth = max(6.0, usable_depth - office_reserve)
        preferred_width = usable_width * [0.60, 0.75, 0.90][variant_index]
        width = clamp(max(preferred_width, area / max(max_depth, 1.0)), 6.0, usable_width)
        depth = area / width

        if service_side == "west":
            x = usable_x_min
        elif service_side == "east":
            x = usable_x_max - width
        else:
            x = usable_x_min + align_offset(usable_width, width, ["start", "center", "end"][variant_index])
        y = usable_y_max - depth if entrance_side == "north" else usable_y_min
    else:
        office_reserve = max(4.0, office_area / max(usable_depth, 1.0))
        max_width = max(6.0, usable_width - office_reserve)
        preferred_depth = usable_depth * [0.60, 0.75, 0.90][variant_index]
        depth = clamp(max(preferred_depth, area / max(max_width, 1.0)), 6.0, usable_depth)
        width = area / depth

        if service_side == "south":
            y = usable_y_min
        elif service_side == "north":
            y = usable_y_max - depth
        else:
            y = usable_y_min + align_offset(usable_depth, depth, ["start", "center", "end"][variant_index])
        x = usable_x_max - width if entrance_side == "east" else usable_x_min

    return Rectangle("Trading Area", x, y, width, depth, True)


def build_yard(
    area: float,
    trading: Rectangle,
    service_side: str,
    building_width: float,
    building_depth: float,
    variant_index: int,
) -> Rectangle:
    overlap_factor = [0.72, 0.86, 1.0][variant_index]
    if service_side in {"north", "south"}:
        span = max(min(trading.width * overlap_factor, trading.width), min(6.0, trading.width))
        depth = max(4.0, area / max(span, 1.0))
        x = trading.x + align_offset(trading.width, span, ["start", "center", "end"][variant_index])
        y = building_depth if service_side == "north" else -depth
        return Rectangle("Yard", x, y, span, depth, False)

    span = max(min(trading.depth * overlap_factor, trading.depth), min(6.0, trading.depth))
    width = max(4.0, area / max(span, 1.0))
    x = building_width if service_side == "east" else -width
    y = trading.y + align_offset(trading.depth, span, ["start", "center", "end"][variant_index])
    return Rectangle("Yard", x, y, width, span, False)


def build_offloading_yard(
    area: float,
    yard: Rectangle,
    service_side: str,
    variant_index: int,
) -> Rectangle:
    if service_side in {"north", "south"}:
        width = max(4.0, yard.width * [0.55, 0.70, 0.85][variant_index])
        depth = max(4.0, area / width)
        x = yard.x + align_offset(yard.width, width, ["end", "center", "start"][variant_index])
        y = yard.top if service_side == "north" else yard.y - depth
        return Rectangle("Off-loading Yard", x, y, width, depth, False)

    depth = max(4.0, yard.depth * [0.55, 0.70, 0.85][variant_index])
    width = max(4.0, area / depth)
    x = yard.right if service_side == "east" else yard.x - width
    y = yard.y + align_offset(yard.depth, depth, ["end", "center", "start"][variant_index])
    return Rectangle("Off-loading Yard", x, y, width, depth, False)


def package_option(
    name: str,
    rectangles: list[Rectangle],
    pos_zones: list[Rectangle],
    frontage_openings: list[dict[str, object]],
    frontage_summary: dict[str, object],
    building_width: float,
    building_depth: float,
    entrance_side: str,
    service_side: str,
    requested_internal_area: float,
    reduction_reason: str | None,
) -> dict[str, object]:
    actual_internal_area = sum(rectangle.area for rectangle in rectangles if rectangle.internal)
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
    score = score_layout(rectangles, checks, entrance_side)
    return {
        "name": name,
        "rectangles": rectangles,
        "pos_zones": pos_zones,
        "frontage_openings": frontage_openings,
        "frontage_summary": frontage_summary,
        "score": score,
        "checks": checks,
        "internal_summary": {
            "building_footprint_area_m2": round(building_area, 1),
            "requested_internal_area_m2": round(requested_internal_area, 1),
            "actual_generated_internal_area_m2": round(actual_internal_area, 1),
            "internal_fit_efficiency_percent": round(fit_efficiency, 1),
            "areas_reduced": actual_internal_area + EPSILON < requested_internal_area,
            "reason": reduction_reason
            if actual_internal_area + EPSILON < requested_internal_area
            else "Full requested internal targets fit inside the building footprint.",
        },
    }


def hard_rules_pass(option: dict[str, object]) -> bool:
    return all(check["passed"] for check in option["checks"] if check["category"] == "hard")


def build_candidate_for_scale(
    building_width: float,
    building_depth: float,
    entrance_side: str,
    service_side: str,
    variant_index: int,
    internal_scale: float,
    reduction_reason: str | None,
    frontage_context: dict[str, object],
) -> dict[str, object]:
    trading_area = REQUESTED_TRADING_AREA * internal_scale
    offices_area = REQUESTED_OFFICES_AREA * internal_scale
    support_depth = frontage_context["support_depth_m"]

    trading = build_trading_rectangle(
        area=trading_area,
        office_area=offices_area,
        building_width=building_width,
        building_depth=building_depth,
        entrance_side=entrance_side,
        service_side=service_side,
        variant_index=variant_index,
        support_depth=support_depth,
    )
    offices = build_office(
        trading=trading,
        entrance_side=entrance_side,
        office_area=offices_area,
        building_width=building_width,
        building_depth=building_depth,
        variant_index=variant_index,
    )
    yard = build_yard(TARGET_AREAS_M2["Yard"], trading, service_side, building_width, building_depth, variant_index)
    offloading = build_offloading_yard(TARGET_AREAS_M2["Off-loading Yard"], yard, service_side, variant_index)

    option_frontage_summary = {
        **frontage_context,
        "openings_fixed_mm": True,
        "trading_connection_basis": "Trading Area must sit behind the entrance support zone and overlap the frontage openings.",
    }

    return package_option(
        name=f"Option {variant_index + 1}",
        rectangles=[trading, offices, yard, offloading],
        pos_zones=frontage_context["pos_zones"],
        frontage_openings=frontage_context["openings"],
        frontage_summary=option_frontage_summary,
        building_width=building_width,
        building_depth=building_depth,
        entrance_side=entrance_side,
        service_side=service_side,
        requested_internal_area=REQUESTED_INTERNAL_AREA,
        reduction_reason=reduction_reason,
    )


def reduction_reason_for_scale(
    building_width: float,
    building_depth: float,
    frontage_context: dict[str, object],
) -> str:
    building_area = building_width * building_depth
    if building_area + EPSILON < REQUESTED_INTERNAL_AREA:
        return (
            f"The building footprint area ({building_area:.1f} m²) is smaller than the requested "
            f"internal area ({REQUESTED_INTERNAL_AREA:.1f} m²)."
        )
    if not frontage_context["frontage_fits"]:
        return "The fixed frontage opening sequence does not fit on the current entrance wall."
    return (
        "The full internal targets could not fit this option while preserving the frontage openings, "
        "the 2400 mm clear strip, POS zones, and the other hard rules."
    )


def build_candidate(
    building_width: float,
    building_depth: float,
    entrance_side: str,
    service_side: str,
    variant_index: int,
    frontage_context: dict[str, object],
) -> dict[str, object]:
    full_target_option = build_candidate_for_scale(
        building_width=building_width,
        building_depth=building_depth,
        entrance_side=entrance_side,
        service_side=service_side,
        variant_index=variant_index,
        internal_scale=1.0,
        reduction_reason=None,
        frontage_context=frontage_context,
    )
    if hard_rules_pass(full_target_option):
        return full_target_option

    low = 0.35
    high = 1.0
    best_option: dict[str, object] | None = None
    reduction_reason = reduction_reason_for_scale(building_width, building_depth, frontage_context)

    for _ in range(18):
        mid = (low + high) / 2.0
        option = build_candidate_for_scale(
            building_width=building_width,
            building_depth=building_depth,
            entrance_side=entrance_side,
            service_side=service_side,
            variant_index=variant_index,
            internal_scale=mid,
            reduction_reason=reduction_reason,
            frontage_context=frontage_context,
        )
        if hard_rules_pass(option):
            best_option = option
            low = mid
        else:
            high = mid

    if best_option is not None:
        return best_option

    fallback_scale = min(1.0, (building_width * building_depth) / max(REQUESTED_INTERNAL_AREA, 1.0))
    return build_candidate_for_scale(
        building_width=building_width,
        building_depth=building_depth,
        entrance_side=entrance_side,
        service_side=service_side,
        variant_index=variant_index,
        internal_scale=max(0.35, fallback_scale),
        reduction_reason=reduction_reason,
        frontage_context=frontage_context,
    )


def generate_layout_options(
    building_width_m: float,
    building_depth_m: float,
    entrance_side: str,
    service_side: str,
) -> list[dict[str, object]]:
    frontage_context = build_frontage_context(building_width_m, building_depth_m, entrance_side)
    options = [
        build_candidate(
            building_width_m,
            building_depth_m,
            entrance_side,
            service_side,
            variant_index,
            frontage_context,
        )
        for variant_index in range(3)
    ]
    options = sorted(options, key=lambda option: option["score"], reverse=True)

    for index, option in enumerate(options, start=1):
        option["name"] = f"Option {index}"

    return options
