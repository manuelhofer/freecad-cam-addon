# SPDX-License-Identifier: LGPL-2.1-or-later
"""Den vollständigen Vergleich an einer kleinen Freiform durchklicken, mit Übernahme/Undo."""

import os
import pathlib
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
import Part


def schritte(h):
    profil = pathlib.Path(os.environ["FREECAD_USER_HOME"]).resolve()
    assert profil.is_dir() and pathlib.Path(App.getUserAppDataDir()).resolve() == profil
    yield 500
    erster = h.modal()
    if erster is not None:
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.accept()
    yield 500
    import Path.Main.Job as PathJob
    from Path.Tool.camassets import user_asset_store
    from PySide import QtGui

    from camaddon import gui_simultan_planung as gp
    from camaddon import halter as hl
    from camaddon import job_schnittwerte as js
    from camaddon import reichweite as rw
    from camaddon import schlichten3d as s3
    from camaddon import schruppen3d as r3
    from camaddon import uebergabe_werkzeuge as ue
    from camaddon import werkzeuge as wz

    # Bei sichtbarem Lauf den zweiten Bildschirm tatsächlich prüfen und benutzen.
    screens = QtGui.QApplication.screens()
    if len(screens) > 1:
        screen = next(
            (s for s in screens if s.name() == os.environ.get("CAMADDON_GROB_BILDSCHIRM")),
            next(s for s in screens if s != QtGui.QApplication.primaryScreen()),
        )
        g = screen.availableGeometry()
        mw = Gui.getMainWindow()
        mw.windowHandle().setScreen(screen)
        mw.setGeometry(g)
        mw.showMaximized()
        yield 500
        h.pruefe(g.contains(mw.frameGeometry().center()), "Fenster nicht auf zweitem Bildschirm")

    ordner = pathlib.Path(tempfile.mkdtemp())
    user_asset_store.set_dir(ordner / "assets")
    w = wz.standardwerkzeug()
    w.gesamtlaenge = 85
    holder = hl.aus_vorlage("er25")
    w.halter = holder.kennung
    kugel = wz.Werkzeug.aus_dict(w.als_dict())
    kugel.kennung = "gui_kugel4"
    kugel.nummer = 4
    kugel.name = "Kugel 4"
    kugel.art = wz.KUGELFRAESER
    kugel.durchmesser = 4
    kugel.eckradius = 2
    bib = wz.Bibliothek([w, kugel])
    bib.halter = [holder]
    bib.speichern()
    ue.uebergeben(bib)

    root = pathlib.Path(__file__).resolve().parents[2]
    Gui.activateWorkbench("PartWorkbench")
    md = App.openDocument(str(root / "beispiele/grob_g550_simultan/g550_winkelaufnahme.FCStd"))
    doc = App.newDocument("SimultanDialog")
    doc.UndoMode = 1
    obj = doc.addObject("Part::Feature", "Kuppel")
    kappe = Part.makeSphere(40, App.Vector(10, 8, -25)).common(
        Part.makeBox(20, 16, 20, App.Vector(0, 0, 6))
    )
    obj.Shape = Part.makeBox(20, 16, 6).fuse(kappe).removeSplitter()
    doc.recompute()
    job = PathJob.Create("Job", [obj])
    from Path.Main.Gui.Job import ViewProvider

    ViewProvider(job.ViewObject)
    alt = job.Stock
    stock = doc.addObject("Part::Feature", "Rohteil")
    stock.Shape = Part.makeBox(20, 16, 18)
    job.Stock = stock
    doc.removeObject(alt.Name)
    faces = [
        f"Face{i+1}" for i, f in enumerate(obj.Shape.Faces) if isinstance(f.Surface, Part.Sphere)
    ]
    t1 = js.controller_ohne_transaktion(doc, job, w, w.schnittwerte[wz.ALLE][1])
    t4 = js.controller_ohne_transaktion(doc, job, kugel, kugel.schnittwerte[wz.ALLE][2])
    grob = r3.lege_an(job, t1, 25, 1.5, aufmass=0.3, flaechen=faces, zwischen=1)
    grob.Rampenanlauf = True
    grob.Eintauchwinkel = 2.5
    op = s3.lege_an(job, t4, 0.02, flaechen=faces)
    rw.merke_maschine(job, md.FileName)
    doc.recompute()
    Gui.activateWorkbench("CAMWorkbench")
    App.setActiveDocument(doc.Name)
    job.ViewObject.show()
    job.Model.ViewObject.show()
    for modell in job.Model.Group:
        modell.ViewObject.show()
    obj.ViewObject.show()
    doc.recompute()
    Gui.updateGui()
    Gui.activeDocument().activeView().viewAxonometric()
    Gui.activeDocument().activeView().fitAll()
    job.Stock.ViewObject.hide()
    yield 500
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, op.Name)
    Gui.runCommand("CamAddon_SimultanPlanen")
    yield 500
    panel = gp.SimultanPanel.offen
    h.pruefe(panel is not None, "Vergleich öffnet nicht")
    if panel is None:
        return
    h.pruefe(not panel.uebernehmen.isEnabled(), "Ungeprüfte Übernahme möglich")
    obj.ViewObject.show()
    for modell in job.Model.Group:
        modell.ViewObject.show()
    view = Gui.getDocument(doc.Name).activeView()
    view.viewAxonometric()
    view.fitAll()
    Gui.updateGui()
    yield 500
    view.saveImage(os.path.join(os.environ["CAMADDON_AUSGABE"], "modell.png"), 640, 480, "Current")
    h.bild("1_vor_pruefung")
    # Änderung vor dem Rechnen gehört zum tatsächlichen Bedienweg.
    op.Grathoehe = 0.018
    doc.recompute()
    from camaddon import simultan_planung as sp

    h.pruefe(panel.mit_schruppen.isChecked(), "Gemeinsamer Vergleich nicht vorbelegt")
    panel.mit_schruppen.setChecked(False)
    h.pruefe(not panel.lagenbereich.isEnabled(), "Feste Vorbearbeitung lässt Bereich aktiv")
    panel.mit_schruppen.setChecked(True)
    panel.von.setValue(4)
    panel.bis.setValue(3)
    h.pruefe(not panel.start.isEnabled(), "Ungültiger Bereich lässt Rechnen zu")
    panel.von.setValue(2)
    h.pruefe(panel.start.isEnabled(), "Gültiger Bereich bleibt gesperrt")
    panel.lagenschritt.setValue(1)
    panel.start.click()
    yield from h.warte_auf(lambda: panel.laeufer is None and panel.start.isEnabled(), 600000)
    import json

    daten = [
        {
            "zwischenlagen": v.zwischenlagen,
            "richtung": v.richtung,
            "anstellung": v.anstellung,
            "grund": v.grund,
            "diameter": float(v.werkzeug.Tool.Diameter),
        }
        for v in (panel.plan.varianten if panel.plan else [])
    ]
    pathlib.Path(os.environ["CAMADDON_AUSGABE"], "varianten.json").write_text(
        json.dumps(daten, ensure_ascii=False, indent=2)
    )
    h.pruefe(panel.plan is not None and panel.plan.beste is not None, panel.status.text())
    if panel.plan is None or panel.plan.beste is None:
        h.bild("2_befund")
        panel.reject()
        return
    h.pruefe(
        panel.tabelle.topLevelItemCount() == len(panel.plan.varianten),
        "Nicht alle gemeinsamen Varianten angezeigt",
    )
    h.pruefe(
        {v.zwischenlagen for v in panel.plan.varianten} == {1, 2, 3},
        "Aktuelle Schruppwahl oder Suchbereich fehlt",
    )
    h.pruefe(panel.plan.vollstaendig, "Unvollständige Suche freigegeben")
    h.pruefe(panel.uebernehmen.isEnabled(), "Geprüfte Übernahme gesperrt")
    h.bild("2_geprueft")
    h.pruefe(sp._zustand(op) == panel.plan.zustand, "Prüfung verändert den Job")
    h.pruefe(
        sp._sicherheitszustand(panel.pruefung, panel.bibliothek) == panel.plan.sicherheitszustand,
        "Anzeigeänderungen sperren die geprüfte Übernahme",
    )
    panel.uebernehmen.click()
    yield 500
    h.pruefe(op.Anstellen and op.Randgang and float(op.BahnGrathoehe) > 0, "Übernahme fehlt")
    h.pruefe(
        abs(float(grob.Zwischenlagen) - panel.plan.beste.zwischenlagen) < 1e-9,
        "Schruppen nicht gemeinsam übernommen",
    )
    h.bild("3_uebernommen")
    doc.undo()
    doc.recompute()
    h.pruefe(
        not op.Anstellen
        and not op.Randgang
        and float(op.BahnGrathoehe) == 0
        and float(grob.Zwischenlagen) == 1,
        "Rückgängig unvollständig",
    )
    h.bild("4_rueckgaengig")
