#!/usr/bin/env python

"""
Retrieve stock quote data from Yahoo and forex rate data from Oanda.
"""

##################################################
# Name:        pyQ - Python Quote Grabber
# Author:      Rimon Barr <barr@cs.cornell.edu>
# Start date:  10 January 2002
# Purpose:     Retrieve stock quote data in Python
# License:     GPL 2.0

##################################################
# Activity log:
#
# 10/01/02 - Initial release
# 14/10/02 - Yahoo changed url format
# 31/10/02 - More convenient programmatic interface and local caching
# 21/09/04 - Updated by Alberto Santini to accomodate Yahoo changes
# 27/01/05 - Updated by Alberto Santini to accomodate Yahoo changes
# 11/01/07 - Updated by Ehud Ben-Reuven, Historical currency exchnage tickers
#            (e.g. USDEUR=X) are retrieved from www.oanda.com
# 15/03/07 - code cleanup; updated Yahoo date format, thanks to Cade Cairns
# 11/04/12 - 0.7.1 Walter Prins: Fixed exception handling during long runs
#            where ctrl-c would get caught by unconditional exception clauses.
#            Fixed regular expression that detects non-existtickers/data.
#            Fixed fetching of current quote for multiple tickers.
#            Cleaned up/refactored to 99% pass PyLint, Pep8 and Pychecker.
# 13/04/12   0.7.2 WP: Start/End date specified as 0 assumes todays date.
#            Replaced time module with datetime to fix handling
#            of dates prior to 01/01/1970. (E.g. ticker ^DJI starts 19281001.)
#            Fixed 2 regressions from 0.7.1.
#            Changed default location of cache.db to script location so running
#            the script from different locations will use the same cache.
# 06/07/12   - Added support for scraping quotes directly off the web page for
#              tickers that do not support download via the ichart URL but does
#              support display of data (e.g. ^DJI)
#            - Added a feature whereby data will be retrieved for todays day
#              from the live quote page if not available in the history.
#            - A few other tweaks and fixes.
# 07/07/12   - Modified Yahoo webpage parser to deal with thousand seperators
#              in long numbers.
#            - Ensure dividend declaration lines get stripped out properly
# 28/10/12   - Tidied up code (PEP8/Lint)
#            - Added a check for "N/A" values from the live site to prevent
#              same from being output.
# 02/11/12   - Improved handling of holidays/not available days.  Data points
#              that are missing from a query date range that otherwise
#              succeeded without error are now marked as "NA", which means
#              they will not be retried as missing on retry attempts.
# 05/11/2012 - Fixed web-scraping to loop and fetch 66 records at a time.
#              Fixed web-scraping where some data rows on some tickers use
#              a different date format to the rest (e.g. ^DJT)
# 09/11/2012 - Added support for retrieving through proxies, potentially with
#              basic authentication (as specified in proxy URL.)  Basic
#              authentication hasn't been tested.
# 12/11/2012 - Fixed a bug introduced through the introduction of urllib2.
#              Basically ^DJI page was now raising an exception on no data
#              which the code wasn't expecting.

import sys, re, traceback, getopt, urllib2, urllib, anydbm, datetime, os

Y2KCUTOFF = 60
__version__ = "0.7.7"
CACHE = 'stocks.db'
DEBUG = 0 #Set to 1 or higher for successively more debug information.
# Set proxy URL if applicable, otherwise None.
# Proxy URL syntax: http://username:password@proxyhost:proxyport
# If no user/pass is required then leave off.
PROXYURL = None


def dbg_print(level, msg):
    """ Utility method to handle debug output.  Messages are only printed
    if the DEBUG level is equal to or higher than the msg level.  Thus
    setting DEBUG = 0 will disable all debug output while higher values
    will increase debug output successively. """
    if DEBUG >= level:
        if DEBUG > 1:
            levelstr = '[%d]' % level
        else:
            levelstr = ''
        print >> sys.stderr, '#%s %s' % (levelstr, msg)


