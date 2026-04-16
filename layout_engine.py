from __future__ import annotations

from constraints import Rectangle, TARGET_AREAS_M2, score_layout, validate_layout

SIDES = ["north", "south", "east", "west"]
EPSILON = 1e-6
REQUESTED_TRADING_AREA = TARGET_AREAS_M2["Trading Area"]
REQUESTED_OFFICES_AREA = TARGET_AREAS_M2["Offices"]
REQUESTED_INTERNAL_AREA = REQUESTED_TRADING_AREA + REQUESTED_OFFICES_AREA


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
        rectangle.x >= 0.0
        and rectangle.y >= 0.0
        and rectangle.right <= building_width
        and rectangle.top <= building_depth
    )


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
        if side in {"north", "south"} and entrance_side in {"east", "west"}:
            preferred = "start" if entrance_side == "east" else "end"
            side_alignments = [preferred] + [alignment for alignment in alignments if alignment != preferred]
        elif side in {"east", "west"} and entrance_side in {"north", "south"}:
            preferred = "start" if entrance_side == "north" else "end"
            side_alignments = [preferred] + [alignment for alignment in alignments if alignment != preferred]
        else:
            side_alignments = alignments

        if side == "north":
            available_depth = building_depth - trading.top
            if available_depth < 4.0:
                continue
            depth = min(preferred_depth, available_depth)
            width = office_area / depth
            if width > building_width:
                depth = available_depth
                width = office_area / depth
        elif side == "south":
            available_depth = trading.y
            if available_depth < 4.0:
                continue
            depth = min(preferred_depth, available_depth)
            width = office_area / depth
            if width > building_width:
                depth = available_depth
                width = office_area / depth
        elif side == "east":
            available_width = building_width - trading.right
            if available_width < 4.0:
                continue
            width = min(preferred_width, available_width)
            depth = office_area / width
            if depth > building_depth:
                width = available_width
                depth = office_area / width
        else:
            available_width = trading.x
            if available_width < 4.0:
                continue
            width = min(preferred_width, available_width)
            depth = office_area / width
            if depth > building_depth:
                width = available_width
                depth = office_area / width

        if width < 4.0 or depth < 4.0 or width > building_width or depth > building_depth:
            if width <= building_width + EPSILON:
                width = min(width, building_width)
            if depth <= building_depth + EPSILON:
                depth = min(depth, building_depth)
        if width < 4.0 or depth < 4.0 or width > building_width or depth > building_depth:
            continue

        for alignment in side_alignments:
            office = place_adjacent(
                "Offices",
                True,
                trading,
                side,
                width,
                depth,
                alignment=alignment,
            )
            if fits_inside(office, building_width, building_depth):
                return office

    for side in candidate_sides:
        if side == "west":
            compact_width = max(4.0, min(preferred_width, trading.x))
            compact_depth = max(4.0, min(preferred_depth, trading.depth, building_depth))
        elif side == "east":
            compact_width = max(4.0, min(preferred_width, building_width - trading.right))
            compact_depth = max(4.0, min(preferred_depth, trading.depth, building_depth))
        elif side == "north":
            compact_width = max(4.0, min(preferred_width, trading.width, building_width))
            compact_depth = max(4.0, min(preferred_depth, building_depth - trading.top))
        else:
            compact_width = max(4.0, min(preferred_width, trading.width, building_width))
            compact_depth = max(4.0, min(preferred_depth, trading.y))

        for alignment in side_alignments:
            office = place_adjacent(
                "Offices",
                True,
                trading,
                side,
                compact_width,
                compact_depth,
                alignment=alignment,
            )
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
) -> Rectangle:
    if entrance_side == service_side:
        if entrance_side in {"north", "south"}:
            office_reserve = max(4.0, office_area / max(building_width, 1.0))
            max_depth = max(6.0, building_depth - office_reserve)
            preferred_width = building_width * [0.56, 0.68, 0.80][variant_index]
            width = clamp(
                max(preferred_width, area / max(max_depth, 1.0)),
                min(6.0, building_width),
                building_width,
            )
            depth = area / width
            x = align_offset(building_width, width, ["start", "center", "end"][variant_index])
            y = building_depth - depth if entrance_side == "north" else 0.0
        else:
            office_reserve = max(4.0, office_area / max(building_depth, 1.0))
            max_width = max(6.0, building_width - office_reserve)
            preferred_depth = building_depth * [0.56, 0.68, 0.80][variant_index]
            depth = clamp(
                max(preferred_depth, area / max(max_width, 1.0)),
                min(6.0, building_depth),
                building_depth,
            )
            width = area / depth
            x = building_width - width if entrance_side == "east" else 0.0
            y = align_offset(building_depth, depth, ["start", "center", "end"][variant_index])
    elif side_axis(entrance_side) != side_axis(service_side):
        if entrance_side in {"north", "south"}:
            office_reserve = max(4.0, office_area / max(building_width, 1.0))
            max_depth = max(6.0, building_depth - office_reserve)
            preferred_width = building_width * [0.54, 0.66, 0.78][variant_index]
            width = clamp(
                max(preferred_width, area / max(max_depth, 1.0)),
                min(6.0, building_width),
                building_width,
            )
            depth = area / width
        else:
            office_reserve = max(4.0, office_area / max(building_depth, 1.0))
            max_width = max(6.0, building_width - office_reserve)
            preferred_depth = building_depth * [0.54, 0.66, 0.78][variant_index]
            depth = clamp(
                max(preferred_depth, area / max(max_width, 1.0)),
                min(6.0, building_depth),
                building_depth,
            )
            width = area / depth

        if entrance_side in {"west", "east"}:
            x = 0.0 if entrance_side == "west" else building_width - width
            y = 0.0 if service_side == "south" else building_depth - depth
        else:
            x = 0.0 if service_side == "west" else building_width - width
            y = 0.0 if entrance_side == "south" else building_depth - depth
    else:
        if entrance_side in {"north", "south"}:
            office_reserve = max(4.0, office_area / max(building_depth, 1.0))
            max_width = max(6.0, building_width - office_reserve)
            depth = building_depth
            width = clamp(area / depth, min(6.0, building_width), max_width)
            x = align_offset(building_width, width, ["start", "center", "end"][variant_index])
            y = 0.0
        else:
            office_reserve = max(4.0, office_area / max(building_width, 1.0))
            max_depth = max(6.0, building_depth - office_reserve)
            width = building_width
            depth = clamp(area / width, min(6.0, building_depth), max_depth)
            x = 0.0
            y = align_offset(building_depth, depth, ["start", "center", "end"][variant_index])

    return Rectangle("Trading Area", x, y, width, depth, True)


