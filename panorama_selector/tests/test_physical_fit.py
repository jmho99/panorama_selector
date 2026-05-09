from panorama_selector.core.models import CameraSpec, LensSpec, LayoutConfig
from panorama_selector.core.physical_fit import check_physical_fit


def test_physical_fit_has_margin_key():
    result = check_physical_fit(LayoutConfig(camera_count=3, radius_mm=100.0), CameraSpec(), LensSpec())
    assert "margin_mm" in result
