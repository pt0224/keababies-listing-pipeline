/*  KEALIST - Method C recolour  (universal template)
 *  ---------------------------------------------------------------------------
 *  Placeholders @@PSD@@ @@OUT@@ @@TAG@@ @@BEFORE@@ @@UNITS@@ are filled by
 *  scripts/05_apply.py. Do not run this file directly.
 *
 *  METHOD C - for every unit, two CLIPPED / CONTAINED layers above the cloth:
 *
 *      [ATLAS Color Fill - <variant>]   blend COLOR    <- hue + saturation
 *      [ATLAS Levels - <gamma>]         gamma          <- luminance
 *       <cloth layer or group>                         <- untouched
 *
 *  The Levels sits BELOW the fill on purpose. Blend COLOR inherits luminance
 *  from below and cannot darken; gamma darkens but skews chroma. Putting the
 *  COLOR fill last re-imposes the exact target hue after the luminance is
 *  right. Reversing the two gives dE ~6 instead of ~1 (measured, 2026-08-29).
 *
 *  Nothing is rasterised, no smart object is opened, the canvas is never
 *  resized, and the master PSD is never written to - 05_apply.py always
 *  operates on a copy in the output folder.
 */
#target photoshop

var PSD    = "@@PSD@@";
var OUTJPG = "@@OUT@@";
var BEFORE = "@@BEFORE@@";
var TAG    = "@@TAG@@";
var UNITS  = @@UNITS@@;

var LOG = [];
function log(s) { LOG.push(s); }
function cID(s) { return charIDToTypeID(s); }
function sID(s) { return stringIDToTypeID(s); }

// ------------------------------------------------------------------ lookup
function childByName(c, n) {
    for (var i = 0; i < c.layers.length; i++) if (c.layers[i].name === n) return c.layers[i];
    return null;
}
/* Address by PATH, never by name. Image 9 has groups literally named
   "1".."5" in two different places; a name search finds the wrong one. */
function byPath(doc, path) {
    var c = doc;
    for (var i = 0; i < path.length; i++) { c = childByName(c, path[i]); if (!c) return null; }
    return c;
}
function findAnywhere(c, n) {
    for (var i = 0; i < c.layers.length; i++) {
        var L = c.layers[i];
        if (L.name === n) return L;
        if (L.typename === "LayerSet") { var r = findAnywhere(L, n); if (r) return r; }
    }
    return null;
}

// ------------------------------------------------------------------ builders
function addSolidFill(rgb, name) {
    var d = new ActionDescriptor(), ref = new ActionReference();
    ref.putClass(sID("contentLayer")); d.putReference(cID("null"), ref);
    var dc = new ActionDescriptor();
    dc.putDouble(cID("Rd  "), rgb[0]); dc.putDouble(cID("Grn "), rgb[1]); dc.putDouble(cID("Bl  "), rgb[2]);
    var dt = new ActionDescriptor(); dt.putObject(cID("Clr "), cID("RGBC"), dc);
    var du = new ActionDescriptor(); du.putObject(cID("Type"), sID("solidColorLayer"), dt);
    d.putObject(cID("Usng"), sID("contentLayer"), du);
    executeAction(cID("Mk  "), d, DialogModes.NO);
    var L = app.activeDocument.activeLayer;
    L.name = name; L.blendMode = BlendMode.COLORBLEND;
    return L;
}
function addLevelsGamma(gamma, name) {
    var d = new ActionDescriptor(), ref = new ActionReference();
    ref.putClass(sID("adjustmentLayer")); d.putReference(cID("null"), ref);
    var dp = new ActionDescriptor();
    dp.putEnumerated(sID("presetKind"), sID("presetKindType"), sID("presetKindDefault"));
    var du = new ActionDescriptor(); du.putObject(cID("Type"), cID("Lvls"), dp);
    d.putObject(cID("Usng"), sID("adjustmentLayer"), du);
    executeAction(cID("Mk  "), d, DialogModes.NO);

    var d2 = new ActionDescriptor(), r2 = new ActionReference();
    r2.putEnumerated(cID("AdjL"), cID("Ordn"), cID("Trgt")); d2.putReference(cID("null"), r2);
    var da = new ActionDescriptor(), lst = new ActionList(), dch = new ActionDescriptor();
    var rch = new ActionReference(); rch.putEnumerated(cID("Chnl"), cID("Chnl"), cID("Cmps"));
    dch.putReference(cID("Chnl"), rch); dch.putDouble(cID("Gmm "), gamma);
    lst.putObject(cID("LvlA"), dch); da.putList(cID("Adjs"), lst);
    d2.putObject(cID("T   "), cID("Lvls"), da);
    executeAction(cID("setd"), d2, DialogModes.NO);

    var L = app.activeDocument.activeLayer; L.name = name; return L;
}
/* GOTCHA: Photoshop auto-clips a layer created directly above an existing
   clipping-group base, and the explicit "Create Clipping Mask" command then
   throws "not currently available". The DOM property is idempotent. */
