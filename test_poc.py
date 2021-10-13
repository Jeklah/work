import pandas as pd
import pytest
from poc import get_dataframe_index


def create_test_golden_master(args):
    dict_to_df = {}
    for i in args:
        dict_to_df[i[0]] = i[1]
    golden_master = pd.DataFrame(dict_to_df.values(), index=dict_to_df.keys())

    return golden_master


def setup_test_env():
    """
    Setup the test environment
    """
    golden_master = create_test_golden_master([("a", [0, "first entry"]), ("b", [1, "second entry"])])
    return golden_master


def test_gold_master_first_value():
    """
    Verify the value of the first value is "first entry"
    """
    golden_master = setup_test_env()
    index = get_dataframe_index(golden_master)

    assert golden_master.loc[index[0], 1] == "first entry"


def test_gold_master_second_value():
    """
    Verify the value of the second value is "second entry"
    """
    golden_master = setup_test_env()
    index = get_dataframe_index(golden_master)

    assert golden_master.loc[index[1], 1] == "second entry"


def test_gold_master_first_key():
    """
    Verify the value of the first key is "a"
    """
    golden_master = setup_test_env()
    index = get_dataframe_index(golden_master)

    assert index[0] == "a"


def test_gold_master_second_key():
    """
    Verify the value of the second key is "b"
    """
    golden_master = setup_test_env()
    index = get_dataframe_index(golden_master)

    assert index[1] == "b"


def test_gold_master_bad_first_value():
    """
    Verify that the first value is not what we expect it to be.
    """
    golden_master = setup_test_env()
    index = get_dataframe_index(golden_master)

    # Intentional fail, expecting "first entry"
    assert golden_master.loc[index[0], 1] == "second entry"


def test_gold_master_bad_second_value():
    """
    Verify that the second value is not what we expect it to be.
    """
    golden_master = setup_test_env()
    index = get_dataframe_index(golden_master)

    # Intentional fail, expecting "second entry"
    assert golden_master.loc[index[1], 1] == "first entry"


def test_gold_master_bad_first_key():
    """
    Verify that the first key is not "a"
    """
    golden_master = setup_test_env()
    index = get_dataframe_index(golden_master)

    # Intentional fail, expecting the first key to be "a".
    assert index[0] == "z"


def test_gold_master_bad_second_key():
    """
    Verify that the second key is not "b"
    """
    golden_master = setup_test_env()
    index = get_dataframe_index(golden_master)

    # Intentional fail, expecting the second key to be "b".
    assert index[1] == "y"
