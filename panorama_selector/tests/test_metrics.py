import math

from panorama_selector.core.metrics import compute_metrics
from panorama_selector.core.models import LayoutConfig, LensSpec


def test_overlap_for_three_130deg_lenses_with_180deg_target():
    metrics = compute_metrics(LayoutConfig(camera_count=3), LensSpec(hfov_deg=130.0))
    assert metrics["angular_step_deg"] == 60.0
    assert metrics["overlap_deg_each"] == 70.0
    assert metrics["blind_deg_each"] == 0.0
    assert metrics["final_panorama_deg"] == 250.0


def test_blind_zone_when_spacing_is_larger_than_hfov():
    config = LayoutConfig(
        camera_count=3,
        target_panorama_deg=180.0,
        use_camera_spacing_deg=True,
        camera_spacing_deg=120.0,
        evaluation_distance_mm=1000.0,
    )
    metrics = compute_metrics(config, LensSpec(hfov_deg=90.0))

    assert metrics["overlap_deg_each"] == 0.0
    assert metrics["blind_deg_each"] == 30.0
    assert metrics["blind_gap_count"] == 2.0
    assert metrics["total_blind_deg"] == 60.0
    assert math.isclose(metrics["blind_arc_length_each_mm"], math.radians(30.0) * 1000.0)


def test_full_360_target_counts_wraparound_blind_gap():
    config = LayoutConfig(camera_count=3, target_panorama_deg=360.0)
    metrics = compute_metrics(config, LensSpec(hfov_deg=90.0))

    assert metrics["blind_gap_count"] == 3.0
    assert metrics["blind_deg_each"] == 30.0
    assert metrics["total_blind_deg"] == 90.0
    assert metrics["final_panorama_deg"] == 270.0