def service_span_length(trading: Rectangle, service_side: str) -> float:
    return trading.width if service_side in {"north", "south"} else trading.depth


def build_yard(
    area: float,
    trading: Rectangle,
    service_side: str,
    variant_index: int,
) -> Rectangle:
    overlap_factor = [0.72, 0.86, 1.0][variant_index]
    if service_side in {"north", "south"}:
        span = max(min(trading.width * overlap_factor, trading.width), min(6.0, trading.width))
        depth = max(4.0, area / max(span, 1.0))
        x = trading.x + align_offset(trading.width, span, ["start", "center", "end"][variant_index])
        y = trading.top if service_side == "north" else -depth
        return Rectangle("Yard", x, y, span, depth, False)

    span = max(min(trading.depth * overlap_factor, trading.depth), min(6.0, trading.depth))
    width = max(4.0, area / max(span, 1.0))
    x = trading.right if service_side == "east" else -width
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
        "score": score,
        "checks": checks,
        "internal_summary": {
            "building_footprint_area_m2": round(building_area, 1),
            "requested_internal_area_m2": round(requested_internal_area, 1),
            "actual_generated_internal_area_m2": round(actual_internal_area, 1),
            "internal_fit_efficiency_percent": round(fit_efficiency, 1),
            "areas_reduced": actual_internal_area + 1e-6 < requested_internal_area,
            "reason": reduction_reason
            if actual_internal_area + 1e-6 < requested_internal_area
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
) -> dict[str, object]:
    trading_area = REQUESTED_TRADING_AREA * internal_scale
    offices_area = REQUESTED_OFFICES_AREA * internal_scale

    trading = build_trading_rectangle(
        area=trading_area,
        office_area=offices_area,
        building_width=building_width,
        building_depth=building_depth,
        entrance_side=entrance_side,
        service_side=service_side,
        variant_index=variant_index,
    )
    offices = build_office(
        trading=trading,
        entrance_side=entrance_side,
        office_area=offices_area,
        building_width=building_width,
        building_depth=building_depth,
        variant_index=variant_index,
    )
    yard = build_yard(TARGET_AREAS_M2["Yard"], trading, service_side, variant_index)
    offloading = build_offloading_yard(TARGET_AREAS_M2["Off-loading Yard"], yard, service_side, variant_index)

    return package_option(
        name=f"Option {variant_index + 1}",
        rectangles=[trading, offices, yard, offloading],
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
    full_target_valid: bool,
) -> str:
    building_area = building_width * building_depth
    if building_area + 1e-6 < REQUESTED_INTERNAL_AREA:
        return (
            f"The building footprint area ({building_area:.1f} m²) is smaller than the requested "
            f"internal area ({REQUESTED_INTERNAL_AREA:.1f} m²)."
        )
    if not full_target_valid:
        return (
            "The full internal targets could not fit this option while preserving the entrance, service-side, "
            "and adjacency hard rules."
        )
    return "Internal areas were reduced to fit the building footprint and hard rules."


def build_candidate(
    building_width: float,
    building_depth: float,
    entrance_side: str,
    service_side: str,
    variant_index: int,
) -> dict[str, object]:
    full_target_option = build_candidate_for_scale(
        building_width=building_width,
        building_depth=building_depth,
        entrance_side=entrance_side,
        service_side=service_side,
        variant_index=variant_index,
        internal_scale=1.0,
        reduction_reason=None,
    )
    if hard_rules_pass(full_target_option):
        return full_target_option

    low = 0.35
    high = 1.0
    best_option: dict[str, object] | None = None
    reduction_reason = reduction_reason_for_scale(
        building_width=building_width,
        building_depth=building_depth,
        full_target_valid=False,
    )

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
        )
        if hard_rules_pass(option):
            best_option = option
            low = mid
        else:
            high = mid

    if best_option is not None:
        return best_option

    fallback_scale = min(1.0, (building_width * building_depth) / REQUESTED_INTERNAL_AREA)
    return build_candidate_for_scale(
        building_width=building_width,
        building_depth=building_depth,
        entrance_side=entrance_side,
        service_side=service_side,
        variant_index=variant_index,
        internal_scale=max(0.35, fallback_scale),
        reduction_reason=reduction_reason_for_scale(
            building_width=building_width,
            building_depth=building_depth,
            full_target_valid=False,
        ),
    )


def generate_layout_options(
    building_width_m: float,
    building_depth_m: float,
    entrance_side: str,
    service_side: str,
) -> list[dict[str, object]]:
    options = [
        build_candidate(building_width_m, building_depth_m, entrance_side, service_side, variant_index)
        for variant_index in range(3)
    ]
    options = sorted(options, key=lambda option: option["score"], reverse=True)

    for index, option in enumerate(options, start=1):
        option["name"] = f"Option {index}"

    return options
