from decimal import Decimal

from ledger.money import money
from run import accounts
from ledger.engine import LedgerEngine
from ledger.models import Account, AuthorizationState, Event, EventType, EntryType
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

# balance are value dated here...
def test_e7_retroactively_changes_day_2_balance_to_negative_370():
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
        Event(
            event_id="E7",
            posted_day=5,
            value_day=2,
            account_id="ACC-001",
            event_type=EventType.DEBIT,
            amount=Decimal("620.00"),
        ),
    ]

    for event in events:
        engine.replay(event)

    assert engine.balance_on(
        "ACC-001",
        1,
    ) == Decimal("250.00")

    assert engine.balance_on(
        "ACC-001",
        2,
    ) == Decimal("-370.00")


# test all value dated balance

def test_e7_changes_later_value_dated_balances():
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
        Event(
            event_id="E7",
            posted_day=5,
            value_day=2,
            account_id="ACC-001",
            event_type=EventType.DEBIT,
            amount=Decimal("620.00"),
        ),
    ]

    for event in events:
        engine.replay(event)

    assert engine.balance_on("ACC-001", 1) == Decimal("250.00")
    assert engine.balance_on("ACC-001", 2) == Decimal("-370.00")
    assert engine.balance_on("ACC-001", 3) == Decimal("30.00")
    assert engine.balance_on("ACC-001", 4) == Decimal("-155.00")
    assert engine.balance_on("ACC-001", 5) == Decimal("-155.00")

# test the assested fees
def test_negative_day_2_balance_assesses_aed_25_fee():
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
                event_id="E7",
                posted_day=5,
                value_day=2,
                account_id="ACC-001",
                event_type=EventType.DEBIT,
                amount=Decimal("620.00"),
            )
        )

        assert engine.balance_on(
            "ACC-001",
            2,
        ) == Decimal("-370.00")

        engine.assess_overdraft_fee(
            "ACC-001",
            2,
        )

        assert engine.balance_on(
            "ACC-001",
            2,
        ) == Decimal("-395.00")

# test overdraft fee one per day behavior

def test_overdraft_fee_is_assessed_only_once_per_day():
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
            event_id="D1",
            posted_day=2,
            value_day=2,
            account_id="ACC-001",
            event_type=EventType.DEBIT,
            amount=Decimal("200.00"),
        )
    )

    engine.assess_overdraft_fee("ACC-001", 2)
    engine.assess_overdraft_fee("ACC-001", 2)
    engine.assess_overdraft_fee("ACC-001", 2)

    fee_entries = [
        entry
        for entry in engine.entries
        if entry.entry_type == EntryType.OVERDRAFT_FEE
    ]

    assert len(fee_entries) == 1

    assert fee_entries[0].amount == Decimal("-25.00")

# test the balance for accuracy and not including days without overdraft fees
def test_e7_recalculation_assesses_fees_on_negative_closing_days():
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
        Event(
            event_id="E7",
            posted_day=5,
            value_day=2,
            account_id="ACC-001",
            event_type=EventType.DEBIT,
            amount=Decimal("620.00"),
        ),
    ]

    for event in events:
        engine.replay(event)

    # Acceptance criterion explicitly asks for the balance
    # before any fee is assessed.
    assert engine.balance_on(
        "ACC-001",
        2,
    ) == Decimal("-370.00")

    engine.assess_overdraft_fees_through(
        "ACC-001",
        5,
    )

    fee_days = [
        entry.value_day
        for entry in engine.entries
        if entry.entry_type == EntryType.OVERDRAFT_FEE
    ]

    assert fee_days == [2, 4, 5]

# reversal testing

def test_e9_reverses_e7_without_deleting_original_entry():
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
                event_id="E7",
                posted_day=5,
                value_day=2,
                account_id="ACC-001",
                event_type=EventType.DEBIT,
                amount=Decimal("620.00"),
            )
        )

    assert engine.balance_on(
            "ACC-001",
            2,
        ) == Decimal("-370.00")

    engine.replay(
            Event(
                event_id="E9",
                posted_day=6,
                value_day=2,
                account_id="ACC-001",
                event_type=EventType.REVERSAL,
                reference_event_id="E7",
            )
        )

    assert engine.balance_on(
            "ACC-001",
            2,
        ) == Decimal("250.00")

    e7_entries = [
            entry
            for entry in engine.entries
            if entry.source_event_id == "E7"
        ]

    e9_entries = [
            entry
            for entry in engine.entries
            if entry.source_event_id == "E9"
        ]

    assert len(e7_entries) == 1
    assert len(e9_entries) == 1

    assert e7_entries[0].amount == Decimal("-620.00")
    assert e9_entries[0].amount == Decimal("620.00")

    # engine.replay(
    #         Event(
    #             event_id="E8",
    #             posted_day=5,
    #             value_day=5,
    #             account_id="ACC-001",
    #             event_type=EventType.AUTHORIZATION,
    #             authorization_id="Auth-B",
    #             amount=Decimal("90.00"),
    #         )
    #     )

    # assert (
    #         engine.authorization_state("Auth-B")
    #         == AuthorizationState.REJECTED
    #     )

    # assert engine.active_holds(
    #         "ACC-001",
    #         5,
    #     ) == Decimal("0.00")


def test_e8_auth_b_is_rejected_when_available_balance_is_negative():
    engine = create_engine()

    # E1: +1200
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

    # E2: -950
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

    # E3: Auth-A hold 200
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

    # E4: +400
    engine.replay(
        Event(
            event_id="E4",
            posted_day=3,
            value_day=3,
            account_id="ACC-001",
            event_type=EventType.CREDIT,
            amount=Decimal("400.00"),
        )
    )

    # E5: settle Auth-A for 185
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

    # E7: backdated debit
    engine.replay(
        Event(
            event_id="E7",
            posted_day=5,
            value_day=2,
            account_id="ACC-001",
            event_type=EventType.DEBIT,
            amount=Decimal("620.00"),
        )
    )

    # Apply overdraft fees through Day 5
    engine.assess_overdraft_fees_through(
        "ACC-001",
        5,
    )

    # Before E8, account should already be negative.
    assert engine.balance_on(
        "ACC-001",
        5,
    ) == Decimal("-230.00")

    # E8: Auth-B tries to hold another 90
    engine.replay(
        Event(
            event_id="E8",
            posted_day=5,
            value_day=5,
            account_id="ACC-001",
            event_type=EventType.AUTHORIZATION,
            authorization_id="Auth-B",
            amount=Decimal("90.00"),
        )
    )

    # Auth-B must be rejected.
    assert (
        engine.authorization_state("Auth-B")
        == AuthorizationState.REJECTED
    )

    # Rejected authorization must not create a hold.
    assert engine.active_holds(
        "ACC-001",
        5,
    ) == Decimal("0.00")

    # Authorization must not change ledger balance.
    assert engine.balance_on(
        "ACC-001",
        5,
    ) == Decimal("-230.00")