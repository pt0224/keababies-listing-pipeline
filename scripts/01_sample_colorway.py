# -*- coding: utf-8 -*-
"""Sample the 5 approved Urban Burp Cloth variant colours from the client reference JPG.
Reports median / mean / mode / percentile spread per variant, in RGB, HEX, LAB, CMYK, HSL.
Sampling boxes deliberately sit INSIDE each visible panel, away from overlap shadows,
the piped edge and the centre seam."""
import json, colorsys
import numpy as np
from PIL import Image

SRC = r"F:\_KEA WORLD\KEA BABIES\FEED\Resources\Product Color Reference 5 Variants\Product Color Reference  5 Variants.jpg"

# (slug, x0, x1, y0, y1) -- two bands per variant to cross-check consistency
BOXES = {
    "blue":  [(220, 430, 700, 1100), (230, 430, 1450, 1750)],
    "cream": [(560, 750, 700, 1100), (580, 760, 1450, 1750)],
    "green": [(880, 1080, 700, 1100), (900, 1090, 1450, 1750)],
    "taupe": [(1200, 1400, 700, 1100), (1230, 1420, 1450, 1750)],
    "grey":  [(1650, 2150, 700, 1100), (1650, 2150, 1450, 1750)],
}

def rgb_to_lab(rgb):
    r, g, b = [c / 255.0 for c in rgb]
    def lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = lin(r), lin(g), lin(b)
    x = r*0.4124564 + g*0.3575761 + b*0.1804375
    y = r*0.2126729 + g*0.7151522 + b*0.0721750
    z = r*0.0193339 + g*0.1191920 + b*0.9503041
    def f(t): return t ** (1/3) if t > 0.008856 else 7.787*t + 16/116
    fx, fy, fz = f(x/0.95047), f(y/1.0), f(z/1.08883)
    return (round(116*fy - 16, 2), round(500*(fx - fy), 2), round(200*(fy - fz), 2))

def rgb_to_cmyk(rgb):
    r, g, b = [c / 255.0 for c in rgb]
    k = 1 - max(r, g, b)
    if k >= 1: return (0, 0, 0, 100)
    c = (1 - r - k) / (1 - k); m = (1 - g - k) / (1 - k); y = (1 - b - k) / (1 - k)
    return tuple(round(v * 100) for v in (c, m, y, k))

def rgb_to_hsl(rgb):
    h, l, s = colorsys.rgb_to_hls(*[c / 255.0 for c in rgb])
    return (round(h * 360), round(s * 100), round(l * 100))

im = Image.open(SRC).convert("RGB")
a = np.asarray(im, dtype=np.uint8)
print(f"source: {SRC}\nsize: {im.size}\n")

out = {}
for slug, boxes in BOXES.items():
    pooled = []
    per_band = []
    for (x0, x1, y0, y1) in boxes:
        patch = a[y0:y1, x0:x1].reshape(-1, 3).astype(np.float64)
        pooled.append(patch)
        per_band.append(tuple(int(v) for v in np.median(patch, axis=0)))
    px = np.vstack(pooled)
    med = tuple(int(v) for v in np.median(px, axis=0))
    mean = tuple(int(round(v)) for v in px.mean(axis=0))
    std = tuple(round(float(v), 1) for v in px.std(axis=0))
    p10 = tuple(int(v) for v in np.percentile(px, 10, axis=0))
    p90 = tuple(int(v) for v in np.percentile(px, 90, axis=0))
    hexv = "#{:02X}{:02X}{:02X}".format(*med)
    band_dE = max(max(abs(per_band[0][i] - per_band[1][i]) for i in range(3)), 0)
    out[slug] = {
        "hex": hexv, "rgb": list(med), "mean_rgb": list(mean), "std_rgb": list(std),
        "p10_rgb": list(p10), "p90_rgb": list(p90),
        "lab": list(rgb_to_lab(med)), "cmyk": list(rgb_to_cmyk(med)), "hsl": list(rgb_to_hsl(med)),
        "band_medians": [list(b) for b in per_band], "band_max_channel_delta": band_dE,
        "n_pixels": int(px.shape[0]),
    }
    print(f"{slug:6s} {hexv}  rgb{med}  lab{rgb_to_lab(med)}  cmyk{rgb_to_cmyk(med)}")
    print(f"       mean{mean} std{std}  p10{p10} p90{p90}  bands {per_band} maxdelta={band_dE}  n={px.shape[0]}")

with open(r"F:\_KEA WORLD\KEA BABIES\FEED\Assets\variant_color_samples_raw.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print("\nwrote variant_color_samples_raw.json")
