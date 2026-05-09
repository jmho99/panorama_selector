from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CameraSpec:
    """Physical camera body dimensions in millimetres."""

    name: str = "Custom Camera"
    body_width_mm: float = 40.0
    body_depth_mm: float = 40.0
    body_height_mm: float = 30.0


@dataclass(frozen=True)
class LensSpec:
    """Lens dimensions and optical field of view."""

    name: str = "Custom Lens"
    hfov_deg: float = 130.0
    vfov_deg: float = 90.0
    diameter_mm: float = 20.0
    length_mm: float = 20.0


@dataclass(frozen=True)
class LayoutConfig:
    """Circular layout configuration."""

    camera_count: int = 3
    radius_mm: float = 80.0
    target_panorama_deg: float = 180.0
    evaluation_distance_mm: float = 5000.0
    use_camera_spacing_deg: bool = False
    camera_spacing_deg: float | None = None
    yaw_offset_deg: float = 0.0


@dataclass(frozen=True)
class Placement:
    """Calculated camera pose on the reference circle."""

    index: int
    angle_deg: float
    x_mm: float
    y_mm: float
    yaw_deg: float
    
@dataclass(frozen=True)
class BlindZoneResult:
    """Near-field blind zone between two adjacent camera FOV boundaries."""

    camera_a_index: int
    camera_b_index: int
    overlap_start_x_mm: float
    overlap_start_y_mm: float
    perpendicular_foot_x_mm: float
    perpendicular_foot_y_mm: float
    camera_spacing_mm: float
    blind_distance_mm: float
    blind_area_mm2: float
