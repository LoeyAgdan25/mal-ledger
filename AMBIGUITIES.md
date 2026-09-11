# Ambiguities

## Monetary rounding mode

The specification defines AED as two decimal places and BHD as
three decimal places but does not specify the rounding algorithm.

Resolution:
Use Decimal with ROUND_HALF_UP.

Reason:
A deterministic rounding policy is necessary before installment
allocation and interest calculations can be implemented.

Alternative considered:
Python Decimal's default ROUND_HALF_EVEN.

Why not chosen:
Using the implicit default would hide an important domain decision.
The selected behavior is therefore made explicit.

## Authorization state representation

The specification requires an append-only ledger but refers to
authorization states such as approved and settled.

Resolution:

Authorization events and later settlement events are stored as
separate immutable facts. The current authorization state is derived
from those facts rather than mutating the original authorization
record.

Reason:

Changing an authorization record from APPROVED to SETTLED would make
the implementation stateful through mutation and would obscure the
history that produced the final result.

## Settlement amount greater than authorization hold

The specification demonstrates an authorization for AED 200 followed
by settlement for AED 185, but does not define whether a settlement
may exceed its original authorization amount.

Resolution:

The current implementation does not add a separate over-capture rule
because none is required by the supplied event stream.


Reason:

Rejecting or accepting over-capture without a specification would add
domain behavior that was not requested.

## Duplicate settlement of one authorization

The specification does not state whether the same authorization can
settle more than once.

Resolution:

Only one accepted settlement is permitted per authorization in this
implementation.

A later settlement against the same already-settled authorization is
rejected with ALREADY_SETTLED.

Reason:

The supplied event model describes a single authorization followed by
a settlement. Accepting multiple settlements would require explicit
partial-capture semantics that are not defined.

## Retroactive overdraft assessment

E7 is posted on Day 5 but has value_date Day 2.

The specification defines closing ledger balance using entries whose
value_date is less than or equal to the evaluated day, but does not
fully specify how a newly discovered backdated transaction interacts
with previously evaluated fee days.

Resolution:

When a backdated event changes historical closing balances, affected
days are reevaluated chronologically.

Fees are ledger entries themselves and therefore participate in the
closing balances of subsequent days.

Reason:

This follows the explicit value-date definition and the requirement
that an overdraft fee is booked with value_date equal to its
assessment day.

## Reversal of previously fee-causing transactions

The specification requires append-only ledger behavior but does not
state whether reversing a transaction automatically reverses fees
previously caused by that transaction.

Resolution:

A reversal only compensates the referenced monetary entry.

Previously assessed overdraft fees remain as separate append-only
ledger entries.

Reason:

Automatically reversing fees would introduce behavior not defined by
the specification.

## Equal installment allocation when currency precision prevents equality

The specification describes E10 as BHD 10.000 posted as three equal
installments.

At BHD three-decimal precision, BHD 10.000 cannot be divided into
three exactly equal representable amounts.

Resolution:

Amounts are converted to minor currency units before division.

Any indivisible remainder is allocated deterministically to the
earliest installments.

For E10 the resulting postings are:

- BHD 3.334
- BHD 3.333
- BHD 3.333

Reason:

This preserves the exact original total and currency precision while
remaining deterministic.