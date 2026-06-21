from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

from two_markdown.context import ConversionContext
from two_markdown.models import ConvertedDocument
from two_markdown.textio import read_text_guess
from two_markdown.utils import markdown_table


class CsvConverter:
    name = "csv"
    extensions = {".csv", ".tsv"}

    def convert(self, path: Path, context: ConversionContext) -> ConvertedDocument:
        text = read_text_guess(path)
        dialect = _detect_dialect(text, path)
        rows = list(csv.reader(StringIO(text), dialect=dialect))
        markdown = f"# {path.stem}\n\n{markdown_table(rows)}" if rows else f"# {path.stem}\n"
        return ConvertedDocument(
            title=path.stem,
            markdown=markdown,
            converter=self.name,
            attachments=context.attachments,
        )


def _detect_dialect(text: str, path: Path) -> csv.Dialect:
    if path.suffix.lower() == ".tsv":
        return _tab_dialect()
    sample = text[:65536]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;|\t")
    except csv.Error:
        return csv.excel


class _TabDialect(csv.Dialect):
    delimiter = "\t"
    quotechar = '"'
    doublequote = True
    skipinitialspace = False
    lineterminator = "\r\n"
    quoting = csv.QUOTE_MINIMAL


def _tab_dialect() -> csv.Dialect:
    return _TabDialect()
