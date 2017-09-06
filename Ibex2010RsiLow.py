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
from pyalgotrade.broker import backtesting as broker
from pyalgotrade.barfeed import yahoofeed
from pyalgotrade.technical import ma, rsi, cross
from pyalgotrade.stratanalyzer import drawdown, returns, sharpe, trades
from pyalgotrade.utils import stats
from pyalgoext import volatility
import pyalgotrade.logger as logger
import math
import os

import Ibex2010Assets as assets

class MyBenchmark(strategy.BacktestingStrategy):
    def __init__(self, feed, instruments, posMax, delay):
        myBroker = broker.Broker(1000000, feed, broker.TradePercentage(0.002))
        strategy.BacktestingStrategy.__init__(self, feed, myBroker)
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
                        self.prepareLong(instrument, bars)

    def prepareLong(self, instrument, bars):
        bar = bars[instrument]
        perInstrument = self.getBroker().getEquity() / self._posMax
        cash = self.getBroker().getCash()
        if perInstrument > cash:
            perInstrument = cash
        perInstrument *= (1 - self._liquidity)
        amount = int(perInstrument / bar.getPrice())
        if amount > 0:
            self._positions[instrument] = self.enterLong(instrument, amount, True)

    def onFinish(self, bars):
        self.endDateTime = bars.getDateTime()

    def logOp(self, type, order):
        self.info("[%s] %s %s %s" % (len(self._positions), type, order.getInstrument(), order.getExecutionInfo()))


class MyStrategy(MyBenchmark):
    def __init__(self, feed, instruments, posMax, entrySma, exitSma, rsiPeriod, overSoldThreshold):
        MyBenchmark.__init__(self, feed, instruments, posMax, exitSma)
        self._overSoldThreshold = overSoldThreshold
        self._prices = {}
        self._entrySmas = {}
        self._exitSmas = {}
        self._rsis = {}
        for instrument in instruments:
            priceDS = feed[instrument].getPriceDataSeries()
            self._prices[instrument] = priceDS
            self._entrySmas[instrument] = ma.SMA(priceDS, entrySma)
            self._exitSmas[instrument] = ma.SMA(priceDS, exitSma)
            self._rsis[instrument] = rsi.RSI(priceDS, rsiPeriod)

    def getEntrySmas(self):
        return self._entrySmas

    def getExitSmas(self):
        return self._exitSmas

    def onBars(self, bars):
        for instrument in bars.keys():
            # Wait for enough bars to be available to calculate a SMA.
            if not self._entrySmas[instrument] or self._entrySmas[instrument][-1] is None\
            or not self._exitSmas[instrument] or self._exitSmas[instrument][-1] is None:
                return

            # If a position was not opened, check if we should enter a long position.
            if instrument not in self._positions:
                if len(self._positions) < self._posMax:
                    bar = bars[instrument]
                    if bar.getPrice() > self._entrySmas[instrument][-1] and self._rsis[instrument][-1] <= self._overSoldThreshold:
                        self.prepareLong(instrument, bars)
            # Check if we have to exit the position.
            elif cross.cross_above(self._prices[instrument], self._exitSmas[instrument]):
                if not self._positions[instrument].exitActive():
                   self._positions[instrument].exitMarket()


def run_strategy(isBenchmark, instruments, posMax, entrySma, exitSma, rsiPeriod, overSoldThreshold):
    # Load the yahoo feed from the CSV file
    feed = yahoofeed.Feed()
    feed.sanitizeBars(True)
    for instrument, startYear in instruments.items():
        for year in range(startYear, assets.endYear):
            if os.path.isfile(assets.folder + instrument + "-" + str(year) + ".csv"):
                feed.addBarsFromCSV(instrument, assets.folder + instrument + "-" + str(year) + ".csv")

    if isBenchmark:
        myStrategy = MyBenchmark(feed, instruments, posMax, exitSma)
    else:
        myStrategy = MyStrategy(feed, instruments, posMax, entrySma, exitSma, rsiPeriod, overSoldThreshold)

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

    plt.getOrCreateSubplot("RSI").addDataSeries("RSI", myStrategy._rsis["FER.MC"])

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

entrySma = 200
exitSma = 15
rsiPeriod = 5
overSoldThreshold = 15

# Benchmark
#run_strategy(True, assets.instruments, 15, entrySma, exitSma, rsiPeriod, overSoldThreshold)

# Strategy
run_strategy(False, assets.instruments, 20, entrySma, exitSma, rsiPeriod, overSoldThreshold)


gb_instruments = ["BP.L", "ISYS.L", "PSON.L"]

class MyCommission(broker.Commission):
    def calculate(self, order, price, quantity):
        commission = 0.0015 * price * quantity
        action = order.getAction();
        isBuy = False
        if action == Order.Action.BUY or action == Order.Action.BUY_TO_COVER:
            isBuy = True
        instrument = order.getInstrument()
        if instrument in gb_instruments:
            if isBuy:
                commission += (0.01 * price * quantity)
        else:
            if isBuy:
                commission += 5
            elif commission < 25:
                commission = 25
        return commission
