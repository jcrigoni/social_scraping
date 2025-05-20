import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime

def setup_logger(name, log_dir='logs'):
    """
    Creates a logging system that writes to both console and files
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # File handler for all logs
    all_logs_file = os.path.join(
        log_dir, 
        f'scraper_all_{datetime.now().strftime("%Y%m%d")}.log'
    )
    file_handler = RotatingFileHandler(
        all_logs_file, maxBytes=10485760, backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Error file handler
    error_logs_file = os.path.join(
        log_dir, 
        f'scraper_errors_{datetime.now().strftime("%Y%m%d")}.log'
    )
    error_file_handler = RotatingFileHandler(
        error_logs_file, maxBytes=10485760, backupCount=5
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(error_file_handler)
    logger.addHandler(console_handler)
    
    return logger