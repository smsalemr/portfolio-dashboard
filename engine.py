"""
engine.py
=========
Calculation logic + live price fetching via yfinance.
Prices are fetched automatically on every dashboard load.
portfolio.json stores NO current_price — all prices are live.
"""

from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from typing import Optional

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "portfolio.json")

SECTOR_COLORS = {
    "Technology":         "#3B82F6",
    "Enterprise Software":"#8B5CF6",
    "Industrials":        "#F59E0B",
    "Energy":             "#10B981",
    "Healthcare":         "#EC4899",
    "Consumer":           "#F97316",
    "Financial":          "#06B6D4",
    "EV / Technology":    "#6366F1",
    "Other":              "#6B7280",
}

STYLE_ICONS = {
    "Compounder":  "🔵",
    "Growth":      "🟣",
    "Cyclical":    "🟠",
    "Value":       "🟡",
    "Speculative": "🔴",
}


# ── Data I/O ──────────────────────────────────────────────────────────────────

def load_portfolio() -> dict:
    with open(DATA_PATH, "r") as f:
        return json.load(f)


def save_portfolio(data: dict):
    # Never write current_price back to disk
    clean = json.loads(json.dumps(data))
    for h in clean.get("holdings", []):
        h.pop("current_price", None)
        h.pop("prev_close", None)
        h.pop("change_pct", None)
    with open(DATA_PATH, "w") as f:
        json.dump(clean, f, indent=2)


# ── Live price fetch ──────────────────────────────────────────────────────────

def fetch_prices(tickers: list[str]) -> dict[str, Optional[dict]]:
    """
    Fetch live prices for a list of tickers via yfinance.
    Returns: {ticker: {price, prev_close, change_pct, market_cap}} or {ticker: None}
    Never raises — bad tickers return None silently.
    """
    results: dict[str, Optional[dict]] = {t: None for t in tickers}
    if not tickers:
        return results
    try:
        import yfinance as yf
        for ticker in tickers:
            try:
                info  = yf.Ticker(ticker).info
                curr  = (info.get("currentPrice")
                         or info.get("regularMarketPrice")
                         or info.get("navPrice"))
                prev  = (info.get("previousClose")
                         or info.get("regularMarketPreviousClose"))
                mcap  = info.get("marketCap")
                if curr is None:
                    continue
                curr = round(float(curr), 2)
                prev = round(float(prev), 2) if prev else curr
                chg  = round(((curr - prev) / prev) * 100, 2) if prev else 0.0
                results[ticker] = {
                    "price":      curr,
                    "prev_close": prev,
                    "change_pct": chg,
                    "market_cap": mcap,
                }
            except Exception:
                pass   # leave as None — dashboard shows stored fallback
    except ImportError:
        pass  # yfinance not installed
    return results


# ── Main computation ──────────────────────────────────────────────────────────

