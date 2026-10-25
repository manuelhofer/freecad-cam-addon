# Manuels Geist (beispiele/geist_stl/Geist1_v2.stl, ein STL) an der 5-Achs-Fräse Tisch/Tisch im
# Assistenten „Bearbeitung“ (W-017): „STL als Teil“, „Weiter“, „Alles aus dieser Aufspannung“ –
# von oben 3D-Schruppen und 3D-Schlichten, „Anlegen“; danach öffnet der Assistent die sieben
# geschwenkten Ebenen nacheinander, ihre Dreiecke gewählt. Jede Ebene rechnet mit dem, was von oben
# und in den Ebenen davor schon weg ist (raum_material.fuer_ebene): Bis 0.281.11 gab ein Eilgang,
# der im Raster 0,76 mm³ streifte, den Rest ab Ebene 2 auf, und jede schruppte das ganze Rohteil
# noch einmal – zusammen gut 2 h 50 min, jetzt 13 min. In einer Ebene, in der nichts mehr zu tun
# ist, geben die Blöcke den Haken ab, und der Knopf heißt „Nächste Ebene →“ (die letzte
# „Fertig“) – vorher blieb nur „Abbrechen“, das die Kette beendet.
import os
import tempfile

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
EBENEN = 7
SCHRUPPEN_EBENEN_MIN = 30.0  # Minuten höchstens, alle Ebenen zusammen (vorher gut 170)


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import PARAMETER_PFAD, beispielmaschine, gui_bearbeitung, gui_stl, sprache
    from camaddon import halter as hl
    from camaddon import maschinenspeicher as msp
    from camaddon import reichweite as rw
    from camaddon import werkzeuge as wz

    ordner = tempfile.mkdtemp()
    asm, _maschine = beispielmaschine.lade(beispielmaschine.TISCH_TISCH)
    pfad = os.path.join(ordner, "fuenfachs.FCStd")
    asm.Document.saveAs(pfad)
    msp.merken_datei(pfad)
    FreeCAD.ParamGet(PARAMETER_PFAD).SetString(rw.ZULETZT_MASCHINE, pfad)
    t1 = wz.standardwerkzeug()
    t2 = wz.Werkzeug(nummer=2, art=wz.KUGELFRAESER, durchmesser=6, schneiden=2,
                     schneidenlaenge=20, gesamtlaenge=70.0)  # fmt: skip
    t2.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=6, vc=150, fz=0.04)]
    bibliothek = wz.Bibliothek([t1, t2])
    halter = hl.aus_vorlage("schrumpf_6_lang")
    halter.kennung = "halter-schrumpf-6-lang"
    bibliothek.halter.append(halter)
    t2.halter = halter.kennung
    t2.laenge_spindelnase = float(halter.laenge) + 35.0
    bibliothek.speichern()
    yield 300

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
    yield from h.warte_auf(
        lambda: all(b.vorschau is not None for b in panel.bloecke if b.aktiv()), 600000
    )
    aktiv = sorted(b.s.kennung for b in panel.bloecke if b.aktiv())
    h.pruefe(aktiv == ["schlichten3d", "schruppen3d"], f"von oben angehakt: {aktiv}")
    h.bild("1_von_oben", panel.form)
    panel.accept()  # Anlegen – danach die erste Ebene
    yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not panel, 600000)

    schruppen = 0.0  # Minuten in den Ebenen
    for nummer in range(1, EBENEN + 1):
        yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not None, 60000)
        ebene = gui_bearbeitung.BearbeitungPanel.offen
        h.pruefe(ebene is not None, f"Ebene {nummer} von {EBENEN} öffnet sich nicht")
        if ebene is None:
            return
        yield 1000
        ebene.knopf_weiter.click()
        yield 500
        yield from h.warte_auf(
            lambda e=ebene: all(b.vorschau is not None for b in e.bloecke if b.aktiv()), 600000
        )
        yield 500
        for block in ebene.aktive_bloecke():
            h.pruefe(not block.hinweis.text(), f"Ebene {nummer}, {block.s.kennung} rot: "
                     f"{block.hinweis.text()!r}")  # fmt: skip
            if block.s.kennung == "schruppen3d" and block.zeit is not None:
                schruppen += float(block.zeit)
        if not ebene.aktive_bloecke():
            # Nichts mehr zu tun: weiter zur nächsten (die letzte: „Fertig“).
            soll = "ba.folge.naechste" if nummer < EBENEN else "ba.folge.fertig"
            knopf = ebene.knopf_fertig
            h.pruefe(
                knopf is not None and knopf.isEnabled() and knopf.text() == sprache.tr(soll),
                f"Ebene {nummer} ohne Haken: Knopf {knopf.text() if knopf else None!r}",
            )
        # Kein Rat „Dafür anhaken: …“ für einen Block, der eben „nichts zu tun“ fand.
        unfertig = ebene.unfertig.text() if not ebene.unfertig.isHidden() else ""
        for block in ebene.bloecke:
            h.pruefe(
                not (block.schon_weg and f"„{block.s.titel()}“" in unfertig),
                f"Ebene {nummer}: {unfertig!r}",
            )
        h.bild(f"2_ebene{nummer}", ebene.form)
        ebene.accept()
        yield from h.warte_auf(
            lambda e=ebene: gui_bearbeitung.BearbeitungPanel.offen is not e, 600000
        )
        h.pruefe(
            gui_bearbeitung.BearbeitungPanel.offen is not ebene,
            f"Ebene {nummer}: „Anlegen“ ging nicht",
        )
        if gui_bearbeitung.BearbeitungPanel.offen is ebene:
            return
    yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is None, 60000)
    h.pruefe(
        gui_bearbeitung.BearbeitungPanel.offen is None, "nach der letzten Ebene noch ein Fenster"
    )
    h.pruefe(
        schruppen <= SCHRUPPEN_EBENEN_MIN,
        f"3D-Schruppen in den Ebenen zusammen {schruppen:.0f} min (höchstens {SCHRUPPEN_EBENEN_MIN:.0f})",
    )
    jobs = [
        o for o in doc.Objects if o.TypeId == "Path::FeaturePython" and hasattr(o, "Operations")
    ]
    h.pruefe(len(jobs) == EBENEN + 1, f"{len(jobs)} Jobs")
    mit_bahn = [j for j in jobs if any(len(op.Path.Commands) > 100 for op in j.Operations.Group)]
    h.pruefe(len(mit_bahn) >= 4, f"Jobs mit Bahn: {[j.Label for j in mit_bahn]}")
    print(f"3D-Schruppen in den Ebenen: {schruppen:.1f} min")
    Gui.Selection.clearSelection()
    Gui.activeDocument().activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("3_angelegt")
