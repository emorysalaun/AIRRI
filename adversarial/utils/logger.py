import logging
import os
import sys
from datetime import datetime


# dual output logger, terminal + file
class ExperimentLogger:
    def __init__(self, experiment_name: str, log_dir: str, level=logging.INFO):
        self.experiment_name = experiment_name

        os.makedirs(log_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"{experiment_name}_{timestamp}.log")

        self._logger = logging.getLogger(experiment_name)
        self._logger.setLevel(level)
        self._logger.propagate = False  # avoid duplicate output

        fmt = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Console handler bound to terminal output
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(fmt)
        self._logger.addHandler(console_handler)

        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(fmt)
        self._logger.addHandler(file_handler)

        self.log_file = log_file
        self.info(f"Logging to: {log_file}")

    # ---- wrappers ----

    def info(self, msg: str):
        self._logger.info(msg)

    def warning(self, msg: str):
        self._logger.warning(msg)

    def error(self, msg: str):
        self._logger.error(msg)

    def debug(self, msg: str):
        self._logger.debug(msg)

    def empty_line(self):
        # iterate over handlers and write a newline directly
        for handler in self._logger.handlers:
            if hasattr(handler, "stream") and handler.stream:
                try:
                    handler.stream.write("\n")
                    handler.flush()
                except Exception:
                    pass

    def section(self, title: str, char: str = "=", width: int = 70):
        # prints a section header
        self.empty_line()
        banner = char * width
        self._logger.info(banner)
        self._logger.info(title)
        self._logger.info(banner)

    def subsection(self, title: str, char: str = "-", width: int = 70):
        # prints a subsection header
        banner = char * width
        self._logger.info(banner)
        self._logger.info(title)
        self._logger.info(banner)
