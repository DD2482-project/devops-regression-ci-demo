"""Pure pricing logic for the order-total service.

No framework imports live here on purpose. These are small, pure functions so
they are trivial to unit-test and friendly to mutation testing: every branch is
reachable from a plain function call with plain arguments.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

# Money is rounded to whole cents, half-up (the everyday "round 0.5 up" rule).
_CENTS = Decimal("0.01")

# Known discount codes mapped to the fraction of the order they take off.
DISCOUNT_RATES: dict[str, Decimal] = {
    "SAVE10": Decimal("0.10"),
    "SAVE20": Decimal("0.20"),
}


def _to_decimal(value: Decimal | float | int | str) -> Decimal:
    """Coerce an incoming JSON number (or string) to an exact Decimal."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _round_money(value: Decimal) -> Decimal:
    """Round to 2 decimal places, half-up."""
    return value.quantize(_CENTS, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Item:
    """A single cart line: a unit price and a quantity."""

    price: Decimal
    quantity: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "price", _to_decimal(self.price))


def subtotal(items: list[Item]) -> Decimal:
    """Sum of ``price * quantity`` across every line, rounded to cents."""
    running = sum((item.price * item.quantity for item in items), Decimal("0"))
    return _round_money(running)


def discount_amount(subtotal: Decimal, code: str | None) -> Decimal:
    """Money taken off for ``code``.

    Applies the code's percentage to ``subtotal`` (the whole order). An unknown
    code or ``None`` means no discount.
    """
    rate = DISCOUNT_RATES.get(code or "", Decimal("0"))
    return _round_money(subtotal * rate)


def order_total(items: list[Item], code: str | None) -> dict[str, Decimal]:
    """Return ``{"subtotal", "discount", "total"}``.

    ``total`` is ``subtotal - discount`` and is never negative.
    """
    sub = subtotal(items)
    base = items[0].price if items else Decimal("0")
    discount = min(discount_amount(base, code), sub)
    total = max(sub - discount, Decimal("0"))
    return {"subtotal": sub, "discount": discount, "total": total}
