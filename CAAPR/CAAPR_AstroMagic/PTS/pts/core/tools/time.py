#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.tools.time Provides functions for dealing with timestamps etc.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import time as _time
from datetime import datetime

# -----------------------------------------------------------------

def wait(seconds):

    """
    This function ...
    :param seconds:
    :return:
    """

    _time.sleep(seconds)

# -----------------------------------------------------------------

def parse(timestamp):

    """
    This function ...
    :param string:
    :return:
    """

    # Parse the timestamp
    date, time = timestamp.split()

    # Combine the date and time stamp to a datetime object
    return parse_date_time(date, time)

# -----------------------------------------------------------------

def parse_line(line):

    """
    This function returns the datetime object corresponding to a certain time stamp (as a string)
    :param line:
    :return:
    """

    # Parse the line
    date, time, dummy = line.split(None, 2)

    # Combine the date and time stamp to a datetime object
    return parse_date_time(date, time)

# -----------------------------------------------------------------

def parse_date_time(date, time):

    """
    This function ...
    :param date:
    :param time:
    :return:
    """

    try: day, month, year = date.split('/')
    except ValueError: return None
    hour, minute, second = time.split(':')
    second, microsecond = second.split('.')

    # Convert the strings to integers
    year = int(year)
    month = int(month)
    day = int(day)
    hour = int(hour)
    minute = int(minute)
    second = int(second)
    microsecond = int(microsecond)

    # Create and return a datetime object
    return datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second, microsecond=microsecond)

# -----------------------------------------------------------------

def now():

    """
    This function ...
    :return:
    """

    return datetime.now()

# -----------------------------------------------------------------

def timestamp():

    """
    This function generates a timestamp (as a string) from a datetime object
    :return:
    """

    # Return a timestamp accurate up to the millisecond
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S.%f")[:-3]

# -----------------------------------------------------------------

def day_and_time_as_string():

    """
    This function ...
    :return:
    """

    return datetime.now().strftime("%A, %d. %B %Y %I:%M%p")

# -----------------------------------------------------------------

def unique_name(name=None, separator="_", precision="milli"):

    """
    This function ...
    :param name:
    :param separator:
    :param precision:
    :return:
    """

    if precision == "milli" or precision == "millisecond": ndigits = 3
    elif precision == "micro" or precision == "microsecond": ndigits = 0
    else: raise ValueError("Invalid precision")

    if name is None: return strip_last_digits(datetime.now().strftime("%Y-%m-%d--%H-%M-%S-%f"), ndigits)
    else:

        # Add a timestamp accurate up to the millisecond to the passed name
        return name + separator + strip_last_digits(datetime.now().strftime("%Y-%m-%d--%H-%M-%S-%f"), ndigits)

# -----------------------------------------------------------------

def strip_last_digits(string, ndigits):

    """
    This function ...
    :param string:
    :param ndigits:
    :return:
    """

    if ndigits == 0: return string
    else: return string[:-ndigits]

# -----------------------------------------------------------------
