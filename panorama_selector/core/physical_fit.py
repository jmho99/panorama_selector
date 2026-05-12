from __future__ import annotations

import math
from dataclasses import replace
from typing import Any

from .geometry import applied_camera_step_deg, chord_distance, compute_layout
from .models import CameraSpec, LensSpec, LayoutConfig, Placement

Point = tuple[float, float]
Polygon = list[Point]
Footprint = dict[str, Any]

EPSILON = 1e-9
MAX_RADIUS_SEARCH_MM = 10_000_000.0


def required_clear_width(camera: CameraSpec, lens: LensSpec, clearance_mm: float) -> float:
    """Return a simple width summary for result display.

    The actual fit check below uses full top-view polygons:
    - camera body rectangle: body_width_mm x body_depth_mm
    - lens triangle: diameter_mm x length_mm
    """
    return max(camera.body_width_mm, lens.diameter_mm) + clearance_mm


def required_total_depth(camera: CameraSpec, lens: LensSpec, clearance_mm: float) -> float:
    """Return a simple front/back depth summary for result display."""
    return camera.body_depth_mm + lens.length_mm + clearance_mm


def estimate_min_radius(
    camera: CameraSpec,
    lens: LensSpec,
    camera_count: int,
    clearance_mm: float = 5.0,
) -> float:
    """Return minimum radius for equal closed-circle spacing.

    For the GUI layout, use estimate_min_radius_for_config() instead so the
    current target panorama angle or manually entered spacing is respected.
    """
    if camera_count < 2:
        return 0.0

    config = LayoutConfig(
        camera_count=camera_count,
        radius_mm=0.0,
        target_panorama_deg=360.0,
        use_camera_spacing_deg=False,
    )
    return estimate_min_radius_for_config(config, camera, lens, clearance_mm)


def estimate_min_radius_for_step(
    camera: CameraSpec,
    lens: LensSpec,
    camera_spacing_deg: float,
    clearance_mm: float = 5.0,
    camera_count: int = 2,
) -> float:
    """Return minimum radius for a given adjacent angular spacing."""
    if camera_count < 2:
        return 0.0
    if camera_spacing_deg <= 0.0:
        return math.inf

    config = LayoutConfig(
        camera_count=camera_count,
        radius_mm=0.0,
        target_panorama_deg=360.0,
        use_camera_spacing_deg=True,
        camera_spacing_deg=camera_spacing_deg,
    )
    return estimate_min_radius_for_config(config, camera, lens, clearance_mm)


def estimate_min_radius_for_config(
    config: LayoutConfig,
    camera: CameraSpec,
    lens: LensSpec,
    clearance_mm: float = 5.0,
) -> float:
    """Find minimum radius using the actual layout and polygon collision.

    Top-view footprint convention:
    - placement point: fixed at the lens half-length position
    - lens: triangle, apex touches the center of the camera front edge
    - camera: rectangle, sized by width/depth
    """
    if config.camera_count < 2:
        return 0.0

    step_deg = applied_camera_step_deg(config, lens)
    if step_deg <= 0.0:
        return math.inf

    envelope_mm = (
        camera.body_width_mm
        + camera.body_depth_mm
        + lens.diameter_mm
        + lens.length_mm
        + clearance_mm
    )
    high = max(envelope_mm * 2.0, config.radius_mm, 1.0)
    low = 0.0

    while high < MAX_RADIUS_SEARCH_MM:
        test_config = replace(config, radius_mm=high)
        if _fit_state(test_config, camera, lens, clearance_mm)["fits"]:
            break
        high *= 2.0
    else:
        return math.inf

    for _ in range(70):
        mid = (low + high) / 2.0
        test_config = replace(config, radius_mm=mid)

        if _fit_state(test_config, camera, lens, clearance_mm)["fits"]:
            high = mid
        else:
            low = mid

    return high


