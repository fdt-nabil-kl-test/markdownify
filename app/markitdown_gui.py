"""
Markdownify — convert documents to clean Markdown.

Two engines, one segmented switch:
  • Quick  (MarkItDown) — fast, lightweight. Great for Office files and text PDFs.
  • Deep   (Docling)     — slower, ML-powered. Handles scanned PDFs, tables, OCR.

Each converted file is written as <name>.md next to the original.
Packaged into a macOS .app and a Windows .exe.
"""

import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, ttk

APP_TITLE = "Markdownify"

# Dark-grey theme
BG = "#26282B"            # window body / tab body
HEADER_BG = "#33363B"     # header bar / tab strip
LOG_BG = "#1E1F22"        # log panel
FG = "#E6E6E6"            # primary text
SUBFG = "#9AA0A6"         # secondary text
ACCENT = "#3E6DA6"        # brand blue
ACCENT_HOVER = "#4C82C4"
ACCENT_OFF = "#3A3F47"
TROUGH = "#3A3F47"


def resource_path(rel):
    """Locate a bundled asset in dev and inside the packaged app."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


SUPPORTED = [
    ("Documents", "*.docx *.pptx *.xlsx *.xls *.pdf *.html *.htm *.csv *.json *.xml *.txt *.md *.epub *.png *.jpg *.jpeg *.tiff"),
    ("All files", "*.*"),
]


def write_md(text, src_path):
    out_path = os.path.splitext(src_path)[0] + ".md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text or "")
    return out_path, len(text or "")


# ---------- Engine loaders (lazy: imported only when a tab is first used) ----------

def load_quick():
    """MarkItDown engine -> returns a convert(path) -> markdown-text function."""
    from markitdown import MarkItDown
    md = MarkItDown()
    return lambda path: (md.convert(path).text_content or "")


def load_deep():
    """Docling engine -> returns a convert(path) -> markdown-text function.

    Uses the models bundled inside the app and runs fully offline (no network),
    so it works on locked-down machines. Falls back to default behaviour if the
    bundled models aren't present (e.g. running from source without them)."""
    models_dir = resource_path(os.path.join("assets", "docling_models"))
    if os.path.isdir(models_dir):
        # force offline so Docling never reaches out to Hugging Face
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions

    if os.path.isdir(models_dir):
        opts = PdfPipelineOptions(artifacts_path=models_dir)
        dc = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
    else:
        dc = DocumentConverter()
    return lambda path: dc.convert(path).document.export_to_markdown()


