# „Weiter bearbeiten“ bei den Löchern: „Bohrung fräsen“ in zwei gleichen Schnitten mit Messen
# dazwischen und Leerfahrten (Manuel, 2026-11-14: „erstes vorschlichten ... und danach nochmal
# erstes vorschlichten .... dann messsen ... dann vertigschlichten ... und dann nochmal vertig
# schlichten ... aber klar alles als option“). Ein Block 80 × 60 × 20 mit einer Bohrung Ø 30
# (durch), T1 der Standardfräser Ø 12; am Job gemerkt die Bohrung, angelegt bis zum Schruppen.
# Job anklicken, „Weiter bearbeiten (Beta)“: vorgewählt „Löcher“, „In zwei gleichen Schnitten“
# angehakt (die Helix lässt 0,3: „erst 0,15, dann 0“), „Leerfahrt nach jedem Schnitt“ wählbar;
# der Messstopp steht zwischen den Schnitten und misst die Bohrung Ø 29,7. „Anlegen“: Bohrung
# fräsen (Schlichtrest 0,15), Leerfahrt (nur der Schlichtzug), Messstopp, der Schlichtzug auf Maß,
# Leerfahrt – kein Bohrer, kein zweites Mal Helix. Der Ø nach jedem Schnitt aus der Bahn.
# ZEITLIMIT: 600
import math

import FreeCAD
import FreeCADGui as Gui
import Part

