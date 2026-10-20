
import tkinter as tk
from tkinter import ttk, messagebox
from decimal import Decimal, InvalidOperation
from database import get_connection
import secrets


# ---------------- WINDOW ----------------

root = tk.Tk()
root.title("Bank Management System")
root.geometry("1100x720")
root.minsize(900, 600)

BG = "#f1f5f9"
NAVY = "#14213d"
BLUE = "#2563eb"
GREEN = "#15803d"
RED = "#dc2626"

root.configure(bg=BG)

style = ttk.Style()
style.theme_use("clam")
style.configure("TNotebook", background=BG, borderwidth=0)
style.configure("TNotebook.Tab", padding=(16, 10), font=("Arial", 10, "bold"))
style.configure("Treeview", rowheight=28, font=("Arial", 10))
style.configure("Treeview.Heading", font=("Arial", 10, "bold"))


def db_error(error):
    messagebox.showerror("Database Error", str(error))


def amount_value(value):
    try:
        amount = Decimal(value.strip())
        if not amount.is_finite() or amount <= 0:
            raise ValueError("Amount must be greater than zero.")
        if amount.as_tuple().exponent < -2:
            raise ValueError("Use a maximum of two decimal places.")
        return amount
    except (InvalidOperation, ValueError) as e:
        messagebox.showerror("Invalid Amount", str(e))
        return None


def get_account_number():
    return str(secrets.randbelow(9000000000) + 1000000000)


# ---------------- HEADER ----------------

header = tk.Frame(root, bg=NAVY, height=100)
header.pack(fill="x")
header.pack_propagate(False)

tk.Label(
    header,
    text="BANK MANAGEMENT SYSTEM",
    font=("Arial", 23, "bold"),
    bg=NAVY,
    fg="white"
).pack(pady=(18, 4))

tk.Label(
    header,
    text="Customer Accounts | Deposits | Withdrawals | Transactions",
    font=("Arial", 10),
    bg=NAVY,
    fg="#cbd5e1"
).pack()


# ---------------- MAIN TABS ----------------

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=18, pady=18)


def create_tab(title):
    frame = tk.Frame(notebook, bg=BG)
    notebook.add(frame, text=title)
    return frame


def make_entry(parent, label, row, default=""):
    tk.Label(
        parent, text=label, bg=BG,
        font=("Arial", 11)
    ).grid(row=row, column=0, sticky="w", padx=12, pady=10)

    entry = ttk.Entry(parent, width=36, font=("Arial", 11))
    entry.grid(row=row, column=1, sticky="ew", padx=12, pady=10)

    if default:
        entry.insert(0, default)

    return entry


def make_button(parent, text, command, color=BLUE):
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=color,
        fg="white",
        activebackground=color,
        activeforeground="white",
        font=("Arial", 10, "bold"),
        relief="flat",
        cursor="hand2",
        padx=14,
        pady=9
    )


def make_table(parent, columns, headings):
    container = tk.Frame(parent, bg=BG)
    container.pack(fill="both", expand=True, padx=15, pady=12)

    tree = ttk.Treeview(
        container, columns=columns, show="headings"
    )

    for column, heading in zip(columns, headings):
        tree.heading(column, text=heading)
        tree.column(column, width=150, anchor="center")

    scrollbar = ttk.Scrollbar(
        container, orient="vertical", command=tree.yview
    )
    tree.configure(yscrollcommand=scrollbar.set)

    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    return tree


# ---------------- CREATE ACCOUNT ----------------

tab_create = create_tab("Create Account")

tk.Label(
    tab_create, text="Open New Bank Account",
    font=("Arial", 18, "bold"), bg=BG, fg=NAVY
).pack(pady=20)

form = tk.Frame(tab_create, bg=BG)
form.pack(pady=10)

name_entry = make_entry(form, "Full Name", 0)
phone_entry = make_entry(form, "Phone Number", 1)
email_entry = make_entry(form, "Email", 2)
address_entry = make_entry(form, "Address", 3)


