from utils import is_even, last_item, max_of, count_words


def test_is_even():
    assert is_even(4) is True
    assert is_even(7) is False


def test_last_item():
    assert last_item([1, 2, 3]) == 3


def test_max_of():
    assert max_of([3, 9, 2]) == 9
    assert max_of([]) is None


def test_count_words():
    assert count_words("hello world") == 2
    assert count_words("") == 0
    assert count_words("a  b") == 2