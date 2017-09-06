# PyAlgoSamples
# Examples using the PyAlgoTrade Library
#
# Copyright 2015-2017 Isaac de la Pena
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
.. moduleauthor:: Isaac de la Pena <isaacdlp@agoraeafi.com>
"""

from pyalgotrade import strategy, plotter
from pyalgotrade.barfeed import yahoofeed
from pyalgotrade.technical import ma
import csv

class MyStrategy(strategy.BacktestingStrategy):
    def __init__(self, feed, instrument, smaShort, smaLong):
        strategy.BacktestingStrategy.__init__(self, feed, 10000)
        self._position = None
        self._instrument = instrument
        # We'll use adjusted close values instead of regular close values.
        self.setUseAdjustedValues(True)
        self._smaShort = ma.SMA(feed[instrument].getPriceDataSeries(), smaShort)
        self._smaLong = ma.SMA(feed[instrument].getPriceDataSeries(), smaLong)
        self.getBroker().getFillStrategy().setVolumeLimit(None)

    def onEnterOk(self, position):
        execInfo = position.getEntryOrder().getExecutionInfo()
        self.info("BUY %i shares at $%.2f Portfolio $%.2f" % (execInfo.getQuantity(), execInfo.getPrice(), self.getBroker().getEquity()))

    def onEnterCanceled(self, position):
        self._position = None

    def onExitOk(self, position):
        execInfo = position.getExitOrder().getExecutionInfo()
        self.info("SELL %i shares at $%.2f Portfolio $%.2f" % (execInfo.getQuantity(), execInfo.getPrice(), self.getBroker().getEquity()))
        self._position = None

    def onExitCanceled(self, position):
        # If the exit was canceled, re-submit it.
        self._position.exitMarket()

    def onBars(self, bars):
        # Wait for enough bars to be available to calculate a SMA.
        if self._smaLong[-1] is None:
            return

        bar = bars[self._instrument]
        # If a position was not opened, check if we should enter a long position.
        if self._position is None:
            if self._smaShort[-1] > self._smaLong[-1]:
                # Enter a buy market order for as many shares as we can. The order is good till canceled.
                amount = int(0.95 * self.getBroker().getEquity() / bar.getAdjClose())
                self._position = self.enterLong(self._instrument, amount, True)
        # Check if we have to exit the position.
        elif self._smaShort[-1] < self._smaLong[-1] and not self._position.exitActive():
            self._position.exitMarket()

class MyBenchmark(MyStrategy):
    def onBars(self, bars):
        bar = bars[self._instrument]
        if self._position is None:
            amount = int(0.95 * self.getBroker().getEquity() / bar.getAdjClose())
            self._position = self.enterLong(self._instrument, amount, True)

def run_strategy(index, startYear, endYear, smaShort, smaLong):

    # Load the yahoo feed from the CSV file
    feed = yahoofeed.Feed()
    feed.sanitizeBars(True)
    for year in range(startYear, endYear):
        feed.addBarsFromCSV(index, "./data/" + index + "-" + str(year) + ".csv")

    myStrategy = MyStrategy(feed, index, smaShort, smaLong)
    myStrategy.run()

    # Important! Otherwise the Benchmark won't run (nor fail)
    feed.reset()

    myBenchmark = MyBenchmark(feed, index, smaShort, smaLong)
    myBenchmark.run()

    retStrategy = myStrategy.getBroker().getEquity()
    retBenchmark = myBenchmark.getBroker().getEquity()

    return [str(startYear) + "-" + str(endYear), retStrategy, retBenchmark, (retStrategy - retBenchmark)]


index = "^GSPC"
with open("SxpStudy.csv", "wb") as csvFile:
    csvWriter = csv.writer(csvFile)
    csvWriter.writerow(["Year", "Strategy", "Benchmark", "Delta"])
    for startYear in range (1950, 2016, 10):
        endYear = startYear + 10
        if endYear > 2016:
            endYear = 2016
        csvWriter.writerow(run_strategy(index, startYear, endYear, 50, 200))