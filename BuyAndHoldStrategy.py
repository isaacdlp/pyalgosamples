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


class MyStrategy(strategy.BacktestingStrategy):
    def __init__(self, feed, instrument):
        strategy.BacktestingStrategy.__init__(self, feed, 1000)
        self.__position = None
        self.__instrument = instrument
        # We'll use adjusted close values instead of regular close values.
        self.setUseAdjustedValues(True)

    def onEnterOk(self, position):
        execInfo = position.getEntryOrder().getExecutionInfo()
        self.info("BUY at $%.2f" % (execInfo.getPrice()))

    def onEnterCanceled(self, position):
        self.__position = None

    def onBars(self, bars):
        # If a position was not opened, check if we should enter a long position.
        if self.__position is None:
            # Enter a buy market order for 25 shares. The order is good till canceled.
            self.__position = self.enterLong(self.__instrument, 25, True)

def run_strategy():
    # Load the yahoo feed from the CSV file
    feed = yahoofeed.Feed()
    feed.addBarsFromCSV("AMS.MC", "data/AMS.MC-2015.csv")

    # Evaluate the strategy with the feed.
    myStrategy = MyStrategy(feed, "AMS.MC")

    # Attach a plotter to the strategy
    plt = plotter.StrategyPlotter(myStrategy)

    # Run the strategy
    myStrategy.run()
    print "Final portfolio value: $%.2f" % myStrategy.getBroker().getEquity()

    # Plot the strategy.
    plt.plot()


run_strategy()