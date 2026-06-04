"""
db.py  —  Persistent Storage Layer
====================================
Handles all portfolio persistence for Streamlit Cloud.

Storage strategy (in priority order):
  1. Streamlit Cloud file storage via st.secrets["storage_path"]
     — if a writable path is configured, JSON is written there
  2. GitHub Gist (if GIST_TOKEN + GIST_ID set in secrets)
     — reads/writes a private GitHub Gist, survives restarts
  3. Local file (data/portfolio.json)
     — works on local machine, resets on Streamlit Cloud restart

To enable GitHub Gist persistence (recommended for Streamlit Cloud):
  In Streamlit Cloud → Settings → Secrets, add:
    GIST_TOKEN = "ghp_your_github_pat_token"
    GIST_ID    = "your_gist_id"

To create a Gist:
  1. Go to gist.github.com
  2. Create a new PRIVATE gist named "portfolio.json"
  3. Paste the default portfolio JSON (or any valid JSON)
  4. Copy the Gist ID from the URL
  5. Create a GitHub Personal Access Token with "gist" scope
  6. Add both to Streamlit secrets

CSV backup/restore is always available regardless of backend.
"""

import json
import os
import io
import csv
from datetime import datetime, timezone
from typing import Optional

# ── Default portfolio (used on first-ever initialization) ──────────────────
DEFAULT_PORTFOLIO = {
    "holdings": [],          # empty — user adds their own
    "cash":     0.0,
    "currency": "USD",
    "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
}

LOCAL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "portfolio.json"
)


# ─────────────────────────────────────────────────────────────────────────────
# BACKEND DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def _get_secrets() -> dict:
    """Safely read Streamlit secrets without crashing if unavailable."""
    try:
        import streamlit as st
        return dict(st.secrets)
    except Exception:
        return {}


def _backend() -> str:
    """Return 'gist' | 'local'."""
    s = _get_secrets()
    if s.get("GIST_TOKEN") and s.get("GIST_ID"):
        return "gist"
    return "local"


# ─────────────────────────────────────────────────────────────────────────────
# GITHUB GIST BACKEND
# ─────────────────────────────────────────────────────────────────────────────

