from __future__ import annotations

import tempfile
import unittest
import importlib
from pathlib import Path

from two_markdown.batch import BatchConverter
from two_markdown.converters.docx_converter import DocxConverter
from two_markdown.converters.pdf_converter import PdfConverter
from two_markdown.converters.pptx_converter import PptxConverter
from two_markdown.converters.xlsx_converter import XlsxConverter
from two_markdown.context import ConversionContext
from two_markdown.models import ConversionOptions
from two_markdown.utils import markdown_table, normalize_extracted_text, sanitize_filename


class UtilityTests(unittest.TestCase):
    def test_sanitize_filename_removes_windows_invalid_characters(self) -> None:
        self.assertEqual(sanitize_filename('a<b>c:d/e\\f|g?h*i'), "a_b_c_d_e_f_g_h_i")

    def test_markdown_table_escapes_pipes(self) -> None:
        table = markdown_table([["A", "B"], ["x|y", "z"]])
        self.assertIn("x\\|y", table)

    def test_normalize_extracted_text_repairs_pdf_line_wraps(self) -> None:
        raw = (
            "securit\n"
            "ies\n"
            ", nor shall there be any sale woul\n"
            "d b\n"
            "e unlawful prior to\n"
            "registration. Starship\n"
            "in accordance with schedule. forward\n"
            " -\n"
            "looking statements and timing o\n"
            "f o\n"
            "ur capital"
        )

        cleaned = normalize_extracted_text(raw)

        self.assertIn("securities, nor", cleaned)
        self.assertIn("would be unlawful", cleaned)
        self.assertIn("to registration", cleaned)
        self.assertIn("Starship in accordance", cleaned)
        self.assertIn("forward-looking", cleaned)
        self.assertIn("timing of our capital", cleaned)

    def test_normalize_extracted_text_removes_long_hex_artifacts(self) -> None:
        raw = (
            "正常正文\n"
            "E6636BB1012F9B6DA981D91E6DDB8054EFBCBE0C937DD29C9A0D463F44DFE5AA2EEB9DEC4153E3D4A81677D38D1F40B28A6BC4C3FF2B283A5942FC7D560DCE07B73A935\n"
            "下一页正文"
        )

        cleaned = normalize_extracted_text(raw)

        self.assertIn("正常正文", cleaned)
        self.assertIn("下一页正文", cleaned)
        self.assertNotIn("E6636", cleaned)


