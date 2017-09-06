from pyalgotrade.tools import yahoofinance
import os
import Ibex2010Assets as assets

if not os.path.isdir(assets.folder):
    os.mkdir(assets.folder)

for instrument, start in assets.all.items():
    for year in range(start, assets.endYear):
        store = assets.folder + instrument + "-" + str(year) + ".csv"
        print store
        yahoofinance.download_daily_bars(instrument, year, store)