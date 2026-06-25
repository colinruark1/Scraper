"""SQLite persistence so the dashboard can read results without re-scraping."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager

from .models import Firm

DB_PATH = "prospects.db"


@contextmanager
def _conn(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str = DB_PATH) -> None:
    with _conn(db_path) as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS firms (
                key            TEXT PRIMARY KEY,
                name           TEXT,
                source         TEXT,
                address        TEXT,
                phone          TEXT,
                website        TEXT,
                rating         REAL,
                review_count   INTEGER,
                loyalty_score  REAL,
                bedroom_match  INTEGER,
                breakdown      TEXT,
                data           TEXT
            )
            """
        )


def save_firms(firms: list[Firm], db_path: str = DB_PATH) -> None:
    init_db(db_path)
    with _conn(db_path) as c:
        c.execute("DELETE FROM firms")
        for f in firms:
            key = f"{f.name.lower().strip()}|{(f.address or '').lower().strip()}"
            c.execute(
                """INSERT OR REPLACE INTO firms
                   (key,name,source,address,phone,website,rating,review_count,
                    loyalty_score,bedroom_match,breakdown,data)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    key, f.name, f.source, f.address, f.phone, f.website,
                    f.rating, f.review_count, f.loyalty_score,
                    int(f.bedroom_match), json.dumps(f.score_breakdown),
                    json.dumps(f.to_dict()),
                ),
            )


def load_firms(db_path: str = DB_PATH, bedroom_only: bool = False) -> list[dict]:
    init_db(db_path)
    with _conn(db_path) as c:
        q = "SELECT * FROM firms"
        if bedroom_only:
            q += " WHERE bedroom_match = 1"
        q += " ORDER BY loyalty_score DESC"
        rows = c.execute(q).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["breakdown"] = json.loads(d["breakdown"] or "{}")
        out.append(d)
    return out
