import logging
from logging.handlers import RotatingFileHandler
import colorlog


def setup_logger(log_file, level=logging.INFO):
    stdout_handler = colorlog.StreamHandler()
    stdout_handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s [%(asctime)s] | %(levelname)s | %(message)s', "%Y-%m-%d %H:%M:%S"))

    file_handler = RotatingFileHandler(
        log_file,
        mode='w+',
        maxBytes=5000000,  # 5 MBytes
        backupCount=20)
    formatter = logging.Formatter('[%(asctime)s] | %(levelname)s | %(message)s', "%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(formatter)

    logger = logging.getLogger("main")
    logger.handlers.clear()
    logger.addHandler(stdout_handler)
    logger.addHandler(file_handler)
    logger.setLevel(level)

    return logger
