from __future__ import annotations

import argparse
from pathlib import Path

from . import i18n
from .app import launch_app
from .batch import BatchConverter
from .models import ConversionOptions, ConversionRecord


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Batch convert files into Obsidian-ready Markdown.")
    parser.add_argument("--source", type=Path, help="Folder containing files to convert.")
    parser.add_argument("--output", type=Path, help="Obsidian vault or output folder.")
    parser.add_argument("--language", default=None, help="UI language code (en, zh, ja, ko, es, fr, de, pt, ru, it, ar, zh-TW).")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing Markdown output files.")
    parser.add_argument("--flat", action="store_true", help="Do not preserve the source folder tree.")
    parser.add_argument("--no-frontmatter", action="store_true", help="Do not add YAML frontmatter.")
    parser.add_argument("--no-attachments", action="store_true", help="Do not write extracted attachments.")
    parser.add_argument("--no-metadata", action="store_true", help="Do not extract document metadata into frontmatter.")
    parser.add_argument("--incremental", action="store_true", help="Skip files unchanged since the last run.")
    parser.add_argument("--dry-run", action="store_true", help="Convert without writing any files.")
    parser.add_argument("--resume", action="store_true", help="Only retry files that failed in the previous report.")
    parser.add_argument("--download-remote", action="store_true", help="Download remote images referenced in HTML.")
    parser.add_argument("--ocr", action="store_true", help="Enable OCR for scanned PDFs and images.")
    parser.add_argument("--ocr-lang", default="eng", help="Tesseract language(s), e.g. 'eng' or 'chi_sim+eng'.")
    parser.add_argument("--audio-lang", default=None, help="Language hint for audio/video transcription.")
    parser.add_argument("--recurse-archives", action="store_true", help="Extract and convert files inside archives.")
    parser.add_argument("--concurrency", type=int, default=1, help="Number of files to convert in parallel.")
    parser.add_argument("--max-size-mb", type=float, default=None, help="Skip files larger than this many megabytes.")
    parser.add_argument("--include", action="append", default=None, help="Glob pattern(s) to include (repeatable).")
    parser.add_argument("--exclude", action="append", default=None, help="Glob pattern(s) to exclude (repeatable).")
    parser.add_argument("--tag", action="append", default=None, help="Extra frontmatter tag (repeatable).")
    parser.add_argument("--frontmatter-template", default=None, help="Path to a YAML frontmatter template file.")
    args = parser.parse_args(argv)

    if args.language:
        i18n.set_language(args.language)

    if not args.source and not args.output:
        launch_app()
        return 0
    if not args.source or not args.output:
        parser.error("--source and --output must be provided together.")

    tags = ("imported", "2markdown")
    if args.tag:
        tags = tuple(args.tag)

    template = None
    if args.frontmatter_template:
        template = Path(args.frontmatter_template).read_text(encoding="utf-8")

    options = ConversionOptions(
        source_dir=args.source,
        output_dir=args.output,
        preserve_tree=not args.flat,
        extract_attachments=not args.no_attachments,
        write_frontmatter=not args.no_frontmatter,
        overwrite=args.overwrite,
        incremental=args.incremental,
        dry_run=args.dry_run,
        resume=args.resume,
        download_remote=args.download_remote,
        ocr=args.ocr,
        ocr_lang=args.ocr_lang,
        audio_lang=args.audio_lang,
        recurse_archives=args.recurse_archives,
        concurrency=max(1, args.concurrency),
        max_file_size_mb=args.max_size_mb,
        include_globs=args.include,
        exclude_globs=args.exclude,
        include_metadata=not args.no_metadata,
        tags=tags,
        frontmatter_template=template,
    )
    converter = BatchConverter()
    summary = converter.run(options, progress=_print_progress)
    print(
        f"Done. total={summary.total} success={summary.succeeded} "
        f"failed={summary.failed} skipped={summary.skipped}"
    )
    print(f"Reports: {summary.report_csv} and {summary.report_json}")
    return 1 if summary.failed else 0


def _print_progress(record: ConversionRecord, index: int, total: int) -> None:
    label = record.output_path if record.output_path else (record.error or record.reason or "")
    print(f"[{index}/{total}] {record.status}: {record.source_path} -> {label}")
