from collections.abc import Callable, Iterator
from functools import wraps
import logging
from pathlib import Path
import time
import tracemalloc
from types import TracebackType
from typing import ParamSpec, TypeVar


P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger(__name__)


def create_large_file(filepath: str | Path, num_lines: int = 200_000) -> Path:
    path = Path(filepath)
    sample_payload = "python-memory-benchmark-line-data-" * 2
    with path.open("w", encoding="utf-8") as file:
        for index in range(num_lines):
            file.write(f"Line {index}: {sample_payload}\n")
    return path


def read_lines_generator(filepath: str | Path) -> Iterator[str]:
    path = Path(filepath)
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            yield line.rstrip("\n")


def read_file_all_at_once(filepath: str | Path) -> list[str]:
    path = Path(filepath)
    with path.open("r", encoding="utf-8") as file:
        return [line.rstrip("\n") for line in file.readlines()]


def compare_memory_usage(filepath: str | Path) -> dict[str, int]:
    tracemalloc.start()
    line_count = 0
    for _ in read_lines_generator(filepath):
        line_count += 1
    _, generator_peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    tracemalloc.start()
    all_lines = read_file_all_at_once(filepath)
    full_line_count = len(all_lines)
    _, full_read_peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "line_count": line_count if line_count == full_line_count else full_line_count,
        "generator_peak_bytes": generator_peak_bytes,
        "full_read_peak_bytes": full_read_peak_bytes,
    }


class Timer:
    def __init__(self, label: str = "Block") -> None:
        self.label: str = label
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.elapsed: float = 0.0

    def __enter__(self) -> "Timer":
        self.start_time = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.end_time = time.perf_counter()
        self.elapsed = self.end_time - self.start_time


def retry_three_times(func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        for attempt in range(1, 4):
            try:
                return func(*args, **kwargs)
            except Exception:
                if attempt == 3:
                    raise
        raise RuntimeError("Retry loop exited unexpectedly.")

    return wrapper


def log_execution_time(func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start
            func_name = getattr(func, "__name__", repr(func))
            logger.info("%s took %.6f seconds", func_name, elapsed)

    return wrapper


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

    temp_file = Path("huge_temp_file.txt")
    try:
        create_large_file(temp_file, num_lines=200_000)
        stats = compare_memory_usage(temp_file)
        print(f"Lines read: {stats['line_count']}")
        print(f"Generator peak memory: {stats['generator_peak_bytes'] / 1024:.2f} KB")
        print(f"Full read peak memory: {stats['full_read_peak_bytes'] / (1024 * 1024):.2f} MB")
    finally:
        temp_file.unlink(missing_ok=True)

    with Timer("Sample sleep") as timer:
        time.sleep(0.05)
    print(f"{timer.label} took {timer.elapsed:.6f} seconds")

    attempts = 0

    @retry_three_times
    def flaky_operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("Temporary failure")
        return "Connected on attempt 3"

    print(flaky_operation())

    @log_execution_time
    def sample_work() -> str:
        time.sleep(0.02)
        return "Done"

    print(sample_work())


if __name__ == "__main__":
    main()
