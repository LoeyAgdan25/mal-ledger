## Rejected: E7 causes exactly one overdraft fee on Day 2

Decision: REJECTED

The non-negotiable overdraft rule states that AED 25.00 is assessed
once per day per account whenever that day's closing ledger balance
is negative.

After E7 is replayed with value_date Day 2, the pre-fee balances are:

- Day 2: AED -370.00
- Day 3: AED 30.00
- Day 4: AED -155.00
- Day 5: AED -155.00

Assessment is performed chronologically because each fee is itself a
ledger posting with value_date equal to its assessment day.

The Day 2 AED 25.00 fee changes the Day 3 balance to AED 5.00.
Day 4 then closes at AED -180.00 and receives another AED 25.00 fee.
Day 5 consequently closes negative and also receives its daily fee.

The resulting fee days are therefore Day 2, Day 4 and Day 5.

I chose to preserve the explicit non-negotiable daily fee rule rather
than alter the implementation to satisfy this contradictory acceptance
criterion.

## Rejected: After E9 all balances and fees return to pre-E7 values

Decision: REJECTED

E9 reverses E7 by appending an equal and opposite ledger entry.

E7 remains in the ledger as AED -620.00 and E9 adds AED +620.00
with the same value date.

This restores the principal effect of E7 to zero.

However, overdraft fees already assessed are independent ledger
entries. The specification does not define automatic reversal of those
fees when the original debit is later reversed.

Therefore the implementation keeps the fee entries unless an explicit
fee-reversal rule is provided.