class SegmentedControl(tk.Canvas):
    """A modern pill toggle (like iOS/macOS): rounded track, the selected
    segment filled in the accent colour. Nothing resizes when you switch."""

    def __init__(self, master, segments, command, width=320, height=40):
        super().__init__(master, width=width, height=height, bg=BG,
                         highlightthickness=0, cursor="hand2")
        self.segments = segments
        self.command = command
        self.sel = 0
        self.w, self.h = width, height
        self.bind("<Button-1>", self._click)
        self._draw()

    def _round_rect(self, x1, y1, x2, y2, r, **kw):
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.create_polygon(pts, smooth=True, **kw)

    def _draw(self):
        self.delete("all")
        self._round_rect(1, 1, self.w - 1, self.h - 1, self.h // 2, fill=TROUGH, outline="")
        n = len(self.segments)
        seg = (self.w - 6) / n
        for i, label in enumerate(self.segments):
            x1 = 3 + i * seg
            x2 = x1 + seg
            if i == self.sel:
                self._round_rect(x1, 3, x2, self.h - 3, (self.h - 6) // 2, fill=ACCENT, outline="")
            self.create_text((x1 + x2) / 2, self.h / 2, text=label,
                             fill="white" if i == self.sel else SUBFG,
                             font=("", 13, "bold"))

    def _click(self, e):
        n = len(self.segments)
        i = max(0, min(n - 1, int(e.x // (self.w / n))))
        if i != self.sel:
            self.sel = i
            self._draw()
            self.command(i)


class ConverterPanel(tk.Frame):
    """One tab: a blurb, a file picker, a progress bar, and a log.

    `loader` is a zero-arg callable returning a convert(path)->text function.
    It is called lazily on first use (engines are slow to import)."""

    def __init__(self, master, blurb, loader, load_msg):
        super().__init__(master, bg=BG)
        self._loader = loader
        self._load_msg = load_msg
        self._convert = None
        self._busy = False
        self._q = queue.Queue()

        tk.Label(self, text=blurb, bg=BG, fg=SUBFG, justify="left",
                 wraplength=580).pack(anchor="w", padx=16, pady=(14, 8))

        self.btn = tk.Label(self, text="Choose files…", bg=ACCENT, fg="white",
                            font=("", 13, "bold"), padx=18, pady=9, cursor="hand2")
        self.btn.pack(anchor="w", padx=16)
        self.btn.bind("<Button-1>", lambda e: self.pick_files())
        self.btn.bind("<Enter>", lambda e: not self._busy and self.btn.configure(bg=ACCENT_HOVER))
        self.btn.bind("<Leave>", lambda e: not self._busy and self.btn.configure(bg=ACCENT))

        self.status = tk.Label(self, text="Ready.", bg=BG, fg=SUBFG)
        self.status.pack(anchor="w", padx=16, pady=(10, 0))

        self.progress = ttk.Progressbar(self, mode="determinate", length=100,
                                        style="Brand.Horizontal.TProgressbar")
        self.progress.pack(fill="x", padx=16, pady=(6, 0))

        log_frame = tk.Frame(self, bg=BG)
        log_frame.pack(fill="both", expand=True, padx=16, pady=(8, 14))
        self.log = tk.Text(log_frame, height=10, wrap="word", state="disabled",
                           bg=LOG_BG, fg=FG, insertbackground=FG, relief="flat",
                           highlightthickness=1, highlightbackground=HEADER_BG,
                           padx=10, pady=8,
                           font=("Menlo", 11) if os.name != "nt" else ("Consolas", 10))
        scroll = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        self.log.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.after(100, self._drain)

    # --- UI event queue (Tk is not thread-safe; workers post, main thread applies) ---
    def _post(self, *event):
        self._q.put(event)

    def _log(self, line):
        self._q.put(("log", line))

    def _drain(self):
        try:
            while True:
                ev = self._q.get_nowait()
                k = ev[0]
                if k == "log":
                    self.log.configure(state="normal")
                    self.log.insert("end", ev[1] + "\n")
                    self.log.see("end")
                    self.log.configure(state="disabled")
                elif k == "pmode":
                    if ev[1] == "indeterminate":
                        self.progress.configure(mode="indeterminate")
                        self.progress.start(12)
                    else:
                        self.progress.stop()
                        self.progress.configure(mode="determinate", maximum=ev[2], value=0)
                elif k == "pval":
                    self.progress.configure(value=ev[1])
                elif k == "status":
                    self.status.configure(text=ev[1])
                elif k == "busy":
                    self._set_busy(ev[1])
        except queue.Empty:
            pass
        self.after(100, self._drain)

    def _set_busy(self, busy):
        self._busy = busy
        self.btn.configure(bg=ACCENT_OFF if busy else ACCENT,
                          fg=SUBFG if busy else "white",
                          cursor="watch" if busy else "hand2")
        if not busy:
            self.progress.stop()
            self.progress.configure(mode="determinate", value=0)

    def pick_files(self):
        if self._busy:
            return
        paths = filedialog.askopenfilenames(title="Choose documents to convert", filetypes=SUPPORTED)
        if not paths:
            return
        self._set_busy(True)
        self.status.configure(text=f"Converting {len(paths)} file(s)…")
        threading.Thread(target=self._run, args=(list(paths),), daemon=True).start()

    def _run(self, paths):
        try:
            if self._convert is None:
                self._log(self._load_msg)
                self._post("pmode", "indeterminate")
                self._convert = self._loader()
        except Exception as e:  # noqa: BLE001 - engine failed to load
            self._log(f"Engine unavailable — {type(e).__name__}: {e}")
            self._post("status", "Engine not available.")
            self._post("busy", False)
            return

        self._post("pmode", "determinate", len(paths))
        ok = 0
        for i, p in enumerate(paths):
            try:
                text = self._convert(p)
                out, chars = write_md(text, p)
                ok += 1
                self._log(f"OK   {os.path.basename(p)}  ->  {os.path.basename(out)}  ({chars:,} chars)")
            except Exception as e:  # noqa: BLE001
                self._log(f"FAIL {os.path.basename(p)}  —  {type(e).__name__}: {e}")
            self._post("pval", i + 1)
        self._log(f"— Done: {ok}/{len(paths)} converted —\n")
        self._post("status", f"Done: {ok}/{len(paths)} converted.")
        self._post("busy", False)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("660x520")
        self.minsize(560, 460)
        self.configure(bg=BG)

        self._init_style()

        # --- branded header ---
        banner = tk.Frame(self, bg=HEADER_BG)
        banner.pack(fill="x")
        self._logo_img = None
        try:
            self._logo_img = tk.PhotoImage(file=resource_path(os.path.join("assets", "header_logo.png")))
            tk.Label(banner, image=self._logo_img, bg=HEADER_BG).pack(side="left", padx=(16, 12), pady=10)
        except Exception:  # noqa: BLE001 - logo is cosmetic
            pass
        tk.Label(banner, text=APP_TITLE, bg=HEADER_BG, fg="white",
                 font=("", 20, "bold")).pack(side="left", pady=12)

        # --- mode switcher (segmented control, not tabs) ---
        switcher = tk.Frame(self, bg=BG)
        switcher.pack(fill="x", pady=(14, 2))
        self.seg = SegmentedControl(switcher, ["⚡  Quick", "🔬  Deep"],
                                    self._select_mode, width=320, height=40)
        self.seg.pack()

        # --- content: both panels stacked in one cell; show the selected one ---
        container = tk.Frame(self, bg=BG)
        container.pack(fill="both", expand=True)
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        self.quick = ConverterPanel(
            container,
            "Quick — fast and lightweight.\n"
            "Best for Word, Excel, PowerPoint and text-based PDFs. Runs instantly.",
            load_quick,
            "Loading Quick engine (MarkItDown)…",
        )
        self.deep = ConverterPanel(
            container,
            "Deep — slower but much smarter.\n"
            "Understands page layout, tables and scanned pages (OCR). Use this when\n"
            "Quick gives poor results. Runs fully offline.",
            load_deep,
            "Loading Deep engine (Docling) — offline…",
        )
        self.quick.grid(row=0, column=0, sticky="nsew")
        self.deep.grid(row=0, column=0, sticky="nsew")
        self.quick.tkraise()

    def _select_mode(self, i):
        (self.quick if i == 0 else self.deep).tkraise()

    def _init_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")  # themeable on all platforms
        except tk.TclError:
            pass
        style.configure("Brand.Horizontal.TProgressbar",
                        background=ACCENT, troughcolor=TROUGH, borderwidth=0)


if __name__ == "__main__":
    # Headless self-tests (verify the frozen app), no GUI:
    #   --selftest <file>       uses the Quick engine (MarkItDown)
    #   --selftest-deep <file>  uses the Deep engine (Docling, offline)
    if len(sys.argv) >= 3 and sys.argv[1] in ("--selftest", "--selftest-deep"):
        conv = load_deep() if sys.argv[1] == "--selftest-deep" else load_quick()
        out, chars = write_md(conv(sys.argv[2]), sys.argv[2])
        print(f"OK   {os.path.basename(sys.argv[2])}  ->  {os.path.basename(out)}  ({chars:,} chars)")
        sys.exit(0)
    App().mainloop()
