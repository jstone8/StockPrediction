# -*- coding: utf-8 -*-

import logging
import requests
import json
import datetime
from flask import Flask, render_template
from pymemcache.client.base import Client
from config import api_keys, db_init, description
from dataCollection import StockPrice
from transaction import get_init_holding, get_curr_holding, get_portfolio_benchmark
from transaction import get_transaction_history

app = Flask(__name__)
'''
_log_folder = './log/'
_log_filename = _log_folder + 'web.log'

log_param = {
    'filename': _log_filename, 
    'filemode': 'a',
    'format'  : '%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s',
    'datefmt' : '%Y-%m-%d %H:%M:%S',
    'style'   : '%',
    'level'   : logging.INFO,
}

logging.basicConfig(**log_param)
'''

_host, _port = '127.0.0.1', 8000

def _json_serializer(key, value):
    if type(value) == str: return value, 1
    return json.dumps(value), 2


def _json_deserializer(key, value, flag):
   if flag == 1: return value
   if flag == 2: return json.loads(value)
   raise Exception('Unknown flag for value: {0}'.format(flag))


def _get_price(symbol):
    sp = StockPrice(symbol)
    sp.get_daily_adjusted()
    data = sp.daily_ts
    key = 'Time Series (Daily)'

    if key in data:
        prev_key, curr_key = sorted(data[key])[-2:]
        prev = float(data[key][prev_key]['5. adjusted close'])
        curr = float(data[key][curr_key]['5. adjusted close'])
    else:
        prev, curr = '-', '-'

    #logging.info('Get price for %s: prev (%s) %s, curr (%s) %s', symbol, 
    #            prev_key, prev, curr_key, curr)

    return prev, curr


def prepare_data(symbols):
    #logging.info('Called')

    client = Client((_host, _port), timeout=30, ignore_exc=True)

    # Get current holdings and cash from the portfolio file
    share, cash = client.get('share'), client.get('cash')
    
    if share is None:
        share, cash, _ = get_curr_holding()

        client.set('share', share)
        client.set('cash', cash)

        #logging.info('Set share from holdings at %s (today %s)', holding[0], 
        #             datetime.today().strftime('%Y-%m-%d'))

    # Get realtime price and the one in the previous trading day for each symbol
    price = client.get('price')
    all_success = True

    if price is None:
        # logging.info('Collect price data for each symbol')

        price = {}

        for i, symbol in enumerate(symbols):
            prev, curr = _get_price(symbol)
            price[symbol] = (prev, curr)
            if prev == '-' or curr == '-': all_success = False

        client.set('price', price, expire=5*60)

    # Calculate total value
    if all_success:
        total_value = cash

        for symbol in symbols:
            total_value += share[symbol] * price[symbol][1]

        # Get initial total value
        init_value = client.get('init_value')

        if init_value is None:
            _, _, init_value = get_init_holding()
            client.set('init_value', init_value)

        total_value_change = 100 * (total_value - init_value) / init_value
    
    else:
        total_value, total_value_change = '-', '-'

    return share, price, cash, total_value, total_value_change


@app.route('/')
def index():
    #logging.info('Receive request')

    symbols = db_init['symbols']
    share, price, cash, total_value, total_value_change = prepare_data(symbols)

    param = {
        'portfolio'  : 'Sample Portfolio',
        'size'       : len(symbols),
        'share'      : share,
        'price'      : price,
        'cash'       : cash,
        'total_value': total_value,
        'total_pct'  : total_value_change,
        'description': description,
        'transaction': get_transaction_history(),
    }
    
    return render_template('index.html', **param)


if __name__ == '__main__':
    app.run(host=_host, port=_port)
