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
    download_models(output_dir=OUT)
    print(f"Downloaded Docling models -> {OUT}")
