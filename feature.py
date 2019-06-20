# -*- coding: utf-8 -*-

import logging
import pandas as pd
from typing import Sequence, List, Tuple, Dict
from config import db_init, data_path
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from database import Database, retrieve_price_news
from indicator import Indicator
from util import get_last_line, pop_last_line

logger = logging.getLogger(__name__)

_data_folder = data_path['root_path'] + 'feature/'
_since_this_date = '2018-01-01'


def build_news_feature(date_string: str, news: Sequence[tuple]) -> tuple:
    '''Build features using the news data between two consecutive trading days
       
       @param: date_string: date that the news data binds to
       @param: news: collection of news (can be empty)
    '''

    def divide(n1: int, n2: int) -> float:
        return n1 / n2 if n2 != 0 else -1.0

    analyzer, threshold = SentimentIntensityAnalyzer(), 0.05
    col_names = ('date_time', 'title', 'content', 'sentiment')

    df = pd.DataFrame(news, columns=col_names, dtype=object)
    df.fillna('', inplace=True)
    df['title_score'] = df['title'].map(lambda x: analyzer.polarity_scores(x)['compound'])
    df['content_score'] = df['content'].map(lambda x: analyzer.polarity_scores(x)['compound'])

    num_news = len(news)

    num_neg_title = sum(df['title_score'] <= -threshold)
    num_pos_title = sum(df['title_score'] >= threshold)
    ratio_neg_title = round(divide(num_neg_title, num_neg_title + num_pos_title), 4)

    num_neg_content = sum(df['content_score'] <= -threshold)
    num_pos_content = sum(df['content_score'] >= threshold)
    ratio_neg_content = round(divide(num_neg_content, num_neg_content + num_pos_content), 4)

    num_neg_sentiment = sum(df['sentiment'] == 'Negative')
    num_pos_sentiment = sum(df['sentiment'] == 'Positive')
    ratio_neg_sentiment = round(divide(num_neg_sentiment, num_neg_sentiment + num_pos_sentiment), 4)
    
    mean_score_title, mean_score_content, mean_score_sentiment = 0, 0, 0
    if num_news > 0:
        mean_score_title = round(df['title_score'].mean(), 4)
        mean_score_content = round(df['content_score'].mean(), 4)
        mean_score_sentiment = round((num_pos_sentiment - num_neg_sentiment) / num_news, 4)

    return (date_string, num_news, 
            mean_score_title, num_neg_title, num_pos_title, ratio_neg_title,
            mean_score_content, num_neg_content, num_pos_content, ratio_neg_content,
            mean_score_sentiment, num_neg_sentiment, num_pos_sentiment, ratio_neg_sentiment)


def build_ta_feature(symbol: str, daily: Sequence[tuple], 
                     save_feature: bool = True) -> pd.DataFrame:
    '''Build features using the daily time series data. Indicators like EMA
       should be computed using the complete set of data (instead of a subset)
        
       @param: symbol: stock symbol that the daily data belongs to
       @param: daily: daily time series data for a symbol
       @param: save_feature: whether to save the features to file
    '''
    logger.info('Build ta feature for: %s. Last daily date: %s', symbol, daily[-1][0])

    col_dtype = {'date': object, 'open': 'float64', 'high': 'float64', 'low': 'float64',
                 'close': 'float64', 'adj_close': 'float64', 'volume': 'int32'}
    df = pd.DataFrame(daily, columns=col_dtype.keys(), dtype=object)
    df = df.astype(col_dtype, copy=True)

    high, low, close, volume = df['high'], df['low'], df['close'], df['volume']

    # Overlap Studies 
    upperband, middleband, lowerband = Indicator.BBANDS(close, timeperiod=5)
    df['ub_r'], df['mb_r'], df['lb_r'] = upperband / close, middleband / close, lowerband / close
    df['trima_r'] = Indicator.TRIMA(close, timeperiod=30) / close
    df['wma_r'] = Indicator.WMA(close, timeperiod=30) / close

    # Momentum Indicator
    macd, macdsignal, macdhist = Indicator.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    df['macdhist'] = macdhist
    df['ppo'] = Indicator.PPO(close, fastperiod=12, slowperiod=26)
    df['rsi'] = Indicator.RSI(close, timeperiod=14)

    # Volume Indicator
    df['adosc'] = Indicator.ADOSC(high, low, close, volume * 1.0, fastperiod=3, slowperiod=10)

    # Volatility Indicator
    df['natr'] = Indicator.NATR(high, low, close, timeperiod=14)

    # Drop rows with NaN values
    df.dropna(axis=0, how='any', inplace=True)

    # Drop useless columns
    col_drop = ['open', 'high', 'low', 'close', 'volume']
    df.drop(columns=col_drop, inplace=True)

    if save_feature:
        df.to_csv(_data_folder + '{0}_ta.csv'.format(symbol), float_format='%.4f', index=False)

    return df


