import logging
import os
import colorlog
from constans import LOG_DIR

os.makedirs(LOG_DIR, exist_ok=True)

def setup_logger(log_filename):
    logger = logging.getLogger(log_filename)

    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)

        file_handler = logging.FileHandler(os.path.join(LOG_DIR, log_filename), encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        stream_handler = colorlog.StreamHandler()
        stream_handler.setLevel(logging.DEBUG)

        color_formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
            }
        )
        stream_handler.setFormatter(color_formatter)

        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

    return logger


def log(message, context="global", level="INFO"):
    if context == "global":
        log_filename = "log.log"
    else:
        log_filename = f"{context}.log"

    logger = setup_logger(log_filename)

    if level == "INFO":
        logger.info(f"[{context}] {message}")
    elif level == "WARNING":
        logger.warning(f"[{context}] {message}")
    elif level == "ERROR":
        logger.error(f"[{context}] {message}")
    elif level == "DEBUG":
        logger.debug(f"[{context}] {message}")
    else:
        logger.info(f"[{context}] {message}")