def print_header():
    """Print program header information to stdout"""
    print 'pyQ v%s, by Rimon Barr:' % __version__
    print '- Python Yahoo Quote fetching utility'


def exit_version():
    """Display version message to command line user."""
    print_header()
    sys.exit(0)


def exit_usage():
    """Display usage/help message to command line user."""
    print_header()
    print """
Usage: pyQ [-i] [start_date [end_date]] ticker [ticker...]
             pyQ -h | -v

    -h, -?, --help        display this help information
    -v, --version         display version'
    -i, --stdin           tickers fed on stdin, one per line
    -r:n, --retryfailed=n Retry failed request control value.

    - date formats are yyyymmdd
    - if start and/or enddate is specified as 0 they assume todays date.
    - if enddate is omitted, it is assumed to be the same as startdate
    - if startdate is omitted, we use *current* stock tables and otherwise, use
        historical stock tables. Current stock tables will give previous close
        price before market closing time.)
    - tickers are exactly what you would type at finance.yahoo.com
    - retry control value n is defined as follows:
            =0 : do not retry failed data points
            >0 : retry failed data points n times
            -1 : retry failed data points, reset retry count
            -2 : ignore cache entirely, refresh ALL data points
    - output format: "ticker, date (yyyymmdd), open, high, low, close, vol"
    - currency exchange rates are also available, but only historically.
        The yahoo ticker for an exchange rate is of the format USDEUR=X. The
        output format is "ticker, date, exchange".

    Send comments, suggestions and bug reports to <wprins@gmail.com>
"""
    sys.exit(0)


def exit_usage_error():
    """Display error message to command line user."""
    sys.exit("pyQ: command syntax error\n" +
             "Try 'pyQ --help' for more information.")


def is_int(i):
    """Checks whether the given object can be converted to an integer"""
    try:
        int(i)
        return 1
    except ValueError:
        return 0


def split_lines(buf):
    """Splits the given buffer on newlines and strips each line"""
    return [line.strip() for line in buf.split('\n')]


def parse_date(yyyymmdd):
    """Convert yyyymmdd string to tuple (yyyy, mm, dd)"""
    return (yyyymmdd[:-4], yyyymmdd[-4:-2], yyyymmdd[-2:])


def yy2yyyy(yy_2digits):
    """Convert a 2 digit century string to a 4 digit century string."""
    yy_2digits = int(yy_2digits) % 100
    if yy_2digits < Y2KCUTOFF:
        return repr(yy_2digits + 2000)
    else:
        return repr(yy_2digits + 1900)


# convert month to number
MONTH2NUM = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}


def dd_mmm_yy2yyyymmdd(dd_mmm_yy):
    """Convert a dd_mmm_yy string to yyyymmdd format"""
    dd_mmm_yy = dd_mmm_yy.split('-')
    day = '%02d' % int(dd_mmm_yy[0])
    month = '%02d' % MONTH2NUM[dd_mmm_yy[1]]
    year = yy2yyyy(dd_mmm_yy[2])
    return year + month + day


def all_dates(startdate, enddate):
    """Return all dates between and including startdate and enddate  in
    ascending order.  Inputs in yyyymmdd format. Excludes weekends."""
    if int(startdate) > int(enddate):
        raise IndexError('startdate must be smaller than enddate')

    startdate = datetime.datetime.strptime(startdate, '%Y%m%d')
    enddate = (datetime.datetime.strptime(enddate, '%Y%m%d')
               + datetime.timedelta(days=1))
    dates = []
    while startdate < enddate:
        if not startdate.weekday() in (5, 6):
            dates.append(startdate.strftime('%Y%m%d'))
        startdate += datetime.timedelta(days=1)

    return dates


def agg_dates(dates):
    """Aggregate list of dates (yyyymmdd) in range pairs"""
    if not dates:
        return []
    aggs = []
    dates = [datetime.datetime.strptime(date, '%Y%m%d') for date in dates]
    dates.sort()
    high = dates.pop(0)
    low = high
    for date in dates:
        if date == high + datetime.timedelta(days=3) and date.weekday()==0:
            high = date
        elif date == high + datetime.timedelta(days=1):
            high = date
        else:
            aggs.append(( low.strftime('%Y%m%d'), high.strftime('%Y%m%d'),))
            high = date
            low = high
    aggs.append((low.strftime('%Y%m%d'), high.strftime('%Y%m%d'),))
    return aggs


