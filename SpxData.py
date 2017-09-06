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

import os
from pyq import pyq

indices = {
    "^GSPC" : 1950,
    "^SP500TR" : 1988
}

folder = "./data/"
if not os.path.isdir(folder):
    os.mkdir(folder)

for index, start in indices.items():
    for year in range(start, 2016):
        with open(folder + index + "-" + str(year) + ".csv", "w") as csv_file:
            csv_data = pyq.get_tickers(str(year) + "0101", str(year) + "1231", [index], False)
            # Format properly the rows
            for row in csv_data:
                row.pop(0)
                row[0] = row[0][0:4] + "-" + row[0][4:6] + "-" + row[0][6:8]
            # Insert the right header
            csv_data.insert(0, ["Date", "Open", "High", "Low", "Close", "Volume", "Adj Close"])

            for row in csv_data:
                csv_file.write(','.join(row) + os.linesep)
