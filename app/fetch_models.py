"""Download Docling's models into assets/docling_models so they can be bundled
into the app for fully-offline use. Skips the download if already present.

Run:  python fetch_models.py
"""
from pathlib import Path

OUT = Path(__file__).parent / "assets" / "docling_models"

if OUT.exists() and any(OUT.iterdir()):
    print(f"Docling models already present: {OUT}")
else:
    from docling.utils.model_downloader import download_models
    OUT.mkdir(parents=True, exist_ok=True)
    # Bundle only what the default pipeline uses: layout + table structure + OCR.
    # Skip CodeFormula (~610 MB) and the figure classifier (~32 MB) — those power
    # code/math-formula and figure-type extraction, which are OFF by default and
    # not needed for office/finance/HR documents. Saves ~640 MB.
    download_models(
        output_dir=OUT,
        with_code_formula=False,
        with_picture_classifier=False,
    )
    print(f"Downloaded Docling models -> {OUT}")
    prune_duplicate_formats(OUT)


def prune_duplicate_formats(out):
    """Docling ships some models in two interchangeable formats and only loads
    one of them. Dropping the unused copy saves ~194 MB in every installer.

    Defensive: each duplicate is only removed when the format we actually use is
    present, so a future Docling that switches formats won't be broken."""
    import shutil
    freed = 0

    # Layout model: the pipeline uses the PyTorch build, not the ONNX one.
    torch_layout = out / "docling-project--docling-layout-heron"
    onnx_layout = out / "docling-project--docling-layout-heron-onnx"
    if torch_layout.is_dir() and onnx_layout.is_dir():
        freed += sum(f.stat().st_size for f in onnx_layout.rglob("*") if f.is_file())
        shutil.rmtree(onnx_layout)

    # RapidOCR loads the .onnx weights; the .pth copies are never opened.
    ocr = out / "RapidOcr"
    if ocr.is_dir() and any(ocr.glob("*.onnx")):
        for pth in ocr.glob("*.pth"):
            freed += pth.stat().st_size
            pth.unlink()

    if freed:
        print(f"Pruned {freed // (1024*1024)} MB of duplicate model formats")
