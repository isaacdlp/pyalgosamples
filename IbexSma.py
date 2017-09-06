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
from pyalgotrade.stratanalyzer import drawdown, returns, sharpe, trades
from pyalgotrade.utils import stats
from pyalgoext import volatility
import IbexAssets as assets
import pyalgotrade.logger as logger
import math

class MyBenchmark(strategy.BacktestingStrategy):
    def __init__(self, feed, instruments, posMax, delay):
        strategy.BacktestingStrategy.__init__(self, feed, 15000)
        self._delay = delay
        self._liquidity = 0.05
        self._positions = {}
        self._posMax = posMax
        self._instruments = instruments
        self.setUseAdjustedValues(True)
        self.getBroker().getFillStrategy().setVolumeLimit(None)
        self.startDateTime = feed.peekDateTime()
        self.endDateTime = None

    def onEnterOk(self, position):
        self.logOp("COMPRA", position.getEntryOrder())

    def onEnterCanceled(self, position):
        del self._positions[position.getInstrument()]
        self.logOp("COMPRA CANCELADA", position.getEntryOrder())

    def onExitOk(self, position):
        del self._positions[position.getInstrument()]
        self.logOp("VENTA", position.getExitOrder())

    def onExitCanceled(self, position):
        # If the exit was canceled, re-submit it.
        position.exitMarket()
        self.logOp("VENTA CANCELADA", position.getExitOrder())

    def onBars(self, bars):
        # Wait for the same bar than the strategy
        if self._delay > 0:
            self._delay -= 1
            return

        for instrument in self._instruments:
            if instrument in bars:
                if instrument not in self._positions:
                    if len(self._positions) < self._posMax:
                        bar = bars[instrument]
                        self._positions[instrument] = self.enterLong(instrument, self.calcShares(bar.getPrice()), True)

    def calcShares(self, priceRef):
        perInstrument = self.getBroker().getEquity() / self._posMax
        cash = self.getBroker().getCash()
        if perInstrument > cash:
            perInstrument = cash
        perInstrument *= (1 - self._liquidity)
        shares = int(perInstrument / priceRef)
        return shares

    def onFinish(self, bars):
        self.endDateTime = bars.getDateTime()

    def logOp(self, type, order):
        self.info("[%s] %s %s %s" % (len(self._positions), type, order.getInstrument(), order.getExecutionInfo()))


class MyStrategy(MyBenchmark):
    def __init__(self, feed, instruments, posMax, smaShort, smaLong):
        MyBenchmark.__init__(self, feed, instruments, posMax, smaLong)
        self._smaShort = {}
        self._smaLong = {}
        for instrument in instruments:
            self._smaShort[instrument] = ma.SMA(feed[instrument].getPriceDataSeries(), smaShort)
            self._smaLong[instrument] = ma.SMA(feed[instrument].getPriceDataSeries(), smaLong)

    def getSMAShorts(self):
        return self._smaShort

    def getSMALongs(self):
        return self._smaLong

    def onBars(self, bars):
        for instrument in self._instruments:
            # Wait for enough bars to be available to calculate a SMA.
            if not self._smaLong[instrument] or self._smaLong[instrument][-1] is None:
                return

            if instrument in bars:
                # If a position was not opened, check if we should enter a long position.
                if instrument not in self._positions:
                    if len(self._positions) < self._posMax:
                        if self._smaShort[instrument][-1] > self._smaLong[instrument][-1]:
                            bar = bars[instrument]
                            self._positions[instrument] = self.enterLong(instrument, self.calcShares(bar.getPrice()), True)
                # Check if we have to exit the position.
                elif self._smaShort[instrument][-1] < self._smaLong[instrument][-1]:
                    if not self._positions[instrument].exitActive():
                       self._positions[instrument].exitMarket()


