"""Generate Markdownify branding assets from the FD MarkItDown logo.

The source logo has an opaque WHITE background. We flood-fill the outer white
to transparent (keeping the white *inside* the document icons), then composite
the result onto a dark-grey rounded tile.

Produces:
  icon_master.png       - 1024px app-icon master
  markdownify.ico        - Windows icon (multi-size)
  assets/header_logo.png - transparent logo for the in-app header bar
(markdownify.icns is built from icon_master.png by build_macos.sh via iconutil.)

Run:  python make_icon.py
"""
import os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(HERE, "assets", "fd_markitdown_logo.png")

# Dark-grey tile (matches the app's dark-grey theme)
TILE_TOP = (58, 63, 71)     # #3A3F47
TILE_BOT = (30, 33, 38)     # #1E2126


def logo_transparent():
    """Return the logo with its outer white background removed."""
    rgb = Image.open(LOGO).convert("RGB")
    seed = (255, 0, 255)  # sentinel colour to mark the background
    for corner in [(0, 0), (rgb.width - 1, 0), (0, rgb.height - 1), (rgb.width - 1, rgb.height - 1)]:
        ImageDraw.floodfill(rgb, corner, seed, thresh=50)
    src = Image.open(LOGO).convert("RGBA")
    out = src.load()
    marked = rgb.load()
    for y in range(rgb.height):
        for x in range(rgb.width):
            if marked[x, y] == seed:
                out[x, y] = (0, 0, 0, 0)
    bbox = src.split()[-1].getbbox()
    return src.crop(bbox) if bbox else src


logo = logo_transparent()

# ---------- App icon (1024px, logo on dark-grey rounded tile) ----------
S = 1024
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
grad = Image.new("RGB", (1, S))
for y in range(S):
    t = y / (S - 1)
    grad.putpixel((0, y), tuple(int(TILE_TOP[i] + (TILE_BOT[i] - TILE_TOP[i]) * t) for i in range(3)))
grad = grad.resize((S, S))
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=232, fill=255)
img.paste(grad, (0, 0), mask)

target = int(S * 0.74)
scale = target / max(logo.size)
big = logo.resize((int(logo.width * scale), int(logo.height * scale)), Image.LANCZOS)
img.alpha_composite(big, ((S - big.width) // 2, (S - big.height) // 2))

img.save(os.path.join(HERE, "icon_master.png"))
img.save(os.path.join(HERE, "markdownify.ico"),
         sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("wrote icon_master.png, markdownify.ico")

# ---------- In-app header logo (transparent, sized for the banner) ----------
h = 108
hw = int(logo.width * (h / logo.height))
logo.resize((hw, h), Image.LANCZOS).save(os.path.join(HERE, "assets", "header_logo.png"))
print("wrote assets/header_logo.png")
