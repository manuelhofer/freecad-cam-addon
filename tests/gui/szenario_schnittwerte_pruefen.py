# Veraltete Schnittwerte im Fenster „Auf der Maschine prüfen“ (Durchsicht W-004,
# D-28): Die Beispiel-Fräse und ein Teil mit zwei Operationen; ihre Controller
# „T3 Schruppen dynamisch“ und „T3 Vollnut“ hat das Addon aus der
# Werkzeugverwaltung angelegt. Oben steht grün „Schnittwerte: Drehzahl und
# Vorschub wie in der Werkzeugverwaltung.“ Dann steigt vc in der
# Werkzeugverwaltung von 120 auf 150 m/min: Beim nächsten Prüfen steht gelb je
# Controller „im Job 3183 U/min · …, laut Werkzeugverwaltung 3979 U/min · … –
# übernehmen“ und darunter „Alle übernehmen“. „übernehmen“ setzt einen, Strg+Z
# nimmt ihn zurück, „Alle übernehmen“ setzt beide – dann ist es wieder grün.
# Beide Controller benutzen dasselbe Werkzeug; die Hinweise nennen T3 einmal,
# ohne „… L001“ (D-09).
import FreeCAD
import FreeCADGui as Gui
from PySide import QtCore

BAHN = ["G0 X0 Y0 Z10", "G1 Z-5 F100", "G1 X50 Y20", "G0 Z10"]


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    import Path.Main.Job as PathJob
    import Path.Op.Custom as PathCustom

    from camaddon import beispielmaschine, gui_reichweite
    from camaddon import job_schnittwerte as js
    from camaddon import uebergabe_werkzeuge as ue
    from camaddon import werkzeuge as wz

    fraeser = wz.Werkzeug(nummer=3, durchmesser=12, schneiden=3, schneidenlaenge=26)
    fraeser.schnittwerte[wz.ALLE] = [
        wz.Einsatz(art=wz.DYNAMISCH, ae=1.2, ap=25, vc=120, fz=0.15),
        wz.Einsatz(art=wz.VOLLNUT, ae=12, ap=3, vc=120, fz=0.05),
    ]
    bibliothek = wz.Bibliothek([fraeser])
    bibliothek.speichern()
    ue.uebergeben(bibliothek)

    asm, _maschine = beispielmaschine.lade(beispielmaschine.FRAESE_3)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    yield 300

    teil = FreeCAD.newDocument("Teil")
    teil.UndoMode = 1
    quader = teil.addObject("Part::Box", "Quader")
    quader.Length, quader.Width, quader.Height = 100, 60, 20
    teil.recompute()
    job = PathJob.Create("Job", [quader])
    # Die Operationen, solange der Job nur einen Controller hat – sonst fragt FreeCAD.
    operationen = []
    for name in ("Dynamisch", "Nut"):
        op = PathCustom.Create(name)
        op.Gcode = BAHN
        operationen.append(op)
    controller = [
        js.lege_controller_an(teil, job, fraeser, einsatz, wz.ALLE)
        for einsatz in fraeser.schnittwerte[wz.ALLE]
    ]
    for op, tc in zip(operationen, controller, strict=True):
        op.ToolController = tc
    teil.recompute()
    dynamisch, nut = controller
    h.pruefe(
        (dynamisch.Label, nut.Label) == ("T3 Schruppen dynamisch", "T3 Vollnut"),
        f"Controller: {dynamisch.Label}, {nut.Label}",
    )
    yield 500

    def pruefen():
        FreeCAD.setActiveDocument(teil.Name)
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(job)
        yield 400  # 1.1.3 verarbeitet die Auswahl verzögert (szenario_reichweite.py)
        QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
        yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None, 15000)
        yield 500
        return gui_reichweite.PruefPanel.offen

    # --- Frisch angelegt: grün ------------------------------------------------------------
    panel = yield from pruefen()
    h.pruefe(panel is not None, "„Auf der Maschine prüfen“ öffnet kein Fenster")
    if panel is None:
        return
    urteil = panel.urteil_schnittwerte
    h.pruefe(
        urteil.text() == "Drehzahl und Vorschub wie in der Werkzeugverwaltung.",
        f"frisch: {urteil.text()!r}",
    )
    h.pruefe(not urteil.visibleRegion().isEmpty(), "Urteil „Schnittwerte“ nicht zu sehen")
    h.pruefe(bool(urteil.toolTip()), "Urteil „Schnittwerte“ ohne Tooltip")
    # D-09: ein Werkzeug für beide Controller, T3 einmal in den Hinweisen.
    h.pruefe(dynamisch.Tool is nut.Tool, f"zweites Werkzeug angehängt: {nut.Tool.Label}")
    hinweise = panel.hinweise.text()
    h.pruefe(hinweise.count("T3 „") == 1, f"T3 nicht genau einmal: {hinweise!r}")
    h.pruefe("L001" not in hinweise, f"„L001“ in den Hinweisen: {hinweise!r}")
    panel.reject()
    yield 800

    # --- vc in der Werkzeugverwaltung erhöht: gelb, je Controller ein Satz --------------------
    for einsatz in fraeser.schnittwerte[wz.ALLE]:
        einsatz.vc = 150
    bibliothek.speichern()
    panel = yield from pruefen()
    if panel is None:
        return
    urteil = panel.urteil_schnittwerte
    text = urteil.text()
    h.pruefe(
        "T3 Schruppen dynamisch: im Job 3183 U/min · 1432 mm/min, laut Werkzeugverwaltung "
        f'3979 U/min · 1790 mm/min – <a href="schnittwerte:{dynamisch.Name}">übernehmen</a>'
        in text,
        f"veraltet: {text!r}",
    )
    h.pruefe("T3 Vollnut: im Job 3183 U/min · 477 mm/min" in text, f"Vollnut fehlt: {text!r}")
    h.pruefe('<a href="schnittwerte:*">Alle übernehmen</a>' in text, f"„Alle“ fehlt: {text!r}")
    h.pruefe(not urteil.visibleRegion().isEmpty(), "veraltete Schnittwerte nicht zu sehen")
    h.bild("1_veraltet", panel.form)

    # „übernehmen“ beim ersten: nur er, ein Schritt Rückgängig.
    urteil.linkActivated.emit(f"schnittwerte:{dynamisch.Name}")
    yield 500
    h.pruefe(dynamisch.SpindleSpeed == 3979, f"übernommen: {dynamisch.SpindleSpeed}")
    h.pruefe(nut.SpindleSpeed == 3183, f"Vollnut mit übernommen: {nut.SpindleSpeed}")
    text = urteil.text()
    h.pruefe(
        "T3 Schruppen dynamisch" not in text and "T3 Vollnut" in text and "Alle" not in text,
        f"nach einem: {text!r}",
    )
    teil.undo()
    h.pruefe(dynamisch.SpindleSpeed == 3183, f"Strg+Z: {dynamisch.SpindleSpeed}")

    # „Alle übernehmen“: beide, danach grün.
    panel.pruefe()
    urteil.linkActivated.emit("schnittwerte:*")
    yield 500
    werte = [
        (tc.SpindleSpeed, round(float(tc.HorizFeed.getValueAs("mm/min")))) for tc in controller
    ]
    h.pruefe(werte == [(3979, 1790), (3979, 597)], f"alle übernommen: {werte}")
    h.pruefe(
        urteil.text() == "Drehzahl und Vorschub wie in der Werkzeugverwaltung.",
        f"nach „Alle“: {urteil.text()!r}",
    )
    h.bild("2_uebernommen", panel.form)
    panel.reject()
    yield 800

    for name in list(FreeCAD.listDocuments()):
        FreeCAD.closeDocument(name)
    yield 300
