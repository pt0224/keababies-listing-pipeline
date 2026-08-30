# -*- coding: utf-8 -*-
"""READ-ONLY audit of the Urban Burp Cloths listing PSDs.
Dumps the layer tree: name, kind, visibility, bounds, and flags smart objects,
solid-colour fills, and adjustment layers (hue/sat, colour balance, LUT) that are
the likely recolour hooks. Opens nothing in Photoshop and writes nothing back."""
import sys, os, json
from psd_tools import PSDImage
from psd_tools.constants import BlendMode

def walk(layer, depth, rows, path=""):
    for l in layer:
        kind = l.kind
        name = l.name
        full = f"{path}/{name}" if path else name
        try:
            bbox = list(l.bbox)
        except Exception:
            bbox = None
        row = {
            "depth": depth, "name": name, "path": full, "kind": kind,
            "visible": bool(l.visible), "opacity": int(l.opacity),
            "blend": str(l.blend_mode).split(".")[-1], "bbox": bbox,
            "has_mask": bool(l.mask), "has_vector_mask": bool(getattr(l, "has_vector_mask", lambda: False)()),
        }
        eff = []
        try:
            if l.effects and len(l.effects):
                eff = [str(e.__class__.__name__) for e in l.effects]
        except Exception:
            pass
        row["effects"] = eff
        rows.append(row)
        if l.is_group():
            walk(l, depth + 1, rows, full)

def main(path):
    psd = PSDImage.open(path)
    rows = []
    walk(psd, 0, rows)
    info = {
        "file": os.path.basename(path),
        "size_mb": round(os.path.getsize(path) / 1048576, 1),
        "width": psd.width, "height": psd.height,
        "color_mode": str(psd.color_mode).split(".")[-1],
        "depth": psd.depth, "channels": psd.channels,
        "layer_count": len(rows),
        "layers": rows,
    }
    print(f"\n{'='*90}\n{info['file']}  |  {psd.width}x{psd.height}  {info['color_mode']} {psd.depth}-bit  |  {info['size_mb']} MB  |  {len(rows)} layers")
    print('='*90)
    for r in rows:
        ind = "  " * r["depth"]
        vis = " " if r["visible"] else "H"
        flag = ""
        n = r["name"].lower()
        if r["kind"] == "smartobject": flag += " [SMART OBJECT]"
        if r["kind"] in ("solidcolor", "gradientfill", "patternfill"): flag += f" [{r['kind'].upper()}]"
        if r["kind"] in ("huesaturation","colorbalance","curves","levels","brightnesscontrast","selectivecolor","colorlookup","gradientmap","photofilter"):
            flag += f" [ADJ:{r['kind']}]"
        if r["effects"]: flag += f" [FX:{','.join(r['effects'])}]"
        if r["has_mask"]: flag += " [mask]"
        if any(k in n for k in ("color","colour","cloth","burp","product","swatch","variant","blue","green","grey","gray","taupe","cream","beige")): flag += " <<"
        print(f"{vis} {ind}{r['name'][:58]:58s} {r['kind']:14s} {str(r['bbox']):28s}{flag}")
    return info

if __name__ == "__main__":
    out = []
    for p in sys.argv[1:]:
        try:
            out.append(main(p))
        except Exception as e:
            print(f"\n!! FAILED {os.path.basename(p)}: {type(e).__name__}: {e}")
    dest = r"F:\_KEA WORLD\KEA BABIES\FEED\Assets\psd_audit_raw.json"
    prev = []
    if os.path.exists(dest):
        prev = json.load(open(dest, encoding="utf-8"))
    names = {i["file"] for i in out}
    prev = [p for p in prev if p["file"] not in names]
    json.dump(prev + out, open(dest, "w", encoding="utf-8"), indent=1)
    print(f"\nwrote {dest}")
