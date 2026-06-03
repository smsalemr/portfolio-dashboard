"""
engine.py
=========
Pure calculation logic — no Streamlit dependency.
Reads data/portfolio.json, fetches prices via yfinance,
returns structured dicts for the dashboard to render.
"""

from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from dataclasses import dataclass, field

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "portfolio.json")

SECTOR_COLORS = {
    "Technology":        "#3B82F6",
    "Enterprise Software":"#8B5CF6",
    "Industrials":       "#F59E0B",
    "Energy":            "#10B981",
    "Healthcare":        "#EC4899",
    "Consumer":          "#F97316",
    "Financial":         "#06B6D4",
    "EV / Technology":   "#6366F1",
    "Other":             "#6B7280",
}

STYLE_ICONS = {
    "Compounder":  "🔵",
    "Growth":      "🟣",
    "Cyclical":    "🟠",
    "Value":       "🟡",
    "Speculative": "🔴",
}

# ── Data loading ──────────────────────────────────────────────────────────────

def load_portfolio() -> dict:
    with open(DATA_PATH, "r") as f:
        return json.load(f)


def save_portfolio(data: dict):
    with open(DATA_PATH, "w") as f:
        json.dump(data, f, indent=2)


# ── Price fetching ────────────────────────────────────────────────────────────

def fetch_prices(tickers: list[str]) -> dict[str, dict]:
    """
    Fetch current prices via yfinance.
    Returns dict: ticker → {price, prev_close, change_pct, market_cap}
    Falls back to stored price if yfinance unavailable.
    """
    results = {}
    try:
        import yfinance as yf
        for ticker in tickers:
            try:
                t    = yf.Ticker(ticker)
                info = t.info
                curr = info.get("currentPrice") or info.get("regularMarketPrice")
                prev = info.get("previousClose") or info.get("regularMarketPreviousClose")
                mcap = info.get("marketCap")

                if curr is None:
                    results[ticker] = None
                    continue

                chg = round(((curr - prev) / prev) * 100, 2) if prev else 0.0
                results[ticker] = {
                    "price":      round(float(curr), 2),
                    "prev_close": round(float(prev), 2) if prev else None,
                    "change_pct": chg,
                    "market_cap": mcap,
                }
            except Exception:
                results[ticker] = None
    except ImportError:
        pass  # yfinance not installed — caller uses stored prices
    return results


# ── Calculations ──────────────────────────────────────────────────────────────

