from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from two_markdown.context import ConversionContext
from two_markdown.errors import ConversionError
from two_markdown.models import ConvertedDocument


class EpubConverter:
    name = "epub"
    extensions = {".epub"}

    def convert(self, path: Path, context: ConversionContext) -> ConvertedDocument:
        try:
            archive = zipfile.ZipFile(path)
        except zipfile.BadZipFile as exc:
            raise ConversionError(f"Could not open EPUB: {exc}") from exc

        warnings: list[str] = []
        try:
            opf_path = _locate_opf(archive)
            opf_root, opf_dir = _read_xml(archive, opf_path)
            manifest, spine = _parse_opf(opf_root)
            metadata = _epub_metadata(opf_root) if context.options.include_metadata else {}
            title = metadata.get("title") or path.stem

            parts = [f"# {title}"]
            for item_id in spine:
                href = manifest.get(item_id)
                if not href:
                    continue
                xhtml_path = _join_zip_path(opf_dir, href)
                chapter_md = _chapter_to_markdown(archive, xhtml_path, context, warnings)
                if chapter_md:
                    parts.append(chapter_md)

            if not spine:
                warnings.append("EPUB spine is empty; no chapters were converted.")

            return ConvertedDocument(
                title=title,
                markdown="\n\n".join(parts),
                converter=self.name,
                attachments=context.attachments,
                warnings=warnings,
                metadata=metadata,
            )
        finally:
            archive.close()


def _locate_opf(archive: zipfile.ZipFile) -> str:
    try:
        container = archive.read("META-INF/container.xml")
    except KeyError as exc:
        raise ConversionError("EPUB container.xml not found.") from exc
    root = ElementTree.fromstring(container)
    for item in root.iter():
        tag = item.tag.split("}")[-1]
        if tag == "rootfile":
            return item.get("full-path") or ""
    raise ConversionError("EPUB OPF path not found in container.xml.")


def _read_xml(archive: zipfile.ZipFile, member: str) -> tuple[ElementTree.Element, str]:
    try:
        data = archive.read(member)
    except KeyError as exc:
        raise ConversionError(f"EPUB member not found: {member}") from exc
    root = ElementTree.fromstring(data)
    return root, str(Path(member).parent)


def _parse_opf(root: ElementTree.Element) -> tuple[dict[str, str], list[str]]:
    manifest: dict[str, str] = {}
    spine: list[str] = []
    for item in root.iter():
        tag = item.tag.split("}")[-1]
        if tag == "item":
            item_id = item.get("id")
            href = item.get("href")
            if item_id and href:
                manifest[item_id] = href
        elif tag == "itemref":
            idref = item.get("idref")
            if idref:
                spine.append(idref)
    return manifest, spine


def _epub_metadata(root: ElementTree.Element) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for item in root.iter():
        tag = item.tag.split("}")[-1]
        if tag in {"title", "creator", "language", "publisher", "date", "subject"} and item.text:
            key = "author" if tag == "creator" else tag
            if key not in metadata:
                metadata[key] = item.text.strip()
    return metadata


def _join_zip_path(base: str, href: str) -> str:
    href = unquote_attr(href.split("#")[0])
    if not base:
        return href
    return str(Path(base) / href).replace("\\", "/")


def unquote_attr(value: str) -> str:
    from urllib.parse import unquote

    return unquote(value)


def _chapter_to_markdown(archive: zipfile.ZipFile, xhtml_path: str, context: ConversionContext, warnings: list[str]) -> str:
    try:
        raw = archive.read(xhtml_path)
    except KeyError:
        return ""
    html = raw.decode("utf-8", errors="replace")
    if context.options.extract_attachments:
        html = _extract_epub_images(archive, html, xhtml_path, context, warnings)
    from two_markdown.converters.html_converter import _to_markdown

    return _to_markdown(html).strip()


def _extract_epub_images(archive: zipfile.ZipFile, html: str, xhtml_path: str, context: ConversionContext, warnings: list[str]) -> str:
    try:
        from bs4 import BeautifulSoup
    except Exception:
        return html
    soup = BeautifulSoup(html, "html.parser")
    base_dir = str(Path(xhtml_path).parent)
    for index, img in enumerate(soup.find_all("img"), start=1):
        src = img.get("src")
        if not src:
            continue
        member = _join_zip_path(base_dir, src)
        try:
            data = archive.read(member)
        except KeyError:
            continue
        name = Path(member).name or f"epub-image-{index}.png"
        img["src"] = context.add_attachment(name, data, alt_text=img.get("alt") or f"image {index}")
    return str(soup)
