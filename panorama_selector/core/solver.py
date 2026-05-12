from __future__ import annotations

from .geometry import applied_camera_step_deg
from .models import CameraSpec, LensSpec, LayoutConfig
from .physical_fit import (
    estimate_min_radius,
    estimate_min_radius_for_config,
    estimate_min_radius_for_step,
)


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
        min_radius_mm = estimate_min_radius_for_config(config, camera, lens, clearance_mm)

    return {
        "min_radius_mm": min_radius_mm,
        "recommended_radius_mm": min_radius_mm * 1.1,
    }


def solve_min_radius_for_step(
    camera: CameraSpec,
    lens: LensSpec,
    camera_count: int,
    camera_spacing_deg: float,
    clearance_mm: float = 5.0,
) -> dict[str, float]:
    """Return the minimum radius for a manually specified camera spacing angle."""

    min_radius_mm = estimate_min_radius_for_step(
        camera=camera,
        lens=lens,
        camera_spacing_deg=camera_spacing_deg,
        clearance_mm=clearance_mm,
        camera_count=camera_count,
    )

    return {
        "min_radius_mm": min_radius_mm,
        "recommended_radius_mm": min_radius_mm * 1.1,
    }


def applied_step_for_layout(config: LayoutConfig, lens: LensSpec) -> float:
    return applied_camera_step_deg(config, lens)
