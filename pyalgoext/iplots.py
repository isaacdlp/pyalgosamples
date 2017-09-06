from pyalgotrade import plotter
from plotly.offline import plot as do_plot
import plotly.tools as tls

def series_plot(self, mplSubplot, dateTimes, color):
   values = []
   for dateTime in dateTimes:
       values.append(self.getValue(dateTime))
   mplSubplot.plot(dateTimes, values, color=color, marker=self.getMarker(), label=self.name)

plotter.Series.plot = series_plot

def subplot_plot(self, mplSubplot, dateTimes):
    for series in self._Subplot__series.values():
        color = None
        if series.needColor():
            color = self._Subplot__getColor(series)
        series.plot(mplSubplot, dateTimes, color)

    # Legend
    # mplSubplot.legend(self._Subplot__series.keys(), shadow=True, loc="best")
    self.customizeSubplot(mplSubplot)

def subplot_getSeries(self, name, defaultClass=plotter.LineMarker):
    try:
        ret = self._Subplot__series[name]
    except KeyError:
        ret = defaultClass()
        ret.name = name
        self._Subplot__series[name] = ret
    return ret

plotter.Subplot.plot = subplot_plot
plotter.Subplot.getSeries = subplot_getSeries

def plot(fig, resize=True, strip_style=False, strip_notes=False, filename='temp-plot.html'):
    plotly_fig = tls.mpl_to_plotly(fig, resize=resize, strip_style=strip_style)

    fl = plotly_fig['layout']
    fl['showlegend'] = True
    fl['legend'] = {}
    fl['legend'].update({'x': 1.01, 'y': 1, 'borderwidth': 1, 'bgcolor': 'rgb(217,217,217)'})
    if strip_notes:
        fl['annotations'] = []
    for key, value in fl.items():
        if key.startswith("xaxis"):
            value['hoverformat'] = '%Y-%m-%d'

    do_plot(plotly_fig, filename=filename)

