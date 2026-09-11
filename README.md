# MAL In-Memory Ledger

An in-memory account ledger implementation for the MAL engineering assessment.

The project provides deterministic handling of:

- credits and debits;
- value-dated transactions;
- authorization holds;
- settlements;
- rejected settlements;
- overdraft fees;
- append-only reversals;
- AED and BHD currency precision;
- installment allocation;
- daily interest accrual;
- Day 6 interest capitalization.

The implementation intentionally contains no web layer, database, persistence layer, UI, ORM, Kafka, or other infrastructure outside the requested ledger domain.

---

## Requirements

- Python 3.12 or later
- `pytest`

---

## Setup

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Install the test dependency:

```bash
pip install pytest
```

---

## Running the Test Suite

### Normal Correctness Suite

Run:

```bash
pytest -v -m "not intentional_failure"
```

This excludes the deliberately retained failing test.
The normal correctness suite should pass.

### Intentional Failing Test

Run the complete suite with:

```bash
pytest -v
```

One test is deliberately expected to fail. It demonstrates the mathematical contradiction in the acceptance criterion requiring all three installments of BHD 10.000 to equal BHD 3.334.

That requirement would produce:

```text
3.334
3.334
3.334
-----
10.002
```

This does not equal the original BHD 10.000 amount.

The implementation instead uses:

```text
3.334
3.333
3.333
-----
10.000
```

The test is marked as follows:

```python
@pytest.mark.intentional_failure
```

The marker must be registered in `pytest.ini`.

> Review note: Keeping an intentionally failing test in the default test suite is unusual for production projects. It is appropriate here only because the assessment explicitly requires it. In a normal project, consider placing it in a separate test module or running it through a dedicated command.

---

## Running the Complete Ledger Scenario

Run:

```bash
python run.py
```

The runner replays the assessment event stream in the exact supplied order.

It then:

1. assesses applicable overdraft fees;
2. calculates rounded daily interest;
3. capitalizes interest once at the end of Day 6;
4. prints the Day 1–Day 6 accounting report;
5. prints authorization and settlement results;
6. prints the final append-only ledger.

---

## Reading the Output

The runner prints several sections.

### Event Replay

This section shows the exact order in which E1–E10 enter the system.

The input list is not automatically sorted by `posted_day` or `value_day`. The supplied event sequence is treated as authoritative.

### Daily Report

For each day from Day 1 through Day 6, the report shows:

- closing ledger balance;
- overdraft fee assessments;
- authorization states;
- processing errors;
- daily interest accrual.

Ledger balances are reconstructed using `value_day`.
Processing order is determined by event replay order.
These concepts are intentionally separate.

---

## Domain Model

The implementation distinguishes between three major concepts:

1. events;
2. ledger entries;
3. derived state.

### Events

An `Event` is an immutable input fact describing something submitted to the ledger.

Examples include:

```text
CREDIT
DEBIT
AUTHORIZATION
SETTLEMENT
REVERSAL
```

Events are never deleted or modified.

### Ledger Entries

A `LedgerEntry` represents an actual monetary posting.

Examples include:

```text
CREDIT
DEBIT
SETTLEMENT
REVERSAL
OVERDRAFT_FEE
INTEREST
```

Credits are positive.

Debits, settlements, and overdraft fees are negative.

A reversal is an equal and opposite compensating ledger entry.

Interest capitalization is a positive credit.

### Derived State

Some values are calculated from immutable facts rather than stored by mutating previous events.

Examples include:

- ledger balance;
- available balance;
- active holds;
- current authorization state.

The core design principle is:

> Immutable facts are stored; current state is derived.

---

## Posted Day Versus Value Day

`posted_day` identifies when the system receives or processes an event.

`value_day` identifies the accounting day affected by the monetary posting.

This distinction is important for E7.

E7 is received on Day 5 but has:

```text
value_day = Day 2
```

Therefore, the transaction changes historical accounting balances beginning on Day 2.

---

## Ledger Balance

The closing ledger balance for an account on a requested day is calculated as:

```text
opening balance
+
all ledger entries where value_day <= requested day
```

Authorization holds are not monetary ledger entries.

---

## Available Balance

Available balance is calculated as:

```text
ledger balance - active authorization holds
```

An authorization is approved only when applying the requested hold leaves the available balance greater than or equal to zero.

---

## Authorization Handling

E3 requests:

```text
Auth-A
AED 200.00
```

After E1 and E2, the ledger balance is:

```text
AED 250.00
```

Applying the hold gives:

```text
250.00 - 200.00 = 50.00
```

