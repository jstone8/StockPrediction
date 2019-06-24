# -*- coding: utf-8 -*-

import time
from typing import Sequence, List, Tuple, Dict
from collections import deque
from datetime import datetime
from functools import wraps

import pytz


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
    '''Pop the last line of a file
        
       @param: filepath: path/name of the file
    '''

    with open(filepath, 'r') as f:
        lines = f.readlines()

    with open(filepath, 'w') as f:
        for line in lines[:-1]:
            f.write(line)

    return lines[-1].strip() if len(lines) > 0 else ''


def get_last_n_lines(filepath: str, n: int) -> Tuple[str]:
    '''Read the last n lines of a file.

       @param: filepath: path/name of the file
       @param: n: number of lines to read
    '''
    with open(filepath, 'r') as f:
        last_n_lines = deque(f, n)

    return map(lambda line: line.strip(), last_n_lines)