# -*- coding: utf-8 -*-
"""KEALIST stage 6 - the Ralph gate. Two checks, both objective.

  1. COLOUR      dE2000 of the recoloured cloth vs the approved target  (< 3.0)
  2. CONTAINMENT nothing changed outside the cloth                      (stray px)

The recoloured region IDENTIFIES ITSELF as the pixels that differ between the
BEFORE and AFTER Photoshop renders. That is deliberate: it means the gate never
depends on a mask assumption, so a wrong container or a leaking mask shows up as
a wrong region rather than passing silently.

On FAIL it prints the corrected gamma, so the caller can re-apply. Never
approve a cloth by eye - a washed-out fill still looks "plausible".

    python 06_verify.py --product urban-burp-cloths --colorway atlas --tag "Image 3"
"""
import argparse, json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from colorlib import rgb_to_lab, de2000, luma, solve_gamma, body_median, rgb_hex

Image.MAX_IMAGE_PIXELS = None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--product", required=True)
    ap.add_argument("--colorway", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--json", action="store_true", help="machine-readable result")
    a = ap.parse_args()

    prod = json.load(open(os.path.join(ROOT, "config", "products", f"{a.product}.json"), encoding="utf-8"))
    cw = json.load(open(os.path.join(ROOT, "config", "colorways", f"{a.colorway}.json"), encoding="utf-8"))
    variants = {v["name"]: v for v in cw["variants"]}
    gates = prod["gates"]
    outdir = prod["paths"]["output"]
    cwname = cw["colorway"]["name"]
    base = prod["paths"]["out_pattern"].format(colorway=cwname, tag=a.tag)

    bp = os.path.join(outdir, "_verify", f"{a.tag} BEFORE.jpg")
    apth = os.path.join(outdir, base + ".jpg")
    for p in (bp, apth):
        if not os.path.exists(p):
            sys.exit(f"missing: {p}")

    before = np.asarray(Image.open(bp).convert("RGB"), dtype=np.int16)
    after = np.asarray(Image.open(apth).convert("RGB"), dtype=np.int16)
    if before.shape != after.shape:
        sys.exit(f"size mismatch {before.shape} vs {after.shape}")

    diff = np.abs(before - after).max(axis=2)
    changed = diff > 20
    if changed.sum() == 0:
        sys.exit("NOTHING CHANGED - container path is probably wrong")

    lbl, n = ndimage.label(ndimage.binary_closing(changed, structure=np.ones((5, 5))))
    sizes = ndimage.sum(changed, lbl, range(1, n + 1))
    order = np.argsort(sizes)[::-1]
    keep = [int(order[0]) + 1]
    for i in order[1:]:                      # multi-part cloths (rim + body)
        if sizes[i] >= 0.15 * sizes[order[0]]:
            keep.append(int(i) + 1)
    main_region = np.isin(lbl, keep)
    stray = int((changed & ~main_region).sum())

    imap = cw["image_map"][a.tag]
    results = []
    if isinstance(imap, dict):
        img = next(i for i in prod["images"] if i["tag"] == a.tag)
        bands = {"/".join(u["path"]): u.get("band") for u in img["units"] if u.get("band")}
        for key, band in bands.items():
            tname = imap[key]
            y0, y1, x0, x1 = band
            med, _ = body_median(after[y0:y1, x0:x1])
            d = de2000(rgb_to_lab(med), tuple(variants[tname]["lab"]))
            results.append({"unit": key, "target": tname, "achieved": rgb_hex(med), "de2000": round(d, 2)})
    else:
        med, _ = body_median(after[main_region])
        d = de2000(rgb_to_lab(med), tuple(variants[imap]["lab"]))
        results.append({"unit": a.tag, "target": imap, "achieved": rgb_hex(med), "de2000": round(d, 2)})

    worst = max(r["de2000"] for r in results)
    colour_ok = worst < gates["de2000_max"]
    contain_ok = stray <= gates["stray_pixels_max"]

    ys, xs = np.where(main_region)
    print(f"{a.tag}  region {int(main_region.sum()):,}px  "
          f"bbox=({xs.min()},{ys.min()})-({xs.max()},{ys.max()})  parts={len(keep)}")
    for r in results:
        mark = "PASS" if r["de2000"] < gates["de2000_max"] else "FAIL"
        print(f"   {r['unit'][:34]:34s} {r['achieved']} -> {r['target']:16s} "
              f"dE={r['de2000']:5.2f}  {mark}")
    print(f"   containment: stray {stray:,} px (limit {gates['stray_pixels_max']:,})  "
          f"{'PASS' if contain_ok else 'FAIL'}")

    # ---- correction hint: re-solve gamma from the BEFORE render, exact region
    hint = None
    if not colour_ok and not isinstance(imap, dict):
        med_b, y0m = body_median(before[main_region])
        y1t = luma(variants[imap]["rgb"])
        hint = round(solve_gamma(y0m, y1t), 4)
        print(f"\n   CORRECTION: cloth measured {rgb_hex(med_b)} Y0={y0m:.1f} in the real render;")
        print(f"               re-run with --gamma {hint}")

    verdict = "PASS" if (colour_ok and contain_ok) else "FAIL"
    print(f"\n{a.tag}: {verdict}")
    if a.json:
        print(json.dumps({"tag": a.tag, "verdict": verdict, "worst_de": worst,
                          "stray": stray, "results": results, "gamma_hint": hint}))
    sys.exit(0 if verdict == "PASS" else 2)


if __name__ == "__main__":
    main()