def get_oanda_fxrate(startdate, enddate, ticker):
    """Retrieve FX exchange closing rates for the pair specified as "ZZZYYY=X"
    where ZZZ is the one currency and YYY is the other currency. Only the
    closing rate is fetched as that's all that's available."""
    dbg_print(1, 'Querying Oanda historical for %s (%s-%s)' %
                   (ticker, startdate, enddate))
    if not (len(ticker) == 8 and ticker.endswith('=X')):
        raise Exception('Illegal FX rate ticker')

    cur1, cur2 = ticker[0:3], ticker[3:6]

    def yyyymmdd2mmddyy(yyyymmdd):
        """Converts a date string in format yyyymmdd to mmddyy format."""
        return yyyymmdd[4:6] + '%2F' + yyyymmdd[6:8] + '%2F' + yyyymmdd[2:4]

    def mmddyy2yyyymmdd(mmddyy):
        """Converts a date string in format mmddyy to  yyyymmdd format."""
        if len(mmddyy) != 10 or mmddyy[2] != '/' or mmddyy[5] != '/':
            raise Exception('Illegal date format')
        return mmddyy[6:10] + mmddyy[0:2] + mmddyy[3:5]

    startdate, enddate = yyyymmdd2mmddyy(startdate), yyyymmdd2mmddyy(enddate)
    url = 'http://www.oanda.com/convert/fxhistory'
    query = (
        ('lang', 'en'),
        ('date1', startdate),
        ('date', enddate),
        ('date_fmt', 'us'),
        ('exch', cur1),
        ('exch2', ''),
        ('expr', cur2),
        ('expr2', ''),
        ('margin_fixed', '0'),
        ('SUBMIT', 'Get+Table'),
        ('format', 'CSV'),
        ('redirected', '1')
        )
    query = ['%s=%s' % (var, val) for (var, val) in query]
    query = '&'.join(query)
    page = urllib2.urlopen(url + '?' + query).read().splitlines()
    table = False
    result = []
    for line in page:
        if line.startswith('<PRE>'):
            table = True
            line = line[5:]
        elif line.startswith('</PRE>'):
            table = False
        if table:
            line = line.split(',')
            line[0] = mmddyy2yyyymmdd(line[0])
            line = [ticker] + line
            result.append(line)
    return result

class TickerDataNotFound(Exception):
    """Exception that is raised when Yahoo reports ticker/data not found"""
    pass


from HTMLParser import HTMLParser
class YahooHTMLPriceTableParser(HTMLParser):
    """Parse the quote data from the Yahoo quote page HTML soup"""
    def __init__(self, ticker):
        HTMLParser.__init__(self)
        self.ticker = ticker
        self.table = False
        self.prices = False
        self.row = None
        self.colno = 0
        self.rowno = 0
        self.output = []

    def handle_starttag(self, tag, _): # third param "attrs" not used
        if tag == 'table':
            if self.prices and self.output == []:
                self.table = True
        if self.table and self.prices:
            dbg_print(5, "Encountered a start tag: %s" % tag)
            if tag == 'tr':
                self.row = [self.ticker]
                self.colno = 1
                self.rowno += 1

    def handle_endtag(self, tag):
        if tag == 'table':
            if self.table:
                dbg_print(5, "Encountered an end tag : %s" % tag)
            self.table = False
        if self.table and self.prices:
            dbg_print(5, "Encountered an end tag : %s" % tag)
            if tag == 'tr':
                if self.row != None and self.row != [self.ticker]:
                    self.output.append(self.row)
                    self.row = None
            if tag == 'td' or tag == 'th':
                self.colno += 1

    def handle_data(self, data):
        if data == 'Prices':
            self.prices = True
        if self.table and self.prices:
            dbg_print(5,"Encountered some data : %s" % data)
            data = data.strip()
            if (data.startswith('Close price adjusted for')
                or data == '*' #* = dividend comment line
                or data.endswith('Dividend')): # Dividend data line
                self.row = None
            if not self.row is None:
                if self.rowno >= 3:
                    if self.colno == 1:
                        try:
                            data = datetime.datetime.strptime(
                                data,'%b %d, %Y').strftime('%Y%m%d')
                        except ValueError:
                            #Some datarows on Yahoo uses alterante date fmt...
                            data = datetime.datetime.strptime(
                                data,'%Y-%m-%d').strftime('%Y%m%d')
                    if self.colno >= 2:
                        data = data.replace(',','')
                self.row.append(data)