def create_account():
    name = name_entry.get().strip()
    phone = phone_entry.get().strip()
    email = email_entry.get().strip()
    address = address_entry.get().strip()

    if not name or not phone:
        messagebox.showwarning(
            "Required Fields", "Name and phone are required."
        )
        return

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
                account_number = get_account_number()

                cur.execute("""
                    INSERT INTO accounts
                    (customer_id, account_number, balance)
                    VALUES (%s, %s, 0.00)
                """, (customer_id, account_number))

        messagebox.showinfo(
            "Account Created",
            f"Customer: {name}\n"
            f"Account Number: {account_number}\n"
            "Opening Balance: Rs. 0.00"
        )

        for entry in (
            name_entry, phone_entry, email_entry, address_entry
        ):
            entry.delete(0, tk.END)

        refresh_customers()

    except Exception as e:
        db_error(e)


make_button(
    form, "Create Account", create_account, GREEN
).grid(row=4, column=1, pady=20, sticky="w")


# ---------------- DEPOSIT / WITHDRAW ----------------

tab_money = create_tab("Deposit / Withdraw")

tk.Label(
    tab_money, text="Account Transactions",
    font=("Arial", 18, "bold"), bg=BG, fg=NAVY
).pack(pady=22)

money_form = tk.Frame(tab_money, bg=BG)
money_form.pack(pady=15)

account_entry = make_entry(
    money_form, "Account Number", 0
)
amount_entry = make_entry(
    money_form, "Amount (Rs.)", 1
)


def perform_transaction(transaction_type):
    account = account_entry.get().strip()
    amount = amount_value(amount_entry.get())

    if not account or amount is None:
        if not account:
            messagebox.showwarning(
                "Required", "Enter an account number."
            )
        return

    try:
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
                    messagebox.showerror(
                        "Not Found", "Account does not exist."
                    )
                    return

                account_id, balance = row

                if transaction_type == "WITHDRAW":
                    if balance < amount:
                        messagebox.showerror(
                            "Insufficient Balance",
                            f"Available balance: Rs. {balance}"
                        )
                        return

                    cur.execute("""
                        UPDATE accounts
                        SET balance = balance - %s
                        WHERE account_id = %s
                    """, (amount, account_id))

                else:
                    cur.execute("""
                        UPDATE accounts
                        SET balance = balance + %s
                        WHERE account_id = %s
                    """, (amount, account_id))

                cur.execute("""
                    INSERT INTO transactions
                    (account_id, transaction_type, amount)
                    VALUES (%s, %s, %s)
                """, (account_id, transaction_type, amount))

                cur.execute("""
                    SELECT balance FROM accounts
                    WHERE account_id = %s
                """, (account_id,))
                new_balance = cur.fetchone()[0]

        messagebox.showinfo(
            "Success",
            f"{transaction_type.title()} successful!\n"
            f"Amount: Rs. {amount}\n"
            f"New Balance: Rs. {new_balance}"
        )

        amount_entry.delete(0, tk.END)
        refresh_customers()

    except Exception as e:
        db_error(e)


money_buttons = tk.Frame(tab_money, bg=BG)
money_buttons.pack(pady=15)

make_button(
    money_buttons,
    "Deposit Money",
    lambda: perform_transaction("DEPOSIT"),
    GREEN
).pack(side="left", padx=10)

make_button(
    money_buttons,
    "Withdraw Money",
    lambda: perform_transaction("WITHDRAW"),
    RED
).pack(side="left", padx=10)


# ---------------- BALANCE CHECK ----------------

tab_balance = create_tab("Check Balance")

tk.Label(
    tab_balance, text="Check Account Balance",
    font=("Arial", 18, "bold"), bg=BG, fg=NAVY
).pack(pady=25)

balance_form = tk.Frame(tab_balance, bg=BG)
balance_form.pack(pady=10)

balance_entry = make_entry(
    balance_form, "Account Number", 0
)

