"""
app.py — Portfolio Intelligence Dashboard
==========================================
Streamlit Cloud deployment with:
  - Password protection
  - Mobile-first responsive layout
  - Live yfinance price refresh
  - Full portfolio CRUD via Update tab

Deploy: streamlit run app.py
Cloud:  share.streamlit.io
"""

import streamlit as st
import plotly.graph_objects as go
import json, os
from datetime import datetime, timezone
from engine import load_portfolio, save_portfolio, fetch_prices, compute_portfolio, STYLE_ICONS

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Portfolio Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Password gate ─────────────────────────────────────────────────────────────
def check_password() -> bool:
    """Return True if user has entered the correct password."""
    # Read password from Streamlit Cloud secrets (or fall back to env var)
    try:
        correct = st.secrets["PASSWORD"]
    except Exception:
        correct = os.environ.get("DASHBOARD_PASSWORD", "portfolio2025")

    if st.session_state.get("authenticated"):
        return True

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Mono:wght@400;500&display=swap');
    html,body,[class*="css"]{background:#080B12!important;color:#E2E8F0!important;}
    .stApp{background:#080B12;}
    .block-container{max-width:400px;margin:auto;padding-top:15vh;}
    div[data-testid="stTextInput"] input{
      background:#0F1420!important;border:1px solid #1E2433!important;
      color:#E2E8F0!important;border-radius:10px!important;
      font-family:'DM Mono',monospace!important;font-size:1rem!important;
      padding:0.6rem 1rem!important;
    }
    div[data-testid="stButton"]>button{
      background:linear-gradient(135deg,#1D4ED8,#1E40AF);
      color:white;border:none;border-radius:10px;
      font-family:'DM Mono',monospace;font-size:0.85rem;
      padding:0.6rem 2rem;width:100%;margin-top:0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(
        "<h2 style='font-family:DM Serif Display,serif;text-align:center;"
        "color:#F1F5F9;margin-bottom:0.3rem;'>Portfolio Intelligence</h2>"
        "<p style='font-family:DM Mono,monospace;font-size:0.7rem;letter-spacing:.15em;"
        "text-transform:uppercase;color:#475569;text-align:center;margin-bottom:2rem;'>"
        "Private Dashboard</p>",
        unsafe_allow_html=True,
    )

    pwd = st.text_input("Password", type="password", placeholder="Enter password…", label_visibility="collapsed")
    if st.button("Unlock"):
        if pwd == correct:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False


if not check_password():
    st.stop()


# ── CSS — mobile-first ────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500;600&display=swap');

html,body,[class*="css"]{
  font-family:'DM Sans',sans-serif;
  background:#080B12!important;
  color:#E2E8F0!important;
}
.stApp{background:#080B12;}
.block-container{padding:1rem 1rem 5rem;max-width:1400px;}
#MainMenu,footer,header,.stDeployButton{visibility:hidden;}

/* ── Mobile viewport fix ── */
@media(max-width:768px){
  .block-container{padding:0.75rem 0.75rem 5rem;}
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"]{
  background:#0F1420;border-radius:12px;padding:4px;gap:2px;
  border:1px solid #1E2433;overflow-x:auto;flex-wrap:nowrap;
}
.stTabs [data-baseweb="tab"]{
  background:transparent;color:#64748B;
  font-family:'DM Mono',monospace;font-size:0.68rem;
  letter-spacing:0.07em;text-transform:uppercase;
  border-radius:8px;padding:0.45rem 0.9rem;border:none;
  white-space:nowrap;
}
.stTabs [aria-selected="true"]{
  background:#1E2D4A!important;color:#60A5FA!important;
}

/* ── Metric cards ── */
div[data-testid="metric-container"]{
  background:#0F1420;border:1px solid #1E2433;
  border-radius:12px;padding:0.9rem 1rem;
}
div[data-testid="metric-container"] label{
  font-family:'DM Mono',monospace!important;
  font-size:0.58rem!important;letter-spacing:.13em!important;
  text-transform:uppercase!important;color:#475569!important;
}
div[data-testid="metric-container"] [data-testid="stMetricValue"]{
  font-family:'DM Serif Display',serif!important;
  font-size:1.35rem!important;color:#F1F5F9!important;
}
div[data-testid="metric-container"] [data-testid="stMetricDelta"]{
  font-family:'DM Mono',monospace!important;font-size:0.72rem!important;
}

/* ── Section header ── */
.sec-hdr{
  font-family:'DM Mono',monospace;font-size:0.6rem;
  letter-spacing:.2em;text-transform:uppercase;color:#3B82F6;
  border-left:3px solid #3B82F6;padding-left:.65rem;margin:1.4rem 0 .8rem;
}

/* ── Cards ── */
.card{
  background:#0F1420;border:1px solid #1E2433;
  border-radius:12px;padding:1rem 1.1rem;margin-bottom:.5rem;
}

/* ── Signal badges ── */
.sig-entry {background:#052E16;color:#4ADE80;border:1px solid #166534;border-radius:20px;padding:2px 10px;font-size:0.7rem;font-weight:600;}
.sig-near  {background:#1C1500;color:#FCD34D;border:1px solid #92400E;border-radius:20px;padding:2px 10px;font-size:0.7rem;font-weight:600;}
.sig-above {background:#1A0E00;color:#FB923C;border:1px solid #9A3412;border-radius:20px;padding:2px 10px;font-size:0.7rem;font-weight:600;}
.sig-exp   {background:#1F0A0A;color:#F87171;border:1px solid #7F1D1D;border-radius:20px;padding:2px 10px;font-size:0.7rem;font-weight:600;}
.sig-review{background:#111827;color:#94A3B8;border:1px solid #374151;border-radius:20px;padding:2px 10px;font-size:0.7rem;font-weight:600;}

/* ── Alerts ── */
.alert-crit{background:#1F0A0A;border:1px solid #7F1D1D;border-left:4px solid #EF4444;border-radius:10px;padding:.65rem .9rem;margin-bottom:.35rem;font-family:'DM Mono',monospace;font-size:0.76rem;}
.alert-warn{background:#1A1300;border:1px solid #78350F;border-left:4px solid #F59E0B;border-radius:10px;padding:.65rem .9rem;margin-bottom:.35rem;font-family:'DM Mono',monospace;font-size:0.76rem;}
.alert-info{background:#0A1520;border:1px solid #1E3A5F;border-left:4px solid #3B82F6;border-radius:10px;padding:.65rem .9rem;margin-bottom:.35rem;font-family:'DM Mono',monospace;font-size:0.76rem;}

/* ── Colors ── */
.green{color:#4ADE80;}.red{color:#F87171;}.blue{color:#60A5FA;}
.mono-sm{font-family:'DM Mono',monospace;font-size:0.72rem;color:#64748B;}
.mono-val{font-family:'DM Mono',monospace;font-size:0.85rem;color:#CBD5E1;}
.ticker-big{font-family:'DM Serif Display',serif;font-size:1.2rem;color:#F1F5F9;}

/* ── Rec cards ── */
.rec-card{background:#0F1420;border:1px solid #1E2433;border-radius:12px;padding:.9rem 1.1rem;margin-bottom:.5rem;}

/* ── Divider ── */
.divider{border:none;border-top:1px solid #1E2433;margin:1rem 0;}
.ts{font-family:'DM Mono',monospace;font-size:0.6rem;color:#2D3A52;}

/* ── Buttons ── */
div[data-testid="stButton"]>button{
  background:linear-gradient(135deg,#1D4ED8,#1E40AF);
  color:white;border:none;border-radius:8px;
  font-family:'DM Sans',sans-serif;font-size:0.8rem;font-weight:600;
  padding:.42rem 1.2rem;transition:all .18s;
}

/* ── Inputs ── */
div[data-testid="stNumberInput"] input,
div[data-testid="stTextInput"] input{
  background:#0F1420!important;border:1px solid #1E2433!important;
  color:#E2E8F0!important;border-radius:8px!important;
  font-family:'DM Mono',monospace!important;
}

/* ── Mobile: stack metrics 2-wide ── */
@media(max-width:600px){
  div[data-testid="metric-container"] [data-testid="stMetricValue"]{
    font-size:1.1rem!important;
  }
}
</style>
""", unsafe_allow_html=True)


# ── Session state & data ──────────────────────────────────────────────────────

def refresh_computed(portfolio_data=None):
    data = portfolio_data or st.session_state.portfolio
    st.session_state.computed = compute_portfolio(data)

if "portfolio" not in st.session_state:
    st.session_state.portfolio = load_portfolio()
if "computed" not in st.session_state:
    refresh_computed()

d = st.session_state.computed
p = st.session_state.portfolio


# ── Helpers ───────────────────────────────────────────────────────────────────

def sig_badge(sig):
    cls  = {"Entry Zone":"sig-entry","Near Entry":"sig-near","Above Target":"sig-above",
             "Expensive":"sig-exp","Review":"sig-review"}.get(sig,"sig-review")
    icon = {"Entry Zone":"🟢","Near Entry":"🟡","Above Target":"🟠",
             "Expensive":"🔴","Review":"⚪"}.get(sig,"")
    return f"<span class='{cls}'>{icon} {sig}</span>"

def fmt_usd(v, d=2):
    return "N/A" if v is None else f"${v:,.{d}f}"

def fmt_pct(v):
    if v is None: return "N/A"
    return f"{'+' if v>=0 else ''}{v:.2f}%"

def cpct(v):
    if v is None: return "—"
    c = "green" if v >= 0 else "red"
    return f"<span class='{c}'>{fmt_pct(v)}</span>"


# ── Header ────────────────────────────────────────────────────────────────────
h1, h2, h3 = st.columns([3, 2, 1])
with h1:
    st.markdown("<h1 style='font-family:DM Serif Display,serif;font-size:1.6rem;"
                "font-weight:400;color:#F1F5F9;margin:0;'>Portfolio Intelligence</h1>",
                unsafe_allow_html=True)
with h2:
    st.markdown(f"<div class='ts' style='padding-top:12px;'>{d['ts']}</div>", unsafe_allow_html=True)
with h3:
    if st.button("⟳"):
        with st.spinner("Fetching prices…"):
            tickers = [h["ticker"] for h in p["holdings"]]
            live    = fetch_prices(tickers)
            if live:
                st.session_state.computed = compute_portfolio(p, live)
                d = st.session_state.computed
        st.rerun()

st.markdown("<hr class='divider'>", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tabs = st.tabs(["📊 Overview", "📈 Holdings", "🔭 Watchlist", "💡 Recs", "✏️ Update"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tabs[0]:

    # Mobile: 2 columns × 3 rows of metrics
    r1c1, r1c2 = st.columns(2)
    r1c1.metric("Total Assets",  fmt_usd(d["grand_total"], 0))
    r1c2.metric("Cash",          fmt_usd(d["cash"], 0),       f"{d['cash_weight']:.1f}% of assets")

    r2c1, r2c2 = st.columns(2)
    r2c1.metric("Invested",      fmt_usd(d["total_mv"], 0),   f"{d['eq_weight']:.1f}% of assets")
    dc = "normal" if d["total_plp"] >= 0 else "inverse"
    r2c2.metric("Total P/L",     fmt_usd(d["total_pl"], 0),   fmt_pct(d["total_plp"]), delta_color=dc)

    r3c1, r3c2 = st.columns(2)
    r3c1.metric("Health Score",  f"{d['health']}/100 — {d['health_grade']}")
    r3c2.metric("Positions",     str(len(d["positions"])))

    st.markdown("<div class='sec-hdr'>Sector Allocation</div>", unsafe_allow_html=True)

    # Donut chart — compact for mobile
    sec_labels = [s["sector"] for s in d["sectors"]]
    sec_values = [s["value"]  for s in d["sectors"]]
    sec_colors = [s["color"]  for s in d["sectors"]]

    fig = go.Figure(go.Pie(
        labels=sec_labels, values=sec_values, hole=0.55,
        marker=dict(colors=sec_colors, line=dict(color="#080B12", width=2)),
        textinfo="percent+label",
        textfont=dict(family="DM Mono", size=9, color="#E2E8F0"),
        hovertemplate="<b>%{label}</b><br>%{value:$,.0f} · %{percent}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False, height=270,
        margin=dict(t=10, b=10, l=5, r=5),
        annotations=[dict(
            text=f"<b>{fmt_usd(d['grand_total'],0)}</b>",
            x=0.5, y=0.5, showarrow=False,
            font=dict(family="DM Serif Display", size=13, color="#F1F5F9"),
        )],
    )
    st.plotly_chart(fig, use_container_width=True)

    # Sector rows
    for s in d["sectors"]:
        st.markdown(
            f"<div class='card' style='padding:.6rem 1rem;margin-bottom:.3rem;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
            f"<span style='display:flex;align-items:center;gap:8px;font-size:.85rem;color:#CBD5E1;'>"
            f"<span style='width:9px;height:9px;border-radius:2px;background:{s['color']};display:inline-block;'></span>"
            f"{s['sector']}</span>"
            f"<span class='mono-val'>{fmt_usd(s['value'],0)} &nbsp; <b>{s['weight']:.1f}%</b></span>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

    if d["alerts"]:
        st.markdown("<div class='sec-hdr'>Alerts</div>", unsafe_allow_html=True)
        for a in d["alerts"]:
            cls = {"CRITICAL":"alert-crit","WARNING":"alert-warn","INFO":"alert-info"}[a["level"]]
            ico = {"CRITICAL":"🚨","WARNING":"⚠️","INFO":"ℹ️"}[a["level"]]
            st.markdown(f"<div class='{cls}'>{ico} <b>{a['ticker']}</b> — {a['msg']}</div>",
                        unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — HOLDINGS
# ══════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    if not d["positions"]:
        st.info("No owned positions yet.")
    else:
        for pos in d["positions"]:
            pl_c  = "green" if pos["pl_pct"] >= 0 else "red"
            chg_c = "green" if pos["change_pct"] >= 0 else "red"
            si    = STYLE_ICONS.get(pos["style"], "")
            st.markdown(
                f"<div class='card'>"
                f"<div style='display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:.4rem;'>"
                f"<div>"
                f"<span class='ticker-big'>{pos['ticker']}</span>"
                f"<span style='margin-left:7px;font-size:.75rem;color:#64748B;'>{pos['name']}</span><br>"
                f"<span class='mono-sm'>{si} {pos['style']} · {pos['sector']}</span>"
                f"</div>"
                f"<div style='text-align:right;'>"
                f"<div style='font-family:DM Serif Display,serif;font-size:1.2rem;color:#F1F5F9;'>{fmt_usd(pos['mv'],0)}</div>"
                f"<div class='mono-sm'><span class='{pl_c}'>{fmt_usd(pos['pl_amt'])} ({fmt_pct(pos['pl_pct'])})</span></div>"
                f"</div>"
                f"</div>"
                f"<div style='display:flex;gap:1.5rem;margin-top:.7rem;flex-wrap:wrap;'>"
                f"<div><div class='mono-sm'>Shares</div><div class='mono-val'>{pos['shares']}</div></div>"
                f"<div><div class='mono-sm'>Avg Buy</div><div class='mono-val'>{fmt_usd(pos['avg_buy'])}</div></div>"
                f"<div><div class='mono-sm'>Current</div><div class='mono-val'>{fmt_usd(pos['current'])}</div></div>"
                f"<div><div class='mono-sm'>Daily</div><div class='mono-val'><span class='{chg_c}'>{fmt_pct(pos['change_pct'])}</span></div></div>"
                f"<div><div class='mono-sm'>Weight</div><div class='mono-val blue'>{pos['weight_total']:.1f}%</div></div>"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            f"<div class='card' style='border-color:#2D3A52;margin-top:.5rem;'>"
            f"<div style='display:flex;justify-content:space-between;flex-wrap:wrap;gap:.8rem;'>"
            f"<div><div class='mono-sm'>Invested</div>"
            f"<div style='font-family:DM Serif Display,serif;font-size:1.1rem;color:#F1F5F9;'>{fmt_usd(d['total_mv'],0)}</div></div>"
            f"<div><div class='mono-sm'>P/L</div>"
            f"<div style='font-family:DM Serif Display,serif;font-size:1.1rem;'>"
            f"<span class='{'green' if d['total_pl']>=0 else 'red'}'>{fmt_usd(d['total_pl'],0)}</span></div></div>"
            f"<div><div class='mono-sm'>Cash</div>"
            f"<div style='font-family:DM Serif Display,serif;font-size:1.1rem;color:#F59E0B;'>{fmt_usd(d['cash'],0)}</div></div>"
            f"<div><div class='mono-sm'>Total</div>"
            f"<div style='font-family:DM Serif Display,serif;font-size:1.1rem;color:#60A5FA;'>{fmt_usd(d['grand_total'],0)}</div></div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — WATCHLIST
# ══════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    if not d["watchlist"]:
        st.info("No watchlist stocks.")
    else:
        for w in d["watchlist"]:
            si      = STYLE_ICONS.get(w["style"],"")
            curr_s  = fmt_usd(w["current"]) if w["current"] else "—"
            tgt_s   = fmt_usd(w["target"])  if w["target"]  else "Not set"
            dist_s  = fmt_pct(w["dist"])    if w["dist"] is not None else "—"
            dist_c  = ("green" if (w["dist"] or 0) < 0 else
                       "red"   if (w["dist"] or 0) > 10 else "mono-val")
            st.markdown(
                f"<div class='card'>"
                f"<div style='display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:.4rem;'>"
                f"<div>"
                f"<span class='ticker-big'>{w['ticker']}</span> "
                f"<span style='font-size:.75rem;color:#64748B;'>{w['name']}</span><br>"
                f"<span class='mono-sm'>{si} {w['style']} · {w['sector']}</span>"
                f"</div>"
                f"<div>{sig_badge(w['signal'])}</div>"
                f"</div>"
                f"<div style='display:flex;gap:1.5rem;margin-top:.7rem;flex-wrap:wrap;'>"
                f"<div><div class='mono-sm'>Current</div><div class='mono-val'>{curr_s}</div></div>"
                f"<div><div class='mono-sm'>Target</div><div class='mono-val'>{tgt_s}</div></div>"
                f"<div><div class='mono-sm'>Distance</div>"
                f"<div class='mono-val'><span class='{dist_c}'>{dist_s}</span></div></div>"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — RECOMMENDATIONS
# ══════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    if not d["recommendations"]:
        st.success("✅ No immediate actions required.")
    else:
        for rec in d["recommendations"]:
            st.markdown(
                f"<div class='rec-card' style='border-left:4px solid {rec['color']};'>"
                f"<div style='display:flex;align-items:center;gap:.6rem;margin-bottom:.3rem;'>"
                f"<span style='font-size:1.2rem;'>{rec['icon']}</span>"
                f"<span style='font-family:DM Mono,monospace;font-size:.68rem;letter-spacing:.1em;"
                f"text-transform:uppercase;color:{rec['color']};font-weight:600;'>{rec['action']}</span>"
                f"</div>"
                f"<p style='font-family:DM Sans,sans-serif;font-size:.84rem;color:#94A3B8;margin:0;line-height:1.6;'>"
                f"{rec['detail']}</p>"
                f"</div>",
                unsafe_allow_html=True,
            )

    if d["cash"] > 5000:
        st.markdown("<div class='sec-hdr'>Cash Deployment Plan</div>", unsafe_allow_html=True)
        cash      = d["cash"]
        reserve   = round(cash * 0.10)
        deployable= cash - reserve
        plan = [
            ("XOM",   "Energy",      0.23, "#10B981", "Sector diversifier + dividend"),
            ("BRK.B", "Financial",   0.22, "#06B6D4", "Defensive value compounder"),
            ("NVDA",  "Technology",  0.22, "#3B82F6", "AI growth — on watchlist"),
            ("CAT",   "Industrials", 0.20, "#F59E0B", "Cyclical, non-correlated"),
            ("CELH",  "Consumer",    0.08, "#F97316", "Speculative — small size"),
            ("CASH",  "Reserve",     0.05, "#4B5563", "Keep for corrections"),
        ]
        for ticker, sector, pct, color, note in plan:
            amt = round(deployable * pct) if ticker != "CASH" else reserve
            st.markdown(
                f"<div class='card' style='border-left:4px solid {color};padding:.7rem 1rem;'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                f"<div>"
                f"<span style='font-family:DM Serif Display,serif;font-size:1.1rem;color:#F1F5F9;'>{ticker}</span>"
                f"<span style='margin-left:8px;font-size:.75rem;color:#64748B;'>{sector}</span>"
                f"</div>"
                f"<div style='text-align:right;'>"
                f"<div style='font-family:DM Mono,monospace;font-size:1rem;color:{color};'>{fmt_usd(amt,0)}</div>"
                f"<div class='mono-sm'>{note}</div>"
                f"</div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — UPDATE PORTFOLIO
# ══════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    # Cash
    st.markdown("<div class='sec-hdr'>Cash Balance</div>", unsafe_allow_html=True)
    new_cash = st.number_input("Cash (USD)", min_value=0.0,
                               value=float(p["cash"]), step=1000.0, format="%.2f")
    if st.button("💾 Save Cash"):
        p["cash"] = new_cash
        save_portfolio(p)
        st.session_state.portfolio = p
        refresh_computed()
        st.success(f"✅ Cash → {fmt_usd(new_cash, 0)}")
        st.rerun()

    # Owned
    st.markdown("<div class='sec-hdr'>Owned Positions</div>", unsafe_allow_html=True)
    for h in [x for x in p["holdings"] if x["status"] == "Owned"]:
        gi = p["holdings"].index(h)
        with st.expander(f"{h['ticker']} — {h['name']}"):
            c1, c2 = st.columns(2)
            ns = c1.number_input("Shares",         min_value=0.0, value=float(h["shares"]),                 step=1.0,   key=f"s_{h['ticker']}")
            na = c2.number_input("Avg Buy ($)",     min_value=0.0, value=float(h["avg_buy"]),               step=0.01, format="%.2f", key=f"a_{h['ticker']}")
            np_ = st.number_input("Current Price ($)", min_value=0.0,
                                   value=float(h.get("current_price") or h["avg_buy"]),
                                   step=0.01, format="%.2f", key=f"cp_{h['ticker']}")
            nn = st.text_input("Notes", value=h.get("notes",""), key=f"n_{h['ticker']}")

            b1, b2 = st.columns(2)
            if b1.button(f"💾 Save", key=f"sv_{h['ticker']}"):
                p["holdings"][gi].update({"shares": ns, "avg_buy": na,
                                           "current_price": np_, "notes": nn})
                save_portfolio(p); st.session_state.portfolio = p
                refresh_computed(); st.success("✅ Saved"); st.rerun()
            if b2.button(f"→ Watchlist", key=f"wl_{h['ticker']}"):
                p["holdings"][gi]["status"] = "Watchlist"
                p["holdings"][gi]["shares"] = 0
                save_portfolio(p); st.session_state.portfolio = p
                refresh_computed(); st.success(f"↩️ Moved to Watchlist"); st.rerun()

    # Watchlist
    st.markdown("<div class='sec-hdr'>Watchlist</div>", unsafe_allow_html=True)
    for h in [x for x in p["holdings"] if x["status"] == "Watchlist"]:
        gi = p["holdings"].index(h)
        with st.expander(f"{h['ticker']} — {h['name']}"):
            c1, c2 = st.columns(2)
            nt = c1.number_input("Target Entry ($)", min_value=0.0,
                                  value=float(h.get("target_entry") or 0),
                                  step=0.50, format="%.2f", key=f"te_{h['ticker']}")
            nc = c2.number_input("Current Price ($)", min_value=0.0,
                                  value=float(h.get("current_price") or 0),
                                  step=0.01, format="%.2f", key=f"cwl_{h['ticker']}")
            nn2 = st.text_input("Notes", value=h.get("notes",""), key=f"nwl_{h['ticker']}")

            b1, b2 = st.columns(2)
            if b1.button("💾 Save", key=f"swl_{h['ticker']}"):
                p["holdings"][gi].update({
                    "target_entry": nt if nt > 0 else None,
                    "current_price": nc if nc > 0 else None,
                    "notes": nn2,
                })
                save_portfolio(p); st.session_state.portfolio = p
                refresh_computed(); st.success("✅ Saved"); st.rerun()
            if b2.button("→ Owned", key=f"own_{h['ticker']}"):
                p["holdings"][gi]["status"] = "Owned"
                save_portfolio(p); st.session_state.portfolio = p
                refresh_computed(); st.success("✅ Marked Owned — set shares above"); st.rerun()

    # Add new
    st.markdown("<div class='sec-hdr'>Add New Stock</div>", unsafe_allow_html=True)
    with st.expander("➕ Add stock"):
        a1, a2 = st.columns(2)
        atk  = a1.text_input("Ticker").upper().strip()
        anm  = a2.text_input("Company Name")
        a3, a4 = st.columns(2)
        asec = a3.selectbox("Sector", ["Technology","Enterprise Software","Energy","Industrials",
                                        "Financial","Healthcare","Consumer","EV / Technology","Other"])
        asty = a4.selectbox("Style",  ["Compounder","Growth","Cyclical","Value","Speculative"])
        a5, a6 = st.columns(2)
        ast  = a5.selectbox("Status", ["Watchlist","Owned"])
        atgt = a6.number_input("Target Entry ($)", min_value=0.0, step=0.50, format="%.2f")
        if st.button("➕ Add"):
            if not atk or not anm:
                st.error("Ticker and name required.")
            elif any(h["ticker"] == atk for h in p["holdings"]):
                st.error(f"{atk} already in portfolio.")
            else:
                p["holdings"].append({"ticker": atk, "name": anm, "sector": asec,
                                       "style": asty, "status": ast, "shares": 0,
                                       "avg_buy": 0.0, "current_price": None,
                                       "target_entry": atgt if atgt > 0 else None, "notes": ""})
                save_portfolio(p); st.session_state.portfolio = p
                refresh_computed(); st.success(f"✅ {atk} added"); st.rerun()
