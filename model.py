# -*- coding: utf-8 -*-

import logging
import pandas as pd
from collections import defaultdict
from typing import Sequence, List, Tuple, Dict
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from database import Database, retrieve_price_news
from indicator import Indicator


_data_folder = './data/feature/'

class Model(object):
    def __init__(self, symbol: str):
        self.symbol = symbol

    
    def load_data(self):
        threshold = 0.001

        datafile = _data_folder + '{0}.csv'.format(self.symbol)
        data = pd.read_csv(datafile, sep=',', index_col='date')
        col_dataX = list(data.columns)[:-1]
        
        data['poc'] = data['adj_close'].pct_change(periods=1)
        data['poc'] = data['poc'].shift(-1)  # Price change in the next day
        data['Y'] = 0
        data.loc[data['poc'] > threshold, 'Y'] = 1
        data.loc[data['poc'] < -threshold, 'Y'] = -1

        self.dataX_today = data[col_dataX].tail(1)
        self.dataX = data[:-1][col_dataX]
        self.dataY = data[:-1]['Y']


    def fit(self):
        param = {
            'n_estimators': 500,
            'max_depth'   : 3,
            'max_features': 'auto', # int, float, 'auto', 'sqrt', 'log2' or None
            'random_state': 0,
        }

        self._clf = RandomForestClassifier(**param)
        self._clf.fit(self.dataX, self.dataY)

    
    def predict_proba(self, X):
        return self._clf.predict_proba(X)


    def predict(self, X):
        return self._clf.predict(X)


def build_news_feature(date_string: str, news: Sequence[tuple]) -> tuple:
    '''Build features using news data between two consecutive trading days

       @param: news: collection of news (can be empty)
    '''
    def divide(n1: int, n2: int) -> float:
        return n1 / n2 if n2 != 0 else -1.0

    analyzer, threshold = SentimentIntensityAnalyzer(), 0.05

    col_names = ('date_time', 'title', 'content', 'sentiment')
    df = pd.DataFrame(news, columns=col_names, dtype=object)
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


def build_news_feature_all(trade_days: Tuple[str], news_data: Sequence[tuple]) -> pd.DataFrame:
    '''Build features on news for the provide trade days
       
       @param: trade_days: Sequence of trade days. Must be in ascending order
       @param: news_data: collection of news. Timestamp of the news must be in ascending order
    '''
    assert list(trade_days) == sorted(list(trade_days)), 'Trade days not in ascending order'
    assert news_data == sorted(news_data, key = lambda x: x[0]), 'News not in ascending order'
    
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
    
    return pd.DataFrame(news_feature, columns=feature_name)


def build_ta_feature(daily: Sequence[tuple]) -> pd.DataFrame:
    '''Build features using the daily time series data. Indicators like EMA
       should be computed using the complete set of data (instead of a subset)

       @param: daily: daily time series data for a symbol
    '''
    col_dtype = {'date': object, 'high': 'float64', 'low': 'float64',
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
    adj_close = df['adj_close']
    col_drop = set(col_dtype.keys()) - set(['date'])
    df.drop(columns=col_drop, inplace=True)

    return adj_close, df


def build_feature():
    '''Construct features based on public news and technical analysis of 
       price/volume for all symbols
    '''
    market_news, symbol_data = retrieve_price_news(start='2018-01-01')
    trade_days = list(zip(*symbol_data[next(iter(symbol_data))]['daily']))[0]

    market_news_feature = build_news_feature_all(trade_days, market_news)
    market_news_feature.set_index('date', inplace=True)
    
    # Build features for each symbol
    for symbol in symbol_data:
        news_feature = build_news_feature_all(trade_days, symbol_data[symbol]['news'])
        news_feature.set_index('date', inplace=True)
        news_feature = news_feature.join(market_news_feature, on='date', 
                                how='outer', lsuffix='_s', rsuffix='_m')

        adj_close, feature = build_ta_feature(symbol_data[symbol]['daily'])
        feature = feature.join(news_feature, on='date', how='left')
        
        # Fill NaN values
        # col_ratio = ['rnt_s', 'rnc_s', 'rns_s', 'rnt_m', 'rnc_m', 'rns_m']
        # feature[col_ratio] = feature[col_ratio].fillna(-1)
        # feature.fillna(0, inplace=True)

        assert not feature.isnull().values.any(), 'Feature matrix contains NaN'

        # Set date types of specific columns to int
        # col_int = list(set(news_feature.columns) - set(col_ratio))
        # feature[col_int] = feature[col_int].astype('int32')
        
        # Save to file
        feature['adj_close'] = adj_close
        feature.to_csv(_data_folder + '{0}.csv'.format(symbol), float_format='%.4f', index=False)


if __name__ == '__main__':
    build_feature()
    
    model = Model('AMZN')
    model.load_data()
    model.fit()
    prob = model.predict_proba(model.dataX_today)
    