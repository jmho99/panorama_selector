from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from panorama_selector.core.geometry import chord_distance
from panorama_selector.core.models import LayoutConfig


class LayoutPanel(QWidget):
    values_changed = Signal()
    calculate_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.camera_count = QSpinBox()
        self.camera_count.setRange(1, 64)
        self.camera_count.setValue(3)

        self.radius_mm = QDoubleSpinBox()
        self.radius_mm.setRange(0.0, 100000.0)
        self.radius_mm.setDecimals(2)
        self.radius_mm.setValue(80.0)
        self.radius_mm.setSuffix(" mm")

        self.target_panorama_deg = QDoubleSpinBox()
        self.target_panorama_deg.setRange(0.0, 360.0)
        self.target_panorama_deg.setDecimals(2)
        self.target_panorama_deg.setValue(180.0)
        self.target_panorama_deg.setSuffix(" °")

        self.use_camera_spacing_deg = QCheckBox("카메라 간 각도 직접 설정")
        self.use_camera_spacing_deg.setChecked(False)

        self.camera_spacing_deg = QDoubleSpinBox()
        self.camera_spacing_deg.setRange(0.0, 360.0)
        self.camera_spacing_deg.setDecimals(2)
        self.camera_spacing_deg.setValue(60.0)
        self.camera_spacing_deg.setSuffix(" °")
        self.camera_spacing_deg.setEnabled(False)

        self.yaw_offset_deg = QDoubleSpinBox()
        self.yaw_offset_deg.setRange(-360.0, 360.0)
        self.yaw_offset_deg.setDecimals(2)
        self.yaw_offset_deg.setValue(0.0)
        self.yaw_offset_deg.setSuffix(" °")

        self.spacing_label = QLabel("-")
        self.calculate_button = QPushButton("계산 / 갱신")

        form = QFormLayout()
        form.addRow("렌즈/카메라 개수", self.camera_count)
        form.addRow("기준원 반지름", self.radius_mm)
        form.addRow("최종 파노라마 목표 각도", self.target_panorama_deg)
        form.addRow("", self.use_camera_spacing_deg)
        form.addRow("카메라 간 각도", self.camera_spacing_deg)
        form.addRow("전체 yaw offset", self.yaw_offset_deg)
        form.addRow("카메라 간 거리", self.spacing_label)

        group = QGroupBox("배치 입력")
        group.setLayout(form)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(self.calculate_button)

        layout = QVBoxLayout(self)
        layout.addWidget(group)
        layout.addLayout(button_row)
        layout.addStretch(1)

        self.camera_count.valueChanged.connect(self._on_values_changed)
        self.radius_mm.valueChanged.connect(self._on_values_changed)
        self.target_panorama_deg.valueChanged.connect(self._on_values_changed)
        self.use_camera_spacing_deg.stateChanged.connect(self._on_camera_spacing_mode_changed)
        self.camera_spacing_deg.valueChanged.connect(self._on_values_changed)
        self.yaw_offset_deg.valueChanged.connect(self._on_values_changed)
        self.calculate_button.clicked.connect(self.calculate_requested.emit)

        self._update_spacing_label()

    def get_config(self) -> LayoutConfig:
        camera_spacing_deg = None
        if self.use_camera_spacing_deg.isChecked():
            camera_spacing_deg = self.camera_spacing_deg.value()

        return LayoutConfig(
            camera_count=self.camera_count.value(),
            radius_mm=self.radius_mm.value(),
            target_panorama_deg=self.target_panorama_deg.value(),
            use_camera_spacing_deg=self.use_camera_spacing_deg.isChecked(),
            camera_spacing_deg=camera_spacing_deg,
            yaw_offset_deg=self.yaw_offset_deg.value(),
        )

    def set_radius(self, radius_mm: float) -> None:
        self.radius_mm.setValue(radius_mm)

    def set_camera_spacing_mm(self, spacing_mm: float) -> None:
        self.spacing_label.setText(f"{spacing_mm:.2f} mm")

    def _on_values_changed(self, *_args: object) -> None:
        self._update_spacing_label()
        self.values_changed.emit()

    def _applied_step_deg(self) -> float | None:
        if self.use_camera_spacing_deg.isChecked():
            return self.camera_spacing_deg.value()

        return None

    def _update_spacing_label(self) -> None:
        step_deg = self._applied_step_deg()

        if step_deg is None:
            self.spacing_label.setText("자동 계산")
            return

        spacing = chord_distance(self.radius_mm.value(), self.camera_count.value(), step_deg)
        self.spacing_label.setText(f"{spacing:.2f} mm")

    def _on_camera_spacing_mode_changed(self, *_args: object) -> None:
        self.camera_spacing_deg.setEnabled(self.use_camera_spacing_deg.isChecked())
        self._on_values_changed()
