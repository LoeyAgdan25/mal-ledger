# Worklog — MAL In-Memory Ledger

## Project

**MAL In-Memory Account Ledger Core**

## Objective

Implement a small deterministic in-memory ledger that processes the supplied event stream while preserving accounting history and correctly handling:

- credits and debits
- value dates
- authorization holds
- settlement
- overdraft fees
- reversals
- installment / EPP allocation
- multiple currency precisions
- daily interest accrual

The implementation intentionally focuses on the ledger domain rather than infrastructure such as databases, HTTP APIs, message brokers, or user interfaces.

---

## Working Approach

I approached the exercise incrementally rather than attempting to implement the entire event stream at once.

For each new requirement I generally followed this process:

1. Read the relevant requirement and identify the expected ledger behavior.
2. Identify any ambiguity or conflict with previously defined behavior.
3. Add or update the domain model where necessary.
4. Implement the smallest behavior required.
5. Add tests for the new behavior.
6. Run the existing tests to check for regressions.
7. Review the resulting balances and ledger entries manually.
8. Record important assumptions or specification conflicts in the documentation.

This allowed the implementation to evolve while keeping previously implemented behavior verifiable.

---

## Initial Design

I first modeled the system around an append-only ledger.

The core principle was that once a financial fact has been recorded, later events should not rewrite that history.

For example:

- a reversal does not delete the original transaction;
- settlement does not mutate the original authorization;
- authorization state is derived from the sequence of events;
- interest capitalization is represented by an additional ledger entry.

This approach provides an auditable history of how the final account state was reached.

I also separated the concepts of:

- **posted day** — when an event is processed;
- **value day** — when its monetary effect applies to the balance.

This became important when implementing backdated transactions.

---

## Monetary Representation

I used Python `Decimal` rather than binary floating-point values.

Currency precision is explicit:

- AED — 2 decimal places
- BHD — 3 decimal places

The specification defines currency precision but does not explicitly define a rounding algorithm.

I therefore selected:

`ROUND_HALF_UP`

and documented this decision in `AMBIGUITIES.md`.

The goal was to make monetary calculations deterministic rather than relying on an implicit Decimal rounding mode.

---

## Credits and Debits

The first implementation stage established the basic ledger behavior for credits and debits.

Ledger entries are immutable records, and balances are derived from those records rather than maintained as a separately mutated balance field.

This provided the foundation for later requirements.

Tests were added before moving to authorization behavior.

---

## Authorization Holds

Authorization introduced an important distinction between:

**ledger balance**

and

**available balance**

An approved authorization should reduce available funds without immediately creating a monetary ledger entry.

Therefore:

`available balance = ledger balance - active authorization holds`

If approving an authorization would cause the available balance to become negative, the authorization is rejected.

Authorization decisions are stored separately from monetary ledger entries.

This preserves the append-only design while allowing the current authorization state to be derived later.

---

## Settlement

Settlement required determining what happens to an existing authorization.

I chose not to modify the original authorization.

Instead, settlement is recorded as another immutable fact.

Once a settlement exists for an approved authorization:

- the authorization is considered settled;
- its hold is no longer active;
- the settlement amount becomes a monetary ledger entry.

The actual settlement amount is used rather than assuming that it must equal the original authorization amount.

A settlement referencing an unknown or invalid authorization is rejected without creating a monetary posting.

---

## Backdated Transactions and Overdraft Fees

The supplied event stream includes a transaction posted later but carrying an earlier value date.

This required balances to be reconstructed according to `value_day` rather than simply according to processing order.

The transaction can therefore affect historical balance calculations.

The overdraft rule was implemented as a daily assessment based on the resulting value-dated balance.

During implementation I identified a conflict between the stated daily overdraft rule and one of the supplied expected outcomes.

Both behaviors cannot hold simultaneously.

I chose to preserve the explicit daily rule and documented the conflicting acceptance criterion in `REJECTED.md` rather than silently introducing a special case purely to reproduce the example.

This keeps the engine deterministic and makes the disagreement visible for review.

---

## Reversals

Reversal behavior follows the append-only accounting model.

The original transaction remains in the ledger.

A reversal creates a new compensating entry with the opposite monetary effect.