Therefore, Auth-A is approved.

The ledger remains AED 250.00 because authorization holds affect available balance, not ledger balance.

---

## Settlement

E5 settles Auth-A for:

```text
AED 185.00
```

The settlement creates a real ledger entry:

```text
AED -185.00
```

The original AED 200.00 authorization hold stops being active.

The remaining AED 15.00 does not create a ledger credit because the authorization hold was never a ledger debit.

---

## Unknown Authorization

E6 attempts to settle:

```text
Auth-Z
```

No corresponding authorization exists.
The settlement is therefore rejected.
No funds leave the account, and no monetary ledger entry is generated.
The rejected event remains part of the immutable event history.

---

## Backdated E7 Debit

E7 is:

```text
posted_day = Day 5
value_day  = Day 2
amount     = AED 620.00
```

Before overdraft fees, its reconstructed Day 2 balance becomes:

```text
AED -370.00
```

Historical accounting days are then evaluated chronologically.

---

## Overdraft Fees

The AED overdraft fee is:

```text
AED 25.00
```

A fee is assessed once per account per day when that day's closing ledger balance is negative.

Under the selected interpretation, the resulting fees are:

```text
Day 2: AED -25.00
Day 4: AED -25.00
Day 5: AED -25.00
```

A fee is itself a ledger entry. Therefore, a fee affects later closing balances.

The selected interpretation and the conflicting acceptance criterion are documented in `REJECTED.md`.

> Review note: The phrase “E7-related fee” can be ambiguous because E7 is backdated and fee entries affect later balances. The implementation should document whether fees are assessed from the original event set, from the evolving ledger including prior fees, or from a recomputed historical view. The examples in this README assume the selected implementation behavior is authoritative.

---

## Auth-B

E8 requests:

```text
Auth-B
AED 90.00
```

At the time E8 is processed, the ledger including the assessed overdraft fees is:

```text
AED -230.00
```

Applying another AED 90.00 hold would produce:

```text
-230.00 - 90.00 = -320.00
```

Therefore, Auth-B is rejected.

A rejected authorization:

- creates no monetary ledger entry;
- creates no active hold.

Later backdated events do not retroactively rewrite this authorization decision.

---

## Reversal

E9 reverses E7.

The ledger is append-only, so E7 is not removed or changed.

Instead:

```text
E7 = AED -620.00
E9 = AED +620.00
```

The two principal postings net to zero.

Previously assessed overdraft fees remain because the assessment does not define an automatic fee-reversal mechanism.

This interpretation is documented in `AMBIGUITIES.md` and `REJECTED.md`.

---

## Currency Precision

The ledger supports:

```text
AED = 2 decimal places
BHD = 3 decimal places
```

Python `Decimal` is used for all monetary arithmetic.

Binary floating-point values are not used for ledger calculations.

The selected rounding mode is:

```text
ROUND_HALF_UP
```

---

## BHD Installments

E10 is:

```text
BHD 10.000
3 installments
```

BHD supports three decimal places.

An exactly equal representation is mathematically impossible at that precision because:

```text
10.000 / 3 = 3.333333...
```

The implementation converts the amount into minor units and distributes the indivisible remainder deterministically.

The resulting ledger entries are:

```text
BHD 3.334
BHD 3.333
BHD 3.333
---------
BHD 10.000
```

The earliest installment receives the remainder.

E10 remains one immutable event but creates three monetary ledger entries.

---

## Daily Interest

The daily interest rate is:

```text
0.04%
```

Internally, this is represented as:

```text
0.0004
```

Interest applies only to positive closing ledger balances.

The calculation is:

```text
positive closing ledger balance × 0.0004
```

Each day's interest is immediately rounded to the precision of the account currency.

Negative or zero balances receive zero interest.

---

## Interest Capitalization

Daily accruals are calculation records. They do not immediately create ledger entries.
After all Day 1–Day 6 accruals have been calculated, the rounded daily values are summed.
That total is posted as one credit with:

```text
value_day = Day 6
```

The implementation therefore guarantees:

```text
capitalized interest
=
sum of rounded daily accruals
```

No rounding remainder is discarded.

---

## ACC-001 Interest Example

After E9, with previously assessed fees retained, the pre-interest closing balances are:

```text
Day 1    250.00
Day 2    225.00
Day 3    625.00
Day 4    415.00
Day 5    390.00
Day 6    390.00
```

Daily interest is:

