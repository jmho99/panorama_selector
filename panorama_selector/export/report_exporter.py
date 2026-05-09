from __future__ import annotations

from pathlib import Path


def export_html_report(output_path: str | Path, title: str, rows: list[tuple[str, str]]) -> Path:
    """Minimal HTML report exporter."""

    path = Path(output_path)
    html_rows = "\n".join(f"<tr><th>{name}</th><td>{value}</td></tr>" for name, value in rows)
    path.write_text(
        f"""
<!doctype html>
<html lang="ko">
<head><meta charset="utf-8"><title>{title}</title></head>
<body>
<h1>{title}</h1>
<table border="1" cellspacing="0" cellpadding="6">
{html_rows}
</table>
</body>
</html>
""".strip(),
        encoding="utf-8",
    )
    return path
