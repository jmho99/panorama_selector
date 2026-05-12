from __future__ import annotations

import math

from .models import LayoutConfig, LensSpec, Placement


def normalize_angle_deg(angle: float) -> float:
    return angle % 360.0


def signed_angle_deg(angle: float) -> float:
    """Convert 0~360 angle to -180~180 angle for easier display/debug."""
    normalized = normalize_angle_deg(angle)
    if normalized > 180.0:
        return normalized - 360.0
    return normalized


def is_closed_panorama(config: LayoutConfig) -> bool:
    """Treat 360-degree target layouts as closed circular layouts."""
    return config.target_panorama_deg >= 360.0


def adjacent_gap_count(config: LayoutConfig) -> int:
    if config.camera_count <= 1:
        return 0
    if is_closed_panorama(config):
        return config.camera_count
    return config.camera_count - 1


def applied_camera_step_deg(config: LayoutConfig, lens: LensSpec) -> float:
    """Return the angular spacing actually used between adjacent camera reference points."""
    if config.camera_count <= 0:
        raise ValueError("camera_count must be positive")

    if config.camera_count == 1:
        return 0.0

    if config.use_camera_spacing_deg and config.camera_spacing_deg is not None:
        return config.camera_spacing_deg

    if is_closed_panorama(config):
        return 360.0 / config.camera_count

    center_span_deg = config.target_panorama_deg - lens.hfov_deg

    if center_span_deg < 0.0:
        center_span_deg = 0.0

    return center_span_deg / (config.camera_count - 1)


def final_panorama_angle_deg(config: LayoutConfig, lens: LensSpec) -> float:
    """Return panorama span based on the two outer FOV edges."""
    if config.camera_count <= 0:
        raise ValueError("camera_count must be positive")

    if config.camera_count == 1:
        return lens.hfov_deg

    if is_closed_panorama(config):
        return 360.0

    step_deg = applied_camera_step_deg(config, lens)
    return lens.hfov_deg + step_deg * (config.camera_count - 1)


def chord_distance(
    radius_mm: float,
    camera_count: int,
    camera_spacing_deg: float | None = None,
) -> float:
    if camera_count < 2:
        return 0.0

    if camera_spacing_deg is None:
        angle_rad = 2.0 * math.pi / camera_count
    else:
        angle_rad = math.radians(camera_spacing_deg)

    return 2.0 * radius_mm * math.sin(angle_rad / 2.0)


def compute_layout(config: LayoutConfig, lens: LensSpec) -> list[Placement]:
    """Calculate placement reference points.

    The placement point is fixed at the lens half-length position.
    The radius is therefore measured from the origin to that lens half-length point.
    """
    if config.camera_count <= 0:
        raise ValueError("camera_count must be positive")
    if config.radius_mm < 0:
        raise ValueError("radius_mm must be non-negative")

    step_deg = applied_camera_step_deg(config, lens)

    if is_closed_panorama(config):
        start_angle_deg = config.yaw_offset_deg
    else:
        center_span_deg = step_deg * (config.camera_count - 1)
        start_angle_deg = config.yaw_offset_deg - center_span_deg / 2.0

    placements: list[Placement] = []

    for i in range(config.camera_count):
        angle_deg = start_angle_deg + i * step_deg
        angle_rad = math.radians(angle_deg)
        x_mm = config.radius_mm * math.cos(angle_rad)
        y_mm = config.radius_mm * math.sin(angle_rad)
        yaw_deg = normalize_angle_deg(angle_deg)

        placements.append(
            Placement(
                index=i + 1,
                angle_deg=normalize_angle_deg(angle_deg),
                x_mm=x_mm,
                y_mm=y_mm,
                yaw_deg=yaw_deg,
            )
        )

    return placements


def fov_edge_angles(yaw_deg: float, hfov_deg: float) -> tuple[float, float]:
    half = hfov_deg / 2.0
    return normalize_angle_deg(yaw_deg - half), normalize_angle_deg(yaw_deg + half)
