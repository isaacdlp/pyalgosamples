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

import mysql.connector
import pyalgotrade.bar as bars
import pyalgotrade.barfeed as barfeed
from pyalgotrade.barfeed import membf
from pyalgotrade import bar
from pyalgotrade import dataseries
from pyalgotrade.utils import dt

def normalize_instrument(instrument):
    return instrument.upper()


PRICE_FIELD = 'CLOSE'
PRICE_FIELDS = ['OPEN', 'HIGH', 'LOW', PRICE_FIELD, 'VOL', 'ADJ']


class DbBar(bar.BasicBar):
    def __init__(self, dateTime, fields, frequency):
        bar.BasicBar.__init__(self, dateTime,
            float(fields[PRICE_FIELDS[0]]),
            float(fields[PRICE_FIELDS[1]]),
            float(fields[PRICE_FIELDS[2]]),
            float(fields[PRICE_FIELDS[3]]),
            float(fields[PRICE_FIELDS[4]]),
            float(fields[PRICE_FIELDS[5]]), frequency)
        self.__fields = fields


    def getField(self, key, price=False):
        if key in self.__fields:
            return self.__fields[key]
        return None

    def getFields(self):
        return self.__fields


# MySQL Database
# Timestamps are stored in UTC.
class Database():
    def __init__(self, config, fields=[]):
        self.__instrumentIds = {}

        for field in PRICE_FIELDS:
            if field not in fields:
                fields.append(field)

        self.__fields = fields
        self.__sqlFields = (','.join(["%s"] * len(self.__fields)))
        self.__config = config
        self.__connection = None

    def start(self):
        self.__connection = mysql.connector.connect(**self.__config)
        self.__connection.isolation_level = None  # To do auto-commit

    def stop(self):
        if self.__connection:
            self.__connection.close()
            self.__connection = None

    def getNextDate(self, dateTime=None):

        sql = "select distinct(fecha)" \
              " from dato where fecha > %s order by fecha asc limit 1"
        args = [dateTime]
        if not dateTime:
            sql = "select distinct(fecha)" \
                  " from dato order by fecha asc limit 1"
            args = []

        cursor = self.__connection.cursor()
        cursor.execute(sql, args)

        row = cursor.fetchone()
        cursor.close()
        if row:
            return row[0]
        return None

    def getBar(self, instrument, frequency, dateTime, timezone=None):
        instrument = normalize_instrument(instrument)
        sql = "select criterio, valor" \
              " from dato where activo = %s and criterio IN (%s) and fecha = %s"
        sql = sql % ('%s', self.__sqlFields, '%s')

        args = [instrument]
        args.extend(self.__fields)
        args.append(dateTime)

        cursor = self.__connection.cursor()
        cursor.execute(sql, args)

        if timezone:
            dateTime = dt.localize(dateTime, timezone)

        fields = {}
        for criteria, value in cursor:
           fields[criteria] = value
        if PRICE_FIELD in fields:
            return DbBar(dateTime, fields, frequency)
        return None

    def getBars(self, instrument, frequency, timezone=None, fromDateTime=None, toDateTime=None):
        instrument = normalize_instrument(instrument)
        sql =  "select fecha, criterio, valor" \
            " from dato where activo = %s and criterio IN (%s)"
        sql = sql % ('%s', self.__sqlFields)

        args = [instrument]
        args.extend(self.__fields)

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

        lastDateTime = None
        fields = {}
        for dateTime, criteria, value in cursor:
            if timezone:
                dateTime = dt.localize(dateTime, timezone)
            if lastDateTime is None:
                lastDateTime = dateTime
            if lastDateTime != dateTime:
                if PRICE_FIELD in fields:
                    ret.append(DbBar(lastDateTime, fields, frequency))
                lastDateTime = dateTime
                fields = {}
            fields[criteria] = value
        if PRICE_FIELD in fields:
            ret.append(DbBar(lastDateTime, fields, frequency))
        cursor.close()
        return ret


class DbMemFeed(barfeed.membf.BarFeed):
    def __init__(self, config, fields, priceField, maxLen=dataseries.DEFAULT_MAX_LEN):
        membf.BarFeed.__init__(self, bar.Frequency.DAY, maxLen)
        self.__db = Database(config, fields)

    def barsHaveAdjClose(self):
        return True

    def getDatabase(self):
        return self.__db

    def loadBars(self, instrument, timezone=None, fromDateTime=None, toDateTime=None):
        self.__db.start()
        bars = self.__db.getBars(instrument, self.getFrequency(), timezone, fromDateTime, toDateTime)
        self.addBarsFromSequence(instrument, bars)
        self.__db.stop()


class DbFeed(barfeed.BaseBarFeed):
    def __init__(self, config, fields, maxLen=dataseries.DEFAULT_MAX_LEN, startDateTime=None, endDateTime=None):
        barfeed.BaseBarFeed.__init__(self, bar.Frequency.DAY, maxLen)
        self.__db = Database(config, fields)
        self.__eof = False
        self.__startDateTime = startDateTime
        self.__endDateTime = endDateTime
        self.__dateTime = startDateTime

    def barsHaveAdjClose(self):
        return True

    def getDatabase(self):
        return self.__db

    # This may raise.
    def start(self):
        self.__db.start()

    # This should not raise.
    def stop(self):
        self.__db.stop()

    def peekDateTime(self):
        if not self.__dateTime:
            return self.getNextDateTime()
        return None

    # This should not raise.
    def join(self):
        return None

    def eof(self):
        return self.__eof

    def getCurrentDateTime(self):
        return self.__dateTime

    def getNextDateTime(self):
        dateTime = self.__db.getNextDate(self.__dateTime)
        if dateTime:
            if self.__endDateTime and self.__endDateTime < dateTime:
                self.__eof = True
            else:
                self.__dateTime = dateTime
        else:
            self.__eof = True

    def getNextBars(self):
        ret = {}
        for instrument in self.getKeys():
            bar = self.__db.getBar(instrument, self.getFrequency(), self.__dateTime)
            if bar:
                ret[instrument] = bar

        self.getNextDateTime()

        return bars.Bars(ret)