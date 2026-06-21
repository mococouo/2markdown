from __future__ import annotations

from importlib.metadata import entry_points
from pathlib import Path
from typing import Protocol

from two_markdown.context import ConversionContext
from two_markdown.models import ConvertedDocument


class Converter(Protocol):
    name: str
    extensions: set[str]

    def convert(self, path: Path, context: ConversionContext) -> ConvertedDocument:
        ...


class ConverterRegistry:
    def __init__(self) -> None:
        self._by_extension: dict[str, Converter] = {}

    def register(self, converter: Converter) -> None:
        for extension in converter.extensions:
            self._by_extension[extension.lower()] = converter

    def get(self, path: Path) -> Converter | None:
        suffix = path.suffix.lower()
        if suffix in self._by_extension:
            return self._by_extension[suffix]
        lowered = path.name.lower()
        for ext in sorted(self._by_extension, key=len, reverse=True):
            if lowered.endswith(ext):
                return self._by_extension[ext]
        return None

    @property
    def supported_extensions(self) -> set[str]:
        return set(self._by_extension)


def default_registry() -> ConverterRegistry:
    from .archive_converter import ArchiveConverter
    from .audio_converter import AudioVideoConverter
    from .csv_converter import CsvConverter
    from .docx_converter import DocxConverter
    from .eml_converter import EmlConverter
    from .epub_converter import EpubConverter
    from .html_converter import HtmlConverter
    from .image_ocr_converter import ImageOcrConverter
    from .ipynb_converter import IpynbConverter
    from .msg_converter import MsgConverter
    from .opendocument_converter import OpenDocumentConverter
    from .org_converter import OrgConverter
    from .pdf_converter import PdfConverter
    from .pptx_converter import PptxConverter
    from .rst_converter import RstConverter
    from .rtf_converter import RtfConverter
    from .text_converter import TextConverter
    from .xlsx_converter import XlsxConverter

    registry = ConverterRegistry()
    for converter in (
        TextConverter(),
        CsvConverter(),
        HtmlConverter(),
        EmlConverter(),
        IpynbConverter(),
        RtfConverter(),
        OrgConverter(),
        RstConverter(),
        EpubConverter(),
        OpenDocumentConverter(),
        DocxConverter(),
        XlsxConverter(),
        PptxConverter(),
        PdfConverter(),
        ImageOcrConverter(),
        AudioVideoConverter(),
        ArchiveConverter(),
        MsgConverter(),
    ):
        registry.register(converter)
    load_plugins(registry)
    return registry


def load_plugins(registry: ConverterRegistry) -> None:
    try:
        eps = entry_points(group="two_markdown.converters")
    except Exception:
        return
    for entry in eps:
        try:
            factory = entry.load()
            converter = factory() if callable(factory) else factory
            registry.register(converter)
        except Exception:
            continue