def get_yahoo_ticker_scrape(startdate, enddate, ticker):
    """Get historical ticker data for the specified date from Yahoo
    using the normal display page URL http://http://finance.yahoo.com/q/hp?
    by scraping/parsing the HTML page itself.  We are forced to resorting
    to this scraping because some tickers are not enabled for downloading
    via the ichart URL, for example "^DJI". Example URL:
    #http://finance.yahoo.com/q/hp?s=^DJI&d=6&e=6&f=2012&g=d&a=0&b=2&c=1992&z=66&y=66
    """
    dbg_print(1, 'Querying Yahoo! website direct for %s (%s-%s)' %
                   (ticker, startdate, enddate))
    num_rows_ubound = len(all_dates(startdate, enddate))
    dbg_print(3, 'Estimated number of rows to fetch: %d' % num_rows_ubound )
    startdate, enddate = parse_date(startdate), parse_date(enddate)
    # As Yahoo will only output on the website 66 rows max at a time, we have
    # to loop to retrieve all the results.  When we get a page with
    # "quote data not available" we stop.
    done = False
    starting_row = 0
    result = []
    while not done:
        url = 'http://finance.yahoo.com/q/hp'
        query = (
            ('s', ticker),
            ('d', '%02d' % (int(enddate[1]) - 1)),
            ('e', enddate[2]),
            ('f', enddate[0]),
            ('g', 'd'),
            ('a', '%02d' % (int(startdate[1]) - 1)),
            ('b', startdate[2]),
            ('c', startdate[0]),
            ('z', 66), #page controls, no of records per page, 66=max supported
            ('y', starting_row),
            )
        query = ['%s=%s' % (var, str(val)) for (var, val) in query]
        query = '&'.join(query)
        url = url + '?' + query
        dbg_print(3, 'URL: %s' % url )
        urldata = urllib2.urlopen(url).read()
        dbg_print(4, 'Result: %s' % urldata )

        match = re.search('quote data is unavailable', urldata, re.I)
        done = (not match is None) or (starting_row > num_rows_ubound)

        if not done:
            parser = YahooHTMLPriceTableParser(ticker)
            parser.feed(urldata)

            result.extend(parser.output[1:])
            starting_row += 66

    if match is None and len(result)==0:
        raise TickerDataNotFound(
            ('Ticker/Ticker data %s for specified '+
             'date range not found or not available.') % ticker)
    return result


