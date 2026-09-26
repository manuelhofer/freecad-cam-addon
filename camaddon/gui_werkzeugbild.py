# SPDX-License-Identifier: LGPL-2.1-or-later
"""Das Bild des Werkzeugs neben seinen Feldern in der Werkzeugverwaltung (W-002).

Schaft, Schneide und Spitze je nach Art – Schaftfräser flach, Torusfräser
mit Eckradius, Radiusfräser mit Kugel, Fasenfräser spitz, Bohrer mit seinem
Spitzenwinkel (leer 118°) –, alles im richtigen Verhältnis. Was nicht eingetragen ist –
geschätzt (Gesamtlänge, Schaft, Schneidenlänge) oder noch Beispielwert –,
ist gestrichelt. Fehlt der Durchmesser, zeigt es die Form der Art mit ihren
Beispielmaßen, damit man beim Durchblättern immer sieht, was für ein
Werkzeug es ist. So sieht man beim Tippen, ob die Maße zusammenpassen. Ohne
Text, damit es in jeder Sprache passt (Arbeitsregeln, Abschnitt 8).
"""

import copy
import math

from PySide import QtCore, QtGui

from . import werkzeuge as wz
from .gui_eingriff import FARBE_KANTE, FARBE_SCHAFT, FARBE_WERKZEUG, FARBE_WERKZEUG_RAND

BREITE, HOEHE = 90, 140  # Pixel – so hoch wie die Felder daneben
RAND = 8  # Pixel
FASENWINKEL = 90.0  # Grad


class WerkzeugBild(QtGui.QWidget):
    """Zeigt ein Werkzeug maßstäblich; `zeige(werkzeug)` setzt es (None = leer)."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(BREITE, HOEHE)
        self.werkzeug = None

    def zeige(self, werkzeug):
        self.werkzeug = werkzeug
        self.update()

    def paintEvent(self, _ereignis):
        maler = QtGui.QPainter(self)
        maler.setRenderHint(QtGui.QPainter.Antialiasing)
        maler.fillRect(self.rect(), self.palette().color(QtGui.QPalette.Base))
        if self.werkzeug is not None:
            self._zeichne(maler, *mit_beispielmassen(self.werkzeug))
        maler.end()

    def _zeichne(self, maler, w, fremd):
        d = w.durchmesser
        schneide = w.schneidenlaenge or 2 * d
        laenge = max(wz.laenge_fuer_cam(w), schneide)
        schaft = wz.schaft_fuer_cam(w)
        massstab = min((HOEHE - 2 * RAND) / laenge, (BREITE - 2 * RAND) / max(d, schaft))
        mitte = BREITE / 2
        boden = RAND + laenge * massstab
        oben = RAND
        halb_d = d * massstab / 2
        halb_schaft = schaft * massstab / 2
        unten_schneide = boden
        oben_schneide = boden - schneide * massstab

        # Schaft: von oben bis zur Schneide.
        maler.setPen(
            _stift(FARBE_KANTE, geschaetzt=not (w.gesamtlaenge and w.schaft) or bool(fremd))
        )
        maler.setBrush(FARBE_SCHAFT)
        maler.drawRect(
            QtCore.QRectF(mitte - halb_schaft, oben, 2 * halb_schaft, oben_schneide - oben)
        )

        # Schneide mit der Spitze der Art.
        umriss = self._schneide(w, mitte, halb_d, oben_schneide, unten_schneide, massstab)
        # Die Schneidenzahl ändert das Bild nicht.
        maler.setPen(
            _stift(
                FARBE_WERKZEUG_RAND, geschaetzt=not w.schneidenlaenge or bool(fremd - {"schneiden"})
            )
        )
        maler.setBrush(FARBE_WERKZEUG)
        maler.drawPath(umriss)
        # Gewendelte Schneiden andeuten – nur im geraden Teil.
        maler.save()
        maler.setClipPath(umriss)
        schritt = max(halb_d * 1.6, 6)
        y = unten_schneide - schritt * 0.3
        while y > oben_schneide:
            maler.drawLine(
                QtCore.QPointF(mitte - halb_d, y + schritt * 0.5), QtCore.QPointF(mitte + halb_d, y)
            )
            y -= schritt
        maler.restore()

    def _schneide(self, w, mitte, halb_d, oben, unten, massstab):
        """Der Umriss der Schneide als Pfad, unten mit der Spitze der Art."""
        pfad = QtGui.QPainterPath()
        links, rechts = mitte - halb_d, mitte + halb_d
        if w.art == wz.RADIUSFRAESER:
            spitze = min(halb_d, unten - oben)
        elif w.art == wz.FASENFRAESER:
            spitze = min(halb_d / math.tan(math.radians(FASENWINKEL / 2)), unten - oben)
        elif w.art == wz.BOHRER:
            winkel = wz.spitzenwinkel_fuer_cam(w)
            spitze = min(halb_d / math.tan(math.radians(winkel / 2)), unten - oben)
        elif w.art == wz.TORUSFRAESER:
            spitze = min((w.eckradius or w.durchmesser / 10) * massstab, halb_d, unten - oben)
        else:
            spitze = 0.0
        pfad.moveTo(links, oben)
        pfad.lineTo(rechts, oben)
        pfad.lineTo(rechts, unten - spitze)
        if w.art == wz.RADIUSFRAESER:
            pfad.arcTo(QtCore.QRectF(links, unten - 2 * spitze, 2 * halb_d, 2 * spitze), 0, -180)
        elif w.art == wz.TORUSFRAESER and spitze > 0:
            pfad.arcTo(
                QtCore.QRectF(rechts - 2 * spitze, unten - 2 * spitze, 2 * spitze, 2 * spitze),
                0,
                -90,
            )
            pfad.lineTo(links + spitze, unten)
            pfad.arcTo(QtCore.QRectF(links, unten - 2 * spitze, 2 * spitze, 2 * spitze), -90, -90)
        elif w.art in (wz.FASENFRAESER, wz.BOHRER):
            pfad.lineTo(mitte, unten)
            pfad.lineTo(links, unten - spitze)
        else:
            pfad.lineTo(rechts, unten)
            pfad.lineTo(links, unten)
        pfad.lineTo(links, oben)
        pfad.closeSubpath()
        return pfad


def mit_beispielmassen(werkzeug):
    """(Werkzeug zum Zeichnen, Maße, die nicht eingetragen sind).

    Ohne Durchmesser eine Kopie, deren leere Maße die Beispiele der Art sind;
    sonst das Werkzeug selbst mit seinen noch grauen Beispielfeldern.
    """
    fremd = set(werkzeug.beispiel)
    if werkzeug.durchmesser > 0:
        return werkzeug, fremd
    muster = copy.copy(werkzeug)
    for feld, wert in wz.beispiele(werkzeug.art).items():
        if not getattr(muster, feld):
            setattr(muster, feld, wert)
            fremd.add(feld)
    return muster, fremd


def _stift(farbe, geschaetzt):
    """Durchgezogen für eingetragene, gestrichelt für geschätzte Maße."""
    stift = QtGui.QPen(farbe, 1.5)
    if geschaetzt:
        stift.setStyle(QtCore.Qt.DashLine)
    return stift
