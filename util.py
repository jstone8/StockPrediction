# -*- coding: utf-8 -*-

import pytz
from typing import Sequence, List, Tuple, Dict
from datetime import datetime


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
    try:
        datetime.strptime(date_string, fmt)
    except:
        return False

    return True