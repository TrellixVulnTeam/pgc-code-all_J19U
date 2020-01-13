# -*- coding: utf-8 -*-
"""
Created on Fri Jan  3 10:50:59 2020

@author: disbr007
Logging module helper functions
"""
import os
import logging


# logger_name = 'logger_name'
# handler_type = logging.StreamHandler() # fxn arg = 'sh' or 'fh'


def logging_level_int(logging_level):
    """
    Parameters
    ----------
    logging_level : STR
        One of the logging levels: 'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'
    
    Returns
    ---------
    INT
        The int corresponding to the logging level
    """
    for key, value in logging._levelToName.items():
        if value == logging_level: 
            return key 
  
    return "Logging level does not exist"


def create_logger(logger_name, handler_type, 
                   handler_level='INFO',
                   filename=None, 
                   duplicate=False):
    """
    Checks if handler of specified type already exists on the logger name
    passed. If it does, and duplicate == False, no new handler is created.
    If it does not, the new handler is created.

    Parameters
    ----------
    logger_name : STR
        The name of the logger, can be existing or not.
    handler_type : STR
        Handler type, either 'sh' for stream handler or 'fh' for file handler.
    handler_level : STR
        One of the logging levels: 'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'
    filename : STR
        Name of logging file, existing or new.
    duplicate : BOOLEAN
    
    Returns
    -------
    logger : logging.Logger
        Either the pre-existing or newly created logger.
    """
    # Create logger
    logger = logging.getLogger(logger_name)
    
    # Check if handlers already exists for logger
    handlers = logger.handlers
    handler = None
    # Parse input for requested handler type and level
    if handler_type == 'sh':
        ht = logging.StreamHandler()
    elif handler_type == 'fh':
        ht = logging.FileHandler(filename)
        # if os.path.exists(filename):
        #     os.remove(filename)
    else:
        print('Unrecognized handler_type argument.')
    desired_level = logging_level_int(handler_level)
    
    for h in handlers:
        # Check if existing handlers are of the right type (console or file)
        if isinstance(h, type(ht)):
            # Check if existing handler is of right level
            existing_level = h.level
            
            if existing_level == desired_level:
                handler = h
                break
    
    # If no handler of specified type and level was found, create it
    if handler is None:
        handler = ht
        logger.setLevel(logging.DEBUG)
        # Create console handler with a higher log level
        handler.setLevel(desired_level)
        # Create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        # Add the handler to the logger
        logger.addHandler(handler)

    return logger