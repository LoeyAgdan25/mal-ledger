from decimal import Decimal

from ledger.engine import LedgerEngine
from ledger.models import (
    Account,
    AuthorizationState,
    Event,
    EventType,
    EntryType,
)
from ledger.money import money


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


def create_engine() -> LedgerEngine:
    return LedgerEngine(accounts.copy())


def build_event_stream() -> list[Event]:
    """
    Assessment event stream.

    IMPORTANT:
    Events are kept in the exact order supplied by the assessment.
    They are NOT sorted by posted_day or value_day.
    """
    return [
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
            event_id="E6",
            posted_day=4,
            value_day=4,
            account_id="ACC-001",
            event_type=EventType.SETTLEMENT,
            authorization_id="Auth-Z",
            amount=Decimal("180.00"),
        ),

        Event(
            event_id="E7",
            posted_day=5,
            value_day=2,
            account_id="ACC-001",
            event_type=EventType.DEBIT,
            amount=Decimal("620.00"),
        ),

        Event(
            event_id="E8",
            posted_day=5,
            value_day=5,
            account_id="ACC-001",
            event_type=EventType.AUTHORIZATION,
            authorization_id="Auth-B",
            amount=Decimal("90.00"),
        ),

        Event(
            event_id="E9",
            posted_day=6,
            value_day=2,
            account_id="ACC-001",
            event_type=EventType.REVERSAL,
            reference_event_id="E7",
        ),

        Event(
            event_id="E10",
            posted_day=5,
            value_day=5,
            account_id="ACC-002",
            event_type=EventType.CREDIT,
            amount=Decimal("10.000"),
            installment_count=3,
        ),
    ]


def format_money(
    amount: Decimal,
    currency: str,
) -> str:
    if currency == "BHD":
        return f"{amount:.3f} {currency}"

    return f"{amount:.2f} {currency}"


def historical_authorization_state(
    engine,
    authorization_id: str,
    day: int,
):
    """
    Return authorization state as of a historical accounting day
    without mutating the original authorization record.
    """
    authorization = engine.find_authorization(
        authorization_id
    )

    if authorization is None:
        return None

    if authorization.value_day > day:
        return None

    if (
        authorization.state
        == AuthorizationState.REJECTED
    ):
        return AuthorizationState.REJECTED

    if engine.has_settlement(
        authorization_id,
        day,
    ):
        return AuthorizationState.SETTLED

    return AuthorizationState.APPROVED


def replay_events(engine) -> None:
    print("=" * 70)
    print("MAL IN-MEMORY LEDGER")
    print("=" * 70)

    print("\n=== EVENT REPLAY ===")

    for event in build_event_stream():

        print(
            f"{event.event_id:<4} "
            f"posted=D{event.posted_day} "
            f"value=D{event.value_day} "
            f"type={event.event_type.value:<15} "
            f"account={event.account_id}"
        )

        engine.replay(event)

        # E7 arrives on Day 5 but is value-dated Day 2.
        #
        # The historical accounting days affected by that
        # backdated debit are reevaluated chronologically.
        #
        # This produces fees for D2, D4 and D5 under the
        # selected fee interpretation.
        if event.event_id == "E7":
            engine.assess_overdraft_fees_through(
                "ACC-001",
                5,
            )


def accrue_and_capitalize_interest(engine) -> None:
    """
    Calculate rounded daily interest first.

    Only after all Day 1-Day 6 accruals exist do we create the
    single Day 6 capitalization entry.
    """

    for account_id in (
        "ACC-001",
        "ACC-002",
    ):
        engine.accrue_interest_through(
            account_id,
            6,
        )

    for account_id in (
        "ACC-001",
        "ACC-002",
    ):
        engine.capitalize_interest(
            account_id,
            6,
        )


def print_daily_report(engine) -> None:
    print("\n")
    print("=" * 70)
    print("DAILY REPORT")
    print("=" * 70)

    for day in range(1, 7):

        print(f"\n--- DAY {day} ---")

        #
        # Closing ledger balances
        #
        print("Closing ledger balances:")

        for account_id in (
            "ACC-001",
            "ACC-002",
        ):
            account = engine.accounts[
                account_id
            ]

            balance = engine.balance_on(
                account_id,
                day,
            )

            print(
                f"  {account_id}: "
                f"{format_money(balance, account.currency)}"
            )

        #
        # Fees
        #
        fees = [
            entry
            for entry in engine.entries
            if (
                entry.entry_type
                == EntryType.OVERDRAFT_FEE
                and entry.value_day == day
            )
        ]

        print("Fee assessments:")

        if not fees:
            print("  None")
        else:
            for fee in fees:
                print(
                    f"  {fee.account_id}: "
                    f"{format_money(fee.amount, fee.currency)}"
                )

        #
        # Authorization state
        #
        print("Authorization states:")

        authorization_found = False

        for authorization in engine.authorizations:

            state = historical_authorization_state(
                engine,
                authorization.authorization_id,
                day,
            )

            if state is None:
                continue

            authorization_found = True

            print(
                f"  "
                f"{authorization.authorization_id}: "
                f"{state.value}"
            )

        if not authorization_found:
            print("  None")

        #
        # Processing errors
        #
        errors = [
            settlement
            for settlement in engine.settlements
            if (
                settlement.value_day == day
                and settlement.state
                == "REJECTED"
            )
        ]

        print("Errors:")

        if not errors:
            print("  None")
        else:
            for error in errors:
                print(
                    f"  {error.event_id}: "
                    f"{error.error}"
                )

        #
        # Daily interest
        #
        print("Interest accruals:")

        accruals = [
            accrual
            for accrual
            in engine.interest_accruals
            if accrual.day == day
        ]

        if not accruals:
            print("  None")
        else:
            for accrual in accruals:

                account = engine.accounts[
                    accrual.account_id
                ]

                print(
                    f"  {accrual.account_id}: "
                    f"{format_money(accrual.amount, account.currency)} "
                    f"on base "
                    f"{format_money(accrual.balance, account.currency)}"
                )


