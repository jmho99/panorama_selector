from panorama_selector.core.geometry import chord_distance, compute_layout
from panorama_selector.core.models import LayoutConfig


def test_chord_distance_for_three_cameras():
    assert round(chord_distance(100.0, 3), 6) == round(173.20508075688772, 6)


def test_compute_layout_count():
    placements = compute_layout(LayoutConfig(camera_count=3, radius_mm=100.0))
    assert len(placements) == 3
