"""
PyTest unit tests for the retry module.
"""

from autolib.retry import retry, retry_ignoring_exceptions
from autolib.coreexception import CoreException


def _throwing_function(arg):
    raise CoreException(f"CoreException - throwing_function() called with {arg}")


def _failing_function(arg):
    print(f'failing_function() called the {arg}')
    return None


def _succeeding_function(arg):
    print(f'succeeding_function() called the {arg}')
    return {'data': [1, 2, 3, 4, 5]}


def _succeeding_function_args_kwargs(*arg, **kwargs):
    print(f'succeeding_function() called the {arg} and {kwargs.get("keyword_arg", "Failure")}')
    return {'data': [1, 2, 3, 4, 5]}


def test_retry_throwing():
    success, return_val, exc = retry(10, 1, _throwing_function, "Test argument")
    assert not success
    assert type(exc) == CoreException


def test_retry_ignore_throwing():
    success, return_val, exc = retry_ignoring_exceptions(10, 1, _throwing_function, "Test argument")
    assert not success
    assert exc is None


def test_retry_failing():
    success, return_val, exc = retry(3, 1, _failing_function, "Test argument")
    assert not success


def test_retry_succeeding():
    success, return_val, exc = retry(3, 1, _succeeding_function, "Test argument")
    assert success
    assert return_val == {'data': [1, 2, 3, 4, 5]}


def test_retry_succeeding_args_kwargs():
    success, return_val, exc = retry(3, 1, _succeeding_function_args_kwargs, ("Test argument", ), {'keyword_arg': 'monkey'})
    assert success
    assert return_val == {'data': [1, 2, 3, 4, 5]}