class BatchTests(unittest.TestCase):
    def test_batch_converts_text_csv_and_html(self) -> None:
        with tempfile.TemporaryDirectory() as source_raw, tempfile.TemporaryDirectory() as output_raw:
            source = Path(source_raw)
            output = Path(output_raw)
            (source / "notes").mkdir()
            (source / "notes" / "a.txt").write_text("hello world", encoding="utf-8")
            (source / "table.csv").write_text("name,value\nalpha,1\n", encoding="utf-8")
            (source / "page.html").write_text(
                "<html><head><title>Page Title</title></head><body><h1>Hello</h1></body></html>",
                encoding="utf-8",
            )

            summary = BatchConverter().run(ConversionOptions(source_dir=source, output_dir=output))

            self.assertEqual(summary.failed, 0)
            self.assertEqual(summary.succeeded, 3)
            self.assertTrue((output / "notes" / "a.md").exists())
            self.assertTrue((output / "table.md").exists())
            self.assertTrue((output / "page.md").exists())
            self.assertTrue((output / "conversion_report.csv").exists())
            self.assertIn("source_path", (output / "page.md").read_text(encoding="utf-8"))

    def test_existing_output_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as source_raw, tempfile.TemporaryDirectory() as output_raw:
            source = Path(source_raw)
            output = Path(output_raw)
            (source / "a.txt").write_text("new", encoding="utf-8")
            (output / "a.md").write_text("old", encoding="utf-8")

            summary = BatchConverter().run(ConversionOptions(source_dir=source, output_dir=output))

            self.assertEqual(summary.succeeded, 1)
            self.assertEqual((output / "a.md").read_text(encoding="utf-8"), "old")
            generated = [path for path in output.glob("a--*.md")]
            self.assertEqual(len(generated), 1)

    def test_unsupported_files_are_reported_as_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as source_raw, tempfile.TemporaryDirectory() as output_raw:
            source = Path(source_raw)
            output = Path(output_raw)
            (source / "unknown.bin").write_bytes(b"\x00\x01")

            summary = BatchConverter().run(ConversionOptions(source_dir=source, output_dir=output))

            self.assertEqual(summary.succeeded, 0)
            self.assertEqual(summary.skipped, 1)
            self.assertIn("No converter registered", summary.records[0].error or "")

    def test_markdown_local_images_are_copied_to_attachments(self) -> None:
        with tempfile.TemporaryDirectory() as source_raw, tempfile.TemporaryDirectory() as output_raw:
            source = Path(source_raw)
            output = Path(output_raw)
            (source / "image.png").write_bytes(b"fake-png")
            (source / "note.md").write_text("![pic](image.png)", encoding="utf-8")

            summary = BatchConverter().run(ConversionOptions(source_dir=source, output_dir=output))

            self.assertEqual(summary.succeeded, 1)
            generated = (output / "note.md").read_text(encoding="utf-8")
            self.assertIn("_attachments", generated)
            self.assertTrue((output / "_attachments" / "note" / "image.png").exists())

    def test_html_local_images_are_copied_to_attachments(self) -> None:
        with tempfile.TemporaryDirectory() as source_raw, tempfile.TemporaryDirectory() as output_raw:
            source = Path(source_raw)
            output = Path(output_raw)
            (source / "image.png").write_bytes(b"fake-png")
            (source / "page.html").write_text('<p>Hello</p><img src="image.png" alt="pic">', encoding="utf-8")

            summary = BatchConverter().run(ConversionOptions(source_dir=source, output_dir=output))

            self.assertEqual(summary.succeeded, 1)
            generated = (output / "page.md").read_text(encoding="utf-8")
            self.assertIn("_attachments", generated)
            self.assertTrue((output / "_attachments" / "page" / "image.png").exists())


class OptionalConverterTests(unittest.TestCase):
    def test_docx_converter_reads_paragraphs(self) -> None:
        docx = _import_or_skip(self, "docx")
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "sample.docx"
            document = docx.Document()
            document.add_heading("Heading", level=1)
            document.add_paragraph("Body text")
            document.save(path)

            result = DocxConverter().convert(path, _context(path))

            self.assertIn("Heading", result.markdown)
            self.assertIn("Body text", result.markdown)

    def test_xlsx_converter_reads_sheet_table(self) -> None:
        openpyxl = _import_or_skip(self, "openpyxl")
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "sample.xlsx"
            workbook = openpyxl.Workbook()
            sheet = workbook.active
            sheet.title = "Data"
            sheet.append(["name", "value"])
            sheet.append(["alpha", 1])
            workbook.save(path)

            result = XlsxConverter().convert(path, _context(path))

            self.assertIn("## Data", result.markdown)
            self.assertIn("alpha", result.markdown)

    def test_pptx_converter_reads_slide_text(self) -> None:
        pptx = _import_or_skip(self, "pptx")
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "sample.pptx"
            presentation = pptx.Presentation()
            slide = presentation.slides.add_slide(presentation.slide_layouts[5])
            slide.shapes.title.text = "Slide title"
            presentation.save(path)

            result = PptxConverter().convert(path, _context(path))

            self.assertIn("Slide title", result.markdown)

    def test_pdf_converter_reports_blank_pdf_as_ocr_candidate(self) -> None:
        pypdf = _import_or_skip(self, "pypdf")
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "blank.pdf"
            writer = pypdf.PdfWriter()
            writer.add_blank_page(width=72, height=72)
            with path.open("wb") as handle:
                writer.write(handle)

            result = PdfConverter().convert(path, _context(path))

            self.assertTrue(result.warnings)
            self.assertIn("require OCR", result.warnings[0])


def _context(path: Path) -> ConversionContext:
    return ConversionContext(path, ConversionOptions(source_dir=path.parent, output_dir=path.parent / "out"))


def _import_or_skip(testcase: unittest.TestCase, module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        testcase.skipTest(f"Optional dependency is not installed: {module_name}")


if __name__ == "__main__":
    unittest.main()
