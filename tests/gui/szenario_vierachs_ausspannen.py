# „Halter stößt an“ im 4-Achs-Assistenten bietet den nächsten Schritt an (P-2026-10-11-63):
# Welle Ø 40 (40 mm lang) mit einem Bund Ø 120 dahinter, Stange Ø 130. T1 (Ø 12, Gesamtlänge 70)
# steckt im ER32 (Spanntiefe 40) – er steht 30 mm heraus; nah am Bund stößt die Mutter (Ø 50) an
# den Bund, frei wäre es ab gut 40 mm. Schritt 2: gelb „… bräuchte mindestens …“, dahinter
# „T1 auf … mm ausspannen“. Ein Klick darauf setzt die Länge ab Spindelnase in der
# Werkzeugverwaltung (gespeichert) um so viel länger, grau steht darunter, was gesetzt ist; die
# Prüfung danach findet nichts mehr.
import re

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

    from camaddon import gui_vierachs
    from camaddon import reichweite as rw
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    t1 = wz.Werkzeug(
        nummer=1, durchmesser=12, schneiden=3, schneidenlaenge=26, gesamtlaenge=70, schaft=12
    )
    t1.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=4.8, ap=2, vc=150, fz=0.08)]
    bib = wz.Bibliothek([t1])
    halter = bib.neuer_halter("er32")
    t1.halter = halter.kennung
    bib.speichern()
    laenge_vorher, _quelle = rw.laenge_des_werkzeugs(t1, bib)

    doc = FreeCAD.newDocument("Bund")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Welle")
    form = Part.makeCylinder(20, 40, FreeCAD.Vector(10, 0, 0), FreeCAD.Vector(1, 0, 0))
    form = form.fuse(Part.makeCylinder(60, 10, FreeCAD.Vector(), FreeCAD.Vector(1, 0, 0)))
    teil.Shape = form.removeSplitter()
    doc.recompute()
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    stirn = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if vr.ist_eben(f)
        and (vr.aussennormale(f) - FreeCAD.Vector(1, 0, 0)).Length < 1e-9
        and f.BoundBox.XMin > 49  # die Stirn der Welle vorne, nicht die des Bunds
    )
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, stirn)
    yield 500

    Gui.runCommand("CamAddon_Vierachs")
    yield 1500
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    panel.feld_stange.setText("130")
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 3000)
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    panel.accept()  # Weiter
    yield 300
    h.pruefe(panel.seite == 2, f"Seite {panel.seite}")
    h.pruefe(panel.fraeser() is not None and panel.fraeser().nummer == 1, "Schruppen: nicht T1")
    yield from h.warte_auf(lambda: panel.vorschau is not None, 60000)
    zeile = panel.halter_schruppen
    yield from h.warte_auf(lambda: zeile.isVisible() and panel._halter_auftrag is None, 120000)
    text = zeile.text()
    h.pruefe("T1 steht 30 mm heraus, bräuchte mindestens" in text, f"Halter: {text!r}")
    verweis = re.search(r'href="(ausspannen:[^"]+)"', text)
    h.pruefe(verweis is not None and "T1 auf" in text and "ausspannen" in text, f"{text!r}")
    yield 300
    h.bild("1_halter_stoesst", panel.form)
    if verweis is None:
        return
    _art, _nummer, laenge, heraus = verweis.group(1).split(":")
    h.pruefe(41 <= int(heraus) <= 45, f"ausspannen auf {heraus} mm")

    zeile.linkActivated.emit(verweis.group(1))
    yield 200
    gespeichert = next(w for w in wz.Bibliothek.laden().werkzeuge if w.nummer == 1)
    h.pruefe(
        abs(gespeichert.laenge_spindelnase - float(laenge)) < 1e-3
        and abs(gespeichert.laenge_spindelnase - (laenge_vorher + int(heraus) - 30)) < 1e-3,
        f"Länge ab Spindelnase {gespeichert.laenge_spindelnase} (vorher {laenge_vorher})",
    )
    yield from h.warte_auf(lambda: panel._halter_auftrag is None, 120000)
    yield 300
    text = zeile.text()
    h.pruefe(
        zeile.isVisible()
        and f"T1 steht jetzt {heraus} mm heraus" in text
        and "bräuchte" not in text,
        f"nach dem Ausspannen: {text!r}",
    )
    h.pruefe("im Halter stecken dann noch" in text, f"{text!r}")
    # Nur dort, wo die gelbe Zeile stand – Schlichten und Plan sind nicht angehakt.
    h.pruefe(
        not panel.halter_schlichten.isVisible() and not panel.halter_plan.isVisible(),
        "die Notiz steht auch bei Bearbeitungen, die nicht angehakt sind",
    )
    h.bild("2_ausgespannt", panel.form)
    panel.reject()
    yield 500
    FreeCAD.closeDocument(doc.Name)
    yield 300
