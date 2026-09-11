"""Score liquidity pillars and classify regimes for the G7.

CB score (per country, monthly):
    z(12m % change in balance sheet) averaged with z(-12m change in policy
    rate), each z-scored against its own 10y rolling history.
DE/FR/IT share the ECB's CB score; fiscal differentiates them.

Fiscal score: z(fiscal impulse) where impulse = -(YoY change in cyclically
adjusted primary balance), annual from IMF WEO, carried forward monthly.
Projection years beyond the current year are dropped.

Composite = 2/3 CB + 1/3 fiscal.

Regime (applied to any score s): sign of level x sign of 6m change:
    s>0 rising  -> Loosening      s>0 falling -> Peak
    s<0 falling -> Tightening     s<0 rising  -> Trough

Outputs: data/regimes.csv, data/regime_heatmap.png, current snapshot printed.
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
DATA = ROOT / "data"

# country -> (balance sheet column, rate column) in cb_monthly.csv
CB_MAP = {
    "USA": ("us_netliq", "us_rate"),
    "JPN": ("jp_assets", "jp_rate"),
    "GBR": ("gb_base", "gb_rate"),
    "CAN": ("ca_assets", "ca_rate"),
    "DEU": ("ea_assets", "ea_rate"),
    "FRA": ("ea_assets", "ea_rate"),
    "ITA": ("ea_assets", "ea_rate"),
}

CB_WEIGHT = 2 / 3  # fiscal gets the rest


def zscore(s, window=120, min_periods=60):
    return (s - s.rolling(window, min_periods=min_periods).mean()) / s.rolling(
        window, min_periods=min_periods
    ).std()


def classify(score):
    direction = score.diff(6)
    regime = pd.Series(np.nan, index=score.index, dtype=object)
    regime[(score > 0) & (direction >= 0)] = "Loosening"
    regime[(score > 0) & (direction < 0)] = "Peak"
    regime[(score <= 0) & (direction < 0)] = "Tightening"
    regime[(score <= 0) & (direction >= 0)] = "Trough"
    regime[score.isna() | direction.isna()] = np.nan
    return regime


def build():
    cb = pd.read_csv(DATA / "cb_monthly.csv", index_col=0, parse_dates=True)
    fiscal = pd.read_csv(DATA / "fiscal_annual.csv", index_col=0)
    fiscal = fiscal[fiscal.index <= pd.Timestamp.now().year]

    rows = []
    for ctry, (bs_col, rate_col) in CB_MAP.items():
        bs_z = zscore(cb[bs_col].pct_change(12))
        rate_z = zscore(-cb[rate_col].diff(12))
        cb_score = pd.concat([bs_z, rate_z], axis=1).mean(axis=1)

        capb = fiscal[f"{ctry.lower()}_capb"]
        impulse_z = zscore(-capb.diff(), window=10, min_periods=5)  # annual
        impulse_m = impulse_z.rename(
            lambda y: pd.Timestamp(year=y, month=12, day=31)
        ).resample("ME").bfill()  # year value applies to all months of that year
        fiscal_score = impulse_m.reindex(cb.index).ffill(limit=11)

        composite = CB_WEIGHT * cb_score + (1 - CB_WEIGHT) * fiscal_score
        df = pd.DataFrame({
            "country": ctry,
            "cb_score": cb_score,
            "fiscal_score": fiscal_score,
            "composite": composite,
            "cb_regime": classify(cb_score),
            "fiscal_regime": classify(fiscal_score),
            "regime": classify(composite),
        })
        rows.append(df)

    panel = pd.concat(rows).rename_axis("date").reset_index()
    panel = panel.dropna(subset=["cb_score"])
    panel.to_csv(DATA / "regimes.csv", index=False)
    return panel


REGIMES = ["Loosening", "Peak", "Tightening", "Trough"]
REGIME_COLORS = ["#2f9e44", "#b2df8a", "#e03131", "#ffa94d"]
COUNTRY_ORDER = ["USA", "DEU", "FRA", "ITA", "GBR", "JPN", "CAN"]


def heatmap(panel, regime_col="regime", title="Composite liquidity regime"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch

    grid = (
        panel.pivot(index="country", columns="date", values=regime_col)
        .reindex(COUNTRY_ORDER)
        .replace({r: i for i, r in enumerate(REGIMES)})
        .astype(float)
    )
    grid = grid.loc[:, grid.columns >= "2005-01-01"]

    fig, ax = plt.subplots(figsize=(13, 4))
    ax.pcolormesh(grid.columns, np.arange(len(COUNTRY_ORDER)),
                  np.ma.masked_invalid(grid.values), shading="nearest",
                  cmap=ListedColormap(REGIME_COLORS), vmin=-0.5, vmax=3.5)
    ax.set_yticks(np.arange(len(COUNTRY_ORDER)), COUNTRY_ORDER)
    ax.invert_yaxis()
    ax.set_title(title)
    ax.legend(handles=[Patch(color=c, label=r)
                       for r, c in zip(REGIMES, REGIME_COLORS)],
              loc="upper left", bbox_to_anchor=(1.0, 1.0))
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    panel = build()
    heatmap(panel).savefig(DATA / "regime_heatmap.png", dpi=120)
    latest = panel.sort_values("date").groupby("country").last()
    print("Snapshot (latest per country):")
    print(latest[
        ["date", "cb_score", "fiscal_score", "composite", "cb_regime", "fiscal_regime", "regime"]
    ].round(2).to_string())
    print("\nwrote data/regimes.csv, data/regime_heatmap.png")

    # self-check: 2020 must be Loosening, 2022 Tightening, for the US composite
    us = panel[panel["country"] == "USA"].set_index("date")
    assert us.loc["2020-06-30", "regime"] == "Loosening", us.loc["2020-06-30"]
    assert us.loc["2022-09-30", "cb_regime"] == "Tightening", us.loc["2022-09-30"]
    print("sanity checks passed (US 2020 Loosening, US 2022 CB Tightening)")
