from __future__ import annotations

from pathlib import Path


ENCODINGS = ("utf-8-sig", "utf-8", "utf-16", "gb18030", "cp936", "latin-1")


def read_text_guess(path: Path) -> str:
    data = path.read_bytes()
    last_error: UnicodeDecodeError | None = None
    for encoding in ENCODINGS:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error:
        raise last_error
    return ""
