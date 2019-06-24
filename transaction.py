# -*- coding: utf-8 -*-

import logging
from datetime import datetime

import pandas as pd

from config import db_init, data_path
from database import Database
from model import Model
from util import get_last_line, pop_last_line


logger = logging.getLogger(__name__)

_data_folder = data_path['root_path'] + 'transaction/'
_portfolio_file = _data_folder + 'portfolio.csv'
_prob_pred_file = _data_folder + 'prob_pred.csv'
_trade_history_file = _data_folder + 'trade_history.csv'


def init_transaction():
    db, symbols = db_init['db'], db_init['symbols']

    total_value = 500000      # Initial total amount of fund
    value_each_stock = 25000  # Own approximate this value of shares for each stock

    open_, close = {}, {}     # Open and close price for each stock today
    today = '2019-05-31'      # datetime.today().strftime('%Y-%m-%d')

    for symbol in symbols:
        data = Database.get_data_daily(db=db, symbol=symbol, start=today)[0]
        open_[symbol], close[symbol] = float(data[1]), float(data[4])

    share = {symbol: int(value_each_stock / close[symbol]) for symbol in symbols}
    cash = total_value - sum([share[symbol] * close[symbol] for symbol in symbols])

    header = ['date'] + [symbol + t for symbol in symbols for t in ['_share', '_open', '_close']]
    header += ['cash', 'total_value', 'benchmark']
    values = [today] + [v for symbol in symbols for v in [share[symbol], open_[symbol], close[symbol]]]
    values += [round(cash, 4), round(total_value, 4), round(total_value, 4)]

    with open(_portfolio_file, 'w') as f:
        f.write(','.join(header) + '\n')
        f.write(','.join(map(str, values)) + '\n')

    with open(_prob_pred_file, 'w') as f:
        header = ['date'] + [symbol + t for symbol in symbols for t in ['_neg', '_neu', '_pos']]
        f.write(','.join(header) + '\n')

    with open(_trade_history_file, 'w') as f:
        header = ['date', 'symbol', 'share', 'transaction', 'price']
        f.write(','.join(header) + '\n')


def get_init_holding():
    '''Get initial holding'''

    symbols = db_init['symbols']

    with open(_portfolio_file, 'r') as f:
        f.readline()
        line = f.readline().split(',')

    share = {s: int(v) for s, v in zip(symbols, line[1:-3:3])}
    cash, total_value = float(line[-3]), float(line[-2])

    return share, cash, total_value


def get_curr_holding():
    '''Get current holding'''

    symbols = db_init['symbols']

    line = get_last_line(_portfolio_file).split(',')
    share = {s: int(v) for s, v in zip(symbols, line[1:-3:3])}
    cash, total_value = float(line[-3]), float(line[-2])

    return line[0], share, cash, total_value


def get_portfolio_benchmark():
    '''Get time series portfolio and benchmark'''

    data = pd.read_csv(_portfolio_file, sep=',', index_col='date', 
                       usecols=['date', 'total_value', 'benchmark'])
    return data


def get_transaction_history():
    '''Get transaction history, in reversed order of date'''

    with open(_trade_history_file, 'r') as f:
        f.readline()
        data = f.readlines()

    data = map(lambda line: line.strip().split(','), data)
    data = sorted(data, key=lambda row: row[0], reverse=True)

    return data


def get_portfolio_data():
    '''Read the entire portfolio file'''

    with open(_portfolio_file, 'r') as f:
        data = f.read()

    return data


def _validate_cash():
    '''Reset cash to a higher value if it is negative in any date, which 
       means there is always sufficient cash for trading
    '''
    logger.info('Called')

    data = pd.read_csv(_portfolio_file, sep=',')
    min_cash = data['cash'].min()

    if min_cash < 0:
        logger.info('Increase initial cash by: %.2f', -min_cash)

        data['cash'] += -min_cash
        data['total_value'] += -min_cash
        data['benchmark'] += -min_cash
        data.to_csv(_portfolio_file, float_format='%.4f', index=False)


