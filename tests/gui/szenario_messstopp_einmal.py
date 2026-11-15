# „Weiter bearbeiten“ beim Schlichten einer Nut ohne zwei Schnitte, mit „Messstopp davor“: genau ein
# Messstopp. Beobachtet in 0.381.0 (nicht nachgeprüft): „Schlichten danach“ hakt nach einer Nut von
# sich aus seinen eigenen Messstopp an – zwei Halte hintereinander. Ein Block 80 × 60 × 20 mit einer
# geschlossenen Nut 30 × 16, 8 tief, T1 der Standardfräser Ø 12; angelegt bis zum Schruppen: die Nut
# mit 0,3 Aufmaß (wie in szenario_zwei_schnitte_nut). Job anklicken, „Weiter bearbeiten (Beta)“:
# „In zwei gleichen Schnitten“ aus, „Messstopp davor“ an. Im Fenster: „Schlichten danach“ angehakt,
# sein eigener Messstopp nicht. „Anlegen“: ein Messstopp (er misst die Nut 15,4 quer in Y), dann der
# Wandzug – kein zweiter.
# Zweiter Fall (Zweifler 2026-11-15): In „Womit weiter?“ das Schruppen gewählt (Aufmaß 0,2): Die Nut
# wird neu geschruppt, „Messstopp davor“ steht davor – zwischen Schruppen und Schlichten der Nut
# bleibt der eigene Messstopp von „Schlichten danach“ (Manuel, 2026-10-17: schruppen, messen,
# schlichten). Erwartet: Messstopp, Nut, Messstopp, Wandzug.
# ZEITLIMIT: 900

import FreeCAD
import FreeCADGui as Gui
import Part

V = FreeCAD.Vector
NUT_Y, NUT_B = 30.0, 16.0


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500
    yield from _fall(h, "Nut", schruppen=False)
    yield from _fall(h, "NutSchruppen", schruppen=True)


