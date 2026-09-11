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

# test initial account balance in zero for different currencies and their precision

def test_two_accounts_use_their_currency_precision():
    assert set(accounts) == {"ACC-001", "ACC-002"}
    assert accounts["ACC-001"].currency == "AED"
    assert accounts["ACC-002"].currency == "BHD"
    assert accounts["ACC-001"].opening_balance == Decimal("0.00")
    assert accounts["ACC-002"].opening_balance == Decimal("0.000")


from decimal import Decimal

from ledger.engine import LedgerEngine
from ledger.models import Account, Event, EventType
from ledger.money import money


def create_engine() -> LedgerEngine:
    accounts = {
        "ACC-001": Account(
            account_id="ACC-001",
            currency="AED",
            opening_balance=money("0", "AED"),
        ),
        "ACC-002": Account(
            account_id="ACC-002",
            currency="BHD",
            opening_balance=money("0", "BHD"),
        ),
    }

    return LedgerEngine(accounts)


def test_day_1_balance_after_e1_and_e2():
    engine = create_engine()

    e1 = Event(
        event_id="E1",
        posted_day=1,
        value_day=1,
        account_id="ACC-001",
        event_type=EventType.CREDIT,
        amount=Decimal("1200.00"),
    )

    e2 = Event(
        event_id="E2",
        posted_day=1,
        value_day=1,
        account_id="ACC-001",
        event_type=EventType.DEBIT,
        amount=Decimal("950.00"),
    )

    engine.replay(e1)
    engine.replay(e2)

    assert engine.balance_on("ACC-001", 1) == Decimal("250.00")