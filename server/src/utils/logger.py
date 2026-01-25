"""
Logging configuration for the FastAPI application.

This module provides a centralized logging setup with:
- Colorized console output for better readability
- Configurable log levels via environment variables
- Optional file logging
- Request logging middleware

Usage:
    from src.utils.logger import logger
    
    logger.info("Server started")
    logger.debug("Processing request")
    logger.error("Something went wrong", exc_info=True)
"""

import logging
import os
import sys
from datetime import datetime
from typing import Optional

# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for colorized log output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    FAINT = "\033[2m"
    
    # Log level colors
    DEBUG = "\033[36m"    # Cyan
    INFO = "\033[32m"     # Green
    WARNING = "\033[33m"  # Yellow
    ERROR = "\033[31m"    # Red
    CRITICAL = "\033[35m" # Magenta
    
    # Component colors
    TIMESTAMP = "\033[90m"  # Gray
    LOGGER_NAME = "\033[36m"  # Cyan


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter that adds colors to log output.
    
    Format: HH:MM:SS LEVEL --- [logger_name] : message
    """
    
    LEVEL_COLORS = {
        logging.DEBUG: Colors.DEBUG,
        logging.INFO: Colors.INFO,
        logging.WARNING: Colors.WARNING,
        logging.ERROR: Colors.ERROR,
        logging.CRITICAL: Colors.CRITICAL,
    }
    
    def format(self, record: logging.LogRecord) -> str:
        # Get the color for this log level
        level_color = self.LEVEL_COLORS.get(record.levelno, Colors.RESET)
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        
        # Format level name (padded to 5 chars)
        level_name = f"{record.levelname:>5}"
        
        # Format logger name (truncated to 40 chars)
        logger_name = record.name[-40:] if len(record.name) > 40 else record.name
        
        # Build the formatted message
        formatted = (
            f"{Colors.FAINT}{timestamp}{Colors.RESET} "
            f"{level_color}{level_name}{Colors.RESET} "
            f"{Colors.FAINT}---{Colors.RESET} "
            f"{Colors.FAINT}[{Colors.RESET}"
            f"{Colors.LOGGER_NAME}{logger_name:>40}{Colors.RESET}"
            f"{Colors.FAINT}]{Colors.RESET} "
            f"{Colors.FAINT}:{Colors.RESET} "
            f"{record.getMessage()}"
        )
        
        # Add exception info if present
        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)
        
        return formatted


class PlainFormatter(logging.Formatter):
    """Plain text formatter for file logging (no colors)."""
    
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        level_name = f"{record.levelname:>5}"
        logger_name = record.name[-40:] if len(record.name) > 40 else record.name
        
        formatted = f"{timestamp} {level_name} --- [{logger_name:>40}] : {record.getMessage()}"
        
        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)
        
        return formatted


def setup_logger(
    name: str = "mflix",
    level: Optional[str] = None,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Set up and configure a logger instance.
    
    Args:
        name: Logger name (default: "mflix")
        level: Log level (default: from LOG_LEVEL env var or INFO)
        log_file: Optional file path for file logging
    
    Returns:
        Configured logger instance
    """
    # Get log level from environment or parameter
    log_level_str = level or os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)
    
    # File handler (optional)
    file_path = log_file or os.getenv("LOG_FILE")
    if file_path:
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(PlainFormatter())
        logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


# Create the default application logger
logger = setup_logger()

