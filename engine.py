"""
engine.py  -  Portfolio Intelligence
=====================================
Exports required by app.py:
  load_portfolio
  save_portfolio
  fetch_prices
  fetch_analysis
  compute_analysis
  compute_portfolio
  STYLE_ICONS
  RATING_STYLES
"""

import json
import math
import os
from datetime import datetime, timezone

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "portfolio.json")

SECTOR_COLORS = {
    "Technology":          "#3B82F6",
    "Enterprise Software": "#8B5CF6",
    "Industrials":         "#F59E0B",
    "Energy":              "#10B981",
    "Healthcare":          "#EC4899",
    "Consumer":            "#F97316",
    "Financial":           "#06B6D4",
    "EV / Technology":     "#6366F1",
    "Other":               "#6B7280",
}

STYLE_ICONS = {
    "Compounder":  "🔵",
    "Growth":      "🟣",
    "Cyclical":    "🟠",
    "Value":       "🟡",
    "Speculative": "🔴",
}

RATING_STYLES = {
    "Strong Buy": ("💎", "#10B981", "#052E16"),
    "Buy":        ("✅", "#4ADE80", "#052E16"),
    "Hold":       ("⏸️",  "#3B82F6", "#0A1520"),
    "Expensive":  ("⚠️",  "#F59E0B", "#1A1300"),
    "Avoid":      ("🚫", "#EF4444", "#1F0A0A"),
}


def load_portfolio():
    with open(DATA_PATH) as f:
        return json.load(f)


def save_portfolio(data):
    clean = json.loads(json.dumps(data))
    for h in clean.get("holdings", []):
        for k in ("current_price", "prev_close", "change_pct"):
            h.pop(k, None)
    with open(DATA_PATH, "w") as f:
        json.dump(clean, f, indent=2)


def fetch_prices(tickers):
    results = {t: None for t in tickers}
    if not tickers:
        return results
    try:
        import yfinance as yf
        for ticker in tickers:
            try:
                info = yf.Ticker(ticker).info
                curr = (info.get("currentPrice")
                        or info.get("regularMarketPrice")
                        or info.get("navPrice"))
                prev = (info.get("previousClose")
                        or info.get("regularMarketPreviousClose"))
                if curr is None:
                    continue
                curr = round(float(curr), 2)
                prev = round(float(prev), 2) if prev else curr
                chg  = round(((curr - prev) / prev) * 100, 2) if prev else 0.0
                results[ticker] = {
                    "price":      curr,
                    "prev_close": prev,
                    "change_pct": chg,
                    "market_cap": info.get("marketCap"),
                }
            except Exception:
                pass
    except ImportError:
        pass
    return results


def fetch_analysis(tickers):
    results = {t: {} for t in tickers}
    if not tickers:
        return results
    try:
        import yfinance as yf
        for ticker in tickers:
            try:
                info = yf.Ticker(ticker).info
                results[ticker] = {
                    "current_price":       info.get("currentPrice") or info.get("regularMarketPrice"),
                    "analyst_target":      info.get("targetMeanPrice"),
                    "analyst_low":         info.get("targetLowPrice"),
                    "analyst_high":        info.get("targetHighPrice"),
                    "analyst_count":       info.get("numberOfAnalystOpinions"),
                    "recommendation":      info.get("recommendationKey", ""),
                    "forward_pe":          info.get("forwardPE"),
                    "trailing_pe":         info.get("trailingPE"),
                    "peg_ratio":           info.get("pegRatio"),
                    "price_to_book":       info.get("priceToBook"),
                    "price_to_sales":      info.get("priceToSalesTrailing12Months"),
                    "ev_to_ebitda":        info.get("enterpriseToEbitda"),
                    "revenue_growth":      info.get("revenueGrowth"),
                    "earnings_growth":     info.get("earningsGrowth"),
                    "earnings_quarterly":  info.get("earningsQuarterlyGrowth"),
                    "profit_margin":       info.get("profitMargins"),
                    "gross_margin":        info.get("grossMargins"),
                    "operating_margin":    info.get("operatingMargins"),
                    "roe":                 info.get("returnOnEquity"),
                    "roa":                 info.get("returnOnAssets"),
                    "market_cap":          info.get("marketCap"),
                    "debt_to_equity":      info.get("debtToEquity"),
                    "current_ratio":       info.get("currentRatio"),
                    "free_cashflow":       info.get("freeCashflow"),
                    "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
                    "fifty_two_week_low":  info.get("fiftyTwoWeekLow"),
                    "beta":                info.get("beta"),
                    "dividend_yield":      info.get("dividendYield"),
                    "sector":              info.get("sector", ""),
                    "industry":            info.get("industry", ""),
                }
            except Exception:
                pass
    except ImportError:
        pass
    return results


