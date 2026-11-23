## Library Management System Class Diagram

```mermaid
classDiagram
    class LibraryError
    class BookNotFoundError
    class MemberNotFoundError
    class BookUnavailableError
    class BorrowLimitExceededError
    class LoanNotFoundError
    class InvalidReturnDateError

    LibraryError <|-- BookNotFoundError
    LibraryError <|-- MemberNotFoundError
    LibraryError <|-- BookUnavailableError
    LibraryError <|-- BorrowLimitExceededError
    LibraryError <|-- LoanNotFoundError
    LibraryError <|-- InvalidReturnDateError

    class Book {
        +str book_id
        +str title
        +str author
        +bool is_borrowed
        +to_dict() dict
        +from_dict(data) Book
    }

    class Member {
        +int max_books = 3
        +str member_id
        +str name
        +float fines
        +add_fine(amount) None
        +to_dict() dict
        +from_dict(data) Member
    }

    class StudentMember {
        +int max_books = 2
    }

    class PremiumMember {
        +int max_books = 5
    }

    Member <|-- StudentMember
    Member <|-- PremiumMember

    class Loan {
        +str book_id
        +str member_id
        +date borrow_date
        +date due_date
        +date return_date
        +bool is_active
        +days_overdue(reference_date) int
        +to_dict() dict
        +from_dict(data) Loan
    }

    class Library {
        +float daily_fine_rate
        +int loan_period_days
        +dict books
        +dict members
        +list loans
        +add_book(book) None
        +add_member(member) None
        +get_active_loans_for_member(member_id) list
        +get_active_loan_for_book(book_id) Loan
        +borrow_book(member_id, book_id, borrow_date) Loan
        +return_book(book_id, return_date) float
        +to_dict() dict
        +from_dict(data) Library
        +save_to_json(filepath) None
        +load_from_json(filepath) Library
    }

    Library "1" *-- "*" Book : manages
    Library "1" *-- "*" Member : registers
    Library "1" *-- "*" Loan : tracks
    Loan "*" --> "1" Book : references
    Loan "*" --> "1" Member : belongs to
```# Python Expense Tracker
A command-line expense tracker built with Python using precise `Decimal` arithmetic and pytest verification.
