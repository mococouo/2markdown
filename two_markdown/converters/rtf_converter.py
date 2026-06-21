from __future__ import annotations

import re
from pathlib import Path

from two_markdown.context import ConversionContext
from two_markdown.models import ConvertedDocument
from two_markdown.textio import read_text_guess


class RtfConverter:
    name = "rtf"
    extensions = {".rtf"}

    def convert(self, path: Path, context: ConversionContext) -> ConvertedDocument:
        raw = read_text_guess(path)
        text = _strip_rtf(raw)
        paragraphs = [block.strip() for block in re.split(r"\n{2,}", text) if block.strip()]
        markdown = f"# {path.stem}\n\n" + "\n\n".join(paragraphs)
        return ConvertedDocument(
            title=path.stem,
            markdown=markdown,
            converter=self.name,
            attachments=context.attachments,
            warnings=["RTF conversion is best-effort; complex formatting may be lost."] if len(raw) > 64 else [],
        )


def _strip_rtf(raw: str) -> str:
    if not raw.startswith("{\\rtf"):
        return raw
    out = []
    i = 0
    skip_group = 0
    while i < len(raw):
        ch = raw[i]
        if ch == "\\":
            if raw[i:i + 2] == "\\u":
                match = re.match(r"\\u(-?\d+)\??", raw[i:])
                if match:
                    code = int(match.group(1))
                    if code < 0:
                        code += 65536
                    out.append(chr(code))
                    i += match.end()
                    continue
            if raw[i:i + 2] == "\\'":
                match = re.match(r"\\'([0-9A-Fa-f]{2})", raw[i:])
                if match:
                    out.append(chr(int(match.group(1), 16)))
                    i += match.end()
                    continue
            match = re.match(r"\\([a-zA-Z]+)(-?\d+)? ?", raw[i:])
            if match:
                word = match.group(1)
                if word in {"par", "page"}:
                    out.append("\n\n")
                elif word == "line":
                    out.append("\n")
                elif word == "tab":
                    out.append("\t")
                elif word in {"fonttbl", "stylesheet", "colortbl", "info", "pict"}:
                    skip_group += 1
                i += match.end()
                continue
            i += 1
            continue
        if ch == "{" and skip_group:
            skip_group += 1
            i += 1
            continue
        if ch == "}" and skip_group:
            skip_group -= 1
            i += 1
            continue
        if ch in "{}":
            i += 1
            continue
        if skip_group:
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)
