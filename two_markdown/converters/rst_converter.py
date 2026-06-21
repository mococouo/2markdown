from __future__ import annotations

import re
from pathlib import Path

from two_markdown.context import ConversionContext
from two_markdown.models import ConvertedDocument
from two_markdown.textio import read_text_guess


class RstConverter:
    name = "rst"
    extensions = {".rst"}

    def convert(self, path: Path, context: ConversionContext) -> ConvertedDocument:
        text = read_text_guess(path)
        markdown = _rst_to_markdown(text, path)
        return ConvertedDocument(
            title=path.stem,
            markdown=markdown,
            converter=self.name,
            attachments=context.attachments,
        )


def _rst_to_markdown(text: str, path: Path) -> str:
    try:
        from docutils.core import publish_string  # type: ignore

        html = publish_string(text, writer_name="html5", settings_overrides={"report_level": 5, "halt_level": 5})
        from two_markdown.converters.html_converter import _to_markdown

        return f"# {path.stem}\n\n" + _to_markdown(html.decode("utf-8", errors="replace")).strip()
    except Exception:
        return _fallback_rst(text, path)


def _fallback_rst(text: str, path: Path) -> str:
    lines = text.splitlines()
    out: list[str] = [f"# {path.stem}"]
    i = 0
    while i < len(lines):
        line = lines[i]
        if i + 1 < len(lines) and re.fullmatch(r"[=\-~`#\"^*+]+", lines[i + 1]) and len(lines[i + 1]) >= max(3, len(line)):
            level = {"=": 2, "-": 3, "~": 4, "`": 5, "#": 6}.get(lines[i + 1][0], 3)
            out.append(f"\n{'#' * level} {line.strip()}")
            i += 2
            continue
        out.append(line)
        i += 1
    body = "\n".join(out)
    body = re.sub(r":code:`([^`]+)`", r"`\1`", body)
    body = re.sub(r"``([^`]+)``", r"`\1`", body)
    body = re.sub(r"\*\*([^*]+)\*\*", r"**\1**", body)
    body = re.sub(r"\*([^*]+)\*", r"*\1*", body)
    return body
