from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Event, Lock
from typing import Callable

from .context import ConversionContext
from .converters import ConverterRegistry, default_registry
from .errors import ConversionError
from .manifest import load_manifest, save_manifest
from .models import BatchSummary, ConversionOptions, ConversionRecord
from .report import read_report, write_reports
from .scanner import discover_files
from .utils import content_hash
from .writer import MarkdownWriter

ProgressCallback = Callable[[ConversionRecord, int, int], None]


class BatchConverter:
    def __init__(self, registry: ConverterRegistry | None = None) -> None:
        self.registry = registry or default_registry()

    def run(
        self,
        options: ConversionOptions,
        progress: ProgressCallback | None = None,
        cancel_event: Event | None = None,
    ) -> BatchSummary:
        options.source_dir = options.source_dir.resolve()
        options.output_dir = options.output_dir.resolve()
        if not options.source_dir.is_dir():
            raise ValueError(f"Source folder does not exist: {options.source_dir}")
        options.output_dir.mkdir(parents=True, exist_ok=True)

        files = discover_files(options)
        if options.resume:
            files = _filter_resume(files, options.output_dir)

        manifest = load_manifest(options.output_dir) if options.incremental else {}
        writer = MarkdownWriter(options)
        records: list[ConversionRecord | None] = [None] * len(files)
        progress_lock = Lock()

        def emit(index: int, record: ConversionRecord) -> None:
            records[index] = record
            if progress:
                with progress_lock:
                    progress(record, index + 1, len(files))

        workers = max(1, min(options.concurrency, 8))
        if workers == 1:
            for index, path in enumerate(files):
                if cancel_event and cancel_event.is_set():
                    emit(index, _cancelled(path))
                    continue
                emit(index, self._handle(path, options, writer, manifest))
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(self._handle, path, options, writer, manifest): index
                    for index, path in enumerate(files)
                }
                for future in as_completed(futures):
                    index = futures[future]
                    if cancel_event and cancel_event.is_set():
                        emit(index, _cancelled(files[index]))
                        continue
                    try:
                        emit(index, future.result())
                    except Exception as exc:
                        emit(index, ConversionRecord(
                            source_path=files[index],
                            status="failed",
                            error=f"{type(exc).__name__}: {exc}",
                        ))

        final_records = [record or _cancelled(files[i]) for i, record in enumerate(records)]
        new_manifest = _build_manifest(options, final_records, manifest)
        if options.incremental and not options.dry_run:
            save_manifest(options.output_dir, new_manifest)

        report_csv, report_json = write_reports(options.output_dir, final_records)
        succeeded = sum(1 for r in final_records if r.status == "success")
        failed = sum(1 for r in final_records if r.status == "failed")
        skipped = sum(1 for r in final_records if r.status == "skipped")
        return BatchSummary(
            total=len(final_records),
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
            report_csv=report_csv,
            report_json=report_json,
            records=final_records,
        )

    def _handle(
        self,
        path: Path,
        options: ConversionOptions,
        writer: MarkdownWriter,
        manifest: dict[str, dict[str, str]],
    ) -> ConversionRecord:
        converter = self.registry.get(path)
        if converter is None:
            return ConversionRecord(
                source_path=path,
                status="skipped",
                error=f"No converter registered for {path.suffix.lower()}",
            )

        relative = path.resolve().relative_to(options.source_dir)
        rel_key = relative.as_posix()
        if options.incremental and not options.dry_run:
            previous = manifest.get(rel_key)
            if previous:
                try:
                    current_hash = content_hash(path)
                except OSError:
                    current_hash = ""
                if current_hash and current_hash == previous.get("hash"):
                    return ConversionRecord(
                        source_path=path,
                        status="skipped",
                        reason="incremental",
                        converter=getattr(converter, "name", None),
                        error="Unchanged since last run.",
                    )

        try:
            context = ConversionContext(path, options, self.registry)
            document = converter.convert(path, context)
            if options.dry_run:
                return ConversionRecord(
                    source_path=path,
                    status="success",
                    converter=document.converter,
                    warnings=document.warnings,
                    reason="dry_run",
                )
            output_path = writer.write(path, document)
            return ConversionRecord(
                source_path=path,
                status="success",
                output_path=output_path,
                converter=document.converter,
                warnings=document.warnings,
            )
        except ConversionError as exc:
            return ConversionRecord(
                source_path=path,
                status="failed",
                converter=getattr(converter, "name", None),
                error=str(exc),
            )
        except Exception as exc:
            return ConversionRecord(
                source_path=path,
                status="failed",
                converter=getattr(converter, "name", None),
                error=f"{type(exc).__name__}: {exc}",
            )


def _cancelled(path: Path) -> ConversionRecord:
    return ConversionRecord(
        source_path=path,
        status="skipped",
        error="Batch cancelled before this file was converted.",
    )


def _filter_resume(files: list[Path], output_dir: Path) -> list[Path]:
    rows = read_report(output_dir)
    if not rows:
        return files
    retry = {Path(row["source_path"]).resolve() for row in rows if row.get("status") != "success"}
    return [path for path in files if path.resolve() in retry]


def _build_manifest(
    options: ConversionOptions,
    records: list[ConversionRecord],
    previous: dict[str, dict[str, str]],
) -> dict[str, dict[str, str]]:
    manifest: dict[str, dict[str, str]] = {}
    for record in records:
        try:
            relative = record.source_path.resolve().relative_to(options.source_dir)
        except ValueError:
            continue
        rel_key = relative.as_posix()
        if record.status == "success" and record.reason != "dry_run":
            try:
                manifest[rel_key] = {
                    "hash": content_hash(record.source_path),
                    "output": str(record.output_path) if record.output_path else "",
                }
            except OSError:
                pass
        elif rel_key in previous and record.status == "skipped" and record.reason == "incremental":
            manifest[rel_key] = previous[rel_key]
    return manifest
