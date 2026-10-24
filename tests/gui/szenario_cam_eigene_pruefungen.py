# Die eigenen Prüfungen von FreeCAD CAM (TestCAMApp, 2093 im Wochen-Build) im selben FreeCAD wie das
# Addon: Das Addon darf an CAM nichts kaputt machen (die CAM-Entwickler, Discord 2026-10-23; Manuel,
# 2026-10-24: „mach das alles so das alle zufriden sind“). Erst der Arbeitsbereich CAM mit der
# Werkzeugleiste des Addons, ein Fenster des Addons geöffnet und geschlossen (Auswahl-Beobachter
# und -Filter kommen und gehen), dann die Prüfungen. Was dabei scheitert, steht in
# cam_pruefungen.txt; scheitern darf nur, was ohne Addon genauso scheitert (BEKANNT_JE_VERSION – mit
# freecadcmd ohne Addon nachgesehen, je Version). TestCAMGui (37) läuft hier nicht: In diesem Szenario-Werkzeug
# stürzt FreeCAD danach in einem Timer ab – auch ohne ein Fenster des Addons, in FreeCAD mit Addon
# ohne das Werkzeug nicht (2026-10-24: 37 grün, danach weiter bedienbar).
# ZEITLIMIT: 1500
import os
import unittest

import FreeCAD
import FreeCADGui as Gui

# Ohne Addon genauso rot (freecadcmd -t TestCAMApp, ohne Addon nachgesehen): im Wochen-Build 27.1 dev
# vom 21.10. keine; in FreeCAD 1.1.4 test46 und test47 von TestPathOpUtil („BRep_API: command not
# done“ in offsetWire – OpenCascade 7.9).
BEKANNT_JE_VERSION = {
    (1, 1): {
        "CAMTests.TestPathOpUtil.TestPathOpUtil.test46",
        "CAMTests.TestPathOpUtil.TestPathOpUtil.test47",
    },
}


def _bekannt():
    try:
        version = tuple(int(x) for x in FreeCAD.Version()[:2])
    except (ValueError, IndexError):
        return set()
    return BEKANNT_JE_VERSION.get(version, set())


def _ergebnis(name, modul):
    lader = unittest.TestLoader()
    suite = lader.loadTestsFromName(modul)
    ergebnis = unittest.TextTestRunner(verbosity=0).run(suite)
    gescheitert = [t.id() for t, _ in ergebnis.failures + ergebnis.errors]
    return ergebnis.testsRun, gescheitert


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500
    Gui.activateWorkbench("CAMWorkbench")
    yield 800
    from camaddon import gui_bearbeitung

    # Ein Fenster des Addons auf und zu: Beobachter und Auswahlfilter müssen wieder weg sein.
    doc = FreeCAD.newDocument("Kasten")
    import Part

    teil = doc.addObject("Part::Feature", "Kasten")
    teil.Shape = Part.makeBox(30, 20, 10)
    doc.recompute()
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, "Face6")
    yield 300
    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None, "„Bearbeitung“ öffnet nicht")
    if panel is not None:
        panel.reject()
        yield 1000
    FreeCAD.closeDocument(doc.Name)
    yield 500
    zeilen = []
    # Die Testjobs von CAM schneiden absichtlich ins Teil – nicht als Schnitte des Addons zählen.
    os.environ["CAMADDON_IM_TEIL_AUS"] = "1"
    for name, modul in (("TestCAMApp", "TestCAMApp"),):
        try:
            anzahl, gescheitert = _ergebnis(name, modul)
        except Exception as fehler:  # noqa: BLE001 – die Prüfung selbst lädt nicht
            h.pruefe(False, f"{name} lädt nicht: {fehler}")
            continue
        neu = sorted(set(gescheitert) - _bekannt())
        zeilen.append(f"{name}: {anzahl} Prüfungen, gescheitert {len(gescheitert)}")
        zeilen += [f"  {t}" for t in gescheitert]
        print(ascii(f"{name}: {anzahl} Prüfungen, gescheitert {len(gescheitert)}"))
        h.pruefe(anzahl > 0, f"{name}: keine Prüfungen gefunden")
        h.pruefe(not neu, f"{name}: mit dem Addon gescheitert: {neu[:10]}")
        yield 300
    with open(
        os.path.join(os.environ["CAMADDON_AUSGABE"], "cam_pruefungen.txt"), "w", encoding="utf-8"
    ) as datei:
        datei.write("\n".join(zeilen) + "\n")
    # Die Prüfungen von CAM lassen Dokumente offen – schließen, ohne zu fragen.
    for name in list(FreeCAD.listDocuments()):
        Gui.getDocument(name).Modified = False
        FreeCAD.closeDocument(name)
    yield 500
    os.environ.pop("CAMADDON_IM_TEIL_AUS", None)
