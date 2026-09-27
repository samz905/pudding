"""In-memory cart. count is the total quantity across lines."""

PRODUCTS = [
    {"sku": "MUG-01", "name": "Enamel mug", "price_cents": 1800},
    {"sku": "TEE-02", "name": "Logo tee", "price_cents": 2400},
    {"sku": "CAP-03", "name": "Canvas cap", "price_cents": 2000},
]


class Cart:
    def __init__(self):
        self.lines = {}

    def add(self, sku, qty=1):
        if sku not in {p["sku"] for p in PRODUCTS}:
            raise KeyError(sku)
        self.lines[sku] = self.lines.get(sku, 0) + qty

    @property
    def count(self):
        return sum(self.lines.values())

    def as_dict(self):
        return {"items": [{"sku": s, "qty": q} for s, q in self.lines.items()], "count": self.count}
