# SPDX-License-Identifier: LGPL-2.1-or-later
"""Kleine Bausteine, die die Dialoge des Addons teilen.

Fette Beschriftung für Pflichtfelder, Knopf, Feld mit Einheit, rote
Hinweiszeile und das Grau für gerechnete oder geerbte Werte – einmal hier,
damit jeder Dialog gleich aussieht (P-2026-09-25-54). Dazu das ruhige
Mausrad: Auswahllisten, Drehfelder und Regler verstellt es nur, wenn sie den
Fokus haben (ruhiges_mausrad) – und blaettere_zu, das einen Abschnitt im
Aufgabenbereich nach oben holt.
"""

import contextlib

from PySide import QtCore, QtGui

GRAU = QtGui.QColor("#6d6d6d")  # gerechnete oder geerbte Werte
ROT = "#c0392b"  # Hinweise, was fehlt oder nicht passt


def fett(text):
    """Beschriftung in Fettschrift – so sind Pflichtfelder markiert."""
    beschriftung = QtGui.QLabel(text)
    schrift = beschriftung.font()
    schrift.setBold(True)
    beschriftung.setFont(schrift)
    return beschriftung


def knopf(text, tooltip, aktion):
    """Knopf, der `aktion()` ohne Argument aufruft; Enter in einem Feld löst ihn nicht aus."""
    k = QtGui.QPushButton(text)
    k.setToolTip(tooltip)
    k.setAutoDefault(False)
    k.clicked.connect(lambda: aktion())
    return k


def mit_einheit(feld, einheit):
    """Feld mit der Einheit rechts daneben; `zeile.einheit` ist die Beschriftung der Einheit
    (für den Wechsel zwischen mm und inch)."""
    zeile = QtGui.QWidget()
    aufbau = QtGui.QHBoxLayout(zeile)
    aufbau.setContentsMargins(0, 0, 0, 0)
    aufbau.addWidget(feld)
    zeile.einheit = QtGui.QLabel(einheit)
    aufbau.addWidget(zeile.einheit)
    return zeile


def hinweiszeile(text=""):
    """Rote Zeile unter den Feldern: was fehlt oder nicht passt, als Satz."""
    zeile = QtGui.QLabel(text)
    zeile.setWordWrap(True)
    zeile.setStyleSheet(f"color: {ROT};")
    zeile.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
    return zeile


def blaettere_zu(widget):
    """Blättert den umgebenden Rollbereich – etwa den Aufgabenbereich –, bis `widget` oben
    steht, oder so weit es geht."""
    bereich = widget.parentWidget()
    while bereich is not None and not isinstance(bereich, QtGui.QScrollArea):
        bereich = bereich.parentWidget()
    if bereich is None or bereich.widget() is None:
        return
    bereich.verticalScrollBar().setValue(widget.mapTo(bereich.widget(), QtCore.QPoint()).y())


def grau(text):
    """Tabellenzelle in Grau – für gerechnete oder geerbte Werte."""
    zelle = QtGui.QTableWidgetItem(text)
    zelle.setForeground(GRAU)
    return zelle


class _RadNurMitFokus(QtCore.QObject):
    """Das Mausrad verstellt ein Feld nur, wenn es den Fokus hat.

    Sonst verstellt man beim Blättern im Aufgabenfenster oder in einer
    Tabelle aus Versehen einen Wert – so kam wohl das „P10“ in Manuels
    Revolverplatz (P-2026-09-26-52). Das Rad geht dann an den Rollbalken des
    Bereichs darüber: Aufgabenfenster oder Tabelle blättern weiter. Selbst
    weitergereicht – im Wochen-Build rollte das Aufgabenfenster sonst nicht.
    """

    def eventFilter(self, feld, ereignis):
        if ereignis.type() != QtCore.QEvent.Wheel or feld.hasFocus():
            return False
        balken = _rollbalken_darueber(feld, ereignis.angleDelta())
        if balken is None:
            ereignis.ignore()  # nichts zu blättern
            return True
        # Geht der Bereich gerade zu, ist sein Rollbalken schon weg – das Feld bekommt das
        # Rad trotzdem nicht.
        with contextlib.suppress(RuntimeError):
            QtCore.QCoreApplication.sendEvent(balken, ereignis)
        ereignis.accept()  # erledigt – nicht noch einmal über die Eltern
        return True


def _rollbalken_darueber(feld, delta):
    """Der Rollbalken des nächsten Bereichs über `feld`, der in Richtung des Rads rollen kann.

    Ein Rollbereich ohne Weg (etwa einer, in den alles passt) zählt nicht.
    """
    senkrecht = abs(delta.y()) >= abs(delta.x())
    bereich = feld.parentWidget()
    while bereich is not None:
        if isinstance(bereich, QtGui.QAbstractScrollArea):
            balken = bereich.verticalScrollBar() if senkrecht else bereich.horizontalScrollBar()
            if balken.maximum() > balken.minimum():
                return balken
        bereich = bereich.parentWidget()
    return None


class RuhigerRegler(QtGui.QSlider):
    """Schieberegler, den das Mausrad nur mit Fokus bewegt – auch dort, wo das Rad
    am Filter vorbei zugestellt wird (im Wochen-Build im Aufgabenfenster)."""

    def wheelEvent(self, ereignis):
        if self.hasFocus():
            super().wheelEvent(ereignis)
        else:
            ereignis.ignore()


_rad = None  # der eine Filter für alle Felder
# Regler ja, Rollbalken nicht (auch sie sind QAbstractSlider) – die sollen blättern.
_MIT_RAD = (QtGui.QComboBox, QtGui.QAbstractSpinBox, QtGui.QSlider)


def ruhiges_mausrad(wurzel):
    """Auswahllisten, Drehfelder und Regler in `wurzel` (und `wurzel` selbst) nehmen
    das Mausrad nur mit Fokus; gibt `wurzel` zurück.

    Auch den Fokus bekommen sie nicht mehr vom Rad, nur von einem Klick oder
    der Tabulatortaste – danach rollt das Rad den Wert wie gewohnt. Für
    Felder, die später dazukommen, noch einmal aufrufen.
    """
    global _rad
    if _rad is None:
        _rad = _RadNurMitFokus()
    felder = [wurzel] if isinstance(wurzel, _MIT_RAD) else []
    for art in _MIT_RAD:
        felder += wurzel.findChildren(art)
    for feld in felder:
        feld.setFocusPolicy(QtCore.Qt.StrongFocus)
        feld.installEventFilter(_rad)
    return wurzel
