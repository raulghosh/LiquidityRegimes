"""Parse cached raw data (from pull.sh) into tidy monthly series.

Sources in data/cache/:
  - fred_*.csv : Fed/ECB/BoJ balance sheets, US TGA, US RRP
  - boe.csv    : BoE notes + reserves (sterling monetary base — the Weekly
                 Report has no single total-assets line; base money is the
                 cleaner liquidity measure anyway)
  - boc.json   : BoC total assets
  - bis_rates.csv : policy rates, monthly, 5 CBs
  - imf_*.json : fiscal balances, annual, G7

Output: data/cb_monthly.csv (balance sheets + policy rates, month-end),
        data/fiscal_annual.csv, and a chart of the raw balance sheets.
"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
CACHE = ROOT / "data" / "cache"
OUT = ROOT / "data"


def load_balance_sheets():
    frames = {}
    for sid, name in [
        ("WALCL", "us_fed_assets"), ("WTREGEN", "us_tga"), ("RRPONTSYD", "us_rrp"),
        ("ECBASSETSW", "ea_assets"), ("JPNASSETS", "jp_assets"),
    ]:
        df = pd.read_csv(CACHE / f"fred_{sid}.csv", na_values=["."],
                         parse_dates=["observation_date"])
        frames[name] = df.set_index("observation_date").iloc[:, 0]

    boe = pd.read_csv(CACHE / "boe.csv")
    boe["date"] = pd.to_datetime(boe["DATE"], format="%d %b %Y")
    frames["gb_base"] = boe.set_index("date").eval("RPWB55A + RPWB56A")

    obs = json.loads((CACHE / "boc.json").read_text())["observations"]
    boc = pd.DataFrame(
        {"date": o["d"], "v": float(o["V36610"]["v"])}
        for o in obs if o.get("V36610", {}).get("v")
    )
    frames["ca_assets"] = boc.set_index(pd.to_datetime(boc["date"]))["v"]

    # month-end values; WALCL and WTREGEN are $mn, RRPONTSYD $bn -> align to $bn
    m = pd.DataFrame({k: s.resample("ME").last() for k, s in frames.items()})
    m["us_fed_assets"] /= 1000
    m["us_tga"] /= 1000
    # US net liquidity: Fed assets - TGA - RRP (all $bn). RRP ~0 pre-2014.
    m["us_netliq"] = m["us_fed_assets"] - m["us_tga"] - m["us_rrp"].fillna(0)
    return m


def load_policy_rates():
    df = pd.read_csv(CACHE / "bis_rates.csv")
    r = df.pivot_table(index="TIME_PERIOD", columns="REF_AREA", values="OBS_VALUE")
    r = r.rename(columns={"US": "us", "XM": "ea", "JP": "jp", "GB": "gb", "CA": "ca"})
    r.index = pd.to_datetime(r.index) + pd.offsets.MonthEnd(0)
    return r.add_suffix("_rate").sort_index()


def load_fiscal():
    frames = []
    for f, name in [("imf_capb.json", "capb"), ("imf_balance.json", "balance")]:
        data = json.loads((CACHE / f).read_text())["values"]
        code = next(iter(data))
        g7 = ["USA", "JPN", "DEU", "FRA", "ITA", "GBR", "CAN"]
        df = pd.DataFrame({c: data[code][c] for c in g7}).rename_axis("year")
        df.columns = [f"{c.lower()}_{name}" for c in df.columns]
        frames.append(df)
    out = pd.concat(frames, axis=1)
    out.index = out.index.astype(int)
    return out.sort_index()


if __name__ == "__main__":
    bs = load_balance_sheets()
    rates = load_policy_rates()
    cb = bs.join(rates, how="outer")
    cb.to_csv(OUT / "cb_monthly.csv")

    fiscal = load_fiscal()
    fiscal.to_csv(OUT / "fiscal_annual.csv")

    print("cb_monthly.csv:", cb.shape)
    print(cb.dropna(how="all").agg(["first_valid_index", "last_valid_index"]).T)
    print("\nfiscal_annual.csv:", fiscal.shape,
          f"years {fiscal.index.min()}-{fiscal.index.max()}")
    print(fiscal.filter(like="_capb").tail(3).round(1))

    # raw-series eyeball chart: balance sheets indexed to 100 at Jan 2007
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cols = {"us_netliq": "US net liquidity", "ea_assets": "ECB",
            "jp_assets": "BoJ", "gb_base": "BoE base", "ca_assets": "BoC"}
    fig, axes = plt.subplots(2, 1, figsize=(11, 9), sharex=True)
    base = cb.loc["2007-01":]
    for c, lbl in cols.items():
        s = base[c] / base[c].dropna().iloc[0] * 100
        axes[0].plot(s.index, s, label=lbl)
    axes[0].set_yscale("log")
    axes[0].set_title("Central bank balance sheets (log, Jan 2007 = 100)")
    axes[0].legend()
    for c in ["us_rate", "ea_rate", "jp_rate", "gb_rate", "ca_rate"]:
        axes[1].plot(base.index, base[c], label=c[:2].upper())
    axes[1].set_title("Policy rates (%)")
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(OUT / "raw_series.png", dpi=120)
    print("\nchart -> data/raw_series.png")
