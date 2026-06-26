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

## Market analysis & investment opportunities

Beyond *who* to buy, the tool scores *which properties* are high-value buys —
the "Market Analysis", "Property Data", and "Investment Information" the
scraping guides describe.

Drop a listings export at `data/properties.csv` (columns:
`listing_id,address,city,state,zip,price,bedrooms,bathrooms,sqft,days_on_market,monthly_rent,property_type,listing_url,owner_firm,price_history`
— see [`data/properties.sample.csv`](data/properties.sample.csv)). Same ToS-safe
rule: the guides recommend Zillow/Redfin/Realtor (all scrape-prohibited) and
point licensed pros at **MLS/RETS feeds** — export from one of those, a licensed
data provider, or your own records.

From that the tool computes:

- **Market stats by zip** ([`market.py`](prospector/market.py)) — median price,
  median $/sqft, median days-on-market, median rental yield, avg price drop.
- **Investment metrics per listing** ([`investment.py`](prospector/investment.py)) —
  cap rate, gross yield, value vs. area comps ($/sqft), price-drop %, and an
  **opportunity score (0–100)** rewarding undervalued + high-yield + motivated
  sellers + 2–3BR matches. Tune `WEIGHTS` to your buy box.

## Run

```bash
python run.py                       # firms (sweeps SEARCH_AREAS) + properties
python run.py "Harrisburg PA" "Erie PA"   # firm search in specific areas
python run.py --skip-firms          # only re-run market/investment analysis
```

Writes `prospects.db` + `prospects.csv` (firms) and prints the top loyal firms
**and** the top investment opportunities.

## Dashboard

```bash
python app.py        # open http://127.0.0.1:5000
```

Three tabs:
- **Loyal Firms** — ranked acquisition targets with signal breakdown.
- **Opportunities** — ranked listings with cap rate, yield, vs-market, DOM, and
  filters for 2–3BR / score ≥ 50.
- **Market Analysis** — per-zip price, $/sqft, DOM, yield, and price-drop stats.

## Project layout

```
run.py                     CLI: firms + properties -> prospects.db / prospects.csv
app.py                     Flask dashboard (firms / opportunities / market)
prospector/
  models.py                Firm, Property, MarketStats data models
  scoring.py               firm loyalty/passion scoring (tune weights)
  market.py                per-zip market analysis aggregation
  investment.py            cap rate / yield / opportunity scoring (tune weights)
  pipeline.py              firms: collect -> de-dup -> score -> store
  property_pipeline.py     properties: load -> market stats -> score -> store
  storage.py               SQLite read/write (firms, properties, market)
  sources/
    google_places.py       Google Places API source (firms)
    yelp.py                Yelp Fusion API source (firms)
    listings.py            ToS-safe firm CSV ingest
    properties.py          ToS-safe listing/property CSV ingest
templates/index.html       dashboard UI
```

## Legal note

You are responsible for complying with each source's Terms of Service and
applicable law. The official APIs used here are the supported path; do not point
the listings source at data you are not licensed to use.
