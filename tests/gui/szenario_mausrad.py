# Das ruhige Mausrad (#39): Wer im Aufgabenfenster oder in einem Dialog blättert
# und dabei über eine Auswahlliste, ein Drehfeld oder einen Regler fährt,
# verstellt nichts – so kam wohl das „P10“ in Manuels Revolverplatz
# (P-2026-09-26-52). Das Rad geht an das, was darunter blättert: Das
# Aufgabenfenster rollt weiter. Erst nach einem Klick ins Feld rollt das Rad
# den Wert wie gewohnt.
#
# Die Rasten kommen wie von einer Maus über den X-Server (XTest): Nur solche
# echten Ereignisse reicht Qt an die Eltern weiter, ein mit sendEvent
# geschicktes nicht. Geprüft wird nur, wo die Maus das Feld auch trifft.
# Ob das Aufgabenfenster über dem Feld weiterrollt, zeigt eine Gegenprobe mit
# einem Drehfeld ohne unseren Filter: Verstellt es sich, schützt FreeCAD
# nicht selbst (1.1.3) – dann muss unser Feld bleiben und das Fenster rollen.
# Der Wochen-Build schützt Drehfelder selbst (Gui::WheelEventFilter) und
# schluckt das Rad dabei; dort bleibt nur, dass sich nichts verstellt.
import ctypes
import os

import FreeCAD
import FreeCADGui as Gui
from PySide import QtCore, QtGui


