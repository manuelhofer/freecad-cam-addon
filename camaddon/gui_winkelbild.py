# SPDX-License-Identifier: LGPL-2.1-or-later
"""Das Bild zur schrägen Achse im Dialog „Maschine bearbeiten“ (W-001, Abschnitt 7c).

Die ausgleichende Achse (X1) nach rechts, gestrichelt der rechte Winkel
darauf – dorthin zeigt das Y des Programms –, und die schräge Achse (Y1),
um α daraus gekippt, mit dem Bogen für α. Positiv kippt sie nach rechts, zur
Plus-Seite von X1. So sieht man, welcher Winkel gemeint ist und in welche
Richtung er zählt. Beschriftet ist nur mit Achsnamen, die in jeder Sprache
gleich sind.
"""

import math

from PySide import QtCore, QtGui

BREITE, HOEHE = 260, 130  # Pixel
RAND = 14  # Pixel
PFEILSPITZE = 7  # Pixel
WINKELMARKE = 9  # Pixel, Kantenlänge des Quadrats für den rechten Winkel
BOGEN = 34  # Pixel, Halbmesser des Bogens für α
# Steilere Winkel zeichnet das Bild flacher – sonst läge Y1 auf X1.
GEZEICHNET_BIS = 75.0  # Grad

FARBE_SCHRAEG = QtGui.QColor("#204a87")
FARBE_WINKEL = QtGui.QColor("#ce5c00")


class WinkelBild(QtGui.QWidget):
    """X1, der rechte Winkel darauf und Y1 um `alpha` Grad gekippt (None: unbekannt)."""

    def __init__(self, alpha, schraeg, ausgleich, programmname):
        super().__init__()
        self.setFixedSize(BREITE, HOEHE)
        self.alpha = alpha
        self.schraeg, self.ausgleich, self.programmname = schraeg, ausgleich, programmname

    def paintEvent(self, _ereignis):
        maler = QtGui.QPainter(self)
        maler.setRenderHint(QtGui.QPainter.Antialiasing)
        maler.fillRect(self.rect(), self.palette().color(QtGui.QPalette.Base))
        schrift = self.palette().color(QtGui.QPalette.Text)
        ursprung = QtCore.QPointF(BREITE / 2 - 20, HOEHE - RAND - 8)
        laenge = ursprung.y() - RAND - 6

        # Die ausgleichende Achse nach rechts.
        _pfeil(maler, ursprung, QtCore.QPointF(BREITE - RAND - 16, ursprung.y()), schrift)
        maler.drawText(QtCore.QPointF(BREITE - RAND - 14, ursprung.y() + 4), self.ausgleich)

        # Der rechte Winkel darauf, gestrichelt – dorthin zeigt das Y des Programms.
        grau = QtGui.QColor(schrift)
        grau.setAlpha(130)
        stift = QtGui.QPen(grau, 1.2, QtCore.Qt.DashLine)
        maler.setPen(stift)
        oben = QtCore.QPointF(ursprung.x(), ursprung.y() - laenge)
        maler.drawLine(ursprung, oben)
        maler.drawText(QtCore.QPointF(oben.x() - 18, oben.y() + 10), self.programmname)
        maler.setPen(QtGui.QPen(grau, 1.0))
        maler.drawRect(
            QtCore.QRectF(ursprung.x(), ursprung.y() - WINKELMARKE, WINKELMARKE, WINKELMARKE)
        )
        if self.alpha is None:
            maler.end()
            return

        # Die schräge Achse, um α aus dem rechten Winkel gekippt (positiv nach rechts).
        gezeichnet = max(-GEZEICHNET_BIS, min(GEZEICHNET_BIS, self.alpha))
        bogenmass = math.radians(gezeichnet)
        spitze = QtCore.QPointF(
            ursprung.x() + laenge * math.sin(bogenmass),
            ursprung.y() - laenge * math.cos(bogenmass),
        )
        _pfeil(maler, ursprung, spitze, FARBE_SCHRAEG, breite=2.0)
        maler.setPen(FARBE_SCHRAEG)
        maler.drawText(QtCore.QPointF(spitze.x() + 6, spitze.y() + 12), self.schraeg)

        # Der Bogen für α zwischen dem rechten Winkel und der schrägen Achse.
        if abs(self.alpha) >= 0.05:
            maler.setPen(QtGui.QPen(FARBE_WINKEL, 1.6))
            kasten = QtCore.QRectF(ursprung.x() - BOGEN, ursprung.y() - BOGEN, 2 * BOGEN, 2 * BOGEN)
            # Qt zählt Winkel in 1/16 Grad, 0 nach rechts, positiv gegen den Uhrzeigersinn.
            maler.drawArc(kasten, 90 * 16, int(-gezeichnet * 16))
            mitte = math.radians(gezeichnet / 2)
            marke = QtCore.QPointF(
                ursprung.x() + (BOGEN + 10) * math.sin(mitte) - 4,
                ursprung.y() - (BOGEN + 10) * math.cos(mitte) + 4,
            )
            maler.drawText(marke, "α")
        maler.end()


def _pfeil(maler, von, nach, farbe, breite=1.4):
    """Linie von `von` nach `nach` mit Spitze bei `nach`."""
    maler.setPen(QtGui.QPen(farbe, breite))
    maler.setBrush(farbe)
    maler.drawLine(von, nach)
    richtung = math.atan2(nach.y() - von.y(), nach.x() - von.x())
    spitze = QtGui.QPolygonF(
        [
            nach,
            QtCore.QPointF(
                nach.x() - PFEILSPITZE * math.cos(richtung - 0.4),
                nach.y() - PFEILSPITZE * math.sin(richtung - 0.4),
            ),
            QtCore.QPointF(
                nach.x() - PFEILSPITZE * math.cos(richtung + 0.4),
                nach.y() - PFEILSPITZE * math.sin(richtung + 0.4),
            ),
        ]
    )
    maler.drawPolygon(spitze)
    maler.setBrush(QtCore.Qt.NoBrush)
