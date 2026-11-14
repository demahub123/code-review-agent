import pytest
from helpers import round_half_up, paginate, parse_bool, dedupe


def test_round_half_up():
    assert round_half_up(2.5) == 3
    assert round_half_up(-2.5) == -3
    assert round_half_up(2.4) == 2
    assert round_half_up(0.5) == 1


def test_paginate():
    items = [1, 2, 3, 4, 5]
    assert paginate(items, 1, 2) == [1, 2]
    assert paginate(items, 3, 2) == [5]
    assert paginate(items, 4, 2) == []
    with pytest.raises(ValueError):
        paginate(items, 0, 2)


def test_parse_bool():
    assert parse_bool("true") is True
    assert parse_bool(" YES ") is True
    assert parse_bool("0") is False
    assert parse_bool("false") is False
    with pytest.raises(ValueError):
        parse_bool("maybe")


def test_dedupe():
    assert dedupe([3, 1, 3, 2, 1]) == [3, 1, 2]