def get_yahoo_ticker_historical(startdate, enddate, ticker,
                                allow_scraping=True):
    """Get historical ticker data for the specified date from Yahoo
    using the http://ichart.finance.yahoo.com/table.csv download URL.
    Note, this URL doesn't work for all tickers, for example ^DJI.
    This is because Yahoo is not licensed to allow download for some
    tickers.  As a consequence, the routine will also fall back to
    a direct scrape of the displayed page if the http://ichart URL
    fails. See get_yahoo_ticker_historical_webscrape.
    """
    dbg_print(1, 'Querying Yahoo! history for %s (%s-%s)' %
                   (ticker, startdate, enddate))
    parsed_startdate = parse_date(startdate)
    parsed_enddate = parse_date(enddate)
    url = 'http://ichart.finance.yahoo.com/table.csv'
    query = (
        ('a', '%02d' % (int(parsed_startdate[1]) - 1)),
        ('b', parsed_startdate[2]),
        ('c', parsed_startdate[0]),
        ('d', '%02d' % (int(parsed_enddate[1]) - 1)),
        ('e', parsed_enddate[2]),
        ('f', parsed_enddate[0]),
        ('s', ticker),
        ('y', '0'),
        ('g', 'd'),
        ('ignore', '.csv'),)
    query = ['%s=%s' % (var, str(val)) for (var, val) in query]
    query = '&'.join(query)
    url = url + '?' + query
    dbg_print(3, 'URL: %s' % url )
    try:
        urldata = urllib2.urlopen(url).read().strip()
        #urllib2 introduced the above url throwing HTTPError 404 on no data for
        # e.g. ^DJI.
        #so we unfortunately have to check for it here and handle it the same
        #way as our manual search in the page text does below.  To Refactor.
    except urllib2.HTTPError as e:
        if allow_scraping:
            return get_yahoo_ticker_scrape(startdate, enddate, ticker)
        else:
            raise TickerDataNotFound(
                ('Ticker/Ticker data %s for specified date range not found or '+
                 'not available.') % ticker)

    dbg_print(4, 'Result: %s' % urldata )
    lines = split_lines(urldata)
    dbg_print(5, 'Split lines: %s' % lines )
    match = re.search('no prices|404 Not Found', urldata, re.I)
    if not match is None:
        #If we fail using ichart URL then try scraping direct from
        #web page, if allowed:
        if allow_scraping:
            return get_yahoo_ticker_scrape(startdate, enddate, ticker)
        else:
            raise TickerDataNotFound(
                ('Ticker/Ticker data %s for specified date range not found or '+
                 'not available.') % ticker)

    lines, result = lines[1:], []
    for line in lines:
        line = line.split(',')
        result.append([ticker, line[0].replace('-', '')] + line[1:])
    return result


def get_cached_ticker(startdate, enddate, ticker, forcefailed=0):
    """Get requested tickers, hopefully from cache.
        startdate, enddate = yyyymmdd starting and ending
        ticker = symbol string
        forcefailed = integer for cachebehaviour
            =0 : do not retry failed data points
            >0 : retry failed data points n times
            -1 : retry failed data points, reset retry count
            -2 : ignore cache entirely, refresh ALL data points"""
    dbg_print(1, 'Querying cache for %s (%s-%s), forcefailed=%d' %
                   (ticker, startdate, enddate, forcefailed))
    dates = all_dates(startdate, enddate)
    # get from cache
    data = {}
    cache_db = anydbm.open(os.path.join(os.path.dirname(__file__), CACHE), 'c')
    for date in dates:
        try:
            data[(date, ticker)] = cache_db[repr((date, ticker))]
        except KeyError:
            pass
    # forced failed
    dbg_print(3, 'keys from db: %s' % data.keys())
    if forcefailed:
        for key in data.keys():
            if (forcefailed == -2 or
                  (type(eval(data[key])) == type(0)
                     and (forcefailed == -1 or eval(data[key]) < forcefailed)
                  )
                ):
                #cause date to be missing, effecting it to be refetched below
                del data[key]
    # compute missing
    cached = [date for date, _ in data.keys()]
    dbg_print(3, 'cached: %s' % cached)
    missing = [date for date in dates if date not in cached]
    dbg_print(3, 'missing: %s' % missing)
    # retry the missing dates
    for startdate, enddate in agg_dates(missing):
        try:
            if len(ticker) == 8 and ticker.endswith('=X'):
                tickerdatalist = get_oanda_fxrate(startdate, enddate, ticker)
            else:
                tickerdatalist = get_yahoo_ticker_historical(startdate,
                                                             enddate, ticker)
            dbg_print(3, 'data from web: %s' % tickerdatalist)
            for row in tickerdatalist:
                _, date, datum = row[0], row[1], row[2:]
                r_datum = repr(datum)
                data[(date, ticker)] = cache_db[repr((date, ticker))] = r_datum

            # Mark dates for which Yahoo legitimately aren't
            # returning data (holidays etc) as permanently NA.
            # But we assume that recent dates are truly missing and dont
            # mark them, so we'll retry recent missing dates that Yahoo
            # maybe doesn't have yet. Always exclude today and future dates.
            cached = [date for date, _ in data.keys()]
            all_dates_desc=sorted(all_dates(startdate, enddate), reverse=True)
            seen_one_date = False
            for date in all_dates_desc:
                if not seen_one_date and date in cached:
                    seen_one_date = True
                if seen_one_date and date not in cached and date < datetime.date.today().strftime('%Y%m%d'):
                    dbg_print(3, 'marking date %s as NA in DB for %s' % (date, ticker))
                    data[(date, ticker)] = cache_db[repr((date, ticker))] = repr('NA')
        except TickerDataNotFound:
            errmsg = "Data for %s between %s and %s not found or not available."
            errmsg = errmsg % (ticker, startdate, enddate)
            print >> sys.stderr, errmsg
    # failed
    cached = [date for date, row in data.keys()]
    failed = [date for date in missing if date not in cached]
    dbg_print(3, 'failed: %s' % failed)
    for date in failed:
        try:
            times = eval(cache_db[repr((date, ticker))])
        except KeyError:
            times = 0
        if forcefailed < 0:
            times = 1
        if times < forcefailed:
            times = times + 1
        data[(date, ticker)] = cache_db[repr((date, ticker))] = repr(times)
    # result
    result = []
    for date in dates:
        datum = eval(data[(date, ticker)])
        if datum != 'NA' and  type(datum) != type(0):
            result.append([ticker, date] + datum)
        elif date == datetime.date.today().strftime('%Y%m%d'):
            datum = get_yahoo_tickers_live([ticker])
            if datum != []:
                dbg_print(3, 'Live Datum retrieved: %s = %s' % (date, datum[0]))
                result.append(datum[0])
    return result


