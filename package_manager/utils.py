import logging
from datetime import datetime

def setup_logger():
    """Configure and return a logger instance"""
    logger = logging.getLogger('package_manager')
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
    
    return logger
