# -*- coding: utf-8 -*-

import logging
from typing import Sequence

from flask import Flask, render_template

from config import db_init, description, log_path
from cache import Cache, collect_price
from transaction import get_portfolio_data


app = Flask(__name__)

_log_filename = log_path['root_path'] + 'web.log'

log_param = {
    'filename': _log_filename, 
    'filemode': 'a',
    'format'  : '%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s',
    'datefmt' : '%Y-%m-%d %H:%M:%S',
    'style'   : '%',
    'level'   : logging.INFO,
}

logging.basicConfig(**log_param)


def prepare_data(symbols: Sequence[str]):
    '''Prepare data for front-end rendering'''

    logging.info('Called')

    # ==========================================================================
    # Get current shares and cash
    share, cash = Cache.get_cached('share'), Cache.get_cached('cash')
    
    if share is None or cash is None:
        logging.warn('Share and/or cash data not found')
        share, cash = Cache.set_share_cash()

    # ==========================================================================
    # Get realtime price and the one in the previous trading day for each symbol
    price = Cache.get_cached('price')

    if price is None:
        logging.warn('Price data not found')
        price = {}

        for symbol in symbols:
            temp = Cache.get_cached(symbol)
            
            if temp is not None and temp[0] != '-' and temp[1] != '-':
                prev, curr = temp
            else:
                prev, curr = collect_price(symbol)
                Cache.set_cached(symbol, (prev, curr), expire=5*60)
            
            price[symbol] = (prev, curr)

    # ==========================================================================
    # Calculate total value and value change percentage
    if all(['-' not in val for val in price.values()]):
        total_value = cash

        for symbol in symbols:
            total_value += share[symbol] * price[symbol][1]

        # Get initial total value
        init_value = Cache.get_cached('init_value')

        if init_value is None:
            logging.warn('Initial total value of portfolio not found')
            init_value = Cache.set_init_value()

        total_value_pct = 100 * (total_value - init_value) / init_value
    
    else:
        total_value, total_value_pct = '-', '-'

    # ==========================================================================
    # Get transaction history
    transaction = Cache.get_cached('transaction')
    
    if transaction is None:
        logging.warn('Transaction data not found')
        transaction = Cache.set_transaction()

    # ==========================================================================
    # Get portfolio statistics
    stats = Cache.get_cached('stats')

    if stats is None:
        logging.warn('Portfolio statistics data not found')
        stats = Cache.set_stats()


    return {
        'portfolio'  : 'Sample Portfolio',
        'size'       : len(symbols),
        'share'      : share,
        'price'      : price,
        'cash'       : cash,
        'total_value': total_value,
        'total_pct'  : total_value_pct,
        'description': description,
        'transaction': transaction,
        'stats'      : stats,
    }


@app.route('/')
def index():
    logging.info('Receive request')

    symbols = db_init['symbols']
    data = prepare_data(symbols)
    
    return render_template('index.html', **data)


@app.route('/data/portfolio')
def get_portfolio():
    return get_portfolio_data()


if __name__ == '__main__':
    app.run()
