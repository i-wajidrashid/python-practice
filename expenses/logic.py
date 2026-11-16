import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation

def validate_amount(amount_str):
    try:
        dec = Decimal(str(amount_str))
        if dec <= 0:
            raise ValueError("Amount must be greater than zero.")
        return dec
    except (InvalidOperation, TypeError):
        raise ValueError("Invalid amount format.")

def validate_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Invalid date format. Use YYYY-MM-DD.")

def add_expense(expenses, amount, category, date_str, note=""):
    dec_amount = validate_amount(amount)
    valid_date = validate_date(date_str)
    
    expense = {
        "amount": dec_amount,
        "category": category.strip(),
        "date": valid_date.isoformat(),
        "note": note.strip()
    }
    expenses.append(expense)
    return expenses

def save_to_csv(expenses, filepath="expenses.csv"):
    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["amount", "category", "date", "note"])
        for exp in expenses:
            writer.writerow([str(exp["amount"]), exp["category"], exp["date"], exp["note"]])

def load_from_csv(filepath="expenses.csv"):
    expenses = []
    try:
        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                expenses.append({
                    "amount": Decimal(row["amount"]),
                    "category": row["category"],
                    "date": row["date"],
                    "note": row["note"]
                })
    except FileNotFoundError:
        pass
    return expenses

def get_monthly_total(expenses, year, month):
    total = Decimal("0.00")
    for exp in expenses:
        exp_date = datetime.fromisoformat(exp["date"])
        if exp_date.year == year and exp_date.month == month:
            total += exp["amount"]
    return total

def get_category_totals(expenses, year, month):
    totals = {}
    for exp in expenses:
        exp_date = datetime.fromisoformat(exp["date"])
        if exp_date.year == year and exp_date.month == month:
            cat = exp["category"]
            totals[cat] = totals.get(cat, Decimal("0.00")) + exp["amount"]
    return totals

def export_month_to_csv(expenses, year, month, filepath):
    monthly_expenses = [
        exp for exp in expenses 
        if datetime.fromisoformat(exp["date"]).year == year and datetime.fromisoformat(exp["date"]).month == month
    ]
    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["amount", "category", "date", "note"])
        for exp in monthly_expenses:
            writer.writerow([str(exp["amount"]), exp["category"], exp["date"], exp["note"]])
    return len(monthly_expenses)
