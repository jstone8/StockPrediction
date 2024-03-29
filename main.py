# -*- coding: utf-8 -*-

import logging

from config import log_path
from dataCollection import collect_data
from feature import update_feature
from transaction import trade
from cache import reset_all_cached


_log_filename = log_path['root_path'] + 'stock_prediction.log'

log_param = {
    'filename': _log_filename, 
    'filemode': 'a',
    'format'  : '%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s',
    'datefmt' : '%Y-%m-%d %H:%M:%S',
    'style'   : '%',
    'level'   : logging.INFO,
}

logging.basicConfig(**log_param)


def main():
    logging.info('Running main function')

    try:
        collect_data()
        update_feature()
        trade()
        reset_all_cached()
    except:
        logging.exception('Critical error occurs')

    logging.info('Complete main function')


if __name__ == '__main__':
    main()