def get_tickers(startdate, enddate, tickers, forcefailed=0):
    """Get tickers.
        startdate, enddate = yyyymmdd starting and ending
        tickers = list of symbol strings
        forcefailed = integer for cachebehaviour
            =0 : do not retry failed data points
            >0 : retry failed data points n times
            -1 : retry failed data points, reset retry count
            -2 : ignore cache entirely, refresh ALL data points"""
    starttime = datetime.datetime.now()
    dbg_print(0, '%s : Fetching %s tickers' % (starttime, len(tickers)))
    result = []
    for ticker in tickers:
        dbg_print(0, '%s' % (ticker))
        tickerdata = get_cached_ticker(startdate, enddate, ticker, forcefailed)
        result.extend(tickerdata)
    endtime = datetime.datetime.now()
    dbg_print(0, '%s : Done. Processed %s tickers in %s' % (endtime, len(tickers), endtime - starttime))
    return result


def _get_yahoo_tickers_live(tickers):
    """Get current value of specified tickers directly from Yahoo."""
    dbg_print(1, 'Querying Yahoo! live for %s' % (tickers))
    # For a reference to how this URL is constructed, see here:
    #http://www.gummy-stuff.org/Yahoo-data.htm
    url = 'http://finance.yahoo.com/d/quotes.csv?%s' % urllib.urlencode(
            {'s': '+'.join(tickers), 'f': 'sohgl1v', 'e': '.csv'})
    dbg_print(3, 'URL: %s' % url )
    urldata = urllib2.urlopen(url).read().strip()
    dbg_print(3, 'Result: %s' % urldata )

    if not re.match("Missing Symbols List", urldata, re.I) is None:
        raise TickerDataNotFound(
            'None of the tickers specified has live quotes available.')

    lines = split_lines(urldata)
    today = datetime.date.today()
    result = []
    for line in lines:
        line = line.split(',')
        if 'N/A' in (line[1], line[2], line[3], line[4]):
            dbg_print(1, 'Warning: Data for '
                        +line[0][1:-1]+','
                        +today.strftime('%Y%m%d')
                        +' contains N/A values. Excluding.' )
        else:
            result.append(
                [
                 (line[0][1:-1]),  #Ticker
                 today.strftime('%Y%m%d'),  #Date
                 line[1], #open
                 line[2], #high
                 line[3], #low
                   #avg of current bid & ask as close:
                   #str((float(line[4])+float(line[5]))/2)
                 line[4], #last trade price (in lieu of close)
                 line[5], # volume
                 line[4]  #last trade price again (in lieu of adjclose)
                ]
                )
    return result


