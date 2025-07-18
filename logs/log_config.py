import logging
from logging.handlers import TimedRotatingFileHandler
import os

def setup_logging():
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = TimedRotatingFileHandler(
            filename=os.path.join(log_dir, "ReactASound_Log.txt"),
            when="midnight",
            interval=1,
            backupCount=7
        )
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