def _safe(v, default=None):
    if v is None:
        return default
    try:
        f = float(v)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return default


def _fmt_mcap(v):
    if v is None:
        return "N/A"
    v = float(v)
    if v >= 1e12:
        return "$%.2fT" % (v / 1e12)
    if v >= 1e9:
        return "$%.1fB" % (v / 1e9)
    if v >= 1e6:
        return "$%.1fM" % (v / 1e6)
    return "$%d" % int(v)


def compute_analysis(tickers, raw, live_prices=None, holdings_map=None):
    results    = {}
    all_scores = []

    for ticker in tickers:
        info  = raw.get(ticker, {})
        lp    = (live_prices or {}).get(ticker) or {}
        hinfo = (holdings_map or {}).get(ticker, {})

        curr       = _safe(lp.get("price")) or _safe(info.get("current_price"))
        target     = _safe(info.get("analyst_target"))
        fpe        = _safe(info.get("forward_pe"))
        peg        = _safe(info.get("peg_ratio"))
        beta       = _safe(info.get("beta"), 1.0)
        d2e        = _safe(info.get("debt_to_equity"), 0.0)
        roe        = _safe(info.get("roe"), 0.0)
        rev_g      = _safe(info.get("revenue_growth"), 0.0)
        earn_g     = _safe(info.get("earnings_growth"), 0.0)
        pm         = _safe(info.get("profit_margin"), 0.0)
        cr         = _safe(info.get("current_ratio"), 1.0)
        mcap       = _safe(info.get("market_cap"))
        wk52h      = _safe(info.get("fifty_two_week_high"))
        wk52l      = _safe(info.get("fifty_two_week_low"))
        rec        = str(info.get("recommendation") or "").lower()
        n_analysts = _safe(info.get("analyst_count"), 0)

        fair_value = None
        if target:
            eps_fwd = (curr / fpe) if (curr and fpe and fpe > 0) else None
            if eps_fwd and eps_fwd > 0:
                fair_value = round(target * 0.60 + (15 * eps_fwd) * 0.40, 2)
            else:
                fair_value = round(target, 2)

        mos = None
        if fair_value and curr and curr > 0:
            mos = round((fair_value - curr) / fair_value * 100, 1)

        upside = None
        if target and curr and curr > 0:
            upside = round((target - curr) / curr * 100, 1)

        q = 5.0
        if pm  is not None: q += min(2.0, pm  * 10)
        if roe is not None: q += min(1.5, roe * 5)
        if rev_g  > 0.15:  q += 1.0
        elif rev_g > 0.05: q += 0.5
        if earn_g > 0.20:  q += 1.0
        elif earn_g > 0.08: q += 0.5
        if cr >= 1.5:       q += 0.5
        if d2e < 50:        q += 0.5
        elif d2e > 200:     q -= 1.0
        if n_analysts >= 10: q += 0.5
        quality = max(1, min(10, round(q, 1)))

        r = 5.0
        if beta is not None:
            if beta > 2.0:   r += 2.0
            elif beta > 1.5: r += 1.5
            elif beta > 1.2: r += 1.0
            elif beta < 0.8: r -= 0.5
        if d2e > 200:   r += 1.5
        elif d2e > 100: r += 0.5
        if cr < 1.0:    r += 1.0
        if pm is not None and pm < 0: r += 1.5
        if wk52h and wk52l and curr:
            rng = wk52h - wk52l
            if rng > 0 and ((curr - wk52l) / rng) < 0.15:
                r += 1.0
        style = hinfo.get("style", "")
        if style == "Speculative": r += 1.5
        elif style == "Growth":    r += 0.5
        elif style == "Value":     r -= 0.5
        risk = max(1, min(10, round(r, 1)))

        if rec in ("strong_buy", "strongbuy"):
            rating = "Strong Buy"
        elif mos is not None and mos >= 20 and quality >= 7:
            rating = "Strong Buy"
        elif mos is not None and mos >= 10 and quality >= 6:
            rating = "Buy"
        elif rec == "buy" and quality >= 5:
            rating = "Buy"
        elif mos is not None and mos < -15:
            rating = "Expensive"
        elif risk >= 8 or (mos is not None and mos < -25):
            rating = "Avoid"
        elif rec in ("sell", "underperform", "strongsell"):
            rating = "Avoid"
        else:
            rating = "Hold"

        icon, color, bg = RATING_STYLES.get(rating, ("--", "#94A3B8", "#0F1420"))

        result = {
            "ticker":          ticker,
            "name":            hinfo.get("name", ticker),
            "status":          hinfo.get("status", ""),
            "style":           hinfo.get("style", ""),
            "current":         curr,
            "analyst_target":  target,
            "analyst_low":     _safe(info.get("analyst_low")),
            "analyst_high":    _safe(info.get("analyst_high")),
            "analyst_count":   int(n_analysts) if n_analysts else None,
            "upside":          upside,
            "fair_value":      fair_value,
            "mos":             mos,
            "forward_pe":      fpe,
            "peg":             peg,
            "revenue_growth":  rev_g,
            "earnings_growth": earn_g,
            "profit_margin":   pm,
            "gross_margin":    _safe(info.get("gross_margin")),
            "roe":             roe,
            "beta":            beta,
            "market_cap":      _fmt_mcap(mcap),
            "market_cap_raw":  mcap,
            "debt_to_equity":  d2e,
            "dividend_yield":  _safe(info.get("dividend_yield")),
            "wk52_high":       wk52h,
            "wk52_low":        wk52l,
            "quality":         quality,
            "risk":            risk,
            "rating":          rating,
            "rating_icon":     icon,
            "rating_color":    color,
            "rating_bg":       bg,
            "has_data":        curr is not None,
        }
        results[ticker] = result
        if result["has_data"]:
            all_scores.append((quality, risk))

    if all_scores:
        avg_quality = round(sum(s[0] for s in all_scores) / len(all_scores), 1)
        avg_risk    = round(sum(s[1] for s in all_scores) / len(all_scores), 1)
    else:
        avg_quality = avg_risk = None

    buy_candidates = [
        r for r in results.values()
        if isinstance(r, dict)
        and r.get("rating") in ("Strong Buy", "Buy")
        and r.get("upside") is not None
    ]
    best_opp = max(buy_candidates, key=lambda x: x["upside"], default=None)

    results["__summary__"] = {
        "avg_quality":   avg_quality,
        "avg_risk":      avg_risk,
        "best_opp":      best_opp["ticker"] if best_opp else None,
        "best_opp_data": best_opp,
        "total_tickers": len(tickers),
        "rated":         sum(1 for r in results.values()
                             if isinstance(r, dict) and r.get("has_data")),
    }
    return results


