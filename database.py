# -*- coding: utf-8 -*-

import logging
import mysql.connector
from typing import Sequence, List, Tuple, Dict
from config import access_credential, db_init

logger = logging.getLogger(__name__)


#############################################################
# SQL Statements

# ===========================================================
create_db = 'CREATE DATABASE IF NOT EXISTS {db}'

# ===========================================================
create_table_intraday = \
'''
CREATE TABLE IF NOT EXISTS {symbol}_Intraday (
    id int NOT NULL AUTO_INCREMENT,
    date_time varchar(255) NOT NULL, /* yyyy-mm-dd hh:mm:ss */
    timezone varchar(255) NOT NULL,
    open varchar(255) NOT NULL,
    high varchar(255) NOT NULL,
    low varchar(255) NOT NULL,
    close varchar(255) NOT NULL,
    volume varchar(255) NOT NULL,
    PRIMARY KEY (id)
);
'''

insert_into_intraday = \
'''
INSERT INTO {symbol}_Intraday (date_time, timezone, open, high, low, close, volume) 
VALUES (%s, %s, %s, %s, %s, %s, %s);
'''

select_from_intraday = \
'''
SELECT date_time, open, high, low, close, volume FROM {symbol}_Intraday
WHERE date_time >= '{start}' ORDER BY date_time;
'''

# ===========================================================
create_table_daily = \
'''
CREATE TABLE IF NOT EXISTS {symbol}_Daily (
    id int NOT NULL AUTO_INCREMENT,
    date_string varchar(255) NOT NULL, /* yyyy-mm-dd */
    timezone varchar(255) NOT NULL,    /* e.g. UTC-05:00 */
    open varchar(255) NOT NULL,
    high varchar(255) NOT NULL,
    low varchar(255) NOT NULL,
    close varchar(255) NOT NULL,
    adjusted_close varchar(255) NOT NULL,
    volume varchar(255) NOT NULL,
    dividend varchar(255),
    split_coeff varchar(255),
    PRIMARY KEY (id)
);
'''

insert_into_daily = \
'''
INSERT INTO {symbol}_Daily (date_string, timezone, open, high, low, close, adjusted_close, volume, dividend, split_coeff) 
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
'''

select_from_daily = \
'''
SELECT date_string, open, high, low, close, adjusted_close, volume FROM {symbol}_Daily
WHERE date_string >= '{start}' ORDER BY date_string;
'''

# ===========================================================
create_table_stock_news = \
'''
CREATE TABLE IF NOT EXISTS Stock_News (
    id int NOT NULL AUTO_INCREMENT,
    symbol varchar(15) NOT NULL,     /* stock symbol or 'Market' */
    date_time varchar(255) NOT NULL,
    timezone varchar(255) NOT NULL,
    title varchar(1023) NOT NULL,
    news_url varchar(1023),
    image_url varchar(1023),
    content text(65535),
    sentiment varchar(255),
    source_name varchar(255),
    PRIMARY KEY (id)
);
'''

insert_into_stock_news = \
'''
INSERT INTO Stock_News (symbol, date_time, timezone, title, news_url, image_url, content, sentiment, source_name) 
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
'''

select_from_stock_news = \
'''
SELECT date_time, title, content, sentiment FROM Stock_News 
WHERE symbol = '{symbol}' AND date_time >= '{start}' ORDER BY date_time;
'''

# ===========================================================
select_last_trade_day = \
'''
SELECT MAX(date_string) FROM {symbol}_Daily
'''


