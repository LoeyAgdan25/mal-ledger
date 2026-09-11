## MAL In-Memory Ledger

An in-memory account ledger for MAL engineering assestment.

The project focuses on deterministic accounting behavior, value dated transactions, authorization holds, settlements, overdraft assstment, append-only reversals, multi-currency precision, installment allocation and daily interest.

No database, HTTP API, UI, or external persistence is used.

# Requirements
    Python 3.12+
    pytest

# Setup
    - Create virtual environment:
        - python3 -m venv .venv

    - Activate it on macOS/Linux:
        - source .venv/bin/activate

    - Install pytest:
        - pip install pytest

# Running the tests

    Run the normal correctness suite:
    pytest -v -m "not intentional_failure"

    This should pass completely.

    The repository deliberately contains one annotated failing test because the assestment requires a failing test against the chosen design.

    To run every test, including the intentional failure.

    pytest -v

    
