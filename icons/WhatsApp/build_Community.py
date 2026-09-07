#!/usr/bin/env python3
"""Build Community.png / Community.jpg for the WhatsApp icon set.

The mark reuses the LAN-Party network topology as its skeleton (hub node,
T-connector, two leaf nodes) and drops the *original* icon files into the
three node windows, so every embedded glyph is pixel-identical to the icon
it stands for. Swap a component by editing NODES below and re-running.

The hub is the current CineNAK lockup, kept whole and with its chalkboard
texture intact, so that tile keeps its own dark field rather than this set's.
The superseded assets live in [deprecated]CinenakK/.

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

# Hub node, then the two leaf nodes: (asset, normalise_field).
#
# normalise_field=True subtracts the asset's own flat background and adds this
# set's #0E192D back, so a source shipping on a slightly different navy leaves
# no seam where its tile meets the field. Set it False for an asset whose
# background is a texture or photograph: there is no single background colour
# to subtract, so normalising would only tint the whole image without removing
# anything. Such a tile keeps its own field and therefore reads as a distinct
# square inside its node - that is inherent to keeping the texture.
NODES = [("CineNAK.png", False),                 # kept whole, chalkboard texture intact
         ("Marketing.jpg", True),
         ("Brettspieltreff.jpg", True)]

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

def frame_svg(shadow):
    """White rings + connectors over their blue halo.

    With shadow=True the node interiors are filled with the field colour so the
    silhouette casting the shadow is solid: the shadow then falls only outside
    the mark and cannot darken the artwork sitting inside a node. That layer
    goes down first, the artwork on top of it, and a shadow=False copy last so
    the ring edges stay crisp over the artwork."""
    fill = f"rgb{BG}" if shadow else "none"
    filt = ' filter="url(#sh)"' if shadow else ""

    def rings(stroke, width):
        out = [f'<path d="{CONNECTORS}" fill="none" stroke="{stroke}" stroke-width="{width}"/>']
        for cx, cy in [HUB, (LEAF_X[0], LEAF_Y), (LEAF_X[1], LEAF_Y)]:
            out.append(f'<rect x="{cx-C}" y="{cy-C}" width="{2*C}" height="{2*C}" '
                       f'rx="{R}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')
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
  <g transform="translate(320,320) scale({S:.5f}) translate(-320,-{CY})"{filt}>
    <g stroke-linejoin="round" stroke-linecap="round">
      {rings(BLUE, RING + 2 * HALO)}
    </g>
    <g stroke-linejoin="round" stroke-linecap="round">
      {rings("url(#glyph)", RING)}
    </g>
  </g>
</svg>'''


def render(svg):
    buf = io.BytesIO()
    cairosvg.svg2png(bytestring=svg.encode(), write_to=buf,
                     output_width=WORK, output_height=WORK)
    return Image.open(io.BytesIO(buf.getvalue())).convert("RGBA")


# ------------------------------------------------------------------ crops
def glyph_square(path, normalise=True):
    """One original asset, cropped to a centred square around its own artwork so
    it fills the node window.

    Assets with an alpha channel are composited straight onto #0E192D. Flat
    assets are handled per the normalise flag documented on NODES."""
    im = Image.open(os.path.join(HERE, path))
    if im.mode in ("RGBA", "LA") or "transparency" in im.info:
        im = im.convert("RGBA")
        ys, xs = np.nonzero(np.asarray(im.split()[-1]) > 8)
        box = _square(xs, ys)
        # crop first: out-of-frame padding stays transparent instead of black
        return Image.alpha_composite(
            Image.new("RGBA", (box[2] - box[0], box[3] - box[1]), BG + (255,)),
            im.crop(box)).convert("RGB")
    a = np.asarray(im.convert("RGB")).astype(np.int16)
    if not normalise:
        # textured background: keep every pixel, the whole square is the artwork
        return im.convert("RGB")
    edge = np.concatenate([a[:6].reshape(-1, 3), a[-6:].reshape(-1, 3)])
    a = np.clip(a - np.median(edge, axis=0) + np.array(BG), 0, 255)
    ys, xs = np.nonzero(np.abs(a - np.array(BG)).max(axis=2) > 12)
    return Image.fromarray(a.astype(np.uint8)).crop(_square(xs, ys))


def _square(xs, ys):
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    half = max(xs.max() - xs.min(), ys.max() - ys.min()) / 2 + 6
    return (round(cx - half), round(cy - half), round(cx + half), round(cy + half))

# ------------------------------------------------------------------ build
k = WORK / 640
inner = round(INNER * S * k)                 # interior half-extent, working px
rad = round((R - RING / 2) * S * k)          # interior corner radius

mask = Image.new("L", (2 * inner, 2 * inner), 0)
ImageDraw.Draw(mask).rounded_rectangle((0, 0, 2 * inner - 1, 2 * inner - 1), rad, fill=255)

canvas = Image.new("RGBA", (WORK, WORK), BG + (255,))
canvas = Image.alpha_composite(canvas, render(frame_svg(shadow=True)))

for (src, norm), centre in zip(NODES, [HUB, (LEAF_X[0], LEAF_Y), (LEAF_X[1], LEAF_Y)]):
    fx, fy = to_frame(centre)
    # a kept-texture tile fills its window: insetting it would frame the
    # texture in a band of field colour, which looks like a mount
    n = 2 * inner if not norm else round(2 * inner * INSET)
    tile = Image.new("RGB", (2 * inner, 2 * inner), BG)
    tile.paste(glyph_square(src, norm).resize((n, n), Image.LANCZOS),
               (inner - n // 2, inner - n // 2))
    canvas.paste(tile, (round(fx * k) - inner, round(fy * k) - inner), mask)

canvas = Image.alpha_composite(canvas, render(frame_svg(shadow=False)))

for name, size in OUT.items():
    out = canvas.convert("RGB").resize((size, size), Image.LANCZOS)
    if name.endswith(".jpg"):
        out.save(os.path.join(HERE, name), quality=95, subsampling=0)
    else:
        out.save(os.path.join(HERE, name))
    print("wrote", name, f"{size}x{size}")
