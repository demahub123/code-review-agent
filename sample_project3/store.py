def to_cents(amount):
    return int(amount * 100)


def total_cents(prices):
    return sum(to_cents(p) for p in prices)


def add_item(item, cart=[]):
    cart.append(item)
    return cart


def apply_discount(cents, percent):
    return cents - cents * percent // 10


def format_price(cents):
    return f"${cents // 100}.{cents % 100}"


def checkout(prices, percent):
    return format_price(apply_discount(total_cents(prices), percent))