def check_physical_fit(
    config: LayoutConfig,
    camera: CameraSpec,
    lens: LensSpec,
    clearance_mm: float = 5.0,
) -> dict[str, Any]:
    """Check physical fit using real top-view polygons."""
    state = _fit_state(config, camera, lens, clearance_mm)

    if config.camera_count < 2:
        min_radius_mm = 0.0
    else:
        min_radius_mm = estimate_min_radius_for_config(config, camera, lens, clearance_mm)

    step_deg = applied_camera_step_deg(config, lens)
    spacing_mm = chord_distance(config.radius_mm, config.camera_count, step_deg)

    return {
        "fits": state["fits"],
        "camera_spacing_mm": spacing_mm,
        "required_clear_width_mm": required_clear_width(camera, lens, clearance_mm),
        "required_total_depth_mm": required_total_depth(camera, lens, clearance_mm),
        "min_footprint_distance_mm": state["min_distance_mm"],
        "margin_mm": state["margin_mm"],
        "min_radius_mm": min_radius_mm,
        "placement_reference": "lens_half_length",
        "camera_body_width_mm": camera.body_width_mm,
        "camera_body_depth_mm": camera.body_depth_mm,
        "lens_diameter_mm": lens.diameter_mm,
        "lens_length_mm": lens.length_mm,
        "footprints": state["footprints"],
    }


def compute_footprint_polygons(
    config: LayoutConfig,
    camera: CameraSpec,
    lens: LensSpec,
    padding_mm: float = 0.0,
) -> list[Footprint]:
    placements = compute_layout(config, lens)
    return compute_footprint_polygons_for_placements(placements, camera, lens, padding_mm)


def compute_footprint_polygons_for_placements(
    placements: list[Placement],
    camera: CameraSpec,
    lens: LensSpec,
    padding_mm: float = 0.0,
) -> list[Footprint]:
    """Build world-space camera/lens footprints for each placement.

    Local coordinate convention:
    - +X: forward optical direction
    - +Y: left/right width direction
    - origin: lens half-length reference point

    Lens triangle:
    - apex at x = -lens.length / 2
    - base edge at x = +lens.length / 2
    - base edge width = lens.diameter

    Camera rectangle:
    - front edge center touches the lens apex
    - body extends backward by camera.body_depth
    - body width = camera.body_width
    """
    footprints: list[Footprint] = []

    for placement in placements:
        camera_polygon = _transform_polygon(
            _local_camera_body_polygon(camera, lens, padding_mm),
            placement,
        )
        lens_polygon = _transform_polygon(
            _local_lens_polygon(lens, padding_mm),
            placement,
        )

        footprints.append(
            {
                "camera_index": placement.index,
                "kind": "camera_body",
                "points": camera_polygon,
            }
        )
        footprints.append(
            {
                "camera_index": placement.index,
                "kind": "lens",
                "points": lens_polygon,
            }
        )

    return footprints


def _fit_state(
    config: LayoutConfig,
    camera: CameraSpec,
    lens: LensSpec,
    clearance_mm: float,
) -> dict[str, Any]:
    footprints = compute_footprint_polygons(config, camera, lens, padding_mm=0.0)

    if config.camera_count < 2:
        return {
            "fits": True,
            "min_distance_mm": 0.0,
            "margin_mm": 0.0,
            "footprints": footprints,
        }

    min_distance_mm, has_overlap = _minimum_distance_between_different_cameras(footprints)
    fits = (not has_overlap) and min_distance_mm + EPSILON >= clearance_mm
    margin_mm = min_distance_mm - clearance_mm

    return {
        "fits": fits,
        "min_distance_mm": min_distance_mm,
        "margin_mm": margin_mm,
        "footprints": footprints,
    }


def _local_camera_body_polygon(
    camera: CameraSpec,
    lens: LensSpec,
    padding_mm: float = 0.0,
) -> Polygon:
    half_width = camera.body_width_mm / 2.0 + padding_mm
    lens_half_length = lens.length_mm / 2.0

    front_x = -lens_half_length
    rear_x = front_x - camera.body_depth_mm - padding_mm

    return [
        (front_x, -half_width),
        (front_x, half_width),
        (rear_x, half_width),
        (rear_x, -half_width),
    ]


def _local_lens_polygon(
    lens: LensSpec,
    padding_mm: float = 0.0,
) -> Polygon:
    half_length = lens.length_mm / 2.0 + padding_mm
    half_diameter = lens.diameter_mm / 2.0 + padding_mm

    apex = (-half_length, 0.0)
    base_left = (half_length, half_diameter)
    base_right = (half_length, -half_diameter)

    return [apex, base_left, base_right]