def run_strategy(isBenchmark, instruments, posMax, smaShort, smaLong):
    # Load the yahoo feed from the CSV file
    feed = yahoofeed.Feed()
    feed.sanitizeBars(True)
    for instrument, startYear in instruments.items():
        for year in range(startYear, assets.endYear):
            feed.addBarsFromCSV(instrument, assets.folder + instrument + "-" + str(year) + ".csv")

    if isBenchmark:
        myStrategy = MyBenchmark(feed, instruments, posMax, smaLong)
    else:
        myStrategy = MyStrategy(feed, instruments, posMax, smaShort, smaLong)

    # Attach analyzers to the strategy.
    # Returns first in case others use it (DataSeries)
    returnsAnalyzer = returns.Returns()
    myStrategy.attachAnalyzer(returnsAnalyzer)
    returnsAnalyzer.getReturns().setMaxLen(1000000)

    sharpeAnalyzer = sharpe.SharpeRatio()
    myStrategy.attachAnalyzer(sharpeAnalyzer)

    drawDownAnalyzer = drawdown.DrawDown()
    myStrategy.attachAnalyzer(drawDownAnalyzer)

    tradesAnalyzer = trades.Trades()
    myStrategy.attachAnalyzer(tradesAnalyzer)

    volaAnalyzer = volatility.VolaAnalyzer(120)
    myStrategy.attachAnalyzer(volaAnalyzer)

    # Attach a plotter to the strategy
    plt = plotter.StrategyPlotter(myStrategy, False)

    volaSeries = volaAnalyzer.getVolaSeries()
    plt.getOrCreateSubplot("Volatility").addDataSeries("Volatility", volaSeries)

    capStart = myStrategy.getBroker().getEquity()
    myStrategy.info("CAPITAL INICIAL: $%.4f" % capStart)

    # Run the strategy
    myStrategy.run()

    # Show basic information
    allRet = returnsAnalyzer.getReturns()
    capEnd = myStrategy.getBroker().getEquity()

    myStrategy.info("CAPITAL FINAL: $%.4f" % capEnd)
    myStrategy.info(" ")
    myStrategy.info("Rentabilidad: %.4f%%" % (100 * (capEnd - capStart) / capStart))
    myStrategy.info("Rentabilidad Anualizada: %.4f%%" % (100 * (math.pow((capEnd / capStart),(365.0 / ((myStrategy.endDateTime - myStrategy.startDateTime).days))) - 1)))
    myStrategy.info("Volatilidad Anualizada: %.4f%%" % (100 * stats.stddev(allRet, 1) * math.sqrt(252)))
    myStrategy.info("Ratio de Sharpe Anualizado: %.4f" % (100 * sharpeAnalyzer.getSharpeRatio(0.0036, True)))

    myStrategy.info("DrawDown Maximo: %.4f%%" % (100 * drawDownAnalyzer.getMaxDrawDown()))
    myStrategy.info("DrawDown Mas Largo: %s dias" % (drawDownAnalyzer.getLongestDrawDownDuration().days))
    myStrategy.info(" ")
    myStrategy.info("Rentabilidad Media: %.4f%%" % (100 * stats.mean(allRet)))
    posRet = []
    negRet = []
    allRet = returnsAnalyzer.getReturns()
    for ret in allRet:
        if ret > 0:
            posRet.append(ret)
        elif ret < 0:
            negRet.append(ret)
    myStrategy.info("Ganancia Media: %.4f%%" % (100 * stats.mean(posRet)))
    myStrategy.info("Perdida Media: %.4f%%" % (100 * stats.mean(negRet)))
    myStrategy.info(" ")
    myStrategy.info("Ganancia Media por Op: $%s" % (stats.mean(tradesAnalyzer.getProfits())))
    myStrategy.info("Perdida Media por Op: $%s" % (stats.mean(tradesAnalyzer.getLosses())))
    myStrategy.info("Comisiones Totales: $%s" % (sum(tradesAnalyzer.getCommissionsForAllTrades())))
    myStrategy.info("Num Ops Igual: %s" % (tradesAnalyzer.getEvenCount()))
    myStrategy.info("Num Ops Gano: %s" % (tradesAnalyzer.getProfitableCount()))
    myStrategy.info("Num Ops Pierdo: %s" % (tradesAnalyzer.getUnprofitableCount()))

    # Plot the strategy.
    plt.plot()

logger.log_format = "[%(levelname)s] %(message)s"

smaShort = 50
smaLong = 200

# Benchmark
#run_strategy(True, assets.indices, 1, smaShort, smaLong)

# Strategy
run_strategy(False, assets.instruments, 10, smaShort, smaLong)