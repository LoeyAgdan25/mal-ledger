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