# -*- coding: utf-8 -*-

import logging
import pandas as pd
from typing import Sequence, List, Tuple, Dict
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

logger = logging.getLogger(__name__)

_data_folder = './data/feature/'


class Model(object):
    def __init__(self, symbol: str):
        self.symbol = symbol

    
    def load_data(self):
        logger.info('Modeling - load data for %s', self.symbol)

        threshold = 0.001

        data = load_feature(self.symbol)
        col_dataX = list(data.columns)[:-1]
        
        data['poc'] = data['adj_close'].pct_change(periods=1)
        data['poc'] = data['poc'].shift(-1)  # Price change in the next day
        data['Y'] = 0
        data.loc[data['poc'] > threshold, 'Y'] = 1
        data.loc[data['poc'] < -threshold, 'Y'] = -1

        self.dataX_today = data[col_dataX].tail(1)
        self.dataX = data[:-1][col_dataX]
        self.dataY = data[:-1]['Y']

        if len(self.dataX_today) > 0:
            logger.info('Modeling - date for prediction: %s', self.dataX_today.index[0])


    def fit(self):
        logger.info('Modeling - build model for %s', self.symbol)

        param = {
            'n_estimators': 500,
            'max_depth'   : 3,
            'max_features': 'auto', # int, float, 'auto', 'sqrt', 'log2' or None
            'random_state': 0,
        }

        self._clf = RandomForestClassifier(**param)

        if len(self.dataX) > 0:
            self._clf.fit(self.dataX, self.dataY)

    
    def predict_proba(self, X):
        logger.info('Modeling - predict prob for %s', self.symbol)

        try:
            return self._clf.predict_proba(X)
        except:
            return [[0, 0, 0]]


    def predict(self, X):
        logger.info('Modeling - predict for %s', self.symbol)

        return self._clf.predict(X)


def load_feature(symbol: str) -> pd.DataFrame:
    ta_file = _data_folder + '{0}_ta.csv'.format(symbol)
    symbol_news_file = _data_folder + '{0}_news.csv'.format(symbol)
    market_news_file = _data_folder + 'Market_news.csv'

    ta_feature = pd.read_csv(ta_file, sep=',', index_col='date')
    symbol_news_feature = pd.read_csv(symbol_news_file, sep=',', index_col='date')
    market_news_feature = pd.read_csv(market_news_file, sep=',', index_col='date')

    news_feature = symbol_news_feature.join(market_news_feature, on='date', 
                                    how='left', lsuffix='_s', rsuffix='_m')
    feature = ta_feature.join(news_feature, on='date', how='left')

    assert not feature.isnull().values.any(), 'Feature matrix contains NaN'
        
    # Move the 'adj_close' column to last
    adj_close = feature['adj_close']
    feature.drop(columns='adj_close', inplace=True)
    feature['adj_close'] = adj_close

    return feature


def main():
    model = Model('AAPL')
    model.load_data()
    model.fit()
    
    prob = model.predict_proba(model.dataX_today)[0]
    print(prob)


if __name__ == '__main__':
    main()
    