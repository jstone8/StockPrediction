# -*- coding: utf-8 -*-

import logging
import requests
import time
from typing import Sequence, List, Tuple, Dict
from datetime import datetime
from database import Database
from config import api_keys, db_init
from util import standardize_datetime, validate_date_fmt


def _build_url(base_url: str, params: dict) -> str:
    return base_url + '&'.join(['{0}={1}'.format(key, params[key]) for key in params])


class StockPrice(object):
    '''Collect time series data (price, volume, etc.) for specified symbol.
       See https://www.alphavantage.co/documentation/ for API details
    '''

    _base_url = 'https://www.alphavantage.co/query?'

    def __init__(self, symbol: str, outputsize: str = 'compact'):
        self.symbol = symbol
        self.outputsize = outputsize   # 'compact' or 'full'
        self.datatype = 'json'

        self.intraday_ts = {}
        self.daily_ts = {}


    def _get_time_series(self, function: str, interval: str = None) -> dict:
        '''Collect time series data using the API call

           @param: function: the time series of choice
           @param: interval: time interval between two consecutive data points
                             Only for intraday time series
           @return: decoded JSON object returned by API call
        '''

        params = {
            'apikey'    : api_keys['alpha_vantage'],
            'function'  : function,
            'symbol'    : self.symbol,
            'outputsize': self.outputsize,
            'datatype'  : self.datatype,
        }

        api_link = _build_url(StockPrice._base_url, params)
        if interval: api_link += '&interval={interval}'.format(interval=interval)

        r = requests.get(api_link)
        
        return r.json() if r.status_code == 200 else {}
    

    def get_intraday(self, interval: str):
        '''Collect intraday time series data'''

        assert interval in ('1min', '5min', '15min', '30min', '60min'), 'Unsupported interval'
        function = 'TIME_SERIES_INTRADAY'
        self.intraday_ts = self._get_time_series(function, interval)


    def get_daily_adjusted(self):
        '''Collect daily time series data'''

        function = 'TIME_SERIES_DAILY_ADJUSTED'
        self.daily_ts = self._get_time_series(function)


    def _prc_data(self, data: dict, trim_to_date: str = '1900-01-01') -> Sequence[tuple]:
        '''Process data for stock price/volume before inserting into database.
           Results are trimmed by date and sorted by datetime.
           Subjected to change with the table schema

           @param: data: collected time series data
           @param: trim_to_date: discard records earlier than the specified date, yyyy-mm-dd
           @return: List of tuples with order consistent with the table schema
        '''

        value_list = []

        if 'Meta Data' in data:
            interval = data['Meta Data'].get('4. Interval', 'Daily')
            key = 'Time Series ({interval})'.format(interval=interval)

            # assume the default timezone is US/Eastern
            for timestamp in sorted(data[key], reverse=True):
                if interval == 'Daily':
                    date_time = standardize_datetime(timestamp, '%Y-%m-%d', include_time=False)
                else:
                    date_time = standardize_datetime(timestamp, '%Y-%m-%d %H:%M:%S')

                if date_time >= trim_to_date:
                    vals = data[key][timestamp]     # keys in vals include index
                    temp_res = [date_time, 'US/Eastern'] + [vals[k] for k in sorted(vals)]
                    value_list.append(tuple(temp_res))
                else: 
                    break

        value_list.reverse() # from oldest to latest

        return value_list


    def prc_data(self, trim_to_date: str = '1900-01-01', db: str = ''):
        assert validate_date_fmt(trim_to_date, '%Y-%m-%d'), 'Date format must be yyyy-mm-dd'
        
        self.intraday_ts = self._prc_data(self.intraday_ts, trim_to_date)
        self.daily_ts = self._prc_data(self.daily_ts, trim_to_date)

        if db:
            if len(self.intraday_ts) > 0:
                Database.insert_data_intraday(db, self.symbol, self.intraday_ts)

            if len(self.daily_ts) > 0:
                Database.insert_data_daily(db, self.symbol, self.daily_ts)


