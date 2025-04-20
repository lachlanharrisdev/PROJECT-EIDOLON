import pytest


def func(x: int) -> int:
    return x + 1


def test_template():
    assert func(4) == 5
