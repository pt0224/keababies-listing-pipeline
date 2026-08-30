# -*- coding: utf-8 -*-
"""READ-ONLY. Prints each PSD in true TOP-TO-BOTTOM display order with clipping flags,
so we can tell which Color Fill layers actually sit ABOVE / are CLIPPED TO the cloth."""
import sys, os
from psd_tools import PSDImage

def rows(layer, depth, acc, path=""):
    # psd-tools yields bottom->top; reverse for display order
    for l in reversed(list(layer)):
        clip = 0
        try: clip = int(l._record.clipping)
        except Exception: pass
        fill = ""
        if l.kind == "solidcolorfill":
            try:
                def find(o):
                    if hasattr(o,"items"):
                        for k,v in o.items():
                            ks=k.decode() if isinstance(k,bytes) else str(k)
                            if ks.strip() in ("Rd","Grn","Bl"): yield ks.strip(),v
                            yield from find(v)
                    elif isinstance(o,(list,tuple)):
                        for v in o: yield from find(v)
                d={k:float(v) for k,v in find(l.data)}
                if {"Rd","Grn","Bl"}<=set(d):
                    fill=" #{:02X}{:02X}{:02X}".format(*[int(round(d[k])) for k in ("Rd","Grn","Bl")])
            except Exception: pass
        acc.append((depth,l.name,l.kind,str(l.blend_mode).split(".")[-1],bool(l.visible),clip,bool(l.mask),fill))
        if l.is_group(): rows(l, depth+1, acc, path)

for p in sys.argv[1:]:
    psd = PSDImage.open(p)
    acc=[]; rows(psd,0,acc)
    print(f"\n{'='*104}\n{os.path.basename(p)}   (TOP of stack first)\n{'='*104}")
    for depth,name,kind,blend,vis,clip,mask,fill in acc:
        c = " <CLIPPED" if clip else ""
        v = " " if vis else "H"
        print(f"{v} {'  '*depth}{name[:44]:44s} {kind:14s} {blend:12s}{' mask' if mask else '     '}{fill:9s}{c}")
