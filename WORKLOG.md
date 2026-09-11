#WORKLOG

##Project
In-Memory Account Ledger Core

## Goal
-----

## Day 1 - Requirements and Domain Design

### Time
Start: 11:25 Sept 11

## Objective
Understand the ledger structure and identify domain requirements

- Review the six day event stream
- build the structure and requirements ( adding test, Enum classes )
- add the day 1 event and testing it
- add ambiguities in decimal places, complete ledger function balancing (debit, credit)


## 2026-09-11 2:54

Implemented authorization processing.

Separated ledger balance from available balance. Approved
authorizations create holds but do not create monetary ledger entries.

Added tests for:
- Auth-A approval
- hold effects on available balance
- authorization rejection
- exact-zero available balance
- multiple active holds

Decided that authorization state will later be derived from immutable
authorization and settlement facts rather than mutating an existing
authorization record.

## 2026-09-11 3:58 GST

Implemented settlement processing.

E5 now:
- validates Auth-A exists
- validates it was approved
- posts the actual AED 185 settlement as a ledger debit
- derives Auth-A as SETTLED
- releases the AED 200 hold without mutating the original
  authorization record

Implemented E6 rejection. An unknown authorization settlement remains
in the event history and produces a rejected settlement result, but
does not produce a monetary ledger entry.

Added duplicate settlement protection.

Documented undefined over-capture and partial settlement behavior.