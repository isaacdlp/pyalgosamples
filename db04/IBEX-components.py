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

import csv
from openpyxl import load_workbook
import warnings
import datetime
import mysql.connector
import decimal

warnings.simplefilter('ignore')

def getList(idxCsv, index, cnx):
    cursor = cnx.cursor()
    with open(idxCsv, "rU") as fileIn:
        csvIn = csv.reader(fileIn)
        csvIn.next()
        idxList = []
        lastEvtDateTime = None
        for row in csvIn:
            evtDateTime = datetime.datetime.strptime(row[0],"%Y-%m-%d")
            if lastEvtDateTime != evtDateTime:
                if lastEvtDateTime:
                    recordList(lastEvtDateTime, index, idxList, cursor)
                lastEvtDateTime = evtDateTime
            for symbol in row[1].split():
                if symbol in idxList:
                    print("%s - symbol %s already in index" % (evtDateTime, symbol))
                else:
                    idxList.append(symbol)
            for symbol in row[2].split():
                if symbol in idxList:
                    idxList.remove(symbol)
                else:
                    print("%s - symbol %s not in index" % (evtDateTime, symbol))
        if lastEvtDateTime:
            recordList(lastEvtDateTime, index, idxList, cursor)
    cnx.commit()
    cursor.close()
    return idxList

def recordList(dateTime, index, instruments, cursor):
    sql = "INSERT IGNORE INTO grupo (fecha, indice, activo) VALUES (%s, %s, %s)"
    for instrument in instruments:
        params = [dateTime, index, instrument]
        cursor.execute(sql, params)

