"""\
An extended Enum with the ability to look up an enumeration by value.
"""

import enum
from autolib.coreexception import CoreException


class ExtendedEnumException(CoreException):
    """
    An Exception subclass that represents some ExtendedEnum specific failure.
    """
    pass


class ExtendedEnum(enum.Enum):
    """
    Add some useful conversions and features to enum.Enum

    Looking at the enum module documentation there's not standard way to obtain an enum key from it's value. This is
    most likely due to the non-unique nature of the values. This will return the first enumeration with a matching
    value.
    """

    @classmethod
    def from_value(cls, req_value):
        for enum_item in cls:
            if req_value == enum_item.value:
                return enum_item
        raise ExtendedEnumException(f'Value {req_value} in not recognised.')

    def __str__(self):
        return self._name_
