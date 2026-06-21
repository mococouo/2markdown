# Supported Formats

2Markdown is designed around small, focused converters. Basic text formats work without optional dependencies; richer formats need the matching dependency group.

## Built in

- Text and Markdown: `.txt`, `.md`
- Tables: `.csv`, `.tsv`
- Web: `.html`, `.htm`
- Email: `.eml`
- Notebooks: `.ipynb`
- Lightweight markup: `.rtf`, `.org`, `.rst`
- Ebooks: `.epub`
- OpenDocument: `.odt`, `.ods`, `.odp`
- Archives: `.zip`, `.tar`, `.tar.gz`, `.tgz`, `.tar.bz2`, `.tar.xz`, `.gz`, `.bz2`, `.xz`

## Optional groups

| Group | Formats / feature | Install |
| --- | --- | --- |
| `office` | `.docx`, `.xlsx`, `.pptx` | `python -m pip install -e .[office]` |
| `pdf` | `.pdf` text, metadata, tables, images where extractable | `python -m pip install -e .[pdf]` |
| `web` | Better HTML conversion and image handling | `python -m pip install -e .[web]` |
| `ocr` | OCR for images and scanned PDFs | `python -m pip install -e .[ocr]` |
| `audio` | Audio/video transcription | `python -m pip install -e .[audio]` |
| `email` | Outlook `.msg` email | `python -m pip install -e .[email]` |
| `markup` | Better reStructuredText rendering | `python -m pip install -e .[markup]` |
| `gui` | Desktop drag-and-drop support | `python -m pip install -e .[gui]` |

Install every optional converter:

```powershell
python -m pip install -e .[all]
```

## Notes

- PDF quality depends on how the PDF was created. Scanned PDFs need OCR.
- Audio/video transcription requires the optional `audio` group and may download models.
- OCR requires Tesseract to be installed on the system in addition to Python packages.
- Unsupported files are written to `conversion_report.csv` and `conversion_report.json` instead of stopping the batch.
