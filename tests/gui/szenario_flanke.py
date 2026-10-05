# Flanke, 5 Achsen simultan (W-015, Spezifikation Strategien 16.3 S3; Manuel, 2026-10-04: „Ja, so
# bauen“, „selbst anhaken, wenn schneller“): Block 80 × 60 × 30 mit einer Tasche 40 × 24, 20 tief,
# Wände mit 10° Formschräge, Ecken R 6 (Kegel); die 5-Achs-Maschine Tisch/Tisch als zuletzt
# benutzte, ein Schaftfräser Ø 10 mit 30 mm Schneide und ein Kugelfräser Ø 6. Die acht Wände
# anklicken → „Bearbeitung“: in der Liste „schräge Wand aus Geraden … – Flanke oder
# 3D-Schlichten“; die Flanke hat den Haken („→ 1 Umlauf, die Achse bis 10° geneigt, etwa …“,
# schneller als das 3D-Schlichten), das 3D-Schlichten nicht. „Anlegen“: „Flanke T…“ mit je Satz
# einer Achse. „Auf der Maschine prüfen“: A steht auf −10°, nichts über die Grenzen.
import math
import os
import tempfile

import FreeCAD
import FreeCADGui as Gui
import Part
from PySide import QtCore

V = FreeCAD.Vector


