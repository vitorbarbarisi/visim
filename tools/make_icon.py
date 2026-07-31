#!/usr/bin/env python3
"""Generate app/visim_icon.png matching real macOS app icons.

Run from the repo root:  ./app/venv/bin/python tools/make_icon.py

Two things measured off the real system icons (Calculator/Notes/Reminders, all
identical) rather than guessed:

1. macOS icons are NOT edge-to-edge. On a 1024pt canvas the body is 818pt,
   leaving 103pt of transparent padding per side. A PNG that fills its whole
   canvas renders visibly larger than every neighbour in the Dock.
2. The corner is Apple's "squircle", not a circular arc. A circular rounded
   rect with a matching mid-curve is still wrong at the extremes: measured
   horizontally at the top row of the body, the system inset is 261pt where a
   circular arc gives 177pt. A superellipse of exponent 5 tracks the real
   curve closely (inset 106/46/15 vs the system's 101/46/13 at 20/60/120pt
   below the top).
3. Apple bakes a soft drop shadow into the asset, so an icon without one reads
   as flat next to its neighbours. The system shadow reaches 31pt above and
   47pt below the body — i.e. offset downward — peaking near 16% alpha just
   outside the edge. The constants below were fitted by grid search against
   that measured alpha profile (residual <=2/255 at every sample point).
"""
import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

CANVAS = 1024
BODY_INSET = 103          # measured: 818pt body on a 1024pt canvas
SQUIRCLE_EXPONENT = 5.0   # superellipse fit to Apple's continuous corner
SQUIRCLE_POINTS = 3000    # outline resolution before downsampling
SUPERSAMPLE = 3           # PIL does not antialias shapes; render big, downscale

# Fitted to the system icons' shadow, not eyeballed. See docstring note 3.
SHADOW_OFFSET = 8         # downward nudge, in canvas pt
SHADOW_BLUR = 16          # gaussian sigma, in canvas pt
SHADOW_OPACITY = 0.28     # alpha of the shape before blurring

LETTER = "V"
LETTER_FILL = "#ffffff"
BODY_FILL = "#1c7ed6"
CAP_HEIGHT_RATIO = 0.46   # letter ink height as a fraction of the body

FONT_CANDIDATES = (
    ("/System/Library/Fonts/SFNSRounded.ttf", "Bold"),
    ("/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf", None),
    ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", None),
    ("/System/Library/Fonts/Helvetica.ttc", None),
)

OUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "app", "visim_icon.png")


def load_font(size: int):
    """First available candidate, asking for the Bold variation when the file
    is a variable font that offers one."""
    for path, variation in FONT_CANDIDATES:
        if not os.path.exists(path):
            continue
        try:
            font = ImageFont.truetype(path, size)
        except OSError:
            continue
        if variation:
            try:
                font.set_variation_by_name(variation)
            except Exception:
                pass  # not a variable font, or no such named instance
        return font, os.path.basename(path)
    return ImageFont.load_default(), "default"


def ink_box(draw, text, font):
    """Bounding box of the drawn pixels, which is what must be optically
    centered — not the font's ascender/descender box."""
    return draw.textbbox((0, 0), text, font=font)


def squircle(center: float, half: float, exponent: float, points: int):
    """Outline of |x/half|^n + |y/half|^n = 1, in the standard superellipse
    parametrization. Apple's icon corner is this shape, not a circular arc."""
    power = 2.0 / exponent
    out = []
    for i in range(points):
        angle = 2.0 * math.pi * i / points
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        x = math.copysign(abs(cos_a) ** power, cos_a)
        y = math.copysign(abs(sin_a) ** power, sin_a)
        out.append((center + half * x, center + half * y))
    return out


def build() -> Image.Image:
    scale = SUPERSAMPLE
    size = CANVAS * scale
    inset = BODY_INSET * scale

    half = (size - 2 * inset) / 2.0
    outline = squircle(size / 2.0, half, SQUIRCLE_EXPONENT, SQUIRCLE_POINTS)

    # Shadow: the same silhouette, nudged down and blurred, sitting under the
    # body. Black RGB with alpha driven by the blurred mask.
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).polygon(
        [(x, y + SHADOW_OFFSET * scale) for x, y in outline],
        fill=int(255 * SHADOW_OPACITY),
    )
    mask = mask.filter(ImageFilter.GaussianBlur(SHADOW_BLUR * scale))
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow.putalpha(mask)

    body = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(body).polygon(outline, fill=BODY_FILL)

    image = Image.alpha_composite(shadow, body)
    draw = ImageDraw.Draw(image)

    body = size - 2 * inset
    target_height = body * CAP_HEIGHT_RATIO

    # Ink height scales linearly with point size, so one correction lands it.
    probe_size = int(target_height)
    font, family = load_font(probe_size)
    box = ink_box(draw, LETTER, font)
    measured = box[3] - box[1]
    if measured > 0:
        font, family = load_font(max(1, round(probe_size * target_height / measured)))
        box = ink_box(draw, LETTER, font)

    ink_w = box[2] - box[0]
    ink_h = box[3] - box[1]
    # Offset by -box[:2] so the ink lands exactly where we want it.
    x = (size - ink_w) / 2 - box[0]
    y = (size - ink_h) / 2 - box[1]
    draw.text((x, y), LETTER, fill=LETTER_FILL, font=font)

    print(f"fonte: {family}  |  altura do V: {ink_h / scale:.0f}pt "
          f"({ink_h / body:.0%} do corpo)")
    return image.resize((CANVAS, CANVAS), Image.LANCZOS)


if __name__ == "__main__":
    icon = build()
    icon.save(OUT_PATH, "PNG")
    print(f"corpo: {CANVAS - 2 * BODY_INSET}pt em canvas de {CANVAS}pt "
          f"({(CANVAS - 2 * BODY_INSET) / CANVAS:.1%}), "
          f"squircle n={SQUIRCLE_EXPONENT:g}")
    print(f"gravado: {OUT_PATH}")
