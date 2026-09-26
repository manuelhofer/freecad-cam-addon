# Erster Start nach der Installation: Sprachwahl erscheint auf Englisch (so
# läuft FreeCAD hier), mit dem Namen des Addons im Titel und Platz für die
# Texte jeder Sprache; beim Wählen von Deutsch beschriftet sie sich um. Die
# Wahl steht sofort in user.cfg, die Knöpfe des Addons sind gleich deutsch,
# und die Werkzeugleiste hängt im Assembly- und im CAM-Arbeitsbereich.
import os

import FreeCAD
import FreeCADGui
from PySide import QtGui


def schritte(h):
    yield 1000
    dialog = h.modal()
    h.pruefe(dialog is not None, "Sprachwahl erscheint beim ersten Start nicht")
    if dialog is None:
        return
    h.bild("1_sprachwahl_englisch", dialog)
    h.pruefe(
        dialog.windowTitle() == "CAM Addon – Choose language",
        f"Sprachwahl startet nicht auf Englisch: {dialog.windowTitle()!r}",
    )

    dialog.liste.setCurrentIndex(dialog.liste.findData("de"))
    yield 300
    h.bild("2_sprachwahl_deutsch", dialog)
    h.pruefe(
        dialog.windowTitle() == "CAM-Addon – Sprache wählen",
        f"Sprachwahl beschriftet sich nicht um: {dialog.windowTitle()!r}",
    )
    # Das Fenster hatte von Anfang an Platz für den längeren deutschen Text –
    # es wächst beim Umschalten nicht auf jedem System mit.
    noetig = dialog.heightForWidth(dialog.width())
    h.pruefe(dialog.minimumHeight() >= noetig, f"zu niedrig: {dialog.minimumHeight()} < {noetig}")
    dialog.accept()
    yield 500

    from camaddon import sprache

    h.pruefe(sprache.gewaehlte_sprache() == "de", "Wahl wurde nicht gespeichert")
    with open(os.path.join(FreeCAD.getUserConfigDir(), "user.cfg"), encoding="utf-8") as datei:
        h.pruefe('Name="Sprache"' in datei.read(), "Wahl steht nicht sofort in user.cfg")

    FreeCADGui.activateWorkbench("AssemblyWorkbench")
    yield 1500
    leisten = [
        t.windowTitle()
        for t in FreeCADGui.getMainWindow().findChildren(QtGui.QToolBar)
        if t.isVisible()
    ]
    h.pruefe("CAM-Addon" in leisten, f"Werkzeugleiste fehlt in Assembly, da sind: {leisten}")
    h.bild("3_assembly_werkzeugleiste")

    FreeCADGui.activateWorkbench("CAMWorkbench")
    yield 2500
    leisten = [
        t.windowTitle()
        for t in FreeCADGui.getMainWindow().findChildren(QtGui.QToolBar)
        if t.isVisible()
    ]
    h.pruefe("CAM-Addon" in leisten, f"Werkzeugleiste fehlt in CAM, da sind: {leisten}")
    h.pruefe(leisten.count("CAM-Addon") == 1, f"Werkzeugleiste doppelt: {leisten}")
    # FreeCAD hat die Texte vor der Wahl gelesen – die Knöpfe sind trotzdem deutsch.
    aktion = FreeCADGui.Command.get("CamAddon_SchnittwerteJob").getAction()[0]
    h.pruefe(aktion.text() == "Schnittwerte in den Job", f"Knopf: {aktion.text()!r}")
    h.pruefe("Setzt Drehzahl und Vorschub" in aktion.toolTip(), f"Tooltip: {aktion.toolTip()!r}")
    h.bild("4_cam_werkzeugleiste")

    # Einstellungsseite: zeigt die gewählte Sprache und speichert eine neue.
    from camaddon import gui_sprachwahl

    seite = gui_sprachwahl.Einstellungsseite()
    seite.loadSettings()
    h.pruefe(
        seite.liste.currentData() == "de", "Einstellungsseite zeigt nicht die gewählte Sprache"
    )
    seite.form.resize(500, 200)
    seite.form.show()
    yield 300
    h.bild("5_einstellungsseite", seite.form)
    seite.liste.setCurrentIndex(seite.liste.findData("en"))
    seite.saveSettings()
    h.pruefe(sprache.gewaehlte_sprache() == "en", "Einstellungsseite speichert die Sprache nicht")
    h.pruefe(
        aktion.text() == "Cutting data into the job", f"zurück auf Englisch: {aktion.text()!r}"
    )
    seite.form.close()

    # Ohne Wahl gilt die Sprache, in der FreeCAD läuft – hier nachgestellt.
    FreeCADGui.setLocale("German")
    sprache._freecad.clear()
    h.pruefe(sprache.freecad_sprache() == "de", f"FreeCAD auf Deutsch: {sprache.freecad_sprache()}")
    FreeCADGui.setLocale("Japanese")
    sprache._freecad.clear()
    h.pruefe(sprache.freecad_sprache() is None, "Japanisch gibt es hier nicht – dann Englisch")
    FreeCADGui.setLocale("English")
    sprache._freecad.clear()