def _gist_load() -> dict:
    import urllib.request
    s       = _get_secrets()
    gist_id = s["GIST_ID"]
    token   = s["GIST_TOKEN"]
    url     = "https://api.github.com/gists/%s" % gist_id
    req     = urllib.request.Request(url, headers={
        "Authorization": "token %s" % token,
        "Accept":        "application/vnd.github.v3+json",
        "User-Agent":    "PortfolioApp",
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
    # Find the portfolio file in the gist
    files = data.get("files", {})
    for fname, fdata in files.items():
        if fname.endswith(".json"):
            raw = fdata.get("content", "{}")
            return json.loads(raw)
    return dict(DEFAULT_PORTFOLIO)


def _gist_save(portfolio: dict) -> bool:
    import urllib.request
    s       = _get_secrets()
    gist_id = s["GIST_ID"]
    token   = s["GIST_TOKEN"]

    portfolio["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    content  = json.dumps(portfolio, indent=2)
    payload  = json.dumps({
        "files": {"portfolio.json": {"content": content}}
    }).encode()

    url = "https://api.github.com/gists/%s" % gist_id
    req = urllib.request.Request(url, data=payload, method="PATCH", headers={
        "Authorization": "token %s" % token,
        "Content-Type":  "application/json",
        "Accept":        "application/vnd.github.v3+json",
        "User-Agent":    "PortfolioApp",
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status == 200


# ─────────────────────────────────────────────────────────────────────────────
# LOCAL FILE BACKEND
# ─────────────────────────────────────────────────────────────────────────────

def _local_load() -> dict:
    if not os.path.exists(LOCAL_PATH):
        return dict(DEFAULT_PORTFOLIO)
    try:
        with open(LOCAL_PATH) as f:
            data = json.load(f)
        # Remove legacy current_price fields
        for h in data.get("holdings", []):
            for k in ("current_price", "prev_close", "change_pct"):
                h.pop(k, None)
        return data
    except Exception:
        return dict(DEFAULT_PORTFOLIO)


def _local_save(portfolio: dict) -> bool:
    try:
        os.makedirs(os.path.dirname(LOCAL_PATH), exist_ok=True)
        portfolio["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        clean = json.loads(json.dumps(portfolio))
        for h in clean.get("holdings", []):
            for k in ("current_price", "prev_close", "change_pct"):
                h.pop(k, None)
        with open(LOCAL_PATH, "w") as f:
            json.dump(clean, f, indent=2)
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API  — engine.py and app.py use only these functions
# ─────────────────────────────────────────────────────────────────────────────

def load_portfolio() -> dict:
    """Load portfolio from the active backend. Never raises."""
    try:
        if _backend() == "gist":
            return _gist_load()
    except Exception:
        pass  # fall through to local
    return _local_load()


def save_portfolio(portfolio: dict) -> bool:
    """Save portfolio to the active backend. Returns True on success."""
    # Always save locally as a cache/fallback
    _local_save(portfolio)
    if _backend() == "gist":
        try:
            return _gist_save(portfolio)
        except Exception:
            return False
    return True


def get_backend_name() -> str:
    b = _backend()
    if b == "gist":
        return "GitHub Gist (persistent)"
    return "Local file (resets on cloud restart)"


# ─────────────────────────────────────────────────────────────────────────────
# HOLDING CRUD
# ─────────────────────────────────────────────────────────────────────────────

def upsert_holding(portfolio: dict, holding: dict) -> dict:
    """
    Add or update a holding by ticker.
    holding must contain at least: ticker, name, sector, style, status,
                                   shares, avg_buy.
    Returns updated portfolio dict (not yet saved — caller must call save_portfolio).
    """
    ticker   = holding["ticker"].strip().upper()
    holdings = portfolio.get("holdings", [])
    existing = [i for i, h in enumerate(holdings) if h["ticker"] == ticker]

    clean = {
        "ticker":        ticker,
        "name":          holding.get("name", ticker),
        "sector":        holding.get("sector", "Other"),
        "style":         holding.get("style", "Growth"),
        "status":        holding.get("status", "Watchlist"),
        "shares":        float(holding.get("shares", 0)),
        "avg_buy":       float(holding.get("avg_buy", 0)),
        "target_entry":  holding.get("target_entry") or None,
        "notes":         holding.get("notes", ""),
    }

    if existing:
        holdings[existing[0]] = clean
    else:
        holdings.append(clean)

    portfolio["holdings"] = holdings
    return portfolio


def delete_holding(portfolio: dict, ticker: str) -> dict:
    """Remove a holding by ticker. Returns updated portfolio dict."""
    ticker   = ticker.strip().upper()
    portfolio["holdings"] = [
        h for h in portfolio.get("holdings", [])
        if h["ticker"] != ticker
    ]
    return portfolio


def set_cash(portfolio: dict, amount: float) -> dict:
    """Update cash balance. Returns updated portfolio dict."""
    portfolio["cash"] = round(float(amount), 2)
    return portfolio


# ─────────────────────────────────────────────────────────────────────────────
# CSV BACKUP / RESTORE
# ─────────────────────────────────────────────────────────────────────────────

EXPORT_FIELDS = [
    "ticker", "name", "sector", "style", "status",
    "shares", "avg_buy", "target_entry", "notes",
]


def export_csv(portfolio: dict) -> str:
    """Return portfolio holdings as a CSV string."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=EXPORT_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for h in portfolio.get("holdings", []):
        writer.writerow({f: h.get(f, "") for f in EXPORT_FIELDS})
    # Append cash as a special row
    output.write("\n# Cash,%s\n" % portfolio.get("cash", 0))
    return output.getvalue()


def import_csv(csv_text: str, existing_portfolio: Optional[dict] = None) -> dict:
    """
    Parse a CSV string (exported by export_csv) and return a portfolio dict.
    Merges into existing_portfolio if provided; otherwise starts fresh.
    """
    portfolio = existing_portfolio or dict(DEFAULT_PORTFOLIO)
    portfolio["holdings"] = []

    lines = csv_text.splitlines()
    data_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# Cash,"):
            try:
                cash_val = float(stripped.split(",")[1])
                portfolio["cash"] = cash_val
            except (IndexError, ValueError):
                pass
        elif stripped and not stripped.startswith("#"):
            data_lines.append(stripped)

    if not data_lines:
        return portfolio

    reader = csv.DictReader(data_lines)
    for row in reader:
        try:
            h = {
                "ticker":       row.get("ticker", "").strip().upper(),
                "name":         row.get("name", ""),
                "sector":       row.get("sector", "Other"),
                "style":        row.get("style", "Growth"),
                "status":       row.get("status", "Watchlist"),
                "shares":       float(row.get("shares", 0) or 0),
                "avg_buy":      float(row.get("avg_buy", 0) or 0),
                "target_entry": float(row["target_entry"]) if row.get("target_entry") else None,
                "notes":        row.get("notes", ""),
            }
            if h["ticker"]:
                portfolio = upsert_holding(portfolio, h)
        except Exception:
            continue

    return portfolio