def compute_portfolio(data: dict, live_prices: dict | None = None) -> dict:
    """
    Compute all dashboard metrics.
    live_prices: output of fetch_prices(). If None, uses avg_buy as price fallback.
    """
    holdings  = data["holdings"]
    cash      = float(data.get("cash", 0))
    owned     = [h for h in holdings if h["status"] == "Owned"]
    watchlist = [h for h in holdings if h["status"] == "Watchlist"]

    # ── Owned positions ───────────────────────────────────────────────────────
    positions = []
    for h in owned:
        ticker  = h["ticker"]
        avg_buy = float(h["avg_buy"])
        shares  = float(h["shares"])

        lp = (live_prices or {}).get(ticker)
        if lp:
            curr = lp["price"]
            prev = lp.get("prev_close", curr)
            chg  = lp.get("change_pct", 0.0)
            live = True
        else:
            curr = avg_buy   # neutral fallback — no P/L distortion
            prev = avg_buy
            chg  = 0.0
            live = False

        mv    = round(shares * curr,    2)
        cb    = round(shares * avg_buy, 2)
        pl    = round(mv - cb,          2)
        pl_pct= round(pl / cb * 100,    2) if cb else 0.0

        positions.append({
            "ticker":     ticker,
            "name":       h["name"],
            "sector":     h["sector"],
            "style":      h["style"],
            "shares":     int(shares),
            "avg_buy":    avg_buy,
            "current":    curr,
            "prev_close": prev,
            "change_pct": chg,
            "mv":         mv,
            "cb":         cb,
            "pl_amt":     pl,
            "pl_pct":     pl_pct,
            "live":       live,
        })

    total_mv  = sum(p["mv"]     for p in positions)
    total_cb  = sum(p["cb"]     for p in positions)
    total_pl  = sum(p["pl_amt"] for p in positions)
    total_plp = round(total_pl / total_cb * 100, 2) if total_cb else 0.0
    grand     = round(total_mv + cash, 2)

    for pos in positions:
        pos["weight_eq"]    = round(pos["mv"] / total_mv * 100,  2) if total_mv else 0.0
        pos["weight_total"] = round(pos["mv"] / grand    * 100,  2) if grand    else 0.0

    cash_w = round(cash    / grand * 100, 2) if grand else 0.0
    eq_w   = round(total_mv / grand * 100, 2) if grand else 0.0

    # ── Sectors (incl. cash) ──────────────────────────────────────────────────
    sector_mv: dict[str, float] = {}
    for pos in positions:
        s = pos["sector"]
        sector_mv[s] = sector_mv.get(s, 0) + pos["mv"]

    sectors = sorted([
        {"sector": s, "value": v,
         "weight": round(v / grand * 100, 2) if grand else 0.0,
         "color":  SECTOR_COLORS.get(s, SECTOR_COLORS["Other"])}
        for s, v in sector_mv.items()
    ], key=lambda x: -x["value"])
    sectors.append({"sector": "Cash", "value": cash,
                    "weight": cash_w, "color": "#4B5563"})

    # ── Watchlist ─────────────────────────────────────────────────────────────
    wl_items = []
    sig_order = {"Entry Zone": 0, "Near Entry": 1, "Above Target": 2,
                 "Expensive": 3, "Review": 4, "No Price": 5}

    for h in watchlist:
        ticker = h["ticker"]
        target = h.get("target_entry")
        lp     = (live_prices or {}).get(ticker)
        curr   = lp["price"]      if lp else None
        chg    = lp.get("change_pct", 0.0) if lp else 0.0

        if target and curr:
            dist = round(((curr - target) / target) * 100, 2)
            sig  = ("Entry Zone"   if dist < 0   else
                    "Near Entry"   if dist <= 5   else
                    "Above Target" if dist <= 10  else "Expensive")
        elif not target:
            sig, dist = "Review", None
        else:
            sig, dist = "No Price", None

        wl_items.append({
            "ticker": ticker, "name": h["name"],
            "sector": h["sector"], "style": h["style"],
            "current": curr, "target": target,
            "dist": dist, "signal": sig,
            "change_pct": chg, "notes": h.get("notes", ""),
            "live": lp is not None,
        })

    wl_items.sort(key=lambda x: sig_order.get(x["signal"], 9))

    # ── Health score ──────────────────────────────────────────────────────────
    score = 50
    for pos in positions:
        if pos["pl_pct"] > 10 and pos["style"] == "Compounder": score += 8
        elif pos["pl_pct"] > 0:  score += 4
        elif pos["pl_pct"] < -10: score -= 6
        if pos["weight_total"] > 35: score -= 5
        elif pos["weight_total"] > 25: score -= 2
    tech_w = sum(p["weight_total"] for p in positions
                 if "Technology" in p["sector"] or p["sector"] == "Enterprise Software")
    if tech_w > 50: score -= 8
    if len(positions) < 3: score -= 10
    if len(set(p["sector"] for p in positions)) < 2: score -= 8
    if cash_w > 40: score -= 6
    elif cash_w > 20: score -= 2
    score += sum(2 for w in wl_items if w["signal"] in ("Entry Zone", "Near Entry"))
    health = max(0, min(100, score))

    if health >= 80:   grade, hcolor = "Excellent", "#10B981"
    elif health >= 60: grade, hcolor = "Good",      "#3B82F6"
    elif health >= 40: grade, hcolor = "Average",   "#F59E0B"
    else:              grade, hcolor = "Weak",       "#EF4444"

    # ── Alerts ────────────────────────────────────────────────────────────────
    alerts = []
    for pos in positions:
        if pos["change_pct"] < -5:
            alerts.append({"level": "CRITICAL", "ticker": pos["ticker"],
                           "msg": f"Daily drop {pos['change_pct']:+.2f}%"})
        if pos["pl_pct"] < -10:
            alerts.append({"level": "WARNING", "ticker": pos["ticker"],
                           "msg": f"Down {pos['pl_pct']:+.2f}% from avg buy"})
        if pos["weight_total"] > 35:
            alerts.append({"level": "WARNING", "ticker": pos["ticker"],
                           "msg": f"Position weight {pos['weight_total']:.1f}% > 35%"})
        if pos["pl_pct"] > 20:
            alerts.append({"level": "INFO", "ticker": pos["ticker"],
                           "msg": f"Up {pos['pl_pct']:+.2f}% — review target"})

    # ── Price status ──────────────────────────────────────────────────────────
    any_live   = any(p["live"] for p in positions)
    price_note = "Live prices" if any_live else "Prices unavailable — showing cost basis"

    return {
        "positions":    positions,
        "watchlist":    wl_items,
        "cash":         cash,
        "cash_weight":  cash_w,
        "eq_weight":    eq_w,
        "total_mv":     total_mv,
        "total_cb":     total_cb,
        "total_pl":     total_pl,
        "total_plp":    total_plp,
        "grand_total":  grand,
        "sectors":      sectors,
        "health":       health,
        "health_grade": grade,
        "health_color": hcolor,
        "alerts":       alerts,
        "recommendations": _build_recommendations(cash, positions, wl_items, grand, tech_w),
        "price_note":   price_note,
        "any_live":     any_live,
        "ts":           datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def _build_recommendations(cash, positions, wl_items, grand, tech_w):
    recs = []
    if cash > 10_000:
        recs.append({
            "priority": 1, "icon": "💰", "color": "#F59E0B",
            "action": "DEPLOY CASH",
            "detail": (f"${cash:,.0f} cash ({cash/grand*100:.0f}% of assets) is undeployed. "
                       f"Target deployment across 3–4 new positions to improve diversification."),
        })
    if tech_w > 45:
        recs.append({
            "priority": 2, "icon": "⚖️", "color": "#3B82F6",
            "action": "DIVERSIFY SECTORS",
            "detail": (f"Technology + Software = {tech_w:.0f}% of total assets. "
                       f"Add Energy (XOM) and Industrials (CAT) to reduce concentration."),
        })
    for w in [x for x in wl_items if x["signal"] in ("Entry Zone", "Near Entry")][:2]:
        dist_s = f"{w['dist']:+.1f}%" if w["dist"] is not None else "at target"
        recs.append({
            "priority": 3, "icon": "🟢", "color": "#10B981",
            "action": f"ENTRY OPPORTUNITY — {w['ticker']}",
            "detail": f"{w['name']} is {dist_s} vs your target ${w['target']:,.2f}. Consider a starter position.",
        })
    recs.append({
        "priority": 4, "icon": "🛡️", "color": "#06B6D4",
        "action": "ADD DEFENSIVE POSITION",
        "detail": "BRK.B provides non-tech, value-oriented ballast. Suggested allocation: 8–10% of total portfolio.",
    })
    for pos in positions:
        if pos["pl_pct"] < -10:
            recs.append({
                "priority": 5, "icon": "🔍", "color": "#EF4444",
                "action": f"REVIEW — {pos['ticker']}",
                "detail": (f"{pos['name']} down {pos['pl_pct']:+.1f}% from avg buy. "
                           f"Re-evaluate thesis or consider averaging down."),
            })
    recs.sort(key=lambda x: x["priority"])
    return recs[:5]
