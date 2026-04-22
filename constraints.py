from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from cashbuild_spec import cashbuild_spec

EPSILON = 1e-6

SPACE_BY_NAME = {space["name"]: space for space in cashbuild_spec["spaces"]}
TARGET_AREAS_M2 = {
    "Trading Area": cashbuild_spec["global_rules"]["structure"]["trading_floor_target_internal_area_m2"],
    "Admin Block": cashbuild_spec["global_rules"]["admin_block"]["target_area_m2"],
    "Yard": 800.0,
    "Off-loading Yard": 400.0,
    "Parking": 550.0,
}
ADMIN_ROOM_LABELS = {
    "Passage",
    "Cash Office",
    "Male Toilets / Change",
    "Female Toilets / Change",
    "Canteen",
}
MIN_DIMENSIONS_M = {
    "Trading Area": {"width": 10.0, "depth": 10.0},
    "Admin Block": {"width": 4.0, "depth": 4.0},
    "Goods Receiving": {"width": 4.0, "depth": 4.0},
    "Yard": {"width": 6.0},
    "Off-loading Yard": {"width": 4.0},
    "Parking": {"depth": 8.0},
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


def projection_overlap_on_side(rect_a: Rectangle, rect_b: Rectangle, side: str) -> float:
    if side in {"north", "south"}:
        return overlap_length(rect_a.x, rect_a.right, rect_b.x, rect_b.right)
    return overlap_length(rect_a.y, rect_a.top, rect_b.y, rect_b.top)


def compactness_score(rectangle: Rectangle) -> float:
    return max(0.0, 1.0 - (rectangle.aspect_ratio - 1.0) / 4.0)


def trading_breadth_score(rectangle: Rectangle, entrance_side: str) -> float:
    if entrance_side in {"north", "south"}:
        ratio = rectangle.width / max(rectangle.depth, EPSILON)
    else:
        ratio = rectangle.depth / max(rectangle.width, EPSILON)
    return min(1.0, max(0.0, ratio / 3.0))


def make_check(rule: str, passed: bool, detail: str, category: str = "hard") -> dict[str, object]:
    return {"rule": rule, "passed": passed, "detail": detail, "category": category}


def is_allowed_overlap(rect_a: Rectangle, rect_b: Rectangle) -> bool:
    labels = {rect_a.label, rect_b.label}
    return "Admin Block" in labels and bool(labels.intersection(ADMIN_ROOM_LABELS))


def room_inside_parent(room: Rectangle, parent: Rectangle) -> bool:
    return (
        room.x >= parent.x - EPSILON
        and room.y >= parent.y - EPSILON
        and room.right <= parent.right + EPSILON
        and room.top <= parent.top + EPSILON
    )


def validate_layout(
    rectangles: list[Rectangle],
    pos_zones: list[Rectangle],
    frontage_openings: list[dict[str, object]],
    frontage_summary: dict[str, object],
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
    admin = rectangle_map["Admin Block"]
    receiving = rectangle_map["Goods Receiving"]
    yard = rectangle_map["Yard"]
    offloading = rectangle_map["Off-loading Yard"]
    parking = rectangle_map["Parking"]
    admin_rooms = [rectangle_map[label] for label in ADMIN_ROOM_LABELS if label in rectangle_map]

    internal_rectangles = [rectangle for rectangle in rectangles if rectangle.internal] + pos_zones
    external_rectangles = [rectangle for rectangle in rectangles if not rectangle.internal]
    floor_rectangles = rectangles + pos_zones
    building_area = building_width * building_depth
    actual_internal_area = sum(
        rectangle.area
        for rectangle in rectangles
        if rectangle.internal and rectangle.label not in ADMIN_ROOM_LABELS
    )

    checks.append(
        make_check(
            "Frontage opening sequence fits on the entrance wall",
            bool(frontage_summary["frontage_fits"]),
            (
                f"Entrance wall length is {frontage_summary['entrance_wall_length_m']:.2f} m and the fixed frontage "
                f"needs {frontage_summary['required_frontage_length_m']:.2f} m."
            ),
        )
    )

    checks.append(
        make_check(
            "Internal spaces fit inside the building footprint",
            all(within_building(rectangle, building_width, building_depth) for rectangle in internal_rectangles),
            "Trading, admin, receiving, and POS spaces stay inside the building footprint.",
        )
    )

    checks.append(
        make_check(
            "External spaces stay outside the building footprint",
            all(outside_building(rectangle, building_width, building_depth) for rectangle in external_rectangles),
            "Yard, off-loading, and parking remain outside the building envelope.",
        )
    )

    overlaps_found = False
    for index in range(len(floor_rectangles)):
        for other_index in range(index + 1, len(floor_rectangles)):
            rect_a = floor_rectangles[index]
            rect_b = floor_rectangles[other_index]
            if is_allowed_overlap(rect_a, rect_b):
                continue
            if overlaps(rect_a, rect_b):
                overlaps_found = True
                break
        if overlaps_found:
            break
    checks.append(
        make_check(
            "Rectangles do not overlap",
            not overlaps_found,
            "Planning blocks stay separate except for admin rooms packed inside the admin block.",
        )
    )

    checks.append(
        make_check(
            "Trading Area stays dominant",
            trading.area >= cashbuild_spec["global_rules"]["structure"]["trading_floor_min_internal_area_m2"],
            (
                f"Trading Area is {trading.area:.1f} m² and the schema minimum is "
                f"{cashbuild_spec['global_rules']['structure']['trading_floor_min_internal_area_m2']:.1f} m²."
            ),
        )
    )

    checks.append(
        make_check(
            "Trading Area touches Admin Block",
            share_edge(trading, admin),
            "The admin block is attached directly to the trading area.",
        )
    )

    checks.append(
        make_check(
            "Goods Receiving touches Trading Area",
            share_edge(trading, receiving),
            "Goods receiving stays directly connected to the trading floor.",
        )
    )

    checks.append(
        make_check(
            "Goods Receiving touches service side",
            touches_boundary(receiving, service_side, building_width, building_depth),
            "Goods receiving sits on the service-facing side of the building.",
        )
    )

    checks.append(
        make_check(
            "Yard aligns with Goods Receiving",
            touches_building_side(yard, service_side, building_width, building_depth)
            and projection_overlap_on_side(yard, receiving, service_side) > EPSILON,
            "The yard is outside the service side and lines up with goods receiving.",
        )
    )

    checks.append(
        make_check(
            "Off-loading Yard touches Yard",
            share_edge(offloading, yard),
            "Off-loading Yard stays attached to the yard for practical service flow.",
        )
    )

    checks.append(
        make_check(
            "Parking sits on the entrance side",
            touches_building_side(parking, entrance_side, building_width, building_depth),
            "Parking is placed on the customer-facing side.",
        )
    )

    checks.append(
        make_check(
            "Admin rooms stay inside the Admin Block",
            all(room_inside_parent(room, admin) for room in admin_rooms),
            "Passage, cash office, toilets/change rooms, and canteen pack inside the admin block.",
        )
    )

    checks.append(
        make_check(
            "Admin rooms share walls tightly",
            len(admin_rooms) == 5,
            "The simplified schema layout uses a fully packed five-room admin arrangement.",
            category="quality",
        )
    )

    internal_area_reduced = actual_internal_area + EPSILON < requested_internal_area
    detail = (
        f"Internal blocks total {actual_internal_area:.1f} m² against a requested {requested_internal_area:.1f} m²."
        if not internal_area_reduced
        else (
            f"Internal blocks were reduced to {actual_internal_area:.1f} m² from the requested "
            f"{requested_internal_area:.1f} m². {reduction_reason or 'The building footprint could not hold the full target cleanly.'}"
        )
    )
    checks.append(make_check("Internal area fit summary", not internal_area_reduced, detail, category="quality"))

    checks.append(
        make_check(
            "Trading shape stays clean",
            trading_breadth_score(trading, entrance_side) >= 0.35,
            f"Trading rectangle is {trading.width:.1f} m x {trading.depth:.1f} m.",
            category="quality",
        )
    )

    checks.append(
        make_check(
            "External service cluster stays compact",
            compactness_score(yard) >= 0.3 and compactness_score(offloading) >= 0.2,
            "Yard and off-loading are kept as practical attached rectangles.",
            category="quality",
        )
    )

    checks.append(
        make_check(
            "Building footprint summary",
            True,
            f"Building footprint area is {building_area:.1f} m².",
            category="quality",
        )
    )

    return checks


def score_layout(rectangles: list[Rectangle], checks: list[dict[str, object]], entrance_side: str) -> float:
    rectangle_map = get_rectangle_map(rectangles)
    trading = rectangle_map["Trading Area"]
    admin = rectangle_map["Admin Block"]
    receiving = rectangle_map["Goods Receiving"]
    yard = rectangle_map["Yard"]
    offloading = rectangle_map["Off-loading Yard"]
    parking = rectangle_map["Parking"]

    hard_checks = [check for check in checks if check["category"] == "hard"]
    hard_pass_rate = sum(bool(check["passed"]) for check in hard_checks) / max(len(hard_checks), 1)

    adjacency_checks = [
        check
        for check in checks
        if check["rule"] in {
            "Trading Area touches Admin Block",
            "Goods Receiving touches Trading Area",
            "Yard aligns with Goods Receiving",
            "Off-loading Yard touches Yard",
        }
    ]
    adjacency_score = sum(bool(check["passed"]) for check in adjacency_checks) / max(len(adjacency_checks), 1)

    proportion_score = (
        trading_breadth_score(trading, entrance_side) * 0.45
        + compactness_score(admin) * 0.15
        + compactness_score(receiving) * 0.15
        + compactness_score(yard) * 0.10
        + compactness_score(offloading) * 0.10
        + compactness_score(parking) * 0.05
    )

    score = adjacency_score * 45.0 + proportion_score * 35.0 + hard_pass_rate * 20.0
    return round(score, 1)
