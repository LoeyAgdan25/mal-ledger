from decimal import Decimal

from ledger.money import money

# test cases for the money function in ledger/money.py
# test floating point accuracy issues and rounding behavior for different currencies

def test_aed_uses_two_decimal_places():
    assert money("1200", "AED") == Decimal("1200.00")


def test_bhd_uses_three_decimal_places():
    assert money("10", "BHD") == Decimal("10.000")


def test_aed_rounding():
    assert money("1.235", "AED") == Decimal("1.24")


def test_bhd_rounding():
    assert money("1.2345", "BHD") == Decimal("1.235")