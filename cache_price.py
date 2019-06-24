# -*- coding: utf-8 -*-

import logging

from config import db_init, log_path
from cache import Cache


_log_filename = log_path['root_path'] + 'cache_price.log'

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

    Cache.set_price(db_init['symbols'])

    logging.info('Complete main function')


if __name__ == '__main__':
    main()
