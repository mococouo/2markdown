from __future__ import annotations

from pathlib import Path

from two_markdown.context import ConversionContext
from two_markdown.errors import MissingDependencyError
from two_markdown.models import ConvertedDocument


class ImageOcrConverter:
    name = "image-ocr"
    extensions = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp"}

    def convert(self, path: Path, context: ConversionContext) -> ConvertedDocument:
        try:
            import pytesseract  # type: ignore
            from PIL import Image  # type: ignore
        except Exception as exc:
            raise MissingDependencyError("pytesseract+Pillow", "Image OCR") from exc

        warnings: list[str] = []
        pages: list[str] = []
        try:
            image = Image.open(path)
        except Exception as exc:
            raise MissingDependencyError("Pillow", "Image OCR") from exc

        frame = 0
        while True:
            frame += 1
            try:
                page_image = image.convert("RGB") if image.mode != "RGB" else image
                text = pytesseract.image_to_string(page_image, lang=context.options.ocr_lang)
            except Exception as exc:
                warnings.append(f"OCR failed on frame {frame}: {exc}")
                break
            cleaned = text.strip()
            if cleaned:
                pages.append(f"## Page {frame}\n\n{cleaned}" if frame > 1 else cleaned)
            try:
                image.seek(image.tell() + 1)
            except EOFError:
                break

        body = "\n\n".join(pages) if pages else "_No text recognized by OCR._"
        if not pages:
            warnings.append("No text recognized. The image may need a different OCR language or higher resolution.")

        return ConvertedDocument(
            title=path.stem,
            markdown=f"# {path.stem}\n\n{body}",
            converter=self.name,
            attachments=context.attachments,
            warnings=warnings,
        )
