
from database import get_connection
from decimal import Decimal, InvalidOperation
import secrets


def create_account():
    name = input("Customer name: ").strip()
    phone = input("Phone number: ").strip()
    email = input("Email: ").strip()
    address = input("Address: ").strip()

    if not name or not phone:
        print("Name and phone are required.")
        return

    account_number = str(secrets.randbelow(9000000000) + 1000000000)

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO customers
                        (full_name, phone, email, address)
                    VALUES (%s, %s, %s, %s)
                    RETURNING customer_id
                """, (name, phone, email or None, address or None))

                customer_id = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO accounts
                        (customer_id, account_number, balance)
                    VALUES (%s, %s, 0.00)
                """, (customer_id, account_number))

        print("Account created successfully!")
        print("Account number:", account_number)

    except Exception as e:
        print("Could not create account:", e)


def get_amount():
    try:
        amount = Decimal(input("Enter amount: ").strip())

        if not amount.is_finite() or amount <= 0:
            raise ValueError("Amount must be positive.")

        if amount.as_tuple().exponent < -2:
            raise ValueError("Maximum two decimal places allowed.")

        return amount

    except (InvalidOperation, ValueError) as e:
        print("Invalid amount:", e)
        return None


def deposit():
    account = input("Account number: ").strip()
    amount = get_amount()

    if amount is None:
        return

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT account_id
                FROM accounts
                WHERE account_number = %s
                FOR UPDATE
            """, (account,))

            row = cur.fetchone()

            if row is None:
                print("Account not found.")
                return

            account_id = row[0]

            cur.execute("""
                UPDATE accounts
                SET balance = balance + %s
                WHERE account_id = %s
            """, (amount, account_id))

            cur.execute("""
                INSERT INTO transactions
                    (account_id, transaction_type, amount)
                VALUES (%s, 'DEPOSIT', %s)
            """, (account_id, amount))

    print("Deposit successful!")


def withdraw():
    account = input("Account number: ").strip()
    amount = get_amount()

    if amount is None:
        return

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT account_id, balance
                FROM accounts
                WHERE account_number = %s
                FOR UPDATE
            """, (account,))

            row = cur.fetchone()

            if row is None:
                print("Account not found.")
                return

            account_id, balance = row

            if balance < amount:
                print("Insufficient balance.")
                return

            cur.execute("""
                UPDATE accounts
                SET balance = balance - %s
                WHERE account_id = %s
            """, (amount, account_id))

            cur.execute("""
                INSERT INTO transactions
                    (account_id, transaction_type, amount)
                VALUES (%s, 'WITHDRAW', %s)
            """, (account_id, amount))

    print("Withdrawal successful!")


def check_balance():
    account = input("Account number: ").strip()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.full_name, a.account_number, a.balance
                FROM accounts a
                JOIN customers c
                    ON a.customer_id = c.customer_id
                WHERE a.account_number = %s
            """, (account,))

            row = cur.fetchone()

    if row:
        print("Customer:", row[0])
        print("Account:", row[1])
        print("Balance: Rs.", row[2])
    else:
        print("Account not found.")


def transaction_history():
    account = input("Account number: ").strip()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT t.transaction_type,
                       t.amount,
                       t.transaction_date
                FROM transactions t
                JOIN accounts a
                    ON t.account_id = a.account_id
                WHERE a.account_number = %s
                ORDER BY t.transaction_date DESC
            """, (account,))

            rows = cur.fetchall()

    if not rows:
        print("No transactions found.")

    for transaction_type, amount, date in rows:
        print(transaction_type, "| Rs.", amount, "|", date)


def main():
    while True:
        print("\n===== BANK MANAGEMENT SYSTEM =====")
        print("1. Create Account")
        print("2. Deposit Money")
        print("3. Withdraw Money")
        print("4. Check Balance")
        print("5. Transaction History")
        print("6. Exit")

        choice = input("Enter choice: ").strip()

        try:
            if choice == "1":
                create_account()
            elif choice == "2":
                deposit()
            elif choice == "3":
                withdraw()
            elif choice == "4":
                check_balance()
            elif choice == "5":
                transaction_history()
            elif choice == "6":
                print("Program closed.")
                break
            else:
                print("Invalid choice.")

        except Exception as e:
            print("Operation failed:", e)


if __name__ == "__main__":
    main()
