# „4-Achs-Bearbeitung“, Schritt Rohteil (W-003 Stufe V1): Eine Welle Ø 60 mit
# einem Nocken bis 36 mm von der Achse; ihre Stirnfläche angeklickt, der Befehl
# legt sie mittig vorne in eine Stange. Leer gilt der Vorschlag Ø 75; mit Ø 80
# bleiben 4,0 mm rundum. „Ganzes Teil“ braucht nur Ø 66. Mit A liegt die
# Stange in X, mit C in Z. Eine gewölbte Fläche wird abgelehnt. Abbrechen
# hinterlässt nichts; „Weiter“ und ohne „Rundum schruppen“ „Anlegen“ ist ein
# Schritt Rückgängig.
import os
import sys

import FreeCAD
import FreeCADGui as Gui
import Part
from PySide import QtGui

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _stirnflaeche(teil):
    """Die ebene Fläche mit Außennormale +Z ganz oben: die Stirnfläche der Welle."""
    from camaddon import vierachs_rohteil as vr

    beste = None
    for i, flaeche in enumerate(teil.Shape.Faces):
        if not vr.ist_eben(flaeche):
            continue
        normale = vr.aussennormale(flaeche)
        if (normale - FreeCAD.Vector(0, 0, 1)).Length < 1e-9:
            hoehe = flaeche.CenterOfMass.z
            if beste is None or hoehe > beste[0]:
                beste = (hoehe, f"Face{i + 1}")
    return beste[1]


