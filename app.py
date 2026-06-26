#!/usr/bin/env python3
"""Local dashboard for browsing ranked prospects.

    python app.py            # then open http://127.0.0.1:5000

Reads prospects.db (run.py writes it). Lets you sort, filter to 2-3BR firms,
and inspect each firm's score breakdown.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from prospector.storage import load_firms, load_properties, load_market

load_dotenv()
app = Flask(__name__)
DB_PATH = os.getenv("DB_PATH", "prospects.db")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/firms")
def api_firms():
    bedroom_only = request.args.get("bedroom_only") == "1"
    firms = load_firms(DB_PATH, bedroom_only=bedroom_only)
    q = (request.args.get("q") or "").lower().strip()
    if q:
        firms = [f for f in firms if q in (f["name"] or "").lower()
                 or q in (f["address"] or "").lower()]
    return jsonify(firms)


@app.route("/api/properties")
def api_properties():
    bedroom_only = request.args.get("bedroom_only") == "1"
    try:
        min_score = float(request.args.get("min_score") or 0)
    except ValueError:
        min_score = 0.0
    props = load_properties(DB_PATH, bedroom_only=bedroom_only, min_score=min_score)
    q = (request.args.get("q") or "").lower().strip()
    if q:
        props = [p for p in props if q in (p["address"] or "").lower()
                 or q in (p["city"] or "").lower() or q in (p["zip"] or "").lower()
                 or q in (p["owner_firm"] or "").lower()]
    return jsonify(props)


@app.route("/api/market")
def api_market():
    return jsonify(load_market(DB_PATH))


if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", "5000")))
