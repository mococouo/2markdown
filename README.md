# 2Markdown

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-beta-orange)

2Markdown is a local batch converter for turning common files into Obsidian-ready Markdown notes.

It is built for people who already have a messy folder of PDFs, Office files, emails, notebooks, web pages, transcripts, ebooks, and text files, and want a clean Markdown vault with attachments, metadata, and conversion reports.

> Built with AI coding models. Designed from real workflow problems.

## Highlights

- Desktop app with drag-and-drop support when `tkinterdnd2` is installed.
- CLI for repeatable batch jobs and automation.
- Obsidian-friendly output: Markdown notes, `_attachments/`, YAML frontmatter, and source metadata.
- Optional converter groups so users only install the heavy dependencies they need.
- Conversion reports for success, failure, skipped files, warnings, and output paths.
- English UI by default, with language switching available in the app.

## Download

Download source archives and future packaged builds from [GitHub Releases](https://github.com/mococouo/2markdown/releases), or run directly from this repository with Python.

## Quick Start

For normal desktop use, double-click:

```text
2Markdown.pyw
```

If this repository was downloaded with the `v0.20` folder at the top level, you can also double-click the `2Markdown.pyw` file in the repository root.

For terminal-based troubleshooting, the same desktop app can still be launched with:

```powershell
python -m two_markdown
```

On Windows, the legacy no-console launcher is still available:

```text
scripts/run_windows.pyw
```

The first launch can install optional converters for Office, PDF, ebooks, OCR, audio/video, and drag-and-drop support.

## CLI Usage

```powershell
python -m two_markdown --source "D:\Files" --output "D:\ObsidianVault\Imported"
```

Common options:

```powershell
python -m two_markdown `
  --source "D:\Files" `
  --output "D:\ObsidianVault\Imported" `
  --incremental `
  --download-remote `
  --concurrency 4
```

Run help for the full option list:

```powershell
python -m two_markdown --help
```

## Install Optional Converters

Install everything:

```powershell
python -m pip install -e .[all]
```

Install only what you need:

```powershell
python -m pip install -e .[office,pdf,web]
```

See [Supported Formats](docs/supported-formats.md) for the full list.

## Output Layout

2Markdown preserves the source folder tree by default:

```text
ObsidianVault/
  Imported/
    Project/
      pitch-deck.md
      notes.md
    _attachments/
      Project/
        pitch-deck/
          slide-1-image.png
    conversion_report.csv
    conversion_report.json
    _2markdown_manifest.json
```

Example frontmatter:

```yaml
---
title: "Pitch Deck"
source_path: "D:\Files\Project\pitch-deck.pdf"
source_ext: ".pdf"
converted_at: "2026-06-22T10:00:00+08:00"
converter: "pdf"
tags:
  - imported
  - 2markdown
---
```

## Desktop Workflow

1. Click the large input area to choose a file, or drop a file or folder onto it.
2. Let 2Markdown create `<source>_markdown` next to the source, or click Change output.
3. Use the Dark mode toggle in the top bar if you prefer a darker workspace.
4. Keep the default options for Obsidian imports.
5. Click Convert.
6. Open the output folder or review the conversion reports.

Advanced options such as overwrite, incremental runs, dry run, OCR, archive recursion, concurrency, and max file size are available behind the advanced panel.

## Documentation

- [Supported formats](docs/supported-formats.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Roadmap](docs/roadmap.md)
- [Changelog](CHANGELOG.md)

## Development

Run tests:

```powershell
python -m unittest discover
```

Install the package in editable mode:

```powershell
python -m pip install -e .
```

Install all optional dependencies for local testing:

```powershell
python -m pip install -e .[all]
```

## Project Status

2Markdown is beta software. It works well for many common document workflows, but conversion quality depends on the source format:

- PDFs created from real text convert better than scanned PDFs.
- Scanned PDFs and images require OCR setup.
- Audio/video transcription requires optional model dependencies.
- Complex page layouts may still need manual review.

## License

MIT. See [LICENSE](LICENSE).
