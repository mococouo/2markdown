from __future__ import annotations

import re
from pathlib import Path
from threading import Lock

from .models import ConvertedDocument, ConversionOptions
from .utils import file_identity, frontmatter_lines, now_iso, sanitize_filename

ATTACHMENT_TOKEN_RE = re.compile(r"\{\{attachment:([^}]+)\}\}")


class MarkdownWriter:
    def __init__(self, options: ConversionOptions) -> None:
        self.options = options
        self._reserved_paths: set[Path] = set()
        self._lock = Lock()

    def write(self, source_path: Path, document: ConvertedDocument) -> Path:
        with self._lock:
            return self._write_locked(source_path, document)

    def _write_locked(self, source_path: Path, document: ConvertedDocument) -> Path:
        source_dir = self.options.source_dir.resolve()
        relative_path = source_path.resolve().relative_to(source_dir)
        relative_dir = relative_path.parent if self.options.preserve_tree else Path()
        note_dir = self.options.output_dir / relative_dir
        note_dir.mkdir(parents=True, exist_ok=True)

        safe_stem = sanitize_filename(source_path.stem)
        output_path = self._choose_output_path(note_dir / f"{safe_stem}.md", source_path, relative_path)

        attachment_dir = self.options.output_dir / "_attachments" / relative_dir / safe_stem
        attachment_map: dict[str, str] = {}
        if self.options.extract_attachments and document.attachments:
            attachment_dir.mkdir(parents=True, exist_ok=True)
            for attachment in document.attachments:
                attachment_path = self._unique_attachment_path(attachment_dir / attachment.filename)
                attachment_path.write_bytes(attachment.data)
                rel = attachment_path.relative_to(output_path.parent).as_posix()
                attachment_map[attachment.filename] = rel

        body = self._replace_attachment_tokens(document.markdown, attachment_map)
        if self.options.write_frontmatter:
            frontmatter = frontmatter_lines(
                title=document.title,
                source_path=source_path,
                converter=document.converter,
                converted_at=now_iso(),
                tags=self.options.tags,
                warnings=document.warnings,
                metadata=document.metadata if self.options.include_metadata else {},
                extra_frontmatter=self.options.extra_frontmatter,
                template=self.options.frontmatter_template,
            )
            body = frontmatter + "\n" + body.lstrip()
        output_path.write_text(body.rstrip() + "\n", encoding="utf-8")
        return output_path

    def _choose_output_path(self, target: Path, source_path: Path, relative_path: Path) -> Path:
        if self.options.overwrite and target not in self._reserved_paths:
            self._reserved_paths.add(target)
            return target
        if not target.exists() and target not in self._reserved_paths:
            self._reserved_paths.add(target)
            return target
        suffix = file_identity(source_path, relative_path)
        candidate = target.with_name(f"{target.stem}--{suffix}{target.suffix}")
        index = 2
        while candidate.exists() or candidate in self._reserved_paths:
            candidate = target.with_name(f"{target.stem}--{suffix}-{index}{target.suffix}")
            index += 1
        self._reserved_paths.add(candidate)
        return candidate

    def _unique_attachment_path(self, target: Path) -> Path:
        if not target.exists():
            return target
        candidate = target.with_name(f"{target.stem}-2{target.suffix}")
        index = 3
        while candidate.exists():
            candidate = target.with_name(f"{target.stem}-{index}{target.suffix}")
            index += 1
        return candidate

    def _replace_attachment_tokens(self, markdown: str, attachment_map: dict[str, str]) -> str:
        def replace(match: re.Match[str]) -> str:
            name = match.group(1)
            return attachment_map.get(name, "")

        return ATTACHMENT_TOKEN_RE.sub(replace, markdown)
