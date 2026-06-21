from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk
from urllib.parse import unquote

PALETTE = {
    "bg": "#f4f5f7",
    "card": "#ffffff",
    "card_alt": "#fafbfc",
    "accent": "#4f46e5",
    "accent_hover": "#4338ca",
    "accent_pressed": "#3730a3",
    "success": "#16a34a",
    "danger": "#dc2626",
    "warning": "#d97706",
    "skipped": "#6b7280",
    "text": "#1f2937",
    "muted": "#6b7280",
    "border": "#e5e7eb",
    "border_focus": "#c7d2fe",
    "row_alt": "#f9fafb",
    "row_selected": "#eef2ff",
}

DND_AVAILABLE = False
DND_FILES = None
try:
    from tkinterdnd2 import DND_FILES as _DND_FILES  # type: ignore

    DND_FILES = _DND_FILES
    DND_AVAILABLE = True
except Exception:
    DND_AVAILABLE = False


def apply_theme(root: tk.Tk) -> ttk.Style:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    p = PALETTE

    style.configure(".", background=p["bg"], foreground=p["text"], font=("Segoe UI", 10))
    style.configure("TFrame", background=p["bg"])
    style.configure("Card.TFrame", background=p["card"])
    style.configure("TLabel", background=p["bg"], foreground=p["text"])
    style.configure("Card.TLabel", background=p["card"], foreground=p["text"])
    style.configure("Muted.TLabel", background=p["bg"], foreground=p["muted"], font=("Segoe UI", 9))
    style.configure("MutedCard.TLabel", background=p["card"], foreground=p["muted"], font=("Segoe UI", 9))
    style.configure("Title.TLabel", background=p["bg"], foreground=p["text"], font=("Segoe UI Semibold", 16))
    style.configure("Subtitle.TLabel", background=p["bg"], foreground=p["muted"], font=("Segoe UI", 10))
    style.configure("Stat.TLabel", background=p["card"], foreground=p["text"], font=("Segoe UI Semibold", 18))
    style.configure("StatCap.TLabel", background=p["card"], foreground=p["muted"], font=("Segoe UI", 9))

    style.configure("TButton", background=p["card"], foreground=p["text"], bordercolor=p["border"],
                    focuscolor=p["border"], font=("Segoe UI", 10), padding=(14, 8), relief="flat")
    style.map("TButton",
              background=[("active", p["card_alt"]), ("disabled", p["card_alt"])],
              foreground=[("disabled", p["muted"])])

    style.configure("Primary.TButton", background=p["accent"], foreground="#ffffff",
                    bordercolor=p["accent"], font=("Segoe UI Semibold", 10), padding=(18, 10), relief="flat")
    style.map("Primary.TButton",
              background=[("active", p["accent_hover"]), ("pressed", p["accent_pressed"]), ("disabled", "#c7d2fe")],
              foreground=[("disabled", "#ffffff")])

    style.configure("Danger.TButton", background=p["danger"], foreground="#ffffff",
                    bordercolor=p["danger"], font=("Segoe UI Semibold", 10), padding=(14, 10), relief="flat")
    style.map("Danger.TButton",
              background=[("active", "#b91c1c"), ("pressed", "#991b1b"), ("disabled", "#fca5a5")])

    style.configure("Ghost.TButton", background=p["bg"], foreground=p["text"],
                    bordercolor=p["border"], font=("Segoe UI", 10), padding=(12, 8), relief="flat")
    style.map("Ghost.TButton",
              background=[("active", p["card_alt"])],
              foreground=[("disabled", p["muted"])])

    style.configure("TCheckbutton", background=p["card"], foreground=p["text"], focuscolor=p["card"],
                    font=("Segoe UI", 10))
    style.map("TCheckbutton", background=[("active", p["card"])])
    style.configure("CardCheck.TCheckbutton", background=p["card"], foreground=p["text"], font=("Segoe UI", 10))

    style.configure("TEntry", fieldbackground=p["card"], foreground=p["text"], bordercolor=p["border"],
                    focuscolor=p["accent"], padding=6, relief="solid")
    style.configure("TSpinbox", fieldbackground=p["card"], foreground=p["text"], bordercolor=p["border"],
                    arrowcolor=p["accent"], padding=4)

    style.configure("TLabelframe", background=p["card"], foreground=p["text"], bordercolor=p["border"],
                    relief="solid")
    style.configure("TLabelframe.Label", background=p["card"], foreground=p["muted"],
                    font=("Segoe UI Semibold", 10))

    style.configure("Treeview", background=p["card"], fieldbackground=p["card"], foreground=p["text"],
                    bordercolor=p["border"], rowheight=26, font=("Segoe UI", 9))
    style.configure("Treeview.Heading", background=p["card_alt"], foreground=p["text"],
                    bordercolor=p["border"], font=("Segoe UI Semibold", 9), relief="flat", padding=(8, 6))
    style.map("Treeview",
              background=[("selected", p["row_selected"])],
              foreground=[("selected", p["text"])])
    style.map("Treeview.Heading", background=[("active", p["card_alt"])])

    style.configure("Horizontal.TProgressbar", background=p["accent"], troughcolor=p["border"],
                    bordercolor=p["border"], thickness=10)

    style.configure("TScrollbar", background=p["card"], troughcolor=p["bg"],
                    bordercolor=p["bg"], arrowcolor=p["muted"])
    style.map("TScrollbar", background=[("active", p["card_alt"])])

    try:
        root.option_add("*TCombobox*Listbox.background", p["card"])
        root.option_add("*TCombobox*Listbox.foreground", p["text"])
        root.option_add("*TCombobox*Listbox.selectBackground", p["row_selected"])
        root.option_add("*TCombobox*Listbox.selectForeground", p["text"])
    except Exception:
        pass

    return style


