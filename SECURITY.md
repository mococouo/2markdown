# Security Policy

2Markdown processes local user files. Treat document parsing as untrusted input.

## Supported versions

Security fixes target the latest released version.

## Reporting a vulnerability

Open a private security advisory if the repository is hosted on GitHub, or contact the maintainer directly.

Please include:

- Affected version or commit.
- File type and converter involved.
- Minimal reproduction steps.
- Whether the issue requires opening a malicious file.

## Security expectations

- Converters must not execute embedded scripts or macros.
- Network access must be opt-in.
- Source files must never be modified.
- Generated Markdown and attachments are written only under the selected output directory.
