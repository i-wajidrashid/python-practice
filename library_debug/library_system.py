import argparse
from datetime import date, timedelta
import json
import logging
from pathlib import Path
import tempfile


logger = logging.getLogger(__name__)


class LibraryError(Exception):
    pass


class BookNotFoundError(LibraryError):
    pass


class MemberNotFoundError(LibraryError):
    pass


class BookUnavailableError(LibraryError):
    pass


class BorrowLimitExceededError(LibraryError):
    pass


class LoanNotFoundError(LibraryError):
    pass


class InvalidReturnDateError(LibraryError):
    pass


class Book:
    def __init__(self, book_id: str, title: str, author: str, is_borrowed: bool = False):
        self.book_id = book_id
        self.title = title
        self.author = author
        self.is_borrowed = is_borrowed

    def to_dict(self) -> dict:
        return {
            "book_id": self.book_id,
            "title": self.title,
            "author": self.author,
            "is_borrowed": self.is_borrowed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Book":
        return cls(
            book_id=data["book_id"],
            title=data["title"],
            author=data["author"],
            is_borrowed=data.get("is_borrowed", False),
        )


class Member:
    max_books = 3

    def __init__(self, member_id: str, name: str, fines: float = 0.0):
        self.member_id = member_id
        self.name = name
        self.fines = float(fines)

    def add_fine(self, amount: float) -> None:
        logger.debug(
            "Adding fine %.2f to member %s (current=%.2f)",
            amount,
            self.member_id,
            self.fines,
        )
        if amount < 0:
            raise ValueError("Fine amount cannot be negative.")
        self.fines += float(amount)
        logger.debug("Member %s new total fines=%.2f", self.member_id, self.fines)

    def to_dict(self) -> dict:
        return {
            "member_id": self.member_id,
            "name": self.name,
            "fines": self.fines,
            "member_type": self.__class__.__name__,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Member":
        logger.debug("Deserializing member data: %s", data)
        member_types = {
            "Member": Member,
            "StudentMember": StudentMember,
            "PremiumMember": PremiumMember,
        }
        target_cls = member_types.get(data.get("member_type", "Member"), Member)
        return target_cls(
            member_id=data["member_id"],
            name=data["name"],
            fines=data.get("fines", 0.0),
        )


class StudentMember(Member):
    max_books = 2


class PremiumMember(Member):
    max_books = 5


class Loan:
    def __init__(
        self,
        book_id: str,
        member_id: str,
        borrow_date: date,
        due_date: date,
        return_date: date | None = None,
    ):
        self.book_id = book_id
        self.member_id = member_id
        self.borrow_date = borrow_date
        self.due_date = due_date
        self.return_date = return_date

    @property
    def is_active(self) -> bool:
        return self.return_date is None

    def days_overdue(self, reference_date: date | None = None) -> int:
        check_date = self.return_date or reference_date
        logger.debug(
            "Calculating overdue days: check_date=%s, due_date=%s",
            check_date,
            self.due_date,
        )
        if check_date is None or check_date <= self.due_date:
            return 0
        return (check_date - self.due_date).days

    def to_dict(self) -> dict:
        return {
            "book_id": self.book_id,
            "member_id": self.member_id,
            "borrow_date": self.borrow_date.isoformat(),
            "due_date": self.due_date.isoformat(),
            "return_date": self.return_date.isoformat() if self.return_date else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Loan":
        return cls(
            book_id=data["book_id"],
            member_id=data["member_id"],
            borrow_date=date.fromisoformat(data["borrow_date"]),
            due_date=date.fromisoformat(data["due_date"]),
            return_date=(
                date.fromisoformat(data["return_date"])
                if data.get("return_date")
                else None
            ),
        )


class Library:
    def __init__(self, daily_fine_rate: float = 2.0, loan_period_days: int = 14):
        self.daily_fine_rate = float(daily_fine_rate)
        self.loan_period_days = int(loan_period_days)
        self.books: dict[str, Book] = {}
        self.members: dict[str, Member] = {}
        self.loans: list[Loan] = []

    def add_book(self, book: Book) -> None:
        self.books[book.book_id] = book

    def add_member(self, member: Member) -> None:
        self.members[member.member_id] = member

    def get_active_loans_for_member(self, member_id: str) -> list[Loan]:
        return [
            loan
            for loan in self.loans
            if loan.member_id == member_id and loan.is_active
        ]

    def get_active_loan_for_book(self, book_id: str) -> Loan | None:
        for loan in self.loans:
            if loan.book_id == book_id and loan.is_active:
                return loan
        return None

    def borrow_book(
        self,
        member_id: str,
        book_id: str,
        borrow_date: date | None = None,
    ) -> Loan:
        logger.debug("borrow_book called: member_id=%s, book_id=%s", member_id, book_id)
        if member_id not in self.members:
            logger.warning("Borrow failed: member %s not found", member_id)
            raise MemberNotFoundError(f"Member {member_id} not found.")
        if book_id not in self.books:
            logger.warning("Borrow failed: book %s not found", book_id)
            raise BookNotFoundError(f"Book {book_id} not found.")

        member = self.members[member_id]
        book = self.books[book_id]

        if book.is_borrowed:
            logger.warning("Borrow failed: book %s is already borrowed", book_id)
            raise BookUnavailableError(f"Book {book_id} is currently borrowed.")

        active_loans = self.get_active_loans_for_member(member_id)
        logger.debug(
            "Member %s active loans=%d, max=%d",
            member_id,
            len(active_loans),
            member.max_books,
        )
        if len(active_loans) >= member.max_books:
            logger.warning("Borrow failed: member %s exceeded limit", member_id)
            raise BorrowLimitExceededError(
                f"Member {member_id} reached limit of {member.max_books} books."
            )

        actual_borrow_date = borrow_date or date.today()
        due_date = actual_borrow_date + timedelta(days=self.loan_period_days)

        book.is_borrowed = True
        loan = Loan(
            book_id=book_id,
            member_id=member_id,
            borrow_date=actual_borrow_date,
            due_date=due_date,
        )
        self.loans.append(loan)
        logger.debug("Created loan for book %s due %s", book_id, due_date)
        return loan

    def return_book(
        self,
        book_id: str,
        return_date: date | None = None,
    ) -> float:
        logger.debug("return_book called: book_id=%s, return_date=%s", book_id, return_date)
        if book_id not in self.books:
            logger.warning("Return failed: book %s not found", book_id)
            raise BookNotFoundError(f"Book {book_id} not found.")

        loan = self.get_active_loan_for_book(book_id)
        if loan is None:
            logger.warning("Return failed: no active loan for book %s", book_id)
            raise LoanNotFoundError(f"No active loan found for book {book_id}.")

        actual_return_date = return_date or date.today()
        if actual_return_date < loan.borrow_date:
            raise InvalidReturnDateError("Return date cannot be earlier than borrow date.")

        loan.return_date = actual_return_date
        self.books[book_id].is_borrowed = False

        overdue_days = loan.days_overdue()
        fine = 0.0
        if overdue_days > 0:
            fine = overdue_days * self.daily_fine_rate
            self.members[loan.member_id].add_fine(fine)

        logger.debug("return_book finished: overdue_days=%d, fine=%.2f", overdue_days, fine)
        return fine

    def to_dict(self) -> dict:
        return {
            "daily_fine_rate": self.daily_fine_rate,
            "loan_period_days": self.loan_period_days,
            "books": [book.to_dict() for book in self.books.values()],
            "members": [member.to_dict() for member in self.members.values()],
            "loans": [loan.to_dict() for loan in self.loans],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Library":
        library = cls(
            daily_fine_rate=data.get("daily_fine_rate", 2.0),
            loan_period_days=data.get("loan_period_days", 14),
        )
        for book_data in data.get("books", []):
            library.add_book(Book.from_dict(book_data))
        for member_data in data.get("members", []):
            library.add_member(Member.from_dict(member_data))
        for loan_data in data.get("loans", []):
            library.loans.append(Loan.from_dict(loan_data))
        return library

    def save_to_json(self, filepath: str | Path) -> None:
        logger.debug("Saving library to %s", filepath)
        path = Path(filepath)
        with path.open("w", encoding="utf-8") as file:
            json.dump(self.to_dict(), file, indent=2)

    @classmethod
    def load_from_json(cls, filepath: str | Path) -> "Library":
        logger.debug("Loading library from %s", filepath)
        path = Path(filepath)
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return cls.from_dict(data)


def configure_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
    else:
        root_logger.setLevel(level)
    logger.setLevel(level)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run library system verification scenarios with configurable logging."
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable DEBUG-level logging output.",
    )
    return parser


def run_demo_scenarios() -> None:
    base = date(2026, 11, 1)

    lib1 = Library()
    for i in range(1, 5):
        lib1.add_book(Book(f"B{i}", f"Book {i}", f"Author {i}"))
    lib1.add_member(Member("M1", "Alice"))
    lib1.borrow_book("M1", "B1", base)
    lib1.borrow_book("M1", "B2", base)
    lib1.borrow_book("M1", "B3", base)
    try:
        lib1.borrow_book("M1", "B4", base)
        logger.error("[Scenario 1] FAIL: M1 borrowed 4 books.")
    except BorrowLimitExceededError:
        logger.info("[Scenario 1] PASS: M1 blocked at 4th book.")

    lib2 = Library()
    lib2.add_book(Book("B1", "Book 1", "Author 1"))
    lib2.add_book(Book("B2", "Book 2", "Author 2"))
    lib2.add_member(Member("M1", "Alice"))
    lib2.borrow_book("M1", "B1", base)
    fine1 = lib2.return_book("B1", base + timedelta(days=16))
    lib2.borrow_book("M1", "B2", base)
    fine2 = lib2.return_book("B2", base + timedelta(days=17))
    expected_total = fine1 + fine2
    actual_total = lib2.members["M1"].fines
    if actual_total == expected_total:
        logger.info("[Scenario 2] PASS: Total fines accumulated to %.2f.", actual_total)
    else:
        logger.error(
            "[Scenario 2] FAIL: member.fines=%.2f (expected %.2f).",
            actual_total,
            expected_total,
        )

    lib3 = Library(daily_fine_rate=2.0, loan_period_days=14)
    lib3.add_book(Book("B1", "Book 1", "Author 1"))
    lib3.add_member(Member("M1", "Alice"))
    lib3.borrow_book("M1", "B1", base)
    fine3 = lib3.return_book("B1", base + timedelta(days=19))
    if fine3 == 10.0:
        logger.info("[Scenario 3] PASS: 5-day late fine is %.2f.", fine3)
    else:
        logger.error("[Scenario 3] FAIL: 5-day late fine is %.2f (expected 10.00).", fine3)

    lib4 = Library()
    lib4.add_book(Book("B1", "Book 1", "Author 1"))
    lib4.add_member(Member("M1", "Alice"))
    lib4.add_member(Member("M2", "Bob"))
    lib4.borrow_book("M1", "B1", base)
    lib4.return_book("B1", base + timedelta(days=4))
    try:
        lib4.borrow_book("M2", "B1", base + timedelta(days=5))
        logger.info("[Scenario 4] PASS: Returned book B1 was borrowed again by M2.")
    except BookUnavailableError:
        logger.error("[Scenario 4] FAIL: Returned book B1 raised BookUnavailableError.")

    lib5 = Library()
    lib5.add_member(PremiumMember("P1", "Charlie"))
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "library.json"
        lib5.save_to_json(filepath)
        loaded = Library.load_from_json(filepath)
    reloaded = loaded.members["P1"]
    if isinstance(reloaded, PremiumMember) and reloaded.max_books == 5:
        logger.info("[Scenario 5] PASS: Reloaded P1 as PremiumMember (max_books=5).")
    else:
        logger.error(
            "[Scenario 5] FAIL: Reloaded P1 as %s (max_books=%d).",
            type(reloaded).__name__,
            reloaded.max_books,
        )


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    configure_logging(debug=args.debug)
    logger.debug("DEBUG logging enabled via CLI option.")
    run_demo_scenarios()


if __name__ == "__main__":
    main()
