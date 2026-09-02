#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
logger
@author: Thomas Leysens
@source: http://sametmax.com/ecrire-des-logs-en-python/
"""

import logging
from logging.handlers import RotatingFileHandler
import time
import datetime
import os

filename = "activity.log"
try:
    os.remove(filename)
except OSError:
    pass

logger = logging.getLogger()
logger.setLevel(logging.INFO)
 
formatter = logging.Formatter('%(asctime)s :: %(levelname)s :: %(message)s')
file_handler = RotatingFileHandler('activity.log', 'a', 1000000, 1)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
 
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
logger.addHandler(stream_handler)


def _get_duration(start):
    """
    Description
    ------------
    
    Measure duration in seconde
    
    Returns
    --------
    
    Namedtuple Points object with:
        - coordinates: tuple with 2 lists (xs and ys)
        - geometry: list of Shapely Points
    
    Parameters
    -----------
    
    - pts (list of tuples coordinates):
        - List of coordinates
        - ex: [(4.56, 45.8), (4.8, 46.29)]
    - epsg_in (int):
        - Input EPSG
        - ex: 4326
    - epsg_out (int):
        - Output EPSG
        - ex: 2154
    
    """
    end=time.time()
    seconds = end-start
    duration = str(datetime.timedelta(seconds=seconds))
    
    return duration