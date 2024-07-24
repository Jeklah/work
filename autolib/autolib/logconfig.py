import sys
import logging


autolib_log = "autolib_log"
autolib_log_filename = "autolib_tests.log"


def log_handler(**kwargs):
    """
    Create a logging instance that logs to the autolib main log.
    :key log_level: The logging level to use (e.g. logging.INFO)
    :key log_to_stdout: In addition to logging to a file, lot to stdout
    :key log_filename: The name of the file to log to.
    """
    log_level = kwargs.get("log_level", logging.INFO)
    log_to_stdout = kwargs.get("log_to_stdout", False)
    log_filename = kwargs.get("log_filename", autolib_log_filename)

    log = logging.getLogger(autolib_log)

    log.setLevel(log_level)

    # Create the log handler
    handler = logging.FileHandler(log_filename, "w", encoding=None, delay=True)

    # Specify log line format
    formatter = logging.Formatter("%(asctime)s - %(threadName)s - %(levelname)s -: %(message)s")

    # Bind formatter to handler
    handler.setFormatter(formatter)

    # Bind handler to logger
    log.addHandler(handler)

    if log_to_stdout:
        # Create a stdout log handler
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(formatter)
        log.addHandler(stdout_handler)

    return log