def compute_portfolio(data, live_prices=None):
    holdings  = data["holdings"]
    cash      = float(data.get("cash", 0))
    owned     = [h for h in holdings if h["status"] == "Owned"]
    watchlist = [h for h in holdings if h["status"] == "Watchlist"]

    positions = []
    for h in owned:
        ticker  = h["ticker"]
        avg_buy = float(h["avg_buy"])
        shares  = float(h["shares"])
        lp      = (live_prices or {}).get(ticker)
        if lp:
            curr = lp["price"]
            prev = lp.get("prev_close", lp["price"])
            chg  = lp.get("change_pct", 0.0)
            live = True
        else:
            curr = prev = avg_buy
            chg  = 0.0
            live = False
        mv     = round(shares * curr,    2)
        cb     = round(shares * avg_buy, 2)
        pl     = round(mv - cb,          2)
        pl_pct = round(pl / cb * 100,    2) if cb else 0.0
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
        pos["weight_eq"]    = round(pos["mv"] / total_mv * 100, 2) if total_mv else 0.0
        pos["weight_total"] = round(pos["mv"] / grand    * 100, 2) if grand    else 0.0

    cash_w = round(cash     / grand * 100, 2) if grand else 0.0
    eq_w   = round(total_mv / grand * 100, 2) if grand else 0.0

    sector_mv = {}
    for pos in positions:
        sector_mv[pos["sector"]] = sector_mv.get(pos["sector"], 0) + pos["mv"]
    sectors = sorted([
        {"sector": s, "value": v,
         "weight": round(v / grand * 100, 2) if grand else 0.0,
         "color":  SECTOR_COLORS.get(s, SECTOR_COLORS["Other"])}
        for s, v in sector_mv.items()
    ], key=lambda x: -x["value"])
    sectors.append({"sector": "Cash", "value": cash,
                    "weight": cash_w, "color": "#4B5563"})

    sig_order = {"Entry Zone": 0, "Near Entry": 1, "Above Target": 2,
                 "Expensive":  3, "Review":     4, "No Price":     5}
    wl_items = []
    for h in watchlist:
        ticker = h["ticker"]
        target = h.get("target_entry")
        lp     = (live_prices or {}).get(ticker)
        curr   = lp["price"]           if lp else None
        chg    = lp.get("change_pct", 0.0) if lp else 0.0
        if target and curr:
            dist = round(((curr - target) / target) * 100, 2)
            sig  = ("Entry Zone"   if dist < 0  else
                    "Near Entry"   if dist <= 5  else
                    "Above Target" if dist <= 10 else "Expensive")
        elif not target:
            sig, dist = "Review", None
        else:
            sig, dist = "No Price", None
        wl_items.append({
            "ticker":     ticker,
            "name":       h["name"],
            "sector":     h["sector"],
            "style":      h["style"],
            "current":    curr,
            "target":     target,
            "dist":       dist,
            "signal":     sig,
            "change_pct": chg,
            "notes":      h.get("notes", ""),
            "live":       lp is not None,
        })
    wl_items.sort(key=lambda x: sig_order.get(x["signal"], 9))

    score = 50
    for pos in positions:
        if pos["pl_pct"] > 10 and pos["style"] == "Compounder": score += 8
        elif pos["pl_pct"] > 0:   score += 4
        elif pos["pl_pct"] < -10: score -= 6
        if pos["weight_total"] > 35:   score -= 5
        elif pos["weight_total"] > 25: score -= 2

    tech_w = sum(p["weight_total"] for p in positions
                 if "Technology" in p["sector"] or p["sector"] == "Enterprise Software")
    if tech_w > 50:                                    score -= 8
    if len(positions) < 3:                             score -= 10
    if len(set(p["sector"] for p in positions)) < 2:  score -= 8
    if cash_w > 40:   score -= 6
    elif cash_w > 20: score -= 2
    score += sum(2 for w in wl_items if w["signal"] in ("Entry Zone", "Near Entry"))
    health = max(0, min(100, score))

    if health >= 80:   grade, hcolor = "Excellent", "#10B981"
    elif health >= 60: grade, hcolor = "Good",      "#3B82F6"
    elif health >= 40: grade, hcolor = "Average",   "#F59E0B"
    else:              grade, hcolor = "Weak",       "#EF4444"

    alerts = []
    for pos in positions:
        if pos["change_pct"] < -5:
            alerts.append({"level": "CRITICAL", "ticker": pos["ticker"],
                           "msg": "Daily drop %+.2f%%" % pos["change_pct"]})
        if pos["pl_pct"] < -10:
            alerts.append({"level": "WARNING", "ticker": pos["ticker"],
                           "msg": "Down %+.2f%% from avg buy" % pos["pl_pct"]})
        if pos["weight_total"] > 35:
            alerts.append({"level": "WARNING", "ticker": pos["ticker"],
                           "msg": "Position weight %.1f%% > 35%%" % pos["weight_total"]})
        if pos["pl_pct"] > 20:
            alerts.append({"level": "INFO", "ticker": pos["ticker"],
                           "msg": "Up %+.2f%% - review target" % pos["pl_pct"]})

    any_live   = any(p["live"] for p in positions)
    price_note = "Live prices" if any_live else "Prices unavailable - showing cost basis"

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
    if cash > 10000:
        recs.append({"priority": 1, "icon": "💰", "color": "#F59E0B",
                     "action": "DEPLOY CASH",
                     "detail": "$%s cash (%d%% of assets) is undeployed. Target 3-4 new positions." % (
                         "{:,.0f}".format(cash), int(cash / grand * 100))})
    if tech_w > 45:
        recs.append({"priority": 2, "icon": "⚖️", "color": "#3B82F6",
                     "action": "DIVERSIFY SECTORS",
                     "detail": "Technology + Software = %d%% of total assets. Add Energy and Industrials." % int(tech_w)})
    for w in [x for x in wl_items if x["signal"] in ("Entry Zone", "Near Entry")][:2]:
        dist_s = "%+.1f%%" % w["dist"] if w["dist"] is not None else "at target"
        recs.append({"priority": 3, "icon": "🟢", "color": "#10B981",
                     "action": "ENTRY OPPORTUNITY - %s" % w["ticker"],
                     "detail": "%s is %s vs your target $%s. Consider a starter position." % (
                         w["name"], dist_s, "{:,.2f}".format(w["target"]))})
    recs.append({"priority": 4, "icon": "🛡️", "color": "#06B6D4",
                 "action": "ADD DEFENSIVE POSITION",
                 "detail": "BRK.B provides non-tech, value-oriented ballast. Suggested: 8-10% of portfolio."})
    for pos in positions:
        if pos["pl_pct"] < -10:
            recs.append({"priority": 5, "icon": "🔍", "color": "#EF4444",
                         "action": "REVIEW - %s" % pos["ticker"],
                         "detail": "%s down %+.1f%% from avg buy. Re-evaluate thesis." % (
                             pos["name"], pos["pl_pct"])})
    recs.sort(key=lambda x: x["priority"])
    return recs[:5]