def get_yahoo_tickers_live(tickers):
    """Get current value of specified tickers directly from Yahoo, in batches
    of 150 tickers at a time."""
    result = []
    while tickers:
        try:
            result += _get_yahoo_tickers_live(tickers[:150])
        except TickerDataNotFound:
            errmsg = "Failed to find live quotes for tickers %s" % tickers
            print >> sys.stderr, errmsg
        tickers = tickers[150:]
    return result


def arg_startdate(args):
    """Parse the startdate from the command line."""
    startdate = datetime.date.today().strftime('%Y%m%d')
    if len(args) >= 1 and is_int(args[0]) and int(args[0]) > 0:
        startdate = args[0]
    dbg_print(1, "Startdate: %s" % startdate)
    return startdate


def arg_enddate(args):
    """Parse the enddate from the command line."""
    enddate = arg_startdate(args)
    if len(args) >= 2 and is_int(args[1]):
        if int(args[1]) == 0:
            enddate = datetime.date.today().strftime('%Y%m%d')
        else:
            enddate = args[1]
    dbg_print(1, "Enddate: %s" % enddate)
    return enddate


def arg_fetchlive(args):
    """Parse the fetchlive parameter from the command line."""
    fetchlive = 1
    if len(args) >= 1 and is_int(args[0]):
        fetchlive = 0
    dbg_print(1, "Fetchlive: %s" % fetchlive)
    return fetchlive


def arg_tickers(args):
    """Parse the tickers from the command line."""
    tickers = []
    for arg in args:
        if not is_int(arg):
            tickers.append(arg.upper())
    dbg_print(1, "Tickers: %s" % tickers)
    return tickers


def main():
    """Main program: Implements arg command line interface to fetching stock
    data from Yahoo."""
    # parse options
    try:
        opts, args = getopt.getopt(
            sys.argv[1:], 'hv?ir:', ['help', 'version', 'stdin', 'retryfailed=']
            )
    except getopt.GetoptError:
        exit_usage_error()

    # setup proxy
    if not PROXYURL is None:
        proxy = urllib2.ProxyHandler({'http': PROXYURL})
        auth = urllib2.HTTPBasicAuthHandler()
        opener = urllib2.build_opener(proxy, auth, urllib2.HTTPHandler)
        urllib2.install_opener(opener)

    # process options
    stdin_tickers = []
    retryfailed = 0
    for option, optarg in opts:
        if option in ("-h", "--help", "-?"):
            exit_usage()
        if option in ("-v", "--version"):
            exit_version()
        if option in ("-i", "--stdin"):
            stdin_tickers = split_lines(sys.stdin.read())
            dbg_print(1, "Reading tickers from stdin.")
        if option in ("-r", "--retryfailed"):
            retryfailed = int(optarg)
            dbg_print(1, "Using cache retry value: %s" % retryfailed)

    startdate = arg_startdate(args)
    enddate = arg_enddate(args)
    fetchlive = arg_fetchlive(args)
    tickers = arg_tickers(args)
    tickers.extend(stdin_tickers)

    if len(tickers) == 0:
        exit_usage()

    if fetchlive:
        result = get_yahoo_tickers_live(tickers)
    else:
        result = get_tickers(startdate, enddate, tickers, retryfailed)

    for line in result:
        print ','.join(line)


try:
    if __name__ == '__main__':
        main()
except KeyboardInterrupt:
    traceback.print_exc()
    dbg_print(1, 'Break!')