def _fall(h, name, schruppen):
    import Path.Main.Job as PathJob
    from PySide import QtCore

    from camaddon import gui_bearbeitung_beta as beta
    from camaddon import job_schnittwerte as js
    from camaddon import messen
    from camaddon import messstopp as ms
    from camaddon import nut as nu
    from camaddon import uebergabe_werkzeuge as ue
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    beta.beta_setzen(True)
    fraeser = wz.standardwerkzeug()
    wz.Bibliothek([fraeser]).speichern()
    ue.uebergeben(wz.Bibliothek([fraeser]))  # das ToolBit für den Controller der Nut
    doc = FreeCAD.newDocument(name)
    teil = doc.addObject("Part::Feature", "Block")
    nut_form = (
        Part.makeBox(14, NUT_B, 8, V(51, NUT_Y - NUT_B / 2, 12))
        .fuse(Part.makeCylinder(NUT_B / 2, 8, V(51, NUT_Y, 12)))
        .fuse(Part.makeCylinder(NUT_B / 2, 8, V(65, NUT_Y, 12)))
    )
    teil.Shape = Part.makeBox(80, 60, 20).cut(nut_form).removeSplitter()
    doc.recompute()
    Gui.activateWorkbench("CAMWorkbench")
    yield 500
    job = PathJob.Create("Job", [teil])
    job.Stock.ExtZpos = 0.0
    doc.recompute()
    form = vr.modell(job).Shape
    grund = next(
        f"Face{i + 1}"
        for i, f in enumerate(form.Faces)
        if f.Surface.__class__.__name__ == "Plane"
        and abs(f.BoundBox.ZMax - 12.0) < 1e-6
        and abs(f.BoundBox.ZMin - 12.0) < 1e-6
    )
    # Das Schruppen, wie der Assistent es anlegt: die Nut mit 0,3 an den Wänden.
    einsatz = next(e for e in fraeser.einsaetze(wz.ALLE) if e.art == wz.SCHRUPPEN)
    tc = js.controller_ohne_transaktion(doc, job, fraeser, einsatz)
    nu.lege_an(job, tc, 4.0, 1.5, aufmass=0.3, schlichten=False, flaechen=[grund])
    job.addProperty("App::PropertyStringList", beta.EIGENSCHAFT_FLAECHEN, beta.GRUPPE, "")
    job.addProperty("App::PropertyInteger", beta.EIGENSCHAFT_ABSCHNITT, beta.GRUPPE, "")
    from camaddon import gui_programm as gp

    job.addProperty("App::PropertyString", gp.EIGENSCHAFT_STEUERUNG, "CAM-Addon", "")
    setattr(job, gp.EIGENSCHAFT_STEUERUNG, "siemens")
    setattr(job, beta.EIGENSCHAFT_FLAECHEN, [grund])
    setattr(job, beta.EIGENSCHAFT_ABSCHNITT, beta.SCHRUPPEN)
    doc.recompute()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400

    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_WeiterBearbeitenBeta"))
    yield from h.warte_auf(lambda: beta.WeiterFrage.offen is not None, 10000)
    frage = beta.WeiterFrage.offen
    h.pruefe(frage is not None, "keine Frage „Womit weiter?“")
    if frage is None:
        return
    h.pruefe(frage.abschnitt() == beta.SCHLICHTEN, f"vorgewählt: {frage.abschnitt()}")
    if schruppen:  # noch einmal schruppen
        frage.wahl[beta.SCHRUPPEN].click()
        yield 300
        frage.aufmass.setText("0,2")
        yield 300
        h.pruefe(frage.abschnitt() == beta.SCHRUPPEN, f"gewählt: {frage.abschnitt()}")
    if frage.zwei.isChecked():
        frage.zwei.click()  # von Hand aus (setChecked allein nähme die Vorgabe wieder)
    h.pruefe(not frage.zwei_wert(), "„In zwei gleichen Schnitten“ noch an")
    frage.messstopp.setChecked(True)
    yield 300
    print(ascii(f"Messen: {frage.messen_text.text()} / {frage.messstopp.text()}"), flush=True)
    h.bild(f"1_womit_weiter_{name}", frage)
    frage.accept()
    yield from h.warte_auf(lambda: beta.BearbeitungPanel.offen is not None, 60000)
    panel = beta.BearbeitungPanel.offen
    yield from h.warte_auf(lambda: panel is not None and not panel.vorschau_laeuft(), 300000)
    yield 1000
    if panel is None:
        h.pruefe(False, "„Weiter bearbeiten“ öffnet kein Fenster")
        return
    if schruppen:  # vom Schritt „Schruppen“ zum Schlichten
        h.bild(f"2a_schruppen_{name}", panel.form)
        panel.weiter()
        yield 2000
        yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 300000)
        yield 1000
    aktiv = [b.s.kennung for b in panel.aktive_bloecke()]
    eigener = panel.schlichten_danach.haken_felder["messstopp"].isChecked()
    print("EINMAL angehakt", aktiv, "eigener Messstopp", eigener, flush=True)
    h.pruefe("schlichtendanach" in aktiv, f"„Schlichten danach“ nicht angehakt: {aktiv}")
    h.pruefe(
        eigener == schruppen,
        f"„Schlichten danach“ eigener Messstopp {eigener} (neu geschruppt: {schruppen})",
    )
    h.bild(f"2_schlichten_{name}", panel.form)
    vorher = len(job.Operations.Group)
    panel.accept(bis_hier=True)
    yield from h.warte_auf(
        lambda: beta.BearbeitungPanel.offen is not panel or panel.geschlossen, 120000
    )
    yield 3000
    dazu = list(job.Operations.Group)[vorher:]
    arten = ["stopp" if ms.ist_messstopp(o) else "schnitt" for o in dazu]
    print("EINMAL dazu", [o.Label for o in dazu], arten, flush=True)
    soll = ["stopp", "schnitt", "stopp", "schnitt"] if schruppen else ["stopp", "schnitt"]
    h.pruefe(arten == soll, f"Folge: {arten}")
    stopp = next((o for o in dazu if ms.ist_messstopp(o)), None)
    m = ms.merkmal_von(list(stopp.Gcode)) if stopp is not None else None
    print(ascii(f"EINMAL Messstopp: {m}"), flush=True)
    h.pruefe(
        m is not None
        and m[0].art == messen.NUT
        and abs(m[0].breite - (NUT_B - 0.6)) < 1e-6
        and m[0].achse == "Y",
        f"Messstopp misst: {m}",
    )
    Gui.Selection.clearSelection()
    if stopp is not None:
        Gui.Selection.addSelection(stopp)
    yield 500
    h.bild(f"3_job_{name}", None)
    with __import__("contextlib").suppress(Exception):
        Gui.Control.closeDialog()
    yield 500
