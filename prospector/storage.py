"""SQLite persistence so the dashboard can read results without re-scraping."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager

from .models import Firm, Property, MarketStats

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
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS properties (
                listing_id        TEXT PRIMARY KEY,
                address           TEXT,
                city              TEXT,
                zip               TEXT,
                price             REAL,
                bedrooms          REAL,
                bathrooms         REAL,
                sqft              REAL,
                price_per_sqft    REAL,
                days_on_market    INTEGER,
                monthly_rent      REAL,
                cap_rate          REAL,
                gross_yield       REAL,
                value_vs_market   REAL,
                price_drop_pct    REAL,
                opportunity_score REAL,
                bedroom_match     INTEGER,
                owner_firm        TEXT,
                listing_url       TEXT,
                breakdown         TEXT,
                data              TEXT
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS market (
                area          TEXT PRIMARY KEY,
                n_listings    INTEGER,
                median_price  REAL,
                median_ppsf   REAL,
                median_dom    REAL,
                median_yield  REAL,
                avg_price_drop REAL
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


def save_properties(props: list[Property], db_path: str = DB_PATH) -> None:
    init_db(db_path)
    with _conn(db_path) as c:
        c.execute("DELETE FROM properties")
        for p in props:
            c.execute(
                """INSERT OR REPLACE INTO properties
                   (listing_id,address,city,zip,price,bedrooms,bathrooms,sqft,
                    price_per_sqft,days_on_market,monthly_rent,cap_rate,
                    gross_yield,value_vs_market,price_drop_pct,opportunity_score,
                    bedroom_match,owner_firm,listing_url,breakdown,data)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    p.listing_id, p.address, p.city, p.zip, p.price, p.bedrooms,
                    p.bathrooms, p.sqft, p.price_per_sqft, p.days_on_market,
                    p.monthly_rent, p.cap_rate, p.gross_yield, p.value_vs_market,
                    p.price_drop_pct, p.opportunity_score, int(p.bedroom_match),
                    p.owner_firm, p.listing_url, json.dumps(p.score_breakdown),
                    json.dumps(p.to_dict()),
                ),
            )


def save_market(stats: dict[str, MarketStats], db_path: str = DB_PATH) -> None:
    init_db(db_path)
    with _conn(db_path) as c:
        c.execute("DELETE FROM market")
        for s in stats.values():
            c.execute(
                """INSERT OR REPLACE INTO market
                   (area,n_listings,median_price,median_ppsf,median_dom,
                    median_yield,avg_price_drop)
                   VALUES (?,?,?,?,?,?,?)""",
                (s.area, s.n_listings, s.median_price, s.median_ppsf,
                 s.median_dom, s.median_yield, s.avg_price_drop),
            )


def load_properties(db_path: str = DB_PATH, bedroom_only: bool = False,
                    min_score: float = 0.0) -> list[dict]:
    init_db(db_path)
    with _conn(db_path) as c:
        q = "SELECT * FROM properties WHERE opportunity_score >= ?"
        params = [min_score]
        if bedroom_only:
            q += " AND bedroom_match = 1"
        q += " ORDER BY opportunity_score DESC"
        rows = c.execute(q, params).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["breakdown"] = json.loads(d["breakdown"] or "{}")
        out.append(d)
    return out


def load_market(db_path: str = DB_PATH) -> list[dict]:
    init_db(db_path)
    with _conn(db_path) as c:
        rows = c.execute(
            "SELECT * FROM market ORDER BY n_listings DESC"
        ).fetchall()
    return [dict(r) for r in rows]
