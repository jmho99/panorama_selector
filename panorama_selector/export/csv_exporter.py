from __future__ import annotations

import csv
from pathlib import Path


def export_rows(output_path: str | Path, rows: list[tuple[str, str]]) -> Path:
    path = Path(output_path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "value"])
        writer.writerows(rows)
    return path
