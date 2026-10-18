# Manuels Ring von vorn (W-033; Manuel, 2026-10-18, zum Ring aus drei Segmenten mit Schlitzen und
# Bohrung: „das bearbeitet man doch von vorne ;)“): der Grund einer Ringnut auf der Stirn
# angeklickt, „4-Achs-Bearbeitung“ auf der Beispiel-Drehmaschine. Rot steht, dass die Fläche
# längs der Achse schaut und in „Bearbeitung“ von vorn gehört; der Verweis öffnet „Bearbeitung“
# auf dem Stangen-Job. Die Kiste hat T1 (Ø 4, radial) und T2 (Ø 10 im axialen Halter): Von vorn
# fräst nur T2. „Alles aus dieser Aufspannung“ – Räumen über alles bis durch (außen herum, die
# Schlitze, die Bohrung), die Nuten auf der Stirn, Messstopp, Wände schlichten; kein Zickzack
# beim Einfahren (Spezifikation Strategien, Abschnitt 5).
# ZEITLIMIT: 900
import contextlib
import os
import shutil
import tempfile

import FreeCAD
import FreeCADGui as Gui

ADDON = "/home/manuel/Projekte/freecad_verbesserrungen/freecad-cam-addon"


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine, gui_bearbeitung, gui_vierachs
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    bibliothek = wz.Bibliothek()
    halter = bibliothek.neuer_halter("vdi30_radial")
    t1 = bibliothek.neues_werkzeug()
    t1.nummer, t1.name, t1.durchmesser, t1.schneiden = 1, "VHM 4", 4.0, 3
    t1.schneidenlaenge, t1.laenge_spindelnase, t1.halter = 12.0, 110.0, halter.kennung
    t1.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=1.0, ap=3, vc=120, fz=0.03)]
    axial = bibliothek.neuer_halter("vdi30_axial")
    t2 = bibliothek.neues_werkzeug()
    t2.nummer, t2.name, t2.durchmesser, t2.schneiden = 2, "VHM 10", 10.0, 3
    t2.schneidenlaenge, t2.laenge_spindelnase, t2.halter = 22.0, 110.0, axial.kennung
    t2.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=2.5, ap=10, vc=150, fz=0.05)]
    bibliothek.speichern()

    asm, _maschine = beispielmaschine.lade(beispielmaschine.DREHMASCHINE)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    yield 300

    ordner = tempfile.mkdtemp()
    datei = os.path.join(ordner, "ring.FCStd")
    shutil.copy(os.path.join(ADDON, "beispiele", "ring_4achs_planbearbeitung.FCStd"), datei)
    doc = FreeCAD.openDocument(datei)
    teil = doc.getObject("Body")
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    # Der Grund einer Ringnut auf der Stirn: eben, nach vorn, zwischen den Stirnflächen (z 5)
    nutgrund = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if vr.ist_eben(f)
        and (vr.aussennormale(f) - FreeCAD.Vector(0, 0, 1)).Length < 1e-9
        and 0.05 < f.BoundBox.ZMin < 7.95
    )
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, nutgrund)
    yield 500

    Gui.runCommand("CamAddon_Vierachs")
    yield 1500
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 3000)
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    panel.knopf_weiter.click()
    yield 300
    h.pruefe(panel.seite == 2, f"Seite {panel.seite}")
    if panel.mit_schlichten.isChecked():
        panel.mit_schlichten.setChecked(False)
    panel.flaeche_umschalten(nutgrund)  # wie ein Klick im 3D: nur diese Fläche
    yield 500
    h.pruefe(panel.gewaehlte == [nutgrund], f"gewählt: {panel.gewaehlte} statt {nutgrund}")
    yield from h.warte_auf(lambda: not panel.rechnet_noch(), 180000)
    yield 800
    rot = panel.hinweis_bearbeitung.text()
    h.pruefe(
        nutgrund in rot and "Stirnseite" in rot and 'href="bearbeitung:' in rot,
        f"rot: {rot!r}",
    )
    h.pruefe(not panel.knopf_fertig.isEnabled(), "„Anlegen“ frei trotz Stirnfläche")
    h.bild("1_stirnseite", panel.form)
    job_name = panel.job.Name
    panel.hinweis_bearbeitung.linkActivated.emit(f"bearbeitung:{nutgrund}")
    yield from h.warte_auf(
        lambda: getattr(gui_bearbeitung.BearbeitungPanel.offen, "job", None) is not None, 20000
    )
    yield 1000
    h.pruefe(gui_vierachs.VierachsPanel.offen is None, "4-Achs-Assistent noch offen")
    stange_job = doc.getObject(job_name)
    h.pruefe(stange_job is not None, "der 4-Achs-Job (die Stange) ist weg")
    dialog = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(
        dialog is not None and dialog.gewaehlte == [nutgrund],
        f"„Bearbeitung“ gewählt: {getattr(dialog, 'gewaehlte', None)}",
    )
    if dialog is None:
        return
    h.pruefe(dialog.job is stange_job, "„Bearbeitung“ nicht auf dem Stangen-Job")
    if dialog.maschine() is not None:  # die Beispiel-Drehmaschine ist nicht gespeichert
        h.pruefe(
            "Von vorn an der Stange" in dialog.maschine_hinweis.text(),
            f"Maschinenzeile: {dialog.maschine_hinweis.text()!r}",
        )
    # Alle Wände, die bis an die Unterkante des Teils gehen: von vorn bis durch räumen.
    z0 = teil.Shape.BoundBox.ZMin
    waende = []
    for i_, f in enumerate(teil.Shape.Faces):
        if abs(f.BoundBox.ZMin - z0) > 1e-6 or f.BoundBox.ZLength < 1e-6:
            continue
        if vr.ist_eben(f) and abs(vr.aussennormale(f).z) > 1e-6:
            continue
        waende.append(f"Face{i_ + 1}")
    print(ascii(f"Wände bis unten: {waende}"))
    dialog.aus_der_aufspannung()
    yield 1500
    print(ascii(f"aus der Aufspannung: {dialog.gewaehlte}"))
    if dialog.knopf_weiter.isEnabled() and dialog.knopf_weiter.isVisible():
        dialog.knopf_weiter.click()
        yield 500
    yield from h.warte_auf(lambda: not dialog.vorschau_laeuft(), 300000)
    yield 1500
    yield from h.warte_auf(lambda: not dialog.vorschau_laeuft(), 300000)
    aus = os.environ.get("CAMADDON_AUSGABE") or tempfile.mkdtemp()
    if dialog.bohrung.aktiv():
        dialog.bohrung.haken.setChecked(False)
        yield 500
        yield from h.warte_auf(lambda: not dialog.vorschau_laeuft(), 300000)
        yield 1000
    for b in dialog.bloecke:
        if b.aktiv():
            print(ascii(f"{b.s.kennung}: {b.ergebnis.text()[:200]}"))
    h.bild("2_bearbeitung", dialog.form)
    if dialog.knopf_weiter.isEnabled() and dialog.knopf_weiter.isVisible():
        dialog.knopf_weiter.click()
        yield 800
    vorher = len(stange_job.Operations.Group)
    if dialog.accept() is not True:
        h.pruefe(False, f"„Anlegen“ ging nicht: {dialog.hinweis.text()!r}")
    yield 3000
    neue = list(stange_job.Operations.Group)[vorher:]
    namen = [o.Label for o in neue]
    print(ascii(f"Operationen: {namen}"))
    h.pruefe(
        namen == ["Räumen T2", "Nut T2", "Messstopp", "Wände schlichten T2"],
        f"Operationen: {namen}",
    )
    from camaddon import pruefstand as ps

    for o in neue:
        gezaehlt = ps.kehren_im_programm(o.Path.Commands) if getattr(o, "Path", None) else None
        h.pruefe(not gezaehlt or gezaehlt[0] == 0, f"{o.Label}: Zickzack {gezaehlt}")
    from PySide import QtGui

    for o in doc.Objects:
        vo_ = getattr(o, "ViewObject", None)
        if vo_ is None:
            continue
        with contextlib.suppress(Exception):
            vo_.Visibility = o in neue or o in stange_job.Model.Group
    for fenster in Gui.getMainWindow().findChildren(QtGui.QMdiSubWindow):
        if fenster.windowTitle().startswith("ring"):
            Gui.getMainWindow().findChild(QtGui.QMdiArea).setActiveSubWindow(fenster)
    yield 600
    rv = Gui.getDocument(doc.Name).activeView()
    rv.setCameraOrientation(FreeCAD.Rotation(FreeCAD.Vector(0.75, 0.25, 0.6), 75).Q)
    yield 200
    Gui.SendMsgToActiveView("ViewFit")
    yield 600
    rv.saveImage(os.path.join(aus, "ring_vorn_3d.png"), 1600, 1100, "White")
    rv.viewTop()
    yield 200
    Gui.SendMsgToActiveView("ViewFit")
    yield 600
    rv.saveImage(os.path.join(aus, "ring_vorn_oben.png"), 1600, 1100, "White")
    with open(os.path.join(aus, "wettbewerb.txt"), "a") as d:
        for o in neue:
            n = len(o.Path.Commands) if hasattr(o, "Path") else 0
            d.write(f"OP {o.Label}: {n} Sätze\n")
