import logging
import inspect

LOGGING_FORMAT = "[%(asctime)s][%(name)s][%(levelname)s] %(message)s"
ERROR_FORMAT = LOGGING_FORMAT + " (%(filename)s:%(lineno)d)"

LOGGING_LEVEL = logging.INFO
FILE_LOGGING_LEVEL = logging.DEBUG
LOG_FILE = "gui4us.log"


# Credits:
# https://stackoverflow.com/questions/384076/
# how-can-i-color-python-logging-output#answer-56944256
class ColoredTxtFormatter(logging.Formatter):
    grey = "\x1b[38;21m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    FORMATS = {
        logging.DEBUG: grey + LOGGING_FORMAT + reset,
        logging.INFO: grey + LOGGING_FORMAT + reset,
        logging.WARNING: yellow + ERROR_FORMAT + reset,
        logging.ERROR: red + ERROR_FORMAT + reset,
        logging.CRITICAL: bold_red + ERROR_FORMAT + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class LoggerFactory:

    def __init__(self):
        pass

    # Logging
    def get_logger(self, component):
        if inspect.isclass(component):
            class_module = component.__module__
            class_name = component.__name__
            logger = logging.getLogger(f"{class_module}.{class_name}")
        else:
            # `component` is the name of component as a string
            logger = logging.getLogger(component)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(LOGGING_LEVEL)
        colored_text_formatter = ColoredTxtFormatter()
        console_handler.setFormatter(colored_text_formatter)
        logger.addHandler(console_handler)

        file_handler = logging.FileHandler(filename=LOG_FILE)
        file_handler.setLevel(FILE_LOGGING_LEVEL)
        file_formatter = logging.Formatter(LOGGING_FORMAT)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        # Use the most broad logging level.
        logger.setLevel(FILE_LOGGING_LEVEL)

        logger.propagate = False
        return logger


__LOGGER_FACTORY = LoggerFactory()


def get_logger(*args, **kwargs):
    return __LOGGER_FACTORY.get_logger(*args, **kwargs)