# Ein STL im 4-Achs-Assistenten (W-017, P-2026-10-11-100; Manuel, 2026-10-11: „so etwas … auf der
# 4-Achs aus einem Rundstahl rausfräsen, soweit es eben möglich ist“). Sein Geist
# (beispiele/geist_stl/Geist1_v2.stl, Glaschick, CC0): 68.242 Dreiecke, 80,8 × 50,9 × 82,7 mm,
# unten eben. Das Netz angeklickt, „4 Achsen“: Erst das Fenster „STL als Teil“ mit Dreiecken und
# Maßen; Maßstab 2 zeigt das Doppelte, „Auf diese Höhe“ mit 82,73 stellt ihn auf 1 zurück.
# „Umwandeln“: ein Körper „Geist1_v2 (Körper)“ aus genau den Dreiecken, das Netz ausgeblendet; der
# Assistent sagt, was geschah, und bittet um die Standfläche. Ein Dreieck der Standfläche
# angeklickt: Sie liegt am Futter, der Kopf vorne an der Stange („eben, am Futter (wird
# abgestochen)“). „Weiter“: „Plan indexiert“ und „Rundum entgraten“ sind aus, mit Grund (ein
# STL hat nur Dreiecke); „Rundum schruppen“ und „Rundum schlichten“ angehakt → „Anlegen“: beide
# Operationen mit Bahnen. Das Fenster steht dabei nie lange (pausen.txt).
import os

import FreeCAD
import FreeCADGui as Gui
import Mesh
from PySide import QtCore

