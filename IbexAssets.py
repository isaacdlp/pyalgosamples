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

folder = "./data/"

endYear = 2016

indices = {
    "^IBEX": 2010,
}

instruments = {
    "ABE.MC": 2010,
    "ACS.MC": 2010,
    "ACX.MC": 2010,
    #"AENA.MC": 2015,
    "ANA.MC": 2010,
    #"AMS.MC": 2010,
    "BBVA.MC": 2010,
    #"BKIA.MC": 2011,
    "BKT.MC": 2010,
    "CABK.MC": 2010,
    #"DIA.MC": 2011,
    "ELE.MC": 2010,
    "ENG.MC": 2010,
    "FCC.MC": 2010,
    "FER.MC": 2010,
    "GAM.MC": 2010,
    "GAS.MC": 2010,
    "GRF.MC": 2010,
    "IAG.MC": 2011,
    "IBE.MC": 2010,
    "IDR.MC": 2010,
    "ITX.MC": 2010,
    "MAP.MC": 2010,
    #"MRL.MC": 2014,
    "MTS.MC": 2010,
    "OHL.MC": 2010,
    "POP.MC": 2010,
    "REE.MC": 2010,
    "REP.MC": 2010,
    "SAB.MC": 2010,
    "SAN.MC": 2010,
    "SCYR.MC": 2010,
    "TEF.MC": 2010,
    "TL5.MC": 2010,
    "TRE.MC": 2010
}

all = {}
all.update(indices.copy())
all.update(instruments.copy())