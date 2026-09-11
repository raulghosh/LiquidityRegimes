# G7 Liquidity Regimes

Classifies each G7 economy into a liquidity regime — **Loosening / Peak /
Tightening / Trough** — from central bank and fiscal conditions, updated
monthly. Built for long-term macro positioning: the framework cares about
regime *transitions*, not point-in-time levels.

**Live app:** deploy your own via [Streamlit Community
Cloud](https://share.streamlit.io) pointed at this repo (`app.py`), or run
locally (below).

## What it measures

Two pillars, weighted **2/3 central bank + 1/3 fiscal** by default (adjustable
live in the app):

### Central bank pillar — split into Quantity and Stance

| Sub-score | Component | Coverage |
|---|---|---|
| Quantity | Balance sheet, 12m % change | Fed, ECB, BoJ, BoE, BoC |
| Quantity | Reserves ÷ GDP, level | US only |
| Stance | Policy rate, 12m change (inverted) | all 5 |
| Stance | Real policy rate (rate − CPI YoY) | all 5 |
| Stance | 2y yield − policy rate | all 5 |
| Stance | SF Fed proxy funds rate − EFFR | US only |

The US balance sheet is **net liquidity** = Fed assets − Treasury General
Account − reverse repo, since TGA/RRP swings often dominate QE/QT month to
month. Germany, France, and Italy share the ECB's score — fiscal is what
differentiates them.

Two **overlays** (shown, not scored): US reserve ampleness (EFFR vs. IORB —
EFFR at or above IORB flags scarcity) and the Chicago Fed National Financial
Conditions Index.

### Fiscal pillar

Fiscal impulse = −(YoY change in the cyclically adjusted primary balance),
IMF WEO, annual, carried forward monthly.

### Scoring and regime classification

Every component is z-scored against its own 10-year rolling history
(positive = looser than usual). A pillar or composite score `s` is classified
by its level and its 6-month change:

```
s > 0, rising   → Loosening       s > 0, falling  → Peak
s ≤ 0, falling  → Tightening      s ≤ 0, rising   → Trough
```

## Repo layout

```
pull.sh          downloads raw data to data/cache/ (gitignored)
build_panel.py   parses the cache into data/cb_monthly.csv, data/fiscal_annual.csv
regimes.py       scores pillars, classifies regimes -> data/regimes.csv, regime_heatmap.png
app.py           Streamlit dashboard, reads data/regimes.csv
```

Data flows one way: `pull.sh` → `build_panel.py` → `regimes.py` → `app.py`.
The committed `data/*.csv` and `data/*.png` let the app run immediately
without a data refresh.

## Data sources (all free, no API keys)

FRED (Fed/ECB/BoJ balance sheets, TGA, RRP, reserves, IORB, EFFR, 2y
Treasury, NFCI) · Bank of England IADB (base money, 5y yield) · Bank of
Canada Valet (assets, 2y yield) · ECB Data Portal (2y yield) · Ministry of
Finance Japan (JGB yields) · BIS (policy rates, CPI) · San Francisco Fed
(proxy funds rate) · IMF WEO / DataMapper (fiscal balances).

## Run locally

```bash
python3 -m pip install -r requirements.txt
bash pull.sh              # download raw data
python3 build_panel.py    # build the monthly panel
python3 regimes.py        # score + classify regimes
python3 -m streamlit run app.py
```

The app's sidebar also has a **Refresh data** button that runs the same three
steps and reloads.

## Known simplifications

- UK front-end rate uses the **5-year** par yield (IADB has no 2-year series).
- Inflation is **headline CPI**, not core, for consistency across all five
  areas via one BIS pull.
- Fiscal impulse is **annual**, carried forward monthly — fiscal regimes move
  on budget cycles, so this is the right resolution rather than a limitation.
- No corporate-spending pillar (data quality/coverage outside the US is a
  research project on its own) and no China/EM coverage — scope is G7 only.

## Roadmap

- Funding-stress overlay for Europe/UK (€STR − deposit rate, SONIA − Bank
  Rate), mirroring the US EFFR−IORB flag.
- SOMA holdings duration (captures Operation Twist-style composition shifts
  that balance-sheet size alone misses).
- Scheduled data refresh (e.g. GitHub Action on a weekly cron) so the
  deployed app doesn't depend on manual refreshes.
