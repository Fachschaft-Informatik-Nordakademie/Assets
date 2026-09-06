#!/usr/bin/env python3
"""Build Community.png / Community.jpg for the WhatsApp icon set.

The mark reuses the LAN-Party network topology as its skeleton (hub node,
T-connector, two leaf nodes) and drops the *original* icon files into the
three node windows, so every embedded glyph is pixel-identical to the icon
it stands for. Swap a component by editing NODES below and re-running.

Palette measured from the lossless PNGs of this set and from
../../logo/FSINF_dark_bg_square_transparent.svg:
    background #0E192D (flat)   blue #003A79
    shadow     #002E59          glyph #FFFFFF -> #C8D2E6
"""
import io, os
import cairosvg
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
BG = (14, 25, 45)          # #0E192D
BLUE = "#003A79"
WORK = 2048                # supersampled working size
OUT = {"Community.png": 1024, "Community.jpg": 640}

# hub node, then the two leaf nodes
NODES = ["Vorstand.jpg", "Marketing.jpg", "Brettspieltreff.jpg"]

# ---------------------------------------------------------------- geometry
# design space is the 640 frame before the fit transform
C, RING, HALO, R = 90, 20, 18, 44      # ring centreline half, stroke, halo, corner
HUB, LEAF_Y, LEAF_X = (320, 150), 470, (196, 444)
BAR_Y = 310
INNER = C - RING // 2                  # interior half-extent
D_X = (LEAF_X[0] - C - HALO, LEAF_X[1] + C + HALO)
D_Y = (HUB[1] - C - HALO, LEAF_Y + C + HALO)
TARGET = 474                           # max extent in the 640 frame (set uses 400-490)
INSET = 0.88                           # keep embedded artwork clear of the ring
S = TARGET / max(D_X[1] - D_X[0], D_Y[1] - D_Y[0])
CY = (D_Y[0] + D_Y[1]) / 2

def to_frame(p):
    """design point -> 640-frame point"""
    return (320 + S * (p[0] - 320), 320 + S * (p[1] - CY))

CONNECTORS = (f"M {HUB[0]},{HUB[1] + C} V {BAR_Y} "
              f"M {LEAF_X[0]},{BAR_Y} H {LEAF_X[1]} "
              f"M {LEAF_X[0]},{BAR_Y} V {LEAF_Y - C} "
              f"M {LEAF_X[1]},{BAR_Y} V {LEAF_Y - C}")

def frame_svg():
    """White rings + connectors over their blue halo; node interiors stay clear."""
    def rings(stroke, width):
        out = [f'<path d="{CONNECTORS}" stroke="{stroke}" stroke-width="{width}"/>']
        for cx, cy in [HUB, (LEAF_X[0], LEAF_Y), (LEAF_X[1], LEAF_Y)]:
            out.append(f'<rect x="{cx-C}" y="{cy-C}" width="{2*C}" height="{2*C}" '
                       f'rx="{R}" stroke="{stroke}" stroke-width="{width}"/>')
        return "\n      ".join(out)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="640" height="640" viewBox="0 0 640 640">
  <defs>
    <linearGradient id="glyph" gradientUnits="userSpaceOnUse" x1="0" y1="74" x2="0" y2="566">
      <stop offset="0%" stop-color="#FFFFFF"/>
      <stop offset="58%" stop-color="#FDFEFE"/>
      <stop offset="100%" stop-color="#C8D2E6"/>
    </linearGradient>
    <filter id="sh" x="-25%" y="-25%" width="150%" height="150%">
      <feDropShadow dx="0" dy="6" stdDeviation="8" flood-color="#002E59" flood-opacity="0.85"/>
    </filter>
  </defs>
  <g transform="translate(320,320) scale({S:.5f}) translate(-320,-{CY})" filter="url(#sh)">
    <g fill="none" stroke-linejoin="round" stroke-linecap="round">
      {rings(BLUE, RING + 2 * HALO)}
    </g>
    <g fill="none" stroke-linejoin="round" stroke-linecap="round">
      {rings("url(#glyph)", RING)}
    </g>
  </g>
</svg>'''

# ------------------------------------------------------------------ crops
def glyph_square(path):
    """Original icon, background normalised to #0E192D, cropped to a centred
    square around its glyph so the artwork fills the node window."""
    im = Image.open(os.path.join(HERE, path)).convert("RGB")
    a = np.asarray(im).astype(np.int16)
    edge = np.concatenate([a[:6].reshape(-1, 3), a[-6:].reshape(-1, 3)])
    src_bg = np.median(edge, axis=0)
    a = np.clip(a - src_bg + np.array(BG), 0, 255)          # match this set's field
    ys, xs = np.nonzero(np.abs(a - np.array(BG)).max(axis=2) > 12)
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    half = max(xs.max() - xs.min(), ys.max() - ys.min()) / 2 + 4
    im = Image.fromarray(a.astype(np.uint8))
    return im.crop((round(cx - half), round(cy - half),
                    round(cx + half), round(cy + half)))

# ------------------------------------------------------------------ build
k = WORK / 640
canvas = Image.new("RGB", (WORK, WORK), BG)
inner = round(INNER * S * k)                 # interior half-extent, working px
rad = round((R - RING / 2) * S * k)          # interior corner radius

mask = Image.new("L", (2 * inner, 2 * inner), 0)
ImageDraw.Draw(mask).rounded_rectangle((0, 0, 2 * inner - 1, 2 * inner - 1), rad, fill=255)

for src, centre in zip(NODES, [HUB, (LEAF_X[0], LEAF_Y), (LEAF_X[1], LEAF_Y)]):
    fx, fy = to_frame(centre)
    n = round(2 * inner * INSET)
    tile = Image.new("RGB", (2 * inner, 2 * inner), BG)
    tile.paste(glyph_square(src).resize((n, n), Image.LANCZOS),
               (inner - n // 2, inner - n // 2))
    canvas.paste(tile, (round(fx * k) - inner, round(fy * k) - inner), mask)

buf = io.BytesIO()
cairosvg.svg2png(bytestring=frame_svg().encode(), write_to=buf,
                 output_width=WORK, output_height=WORK)
canvas = Image.alpha_composite(canvas.convert("RGBA"),
                               Image.open(io.BytesIO(buf.getvalue())).convert("RGBA"))

for name, size in OUT.items():
    out = canvas.convert("RGB").resize((size, size), Image.LANCZOS)
    if name.endswith(".jpg"):
        out.save(os.path.join(HERE, name), quality=95, subsampling=0)
    else:
        out.save(os.path.join(HERE, name))
    print("wrote", name, f"{size}x{size}")