def build_news_feature_all(symbol: str, trade_days: Tuple[str], news_data: Sequence[tuple],
                           save_feature: bool = True) -> pd.DataFrame:
    '''Build features on news for the provide trade days
       
       @param: symbol: stock symbol that the news data belongs to
       @param: trade_days: Sequence of trade days. Must be in ascending order
       @param: news_data: collection of news. Timestamp of the news must be in ascending order
       @param: save_feature: whether to save the features to file
    '''
    logger.info('Build news feature for %s, from %s to %s', symbol, trade_days[0], trade_days[-1])

    if not list(trade_days) == sorted(list(trade_days)):
        logger.error('Trade days not in ascending order')
    if news_data != sorted(news_data, key = lambda x: x[0]):
        logger.error('News not ordered by date')
    
    news_feature, idx = [], 0

    for i, date_string in enumerate(trade_days[:-1]):
        next_trade_day = trade_days[i + 1]
        news = []

        # Get all news between current and next trade day
        # and bind them to the current trade day
        while idx < len(news_data) and news_data[idx][0] < next_trade_day:
            news.append(news_data[idx])
            idx += 1

        news_feature.append(build_news_feature(date_string, news))

    # Bind all remaining news to the last trade day
    news_feature.append(build_news_feature(trade_days[-1], news_data[idx:]))

    feature_name = ['date', 'n_news', 'mst', 'nnt', 'npt', 'rnt', 'msc', 
                    'nnc', 'npc', 'rnc', 'mss', 'nns', 'nps', 'rns']
    
    news_feature = pd.DataFrame(news_feature, columns=feature_name)

    if save_feature:
        news_feature.to_csv(_data_folder + '{0}_news.csv'.format(symbol), 
                            float_format='%.4f', index=False)

    return news_feature


def build_feature_all(symbols: Sequence[str] = ()):
    '''Construct features based on public news and technical analysis of 
       price/volume for the provided symbols
       
       @param: symbols: sequence of symbols to build feature. If empty, use all symbols
    '''
    logger.info('Called')

    market_news, symbol_data = retrieve_price_news(symbols=symbols, start=_since_this_date)

    # Trade days may vary for different symbols
    # Subject to future change
    trade_days = list(zip(*symbol_data[next(iter(symbol_data))]['daily']))[0]

    # Build features for market news
    market_news_feature = build_news_feature_all('Market', trade_days, market_news)
    
    # Build features for each symbol
    for symbol in symbol_data:
        news_feature = build_news_feature_all(symbol, trade_days, symbol_data[symbol]['news'])
        feature = build_ta_feature(symbol, symbol_data[symbol]['daily'])


def update_ta_feature(symbol: str):
    '''Update ta features for the specified symbol with the latest daily time series data'''
    logger.info('Called for %s', symbol)

    db = db_init['db']

    last_trade_day = Database.get_last_trade_day(db, symbol)
    last_ta_line = get_last_line(_data_folder + '{0}_ta.csv'.format(symbol))
    last_ta_day = last_ta_line.split(',')[0]

    logger.info('Last trade day: %s, last ta day: %s', last_trade_day, last_ta_day)

    if last_ta_day < last_trade_day:
        data = Database.get_data_daily(db, symbol, start=_since_this_date)
        build_ta_feature(symbol, data)


def update_news_feature(symbol: str):
    '''Update mews features for the specified symbol with the latest news data.
       Should be used on a daily basis
    '''
    logger.info('Called for %s', symbol)

    db, symbols = db_init['db'], db_init['symbols']

    if symbol == 'Market':
        last_trade_day = Database.get_last_trade_day(db, symbols[0])
    else:
        last_trade_day = Database.get_last_trade_day(db, symbol)
    
    # Get news data and build feature for the last trade day
    news = Database.get_data_news(db, symbol, start=last_trade_day)
    news_feature = build_news_feature(last_trade_day, news)

    from_date, to_date = (news[0][0], news[-1][0]) if len(news) > 0 else ('-', '-')
    logger.info('Get %d news, from %s to %s', len(news), from_date, to_date)

    # Get the date for the last news feature in file to determine whether the
    # newly built news feature should override the existing one or simply append
    new_feature_file = _data_folder + '{0}_news.csv'.format(symbol)
    last_news_line = get_last_line(new_feature_file)
    last_news_day = last_news_line.split(',')[0]

    logger.info('Last trade day: %s, last news day: %s', last_trade_day, last_news_day)
    if last_news_day > last_trade_day:
        logger.error('Unexpected behavior for last trade and news date')

    if last_news_day == last_trade_day:
        logger.info('Override the news feature for %s', last_news_day)
        pop_last_line(new_feature_file)
    else:
        logger.info('Add the news feature for %s', last_trade_day)

    with open(new_feature_file, 'a') as f:
        f.write(','.join(map(str, news_feature)) + '\n')


def update_feature():
    logger.info('Start updating feature')
    # build_feature_all()
    
    symbols = db_init['symbols']

    for symbol in symbols:
        update_ta_feature(symbol=symbol)
        update_news_feature(symbol=symbol)
    
    update_news_feature(symbol='Market')

    logger.info('Complete feature update')
    

if __name__ == '__main__':
    # update_feature()
    build_feature_all()
    