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
