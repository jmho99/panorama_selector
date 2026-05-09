from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDoubleSpinBox, QFormLayout, QGroupBox, QLineEdit, QVBoxLayout, QWidget

from panorama_selector.core.models import CameraSpec, LensSpec


def _dimension_spin(default: float, suffix: str = " mm") -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(0.0, 100000.0)
    spin.setDecimals(2)
    spin.setValue(default)
    spin.setSuffix(suffix)
    return spin


class SpecPanel(QWidget):
    values_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.camera_name = QLineEdit("Custom Camera")
        self.camera_width_mm = _dimension_spin(40.0)
        self.camera_depth_mm = _dimension_spin(40.0)
        self.camera_height_mm = _dimension_spin(30.0)

        self.lens_name = QLineEdit("Custom Lens")
        self.lens_hfov_deg = _dimension_spin(130.0, " °")
        self.lens_hfov_deg.setRange(1.0, 360.0)
        self.lens_vfov_deg = _dimension_spin(90.0, " °")
        self.lens_vfov_deg.setRange(1.0, 360.0)
        self.lens_diameter_mm = _dimension_spin(20.0)
        self.lens_length_mm = _dimension_spin(20.0)

        self.clearance_mm = _dimension_spin(5.0)

        camera_form = QFormLayout()
        camera_form.addRow("카메라 이름", self.camera_name)
        camera_form.addRow("카메라 폭", self.camera_width_mm)
        camera_form.addRow("카메라 깊이", self.camera_depth_mm)
        camera_form.addRow("카메라 높이", self.camera_height_mm)

        lens_form = QFormLayout()
        lens_form.addRow("렌즈 이름", self.lens_name)
        lens_form.addRow("HFOV", self.lens_hfov_deg)
        lens_form.addRow("VFOV", self.lens_vfov_deg)
        lens_form.addRow("렌즈 직경", self.lens_diameter_mm)
        lens_form.addRow("렌즈 길이", self.lens_length_mm)
        lens_form.addRow("외형 clearance", self.clearance_mm)

        camera_group = QGroupBox("카메라 외형")
        camera_group.setLayout(camera_form)
        lens_group = QGroupBox("렌즈 스펙")
        lens_group.setLayout(lens_form)

        layout = QVBoxLayout(self)
        layout.addWidget(camera_group)
        layout.addWidget(lens_group)
        layout.addStretch(1)

        for widget in (
            self.camera_name,
            self.camera_width_mm,
            self.camera_depth_mm,
            self.camera_height_mm,
            self.lens_name,
            self.lens_hfov_deg,
            self.lens_vfov_deg,
            self.lens_diameter_mm,
            self.lens_length_mm,
            self.clearance_mm,
        ):
            if isinstance(widget, QLineEdit):
                widget.textChanged.connect(self._on_values_changed)
            else:
                widget.valueChanged.connect(self._on_values_changed)

    def _on_values_changed(self, *args) -> None:
        self.values_changed.emit()
        
    def get_camera_spec(self) -> CameraSpec:
        return CameraSpec(
            name=self.camera_name.text().strip() or "Custom Camera",
            body_width_mm=self.camera_width_mm.value(),
            body_depth_mm=self.camera_depth_mm.value(),
            body_height_mm=self.camera_height_mm.value(),
        )

    def get_lens_spec(self) -> LensSpec:
        return LensSpec(
            name=self.lens_name.text().strip() or "Custom Lens",
            hfov_deg=self.lens_hfov_deg.value(),
            vfov_deg=self.lens_vfov_deg.value(),
            diameter_mm=self.lens_diameter_mm.value(),
            length_mm=self.lens_length_mm.value(),
        )

    def get_clearance_mm(self) -> float:
        return self.clearance_mm.value()

    def set_camera_spec(self, camera: CameraSpec) -> None:
        self.camera_name.setText(camera.name)
        self.camera_width_mm.setValue(camera.body_width_mm)
        self.camera_depth_mm.setValue(camera.body_depth_mm)
        self.camera_height_mm.setValue(camera.body_height_mm)

    def set_lens_spec(self, lens: LensSpec) -> None:
        self.lens_name.setText(lens.name)
        self.lens_hfov_deg.setValue(lens.hfov_deg)
        self.lens_vfov_deg.setValue(lens.vfov_deg)
        self.lens_diameter_mm.setValue(lens.diameter_mm)
        self.lens_length_mm.setValue(lens.length_mm)
