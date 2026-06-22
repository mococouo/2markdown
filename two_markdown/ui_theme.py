from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from urllib.parse import unquote

FONT_FAMILY = "Microsoft YaHei UI"

LIGHT_PALETTE = {
    "bg": "#eef2f6",
    "card": "#ffffff",
    "card_alt": "#f8fafc",
    "card_disabled": "#eef2f7",
    "panel": "#f6f8fb",
    "sidebar": "#172033",
    "sidebar_text": "#f8fafc",
    "sidebar_muted": "#aebbd0",
    "accent": "#2563eb",
    "accent_hover": "#1d4ed8",
    "accent_pressed": "#1e40af",
    "accent_disabled": "#bfdbfe",
    "accent_soft": "#dbeafe",
    "accent_alt": "#0f766e",
    "success": "#059669",
    "danger": "#dc2626",
    "danger_hover": "#b91c1c",
    "danger_pressed": "#991b1b",
    "danger_disabled": "#fca5a5",
    "warning": "#d97706",
    "skipped": "#64748b",
    "text": "#111827",
    "muted": "#64748b",
    "border": "#d7dee8",
    "border_focus": "#93c5fd",
    "row_alt": "#f8fafc",
    "row_selected": "#e0f2fe",
    "drop": "#f8fafc",
    "drop_hover": "#eff6ff",
    "drop_shadow": "#dde6f0",
    "chip": "#eaf2ff",
    "chip_text": "#1d4ed8",
}

DARK_PALETTE = {
    "bg": "#0f131a",
    "card": "#171c25",
    "card_alt": "#202634",
    "card_disabled": "#242a36",
    "panel": "#141922",
    "sidebar": "#070b13",
    "sidebar_text": "#f8fafc",
    "sidebar_muted": "#9aa7b9",
    "accent": "#38bdf8",
    "accent_hover": "#0ea5e9",
    "accent_pressed": "#0284c7",
    "accent_disabled": "#16445c",
    "accent_soft": "#12344a",
    "accent_alt": "#2dd4bf",
    "success": "#34d399",
    "danger": "#f87171",
    "danger_hover": "#ef4444",
    "danger_pressed": "#dc2626",
    "danger_disabled": "#5b2527",
    "warning": "#fbbf24",
    "skipped": "#94a3b8",
    "text": "#f8fafc",
    "muted": "#a7b0be",
    "border": "#2d3645",
    "border_focus": "#38bdf8",
    "row_alt": "#151a22",
    "row_selected": "#17324a",
    "drop": "#141922",
    "drop_hover": "#172235",
    "drop_shadow": "#0a0d13",
    "chip": "#13263a",
    "chip_text": "#dbeafe",
}

PALETTE = dict(LIGHT_PALETTE)

DND_AVAILABLE = False
DND_FILES = None
try:
    from tkinterdnd2 import DND_FILES as _DND_FILES  # type: ignore

    DND_FILES = _DND_FILES
    DND_AVAILABLE = True
except Exception:
    DND_AVAILABLE = False