class StockNews(object):
    '''Collect latest news for specified symbols and general market news'''

    _base_url = 'https://stocknewsapi.com/api/v1'

    @classmethod
    def get_ticker_news(cls, symbol: str, page: int = 0, date_range: str = None) -> Dict[str, dict]:
        '''Collect news for the specified symbol
           
           @param: symbol: stock symbol
           @param: page: use page parameter (e.g. 2, 3, ...) to obtain more than 50 results
           @param: date_range: retrieve news on specific dates, format: mmddyyyy and today.

           page and date_range can only be used with premium plan
        '''
        
        params = {
            'tickers' : symbol,
            'items'   : 50,
            'type'    : 'article',
            'fallback': 'false',
            'token'   : api_keys['stock_news'],
        }

        if page: params['page'] = page
        if date_range: params['date_range'] = date_range

        api_link = _build_url(StockNews._base_url + '?', params)
        r = requests.get(api_link)
        
        return {symbol: r.json() if r.status_code == 200 else {}}


    @classmethod
    def get_general_market_news(cls, page: int = 0, date_range: str = None) -> Dict[str, dict]:
        '''Collect general news for market. Only available with premium plan
           
           @param: page: use page parameter (e.g. 2, 3, ...) to obtain more than 50 results
           @param: date_range: retrieve news on specific dates, format: mmddyyyy and today.
        '''

        params = {
            'section' : 'general',
            'items'   : 50,
            'type'    : 'article',
            'token'   : api_keys['stock_news_2'],
        }

        if page: params['page'] = page
        if date_range: params['date_range'] = date_range

        api_link = _build_url(cls._base_url + '/category?', params)
        r = requests.get(api_link)
        
        return {'Market': r.json() if r.status_code == 200 else {}}


    @classmethod
    def prc_data(cls, result: Dict[str, dict], trim_to_date: str = '1900-01-01',
                 db: str = '') -> Sequence[tuple]:
        '''Process data for stock news before inserting into database.
           Subjected to change with the table schema

           @param: result: collected time series data
           @param: trim_to_date: discard records earlier than the specified date, yyyy-mm-dd
           @return: List of tuples with order consistent with the table schema
        '''

        assert validate_date_fmt(trim_to_date, '%Y-%m-%d'), 'Date format must be yyyy-mm-dd'

        [(symbol, data)] = result.items()
        value_list = []

        # Convert datatime to this timezone
        timezone = 'US/Eastern'

        for item in data.get('data', []):
            keys = ('title', 'news_url', 'image_url', 'text', 'sentiment', 'source_name')
            date_time = standardize_datetime(item['date'], '%a, %d %b %Y %H:%M:%S %z', 
                                             to_timezone=timezone)
            
            if date_time >= trim_to_date:
                temp_res = [symbol, date_time, timezone] + [item[k] for k in keys]
                value_list.append(tuple(temp_res))

        value_list = sorted(value_list, key=lambda item: item[1])  # sort by date_time

        if db and len(value_list) > 0:
            Database.insert_data_news(db, value_list)

        return value_list


def main():
    db, symbols = db_init['db'], db_init['symbols']
    today = datetime.today().strftime('%Y-%m-%d')
    
    gen_news = StockNews.get_general_market_news()
    gen_news = StockNews.prc_data(gen_news, trim_to_date=today, db=db)

    print('Insert {0} rows into the news table'.format(len(gen_news)))
    print('Complete collection of general market news')
    print()
    time.sleep(10)

    for symbol in symbols:
        sym_news = StockNews.get_ticker_news(symbol=symbol)
        sym_news = StockNews.prc_data(sym_news, trim_to_date=today, db=db)
        
        print('Insert {0} rows into Stock_News'.format(len(sym_news)))
        print('Complete collection of {0} news'.format(symbol))
        print()
        if symbol != symbols[-1]: time.sleep(10)
    
    for symbol in symbols:
        outputsize, interval = 'compact', '15min'
        sp = StockPrice(symbol, outputsize)
        sp.get_intraday(interval)
        sp.get_daily_adjusted()
        sp.prc_data(trim_to_date=today, db=db)
        
        print('Insert {0} rows into {1}.{2}_Intraday'.format(len(sp.intraday_ts), db, symbol))
        print('Insert {0} rows into {1}.{2}_Daily'.format(len(sp.daily_ts), db, symbol))
        print('Complete collection of {0} price'.format(symbol))
        print()
        if symbol != symbols[-1]: time.sleep(30)


if __name__ == '__main__':
    main()
