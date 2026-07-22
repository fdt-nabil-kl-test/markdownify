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
