#!/usr/bin/env python3
"""CLI entry point. Runs the scrape+score pipeline and writes prospects.db,
plus a CSV you can open in Excel.

Usage:
    python run.py                       # use SEARCH_AREAS from .env
    python run.py "Harrisburg PA" "Erie PA"
    python run.py --csv prospects.csv
"""
from __future__ import annotations

import argparse
import csv
import logging
import os
import sys

from dotenv import load_dotenv

from prospector.pipeline import run
from prospector.property_pipeline import run_properties


def main() -> int:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="PA real-estate firm prospector")
    parser.add_argument("areas", nargs="*", help="Areas to search, e.g. 'Erie PA'")
    parser.add_argument("--csv", default="prospects.csv", help="CSV output path")
    parser.add_argument("--db", default="prospects.db", help="SQLite output path")
    parser.add_argument("--properties", default=None,
                        help="Path to a listings CSV (default: data/properties.csv)")
    parser.add_argument("--skip-firms", action="store_true",
                        help="Only run market/investment analysis on properties")
    args = parser.parse_args()

    areas = args.areas or [
        a.strip()
        for a in os.getenv("SEARCH_AREAS", os.getenv("SEARCH_LOCATION", "Pennsylvania")).split(",")
        if a.strip()
    ]
    firms = []
    if not args.skip_firms:
        print(f"Searching {len(areas)} area(s): {', '.join(areas)}\n")
        firms = run(areas, db_path=args.db)
        if firms:
            _write_csv(firms, args.csv)
            print(f"\nTop loyal firms (full ranked list in {args.csv}):\n")
            for i, f in enumerate(firms[:10], 1):
                flag = " [2-3BR]" if f.bedroom_match else ""
                print(f"{i:2}. {f.loyalty_score:5.1f}  {f.name}{flag}")
        else:
            print(
                "\nNo firms found. Add a Google Places and/or Yelp key to .env,\n"
                "or drop a data/listings.csv file."
            )

    # --- market + investment analysis on property/listing data -----------
    props, stats = run_properties(args.properties, db_path=args.db)
    if props:
        print("\nTop investment opportunities (price, cap rate, opportunity):\n")
        for i, p in enumerate(props[:10], 1):
            flag = " [2-3BR]" if p.bedroom_match else ""
            price = f"${p.price:,.0f}" if p.price else "—"
            cap = f"{p.cap_rate}% cap" if p.cap_rate is not None else "cap n/a"
            print(f"{i:2}. {p.opportunity_score:5.1f}  {p.address or p.listing_id} "
                  f"({price}, {cap}){flag}")
    elif args.skip_firms:
        print(
            "\nNo property data found. Drop a data/properties.csv file "
            "(see data/properties.sample.csv) and re-run."
        )

    if not firms and not props:
        return 1
    print("\nRun the dashboard with:  python app.py")
    return 0


def _write_csv(firms, path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "rank", "loyalty_score", "name", "2-3BR_match", "rating",
            "review_count", "address", "phone", "website", "sources",
            "reviews_ratings", "tenant_language", "longevity", "bedroom_focus",
        ])
        for i, fm in enumerate(firms, 1):
            b = fm.score_breakdown
            w.writerow([
                i, fm.loyalty_score, fm.name, "yes" if fm.bedroom_match else "no",
                fm.rating or "", fm.review_count, fm.address or "", fm.phone or "",
                fm.website or "", fm.source,
                b.get("reviews_ratings", ""), b.get("tenant_language", ""),
                b.get("longevity", ""), b.get("bedroom_focus", ""),
            ])


if __name__ == "__main__":
    sys.exit(main())
