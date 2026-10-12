# Ein STL aus einer N-Eck-Stange im Schraubstock (W-018, P-2026-10-12-122): Manuels Geist
# (beispiele/geist_stl/Geist1_v2.stl) ohne Maschine (3 Achsen). Das Netz angeklickt, „Bearbeitung“:
# im Fenster „STL als Teil“ „Aus einer N-Eck-Stange im Schraubstock“ angehakt (8 Flächen, Achse Z,
# 20 mm im Schraubstock), „Umwandeln“ → der Grundjob „… – Aufspannung 1 von 8“ in der
# 8-Eck-Stange, dazu die Aufspannungen 2 … 8 als eigene Jobs. Der Assistent sagt, wie man einrichtet;
# „Alles aus dieser Aufspannung“, „Anlegen“ – und die zweite Aufspannung öffnet sich, ihre
# Vorschau rechnet mit dem Restmaterial der ersten. Dort „Abbrechen“: Die Kette hört auf.
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
    from camaddon import n_eck as ne
    from camaddon import schwenken as sw
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
    dialog = gui_stl.StlDialog.offen
    h.pruefe(dialog is not None and dialog.n_eck is not None, "keine Wahl der N-Eck-Stange")
    if dialog is None or dialog.n_eck is None:
        return
    h.pruefe(not dialog.n_eck.isChecked(), "N-Eck-Stange schon gewählt")
    dialog.n_eck.setChecked(True)
    h.pruefe(dialog.feld_n.value() == 8 and dialog.feld_achse.currentData() == "Z", "Vorgaben")
    yield 300
    h.bild("1_stl_als_teil_n_eck", dialog)
    dialog.accept()
    yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not None, 180000)
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    grund = panel.job
    aufspannungen = sw.aufspannungen_von(grund)
    h.pruefe(len(aufspannungen) == 7, f"Aufspannungen: {len(aufspannungen)}")
    h.pruefe(grund.Label.endswith("Aufspannung 1 von 8"), f"Grundjob: {grund.Label}")
    h.pruefe(
        (panel._folge or "").startswith("Aufspannung 1 von 8: Stange um 0° gegen die erste"),
        f"Satz: {panel._folge!r}",
    )
    stange = grund.Stock.Shape.BoundBox
    h.pruefe(abs(stange.XMin) < 1e-6 and stange.XLength > 100, f"Stange: {stange}")
    yield 1000
    panel.knopf_weiter.click()
    yield 500
    panel.aus_der_aufspannung()
    yield 500
    aktiv = sorted(b.s.kennung for b in panel.bloecke if b.aktiv())
    h.pruefe(aktiv == ["schlichten3d", "schruppen3d"], f"angehakt: {aktiv}")
    yield from h.warte_auf(
        lambda: all(b.vorschau is not None for b in panel.bloecke if b.aktiv()), 300000
    )
    erste = {b.s.kennung: b.ergebnis.text() for b in panel.bloecke if b.aktiv()}
    # In der Stange schruppt es in Zeilen von der Stirn zum Schraubstock, nicht in Ringen.
    h.pruefe("Zeilen" in erste.get("schruppen3d", ""), f"Schruppen: {erste}")
    h.bild("2_aufspannung_1", panel.form)
    Gui.activeDocument().activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 300
    h.bild("3_stange_aufspannung_1")
    panel.accept()  # Anlegen – danach die zweite Aufspannung
    yield from h.warte_auf(
        lambda: gui_bearbeitung.BearbeitungPanel.offen not in (None, panel), 600000
    )
    zweite = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(zweite is not None and zweite is not panel, "zweite Aufspannung nicht offen")
    if zweite is None or zweite is panel:
        return
    h.pruefe(zweite.job is aufspannungen[0], f"Job: {zweite.job and zweite.job.Label}")
    h.pruefe(
        (zweite._folge or "").startswith("Aufspannung 2 von 8: Stange um 45° gegen die erste"),
        f"Satz: {zweite._folge!r}",
    )
    yield 1000
    zweite.knopf_weiter.click()
    yield 500
    zweite.aus_der_aufspannung()
    yield from h.warte_auf(
        lambda: all(b.vorschau is not None for b in zweite.bloecke if b.aktiv()), 300000
    )
    dann = {b.s.kennung: b.ergebnis.text() for b in zweite.bloecke if b.aktiv()}
    gruende = set(zweite._zugang.unerreichbar.values()) if zweite._zugang else set()
    h.pruefe(
        "Kommt in einer anderen Aufspannung der Stange dran." in gruende
        and not any("schwenkt" in g or "Spannmittel" in g for g in gruende),
        f"Gründe: {gruende}",
    )
    h.pruefe("schruppen3d" in dann, f"zweite: {dann}")
    with open(os.path.join(os.environ["CAMADDON_AUSGABE"], "ergebnis_texte.txt"), "w") as datei:
        datei.write(f"erste: {erste}\nzweite: {dann}\n")
    h.bild("4_aufspannung_2", zweite.form)
    Gui.SendMsgToActiveView("ViewFit")
    yield 300
    h.bild("5_stange_aufspannung_2")
    zweite.reject()  # Abbrechen: Die Kette hört auf, die Aufspannungen bleiben
    yield 1500
    h.pruefe(gui_bearbeitung.BearbeitungPanel.offen is None, "nach Abbrechen noch ein Fenster")
    h.pruefe(len(sw.aufspannungen_von(grund)) == 7, "Aufspannungen weg")
    h.pruefe(ne.ist_n_eck(grund), "Grundjob nicht als N-Eck")
