"""
PyTest unit tests for the timeout decorator.
"""

import time
import pytest
from functools import wraps

from autolib.timeout import timeout, TimeoutException


def time_taken(f):
    @wraps(f)
    def fn_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = f(*args, **kwargs)
        end_time = time.perf_counter()
        taken = end_time - start_time
        return result, taken
    return fn_wrapper


@timeout(5)
def takes_6_seconds():
    time.sleep(6)
    return True


@timeout(5)
def takes_4_seconds():
    time.sleep(4)
    return True


@time_taken
def time_timeout():
    try:
        takes_6_seconds()
    except TimeoutException:
        pass

    return True


def test_more_than_five_seconds():
    """\
    Check that a function that takes more than the timeout triggers a TimeoutException.
    """
    with pytest.raises(TimeoutException):
        assert takes_6_seconds()


def test_less_than_five_seconds():
    """\
    Check that a function that takes less than the timeout completes without triggering a TimeoutException
    """
    assert takes_4_seconds()


def test_timeout_duration_accuracy():
    result, duration = time_timeout()
    assert int(duration) == 5
