import pandas as pd
import pytest
from poc import (get_dataframe_index,
                 create_gold_master)


def load_golden_master():
    """
    Function to load the golden master from external file.
    """
    golden_master = pd.read_pickle('./test_df.pkl')

    yield golden_master


@pytest.mark.parametrize('golden_master', load_golden_master())
def test_gold_master_first_value(golden_master):
    """
    Verify the value of the first value is "first entry"
    """
    index = get_dataframe_index(golden_master)
    FIRST_ENTRY = golden_master.loc[index[0], 0]

    assert FIRST_ENTRY == "first entry col1"

@pytest.mark.parametrize('golden_master', load_golden_master())
def test_gold_master_second_value(golden_master):
    """
    Verify the value of the second value is "second entry"
    """
    index = get_dataframe_index(golden_master)
    SECOND_ENTRY = golden_master.loc[index[0], 1]

    assert SECOND_ENTRY  == "second entry col1"


@pytest.mark.parametrize('golden_master', load_golden_master())
def test_gold_master_first_key(golden_master):
    """
    Verify the value of the first key is "a"
    """
    index = get_dataframe_index(golden_master)
    FIRST_ROW = index[0]

    assert FIRST_ROW == "named row 1"


@pytest.mark.parametrize('golden_master', load_golden_master())
def test_gold_master_second_key(golden_master):
    """
    Verify the value of the second key is "b"
    """
    index = get_dataframe_index(golden_master)
    SECOND_ROW = index[1]

    assert SECOND_ROW == "named row 2"


@pytest.mark.parametrize('golden_master', load_golden_master())
def test_gold_master_bad_first_value(golden_master):
    """
    Verify that the first value is not what we expect it to be.
    """
    index = get_dataframe_index(golden_master)
    FIRST_ENTRY_BAD = golden_master.loc[index[0], 1]


    assert FIRST_ENTRY_BAD != "second entry"


@pytest.mark.parametrize('golden_master', load_golden_master())
def test_gold_master_bad_second_value(golden_master):
    """
    Verify that the second value is not what we expect it to be.
    """
    index = get_dataframe_index(golden_master)
    SECOND_ENTRY_BAD = golden_master.loc[index[1], 1]

    assert SECOND_ENTRY_BAD != "first entry"


@pytest.mark.parametrize('golden_master', load_golden_master())
def test_gold_master_bad_first_key(golden_master):
    """
    Verify that the first key is not "a"
    """
    index = get_dataframe_index(golden_master)
    FIRST_ROW_BAD = index[0]

    assert FIRST_ROW_BAD != "z"


@pytest.mark.parametrize('golden_master', load_golden_master())
def test_gold_master_bad_second_key(golden_master):
    """
    Verify that the second key is not "b"
    """
    index = get_dataframe_index(golden_master)
    SECOND_ROW_BAD = index[1]

    assert SECOND_ROW_BAD != "y"
