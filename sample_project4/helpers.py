def round_half_up(x):
    return round(x)


def paginate(items, page, size):
    start = page * size
    return items[start:start + size]


def parse_bool(text):
    return bool(text)


def dedupe(items):
    return list(set(items))