Conceptually:

`original transaction + reversal = net zero monetary effect`

This preserves the fact that the original transaction occurred while allowing its financial effect to be reversed.

I deliberately did not delete or modify the original entry.

---

## Installments / EPP

Installment allocation introduced a monetary rounding problem.

A transaction cannot always be divided equally into the requested number of installments while simultaneously satisfying currency precision and exact conservation of the original amount.

The implementation therefore:

1. converts the total into currency minor units;
2. divides those units across the requested installment count;
3. distributes the remainder deterministically;
4. converts the allocated values back to Decimal amounts.

The important invariant is:

`sum(all installment amounts) == original transaction amount`

For example, BHD `10.000` divided into three installments cannot produce three identical `3.334` entries because:

`3.334 + 3.334 + 3.334 = 10.002`

The implementation instead preserves the original amount using a deterministic allocation such as:

`3.334 + 3.333 + 3.333 = 10.000`

The contradictory equal-installment expectation is preserved as an intentionally failing test and is excluded from the normal test run through a pytest marker.

This makes the specification conflict reproducible rather than hiding it.

---

## Daily Interest

Daily interest was added after the main transaction lifecycle was working.

Interest is calculated from the applicable daily balance using the configured daily interest rate.

The calculation follows this sequence:

1. determine the relevant balance for the day;
2. calculate that day's interest;
3. round the daily amount using the account currency precision;
4. retain the daily accrual;
5. accumulate the rounded daily amounts;
6. capitalize the accumulated interest as a ledger entry at the end of the supplied period.

This behavior is exposed through:

`engine.accrue_interest_through(account_id, day)`

The method accrues interest through the requested day while avoiding duplicate daily accrual for days that have already been processed.

The numerical assumptions and constants used for this part of the implementation are documented separately.

---

## Testing Strategy

Tests were added incrementally as each behavior was implemented.

The suite covers the important domain behaviors including:

- monetary precision;
- credits and debits;
- value-dated balances;
- authorization approval;
- authorization rejection;
- active holds;
- available balance;
- settlement;
- invalid settlement;
- overdraft assessment;
- reversal behavior;
- installment allocation;
- BHD precision;
- daily interest;
- interest capitalization.

The normal test command excludes the intentionally contradictory specification test:

`pytest -v -m "not intentional_failure"`

At the final verification stage this produced:

**30 passing tests and 1 intentionally deselected test.**

The intentionally failing test can still be run separately to demonstrate the installment specification conflict.

---

## Specification Ambiguities

I avoided silently guessing where the requirements did not completely define behavior.

Important decisions were recorded in `AMBIGUITIES.md`, including:

- monetary rounding mode;
- authorization state representation;
- settlement behavior;
- interpretation of append-only state;
- behavior where the supplied expected result conflicts with another stated invariant.

Numerical assumptions are documented in `NUMBERS.md`.

Requirements that could not simultaneously be satisfied are documented in `REJECTED.md`.

The intention of these documents is to separate:

**what the specification explicitly states**

from

**what I had to decide as the implementer.**

---

## AI Usage

AI tools were used during development, as permitted by the assessment.

I used AI primarily for:

- discussing possible interpretations of ambiguous requirements;
- reviewing implementation approaches;
- identifying potential edge cases;
- generating and reviewing test ideas;
- debugging Python errors;
- reviewing documentation structure;
- challenging assumptions in the implementation.

I did not treat AI output as authoritative.

Suggested behavior was checked against the supplied requirements, the resulting ledger entries, test results, and my understanding of payment transaction processing.

I have professional experience working with POS/payment systems, so concepts such as transaction reversals, authorization, settlement, installment/EPP processing, and interest-related transaction behavior were familiar domain concepts. AI was primarily useful for accelerating implementation and review rather than replacing the domain reasoning behind those decisions.

---

## Problems Encountered

The most significant difficulties were not Python implementation problems but specification interpretation.

### Conflicting overdraft behavior

The stated daily overdraft rule and one supplied expected result could not both be reproduced without introducing a special case.

I chose the general invariant and documented the disagreement.

### Equal installment requirement

BHD `10.000 / 3` cannot produce three identical currency-valid installment amounts while also summing exactly to `10.000`.

