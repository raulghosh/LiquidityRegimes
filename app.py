"""G7 Liquidity Regime dashboard.

Run:  streamlit run app.py
Data: python3 build_panel.py && python3 regimes.py first (or use the
      sidebar refresh button, which shells out to pull.sh + both scripts).
"""

import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from regimes import COUNTRY_ORDER, REGIME_COLORS, REGIMES, classify, heatmap

ROOT = Path(__file__).parent
STYLE = dict(zip(REGIMES, REGIME_COLORS))

st.set_page_config(page_title="G7 Liquidity Regimes", layout="wide")


@st.cache_data
def load_panel():
    df = pd.read_csv(ROOT / "data" / "regimes.csv", parse_dates=["date"])
    return df


def color_regime(v):
    return f"background-color: {STYLE[v]}; color: black" if v in STYLE else ""


panel = load_panel()

with st.sidebar:
    st.header("Settings")
    cb_w = st.slider("CB pillar weight", 0.0, 1.0, 2 / 3, 0.05,
                     help="Fiscal gets 1 - weight. Default 2/3 CB, 1/3 fiscal.")
    view = st.radio("Heatmap pillar", ["Composite", "Central bank", "Fiscal"])
    if st.button("Refresh data (pulls all sources)"):
        with st.spinner("Downloading and rebuilding..."):
            for cmd in (["bash", "pull.sh"],
                        [sys.executable, "build_panel.py"],
                        [sys.executable, "regimes.py"]):
                r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
                if r.returncode:
                    st.error(f"{' '.join(cmd)} failed:\n{r.stderr[-2000:]}")
                    st.stop()
        st.cache_data.clear()
        st.rerun()

# recompute composite + regime with the chosen weight
panel = panel.sort_values(["country", "date"]).reset_index(drop=True)
panel["composite"] = cb_w * panel["cb_score"] + (1 - cb_w) * panel["fiscal_score"]
panel["regime"] = panel.groupby("country", group_keys=False)["composite"].apply(classify)

st.title("G7 Liquidity Regimes")
st.caption(
    "CB pillar = Quantity (balance sheet, reserves) + Stance (rate momentum, "
    "real rate, 2y−policy, proxy funds rate); fiscal = impulse from CAPB. "
    "All z-scored vs own 10y history. Sources: FRED, SF Fed, BoE, BoC, ECB, "
    "MoF Japan, BIS, IMF WEO. "
    f"Latest data: {panel['date'].max().date()}"
)

# --- snapshot table ---
latest = (
    panel.dropna(subset=["composite"])
    .groupby("country").last()
    .reindex(COUNTRY_ORDER)
    .reset_index()
)
st.subheader("Current snapshot")
st.dataframe(
    latest[["country", "date", "quantity_score", "stance_score", "cb_score",
            "fiscal_score", "composite", "cb_regime", "fiscal_regime", "regime"]]
    .style.map(color_regime, subset=["cb_regime", "fiscal_regime", "regime"])
    .format({c: "{:.2f}" for c in ["quantity_score", "stance_score", "cb_score",
                                   "fiscal_score", "composite"]}
            | {"date": lambda d: d.date()}),
    hide_index=True, use_container_width=True,
)

# --- heatmap ---
col = {"Composite": "regime", "Central bank": "cb_regime", "Fiscal": "fiscal_regime"}[view]
st.subheader(f"{view} regime history")
st.pyplot(heatmap(panel, regime_col=col, title=""), use_container_width=True)

# --- country detail ---
st.subheader("Country detail")
ctry = st.selectbox("Country", COUNTRY_ORDER)
detail = panel[panel["country"] == ctry].set_index("date")
last = detail.dropna(subset=["composite"]).iloc[-1]
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Quantity", f"{last['quantity_score']:.2f}", help="Balance sheet momentum (+ reserves/GDP for US)")
c2.metric("Stance", f"{last['stance_score']:.2f}", help="Rate momentum, real rate, 2y-policy (+ proxy rate gap for US)")
c3.metric("CB regime", last["cb_regime"], f"{last['cb_score']:.2f}")
c4.metric("Fiscal regime", last["fiscal_regime"], f"{last['fiscal_score']:.2f}")
c5.metric("Composite", last["regime"], f"{last['composite']:.2f}")
st.line_chart(detail[["quantity_score", "stance_score", "fiscal_score", "composite"]])

if ctry == "USA":
    st.subheader("US plumbing overlays")
    o1, o2 = st.columns(2)
    o1.metric("Reserves", str(last["reserves_flag"]).title(),
              f"EFFR−IORB {last['effr_iorb_bp']:+.0f}bp", delta_color="off",
              help="EFFR at or above IORB signals scarce reserves (NY Fed / Fed Board indicators)")
    o2.metric("Chicago Fed NFCI", f"{last['nfci']:.2f}", delta_color="off",
              help="Negative = looser-than-average financial conditions")
    st.line_chart(detail[["effr_iorb_bp"]].loc["2015":], height=200)
