from __future__ import annotations

from pathlib import Path

from two_markdown.context import ConversionContext
from two_markdown.errors import MissingDependencyError
from two_markdown.models import ConvertedDocument
from two_markdown.utils import markdown_table, normalize_extracted_text


class PdfConverter:
    name = "pdf"
    extensions = {".pdf"}

    def convert(self, path: Path, context: ConversionContext) -> ConvertedDocument:
        try:
            from pypdf import PdfReader
        except Exception as exc:
            raise MissingDependencyError("pypdf", "PDF conversion") from exc

        reader = PdfReader(str(path))
        parts = [f"# {path.stem}"]
        warnings: list[str] = []

        outline = _outline(reader) if context.options.include_metadata else []
        if outline:
            parts.append("## Contents")
            parts.append(outline)

        plumber = _open_pdfplumber(path)
        extracted_pages = 0
        total_pages = len(reader.pages)
        for index, page in enumerate(reader.pages, start=1):
            parts.append(f"## Page {index}")
            text = normalize_extracted_text(page.extract_text() or "")
            tables = _pdfplumber_tables(plumber, index) if plumber else []
            if text:
                extracted_pages += 1
                parts.append(text)
            elif context.options.ocr:
                ocr_text = _ocr_page(path, index, context, warnings)
                if ocr_text:
                    extracted_pages += 1
                    parts.append(ocr_text)
                else:
                    parts.append("_No extractable text on this page._")
            else:
                parts.append("_No extractable text on this page._")
            for table in tables:
                parts.append(markdown_table(table))
            if context.options.extract_attachments:
                parts.extend(_extract_page_images(page, index, context, warnings))

        if plumber:
            plumber.close()

        if extracted_pages == 0 and total_pages:
            warnings.append("PDF has no extractable text. It may be scanned and require OCR (enable the OCR option).")
        elif extracted_pages < total_pages:
            warnings.append("Some PDF pages had no extractable text and may require OCR.")

        metadata = _pdf_metadata(reader) if context.options.include_metadata else {}

        return ConvertedDocument(
            title=metadata.get("title") or path.stem,
            markdown="\n\n".join(parts),
            converter=self.name,
            attachments=context.attachments,
            warnings=warnings,
            metadata=metadata,
        )


def _open_pdfplumber(path: Path):
    try:
        import pdfplumber
    except Exception:
        return None
    try:
        return pdfplumber.open(str(path))
    except Exception:
        return None


def _pdfplumber_tables(plumber, page_number: int) -> list[list[list[object]]]:
    if plumber is None or page_number > len(plumber.pages):
        return []
    try:
        page = plumber.pages[page_number - 1]
        tables = page.extract_tables() or []
    except Exception:
        return []
    cleaned: list[list[list[object]]] = []
    for table in tables:
        rows = [[(cell or "").replace("\n", " ") if cell is not None else "" for cell in row] for row in table]
        if rows:
            cleaned.append(rows)
    return cleaned


def _outline(reader: object) -> str:
    try:
        outline = reader.outline  # type: ignore[attr-defined]
    except Exception:
        return ""
    lines: list[str] = []

    def walk(items: object, depth: int) -> None:
        if not items:
            return
        for item in items:  # type: ignore[attr-defined]
            if isinstance(item, list):
                walk(item, depth + 1)
            else:
                title = getattr(item, "title", None) or str(item)
                lines.append(f"{'  ' * depth}- {title}")

    try:
        walk(outline, 0)
    except Exception:
        return ""
    return "\n".join(lines) if lines else ""


def _ocr_page(path: Path, page_number: int, context: ConversionContext, warnings: list[str]) -> str:
    try:
        import fitz  # type: ignore
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
    except Exception as exc:
        warnings.append(f"OCR is not available (needs PyMuPDF + pytesseract): {exc}")
        return ""
    try:
        doc = fitz.open(str(path))
        page = doc.load_page(page_number - 1)
        pix = page.get_pixmap(dpi=200)
        image = Image.frombytes("RGB" if pix.alpha < 5 else "RGBA", (pix.width, pix.height), pix.samples)
        if image.mode == "RGBA":
            image = image.convert("RGB")
        text = pytesseract.image_to_string(image, lang=context.options.ocr_lang)
        doc.close()
    except Exception as exc:
        warnings.append(f"OCR failed on page {page_number}: {exc}")
        return ""
    return normalize_extracted_text(text)


def _pdf_metadata(reader: object) -> dict[str, str]:
    metadata: dict[str, str] = {}
    try:
        info = reader.metadata  # type: ignore[attr-defined]
    except Exception:
        return metadata
    if not info:
        return metadata
    mapping = {
        "/Title": "title",
        "/Author": "author",
        "/Subject": "subject",
        "/Keywords": "keywords",
        "/Creator": "creator",
        "/Producer": "producer",
    }
    for raw, key in mapping.items():
        value = info.get(raw)
        if value and str(value).strip():
            metadata[key] = str(value).strip()
    created = info.get("/CreationDate")
    if created:
        metadata["created"] = str(created)
    modified = info.get("/ModDate")
    if modified:
        metadata["modified"] = str(modified)
    return metadata


def _extract_page_images(
    page: object,
    page_number: int,
    context: ConversionContext,
    warnings: list[str],
) -> list[str]:
    links: list[str] = []
    try:
        images = getattr(page, "images", [])
    except Exception as exc:
        warnings.append(f"Could not inspect PDF images on page {page_number}: {exc}")
        return links
    for image_index, image in enumerate(images, start=1):
        try:
            name = getattr(image, "name", None) or f"page-{page_number}-image-{image_index}.bin"
            data = image.data
            filename = f"page-{page_number}-{name}"
            links.append(context.add_attachment(filename, data, alt_text=f"page {page_number} image {image_index}"))
        except Exception as exc:
            warnings.append(f"Could not extract PDF image on page {page_number}: {exc}")
    return links
