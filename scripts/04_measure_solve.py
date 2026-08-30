# -*- coding: utf-8 -*-
"""KEALIST stage 4 - measure each cloth's luminance and solve its Levels gamma.

READ-ONLY on the masters. Produces a provisional gamma per image; the verify
stage refines it from the real Photoshop render if the dE gate fails.

WHY PROVISIONAL: psd-tools does NOT apply a group's own layer mask when it
composites that group, so a group alpha over-reports the cloth area and the
measured midtone can be contaminated. For 'smartobject' containers the alpha is
exact and the first solve is usually final. For 'group' containers treat the
first number as a starting point - the correction loop closes the gap.

    python 04_measure_solve.py --product urban-burp-cloths --colorway atlas
"""
import argparse, json, os, sys
import numpy as np
from psd_tools import PSDImage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from colorlib import luma, solve_gamma, body_median, rgb_hex

ROOT = os.path.dirname(HERE)


def load(product, colorway):
    p = json.load(open(os.path.join(ROOT, "config", "products", f"{product}.json"), encoding="utf-8"))
    c = json.load(open(os.path.join(ROOT, "config", "colorways", f"{colorway}.json"), encoding="utf-8"))
    return p, c


def find(layer, name):
    for l in layer:
        if l.name == name:
            return l
        if l.is_group():
            r = find(l, name)
            if r is not None:
                return r
    return None


def by_path(psd, path):
    c = psd
    for n in path:
        nxt = None
        for l in c:
            if l.name == n:
                nxt = l
                break
        if nxt is None:
            return None
        c = nxt
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--product", required=True)
    ap.add_argument("--colorway", required=True)
    ap.add_argument("--only", nargs="*", help="limit to these image tags")
    a = ap.parse_args()

    prod, cw = load(a.product, a.colorway)
    variants = {v["name"]: v for v in cw["variants"]}
    imap = cw["image_map"]
    masters = prod["paths"]["masters"]
    pattern = prod["paths"]["master_pattern"]

    out = {}
    for img in prod["images"]:
        tag = img["tag"]
        if a.only and tag not in a.only:
            continue
        target = imap.get(tag)
        psd_path = os.path.join(masters, pattern.format(tag=tag))
        if not os.path.exists(psd_path):
            print(f"{tag:9s} !! master not found: {psd_path}")
            continue

        # ---- multi-unit image (the stack shot): measure each band off the guide render
        if img["kind"] == "multi":
            print(f"{tag:9s} multi-unit - bands are measured from the BEFORE render "
                  f"by 05_apply.py (see config 'units')")
            out[tag] = {"kind": "multi", "units": img["units"], "map": target}
            continue

        try:
            psd = PSDImage.open(psd_path)
            lay = find(psd, img["container"])
            if lay is None:
                print(f"{tag:9s} !! container '{img['container']}' not found")
                continue
            comp = np.asarray(lay.composite().convert("RGBA"), dtype=np.float32)
            m = comp[..., 3] > 250
            if m.sum() < 5000:
                print(f"{tag:9s} !! only {int(m.sum())} opaque px in container")
                continue
            med, y0 = body_median(comp[..., :3][m])
            t = variants[target]
            y1 = luma(t["rgb"])
            g = solve_gamma(y0, y1)
            out[tag] = {"kind": img["kind"], "container": img["container"],
                        "current_hex": rgb_hex(med), "Y0": round(y0, 1),
                        "target": target, "target_hex": t["hex"], "target_rgb": t["rgb"],
                        "Y1": round(y1, 1), "gamma": round(g, 4), "provisional": img["kind"] == "group"}
            flag = " (provisional)" if img["kind"] == "group" else ""
            print(f"{tag:9s} {img['container']:22s} {rgb_hex(med)} Y0={y0:6.1f} -> "
                  f"{target:16s} {t['hex']} Y1={y1:6.1f}  gamma={g:.4f}{flag}")
        except Exception as e:
            print(f"{tag:9s} !! {type(e).__name__}: {e}")

    dest = os.path.join(ROOT, "logs", f"gammas_{a.colorway}.json")
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=1)
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
