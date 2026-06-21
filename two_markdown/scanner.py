from __future__ import annotations

from pathlib import Path

from .models import ConversionOptions
from .utils import matches_globs


def discover_files(options: ConversionOptions) -> list[Path]:
    source_dir = options.source_dir.resolve()
    output_dir = options.output_dir.resolve()
    max_bytes = options.max_file_size_mb * (1 << 20) if options.max_file_size_mb else None
    files: list[Path] = []
    for path in source_dir.rglob("*"):
        if not path.is_file():
            continue
        if options.skip_hidden and _has_hidden_part(path.relative_to(source_dir)):
            continue
        try:
            resolved = path.resolve()
            if resolved == output_dir or output_dir in resolved.parents:
                continue
        except OSError:
            pass
        relative = path.relative_to(source_dir)
        if options.include_globs and not matches_globs(relative, options.include_globs):
            continue
        if options.exclude_globs and matches_globs(relative, options.exclude_globs):
            continue
        if max_bytes is not None:
            try:
                if path.stat().st_size > max_bytes:
                    continue
            except OSError:
                continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(source_dir).as_posix().casefold())


def _has_hidden_part(relative_path: Path) -> bool:
    return any(part.startswith(".") for part in relative_path.parts)
