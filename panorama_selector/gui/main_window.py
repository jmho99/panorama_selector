from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from panorama_selector.core.geometry import compute_layout
from panorama_selector.core.metrics import compute_metrics
from panorama_selector.core.physical_fit import check_physical_fit
from panorama_selector.core.solver import solve_min_radius_for_layout
from panorama_selector.data.repository import SpecRepository
from panorama_selector.gui.canvas_view import CanvasView
from panorama_selector.gui.layout_panel import LayoutPanel
from panorama_selector.gui.library_panel import LibraryPanel
from panorama_selector.gui.result_panel import ResultPanel
from panorama_selector.gui.spec_panel import SpecPanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Panorama Camera Selector")
        self.resize(1280, 820)

        self.repository = SpecRepository(self._default_db_path())

        self.layout_panel = LayoutPanel()
        self.spec_panel = SpecPanel()
        self.canvas_view = CanvasView()
        self.result_panel = ResultPanel()
        self.library_panel = LibraryPanel(str(self.repository.db_path))

        self.apply_min_radius_button = QPushButton("외형 기준 최소 반지름 적용")

        self._build_ui()
        self._connect_signals()
        self._refresh_library()
        self.calculate()

    def _build_ui(self) -> None:
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(self.layout_panel)
        left_layout.addWidget(self.spec_panel)
        left_layout.addWidget(self.apply_min_radius_button)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(self.canvas_view, 3)
        right_layout.addWidget(self.result_panel, 2)

        splitter = QSplitter()
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        design_tab = QWidget()
        design_layout = QHBoxLayout(design_tab)
        design_layout.addWidget(splitter)

        tabs = QTabWidget()
        tabs.addTab(design_tab, "배치 계산")
        tabs.addTab(self.library_panel, "라이브러리")
        self.setCentralWidget(tabs)

    def _connect_signals(self) -> None:
        self.layout_panel.calculate_requested.connect(self.calculate)
        self.layout_panel.values_changed.connect(self.calculate)
        self.spec_panel.values_changed.connect(self.calculate)
        self.apply_min_radius_button.clicked.connect(self.apply_min_radius)

        self.library_panel.refresh_button.clicked.connect(self._refresh_library)
        self.library_panel.save_camera_requested.connect(self._save_current_camera)
        self.library_panel.save_lens_requested.connect(self._save_current_lens)
        self.library_panel.load_camera_requested.connect(self._load_camera)
        self.library_panel.load_lens_requested.connect(self._load_lens)
        self.library_panel.delete_camera_requested.connect(self._delete_camera)
        self.library_panel.delete_lens_requested.connect(self._delete_lens)
        self.library_panel.db_path_changed.connect(self._change_db_path)

    def calculate(self) -> None:
        config = self.layout_panel.get_config()
        camera = self.spec_panel.get_camera_spec()
        lens = self.spec_panel.get_lens_spec()
        clearance_mm = self.spec_panel.get_clearance_mm()

        try:
            placements = compute_layout(config, lens)
            metrics = compute_metrics(config, lens)
            fit = check_physical_fit(config, camera, lens, clearance_mm)
            solution = solve_min_radius_for_layout(config, camera, lens, clearance_mm)
        except ValueError as exc:
            QMessageBox.warning(self, "입력 오류", str(exc))
            return

        self.layout_panel.set_camera_spacing_mm(metrics["camera_spacing_mm"])
        self.canvas_view.set_scene(config, lens, placements, fit)
        self.result_panel.set_results(self._format_result_rows(metrics, fit, solution))
        self.statusBar().showMessage("계산 완료")

    def apply_min_radius(self) -> None:
        config = self.layout_panel.get_config()
        camera = self.spec_panel.get_camera_spec()
        lens = self.spec_panel.get_lens_spec()
        clearance_mm = self.spec_panel.get_clearance_mm()

        solution = solve_min_radius_for_layout(config, camera, lens, clearance_mm)
        recommended_radius_mm = solution["recommended_radius_mm"]

        if not math.isfinite(recommended_radius_mm):
            QMessageBox.warning(
                self,
                "계산 불가",
                "카메라 간 각도 간격이 0°이므로 외형 기준 최소 반지름을 계산할 수 없습니다.",
            )
            return

        self.layout_panel.set_radius(recommended_radius_mm)
        self.calculate()

    def _format_result_rows(
        self,
        metrics: dict[str, float],
        fit: dict[str, Any],
        solution: dict[str, float],
    ) -> list[tuple[str, str]]:
        fit_text = "가능" if fit["fits"] else "간섭 가능"

        near_blind_count = metrics.get("near_blind_zone_count", 0.0)
        near_blind_text = "있음" if near_blind_count > 0.0 else "없음"

        min_radius_text = self._format_mm(fit["min_radius_mm"])
        recommended_radius_text = self._format_mm(solution["recommended_radius_mm"])

        return [
            ("카메라 개수", f"{metrics['camera_count']:.0f}"),
            ("HFOV", f"{metrics['hfov_deg']:.2f} °"),
            ("목표 파노라마 각도", f"{metrics['target_panorama_deg']:.2f} °"),
            ("최종 파노라마 각도", f"{metrics['final_panorama_deg']:.2f} °"),
            ("카메라 간 각도 간격", f"{metrics['angular_step_deg']:.2f} °"),
            ("인접 카메라 overlap 각도", f"{metrics['overlap_deg_each']:.2f} °"),
            ("렌즈 간 거리", f"{metrics['camera_spacing_mm']:.2f} mm"),
            ("현재 외형 최소 간격", f"{fit['min_footprint_distance_mm']:.2f} mm"),
            ("외형 기준 최소 반지름", min_radius_text),
            ("권장 반지름", recommended_radius_text),

            ("근거리 블라인드 발생 여부", near_blind_text),
            ("근거리 블라인드 개수", f"{near_blind_count:.0f}"),
            ("근거리 블라인드 평균거리", f"{metrics.get('near_blind_distance_avg_mm', 0.0):.2f} mm"),
            ("근거리 블라인드 최대거리", f"{metrics.get('near_blind_distance_max_mm', 0.0):.2f} mm"),
            ("근거리 블라인드 총 면적", f"{metrics.get('near_blind_area_total_mm2', 0.0):.2f} mm²"),

            ("외형 배치 가능 여부", fit_text),
            ("배치 기준점", "렌즈 길이 1/2 위치"),
            ("카메라 외형", f"{fit['camera_body_width_mm']:.2f} × {fit['camera_body_depth_mm']:.2f} mm"),
            ("렌즈 외형", f"직경 {fit['lens_diameter_mm']:.2f} mm / 길이 {fit['lens_length_mm']:.2f} mm"),
            ("필요 clearance 기준 폭", f"{fit['required_clear_width_mm']:.2f} mm"),
            ("필요 전체 깊이", f"{fit['required_total_depth_mm']:.2f} mm"),
            ("현재 외형 여유", f"{fit['margin_mm']:.2f} mm"),
            
        ]

    def _format_mm(self, value: float) -> str:
        if not math.isfinite(value):
            return "계산 불가"
        return f"{value:.2f} mm"

    def _save_current_camera(self) -> None:
        self.repository.save_camera(self.spec_panel.get_camera_spec())
        self._refresh_library()
        self.statusBar().showMessage("카메라 스펙 저장 완료")

    def _save_current_lens(self) -> None:
        self.repository.save_lens(self.spec_panel.get_lens_spec())
        self._refresh_library()
        self.statusBar().showMessage("렌즈 스펙 저장 완료")

    def _load_camera(self, name: str) -> None:
        camera = self.repository.get_camera(name)
        if camera is None:
            QMessageBox.warning(self, "불러오기 실패", f"카메라를 찾을 수 없습니다: {name}")
            return
        self.spec_panel.set_camera_spec(camera)
        self.calculate()

    def _load_lens(self, name: str) -> None:
        lens = self.repository.get_lens(name)
        if lens is None:
            QMessageBox.warning(self, "불러오기 실패", f"렌즈를 찾을 수 없습니다: {name}")
            return
        self.spec_panel.set_lens_spec(lens)
        self.calculate()

    def _delete_camera(self, name: str) -> None:
        result = QMessageBox.question(
            self,
            "카메라 삭제",
            f"선택한 카메라 스펙을 삭제할까요?\n\n{name}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if result != QMessageBox.StandardButton.Yes:
            return

        self.repository.delete_camera(name)
        self._refresh_library()
        self.statusBar().showMessage(f"카메라 스펙 삭제 완료: {name}")

    def _delete_lens(self, name: str) -> None:
        result = QMessageBox.question(
            self,
            "렌즈 삭제",
            f"선택한 렌즈 스펙을 삭제할까요?\n\n{name}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if result != QMessageBox.StandardButton.Yes:
            return

        self.repository.delete_lens(name)
        self._refresh_library()
        self.statusBar().showMessage(f"렌즈 스펙 삭제 완료: {name}")

    def _refresh_library(self) -> None:
        self.library_panel.set_items(self.repository.list_cameras(), self.repository.list_lenses())

    def _change_db_path(self, db_path: str) -> None:
        self.repository = SpecRepository(db_path)
        self.library_panel.set_db_path(str(self.repository.db_path))
        self._refresh_library()

    def _default_db_path(self) -> Path:
        return Path.home() / ".panorama_selector" / "panorama_specs.sqlite3"


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
