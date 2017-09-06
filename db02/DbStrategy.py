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

from pyalgotrade import strategy
from pyalgoext import dbfeed
import datetime

class MyStrategy(strategy.BacktestingStrategy):
    def __init__(self, feed):
        strategy.BacktestingStrategy.__init__(self, feed)
        self.setUseAdjustedValues(False)

    def onBars(self, bars):
        for instrument in bars.keys():
            bar = bars[instrument]
            self.info("%s %s %s %s %s" % (instrument, bars.getDateTime(), bar.getOpen(), bar.getPrice(),  bar.getField('PER')))

config = {
  'user': 'root',
  'password': '',
  'host': '127.0.0.1',
  'database': 'ibex35',
  'raise_on_warnings': True,
}

fields = [
    'PER'
]

instruments = [
    'TEF.MC',
    'REP.MC',
    'BBVA.MC'
]

dateStart = datetime.date(2010, 01, 04)
dateEnd = datetime.date(2012, 01, 04)

feed = dbfeed.DbFeed(config, fields, 10, dateStart, dateEnd)
for instrument in instruments:
    feed.registerInstrument(instrument)

myStrategy = MyStrategy(feed)
myStrategy.run()

