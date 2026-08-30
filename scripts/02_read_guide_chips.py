# -*- coding: utf-8 -*-
"""Find the solid colour CHIPS overlaid on each panel of the task guide screenshot,
sample each one, and match it to the nearest approved Atlas variant by dE2000."""
import json, math
import numpy as np
from PIL import Image

GUIDE = r"F:\_KEA WORLD\KEA BABIES\FEED\Resources\Guide Instructions  -Task.png"
V = json.load(open(r"F:\_KEA WORLD\KEA BABIES\FEED\Assets\variants.json", encoding="utf-8"))["variants"]

def rgb2lab(rgb):
    r,g,b=[c/255 for c in rgb]
    f=lambda c: c/12.92 if c<=0.04045 else ((c+0.055)/1.055)**2.4
    r,g,b=f(r),f(g),f(b)
    x=r*.4124564+g*.3575761+b*.1804375; y=r*.2126729+g*.7151522+b*.072175; z=r*.0193339+g*.119192+b*.9503041
    t=lambda v: v**(1/3) if v>0.008856 else 7.787*v+16/116
    fx,fy,fz=t(x/.95047),t(y/1.0),t(z/1.08883)
    return (116*fy-16, 500*(fx-fy), 200*(fy-fz))

def de2000(l1,l2):
    L1,a1,b1=l1; L2,a2,b2=l2
    dLp=L2-L1; Lb=(L1+L2)/2
    C1=math.hypot(a1,b1); C2=math.hypot(a2,b2); Cb=(C1+C2)/2
    G=0.5*(1-math.sqrt(Cb**7/(Cb**7+25**7))) if Cb>0 else 0
    a1p=a1*(1+G); a2p=a2*(1+G)
    C1p=math.hypot(a1p,b1); C2p=math.hypot(a2p,b2); dCp=C2p-C1p; Cbp=(C1p+C2p)/2
    h1=math.degrees(math.atan2(b1,a1p))%360; h2=math.degrees(math.atan2(b2,a2p))%360
    dh=h2-h1
    if abs(dh)>180: dh-=360*(1 if dh>0 else -1)
    dHp=2*math.sqrt(C1p*C2p)*math.sin(math.radians(dh/2))
    Hbp=(h1+h2)/2
    if abs(h1-h2)>180: Hbp+=180
    T=1-.17*math.cos(math.radians(Hbp-30))+.24*math.cos(math.radians(2*Hbp))+.32*math.cos(math.radians(3*Hbp+6))-.20*math.cos(math.radians(4*Hbp-63))
    Sl=1+(.015*(Lb-50)**2)/math.sqrt(20+(Lb-50)**2); Sc=1+.045*Cbp; Sh=1+.015*Cbp*T
    Rt=-2*math.sqrt(Cbp**7/(Cbp**7+25**7))*math.sin(math.radians(60*math.exp(-(((Hbp-275)/25)**2)))) if Cbp>0 else 0
    return math.sqrt((dLp/Sl)**2+(dCp/Sc)**2+(dHp/Sh)**2+Rt*(dCp/Sc)*(dHp/Sh))

im = Image.open(GUIDE).convert("RGB")
W,H = im.size
a = np.asarray(im, dtype=np.int16)
print(f"guide: {W}x{H}")

# panel grid: 2 rows x 4 cols. Find panel bounds by the guide's own layout.
# Detect flat regions: local window where max-min per channel is tiny.
from scipy import ndimage
gray = a.astype(np.float32)
# flatness = local range over 9x9
mx = ndimage.maximum_filter(gray, size=(9,9,1))
mn = ndimage.minimum_filter(gray, size=(9,9,1))
flat = ((mx-mn).max(axis=2) < 4)
# exclude near-white / near-black
lum = gray.mean(axis=2)
flat &= (lum > 60) & (lum < 235)
lbl, n = ndimage.label(flat)
print(f"flat regions found: {n}")
objs = ndimage.find_objects(lbl)
cands=[]
for i,sl in enumerate(objs, start=1):
    ys, xs = sl
    h, w = ys.stop-ys.start, xs.stop-xs.start
    area = (lbl[sl]==i).sum()
    if area < 900 or h < 25 or w < 18: continue
    fill = area/(h*w)
    if fill < 0.55: continue
    reg = a[sl][lbl[sl]==i]
    med = tuple(int(v) for v in np.median(reg, axis=0))
    cands.append({"bbox":[int(xs.start),int(ys.start),int(xs.stop),int(ys.stop)],
                  "wh":[int(w),int(h)],"area":int(area),"rgb":list(med),
                  "hex":"#{:02X}{:02X}{:02X}".format(*med)})

# assign each candidate to a panel cell (2 rows x 4 cols)
cells = {}
for c in cands:
    cx = (c["bbox"][0]+c["bbox"][2])//2; cy=(c["bbox"][1]+c["bbox"][3])//2
    col = min(3, max(0, int(cx / (W/4)))); row = 0 if cy < H*0.5 else 1
    img_no = 2 + row*4 + col
    cells.setdefault(img_no, []).append(c)

print(f"\n{'img':>5} {'chip hex':10} {'size':>10} {'area':>7}   nearest Atlas variant        dE")
print("-"*82)
results={}
for img_no in sorted(cells):
    # biggest flat chip in that panel
    best = sorted(cells[img_no], key=lambda c:-c["area"])
    for c in best[:3]:
        lab = rgb2lab(c["rgb"])
        ranked = sorted(((de2000(lab, tuple(v["lab"])), v) for v in V), key=lambda t:t[0])
        d, v = ranked[0]
        print(f"{img_no:>5} {c['hex']:10} {c['wh'][0]:>4}x{c['wh'][1]:<4} {c['area']:>7}   {v['name']:<22} {d:6.2f}")
        results.setdefault(img_no, []).append({**c, "match": v["name"], "match_hex": v["hex"], "de2000": round(d,2)})
    print()
json.dump(results, open(r"F:\_KEA WORLD\KEA BABIES\FEED\Assets\guide_chip_matches.json","w",encoding="utf-8"), indent=1)
print("wrote guide_chip_matches.json")