def print_interest_summary(engine) -> None:
    print("\n")
    print("=" * 70)
    print("INTEREST SUMMARY")
    print("=" * 70)

    for account_id in (
        "ACC-001",
        "ACC-002",
    ):

        account = engine.accounts[
            account_id
        ]

        accruals = [
            accrual
            for accrual
            in engine.interest_accruals
            if accrual.account_id
            == account_id
        ]

        print(
            f"\n{account_id} "
            f"({account.currency})"
        )

        total = Decimal("0")

        for accrual in accruals:

            total += accrual.amount

            print(
                f"  Day {accrual.day}: "
                f"balance="
                f"{format_money(accrual.balance, account.currency)}, "
                f"interest="
                f"{format_money(accrual.amount, account.currency)}"
            )

        print(
            "  Rounded accrual total: "
            f"{format_money(total, account.currency)}"
        )

        capitalization = [
            entry
            for entry in engine.entries
            if (
                entry.account_id
                == account_id
                and entry.entry_type
                == EntryType.INTEREST
            )
        ]

        if capitalization:
            entry = capitalization[0]

            print(
                "  Day 6 capitalization: "
                f"{format_money(entry.amount, account.currency)}"
            )
        else:
            print(
                "  Day 6 capitalization: None"
            )


def print_authorization_summary(engine) -> None:
    print("\n")
    print("=" * 70)
    print("AUTHORIZATION SUMMARY")
    print("=" * 70)

    for authorization in engine.authorizations:

        current_state = (
            engine.authorization_state(
                authorization.authorization_id
            )
        )

        account = engine.accounts[
            authorization.account_id
        ]

        print(
            f"{authorization.authorization_id}: "
            f"original={authorization.state.value}, "
            f"current={current_state.value}, "
            f"amount="
            f"{format_money(authorization.amount, account.currency)}"
        )


def print_settlement_summary(engine) -> None:
    print("\n")
    print("=" * 70)
    print("SETTLEMENT RESULTS")
    print("=" * 70)

    if not engine.settlements:
        print("None")
        return

    for settlement in engine.settlements:

        account = engine.accounts[
            settlement.account_id
        ]

        print(
            f"{settlement.event_id}: "
            f"auth={settlement.authorization_id}, "
            f"state={settlement.state}, "
            f"amount="
            f"{format_money(settlement.amount, account.currency)}, "
            f"error={settlement.error or '-'}"
        )


def print_ledger(engine) -> None:
    print("\n")
    print("=" * 70)
    print("FINAL LEDGER ENTRIES")
    print("=" * 70)

    for entry in engine.entries:

        print(
            f"{entry.entry_id:<24} "
            f"source={entry.source_event_id:<20} "
            f"account={entry.account_id} "
            f"value=D{entry.value_day} "
            f"type={entry.entry_type.value:<15} "
            f"amount="
            f"{format_money(entry.amount, entry.currency)}"
        )


def print_final_balances(engine) -> None:
    print("\n")
    print("=" * 70)
    print("FINAL DAY 6 BALANCES")
    print("=" * 70)

    for account_id in (
        "ACC-001",
        "ACC-002",
    ):

        account = engine.accounts[
            account_id
        ]

        balance = engine.balance_on(
            account_id,
            6,
        )

        print(
            f"{account_id}: "
            f"{format_money(balance, account.currency)}"
        )


def main() -> None:
    engine = create_engine()

    # 1. Replay immutable input events.
    replay_events(engine)

    # 2. Calculate Day 1-Day 6 interest and post
    #    one capitalization entry per eligible account.
    accrue_and_capitalize_interest(engine)

    # 3. Produce assessment output.
    print_daily_report(engine)
    print_interest_summary(engine)
    print_authorization_summary(engine)
    print_settlement_summary(engine)
    print_ledger(engine)
    print_final_balances(engine)


if __name__ == "__main__":
    main()
