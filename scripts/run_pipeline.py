# -*- coding: utf-8 -*-
"""KEALIST - one-command orchestrator with a bounded correction loop.

    python run_pipeline.py --product urban-burp-cloths --colorway atlas
    python run_pipeline.py ... --only "Image 3" "Image 7"
    python run_pipeline.py ... --from apply           # skip the measure stage

Stages:  measure -> apply -> verify -> (correct -> re-apply -> re-verify)

The loop is bounded by gates.max_correction_loops (default 3). If an image
still fails after that it STOPS and reports - it never silently ships a failed
gate, and it never lowers the gate to make something pass.
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable


def run(script, args, capture=False):
    cmd = [PY, os.path.join(HERE, script)] + args
    if capture:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    return subprocess.call(cmd), ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--product", required=True)
    ap.add_argument("--colorway", required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--from", dest="start", default="measure",
                    choices=["measure", "apply", "verify"])
    a = ap.parse_args()

    prod = json.load(open(os.path.join(ROOT, "config", "products", f"{a.product}.json"), encoding="utf-8"))
    max_loops = prod["gates"]["max_correction_loops"]
    tags = [i["tag"] for i in prod["images"]]
    if a.only:
        tags = [t for t in tags if t in a.only]
    common = ["--product", a.product, "--colorway", a.colorway]

    if a.start == "measure":
        print("=" * 74 + "\nSTAGE 4  measure + solve gamma\n" + "=" * 74)
        rc, _ = run("04_measure_solve.py", common + (["--only"] + tags if a.only else []))
        if rc != 0:
            sys.exit("measure stage failed")

    summary = []
    for tag in tags:
        print("\n" + "=" * 74 + f"\n{tag}\n" + "=" * 74)
        gamma = None
        verdict, detail = "NOT RUN", ""
        for attempt in range(1, max_loops + 1):
            if a.start != "verify" or attempt > 1:
                args = common + ["--tag", tag]
                if gamma is not None:
                    args += ["--gamma", str(gamma)]
                rc, _ = run("05_apply.py", args)
                if rc != 0:
                    verdict, detail = "APPLY FAILED", f"attempt {attempt}"
                    break
            rc, out = run("06_verify.py", common + ["--tag", tag], capture=True)
            print(out.rstrip())
            if rc == 0:
                verdict, detail = "PASS", f"attempt {attempt}"
                break
            hint = None
            for line in out.splitlines():
                if "--gamma" in line:
                    try:
                        hint = float(line.split("--gamma")[1].strip())
                    except ValueError:
                        pass
            if hint is None or attempt == max_loops:
                verdict = "FAIL"
                detail = f"after {attempt} attempt(s)" + ("" if hint else " - no correction available")
                break
            print(f"\n   -> correcting gamma to {hint} and re-applying (attempt {attempt + 1})")
            gamma = hint
        summary.append((tag, verdict, detail))

    print("\n" + "=" * 74 + "\nSUMMARY\n" + "=" * 74)
    bad = 0
    for tag, v, d in summary:
        print(f"  {tag:10s} {v:14s} {d}")
        if v != "PASS":
            bad += 1
    print(f"\n{len(summary) - bad}/{len(summary)} passed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
