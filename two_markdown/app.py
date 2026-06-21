from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import i18n
from .batch import BatchConverter
from .config import load_config, save_config
from .dependencies import (
    InstallResult,
    OptionalDependency,
    OptionalDependencyInstallError,
    install_optional_dependencies_grouped,
    missing_optional_dependencies,
)
from .errors import MissingDependencyError
from .models import BatchSummary, ConversionOptions, ConversionRecord
from .ui_theme import DND_AVAILABLE, PALETTE, DropZone, apply_theme

try:
    from tkinterdnd2 import TkinterDnD  # type: ignore

    _BaseTk = TkinterDnD.Tk
except Exception:
    _BaseTk = tk.Tk


class MarkdownApp(_BaseTk):
    def __init__(self) -> None:
        super().__init__()
        self._config = load_config()
        i18n.set_language(self._config.get("language", "en"))
        self.title("2Markdown")
        self.geometry("1060x780")
        self.minsize(880, 620)
        self.configure(background=PALETTE["bg"])

        self.source_var = tk.StringVar(value=self._config.get("last_source", ""))
        self.output_var = tk.StringVar(value=self._config.get("last_output", ""))
        self._source_include: list[str] | None = None
        self.preserve_tree_var = tk.BooleanVar(value=bool(self._config.get("preserve_tree", True)))
        self.attachments_var = tk.BooleanVar(value=bool(self._config.get("extract_attachments", True)))
        self.frontmatter_var = tk.BooleanVar(value=bool(self._config.get("write_frontmatter", True)))
        self.metadata_var = tk.BooleanVar(value=bool(self._config.get("include_metadata", True)))
        self.overwrite_var = tk.BooleanVar(value=bool(self._config.get("overwrite", False)))
        self.incremental_var = tk.BooleanVar(value=bool(self._config.get("incremental", False)))
        self.dry_run_var = tk.BooleanVar(value=bool(self._config.get("dry_run", False)))
        self.resume_var = tk.BooleanVar(value=bool(self._config.get("resume", False)))
        self.download_remote_var = tk.BooleanVar(value=bool(self._config.get("download_remote", False)))
        self.recurse_archives_var = tk.BooleanVar(value=bool(self._config.get("recurse_archives", False)))
        self.ocr_var = tk.BooleanVar(value=bool(self._config.get("ocr", False)))
        self.ocr_lang_var = tk.StringVar(value=self._config.get("ocr_lang", "eng"))
        self.audio_lang_var = tk.StringVar(value=self._config.get("audio_lang", ""))
        self.concurrency_var = tk.IntVar(value=int(self._config.get("concurrency", 1)))
        self.max_size_var = tk.StringVar(value=str(self._config.get("max_size_mb", "")))
        self.lang_var = tk.StringVar(value=i18n.current_language())
        self.status_var = tk.StringVar(value=i18n.t("status_idle"))
        self.progress_var = tk.DoubleVar(value=0)

        self._queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._cancel_event = threading.Event()
        self._installing = False
        self._counts = {"success": 0, "failed": 0, "skipped": 0}
        self._advanced_visible = False

        apply_theme(self)
        self._build_ui()
        self._apply_texts()
        self._maybe_offer_install()
        self.after(100, self._poll_queue)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=(20, 16, 20, 16))
        outer.pack(fill=tk.BOTH, expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(4, weight=1)

        self._build_header(outer)
        self._build_drop_zones(outer)
        self._build_options(outer)
        self._build_actions(outer)
        self._build_results(outer)
        self._build_progress(outer)

    def _build_header(self, parent: ttk.Frame) -> None:
        header = ttk.Frame(parent)
        header.grid(row=0, column=0, sticky=tk.EW, pady=(0, 14))
        header.columnconfigure(1, weight=1)
        badge = tk.Canvas(header, width=44, height=44, bg=PALETTE["bg"], highlightthickness=0)
        badge.create_oval(2, 2, 42, 42, fill=PALETTE["accent"], outline="")
        badge.create_text(22, 23, text="2M", fill="#ffffff", font=("Segoe UI Semibold", 14))
        badge.grid(row=0, column=0, padx=(0, 14), rowspan=2)
        titles = ttk.Frame(header)
        titles.grid(row=0, column=1, sticky=tk.W)
        self.title_label = ttk.Label(titles, text="2Markdown", style="Title.TLabel")
        self.title_label.pack(anchor=tk.W)
        self.subtitle_label = ttk.Label(titles, style="Subtitle.TLabel")
        self.subtitle_label.pack(anchor=tk.W)

        right = ttk.Frame(header)
        right.grid(row=0, column=2, sticky=tk.NE)
        lang_row = ttk.Frame(right)
        lang_row.pack(anchor=tk.E)
        self.lang_combo = ttk.Combobox(lang_row, textvariable=self.lang_var, state="readonly", width=14)
        self.lang_combo["values"] = [name for _code, name in i18n.available_languages()]
        self.lang_combo.pack(side=tk.RIGHT)
        self.lang_label = ttk.Label(lang_row, style="Muted.TLabel")
        self.lang_label.pack(side=tk.RIGHT, padx=(0, 6))
        self.lang_combo.bind("<<ComboboxSelected>>", self._change_language)
        stats_row = ttk.Frame(right)
        stats_row.pack(anchor=tk.E, pady=(8, 0))
        self._stat_success = self._stat_card(stats_row, "success", PALETTE["success"], 0)
        self._stat_success.grid(row=0, column=0, padx=(0, 6))
        self._stat_failed = self._stat_card(stats_row, "failed", PALETTE["danger"], 0)
        self._stat_failed.grid(row=0, column=1, padx=6)
        self._stat_skipped = self._stat_card(stats_row, "skipped", PALETTE["skipped"], 0)
        self._stat_skipped.grid(row=0, column=2, padx=(6, 0))

    def _stat_card(self, parent: tk.Widget, caption_key: str, color: str, value: int) -> ttk.Frame:
        card = ttk.Frame(parent, style="Card.TFrame", padding=(16, 8))
        card.columnconfigure(0, weight=1)
        value_label = ttk.Label(card, text=str(value), style="Stat.TLabel")
        value_label.configure(foreground=color)
        value_label.grid(row=0, column=0)
        cap = ttk.Label(card, text=i18n.t(caption_key), style="StatCap.TLabel")
        cap.grid(row=1, column=0)
        card._value_label = value_label  # type: ignore[attr-defined]
        card._cap_label = cap  # type: ignore[attr-defined]
        return card

    def _set_stat(self, card: ttk.Frame, value: int) -> None:
        label = getattr(card, "_value_label", None)
        if label is not None:
            label.configure(text=str(value))

    def _build_drop_zones(self, parent: ttk.Frame) -> None:
        row = ttk.Frame(parent)
        row.grid(row=1, column=0, sticky=tk.EW, pady=(0, 14))
        row.columnconfigure(0, weight=1, uniform="zone")
        row.columnconfigure(1, weight=1, uniform="zone")
        self.source_zone = DropZone(
            row, "", "",
            on_browse=self._choose_source, on_drop=self._drop_source,
            change_hint=i18n.t("or_click_browse"),
        )
        self.source_zone.grid(row=0, column=0, sticky=tk.NSEW, padx=(0, 10))
        self.output_zone = DropZone(
            row, "", "",
            on_browse=self._choose_output, on_drop=self._drop_output,
            change_hint=i18n.t("or_click_browse"),
        )
        self.output_zone.grid(row=0, column=1, sticky=tk.NSEW, padx=(10, 0))

    def _build_options(self, parent: ttk.Frame) -> None:
        wrap = ttk.Frame(parent)
        wrap.grid(row=2, column=0, sticky=tk.EW, pady=(0, 12))
        wrap.columnconfigure(0, weight=1)

        primary = ttk.Frame(wrap, style="Card.TFrame", padding=14)
        primary.grid(row=0, column=0, sticky=tk.EW)
        primary.columnconfigure(2, weight=1)
        for col in range(4):
            primary.columnconfigure(col, weight=1)
        self.primary_checks: list[ttk.Checkbutton] = []
        self.primary_check_keys = [
            ("keep_tree", self.preserve_tree_var),
            ("attachments", self.attachments_var),
            ("frontmatter", self.frontmatter_var),
            ("metadata", self.metadata_var),
        ]
        for index, (key, var) in enumerate(self.primary_check_keys):
            cb = ttk.Checkbutton(primary, text=i18n.t(key), variable=var, style="CardCheck.TCheckbutton")
            cb.grid(row=0, column=index, sticky=tk.W, padx=(0, 12))
            self.primary_checks.append(cb)
        self.advanced_toggle = ttk.Button(primary, text=i18n.t("show_advanced"), style="Ghost.TButton", command=self._toggle_advanced)
        self.advanced_toggle.grid(row=0, column=4, sticky=tk.E)

        self.advanced_card = ttk.Frame(wrap, style="Card.TFrame", padding=14)
        for col in range(4):
            self.advanced_card.columnconfigure(col, weight=1)
        self.advanced_checks: list[ttk.Checkbutton] = []
        self.advanced_check_keys = [
            ("overwrite", self.overwrite_var),
            ("incremental", self.incremental_var),
            ("dry_run", self.dry_run_var),
            ("resume", self.resume_var),
            ("download_remote", self.download_remote_var),
            ("recurse_archives", self.recurse_archives_var),
            ("ocr", self.ocr_var),
        ]
        for index, (key, var) in enumerate(self.advanced_check_keys):
            r, c = divmod(index, 4)
            cb = ttk.Checkbutton(self.advanced_card, text=i18n.t(key), variable=var, style="CardCheck.TCheckbutton")
            cb.grid(row=r, column=c, sticky=tk.W, padx=(0, 12), pady=4)
            self.advanced_checks.append(cb)
        inputs = ttk.Frame(self.advanced_card, style="Card.TFrame")
        inputs.grid(row=4, column=0, columnspan=4, sticky=tk.W, pady=(10, 0))
        self.lbl_concurrency = ttk.Label(inputs, style="MutedCard.TLabel")
        self.lbl_concurrency.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Spinbox(inputs, from_=1, to=16, width=4, textvariable=self.concurrency_var).pack(side=tk.LEFT, padx=(0, 16))
        self.lbl_ocr_lang = ttk.Label(inputs, style="MutedCard.TLabel")
        self.lbl_ocr_lang.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Entry(inputs, textvariable=self.ocr_lang_var, width=12).pack(side=tk.LEFT, padx=(0, 16))
        self.lbl_audio_lang = ttk.Label(inputs, style="MutedCard.TLabel")
        self.lbl_audio_lang.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Entry(inputs, textvariable=self.audio_lang_var, width=10).pack(side=tk.LEFT, padx=(0, 16))
        self.lbl_max_size = ttk.Label(inputs, style="MutedCard.TLabel")
        self.lbl_max_size.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Entry(inputs, textvariable=self.max_size_var, width=8).pack(side=tk.LEFT)

    def _toggle_advanced(self) -> None:
        self._advanced_visible = not self._advanced_visible
        if self._advanced_visible:
            self.advanced_card.grid(row=1, column=0, sticky=tk.EW, pady=(8, 0))
            self.advanced_toggle.configure(text=i18n.t("hide_advanced"))
        else:
            self.advanced_card.grid_forget()
            self.advanced_toggle.configure(text=i18n.t("show_advanced"))

    def _build_actions(self, parent: ttk.Frame) -> None:
        bar = ttk.Frame(parent)
        bar.grid(row=3, column=0, sticky=tk.EW, pady=(0, 12))
        self.start_button = ttk.Button(bar, text=i18n.t("start"), style="Primary.TButton", command=self._start)
        self.start_button.pack(side=tk.LEFT)
        self.cancel_button = ttk.Button(bar, text=i18n.t("cancel"), style="Danger.TButton", command=self._cancel, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT, padx=(10, 0))
        self.open_button = ttk.Button(bar, text=i18n.t("open_output"), style="Ghost.TButton", command=self._open_output, state=tk.DISABLED)
        self.open_button.pack(side=tk.LEFT, padx=(10, 0))
        self.install_button = ttk.Button(bar, text=i18n.t("install"), style="Ghost.TButton", command=self._click_install)
        self.install_button.pack(side=tk.LEFT, padx=(10, 0))
        self.dnd_note = ttk.Label(bar, style="Muted.TLabel")
        self.dnd_note.pack(side=tk.LEFT, padx=(12, 0))

    def _build_results(self, parent: ttk.Frame) -> None:
        paned = ttk.PanedWindow(parent, orient=tk.VERTICAL)
        paned.grid(row=4, column=0, sticky=tk.NSEW, pady=(0, 8))

        table_card = ttk.Frame(paned, style="Card.TFrame", padding=2)
        table_card.columnconfigure(0, weight=1)
        table_card.rowconfigure(0, weight=1)
        columns = ("status", "source", "output", "message")
        self.table = ttk.Treeview(table_card, columns=columns, show="headings", style="Treeview")
        widths = {"status": 90, "source": 300, "output": 300, "message": 240}
        for column in columns:
            self.table.heading(column, text=column.title())
            self.table.column(column, width=widths[column], anchor=tk.W)
        self.table.tag_configure("success", foreground=PALETTE["success"])
        self.table.tag_configure("failed", foreground=PALETTE["danger"])
        self.table.tag_configure("skipped", foreground=PALETTE["skipped"])
        self.table.grid(row=0, column=0, sticky=tk.NSEW)
        vsb = ttk.Scrollbar(table_card, orient=tk.VERTICAL, command=self.table.yview)
        vsb.grid(row=0, column=1, sticky=tk.NS)
        self.table.configure(yscrollcommand=vsb.set)
        paned.add(table_card, weight=3)

        log_card = ttk.Frame(paned, style="Card.TFrame", padding=8)
        log_card.columnconfigure(0, weight=1)
        log_card.rowconfigure(1, weight=1)
        self.log_label = ttk.Label(log_card, style="MutedCard.TLabel")
        self.log_label.grid(row=0, column=0, sticky=tk.W)
        self.log_text = tk.Text(log_card, height=6, bg=PALETTE["card"], fg=PALETTE["text"],
                                relief="flat", bd=0, font=("Consolas", 9), wrap=tk.WORD,
                                highlightthickness=1, highlightbackground=PALETTE["border"],
                                highlightcolor=PALETTE["border"], padx=8, pady=6)
        self.log_text.grid(row=1, column=0, sticky=tk.NSEW)
        self.log_text.configure(state=tk.DISABLED)
        hsb = ttk.Scrollbar(log_card, orient=tk.HORIZONTAL, command=self.log_text.xview)
        hsb.grid(row=2, column=0, sticky=tk.EW)
        self.log_text.configure(xscrollcommand=hsb.set)
        paned.add(log_card, weight=1)

    def _build_progress(self, parent: ttk.Frame) -> None:
        bar = ttk.Frame(parent)
        bar.grid(row=5, column=0, sticky=tk.EW)
        bar.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(bar, variable=self.progress_var, maximum=100, style="Horizontal.TProgressbar")
        self.progress.grid(row=0, column=0, sticky=tk.EW)
        self.status_label = ttk.Label(bar, textvariable=self.status_var, style="Muted.TLabel")
        self.status_label.grid(row=1, column=0, sticky=tk.W, pady=(6, 0))

    def _apply_texts(self) -> None:
        self.title_label.configure(text=i18n.t("app_title"))
        self.subtitle_label.configure(text=i18n.t("app_subtitle"))
        self.source_zone.set_texts(i18n.t("source_zone_title"), i18n.t("source_zone_hint"), i18n.t("or_click_browse"))
        self.output_zone.set_texts(i18n.t("output_zone_title"), i18n.t("output_zone_hint"), i18n.t("or_click_browse"))
        if self.source_var.get():
            self.source_zone.set_path(self.source_var.get())
        if self.output_var.get():
            self.output_zone.set_path(self.output_var.get())
        for cb, (key, _var) in zip(self.primary_checks, self.primary_check_keys):
            cb.configure(text=i18n.t(key))
        for cb, (key, _var) in zip(self.advanced_checks, self.advanced_check_keys):
            cb.configure(text=i18n.t(key))
        self.advanced_toggle.configure(text=i18n.t("hide_advanced" if self._advanced_visible else "show_advanced"))
        self.start_button.configure(text=i18n.t("start"))
        self.cancel_button.configure(text=i18n.t("cancel"))
        self.open_button.configure(text=i18n.t("open_output"))
        self.install_button.configure(text=i18n.t("install"))
        self.lang_label.configure(text=i18n.t("language"))
        self.lbl_concurrency.configure(text=i18n.t("concurrency"))
        self.lbl_ocr_lang.configure(text=i18n.t("ocr_lang"))
        self.lbl_audio_lang.configure(text=i18n.t("audio_lang"))
        self.lbl_max_size.configure(text=i18n.t("max_size"))
        self.log_label.configure(text=i18n.t("log"))
        for col, key in zip(("status", "source", "output", "message"), ("col_status", "col_source", "col_output", "col_message")):
            self.table.heading(col, text=i18n.t(key))
        for card, key in ((self._stat_success, "success"), (self._stat_failed, "failed"), (self._stat_skipped, "skipped")):
            cap = getattr(card, "_cap_label", None)
            if cap is not None:
                cap.configure(text=i18n.t(key))
        if not DND_AVAILABLE:
            self.dnd_note.configure(text=i18n.t("tip_dnd_unavailable"))
        else:
            self.dnd_note.configure(text="")
        self.status_var.set(i18n.t("status_idle"))

    def _change_language(self, _event: object = None) -> None:
        code = self._code_for_display(self.lang_var.get())
        i18n.set_language(code)
        self._config["language"] = code
        save_config(self._config)
        self._apply_texts()

    def _code_for_display(self, display: str) -> str:
        for code, name in i18n.available_languages():
            if name == display:
                return code
        return "en"

    def _choose_source(self) -> None:
        target = filedialog.askdirectory(title=i18n.t("source_zone_title"))
        if target:
            self._set_source(target, is_file=False)

    def _choose_output(self) -> None:
        target = filedialog.askdirectory(title=i18n.t("output_zone_title"))
        if target:
            self._set_output(target)

    def _drop_source(self, path: str) -> None:
        p = Path(path)
        if p.is_file():
            self._set_source(str(p.parent), is_file=True, include=p.name)
        else:
            self._set_source(str(p), is_file=False)

    def _drop_output(self, path: str) -> None:
        self._set_output(path)

    def _set_source(self, path: str, *, is_file: bool = False, include: str | None = None) -> None:
        self.source_var.set(path)
        self.source_zone.set_path(path if not is_file else f"{path} / {include}")
        self._source_include = [include] if include else None
        self._config["last_source"] = path
        save_config(self._config)
        if not self.output_var.get().strip():
            self._auto_set_output(Path(path))

    def _set_output(self, path: str) -> None:
        self.output_var.set(path)
        self.output_zone.set_path(path)
        self._config["last_output"] = path
        save_config(self._config)

    def _auto_set_output(self, source: Path) -> None:
        if not source.exists():
            return
        candidate = source.parent / f"{source.name}_markdown"
        self._set_output(str(candidate))
        self.status_var.set(i18n.t("output_auto_set", path=str(candidate)))

    def _open_output(self) -> None:
        output = self.output_var.get().strip()
        if not output or not Path(output).is_dir():
            return
        _open_in_file_manager(Path(output))

    def _maybe_offer_install(self) -> None:
        missing = missing_optional_dependencies()
        if not missing:
            self.install_button.pack_forget()
            self.status_var.set(i18n.t("status_idle"))
            return
        if self._config.get("asked_install_all"):
            self.status_var.set(i18n.t("status_install_skipped"))
            self._log(_missing_summary(missing))
            return
        choice = messagebox.askyesnocancel(
            i18n.t("dialog_install_title"),
            i18n.t("welcome_msg") + "\n\n" + i18n.t("dialog_install_msg"),
            default=messagebox.YES,
        )
        self._config["asked_install_all"] = True
        save_config(self._config)
        if choice is None:
            self.status_var.set(i18n.t("status_install_skipped"))
        elif choice:
            self._start_install()
        else:
            self.status_var.set(i18n.t("status_install_skipped"))

    def _click_install(self) -> None:
        if self._installing:
            return
        self._start_install()

    def _start_install(self) -> None:
        if self._installing:
            return
        self._installing = True
        self.install_button.configure(state=tk.DISABLED)
        self.status_var.set(i18n.t("status_installing"))
        self._log(i18n.t("status_installing"))
        threading.Thread(target=self._install_thread, daemon=True).start()

    def _install_thread(self) -> None:
        try:
            result = install_optional_dependencies_grouped()
            self._queue.put(("deps_result", result))
        except Exception as exc:
            self._queue.put(("deps_error", exc))

    def _handle_install_result(self, result: InstallResult) -> None:
        self._installing = False
        self._set_running(False)
        still_missing = missing_optional_dependencies()
        if not still_missing:
            self.install_button.pack_forget()
            self.status_var.set(i18n.t("status_install_done"))
            self._log(i18n.t("status_install_done"))
            return
        self.install_button.configure(state=tk.NORMAL)
        if result.succeeded:
            names = ", ".join(result.succeeded)
            self._log(f"Installed: {names}")
            self.status_var.set(i18n.t("status_install_skipped"))
            if result.failed:
                failed_names = ", ".join(result.failed)
                self._log(f"Failed groups: {failed_names}")
                messagebox.showwarning(
                    "2Markdown",
                    f"{i18n.t('status_install_skipped')}\n\n"
                    f"Installed: {names}\n"
                    f"Failed: {failed_names}",
                )
        else:
            detail = result.output[-1000:]
            self._log(f"Install failed: {detail}")
            self.status_var.set(i18n.t("status_install_failed"))
            messagebox.showwarning("2Markdown", i18n.t("status_install_failed") + "\n\n" + detail)

    def _start(self) -> None:
        if self._installing:
            messagebox.showinfo("2Markdown", i18n.t("dialog_busy"))
            return
        source_text = self.source_var.get().strip()
        if not source_text or not Path(source_text).is_dir():
            messagebox.showerror("2Markdown", i18n.t("dialog_invalid_source"))
            return
        output_text = self.output_var.get().strip()
        if not output_text:
            self._auto_set_output(Path(source_text))
            output_text = self.output_var.get().strip()
        if not output_text:
            messagebox.showerror("2Markdown", i18n.t("dialog_invalid_output"))
            return

        for item in self.table.get_children():
            self.table.delete(item)
        self._counts = {"success": 0, "failed": 0, "skipped": 0}
        self._set_stat(self._stat_success, 0)
        self._set_stat(self._stat_failed, 0)
        self._set_stat(self._stat_skipped, 0)
        self.progress_var.set(0)
        self._cancel_event.clear()
        self._set_running(True)
        self.open_button.configure(state=tk.DISABLED)
        self.status_var.set(i18n.t("status_converting", index=0, total=0))

        options = self._build_options_object(source_text, output_text)
        self._log(f"{source_text} -> {output_text}")
        self._worker = threading.Thread(target=self._run_batch, args=(options,), daemon=True)
        self._worker.start()

    def _build_options_object(self, source_text: str, output_text: str) -> ConversionOptions:
        max_size = None
        raw_size = self.max_size_var.get().strip()
        if raw_size:
            try:
                max_size = float(raw_size)
            except ValueError:
                max_size = None
        audio_lang = self.audio_lang_var.get().strip() or None
        return ConversionOptions(
            source_dir=Path(source_text),
            output_dir=Path(output_text),
            preserve_tree=self.preserve_tree_var.get(),
            extract_attachments=self.attachments_var.get(),
            write_frontmatter=self.frontmatter_var.get(),
            overwrite=self.overwrite_var.get(),
            include_metadata=self.metadata_var.get(),
            incremental=self.incremental_var.get(),
            dry_run=self.dry_run_var.get(),
            resume=self.resume_var.get(),
            download_remote=self.download_remote_var.get(),
            ocr=self.ocr_var.get(),
            ocr_lang=self.ocr_lang_var.get().strip() or "eng",
            audio_lang=audio_lang,
            recurse_archives=self.recurse_archives_var.get(),
            concurrency=max(1, int(self.concurrency_var.get())),
            max_file_size_mb=max_size,
            include_globs=self._source_include,
        )

    def _cancel(self) -> None:
        self._cancel_event.set()
        self.status_var.set(i18n.t("status_cancelling"))

    def _run_batch(self, options: ConversionOptions) -> None:
        converter = BatchConverter()

        def progress(record: ConversionRecord, index: int, total: int) -> None:
            self._queue.put(("record", (record, index, total)))

        try:
            summary = converter.run(options, progress=progress, cancel_event=self._cancel_event)
            self._queue.put(("done", summary))
        except Exception as exc:
            self._queue.put(("error", exc))

    def _poll_queue(self) -> None:
        try:
            while True:
                event, payload = self._queue.get_nowait()
                if event == "record":
                    record, index, total = payload  # type: ignore[misc]
                    self._add_record(record)
                    self.progress_var.set((index / total) * 100 if total else 0)
                    self.status_var.set(i18n.t("status_converting", index=index, total=total))
                    self._log_record(record)
                elif event == "done":
                    self._finish(payload)  # type: ignore[arg-type]
                elif event == "error":
                    self._set_running(False)
                    self._log(f"Error: {payload}")
                    messagebox.showerror("2Markdown", str(payload))
                elif event == "deps_result":
                    self._handle_install_result(payload)  # type: ignore[arg-type]
                elif event == "deps_error":
                    self._installing = False
                    self.install_button.configure(state=tk.NORMAL)
                    self._set_running(False)
                    detail = payload.output[-1200:] if isinstance(payload, OptionalDependencyInstallError) else str(payload)
                    self._log(f"Install failed: {detail}")
                    self.status_var.set(i18n.t("status_install_failed"))
                    messagebox.showwarning("2Markdown", i18n.t("status_install_failed") + "\n\n" + detail)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _add_record(self, record: ConversionRecord) -> None:
        output = str(record.output_path) if record.output_path else ""
        message = record.error or "; ".join(record.warnings) or record.reason or ""
        tag = record.status
        self.table.insert("", tk.END, values=(record.status, str(record.source_path), output, message), tags=(tag,))
        if record.status in self._counts:
            self._counts[record.status] += 1
            card = {"success": self._stat_success, "failed": self._stat_failed, "skipped": self._stat_skipped}[record.status]
            self._set_stat(card, self._counts[record.status])

    def _finish(self, summary: BatchSummary) -> None:
        self._set_running(False)
        self.progress_var.set(100 if summary.total else 0)
        self._set_stat(self._stat_success, summary.succeeded)
        self._set_stat(self._stat_failed, summary.failed)
        self._set_stat(self._stat_skipped, summary.skipped)
        self.status_var.set(i18n.t("status_done", success=summary.succeeded, failed=summary.failed, skipped=summary.skipped))
        self._log(i18n.t("status_done", success=summary.succeeded, failed=summary.failed, skipped=summary.skipped))
        self._log(f"Report: {summary.report_csv}")
        if summary.total:
            self.open_button.configure(state=tk.NORMAL)
        self._maybe_offer_dep_install(summary)
        open_now = messagebox.askyesno(
            i18n.t("dialog_done_title"),
            i18n.t("dialog_done_msg", success=summary.succeeded, failed=summary.failed, skipped=summary.skipped),
            default=messagebox.YES,
        )
        if open_now:
            self._open_output()

    def _maybe_offer_dep_install(self, summary: BatchSummary) -> None:
        if self._installing:
            return
        failures: dict[str, int] = {}
        for record in summary.records:
            if record.status != "failed" or not record.error:
                continue
            feature = _missing_feature_from_error(record.error)
            if feature:
                failures[feature] = failures.get(feature, 0) + 1
        if not failures:
            return
        feature, count = next(iter(failures.items()))
        choice = messagebox.askyesno(
            i18n.t("dialog_need_install_title", feature=feature),
            i18n.t("dialog_need_install_msg", count=count, feature=feature),
            default=messagebox.YES,
        )
        if choice:
            self._start_install()

    def _log_record(self, record: ConversionRecord) -> None:
        label = record.output_path if record.output_path else (record.error or record.reason or "")
        self._log(f"[{record.status}] {record.source_path.name} -> {label}")

    def _log(self, message: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _set_running(self, running: bool) -> None:
        self.start_button.configure(state=tk.DISABLED if running else tk.NORMAL)
        self.cancel_button.configure(state=tk.NORMAL if running else tk.DISABLED)


def _missing_summary(missing: list[OptionalDependency]) -> str:
    return ", ".join(sorted({d.import_name for d in missing}))


def _missing_feature_from_error(error: str) -> str | None:
    if "optional package" not in error:
        return None
    marker = "package '"
    idx = error.find(marker)
    if idx < 0:
        return None
    rest = error[idx + len(marker):]
    end = rest.find("'")
    if end < 0:
        return None
    return rest[:end]


def _open_in_file_manager(path: Path) -> None:
    try:
        if os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif _sys_platform() == "darwin":
            os.system(f'open "{path}"')
        else:
            os.system(f'xdg-open "{path}"')
    except Exception:
        pass


def _sys_platform() -> str:
    import sys

    return sys.platform


def launch_app() -> None:
    app = MarkdownApp()
    app.mainloop()
