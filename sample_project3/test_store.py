from store import (
    to_cents, total_cents, add_item, apply_discount, format_price, checkout,
)


def test_to_cents():
    assert to_cents(19.99) == 1999


def test_total_cents():
    assert total_cents([19.99, 0.01]) == 2000


def test_add_item_is_independent():
    assert add_item("a") == ["a"]
    assert add_item("b") == ["b"]


def test_apply_discount():
    assert apply_discount(2000, 10) == 1800


def test_format_price():
    assert format_price(1800) == "$18.00"
    assert format_price(5) == "$0.05"


def test_checkout():
    assert checkout([19.99, 0.01], 10) == "$18.00"