def compute_portfolio(data: dict, live_prices: dict | None = None) -> dict:
    """
    Main computation. Returns everything the dashboard needs.
    live_prices: ticker → {price, prev_close, change_pct} or None to use stored.
    """
    holdings = data["holdings"]
    cash     = float(data.get("cash", 0))

    owned     = [h for h in holdings if h["status"] == "Owned"]
    watchlist = [h for h in holdings if h["status"] == "Watchlist"]

    # ── Resolve current prices ────────────────────────────────────────────────
    positions = []
    for h in owned:
        ticker = h["ticker"]
        stored = h.get("current_price") or h["avg_buy"]

        if live_prices and live_prices.get(ticker):
            lp     = live_prices[ticker]
            curr   = lp["price"]
            prev   = lp.get("prev_close", stored)
            chg    = lp.get("change_pct", 0.0)
        else:
            curr = stored
            prev = stored
            chg  = 0.0

        shares   = h["shares"]
        avg_buy  = h["avg_buy"]
        mv       = round(shares * curr, 2)
        cb       = round(shares * avg_buy, 2)
        pl_amt   = round(mv - cb, 2)
        pl_pct   = round((pl_amt / cb) * 100, 2) if cb > 0 else 0.0

        positions.append({
            "ticker":      ticker,
            "name":        h["name"],
            "sector":      h["sector"],
            "style":       h["style"],
            "shares":      shares,
            "avg_buy":     avg_buy,
            "current":     curr,
            "prev_close":  prev,
            "change_pct":  chg,
            "mv":          mv,
            "cb":          cb,
            "pl_amt":      pl_amt,
            "pl_pct":      pl_pct,
        })

    # ── Totals ────────────────────────────────────────────────────────────────
    total_mv  = sum(p["mv"]  for p in positions)
    total_cb  = sum(p["cb"]  for p in positions)
    total_pl  = sum(p["pl_amt"] for p in positions)
    total_plp = round((total_pl / total_cb) * 100, 2) if total_cb > 0 else 0.0
    grand_total = total_mv + cash

    # ── Weights (vs grand total including cash) ───────────────────────────────
    for p in positions:
        p["weight_eq"]    = round(p["mv"] / total_mv   * 100, 2) if total_mv   else 0.0
        p["weight_total"] = round(p["mv"] / grand_total * 100, 2) if grand_total else 0.0

    cash_weight = round(cash / grand_total * 100, 2) if grand_total else 0.0
    eq_weight   = round(total_mv / grand_total * 100, 2) if grand_total else 0.0

    # ── Sector allocation ─────────────────────────────────────────────────────
    sector_mv: dict[str, float] = {}
    for p in positions:
        s = p["sector"]
        sector_mv[s] = sector_mv.get(s, 0) + p["mv"]

    sectors = [
        {
            "sector":  s,
            "value":   v,
            "weight":  round(v / grand_total * 100, 2),
            "color":   SECTOR_COLORS.get(s, SECTOR_COLORS["Other"]),
        }
        for s, v in sorted(sector_mv.items(), key=lambda x: -x[1])
    ]
    # Add cash as a pseudo-sector
    sectors.append({
        "sector": "Cash",
        "value":  cash,
        "weight": cash_weight,
        "color":  "#4B5563",
    })

    # ── Watchlist signals ─────────────────────────────────────────────────────
    wl_items = []
    for h in watchlist:
        ticker = h["ticker"]
        target = h.get("target_entry")

        if live_prices and live_prices.get(ticker):
            curr = live_prices[ticker]["price"]
            chg  = live_prices[ticker].get("change_pct", 0.0)
        else:
            curr = h.get("current_price")
            chg  = 0.0

        if target and curr:
            dist = round(((curr - target) / target) * 100, 2)
            if dist < 0:            sig = "Entry Zone"
            elif dist <= 5:         sig = "Near Entry"
            elif dist <= 10:        sig = "Above Target"
            else:                   sig = "Expensive"
        elif not target:
            sig  = "Review"
            dist = None
        else:
            sig  = "No Price"
            dist = None

        wl_items.append({
            "ticker":  ticker,
            "name":    h["name"],
            "sector":  h["sector"],
            "style":   h["style"],
            "current": curr,
            "target":  target,
            "dist":    dist,
            "signal":  sig,
            "change_pct": chg,
            "notes":   h.get("notes", ""),
        })

    # Sort: Entry Zone → Near Entry → Above Target → Expensive → Review
    sig_order = {"Entry Zone": 0, "Near Entry": 1, "Above Target": 2, "Expensive": 3, "Review": 4, "No Price": 5}
    wl_items.sort(key=lambda x: sig_order.get(x["signal"], 9))

    # ── Health score ──────────────────────────────────────────────────────────
    score = 50
    for p in positions:
        if p["pl_pct"] > 10 and p["style"] == "Compounder":
            score += 8
        elif p["pl_pct"] > 0:
            score += 4
        elif p["pl_pct"] < -10:
            score -= 6
        if p["weight_total"] > 35:
            score -= 5
        elif p["weight_total"] > 25:
            score -= 2

    tech_w = sum(p["weight_total"] for p in positions if "Technology" in p["sector"] or p["sector"] == "Enterprise Software")
    if tech_w > 50: score -= 8
    if len(positions) < 3: score -= 10
    if len(set(p["sector"] for p in positions)) < 2: score -= 8
    if cash_weight > 40: score -= 6
    elif cash_weight > 20: score -= 2
    entry_wl = sum(1 for w in wl_items if w["signal"] in ("Entry Zone", "Near Entry"))
    score += entry_wl * 2

    health = max(0, min(100, score))
    if health >= 80:   grade, hcolor = "Excellent", "#10B981"
    elif health >= 60: grade, hcolor = "Good",      "#3B82F6"
    elif health >= 40: grade, hcolor = "Average",   "#F59E0B"
    else:              grade, hcolor = "Weak",       "#EF4444"

    # ── Buy recommendations ───────────────────────────────────────────────────
    recommendations = _build_recommendations(
        cash=cash, positions=positions, wl_items=wl_items,
        grand_total=grand_total, tech_w=tech_w
    )

    # ── Alerts ────────────────────────────────────────────────────────────────
    alerts = []
    for p in positions:
        if p["change_pct"] < -5:
            alerts.append({"level": "CRITICAL", "ticker": p["ticker"],
                           "msg": f"Daily drop of {p['change_pct']:+.2f}%"})
        if p["pl_pct"] < -10:
            alerts.append({"level": "WARNING", "ticker": p["ticker"],
                           "msg": f"Down {p['pl_pct']:+.2f}% from avg buy price"})
        if p["weight_total"] > 35:
            alerts.append({"level": "WARNING", "ticker": p["ticker"],
                           "msg": f"Position weight {p['weight_total']:.1f}% exceeds 35%"})
        if p["pl_pct"] > 20:
            alerts.append({"level": "INFO", "ticker": p["ticker"],
                           "msg": f"Up {p['pl_pct']:+.2f}% — consider reviewing target"})

    return {
        "positions":       positions,
        "watchlist":       wl_items,
        "cash":            cash,
        "cash_weight":     cash_weight,
        "eq_weight":       eq_weight,
        "total_mv":        total_mv,
        "total_cb":        total_cb,
        "total_pl":        total_pl,
        "total_plp":       total_plp,
        "grand_total":     grand_total,
        "sectors":         sectors,
        "health":          health,
        "health_grade":    grade,
        "health_color":    hcolor,
        "alerts":          alerts,
        "recommendations": recommendations,
        "ts":              datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def _build_recommendations(cash, positions, wl_items, grand_total, tech_w):
    recs = []

    entry_opps = [w for w in wl_items if w["signal"] in ("Entry Zone", "Near Entry") and w["target"]]
    near_opps  = [w for w in wl_items if w["signal"] == "Near Entry"  and w["target"]]

    # Cash deployment
    if cash > 10_000:
        deploy = min(cash * 0.85, cash - 5000)
        recs.append({
            "priority": 1,
            "action":   "DEPLOY CASH",
            "detail":   f"${cash:,.0f} cash ({cash/grand_total*100:.0f}% of assets) is undeployed. "
                        f"Target ${deploy:,.0f} allocation across 3–4 new positions.",
            "color":    "#F59E0B",
            "icon":     "💰",
        })

    # Sector diversification
    if tech_w > 45:
        recs.append({
            "priority": 2,
            "action":   "DIVERSIFY SECTORS",
            "detail":   f"Technology + Software = {tech_w:.0f}% of total assets. "
                        f"Add Energy (XOM) and Industrials (CAT) to reduce sector concentration.",
            "color":    "#3B82F6",
            "icon":     "⚖️",
        })

    # Entry opportunities
    for w in entry_opps[:2]:
        dist_str = f"{w['dist']:+.1f}%" if w["dist"] is not None else "at target"
        recs.append({
            "priority": 3,
            "action":   f"ENTRY OPPORTUNITY — {w['ticker']}",
            "detail":   f"{w['name']} is {dist_str} vs your target of ${w['target']:,.2f}. "
                        f"Consider initiating a starter position.",
            "color":    "#10B981",
            "icon":     "🟢",
        })

    # Defensive position
    brkb = next((w for w in wl_items if w["ticker"] == "BRK.B"), None)
    if brkb:
        recs.append({
            "priority": 4,
            "action":   "ADD DEFENSIVE POSITION",
            "detail":   "BRK.B (Berkshire Hathaway) provides non-tech, value-oriented ballast. "
                        "Recommended allocation: 8–10% of total portfolio.",
            "color":    "#06B6D4",
            "icon":     "🛡️",
        })

    # Underperforming positions
    for p in positions:
        if p["pl_pct"] < -10:
            recs.append({
                "priority": 5,
                "action":   f"REVIEW — {p['ticker']}",
                "detail":   f"{p['name']} is down {p['pl_pct']:+.1f}%. Re-evaluate thesis. "
                            f"Average down if conviction remains high, or reassess exit.",
                "color":    "#EF4444",
                "icon":     "🔍",
            })

    recs.sort(key=lambda x: x["priority"])
    return recs[:5]
