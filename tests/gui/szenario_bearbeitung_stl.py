# Ein STL im Assistenten „Bearbeitung“ (W-017, P-2026-10-11-103): Manuels Geist
# (beispiele/geist_stl/Geist1_v2.stl, 68.242 Dreiecke) ohne Maschine (3 Achsen). Das Netz angeklickt,
# „Bearbeitung“: erst „STL als Teil“, „Umwandeln“ → das Fenster mit dem Job. „Weiter“, „Alles aus
# dieser Aufspannung“: gewählt sind die 25.577 Freiform-Dreiecke von oben, die Liste hat statt einer
# Zeile je Dreieck eine („Teil aus STL: … Dreiecke Freiform – 3D-Schruppen, 3D-Schlichten, bis Z
# 0,1“), was nicht geht, steht rot darunter; angehakt nur 3D-Schruppen (T1 Schaftfräser Ø 12) und 3D-Schlichten (T2 Kugel Ø 6),
# die anderen Blöcke sagen, dass ein STL nur Dreiecke hat. Beide Vorschauen rechnen, „Anlegen“: zwei
# Operationen mit Bahnen. Das Fenster steht dabei nie lange (pausen.txt).
import os

import FreeCAD
import FreeCADGui as Gui
import Mesh
from PySide import QtCore

GEIST = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "..",
    "beispiele",
    "geist_stl",
    "Geist1_v2.stl",
)


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import gui_bearbeitung, gui_stl
    from camaddon import maschinenspeicher as ms
    from camaddon import werkzeuge as wz

    t1 = wz.standardwerkzeug()
    t2 = wz.Werkzeug(nummer=2, art=wz.KUGELFRAESER, durchmesser=6, schneiden=2,
                     schneidenlaenge=20)  # fmt: skip
    t2.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=6, vc=150, fz=0.04)]
    wz.Bibliothek([t1, t2]).speichern()
    ms.speichern([])

    doc = FreeCAD.newDocument("Geist")
    doc.UndoMode = 1
    netz = doc.addObject("Mesh::Feature", "Geist1_v2")
    netz.Mesh = Mesh.Mesh(GEIST)
    doc.recompute()
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(netz)
    gui_bearbeitung.nullpunkt_vorgeben(None)
    yield 300

    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_Bearbeitung"))  # modal
    yield from h.warte_auf(lambda: gui_stl.StlDialog.offen is not None, 5000)
    h.pruefe(gui_stl.StlDialog.offen is not None, "Fenster „STL als Teil“ nicht offen")
    if gui_stl.StlDialog.offen is None:
        return
    gui_stl.StlDialog.offen.accept()
    yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not None, 120000)
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    yield 1000
    panel.knopf_weiter.click()
    yield 500
    panel.aus_der_aufspannung()
    yield 500
    h.pruefe(len(panel.gewaehlte) > 20000, f"gewählt: {len(panel.gewaehlte)}")
    zeilen = [panel.flaechen_liste.item(i).text() for i in range(panel.flaechen_liste.count())]
    # Gewählt ist nur Freiform – was von oben nicht geht, steht rot darunter (richtungen_box).
    h.pruefe(
        len(zeilen) == 1
        and zeilen[0].startswith("Teil aus STL: 25\u202f577 Dreiecke Freiform")
        and zeilen[0].endswith("3D-Schruppen, 3D-Schlichten, bis Z 0,1"),
        f"Liste: {zeilen}",
    )
    h.pruefe(panel.richtungen_box.isVisible(), "kein Kasten mit dem, was von oben nicht geht")
    aktiv = sorted(b.s.kennung for b in panel.bloecke if b.aktiv())
    h.pruefe(aktiv == ["schlichten3d", "schruppen3d"], f"angehakt: {aktiv}")
    plan = next(b for b in panel.bloecke if b.s.kennung == "planfraesen")
    h.pruefe(
        not plan.haken.isEnabled() and "nur Dreiecke" in plan.erklaerung.text(),
        f"Planfräsen: {plan.erklaerung.text()!r}",
    )
    schlichten = next(b for b in panel.bloecke if b.s.kennung == "schlichten3d")
    h.pruefe(
        schlichten.fraeser() is not None and schlichten.fraeser().nummer == 2,
        "3D-Schlichten nicht mit der Kugel T2",
    )
    yield from h.warte_auf(
        lambda: all(b.vorschau is not None for b in panel.bloecke if b.aktiv()), 300000
    )
    for b in panel.bloecke:
        if b.aktiv():
            h.pruefe(b.ergebnis.text().startswith("→ "), f"{b.s.kennung}: {b.ergebnis.text()!r}")
            h.pruefe(not b.hinweis.text(), f"{b.s.kennung} rot: {b.hinweis.text()!r}")
    h.bild("1_alles_aus_der_aufspannung", panel.form)
    Gui.activeDocument().activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("2_geist_gefaerbt")

    job = panel.job
    panel.accept()  # Anlegen
    yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is None, 600000)
    namen = []
    for op in job.Operations.Group:
        saetze = len(op.Path.Commands) if getattr(op, "Path", None) else 0
        namen.append(op.Label)
        h.pruefe(saetze > 1000, f"{op.Label}: {saetze} Sätze")
    h.pruefe(namen == ["3D-Schruppen T1", "3D-Schlichten T2"], f"Operationen: {namen}")
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("3_angelegt")
