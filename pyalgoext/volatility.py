# PyAlgoExt
# Extensions to the PyAlgoTrade Library
#
# Copyright 2015-2016 Isaac de la Pena
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

import math
from collections import deque

from pyalgotrade import stratanalyzer
from pyalgotrade import dataseries
from pyalgotrade.stratanalyzer import returns
from pyalgotrade.utils import stats

class VolaAnalyzer(stratanalyzer.StrategyAnalyzer):
    """A :class:`pyalgotrade.stratanalyzer.StrategyAnalyzer` that calculates
    the X-sessions daily volatility ratio for the whole portfolio.

    :param sessions: the number of historic sessions to consider for each daily volatility ratio.
    :type sessions: int.
    """

    def __init__(self, sessions=126):
        self.__retBuffer = []
        self.__sessions = sessions
        self.__returns = dataseries.SequenceDataSeries(maxLen=sessions)
        self.__volaSeries = dataseries.SequenceDataSeries()
        self.__currentDate = None

    def getVolaSeries(self):
        return self.__volaSeries

    def beforeAttach(self, strat):
        # Get or create a shared ReturnsAnalyzerBase
        analyzer = returns.ReturnsAnalyzerBase.getOrCreateShared(strat)
        analyzer.getEvent().subscribe(self.__onReturns)

    def __onReturns(self, dateTime, returnsAnalyzerBase):
        netReturn = returnsAnalyzerBase.getNetReturn()
        # Calculate daily returns.
        if dateTime.date() == self.__currentDate:
            self.__retBuffer.append(netReturn)
        else:
            if self.__retBuffer:
                self.__retBuffer.append(netReturn)
                netReturn = self.__retBuffer[0]
                for aReturn in self.__retBuffer[1:]:
                    netReturn = (1 + netReturn) * (1 + aReturn) - 1
                self.__retBuffer = []
            self.__currentDate = dateTime.date()
            self.__returns.append(netReturn)
            if len(self.__returns) == self.__sessions:
                self.__volaSeries.appendWithDateTime(dateTime.date(), stats.stddev(self.__returns, 1) * math.sqrt(252) * 100)