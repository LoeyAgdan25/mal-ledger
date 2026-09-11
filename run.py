from ledger.models import Account
from ledger.money import money


accounts = {
    "ACC-001": Account(
        account_id="ACC-001",
        currency="AED",
        opening_balance=money("0", "AED"),
    ),
    "ACC-002": Account(
        account_id="ACC-002",
        currency="BHD",
        opening_balance=money("0", "BHD"),
    ),
}


if __name__ == "__main__":
    for account in accounts.values():
        print(account)