# ---------------------------------------------------------------------------
# CAPITAL ALLOCATION ENGINE
# ---------------------------------------------------------------------------

def compute_allocation(data, live_prices=None, analysis=None):
    """
    Capital Allocation Engine.

    Inputs:
      data        - portfolio.json dict
      live_prices - output of fetch_prices()
      analysis    - output of compute_analysis() (optional, uses scores if present)

    Returns allocation dict with:
      available_cash, reserve_cash, deployable_cash,
      overall_mode, concentration_warnings,
      candidates (ranked list with dollar amounts),
      sector_headroom (how much more each sector can absorb)
    """

    holdings   = data["holdings"]
    cash       = float(data.get("cash", 0))
    grand      = float(sum(
        (float(h["shares"]) * ((live_prices or {}).get(h["ticker"], {}) or {}).get("price", float(h["avg_buy"])))
        for h in holdings if h["status"] == "Owned"
    ) + cash) or 1.0

    # Rules
    MAX_POSITION_PCT   = 25.0   # no single position > 25% of total
    MAX_SECTOR_PCT     = 40.0   # no sector > 40%
    MIN_CASH_RESERVE   = 0.15   # keep 15% as cash reserve

    reserve_cash    = round(grand * MIN_CASH_RESERVE, 2)
    deployable_cash = max(0.0, round(cash - reserve_cash, 2))

    # Current sector weights
    sector_mv = {}
    pos_weights = {}
    for h in holdings:
        if h["status"] != "Owned":
            continue
        lp    = (live_prices or {}).get(h["ticker"]) or {}
        price = lp.get("price") or float(h["avg_buy"])
        mv    = float(h["shares"]) * price
        sec   = h["sector"]
        sector_mv[sec]        = sector_mv.get(sec, 0) + mv
        pos_weights[h["ticker"]] = round(mv / grand * 100, 2)

    sector_weights = {s: round(v / grand * 100, 2) for s, v in sector_mv.items()}

    # Sector headroom (how much $ more before hitting 40% cap)
    sector_headroom = {}
    for sec, w in sector_weights.items():
        room_pct = max(0.0, MAX_SECTOR_PCT - w)
        sector_headroom[sec] = round(room_pct / 100 * grand, 2)

    # Concentration warnings
    warnings = []
    for ticker, w in pos_weights.items():
        if w > MAX_POSITION_PCT:
            warnings.append({
                "type": "position",
                "msg":  "%s is %.1f%% of portfolio (max %.0f%%)" % (ticker, w, MAX_POSITION_PCT),
                "icon": "⚠️",
            })
    for sec, w in sector_weights.items():
        if w > MAX_SECTOR_PCT:
            warnings.append({
                "type": "sector",
                "msg":  "%s sector is %.1f%% of portfolio (max %.0f%%)" % (sec, w, MAX_SECTOR_PCT),
                "icon": "⚠️",
            })
    cash_pct = cash / grand * 100
    if cash_pct < MIN_CASH_RESERVE * 100:
        warnings.append({
            "type": "cash",
            "msg":  "Cash %.1f%% is below %.0f%% minimum reserve" % (cash_pct, MIN_CASH_RESERVE * 100),
            "icon": "⚠️",
        })

    # Build candidate list from all holdings
    candidates_raw = []
    an = analysis or {}

    for h in holdings:
        ticker = h["ticker"]
        status = h["status"]
        a      = an.get(ticker, {})
        if not isinstance(a, dict):
            continue

        quality  = a.get("quality")
        risk     = a.get("risk")
        mos      = a.get("mos")
        upside   = a.get("upside")
        rating   = a.get("rating", "Hold")

        # Skip Avoid-rated or ones with no data
        if rating == "Avoid":
            continue
        if quality is None and upside is None:
            continue

        # Allocation Score (0-100)
        q_score  = ((quality or 5) / 10) * 40          # 40% weight
        mos_norm = min(max((mos or 0) + 30, 0), 60)     # map -30..+30 → 0..60
        m_score  = (mos_norm / 60) * 25                 # 25% weight
        up_norm  = min(max((upside or 0), 0), 50)       # cap at 50% upside
        u_score  = (up_norm / 50) * 20                  # 20% weight
        r_inv    = (10 - (risk or 5)) / 9               # invert risk: low risk = high score
        r_score  = r_inv * 15                            # 15% weight

        alloc_score = round(q_score + m_score + u_score + r_score, 1)

        # Position headroom: how much more can go into this stock
        curr_w   = pos_weights.get(ticker, 0.0)
        room_pct = max(0.0, MAX_POSITION_PCT - curr_w)
        max_add  = round(room_pct / 100 * grand, 2)

        # Sector headroom
        sec        = h["sector"]
        sec_room   = sector_headroom.get(sec, grand * MAX_SECTOR_PCT / 100)

        # Effective max = min of position headroom and sector headroom
        effective_max = min(max_add, sec_room)

        # Owned positions get priority boost
        priority_boost = 5 if status == "Owned" else 0
        # Strong Buy gets extra boost
        if rating == "Strong Buy": priority_boost += 8
        elif rating == "Buy":      priority_boost += 4

        final_score = min(100, alloc_score + priority_boost)

        candidates_raw.append({
            "ticker":       ticker,
            "name":         h.get("name", ticker),
            "sector":       sec,
            "status":       status,
            "style":        h.get("style", ""),
            "rating":       rating,
            "alloc_score":  final_score,
            "quality":      quality,
            "risk":         risk,
            "mos":          mos,
            "upside":       upside,
            "current_w":    curr_w,
            "max_add":      effective_max,
        })

    # Sort by allocation score descending
    candidates_raw.sort(key=lambda x: -x["alloc_score"])

    # Distribute deployable cash proportionally (top 5 candidates)
    top5 = [c for c in candidates_raw if c["max_add"] > 0][:5]
    total_score = sum(c["alloc_score"] for c in top5) or 1.0
    cash_left   = deployable_cash

    candidates = []
    for c in top5:
        proportion  = c["alloc_score"] / total_score
        raw_amount  = round(deployable_cash * proportion, -2)   # round to $100
        amount      = min(raw_amount, c["max_add"], cash_left)
        amount      = max(0.0, round(amount / 100) * 100)       # snap to $100
        cash_left   = max(0.0, cash_left - amount)
        if amount >= 100:
            candidates.append({**c, "suggested_amount": amount})

    # Overall mode
    avg_score = sum(c["alloc_score"] for c in candidates_raw[:5]) / max(len(candidates_raw[:5]), 1)
    n_buys    = sum(1 for c in candidates_raw if c["rating"] in ("Strong Buy", "Buy"))

    if deployable_cash < 1000:
        mode = "Hold Cash"
        mode_color = "#6B7280"
        mode_icon  = "🏦"
        mode_desc  = "Insufficient deployable cash after reserve. Build cash position first."
    elif avg_score >= 70 and n_buys >= 2:
        mode = "Aggressive Buy"
        mode_color = "#10B981"
        mode_icon  = "🚀"
        mode_desc  = "Multiple high-scoring opportunities with strong analyst backing. Deploy capital actively."
    elif avg_score >= 55 and n_buys >= 1:
        mode = "Selective Buying"
        mode_color = "#3B82F6"
        mode_icon  = "✅"
        mode_desc  = "Good opportunities exist but be selective. Focus on top 2-3 highest-scored candidates."
    elif len(warnings) >= 2:
        mode = "Defensive Mode"
        mode_color = "#EF4444"
        mode_icon  = "🛡️"
        mode_desc  = "Portfolio has concentration risk or low cash. Prioritise rebalancing over new positions."
    else:
        mode = "Hold Cash"
        mode_color = "#F59E0B"
        mode_icon  = "⏸️"
        mode_desc  = "No compelling entry points at current prices. Preserve cash and wait for better levels."

    return {
        "available_cash":         cash,
        "reserve_cash":           reserve_cash,
        "deployable_cash":        deployable_cash,
        "cash_pct":               round(cash_pct, 1),
        "grand_total":            grand,
        "overall_mode":           mode,
        "mode_color":             mode_color,
        "mode_icon":              mode_icon,
        "mode_desc":              mode_desc,
        "concentration_warnings": warnings,
        "candidates":             candidates,
        "all_candidates":         candidates_raw,
        "sector_weights":         sector_weights,
        "sector_headroom":        sector_headroom,
        "pos_weights":            pos_weights,
    }
