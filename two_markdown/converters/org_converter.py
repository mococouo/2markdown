from __future__ import annotations

import re
from pathlib import Path

from two_markdown.context import ConversionContext
from two_markdown.models import ConvertedDocument
from two_markdown.textio import read_text_guess


class OrgConverter:
    name = "org"
    extensions = {".org"}

    def convert(self, path: Path, context: ConversionContext) -> ConvertedDocument:
        text = read_text_guess(path)
        metadata = _org_metadata(text) if context.options.include_metadata else {}
        markdown = _org_to_markdown(text)
        return ConvertedDocument(
            title=metadata.get("title") or path.stem,
            markdown=markdown,
            converter=self.name,
            attachments=context.attachments,
            metadata=metadata,
        )


def _org_metadata(text: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for match in re.finditer(r"^#\+([A-Z_]+):\s*(.*)$", text, flags=re.MULTILINE):
        key, value = match.group(1).lower(), match.group(2).strip()
        if key in {"title", "author", "date", "email", "language"}:
            metadata[key] = value
    return metadata


def _org_to_markdown(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    in_src = False
    src_lang = ""
    for line in lines:
        src_start = re.match(r"^#\+BEGIN_SRC\s+(\w+)", line, flags=re.IGNORECASE)
        if src_start:
            in_src = True
            src_lang = src_start.group(1)
            out.append(f"```{src_lang}")
            continue
        if re.match(r"^#\+END_SRC", line, flags=re.IGNORECASE) and in_src:
            in_src = False
            out.append("```")
            continue
        if in_src:
            out.append(line)
            continue
        if re.match(r"^#\+", line):
            continue
        heading = re.match(r"^(\*+)\s+(.*)$", line)
        if heading:
            level = len(heading.group(1))
            out.append(f"{'#' * min(level, 6)} {heading.group(2)}")
            continue
        out.append(_inline_org(line))
    return "\n".join(out)


def _inline_org(line: str) -> str:
    line = re.sub(r"\*([^*\s][^*]*?)\*", r"**\1**", line)
    line = re.sub(r"/([^/\s][^/]*?)/", r"*\1*", line)
    line = re.sub(r"_([^_\s][^_]*?)_", r"<u>\1</u>", line)
    line = re.sub(r"=([^=\s][^=]*?)=", r"`\1`", line)
    line = re.sub(r"~([^~\s][^~]*?)~", r"`\1`", line)
    return line