def _transform_polygon(local_polygon: Polygon, placement: Placement) -> Polygon:
    yaw_rad = math.radians(placement.yaw_deg)
    cos_yaw = math.cos(yaw_rad)
    sin_yaw = math.sin(yaw_rad)

    transformed: Polygon = []

    for local_x, local_y in local_polygon:
        world_x = placement.x_mm + local_x * cos_yaw - local_y * sin_yaw
        world_y = placement.y_mm + local_x * sin_yaw + local_y * cos_yaw
        transformed.append((world_x, world_y))

    return transformed


def _minimum_distance_between_different_cameras(
    footprints: list[Footprint],
) -> tuple[float, bool]:
    min_distance = math.inf
    has_overlap = False

    for i, footprint_a in enumerate(footprints):
        index_a = int(footprint_a["camera_index"])
        polygon_a = footprint_a["points"]

        for footprint_b in footprints[i + 1 :]:
            index_b = int(footprint_b["camera_index"])

            if index_a == index_b:
                continue

            polygon_b = footprint_b["points"]

            if _polygons_intersect(polygon_a, polygon_b):
                has_overlap = True
                min_distance = 0.0
                continue

            distance = _polygon_distance(polygon_a, polygon_b)
            min_distance = min(min_distance, distance)

    if math.isinf(min_distance):
        min_distance = 0.0

    return min_distance, has_overlap


def _polygons_intersect(polygon_a: Polygon, polygon_b: Polygon) -> bool:
    """Convex polygon intersection test using SAT.

    Touching edges are treated as not intersecting, but the separate clearance
    check still requires min_distance_mm >= clearance_mm.
    """
    for polygon in (polygon_a, polygon_b):
        for axis in _polygon_axes(polygon):
            min_a, max_a = _project_polygon(polygon_a, axis)
            min_b, max_b = _project_polygon(polygon_b, axis)

            if max_a <= min_b + EPSILON or max_b <= min_a + EPSILON:
                return False

    return True


def _polygon_axes(polygon: Polygon) -> list[Point]:
    axes: list[Point] = []

    for i, point_a in enumerate(polygon):
        point_b = polygon[(i + 1) % len(polygon)]
        edge_x = point_b[0] - point_a[0]
        edge_y = point_b[1] - point_a[1]

        axis_x = -edge_y
        axis_y = edge_x
        length = math.hypot(axis_x, axis_y)

        if length <= EPSILON:
            continue

        axes.append((axis_x / length, axis_y / length))

    return axes


def _project_polygon(polygon: Polygon, axis: Point) -> tuple[float, float]:
    values = [_dot(point, axis) for point in polygon]
    return min(values), max(values)


def _polygon_distance(polygon_a: Polygon, polygon_b: Polygon) -> float:
    if _polygons_intersect(polygon_a, polygon_b):
        return 0.0

    min_distance = math.inf

    for point in polygon_a:
        for start, end in _polygon_edges(polygon_b):
            min_distance = min(min_distance, _point_to_segment_distance(point, start, end))

    for point in polygon_b:
        for start, end in _polygon_edges(polygon_a):
            min_distance = min(min_distance, _point_to_segment_distance(point, start, end))

    if math.isinf(min_distance):
        return 0.0

    return min_distance


def _polygon_edges(polygon: Polygon) -> list[tuple[Point, Point]]:
    return [(polygon[i], polygon[(i + 1) % len(polygon)]) for i in range(len(polygon))]


def _point_to_segment_distance(point: Point, start: Point, end: Point) -> float:
    segment_x = end[0] - start[0]
    segment_y = end[1] - start[1]
    segment_length_sq = segment_x * segment_x + segment_y * segment_y

    if segment_length_sq <= EPSILON:
        return math.hypot(point[0] - start[0], point[1] - start[1])

    t = (
        ((point[0] - start[0]) * segment_x + (point[1] - start[1]) * segment_y)
        / segment_length_sq
    )
    t = max(0.0, min(1.0, t))

    closest_x = start[0] + t * segment_x
    closest_y = start[1] + t * segment_y

    return math.hypot(point[0] - closest_x, point[1] - closest_y)


def _dot(point_a: Point, point_b: Point) -> float:
    return point_a[0] * point_b[0] + point_a[1] * point_b[1]
