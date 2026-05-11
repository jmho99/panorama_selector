from __future__ import annotations

import sqlite3
from pathlib import Path

from panorama_selector.core.models import CameraSpec, LensSpec
from .schema import CREATE_TABLES_SQL


class SpecRepository:
    """Small SQLite repository for camera and lens specs."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(CREATE_TABLES_SQL)

    def save_camera(self, camera: CameraSpec) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO cameras (name, body_width_mm, body_depth_mm, body_height_mm)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    body_width_mm = excluded.body_width_mm,
                    body_depth_mm = excluded.body_depth_mm,
                    body_height_mm = excluded.body_height_mm
                """,
                (camera.name, camera.body_width_mm, camera.body_depth_mm, camera.body_height_mm),
            )

    def save_lens(self, lens: LensSpec) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO lenses (name, hfov_deg, vfov_deg, diameter_mm, length_mm)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    hfov_deg = excluded.hfov_deg,
                    vfov_deg = excluded.vfov_deg,
                    diameter_mm = excluded.diameter_mm,
                    length_mm = excluded.length_mm
                """,
                (lens.name, lens.hfov_deg, lens.vfov_deg, lens.diameter_mm, lens.length_mm),
            )

    def delete_camera(self, name: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM cameras WHERE name = ?",
                (name,),
            )

    def delete_lens(self, name: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM lenses WHERE name = ?",
                (name,),
            )

    def list_cameras(self) -> list[CameraSpec]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name, body_width_mm, body_depth_mm, body_height_mm FROM cameras ORDER BY name"
            ).fetchall()
        return [CameraSpec(*row) for row in rows]

    def list_lenses(self) -> list[LensSpec]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name, hfov_deg, vfov_deg, diameter_mm, length_mm FROM lenses ORDER BY name"
            ).fetchall()
        return [LensSpec(*row) for row in rows]

    def get_camera(self, name: str) -> CameraSpec | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT name, body_width_mm, body_depth_mm, body_height_mm FROM cameras WHERE name = ?",
                (name,),
            ).fetchone()
        return CameraSpec(*row) if row else None

    def get_lens(self, name: str) -> LensSpec | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT name, hfov_deg, vfov_deg, diameter_mm, length_mm FROM lenses WHERE name = ?",
                (name,),
            ).fetchone()
        return LensSpec(*row) if row else None
