# KeaBabies — Amazon Listing Harness  ·  **KEALIST**

> Turns a new **colourway** into a finished Amazon listing: approved colour reference →
> recoloured listing PSDs + JPGs → listing copy → verified delivery.
> **Status:** production-proven on *Urban Burp Cloths · Atlas* (8 images, 2026-08-29).

Client: **KeaBabies** · Category: **Feed** (parameterised — add more via config)
App home: `F:\_AI TOOLS\_AI AUTOMATION\KeaBabies Amazon Listing\`

---

## The idea

KeaBabies sells each product as a **5-pack under a colourway set name** (*Atlas, Slate,
Grayscape, Wilderness*…). A new colourway is not new photography — it is the **same listing
images recoloured**. This harness does that recolour to a measured tolerance, and writes the
listing copy that ships with it.

The value is not the recolour. It is the **closed loop**:

```
measure  →  solve  →  apply  →  verify  →  correct  →  re-verify
```

On the Atlas run that loop caught three failures that looked fine by eye:
a washed-out fill (ΔE 20.6), a chroma-skewed layer order (ΔE 5.9), and an image where only
the piping recoloured (ΔE 12.0). See `LESSONS.md`.

---

## Quick start

```powershell
$py = "C:\Users\Paul\miniconda3\python.exe"
cd "F:\_AI TOOLS\_AI AUTOMATION\KeaBabies Amazon Listing\scripts"

# whole colourway, all images, with the correction loop
& $py run_pipeline.py --product urban-burp-cloths --colorway atlas

# one image
& $py run_pipeline.py --product urban-burp-cloths --colorway atlas --only "Image 3"

# skip the measure stage (gammas already solved)
& $py run_pipeline.py --product urban-burp-cloths --colorway atlas --from apply
```

Requires **Photoshop 2026** installed (the JSX is driven through `Photoshop.exe`) and
miniconda Python with `numpy`, `pillow`, `scipy`, `psd-tools`.

---

## Method C — the recolour

Two **non-destructive** layers per cloth, clipped to a Smart Object or contained by a group mask:

```
[ATLAS Color Fill - <variant>]   blend COLOR    ← hue + saturation (target hex)
[ATLAS Levels - <gamma>]         gamma          ← luminance
 <cloth layer / group>                          ← untouched
```

**Order is not cosmetic.** `COLOR` blend inherits luminance from below and cannot darken;
gamma darkens but skews chroma. Fill on top re-imposes the exact hue after the luminance is
right. Reversed, the same image measures ΔE 5.9 instead of 1.9.

Gamma is **solved, never guessed**:
`gamma = ln(Y₀/255) / ln(Y₁/255)`, with `Y = 0.30R + 0.59G + 0.11B` — Photoshop's own
COLOR/LUMINOSITY weights, in gamma space.

Nothing is rasterised. No Smart Object is opened or replaced. The canvas is never resized.
**Masters are opened read-only and never written to** — every run works on a copy in `output/`.

---

## Gates (`config/products/*.json → gates`)

| Gate | Default | Meaning |
|---|---|---|
| `de2000_max` | **3.0** | cloth colour vs approved target |
| `stray_pixels_max` | **2000** | pixels changed outside the cloth |
| `max_correction_loops` | **3** | then STOP and report — never lower the gate |

Containment is measured by diffing the BEFORE/AFTER Photoshop renders, so the recoloured
region identifies itself. A wrong container produces a wrong region rather than a silent pass.

---

## Layout

```
KeaBabies Amazon Listing/
├── README.md                 ← this file
├── LESSONS.md                ← ⭐ read before every new colourway
├── docs/
│   ├── 01_PIPELINE.md        stage-by-stage
│   ├── 02_ROLES.md           the 5 harness roles + Ralph gates
│   └── 03_LISTING_COPY.md    title / bullets / description conventions
├── config/
│   ├── products/<slug>.json  paths, per-image container map, gates, untouchables
│   └── colorways/<name>.json variants (hex/LAB/CMYK) + image→variant map + provenance
├── scripts/
│   ├── colorlib.py           PORTABLE colour maths (dE2000, gamma solve, luma)
│   ├── 01_sample_colorway.py reference JPG → variant hexes
│   ├── 02_read_guide_chips.py annotated guide → image→variant map
│   ├── 03a/b/c_audit_*.py    READ-ONLY PSD structure / stacking / fill audits
│   ├── 04_measure_solve.py   cloth luma → gamma
│   ├── 05_apply.py           generate + run the JSX (on a copy)
│   ├── 06_verify.py          the Ralph gate
│   ├── 07_separation_check.py ΔE matrix across the colourway
│   ├── 08_swatch_sheet.py    client approval sheet
│   ├── method_c.jsx          universal recolour template
│   └── run_pipeline.py       one-command orchestrator + correction loop
├── logs/                     solved gammas, generated JSX, Photoshop logs
└── output/                   scratch (client deliverables go to the client folder)
```

---

## Adding a new colourway

1. Drop the client's approved reference image → `01_sample_colorway.py` → `config/colorways/<name>.json`
2. `07_separation_check.py` — **if any pair is under ΔE 5, raise it with the client now**, not later
3. `02_read_guide_chips.py` on the annotated guide → image→variant map
4. `08_swatch_sheet.py` → get the colours signed off before touching a PSD
5. `run_pipeline.py --colorway <name>`
6. Write the listing copy per `docs/03_LISTING_COPY.md`

## Adding a new product

Copy `config/products/urban-burp-cloths.json`, then run `03b_audit_stacking.py` on each PSD to
find the real cloth container. **Do not assume a layer called `Color Fill …` is the cloth hook** —
several of them grade the background (LESSONS L5).

---

## Not to be confused with

`F:\_AI TOOLS\_AI AUTOMATION\Amazon Listing Designer\` — a Node/Electron app that *generates*
new listing images from brand templates. KEALIST *recolours existing client PSDs* and produces
the listing copy. Different jobs, no overlap.

## Related

- `Hemway Product Rollout V2` — same problem shape (118 colour variants) but render-driven
  rather than photographic. `colorlib.py` is the portable piece if the two ever merge.
- Vault skill: `.claude/skills/keababies-amazon-listing/SKILL.md`
- Client work folder: `F:\_KEA WORLD\KEA BABIES\FEED\`
