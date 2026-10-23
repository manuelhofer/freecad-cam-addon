# „Fertigteil als Rohteil“ (W-029; Manuel, 2026-10-18: „ein neues teil im selben ordner mit dem
# namen ... aufspannung 1 fertigteil ... so das man das dann nutzen kann als rohteil für die zweite
# aufspannung“): Manuels C-Ring mit seinen zwei Jobs. Im Menü „CAM-Addon“ steht der Befehl; ohne
# Auswahl fragt er, welcher Job. Für den Job aus Platte: Danach liegt „cring – Aufspannung 1 –
# Fertigteil“ im Dokument (das Teil heißt nur „Körper“, also der Name des Dokuments), dort, wo
# das Teil liegt (das Teil steckt ganz darin, das Rohteil ist größer), und als eigene Datei im
# Ordner des Dokuments; „Bearbeitung“ bietet es als Rohteil an. Die Meldung nennt Datei und den
# nächsten Schritt. Noch einmal gerechnet: dasselbe Objekt, keins dazu. Ein Job, dessen Rohteil
# das Fertigteil ist, wäre Aufspannung 2.
import os
import shutil
import tempfile

import FreeCAD
import FreeCADGui as Gui
from PySide import QtCore, QtGui

ADDON = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _meldung_lesen(h):
    meldung = h.modal()
    text = meldung.text() if isinstance(meldung, QtGui.QMessageBox) else ""
    return meldung, text


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500
    from camaddon import fertigteil as ft
    from camaddon import vierachs_rohteil as vr
    from camaddon.gui_bearbeitung import rohteil_kandidaten

    ordner = tempfile.mkdtemp()
    datei = os.path.join(ordner, "cring.FCStd")
    shutil.copy(os.path.join(ADDON, "beispiele", "c_ring_nut_3achs.FCStd"), datei)
    doc = FreeCAD.openDocument(datei)
    yield 1000
    Gui.activateWorkbench("CAMWorkbench")
    jobs = [o for o in doc.Objects if hasattr(o, "Operations")]
    platte = next(j for j in jobs if j.Label.startswith("C-Ring aus Platte"))
    teil = vr.original(vr.modell(platte))
    menue = next(
        (
            m
            for m in Gui.getMainWindow().menuBar().findChildren(QtGui.QMenu)
            if m.title() == "CAM-Addon"
        ),
        None,
    )
    texte = [a.text() for a in menue.actions()] if menue is not None else []
    h.pruefe("Fertigteil als Rohteil" in texte, f"Menü: {texte}")

    # Ohne Auswahl: Welcher Job? Die Liste nennt beide.
    Gui.Selection.clearSelection()
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_Fertigteil"))
    yield from h.warte_auf(lambda: isinstance(h.modal(), QtGui.QInputDialog), 5000)
    frage = h.modal()
    h.pruefe(isinstance(frage, QtGui.QInputDialog), f"keine Frage nach dem Job: {frage!r}")
    if isinstance(frage, QtGui.QInputDialog):
        h.pruefe(frage.comboBoxItems() == [j.Label for j in jobs], f"Jobs: {frage.comboBoxItems()}")
        h.bild("1_welcher_job", frage)
        frage.setTextValue(platte.Label)
        frage.accept()
    yield from h.warte_auf(lambda: isinstance(h.modal(), QtGui.QMessageBox), 60000)
    meldung, text = _meldung_lesen(h)
    h.bild("2_fertig", meldung)
    fertig = ft.vorhanden(platte)
    h.pruefe(fertig is not None, f"kein Fertigteil im Dokument; Meldung: {text!r}")
    if isinstance(meldung, QtGui.QMessageBox):
        meldung.accept()
    yield 500
    if fertig is None:
        return
    # Das Teil heißt nur „Body“: Das Fertigteil nennt das Dokument.
    name = "cring – Aufspannung 1 – Fertigteil"
    h.pruefe(fertig.Label == name, f"Name: {fertig.Label!r}")
    pfad = os.path.join(ordner, fertig.Label + ".FCStd")
    h.pruefe(os.path.exists(pfad), f"keine Datei {pfad!r}: {os.listdir(ordner)}")
    for soll in (fertig.Label, pfad, "Teil aus dem Dokument", "Raster 0,5 mm"):
        h.pruefe(soll in text, f"„{soll}“ fehlt in der Meldung: {text!r}")
    # Die Bahnen des Beispiels schneiden nirgends ins Teil (bis 0.276.3 fuhr „Wände schlichten
    # T1“ durch die Stege der Nut – das Fertigteil fand es): keine Warnung.
    h.pruefe("Achtung" not in text, f"Warnung: {text[:200]!r}")
    form = fertig.Shape
    h.pruefe(form.isValid() and len(form.Solids) == 1, f"Körper: {form.ShapeType}, gültig?")
    innen = teil.Shape.common(form).Volume
    h.pruefe(
        innen > 0.99 * teil.Shape.Volume,
        f"Das Teil liegt nicht im Fertigteil: {innen:.0f} von {teil.Shape.Volume:.0f} mm³",
    )
    rohteil = platte.Stock.Shape.Volume
    h.pruefe(
        teil.Shape.Volume < form.Volume < rohteil,
        f"Volumen: Teil {teil.Shape.Volume:.0f}, Fertigteil {form.Volume:.0f}, Rohteil {rohteil:.0f}",
    )
    h.pruefe(fertig in rohteil_kandidaten(doc, teil), "nicht als Rohteil angeboten")
    h.pruefe(fertig.Aufspannung == 1, f"Aufspannung {fertig.Aufspannung}")
    print(f"Fertigteil: {name}: {len(form.Faces)} Flächen, {form.Volume:.0f} mm³")
    andere = FreeCAD.openDocument(pfad)
    h.pruefe(
        len(andere.Objects) == 1 and abs(andere.Objects[0].Shape.Volume - form.Volume) < 1e-3,
        f"in der Datei: {[o.Label for o in andere.Objects]}",
    )
    FreeCAD.closeDocument(andere.Name)
    FreeCAD.setActiveDocument(doc.Name)

    # Noch einmal, den Job angeklickt: kein zweites Fertigteil.
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, platte.Name)
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_Fertigteil"))
    yield from h.warte_auf(lambda: isinstance(h.modal(), QtGui.QMessageBox), 60000)
    meldung, _ = _meldung_lesen(h)
    if isinstance(meldung, QtGui.QMessageBox):
        meldung.accept()
    yield 500
    zahl = len([o for o in doc.Objects if getattr(o, "AusJob", None) == platte.Name])
    h.pruefe(zahl == 1, f"{zahl} Fertigteile aus demselben Job")

    # Ein Job mit dem Fertigteil als Rohteil (ein Klon wie in „Bearbeitung“) ist Aufspannung 2.
    import Path.Main.Job as PathJob

    rund = next(j for j in jobs if j is not platte)
    klon = PathJob.createResourceClone(rund, fertig, "Stock", "Stock")
    alt = rund.Stock
    rund.Stock = klon
    h.pruefe(ft.aufspannung(rund) == 2, f"Aufspannung {ft.aufspannung(rund)}")
    h.pruefe("Aufspannung 2" in ft.name_fuer(rund), ft.name_fuer(rund))
    rund.Stock = alt
    Gui.getDocument(doc.Name).Modified = False
    FreeCAD.closeDocument(doc.Name)
