# -*- coding: utf-8 -*-
"""KEALIST stage 5 - apply Method C to one listing image via Photoshop JSX.

Always works on a COPY in the output folder. The master is opened only by
stage 4 (read-only) and is never written to.

    python 05_apply.py --product urban-burp-cloths --colorway atlas --tag "Image 3"
    python 05_apply.py ... --tag "Image 3" --gamma 0.505      # override the solve
"""
import argparse, json, os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from colorlib import luma, solve_gamma, body_median

PHOTOSHOP = r"C:\Program Files\Adobe\Adobe Photoshop 2026\Photoshop.exe"


def cfg(product, colorway):
    p = json.load(open(os.path.join(ROOT, "config", "products", f"{product}.json"), encoding="utf-8"))
    c = json.load(open(os.path.join(ROOT, "config", "colorways", f"{colorway}.json"), encoding="utf-8"))
    return p, c


def build_units(prod, cw, gammas, tag, gamma_override=None):
    """Turn config + solved gammas into the UNITS array the JSX consumes."""
    variants = {v["name"]: v for v in cw["variants"]}
    img = next(i for i in prod["images"] if i["tag"] == tag)
    imap = cw["image_map"][tag]
    units = []

    if img["kind"] == "multi":
        bands = json.load(open(os.path.join(ROOT, "logs", f"bands_{cw['colorway']['name'].lower()}_{tag}.json"),
                               encoding="utf-8"))
        for u in img["units"]:
            key = "/".join(u["path"])
            src = u.get("mirrors", key)
            target = imap.get(src) or imap.get(key)
            if not target:
                continue
            g = bands[src]["gamma"]
            units.append({"path": u["path"], "kind": "group", "rgb": variants[target]["rgb"],
                          "gamma": round(g, 4),
                          "label": target + (" rim" if "mirrors" in u else "")})
    else:
        target = imap
        if gamma_override is not None:
            g = gamma_override
        elif tag in gammas and "gamma" in gammas[tag]:
            g = gammas[tag]["gamma"]
        else:
            raise SystemExit(
                f"no solved gamma for '{tag}'.\n"
                f"  run:  python 04_measure_solve.py --product <p> --colorway <c> "
                f"--only \"{tag}\"\n"
                f"  or pass one explicitly with --gamma")
        units.append({"path": [img["container"]], "kind": img["kind"],
                      "rgb": variants[target]["rgb"], "gamma": round(float(g), 4), "label": target})
    return units


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--product", required=True)
    ap.add_argument("--colorway", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--gamma", type=float, default=None)
    ap.add_argument("--no-before", action="store_true", help="skip the BEFORE baseline export")
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()

    prod, cw = cfg(a.product, a.colorway)
    cwname = cw["colorway"]["name"]
    gpath = os.path.join(ROOT, "logs", f"gammas_{a.colorway}.json")
    gammas = json.load(open(gpath, encoding="utf-8")) if os.path.exists(gpath) else {}

    masters = prod["paths"]["masters"]
    outdir = prod["paths"]["output"]
    os.makedirs(outdir, exist_ok=True)
    os.makedirs(os.path.join(outdir, "_verify"), exist_ok=True)

    src = os.path.join(masters, prod["paths"]["master_pattern"].format(tag=a.tag))
    base = prod["paths"]["out_pattern"].format(colorway=cwname, tag=a.tag)
    dst_psd = os.path.join(outdir, base + ".psd")
    out_jpg = os.path.join(outdir, base + ".jpg")
    before = "" if a.no_before else os.path.join(outdir, "_verify", f"{a.tag} BEFORE.jpg")

    if not os.path.exists(src):
        sys.exit(f"master not found: {src}")
    print(f"copying master -> {dst_psd}")
    shutil.copy2(src, dst_psd)

    units = build_units(prod, cw, gammas, a.tag, a.gamma)
    print(f"units: {len(units)}")
    for u in units:
        print(f"   {'/'.join(u['path'])[:52]:52s} -> {u['label']:20s} gamma={u['gamma']}")

    tpl = open(os.path.join(HERE, "method_c.jsx"), encoding="utf-8").read()
    logf = os.path.join(ROOT, "logs", f"jsx_{a.tag.replace(' ', '_')}.txt")
    jsx = (tpl.replace("@@PSD@@", dst_psd.replace("\\", "/"))
              .replace("@@OUT@@", out_jpg.replace("\\", "/"))
              .replace("@@BEFORE@@", before.replace("\\", "/"))
              .replace("@@TAG@@", a.tag)
              .replace("@@QUALITY@@", str(prod["export"]["jpeg_quality"]))
              .replace("@@LOG@@", logf.replace("\\", "/"))
              .replace("@@UNITS@@", json.dumps(units, indent=2)))
    jsx_path = os.path.join(ROOT, "logs", f"run_{a.tag.replace(' ', '_')}.jsx")
    open(jsx_path, "w", encoding="utf-8").write(jsx)

    if os.path.exists(logf):
        os.remove(logf)
    print("running photoshop ...")
    subprocess.Popen([PHOTOSHOP, jsx_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    t0 = time.time()
    while time.time() - t0 < a.timeout:
        if os.path.exists(logf):
            time.sleep(1.5)
            break
        time.sleep(3)
    if not os.path.exists(logf):
        sys.exit(f"TIMEOUT after {a.timeout}s - no log at {logf}")

    log = open(logf, encoding="utf-8").read()
    print("\n" + log)
    if "STATUS=OK" not in log:
        sys.exit(1)


if __name__ == "__main__":
    main()