```text
Day 1:
250.00 × 0.0004 = 0.100
rounded = 0.10

Day 2:
225.00 × 0.0004 = 0.090
rounded = 0.09

Day 3:
625.00 × 0.0004 = 0.250
rounded = 0.25

Day 4:
415.00 × 0.0004 = 0.166
rounded = 0.17

Day 5:
390.00 × 0.0004 = 0.156
rounded = 0.16

Day 6:
390.00 × 0.0004 = 0.156
rounded = 0.16
```

Total:

```text
0.10
0.09
0.25
0.17
0.16
0.16
----
0.93 AED
```

A single Day 6 credit of:

```text
AED +0.93
```

is posted.

The final Day 6 balance is therefore:

```text
AED 390.93
```

---

## ACC-002 Interest Example

E10 gives ACC-002:

```text
Day 5 = BHD 10.000
Day 6 = BHD 10.000
```

Interest is:

```text
Day 5:
10.000 × 0.0004 = 0.004

Day 6:
10.000 × 0.0004 = 0.004
```

Capitalized total:

```text
BHD 0.008
```

Final Day 6 balance:

```text
BHD 10.008
```

---

## Day 6 Ordering

Day 6 interest is calculated using the balance before the Day 6 interest capitalization entry.

The sequence is:

```text
calculate Day 6 interest
        ↓
sum rounded Day 1–Day 6 accruals
        ↓
post one Day 6 interest credit
```

This prevents capitalized interest from earning interest on itself on the same day.

---

## Expected Final Balances

With the documented design decisions:

```text
ACC-001
Day 6 = AED 390.93
```

and:

```text
ACC-002
Day 6 = BHD 10.008
```

---

## Project Structure

```text
mal-ledger/
├── ledger/
│   ├── __init__.py
│   ├── engine.py
│   ├── models.py
│   └── money.py
│
├── tests/
│   ├── __init__.py
│   └── test_basic_ledger.py
│
├── run.py
├── pytest.ini
├── README.md
├── NUMBERS.md
├── AMBIGUITIES.md
├── REJECTED.md
└── WORKLOG.md
```

---

## Supporting Documentation

### `NUMBERS.md`

Documents numerical constants used by the implementation, including:

- AED precision;
- BHD precision;
- AED 25.00 overdraft fee;
- 0.04% daily interest rate;
- Day 6 capitalization;
- installment allocation.

Each selected value includes an explanation of why it is used.

### `AMBIGUITIES.md`

Documents behavior not completely specified by the assessment and the deterministic interpretation selected by this implementation.

Examples include:

- rounding mode;
- retroactive fee evaluation;
- fee treatment after reversal;
- authorization decisions after later backdated events;
- BHD installment remainder allocation;
- Day 6 interest ordering.

### `REJECTED.md`

Documents acceptance criteria that conflict with stronger requirements or mathematical constraints.

Examples include:

- exactly one E7-related fee;
- automatically returning all fees after E9;
- three installments all equal to BHD 3.334;
- discarding interest rounding remainder.

### `WORKLOG.md`

Contains timestamped implementation progress and design decisions.

Entries should reflect actual development activity and should not be retroactively fabricated.

---

## Review Summary

The README is structurally sound and clearly explains the main ledger concepts. The following points should be verified against the implementation before submission:

1. Confirm that the documented final balances match the actual output from `python run.py`.
2. Confirm that the overdraft-fee algorithm produces exactly the documented Day 2, Day 4, and Day 5 fees.
3. Confirm that interest is calculated before Day 6 capitalization.
4. Confirm that daily interest is rounded per day, not only after summing all accruals.
5. Confirm that BHD installment entries sum exactly to BHD 10.000.
6. Confirm that rejected settlements and rejected authorizations create no monetary ledger entries.
7. Confirm that reversal entries are append-only and do not delete or mutate E7.
8. Confirm that `pytest.ini` registers the `intentional_failure` marker.
9. Confirm that the normal test command passes:
   ```bash
   pytest -v -m "not intentional_failure"
   ```
10. Confirm that the complete test command produces only the documented intentional failure.

---

## Core Design Statement

The primary architectural principle of this implementation is:

> Immutable facts are stored; current state is derived.

Events and ledger postings remain append-only.

Balances, active holds, authorization states, interest accruals, and reporting views are reconstructed from those facts.

## Known limitations / Out of scope

- Replay assumes each supplied event is processed once.
- Event-id deduplication is not implemented.
- Authorization identifiers are assumed unique in the supplied stream.
- Cross-account authorization references are not part of the supplied scenario.
- Interest capitalization supports the supplied six-day assessment period,
  not recurring production statement cycles.