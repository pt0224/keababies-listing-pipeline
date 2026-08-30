# -*- coding: utf-8 -*-
"""Builds the Atlas colourway approval swatch sheet (PNG) from variants.json."""
import json
from PIL import Image, ImageDraw, ImageFont

SRC = r"F:\_KEA WORLD\KEA BABIES\FEED\Assets\variants.json"
OUT = r"F:\_KEA WORLD\KEA BABIES\FEED\Assets\Atlas Colorway - Swatch Sheet.png"
REF = r"F:\_KEA WORLD\KEA BABIES\FEED\Resources\Product Color Reference 5 Variants\Product Color Reference  5 Variants.jpg"

data = json.load(open(SRC, encoding="utf-8"))
variants = data["variants"]

W, H = 2000, 1620
img = Image.new("RGB", (W, H), "#FFFFFF")
d = ImageDraw.Draw(img)

def font(sz, bold=False):
    for p in (r"C:\Windows\Fonts\seguisb.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
              r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"):
        try: return ImageFont.truetype(p, sz)
        except Exception: continue
    return ImageFont.load_default()

d.text((80, 60), "KeaBabies \u2014 Urban Burp Cloths", font=font(58, True), fill="#1A1A1A")
d.text((80, 132), f"{data['colorway']['name']} colourway \u00b7 5-pack \u00b7 approved variant colours", font=font(34), fill="#6A6A6A")
d.line((80, 200, W - 80, 200), fill="#E0E0E0", width=3)

n = len(variants)
pad, top = 80, 260
cw = (W - pad * 2) // n
sw = cw - 30
for i, v in enumerate(variants):
    x = pad + i * cw
    d.rounded_rectangle((x, top, x + sw, top + 560), radius=18, fill=v["hex"])
    d.text((x, top + 600), v["name"], font=font(38, True), fill="#1A1A1A")
    d.text((x, top + 652), v["hex"], font=font(32), fill="#4A4A4A")
    y = top + 706
    for label, val in (
        ("RGB", "{} {} {}".format(*v["rgb"])),
        ("CMYK", "{} {} {} {}".format(*v["cmyk"])),
        ("LAB", "{} {} {}".format(*[round(c) for c in v["lab"]])),
        ("Pos", f"#{v['position']} in pack"),
    ):
        d.text((x, y), f"{label}", font=font(24, True), fill="#8A8A8A")
        d.text((x + 90, y), val, font=font(24), fill="#3A3A3A")
        y += 38

# reference strip
try:
    ref = Image.open(REF).convert("RGB")
    ref.thumbnail((360, 360))
    img.paste(ref, (W - 80 - ref.width, 1200))
    d.text((W - 80 - ref.width, 1200 - 38), "client reference", font=font(24), fill="#8A8A8A")
except Exception as e:
    print("ref skip:", e)

d.text((80, H - 70), "Sampled from client reference JPG \u00b7 median of 2 bands per panel \u00b7 sRGB", font=font(26), fill="#9A9A9A")
img.save(OUT, quality=95)
print("wrote", OUT)
