import logging
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from datetime import datetime

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Ensure logs have correct filenames
def get_log_filename():
    return logs_dir / f"bot_{datetime.now().strftime('%Y-%m-%d')}.log"

# Create a TimedRotatingFileHandler with proper filename format
class CustomTimedRotatingFileHandler(TimedRotatingFileHandler):
    def __init__(self, filename, when="midnight", interval=1, backupCount=7, encoding="utf-8", utc=True):
        super().__init__(filename, when, interval, backupCount, encoding, utc)
        self.baseFilename = str(get_log_filename())  # Ensures correct naming on startup

    def doRollover(self):
        """Ensure the new log file follows the naming format"""
        self.stream.close()
        new_log_filename = get_log_filename()
        if self.backupCount > 0:
            self.rotate(self.baseFilename, new_log_filename)
        self.baseFilename = str(new_log_filename)
        self.stream = self._open()

# Initialize logging with correct formatting
log_file = get_log_filename()

handler = CustomTimedRotatingFileHandler(
    filename=str(log_file),  # Ensure it starts with the correct filename
    when="midnight",
    interval=1,
    backupCount=7,
    encoding="utf-8",
    utc=True  # Ensures UTC-based rotation
)

# Set log formatting
formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
handler.setFormatter(formatter)

logger = logging.getLogger("TrabajoBot")
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)
logger.propagate = False  # Prevent double logging

# Console logging
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)  # Set to DEBUG to see all logs
console_format = logging.Formatter("[%(levelname)s] [%(name)s] %(message)s")
console_handler.setFormatter(console_format)
logger.addHandler(console_handler)
