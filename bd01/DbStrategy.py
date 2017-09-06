from pyalgotrade import strategy
from pyalgoext import dbfeed
import datetime

class MyStrategy(strategy.BacktestingStrategy):
    def __init__(self, feed):
        strategy.BacktestingStrategy.__init__(self, feed)

    def onBars(self, bars):
        for instrument in bars.keys():
            bar = bars[instrument]
            self.info("%s %s %s" % (instrument, bars.getDateTime(), bar.getPrice()))

config = {
  'user': 'root',
  'password': '',
  'host': '127.0.0.1',
  'database': 'almacen',
  'raise_on_warnings': True,
}

price_Field = 'PRICE'

instruments = [
    'BE0003470755',
    'AT0000A18XM4',
    'AT0000937503',
    'AT0000908504',
    'AT0000809058',
    'AT0000743059',
    'AT0000730007',
    'AT0000720008',
    'AT0000652011',
    'AT0000606306'
]

feed = dbfeed.DbMemFeed(config, price_Field)
for instrument in instruments:
    feed.loadBars(instrument)

myStrategy = MyStrategy(feed)
myStrategy.run()