#############################################################
class Database(object):
    '''Database management'''

    @classmethod
    def init_db(cls, db: str, symbol: str, *other_symbols) -> None:
        '''Create database and tables
           
           @param: db: name of the database to be created
           @param: symbol: create intraday/daily table for the symbol
           @param: other_symbols: additional symbols to add
        '''

        connect = mysql.connector.connect(host='localhost', **access_credential)
        cursor = connect.cursor()

        cursor.execute(create_db.format(db=db))
        cursor.execute('USE ' + db)

        cursor.execute(create_table_stock_news)

        for ticker in (symbol,) + other_symbols:
            cursor.execute(create_table_intraday.format(symbol=ticker))
            cursor.execute(create_table_daily.format(symbol=ticker))

        cursor.close()
        connect.close()


    @classmethod
    def _insert_data(cls, db: str, sql: str, data: Sequence[tuple]) -> None:
        '''Insert data into table using the sql statement
           
           @param: db: name of the database to use
           @param: str: insertion sql to be executed
           @param: data: sequence of records to be inserted
        '''

        connect = mysql.connector.connect(host='localhost', **access_credential)
        cursor = connect.cursor()
        cursor.execute('USE ' + db)

        cursor.executemany(sql, data)

        connect.commit()
        cursor.close()
        connect.close()


    @classmethod
    def insert_data_intraday(cls, db: str, symbol: str, data: Sequence[tuple]) -> None:
        cls._insert_data(db, insert_into_intraday.format(symbol=symbol), data)


    @classmethod
    def insert_data_daily(cls, db: str, symbol: str, data: Sequence[tuple]) -> None:
        cls._insert_data(db, insert_into_daily.format(symbol=symbol), data)


    @classmethod
    def insert_data_news(cls, db: str, data: Sequence[tuple]) -> None:
        cls._insert_data(db, insert_into_stock_news, data)


    @classmethod
    def _get_data(cls, db: str, sql: str) -> Sequence[tuple]:
        '''Get data from table using the sql statement
           
           @param: db: name of the database to use
           @param: str: selection sql to be executed
           @return: List of tuples
        '''

        connect = mysql.connector.connect(host='localhost', **access_credential)
        cursor = connect.cursor()
        cursor.execute('USE ' + db)

        cursor.execute(sql)
        data = cursor.fetchall()

        cursor.close()
        connect.close()

        return data


    @classmethod
    def get_data_intraday(cls, db: str, symbol: str, start: str = '1900-01-01'):
        return cls._get_data(db, select_from_intraday.format(symbol=symbol, start=start))


    @classmethod
    def get_data_daily(cls, db: str, symbol: str, start: str = '1900-01-01'):
        return cls._get_data(db, select_from_daily.format(symbol=symbol, start=start))


    @classmethod
    def get_data_news(cls, db: str, symbol: str, start: str = '1900-01-01'):
        return cls._get_data(db, select_from_stock_news.format(symbol=symbol, start=start))


    @classmethod
    def get_last_trade_day(cls, db: str, symbol: str) -> str:
        return cls._get_data(db, select_last_trade_day.format(symbol=symbol))[0][0]


def retrieve_price_news(db: str = '', symbols: Sequence[str] = (), 
                        start: str = '1900-01-01') -> tuple:
    '''Get market news, and daily price/volume and news for all symbols
       
       @param: start: retrieve data since this date
       @param: symbols: sequence of symbols to retrieve data. If empty, use all symbols
    '''

    if not db: db = db_init['db']
    if not symbols: symbols = db_init['symbols']

    market_news = Database.get_data_news(db, 'Market', start=start)
    data = {symbol: {} for symbol in symbols}

    for symbol in symbols:
        data[symbol]['daily'] = Database.get_data_daily(db, symbol, start=start)
        data[symbol]['news'] = Database.get_data_news(db, symbol, start=start)

    return market_news, data


def main():
    assert len(db_init['symbols']) > 0, 'Must provide at least one symbol'
    Database.init_db(db_init['db'], *db_init['symbols'])


def test():
    db = 'TestDB'
    symbols = ('GOOG', 'AMZN', 'AAPL', 'FB', 'MSFT')
    Database.init_db(db, *symbols)

    data_intraday = [
        ("2019-05-24 16:00:00","US/Eastern","126.2200","126.3400","126.0300","126.0300","809795"),
        ("2019-05-24 16:00:00","US/Eastern","126.2200","126.3400","126.0300","126.0300","809795")
    ]
    Database.insert_data_intraday(db, 'MSFT', data_intraday)

    data_daily = [
        ("2019-05-24","US/Eastern","126.9100","127.4150","125.9700","126.2400","126.2400","14123358","0.0000","1.0000"),
        ("2019-05-23","US/Eastern","126.2000","126.2900","124.7400","126.1800","126.1800","23603810","0.0000","1.0000")
    ]
    Database.insert_data_daily(db, 'MSFT', data_daily)

    data_stock_news = [
        ("TSLA","2019-05-28 11:13:12","US/Eastern","This Chinese Electric Car Maker Has Just Heaped Even More Pressure On Tesla","http://feedproxy.google.com/~r/BusinessRss/~3/bDnBSXknrmQ/","https://stocknewsapi.com/images/v1/n/i/niotes72.jpg","Electric car maker Nio advanced after the Chinese Tesla rival posted better-than-expected Q1 earnings, as ES8 deliveries rose despite a fall in subsidies.","Neutral","Investors Business Daily"),
        ("Market","2019-05-28 11:13:12","US/Eastern","This Chinese Electric Car Maker Has Just Heaped Even More Pressure On Tesla","http://feedproxy.google.com/~r/BusinessRss/~3/bDnBSXknrmQ/","https://stocknewsapi.com/images/v1/n/i/niotes72.jpg","Electric car maker Nio advanced after the Chinese Tesla rival posted better-than-expected Q1 earnings, as ES8 deliveries rose despite a fall in subsidies.","Neutral","Investors Business Daily")
    ]
    Database.insert_data_news(db, data_stock_news)


if __name__ == '__main__':
    main()
