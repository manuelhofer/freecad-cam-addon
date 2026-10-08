# SPDX-License-Identifier: LGPL-2.1-or-later
"""Programmfenster im tatsächlichen FreeCAD-Theme: Rollhintergrund und Neuaufbau."""

import json
import os
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui
import Part
import Path as NCPath
import Path.Main.Job as PathJob
from PySide import QtCore, QtGui


def kontrast(farbe, hintergrund):
    """Kontrast der wirksamen Schriftfarbe zum tatsächlich gerenderten Hintergrund."""

    def helligkeit(c):
        rgb = [x / 255 for x in c.getRgb()[:3]]
        linear = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in rgb]
        return sum(x * y for x, y in zip(linear, (0.2126, 0.7152, 0.0722), strict=True))

    dunkel, hell = sorted((helligkeit(farbe), helligkeit(hintergrund)))
    return (hell + 0.05) / (dunkel + 0.05)


def schritte(h):
    """Den gerenderten Rollinhalt mit dem Dialog vergleichen, auch nach Steuerungswechsel."""
    profil = Path(os.environ["FREECAD_USER_HOME"]).resolve()
    assert profil.is_dir() and Path(App.getUserAppDataDir()).resolve() == profil
    yield 500
    modal = h.modal()
    if modal is not None:
        modal.liste.setCurrentIndex(modal.liste.findData("de"))
        modal.accept()
    from camaddon import gui_programm as gp
    from camaddon import job_schnittwerte as js
    from camaddon import sprache
    from camaddon import uebergabe_werkzeuge as ue
    from camaddon import werkzeuge as wz
    from camaddon.sprache import tr

    sprache.setze_sprache("de")
    doc = App.newDocument("ProgrammTheme")
    obj = doc.addObject("Part::Feature", "Teil")
    obj.Shape = Part.makeBox(20, 20, 10)
    doc.recompute()
    w = wz.standardwerkzeug()
    bib = wz.Bibliothek([w])
    bib.speichern()
    ue.uebergeben(bib)
    job = PathJob.Create("Job", [obj])
    tc = js.controller_ohne_transaktion(doc, job, w, w.einsaetze(wz.ALLE)[0])
    op = doc.addObject("Path::Feature", "Probe")
    op.addProperty("App::PropertyLink", "ToolController")
    op.ToolController = tc
    op.Path = NCPath.Path([NCPath.Command("G0", {"X": 0, "Y": 0, "Z": 20})])
    job.Operations.addObject(op)
    doc.recompute()
    screen = next((s for s in QtGui.QApplication.screens() if s.name() == "DP-1"), None)
    mw = Gui.getMainWindow()
    if screen is not None:
        mw.showNormal()
        mw.windowHandle().setScreen(screen)
        mw.setGeometry(screen.availableGeometry())
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    Gui.runCommand("CamAddon_ProgrammSchreiben")
    yield 700
    d = gp.ProgrammDialog.offen
    h.pruefe(d is not None, "Programmfenster fehlt")
    if d is None:
        return
    if screen is not None:
        d.windowHandle().setScreen(screen)
        box = screen.availableGeometry()
        d.move(box.x() + (box.width() - d.width()) // 2, box.y() + (box.height() - d.height()) // 2)
    yield 300
    theme = os.environ.get("CAMADDON_THEME", "")
    hell = theme == "FreeCAD Light"
    report = {"theme": theme, "bildschirm": d.windowHandle().screen().name(), "farben": []}
    for kennung in ("linuxcnc", "fanuc", "siemens"):
        index = d.wahl_steuerung.findData(kennung)
        h.pruefe(index >= 0, f"Steuerung fehlt: {kennung}")
        d.wahl_steuerung.setCurrentIndex(index)
        yield 300
        Gui.updateGui()
        bild = d.grab().toImage()
        a = bild.pixelColor(2, 32)
        # Den zusammengesetzten Dialog messen: grab() des transparenten Kindes
        # allein zeichnet wieder dessen Systempaletten-Hintergrund.
        punkt = d.einstellungen.widget().mapTo(d, QtCore.QPoint(2, 22))
        b = bild.pixelColor(punkt)
        abstand = max(abs(x - y) for x, y in zip(a.getRgb()[:3], b.getRgb()[:3], strict=True))
        report["farben"].append({"steuerung": kennung, "dialog": a.name(), "inhalt": b.name()})
        if theme:
            h.pruefe(
                a.lightness() > 180 if hell else a.lightness() < 100,
                f"FreeCAD-Theme nicht wirksam: {theme} {a.name()}",
            )
        h.pruefe(abstand <= 3, f"{kennung}: Rollinhalt {b.name()} passt nicht zu Dialog {a.name()}")
        erklaerung = next(
            w
            for w in d.einstellungen.findChildren(QtGui.QLabel)
            if w.text() == tr("pp.einstellungen.erklaerung")
        )
        schrift = erklaerung.palette().color(QtGui.QPalette.WindowText)
        wert = kontrast(schrift, b)
        report["farben"][-1].update(schrift=schrift.name(), kontrast=wert)
        h.pruefe(wert >= 4.5, f"{kennung}: Erklärung zu kontrastarm: {wert:.2f}")
        h.pruefe(d.haken and d.vorschau.toPlainText(), f"{kennung}: Einstellungen/Vorschau leer")
        h.bild(("hell" if hell else "dunkel") + "_" + kennung, d)
    if screen is not None:
        h.pruefe(
            screen.availableGeometry().contains(d.frameGeometry().center()),
            "Testfenster nicht auf Bildschirm 2",
        )
    (Path(os.environ["CAMADDON_AUSGABE"]) / "theme.json").write_text(json.dumps(report, indent=2))
    d.reject()
    yield 200
