from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from string import Template


WINDOWS_RESERVED_NAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}


def sanitize_filename(name: str, fallback: str = "untitled") -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        cleaned = fallback
    if cleaned.casefold() in WINDOWS_RESERVED_NAMES:
        cleaned = f"{cleaned}_"
    return cleaned[:160]


def slug_attachment_name(filename: str, fallback: str = "attachment") -> str:
    stem = sanitize_filename(Path(filename).stem, fallback=fallback)
    suffix = Path(filename).suffix.lower()
    if not suffix or len(suffix) > 12:
        suffix = ".bin"
    return f"{stem}{suffix}"


def short_hash(value: str | bytes, length: int = 8) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8", errors="replace")
    return hashlib.sha256(value).hexdigest()[:length]


def file_identity(path: Path, relative_path: Path) -> str:
    try:
        stat = path.stat()
        raw = f"{relative_path.as_posix()}|{stat.st_size}|{stat.st_mtime_ns}"
    except OSError:
        raw = relative_path.as_posix()
    return short_hash(raw)


def content_hash(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(chunk_size), b""):
                digest.update(chunk)
    except OSError:
        return short_hash(str(path))
    return digest.hexdigest()[:16]


def matches_globs(relative_path: Path, patterns: list[str] | None) -> bool:
    if not patterns:
        return False
    posix = relative_path.as_posix()
    name = relative_path.name
    for pattern in patterns:
        normalized = pattern.strip()
        if not normalized:
            continue
        if fnmatch(posix, normalized) or fnmatch(name, normalized):
            return True
    return False


def frontmatter_lines(
    *,
    title: str,
    source_path: Path,
    converter: str,
    converted_at: str,
    tags: tuple[str, ...],
    warnings: list[str],
    metadata: dict[str, str],
    extra_frontmatter: dict[str, str],
    template: str | None,
) -> str:
    if template:
        fields: dict[str, str] = {
            "title": title,
            "source_path": str(source_path),
            "source_ext": source_path.suffix.lower(),
            "converted_at": converted_at,
            "converter": converter,
            "tags": "\n".join(f"  - {_yaml_string(tag)}" for tag in tags),
            "warnings": "\n".join(f"  - {_yaml_string(w)}" for w in warnings) if warnings else "",
        }
        for key, value in metadata.items():
            fields[f"meta_{key}"] = value
        for key, value in extra_frontmatter.items():
            fields[key] = value
        rendered = Template(template).safe_substitute(fields)
        return "---\n" + rendered.strip("\n") + "\n---"

    lines = [
        "---",
        f"title: {_yaml_string(title)}",
        f"source_path: {_yaml_string(str(source_path))}",
        f"source_ext: {_yaml_string(source_path.suffix.lower())}",
        f"converted_at: {_yaml_string(converted_at)}",
        f"converter: {_yaml_string(converter)}",
    ]
    for key, value in metadata.items():
        lines.append(f"{key}: {_yaml_string(value)}")
    for key, value in extra_frontmatter.items():
        lines.append(f"{key}: {_yaml_string(value)}")
    lines.append("tags:")
    for tag in tags:
        lines.append(f"  - {_yaml_string(tag)}")
    if warnings:
        lines.append("conversion_warnings:")
        for warning in warnings:
            lines.append(f"  - {_yaml_string(warning)}")
    lines.append("---")
    return "\n".join(lines)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _yaml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'



def markdown_table(rows: list[list[object]]) -> str:
    if not rows:
        return ""
    normalized = [[_cell_to_markdown(cell) for cell in row] for row in rows]
    width = max(len(row) for row in normalized)
    padded = [row + [""] * (width - len(row)) for row in normalized]
    header = padded[0]
    separator = ["---"] * width
    body = padded[1:]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in body)
    return "\n".join(lines)


def normalize_extracted_text(text: str) -> str:
    """Clean text extracted from visual-layout formats such as PDF slides."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _remove_long_artifact_tokens(normalized)
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    normalized = re.sub(r"\n\s*-\s*\n", "-", normalized)
    blocks = re.split(r"\n\s*\n", normalized)
    cleaned = [_normalize_text_block(block) for block in blocks]
    return "\n\n".join(block for block in cleaned if block).strip()


def _cell_to_markdown(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", " ").replace("\n", " ").strip()
    return text.replace("|", "\\|")


def _remove_long_artifact_tokens(text: str) -> str:
    # PDF export tools often add repeated page IDs or watermarks as long hex strings.
    return re.sub(r"\b[0-9A-Fa-f]{40,}\b", "", text)


def _normalize_text_block(block: str) -> str:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if not lines:
        return ""
    if _looks_like_structured_markdown(lines):
        return "\n".join(lines)
    output = lines[0]
    for line in lines[1:]:
        output = _join_extracted_line(output, line)
    output = re.sub(r"\s+([,.;:!?])", r"\1", output)
    output = re.sub(r"\(\s+", "(", output)
    output = re.sub(r"\s+\)", ")", output)
    output = re.sub(r"\s{2,}", " ", output)
    return output.strip()


def _looks_like_structured_markdown(lines: list[str]) -> bool:
    markers = ("#", "- ", "* ", "> ", "|")
    return any(line.startswith(markers) for line in lines)


def _join_extracted_line(output: str, line: str) -> str:
    if not output:
        return line
    if output.endswith(("-", "\u2010", "\u2011", "\u2012", "\u2013")):
        return output.rstrip("-\u2010\u2011\u2012\u2013 ") + line.lstrip()
    if re.match(r"^[,.;:!?)]", line):
        return output + line

    previous = re.search(r"([A-Za-z]{1,32})$", output)
    current = re.match(r"^([a-z]{1,8})([,\.;:]?)(?:\s+(.*)|$)", line)
    if previous and current:
        previous_word = previous.group(1)
        first_fragment = current.group(1)
        punctuation = current.group(2) or ""
        remainder = current.group(3) or ""
        if _should_join_fragment(previous_word, first_fragment, remainder):
            tail = first_fragment + punctuation
            if remainder:
                tail += " " + remainder
            return output + tail

    return output + " " + line


def _should_join_fragment(previous_word: str, first_fragment: str, remainder: str) -> bool:
    common_short_words = {
        "a",
        "an",
        "as",
        "at",
        "be",
        "by",
        "for",
        "if",
        "in",
        "is",
        "it",
        "no",
        "of",
        "on",
        "or",
        "the",
        "to",
        "we",
    }
    if previous_word != previous_word.lower():
        return False
    previous_lower = previous_word.lower()
    if len(previous_word) <= 2 and previous_lower not in common_short_words:
        return True
    if len(first_fragment) <= 4 and previous_lower not in common_short_words:
        return True
    if len(first_fragment) == 1 and remainder:
        return True
    return False
