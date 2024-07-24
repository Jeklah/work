"""\
This timeout decorator is derived from this StackOverflow post and can be used to wrap code in the autolib
core to impose a customisable timeout after which the wrapped method will throw a TimeoutException.

https://stackoverflow.com/questions/2281850/timeout-function-if-it-takes-too-long-to-finish
"""

import errno
import os
import signal
import functools

from autolib.coreexception import CoreException


class TimeoutException(CoreException):
    """\
    Indicates that a wrapped function or method has not completed within the specified time period.
    """
    pass


def timeout(seconds: int = 10, error_message: str = os.strerror(errno.ETIME)):
    """\
    Decorator that wraps methods such that if they do not complete within a specified time they are terminated and
    a TimeoutException is raised.

    :param seconds: Timeout duration in seconds
    :param error_message: An error message to use in the TimeoutException
    """
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutException(error_message)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wrapper

    return decorator
