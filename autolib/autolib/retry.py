import time

from autolib.coreexception import CoreException


def retry(retries, delay, fn, *args, **kwargs):
    """
    Calls a specified function a requested number of times delaying between each until it responds with an expression
    that evaulates to True or throws an exception. The return value is a tuple containing a boolean to indicate that
    the called function was successful, the value returned by the called function and any CoreException subclass
    that was raised.

    e.g.::

        def function_to_retry(arg1, arg2):
            # Do something
            print(f'Arguments: {arg1}, {arg2}')
            raise Exception("Failure")

        success, return_val, exc = RetryFunc(20, 1, function_to_retry, "first arg", "second arg")
        if success:
            # Do something with return_val - In this example this will never be called
        else:
            # Handle failure
            if exc:
                print(f'The following exception was raised: {exc}')
    """
    return _retry(retries, delay, fn, False, *args, **kwargs)


def retry_ignoring_exceptions(retries, delay, fn, *args, **kwargs):
    """
    Similar to retry() but ignores all CoreExceptions raised by the called function.
    """
    return _retry(retries, delay, fn, True, *args, **kwargs)


def _retry(retries, delay, fn, ignore_exceptions, *args, **kwargs):
    success = False
    result_val = None
    exc = None

    try:
        for retry_index in range(retries):
            if ignore_exceptions:
                try:
                    result_val = fn(*args, **kwargs)
                except CoreException:
                    pass
            else:
                result_val = fn(*args, **kwargs)
            if result_val:
                success = True
                break
            time.sleep(delay)
        return success, result_val, exc
    except CoreException as e:
        success = False
        result_val = None
        exc = e
        return success, result_val, exc

