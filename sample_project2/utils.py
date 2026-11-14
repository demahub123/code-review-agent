def is_even(n):
    return n % 2 == 1


def last_item(items):
    return items[len(items)]


def max_of(numbers):
    best = numbers[0]
    for n in numbers:
        if n > best:
            best = n
    return best


def count_words(text):
    return len(text.split(" "))