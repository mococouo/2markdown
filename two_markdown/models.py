from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


RecordStatus = Literal["success", "failed", "skipped"]


@dataclass(slots=True)
class ConversionOptions:
    source_dir: Path
    output_dir: Path
    preserve_tree: bool = True
    extract_attachments: bool = True
    write_frontmatter: bool = True
    overwrite: bool = False
    skip_hidden: bool = True
    tags: tuple[str, ...] = ("imported", "2markdown")
    incremental: bool = False
    dry_run: bool = False
    concurrency: int = 1
    download_remote: bool = False
    ocr: bool = False
    ocr_lang: str = "eng"
    audio_lang: str | None = None
    include_metadata: bool = True
    recurse_archives: bool = False
    include_globs: list[str] | None = None
    exclude_globs: list[str] | None = None
    resume: bool = False
    max_file_size_mb: float | None = None
    frontmatter_template: str | None = None
    extra_frontmatter: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class Attachment:
    filename: str
    data: bytes


@dataclass(slots=True)
class ConvertedDocument:
    title: str
    markdown: str
    converter: str
    attachments: list[Attachment] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ConversionRecord:
    source_path: Path
    status: RecordStatus
    output_path: Path | None = None
    converter: str | None = None
    warnings: list[str] = field(default_factory=list)
    error: str | None = None
    reason: str | None = None


@dataclass(slots=True)
class BatchSummary:
    total: int
    succeeded: int
    failed: int
    skipped: int
    report_csv: Path
    report_json: Path
    records: list[ConversionRecord]
