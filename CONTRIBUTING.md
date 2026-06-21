# Contributing

Thanks for improving 2Markdown.

## Development setup

```powershell
python -m pip install -e .
python -m unittest discover
```

Install optional converter groups only when you need to work on those formats:

```powershell
python -m pip install -e .[office,pdf,web]
```

## Guidelines

- Keep converters small and format-specific.
- Do not make network calls during conversion unless the user explicitly enables that feature.
- Do not overwrite source files.
- Preserve Obsidian-friendly output: Markdown notes, `_attachments/`, frontmatter, and reports.
- Add focused tests for new converter behavior.

## Pull requests

Include:

- What changed.
- Which formats are affected.
- Test command output.
- Any new optional dependencies.
