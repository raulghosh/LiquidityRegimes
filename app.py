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
    "Central bank balance-sheet + policy-rate momentum and fiscal impulse, "
    "z-scored vs own 10y history. Sources: FRED, BoE, BoC, BIS, IMF WEO. "
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
    latest[["country", "date", "cb_score", "fiscal_score", "composite",
            "cb_regime", "fiscal_regime", "regime"]]
    .style.map(color_regime, subset=["cb_regime", "fiscal_regime", "regime"])
    .format({"cb_score": "{:.2f}", "fiscal_score": "{:.2f}",
             "composite": "{:.2f}", "date": lambda d: d.date()}),
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
c1, c2, c3 = st.columns(3)
last = detail.dropna(subset=["composite"]).iloc[-1]
c1.metric("CB regime", last["cb_regime"], f"{last['cb_score']:.2f}")
c2.metric("Fiscal regime", last["fiscal_regime"], f"{last['fiscal_score']:.2f}")
c3.metric("Composite", last["regime"], f"{last['composite']:.2f}")
st.line_chart(detail[["cb_score", "fiscal_score", "composite"]])
