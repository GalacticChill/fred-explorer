#!/usr/bin/env python3
"""Build step for FRED Explorer.

Fetches a curated set of public-domain U.S. macroeconomic series from FRED's
keyless CSV endpoint and bundles them into a single static index.html (data
embedded inline, so the published page needs no API key and makes no network
calls). Re-run to refresh the data: `python3 build.py`.
"""
import json
import sys
import urllib.request
from datetime import date

# id, display name, unit, category, source (all public-domain U.S. gov series)
SERIES = [
    ("UNRATE",   "Unemployment Rate",       "%",                 "Labor",       "BLS"),
    ("PAYEMS",   "Nonfarm Payrolls",        "thousands",         "Labor",       "BLS"),
    ("ICSA",     "Initial Jobless Claims",  "claims",            "Labor",       "DOL"),
    ("CPIAUCSL", "CPI (All Items)",         "index 1982-84=100", "Prices",      "BLS"),
    ("PCEPI",    "PCE Price Index",         "index 2017=100",    "Prices",      "BEA"),
    ("PPIACO",   "PPI (All Commodities)",   "index 1982=100",    "Prices",      "BLS"),
    ("FEDFUNDS", "Federal Funds Rate",      "%",                 "Rates",       "Federal Reserve"),
    ("GS10",     "10-Year Treasury Yield",  "%",                 "Rates",       "Federal Reserve"),
    ("GS2",      "2-Year Treasury Yield",   "%",                 "Rates",       "Federal Reserve"),
    ("T10Y2Y",   "10Y-2Y Treasury Spread",  "%",                 "Rates",       "Federal Reserve"),
    ("M2SL",     "M2 Money Stock",          "$ billions",        "Money",       "Federal Reserve"),
    ("INDPRO",   "Industrial Production",   "index 2017=100",    "Output",      "Federal Reserve"),
    ("GDPC1",    "Real GDP (quarterly)",    "$ billions 2017",   "Output",      "BEA"),
    ("HOUST",    "Housing Starts",          "thousands",         "Housing",     "Census"),
    ("RSAFS",    "Retail Sales",            "$ millions",        "Consumer",    "Census"),
    ("PCE",      "Personal Consumption Exp.","$ billions",       "Consumer",    "BEA"),
    ("WTISPLC",  "WTI Crude Oil Price",     "$/barrel",          "Commodities", "EIA"),
]

CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"


def month_index(y, m):
    return y * 12 + (m - 1)


def fetch(series_id):
    url = CSV_URL.format(series_id)
    req = urllib.request.Request(url, headers={"User-Agent": "fred-explorer-build/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        text = resp.read().decode("utf-8")
    rows = [ln for ln in text.splitlines() if ln.strip()]
    rows = rows[1:]  # drop header
    pairs = []
    for ln in rows:
        parts = ln.split(",")
        if len(parts) < 2:
            continue
        d = parts[0].strip()
        v = parts[1].strip()
        y, m, _ = d.split("-")
        val = None if v in (".", "") else float(v)
        pairs.append((int(y), int(m), val))
    if not pairs:
        raise RuntimeError("no data for " + series_id)
    # dense monthly array from first to last observation
    start_y, start_m, _ = pairs[0]
    end_y, end_m, _ = pairs[-1]
    n = month_index(end_y, end_m) - month_index(start_y, start_m) + 1
    values = [None] * n
    base = month_index(start_y, start_m)
    for (y, m, val) in pairs:
        values[month_index(y, m) - base] = val
    return {"start": "%04d-%02d" % (start_y, start_m), "values": values}


def main():
    meta = []
    series = {}
    for (sid, name, unit, cat, src) in SERIES:
        sys.stderr.write("fetching %s ...\n" % sid)
        data = fetch(sid)
        meta.append({"id": sid, "name": name, "unit": unit, "cat": cat, "src": src,
                     "start": data["start"], "n": len(data["values"])})
        series[sid] = data
    bundle = {"built": date.today().isoformat(), "meta": meta, "series": series}
    payload = json.dumps(bundle, separators=(",", ":"))

    with open("index.template.html", "r") as f:
        template = f.read()
    html = template.replace("/*__DATA__*/", payload)
    with open("index.html", "w") as f:
        f.write(html)

    sys.stderr.write("wrote index.html (%d KB, %d series)\n" % (len(html) // 1024, len(meta)))


if __name__ == "__main__":
    main()
