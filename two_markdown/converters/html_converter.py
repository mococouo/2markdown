from __future__ import annotations

import base64
import mimetypes
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import urlopen

from two_markdown.context import ConversionContext
from two_markdown.models import ConvertedDocument
from two_markdown.textio import read_text_guess


class HtmlConverter:
    name = "html"
    extensions = {".html", ".htm"}

    def convert(self, path: Path, context: ConversionContext) -> ConvertedDocument:
        html = read_text_guess(path)
        warnings: list[str] = []
        metadata = _extract_meta(html) if context.options.include_metadata else {}
        if context.options.extract_attachments:
            html, warnings = _extract_html_images(html, path, context)
        title = metadata.get("title") or _extract_title(html) or path.stem
        markdown = _to_markdown(html)
        return ConvertedDocument(
            title=title,
            markdown=markdown,
            converter=self.name,
            attachments=context.attachments,
            warnings=warnings,
            metadata=metadata,
        )


def _extract_meta(html: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for match in re.finditer(r"<meta\s+[^>]*>", html, flags=re.IGNORECASE):
        tag = match.group(0)
        name = _attr(tag, "name") or _attr(tag, "property")
        content = _attr(tag, "content")
        if not name or not content:
            continue
        key = name.lower().strip()
        if key in {"author", "description", "keywords", "generator"}:
            metadata[key] = content.strip()
        elif key in {"og:title", "dc.title"} and "title" not in metadata:
            metadata["title"] = content.strip()
        elif key in {"og:description"} and "description" not in metadata:
            metadata["description"] = content.strip()
        elif key in {"article:author", "dc.creator"} and "author" not in metadata:
            metadata["author"] = content.strip()
    return metadata


def _attr(tag: str, name: str) -> str | None:
    match = re.search(rf'{name}\s*=\s*"([^"]*)"|{name}\s*=\s*\'([^\']*)\'', tag, flags=re.IGNORECASE)
    if match:
        return match.group(1) if match.group(1) is not None else match.group(2)
    return None


def _extract_title(html: str) -> str | None:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return re.sub(r"\s+", " ", _strip_tags(match.group(1))).strip() or None


def _to_markdown(html: str) -> str:
    try:
        from markdownify import markdownify as md

        return md(html, heading_style="ATX").strip() + "\n"
    except Exception:
        parser = _BasicMarkdownHTMLParser()
        parser.feed(html)
        return parser.markdown.strip() + "\n"


def _extract_html_images(
    html: str,
    source_path: Path,
    context: ConversionContext,
) -> tuple[str, list[str]]:
    warnings: list[str] = []
    try:
        from bs4 import BeautifulSoup
    except Exception:
        return html, ["HTML image extraction requires beautifulsoup4."]

    soup = BeautifulSoup(html, "html.parser")
    for index, img in enumerate(soup.find_all("img"), start=1):
        src = img.get("src")
        if not src:
            continue
        alt_text = img.get("alt") or f"image {index}"
        attachment = _read_html_image(src, source_path, index, context)
        if attachment is None:
            if not _is_remote_or_anchor(src):
                warnings.append(f"Referenced image not found: {src}")
            continue
        filename, data = attachment
        img["src"] = context.add_attachment(filename, data, alt_text=alt_text)
    return str(soup), warnings


def _read_html_image(src: str, source_path: Path, index: int, context: ConversionContext) -> tuple[str, bytes] | None:
    if src.startswith("data:"):
        return _read_data_uri_image(src, index)
    if _is_remote_or_anchor(src):
        if context.options.download_remote and src.startswith(("http://", "https://")):
            return _download_remote_image(src, index, context)
        return None
    parsed = urlparse(src)
    clean = unquote(parsed.path or src)
    candidate = Path(clean)
    if not candidate.is_absolute():
        candidate = source_path.parent / candidate
    if not candidate.is_file():
        return None
    return candidate.name, candidate.read_bytes()


def _download_remote_image(src: str, index: int, context: ConversionContext) -> tuple[str, bytes] | None:
    try:
        with urlopen(src, timeout=20) as response:  # noqa: S310 - URL is user-supplied
            data = response.read()
    except Exception:
        return None
    parsed = urlparse(src)
    name = Path(parsed.path).name or f"remote-image-{index}"
    if not Path(name).suffix:
        suffix = mimetypes.guess_extension(parsed.path) or ".bin"
        name = f"remote-image-{index}{suffix}"
    return name, data


def _read_data_uri_image(src: str, index: int) -> tuple[str, bytes] | None:
    if "," not in src:
        return None
    header, payload = src.split(",", 1)
    if ";base64" not in header:
        return None
    media_type = header[5:].split(";", 1)[0] or "application/octet-stream"
    extension = mimetypes.guess_extension(media_type) or ".bin"
    try:
        data = base64.b64decode(payload)
    except ValueError:
        return None
    return f"image-{index}{extension}", data


def _is_remote_or_anchor(src: str) -> bool:
    parsed = urlparse(src)
    return parsed.scheme in {"http", "https", "mailto", "tel"} or src.startswith("#")


def _strip_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value)


class _BasicMarkdownHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._link_stack: list[str | None] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    @property
    def markdown(self) -> str:
        text = "".join(self.parts)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(tag[1])
            self.parts.append("\n\n" + "#" * level + " ")
        elif tag in {"p", "div", "section", "article"}:
            self.parts.append("\n\n")
        elif tag == "br":
            self.parts.append("\n")
        elif tag in {"strong", "b"}:
            self.parts.append("**")
        elif tag in {"em", "i"}:
            self.parts.append("*")
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag == "a":
            self.parts.append("[")
            self._link_stack.append(attrs_dict.get("href"))
        elif tag == "table":
            self._table = []
        elif tag == "tr":
            self._row = []
        elif tag in {"th", "td"}:
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"strong", "b"}:
            self.parts.append("**")
        elif tag in {"em", "i"}:
            self.parts.append("*")
        elif tag == "a":
            href = self._link_stack.pop() if self._link_stack else None
            self.parts.append(f"]({href})" if href else "]")
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6", "p", "div", "section", "article"}:
            self.parts.append("\n\n")
        elif tag in {"th", "td"} and self._cell is not None and self._row is not None:
            self._row.append("".join(self._cell).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table:
            from two_markdown.utils import markdown_table

            rendered = markdown_table([list(row) for row in self._table])
            self.parts.append("\n\n" + rendered + "\n\n")
            self._table = None

    def handle_data(self, data: str) -> None:
        collapsed = re.sub(r"\s+", " ", data)
        if not collapsed.strip():
            return
        if self._cell is not None:
            self._cell.append(collapsed)
        else:
            self.parts.append(collapsed)
