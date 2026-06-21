from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from two_markdown.batch import BatchConverter
from two_markdown.context import ConversionContext
from two_markdown.converters.archive_converter import ArchiveConverter
from two_markdown.converters.csv_converter import CsvConverter
from two_markdown.converters.eml_converter import EmlConverter
from two_markdown.converters.epub_converter import EpubConverter
from two_markdown.converters.html_converter import HtmlConverter
from two_markdown.converters.ipynb_converter import IpynbConverter
from two_markdown.converters.opendocument_converter import OpenDocumentConverter
from two_markdown.converters.org_converter import OrgConverter
from two_markdown.converters.rtf_converter import RtfConverter
from two_markdown.converters.rst_converter import RstConverter
from two_markdown.converters import default_registry
from two_markdown.models import ConversionOptions
from two_markdown.utils import content_hash, frontmatter_lines, matches_globs


def _ctx(path: Path, **kw) -> ConversionContext:
    options = ConversionOptions(source_dir=path.parent, output_dir=path.parent / "out", **kw)
    return ConversionContext(path, options, default_registry())


class NewConverterTests(unittest.TestCase):
    def test_eml_extracts_headers_and_body(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "msg.eml"
            path.write_bytes(
                b"From: alice@example.com\r\nTo: bob@example.com\r\nSubject: Hello\r\n"
                b"Content-Type: text/plain\r\n\r\nThis is the body.\r\n"
            )
            doc = EmlConverter().convert(path, _ctx(path))
            self.assertIn("This is the body.", doc.markdown)
            self.assertEqual(doc.metadata.get("from"), "alice@example.com")
            self.assertEqual(doc.metadata.get("title"), "Hello")

    def test_eml_extracts_attachment(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "msg.eml"
            payload = (
                b"From: a@x.com\r\nSubject: With file\r\n"
                b'Content-Type: multipart/mixed; boundary="b"\r\n\r\n'
                b"--b\r\nContent-Type: text/plain\r\n\r\nbody\r\n"
                b"--b\r\nContent-Type: text/plain\r\nContent-Disposition: attachment; filename=\"note.txt\"\r\n"
                b"\r\nattached text\r\n--b--\r\n"
            )
            path.write_bytes(payload)
            doc = EmlConverter().convert(path, _ctx(path))
            self.assertTrue(any(a.filename == "note.txt" for a in doc.attachments))

    def test_ipynb_renders_code_and_output(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "nb.ipynb"
            nb = {
                "cells": [
                    {"cell_type": "markdown", "source": "# Hello"},
                    {"cell_type": "code", "source": "print(1)", "outputs": [{"output_type": "stream", "text": "1\n"}]},
                ],
                "metadata": {"kernelspec": {"name": "py", "language": "python"}},
            }
            path.write_text(json.dumps(nb), encoding="utf-8")
            doc = IpynbConverter().convert(path, _ctx(path))
            self.assertIn("```python", doc.markdown)
            self.assertIn("print(1)", doc.markdown)
            self.assertEqual(doc.metadata.get("language"), "python")

    def test_rtf_strips_control_words(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "r.rtf"
            path.write_text(r"{\rtf1\ansi Hello \b bold\b0 world\par second}", encoding="utf-8")
            doc = RtfConverter().convert(path, _ctx(path))
            self.assertIn("Hello", doc.markdown)
            self.assertIn("second", doc.markdown)
            self.assertNotIn("\\rtf", doc.markdown)

    def test_org_converts_headings_and_emphasis(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "d.org"
            path.write_text(
                "#+TITLE: My Doc\n#+AUTHOR: Me\n* Heading\n- item\n*bold* /ital/\n#+BEGIN_SRC python\nx=1\n#+END_SRC\n",
                encoding="utf-8",
            )
            doc = OrgConverter().convert(path, _ctx(path))
            self.assertIn("# Heading", doc.markdown)
            self.assertIn("**bold**", doc.markdown)
            self.assertIn("```python", doc.markdown)
            self.assertEqual(doc.metadata.get("title"), "My Doc")
            self.assertEqual(doc.metadata.get("author"), "Me")

    def test_rst_fallback_converts_underlined_titles(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "d.rst"
            path.write_text("Title\n=====\n\nSome paragraph.\n\nSub\n---\n\n:code:`x`", encoding="utf-8")
            doc = RstConverter().convert(path, _ctx(path))
            self.assertIn("Some paragraph.", doc.markdown)

    def test_csv_handles_tsv(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "d.tsv"
            path.write_text("a\tb\n1\t2\n", encoding="utf-8")
            doc = CsvConverter().convert(path, _ctx(path))
            self.assertIn("a", doc.markdown)
            self.assertIn("1", doc.markdown)

    def test_html_extracts_meta(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "p.html"
            path.write_text(
                '<html><head><meta name="author" content="Carol"><meta name="description" content="Desc">'
                '<title>T</title></head><body><h1>Hi</h1></body></html>',
                encoding="utf-8",
            )
            doc = HtmlConverter().convert(path, _ctx(path))
            self.assertEqual(doc.metadata.get("author"), "Carol")
            self.assertEqual(doc.title, "T")

    def test_html_fallback_parser_renders_tables(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "p.html"
            path.write_text("<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>", encoding="utf-8")
            from two_markdown.converters.html_converter import _BasicMarkdownHTMLParser
            parser = _BasicMarkdownHTMLParser()
            parser.feed(path.read_text(encoding="utf-8"))
            md = parser.markdown
            self.assertIn("| A | B |", md)
            self.assertIn("| 1 | 2 |", md)

    def test_epub_converts_chapter_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "book.epub"
            container = ('<?xml version="1.0"?><container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                         '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
            opf = ('<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0">'
                   '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Book</dc:title><dc:creator>Auth</dc:creator></metadata>'
                   '<manifest><item id="c" href="c.xhtml" media-type="application/xhtml+xml"/></manifest>'
                   '<spine><itemref idref="c"/></spine></package>')
            chapter = ('<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml"><body>'
                       '<h1>Chapter One</h1><p>Hello epub</p></body></html>')
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("mimetype", "application/epub+zip")
                z.writestr("META-INF/container.xml", container)
                z.writestr("OEBPS/content.opf", opf)
                z.writestr("OEBPS/c.xhtml", chapter)
            doc = EpubConverter().convert(path, _ctx(path))
            self.assertIn("Chapter One", doc.markdown)
            self.assertEqual(doc.metadata.get("title"), "Book")
            self.assertEqual(doc.metadata.get("author"), "Auth")

    def test_opendocument_converts_text_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "doc.odt"
            content = ('<?xml version="1.0"?><office:document-content '
                       'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
                       'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">'
                       '<office:body><office:text><text:h text:outline-level="1">Heading</text:h>'
                       '<text:p>Body text</text:p></office:text></office:body></office:document-content>')
            meta = ('<?xml version="1.0"?><office:document-meta xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
                    'xmlns:dc="http://purl.org/dc/elements/1.1/"><office:meta><dc:title>ODT</dc:title></office:meta></office:document-meta>')
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("mimetype", "application/vnd.oasis.opendocument.text")
                z.writestr("content.xml", content)
                z.writestr("meta.xml", meta)
            doc = OpenDocumentConverter().convert(path, _ctx(path))
            self.assertIn("Heading", doc.markdown)
            self.assertIn("Body text", doc.markdown)
            self.assertEqual(doc.metadata.get("title"), "ODT")

    def test_archive_lists_contents_when_not_recurring(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "pack.zip"
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("a.txt", "inside")
            doc = ArchiveConverter().convert(path, _ctx(path))
            self.assertIn("a.txt", doc.markdown)

    def test_archive_recurses_into_supported_files(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "pack.zip"
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("notes/a.txt", "inside text")
                z.writestr("data.csv", "x,y\n1,2\n")
            doc = ArchiveConverter().convert(path, _ctx(path, recurse_archives=True))
            self.assertIn("inside text", doc.markdown)
            self.assertIn("data.csv", doc.markdown)


class FeatureTests(unittest.TestCase):
    def test_dry_run_writes_no_files(self) -> None:
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
            source, output = Path(src), Path(out)
            (source / "a.txt").write_text("hi", encoding="utf-8")
            summary = BatchConverter().run(ConversionOptions(source_dir=source, output_dir=output, dry_run=True))
            self.assertEqual(summary.succeeded, 1)
            self.assertEqual(summary.records[0].reason, "dry_run")
            self.assertEqual(list(output.glob("*.md")), [])

    def test_incremental_skips_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
            source, output = Path(src), Path(out)
            (source / "a.txt").write_text("v1", encoding="utf-8")
            BatchConverter().run(ConversionOptions(source_dir=source, output_dir=output, incremental=True))
            second = BatchConverter().run(ConversionOptions(source_dir=source, output_dir=output, incremental=True))
            self.assertTrue(any(r.reason == "incremental" for r in second.records))

    def test_concurrency_converts_all(self) -> None:
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
            source, output = Path(src), Path(out)
            for i in range(5):
                (source / f"{i}.txt").write_text(str(i), encoding="utf-8")
            summary = BatchConverter().run(ConversionOptions(source_dir=source, output_dir=output, concurrency=4))
            self.assertEqual(summary.succeeded, 5)
            self.assertEqual(summary.failed, 0)

    def test_glob_include_filter(self) -> None:
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
            source, output = Path(src), Path(out)
            (source / "keep.txt").write_text("y", encoding="utf-8")
            (source / "drop.txt").write_text("n", encoding="utf-8")
            summary = BatchConverter().run(ConversionOptions(source_dir=source, output_dir=output, include_globs=["keep.txt"]))
            self.assertEqual(summary.total, 1)
            self.assertTrue((output / "keep.md").exists())

    def test_glob_exclude_filter(self) -> None:
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
            source, output = Path(src), Path(out)
            (source / "keep.txt").write_text("y", encoding="utf-8")
            (source / "skip.bin").write_bytes(b"")
            summary = BatchConverter().run(ConversionOptions(source_dir=source, output_dir=output, exclude_globs=["*.bin"]))
            self.assertEqual(summary.total, 1)

    def test_resume_only_retries_failed(self) -> None:
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
            source, output = Path(src), Path(out)
            (source / "good.txt").write_text("ok", encoding="utf-8")
            (source / "bad.bin").write_bytes(b"\x00")
            first = BatchConverter().run(ConversionOptions(source_dir=source, output_dir=output))
            self.assertEqual(first.succeeded, 1)
            self.assertEqual(first.skipped, 1)
            second = BatchConverter().run(ConversionOptions(source_dir=source, output_dir=output, resume=True))
            self.assertEqual(second.total, 1)
            self.assertEqual(second.records[0].source_path.name, "bad.bin")

    def test_max_file_size_skips_large_files(self) -> None:
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
            source, output = Path(src), Path(out)
            (source / "big.txt").write_text("x" * 4096, encoding="utf-8")
            (source / "small.txt").write_text("y", encoding="utf-8")
            summary = BatchConverter().run(ConversionOptions(source_dir=source, output_dir=output, max_file_size_mb=0.001))
            self.assertEqual(summary.total, 1)
            self.assertTrue((output / "small.md").exists())

    def test_frontmatter_template_substitution(self) -> None:
        fm = frontmatter_lines(
            title="Doc", source_path=Path("a.docx"), converter="docx", converted_at="2026-01-01T00:00:00+00:00",
            tags=("imported",), warnings=[], metadata={"author": "Alice"}, extra_frontmatter={},
            template="title: $title\nauthor: $meta_author",
        )
        self.assertIn("title: Doc", fm)
        self.assertIn("author: Alice", fm)

    def test_frontmatter_includes_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
            source, output = Path(src), Path(out)
            (source / "a.txt").write_text("hi", encoding="utf-8")
            BatchConverter().run(ConversionOptions(source_dir=source, output_dir=output, extra_frontmatter={"vault": "notes"}))
            text = (output / "a.md").read_text(encoding="utf-8")
            self.assertIn("vault: \"notes\"", text)

    def test_content_hash_stable(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "f.txt"
            path.write_text("abc", encoding="utf-8")
            self.assertEqual(content_hash(path), content_hash(path))

    def test_matches_globs(self) -> None:
        self.assertTrue(matches_globs(Path("a/b.txt"), ["*.txt"]))
        self.assertTrue(matches_globs(Path("a/b.txt"), ["b.txt"]))
        self.assertFalse(matches_globs(Path("a/b.txt"), ["*.csv"]))
        self.assertFalse(matches_globs(Path("a/b.txt"), []))

    def test_registry_supports_new_extensions(self) -> None:
        registry = default_registry()
        for ext in [".eml", ".ipynb", ".rtf", ".org", ".rst", ".epub", ".odt", ".ods", ".odp", ".zip", ".tsv"]:
            self.assertIn(ext, registry.supported_extensions, f"missing {ext}")


if __name__ == "__main__":
    unittest.main()
