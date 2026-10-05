import logging

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
NOISY_LOGGERS = ["httpx", "httpcore"]


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=level.upper(),
        format=LOG_FORMAT,
        force=True,
    )

    for name in NOISY_LOGGERS:
        noisy_logger = logging.getLogger(name)
        noisy_logger.setLevel(logging.WARNING)