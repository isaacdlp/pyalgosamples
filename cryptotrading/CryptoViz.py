import pandas as pd
import plotly.offline as py
import plotly.graph_objs as go

df = pd.read_csv("data/BTC_ETH.csv")
df.set_index("Date", inplace=True)

viz = go.Scatter(x=df.index, y=df['Adj Close'])
py.plot([viz], filename="../store/btc-eth-poloniex.html")

