#!/bin/bash
# Download all raw data to data/cache/. Run before build_panel.py.
set -e
cd "$(dirname "$0")"
mkdir -p data/cache
C="curl -sL --fail --retry 3 --max-time 120"

# FRED: Fed/ECB/BoJ balance sheets, TGA, RRP, reserves, IORB/IOER, EFFR,
#       US 2y, Chicago NFCI, nominal GDP
for s in WALCL WTREGEN RRPONTSYD ECBASSETSW JPNASSETS WRESBAL IORB IOER EFFR DGS2 NFCI GDP; do
  $C "https://fred.stlouisfed.org/graph/fredgraph.csv?id=$s" -o "data/cache/fred_$s.csv"
  echo "fred_$s.csv $(wc -l < data/cache/fred_$s.csv) lines"
done

# BoE: notes in circulation + reserve balances (sterling monetary base)
$C "https://www.bankofengland.co.uk/boeapps/iadb/fromshowcolumns.asp?csv.x=yes&Datefrom=01/Jan/2000&Dateto=now&SeriesCodes=RPWB55A,RPWB56A&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N" -o data/cache/boe.csv
echo "boe.csv $(wc -l < data/cache/boe.csv) lines"

# BoC: total assets V36610
$C "https://www.bankofcanada.ca/valet/observations/V36610/json" -o data/cache/boc.json
echo "boc.json $(wc -c < data/cache/boc.json) bytes"

# BIS: policy rates, monthly, 5 CBs
$C "https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/M.US+XM+JP+GB+CA?format=csv&startPeriod=1999-01" -o data/cache/bis_rates.csv
echo "bis_rates.csv $(wc -l < data/cache/bis_rates.csv) lines"

# Stance inputs: CPI YoY (BIS), front-end yields, SF Fed proxy funds rate
$C "https://stats.bis.org/api/v2/data/dataflow/BIS/WS_LONG_CPI/1.0/M.US+XM+JP+GB+CA.771?format=csv&startPeriod=1999-01" -o data/cache/bis_cpi.csv
echo "bis_cpi.csv $(wc -l < data/cache/bis_cpi.csv) lines"
$C "https://www.frbsf.org/wp-content/uploads/proxy-funds-rate-chart1-data.csv" -o data/cache/sf_proxy.csv
echo "sf_proxy.csv $(wc -l < data/cache/sf_proxy.csv) lines"
$C "https://data-api.ecb.europa.eu/service/data/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y?format=csvdata&startPeriod=2004-09-06" -o data/cache/ecb_2y.csv
echo "ecb_2y.csv $(wc -l < data/cache/ecb_2y.csv) lines"
$C "https://www.bankofcanada.ca/valet/observations/BD.CDN.2YR.DQ.YLD/json?start_date=1999-01-01" -o data/cache/boc_2y.json
echo "boc_2y.json $(wc -c < data/cache/boc_2y.json) bytes"
# UK: IADB has no 2y series; 5y par yield is the closest front-end proxy
$C "https://www.bankofengland.co.uk/boeapps/iadb/fromshowcolumns.asp?csv.x=yes&Datefrom=01/Jan/1999&Dateto=now&SeriesCodes=IUDSNPY&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N" -o data/cache/boe_5y.csv
echo "boe_5y.csv $(wc -l < data/cache/boe_5y.csv) lines"
$C "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv" -o data/cache/mof_jgb.csv
echo "mof_jgb.csv $(wc -l < data/cache/mof_jgb.csv) lines"

# IMF: cyclically adjusted primary balance + overall balance, G7, annual
$C "https://www.imf.org/external/datamapper/api/v1/GGCBP_G01_PGDP_PT/USA/JPN/DEU/FRA/ITA/GBR/CAN" -o data/cache/imf_capb.json
$C "https://www.imf.org/external/datamapper/api/v1/GGXCNL_NGDP/USA/JPN/DEU/FRA/ITA/GBR/CAN" -o data/cache/imf_balance.json
echo "imf: $(wc -c < data/cache/imf_capb.json) + $(wc -c < data/cache/imf_balance.json) bytes"

echo "done"
