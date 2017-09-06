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
import datetime
from lxml import html
import requests

def getList(idxCsv, idxDateTime=None):
    if not idxDateTime:
        idxDateTime = datetime.datetime.now()
    with open(idxCsv, "rU") as fileIn:
        csvIn = csv.reader(fileIn)
        csvIn.next()
        idxList = []
        for row in csvIn:
            evtDateTime = datetime.datetime.strptime(row[0],"%Y-%m-%d")
            if evtDateTime > idxDateTime:
                break
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
    return idxList

def getListFromYahoo(index):
    components = []
    n = 0
    while True:
        page = requests.get("http://finance.yahoo.com/q/cp?s=%s&c=%s" % (index, n))
        tree = html.fromstring(page.content)
        assets = tree.xpath("//td[@class=\"yfnc_tabledata1\"]/b/a/text()")
        if assets:
            components.extend(assets)
            n += 1
        else:
            break
    return components

