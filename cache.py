# -*- coding: utf-8 -*-

import logging
import json
import pandas as pd
import time
from datetime import datetime
from typing import Sequence

import timeout_decorator
from pymemcache.client.base import Client
from empyrical import (simple_returns, cum_returns, aggregate_returns, max_drawdown, 
                       annual_return, annual_volatility, calmar_ratio, omega_ratio, 
                       sharpe_ratio, alpha_beta, tail_ratio, capture)

from config import cache_url
from dataCollection import StockPrice
from transaction import get_init_holding, get_curr_holding, get_portfolio_benchmark
from transaction import get_transaction_history


logger = logging.getLogger(__name__)


def json_serializer(key, value):
    if isinstance(value, str): return value, 1
    return json.dumps(value), 2


def json_deserializer(key, value, flag):
   if flag == 1: return value
   if flag == 2: return json.loads(value)
   raise Exception('Unknown flag for value: {0}'.format(flag))


def collect_price(symbol):
    @timeout_decorator.timeout(3, use_signals=False)
    def collect():
        sp = StockPrice(symbol)
        sp.get_daily_adjusted()
        return sp.daily_ts

    try:
        data = collect()
    except:
        data = {}
        logger.info('Time out: %s', symbol)

    key = 'Time Series (Daily)'

    if key in data:
        prev_key, curr_key = sorted(data[key])[-2:]
        prev = float(data[key][prev_key]['5. adjusted close'])
        curr = float(data[key][curr_key]['5. adjusted close'])

        logger.info('Get price for %s: prev (%s) %s, curr (%s) %s', symbol, 
                    prev_key, prev, curr_key, curr)
    else:
        prev, curr = '-', '-'

        logger.info('Get price for %s: prev %s, curr %s', symbol, prev, curr)

    return prev, curr


def compute_stats(portfolio, benchmark):
    '''Compute statistics for the current portfolio'''
    stats = {}

    grp_by_year = portfolio.groupby(lambda x: x.year)
    stats['1yr_highest'] = grp_by_year.max().iloc[-1]
    stats['1yr_lowest'] = grp_by_year.min().iloc[-1]

    portfolio_return = simple_returns(portfolio)
    # benchmark_return = simple_returns(benchmark)
    
    stats['wtd_return'] = aggregate_returns(portfolio_return, 'weekly').iloc[-1]
    stats['mtd_return'] = aggregate_returns(portfolio_return, 'monthly').iloc[-1]
    stats['ytd_return'] = aggregate_returns(portfolio_return, 'yearly').iloc[-1]
    stats['max_drawdown'] = max_drawdown(portfolio_return)
    # stats['annual_return'] = annual_return(portfolio_return, period='daily')
    stats['annual_volatility'] = annual_volatility(portfolio_return, period='daily', alpha=2.0)
    # stats['calmar_ratio'] = calmar_ratio(portfolio_return, period='daily')
    # stats['omega_ratio'] = omega_ratio(portfolio_return, risk_free=0.0)
    stats['sharpe_ratio_1yr'] = sharpe_ratio(portfolio_return, risk_free=0.0, period='daily')
    # stats['alpha'], stats['beta'] = alpha_beta(portfolio_return, benchmark_return, 
    #                                            risk_free=0.0, period='daily')
    stats['tail_ratio'] = tail_ratio(portfolio_return)
    # stats['capture_ratio'] = capture(portfolio_return, benchmark_return, period='daily')

    return stats


class Cache(object):
    '''Cache operations'''

    client = Client((cache_url['host'], cache_url['port']), 
                    timeout=30, ignore_exc=True, 
                    serializer=json_serializer, deserializer=json_deserializer)

    @classmethod
    def get_cached(cls, key: str):
        logger.info('Get cached %s', key)
        return cls.client.get(key)


    @classmethod
    def set_cached(cls, key: str, value, expire: int = 0):
        logger.info('Set value for %s', key)
        cls.client.set(key, value, expire=expire)


    @classmethod
    def set_share_cash(cls):
        date, share, cash, _ = get_curr_holding()

        cls.client.set('share', share)
        cls.client.set('cash', cash)

        logger.info('Set share and cash from holdings at %s (today %s)', date, 
                    datetime.today().strftime('%Y-%m-%d'))

        return share, cash


    @classmethod
    def set_price(cls, symbols: Sequence[str]):
        '''This method is not directly called in the web application as it requires
           a few minutes (due to rate limit of api call) to collect all data 
           and thus can lead to significant delay in http response
        '''

        logger.info('Collect price data for each symbol')

        price = {}
        
        for symbol in symbols:
            prev, curr = collect_price(symbol)
            price[symbol] = (prev, curr)
            cls.client.set(symbol, (prev, curr))

            if symbol != symbols[-1]: time.sleep(12)

        cls.client.set('price', price)


    @classmethod
    def set_init_value(cls):
        logger.info('Compute initial total value')

        _, _, init_value = get_init_holding()
        cls.client.set('init_value', init_value)

        return init_value


    @classmethod
    def set_transaction(cls):
        logger.info('Get transaction history')

        transaction = get_transaction_history()
        cls.client.set('transaction', transaction)

        return transaction


    @classmethod
    def set_stats(cls):
        logger.info('Compute statistics of portfolio')

        data = get_portfolio_benchmark()
        data.index = pd.to_datetime(data.index)
        stats = compute_stats(data['total_value'], data['benchmark'])

        cls.client.set('stats', stats)

        return stats


if __name__ == '__main__':
    pass
