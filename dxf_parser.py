from __future__ import annotations

import os
import tempfile
from collections import Counter
from typing import Dict, List, Sequence, Tuple

import ezdxf

ENTRANCE_LAYER_KEYWORDS = ["ENTRANCE", "ENTRY", "FRONT", "CUSTOMER"]
SERVICE_LAYER_KEYWORDS = ["SERVICE", "ROLLER", "SHUTTER", "LOADING", "OFFLOAD", "RECEIVING", "YARD"]
DOOR_LAYER_KEYWORDS = ["DOOR", "OPENING", "ENTRANCE", "ENTRY", "ROLLER", "SHUTTER", "SERVICE"]


def inspect_dxf_bytes(file_bytes: bytes) -> Dict:
    """Inspect an uploaded DXF file and return a simple report."""

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name

        document = ezdxf.readfile(temp_path)
        modelspace = document.modelspace()

        layer_names = sorted(layer.dxf.name for layer in document.layers)
        entity_counts = Counter()
        store_envelopes: List[Dict] = []
        door_candidates: List[Dict] = []

        for entity in modelspace:
            layer_name = entity.dxf.layer
            entity_counts[layer_name] += 1

            if layer_name.upper() == "STORE_ENVELOPE" and entity.dxftype() in {"LWPOLYLINE", "POLYLINE"}:
                points = polyline_points(entity)
                bounds = bounds_from_points(points)
                store_envelopes.append(
                    {
                        "handle": entity.dxf.handle,
                        "entity_type": entity.dxftype(),
                        "closed": entity_is_closed(entity),
                        "min_x": bounds["min_x"],
                        "min_y": bounds["min_y"],
                        "max_x": bounds["max_x"],
                        "max_y": bounds["max_y"],
                        "width": bounds["width"],
                        "depth": bounds["depth"],
                    }
                )

            door_candidate = build_door_candidate(entity)
            if door_candidate:
                door_candidates.append(door_candidate)

        selected_envelope = choose_store_envelope(store_envelopes)
        entrance_door = choose_door_candidate(door_candidates, "entrance", selected_envelope)
        service_door = choose_door_candidate(door_candidates, "service", selected_envelope)

        return {
            "layers": layer_names,
            "entity_counts": [
                {"layer": layer_name, "entity_count": entity_counts.get(layer_name, 0)}
                for layer_name in layer_names
            ],
            "store_envelopes": store_envelopes,
            "selected_store_envelope": selected_envelope,
            "entrance_door": entrance_door,
            "service_door": service_door,
        }
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


def entity_is_closed(entity) -> bool:
    closed_value = getattr(entity, "closed", None)
    if closed_value is not None:
        return bool(closed_value() if callable(closed_value) else closed_value)

    closed_value = getattr(entity, "is_closed", None)
    if closed_value is not None:
        return bool(closed_value() if callable(closed_value) else closed_value)

    return False


def polyline_points(entity) -> List[Tuple[float, float]]:
    if entity.dxftype() == "LWPOLYLINE":
        return [(point[0], point[1]) for point in entity.get_points()]

    return [(vertex.dxf.location.x, vertex.dxf.location.y) for vertex in entity.vertices]


def bounds_from_points(points: Sequence[Tuple[float, float]]) -> Dict[str, float]:
    if not points:
        return {"min_x": 0.0, "min_y": 0.0, "max_x": 0.0, "max_y": 0.0, "width": 0.0, "depth": 0.0}

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    min_x = min(xs)
    min_y = min(ys)
    max_x = max(xs)
    max_y = max(ys)

    return {
        "min_x": min_x,
        "min_y": min_y,
        "max_x": max_x,
        "max_y": max_y,
        "width": max_x - min_x,
        "depth": max_y - min_y,
    }


def choose_store_envelope(store_envelopes: List[Dict]) -> Dict | None:
    if not store_envelopes:
        return None

    closed_envelopes = [envelope for envelope in store_envelopes if envelope["closed"]]
    candidates = closed_envelopes or store_envelopes
    return max(candidates, key=lambda envelope: envelope["width"] * envelope["depth"])


def build_door_candidate(entity) -> Dict | None:
    layer_name = entity.dxf.layer
    upper_layer = layer_name.upper()

    if not any(keyword in upper_layer for keyword in DOOR_LAYER_KEYWORDS):
        return None

    center = entity_center(entity)
    if center is None:
        return None

    role = classify_door_role(upper_layer)
    return {
        "handle": entity.dxf.handle,
        "layer": layer_name,
        "entity_type": entity.dxftype(),
        "role": role,
        "x": center[0],
        "y": center[1],
    }


def classify_door_role(upper_layer: str) -> str:
    if any(keyword in upper_layer for keyword in SERVICE_LAYER_KEYWORDS):
        return "service"
    if any(keyword in upper_layer for keyword in ENTRANCE_LAYER_KEYWORDS):
        return "entrance"
    return "generic"


def choose_door_candidate(candidates: List[Dict], role: str, envelope: Dict | None) -> Dict | None:
    if envelope is None:
        return None

    preferred = [candidate for candidate in candidates if candidate["role"] == role]
    if role == "entrance" and not preferred:
        preferred = [candidate for candidate in candidates if candidate["role"] == "generic"]
    if not preferred:
        return None

    enriched = []
    for candidate in preferred:
        side, distance = nearest_side(candidate["x"], candidate["y"], envelope)
        enriched.append({**candidate, "side": side, "distance_to_side": distance})

    return min(enriched, key=lambda candidate: candidate["distance_to_side"])


def nearest_side(x: float, y: float, envelope: Dict) -> Tuple[str, float]:
    distances = {
        "west": abs(x - envelope["min_x"]),
        "east": abs(envelope["max_x"] - x),
        "south": abs(y - envelope["min_y"]),
        "north": abs(envelope["max_y"] - y),
    }
    side = min(distances, key=distances.get)
    return side, distances[side]


def entity_center(entity) -> Tuple[float, float] | None:
    entity_type = entity.dxftype()

    if entity_type == "LINE":
        start = entity.dxf.start
        end = entity.dxf.end
        return ((start.x + end.x) / 2.0, (start.y + end.y) / 2.0)

    if entity_type == "LWPOLYLINE":
        points = [(point[0], point[1]) for point in entity.get_points()]
        return center_from_points(points)

    if entity_type == "POLYLINE":
        points = [(vertex.dxf.location.x, vertex.dxf.location.y) for vertex in entity.vertices]
        return center_from_points(points)

    if entity_type in {"CIRCLE", "ARC"}:
        center = entity.dxf.center
        return (center.x, center.y)

    if entity_type == "INSERT":
        insert = entity.dxf.insert
        return (insert.x, insert.y)

    return None


def center_from_points(points: Sequence[Tuple[float, float]]) -> Tuple[float, float] | None:
    if not points:
        return None

    bounds = bounds_from_points(points)
    return ((bounds["min_x"] + bounds["max_x"]) / 2.0, (bounds["min_y"] + bounds["max_y"]) / 2.0)