V = FreeCAD.Vector
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

    from camaddon import gui_stl, gui_vierachs, stl_teil
    from camaddon import vierachs_operation as vo
    from camaddon import vierachs_rohteil as vr
    from camaddon import vierachs_schlichten as vs
    from camaddon import werkzeuge as wz

    t1 = wz.Werkzeug(nummer=1, durchmesser=8, schneiden=3, schneidenlaenge=30)
    t1.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=3.2, ap=2, vc=150, fz=0.05)]
    t2 = wz.Werkzeug(nummer=2, art=wz.KUGELFRAESER, durchmesser=4, schneiden=2,
                     schneidenlaenge=20)  # fmt: skip
    t2.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.2, ap=4, vc=150, fz=0.03)]
    wz.Bibliothek([t1, t2]).speichern()

    doc = FreeCAD.newDocument("Geist")
    doc.UndoMode = 1
    netz = doc.addObject("Mesh::Feature", "Geist1_v2")
    netz.Mesh = Mesh.Mesh(GEIST)
    doc.recompute()
    dreiecke = netz.Mesh.CountFacets
    h.pruefe(dreiecke == 68242, f"Dreiecke im Netz: {dreiecke}")
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(netz)
    yield 300

    # --- „STL als Teil“ --------------------------------------------------------------------
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_Vierachs"))  # modal
    yield from h.warte_auf(lambda: gui_stl.StlDialog.offen is not None, 5000)
    dialog = gui_stl.StlDialog.offen
    h.pruefe(dialog is not None, "Fenster „STL als Teil“ nicht offen")
    if dialog is None:
        return
    h.pruefe(dialog.windowTitle() == "STL als Teil", f"Titel: {dialog.windowTitle()!r}")
    h.pruefe(
        dialog.masse_text.text() == "Danach: 80,7 × 50,9 × 82,7 mm.",
        f"Maße: {dialog.masse_text.text()!r}",
    )
    dialog.feld_massstab.setValue(2.0)
    h.pruefe(dialog.masse_text.text().startswith("Danach: 161,5 ×"), dialog.masse_text.text())
    dialog.feld_hoehe.setValue(82.73)
    dialog._auf_hoehe()
    h.pruefe(
        abs(dialog.massstab() - 1.0) < 1e-4, f"Maßstab nach „Auf diese Höhe“: {dialog.massstab()}"
    )
    h.bild("1_stl_als_teil", dialog)
    dialog.accept()
    yield from h.warte_auf(lambda: gui_vierachs.VierachsPanel.offen is not None, 60000)
    panel = gui_vierachs.VierachsPanel.offen
    teil = next((o for o in doc.Objects if stl_teil.aus_stl(o)), None)
    h.pruefe(teil is not None and teil.Shape.ShapeType == "Solid", "kein Körper aus dem Netz")
    h.pruefe(panel is not None, "Assistent nicht offen")
    if panel is None or teil is None:
        return
    h.pruefe(teil.Label == "Geist1_v2 (Körper)", f"Name: {teil.Label!r}")
    h.pruefe(not netz.ViewObject.Visibility, "Netz noch sichtbar")
    anleitung = panel.anleitung.text()
    h.pruefe(
        anleitung.startswith("Körper aus 68\u202f242 Dreiecken.") and "Standfläche" in anleitung,
        f"Anleitung: {anleitung!r}",
    )
    h.pruefe(doc.UndoNames[:1] == ["STL als Teil"], f"Rückgängig: {doc.UndoNames[:2]}")
    h.bild("2_assistent_stl", panel.form)

    # --- Eine Achse des Teils statt einer Fläche: „X“ ----------------------------------------------
    h.pruefe(panel.teilachsen.isVisible(), "Knöpfe X, Y, Z nicht da")
    panel.knoepfe_teilachse["X"].click()
    yield from h.warte_auf(lambda: panel.job is not None, 30000)
    text = panel.teil_text.text()
    h.pruefe("Achse X (längs der Stange, Plus-Ende vorne)" in text, f"Teil mit Achse X: {text!r}")
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 5000)

    # --- Die Standfläche ans Futter -----------------------------------------------------------
    standflaeche = next(
        f"Face{i}"
        for i, f in enumerate(teil.Shape.Faces, 1)
        if abs(f.CenterOfMass.z) < 1e-6 and vr.aussennormale(f).z < -0.99
    )
    Gui.Selection.clearSelection()
    # Im Job liegt der Klon (das Original ist ausgeblendet): Seine Flächen heißen wie die des Teils.
    Gui.Selection.addSelection(doc.Name, vr.modell(panel.job).Name, standflaeche)
    yield from h.warte_auf(lambda: panel.flaeche == standflaeche, 30000)
    h.pruefe(panel.job is not None and panel.umgedreht, "kein Job oder Standfläche nicht am Futter")
    if panel.job is None:
        return
    text = panel.teil_text.text()
    h.pruefe("am Futter (wird abgestochen)" in text, f"Teil: {text!r}")
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 3000)
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 5000)
    job = panel.job
    klon = vr.modell(job)
    laengs = job.Stock.Placement.Rotation.multVec(V(0, 0, 1))
    a = [ecke.Point.dot(laengs) for ecke in klon.Shape.Vertexes]
    # Der Kopf vorne bei a = 0, die Standfläche 82,73 dahinter; die Stange (vorgeschlagen) um
    # das ganze Teil – es braucht Ø 80,75.
    h.pruefe(abs(max(a)) < 0.05 and abs(min(a) + 82.73) < 0.05, f"Klon längs {min(a)} … {max(a)}")
    h.pruefe(2 * job.Stock.Radius.Value > 81, f"Stange Ø {2 * job.Stock.Radius.Value}")
    e = vr.einstellung(job)
    h.pruefe(e is not None and e.umgedreht and e.flaeche == standflaeche, f"Einstellung: {e}")
    h.bild("3_standflaeche_am_futter")

    # --- Rundum schruppen und schlichten -------------------------------------------------------
    panel.accept()  # Weiter
    yield 300
    h.pruefe(panel.seite == 2, f"Seite {panel.seite}")
    h.pruefe(
        not panel.mit_plan.isEnabled()
        and panel.plan_grund.text().startswith("Ein Körper aus einem STL"),
        f"Plan indexiert: {panel.plan_grund.text()!r}",
    )
    h.pruefe(
        not panel.mit_entgraten.isEnabled()
        and panel.entgrat_grund.text().startswith("Ein Körper aus einem STL"),
        f"Entgraten: {panel.entgrat_grund.text()!r}",
    )
    panel.mit_schruppen.setChecked(True)
    panel.mit_schlichten.setChecked(True)
    # Solange gerechnet wird, dreht sich oben ein Zeichen (gui_rechnet, 2026-10-12).
    yield from h.warte_auf(lambda: panel._rechnet.zu_sehen, 5000)
    h.pruefe(panel._rechnet.zu_sehen, "kein Zeichen, dass gerechnet wird")
    h.pruefe(panel.rechnet.text().endswith("rechnet …"), f"Zeichen: {panel.rechnet.text()!r}")
    # Neben „Anlegen“ dreht sich ein Rad, „Anlegen“ oben und unten ist so lange grau.
    h.pruefe(not panel.rad_unten.isHidden(), "kein Rad neben „Anlegen“ unten")
    oben = panel.knopf_anlegen()
    h.pruefe(oben is not None and not oben.isEnabled(), "„Anlegen“ oben bedienbar beim Rechnen")
    h.pruefe(not panel.knopf_fertig.isEnabled(), "„Anlegen“ unten bedienbar beim Rechnen")
    h.bild("4a_rechnet", panel.form)
    h.bild("4b_rechnet_statusleiste")
    yield from h.warte_auf(
        lambda: panel.vorschau is not None and panel.vorschau_schlichten is not None, 240000
    )
    # Fertig, auch der Rest für die Kugel: das Zeichen ist weg.
    yield from h.warte_auf(lambda: not panel.rechnet_noch(), 240000)
    yield 400
    h.pruefe(not panel._rechnet.zu_sehen, "Zeichen bleibt nach dem Rechnen")
    h.pruefe(panel.rad_unten.isHidden(), "Rad dreht nach dem Rechnen weiter")
    h.pruefe(panel.knopf_fertig.isEnabled(), "„Anlegen“ bleibt nach dem Rechnen grau")
    h.pruefe(panel.vorschau is not None, "keine Vorschau Schruppen")
    h.pruefe(panel.vorschau_schlichten is not None, "keine Vorschau Schlichten")
    h.pruefe(not panel.hinweis_bearbeitung.text(), f"rot: {panel.hinweis_bearbeitung.text()!r}")
    h.bild("4_schruppen_schlichten", panel.form)
    panel.accept()  # Anlegen
    yield from h.warte_auf(lambda: gui_vierachs.VierachsPanel.offen is None, 240000)
    ops = [o for o in job.Operations.Group if vo.ist_rundum(o)]
    namen = [o.Label for o in ops]
    h.pruefe(namen == ["Rundum schruppen T1", "Rundum schlichten T2"], f"Operationen: {namen}")
    for op in ops:
        saetze = [b for b in op.Path.Commands if b.Name in ("G1", "G2", "G3")]
        h.pruefe(len(saetze) > 100, f"{op.Label}: {len(saetze)} Sätze")
    schlichten = next((o for o in ops if vs.ist_schlichten(o)), None)
    h.pruefe(schlichten is not None and schlichten.Umdrehungen > 10, "Schlichten ohne Umdrehungen")
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("5_angelegt")
