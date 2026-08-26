import atexit
import logging
import logging.handlers
import os
import queue as _queue
from logging.handlers import RotatingFileHandler
import colorlog
from bot.constans import LOG_DIR

os.makedirs(LOG_DIR, exist_ok=True)

LOG_MAX_BYTES = 10 * 1024 * 1024
LOG_BACKUP_COUNT = 5

_LOG_QUEUE_MAXSIZE = 10000
_file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
_color_formatter = colorlog.ColoredFormatter(
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

_stream_handler = colorlog.StreamHandler()
_stream_handler.setLevel(logging.DEBUG)
_stream_handler.setFormatter(_color_formatter)

_logger_cache: dict = {}
_file_handlers: dict = {}
_listeners: dict = {}


def _make_file_handler(log_filename: str) -> RotatingFileHandler:
    handler = _file_handlers.get(log_filename)
    if handler is not None:
        return handler
    handler = RotatingFileHandler(
        os.path.join(LOG_DIR, log_filename),
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8',
    )
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(_file_formatter)
    _file_handlers[log_filename] = handler
    return handler


def setup_logger(log_filename: str) -> logging.Logger:
    cached = _logger_cache.get(log_filename)
    if cached is not None:
        return cached

    logger = logging.getLogger(log_filename)
    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        log_queue: _queue.Queue = _queue.Queue(maxsize=_LOG_QUEUE_MAXSIZE)
        queue_handler = logging.handlers.QueueHandler(log_queue)
        queue_handler.setLevel(logging.DEBUG)
        logger.addHandler(queue_handler)

        file_handler = _make_file_handler(log_filename)
        listener = logging.handlers.QueueListener(
            log_queue,
            file_handler,
            _stream_handler,
            respect_handler_level=True,
        )
        listener.start()
        _listeners[log_filename] = listener

    _logger_cache[log_filename] = logger
    return logger


def _shutdown_listeners() -> None:
    for listener in list(_listeners.values()):
        try:
            listener.stop()
        except Exception:
            pass
    _listeners.clear()


atexit.register(_shutdown_listeners)


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
