from dataclasses import dataclass
from datetime import date, timedelta
import json
from pathlib import Path
from typing import Any, ClassVar
import pytest


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


@dataclass
class Book:
    book_id: str
    title: str
    author: str
    is_borrowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "book_id": self.book_id,
            "title": self.title,
            "author": self.author,
            "is_borrowed": self.is_borrowed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Book":
        return cls(
            book_id=str(data["book_id"]),
            title=str(data["title"]),
            author=str(data["author"]),
            is_borrowed=bool(data.get("is_borrowed", False)),
        )


@dataclass
class Member:
    member_id: str
    name: str
    fines: float = 0.0
    max_books: ClassVar[int] = 3

    def __post_init__(self) -> None:
        self.fines = float(self.fines)

    def add_fine(self, amount: float) -> None:
        if amount < 0:
            raise ValueError("Fine amount cannot be negative.")
        self.fines += float(amount)

    def to_dict(self) -> dict[str, Any]:
        return {
            "member_id": self.member_id,
            "name": self.name,
            "fines": self.fines,
            "member_type": self.__class__.__name__,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Member":
        member_types: dict[str, type[Member]] = {
            "Member": Member,
            "StudentMember": StudentMember,
            "PremiumMember": PremiumMember,
        }
        target_cls = member_types.get(str(data.get("member_type", "Member")), Member)
        return target_cls(
            member_id=str(data["member_id"]),
            name=str(data["name"]),
            fines=float(data.get("fines", 0.0)),
        )


@dataclass
class StudentMember(Member):
    max_books: ClassVar[int] = 2


@dataclass
class PremiumMember(Member):
    max_books: ClassVar[int] = 5


class Loan:
    def __init__(
        self,
        book_id: str,
        member_id: str,
        borrow_date: date,
        due_date: date,
        return_date: date | None = None,
    ) -> None:
        self.book_id: str = book_id
        self.member_id: str = member_id
        self.borrow_date: date = borrow_date
        self.due_date: date = due_date
        self.return_date: date | None = return_date

    @property
    def is_active(self) -> bool:
        return self.return_date is None

    def days_overdue(self, reference_date: date | None = None) -> int:
        check_date = self.return_date or reference_date
        if check_date is None or check_date <= self.due_date:
            return 0
        return (check_date - self.due_date).days

    def to_dict(self) -> dict[str, Any]:
        return {
            "book_id": self.book_id,
            "member_id": self.member_id,
            "borrow_date": self.borrow_date.isoformat(),
            "due_date": self.due_date.isoformat(),
            "return_date": self.return_date.isoformat() if self.return_date else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Loan":
        raw_return_date = data.get("return_date")
        return cls(
            book_id=str(data["book_id"]),
            member_id=str(data["member_id"]),
            borrow_date=date.fromisoformat(str(data["borrow_date"])),
            due_date=date.fromisoformat(str(data["due_date"])),
            return_date=(
                date.fromisoformat(str(raw_return_date))
                if raw_return_date
                else None
            ),
        )


class Library:
    def __init__(self, daily_fine_rate: float = 2.0, loan_period_days: int = 14) -> None:
        self.daily_fine_rate: float = float(daily_fine_rate)
        self.loan_period_days: int = int(loan_period_days)
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
        if member_id not in self.members:
            raise MemberNotFoundError(f"Member {member_id} not found.")
        if book_id not in self.books:
            raise BookNotFoundError(f"Book {book_id} not found.")

        member = self.members[member_id]
        book = self.books[book_id]

        if book.is_borrowed:
            raise BookUnavailableError(f"Book {book_id} is currently borrowed.")

        active_loans = self.get_active_loans_for_member(member_id)
        if len(active_loans) >= member.max_books:
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
        return loan

    def return_book(
        self,
        book_id: str,
        return_date: date | None = None,
    ) -> float:
        if book_id not in self.books:
            raise BookNotFoundError(f"Book {book_id} not found.")

        loan = self.get_active_loan_for_book(book_id)
        if loan is None:
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

        return fine

    def to_dict(self) -> dict[str, Any]:
        return {
            "daily_fine_rate": self.daily_fine_rate,
            "loan_period_days": self.loan_period_days,
            "books": [book.to_dict() for book in self.books.values()],
            "members": [member.to_dict() for member in self.members.values()],
            "loans": [loan.to_dict() for loan in self.loans],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Library":
        library = cls(
            daily_fine_rate=float(data.get("daily_fine_rate", 2.0)),
            loan_period_days=int(data.get("loan_period_days", 14)),
        )
        for book_data in data.get("books", []):
            library.add_book(Book.from_dict(book_data))
        for member_data in data.get("members", []):
            library.add_member(Member.from_dict(member_data))
        for loan_data in data.get("loans", []):
            library.loans.append(Loan.from_dict(loan_data))
        return library

    def save_to_json(self, filepath: str | Path) -> None:
        path = Path(filepath)
        with path.open("w", encoding="utf-8") as file:
            json.dump(self.to_dict(), file, indent=2)

    @classmethod
    def load_from_json(cls, filepath: str | Path) -> "Library":
        path = Path(filepath)
        with path.open("r", encoding="utf-8") as file:
            data: dict[str, Any] = json.load(file)
        return cls.from_dict(data)


@pytest.fixture
def base_date() -> date:
    return date(2026, 11, 1)


@pytest.fixture
def library() -> Library:
    lib = Library(daily_fine_rate=2.0, loan_period_days=14)
    for index in range(1, 7):
        lib.add_book(Book(f"B{index}", f"Book Title {index}", f"Author {index}"))
    lib.add_member(Member("M1", "Standard Member"))
    lib.add_member(StudentMember("S1", "Student Member"))
    lib.add_member(PremiumMember("P1", "Premium Member"))
    return lib


def test_member_can_borrow_at_most_three_books(library: Library, base_date: date) -> None:
    library.borrow_book("M1", "B1", base_date)
    library.borrow_book("M1", "B2", base_date)
    library.borrow_book("M1", "B3", base_date)

    assert len(library.get_active_loans_for_member("M1")) == 3

    with pytest.raises(BorrowLimitExceededError):
        library.borrow_book("M1", "B4", base_date)


def test_book_that_is_out_cannot_be_borrowed(library: Library, base_date: date) -> None:
    library.borrow_book("M1", "B1", base_date)

    assert library.books["B1"].is_borrowed is True

    with pytest.raises(BookUnavailableError):
        library.borrow_book("S1", "B1", base_date)


def test_returning_book_on_time_adds_no_fine(library: Library, base_date: date) -> None:
    library.borrow_book("M1", "B1", base_date)
    fine = library.return_book("B1", base_date + timedelta(days=14))

    assert fine == 0.0
    assert library.members["M1"].fines == 0.0
    assert library.books["B1"].is_borrowed is False


def test_returning_book_late_adds_fine(library: Library, base_date: date) -> None:
    library.borrow_book("M1", "B1", base_date)
    late_return_date = base_date + timedelta(days=19)
    fine = library.return_book("B1", late_return_date)

    assert fine == 10.0
    assert library.members["M1"].fines == 10.0
    assert library.books["B1"].is_borrowed is False


def test_inherited_members_have_different_limits(library: Library, base_date: date) -> None:
    library.borrow_book("S1", "B1", base_date)
    library.borrow_book("S1", "B2", base_date)

    with pytest.raises(BorrowLimitExceededError):
        library.borrow_book("S1", "B3", base_date)

    library.return_book("B1", base_date + timedelta(days=1))
    library.return_book("B2", base_date + timedelta(days=1))

    for index in range(1, 6):
        library.borrow_book("P1", f"B{index}", base_date)

    assert len(library.get_active_loans_for_member("P1")) == 5

    with pytest.raises(BorrowLimitExceededError):
        library.borrow_book("P1", "B6", base_date)


def test_custom_exceptions_for_invalid_operations(library: Library, base_date: date) -> None:
    with pytest.raises(MemberNotFoundError):
        library.borrow_book("UNKNOWN", "B1", base_date)

    with pytest.raises(BookNotFoundError):
        library.borrow_book("M1", "UNKNOWN", base_date)

    with pytest.raises(LoanNotFoundError):
        library.return_book("B1", base_date)

    library.borrow_book("M1", "B1", base_date)
    with pytest.raises(InvalidReturnDateError):
        library.return_book("B1", base_date - timedelta(days=1))


def test_save_and_load_library_as_json(
    library: Library,
    base_date: date,
    tmp_path: Path,
) -> None:
    library.borrow_book("M1", "B1", base_date)
    library.return_book("B1", base_date + timedelta(days=17))
    library.borrow_book("P1", "B2", base_date)

    json_file = tmp_path / "library.json"
    library.save_to_json(json_file)

    loaded_library = Library.load_from_json(json_file)

    assert len(loaded_library.books) == 6
    assert loaded_library.books["B1"].is_borrowed is False
    assert loaded_library.books["B2"].is_borrowed is True
    assert loaded_library.members["M1"].fines == 6.0
    assert isinstance(loaded_library.members["S1"], StudentMember)
    assert isinstance(loaded_library.members["P1"], PremiumMember)
    assert len(loaded_library.loans) == 2
    assert loaded_library.get_active_loan_for_book("B2") is not None
