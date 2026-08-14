"""
Markdownify — convert documents to clean Markdown.

Two engines, one segmented switch:
  • Quick  (MarkItDown) — fast, lightweight. Great for Office files and text PDFs.
  • Deep   (Docling)     — slower, ML-powered. Handles scanned PDFs, tables, OCR.

Each converted file is written as <name>.md next to the original.
Packaged into a macOS .app and a Windows .exe.
"""

import multiprocessing
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

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


def unique_md_path(src_path):
    """Pick an output path that never overwrites the input or an existing file.
    report.pdf -> report.md, then report (2).md, report (3).md, …"""
    stem = os.path.splitext(src_path)[0]
    candidate = stem + ".md"
    n = 2
    while os.path.exists(candidate) or os.path.abspath(candidate) == os.path.abspath(src_path):
        candidate = f"{stem} ({n}).md"
        n += 1
    return candidate


def write_md(text, src_path):
    out_path = unique_md_path(src_path)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text or "")
    return out_path, len(text or "")


OFFICE_EXT = {".docx", ".xlsx", ".xls", ".pptx"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}


def pdf_text_health(path, probe_pages=8):
    """Cheap probe of a PDF's text layer. Returns 'scanned', 'garbled' or 'ok'.

    Reads the first few pages only — corruption often starts partway in, but
    reading the whole file would be slow for large documents."""
    try:
        from pdfminer.high_level import extract_text
        txt = extract_text(path, maxpages=probe_pages) or ""
    except Exception:  # noqa: BLE001 - probe is best-effort only
        return "ok"
    if len(txt.strip()) < 100:
        return "scanned"          # little/no text layer -> needs OCR
    if _looks_garbled(txt):
        return "garbled"
    return "ok"


# Common words containing an ff/fi/fl ligature. A PDF with a broken ligature
# mapping turns these into things like "diUerent" or "oUice".
_LIGATURE_WORDS = {
    "different", "difficult", "difficulty", "office", "offer", "offered", "staff",
    "effect", "effective", "efficient", "office", "official", "offboarding",
    "first", "fill", "filled", "final", "finally", "file", "filed", "files",
    "confirm", "confirmation", "notification", "notifications", "specific",
    "affect", "affected", "off", "offline", "profile", "benefit", "benefits",
    "identify", "identified", "certificate", "certification", "sufficient",
}


def _looks_garbled(txt):
    """True if the text shows the broken-ligature signature.

    Requires that swapping the odd character for an f-ligature yields a real
    word — so genuine CamelCase names (BitLocker, MediaTek, PalmRest) are not
    mistaken for corruption."""
    import re
    hits = 0
    for word in re.findall(r"[A-Za-z]*[a-z]{2}[A-Z0-9][a-z]{2}[A-Za-z]*", txt):
        m = re.search(r"[a-z]{2}([A-Z0-9])[a-z]{2}", word)
        if not m:
            continue
        odd = m.group(1)
        for lig in ("ff", "fi", "fl", "ffi"):
            if word.replace(odd, lig, 1).lower() in _LIGATURE_WORDS:
                hits += 1
                break
        if hits >= 1:   # dictionary check makes a single hit reliable
            return True
    return False


def pdf_image_count(path, probe_pages=8):
    """How many images the first pages of a PDF contain (0 if none/unreadable).

    Used to warn that the Quick engine would silently drop them."""
    try:
        from pdfminer.high_level import extract_pages
        from pdfminer.layout import LTImage, LTFigure
    except Exception:  # noqa: BLE001
        return 0
    n = 0

    def walk(obj):
        nonlocal n
        for x in obj:
            if isinstance(x, LTImage):
                n += 1
            elif isinstance(x, LTFigure):
                walk(x)

    try:
        for i, page in enumerate(extract_pages(path)):
            if i >= probe_pages:
                break
            walk(page)
    except Exception:  # noqa: BLE001 - probe is best-effort only
        return 0
    return n


def suggest_engine(paths, current_is_deep, force_ocr_on, include_images=True):
    """Recommend the better engine/settings for the chosen files.

    Returns (target_is_deep, want_force_ocr, message) or None if the current
    selection is already the sensible choice."""
    exts = [os.path.splitext(p)[1].lower() for p in paths]

    if all(e in OFFICE_EXT for e in exts) and current_is_deep:
        return (False, False,
                "These look like Office documents (Word/Excel/PowerPoint).\n\n"
                "Quick reads their text directly — it's faster and more accurate, "
                "and it keeps images.\n\nSwitch to Quick?")

    if all(e in IMAGE_EXT for e in exts) and not current_is_deep:
        return (True, False,
                "These are image files.\n\n"
                "Quick cannot read text from images — it would produce an empty file. "
                "Deep uses OCR to read them.\n\nSwitch to Deep?")

    pdfs = [p for p, e in zip(paths, exts) if e == ".pdf"]
    if pdfs and len(pdfs) <= 5:
        health = [pdf_text_health(p) for p in pdfs]
        if any(h in ("scanned", "garbled") for h in health):
            why = ("This PDF looks scanned — it has no readable text layer."
                   if "scanned" in health else
                   "This PDF's text layer looks corrupted — some words would come "
                   "out garbled (e.g. “diUerent” instead of “different”).")
            if not current_is_deep:
                return (True, True,
                        f"{why}\n\n"
                        "Deep with Force OCR reads the page visually and gets clean text.\n\n"
                        "Switch to Deep with Force OCR?")
            if not force_ocr_on:
                return (True, True,
                        f"{why}\n\n"
                        "Turning on Force OCR will give much better text.\n\n"
                        "Enable Force OCR for this conversion?")

        # A readable PDF, but Quick cannot carry images out of a PDF at all.
        if not current_is_deep and include_images:
            total = sum(pdf_image_count(p) for p in pdfs)
            if total:
                return (True, False,
                        f"This PDF contains {total} image"
                        f"{'s' if total != 1 else ''} (screenshots, charts, photos).\n\n"
                        "Quick cannot carry images out of a PDF — they would all be "
                        "missing from the .md. Deep keeps them.\n\n"
                        "Switch to Deep to keep the images?")
    return None


