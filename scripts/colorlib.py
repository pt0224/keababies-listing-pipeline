# -*- coding: utf-8 -*-
"""Shared colour maths for the KEALIST harness.

PORTABLE - nothing in this file is KeaBabies-specific. Any client harness doing
luminance-preserving recolour should import from here rather than re-implement.

The two constants that matter:
  * LUMA weights 0.30/0.59/0.11 in GAMMA space - these are what Photoshop's
    COLOR / LUMINOSITY blend modes actually use. Do not swap in the Rec.709
    linear-light weights; the gamma solve will be wrong.
  * dE2000 - the only acceptable pass/fail metric. Never eyeball a colour match.
"""
import math

# --------------------------------------------------------------- conversions
def hex_rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def rgb_hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(*[int(round(c)) for c in rgb])


def luma(rgb):
    """Photoshop COLOR/LUMINOSITY luminance, gamma space."""
    return 0.30 * rgb[0] + 0.59 * rgb[1] + 0.11 * rgb[2]


def rgb_to_lab(rgb):
    r, g, b = [c / 255.0 for c in rgb]
    f = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = f(r), f(g), f(b)
    x = r * .4124564 + g * .3575761 + b * .1804375
    y = r * .2126729 + g * .7151522 + b * .0721750
    z = r * .0193339 + g * .1191920 + b * .9503041
    t = lambda v: v ** (1 / 3) if v > 0.008856 else 7.787 * v + 16 / 116
    fx, fy, fz = t(x / .95047), t(y / 1.0), t(z / 1.08883)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def rgb_to_cmyk(rgb):
    r, g, b = [c / 255.0 for c in rgb]
    k = 1 - max(r, g, b)
    if k >= 1:
        return (0, 0, 0, 100)
    c = (1 - r - k) / (1 - k)
    m = (1 - g - k) / (1 - k)
    y = (1 - b - k) / (1 - k)
    return tuple(int(round(v * 100)) for v in (c, m, y, k))


# --------------------------------------------------------------------- dE2000
def de2000(lab1, lab2):
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    dLp = L2 - L1
    Lb = (L1 + L2) / 2
    C1 = math.hypot(a1, b1)
    C2 = math.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7))) if Cb > 0 else 0
    a1p, a2p = a1 * (1 + G), a2 * (1 + G)
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    dCp = C2p - C1p
    Cbp = (C1p + C2p) / 2
    h1 = math.degrees(math.atan2(b1, a1p)) % 360
    h2 = math.degrees(math.atan2(b2, a2p)) % 360
    dh = h2 - h1
    if abs(dh) > 180:
        dh -= 360 * (1 if dh > 0 else -1)
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dh / 2))
    Hbp = (h1 + h2) / 2
    if abs(h1 - h2) > 180:
        Hbp += 180
    T = (1 - .17 * math.cos(math.radians(Hbp - 30)) + .24 * math.cos(math.radians(2 * Hbp))
         + .32 * math.cos(math.radians(3 * Hbp + 6)) - .20 * math.cos(math.radians(4 * Hbp - 63)))
    Sl = 1 + (.015 * (Lb - 50) ** 2) / math.sqrt(20 + (Lb - 50) ** 2)
    Sc = 1 + .045 * Cbp
    Sh = 1 + .015 * Cbp * T
    Rt = (-2 * math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7))
          * math.sin(math.radians(60 * math.exp(-(((Hbp - 275) / 25) ** 2))))) if Cbp > 0 else 0
    return math.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2
                     + Rt * (dCp / Sc) * (dHp / Sh))


def de_hex(h1, h2):
    return de2000(rgb_to_lab(hex_rgb(h1)), rgb_to_lab(hex_rgb(h2)))


# ------------------------------------------------------------- the gamma solve
def solve_gamma(y0, y1):
    """Levels INPUT gamma that maps measured luma y0 -> target luma y1.

    Photoshop Levels: out = 255 * (in/255) ** (1/gamma)
    so   gamma = ln(y0/255) / ln(y1/255)

    This is why the harness never guesses a Curves adjustment by eye: given the
    measured cloth midtone and the target hex, the correction is a closed form.
    """
    if not (0 < y0 < 255 and 0 < y1 < 255):
        raise ValueError(f"luma out of range: y0={y0} y1={y1}")
    return math.log(y0 / 255.0) / math.log(y1 / 255.0)


# ------------------------------------------------------------------- sampling
def body_median(pixels, lo=20, hi=80):
    """Median of the fabric BODY - trims the darkest/brightest tails so deep
    shadow and specular highlight do not drag the reading. `pixels` = Nx3 array."""
    import numpy as np
    p = np.asarray(pixels, dtype=np.float32).reshape(-1, 3)
    Y = 0.30 * p[:, 0] + 0.59 * p[:, 1] + 0.11 * p[:, 2]
    a, b = np.percentile(Y, [lo, hi])
    body = p[(Y >= a) & (Y <= b)]
    if len(body) == 0:
        body = p
    med = tuple(int(v) for v in np.median(body, axis=0))
    Yb = float((0.30 * body[:, 0] + 0.59 * body[:, 1] + 0.11 * body[:, 2]).mean())
    return med, Yb


def separation_matrix(variants):
    """dE2000 between every pair. Returns (rows, closest_pair, closest_dE).
    Anything under ~5 will read as a duplicate at thumbnail size - flag it."""
    rows, worst, pair = [], 1e9, None
    for i, a in enumerate(variants):
        row = []
        for j, b in enumerate(variants):
            d = 0.0 if i == j else de2000(tuple(a["lab"]), tuple(b["lab"]))
            row.append(d)
            if i < j and d < worst:
                worst, pair = d, (a["name"], b["name"])
        rows.append(row)
    return rows, pair, worst
