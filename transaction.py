# -*- coding: utf-8 -*-

import logging
import pandas as pd
from datetime import datetime
from config import db_init
from database import Database
from model import Model
from util import get_last_line, pop_last_line

logger = logging.getLogger(__name__)

_data_folder = './data/transaction/'
_transaction_file = _data_folder + 'transaction.csv'


def init_transaction():
    db, symbols = db_init['db'], db_init['symbols']

    total_value = 1000000     # Initial total amount of fund
    value_each_stock = 10000  # Own approximate this value of shares for each stock

    open_, close = {}, {}     # Open and close price for each stock today
    today = '2019-06-04'      # datetime.today().strftime('%Y-%m-%d')

    for symbol in symbols:
        data = Database.get_data_daily(db=db, symbol=symbol, start=today)[0]
        open_[symbol], close[symbol] = float(data[1]), float(data[4])

    share = {symbol: int(value_each_stock / close[symbol]) for symbol in symbols}
    cash = total_value - sum([share[symbol] * close[symbol] for symbol in symbols])

    header = ['date'] + [symbol + t for symbol in symbols for t in ['_share', '_open', '_close']]
    header += ['cash', 'total_value']
    values = [today] + [v for symbol in symbols for v in [share[symbol], open_[symbol], close[symbol]]]
    values += [cash, total_value]

    with open(_transaction_file, 'w') as f:
        f.write(','.join(map(str, header)) + '\n')
        f.write(','.join(map(str, values)) + '\n')


def _validate_cash():
    '''Reset cash to a higher value if it is negative in any date, which 
       means there is always sufficient cash for trading
    '''
    logger.info('Called')

    data = pd.read_csv(_transaction_file, sep=',')
    min_cash = data['cash'].min()

    if min_cash < 0:
        logger.info('Increase initial cash by: %.2f', -min_cash)

        data['cash'] += -min_cash
        data['total_value'] += -min_cash
        data.to_csv(_transaction_file, float_format='%.4f', index=False)


def get_init_share() -> dict:
    symbols = db_init['symbols']

    with open(_transaction_file, 'r') as f:
        f.readline()
        line = f.readline().split(',')

    share = {s: int(v) for s, v in zip(symbols, line[1:-2:3])}

    return share


def update_fund():
    '''Finalized the last transaction using the lastest daily price data, if available.

       If today is a trading day, then buy shares at the open price, based on 
       the trading decisions (i.e. the number of shares to buy) made before 
       the market is open. The total value at the end of day is calculated 
       with the close price. If not a trading day, do nothing.
    '''
    logger.info('Called')

    db, symbols = db_init['db'], db_init['symbols']

    # Trading decisions for this day
    curr_transaction = pop_last_line(_transaction_file).split(',')
    if curr_transaction[0] != 'NA':
        logger.error('Trading decision not available: %s', curr_transaction[0])

    last_transaction = get_last_line(_transaction_file).split(',')
    cash = float(last_transaction[-2])
    last_trade_day = Database.get_last_trade_day(db, symbols[0])

    logger.info('Last trade day: %s', last_trade_day)
    logger.info('Last transaction date: %s', last_transaction[0])
    if last_trade_day < last_transaction[0]:
        logger.error('Unexpected behavior for last trade and transaction date')

    # New daily price data is available to finalize the transaction
    if last_trade_day > last_transaction[0]:
        logger.info('Finalize transaction for: %s', last_trade_day)

        last_share = {s: int(v) for s, v in zip(symbols, last_transaction[1:-2:3])}
        curr_share = {s: int(v) for s, v in zip(symbols, curr_transaction[1:-2:3])}
        curr_open, curr_close = {}, {}

        # Get open and close price for this day
        for symbol in symbols:
            data = Database.get_data_daily(db=db, symbol=symbol, start=last_trade_day)[0]
            curr_open[symbol], curr_close[symbol] = float(data[1]), float(data[4])

        # Buy shares at the open price
        for symbol in symbols:
            cash -= (curr_share[symbol] - last_share[symbol]) * curr_open[symbol]

        # Total value at the end of day
        total = cash + sum(curr_share[symbol] * curr_close[symbol] for symbol in symbols)

        # Update the transaction information
        curr_transaction = [last_trade_day]
        for symbol in symbols:
            curr_transaction += [curr_share[symbol], curr_open[symbol], curr_close[symbol]]
        curr_transaction += [round(cash, 4), round(total, 4)]

    with open(_transaction_file, 'a') as f:
        f.write(','.join(map(str, curr_transaction)) + '\n')

    _validate_cash()


def make_trade_decision():
    '''Train model and make a trading decison for each symbol. Trading decisions 
       are to be used for the next trading day 

       If run on the non-trading day, e.g. weekends, the current trading decisions are updated
    '''
    logger.info('Called')
    
    symbols = db_init['symbols']

    init_share = get_init_share()
    line = get_last_line(_transaction_file).split(',')
    
    if line[0] == 'NA':    # This transaction is not finalized
        logger.info('Update the current trading decision')
        
        pop_last_line(_transaction_file)
        line = get_last_line(_transaction_file).split(',')

        logger.info('Last transaction data retrieved: %s', line[0])

    curr_share = {s: int(v) for s, v in zip(symbols, line[1:-2:3])}

    for symbol in symbols:
        model = Model(symbol)
        model.load_data()
        model.fit()
        
        neg, neu, pos = model.predict_proba(model.dataX_today)[0]

        # A simple strategy
        transaction = int(round(init_share[symbol] * (pos - neg) / 2, 0))
        
        # Do not consider short-selling
        if curr_share[symbol] + transaction < 0:
            transaction = -curr_share[symbol]

        curr_share[symbol] += transaction

        logger.info('Trading decision for %s: %d share', symbol, transaction)

    # Log trading decisions for the next trading day
    values = ['NA'] + [v for symbol in symbols for v in [curr_share[symbol], 'NA', 'NA']]
    values += ['NA', 'NA']

    with open(_transaction_file, 'a') as f:
        f.write(','.join(map(str, values)) + '\n')


def trade():
    logger.info('Start trading process')

    update_fund()
    make_trade_decision()

    logger.info('Complete trading process')


if __name__ == '__main__':
    # trade()
    pass