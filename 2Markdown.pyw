from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path
from tkinter import messagebox


def _project_root() -> Path:
    launch_dir = Path(__file__).resolve().parent
    for candidate in (launch_dir / "v0.20", launch_dir):
        if (candidate / "two_markdown").is_dir():
            return candidate
    return launch_dir


try:
    ROOT = _project_root()
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    runpy.run_module("two_markdown", run_name="__main__")
except Exception as exc:
    messagebox.showerror(
        "2Markdown",
        "Unable to start 2Markdown.\n\n"
        "Make sure Python 3.10+ is installed, then try opening this file again.\n\n"
        f"Details: {exc}",
    )
