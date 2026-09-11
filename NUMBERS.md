# Numerical Decisions

## AED precision

Value: 2 decimal places.

Reason:
The specification explicitly requires AED amounts to be stored and
rounded to two decimal places.

Why not half:
A one-decimal representation would violate the required currency
precision and could not accurately represent the AED 25.00 fee.

## BHD precision

Value: 3 decimal places.

Reason:
The specification explicitly requires BHD amounts to use three
decimal places.

## Opening balances

ACC-001: AED 0.00
ACC-002: BHD 0.000

Reason:
Both are explicitly specified.

## Rounding mode

Value: ROUND_HALF_UP

Reason:
The specification defines currency precision but does not define
a rounding mode. ROUND_HALF_UP was chosen as an explicit,
deterministic monetary rounding policy.

This decision is also documented in AMBIGUITIES.md.

## Minimum available balance after authorization

Value: 0.

Reason:

The specification states that an authorization is approved if the
available balance remains "at or above zero" after applying the hold.

Therefore the comparison is:

available_after_hold >= 0

not:

available_after_hold > 0

## Overdraft fee

Value: AED 25.00.

Reason:
Explicitly specified by the assessment.


## Overdraft threshold

Value: closing ledger balance < AED 0.00.

Reason:
The fee applies when the closing ledger balance is negative.

A zero closing balance therefore does not incur a fee.

## Daily interest rate

Value: 0.0004 per day.

Equivalent percentage: 0.04%.

Reason:
Explicitly specified by the assessment.

Why not half:
This is a supplied business rule rather than a chosen constant.
Using 0.0002 would change the specified financial behavior.

## Interest capitalization day

Value: Day 6.

Reason:
The assessment requires daily rounded accruals to capitalize as a
single credit at the end of Day 6.

Why not half:
There is no meaningful half-day equivalent in the supplied assessment
window.