balance_result = tk.Label(
    tab_balance,
    text="Enter an account number to view details",
    font=("Arial", 13),
    bg=BG, fg=NAVY,
    justify="left"
)
balance_result.pack(pady=30)


def check_balance():
    account = balance_entry.get().strip()

    if not account:
        messagebox.showwarning(
            "Required", "Enter an account number."
        )
        return

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT c.full_name, c.phone,
                           a.account_number, a.balance
                    FROM accounts a
                    JOIN customers c
                      ON a.customer_id = c.customer_id
                    WHERE a.account_number = %s
                """, (account,))

                row = cur.fetchone()

        if row:
            balance_result.config(
                text=f"Customer Name: {row[0]}\n"
                     f"Phone: {row[1]}\n"
                     f"Account Number: {row[2]}\n"
                     f"Available Balance: Rs. {row[3]}"
            )
        else:
            balance_result.config(text="Account not found.")

    except Exception as e:
        db_error(e)


make_button(
    balance_form, "Check Balance", check_balance
).grid(row=0, column=2, padx=12)


# ---------------- CUSTOMER LIST ----------------

tab_customers = create_tab("Customers")

tk.Label(
    tab_customers, text="All Bank Customers",
    font=("Arial", 18, "bold"), bg=BG, fg=NAVY
).pack(pady=15)

customer_tree = make_table(
    tab_customers,
    ("id", "name", "phone", "email", "account", "balance"),
    ("Customer ID", "Full Name", "Phone",
     "Email", "Account Number", "Balance (Rs.)")
)


def refresh_customers():
    for item in customer_tree.get_children():
        customer_tree.delete(item)

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT c.customer_id, c.full_name,
                           c.phone, c.email,
                           a.account_number, a.balance
                    FROM customers c
                    LEFT JOIN accounts a
                      ON c.customer_id = a.customer_id
                    ORDER BY c.customer_id DESC
                """)

                rows = cur.fetchall()

        for row in rows:
            customer_tree.insert("", tk.END, values=row)

    except Exception as e:
        db_error(e)


customer_buttons = tk.Frame(tab_customers, bg=BG)
customer_buttons.pack(pady=8)

make_button(
    customer_buttons, "Refresh Customers", refresh_customers
).pack()


# ---------------- TRANSACTION HISTORY ----------------

tab_history = create_tab("Transaction History")

tk.Label(
    tab_history, text="Transaction History",
    font=("Arial", 18, "bold"), bg=BG, fg=NAVY
).pack(pady=15)

history_form = tk.Frame(tab_history, bg=BG)
history_form.pack(pady=5)

history_entry = make_entry(
    history_form, "Account Number", 0
)

history_tree = make_table(
    tab_history,
    ("id", "type", "amount", "date"),
    ("Transaction ID", "Type", "Amount (Rs.)", "Date")
)


def show_history():
    account = history_entry.get().strip()

    if not account:
        messagebox.showwarning(
            "Required", "Enter an account number."
        )
        return

    for item in history_tree.get_children():
        history_tree.delete(item)

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT t.transaction_id,
                           t.transaction_type,
                           t.amount,
                           t.transaction_date
                    FROM transactions t
                    JOIN accounts a
                      ON t.account_id = a.account_id
                    WHERE a.account_number = %s
                    ORDER BY t.transaction_date DESC
                """, (account,))

                rows = cur.fetchall()

        for row in rows:
            history_tree.insert("", tk.END, values=row)

        if not rows:
            messagebox.showinfo(
                "No Transactions",
                "No transaction records found."
            )

    except Exception as e:
        db_error(e)


make_button(
    history_form, "Show History", show_history
).grid(row=0, column=2, padx=12)


# ---------------- START APPLICATION ----------------

if __name__ == "__main__":
    try:
        # Verify the database connection at startup.
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")

        root.after(200, refresh_customers)
        root.mainloop()

    except Exception as e:
        messagebox.showerror(
            "Connection Error",
            f"Cannot connect to PostgreSQL.\n\n{e}"
        )
        root.destroy()
