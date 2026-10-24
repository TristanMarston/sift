"""JSON Lines helpers. A JSON string may contain U+2028 and other characters that str.splitlines() treats as line
breaks (real Mercari descriptions do), so lines are read on "\\n" only and written ASCII-escaped: no consumer of our
files, whatever it uses to split lines, can cut a record in half."""
import json
from pathlib import Path


def dumps(obj) -> str:
    """One record as one ASCII-only line (no trailing newline)."""
    return json.dumps(obj, ensure_ascii=True)


def read(path) -> list[str]:
    """The non-empty lines of a .jsonl file, split on "\\n" only. A missing file has no lines."""
    path = Path(path)
    return [line for line in path.read_text(encoding="utf-8").split("\n") if line.strip()] if path.exists() else []


def load(path) -> list[dict]:
    return [json.loads(line) for line in read(path)]
