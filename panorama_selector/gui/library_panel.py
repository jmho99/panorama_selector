from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from panorama_selector.core.models import CameraSpec, LensSpec


class LibraryPanel(QWidget):
    save_camera_requested = Signal()
    save_lens_requested = Signal()
    load_camera_requested = Signal(str)
    load_lens_requested = Signal(str)
    db_path_changed = Signal(str)

    def __init__(self, default_db_path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.db_path_label = QLabel(default_db_path)
        self.db_path_label.setTextInteractionFlags(self.db_path_label.textInteractionFlags() | QtTextSelectableByMouse())

        self.choose_db_button = QPushButton("DB 위치 선택")
        self.refresh_button = QPushButton("목록 새로고침")
        self.save_camera_button = QPushButton("현재 카메라 저장")
        self.save_lens_button = QPushButton("현재 렌즈 저장")
        self.load_camera_button = QPushButton("선택 카메라 불러오기")
        self.load_lens_button = QPushButton("선택 렌즈 불러오기")

        self.camera_list = QListWidget()
        self.lens_list = QListWidget()

        camera_tab = QWidget()
        camera_layout = QVBoxLayout(camera_tab)
        camera_layout.addWidget(self.camera_list)
        camera_layout.addWidget(self.load_camera_button)

        lens_tab = QWidget()
        lens_layout = QVBoxLayout(lens_tab)
        lens_layout.addWidget(self.lens_list)
        lens_layout.addWidget(self.load_lens_button)

        self.tabs = QTabWidget()
        self.tabs.addTab(camera_tab, "카메라")
        self.tabs.addTab(lens_tab, "렌즈")

        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("DB:"))
        path_row.addWidget(self.db_path_label, 1)
        path_row.addWidget(self.choose_db_button)

        button_row = QHBoxLayout()
        button_row.addWidget(self.save_camera_button)
        button_row.addWidget(self.save_lens_button)
        button_row.addStretch(1)
        button_row.addWidget(self.refresh_button)

        group = QGroupBox("스펙 라이브러리")
        group_layout = QVBoxLayout(group)
        group_layout.addLayout(path_row)
        group_layout.addLayout(button_row)
        group_layout.addWidget(self.tabs)

        layout = QVBoxLayout(self)
        layout.addWidget(group)

        self.choose_db_button.clicked.connect(self._choose_db_path)
        self.save_camera_button.clicked.connect(self.save_camera_requested.emit)
        self.save_lens_button.clicked.connect(self.save_lens_requested.emit)
        self.load_camera_button.clicked.connect(self._emit_load_camera)
        self.load_lens_button.clicked.connect(self._emit_load_lens)

    def set_db_path(self, path: str) -> None:
        self.db_path_label.setText(path)

    def set_items(self, cameras: list[CameraSpec], lenses: list[LensSpec]) -> None:
        self.camera_list.clear()
        self.lens_list.clear()
        for camera in cameras:
            self.camera_list.addItem(camera.name)
        for lens in lenses:
            self.lens_list.addItem(lens.name)

    def _choose_db_path(self) -> None:
        current = Path(self.db_path_label.text()).expanduser()
        selected, _ = QFileDialog.getSaveFileName(
            self,
            "SQLite DB 선택",
            str(current),
            "SQLite DB (*.sqlite3 *.db);;All Files (*)",
        )
        if selected:
            self.db_path_changed.emit(selected)

    def _emit_load_camera(self) -> None:
        item = self.camera_list.currentItem()
        if item is not None:
            self.load_camera_requested.emit(item.text())

    def _emit_load_lens(self) -> None:
        item = self.lens_list.currentItem()
        if item is not None:
            self.load_lens_requested.emit(item.text())


def QtTextSelectableByMouse():
    from PySide6.QtCore import Qt

    return Qt.TextInteractionFlag.TextSelectableByMouse
