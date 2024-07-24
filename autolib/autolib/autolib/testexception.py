"""\
Exception classes for indicating failures in test code.
"""


class TestException(Exception):
    """
    A subclass of Exception to represent faults occurring in test code.
    """
    __test__ = False

