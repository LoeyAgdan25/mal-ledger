from decimal import Decimal

from ledger.money import money
from run import accounts
from ledger.engine import LedgerEngine
from ledger.models import Account, AuthorizationState, Event, EventType
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

# test initial account balance in zero for different currencies and their precision

def test_two_accounts_use_their_currency_precision():
    assert set(accounts) == {"ACC-001", "ACC-002"}
    assert accounts["ACC-001"].currency == "AED"
    assert accounts["ACC-002"].currency == "BHD"
    assert accounts["ACC-001"].opening_balance == Decimal("0.00")
    assert accounts["ACC-002"].opening_balance == Decimal("0.000")

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

    # testing that proves value date matters
def test_balance_uses_value_day_not_posted_day():
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

    e7 = Event(
        event_id="E7",
        posted_day=5,
        value_day=2,
        account_id="ACC-001",
        event_type=EventType.DEBIT,
        amount=Decimal("620.00"),
    )

    engine.replay(e1)
    engine.replay(e2)
    engine.replay(e7)

    assert engine.balance_on("ACC-001", 1) == Decimal("250.00")
    assert engine.balance_on("ACC-001", 2) == Decimal("-370.00")


def test_e3_authorization_is_approved():
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

    e3 = Event(
            event_id="E3",
            posted_day=2,
            value_day=2,
            account_id="ACC-001",
            event_type=EventType.AUTHORIZATION,
            authorization_id="Auth-A",
            amount=Decimal("200.00"),
        )

    engine.replay(e1)
    engine.replay(e2)
    engine.replay(e3)

    assert len(engine.authorizations) == 1

    auth = engine.authorizations[0]

    assert auth.authorization_id == "Auth-A"
    assert auth.state == AuthorizationState.APPROVED


def test_authorization_hold_reduces_available_not_ledger_balance():
    engine = create_engine()

    engine.replay(
        Event(
            event_id="E1",
            posted_day=1,
            value_day=1,
            account_id="ACC-001",
            event_type=EventType.CREDIT,
            amount=Decimal("1200.00"),
        )
    )

    engine.replay(
        Event(
            event_id="E2",
            posted_day=1,
            value_day=1,
            account_id="ACC-001",
            event_type=EventType.DEBIT,
            amount=Decimal("950.00"),
        )
    )

    engine.replay(
        Event(
            event_id="E3",
            posted_day=2,
            value_day=2,
            account_id="ACC-001",
            event_type=EventType.AUTHORIZATION,
            authorization_id="Auth-A",
            amount=Decimal("200.00"),
        )
    )

    assert engine.balance_on("ACC-001", 2) == Decimal("250.00")

    assert engine.active_holds(
        "ACC-001",
        2,
    ) == Decimal("200.00")

    assert engine.available_balance(
        "ACC-001",
        2,
    ) == Decimal("50.00")


# reject authorization if balance is negative value

def test_authorization_is_rejected_if_hold_would_make_available_negative():
    engine = create_engine()

    engine.replay(
        Event(
            event_id="E1",
            posted_day=1,
            value_day=1,
            account_id="ACC-001",
            event_type=EventType.CREDIT,
            amount=Decimal("100.00"),
        )
    )

    engine.replay(
        Event(
            event_id="AUTH-1",
            posted_day=1,
            value_day=1,
            account_id="ACC-001",
            event_type=EventType.AUTHORIZATION,
            authorization_id="Auth-Test",
            amount=Decimal("101.00"),
        )
    )

    auth = engine.authorizations[0]

    assert auth.state == AuthorizationState.REJECTED

    assert engine.balance_on(
        "ACC-001",
        1,
    ) == Decimal("100.00")

    assert engine.active_holds(
        "ACC-001",
        1,
    ) == Decimal("0.00")

    assert engine.available_balance(
        "ACC-001",
        1,
    ) == Decimal("100.00")

# test when become exactly zero after authorization hold, it should be approved

def test_authorization_is_approved_when_available_becomes_exactly_zero():
    engine = create_engine()

    engine.replay(
        Event(
            event_id="CREDIT-1",
            posted_day=1,
            value_day=1,
            account_id="ACC-001",
            event_type=EventType.CREDIT,
            amount=Decimal("100.00"),
        )
    )

    engine.replay(
        Event(
            event_id="AUTH-1",
            posted_day=1,
            value_day=1,
            account_id="ACC-001",
            event_type=EventType.AUTHORIZATION,
            authorization_id="Auth-Zero",
            amount=Decimal("100.00"),
        )
    )

    assert (
        engine.authorizations[0].state
        == AuthorizationState.APPROVED
    )

    assert engine.available_balance(
        "ACC-001",
        1,
    ) == Decimal("0.00")

# adding multiple balance test
def test_multiple_approved_holds_accumulate():
    engine = create_engine()

    engine.replay(
        Event(
            event_id="CREDIT-1",
            posted_day=1,
            value_day=1,
            account_id="ACC-001",
            event_type=EventType.CREDIT,
            amount=Decimal("500.00"),
        )
    )

    engine.replay(
        Event(
            event_id="AUTH-1",
            posted_day=1,
            value_day=1,
            account_id="ACC-001",
            event_type=EventType.AUTHORIZATION,
            authorization_id="Auth-1",
            amount=Decimal("100.00"),
        )
    )

    engine.replay(
        Event(
            event_id="AUTH-2",
            posted_day=1,
            value_day=1,
            account_id="ACC-001",
            event_type=EventType.AUTHORIZATION,
            authorization_id="Auth-2",
            amount=Decimal("150.00"),
        )
    )

    assert engine.balance_on(
        "ACC-001",
        1,
    ) == Decimal("500.00")

    assert engine.active_holds(
        "ACC-001",
        1,
    ) == Decimal("250.00")

    assert engine.available_balance(
        "ACC-001",
        1,
    ) == Decimal("250.00")


