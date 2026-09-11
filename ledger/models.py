from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class EventType(str, Enum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"
    AUTHORIZATION = "AUTHORIZATION"
    SETTLEMENT = "SETTLEMENT"
    REVERSAL = "REVERSAL"


class EntryType(str, Enum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"
    SETTLEMENT = "SETTLEMENT"
    REVERSAL = "REVERSAL"
    OVERDRAFT_FEE = "OVERDRAFT_FEE"
    INTEREST = "INTEREST"


@dataclass(frozen=True)
class Account:
    account_id: str
    currency: str
    opening_balance: Decimal


@dataclass(frozen=True)
class Event:
    event_id: str
    posted_day: int
    value_day: int
    account_id: str
    event_type: EventType

    amount: Decimal | None = None
    authorization_id: str | None = None
    reference_event_id: str | None = None


@dataclass(frozen=True)
class LedgerEntry:
    entry_id: str
    source_event_id: str
    account_id: str
    currency: str
    amount: Decimal
    value_day: int
    entry_type: EntryType