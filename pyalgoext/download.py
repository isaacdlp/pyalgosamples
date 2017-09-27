import quandl
import datetime
import time
import pandas as pd

def quandl_bitcoin(instrument, store):
    df = quandl.get(instrument, returns="pandas")
    df.to_csv(store,
        columns=["Open", "High", "Low", "Close", "Volume (Currency)", "Close"],
        header=["Open", "High", "Low", "Close", "Volume", "Adj Close"]
    )

def poloniex_crypto(poloniex_pair, store, start_date=None, end_date=None):
    base_polo_url = 'https://poloniex.com/public?command=returnChartData&currencyPair={}&start={}&end={}&period={}'
    if start_date is None:
        start_date = datetime.datetime.strptime('2015-01-01', '%Y-%m-%d')  # get data from the start of 2015
    if end_date is None:
        end_date = datetime.datetime.now()  # up until today
    pediod = 86400  # pull daily data (86,400 seconds per day)
    start_time = int(time.mktime(start_date.timetuple()))
    end_time = int(time.mktime(end_date.timetuple()))

    json_url = base_polo_url.format(poloniex_pair, start_time, end_time, pediod)
    df = pd.read_json(json_url)
    df = df.set_index('date')
    df.index.rename("Date", inplace=True)
    df.to_csv(store,
        columns=["open", "high", "low", "close", "quoteVolume", "close"],
        header=["Open", "High", "Low", "Close", "Volume", "Adj Close"]
    )
