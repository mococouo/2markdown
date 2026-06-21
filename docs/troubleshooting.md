# Troubleshooting

## The desktop app opens a console window

Use `scripts/run_windows.pyw` on Windows. `.bat` files always show or flash a console window.

## Drag and drop does not work

Install the GUI helper:

```powershell
python -m pip install -e .[gui]
```

Without it, the drop zones still work as click-to-browse pickers.

## Office or PDF files fail

Install the matching optional group:

```powershell
python -m pip install -e .[office,pdf]
```

The app also offers to install missing converters when a batch fails because a dependency is missing.

## Scanned PDFs produce little or no text

Enable OCR and install the OCR group:

```powershell
python -m pip install -e .[ocr]
python -m two_markdown --source "D:\Files" --output "D:\Vault\Imported" --ocr --ocr-lang eng
```

Chinese OCR typically needs Tesseract language data such as `chi_sim`.

## Output contains repeated IDs or broken line wraps

PDFs often store visual layout rather than clean paragraphs. 2Markdown removes common long ID artifacts and normalizes obvious line wrapping, but some highly formatted PDFs still need manual review.

## The app cannot install dependencies

Run the manual installer:

```powershell
scripts\install_converters.bat
```

Or install from the terminal:

```powershell
python -m pip install -e .[all]
```
