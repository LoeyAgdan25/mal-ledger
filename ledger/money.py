from decimal import Decimal, ROUND_HALF_UP


CURRENCY_PRECISION = {
    "AED": Decimal("0.01"),
    "BHD": Decimal("0.001"),
}

OVERDRAFT_FEE_AED = Decimal("25.00")

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

# add generic amount splitter / this calculate exactly the amount

def split_amount(
    value: str | Decimal,
    currency: str,
    count: int,
) -> list[Decimal]:
    if count <= 0:
        raise ValueError(
            "Installment count must be greater than zero"
        )

    total = money(value, currency)
    precision = CURRENCY_PRECISION[currency]

    minor_units = int(total / precision)

    base_units, remainder = divmod(
        minor_units,
        count,
    )

    parts: list[Decimal] = []

    for index in range(count):
        units = base_units

        if index < remainder:
            units += 1

        part = money(
            Decimal(units) * precision,
            currency,
        )

        parts.append(part)

    return parts