from __future__ import annotations

from pathlib import Path
import re
from urllib.parse import unquote, urlparse

from two_markdown.context import ConversionContext
from two_markdown.models import ConvertedDocument
from two_markdown.textio import read_text_guess

MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


class TextConverter:
    name = "text"
    extensions = {".txt", ".md"}

    def convert(self, path: Path, context: ConversionContext) -> ConvertedDocument:
        text = read_text_guess(path)
        warnings: list[str] = []
        converter_name = self.name if path.suffix.lower() == ".txt" else "markdown"
        if path.suffix.lower() == ".md" and context.options.extract_attachments:
            text, warnings = _extract_markdown_images(text, path, context)
        return ConvertedDocument(
            title=path.stem,
            markdown=text,
            converter=converter_name,
            attachments=context.attachments,
            warnings=warnings,
        )


def _extract_markdown_images(
    markdown: str,
    source_path: Path,
    context: ConversionContext,
) -> tuple[str, list[str]]:
    warnings: list[str] = []

    def replace(match: re.Match[str]) -> str:
        alt_text = match.group(1)
        raw_target = match.group(2).strip()
        image_path = _resolve_markdown_image(raw_target, source_path)
        if image_path is None:
            return match.group(0)
        if not image_path.is_file():
            warnings.append(f"Referenced image not found: {raw_target}")
            return match.group(0)
        try:
            return context.add_attachment(image_path.name, image_path.read_bytes(), alt_text=alt_text or image_path.stem)
        except OSError as exc:
            warnings.append(f"Could not copy referenced image {raw_target}: {exc}")
            return match.group(0)

    return MARKDOWN_IMAGE_RE.sub(replace, markdown), warnings


def _resolve_markdown_image(raw_target: str, source_path: Path) -> Path | None:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    if " " in target and not Path(target).exists():
        target = target.split(" ", 1)[0]
    target = target.strip("'\"")
    parsed = urlparse(target)
    if parsed.scheme in {"http", "https", "mailto", "tel", "data"} or target.startswith("#"):
        return None
    clean = unquote(parsed.path or target)
    candidate = Path(clean)
    if not candidate.is_absolute():
        candidate = source_path.parent / candidate
    return candidate
