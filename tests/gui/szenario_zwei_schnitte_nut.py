# „Weiter bearbeiten“ beim Schlichten einer Nut: zwei gleiche Schnitte mit Messen der Breite
# dazwischen und Leerfahrten (Manuel, 2026-11-14: „erstes vorschlichten ... und danach nochmal erstes
# vorschlichten .... dann messsen ... dann vertigschlichten ... und dann nochmal vertig schlichten“).
# Ein Block 80 × 60 × 20 mit einer geschlossenen Nut 30 × 16, 8 tief (Mittellinie in X, y 30), T1
# der Standardfräser Ø 12; am Job gemerkt ihr Grund, angelegt bis zum Schruppen: die Nut mit 0,3
# Aufmaß, ohne „Wand schlichten“ (so legt der Assistent sie an – die Wände macht „Schlichten danach“).
# Job anklicken, „Weiter bearbeiten (Beta)“: vorgewählt „Schlichten“ (keine Löcher), „In zwei
# gleichen Schnitten“ angehakt („erst 0,15, dann 0“), der Messstopp steht zwischen den Schnitten und
# misst die Nut 15,7 quer in Y; „Leerfahrt nach jedem Schnitt“ dazu. „Anlegen“: der Wandzug mit
# Rest 0,15, Leerfahrt, Messstopp (Nut 15,7), der Wandzug auf Maß, Leerfahrt – ohne den Messstopp,
# den „Schlichten danach“ nach einer Nut sonst von sich aus davor setzt. Die Steuerung am Job ist
# Siemens: Mit der Nummer des Tasters misst CYCLE977 die Nut, ohne hält die Maschine.
# ZEITLIMIT: 600

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

    import Path.Main.Job as PathJob
    from PySide import QtCore, QtGui

    from camaddon import gui_bearbeitung_beta as beta
    from camaddon import job_schnittwerte as js
    from camaddon import leerfahrt as lf
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
    doc = FreeCAD.newDocument("Nut")
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
    schruppen = next(e for e in fraeser.einsaetze(wz.ALLE) if e.art == wz.SCHRUPPEN)
    tc = js.controller_ohne_transaktion(doc, job, fraeser, schruppen)
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
    h.pruefe(frage.zwei.isVisible() and frage.zwei.isChecked(), "„zwei Schnitte“ nicht an")
    h.pruefe("0,15" in frage.zwei_text.text(), f"erst/dann: {frage.zwei_text.text()!r}")
    h.pruefe("zwischen" in frage.messstopp.text(), f"Messstopp: {frage.messstopp.text()!r}")
    frage.leerfahrt.setChecked(True)
    frage.messstopp.setChecked(True)
    yield 300
    satz = frage.messen_text.text()
    print(ascii(f"Messen: {satz} / {frage.messstopp.text()}"), flush=True)
    h.pruefe("Nut" in satz and "15,7" in satz and "Y" in satz, f"Messen: {satz!r}")
    # Beim Öffnen ganz zu sehen: der Satz unter dem Messstopp über den Knöpfen (showEvent).
    unten = frage.messen_text.geometry().bottom()
    knoepfe = min(k.geometry().top() for k in frage.findChildren(QtGui.QDialogButtonBox))
    h.pruefe(unten <= knoepfe, f"Satz verdeckt: unten {unten}, Knöpfe ab {knoepfe}")
    h.bild("1_womit_weiter_nut", frage)
    # Mit dem Taster: der Satz sagt, dass er die Nut misst (Siemens CYCLE977 „Nut“).
    frage.taster.setText("99")
    yield 200
    satz_t = frage.messen_text.text()
    print(ascii(f"Messen mit Taster: {satz_t}"), flush=True)
    h.pruefe(frage._zyklus, "Siemens: kein Messzyklus für die Nut")
    h.pruefe("T99" in satz_t and "Nut" in satz_t, f"mit Taster: {satz_t!r}")
    # Nur messen: Die Wände der Nut schlichtet eine Nut „nur schlichten“ ohne Radiuskorrektur.
    h.pruefe(
        not frage.korrigieren.isVisible() and not frage.korrigieren_wert(), "Nut: „korrigiert“"
    )
    h.pruefe("Verschlei" not in satz_t, f"Nut: Satz mit Korrektur: {satz_t!r}")
    h.bild("2_womit_weiter_nut_taster", frage)
    frage.taster.setText("")
    yield 200
    frage.accept()
    yield from h.warte_auf(lambda: beta.BearbeitungPanel.offen is not None, 60000)
    panel = beta.BearbeitungPanel.offen
    yield from h.warte_auf(lambda: panel is not None and not panel.vorschau_laeuft(), 300000)
    yield 1000
    if panel is None:
        h.pruefe(False, "„Weiter bearbeiten“ öffnet kein Fenster")
        return
    aktiv = [b.s.kennung for b in panel.aktive_bloecke()]
    print("NUT angehakt", aktiv, "Seite", panel.seite(), flush=True)
    h.pruefe("schlichtendanach" in aktiv, f"„Schlichten danach“ nicht angehakt: {aktiv}")
    h.bild("3_schlichten", panel.form)
    h.pruefe(
        not panel.schlichten_danach.haken_felder["messstopp"].isChecked(),
        "„Schlichten danach“ mit eigenem Messstopp",
    )
    vorher = len(job.Operations.Group)
    panel.accept(bis_hier=True)
    yield from h.warte_auf(
        lambda: beta.BearbeitungPanel.offen is not panel or panel.geschlossen, 120000
    )
    yield 3000
    dazu = list(job.Operations.Group)[vorher:]
    arten = [
        "stopp" if ms.ist_messstopp(o) else "leer" if lf.ist_leerfahrt(o) else "schnitt"
        for o in dazu
    ]
    print("NUT dazu", [o.Label for o in dazu], arten, flush=True)
    h.pruefe(arten == ["schnitt", "leer", "stopp", "schnitt", "leer"], f"Folge: {arten}")
    stopp = next((o for o in dazu if ms.ist_messstopp(o)), None)
    m = ms.merkmal_von(list(stopp.Gcode)) if stopp is not None else None
    print(ascii(f"NUT Messstopp: {m}"), flush=True)
    h.pruefe(
        m is not None
        and m[0].art == messen.NUT
        and abs(m[0].breite - (NUT_B - 0.3)) < 1e-6
        and m[0].achse == "Y",
        f"Messstopp misst: {m}",
    )
    if arten == ["schnitt", "leer", "stopp", "schnitt", "leer"]:
        erster, _leer, _stopp, zweiter, _leer2 = dazu
        r = erster.ToolController.Tool.Diameter.Value / 2

        def breite(op):
            quer = [
                abs(b.Parameters["Y"] - NUT_Y)
                for b in op.Path.Commands
                if b.Name in ("G1", "G2", "G3") and "Y" in b.Parameters
                and 45.0 < b.Parameters.get("X", 0.0) < 75.0
            ]  # fmt: skip
            return round(2 * (max(quer) + r), 3) if quer else 0.0

        print("NUT breit", breite(erster), breite(zweiter), flush=True)
        h.pruefe(abs(breite(erster) - (NUT_B - 0.3)) < 0.01, f"erster: {breite(erster)}")
        h.pruefe(abs(breite(zweiter) - NUT_B) < 0.01, f"zweiter: {breite(zweiter)}")
    Gui.Selection.clearSelection()
    if stopp is not None:
        Gui.Selection.addSelection(stopp)
    yield 500
    h.bild("4_job", None)
    with __import__("contextlib").suppress(Exception):
        Gui.Control.closeDialog()
    yield 500