def recordData(fileName, cnx):
    wb = load_workbook(filename=fileName, read_only=True)
    sheets = wb.get_sheet_names()

    cursor = cnx.cursor()
    sql = "INSERT IGNORE INTO dato (activo, criterio, fecha, valor) VALUES (%s, %s, %s, %s)"

    for sheet in sheets:
        if sheet in ['__FDSCACHE__', 'Companies']:
            continue

        ws = wb.get_sheet_by_name(sheet)
        for y, row in enumerate(ws.rows):
            if y > 1:
                for x, concept in enumerate(['PBV', 'PER', 'DPS', 'NDE', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOL', 'ADJ']):
                    dateTime = row[x * 2].value
                    value = row[(x * 2) + 1].value
                    if dateTime != None and not isinstance(value, str):
                        if isinstance(value, float):
                            value = round(value, 10)
                        params = [sheet, concept, dateTime, value]
                        cursor.execute(sql, params)
                    elif concept != 'NDE':
                        print "%s %s %s %s %s" % (sheet, dateTime, concept, value, type(value))

        cnx.commit()

    cursor.close()


def validateData(cnx, cnx2):
    cursor = cnx.cursor()
    sql = "SELECT DISTINCT(activo) FROM dato"
    cursor.execute(sql)
    instruments = []
    for row in cursor:
        instruments.append(row[0])


    prob = 0

    for instrument in instruments:
        sql = "SELECT fecha, criterio, valor FROM dato WHERE activo = %s ORDER BY fecha ASC"
        lastDateTime = None
        dateTime = None
        cursor.execute(sql, [instrument])
        Open = None
        High = None
        Low = None
        Close = None
        for row in cursor:
            dateTime = row[0]

            if lastDateTime == None:
                lastDateTime = dateTime
            if lastDateTime != dateTime:

                fixer = cnx2.cursor()

                isDie = False
                if not Close:
                    print "MISSING CLOSE"
                    print "%s %s %s %s %s %s" % (instrument, lastDateTime, Open, High, Low, Close)

                    if Open:
                        Close = Open
                    elif High:
                        Close = High
                    elif Low:
                        Close = Low
                    else:
                        print "DELETED"
                        fixer.execute("DELETE FROM dato WHERE activo = %s AND fecha = %s",
                                      [instrument, lastDateTime])
                        cnx2.commit()
                        isDie = True

                if not isDie:
                    if not High:
                        prob += 1
                        High = Close
                        print "%s MISSING HIGH" % prob
                        fixer.execute("INSERT INTO dato (valor, activo, criterio, fecha) VALUES (%s, %s, %s, %s)",
                                     [Close, instrument, 'HIGH', lastDateTime])
                        cnx2.commit()
                    if not Low:
                        prob += 1
                        Low = Close
                        print "%s MISSING LOW" % prob
                        fixer.execute("INSERT INTO dato (valor, activo, criterio, fecha) VALUES (%s, %s, %s, %s)",
                                     [Close, instrument, 'LOW', lastDateTime])
                        cnx2.commit()
                    if not Open:
                        prob += 1
                        Open = Close
                        print "%s MISSING OPEN" % prob
                        fixer.execute("INSERT INTO dato (valor, activo, criterio, fecha) VALUES (%s, %s, %s, %s)",
                                      [Close, instrument, 'OPEN', lastDateTime])
                        cnx2.commit()

                    if High < Low:
                        print "high < low on"
                        isDie = True
                    elif High < Open:
                        prob += 1
                        print "%s high < open" % prob
                        fixer.execute("UPDATE dato SET valor = %s WHERE activo = %s AND criterio = %s AND fecha = %s",
                                     [Open, instrument, 'HIGH', lastDateTime])
                        cnx2.commit()
                    elif High < Close:
                        prob += 1
                        print "%s high < close" % prob
                        fixer.execute("UPDATE dato SET valor = %s WHERE activo = %s AND criterio = %s AND fecha = %s",
                                      [Close, instrument, 'HIGH', lastDateTime])
                        cnx2.commit()
                    elif Low > Open:
                        prob += 1
                        print "%s low > open" % prob
                        fixer.execute("UPDATE dato SET valor = %s WHERE activo = %s AND criterio = %s AND fecha = %s",
                                      [Open, instrument, 'LOW', lastDateTime])
                        cnx2.commit()
                    elif Low > Close:
                        prob += 1
                        print "%s low > close" % prob
                        fixer.execute("UPDATE dato SET valor = %s WHERE activo = %s AND criterio = %s AND fecha = %s",
                                      [Close, instrument, 'LOW', lastDateTime])
                        cnx2.commit()
                else:
                    pass
                    #print "%s %s %s %s %s %s" % (instrument, lastDateTime, Open, High, Low, Close)
                    #exit(0)

                lastDateTime = dateTime
                Open = None
                High = None
                Low = None
                Close = None

            if row[1] == 'OPEN':
                Open = row[2]
            elif row[1] == 'HIGH':
                High = row[2]
            elif row[1] == 'LOW':
                Low = row[2]
            elif row[1] == 'CLOSE':
                Close = row[2]

        if lastDateTime != dateTime:

            fixer = cnx2.cursor()

            isDie = False
            if not Close:
                print "MISSING CLOSE"
                print "%s %s %s %s %s %s" % (instrument, lastDateTime, Open, High, Low, Close)
                exit(0)

                if Open:
                    Close = Open
                elif High:
                    Close = High
                elif Low:
                    Close = Low
                else:
                    exit(0)

                fixer.execute("INSERT INTO dato (valor, activo, criterio, fecha) VALUES (%s, %s, %s, %s)",
                              [Close, instrument, 'HIGH', lastDateTime])
                cnx2.commit()

            if not High:
                prob += 1
                High = Close
                print "%s MISSING HIGH" % prob
                fixer.execute("INSERT INTO dato (valor, activo, criterio, fecha) VALUES (%s, %s, %s, %s)",
                              [Close, instrument, 'HIGH', lastDateTime])
                cnx2.commit()
            if not Low:
                prob += 1
                Low = Close
                print "%s MISSING LOW" % prob
                fixer.execute("INSERT INTO dato (valor, activo, criterio, fecha) VALUES (%s, %s, %s, %s)",
                              [Close, instrument, 'LOW', lastDateTime])
                cnx2.commit()
            if not Open:
                prob += 1
                Open = Close
                print "%s MISSING OPEN" % prob
                fixer.execute("INSERT INTO dato (valor, activo, criterio, fecha) VALUES (%s, %s, %s, %s)",
                              [Close, instrument, 'OPEN', lastDateTime])
                cnx2.commit()

            if High < Low:
                print "high < low on"
                isDie = True
            elif High < Open:
                prob += 1
                print "%s high < open" % prob
                fixer.execute("UPDATE dato SET valor = %s WHERE activo = %s AND criterio = %s AND fecha = %s",
                              [Open, instrument, 'HIGH', lastDateTime])
                cnx2.commit()
            elif High < Close:
                prob += 1
                print "%s high < close" % prob
                fixer.execute("UPDATE dato SET valor = %s WHERE activo = %s AND criterio = %s AND fecha = %s",
                              [Close, instrument, 'HIGH', lastDateTime])
                cnx2.commit()
            elif Low > Open:
                prob += 1
                print "%s low > open" % prob
                fixer.execute("UPDATE dato SET valor = %s WHERE activo = %s AND criterio = %s AND fecha = %s",
                              [Open, instrument, 'LOW', lastDateTime])
                cnx2.commit()
            elif Low > Close:
                prob += 1
                print "%s low > close" % prob
                fixer.execute("UPDATE dato SET valor = %s WHERE activo = %s AND criterio = %s AND fecha = %s",
                              [Close, instrument, 'LOW', lastDateTime])
                cnx2.commit()

            if isDie:
                print "%s %s %s %s %s %s" % (instrument, lastDateTime, Open, High, Low, Close)
                exit(0)

            lastDateTime = dateTime
            Open = None
            High = None
            Low = None
            Close = None

    cursor.close()



config = {
    'user': 'root',
    'password': '',
    'host': 'localhost',
    'database': 'ibex35',
    'raise_on_warnings': True
}
cnx = mysql.connector.connect(**config)
cnx.isolation_level = None  			# To do auto-commit

cnx2 = mysql.connector.connect(**config)
cnx2.isolation_level = None

#getList('IBEX-components.csv', 'IBEX35', cnx)
#recordData('IBEX_DATA.xlsx', cnx)
validateData(cnx, cnx2)

cnx2.close()
cnx.close()