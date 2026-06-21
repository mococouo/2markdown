from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class OptionalDependency:
    package: str
    import_name: str
    group: str = "core"


OPTIONAL_DEPENDENCIES: tuple[OptionalDependency, ...] = (
    OptionalDependency("beautifulsoup4>=4.12", "bs4", "web"),
    OptionalDependency("markdownify>=0.11", "markdownify", "web"),
    OptionalDependency("openpyxl>=3.1", "openpyxl", "office"),
    OptionalDependency("pypdf>=4.0", "pypdf", "pdf"),
    OptionalDependency("pdfplumber>=0.10", "pdfplumber", "pdf"),
    OptionalDependency("python-docx>=1.1", "docx", "office"),
    OptionalDependency("python-pptx>=0.6", "pptx", "office"),
    OptionalDependency("Pillow>=10.0", "PIL", "image"),
    OptionalDependency("pytesseract>=0.3", "pytesseract", "ocr"),
    OptionalDependency("PyMuPDF>=1.24", "fitz", "ocr"),
    OptionalDependency("faster-whisper>=1.0", "faster_whisper", "audio"),
    OptionalDependency("extract-msg>=0.48", "extract_msg", "email"),
    OptionalDependency("docutils>=0.20", "docutils", "markup"),
    OptionalDependency("tkinterdnd2>=0.3", "tkinterdnd2", "gui"),
)


DEPENDENCY_GROUPS: dict[str, tuple[str, ...]] = {
    "office": ("openpyxl", "python-docx", "python-pptx"),
    "pdf": ("pypdf", "pdfplumber"),
    "web": ("beautifulsoup4", "markdownify"),
    "image": ("Pillow",),
    "ocr": ("Pillow", "pytesseract", "PyMuPDF"),
    "audio": ("faster-whisper",),
    "email": ("extract-msg",),
    "markup": ("docutils",),
    "gui": ("tkinterdnd2>=0.3",),
    "all": tuple(dependency.package for dependency in OPTIONAL_DEPENDENCIES),
}

_INSTALL_ORDER: tuple[str, ...] = (
    "office", "pdf", "web", "image", "ocr", "audio", "email", "markup", "gui",
)


class OptionalDependencyInstallError(RuntimeError):
    def __init__(self, output: str) -> None:
        super().__init__("Optional converter dependency installation failed.")
        self.output = output


class InstallResult:
    __slots__ = ("succeeded", "failed", "output")

    def __init__(self) -> None:
        self.succeeded: list[str] = []
        self.failed: list[str] = []
        self.output: str = ""


def missing_optional_dependencies(group: str | None = None) -> list[OptionalDependency]:
    deps = _dependencies_for_group(group) if group else OPTIONAL_DEPENDENCIES
    return [
        dependency
        for dependency in deps
        if importlib.util.find_spec(dependency.import_name) is None
    ]


def install_optional_dependencies(group: str | None = None) -> str:
    """Install converters. Groups are installed independently so one
    failure (e.g. tkinterdnd2) does not abort the others. Raises only if
    every group fails."""
    result = _install_groups([group] if group else list(_INSTALL_ORDER))
    if result.output and not result.succeeded and result.failed:
        raise OptionalDependencyInstallError(result.output)
    return result.output


def install_optional_dependencies_grouped(group: str | None = None) -> InstallResult:
    """Like install_optional_dependencies but returns a detailed result
    instead of raising, so callers can report partial successes."""
    return _install_groups([group] if group else list(_INSTALL_ORDER))


def _install_groups(groups: list[str]) -> InstallResult:
    result = InstallResult()
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    python = _python_console_executable()
    log: list[str] = []

    for grp in groups:
        deps = _dependencies_for_group(grp)
        packages = [d.package for d in deps if importlib.util.find_spec(d.import_name) is None]
        if not packages:
            continue
        command = [python, "-m", "pip", "install", *packages]
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
        )
        log.append(f"--- {grp} ---")
        log.append(completed.stdout)
        if completed.returncode == 0:
            result.succeeded.append(grp)
        else:
            result.failed.append(grp)

    result.output = "\n".join(log)
    return result


def _dependencies_for_group(group: str) -> list[OptionalDependency]:
    packages = DEPENDENCY_GROUPS.get(group, ())
    matched: list[OptionalDependency] = []
    for dependency in OPTIONAL_DEPENDENCIES:
        if dependency.package in packages:
            matched.append(dependency)
    return matched


def _python_console_executable() -> str:
    executable = Path(sys.executable)
    if executable.name.lower() == "pythonw.exe":
        console = executable.with_name("python.exe")
        if console.exists():
            return str(console)
    return str(executable)