def rundrechteck(b, h, r, z, mx=40.0, my=30.0):
    x0, x1, y0, y1 = mx - b / 2, mx + b / 2, my - h / 2, my + h / 2
    kanten = []
    for (ax, ay), (ex, ey), (cx, cy), w0 in (
        ((x0 + r, y0), (x1 - r, y0), (x1 - r, y0 + r), -90),
        ((x1, y0 + r), (x1, y1 - r), (x1 - r, y1 - r), 0),
        ((x1 - r, y1), (x0 + r, y1), (x0 + r, y1 - r), 90),
        ((x0, y1 - r), (x0, y0 + r), (x0 + r, y0 + r), 180),
    ):
        kanten.append(Part.LineSegment(V(ax, ay, z), V(ex, ey, z)).toShape())
        kreis = Part.Circle(V(cx, cy, z), V(0, 0, 1), r)
        kanten.append(Part.ArcOfCircle(kreis, math.radians(w0), math.radians(w0 + 90)).toShape())
    return Part.Wire(kanten)


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import PARAMETER_PFAD, beispielmaschine, gui_bearbeitung, gui_reichweite
    from camaddon import flanke as flop
    from camaddon import flanke_bahn as fb
    from camaddon import maschinenspeicher as msp
    from camaddon import reichweite as rw
    from camaddon import werkzeuge as wz

    ordner = tempfile.mkdtemp()
    asm, _maschine = beispielmaschine.lade(beispielmaschine.TISCH_TISCH)
    pfad_maschine = os.path.join(ordner, "fuenfachs.FCStd")
    asm.Document.saveAs(pfad_maschine)
    msp.merken_datei(pfad_maschine)
    FreeCAD.ParamGet(PARAMETER_PFAD).SetString(rw.ZULETZT_MASCHINE, pfad_maschine)
    yield 300
    t5 = wz.Werkzeug(
        nummer=5,
        name="VHM 10 lang",
        art=wz.SCHAFTFRAESER,
        durchmesser=10.0,
        schneiden=4,
        schneidenlaenge=30.0,
        gesamtlaenge=80.0,
        schneidstoff=wz.VHM,
    )
    t5.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=20.0, vc=150.0, fz=0.04)]
    t3 = wz.Werkzeug(
        nummer=3,
        name="Kugel 6",
        art=wz.KUGELFRAESER,
        durchmesser=6.0,
        schneiden=2,
        schneidenlaenge=12.0,
        gesamtlaenge=60.0,
        schneidstoff=wz.VHM,
    )
    t3.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=0.3, vc=150.0, fz=0.05)]
    wz.Bibliothek([t5, t3]).speichern()

    doc = FreeCAD.newDocument("Formschraege")
    doc.UndoMode = 1
    d = 20 * math.tan(math.radians(10))
    loft = Part.makeLoft(
        [rundrechteck(40, 24, 6, 10.0), rundrechteck(40 + 2 * d, 24 + 2 * d, 6 + d, 30.0)],
        True,
        True,
    )
    teil = doc.addObject("Part::Feature", "Block")
    teil.Shape = Part.makeBox(80, 60, 30).cut(loft).removeSplitter()
    doc.recompute()
    FreeCAD.setActiveDocument(doc.Name)
    waende = [
        f"Face{i + 1}"
        for i in range(len(teil.Shape.Faces))
        if fb.ist_wand(teil.Shape, f"Face{i + 1}")
    ]
    h.pruefe(len(waende) == 8, f"Wände: {waende}")
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, waende[0])
    yield 500

    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2500
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    eintrag = panel.maschine()
    h.pruefe(eintrag is not None and eintrag.art == msp.FRAESE_5, f"Maschine: {eintrag}")
    for name in waende[1:]:
        panel.flaeche_umschalten(name)
    yield 1000
    flanke, s3 = panel.flanke, panel.schlichten3d
    yield from h.warte_auf(
        lambda: all(b.vorschau is not None or not b.aktiv() for b in panel.bloecke), 300000
    )
    yield from h.warte_auf(lambda: flanke.zeit is not None and s3.zeit is not None, 300000)
    yield 2000
    liste = [panel.flaechen_liste.item(i).text() for i in range(panel.flaechen_liste.count())]
    h.pruefe(
        all("schräge Wand aus Geraden" in t and "Flanke oder 3D-Schlichten" in t for t in liste),
        f"Liste: {liste[:2]}",
    )
    h.pruefe(flanke.aktiv() and not s3.aktiv(), f"Haken: Flanke {flanke.aktiv()}, 3D {s3.aktiv()}")
    h.pruefe(flanke.fraeser() is not None and flanke.fraeser().nummer == 5, "Flanke nicht T5")
    text = flanke.ergebnis.text()
    h.pruefe(
        text.startswith("→ 1 Umlauf, die Achse bis 10° geneigt, etwa ")
        and "die schnellste" in text,
        f"Flanke: {text!r}",
    )
    h.pruefe(flanke.zeit < s3.zeit, f"Flanke {flanke.zeit} min, 3D {s3.zeit} min")
    h.pruefe(not flanke.hinweis.text(), f"rot: {flanke.hinweis.text()!r}")
    # Die Flanke macht die Wände fertig – kein roter Satz darüber, kein „Ebene schwenken“.
    h.pruefe(not panel.unfertig.isVisible(), f"unfertig: {panel.unfertig.text()!r}")
    h.pruefe(not panel.schwenken_zeile.isVisible(), "„Ebene schwenken“ angeboten")
    panel.seite_zeigen(1)
    yield 500
    h.bild("1_was_soll_weg", panel.form)
    panel.seite_zeigen(2)
    yield 500
    h.bild("2_einstellungen", panel.form)

    # --- Anlegen ------------------------------------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    ops = [o for o in job.Operations.Group if flop.ist_flanke(o)]
    h.pruefe(len(ops) == 1, f"Operationen: {[o.Label for o in job.Operations.Group]}")
    if not ops:
        return
    op = ops[0]
    h.pruefe(op.Label == "Flanke T5" and op.Umlaeufe == 1, f"{op.Label}, {op.Umlaeufe}")
    h.pruefe(len(op.Werkzeugachsen) == len(op.Path.Commands) > 10, "Achsen je Satz")
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("3_angelegt")

    # --- Auf der Maschine prüfen ------------------------------------------------------------
    Gui.Selection.addSelection(job)
    yield 400
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None, 120000)
    pruef = gui_reichweite.PruefPanel.offen
    h.pruefe(pruef is not None, "„Auf der Maschine prüfen“ öffnet kein Fenster")
    if pruef is None:
        return
    yield 1500
    spieler = pruef.abspieler
    fahrt = spieler.abfahrt
    schraeg = [
        i for i, s in enumerate(fahrt.stationen) if abs(float(s.rund.get("A", 0.0)) + 10) < 0.01
    ]
    h.pruefe(len(schraeg) > 20, f"Stationen mit A −10°: {len(schraeg)}")
    if schraeg:
        spieler.springe_zu_station(schraeg[len(schraeg) // 3])
    yield 600
    spieler.knopf_hinsehen.click()
    yield 800
    h.bild("4_auf_der_maschine")
    pruef.reject()
    yield 500
    FreeCAD.closeDocument(doc.Name)
    yield 300
