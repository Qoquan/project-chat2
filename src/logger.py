import logging
import sys
from datetime import datetime

def setup_logger(name: str = "Chat labo", level: int = logging.INFO) -> logging.Logger:
    """Set up and return a logger with colored setup."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if logger.hasHandlers :
        return logger  # Avoid adding multiple handlers
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    class ColoredFormatter(logging.Formatter):
        """Custom formater with ANSI colors.   """
        
        COLORS = {
            'DEBUG': '\033[94m',    # Blue
            'INFO': '\033[92m',     # Green
            'WARNING': '\033[93m',  # Yellow
            'ERROR': '\033[91m',    # Red
            'CRITICAL': '\033[95m', # Magenta
        }
        RESET = '\033[0m'
        BOLD = '\033[1m'
        
        def format(self, record):
            color = self.COLORS.get(record.levelname, self.RESET)
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_message = (
                f"{self.BOLD}[{timestamp}]{self.RESET}"
                f" {color}{record.levelname:8}{self.RESET} - "
                f"{record.getMessage()}"
            )
            if record.exc_info:
                log_message += f"\n{self.formatException(record.exc_info)}"
                
            return log_message
        
    formatter = ColoredFormatter()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

server_logger = setup_logger("Chat labo", logging.INFO)

def log_info(message: str):
    server_logger.info(message)
    
def log_warning(message: str):
    server_logger.warning(message)
    
def log_error(message: str):
    server_logger.error(message)

def log_debug(message: str):
    server_logger.debug(message)
    
def log_critical(message: str):
    server_logger.critical(message)
    