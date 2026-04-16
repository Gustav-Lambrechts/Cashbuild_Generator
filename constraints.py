from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

EPSILON = 1e-6

TARGET_AREAS_M2 = {
    "Trading Area": 1250.0,
    "Offices": 130.0,
    "Yard": 800.0,
    "Off-loading Yard": 400.0,
}

MIN_DIMENSIONS_M = {
    "Offices": {"width": 4.0, "depth": 4.0},
    "Yard": {"width": 6.0},
    "Off-loading Yard": {"width": 4.0},
}


@dataclass
class Rectangle:
    label: str
    x: float
    y: float
    width: float
    depth: float
    internal: bool

    @property
    def area(self) -> float:
        return self.width * self.depth

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y + self.depth

    @property
    def aspect_ratio(self) -> float:
        short_side = max(min(self.width, self.depth), EPSILON)
        return max(self.width, self.depth) / short_side


def get_rectangle_map(rectangles: Iterable[Rectangle]) -> dict[str, Rectangle]:
    return {rectangle.label: rectangle for rectangle in rectangles}


def overlap_length(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def share_edge(rect_a: Rectangle, rect_b: Rectangle) -> bool:
    vertical_touch = (
        abs(rect_a.right - rect_b.x) < EPSILON or abs(rect_b.right - rect_a.x) < EPSILON
    ) and overlap_length(rect_a.y, rect_a.top, rect_b.y, rect_b.top) > EPSILON
    horizontal_touch = (
        abs(rect_a.top - rect_b.y) < EPSILON or abs(rect_b.top - rect_a.y) < EPSILON
    ) and overlap_length(rect_a.x, rect_a.right, rect_b.x, rect_b.right) > EPSILON
    return vertical_touch or horizontal_touch


def overlaps(rect_a: Rectangle, rect_b: Rectangle) -> bool:
    x_overlap = overlap_length(rect_a.x, rect_a.right, rect_b.x, rect_b.right)
    y_overlap = overlap_length(rect_a.y, rect_a.top, rect_b.y, rect_b.top)
    return x_overlap > EPSILON and y_overlap > EPSILON


def touches_boundary(rectangle: Rectangle, side: str, building_width: float, building_depth: float) -> bool:
    if side == "north":
        return abs(rectangle.top - building_depth) < EPSILON
    if side == "south":
        return abs(rectangle.y) < EPSILON
    if side == "east":
        return abs(rectangle.right - building_width) < EPSILON
    if side == "west":
        return abs(rectangle.x) < EPSILON
    raise ValueError(f"Unsupported side: {side}")


def touches_building_side(rectangle: Rectangle, side: str, building_width: float, building_depth: float) -> bool:
    if side == "north":
        return abs(rectangle.y - building_depth) < EPSILON
    if side == "south":
        return abs(rectangle.top) < EPSILON
    if side == "east":
        return abs(rectangle.x - building_width) < EPSILON
    if side == "west":
        return abs(rectangle.right) < EPSILON
    raise ValueError(f"Unsupported side: {side}")


def within_building(rectangle: Rectangle, building_width: float, building_depth: float) -> bool:
    return (
        rectangle.x >= -EPSILON
        and rectangle.y >= -EPSILON
        and rectangle.right <= building_width + EPSILON
        and rectangle.top <= building_depth + EPSILON
    )


def outside_building(rectangle: Rectangle, building_width: float, building_depth: float) -> bool:
    x_overlap = overlap_length(rectangle.x, rectangle.right, 0.0, building_width)
    y_overlap = overlap_length(rectangle.y, rectangle.top, 0.0, building_depth)
    return not (x_overlap > EPSILON and y_overlap > EPSILON)


def projection_overlap_on_side(
    rect_a: Rectangle,
    rect_b: Rectangle,
    side: str,
) -> float:
    if side in {"north", "south"}:
        return overlap_length(rect_a.x, rect_a.right, rect_b.x, rect_b.right)
    return overlap_length(rect_a.y, rect_a.top, rect_b.y, rect_b.top)


def is_grouped_on_service_side(
    rectangle: Rectangle,
    service_side: str,
    building_width: float,
    building_depth: float,
) -> bool:
    if service_side == "north":
        return rectangle.y >= building_depth - EPSILON
    if service_side == "south":
        return rectangle.top <= EPSILON
    if service_side == "east":
        return rectangle.x >= building_width - EPSILON
    if service_side == "west":
        return rectangle.right <= EPSILON
    raise ValueError(f"Unsupported side: {service_side}")


def compactness_score(rectangle: Rectangle) -> float:
    return max(0.0, 1.0 - (rectangle.aspect_ratio - 1.0) / 4.0)


def trading_breadth_score(rectangle: Rectangle, entrance_side: str) -> float:
    if entrance_side in {"north", "south"}:
        ratio = rectangle.width / max(rectangle.depth, EPSILON)
    else:
        ratio = rectangle.depth / max(rectangle.width, EPSILON)
    return min(1.0, max(0.0, ratio / 3.0))


def make_check(rule: str, passed: bool, detail: str, category: str = "hard") -> dict[str, object]:
    return {
        "rule": rule,
        "passed": passed,
        "detail": detail,
        "category": category,
    }


def validate_layout(
    rectangles: list[Rectangle],
    building_width: float,
    building_depth: float,
    entrance_side: str,
    service_side: str,
    requested_internal_area: float,
    reduction_reason: str | None = None,
) -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []
    rectangle_map = get_rectangle_map(rectangles)

    trading = rectangle_map["Trading Area"]
    offices = rectangle_map["Offices"]
    yard = rectangle_map["Yard"]
    offloading = rectangle_map["Off-loading Yard"]

    internal_rectangles = [rectangle for rectangle in rectangles if rectangle.internal]
    external_rectangles = [rectangle for rectangle in rectangles if not rectangle.internal]
    building_area = building_width * building_depth
    actual_internal_area = sum(rectangle.area for rectangle in internal_rectangles)

    checks.append(
        make_check(
            "Internal spaces fit inside the building footprint",
            all(within_building(rectangle, building_width, building_depth) for rectangle in internal_rectangles),
            "Trading Area and Offices stay inside the building footprint.",
        )
    )

    checks.append(
        make_check(
            "External spaces stay outside the building footprint",
            all(outside_building(rectangle, building_width, building_depth) for rectangle in external_rectangles),
            "Yard and Off-loading Yard stay outside the building footprint, except for shared edges.",
        )
    )

    overlaps_found = any(
        overlaps(rectangles[index], rectangles[other_index])
        for index in range(len(rectangles))
        for other_index in range(index + 1, len(rectangles))
    )
    checks.append(
        make_check(
            "Rectangles do not overlap",
            not overlaps_found,
            "Spaces use separate footprints with shared edges only.",
        )
    )

    checks.append(
        make_check(
            "Trading Area touches Offices",
            share_edge(trading, offices),
            "Trading Area and Offices share an edge.",
        )
    )

    yard_aligned_with_trading = (
        touches_boundary(trading, service_side, building_width, building_depth)
        and touches_building_side(yard, service_side, building_width, building_depth)
        and projection_overlap_on_side(trading, yard, service_side) > EPSILON
    )
    checks.append(
        make_check(
            "Yard touches the building on the service side aligned with Trading Area",
            yard_aligned_with_trading,
            "Yard shares the service-side building edge over a span that overlaps Trading Area.",
        )
    )

    checks.append(
        make_check(
            "Off-loading Yard touches Yard",
            share_edge(offloading, yard),
            "Off-loading Yard and Yard share an edge.",
        )
    )

    checks.append(
        make_check(
            "Offices avoid the entrance side",
            not touches_boundary(offices, entrance_side, building_width, building_depth),
            "Offices do not touch the entrance-side building boundary.",
        )
    )

    checks.append(
        make_check(
            "Trading Area touches the entrance side",
            touches_boundary(trading, entrance_side, building_width, building_depth),
            "Trading Area connects directly to the entrance-side building boundary.",
        )
    )

    grouped_on_service_side = is_grouped_on_service_side(
        yard, service_side, building_width, building_depth
    ) and is_grouped_on_service_side(offloading, service_side, building_width, building_depth)
    checks.append(
        make_check(
            "Yard cluster stays grouped on the service side",
            grouped_on_service_side,
            "Yard and Off-loading Yard remain outside the building on the service side.",
        )
    )

    checks.append(
        make_check(
            "Internal and external designation is correct",
            trading.internal and offices.internal and not yard.internal and not offloading.internal,
            "Trading Area and Offices are internal; Yard spaces are external.",
        )
    )

    internal_area_reduced = actual_internal_area + EPSILON < requested_internal_area
    if internal_area_reduced:
        detail = (
            f"Internal areas were reduced to {actual_internal_area:.1f} m² from the requested "
            f"{requested_internal_area:.1f} m². {reduction_reason or 'The building could not fit the full internal targets while keeping the hard rules.'}"
        )
    else:
        detail = (
            f"Full internal targets fit inside the building footprint. "
            f"Building area: {building_area:.1f} m², generated internal area: {actual_internal_area:.1f} m²."
        )
    checks.append(
        make_check(
            "Internal area fit summary",
            not internal_area_reduced,
            detail,
            category="quality",
        )
    )

    checks.append(
        make_check(
            "Offices meet the minimum width",
            offices.width >= MIN_DIMENSIONS_M["Offices"]["width"],
            f"Offices width is {offices.width:.1f} m.",
            category="quality",
        )
    )
    checks.append(
        make_check(
            "Offices meet the minimum depth",
            offices.depth >= MIN_DIMENSIONS_M["Offices"]["depth"],
            f"Offices depth is {offices.depth:.1f} m.",
            category="quality",
        )
    )
    checks.append(
        make_check(
            "Yard meets the minimum width",
            max(yard.width, yard.depth) >= MIN_DIMENSIONS_M["Yard"]["width"],
            f"Yard footprint is {yard.width:.1f} x {yard.depth:.1f} m.",
            category="quality",
        )
    )
    checks.append(
        make_check(
            "Off-loading Yard meets the minimum width",
            max(offloading.width, offloading.depth) >= MIN_DIMENSIONS_M["Off-loading Yard"]["width"],
            f"Off-loading Yard footprint is {offloading.width:.1f} x {offloading.depth:.1f} m.",
            category="quality",
        )
    )

    return checks


def score_layout(
    rectangles: list[Rectangle],
    checks: list[dict[str, object]],
    entrance_side: str,
) -> float:
    rectangle_map = get_rectangle_map(rectangles)
    trading = rectangle_map["Trading Area"]
    offices = rectangle_map["Offices"]
    yard = rectangle_map["Yard"]
    offloading = rectangle_map["Off-loading Yard"]

    hard_checks = [check for check in checks if check["category"] == "hard"]
    hard_pass_rate = sum(bool(check["passed"]) for check in hard_checks) / max(len(hard_checks), 1)

    adjacency_checks = [
        check
        for check in checks
        if check["rule"]
        in {
            "Trading Area touches Offices",
            "Yard touches the building on the service side aligned with Trading Area",
            "Off-loading Yard touches Yard",
            "Yard cluster stays grouped on the service side",
        }
    ]
    adjacency_score = sum(bool(check["passed"]) for check in adjacency_checks) / max(len(adjacency_checks), 1)

    entrance_checks = [
        check
        for check in checks
        if check["rule"] in {"Trading Area touches the entrance side", "Offices avoid the entrance side"}
    ]
    entrance_score = sum(bool(check["passed"]) for check in entrance_checks) / max(len(entrance_checks), 1)

    proportion_score = (
        compactness_score(offices) * 0.30
        + compactness_score(yard) * 0.15
        + compactness_score(offloading) * 0.15
        + trading_breadth_score(trading, entrance_side) * 0.40
    )
    compactness = sum(compactness_score(rectangle) for rectangle in rectangles) / len(rectangles)

    score = (
        adjacency_score * 40.0
        + entrance_score * 20.0
        + proportion_score * 20.0
        + compactness * 20.0
    )
    score *= 0.55 + 0.45 * hard_pass_rate

    return round(score, 1)
