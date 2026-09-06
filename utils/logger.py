import json
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def setup_logger() -> logging.Logger:
    Path("logs").mkdir(exist_ok=True)
    logger = logging.getLogger("auto_accept")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    handler = TimedRotatingFileHandler("logs/bot.log", when="midnight", backupCount=30, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler())
    return logger


def log_json(logger: logging.Logger, event: str, **details: object) -> None:
    logger.info(json.dumps({"event": event, **details}, ensure_ascii=False, default=str))
