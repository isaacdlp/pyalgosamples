from pyalgoext import download
from datetime import datetime

download.poloniex_crypto("BTC_ETH", "data/BTC_ETH.csv")
download.poloniex_crypto("BTC_LTC", "data/BTC_LTC.csv", datetime.strptime('2016-06-01', '%Y-%m-%d'))