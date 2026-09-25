# Erster Start nach der Installation: Sprachwahl erscheint auf Englisch,
# beschriftet sich beim Wählen von Deutsch um, danach hängt die Werkzeug-
# leiste des Addons im Assembly-Arbeitsbereich.
import FreeCADGui
from PySide import QtGui


def schritte(h):
    yield 1000
    dialog = h.modal()
    h.pruefe(dialog is not None, "Sprachwahl erscheint beim ersten Start nicht")
    if dialog is None:
        return
    h.bild("1_sprachwahl_englisch", dialog)
    h.pruefe(dialog.windowTitle() == "Choose language", "Sprachwahl startet nicht auf Englisch")

    dialog.liste.setCurrentIndex(dialog.liste.findData("de"))
    yield 300
    h.bild("2_sprachwahl_deutsch", dialog)
    h.pruefe(dialog.windowTitle() == "Sprache wählen", "Sprachwahl beschriftet sich nicht um")
    dialog.accept()
    yield 500

    from camaddon import sprache

    h.pruefe(sprache.gewaehlte_sprache() == "de", "Wahl wurde nicht gespeichert")

    FreeCADGui.activateWorkbench("AssemblyWorkbench")
    yield 1500
    leisten = [t.windowTitle() for t in FreeCADGui.getMainWindow().findChildren(QtGui.QToolBar)
               if t.isVisible()]
    h.pruefe("CAM-Addon" in leisten, f"Werkzeugleiste fehlt in Assembly, da sind: {leisten}")
    h.bild("3_assembly_werkzeugleiste")

    FreeCADGui.activateWorkbench("CAMWorkbench")
    yield 2500
    leisten = [t.windowTitle() for t in FreeCADGui.getMainWindow().findChildren(QtGui.QToolBar)
               if t.isVisible()]
    h.pruefe("CAM-Addon" in leisten, f"Werkzeugleiste fehlt in CAM, da sind: {leisten}")
    h.bild("4_cam_werkzeugleiste")

    # Einstellungsseite: zeigt die gewählte Sprache und speichert eine neue.
    from camaddon import gui_sprachwahl

    seite = gui_sprachwahl.Einstellungsseite()
    seite.loadSettings()
    h.pruefe(seite.liste.currentData() == "de", "Einstellungsseite zeigt nicht die gewählte Sprache")
    seite.form.resize(500, 200)
    seite.form.show()
    yield 300
    h.bild("5_einstellungsseite", seite.form)
    seite.liste.setCurrentIndex(seite.liste.findData("en"))
    seite.saveSettings()
    h.pruefe(sprache.gewaehlte_sprache() == "en", "Einstellungsseite speichert die Sprache nicht")
    seite.form.close()
