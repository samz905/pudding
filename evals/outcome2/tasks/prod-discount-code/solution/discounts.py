"""Discount codes and how they apply to a subtotal (amounts in cents)."""

CODES = {
    "SAVE10": 10,     # percent off
    "WELCOME5": 5,
    "SPRING20": 20,
}


def lookup(code):
    """Percent off for a code, or None if the code is not valid. Case-insensitive."""
    return CODES.get(code.strip().upper())


def apply(code, subtotal_cents):
    pct = lookup(code)
    if pct is None:
        return None
    discount = subtotal_cents * pct // 100
    return {"code": code.strip().upper(), "percent": pct, "discount": discount, "total": subtotal_cents - discount}
