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

class AuthorizationState(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SETTLED = "SETTLED"

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
    installment_count: int = 1


@dataclass(frozen=True)
class LedgerEntry:
    entry_id: str
    source_event_id: str
    account_id: str
    currency: str
    amount: Decimal
    value_day: int
    entry_type: EntryType


@dataclass(frozen=True)
class AuthorizationResult:
    authorization_id: str
    account_id: str
    amount: Decimal
    state: AuthorizationState
    event_id: str
    value_day: int

@dataclass(frozen=True)
class SettlementResult:
    authorization_id: str
    account_id: str
    amount: Decimal
    state: str
    event_id: str
    value_day: int
    error: str | None = None

@dataclass(frozen=True)
class InterestAccrual:
    account_id: str
    day: int
    balance: Decimal
    amount: Decimal