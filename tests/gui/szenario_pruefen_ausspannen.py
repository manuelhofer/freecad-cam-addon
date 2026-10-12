# „Kollision prüfen“ bietet bei einem anstoßenden Halter den nächsten Schritt an
# (P-2026-10-11-63): Welle Ø 40 mit einem Bund Ø 140 dahinter in der Stange Ø 150 auf dem
# Beispiel-Drehautomaten; „Rundum schruppen“ mit T1 (Ø 12, Gesamtlänge 70) im angetriebenen
# Radialhalter ER32 (Spanntiefe 40) – er steht 30 mm heraus, nah am Bund stößt der Halter an.
# Unter den Befunden „T1 auf … mm ausspannen“; ein Klick setzt die Länge ab Spindelnase in der
# Werkzeugverwaltung (gespeichert), grau steht darunter, was gesetzt ist, und das Fenster rechnet
# mit der neuen Länge. Noch einmal geprüft, stößt der Halter von T1 dort nicht mehr an.
import os
import re
import tempfile

import FreeCAD
import FreeCADGui as Gui
import Part


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine, gui_reichweite
    from camaddon import halter as hl
    from camaddon import maschinenspeicher as msp
    from camaddon import reichweite as rw
    from camaddon import vierachs_achsen as va
    from camaddon import vierachs_operation as vo
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    ordner = tempfile.mkdtemp()
    asm, ma = beispielmaschine.lade(beispielmaschine.DREHMASCHINE)
    pfad_maschine = os.path.join(ordner, "drehmaschine_y.FCStd")
    asm.Document.saveAs(pfad_maschine)
    msp.merken_datei(pfad_maschine)
    achse = va.von_maschine(asm, ma)[0]

    t1 = wz.Werkzeug(
        nummer=1, durchmesser=12, schneiden=3, schneidenlaenge=26, gesamtlaenge=70, schaft=12
    )
    t1.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=4.8, ap=2, vc=150, fz=0.08)]
    bib = wz.Bibliothek([t1])
    halter = bib.neuer_halter("vdi_radial_er32", vdi=30)
    t1.halter = halter.kennung
    bib.speichern()
    laenge_vorher, _quelle = rw.laenge_des_werkzeugs(t1, bib)

    doc = FreeCAD.newDocument("Bund")
    teil = doc.addObject("Part::Feature", "Welle")
    form = Part.makeCylinder(20, 40, FreeCAD.Vector(10, 0, 0), FreeCAD.Vector(1, 0, 0))
    form = form.fuse(Part.makeCylinder(70, 10, FreeCAD.Vector(), FreeCAD.Vector(1, 0, 0)))
    teil.Shape = form.removeSplitter()
    doc.recompute()
    stirn = next(
        f
        for f in teil.Shape.Faces
        if vr.ist_eben(f)
        and (vr.aussennormale(f) - FreeCAD.Vector(1, 0, 0)).Length < 1e-9
        and f.BoundBox.XMin > 49
    )
    lage = vr.berechne(teil.Shape, stirn, achse, durchmesser=150)
    job = vr.richte_ein(doc, teil, lage, vr.Stange(150.0, frei_hinten=40.0), achse)
    tc = job.Tools.Group[0]
    tc.Tool.Diameter = 12
    tc.ToolNumber = 1
    tc.HorizFeed = "1500 mm/min"
    vo.lege_an(
        job, tc, achse, zustellung=5.0, steigung=8.0, aufmass=0.3, halter=hl.seitlich(halter)
    )
    doc.recompute()
    rw.merke_maschine(job, pfad_maschine)
    yield 1000
    FreeCAD.setActiveDocument(doc.Name)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400

    Gui.runCommand("CamAddon_AufMaschinePruefen")
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None, 120000, 10)
    pruef = gui_reichweite.PruefPanel.offen
    h.pruefe(pruef is not None, "kein Prüffenster")
    if pruef is None:
        return
    yield from h.warte_auf(lambda: not pruef.rechnet(), 120000)
    k = pruef.kollision
    pruef.urteil_kollision.linkActivated.emit("kollision:pruefen")
    yield from h.warte_auf(lambda: not k.laeuft and k.ergebnis is not None, 300000)
    yield 300
    texte = [b.text() for b in k.ergebnis.befunde]
    halter_t1 = [t for t in texte if "Halter von T1" in t and "bräuchte es mindestens" in t]
    h.pruefe(bool(halter_t1), f"kein Befund „Halter von T1 … bräuchte“: {texte[:3]}")
    zeile = k.ausspannen_zeile.text()
    verweis = re.search(r'href="(ausspannen:[^"]+)"', zeile)
    h.pruefe(k.ausspannen_zeile.isVisible() and verweis is not None, f"Ausspannen: {zeile!r}")
    h.bild("1_halter_stoesst", pruef.form)
    if verweis is None:
        return
    _art, _nummer, laenge, heraus = verweis.group(1).split(":")

    k.ausspannen_zeile.linkActivated.emit(verweis.group(1))
    yield 300
    gespeichert_bib = wz.Bibliothek.laden()
    gespeichert = next(w for w in gespeichert_bib.werkzeuge if w.nummer == 1)
    # Ohne gemessene Länge ab Spindelnase setzt der Klick „Schaut aus dem Halter“
    # (P-2026-10-12-113); die Länge folgt daraus.
    laenge_jetzt, _quelle = rw.laenge_des_werkzeugs(gespeichert, gespeichert_bib)
    h.pruefe(
        abs(laenge_jetzt - float(laenge)) < 1e-3
        and laenge_jetzt > laenge_vorher
        and abs(gespeichert.ausspannlaenge - float(heraus)) < 1e-3,
        f"Länge {laenge_jetzt} (vorher {laenge_vorher}), heraus {gespeichert.ausspannlaenge}",
    )
    notiz = k.notiz.text()
    h.pruefe(
        k.notiz.isVisible() and notiz.startswith(f"T1 steht jetzt {heraus} mm heraus"),
        f"Notiz: {notiz!r}",
    )
    yield from h.warte_auf(lambda: not pruef.rechnet(), 120000)
    yield 300
    h.pruefe(k.ergebnis is None and k.notiz.isVisible(), "nach dem Ausspannen nicht neu gerechnet")
    h.bild("2_ausgespannt", pruef.form)

    pruef.urteil_kollision.linkActivated.emit("kollision:pruefen")
    yield from h.warte_auf(lambda: not k.laeuft and k.ergebnis is not None, 300000)
    yield 300
    texte = [b.text() for b in k.ergebnis.befunde]
    h.pruefe(
        not any("Halter von T1" in t and "bräuchte es mindestens" in t for t in texte),
        f"der Halter von T1 stößt noch an: {texte[:3]}",
    )
    h.bild("3_neu_geprueft", pruef.form)
    pruef.reject()
    yield 800
    FreeCAD.closeDocument(doc.Name)
    yield 300
