"""
Logging configuration with rotating file handlers.
Module for centralized logging setup across the project.
"""

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional


class LoggingConfig:
    """Centralized logging configuration"""
    
    # Log directory
    LOG_DIR = Path(__file__).parent / "logs"
    
    # Log file sizes and backups
    MAX_BYTES = 10 * 1024 * 1024  # 10 MB
    BACKUP_COUNT = 5
    
    # Log format
    DETAILED_FORMAT = (
        '%(asctime)s - %(name)s - %(levelname)s - '
        '[%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s'
    )
    SIMPLE_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    @staticmethod
    def setup_logger(
        name: str,
        log_file: str = "app.log",
        level: int = logging.DEBUG,
        console_level: int = logging.INFO,
        use_detailed_format: bool = True
    ) -> logging.Logger:
        """
        Setup logger with rotating file handler and console handler.
        
        Args:
            name: Logger name (usually __name__)
            log_file: Name of the log file in logs directory
            level: File logging level (default DEBUG)
            console_level: Console logging level (default INFO)
            use_detailed_format: Use detailed format with function names
            
        Returns:
            Configured logger instance
        """
        # Create log directory if not exists
        LoggingConfig.LOG_DIR.mkdir(exist_ok=True)
        
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)  # Logger catches all levels
        
        # Prevent adding duplicate handlers
        if logger.handlers:
            return logger
        
        # Format
        formatter = logging.Formatter(
            LoggingConfig.DETAILED_FORMAT 
            if use_detailed_format 
            else LoggingConfig.SIMPLE_FORMAT,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File handler with rotation
        log_path = LoggingConfig.LOG_DIR / log_file
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_path,
            maxBytes=LoggingConfig.MAX_BYTES,
            backupCount=LoggingConfig.BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    @staticmethod
    def get_logger(name: str, log_file: str = "app.log") -> logging.Logger:
        """
        Get or create logger with standard configuration.
        
        Args:
            name: Logger name
            log_file: Log file name
            
        Returns:
            Logger instance
        """
        return LoggingConfig.setup_logger(name, log_file)


# Create module-level loggers for common use cases
def get_bot_logger() -> logging.Logger:
    """Get logger for bot module"""
    return LoggingConfig.get_logger("quicksay_bot", "bot.log")


def get_worker_logger() -> logging.Logger:
    """Get logger for celery worker"""
    return LoggingConfig.get_logger("quicksay_worker", "celery_worker.log")


def get_webhook_logger() -> logging.Logger:
    """Get logger for webhook server"""
    return LoggingConfig.get_logger("quicksay_webhook", "webhook_server.log")


def get_db_logger() -> logging.Logger:
    """Get logger for database operations"""
    return LoggingConfig.get_logger("quicksay_db", "database.log")


def get_payment_logger() -> logging.Logger:
    """Get logger for payment operations"""
    return LoggingConfig.get_logger("quicksay_payments", "payments.log")


# Export main function for easy access
setup_logger = LoggingConfig.setup_logger
get_logger = LoggingConfig.get_logger
