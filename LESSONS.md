# KEALIST — LESSONS

Self-improving log. **Every entry here cost real time to discover.** Read this before
touching a new colourway, and append to it whenever something bites.

Format: what happened → why → what to do instead.

---

## L1 — A `COLOR` blend cannot darken *(2026-08-29, Atlas)*

**What happened.** Swapping the Color Fill value alone produced pale, washed-out cloths.
Image 2 came out `#D9C8C0` against a `#938279` target — **ΔE 20.6**.

**Why.** Photoshop's `COLOR` blend takes hue + saturation from the fill and inherits
**luminance from the layers below**. The Atlas palette is 16–32 L\* darker than the Basic
colours baked into the PSDs, so there was no mechanism to darken.

**Do instead.** Pair every Color Fill with a **Levels gamma** layer. Solve it, don't guess:
`gamma = ln(Y₀/255) / ln(Y₁/255)` using the 0.30/0.59/0.11 gamma-space weights.

---

## L2 — The Levels must sit BELOW the fill *(2026-08-29, Atlas)*

**What happened.** With Levels *above* the Color Fill, Image 2 landed at `#A48474` — visibly
too red. **ΔE 5.9.**

**Why.** A gamma curve darkens the channels unevenly, which shifts chroma. Applied after the
hue swap, that skew is the final word.

**Do instead.** Order is `Color Fill (COLOR)` on top, `Levels (gamma)` underneath, both
clipped/contained to the cloth. The fill then re-imposes the exact target hue *after* the
luminance is correct. Same file, same gamma, reordered: **ΔE 20.6 → 5.9 → 1.9.**

---

## L3 — Group top-child trap *(2026-08-29, Image 5B)*

**What happened.** Image 5B recoloured **only the piping**, not the cloth body. 107k px changed
instead of ~1M. It looked plausible in a thumbnail; only the ΔE gate caught it (12.0).

**Why.** The script set the group's topmost child active, then created the new layer. When that
top child is *itself a group*, Photoshop creates the new layer **inside** it — so the recolour
only reached the `rims` subgroup.

**Do instead.** Never rely on creation position. Create the layer, then move it explicitly:
`layer.move(group, ElementPlacement.PLACEATBEGINNING)`.

---

## L4 — "Create Clipping Mask is not currently available" *(2026-08-29, Image 4)*

**What happened.** Image 4 aborted outright with that error.

**Why.** Its Smart Object already had a clipped Hue/Sat above it. A layer inserted directly
above an existing clipping-group base is **auto-clipped** by Photoshop, and the explicit
`groupEvent` action then fails because there is nothing left to do.

**Do instead.** Use the idempotent DOM property: `if (L.grouped === false) L.grouped = true;`

---

## L5 — Not every `Color Fill` is a cloth hook *(2026-08-29, Image 2)*

**What happened.** The first plan named `Color Fill 1` as Image 2's recolour hook. It isn't —
it lives inside the `BG 08/31 > BG` group and grades the **background photograph**. Editing it
would have tinted the backdrop and left the cloth untouched.

**Why.** Layer names repeat and say nothing about stacking position or scope.

**Do instead.** Run `03b_audit_stacking.py` — it prints true top-to-bottom order with clipping
flags. Confirm the hook is *above the cloth* before editing. If there is no hook, add one.

---

## L6 — psd-tools ignores a group's own mask *(2026-08-29)*

**What happened.** Gamma solved from a group composite was wrong for Image 5B, because the
sampled region included pixels the group mask hides.

**Why.** `layer.composite()` on a `LayerSet` does not apply that set's own layer mask, so the
returned alpha over-reports coverage.

**Do instead.** Treat group-derived gammas as **provisional**. Measure the final number from a
Photoshop-rendered BEFORE frame, restricted to the region the verify stage identifies. That is
what the correction loop does automatically.

---

## L7 — Verify against what actually changed, not against a mask *(2026-08-29)*

**Why it matters.** Any gate built on "the mask I think is the cloth" inherits the same wrong
assumption that caused the bug. Diffing the BEFORE/AFTER renders makes the region
self-identifying: a wrong container shows up as a wrong region instead of quietly passing.

Keep both halves of the gate — **colour (ΔE < 3.0)** *and* **containment (stray pixels)**. L3
passed neither; a colour-only gate would still have caught it, but a containment-only gate
would not.

---

## L8 — `PYTHONIOENCODING=utf-8` for the audit scripts *(2026-08-29)*

Image 8 has a **narrow no-break space (U+202F)** in a layer name. Printing it crashes the
default Windows console codec, and the script dies *after* doing its work but *before* writing
its JSON — so the file silently goes missing from the results.

---

## L9 — Colour separation is a design constraint, not a QA step *(2026-08-29, Atlas)*

Trailhead Taupe `#97806E` and Granite `#938279` are only **ΔE2000 4.1** apart. They are
distinguishable at full size and near-identical at thumbnail size.

Run `07_separation_check.py` on every new colourway **before** any PSD work. If a pair is under
~5, that is not a retouching problem to fix later — it is a layout rule to enforce now
(never place them adjacent in a pack shot) and a question to raise with the client.

---

## L10 — Chips on the client guide are data, not decoration *(2026-08-29, Atlas)*

The solid rectangles on `Guide Instructions -Task.png` looked like a screenshot artifact. They
are the **image-to-variant map**: every one matched an approved variant at ΔE < 2.0.

Always measure annotations before dismissing them — `02_read_guide_chips.py`.

---

## Open / unresolved

- **Baked-in packaging artwork.** Image 9's printed mountain graphic has no dedicated layer;
  recolouring it needs a colour-range mask bounded to the mountain and excluding the green
  "5 PACK" badge. Not yet automated.
- **Multi-cloth frames.** Images 4 and 6 contain additional cloths the guide chip does not
  mark. The harness recolours only the marked one and reports the others — deliberately, since
  Image 4's middle layer must keep reading as *water-resistant fleece*.
