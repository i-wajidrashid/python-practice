from dataclasses import is_dataclass
import logging
from pathlib import Path
import time
import pytest
from features.python_features import (
    Timer,
    compare_memory_usage,
    create_large_file,
    log_execution_time,
    read_lines_generator,
    retry_three_times,
)
from library.library import Book, Member, PremiumMember, StudentMember


def test_book_is_dataclass_with_defaults_and_equality() -> None:
    assert is_dataclass(Book)
    first = Book("B1", "Clean Code", "Robert C. Martin")
    second = Book("B1", "Clean Code", "Robert C. Martin")
    assert first == second
    assert first.is_borrowed is False


def test_member_and_subclasses_are_dataclasses() -> None:
    assert is_dataclass(Member)
    assert is_dataclass(StudentMember)
    assert is_dataclass(PremiumMember)

    regular = Member("M1", "Wajid")
    student = StudentMember("S1", "Ali")
    premium = PremiumMember("P1", "Sara")

    assert regular == Member("M1", "Wajid", 0.0)
    assert regular.max_books == 3
    assert student.max_books == 2
    assert premium.max_books == 5


def test_read_lines_generator_yields_one_line_at_a_time(tmp_path: Path) -> None:
    sample_file = tmp_path / "sample.txt"
    sample_file.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

    gen = read_lines_generator(sample_file)
    assert next(gen) == "alpha"
    assert next(gen) == "beta"
    assert next(gen) == "gamma"

    with pytest.raises(StopIteration):
        next(gen)


def test_generator_uses_less_memory_than_full_read(tmp_path: Path) -> None:
    large_file = create_large_file(tmp_path / "large.txt", num_lines=50_000)
    stats = compare_memory_usage(large_file)

    assert stats["line_count"] == 50_000
    assert stats["generator_peak_bytes"] < stats["full_read_peak_bytes"]


def test_timer_context_manager_measures_elapsed_time() -> None:
    with Timer("sleep_block") as timer:
        time.sleep(0.05)

    assert timer.label == "sleep_block"
    assert timer.elapsed >= 0.04


def test_timer_context_manager_records_time_on_exception() -> None:
    with pytest.raises(ValueError):
        with Timer("failing_block") as timer:
            time.sleep(0.01)
            raise ValueError("boom")

    assert timer.elapsed >= 0.01


def test_retry_decorator_succeeds_on_first_try() -> None:
    calls = 0

    @retry_three_times
    def always_works() -> str:
        nonlocal calls
        calls += 1
        return "success"

    assert always_works() == "success"
    assert calls == 1


def test_retry_decorator_succeeds_on_third_try() -> None:
    calls = 0

    @retry_three_times
    def works_on_third_try() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ValueError("temporary error")
        return "recovered"

    assert works_on_third_try() == "recovered"
    assert calls == 3


def test_retry_decorator_raises_after_three_failures() -> None:
    calls = 0

    @retry_three_times
    def always_fails() -> str:
        nonlocal calls
        calls += 1
        raise RuntimeError("permanent error")

    with pytest.raises(RuntimeError, match="permanent error"):
        always_fails()

    assert calls == 3


def test_log_execution_time_logs_duration_and_returns_value(
    caplog: pytest.LogCaptureFixture,
) -> None:
    @log_execution_time
    def multiply(a: int, b: int) -> int:
        time.sleep(0.01)
        return a * b

    with caplog.at_level(logging.INFO):
        result = multiply(6, 7)

    assert result == 42
    assert "multiply took" in caplog.text
    assert "seconds" in caplog.text
