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

SCENARIO = 0


from pyalgotrade import strategy, plotter
from pyalgotrade.broker import backtesting as broker
from pyalgotrade.stratanalyzer import returns, sharpe, drawdown, trades
from pyalgotrade.utils import stats
from pyalgotrade.technical import macd, cross, ma
from pyalgoext import dbfeed, organizers, volatility
import datetime
import math


class MyBenchmark(strategy.BacktestingStrategy):
    def __init__(self, feed, posMax, capital):
        myBroker = broker.Broker(capital, feed, broker.TradePercentage(0.002))
        myBroker.setAllowNegativeCash(True)
        myBroker.getFillStrategy().setVolumeLimit(None)

        super(MyBenchmark, self).__init__(feed, myBroker)

        self._feed = feed
        self._session = 0
        self._liquidity = 0.05
        self._posMax = posMax
        self._positions = {}

        self.startDateTime = None
        self.endDateTime = None

        self.setUseAdjustedValues(True)

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
        self.logOp("VENTA CANCELADA", position.getExitOrder())

    def reviewMembers(self):
        members = self._feed.getMembers()
        for instrument, position in self._positions.items():
            if instrument not in members:
                if not position.getExitOrder():
                    position.exitMarket()

    def prepareEnter(self, instrument, bars):
        bar = bars[instrument]
        perInstrument = self.getBroker().getEquity() / self._posMax
        cash = self.getBroker().getCash()
        if perInstrument > cash:
            perInstrument = cash
        perInstrument *= (1 - self._liquidity)
        amount = int(perInstrument / float(bar.getPrice()))
        if amount > 0:
            self._positions[instrument] = self.enterLong(instrument, amount, True)

    def onStart(self):
        self.startDateTime = self.getCurrentDateTime()

    def onFinish(self, bars):
        self.endDateTime = bars.getDateTime()

    def logOp(self, type, order):
        self.info("[%s] %s %s %s" % (len(self._positions), type, order.getInstrument(), order.getExecutionInfo()))

    def onBars(self, bars):
        self._session += 1
        if self._session >= 200:
            self.reviewMembers()

            for instrument in self._feed.getMembers():
                if instrument in bars and instrument not in self._positions:
                    if len(self._positions) < self._posMax:
                        self.prepareEnter(instrument, bars)


class MyFundamentalStrategy(MyBenchmark):
    def __init__(self, feed, posMax, capital, rules, days=None, buffer=0):
        eventWindow = organizers.BasicOrganizerWindow(feed, rules)
        self._organizer = organizers.BasicOrganizer(feed, eventWindow)

        super(MyFundamentalStrategy, self).__init__(feed, posMax, capital)

        self._lastReview = None
        self._days = days
        self._buffer = 0

    def reviewOrder(self):
        leaders = [top[0] for top in self._organizer[-1][0:(self._posMax + self._buffer)]]
        for instrument, position in self._positions.items():
            if instrument not in leaders:
                if not position.getExitOrder():
                    position.exitMarket()

    def onBars(self, bars):
        self._session += 1
        if self._session >= 200:
            self.reviewMembers()

            dateTime = bars.getDateTime()
            if self._days is not None:
                if self._lastReview is None:
                    self._lastReview = dateTime
                elif dateTime > self._lastReview + datetime.timedelta(days=self._days):
                   self._lastReview = dateTime
                   self.reviewOrder()

            order = self._organizer[-1]
            for instrument, score in order:
                if instrument in bars and instrument not in self._positions:
                    if len(self._positions) < self._posMax:
                        self.prepareEnter(instrument, bars)


class MyTechnicalStrategyMACD(MyBenchmark):
    def __init__(self, feed, posMax, capital):
        super(MyTechnicalStrategyMACD, self).__init__(feed, posMax, capital)

        self._prices = {}
        self._vols = {}

    def doTechnical(self, bars, members, leaders):
        for instrument in members:
            if instrument in bars:
                if not instrument in self._prices:
                    self._prices[instrument] = macd.MACD(self._feed[instrument].getPriceDataSeries(), 12, 26, 9)
                    self._vols[instrument] = macd.MACD(self._feed[instrument].getVolumeDataSeries(), 12, 26, 9)
                elif self._session >= 200:
                    pri = self._prices[instrument]
                    vol = self._vols[instrument]
                    if instrument in self._positions:
                        if cross.cross_below(pri.getSignal(), pri) and cross.cross_below(vol.getSignal(), vol):
                            position = self._positions[instrument]
                            if not position.getExitOrder():
                                position.exitMarket()
                    elif instrument in leaders:
                        if cross.cross_above(pri.getSignal(), pri) and cross.cross_above(vol.getSignal(), vol):
                            if len(self._positions) < self._posMax:
                                self.prepareEnter(instrument, bars)

    def onBars(self, bars):
        self._session += 1
        self.reviewMembers()

        members = self._feed.getMembers()
        self.doTechnical(bars, members, members)


