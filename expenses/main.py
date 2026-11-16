import sys
from expenses.logic import (
    add_expense, save_to_csv, load_from_csv, 
    get_monthly_total, get_category_totals, export_month_to_csv
)

def main():
    expenses = load_from_csv()
    
    if len(sys.argv) < 2:
        print("Usage: python3 -m expenses.main [add|total]")
        return

    command = sys.argv[1]
    
    if command == "add":
        if len(sys.argv) < 5:
            print("Usage: python3 -m expenses.main add <amount> <category> <YYYY-MM-DD> [note]")
            return
        try:
            amount, category, date_str = sys.argv[2], sys.argv[3], sys.argv[4]
            note = sys.argv[5] if len(sys.argv) > 5 else ""
            add_expense(expenses, amount, category, date_str, note)
            save_to_csv(expenses)
            print("Expense added successfully!")
        except ValueError as e:
            print(f"Error: {e}")
            
    elif command == "total":
        if len(sys.argv) < 4:
            print("Usage: python3 -m expenses.main total <YYYY> <MM>")
            return
        year, month = int(sys.argv[2]), int(sys.argv[3])
        tot = get_monthly_total(expenses, year, month)
        cats = get_category_totals(expenses, year, month)
        print(f"Total for {year}-{month:02d}: {tot}")
        print("By Category:")
        for cat, amt in cats.items():
            print(f"  - {cat}: {amt}")

if __name__ == "__main__":
    main()
