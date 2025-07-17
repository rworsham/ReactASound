import logging
from logging.handlers import TimedRotatingFileHandler

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = TimedRotatingFileHandler(
            filename="ReactASound_Log.txt",
            when="midnight",
            interval=1,
            backupCount=7
        )
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)