def parse_dnd_paths(data: str) -> list[str]:
    paths: list[str] = []
    for token in data.split():
        token = token.strip()
        if token.startswith("{") and token.endswith("}"):
            token = token[1:-1]
        paths.append(unquote(token))
    return paths


class DropZone(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        title: str,
        hint: str,
        on_browse: object,
        on_drop: object,
        height: int = 110,
        change_hint: str = "",
    ) -> None:
        super().__init__(master, style="Card.TFrame")
        self._title = title
        self._hint = hint
        self._change_hint = change_hint or "Click or drop to change"
        self._on_browse = on_browse
        self._on_drop = on_drop
        self._path: str = ""
        self._height = height
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._canvas = tk.Canvas(self, height=height, bg=PALETTE["card"],
                                 highlightthickness=2, highlightbackground=PALETTE["border"],
                                 highlightcolor=PALETTE["accent"], bd=0)
        self._canvas.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self._draw()
        self._canvas.bind("<Button-1>", lambda _e: self._browse())
        self._canvas.bind("<Configure>", lambda _e: self._draw())

        if DND_AVAILABLE:
            try:
                self._canvas.drop_target_register(DND_FILES)  # type: ignore[attr-defined]
                self._canvas.dnd_bind("<<Drop>>", self._handle_drop)  # type: ignore[attr-defined]
                self._canvas.dnd_bind("<<DragEnter>>", self._handle_drag_enter)  # type: ignore[attr-defined]
                self._canvas.dnd_bind("<<DragLeave>>", self._handle_drag_leave)  # type: ignore[attr-defined]
            except Exception:
                pass

    def set_texts(self, title: str, hint: str, change_hint: str = "") -> None:
        self._title = title
        self._hint = hint
        if change_hint:
            self._change_hint = change_hint
        self._draw()

    def set_path(self, path: str) -> None:
        self._path = path
        self._draw()

    def get_path(self) -> str:
        return self._path

    def _browse(self) -> None:
        if callable(self._on_browse):
            self._on_browse()

    def _handle_drop(self, event) -> None:  # type: ignore[no-untyped-def]
        paths = parse_dnd_paths(event.data)
        if paths and callable(self._on_drop):
            self._on_drop(paths[0])
        self._canvas.configure(highlightbackground=PALETTE["border"])

    def _handle_drag_enter(self, event) -> None:  # type: ignore[no-untyped-def]
        self._canvas.configure(highlightbackground=PALETTE["accent"])

    def _handle_drag_leave(self, event) -> None:  # type: ignore[no-untyped-def]
        self._canvas.configure(highlightbackground=PALETTE["border"])

    def _draw(self) -> None:
        canvas = self._canvas
        canvas.delete("all")
        width = canvas.winfo_width() or 480
        height = canvas.winfo_height() or self._height
        if width < 2:
            width = 480
        if height < 2:
            height = self._height
        cx = width / 2
        if self._path:
            name = Path(self._path).name or self._path
            canvas.create_text(cx, height / 2 - 10, text=name, fill=PALETTE["text"],
                               font=("Segoe UI Semibold", 11))
            canvas.create_text(cx, height / 2 + 12, text=self._path, fill=PALETTE["muted"],
                               font=("Segoe UI", 8), width=width - 24)
            canvas.create_text(cx, height - 12, text=self._change_hint,
                               fill=PALETTE["muted"], font=("Segoe UI", 8))
        else:
            icon_y = height / 2 - 18
            canvas.create_text(cx, icon_y, text="\u2913", fill=PALETTE["accent"],
                               font=("Segoe UI", 24))
            canvas.create_text(cx, icon_y + 28, text=self._title, fill=PALETTE["text"],
                               font=("Segoe UI Semibold", 11))
            canvas.create_text(cx, icon_y + 48, text=self._hint, fill=PALETTE["muted"],
                               font=("Segoe UI", 9))
