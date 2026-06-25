# PA Real-Estate Acquisition Prospector

A scraping + scoring tool that finds real-estate / property-management firms in
Pennsylvania that serve **2–3 bedroom apartments**, and ranks them by a
**"loyal & passionate" score** so you can spot the best acquisition targets.

## What "loyal & passionate" means here

No data source literally labels a firm "loyal" or "passionate." This tool builds
a 0–100 composite score from measurable proxies:

| Signal (weight)        | What it measures                                              |
|------------------------|--------------------------------------------------------------|
| Reviews & ratings (35%)| Average star rating blended with review volume (engagement). |
| Tenant language (30%)  | How often reviews use loyalty/passion phrases ("renewed", "felt like home", "like family", "go above and beyond"…). |
| Longevity (20%)        | Years active, estimated from the earliest review on record.  |
| 2–3BR focus (15%)      | Whether the firm actually advertises 2–3 bedroom / family units. |

Weights live in [`prospector/scoring.py`](prospector/scoring.py) — tune them to
taste. Treat the score as a **lead-ranking aid, not a verdict**; do your own
diligence before approaching anyone.

## Data sources (and why no Zillow scraping)

- **Google Places** and **Yelp** are queried through their **official APIs** —
  reliable, and within their Terms of Service.
- **Zillow / Apartments.com explicitly prohibit scraping** and actively block
  bots. Scraping them would expose your firm to legal and reputational risk, so
  this tool does **not** do it. Instead, the *listings* source ingests bedroom
  data from a **CSV you obtain legitimately** (an official partner/API feed, an
  MLS/IDX export, a licensed data provider, or your own records). See
  [`prospector/sources/listings.py`](prospector/sources/listings.py).

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then paste in your API keys
```

Get free API keys:
- Google Places: https://developers.google.com/maps/documentation/places/web-service/get-api-key
- Yelp Fusion: https://docs.developer.yelp.com/docs/fusion-intro

(Optional) drop a `data/listings.csv` with columns
`name,address,phone,website,bedrooms,source_id` — see
[`data/listings.sample.csv`](data/listings.sample.csv).

## Run

```bash
python run.py                       # sweeps SEARCH_AREAS from .env
python run.py "Harrisburg PA" "Erie PA"   # or pick specific areas
```

This writes `prospects.db` and `prospects.csv` (open in Excel) and prints the
top 10.

## Dashboard

```bash
python app.py        # open http://127.0.0.1:5000
```

Sort by score, filter to firms serving 2–3BR units, search by name/area, and
inspect each firm's signal breakdown.

## Project layout

```
run.py                     CLI: scrape + score -> prospects.db / prospects.csv
app.py                     Flask dashboard
prospector/
  models.py                Firm / Review data model + cross-source merge
  scoring.py               loyalty/passion scoring (tune weights here)
  pipeline.py              collect -> de-dup -> score -> store
  storage.py               SQLite read/write
  sources/
    google_places.py       Google Places API source
    yelp.py                Yelp Fusion API source
    listings.py            ToS-safe CSV ingest (your Zillow/Apartments data)
templates/index.html       dashboard UI
```

## Legal note

You are responsible for complying with each source's Terms of Service and
applicable law. The official APIs used here are the supported path; do not point
the listings source at data you are not licensed to use.
