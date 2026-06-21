from __future__ import annotations

import zipfile
from pathlib import Path
from xml.etree import ElementTree

from two_markdown.context import ConversionContext
from two_markdown.errors import ConversionError
from two_markdown.models import ConvertedDocument
from two_markdown.utils import markdown_table


class OpenDocumentConverter:
    name = "opendocument"
    extensions = {".odt", ".ods", ".odp", ".fodt", ".fods", ".fodp"}

    def convert(self, path: Path, context: ConversionContext) -> ConvertedDocument:
        if path.suffix.lower().startswith(".fod"):
            raise ConversionError("Flat OpenDocument (.fod*) is not supported; use the packaged (.od*) form.")
        try:
            archive = zipfile.ZipFile(path)
        except zipfile.BadZipFile as exc:
            raise ConversionError(f"Could not open OpenDocument file: {exc}") from exc

        warnings: list[str] = []
        try:
            root = ElementTree.fromstring(archive.read("content.xml"))
            metadata = _odf_metadata(archive) if context.options.include_metadata else {}
            kind = _document_kind(path)

            if kind == "spreadsheet":
                markdown = _render_spreadsheet(root, context, warnings)
            else:
                markdown = _render_body(root, context, warnings)

            if context.options.extract_attachments:
                markdown += _extract_odf_images(archive, context, warnings)

            return ConvertedDocument(
                title=metadata.get("title") or path.stem,
                markdown=f"# {metadata.get('title') or path.stem}\n\n{markdown}",
                converter=self.name,
                attachments=context.attachments,
                warnings=warnings,
                metadata=metadata,
            )
        finally:
            archive.close()


def _document_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".ods":
        return "spreadsheet"
    return "document"


def _render_body(root: ElementTree.Element, context: ConversionContext, warnings: list[str]) -> str:
    parts: list[str] = []
    for node in root.iter():
        tag = node.tag.split("}")[-1]
        if tag in {"h", "p", "list-item"} and node.text:
            text = _flatten_text(node)
            if not text.strip():
                continue
            if tag == "h":
                level = _outline_level(node)
                parts.append(f"{'#' * level} {text.strip()}")
            else:
                parts.append(text.strip())
        elif tag == "table":
            parts.append(_render_table(node))
    return "\n\n".join(parts)


def _render_spreadsheet(root: ElementTree.Element, context: ConversionContext, warnings: list[str]) -> str:
    parts: list[str] = []
    for node in root.iter():
        tag = node.tag.split("}")[-1]
        if tag == "table":
            name = node.get("{urn:oasis:names:tc:opendocument:xmlns:table:1.0}name") or "Sheet"
            parts.append(f"## {name}\n")
            parts.append(_render_table(node))
    return "\n\n".join(parts) if parts else "_No sheets found._"


def _render_table(node: ElementTree.Element) -> str:
    rows: list[list[object]] = []
    for row in node.iter():
        if row.tag.split("}")[-1] != "table-row":
            continue
        cells: list[object] = []
        for cell in row:
            if cell.tag.split("}")[-1] != "table-cell":
                continue
            cells.append(_flatten_text(cell))
        if any(str(c).strip() for c in cells):
            rows.append(cells)
    return markdown_table(rows) if rows else ""


def _flatten_text(node: ElementTree.Element) -> str:
    return "".join(node.itertext()).strip()


def _outline_level(node: ElementTree.Element) -> int:
    level = node.get("{urn:oasis:names:tc:opendocument:xmlns:text:1.0}outline-level")
    if level and level.isdigit():
        return max(1, min(int(level), 6))
    return 2


def _odf_metadata(archive: zipfile.ZipFile) -> dict[str, str]:
    metadata: dict[str, str] = {}
    try:
        root = ElementTree.fromstring(archive.read("meta.xml"))
    except (KeyError, ElementTree.ParseError):
        return metadata
    for node in root.iter():
        tag = node.tag.split("}")[-1]
        if tag in {"title", "creator", "subject", "description", "language", "keyword"} and node.text:
            key = "author" if tag == "creator" else tag
            if key not in metadata:
                metadata[key] = node.text.strip()
    return metadata


def _extract_odf_images(archive: zipfile.ZipFile, context: ConversionContext, warnings: list[str]) -> str:
    links: list[str] = []
    for info in archive.infolist():
        if not info.filename.startswith("Pictures/"):
            continue
        name = Path(info.filename).name
        try:
            links.append(context.add_attachment(name, archive.read(info.filename), alt_text=Path(name).stem))
        except Exception as exc:
            warnings.append(f"Could not extract OpenDocument image {name}: {exc}")
    return "\n\n" + "\n\n".join(links) if links else ""