class MyTechnicalStrategySMA(MyBenchmark):
    def __init__(self, feed, posMax, capital):
        super(MyTechnicalStrategySMA, self).__init__(feed, posMax, capital)

        self._smaShort = { }
        self._smaLong = { }

    def doTechnical(self, bars, members, leaders):
        for instrument in members:
            if instrument in bars:
                if not instrument in self._smaLong:
                    self._smaShort[instrument] = ma.SMA(self._feed[instrument].getPriceDataSeries(), 50)
                    self._smaLong[instrument] = ma.SMA(self._feed[instrument].getPriceDataSeries(), 200)
                elif self._session >= 200:
                    if instrument in self._positions:
                        if cross.cross_below(self._smaShort[instrument], self._smaLong[instrument]):
                            position = self._positions[instrument]
                            if not position.getExitOrder():
                                position.exitMarket()
                    elif instrument in leaders:
                        if cross.cross_above(self._smaShort[instrument], self._smaLong[instrument]):
                            if len(self._positions) < self._posMax:
                                self.prepareEnter(instrument, bars)

    def onBars(self, bars):
        self._session += 1
        self.reviewMembers()

        members = self._feed.getMembers()
        self.doTechnical(bars, members, members)


class MyCombinedStrategy(MyFundamentalStrategy, MyTechnicalStrategySMA):
    def __init__(self, feed, posMax, capital, rules, days=None, buffer=0):
        super(MyCombinedStrategy, self).__init__(feed, posMax, capital, rules, days, buffer)

    def onBars(self, bars):
        self._session += 1
        self.reviewMembers()

        dateTime = bars.getDateTime()
        if self._days is not None:
            if self._lastReview is None:
                self._lastReview = dateTime
            elif dateTime > self._lastReview + datetime.timedelta(days=self._days):
                self._lastReview = dateTime
                self.reviewOrder()

        members = self._feed.getMembers()
        leaders = [top[0] for top in self._organizer[-1][0:19]]
        self.doTechnical(bars, members, leaders)


# Config params

config = {
  'user': 'root',
  'password': '',
  'host': '127.0.0.1',
  'database': 'ibex35',
  'raise_on_warnings': True,
}

fields = [
    'PER',
    'PBV',
    'DPS',
    'NDE'
]

indices = [
    'IBEX35'
]

capStart = 1000000
startDate = None # e.g. datetime.date(2015, 06, 01)
endDate = None

feed = dbfeed.DbFeed(config, fields, 10, startDate, endDate)
for index in indices:
    feed.registerIndex(index)

# Pick strategy

myStrategy = None
if SCENARIO == 2:
    myStrategy = MyBenchmark(feed, 10, capStart)
elif SCENARIO == 3:
    rules = [
        organizers.OrderRule('PBV', True)
    ]
    myStrategy = MyFundamentalStrategy(feed, 10, capStart, rules)
elif SCENARIO == 4:
    rules = [
        organizers.OrderRule('PER', True),
        organizers.OrderRule('NDE', True),
        organizers.OrderRule('DPS')
    ]
    myStrategy = MyFundamentalStrategy(feed, 10, capStart, rules)
elif SCENARIO == 5:
    rules = [
        organizers.OrderRule('PBV', True, 0.5),
        organizers.OrderRule('PER', True, 0.5),
        organizers.OrderRule('NDE', True),
        organizers.OrderRule('DPS')
    ]
    myStrategy = MyFundamentalStrategy(feed, 10, capStart, rules, 90)
elif SCENARIO == 6:
    myStrategy = MyTechnicalStrategyMACD(feed, 10, capStart)
elif SCENARIO == 7:
    myStrategy = MyTechnicalStrategySMA(feed, 10, capStart)
elif SCENARIO == 8:
    rules = [
        organizers.OrderRule('PBV', True, 0.5),
        organizers.OrderRule('PER', True, 0.5),
        organizers.OrderRule('NDE', True),
        organizers.OrderRule('DPS')
    ]
    myStrategy = MyCombinedStrategy(feed, 10, capStart, rules)
else:
    myStrategy = MyBenchmark(feed, 30, capStart)

# Attach analyzers to the strategy

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
myStrategy.info("Rentabilidad Anualizada: %.4f%%" % (
    100 * (math.pow((capEnd / capStart), (365.0 / ((myStrategy.endDateTime - myStrategy.startDateTime).days))) - 1)))
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

plt.plot()

