# Dialog „Maschine bearbeiten“ an der Beispiel-Drehmaschine: leer öffnen,
# Betriebsarten (Z1, X1, S4 + C4 an einem Gelenk, Revolver) und Aufnahmen
# anlegen, 12 Revolverplätze verteilen, OK = ein Schritt Rückgängig,
# Abbrechen verwirft.
import os
import sys

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtGui

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def eintrag(baum, text_anfang):
    it = QtGui.QTreeWidgetItemIterator(baum)
    while it.value():
        if it.value().text(0).lstrip("↔⟳ ").startswith(text_anfang):
            return it.value()
        it += 1
    return None


def feld(panel, zeile):
    return panel.detail_aufbau.itemAt(zeile, QtGui.QFormLayout.FieldRole).widget()


def tippen(widget, text):
    widget.setText(text)
    widget.editingFinished.emit()


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.accept()
    yield 500

    import beispielmaschinen
    from camaddon import gui_maschine, maschine as m

    asm = beispielmaschinen.drehmaschine()
    doc = asm.Document
    Gui.activateWorkbench("AssemblyWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(asm)
    yield 500
    undo_vorher = len(doc.UndoNames)

    Gui.runCommand("CamAddon_MaschineBearbeiten")
    yield 1500
    panel = gui_maschine.MaschinenPanel.offen
    h.pruefe(panel is not None, "Dialog öffnet sich nicht")
    if panel is None:
        return
    h.bild("1_leer")
    h.pruefe(panel.hinweise.count() == 2, f"leere Maschine: {panel.hinweise.count()} Hinweise statt 2")
    h.pruefe(panel.knopf_betriebsart.isEnabled(), "„+ Betriebsart“ ist beim Öffnen nicht bedienbar")

    # Betriebsarten anlegen – wie ein Benutzer: Gelenk wählen, Art wählen, Felder füllen.
    for gelenk, art, name, werte in (
        ("Z", m.ART_LINEAR, "Z1", ["30000"]),
        ("X", m.ART_LINEAR, "X1", ["24000"]),
        ("Spindel", m.ART_SPINDEL, "S4", ["4000"]),
        ("Spindel", m.ART_POSITIONIEREN, "C4", [None, "100"]),
        ("Revolverachse", m.ART_REVOLVER, "T", []),
    ):
        panel.achsen.setCurrentItem(eintrag(panel.achsen, gelenk))
        panel._betriebsart_neu(doc.getObject(gelenk), art)
        yield 100
        tippen(feld(panel, 0), name)
        for i, wert in enumerate(werte, start=1):
            if wert is not None:
                tippen(feld(panel, i), wert)
        yield 100

    panel.achsen.setCurrentItem(eintrag(panel.achsen, "X1"))
    yield 300
    h.bild("2_achsen_x1_gewaehlt")

    # Aufnahmen: Futter als Werkstückaufnahme, angetrieben von S4 gibt es nur bei
    # Werkzeugen; Revolverplätze über die Verteilhilfe.
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.getObject("Spannflaeche"))
    panel._aufnahme_neu(m.AUFNAHME_WERKSTUECK)
    yield 200
    tippen(feld(panel, 0), "Futter")
    rev = next(ba for ba in m.betriebsarten(panel.maschine) if ba.Art == m.ART_REVOLVER)
    dialog = gui_maschine.VerteilDialog(panel.form, [rev], panel._lcs_im_revolver)
    dialog.show()
    yield 300
    h.bild("3_verteilen", dialog)
    angeboten = [dialog.wahl_lcs.itemText(i) for i in range(dialog.wahl_lcs.count())]
    h.pruefe(angeboten == ["Werkzeugplatz"], f"Verteilhilfe bietet {angeboten} an statt nur den Werkzeugplatz")
    alle = [o.Label for o in panel._alle_lcs()]
    h.pruefe(not any(n.startswith("Origin") for n in alle), f"Ursprünge als Koordinatensystem angeboten: {alle}")
    dialog.accept()
    m.verteile_plaetze(panel.maschine, panel.kette, rev, doc.getObject("Werkzeugplatz"), 12)
    doc.recompute()
    panel._fuelle_alles()
    yield 500

    h.pruefe(panel.aufnahmen.topLevelItemCount() == 2, f"{panel.aufnahmen.topLevelItemCount()} Einträge oben statt 2 (Revolver-Gruppe, Futter)")
    gruppe = panel.aufnahmen.topLevelItem(0)
    h.pruefe(gruppe.childCount() == 12 and "12" in gruppe.text(0), f"Revolver-Gruppe: {gruppe.text(0)}, {gruppe.childCount()} Plätze")
    del gruppe  # keine Zeilen-Objekte über einen Neuaufbau der Liste hinweg festhalten
    futter = panel.aufnahmen.topLevelItem(1).text(0)
    h.pruefe(futter.startswith("Futter  ·"), f"Aufnahme heißt nicht „Futter“: {futter}")
    texte = [panel.hinweise.item(i).text() for i in range(panel.hinweise.count())]
    h.pruefe(texte == ["Alles vollständig – keine Hinweise."], f"Hinweise nach dem Ausfüllen: {texte}")
    panel.aufnahmen.setCurrentItem(eintrag(panel.aufnahmen, "P3"))
    yield 300
    h.bild("4_vollstaendig_p3_gewaehlt")

    # Ein Fehler: X1 ohne Eilgang -> Hinweis erscheint, Klick springt zur Achse.
    panel.achsen.setCurrentItem(eintrag(panel.achsen, "X1"))
    yield 100
    tippen(feld(panel, 1), "")
    yield 300
    texte = [panel.hinweise.item(i).text() for i in range(panel.hinweise.count())]
    h.pruefe(any("X1" in t and "Eilgang" in t for t in texte), f"fehlender Eilgang nicht gemeldet: {texte}")
    panel.aufnahmen.setCurrentItem(None)
    panel._hinweis_geklickt(panel.hinweise.item(0))
    aktuell = panel.achsen.currentItem()
    h.pruefe(aktuell is not None and aktuell.text(0).startswith("X1"), "Klick auf Hinweis springt nicht zu X1")
    del aktuell
    tippen(feld(panel, 1), "24000")
    yield 300
    h.bild("5_hinweis_geklickt")

    panel.accept()
    yield 500
    h.pruefe(len(doc.UndoNames) == undo_vorher + 1, f"OK ergibt {len(doc.UndoNames) - undo_vorher} Rückgängig-Schritte statt 1")
    ma = m.finde_maschine(asm)
    namen = sorted(ba.NcName for ba in m.betriebsarten(ma)) if ma else []
    h.pruefe(namen == ["C4", "S4", "T", "X1", "Z1"], f"nach OK: {namen}")

    # Abbrechen verwirft: X1 umbenennen und abbrechen.
    Gui.runCommand("CamAddon_MaschineBearbeiten")
    yield 1000
    panel = gui_maschine.MaschinenPanel.offen
    panel.achsen.setCurrentItem(eintrag(panel.achsen, "X1"))
    tippen(feld(panel, 0), "X9")
    panel.reject()
    yield 500
    namen = sorted(ba.NcName for ba in m.betriebsarten(ma))
    h.pruefe("X1" in namen and "X9" not in namen, f"Abbrechen verwirft nicht: {namen}")

    # Rückgängig nimmt die ganze Maschine in einem Schritt zurück.
    doc.undo()
    yield 300
    h.pruefe(m.finde_maschine(asm) is None, "Rückgängig entfernt die Maschine nicht")
