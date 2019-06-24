# -*- coding: utf-8 -*-

# https://dev.mysql.com/doc/refman/8.0/en/creating-accounts.html
# sudo mysql -u root -p
# CREATE USER 'admin'@'localhost' IDENTIFIED BY 'admin';
# GRANT ALL ON *.* TO 'admin'@'localhost' WITH GRANT OPTION;

api_keys = {
    'alpha_vantage'  : 'your-api-key',
    'stock_news'     : 'your-api-key',
}

cache_url = {
    'host': '127.0.0.1',
    'port': 8000,
}

db_access = {
    'host'    : '127.0.0.1',
    'port'    : 3306,
    'user'    : 'admin',
    'password': 'admin',
}

db_init = {
    'db'     : 'StockDB',
    'symbols': ('GOOG', 'AMZN', 'AAPL', 'FB', 'MSFT', 'ADBE', 'UBER', 'TSLA', 'NFLX', 'BABA'),
}

description = {
    'GOOG': 'Alphabet, Inc.',
    'AMZN': 'Amazon.com, Inc.',
    'AAPL': 'Apple, Inc.',
    'FB'  : 'Facebook, Inc.',
    'MSFT': 'Microsoft Corporation',
    'ADBE': 'Adobe, Inc',
    'UBER': 'Uber Technologies, Inc.',
    'TSLA': 'Tesla, Inc',
    'NFLX': 'Netflix, Inc.',
    'BABA': 'Alibaba Group Holding Ltd.',
}

data_path = {
    'root_path': './data/',
}

log_path = {
    'root_path': './log/',
}