from datetime import date, timedelta
import logging
from pathlib import Path
import pytest

from library_debug.library_system import (
    Book,
    BookNotFoundError,
    BookUnavailableError,
    BorrowLimitExceededError,
    InvalidReturnDateError,
    Library,
    LoanNotFoundError,
    Member,
    MemberNotFoundError,
    PremiumMember,
    StudentMember,
    build_parser,
)


@pytest.fixture
def base_date() -> date:
    return date(2026, 11, 1)


@pytest.fixture
def library() -> Library:
    lib = Library(daily_fine_rate=2.0, loan_period_days=14)
    for index in range(1, 7):
        lib.add_book(Book(f"B{index}", f"Book Title {index}", f"Author {index}"))
    lib.add_member(Member("M1", "Standard Member"))
    lib.add_member(Member("M2", "Second Member"))
    lib.add_member(StudentMember("S1", "Student Member"))
    lib.add_member(PremiumMember("P1", "Premium Member"))
    return lib


def test_bug1_borrow_limit_blocks_fourth_book(library: Library, base_date: date) -> None:
    library.borrow_book("M1", "B1", base_date)
    library.borrow_book("M1", "B2", base_date)
    library.borrow_book("M1", "B3", base_date)

    with pytest.raises(BorrowLimitExceededError):
        library.borrow_book("M1", "B4", base_date)


def test_bug2_multiple_late_returns_accumulate_fines(
    library: Library,
    base_date: date,
) -> None:
    library.borrow_book("M1", "B1", base_date)
    fine1 = library.return_book("B1", base_date + timedelta(days=16))

    library.borrow_book("M1", "B2", base_date)
    fine2 = library.return_book("B2", base_date + timedelta(days=17))

    assert fine1 == 4.0
    assert fine2 == 6.0
    assert library.members["M1"].fines == 10.0


def test_bug3_late_fine_counts_only_days_past_due_date(
    library: Library,
    base_date: date,
) -> None:
    library.borrow_book("M1", "B1", base_date)
    fine = library.return_book("B1", base_date + timedelta(days=19))

    assert fine == 10.0
    assert library.members["M1"].fines == 10.0


def test_bug4_returned_book_can_be_borrowed_again(
    library: Library,
    base_date: date,
) -> None:
    library.borrow_book("M1", "B1", base_date)
    library.return_book("B1", base_date + timedelta(days=4))

    assert library.books["B1"].is_borrowed is False

    new_loan = library.borrow_book("M2", "B1", base_date + timedelta(days=5))
    assert new_loan.member_id == "M2"
    assert library.books["B1"].is_borrowed is True


def test_bug5_json_reload_preserves_member_subclasses(
    library: Library,
    tmp_path: Path,
) -> None:
    json_file = tmp_path / "library.json"
    library.save_to_json(json_file)

    loaded = Library.load_from_json(json_file)

    assert isinstance(loaded.members["S1"], StudentMember)
    assert loaded.members["S1"].max_books == 2
    assert isinstance(loaded.members["P1"], PremiumMember)
    assert loaded.members["P1"].max_books == 5


def test_book_that_is_out_cannot_be_borrowed(library: Library, base_date: date) -> None:
    library.borrow_book("M1", "B1", base_date)
    with pytest.raises(BookUnavailableError):
        library.borrow_book("S1", "B1", base_date)


def test_returning_book_on_time_adds_no_fine(library: Library, base_date: date) -> None:
    library.borrow_book("M1", "B1", base_date)
    fine = library.return_book("B1", base_date + timedelta(days=14))
    assert fine == 0.0
    assert library.members["M1"].fines == 0.0


def test_custom_exceptions_for_invalid_operations(
    library: Library,
    base_date: date,
) -> None:
    with pytest.raises(MemberNotFoundError):
        library.borrow_book("UNKNOWN", "B1", base_date)
    with pytest.raises(BookNotFoundError):
        library.borrow_book("M1", "UNKNOWN", base_date)
    with pytest.raises(LoanNotFoundError):
        library.return_book("B1", base_date)

    library.borrow_book("M1", "B1", base_date)
    with pytest.raises(InvalidReturnDateError):
        library.return_book("B1", base_date - timedelta(days=1))


def test_cli_debug_flag_parsing() -> None:
    parser = build_parser()
    assert parser.parse_args([]).debug is False
    assert parser.parse_args(["--debug"]).debug is True
    assert parser.parse_args(["-d"]).debug is True


def test_debug_logging_emits_debug_records(
    library: Library,
    base_date: date,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG, logger="library_debug.library_system"):
        library.borrow_book("M1", "B1", base_date)

    assert any(record.levelno == logging.DEBUG for record in caplog.records)