# ---------- Engine loaders (lazy: imported only when a tab is first used) ----------

def load_quick():
    """MarkItDown engine -> returns a convert(path, include_images) function.

    include_images=True embeds the document's images directly into the Markdown
    (as data URIs) so the .md is self-contained. False = clean text, no images."""
    from markitdown import MarkItDown
    md = MarkItDown()

    def convert(path, include_images=True, force_ocr=False):  # force_ocr N/A for Quick
        return md.convert(path, keep_data_uris=include_images).text_content or ""

    return convert


def load_deep():
    """Docling engine -> returns a convert(path, include_images) function.

    Uses the models bundled inside the app and runs fully offline (no network),
    so it works on locked-down machines. include_images=True embeds figures/
    screenshots into the Markdown; False leaves placeholders."""
    models_dir = resource_path(os.path.join("assets", "docling_models"))
    if os.path.isdir(models_dir):
        # force offline so Docling never reaches out to Hugging Face
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    # TorchDynamo (PyTorch's JIT) recurses without bound inside a packaged app
    # when the layout model runs, failing every PDF with RecursionError. Eager
    # mode is unaffected, so switch the JIT off before torch is imported.
    os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")
    os.environ.setdefault("TORCH_COMPILE_DISABLE", "1")

    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
    from docling_core.types.doc import ImageRefMode

    converters = {}  # cached per force_ocr setting (building one is slow)

    def get_converter(force_ocr):
        if force_ocr not in converters:
            opts = PdfPipelineOptions(generate_picture_images=True)  # so images can be embedded
            # PDF images are re-rendered from the page; at the default 1.0 scale
            # (72 dpi) screenshots are too blurry to read. 2.0 doubles the
            # resolution for no measurable extra time.
            opts.images_scale = 2.0
            if os.path.isdir(models_dir):
                opts.artifacts_path = models_dir
            if force_ocr:
                # Re-OCR the rendered page instead of trusting the PDF's text layer.
                # Fixes garbled/broken text-layer PDFs and reads scanned pages.
                opts.do_ocr = True
                opts.ocr_options = RapidOcrOptions(force_full_page_ocr=True)
            converters[force_ocr] = DocumentConverter(
                format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
        return converters[force_ocr]

    def convert(path, include_images=True, force_ocr=False):
        doc = get_converter(force_ocr).convert(path).document
        mode = ImageRefMode.EMBEDDED if include_images else ImageRefMode.PLACEHOLDER
        return doc.export_to_markdown(image_mode=mode)

    return convert


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

    def set(self, i):
        """Move the highlight without firing the callback."""
        if 0 <= i < len(self.segments) and i != self.sel:
            self.sel = i
            self._draw()

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

    def __init__(self, master, blurb, loader, load_msg, force_ocr_option=False,
                 switch_cb=None):
        super().__init__(master, bg=BG)
        self._loader = loader
        self._load_msg = load_msg
        self._convert = None
        self._busy = False
        self._q = queue.Queue()
        self._force_ocr_option = force_ocr_option
        self._switch_cb = switch_cb

        tk.Label(self, text=blurb, bg=BG, fg=SUBFG, justify="left",
                 wraplength=580).pack(anchor="w", padx=16, pady=(14, 8))

        self.btn = tk.Label(self, text="Choose files…", bg=ACCENT, fg="white",
                            font=("", 13, "bold"), padx=18, pady=9, cursor="hand2")
        self.btn.pack(anchor="w", padx=16)
        self.btn.bind("<Button-1>", lambda e: self.pick_files())
        self.btn.bind("<Enter>", lambda e: not self._busy and self.btn.configure(bg=ACCENT_HOVER))
        self.btn.bind("<Leave>", lambda e: not self._busy and self.btn.configure(bg=ACCENT))

        self.include_images = tk.BooleanVar(value=True)
        tk.Checkbutton(
            self, text="Include images in the .md (self-contained, larger file)",
            variable=self.include_images, bg=BG, fg=SUBFG, selectcolor=LOG_BG,
            activebackground=BG, activeforeground=FG, highlightthickness=0, bd=0,
            cursor="hand2",
        ).pack(anchor="w", padx=16, pady=(10, 0))

        self.force_ocr = tk.BooleanVar(value=False)
        if self._force_ocr_option:
            tk.Checkbutton(
                self, text="Force OCR (for scanned or garbled PDFs — slower)",
                variable=self.force_ocr, bg=BG, fg=SUBFG, selectcolor=LOG_BG,
                activebackground=BG, activeforeground=FG, highlightthickness=0, bd=0,
                cursor="hand2",
            ).pack(anchor="w", padx=16, pady=(4, 0))

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
        paths = list(paths)

        # Suggest the better engine/settings for these files before converting.
        self.status.configure(text="Checking the files…")
        self.update_idletasks()
        try:
            hint = suggest_engine(paths, current_is_deep=self._force_ocr_option,
                                  force_ocr_on=self.force_ocr.get(),
                                  include_images=self.include_images.get())
        except Exception:  # noqa: BLE001 - advice must never block conversion
            hint = None
        self.status.configure(text="Ready.")

        if hint:
            target_deep, want_ocr, msg = hint
            if messagebox.askyesno("Suggestion", msg, parent=self):
                self._switch(target_deep, want_ocr, paths)
                return

        self.start(paths)

    def _switch(self, target_deep, want_ocr, paths):
        if self._switch_cb:
            self._switch_cb(target_deep, want_ocr, paths)
        else:
            self.start(paths, want_ocr)

    def start(self, paths, force_ocr_override=None):
        """Begin converting; safe to call from the main thread."""
        if self._busy:
            return
        if force_ocr_override is not None:
            self.force_ocr.set(force_ocr_override)
        self._set_busy(True)
        self.status.configure(text=f"Converting {len(paths)} file(s)…")
        # read Tk variables here (main thread) — not from the worker thread
        opts = (self.include_images.get(), self.force_ocr.get())
        threading.Thread(target=self._run, args=(paths, opts), daemon=True).start()

    def _run(self, paths, opts):
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
        include_images, force_ocr = opts
        ok = 0
        for i, p in enumerate(paths):
            try:
                text = self._convert(p, include_images, force_ocr)
                out, chars = write_md(text, p)
                if chars == 0:
                    # Don't claim success on an empty result — say why.
                    self._log(f"EMPTY {os.path.basename(p)} — no text found. "
                              f"{'Try the Deep engine (OCR).' if not self._force_ocr_option else 'Try Force OCR.'}")
                else:
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
            switch_cb=self._switch_engine,
        )
        self.deep = ConverterPanel(
            container,
            "Deep — slower but much smarter.\n"
            "Understands page layout, tables and scanned pages (OCR). Use this when\n"
            "Quick gives poor results. Runs fully offline.",
            load_deep,
            "Loading Deep engine (Docling) — offline…",
            force_ocr_option=True,
            switch_cb=self._switch_engine,
        )
        self.quick.grid(row=0, column=0, sticky="nsew")
        self.deep.grid(row=0, column=0, sticky="nsew")
        self.quick.tkraise()

    def _select_mode(self, i):
        (self.quick if i == 0 else self.deep).tkraise()

    def _switch_engine(self, target_deep, want_ocr, paths):
        """Accepted a suggestion: move to the other engine and convert there."""
        panel = self.deep if target_deep else self.quick
        self.seg.set(1 if target_deep else 0)
        panel.tkraise()
        panel.start(paths, want_ocr if target_deep else None)

    def _init_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")  # themeable on all platforms
        except tk.TclError:
            pass
        style.configure("Brand.Horizontal.TProgressbar",
                        background=ACCENT, troughcolor=TROUGH, borderwidth=0)


if __name__ == "__main__":
    # MUST be the first call. In a frozen app, worker processes started by the
    # Deep engine's libraries re-execute this file; without freeze_support()
    # each one would build another GUI window (and spawn more children).
    multiprocessing.freeze_support()

    # Docling's PDF parser recurses deeply. A packaged app has less usable stack
    # than a plain Python run, so without these it fails with RecursionError on
    # documents that convert fine from source.
    sys.setrecursionlimit(20000)
    try:
        threading.stack_size(64 * 1024 * 1024)  # worker threads need room too
    except (ValueError, RuntimeError):
        pass

    # Headless self-tests (verify the frozen app), no GUI:
    #   --selftest <file>       uses the Quick engine (MarkItDown)
    #   --selftest-deep <file>  uses the Deep engine (Docling, offline)
    if len(sys.argv) >= 3 and sys.argv[1] in ("--selftest", "--selftest-deep"):
        conv = load_deep() if sys.argv[1] == "--selftest-deep" else load_quick()
        out, chars = write_md(conv(sys.argv[2]), sys.argv[2])
        print(f"OK   {os.path.basename(sys.argv[2])}  ->  {os.path.basename(out)}  ({chars:,} chars)")
        sys.exit(0)
    App().mainloop()
