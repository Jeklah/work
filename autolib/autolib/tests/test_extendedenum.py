import enum

import pytest

from autolib.extendedenum import ExtendedEnum, ExtendedEnumException


@enum.unique
class SomeExtendedEnum(ExtendedEnum):
    """
    A test extended enumeration
    """
    ITEM_1 = 'Item 1'
    ITEM_2 = 'Item 2'
    ITEM_3 = 'Item 3'
    ITEM_4 = 'Item 4'
    ITEM_5 = 'Item 5'
    ITEM_6 = 'Item 6'


def test_basic_enum():
    """\
    """
    test_enum_item_1 = SomeExtendedEnum.ITEM_1
    assert test_enum_item_1.name == 'ITEM_1'
    assert test_enum_item_1.value == 'Item 1'

    test_enum_item_6 = SomeExtendedEnum.ITEM_6
    assert test_enum_item_6.name == 'ITEM_6'
    assert test_enum_item_6.value == 'Item 6'


def test_from_value_happy():
    """\
    """
    assert SomeExtendedEnum.from_value('Item 1') == SomeExtendedEnum.ITEM_1
    assert SomeExtendedEnum.from_value('Item 6') == SomeExtendedEnum.ITEM_6


def test_from_value_sad():
    with pytest.raises(ExtendedEnumException):
        assert SomeExtendedEnum.from_value('Item 7') is None

    with pytest.raises(ExtendedEnumException):
        assert SomeExtendedEnum.from_value('') is None


def test_from_value_bad():
    with pytest.raises(ExtendedEnumException):
        assert SomeExtendedEnum.from_value(600) is None
