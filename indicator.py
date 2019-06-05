# -*- coding: utf-8 -*-

import logging
import talib
import numpy as np


class Indicator(object):
    '''Wrapper for various useful indicators
       See https://mrjbq7.github.io/ta-lib/
    '''

    # Overlap Studies Functions
    @staticmethod
    def BBANDS(close, timeperiod=5, nbdevup=2, nbdevdn=2, matype=0):
        # Bollinger Bands
        param = {
            'timeperiod': timeperiod,
            'nbdevup'   : nbdevup,
            'nbdevdn'   : nbdevdn,
            'matype'    : matype,
        }

        upperband, middleband, lowerband = talib.BBANDS(close, **param)
        return upperband, middleband, lowerband


    @staticmethod
    def DEMA(close, timeperiod=30):
        # Double Exponential Moving Average
        return talib.DEMA(close, timeperiod=timeperiod)
    

    @staticmethod
    def MA(close, timeperiod=30, matype=0):
        # Moving average
        return talib.MA(close, timeperiod=timeperiod, matype=matype)
    

    @staticmethod
    def SMA(close, timeperiod=30):
        # Simple Moving Average
        return talib.SMA(close, timeperiod=timeperiod)
    

    @staticmethod
    def TEMA(close, timeperiod=30):
        # Triple Exponential Moving Average
        return talib.TEMA(close, timeperiod=timeperiod)
    

    @staticmethod
    def TRIMA(close, timeperiod=30):
        # Triangular Moving Average
        return talib.TRIMA(close, timeperiod=timeperiod)
    

    @staticmethod
    def WMA(close, timeperiod=30):
        # Weighted Moving Average
        return talib.WMA(close, timeperiod=timeperiod)


    # Momentum Indicator Functions
    @staticmethod
    def APO(close, fastperiod=12, slowperiod=26, matype=0):
        # Absolute Price Oscillator
        param = {
            'fastperiod': fastperiod,
            'slowperiod': slowperiod,
            'matype'    : matype,
        }

        return talib.APO(close, **param)
    

    @staticmethod
    def MACD(close, fastperiod=12, slowperiod=26, signalperiod=9):
        # Moving Average Convergence/Divergence
        param = {
            'fastperiod'  : fastperiod,
            'slowperiod'  : slowperiod,
            'signalperiod': signalperiod,
        }

        macd, macdsignal, macdhist = talib.MACD(close, **param)
        return macd, macdsignal, macdhist
    

    @staticmethod
    def MOM(close, timeperiod=10):
        # Momentum
        return talib.MOM(close, timeperiod=timeperiod)
    

    @staticmethod
    def PPO(close, fastperiod=12, slowperiod=26, matype=0):
        # Percentage Price Oscillator
        param = {
            'fastperiod': fastperiod,
            'slowperiod': slowperiod,
            'matype'    : matype,
        }

        return talib.PPO(close, **param)
    

    @staticmethod
    def ROC(close, timeperiod=10):
        # Rate of change : ((price/prevPrice)-1)*100
        return talib.ROC(close, timeperiod=timeperiod)
    

    @staticmethod
    def RSI(close, timeperiod=14):
        # Relative Strength Index
        return talib.RSI(close, timeperiod=timeperiod)


    # Volume Indicator Functions
    @staticmethod
    def AD(high, low, close, volume):
        # Chaikin A/D Line
        return talib.AD(high, low, close, volume)
    

    @staticmethod
    def ADOSC(high, low, close, volume, fastperiod=3, slowperiod=10):
        # Chaikin A/D Oscillator
        param = {
            'fastperiod': fastperiod,
            'slowperiod': slowperiod,
        }

        return talib.ADOSC(high, low, close, volume, **param)
    

    @staticmethod
    def OBV(close, volume):
        # On Balance Volume
        return talib.OBV(close, volume)


    # Volatility Indicator Functions
    @staticmethod
    def ATR(high, low, close, timeperiod=14):
        # Average True Range
        return talib.ATR(high, low, close, timeperiod=timeperiod)
    

    @staticmethod
    def NATR(high, low, close, timeperiod=14):
        # Normalized Average True Range
        return talib.NATR(high, low, close, timeperiod=timeperiod)
    

    @staticmethod
    def TRANGE(high, low, close):
        # True Range
        return talib.TRANGE(high, low, close)


if __name__ == '__main__':
    pass
