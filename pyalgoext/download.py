import quandl


def quandl_bitcoin(instrument, store):
    df = quandl.get(instrument, returns="pandas")
    df.to_csv(store,
        columns=["Open", "High", "Low", "Close", "Volume (BTC)", "Close"],
        header=["Open", "High", "Low", "Close", "Volume", "Adj Close"]
    )