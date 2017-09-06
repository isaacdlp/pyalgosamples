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