def finalize_transaction():
    '''Finalized the transaction for today based on the predicted probabilities and
       update the fund using the lastest daily price data.

       Rule to follow:
           If today is a trading day, then buy shares at the open price, based on 
           the predicted probabilities and the derived trading strategy. The total 
           value at the end of day is calculated with the close price. 

           If not a trading day, do nothing.
    '''
    logger.info('Called')

    db, symbols = db_init['db'], db_init['symbols']

    # Probabilities of price change for this day
    curr_prob = pop_last_line(_prob_pred_file).split(',')
    if curr_prob[0] != 'NA':
        logger.error('Probability data not available: %s', curr_prob[0])

    last_transaction = get_last_line(_portfolio_file).split(',')
    cash = float(last_transaction[-3])
    last_trade_day = Database.get_last_trade_day(db, symbols[0])

    logger.info('Last trade day: %s', last_trade_day)
    logger.info('Last transaction date: %s', last_transaction[0])
    if last_trade_day < last_transaction[0]:
        logger.error('Unexpected behavior for last trade and transaction date')

    # New daily price data is available to finalize the transaction
    if last_trade_day > last_transaction[0] and curr_prob[0] == 'NA':
        logger.info('Finalize transaction for: %s', last_trade_day)

        init_share, init_cash, _ = get_init_holding()
        curr_share = {s: int(v) for s, v in zip(symbols, last_transaction[1:-3:3])}
        probs = {s: tuple(map(float, curr_prob[i * 3 + 1 : i * 3 + 4])) for i, s in enumerate(symbols)}

        curr_open, curr_close = {}, {}

        # Get open and close price for this day
        for symbol in symbols:
            data = Database.get_data_daily(db=db, symbol=symbol, start=last_trade_day)[0]
            curr_open[symbol], curr_close[symbol] = float(data[1]), float(data[4])

        # Buy/sell shares at the open price
        for symbol in symbols:
            # A simple strategy
            pos, neg = probs[symbol][-1], probs[symbol][0]
            transaction = int(round(init_share[symbol] * (pos - neg) / 2, 0))
            
            # Do not consider short-selling
            if curr_share[symbol] + transaction < 0:
                transaction = -curr_share[symbol]

            logger.info('Trading decision for %s (%d): %d share (%.4f, %.4f)', 
                        symbol, curr_share[symbol], transaction, pos, neg)

            # Log this transaction to trade history
            with open(_trade_history_file, 'a') as f:
                record = (last_trade_day, symbol, curr_share[symbol], transaction, round(curr_open[symbol], 4))
                f.write(','.join(map(str, record)) + '\n')

            # Update number of shares and cash
            curr_share[symbol] += transaction
            cash -= transaction * curr_open[symbol]

        # Total value and benchmark at the end of day
        total = cash + sum(curr_share[symbol] * curr_close[symbol] for symbol in symbols)
        benchmark = init_cash + sum(init_share[symbol] * curr_close[symbol] for symbol in symbols)

        # Update the transaction information
        curr_transaction = [last_trade_day]
        for symbol in symbols:
            curr_transaction += [curr_share[symbol], curr_open[symbol], curr_close[symbol]]
        curr_transaction += [round(cash, 4), round(total, 4), round(benchmark, 4)]

        with open(_portfolio_file, 'a') as f:
            f.write(','.join(map(str, curr_transaction)) + '\n')

        # Update the date for the probability predictions made for this day
        curr_prob[0] = last_trade_day

        _validate_cash()

    with open(_prob_pred_file, 'a') as f:
        f.write(','.join(curr_prob) + '\n')


def predict_price_change():
    '''Train model and predict probability of price change in the next day for each symbol.
       If run on the non-trading day, e.g. weekends, the current probabilities are updated
    '''
    logger.info('Called')
    
    symbols = db_init['symbols']
    line = get_last_line(_prob_pred_file).split(',')
    
    # If on the non-trading day, update the probability predictions
    if line[0] == 'NA':
        logger.info('Update the current predicted probabilities')
        pop_last_line(_prob_pred_file)

    prob_pred = {}

    for symbol in symbols:
        model = Model(symbol)
        model.load_data()
        model.fit()
        
        neg, neu, pos = model.predict_proba()
        prob_pred[symbol] = tuple(map(lambda x: round(x, 4), (neg, neu, pos)))

    # Log probability predictions for the next trading day
    prob = ['NA'] + [v for symbol in symbols for v in prob_pred[symbol]]

    with open(_prob_pred_file, 'a') as f:
        f.write(','.join(map(str, prob)) + '\n')


def trade():
    logger.info('Start trading process')

    finalize_transaction()
    predict_price_change()

    logger.info('Complete trading process')


if __name__ == '__main__':
    data = get_transaction_history()
