# PyAlgoTrade
#
# Copyright 2011-2015 Gabriel Martin Becedillas Ruiz
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
.. moduleauthor:: Gabriel Martin Becedillas Ruiz <gabriel.becedillas@gmail.com>
"""

from pyalgotrade.barfeed import membf
from pyalgotrade import bar
from pyalgotrade import dataseries
from pyalgotrade.utils import dt

import mysql.connector

# MySQL Database
# Timestamps are stored in UTC.
class Database():
    def __init__(self, config, priceField):
        self.__config = config
        self.__priceField = "PRICE"

    def start(self):
        self.__connection = mysql.connector.connect(**self.__config)
        self.__connection.isolation_level = None  # To do auto-commit

    def stop(self):
        self.__connection.close()
        self.__connection = None

    def getBars(self, instrument, frequency, timezone=None, fromDateTime=None, toDateTime=None):
        sql =  "select fecha, valor" \
            " from dato where activo = %s and criterio = %s"

        args = [instrument, self.__priceField]

        if fromDateTime is not None:
            sql += " and fecha >= %s"
            args.append(fromDateTime)
        if toDateTime is not None:
            sql += " and fecha <= %s"
            args.append(toDateTime)

        sql += " order by fecha asc"
        cursor = self.__connection.cursor()
        cursor.execute(sql, args)
        ret = []

        for dateTime, value in cursor:
            if timezone:
                dateTime = dt.localize(dateTime, timezone)

            ret.append(bar.BasicBar(dateTime, value, value, value, value, 0, value, frequency))

        cursor.close()
        return ret


class DbMemFeed(membf.BarFeed):
    def __init__(self, config, priceField, maxLen=dataseries.DEFAULT_MAX_LEN):
        membf.BarFeed.__init__(self, bar.Frequency.DAY, maxLen)
        self.__db = Database(config, priceField)

    def barsHaveAdjClose(self):
        return True

    def getDatabase(self):
        return self.__db

    def loadBars(self, instrument, timezone=None, fromDateTime=None, toDateTime=None):
        self.__db.start()
        bars = self.__db.getBars(instrument, self.getFrequency(), timezone, fromDateTime, toDateTime)
        self.addBarsFromSequence(instrument, bars)
        self.__db.stop()
