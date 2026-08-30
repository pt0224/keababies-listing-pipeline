# -*- coding: utf-8 -*-
"""READ-ONLY deep audit: solid-colour fill VALUES + smart-object link info.
Tells us the CURRENT (Basic colourway) colours and whether cloth smart objects are
embedded or externally linked -- which decides replace-contents vs recolour."""
import sys, os, json
from psd_tools import PSDImage

def so_info(l):
    d = {}
    try:
        so = l.smart_object
        d["so_kind"] = str(getattr(so, "kind", "?"))
        d["so_name"] = getattr(so, "filename", None)
        d["so_type"] = str(getattr(so, "filetype", None))
        try: d["so_bytes"] = len(so.data) if so.kind == "data" else None
        except Exception: d["so_bytes"] = None
    except Exception as e:
        d["so_error"] = f"{type(e).__name__}"
    return d

def fill_info(l):
    out = {}
    try:
        data = l.data
        def find(o):
            if hasattr(o, "items"):
                for k, v in o.items():
                    ks = k.decode() if isinstance(k, bytes) else str(k)
                    if ks.strip() in ("Clr", "Rd", "Grn", "Bl"):
                        yield ks.strip(), v
                    yield from find(v)
            elif isinstance(o, (list, tuple)):
                for v in o: yield from find(v)
        rgb = {}
        for k, v in find(data):
            if k in ("Rd", "Grn", "Bl"):
                try: rgb[k] = float(v)
                except Exception: pass
        if {"Rd", "Grn", "Bl"} <= set(rgb):
            r, g, b = [int(round(rgb[k])) for k in ("Rd", "Grn", "Bl")]
            out["fill_rgb"] = [r, g, b]
            out["fill_hex"] = "#{:02X}{:02X}{:02X}".format(r, g, b)
    except Exception as e:
        out["fill_error"] = f"{type(e).__name__}"
    return out

def walk(layer, rows, path=""):
    for l in layer:
        full = f"{path}/{l.name}" if path else l.name
        r = {"path": full, "name": l.name, "kind": l.kind, "visible": bool(l.visible)}
        try: r["bbox"] = list(l.bbox)
        except Exception: r["bbox"] = None
        if l.kind == "smartobject": r.update(so_info(l))
        if l.kind in ("solidcolorfill",): r.update(fill_info(l))
        if l.kind == "smartobject" or l.kind == "solidcolorfill":
            rows.append(r)
        if l.is_group(): walk(l, rows, full)

res = {}
for p in sys.argv[1:]:
    name = os.path.basename(p)
    try:
        psd = PSDImage.open(p)
        rows = []
        walk(psd, rows)
        res[name] = rows
        print(f"\n===== {name} =====")
        for r in rows:
            extra = ""
            if "fill_hex" in r: extra = f"  FILL {r['fill_hex']} {r.get('fill_rgb')}"
            if r["kind"] == "smartobject":
                extra = f"  SO[{r.get('so_kind')}] {str(r.get('so_name'))[:52]} type={r.get('so_type')}"
            print(f"  {'':2s}{r['name'][:46]:46s} {r['kind']:14s} vis={int(r['visible'])}{extra}")
    except Exception as e:
        print(f"!! {name}: {type(e).__name__}: {e}")

dest = r"F:\_KEA WORLD\KEA BABIES\FEED\Assets\psd_detail_raw.json"
prev = json.load(open(dest, encoding="utf-8")) if os.path.exists(dest) else {}
prev.update(res)
json.dump(prev, open(dest, "w", encoding="utf-8"), indent=1)
print(f"\nwrote {dest}")
