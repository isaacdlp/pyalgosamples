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


import mysql.connector
import pyalgotrade.bar as bars
import pyalgotrade.barfeed as barfeed
from pyalgotrade.barfeed import membf
from pyalgotrade import bar
from pyalgotrade import dataseries
from pyalgotrade.utils import dt
import datetime

def normalize_instrument(instrument):
    return instrument.upper()


class DbBar(bar.BasicBar):

    PRICE_FIELD = 'CLOSE'
    PRICE_FIELDS = ['OPEN', 'HIGH', 'LOW', PRICE_FIELD, 'VOL', 'ADJ']

    def __init__(self, dateTime, fields, frequency):
        v = []
        for param in DbBar.PRICE_FIELDS:
            if param == None:
                v.append(0)
            else:
                v.append(float(fields[param]))
        bar.BasicBar.__init__(self, dateTime, v[0], v[1], v[2], v[3], v[4], v[5], frequency)
        self.__fields = fields

    def getField(self, key):
        if key in self.__fields:
            return self.__fields[key]
        return None

    def getFields(self):
        return self.__fields


# MySQL Database
# Timestamps are stored in UTC.
class Database():
    def __init__(self, config, fields):
        self.__instrumentIds = {}

        for field in DbBar.PRICE_FIELDS:
            if field and field not in fields:
                fields.append(field)
        self.__priceField = DbBar.PRICE_FIELD

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

    def getMembers(self, index, dateTime):
        sql = "select activo from grupo where fecha = (select max(fecha) from grupo where fecha <= %s and indice = %s) and indice = %s"
        args = [dateTime, index, index]

        cursor = self.__connection.cursor()
        cursor.execute(sql, args)

        ret = []
        for row in cursor:
            ret.append(row[0])
        cursor.close()
        return ret

    def getDates(self, fromDateTime=None, toDateTime=None):
        sql = "select distinct(fecha) from dato"
        args = []
        if fromDateTime:
            sql += " where fecha >= %s"
            args.append(fromDateTime)
        if toDateTime:
            if len(args) > 0:
                sql += " and"
            else:
                sql += " where"
            sql += " fecha <= %s"
            args.append(toDateTime)

        sql += " order by fecha asc"

        cursor = self.__connection.cursor()
        cursor.execute(sql, args)

        ret = []
        for row in cursor:
            dateTime = row[0]
            if not isinstance(dateTime, datetime.datetime):
                dateTime = datetime.datetime.combine(dateTime, datetime.time.min)
            ret.append(dateTime)
        cursor.close()
        return ret

    def getBars(self, instruments, frequency, dateTime):
        ret = {}
        instNum = len(instruments)
        if instNum > 0:
            instFields = (','.join(["%s"] * instNum))

            sql =  "select activo, criterio, valor" \
                " from dato where fecha = %s and activo IN (%s) and criterio IN (%s)"
            sql = sql % ('%s', instFields, self.__sqlFields)

            args = [dateTime]
            args.extend(instruments)
            args.extend(self.__fields)

            sql += " order by activo asc"
            cursor = self.__connection.cursor()
            cursor.execute(sql, args)

            lastInstrument = None
            fields = {}
            for instrument, criteria, value in cursor:
                if lastInstrument is None:
                    lastInstrument = instrument
                if lastInstrument != instrument:
                    if self.__priceField in fields:
                        ret[lastInstrument] = DbBar(dateTime, fields, frequency)
                    lastInstrument = instrument
                    fields = {}
                fields[criteria] = value
            if self.__priceField in fields:
                ret[lastInstrument] = DbBar(dateTime, fields, frequency)
            cursor.close()
        return ret


class DbFeed(barfeed.BaseBarFeed):
    def __init__(self, config, fields, maxLen=dataseries.DEFAULT_MAX_LEN, startDateTime=None, endDateTime=None):
        barfeed.BaseBarFeed.__init__(self, bar.Frequency.DAY, maxLen)
        self.__db = Database(config, fields)
        self.__eof = False
        self.__startDateTime = startDateTime
        self.__endDateTime = endDateTime
        self.__indices = []
        self.__instruments = []

    def barsHaveAdjClose(self):
        return True

    def getDatabase(self):
        return self.__db

    # This may raise.
    def start(self):
        self.__db.start()
        self.__dates = self.__db.getDates(self.__startDateTime, self.__endDateTime)
        self.__dateTime = None
        self.__datePos = -1
        self.getNextDatePos()
        self.getNextDateTime()

    # This should not raise.
    def stop(self):
        self.__db.stop()

    def peekDateTime(self):
        return None

    # This should not raise.
    def join(self):
        return None

    def eof(self):
        return self.__eof

    def getCurrentDateTime(self):
        return self.__dateTime

    def getNextDateTime(self):
        if not self.__eof:
            self.__dateTime = self.__dates[self.__datePos]

    def getNextDatePos(self):
        self.__datePos += 1
        if not self.__datePos < len(self.__dates):
            self.__eof = True

    def registerIndex(self, index):
        if index not in self.__indices:
            self.__indices.append(index)
            return True
        return False

    def getMembers(self):
        return self.__members

    def getNextMembers(self):
        members = []
        if len(self.__indices) > 0:
            for index in self.__indices:
                candidates = self.__db.getMembers(index, self.__dateTime)
                for candidate in candidates:
                    if candidate not in members:
                        members.append(candidate)
                        if candidate not in self.__instruments:
                            self.__instruments.append(candidate)
            self.__members = members
        else:
            self.__members = self.getRegisteredInstruments()
            self.__instruments = self.getRegisteredInstruments()

    def getNextBars(self):
        self.getNextDateTime()
        self.getNextMembers()

        ret = self.__db.getBars(self.__instruments, self.getFrequency(), self.__dateTime)
        for i in range(len(self.__instruments) - 1, -1, -1):
            instrument = self.__instruments[i]
            if instrument not in ret:
                self.__instruments.pop(i)

        self.getNextDatePos()

        return bars.Bars(ret)