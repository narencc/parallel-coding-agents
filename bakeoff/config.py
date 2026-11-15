"""Settings, not secrets: one model per independent lane."""

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "sample"
MAX_ROUNDS = 4
MAX_OUTPUT_TOKENS = 4000
TEST_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class Lane:
    name: str
    model: str
    reasoning_effort: str = "low"


LANES = (
    Lane("lane-1", "gpt-6-astra"),
    Lane("lane-2", "gpt-6.1-sol"),
    Lane("lane-3", "gpt-6.1-terra"),
    Lane("lane-4", "gpt-6-luna"),
    Lane("lane-5", "gpt-6-sol"),
)
