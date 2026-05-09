from __future__ import annotations

import math

from .geometry import applied_camera_step_deg, chord_distance
from .models import CameraSpec, LensSpec, LayoutConfig


def required_clear_width(camera: CameraSpec, lens: LensSpec, clearance_mm: float) -> float:
    return max(camera.body_width_mm, lens.diameter_mm) + clearance_mm


def estimate_min_radius(camera: CameraSpec, lens: LensSpec, camera_count: int, clearance_mm: float = 5.0) -> float:
    if camera_count < 2:
        return 0.0

    required_width_mm = required_clear_width(camera, lens, clearance_mm)
    return required_width_mm / (2.0 * math.sin(math.pi / camera_count))


def estimate_min_radius_for_step(
    camera: CameraSpec,
    lens: LensSpec,
    camera_spacing_deg: float,
    clearance_mm: float = 5.0,
) -> float:
    required_width_mm = required_clear_width(camera, lens, clearance_mm)

    if camera_spacing_deg <= 0.0:
        return 0.0

    sin_half_step = math.sin(math.radians(camera_spacing_deg) / 2.0)
    if sin_half_step <= 0.0:
        return 0.0

    return required_width_mm / (2.0 * sin_half_step)


def check_physical_fit(
    config: LayoutConfig,
    camera: CameraSpec,
    lens: LensSpec,
    clearance_mm: float = 5.0,
) -> dict[str, float | bool]:
    step_deg = applied_camera_step_deg(config, lens)

    spacing_mm = chord_distance(config.radius_mm, config.camera_count, step_deg)
    required_width_mm = required_clear_width(camera, lens, clearance_mm)

    if config.camera_count < 2:
        min_radius_mm = 0.0
    else:
        min_radius_mm = estimate_min_radius_for_step(camera, lens, step_deg, clearance_mm)

    margin_mm = spacing_mm - required_width_mm

    return {
        "fits": margin_mm >= 0.0,
        "camera_spacing_mm": spacing_mm,
        "required_clear_width_mm": required_width_mm,
        "margin_mm": margin_mm,
        "min_radius_mm": min_radius_mm,
    }
