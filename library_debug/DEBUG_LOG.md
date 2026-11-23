# Library System Debugging Log

## Bug 1: Standard Member Allowed to Borrow 4 Books
- **Tool Used:** PyCharm Debugger
- **Symptom:** Scenario 1 allowed `M1` (standard member with `max_books = 3`) to borrow a 4th book (`B4`) instead of raising `BorrowLimitExceededError`.
- **Theory:** The borrow limit comparison in `Library.borrow_book` had an off-by-one operator error (`>` instead of `>=`).
- **How I Proved It:** Placed a breakpoint inside `Library.borrow_book` during the 4th borrow. PyCharm's Variables panel showed `len(active_loans) = 3` and `member.max_books = 3`. Stepping over (`F8`) skipped `raise BorrowLimitExceededError` because `3 > 3` evaluated to `False`.
- **Fix:** Changed `if len(active_loans) > member.max_books:` to `if len(active_loans) >= member.max_books:`.

## Bug 2: Multiple Late Fines Overwrite Previous Fines
- **Tool Used:** PyCharm Debugger
- **Symptom:** In Scenario 2, after two separate late returns, `member.fines` equaled only the second fine instead of the sum of both fines.
- **Theory:** `Member.add_fine` was overwriting `self.fines` instead of accumulating it.
- **How I Proved It:** Stepped into `Member.add_fine` (`F7`) during the second late return. Variables showed `self.fines` holding the first fine before the assignment, and stepping over (`F8`) replaced `self.fines` with `amount` instead of adding to it.
- **Fix:** Changed `self.fines = float(amount)` to `self.fines += float(amount)`.

## Bug 3: Late Fine Calculated From Borrow Date Instead of Due Date
- **Tool Used:** PyCharm Debugger
- **Symptom:** In Scenario 3, returning a book 5 days late on a 14-day loan at `$2.00/day` charged `$38.00` instead of `$10.00`.
- **Theory:** `Loan.days_overdue` was subtracting `borrow_date` instead of `due_date`, counting all 19 days of the loan instead of the 5 overdue days.
- **How I Proved It:** Stepped into `Loan.days_overdue` (`F7`). Variables showed `check_date = 2026-11-20`, `self.due_date = 2026-11-15`, and `self.borrow_date = 2026-11-01`. Stepping over returned `19` (`check_date - self.borrow_date`) instead of `5`.
- **Fix:** Changed `return (check_date - self.borrow_date).days` to `return (check_date - self.due_date).days`.

## Bug 4: Returned Book Stays Marked as Borrowed
- **Tool Used:** PyCharm Debugger
- **Symptom:** In Scenario 4, after `M1` returned `B1`, `M2` attempting to borrow `B1` raised `BookUnavailableError`.
- **Theory:** `Library.return_book` was not resetting `book.is_borrowed` to `False`.
- **How I Proved It:** Stepped through `Library.return_book` (`F8`). On `self.books[book_id].is_borrowed = loan.is_active`, `loan.return_date` was still `None`, so `loan.is_active` evaluated to `True`, keeping `book.is_borrowed` set to `True` even after `loan.return_date` was updated on the next line.
- **Fix:** Updated `loan.return_date = actual_return_date` first and explicitly set `self.books[book_id].is_borrowed = False`.

## Bug 5: JSON Reload Loses Member Subclass (`PremiumMember` / `StudentMember`)
- **Tool Used:** Terminal `breakpoint()` (`pdb`) only
- **Symptom:** In Scenario 5, saving a `PremiumMember` (`max_books = 5`) to JSON and reloading returned a plain `Member` (`max_books = 3`).
- **Theory:** `Member.from_dict` was reading the wrong dictionary key for the serialized member class name.
- **How I Proved It:** Inserted `breakpoint()` in `Member.from_dict` and ran the script in the terminal. At the `(Pdb)` prompt, `p data` showed `'member_type': 'PremiumMember'`, while `p data.get("type")` returned `None`. Stepping with `n` and inspecting `p target_cls` confirmed it fell back to `<class '__main__.Member'>`.
- **Fix:** Changed `data.get("type", "Member")` to `data.get("member_type", "Member")` and removed the `breakpoint()` call.