function clipTo(L) {
    try { if (L && L.grouped === false) L.grouped = true; }
    catch (e) { log("   clip warn: " + e.message); }
}
function exportJPG(doc, path) {
    var o = new JPEGSaveOptions();
    o.quality = @@QUALITY@@; o.embedColorProfile = true;
    o.formatOptions = FormatOptions.STANDARDBASELINE;
    doc.saveAs(new File(path), o, true, Extension.LOWERCASE);   // asCopy -> layers survive
}

// ---------------------------------------------------------------------- run
var oldUnits = app.preferences.rulerUnits;
app.preferences.rulerUnits = Units.PIXELS;
app.displayDialogs = DialogModes.NO;

var doc = null;
try {
    doc = app.open(new File(PSD));
    var W0 = doc.width.value, H0 = doc.height.value;
    log("opened " + doc.name + "  " + W0 + "x" + H0);

    if (BEFORE !== "") { exportJPG(doc, BEFORE); log("exported BEFORE baseline"); }

    var done = 0;
    for (var i = 0; i < UNITS.length; i++) {
        var u = UNITS[i];
        var t = (u.path && u.path.length > 1) ? byPath(doc, u.path) : findAnywhere(doc, u.path[0]);
        if (!t) { log("MISS  " + u.path.join("/")); continue; }

        if (u.kind === "smartobject" || t.typename === "ArtLayer") {
            doc.activeLayer = t;
            var lv = addLevelsGamma(u.gamma, "ATLAS Levels - " + u.label); clipTo(lv);
            doc.activeLayer = lv;
            var fl = addSolidFill(u.rgb, "ATLAS Color Fill - " + u.label); clipTo(fl);
        } else {
            if (t.layers.length === 0) { log("SKIP empty group " + u.path.join("/")); continue; }
            /* GOTCHA: if the group's top child is itself a GROUP, creating a
               layer while it is active drops the new layer INSIDE that child
               group - which recolours only that sub-part (cost us Image 5B).
               Create, then MOVE explicitly to the top of the intended group. */
            doc.activeLayer = t.layers[0];
            var lv2 = addLevelsGamma(u.gamma, "ATLAS Levels - " + u.label);
            lv2.move(t, ElementPlacement.PLACEATBEGINNING);
            var fl2 = addSolidFill(u.rgb, "ATLAS Color Fill - " + u.label);
            fl2.move(t, ElementPlacement.PLACEATBEGINNING);
        }
        done++;
        log("OK    " + u.path.join("/") + "  -> " + u.label + "  gamma=" + u.gamma);
    }
    log("units applied: " + done + "/" + UNITS.length);
    if (done === 0) throw new Error("no units applied - check container paths");

    exportJPG(doc, OUTJPG);
    log("exported " + OUTJPG);

    var po = new PhotoshopSaveOptions(); po.layers = true; po.embedColorProfile = true;
    doc.saveAs(new File(PSD), po, false, Extension.LOWERCASE);
    log("saved psd");

    if (doc.width.value !== W0 || doc.height.value !== H0)
        log("!! SIZE CHANGED " + W0 + "x" + H0 + " -> " + doc.width.value + "x" + doc.height.value);
    else
        log("size preserved: " + W0 + "x" + H0);

    doc.close(SaveOptions.DONOTSAVECHANGES);
    log("STATUS=OK");
} catch (e) {
    log("STATUS=FAIL  " + e.message);
    try { if (doc) doc.close(SaveOptions.DONOTSAVECHANGES); } catch (e2) {}
}
app.preferences.rulerUnits = oldUnits;

var f = new File("@@LOG@@");
f.open("w"); f.write(LOG.join("\n")); f.close();
