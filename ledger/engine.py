from decimal import Decimal

from ledger.models import (
    Account,
    AuthorizationResult,
    AuthorizationState,
    Event,
    EventType,
    EntryType,
    LedgerEntry,
    SettlementResult,
)
from ledger.money import money, OVERDRAFT_FEE_AED

class LedgerEngine:
    def __init__(self, accounts: dict[str, Account]):
        self.accounts = accounts

        # Immutable facts appended during replay.
        self.events: list[Event] = []
        self.entries: list[LedgerEntry] = []
        self.authorizations: list[AuthorizationResult] = []
        self.settlements: list[SettlementResult] = []

    def replay(self, event: Event) -> None:
        self.events.append(event)

        account = self.accounts[event.account_id]

        if event.event_type == EventType.CREDIT:
            self._post_credit(event, account)

        elif event.event_type == EventType.DEBIT:
            self._post_debit(event, account)

        elif event.event_type == EventType.AUTHORIZATION:
            self._process_authorization(event, account)

        elif event.event_type == EventType.SETTLEMENT:
            self._process_settlement(event, account)
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

    #fix the active holds to be updated when settled

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
                and not self.has_settlement(
                    authorization.authorization_id,
                    day,
                )
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

    #find the authorization without mutating
    def find_authorization(
        self,
        authorization_id: str,
    ) -> AuthorizationResult | None:
        for authorization in self.authorizations:
            if authorization.authorization_id == authorization_id:
                return authorization

        return None

    #  add helper wether authorization is accepted
    # this determine when it is settled the hold is no longer active
    def has_settlement(
        self,
        authorization_id: str,
        day: int | None = None,
    ) -> bool:
        return any(
            settlement.authorization_id == authorization_id
            and settlement.state == "ACCEPTED"
            and (
                day is None
                or settlement.value_day <= day
            )
            for settlement in self.settlements
        )

    #process the settlement
    def _process_settlement(
        self,
        event: Event,
        account: Account,
    ) -> None:
        if event.amount is None:
            raise ValueError("Settlement requires an amount")

        if event.authorization_id is None:
            raise ValueError(
                "Settlement requires authorization_id"
            )

        authorization = self.find_authorization(
            event.authorization_id
        )

        if authorization is None:
            self.settlements.append(
                SettlementResult(
                    authorization_id=event.authorization_id,
                    account_id=account.account_id,
                    amount=money(
                        event.amount,
                        account.currency,
                    ),
                    state="REJECTED",
                    event_id=event.event_id,
                    value_day=event.value_day,
                    error="UNKNOWN_AUTHORIZATION",
                )
            )

            return

        if authorization.state != AuthorizationState.APPROVED:
            self.settlements.append(
                SettlementResult(
                    authorization_id=event.authorization_id,
                    account_id=account.account_id,
                    amount=money(
                        event.amount,
                        account.currency,
                    ),
                    state="REJECTED",
                    event_id=event.event_id,
                    value_day=event.value_day,
                    error="AUTHORIZATION_NOT_APPROVED",
                )
            )

            return

        if self.has_settlement(event.authorization_id):
            self.settlements.append(
                SettlementResult(
                    authorization_id=event.authorization_id,
                    account_id=account.account_id,
                    amount=money(
                        event.amount,
                        account.currency,
                    ),
                    state="REJECTED",
                    event_id=event.event_id,
                    value_day=event.value_day,
                    error="ALREADY_SETTLED",
                )
            )
            return

        settlement_amount = money(
            event.amount,
            account.currency,
        )

        entry = LedgerEntry(
            entry_id=f"{event.event_id}-ENTRY",
            source_event_id=event.event_id,
            account_id=account.account_id,
            currency=account.currency,
            amount=-settlement_amount,
            value_day=event.value_day,
            entry_type=EntryType.SETTLEMENT,
        )

        self.entries.append(entry)

        self.settlements.append(
            SettlementResult(
                authorization_id=event.authorization_id,
                account_id=account.account_id,
                amount=settlement_amount,
                state="ACCEPTED",
                event_id=event.event_id,
                value_day=event.value_day,
                error=None,
            )
        )

    # Derived current authorization state.
    # The original authorization fact remains immutable.
    def authorization_state(
        self,
        authorization_id: str,
    ) -> AuthorizationState | None:
        authorization = self.find_authorization(
            authorization_id
        )

        if authorization is None:
            return None

        if authorization.state == AuthorizationState.REJECTED:
            return AuthorizationState.REJECTED

        if self.has_settlement(authorization_id):
            return AuthorizationState.SETTLED

        return AuthorizationState.APPROVED

    # Check condition if there is overdraft fee
    def has_overdraft_fee(
        self,
        account_id: str,
        day: int,
    ) -> bool:
        return any(
            entry.account_id == account_id
            and entry.value_day == day
            and entry.entry_type == EntryType.OVERDRAFT_FEE
            for entry in self.entries
        )

    # Assest the overdraft fee if the available balance is negative and no overdraft fee has been applied yet
    def assess_overdraft_fee(
        self,
        account_id: str,
        day: int,
    ) -> None:
        account = self.accounts[account_id]

        if account.currency != "AED":
            return

        if self.has_overdraft_fee(account_id, day):
            return

        closing_balance = self.balance_on(
            account_id,
            day,
        )

        if closing_balance >= Decimal("0"):
            return

        fee_entry = LedgerEntry(
            entry_id=f"FEE-{account_id}-D{day}",
            source_event_id=f"SYSTEM-FEE-D{day}",
            account_id=account_id,
            currency=account.currency,
            amount=-OVERDRAFT_FEE_AED,
            value_day=day, #value_date to the day assessed
            entry_type=EntryType.OVERDRAFT_FEE,
        )

        self.entries.append(fee_entry)

    # this assest overdraft fees for all days up to the specified day. for critical accounting details

    def assess_overdraft_fees_through(
        self,
        account_id: str,
        through_day: int,
    ) -> None:
        for day in range(1, through_day + 1):
            self.assess_overdraft_fee(
                account_id,
                day,
            )