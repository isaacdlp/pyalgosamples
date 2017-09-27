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


import pandas as pd
import plotly.offline as py
import plotly.graph_objs as go
from pyalgoext import iplots

df = pd.read_csv("data/BTC_ETH.csv")
df.set_index("Date", inplace=True)

viz = go.Scatter(x=df.index, y=df['Adj Close'])
filename = "../store/btc-eth-poloniex-augmented.html"
py.plot([viz], filename=filename, auto_open=False)

# This line makes the difference!
iplots.augment(filename)


