import pytest


def test_function():
    check = False
    print('checking check is true: ')
    assert check is True

def main():
    test_function()

if __name__ == '__main__':
    main()