class Maus:
    """Das Mausrad des X-Servers, auf dem FreeCAD läuft (Xvfb)."""

    def __init__(self):
        self.x11 = ctypes.cdll.LoadLibrary("libX11.so.6")
        self.xtst = ctypes.cdll.LoadLibrary("libXtst.so.6")
        self.x11.XOpenDisplay.restype = ctypes.c_void_p
        self.x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        self.x11.XFlush.argtypes = [ctypes.c_void_p]
        self.xtst.XTestFakeMotionEvent.argtypes = [ctypes.c_void_p] + [ctypes.c_int] * 3
        self.xtst.XTestFakeMotionEvent.argtypes.append(ctypes.c_ulong)
        self.xtst.XTestFakeButtonEvent.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_int,
            ctypes.c_ulong,
        ]
        self.anzeige = self.x11.XOpenDisplay(os.environ["DISPLAY"].encode())

    def rad(self, widget, rasten=-1):
        """Rasten über der Mitte von `widget` (negativ: zu sich hin); wartet, bis Qt sie hat."""
        mitte = widget.mapToGlobal(QtCore.QPoint(widget.width() // 2, widget.height() // 2))
        self.xtst.XTestFakeMotionEvent(self.anzeige, -1, mitte.x(), mitte.y(), 0)
        knopf = 5 if rasten < 0 else 4  # X11: 4 rollt weg, 5 zu sich hin
        for _ in range(abs(rasten)):
            self.xtst.XTestFakeButtonEvent(self.anzeige, knopf, 1, 0)
            self.xtst.XTestFakeButtonEvent(self.anzeige, knopf, 0, 0)
        self.x11.XFlush(self.anzeige)
        yield 400


def trifft(widget):
    """Liegt `widget` (oder etwas in ihm) unter seiner Mitte – kommt die Raste dort an?"""
    mitte = widget.mapToGlobal(QtCore.QPoint(widget.width() // 2, widget.height() // 2))
    unter = QtGui.QApplication.widgetAt(mitte)
    return unter is not None and (unter is widget or widget.isAncestorOf(unter))


def fokus(widget):
    """Fokus wie nach einem Klick ins Feld."""
    widget.window().activateWindow()
    QtGui.QApplication.setActiveWindow(widget.window())
    widget.setFocus(QtCore.Qt.MouseFocusReason)
    QtGui.QApplication.processEvents()
    return widget.hasFocus()


def wert(widget):
    return widget.currentIndex() if isinstance(widget, QtGui.QComboBox) else widget.value()


def schritte(h):
    yield 500
    maus = Maus()
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        # Auch hier: Das Rad über der Liste wechselt die Sprache nicht.
        vorher = erster.liste.currentIndex()
        yield from maus.rad(erster.liste)
        h.pruefe(erster.liste.currentIndex() == vorher, "Rad wechselt die Sprache")
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine, gui_maschine, gui_verfahren, gui_werkzeuge

    # Werkzeugverwaltung: Art und Nummer verstellt das Rad nur nach einem Klick.
    Gui.runCommand("CamAddon_Werkzeugverwaltung")
    yield 800
    d = gui_werkzeuge.WerkzeugDialog.offen
    h.pruefe(d is not None, "Werkzeugverwaltung geht nicht auf")
    if d is None:
        return
    d.knopf_neu.click()
    yield 300
    fokus(d.feld_bezeichnung)  # der Fokus ist woanders
    for feld in (d.feld_art, d.feld_nummer):
        vorher = wert(feld)
        yield from maus.rad(feld)
        h.pruefe(wert(feld) == vorher, f"{type(feld).__name__} ohne Fokus verstellt")
    # Nach einem Klick in die Nummer rollt das Rad sie wie gewohnt (T1 → T2).
    h.pruefe(fokus(d.feld_nummer), "Nummer: kein Fokus")
    vorher = d.feld_nummer.value()
    yield from maus.rad(d.feld_nummer, 1)
    h.pruefe(d.feld_nummer.value() == vorher + 1, f"Nummer mit Fokus: {d.feld_nummer.value()}")
    QtCore.QTimer.singleShot(0, d.reject)  # „Speichern?“ blockierte sonst
    yield 500
    frage = h.modal()
    if isinstance(frage, QtGui.QMessageBox):
        frage.button(QtGui.QMessageBox.Discard).click()
    yield 300

    # Maschine bearbeiten: Der Revolverplatz bleibt, das Aufgabenfenster rollt.
    asm, _ma = beispielmaschine.lade(beispielmaschine.DREHMASCHINE)
    yield 500
    Gui.Selection.addSelection(asm)
    Gui.runCommand("CamAddon_MaschineBearbeiten")
    yield from h.warte_auf(lambda: gui_maschine.MaschinenPanel.offen is not None)
    panel = gui_maschine.MaschinenPanel.offen
    h.pruefe(panel is not None, "„Maschine bearbeiten“ geht nicht auf")
    if panel is None:
        return
    treffer = panel.aufnahmen.findItems("P3", QtCore.Qt.MatchStartsWith | QtCore.Qt.MatchRecursive)
    h.pruefe(bool(treffer), "P3 fehlt")
    platz = None
    if treffer:
        panel.aufnahmen.setCurrentItem(treffer[0])
        yield 300
        platz = next(iter(panel.details.findChildren(QtGui.QSpinBox)), None)
        h.pruefe(platz is not None, "kein Feld „Revolverplatz“")
    aufgaben = next(
        (
            b
            for b in Gui.getMainWindow().findChildren(QtGui.QScrollArea)
            if b.isAncestorOf(panel.form)
        ),
        None,
    )
    if platz is not None and aufgaben is not None:
        aufgaben.ensureWidgetVisible(platz)
        yield 300
    freecad_schuetzt = True
    if platz is not None and aufgaben is not None:
        # Gegenprobe: ein Drehfeld ohne unseren Filter, gleich unter dem Revolverplatz.
        probe = QtGui.QSpinBox()
        probe.setRange(0, 100)
        probe.setValue(50)
        probe.setFocusPolicy(QtCore.Qt.StrongFocus)
        panel.details.layout().addWidget(probe)
        yield 300
        aufgaben.ensureWidgetVisible(probe)
        yield 300
        if trifft(probe):
            yield from maus.rad(probe, 1)
            freecad_schuetzt = probe.value() == 50
        probe.hide()
        probe.deleteLater()
        aufgaben.ensureWidgetVisible(platz)
        yield 300
    if platz is not None and aufgaben is not None and trifft(platz):
        rollbalken = aufgaben.verticalScrollBar()
        gerollt = rollbalken.value()
        # Weg vom Ende, an dem das Fenster gerade steht – dann muss es rollen.
        rasten = 3 if gerollt > rollbalken.minimum() else -3
        vorher = platz.value()
        h.bild("1_vor_dem_rad")
        yield from maus.rad(platz, rasten)
        h.pruefe(platz.value() == vorher, f"Revolverplatz verstellt: P{platz.value()}")
        h.pruefe(
            freecad_schuetzt or rollbalken.value() != gerollt,
            f"Aufgabenfenster rollt nicht ({gerollt} → {rollbalken.value()})",
        )
        h.bild("2_nach_dem_rad")
    panel.reject()
    yield 500

    # Maschine verfahren: Regler und Feld fahren die Achse nur nach einem Klick.
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(asm)
    Gui.runCommand("CamAddon_MaschineVerfahren")
    yield from h.warte_auf(lambda: gui_verfahren.VerfahrPanel.offen is not None)
    panel = gui_verfahren.VerfahrPanel.offen
    h.pruefe(panel is not None, "„Maschine verfahren“ geht nicht auf")
    if panel is None:
        return
    x = panel.achse("X1")
    for element in panel.zeilen[x]:
        if not trifft(element):
            continue
        fokus(panel.knopf_grundstellung)  # beim Öffnen hat der erste Regler den Fokus
        vorher = wert(element)
        yield from maus.rad(element)
        fokussiert = QtGui.QApplication.focusWidget()
        h.pruefe(
            wert(element) == vorher,
            f"X1: {type(element).__name__} ohne Fokus verstellt ({vorher} → {wert(element)};"
            f" Fokus: {type(fokussiert).__name__ if fokussiert else None})",
        )
    h.bild("3_verfahren_nach_dem_rad")
    panel.reject()
    yield 500
    for name in list(FreeCAD.listDocuments()):
        FreeCAD.closeDocument(name)
    yield 300
