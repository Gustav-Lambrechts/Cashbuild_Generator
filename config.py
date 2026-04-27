from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - safe runtime fallback
    yaml = None


DEFAULT_TEMPLATE_CONFIG: dict[str, Any] = {
    "project": "Cashbuild Generator",
    "zone_standards": {
        "trading": {
            "ideal_area_m2": 1200,
            "minimum_area_m2": 1080,
            "preferred_dimensions_mm": {"width": 30000, "depth": 36000},
            "compact_dimensions_mm": {"width": 23200, "depth": 35650},
        },
        "admin_block": {
            "target_area_m2": 130,
            "preferred_depth_mm": {"minimum": 6050, "maximum": 6385},
        },
        "goods_receiving": {
            "preferred_band_depth_mm": 6230,
            "target_area_m2": 130,
        },
        "yard": {"minimum_area_m2": 900, "preferred_shape": "l_shape"},
        "offloading": {"minimum_area_m2": 450, "preferred_relationship": "attached_to_yard"},
        "parking": {"strategy": "flexible"},
    },
    "generator_priorities": [
        "fit_trading_first",
        "place_admin_block_from_selected_wall",
        "attach_goods_receiving_to_admin_and_trading",
        "place_yard_on_service_side",
        "attach_offloading_to_yard",
        "keep_remaining_circulation_clear",
    ],
}

TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "cashbuild.yaml"


def parse_scalar(value: str) -> Any:
    text = value.strip()
    if not text:
        return ""
    if text.lower() in {"true", "false"}:
        return text.lower() == "true"
    if text.lower() in {"null", "none"}:
        return None
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text.strip("'\"")


def parse_simple_yaml(text: str) -> dict[str, Any]:
    """
    Fallback parser for the small nested YAML structures used in this project.
    It supports dictionaries, simple lists, and scalar values.
    """
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()

        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()

        parent = stack[-1][1]

        if line.startswith("- "):
            value = parse_scalar(line[2:])
            if isinstance(parent, list):
                parent.append(value)
            continue

        if ":" not in line:
            continue

        key, raw_value = line.split(":", 1)
        key = key.strip()
        value_text = raw_value.strip()

        next_container: Any
        if value_text:
            next_container = parse_scalar(value_text)
        else:
            next_container = {}

        if isinstance(parent, dict):
            parent[key] = next_container
        elif isinstance(parent, list):
            parent.append({key: next_container})

        if not value_text:
            lookahead_container: Any = {}
            stack.append((indent, parent[key] if isinstance(parent, dict) else parent[-1][key]))

    # Second pass: convert empty dict placeholders that really own list items.
    lines = text.splitlines()
    for index, raw_line in enumerate(lines):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if ":" not in raw_line or raw_line.strip().startswith("- "):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        key, raw_value = raw_line.strip().split(":", 1)
        if raw_value.strip():
            continue

        next_meaningful = None
        for later_line in lines[index + 1 :]:
            if later_line.strip() and not later_line.lstrip().startswith("#"):
                next_meaningful = later_line
                break

        if next_meaningful is None:
            continue

        next_indent = len(next_meaningful) - len(next_meaningful.lstrip(" "))
        if next_indent <= indent or not next_meaningful.strip().startswith("- "):
            continue

        target_stack: list[tuple[int, Any]] = [(-1, root)]
        for revisit_line in lines[: index + 1]:
            if not revisit_line.strip() or revisit_line.lstrip().startswith("#"):
                continue
            revisit_indent = len(revisit_line) - len(revisit_line.lstrip(" "))
            revisit_text = revisit_line.strip()
            while len(target_stack) > 1 and revisit_indent <= target_stack[-1][0]:
                target_stack.pop()
            if revisit_text.startswith("- ") or ":" not in revisit_text:
                continue
            revisit_key, revisit_value = revisit_text.split(":", 1)
            revisit_key = revisit_key.strip()
            revisit_value = revisit_value.strip()
            parent_container = target_stack[-1][1]
            if revisit_value:
                continue
            if isinstance(parent_container, dict):
                if revisit_key == key and revisit_indent == indent:
                    parent_container[revisit_key] = []
                    break
                target_stack.append((revisit_indent, parent_container[revisit_key]))

    stack = [(-1, root)]
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if line.startswith("- "):
            if isinstance(parent, list):
                parent.append(parse_scalar(line[2:]))
            continue
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value_text = raw_value.strip()
        if not value_text:
            if isinstance(parent, dict):
                stack.append((indent, parent[key]))
            continue
    return root


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


@lru_cache(maxsize=1)
def load_template_config() -> dict[str, Any]:
    if not TEMPLATE_PATH.exists():
        return deepcopy(DEFAULT_TEMPLATE_CONFIG)

    try:
        file_text = TEMPLATE_PATH.read_text()
        if yaml is not None:
            loaded = yaml.safe_load(file_text) or {}
        else:
            loaded = parse_simple_yaml(file_text) or {}
    except Exception:
        return deepcopy(DEFAULT_TEMPLATE_CONFIG)

    if not isinstance(loaded, dict):
        return deepcopy(DEFAULT_TEMPLATE_CONFIG)

    return deep_merge(DEFAULT_TEMPLATE_CONFIG, loaded)


def template_zone(zone_name: str) -> dict[str, Any]:
    config = load_template_config()
    zone_config = config.get("zone_standards", {}).get(zone_name, {})
    return zone_config if isinstance(zone_config, dict) else {}


def mm_value_to_m(value_mm: float | int | None, default_m: float) -> float:
    if value_mm is None:
        return default_m
    return float(value_mm) / 1000.0


def template_standards() -> dict[str, Any]:
    trading = template_zone("trading")
    admin = template_zone("admin_block")
    receiving = template_zone("goods_receiving")
    yard = template_zone("yard")
    offloading = template_zone("offloading")

    preferred_dimensions = trading.get("preferred_dimensions_mm", {})
    compact_dimensions = trading.get("compact_dimensions_mm", {})
    admin_depth = admin.get("preferred_depth_mm", {})

    return {
        "trading_ideal_area_m2": float(trading.get("ideal_area_m2", 1200)),
        "trading_minimum_area_m2": float(trading.get("minimum_area_m2", 1080)),
        "trading_preferred_dimensions_m": [
            mm_value_to_m(preferred_dimensions.get("width"), 30.0),
            mm_value_to_m(preferred_dimensions.get("depth"), 36.0),
        ],
        "trading_compact_dimensions_m": [
            mm_value_to_m(compact_dimensions.get("width"), 23.2),
            mm_value_to_m(compact_dimensions.get("depth"), 35.65),
        ],
        "admin_target_area_m2": float(admin.get("target_area_m2", 130)),
        "admin_preferred_depth_range_m": [
            mm_value_to_m(admin_depth.get("minimum"), 6.05),
            mm_value_to_m(admin_depth.get("maximum"), 6.385),
        ],
        "service_band_depth_m": mm_value_to_m(receiving.get("preferred_band_depth_mm"), 6.23),
        "goods_receiving_target_area_m2": float(receiving.get("target_area_m2", 130)),
        "yard_minimum_area_m2": float(yard.get("minimum_area_m2", 900)),
        "offloading_minimum_area_m2": float(offloading.get("minimum_area_m2", 450)),
        "generator_priorities": load_template_config().get("generator_priorities", []),
    }
