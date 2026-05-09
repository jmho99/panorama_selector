from __future__ import annotations

import math

from .geometry import (
    adjacent_gap_count,
    applied_camera_step_deg,
    chord_distance,
    compute_layout,
    final_panorama_angle_deg,
    is_closed_panorama,
)
from .models import BlindZoneResult, LensSpec, LayoutConfig, Placement


def _cross(ax: float, ay: float, bx: float, by: float) -> float:
    return ax * by - ay * bx


def _ray_intersection(
    origin_a: tuple[float, float],
    angle_a_deg: float,
    origin_b: tuple[float, float],
    angle_b_deg: float,
    eps: float = 1e-9,
) -> tuple[float, float] | None:
    """Return the forward intersection point of two rays, or None."""

    angle_a_rad = math.radians(angle_a_deg)
    angle_b_rad = math.radians(angle_b_deg)

    dir_a_x = math.cos(angle_a_rad)
    dir_a_y = math.sin(angle_a_rad)
    dir_b_x = math.cos(angle_b_rad)
    dir_b_y = math.sin(angle_b_rad)

    denominator = _cross(dir_a_x, dir_a_y, dir_b_x, dir_b_y)
    if abs(denominator) < eps:
        return None

    rel_x = origin_b[0] - origin_a[0]
    rel_y = origin_b[1] - origin_a[1]

    t = _cross(rel_x, rel_y, dir_b_x, dir_b_y) / denominator
    u = _cross(rel_x, rel_y, dir_a_x, dir_a_y) / denominator

    if t < -eps or u < -eps:
        return None

    return origin_a[0] + t * dir_a_x, origin_a[1] + t * dir_a_y


def compute_near_blind_zone_between_pair(
    camera_a: Placement,
    camera_b: Placement,
    lens: LensSpec,
) -> BlindZoneResult | None:
    """
    Compute the near-field blind zone between two adjacent cameras.

    The overlap start point is the intersection of:
    - camera_a upper/right FOV boundary: yaw + HFOV / 2
    - camera_b lower/left FOV boundary: yaw - HFOV / 2

    The blind distance is the perpendicular distance from the camera-center
    baseline to that overlap start point.
    """

    half_hfov_deg = lens.hfov_deg / 2.0
    origin_a = (camera_a.x_mm, camera_a.y_mm)
    origin_b = (camera_b.x_mm, camera_b.y_mm)

    overlap_start = _ray_intersection(
        origin_a,
        camera_a.yaw_deg + half_hfov_deg,
        origin_b,
        camera_b.yaw_deg - half_hfov_deg,
    )
    if overlap_start is None:
        return None

    base_x = origin_b[0] - origin_a[0]
    base_y = origin_b[1] - origin_a[1]
    base_len_sq = base_x * base_x + base_y * base_y
    if base_len_sq <= 0.0:
        return None

    point_x = overlap_start[0] - origin_a[0]
    point_y = overlap_start[1] - origin_a[1]
    camera_spacing_mm = math.sqrt(base_len_sq)

    projection_ratio = (point_x * base_x + point_y * base_y) / base_len_sq
    perpendicular_foot_x = origin_a[0] + projection_ratio * base_x
    perpendicular_foot_y = origin_a[1] + projection_ratio * base_y

    blind_distance_mm = abs(_cross(base_x, base_y, point_x, point_y)) / camera_spacing_mm
    blind_area_mm2 = 0.5 * camera_spacing_mm * blind_distance_mm

    return BlindZoneResult(
        camera_a_index=camera_a.index,
        camera_b_index=camera_b.index,
        overlap_start_x_mm=overlap_start[0],
        overlap_start_y_mm=overlap_start[1],
        perpendicular_foot_x_mm=perpendicular_foot_x,
        perpendicular_foot_y_mm=perpendicular_foot_y,
        camera_spacing_mm=camera_spacing_mm,
        blind_distance_mm=blind_distance_mm,
        blind_area_mm2=blind_area_mm2,
    )


def compute_near_blind_zones(config: LayoutConfig, lens: LensSpec) -> list[BlindZoneResult]:
    """Compute near-field blind zones for all adjacent camera pairs."""

    if config.camera_count <= 1:
        return []

    step_deg = applied_camera_step_deg(config, lens)
    if lens.hfov_deg <= step_deg:
        return []

    placements = compute_layout(config, lens)
    adjacent_pairs = list(zip(placements[:-1], placements[1:]))

    if is_closed_panorama(config):
        adjacent_pairs.append((placements[-1], placements[0]))

    results: list[BlindZoneResult] = []
    for camera_a, camera_b in adjacent_pairs:
        blind_zone = compute_near_blind_zone_between_pair(camera_a, camera_b, lens)
        if blind_zone is not None:
            results.append(blind_zone)

    return results


def compute_metrics(config: LayoutConfig, lens: LensSpec) -> dict[str, float]:
    if config.camera_count <= 0:
        raise ValueError("camera_count must be positive")
    if lens.hfov_deg <= 0:
        raise ValueError("hfov_deg must be positive")
    if config.evaluation_distance_mm < 0:
        raise ValueError("evaluation_distance_mm must be non-negative")

    step_deg = applied_camera_step_deg(config, lens)
    gap_count = adjacent_gap_count(config)

    overlap_deg = max(0.0, lens.hfov_deg - step_deg)
    blind_deg = max(0.0, step_deg - lens.hfov_deg)
    total_blind_deg = blind_deg * gap_count

    final_panorama_deg = final_panorama_angle_deg(config, lens)

    blind_rad = math.radians(blind_deg)
    blind_arc_length_mm = config.evaluation_distance_mm * blind_rad
    blind_sector_area_mm2 = 0.5 * (config.evaluation_distance_mm**2) * blind_rad
    total_blind_sector_area_mm2 = blind_sector_area_mm2 * gap_count

    near_blind_zones = compute_near_blind_zones(config, lens)
    near_blind_zone_count = len(near_blind_zones)
    total_near_blind_area_mm2 = sum(zone.blind_area_mm2 for zone in near_blind_zones)
    max_near_blind_distance_mm = max(
        (zone.blind_distance_mm for zone in near_blind_zones),
        default=0.0,
    )
    avg_near_blind_distance_mm = (
        sum(zone.blind_distance_mm for zone in near_blind_zones) / near_blind_zone_count
        if near_blind_zone_count > 0
        else 0.0
    )

    return {
        "camera_count": float(config.camera_count),
        "target_panorama_deg": config.target_panorama_deg,
        "angular_step_deg": step_deg,
        "hfov_deg": lens.hfov_deg,
        "final_panorama_deg": final_panorama_deg,
        "overlap_deg_each": overlap_deg,
        "blind_deg_each": blind_deg,
        "blind_gap_count": float(gap_count),
        "total_blind_deg": total_blind_deg,
        "blind_arc_length_each_mm": blind_arc_length_mm,
        "blind_sector_area_each_mm2": blind_sector_area_mm2,
        "total_blind_sector_area_mm2": total_blind_sector_area_mm2,
        "camera_spacing_mm": chord_distance(config.radius_mm, config.camera_count, step_deg),
        "near_blind_zone_count": float(near_blind_zone_count),
        "near_blind_distance_avg_mm": avg_near_blind_distance_mm,
        "near_blind_distance_max_mm": max_near_blind_distance_mm,
        "near_blind_area_total_mm2": total_near_blind_area_mm2,
    }
