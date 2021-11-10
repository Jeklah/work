import pytest

def random_number():
    num = [1, 2, 3, 4, 5]
    for n in num:
        yield n

def test_test(n):
    if n % 2 == 0:
        assert True

@pytest.mark.parametrize('n', random_number)
def test_outer():
    for _ in range(5):
        if test_test(n):
            assert True
