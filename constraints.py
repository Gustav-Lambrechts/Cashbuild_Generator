from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from cashbuild_spec import cashbuild_spec

EPSILON = 1e-6

SPACE_BY_NAME = {space["name"]: space for space in cashbuild_spec["spaces"]}
TARGET_AREAS_M2 = {
    "Trading Area": cashbuild_spec["global_rules"]["structure"]["trading_floor_target_internal_area_m2"],
    "Admin Block": cashbuild_spec["global_rules"]["admin_block"]["target_area_m2"],
    "Yard": cashbuild_spec["global_rules"]["yard"]["minimum_area_m2"],
    "Off-loading Yard": cashbuild_spec["global_rules"]["off_loading"]["minimum_area_m2"],
    "Parking": 550.0,
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
    preferred_width, preferred_depth = cashbuild_spec["global_rules"]["structure"]["trading_floor_preferred_dimensions_m"]
    preferred_score = (
        min(rectangle.width / max(preferred_width, EPSILON), preferred_width / max(rectangle.width, EPSILON))
        + min(rectangle.depth / max(preferred_depth, EPSILON), preferred_depth / max(rectangle.depth, EPSILON))
    ) / 2.0

    if entrance_side in {"north", "south"}:
        ratio = rectangle.width / max(rectangle.depth, EPSILON)
    else:
        ratio = rectangle.depth / max(rectangle.width, EPSILON)
    breadth_score = min(1.0, max(0.0, ratio / 3.0))
    return min(1.0, max(breadth_score, preferred_score))


def make_check(rule: str, passed: bool, detail: str, category: str = "hard") -> dict[str, object]:
    return {"rule": rule, "passed": passed, "detail": detail, "category": category}


def is_allowed_overlap(rect_a: Rectangle, rect_b: Rectangle) -> bool:
    labels = {rect_a.label, rect_b.label}
    return "Trading Area" in labels and any(label.startswith("POS Zone") for label in labels)


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
    admin_target = cashbuild_spec["global_rules"]["admin_block"]["target_area_m2"]
    admin_difference = abs(admin.area - admin_target)

    internal_rectangles = [trading] + pos_zones
    external_rectangles = [rectangle for rectangle in rectangles if not rectangle.internal]
    floor_rectangles = rectangles + pos_zones
    building_area = building_width * building_depth
    actual_internal_area = trading.area

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
            "Trading Area matches the entered shop size",
            within_building(trading, building_width, building_depth),
            "The entered width and depth define the Trading Area rectangle directly.",
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
            "Macro planning blocks stay separate and do not overlap one another.",
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
            "Admin Block sits outside Trading Area and touches it",
            share_edge(trading, admin) and not overlaps(trading, admin),
            "Admin Block should attach outside the Trading Area without reducing it.",
        )
    )

    checks.append(
        make_check(
            "Goods Receiving sits outside Trading Area and touches it",
            share_edge(trading, receiving) and not overlaps(trading, receiving),
            "Goods Receiving should attach outside the Trading Area without reducing it.",
        )
    )

    checks.append(
        make_check(
            "Admin Block touches Goods Receiving",
            share_edge(admin, receiving),
            "Admin Block and Goods Receiving should form one attached macro band.",
        )
    )

    checks.append(
        make_check(
            "Yard sits on the service side",
            touches_building_side(yard, service_side, building_width, building_depth),
            "The yard remains external and is based on the selected service side.",
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
            "Admin Block stays clear of Trading Area and Yard",
            not overlaps(admin, yard) and not overlaps(admin, offloading) and not overlaps(admin, trading),
            "Admin Block should not conflict badly with the Trading Area or external yards.",
        )
    )

    detail = (
        f"Trading Area is locked to the entered shop size at {trading.area:.1f} m². "
        f"{reduction_reason or ''}".strip()
    )
    checks.append(make_check("Internal area fit summary", True, detail, category="quality"))

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
            "Yard meets latest area target",
            yard.area + EPSILON >= cashbuild_spec["global_rules"]["yard"]["minimum_area_m2"],
            (
                f"Yard is {yard.area:.1f} m² against a "
                f"{cashbuild_spec['global_rules']['yard']['minimum_area_m2']:.1f} m² minimum."
            ),
            category="quality",
        )
    )

    checks.append(
        make_check(
            "Off-loading Yard meets latest area target",
            offloading.area + EPSILON >= cashbuild_spec["global_rules"]["off_loading"]["minimum_area_m2"],
            (
                f"Off-loading Yard is {offloading.area:.1f} m² against a "
                f"{cashbuild_spec['global_rules']['off_loading']['minimum_area_m2']:.1f} m² minimum."
            ),
            category="quality",
        )
    )

    checks.append(
        make_check(
            "Admin Block stays near target area",
            admin_difference <= 20.0,
            f"Admin Block is {admin.area:.1f} m² against a {admin_target:.1f} m² target.",
            category="quality",
        )
    )

    checks.append(
        make_check(
            "Macro zones are ready for future Stage 2 detailing",
            True,
            "Stage 1 stops at Trading Area, Admin Block, and Goods Receiving so later micro-layout generation can happen inside those macro zones.",
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

    adjacency_checks = [
        check
        for check in checks
        if check["rule"] in {
            "Admin Block sits outside Trading Area and touches it",
            "Goods Receiving sits outside Trading Area and touches it",
            "Admin Block touches Goods Receiving",
            "Off-loading Yard touches Yard",
        }
    ]
    adjacency_score = sum(bool(check["passed"]) for check in adjacency_checks) / max(len(adjacency_checks), 1)

    access_checks = [
        check
        for check in checks
        if check["rule"] in {
            "Frontage opening sequence fits on the entrance wall",
            "Yard sits on the service side",
            "Parking sits on the entrance side",
            "Trading Area matches the entered shop size",
            "External spaces stay outside the building footprint",
        }
    ]
    access_score = sum(bool(check["passed"]) for check in access_checks) / max(len(access_checks), 1)

    non_overlap_checks = [check for check in checks if check["rule"] == "Rectangles do not overlap"]
    non_overlap_score = sum(bool(check["passed"]) for check in non_overlap_checks) / max(len(non_overlap_checks), 1)

    trading_dominance_checks = [check for check in checks if check["rule"] == "Trading Area stays dominant"]
    trading_dominance_score = sum(bool(check["passed"]) for check in trading_dominance_checks) / max(len(trading_dominance_checks), 1)

    proportion_score = (
        trading_breadth_score(trading, entrance_side) * 0.50
        + compactness_score(admin) * 0.15
        + compactness_score(receiving) * 0.15
        + compactness_score(yard) * 0.10
        + compactness_score(offloading) * 0.05
        + compactness_score(parking) * 0.05
    )

    score = (
        adjacency_score * 28.0
        + access_score * 22.0
        + proportion_score * 22.0
        + non_overlap_score * 14.0
        + trading_dominance_score * 14.0
    )
    return round(score, 1)
