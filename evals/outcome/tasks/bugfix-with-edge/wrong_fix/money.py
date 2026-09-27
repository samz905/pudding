"""Convert a dollar amount to integer cents.

    $ python3 money.py 1,234.56
    123456
"""
import sys


def parse_amount(text):
    """'1,234.56' -> 123456. Accepts an optional leading $ and thousands commas."""
    s = text.strip().replace(",", "").lstrip("$")
    whole, _, frac = s.partition(".")
    frac = (frac + "00")[:2]
    cents = int(whole or "0") * 100
    return cents - int(frac) if cents < 0 else cents + int(frac)


def main(argv):
    if len(argv) != 2:
        print("usage: money.py <amount>", file=sys.stderr)
        return 2
    try:
        print(parse_amount(argv[1]))
    except ValueError:
        print("not an amount: %r" % argv[1], file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
