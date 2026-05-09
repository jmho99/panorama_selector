from __future__ import annotations

import math
from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from panorama_selector.core.geometry import (
    applied_camera_step_deg,
    final_panorama_angle_deg,
    fov_edge_angles,
    is_closed_panorama,
)
from panorama_selector.core.metrics import compute_near_blind_zones
from panorama_selector.core.models import BlindZoneResult, LensSpec, LayoutConfig, Placement


class CanvasView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(520, 520)
        self._config: LayoutConfig | None = None
        self._lens: LensSpec | None = None
        self._placements: list[Placement] = []
        self._fit: dict[str, Any] = {}

    def set_scene(
        self,
        config: LayoutConfig,
        lens: LensSpec,
        placements: list[Placement],
        fit: dict[str, Any],
    ) -> None:
        self._config = config
        self._lens = lens
        self._placements = placements
        self._fit = fit
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), self.palette().base())

        if self._config is None or self._lens is None or not self._placements:
            self._draw_empty(painter)
            return

        near_blind_zones = compute_near_blind_zones(self._config, self._lens)

        margin = 48
        center = QPointF(self.width() / 2.0, self.height() / 2.0)

        view_radius_px = min(self.width(), self.height()) / 2.0 - margin
        view_radius_mm = self._view_radius_mm(near_blind_zones)
        px_per_mm = view_radius_px / view_radius_mm

        reference_radius_px = self._config.radius_mm * px_per_mm

        self._draw_analysis_label(painter)
        self._draw_reference_circle(painter, center, reference_radius_px)
        self._draw_angular_blind_zones(painter, center, view_radius_px)
        self._draw_cameras(painter, center, px_per_mm, view_radius_px)
        self._draw_near_blind_zones(painter, center, px_per_mm, near_blind_zones)
        self._draw_caption(painter)

    def _view_radius_mm(self, near_blind_zones: list[BlindZoneResult]) -> float:
        assert self._config is not None

        max_distance_mm = max(self._config.radius_mm * 2.5, 1.0)

        for placement in self._placements:
            max_distance_mm = max(
                max_distance_mm,
                math.hypot(placement.x_mm, placement.y_mm) * 1.5,
            )

        for zone in near_blind_zones:
            max_distance_mm = max(
                max_distance_mm,
                math.hypot(zone.overlap_start_x_mm, zone.overlap_start_y_mm) * 1.4,
                math.hypot(zone.perpendicular_foot_x_mm, zone.perpendicular_foot_y_mm) * 1.4,
            )

        return max(self._config.evaluation_distance_mm, 1.0)
        
    def _world_to_screen(self, center: QPointF, px_per_mm: float, x_mm: float, y_mm: float) -> QPointF:
        return QPointF(center.x() + x_mm * px_per_mm, center.y() - y_mm * px_per_mm)

    def _draw_empty(self, painter: QPainter) -> None:
        painter.setPen(QPen(Qt.GlobalColor.gray, 1))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "계산 / 갱신을 누르면 배치가 표시됩니다.")

    def _draw_analysis_label(self, painter: QPainter) -> None:
        if self._config is None:
            return

        painter.setPen(QPen(QColor(120, 120, 120), 1))
        painter.setFont(QFont("Sans Serif", 8))
        painter.drawText(
            QRectF(12, self.height() - 28, self.width() - 24, 18),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            f"분석 거리: {self._config.evaluation_distance_mm:.1f} mm "
            f"(계산 단위는 mm, 화면은 근거리 배치 확인용 확대 표시)",
        )

    def _draw_reference_circle(self, painter: QPainter, center: QPointF, radius_px: float) -> None:
        painter.setPen(QPen(QColor(120, 120, 120), 1, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius_px, radius_px)

        painter.drawLine(
            QPointF(center.x() - radius_px, center.y()),
            QPointF(center.x() + radius_px, center.y()),
        )
        painter.drawLine(
            QPointF(center.x(), center.y() - radius_px),
            QPointF(center.x(), center.y() + radius_px),
        )

    def _draw_angular_blind_zones(self, painter: QPainter, center: QPointF, view_radius_px: float) -> None:
        if self._lens is None or self._config is None or self._config.camera_count <= 1:
            return

        half_fov = self._lens.hfov_deg / 2.0
        painter.setPen(QPen(QColor(200, 80, 80), 1, Qt.PenStyle.DotLine))
        painter.setBrush(QColor(220, 80, 80, 35))

        yaw_angles = [placement.yaw_deg for placement in self._placements]
        for i in range(1, len(yaw_angles)):
            while yaw_angles[i] <= yaw_angles[i - 1]:
                yaw_angles[i] += 360.0

        pair_count = self._config.camera_count if is_closed_panorama(self._config) else self._config.camera_count - 1

        for i in range(pair_count):
            current_yaw = yaw_angles[i]
            next_yaw = yaw_angles[(i + 1) % self._config.camera_count]
            if i == self._config.camera_count - 1:
                next_yaw += 360.0

            gap_start = current_yaw + half_fov
            gap_end = next_yaw - half_fov

            if gap_end <= gap_start:
                continue

            self._draw_center_wedge(painter, center, view_radius_px, gap_start, gap_end)

    def _draw_center_wedge(
        self,
        painter: QPainter,
        center: QPointF,
        radius_px: float,
        start_deg: float,
        end_deg: float,
    ) -> None:
        points = [center]
        sample_count = max(2, int(abs(end_deg - start_deg) / 5.0) + 2)

        for i in range(sample_count):
            deg = start_deg + (end_deg - start_deg) * i / max(sample_count - 1, 1)
            rad = math.radians(deg)
            points.append(
                QPointF(
                    center.x() + math.cos(rad) * radius_px,
                    center.y() - math.sin(rad) * radius_px,
                )
            )

        painter.drawPolygon(points)

    def _draw_near_blind_zones(
        self,
        painter: QPainter,
        center: QPointF,
        px_per_mm: float,
        near_blind_zones: list[BlindZoneResult],
    ) -> None:
        if not near_blind_zones:
            return

        placement_by_index = {placement.index: placement for placement in self._placements}

        for zone in near_blind_zones:
            camera_a = placement_by_index.get(zone.camera_a_index)
            camera_b = placement_by_index.get(zone.camera_b_index)

            if camera_a is None or camera_b is None:
                continue

            point_a = self._world_to_screen(center, px_per_mm, camera_a.x_mm, camera_a.y_mm)
            point_b = self._world_to_screen(center, px_per_mm, camera_b.x_mm, camera_b.y_mm)
            overlap_point = self._world_to_screen(
                center,
                px_per_mm,
                zone.overlap_start_x_mm,
                zone.overlap_start_y_mm,
            )
            foot_point = self._world_to_screen(
                center,
                px_per_mm,
                zone.perpendicular_foot_x_mm,
                zone.perpendicular_foot_y_mm,
            )

            painter.setBrush(QColor(230, 60, 60, 70))
            painter.setPen(QPen(QColor(210, 40, 40), 2))
            painter.drawPolygon([point_a, point_b, overlap_point])

            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(180, 30, 30), 1, Qt.PenStyle.DashLine))
            painter.drawLine(foot_point, overlap_point)

            painter.setBrush(QColor(230, 60, 60))
            painter.setPen(QPen(QColor(140, 20, 20), 1))
            painter.drawEllipse(overlap_point, 4, 4)

    def _draw_cameras(
        self,
        painter: QPainter,
        center: QPointF,
        px_per_mm: float,
        fov_length_px: float,
    ) -> None:
        assert self._lens is not None

        fit_ok = bool(self._fit.get("fits", True))
        camera_color = QColor(60, 120, 220) if fit_ok else QColor(220, 90, 70)
        fov_color = QColor(80, 160, 220, 45)

        for placement in self._placements:
            pos = self._world_to_screen(center, px_per_mm, placement.x_mm, placement.y_mm)
            left_deg, right_deg = fov_edge_angles(placement.yaw_deg, self._lens.hfov_deg)
            self._draw_fov_wedge(painter, pos, left_deg, right_deg, fov_color, fov_length_px)

        for placement in self._placements:
            pos = self._world_to_screen(center, px_per_mm, placement.x_mm, placement.y_mm)

            painter.setBrush(camera_color)
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.drawEllipse(pos, 7, 7)

            yaw_rad = math.radians(placement.yaw_deg)
            heading = QPointF(
                pos.x() + math.cos(yaw_rad) * 32,
                pos.y() - math.sin(yaw_rad) * 32,
            )
            painter.drawLine(pos, heading)
            painter.drawText(pos + QPointF(8, -8), f"C{placement.index}")

    def _draw_fov_wedge(
        self,
        painter: QPainter,
        origin: QPointF,
        left_deg: float,
        right_deg: float,
        color: QColor,
        length_px: float,
    ) -> None:
        points = [origin]

        for deg in self._angle_samples(left_deg, right_deg, count=32):
            rad = math.radians(deg)
            points.append(
                QPointF(
                    origin.x() + math.cos(rad) * length_px,
                    origin.y() - math.sin(rad) * length_px,
                )
            )

        painter.setBrush(color)
        painter.setPen(QPen(QColor(80, 160, 220, 110), 1))
        painter.drawPolygon(points)

    def _angle_samples(self, left_deg: float, right_deg: float, count: int) -> list[float]:
        if self._lens is None:
            return []

        hfov = self._lens.hfov_deg
        return [(left_deg + hfov * i / max(count - 1, 1)) % 360.0 for i in range(count)]

    def _draw_caption(self, painter: QPainter) -> None:
        if self._config is None or self._lens is None:
            return

        painter.setPen(QPen(Qt.GlobalColor.darkGray, 1))
        painter.setFont(QFont("Sans Serif", 9))

        status = "외형 간섭 없음" if self._fit.get("fits", True) else "외형 간섭 가능"

        if self._config.use_camera_spacing_deg and self._config.camera_spacing_deg is not None:
            step = self._config.camera_spacing_deg
            mode = "직접각"
        else:
            step = applied_camera_step_deg(self._config, self._lens)
            mode = "목표각-HFOV"

        angular_blind = max(0.0, step - self._lens.hfov_deg)
        near_blind_count = len(compute_near_blind_zones(self._config, self._lens))
        final_angle = final_panorama_angle_deg(self._config, self._lens)

        if angular_blind > 0.0:
            blind_status = "각도 블라인드 있음"
        elif near_blind_count > 0:
            blind_status = "근거리 블라인드 있음"
        else:
            blind_status = "블라인드 없음"

        caption = (
            f"N={self._config.camera_count}, R={self._config.radius_mm:.1f} mm, "
            f"Step={step:.1f}°({mode}), HFOV={self._lens.hfov_deg:.1f}°, "
            f"목표={self._config.target_panorama_deg:.1f}°, 최종={final_angle:.1f}°, "
            f"{blind_status} / {status}"
        )

        painter.drawText(
            QRectF(12, 10, self.width() - 24, 40),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            caption,
        )
