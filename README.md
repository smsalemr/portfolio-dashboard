# Portfolio Intelligence — Deployment Guide

## Files

```
portfolio-dashboard/
├── app.py                          ← Main dashboard
├── engine.py                       ← Calculation logic
├── requirements.txt                ← Dependencies
├── .gitignore                      ← Excludes secrets from Git
├── .streamlit/
│   ├── config.toml                 ← Theme + server settings
│   └── secrets.toml.template       ← Copy → secrets.toml, set password
└── data/
    └── portfolio.json              ← Your portfolio data
```

## Deploy to Streamlit Cloud (Free)

### Step 1 — GitHub
1. Go to github.com → sign in (or create free account)
2. Click **New repository**
3. Name it: `portfolio-dashboard`
4. Set to **Private** ← important
5. Click **Create repository**
6. Upload all files from this ZIP (drag and drop in GitHub's web UI)

### Step 2 — Streamlit Cloud
1. Go to **share.streamlit.io**
2. Sign in with your GitHub account
3. Click **New app**
4. Select your `portfolio-dashboard` repo
5. Main file: `app.py`
6. Click **Deploy**

### Step 3 — Set Password
1. In Streamlit Cloud, click your app → **Settings** → **Secrets**
2. Paste exactly:
   ```
   PASSWORD = "choose_your_password_here"
   ```
3. Click **Save** — app restarts automatically

### Step 4 — Open on iPhone
- Your URL will be: `https://[your-username]-portfolio-dashboard-app-[hash].streamlit.app`
- Open in Safari → tap Share → **Add to Home Screen**
- It will behave like a native app icon

## Updating Portfolio Data

**From iPhone (easiest):**
- Open dashboard → tap **✏️ Update** tab
- Edit cash, shares, prices directly
- Tap 💾 Save — changes persist immediately

**From computer:**
- Edit `data/portfolio.json` directly
- Commit and push to GitHub
- Streamlit Cloud auto-redeploys in ~30 seconds

## Live Prices

Tap **⟳** (top right) to fetch live prices via yfinance.
Works on iPhone Safari — takes 5–15 seconds depending on connection.

## Password Change

Go to Streamlit Cloud → your app → Settings → Secrets → update PASSWORD value.

## Notes

- The dashboard stores data in `portfolio.json` inside the repo
- Streamlit Cloud free tier: always-on with 1GB RAM, sufficient for this app
- Private GitHub repo = only you can see the source code
- Password gate = only you can access the live dashboard
