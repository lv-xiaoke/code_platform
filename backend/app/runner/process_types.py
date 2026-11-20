from dataclasses import dataclass
from typing import TypedDict


@dataclass(frozen=True)
class ProcessBudget:
    wall_seconds: float
    cpu_seconds: float
    memory_mb: int
    output_bytes: int
    max_processes: int = 32


class ProcessResult(TypedDict):
    status: str
    stdout: str
    stderr: str
    exit_code: int | None
    duration_ms: float
