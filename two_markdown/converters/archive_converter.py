from __future__ import annotations

import bz2
import gzip
import lzma
import tarfile
import tempfile
import zipfile
from pathlib import Path

from two_markdown.context import ConversionContext
from two_markdown.errors import ConversionError
from two_markdown.models import ConvertedDocument
from two_markdown.utils import markdown_table


class ArchiveConverter:
    name = "archive"
    extensions = {
        ".zip", ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2",
        ".tar.xz", ".txz", ".gz", ".bz2", ".xz",
    }

    SKIP_INNER_NAMES = {"archive", "audio-video"}

    def convert(self, path: Path, context: ConversionContext) -> ConvertedDocument:
        warnings: list[str] = []
        if path.suffix.lower() == ".7z":
            raise ConversionError("7z archives are not supported by the built-in extractor.")

        if context.options.recurse_archives and context.registry is not None:
            markdown = self._recurse(path, context, warnings)
        else:
            markdown = self._list_contents(path, context, warnings)

        return ConvertedDocument(
            title=path.stem,
            markdown=f"# {path.stem}\n\n{markdown}",
            converter=self.name,
            attachments=context.attachments,
            warnings=warnings,
        )

    def _list_contents(self, path: Path, context: ConversionContext, warnings: list[str]) -> str:
        entries = _list_archive(path, warnings)
        if not entries:
            return "_Archive is empty or could not be read._"
        rows: list[list[object]] = [["Path", "Size"]]
        for name, size in entries:
            rows.append([name, size])
        note = "\n\n_Enable \"Recurse archives\" to extract and convert the contents._" if not context.options.recurse_archives else ""
        return markdown_table(rows) + note

    def _recurse(self, path: Path, context: ConversionContext, warnings: list[str]) -> str:
        with tempfile.TemporaryDirectory(prefix="2markdown_archive_") as temp_raw:
            temp_dir = Path(temp_raw)
            try:
                _extract_archive(path, temp_dir, warnings)
            except Exception as exc:
                raise ConversionError(f"Could not extract archive: {exc}") from exc

            inner_files = sorted(p for p in temp_dir.rglob("*") if p.is_file())
            if not inner_files:
                return "_Archive is empty._"

            parts: list[str] = []
            for inner in inner_files:
                rel = inner.relative_to(temp_dir)
                converter = context.registry.get(inner) if context.registry else None
                if converter is None:
                    continue
                if getattr(converter, "name", "") in self.SKIP_INNER_NAMES:
                    continue
                try:
                    sub_doc = converter.convert(inner, context)
                except Exception as exc:
                    warnings.append(f"Could not convert {rel.as_posix()}: {exc}")
                    continue
                parts.append(f"## {rel.as_posix()}")
                parts.append(sub_doc.markdown)
                warnings.extend(sub_doc.warnings)
            return "\n\n".join(parts) if parts else "_No supported files inside the archive._"


def _list_archive(path: Path, warnings: list[str]) -> list[tuple[str, int]]:
    suffix = path.suffix.lower()
    name = path.name.lower()
    entries: list[tuple[str, int]] = []
    try:
        if suffix == ".zip":
            with zipfile.ZipFile(path) as archive:
                for info in archive.infolist():
                    if not info.is_dir():
                        entries.append((info.filename, info.file_size))
        elif name.endswith((".gz",)) and not name.endswith((".tar.gz", ".tgz")):
            pass
        elif name.endswith((".bz2",)) and not name.endswith((".tar.bz2", ".tbz2")):
            pass
        elif name.endswith((".xz",)) and not name.endswith((".tar.xz", ".txz")):
            pass
        else:
            with tarfile.open(path) as archive:
                for member in archive.getmembers():
                    if member.isfile():
                        entries.append((member.name, member.size))
    except Exception as exc:
        warnings.append(f"Could not list archive contents: {exc}")
    return entries


def _extract_archive(path: Path, dest: Path, warnings: list[str]) -> None:
    suffix = path.suffix.lower()
    name = path.name.lower()
    if suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            _safe_zip_extract(archive, dest, warnings)
    elif name.endswith((".gz",)) and not name.endswith((".tar.gz", ".tgz")):
        out_name = path.stem
        with gzip.open(path, "rb") as src, (dest / out_name).open("wb") as dst:
            dst.write(src.read())
    elif name.endswith((".bz2",)) and not name.endswith((".tar.bz2", ".tbz2")):
        out_name = path.stem
        with bz2.open(path, "rb") as src, (dest / out_name).open("wb") as dst:
            dst.write(src.read())
    elif name.endswith((".xz",)) and not name.endswith((".tar.xz", ".txz")):
        out_name = path.stem
        with lzma.open(path, "rb") as src, (dest / out_name).open("wb") as dst:
            dst.write(src.read())
    else:
        with tarfile.open(path) as archive:
            try:
                archive.extractall(dest, filter="data")
            except TypeError:
                archive.extractall(dest)


def _safe_zip_extract(archive: zipfile.ZipFile, dest: Path, warnings: list[str]) -> None:
    dest = dest.resolve()
    for info in archive.infolist():
        if info.is_dir():
            continue
        target = (dest / info.filename).resolve()
        if not str(target).startswith(str(dest)):
            warnings.append(f"Skipped unsafe archive path: {info.filename}")
            continue
        archive.extract(info, dest)
