"""\
Exception classes specific to devices supported by the automation library.
"""
from autolib.coreexception import CoreException


class DeviceException(CoreException):
    """
    A subclass of Exception to represent faults occurring in automation library models.
    """
    pass
