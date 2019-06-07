# -*- coding: utf-8 -*-

import logging
from dataCollection import collect_data
from feature import update_feature
from transaction import trade

_log_folder = './log/'
_log_filename = _log_folder + 'stock_prediction.log'

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

    #collect_data()
    #update_feature()
    trade()

    logging.info('Complete main function')


if __name__ == '__main__':
    main()
