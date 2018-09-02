# -*- coding: utf-8 -*-

"""
logger module
"""

import logging


def setup(logfile=None, level=logging.WARNING):
    """
    Setup the logger instance
    :param logfile: Name of the file to use for logging output
    :param level: Log level to set
    """
    logger = logging.getLogger(__package__)
    logger.setLevel(level)
    if logfile is None:
        logger_handler = logging.StreamHandler()
    else:
        logger_handler = logging.FileHandler(logfile)
    if level == logging.DEBUG:
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(threadName)s: %(name)s.%(funcName)s() %(message)s')
    else:
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(threadName)s: %(message)s')
    logger_handler.setLevel(level)
    logger_handler.setFormatter(formatter)
    logger.addHandler(logger_handler)
