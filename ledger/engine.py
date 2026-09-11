from decimal import Decimal

# defines ledger balance using value date, not posting date

from ledger.models import (
    Account,
    Event,
    EventType,
    EntryType,
    LedgerEntry,
)
from ledger.money import money


class LedgerEngine:
    def __init__(self, accounts: dict[str, Account]):
        self.accounts = accounts

        # Append-only collections.
        self.events: list[Event] = []
        self.entries: list[LedgerEntry] = []

    def replay(self, event: Event) -> None:
        """
        Replay one event into the in-memory ledger.
        """
        self.events.append(event)

        account = self.accounts[event.account_id]

        if event.event_type == EventType.CREDIT:
            self._post_credit(event, account)

        elif event.event_type == EventType.DEBIT:
            self._post_debit(event, account)

        else:
            raise NotImplementedError(
                f"{event.event_type} is not implemented yet"
            )

    def _post_credit(self, event: Event, account: Account) -> None:
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

    def _post_debit(self, event: Event, account: Account) -> None:
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