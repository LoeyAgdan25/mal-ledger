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