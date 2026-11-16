import pytest
from decimal import Decimal
from expenses.logic import (
    add_expense, validate_amount, validate_date, 
    get_monthly_total, get_category_totals, export_month_to_csv
)

def test_validate_amount_valid():
    assert validate_amount("45.50") == Decimal("45.50")

def test_validate_amount_negative():
    with pytest.raises(ValueError, match="Amount must be greater than zero."):
        validate_amount("-10.00")

def test_validate_amount_invalid():
    with pytest.raises(ValueError, match="Invalid amount format."):
        validate_amount("abc")

def test_validate_date_valid():
    parsed = validate_date("2026-11-16")
    assert parsed.year == 2026 and parsed.month == 11 and parsed.day == 16

def test_validate_date_invalid():
    with pytest.raises(ValueError, match="Invalid date format."):
        validate_date("16-11-2026")

def test_add_expense_success():
    expenses = []
    add_expense(expenses, "100.00", "Food", "2026-11-01", "Groceries")
    assert len(expenses) == 1
    assert expenses[0]["amount"] == Decimal("100.00")
    assert expenses[0]["category"] == "Food"

def test_monthly_and_category_totals():
    expenses = []
    add_expense(expenses, "50.00", "Food", "2026-11-05")
    add_expense(expenses, "25.00", "Transport", "2026-11-10")
    add_expense(expenses, "200.00", "Food", "2026-10-01")
    
    total_nov = get_monthly_total(expenses, 2026, 11)
    assert total_nov == Decimal("75.00")
    
    cats = get_category_totals(expenses, 2026, 11)
    assert cats["Food"] == Decimal("50.00")
    assert cats["Transport"] == Decimal("25.00")

def test_export_month_to_csv(tmp_path):
    expenses = []
    add_expense(expenses, "60.00", "Utilities", "2026-11-12")
    file_path = tmp_path / "nov_export.csv"
    count = export_month_to_csv(expenses, 2026, 11, str(file_path))
    assert count == 1
    assert file_path.exists()