def _gewoelbte_flaeche(teil):
    from camaddon import vierachs_rohteil as vr

    return next(f"Face{i + 1}" for i, f in enumerate(teil.Shape.Faces) if not vr.ist_eben(f))


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import PARAMETER_PFAD, gui_vierachs
    from camaddon import vierachs_rohteil as vr

    doc = FreeCAD.newDocument("Welle")
    doc.UndoMode = 1
    welle = Part.makeCylinder(30, 100).fuse(Part.makeCylinder(10, 30, FreeCAD.Vector(26, 0, 0)))
    teil = doc.addObject("Part::Feature", "Welle")
    teil.Shape = welle.removeSplitter()
    doc.recompute()
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    stirn = _stirnflaeche(teil)
    objekte_vorher = sorted(o.Name for o in doc.Objects)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, stirn)
    yield 500

    # Zuletzt benutzt: Planaufmaß 0 – grau steht „0“ da, nicht nichts (Manuel, 2026-09-30).
    parameter = FreeCAD.ParamGet(PARAMETER_PFAD)
    parameter.SetFloat("VaPlanaufmass", 0.0)
    Gui.runCommand("CamAddon_Vierachs")
    yield 1500
    panel = gui_vierachs.VierachsPanel.offen
    parameter.RemFloat("VaPlanaufmass")
    h.pruefe(panel is not None, "Fenster öffnet sich nicht")
    if panel is None:
        return
    grau = panel.felder_laenge["planaufmass"].placeholderText()
    h.pruefe(grau == "0", f"Planaufmaß 0 grau: {grau!r}")
    h.pruefe(panel.job is not None, "kein Job für die gewählte Fläche")
    if panel.job is None:
        return
    rohteil = panel.job.Stock
    h.pruefe(abs(rohteil.Radius.Value - 37.5) < 1e-6, f"Vorschlag: Radius {rohteil.Radius}")
    h.pruefe(stirn in panel.teil_text.text(), f"Teil-Zeile: {panel.teil_text.text()!r}")
    h.pruefe("60,0" in panel.teil_text.text(), f"runde Fläche Ø 60: {panel.teil_text.text()!r}")
    h.pruefe(
        panel.feld_stange.placeholderText() == "75",
        f"Vorschlag {panel.feld_stange.placeholderText()!r}",
    )
    h.pruefe("72,0" in panel.braucht_flaeche.text(), f"braucht: {panel.braucht_flaeche.text()!r}")
    h.pruefe("66,0" in panel.braucht_teil.text(), f"braucht: {panel.braucht_teil.text()!r}")
    h.pruefe(panel.knopf_mitte_flaeche.isChecked(), "runde Fläche nicht vorgewählt")
    h.pruefe(teil.ViewObject.Visibility is False, "Original noch sichtbar")
    h.pruefe(rohteil.ViewObject.Selectable is False, "Stange lässt sich anklicken")
    h.pruefe(
        panel.knopf_anlegen() is not None and panel.knopf_anlegen().isEnabled(),
        "„Weiter“ nicht bedienbar",
    )
    h.pruefe(panel.knopf_anlegen().text() == "Weiter", f"OK heißt {panel.knopf_anlegen().text()!r}")
    hilfe = panel.form.findChild(QtGui.QToolButton, "hilfe_vierachs")
    h.pruefe(hilfe is not None, "kein Knopf (?) zur Hilfe")

    # Rundachse C und Ø 80: 4,0 mm rundum, die Welle mittig in einer Stange längs Z.
    h.pruefe(panel.buchstabe() == "A", f"ab Werk Rundachse {panel.buchstabe()}")
    panel.waehle_rundachse("C")
    panel.feld_stange.setText("80")
    yield from h.warte_auf(lambda: abs(rohteil.Radius.Value - 40) < 1e-6, 3000)
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    h.pruefe(abs(rohteil.Radius.Value - 40) < 1e-6, f"Ø 80: Radius {rohteil.Radius}")
    h.pruefe("4,0" in panel.urteil.text(), f"Urteil: {panel.urteil.text()!r}")
    bb = rohteil.Shape.BoundBox
    h.pruefe(abs(bb.ZMax - 1) < 1e-6 and abs(bb.ZMin + 133) < 1e-6, f"Stange in Z: {bb}")
    klon = vr.modell(panel.job)
    kbb = klon.Shape.BoundBox
    h.pruefe(abs(kbb.ZMax) < 1e-6 and abs(kbb.ZMin + 100) < 1e-6, f"Welle in Z: {kbb}")
    h.pruefe("134" in panel.laenge_text.text(), f"Länge: {panel.laenge_text.text()!r}")
    Gui.SendMsgToActiveView("ViewFit")
    h.bild("1_fenster", panel.form)
    h.bild("2_stange_c")

    # Ganzes Teil möglichst mittig: die Mitte rückt, Ø 66 genügt.
    panel.knopf_mitte_teil.setChecked(True)
    yield 500
    h.pruefe(panel.mitte == vr.MITTE_TEIL, "Mitte nicht umgeschaltet")
    h.pruefe("7,0" in panel.urteil.text(), f"ganzes Teil: {panel.urteil.text()!r}")

    # Rundachse A: die Stange liegt in X.
    panel.waehle_rundachse("A")
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    bb = rohteil.Shape.BoundBox
    h.pruefe(abs(bb.XMax - 1) < 1e-6 and abs(bb.XMin + 133) < 1e-6, f"Stange bei A: {bb}")
    Gui.SendMsgToActiveView("ViewFit")
    h.bild("3_stange_a")

    # +90°: die Drehlage steht im Feld.
    panel.plus90()
    yield 500
    h.pruefe(panel.feld_drehlage.text() == "90", f"Drehlage: {panel.feld_drehlage.text()!r}")

    # Eine gewölbte Fläche geht nicht – ein Satz sagt warum, der Job bleibt.
    panel.waehle_flaeche(teil, _gewoelbte_flaeche(teil))
    yield 200
    h.pruefe("nicht eben" in panel.urteil.text(), f"gewölbt: {panel.urteil.text()!r}")
    h.pruefe(panel.job is not None and panel.flaeche == stirn, "Job nach gewölbter Fläche weg")

    # Abbrechen: nichts bleibt, das Original ist wieder zu sehen.
    panel.reject()
    yield 500
    h.pruefe(sorted(o.Name for o in doc.Objects) == objekte_vorher, "nach Abbrechen bleibt etwas")
    h.pruefe(teil.ViewObject.Visibility is True, "Original nach Abbrechen unsichtbar")

    # Noch einmal, Ø 80 und Rundachse C, „Anlegen“: ein Schritt Rückgängig.
    undo_vorher = len(doc.UndoNames)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, stirn)
    Gui.runCommand("CamAddon_Vierachs")
    yield 1500
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None, "Fenster öffnet sich kein zweites Mal")
    if panel is None:
        return
    h.pruefe(panel.buchstabe() == "A", "Abbrechen hat die Rundachse als Vorschlag gemerkt")
    panel.waehle_rundachse("C")
    panel.feld_stange.setText("80")
    yield 800
    # „Weiter“, dann ohne „Rundum schruppen“ „Anlegen“: nur Job und Stange.
    panel.accept()
    yield 300
    panel.mit_schruppen.setChecked(False)
    panel.accept()
    yield 800
    jobs = [o for o in doc.Objects if type(getattr(o, "Proxy", None)).__name__ == "ObjectJob"]
    h.pruefe(len(jobs) == 1, f"{len(jobs)} Jobs nach „Anlegen“")
    if jobs:
        h.pruefe(abs(jobs[0].Stock.Radius.Value - 40) < 1e-6, "Stange nach „Anlegen“ nicht Ø 80")
        h.pruefe(jobs[0].Stock.ViewObject.Selectable is True, "Stange bleibt unanklickbar")
        # 1.1.3 gibt den Namen des abgebrochenen Jobs nicht wieder frei: „… 4 Achsen001“.
        h.pruefe(jobs[0].Label.startswith("Welle – 4 Achsen"), f"Name des Jobs: {jobs[0].Label!r}")
    h.pruefe(len(doc.UndoNames) == undo_vorher + 1, f"Rückgängig-Schritte: {doc.UndoNames}")
    Gui.SendMsgToActiveView("ViewFit")
    h.bild("4_angelegt")
    doc.undo()
    yield 500
    h.pruefe(sorted(o.Name for o in doc.Objects) == objekte_vorher, "Strg+Z lässt etwas stehen")
