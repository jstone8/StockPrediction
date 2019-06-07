# -*- coding: utf-8 -*-

import pytz
import time
from typing import Sequence, List, Tuple, Dict
from datetime import datetime
from functools import wraps


def timed(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print('{} ran in {}s'.format(func.__name__, round(end - start, 2)))
        return result
    return wrapper


def standardize_datetime(date_string: str, fmt: str, include_time: bool = True,
                         to_timezone: str = '') -> str:
    '''Convert date based on timezone and format to yyyy-mm-dd

       @param: date_string: date string to be standardized
       @param: fmt: format of the provided date string
       @param: include_time: whether to include time with format hh:mm:ss
       @param: to_timezone: convert date to the specified timezone, e.g. US/Eastern
    '''

    date_time = datetime.strptime(date_string, fmt)

    if to_timezone:
        tz = pytz.timezone(to_timezone)
        date_time = date_time.astimezone(tz)

    if include_time: 
        return date_time.strftime('%Y-%m-%d %H:%M:%S')
        
    return date_time.strftime('%Y-%m-%d')


def validate_date_fmt(date_string: str, fmt: str) -> bool:
    '''Validate date format

       @param: date_string: date string to be validated
       @param: fmt: desired date format
    '''

    try:
        datetime.strptime(date_string, fmt)
    except:
        return False

    return True


def get_last_line(filepath: str) -> str:
    '''Read the last line of a file. In Linux, this can be done quickly 
       using 'tail -n 1 filepath'

       @param: filepath: path/name of the file
    '''

    last_line = ''

    with open(filepath, 'r') as f:
        for line in f: last_line = line

    return last_line.strip()


def pop_last_line(filepath: str) -> str:
    '''Pop the last line of a file'''

    with open(filepath, 'r') as f:
        lines = f.readlines()

    with open(filepath, 'w') as f:
        for line in lines[:-1]:
            f.write(line)

    return lines[-1].strip() if len(lines) > 0 else ''
