# Runde Rohteile auf der Fräse (W-021; Manuel, 2026-10-12: „ich kann auch auf der fräsmaschine ein
# dreibacken futter einspannen und somit runde rohteile haben“; 2026-10-16: „wie gesagt es gibt auch
# runde rohteile auf der fräse“): Manuels C-Ring (Ø 60 × 10) ohne Job, die Oberseite angeklickt,
# „Bearbeitung“ auf der 3-Achs-Fräse. In Schritt 1 „Zylinder mit Aufmaß“, Aufmaß oben 1, Umfang 2,
# unten 3: Das Rohteil des Jobs ist ein stehender Zylinder um den Ring – Radius 32, Höhe 14, die
# Achse in der Mitte des Rings. Oben in Schritt 2 steht „Zylinder, Aufmaß oben 1, Umfang 2, unten
# 3 mm“. Das Planfräsen der Oberseite fährt nicht in den leeren Ecken des Kastens um den Zylinder
# (Materialstand aus dem Rohteil).
import math
import os
import shutil
import tempfile

import FreeCAD
import FreeCADGui as Gui

ADDON = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine, gui_bearbeitung
    from camaddon import maschinenspeicher as ms
    from camaddon import werkzeuge as wz

    wz.Bibliothek([wz.standardwerkzeug()]).speichern()
    ms.speichern([])
    ordner = tempfile.mkdtemp()
    asm, _maschine = beispielmaschine.lade(beispielmaschine.FRAESE_3)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    asm.Document.saveAs(os.path.join(ordner, "Fraese.FCStd"))
    yield 300
    datei = os.path.join(ordner, "cring.FCStd")
    shutil.copy(os.path.join(ADDON, "beispiele", "c_ring_nut_3achs.FCStd"), datei)
    doc = FreeCAD.openDocument(datei)
    # Ohne seinen Job: Der Assistent legt einen neuen an (Schritt 1 offen).
    koerper = doc.getObject("Body")
    bleibt = {koerper.Name, *(o.Name for o in koerper.OutListRecursive)}
    for job in [o for o in doc.Objects if hasattr(o, "Operations")]:
        weg = [o.Name for o in job.OutListRecursive if o.Name not in bleibt]
        doc.removeObject(job.Name)
        for name in weg:
            if doc.getObject(name) is not None:
                doc.removeObject(name)
    doc.recompute()
    yield 500
    Gui.activateWorkbench("CAMWorkbench")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, "Body", "Face4")
    yield 500
    gui_bearbeitung.nullpunkt_vorgeben(None)
    Gui.runCommand("CamAddon_Bearbeitung")
    yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not None)
    yield 1500
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    panel.knopf_rohteil_zylinder.setChecked(True)
    for feld, wert in (("oben", "1"), ("seite", "2"), ("unten", "3")):
        panel.felder_rohteil[feld].setText(wert)
    panel._rohteil_anwenden()
    yield 1000
    rohteil = panel.job.Stock
    h.pruefe(hasattr(rohteil, "Radius"), f"kein Zylinder: {rohteil.TypeId}")
    if hasattr(rohteil, "Radius"):
        radius, hoehe = float(rohteil.Radius), float(rohteil.Height)
        h.pruefe(abs(radius - 32.0) < 0.05, f"Radius {radius}")
        h.pruefe(abs(hoehe - 14.0) < 1e-6, f"Höhe {hoehe}")
        teil = panel.job.Model.Group[0].Shape
        mitte = rohteil.Placement.Base
        kante = max(math.hypot(v.Point.x - mitte.x, v.Point.y - mitte.y) for v in teil.Vertexes)
        h.pruefe(abs(kante - 30.0) < 0.05, f"Achse nicht in der Mitte des Rings: {kante:.3f}")
    h.bild("1_zylinder")
    panel.seite_zeigen(1)
    yield 500
    h.pruefe(
        "Zylinder, Aufmaß oben 1, Umfang 2, unten 3 mm" in panel.rohteil_kurz.text(),
        f"oben: {panel.rohteil_kurz.text()!r}",
    )
    yield from h.warte_auf(
        lambda: not panel.vorschau_laeuft()
        and all(b.vorschau is not None or not b.aktiv() for b in panel.bloecke),
        300000,
    )
    yield 2000
    plan = panel.plan
    h.pruefe(plan.aktiv() and plan.vorschau is not None, f"Planfräsen: {plan.ergebnis.text()!r}")
    if plan.vorschau is not None and hasattr(rohteil, "Radius"):
        mitte = rohteil.Placement.Base
        aussen = [
            p
            for p in plan.vorschau.punkte
            if not p.eilgang
            and p.z < mitte.z + float(rohteil.Height) - 0.01
            and math.hypot(p.x - mitte.x, p.y - mitte.y) > float(rohteil.Radius) + 6.5
        ]
        h.pruefe(not aussen, f"Planfräsen in den leeren Ecken: {len(aussen)} Punkte")
    h.bild("2_was_soll_weg", panel.form)
    panel.reject()
    yield 500
