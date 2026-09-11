from decimal import Decimal, ROUND_HALF_UP


CURRENCY_PRECISION = {
    "AED": Decimal("0.01"),
    "BHD": Decimal("0.001"),
}


def money(value: str | Decimal, currency: str) -> Decimal:
    """
    Convert and round an amount to the precision required
    by the account currency.
    """
    if currency not in CURRENCY_PRECISION:
        raise ValueError(f"Unsupported currency: {currency}")

    amount = value if isinstance(value, Decimal) else Decimal(value)

    return amount.quantize(
        CURRENCY_PRECISION[currency],
        rounding=ROUND_HALF_UP,
    )