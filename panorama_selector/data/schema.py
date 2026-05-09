CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS cameras (
    name TEXT PRIMARY KEY,
    body_width_mm REAL NOT NULL,
    body_depth_mm REAL NOT NULL,
    body_height_mm REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS lenses (
    name TEXT PRIMARY KEY,
    hfov_deg REAL NOT NULL,
    vfov_deg REAL NOT NULL,
    diameter_mm REAL NOT NULL,
    length_mm REAL NOT NULL
);
"""