I prioritized conservation of money and documented the contradiction.

### Append-only state

Authorization and settlement initially appear naturally stateful.

Instead of mutating authorization records, I modeled later actions as additional facts and derived current state from those facts.

### Historical balances after reversal

A reversal carrying an earlier value date can change the reconstructed historical balance even though fees previously generated from the earlier processing state remain ledger facts.

The current implementation does not automatically reverse previously assessed fees because the specification does not define fee-reversal behavior.

A production implementation would likely model explicit fee reassessment or fee reversal events.

---

## Known Limitations

This implementation intentionally remains small and focused on the supplied assessment scenario.

It is not intended to represent a complete production banking ledger.

Known limitations include:

- no database persistence;
- no HTTP/API layer;
- no distributed transaction handling;
- no message broker;
- no concurrent transaction processing;
- no general event-id deduplication mechanism;
- supplied events are assumed to be replayed once;
- authorization identifiers are assumed to be valid and unique within the supplied scenario;
- production-grade account and authorization ownership validation is outside the current scope;
- recurring statement-cycle interest processing is not implemented;
- fee reversal/reassessment policy is not defined by the supplied requirements.

These would be important concerns in a production implementation but were intentionally not added because they do not improve the correctness of the supplied domain exercise.


## Final Verification

Before considering the implementation complete, I:

- ran the normal test suite;
- verified that all non-contradictory tests passed;
- ran the demonstration program;
- manually inspected important ledger entries;
- checked final balances;
- reviewed currency precision;
- reviewed installment conservation;
- reviewed interest capitalization;
- documented specification conflicts;
- documented known limitations.

Final normal test status:

**30 passed, 1 intentionally deselected**

The remaining deselected test exists specifically to demonstrate a documented contradiction in the supplied installment expectation.

---

## What I Would Do Next

If this engine were moving toward production rather than remaining an assessment exercise, the next priorities would be:

1. event-level idempotency and duplicate detection;
2. persistent ledger storage;
3. transactional consistency and concurrency control;
4. stronger account/authorization ownership validation;
5. explicit fee reversal and reassessment rules;
6. recurring interest/statement-cycle processing;
7. audit metadata and observability;
8. an application/API layer around the domain engine.

I intentionally stopped before these additions because the goal of this exercise is to demonstrate correctness and reasoning around the supplied ledger requirements rather than build an entire banking platform.

---

## Final Reflection

The main challenge of this exercise was not producing a large amount of code.

It was deciding how to preserve consistent accounting invariants when some requirements were ambiguous or contradictory.

The principles I prioritized were:

**preserve history, conserve money, make rounding explicit, derive state from facts, keep behavior deterministic, test important invariants, and document decisions rather than hiding ambiguity.**

The resulting implementation is intentionally small enough that I can explain and defend its behavior without relying on external tools.

## Development Timeline

### 11:25 — Requirements analysis and ledger foundation
- Reviewed the event stream.
- Identified the core ledger invariants.
- Established append-only ledger behavior.
- Separated posted day from value day.

### 14:54 — Authorization and holds
- Implemented authorization decisions.
- Added active holds.
- Distinguished ledger balance from available balance.
- Added authorization tests.

### 15:58 — Settlement
- Added settlement handling.
- Derived settlement state without mutating authorization.
- Released settled authorization holds.
- Added rejection behavior for invalid settlement.

### 17:25 — Backdated transaction and overdraft
- Implemented value-dated balance reconstruction.
- Added overdraft assessment.
- Identified contradiction in expected overdraft behavior.
- Documented the decision rather than adding a special case.

### 18:00 — Reversal
- Added compensating reversal entries.
- Preserved the original transaction in the ledger.

### 18:38 — EPP / installments
- Implemented minor-unit installment allocation.
- Identified the BHD 10.000 / 3 mathematical contradiction.
- Added the intentional-failure test.

### 20:00 — Daily interest
- Implemented daily accrual.
- Added currency-aware daily rounding.
- Added capitalization.
- Added duplicate-accrual protection.

### 20:42 — Verification and documentation
- Ran the complete test suite.
- Reviewed final balances.
- Updated ambiguities and rejected requirements.
- Reviewed submission documentation.