from __future__ import annotations

from .geometry import applied_camera_step_deg
from .models import CameraSpec, LensSpec, LayoutConfig
from .physical_fit import estimate_min_radius, estimate_min_radius_for_step


def solve_min_radius(
    camera: CameraSpec,
    lens: LensSpec,
    camera_count: int,
    clearance_mm: float = 5.0,
) -> dict[str, float]:
    """Return the minimum circular reference radius for equal closed-circle spacing."""

    min_radius_mm = estimate_min_radius(camera, lens, camera_count, clearance_mm)
    return {
        "min_radius_mm": min_radius_mm,
        "recommended_radius_mm": min_radius_mm * 1.1,
    }


def solve_min_radius_for_layout(
    config: LayoutConfig,
    camera: CameraSpec,
    lens: LensSpec,
    clearance_mm: float = 5.0,
) -> dict[str, float]:
    """Return the minimum radius using the layout's actual angular spacing."""

    if config.camera_count < 2:
        min_radius_mm = 0.0
    else:
        step_deg = applied_camera_step_deg(config, lens)
        min_radius_mm = estimate_min_radius_for_step(camera, lens, step_deg, clearance_mm)

    return {
        "min_radius_mm": min_radius_mm,
        "recommended_radius_mm": min_radius_mm * 1.1,
    }
