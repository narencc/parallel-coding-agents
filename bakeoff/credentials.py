"""Read the project key without printing it or changing the parent shell."""

import os
from dataclasses import dataclass, field

from dotenv import dotenv_values

from .config import ROOT


@dataclass(frozen=True)
class Credentials:
    key: str = field(repr=False)
    source: str


def load_credentials() -> Credentials:
    if "OPENAI_API_KEY" in os.environ:
        key = os.environ["OPENAI_API_KEY"]
        source = "process environment"
    else:
        # An absolute path works even when the command starts in another folder.
        key = dotenv_values(ROOT / ".env", interpolate=False).get("OPENAI_API_KEY") or ""
        source = "project .env file"
    key = key.strip()
    if not key or key == "replace_with_your_openai_api_key":
        raise ValueError(
            "OPENAI_API_KEY is missing or still a placeholder. Set it in the project .env "
            "file. An exported environment value takes precedence, even if empty."
        )
    return Credentials(key=key, source=source)
