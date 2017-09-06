from pyalgotrade import strategy
from pyalgotrade.barfeed import yahoofeed
from pyalgotrade.technical import ma

class MyStrategy(strategy.BacktestingStrategy):
    def __init__(self, feed, instrument):
        strategy.BacktestingStrategy.__init__(self, feed)
        self.__sma = ma.SMA(feed[instrument].getCloseDataSeries(), 15)
        self.__instrument = instrument

    def onBars(self, bars):
        bar = bars[self.__instrument]
        self.info("%s %s" % (bar.getClose(), self.__sma[-1]))

feed = yahoofeed.Feed()
feed.addBarsFromCSV("TEF.MC", "data/TEF.MC-2015.csv")

myStrategy = MyStrategy(feed, "TEF.MC")
myStrategy.run()