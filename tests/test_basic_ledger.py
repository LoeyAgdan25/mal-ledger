from decimal import Decimal

from ledger.money import money
from run import accounts

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


def test_two_accounts_use_their_currency_precision():
    assert set(accounts) == {"ACC-001", "ACC-002"}
    assert accounts["ACC-001"].currency == "AED"
    assert accounts["ACC-002"].currency == "BHD"
    assert accounts["ACC-001"].opening_balance == Decimal("0.00")
    assert accounts["ACC-002"].opening_balance == Decimal("0.000")