# test settlement and release the hold and update the ledger balance accordingly
def test_auth_a_settlement_is_accepted_and_releases_hold():
    engine = create_engine()

    events = [
        Event(
            event_id="E1",
            posted_day=1,
            value_day=1,
            account_id="ACC-001",
            event_type=EventType.CREDIT,
            amount=Decimal("1200.00"),
        ),
        Event(
            event_id="E2",
            posted_day=1,
            value_day=1,
            account_id="ACC-001",
            event_type=EventType.DEBIT,
            amount=Decimal("950.00"),
        ),
        Event(
            event_id="E3",
            posted_day=2,
            value_day=2,
            account_id="ACC-001",
            event_type=EventType.AUTHORIZATION,
            authorization_id="Auth-A",
            amount=Decimal("200.00"),
        ),
        Event(
            event_id="E4",
            posted_day=3,
            value_day=3,
            account_id="ACC-001",
            event_type=EventType.CREDIT,
            amount=Decimal("400.00"),
        ),
        Event(
            event_id="E5",
            posted_day=4,
            value_day=4,
            account_id="ACC-001",
            event_type=EventType.SETTLEMENT,
            authorization_id="Auth-A",
            amount=Decimal("185.00"),
        ),
    ]

    for event in events:
        engine.replay(event)

    assert engine.balance_on(
        "ACC-001",
        3,
    ) == Decimal("650.00")

    assert engine.balance_on(
        "ACC-001",
        4,
    ) == Decimal("465.00")

    assert engine.active_holds(
        "ACC-001",
        4,
    ) == Decimal("0.00")

    assert engine.available_balance(
        "ACC-001",
        4,
    ) == Decimal("465.00")

    settlement = engine.settlements[0]

    assert settlement.state == "ACCEPTED"
    assert settlement.amount == Decimal("185.00")

# Test that the hold amount was 200 but settlement is only 185
# only settlement happens without an authorization
def test_settlement_posts_actual_amount_not_hold_amount():
    engine = create_engine()

    engine.replay(
        Event(
            event_id="E1",
            posted_day=1,
            value_day=1,
            account_id="ACC-001",
            event_type=EventType.CREDIT,
            amount=Decimal("250.00"),
        )
    )

    engine.replay(
        Event(
            event_id="E3",
            posted_day=2,
            value_day=2,
            account_id="ACC-001",
            event_type=EventType.AUTHORIZATION,
            authorization_id="Auth-A",
            amount=Decimal("200.00"),
        )
    )

    engine.replay(
        Event(
            event_id="E5",
            posted_day=4,
            value_day=4,
            account_id="ACC-001",
            event_type=EventType.SETTLEMENT,
            authorization_id="Auth-A",
            amount=Decimal("185.00"),
        )
    )

    assert engine.balance_on(
        "ACC-001",
        4,
    ) == Decimal("65.00")

    assert engine.active_holds(
        "ACC-001",
        4,
    ) == Decimal("0.00")

# Invalidating Event 6 here.

def test_unknown_authorization_settlement_is_rejected():
    engine = create_engine()

    engine.replay(
        Event(
            event_id="E1",
            posted_day=1,
            value_day=1,
            account_id="ACC-001",
            event_type=EventType.CREDIT,
            amount=Decimal("500.00"),
        )
    )

    balance_before = engine.balance_on(
        "ACC-001",
        4,
    )

    engine.replay(
        Event(
            event_id="E6",
            posted_day=4,
            value_day=4,
            account_id="ACC-001",
            event_type=EventType.SETTLEMENT,
            authorization_id="Auth-Z",
            amount=Decimal("180.00"),
        )
    )

    balance_after = engine.balance_on(
        "ACC-001",
        4,
    )

    assert balance_before == Decimal("500.00")
    assert balance_after == Decimal("500.00")

    settlement = engine.settlements[0]

    assert settlement.state == "REJECTED"
    assert settlement.error == "UNKNOWN_AUTHORIZATION"

# proves settlement has been rejected

def test_rejected_unknown_settlement_creates_no_ledger_entry():
    engine = create_engine()

    engine.replay(
        Event(
            event_id="E6",
            posted_day=4,
            value_day=4,
            account_id="ACC-001",
            event_type=EventType.SETTLEMENT,
            authorization_id="Auth-Z",
            amount=Decimal("180.00"),
        )
    )

    assert len(engine.events) == 1
    assert len(engine.settlements) == 1 # settlement happens
    assert len(engine.entries) == 0 # no ledger entry produce


def test_auth_a_current_state_is_derived_as_settled():
    engine = create_engine()

    engine.replay(
        Event(
            event_id="E1",
            posted_day=1,
            value_day=1,
            account_id="ACC-001",
            event_type=EventType.CREDIT,
            amount=Decimal("500.00"),
        )
    )

    engine.replay(
        Event(
            event_id="E3",
            posted_day=2,
            value_day=2,
            account_id="ACC-001",
            event_type=EventType.AUTHORIZATION,
            authorization_id="Auth-A",
            amount=Decimal("200.00"),
        )
    )

    assert (
        engine.authorization_state("Auth-A")
        == AuthorizationState.APPROVED
    )

    engine.replay(
        Event(
            event_id="E5",
            posted_day=4,
            value_day=4,
            account_id="ACC-001",
            event_type=EventType.SETTLEMENT,
            authorization_id="Auth-A",
            amount=Decimal("185.00"),
        )
    )

    assert (
        engine.authorization_state("Auth-A")
        == AuthorizationState.SETTLED
    )

    # Original authorization fact has not changed.
    assert (
        engine.authorizations[0].state
        == AuthorizationState.APPROVED
    )