def apply_theme(root: tk.Tk, *, dark: bool = False) -> ttk.Style:
    PALETTE.clear()
    PALETTE.update(DARK_PALETTE if dark else LIGHT_PALETTE)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    p = PALETTE

    style.configure(".", background=p["bg"], foreground=p["text"], font=(FONT_FAMILY, 10))
    style.configure("TFrame", background=p["bg"])
    style.configure("Card.TFrame", background=p["card"])
    style.configure("Action.TFrame", background=p["card"])
    style.configure("Sidebar.TFrame", background=p["sidebar"])
    style.configure("TLabel", background=p["bg"], foreground=p["text"])
    style.configure("Card.TLabel", background=p["card"], foreground=p["text"])
    style.configure("CardTitle.TLabel", background=p["card"], foreground=p["text"], font=(FONT_FAMILY, 17, "bold"))
    style.configure("Muted.TLabel", background=p["bg"], foreground=p["muted"], font=(FONT_FAMILY, 9))
    style.configure("MutedCard.TLabel", background=p["card"], foreground=p["muted"], font=(FONT_FAMILY, 9))
    style.configure("Title.TLabel", background=p["sidebar"], foreground=p["sidebar_text"], font=(FONT_FAMILY, 18, "bold"))
    style.configure("Subtitle.TLabel", background=p["bg"], foreground=p["muted"], font=(FONT_FAMILY, 10))
    style.configure("Hero.TLabel", background=p["bg"], foreground=p["text"], font=(FONT_FAMILY, 20, "bold"))
    style.configure("Section.TLabel", background=p["bg"], foreground=p["text"], font=(FONT_FAMILY, 11, "bold"))
    style.configure("ActionStatus.TLabel", background=p["card"], foreground=p["muted"], font=(FONT_FAMILY, 9))
    style.configure("SidebarMuted.TLabel", background=p["sidebar"], foreground=p["sidebar_muted"], font=(FONT_FAMILY, 9))
    style.configure("SidebarSection.TLabel", background=p["sidebar"], foreground=p["sidebar_text"], font=(FONT_FAMILY, 10, "bold"))
    style.configure("SidebarStep.TLabel", background=p["sidebar"], foreground=p["sidebar_muted"], font=(FONT_FAMILY, 9))
    style.configure("Stat.TLabel", background=p["card"], foreground=p["text"], font=(FONT_FAMILY, 18, "bold"))
    style.configure("StatCap.TLabel", background=p["card"], foreground=p["muted"], font=(FONT_FAMILY, 9))
    style.configure("Chip.TLabel", background=p["chip"], foreground=p["chip_text"],
                    font=(FONT_FAMILY, 9), padding=(10, 4))

    style.configure("TButton", background=p["card"], foreground=p["text"], bordercolor=p["border"],
                    focuscolor=p["border"], font=(FONT_FAMILY, 10), padding=(14, 8), relief="flat")
    style.map("TButton",
              background=[("active", p["card_alt"]), ("disabled", p["card_disabled"])],
              foreground=[("disabled", p["muted"])])

    style.configure("Primary.TButton", background=p["accent"], foreground="#ffffff",
                    bordercolor=p["accent"], font=(FONT_FAMILY, 10, "bold"), padding=(22, 11), relief="flat")
    style.map("Primary.TButton",
              background=[("active", p["accent_hover"]), ("pressed", p["accent_pressed"]), ("disabled", p["accent_disabled"])],
              foreground=[("disabled", "#ffffff")])

    style.configure("Danger.TButton", background=p["danger"], foreground="#ffffff",
                    bordercolor=p["danger"], font=(FONT_FAMILY, 10, "bold"), padding=(14, 10), relief="flat")
    style.map("Danger.TButton",
              background=[("active", p["danger_hover"]), ("pressed", p["danger_pressed"]), ("disabled", p["danger_disabled"])])

    style.configure("Ghost.TButton", background=p["card"], foreground=p["text"],
                    bordercolor=p["border"], font=(FONT_FAMILY, 10), padding=(12, 8), relief="flat")
    style.map("Ghost.TButton",
              background=[("active", p["card_alt"])],
              foreground=[("disabled", p["muted"])])

    style.configure("TCheckbutton", background=p["card"], foreground=p["text"], focuscolor=p["card"],
                    font=(FONT_FAMILY, 10))
    style.map("TCheckbutton", background=[("active", p["card"])])
    style.configure("CardCheck.TCheckbutton", background=p["card"], foreground=p["text"], font=(FONT_FAMILY, 10))
    style.configure("SidebarCheck.TCheckbutton", background=p["sidebar"], foreground=p["sidebar_text"],
                    focuscolor=p["sidebar"], font=(FONT_FAMILY, 9))
    style.map("SidebarCheck.TCheckbutton", background=[("active", p["sidebar"])],
              foreground=[("disabled", p["sidebar_muted"])])

    style.configure("TEntry", fieldbackground=p["card"], foreground=p["text"], bordercolor=p["border"],
                    focuscolor=p["accent"], padding=6, relief="solid")
    style.configure("TSpinbox", fieldbackground=p["card"], foreground=p["text"], bordercolor=p["border"],
                    arrowcolor=p["accent"], padding=4)
    style.configure("TCombobox", fieldbackground=p["card"], background=p["card"], foreground=p["text"],
                    bordercolor=p["border"], arrowcolor=p["accent"], padding=4)
    style.map("TCombobox",
              fieldbackground=[("readonly", p["card"])],
              foreground=[("readonly", p["text"])],
              background=[("readonly", p["card_alt"])])

    style.configure("TLabelframe", background=p["card"], foreground=p["text"], bordercolor=p["border"],
                    relief="solid")
    style.configure("TLabelframe.Label", background=p["card"], foreground=p["muted"],
                    font=(FONT_FAMILY, 10, "bold"))

    style.configure("Treeview", background=p["card"], fieldbackground=p["card"], foreground=p["text"],
                    bordercolor=p["border"], rowheight=30, font=(FONT_FAMILY, 9))
    style.configure("Treeview.Heading", background=p["card_alt"], foreground=p["text"],
                    bordercolor=p["border"], font=(FONT_FAMILY, 9, "bold"), relief="flat", padding=(8, 7))
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
        self._hovered = False
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._canvas = tk.Canvas(self, height=height, bg=PALETTE["card"],
                                 highlightthickness=0, bd=0)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._draw()
        self._canvas.bind("<Button-1>", lambda _e: self._browse())
        self._canvas.bind("<Configure>", lambda _e: self._draw())
        self._canvas.bind("<Enter>", lambda _e: self._set_hover(True))
        self._canvas.bind("<Leave>", lambda _e: self._set_hover(False))

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

    def refresh_theme(self) -> None:
        self._canvas.configure(bg=PALETTE["card"])
        self._draw()

    def _browse(self) -> None:
        if callable(self._on_browse):
            self._on_browse()

    def _handle_drop(self, event) -> None:  # type: ignore[no-untyped-def]
        paths = parse_dnd_paths(event.data)
        if paths and callable(self._on_drop):
            self._on_drop(paths[0])
        self._set_hover(False)

    def _handle_drag_enter(self, event) -> None:  # type: ignore[no-untyped-def]
        self._set_hover(True)

    def _handle_drag_leave(self, event) -> None:  # type: ignore[no-untyped-def]
        self._set_hover(False)

    def _set_hover(self, active: bool) -> None:
        if self._hovered == active:
            return
        self._hovered = active
        self._draw()

    def _round_rect(self, x1: float, y1: float, x2: float, y2: float, radius: float, **kwargs: object) -> None:
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        self._canvas.create_polygon(points, smooth=True, splinesteps=18, **kwargs)

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
        pad = 10
        fill = PALETTE["drop_hover"] if self._hovered else PALETTE["drop"]
        border = PALETTE["accent"] if self._hovered else PALETTE["border"]
        self._round_rect(pad + 3, pad + 5, width - pad + 1, height - pad + 3, 26,
                         fill=PALETTE["drop_shadow"], outline="")
        self._round_rect(pad, pad, width - pad, height - pad, 26,
                         fill=fill, outline="")
        canvas.create_rectangle(
            pad,
            pad,
            width - pad,
            height - pad,
            outline=border,
            width=2,
            dash=(8, 6),
        )
        if self._path:
            canvas.create_text(cx, height / 2, text=self._path, fill=PALETTE["text"],
                               font=(FONT_FAMILY, 15, "bold"), width=width - 64)
        else:
            canvas.create_text(cx, height / 2 - 42, text="+", fill=PALETTE["accent"],
                               font=(FONT_FAMILY, 30, "bold"))
            canvas.create_text(cx, height / 2 - 4, text=self._title, fill=PALETTE["text"],
                               font=(FONT_FAMILY, 15, "bold"), width=width - 64)
            canvas.create_text(cx, height / 2 + 26, text=self._hint, fill=PALETTE["muted"],
                               font=(FONT_FAMILY, 10), width=width - 72)
