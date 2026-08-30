# KEALIST — Harness roles & Ralph gates

Five roles. Each owns one stage and one question. A role never approves its own output —
the Verifier is the only role that can pass a gate.

---

## 1. Auditor — *"where is the cloth?"*

Read-only. Maps every PSD's layer tree with true top-to-bottom order and clipping flags,
and identifies the container that actually owns the product.

- `03a_audit_layers.py` · `03b_audit_stacking.py` · `03c_audit_fills.py`
- **Must distinguish a cloth hook from a background grade.** A `Color Fill` layer buried in a
  BG group is a backdrop tint, not the product (LESSONS L5).
- Records the answer into `config/products/<slug>.json → images[].container/kind`.

**Gate — Brief:** is the container above the cloth, and does its coverage look like a cloth?

---

## 2. Colourist — *"what colour, exactly?"*

Owns the approved reference. Extracts hex / RGB / LAB / CMYK per variant, with sampling stats,
and runs the separation matrix.

- `01_sample_colorway.py` · `02_read_guide_chips.py` · `07_separation_check.py` · `08_swatch_sheet.py`
- Sampling is the **median of the fabric body** with the top/bottom 20% of luma trimmed, taken
  from two bands per panel, away from piping, seam and overlap shadow.
- Any pair under **ΔE 5** is escalated as a design constraint, not logged as a QA note.

**Gate — Spec:** are the colours signed off, and is the image→variant map confirmed?

---

## 3. Solver — *"how much darker?"*

Measures the cloth's current luminance and solves the Levels gamma in closed form.

- `04_measure_solve.py`, `colorlib.solve_gamma`
- `gamma = ln(Y₀/255) / ln(Y₁/255)` with the 0.30/0.59/0.11 gamma-space weights.
- Group-derived numbers are **provisional** — psd-tools ignores a group's own mask
  (LESSONS L6). Smart-object numbers are exact.

**Gate — Spec:** is the gamma solved from a measurement, not chosen by eye?

---

## 4. Operator — *"apply it, change nothing else"*

The only role that talks to Photoshop.

- `05_apply.py` + `method_c.jsx`
- Hard rules: work on a **copy**; never open/replace/rasterise a Smart Object; never resize;
  address multi-unit files by **path, not name**; leave everything in `untouchables` alone.

**Gate — Asset:** did every unit apply, and is the canvas still the original size?

---

## 5. Verifier — *"prove it"*

The only role that can pass work. Objective, two-part, no eyeballing.

- `06_verify.py`
- **Colour:** ΔE2000 < 3.0 against the approved target.
- **Containment:** stray changed pixels outside the self-identified region.
- On failure it re-solves the gamma from the real render and hands back a correction.

**Gate — Delivery:** both checks green, at native size, master untouched?

---

## The correction loop

```
apply → verify → FAIL → re-solve gamma from the BEFORE render → re-apply → verify
```

Bounded by `gates.max_correction_loops` (default 3). After that it **stops and reports**.

Two things it will never do: lower a gate to make something pass, or approve on appearance.
A washed-out fill and a piping-only recolour both look plausible in a thumbnail — that is
precisely why the gate is numeric.

---

## Escalate to Paul (taste-level, one tap)

The harness decides craft autonomously. These go to Paul:

- a colourway pair under ΔE 5 — accept the adjacency rule, or ask the client to separate them?
- an image containing more cloths than the guide marks (which ones change?)
- artwork baked into a photograph with no layer to drive (e.g. printed packaging graphics)
- any image still failing after the correction loop
