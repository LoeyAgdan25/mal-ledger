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