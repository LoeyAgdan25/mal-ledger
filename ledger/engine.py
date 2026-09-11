from decimal import Decimal

from ledger.models import (
    Account,
    AuthorizationResult,
    AuthorizationState,
    Event,
    EventType,
    EntryType,
    LedgerEntry,
)
from ledger.money import money


class LedgerEngine:
    def __init__(self, accounts: dict[str, Account]):
        self.accounts = accounts

        # Immutable facts appended during replay.
        self.events: list[Event] = []
        self.entries: list[LedgerEntry] = []
        self.authorizations: list[AuthorizationResult] = []

    def replay(self, event: Event) -> None:
        self.events.append(event)

        account = self.accounts[event.account_id]

        if event.event_type == EventType.CREDIT:
            self._post_credit(event, account)

        elif event.event_type == EventType.DEBIT:
            self._post_debit(event, account)

        elif event.event_type == EventType.AUTHORIZATION:
            self._process_authorization(event, account)

        else:
            raise NotImplementedError(
                f"{event.event_type} is not implemented yet"
            )

    def _post_credit(
        self,
        event: Event,
        account: Account,
    ) -> None:
        if event.amount is None:
            raise ValueError("Credit requires an amount")

        entry = LedgerEntry(
            entry_id=f"{event.event_id}-ENTRY",
            source_event_id=event.event_id,
            account_id=account.account_id,
            currency=account.currency,
            amount=money(event.amount, account.currency),
            value_day=event.value_day,
            entry_type=EntryType.CREDIT,
        )

        self.entries.append(entry)

    def _post_debit(
        self,
        event: Event,
        account: Account,
    ) -> None:
        if event.amount is None:
            raise ValueError("Debit requires an amount")

        entry = LedgerEntry(
            entry_id=f"{event.event_id}-ENTRY",
            source_event_id=event.event_id,
            account_id=account.account_id,
            currency=account.currency,
            amount=-money(event.amount, account.currency),
            value_day=event.value_day,
            entry_type=EntryType.DEBIT,
        )

        self.entries.append(entry)

    def _process_authorization(
        self,
        event: Event,
        account: Account,
    ) -> None:
        if event.amount is None:
            raise ValueError("Authorization requires an amount")

        if event.authorization_id is None:
            raise ValueError("Authorization requires authorization_id")

        hold_amount = money(event.amount, account.currency)

        current_available = self.available_balance(
            account.account_id,
            event.value_day,
        )

        available_after_hold = current_available - hold_amount

        if available_after_hold >= Decimal("0"):
            state = AuthorizationState.APPROVED
        else:
            state = AuthorizationState.REJECTED

        result = AuthorizationResult(
            authorization_id=event.authorization_id,
            account_id=account.account_id,
            amount=hold_amount,
            state=state,
            event_id=event.event_id,
            value_day=event.value_day,
        )

        self.authorizations.append(result)

    def balance_on(
        self,
        account_id: str,
        day: int,
    ) -> Decimal:
        account = self.accounts[account_id]

        balance = account.opening_balance

        for entry in self.entries:
            if (
                entry.account_id == account_id
                and entry.value_day <= day
            ):
                balance += entry.amount

        return money(balance, account.currency)

    def active_holds(
        self,
        account_id: str,
        day: int,
    ) -> Decimal:
        account = self.accounts[account_id]

        total = Decimal("0")

        for authorization in self.authorizations:
            if (
                authorization.account_id == account_id
                and authorization.value_day <= day
                and authorization.state == AuthorizationState.APPROVED
            ):
                total += authorization.amount

        return money(total, account.currency)

    def available_balance(
        self,
        account_id: str,
        day: int,
    ) -> Decimal:
        account = self.accounts[account_id]

        ledger_balance = self.balance_on(
            account_id,
            day,
        )

        holds = self.active_holds(
            account_id,
            day,
        )

        return money(
            ledger_balance - holds,
            account.currency,
        )