V = FreeCAD.Vector
D = 30.0


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    import Path.Main.Job as PathJob
    from PySide import QtCore

    from camaddon import bohrung as bo
    from camaddon import bohrung_bahn as bb
    from camaddon import gui_bearbeitung_beta as beta
    from camaddon import leerfahrt as lf
    from camaddon import messstopp as ms
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    beta.beta_setzen(True)
    wz.Bibliothek([wz.standardwerkzeug()]).speichern()
    doc = FreeCAD.newDocument("Bohrung")
    teil = doc.addObject("Part::Feature", "Block")
    teil.Shape = Part.makeBox(80, 60, 20).cut(Part.makeCylinder(D / 2, 20, V(25, 30, 0)))
    doc.recompute()
    Gui.activateWorkbench("CAMWorkbench")
    yield 500
    job = PathJob.Create("Job", [teil])
    doc.recompute()
    klon = vr.modell(job)
    bohrung = next(b for b in bb.bohrungen(klon.Shape) if abs(b.radius - D / 2) < 1e-6)
    job.addProperty("App::PropertyStringList", beta.EIGENSCHAFT_FLAECHEN, beta.GRUPPE, "")
    job.addProperty("App::PropertyInteger", beta.EIGENSCHAFT_ABSCHNITT, beta.GRUPPE, "")
    setattr(job, beta.EIGENSCHAFT_FLAECHEN, [bohrung.name])
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
    h.pruefe(frage.abschnitt() == beta.LOECHER, f"vorgewählt: {frage.abschnitt()}")
    h.pruefe(frage.zwei.isVisible() and frage.zwei.isChecked(), "„zwei Schnitte“ nicht an")
    h.pruefe(
        not frage.aufmass.isVisible() and not frage.aufmass_einheit.isVisible(),
        "Feld „Aufmaß“ (oder sein „mm“) bei den Löchern",
    )
    h.pruefe("zwischen" in frage.messstopp.text(), f"Messstopp: {frage.messstopp.text()!r}")
    h.pruefe("0,15" in frage.zwei_text.text(), f"erst/dann: {frage.zwei_text.text()!r}")
    h.pruefe(frage.leerfahrt.isVisible() and not frage.leerfahrt.isChecked(), "Leerfahrt")
    frage.leerfahrt.setChecked(True)
    frage.messstopp.setChecked(True)  # ohne Operationen im Job aus vorbelegt
    yield 300
    satz = frage.messen_text.text()
    print(ascii(f"Messen: {satz} / {frage.messstopp.text()}"), flush=True)
    h.pruefe("Bohrung" in satz and "29,7" in satz, f"Messen: {satz!r}")
    h.pruefe("zwischen" in frage.messstopp.text(), f"Messstopp: {frage.messstopp.text()!r}")
    h.bild("1_womit_weiter_loecher", frage)
    # Gegenprobe: beim Schlichten ohne Gang davor kein „zwei Schnitte“, der Satz wieder der Job.
    frage.wahl[beta.SCHLICHTEN].setChecked(True)
    yield 200
    h.pruefe(not frage.zwei.isVisible(), "„zwei Schnitte“ beim Schlichten ohne Gang davor")
    frage.wahl[beta.LOECHER].setChecked(True)
    yield 200
    h.pruefe(frage.zwei.isChecked() and frage.zwei_wert(), "„zwei Schnitte“ nach dem Wechsel aus")
    frage.accept()
    yield from h.warte_auf(lambda: beta.BearbeitungPanel.offen is not None, 60000)
    panel = beta.BearbeitungPanel.offen
    yield from h.warte_auf(lambda: panel is not None and not panel.vorschau_laeuft(), 300000)
    yield 1000
    if panel is None:
        h.pruefe(False, "„Weiter bearbeiten“ öffnet kein Fenster")
        return
    aktiv = [b.s.kennung for b in panel.aktive_bloecke()]
    print("ZWEI angehakt", aktiv, "Seite", panel.seite(), flush=True)
    h.pruefe("bohrung" in aktiv, f"„Bohrung fräsen“ nicht angehakt: {aktiv}")
    h.bild("2_loecher", panel.form)
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
    print("ZWEI dazu", [o.Label for o in dazu], arten, flush=True)
    h.pruefe(arten == ["schnitt", "leer", "stopp", "schnitt", "leer"], f"Folge: {arten}")
    if arten != ["schnitt", "leer", "stopp", "schnitt", "leer"]:
        return
    erster, leer, stopp, zweiter, leer2 = dazu
    h.pruefe(bo.ist_bohrungsfraesen(erster) and bo.ist_bohrungsfraesen(zweiter), "keine Bohrung")
    h.pruefe(
        abs(float(erster.Schlichtrest) - 0.15) < 1e-9 and not erster.NurSchlichten,
        f"erster: Rest {erster.Schlichtrest}",
    )
    h.pruefe(zweiter.NurSchlichten and float(zweiter.Schlichtrest) == 0.0, "zweiter: Werte")
    mitte = (bohrung.mitte[0], bohrung.mitte[1])
    r = erster.ToolController.Tool.Diameter.Value / 2

    def durchmesser(op):
        weit, helix, z = 0.0, 0, None
        for b in op.Path.Commands:
            p = b.Parameters
            neu_z = p.get("Z", z)
            if b.Name in ("G2", "G3"):
                weit = max(weit, math.hypot(p["X"] - mitte[0], p["Y"] - mitte[1]))
                helix += int(z is not None and abs(neu_z - z) > 1e-6)
            z = neu_z
        return 2 * (weit + r), helix

    gemessen = [durchmesser(o) for o in (erster, leer, zweiter, leer2)]
    print("ZWEI Ø/Helix", [(round(d, 3), n) for d, n in gemessen], flush=True)
    soll = [D - 0.3, D - 0.3, D, D]
    h.pruefe(
        all(abs(d - s) < 0.01 for (d, _n), s in zip(gemessen, soll, strict=True)),
        f"Ø nach jedem Schnitt: {gemessen}",
    )
    h.pruefe(gemessen[0][1] > 0 and all(n == 0 for _d, n in gemessen[1:]), f"Helix: {gemessen}")
    m = ms.merkmal_von(list(stopp.Gcode))
    print(ascii(f"ZWEI Messstopp: {m}"), flush=True)
    h.pruefe(
        m is not None and m[0].art == "bohrung" and abs(m[0].durchmesser - (D - 0.3)) < 1e-6,
        f"Messstopp misst: {m}",
    )
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(leer)
    yield 500
    h.bild("3_job", None)
    with __import__("contextlib").suppress(Exception):
        Gui.Control.closeDialog()
    yield 500
