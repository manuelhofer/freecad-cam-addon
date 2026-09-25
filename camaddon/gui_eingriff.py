# SPDX-License-Identifier: LGPL-2.1-or-later
"""Das Bild des Eingriffs zur gewählten Zeile der Schnittwerte (W-002, Abschnitt 6.2).

Links die Draufsicht: der Fräser, das Material daneben und der Bogen, über
den jeder Zahn im Material ist (rot). Rechts die Seitenansicht: die Schneide
und der Teil, der bei diesem ap arbeitet (rot). Das Bild ändert sich beim
Tippen und enthält keinen Text, damit es in jeder Sprache passt
(Arbeitsregeln, Abschnitt 8).
"""

import math

from PySide import QtCore, QtGui

from . import schnittdaten as sd

BREITE, HOEHE = 330, 150  # Pixel
RAND = 12  # Pixel

FARBE_MATERIAL = QtGui.QColor("#c9c9c9")
FARBE_KANTE = QtGui.QColor("#8a8a8a")
FARBE_WERKZEUG = QtGui.QColor("#729fcf")
FARBE_WERKZEUG_RAND = QtGui.QColor("#204a87")
FARBE_SCHAFT = QtGui.QColor("#d3d7cf")
FARBE_EINGRIFF = QtGui.QColor("#cc0000")
FARBE_PFEIL = QtGui.QColor("#555753")


class EingriffBild(QtGui.QWidget):
    """Zeigt ae, ap und den Eingriffswinkel eines Einsatzes; `zeige()` setzt die Werte."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(BREITE, HOEHE)
        self.durchmesser = 0.0
        self.schneidenlaenge = 0.0
        self.ae = 0.0
        self.ap = 0.0

    def zeige(self, durchmesser, schneidenlaenge, ae, ap):
        """Neue Werte (mm); 0 heißt unbekannt – dann bleibt das jeweilige Bild leer."""
        self.durchmesser, self.schneidenlaenge = durchmesser, schneidenlaenge
        self.ae, self.ap = ae, ap
        self.update()

    def paintEvent(self, _ereignis):
        maler = QtGui.QPainter(self)
        maler.setRenderHint(QtGui.QPainter.Antialiasing)
        maler.fillRect(self.rect(), self.palette().color(QtGui.QPalette.Base))
        if self.durchmesser > 0:
            halb = BREITE // 2
            self._draufsicht(maler, QtCore.QRectF(0, 0, halb, HOEHE))
            self._seitenansicht(maler, QtCore.QRectF(halb, 0, BREITE - halb, HOEHE))
        maler.end()

    # --- Draufsicht -----------------------------------------------------------------

    def _draufsicht(self, maler, feld):
        """Fräser von oben, Vorschub nach oben, Material rechts (bei Vollnut beidseits)."""
        r = (feld.height() - 2 * RAND) * 0.36
        mitte = QtCore.QPointF(feld.left() + feld.width() * 0.42, feld.center().y() + 6)
        ae = min(self.ae, self.durchmesser) / self.durchmesser * 2 * r  # in Pixeln
        oben, unten = feld.top() + RAND, feld.bottom() - RAND
        links, rechts = feld.left() + RAND, feld.right() - RAND
        vollnut = self.ae >= self.durchmesser

        maler.setPen(QtCore.Qt.NoPen)
        maler.setBrush(FARBE_MATERIAL)
        if ae > 0:
            # Vor dem Fräser steht das Material noch bis ae an, dahinter ist die
            # neue Wand bei der Schneide – bei der Vollnut auf beiden Seiten.
            anfang = mitte.x() + r - ae
            maler.drawRect(QtCore.QRectF(anfang, oben, rechts - anfang, mitte.y() - oben))
            maler.drawRect(
                QtCore.QRectF(mitte.x() + r, mitte.y(), rechts - mitte.x() - r, unten - mitte.y())
            )
            if vollnut:
                maler.drawRect(QtCore.QRectF(links, oben, mitte.x() - r - links, unten - oben))

        maler.setPen(QtGui.QPen(FARBE_WERKZEUG_RAND, 1.5))
        maler.setBrush(FARBE_WERKZEUG)
        maler.drawEllipse(mitte, r, r)

        phi = math.degrees(sd.eingriffswinkel(self.ae, self.durchmesser))
        if phi > 0:
            kreis = QtCore.QRectF(mitte.x() - r, mitte.y() - r, 2 * r, 2 * r)
            maler.setPen(_dicker_stift())
            maler.setBrush(QtCore.Qt.NoBrush)
            # Qt zählt Winkel in 1/16 Grad, ab 3 Uhr gegen den Uhrzeigersinn –
            # genau der Weg eines Zahns ins Material bei Vorschub nach oben.
            maler.drawArc(kreis, 0, int(phi * 16))

        # Vorschubrichtung.
        maler.setPen(QtGui.QPen(FARBE_PFEIL, 2))
        spitze = QtCore.QPointF(mitte.x(), oben + 2)
        maler.drawLine(QtCore.QPointF(mitte.x(), mitte.y() - r - 6), spitze)
        _spitze(maler, spitze, oben=True)

    # --- Seitenansicht ------------------------------------------------------------------

    def _seitenansicht(self, maler, feld):
        """Fräser von der Seite, Werkstück rechts daneben mit der Höhe ap."""
        d = self.durchmesser
        laenge = self.schneidenlaenge or max(self.ap, d)  # unbekannt: so lang wie nötig
        gesamt = max(laenge * 1.5, self.ap * 1.15, 2 * d)  # was ins Bild muss, in mm
        massstab = (feld.height() - 2 * RAND) / gesamt
        breite = min(d * massstab, feld.width() * 0.3)
        links = feld.left() + feld.width() * 0.25
        boden = feld.bottom() - RAND
        oben = feld.top() + RAND

        # Werkstück: rechts vom Fräser, so hoch wie ap.
        ap = self.ap * massstab
        maler.setPen(QtCore.Qt.NoPen)
        maler.setBrush(FARBE_MATERIAL)
        if ap > 0:
            maler.drawRect(
                QtCore.QRectF(links + breite, boden - ap, feld.right() - RAND - links - breite, ap)
            )

        # Schaft und Schneide.
        schneide = laenge * massstab
        maler.setPen(QtGui.QPen(FARBE_KANTE, 1))
        maler.setBrush(FARBE_SCHAFT)
        maler.drawRect(QtCore.QRectF(links, oben, breite, boden - schneide - oben))
        stift = QtGui.QPen(FARBE_WERKZEUG_RAND, 1.5)
        if not self.schneidenlaenge:
            stift.setStyle(QtCore.Qt.DashLine)
        maler.setPen(stift)
        maler.setBrush(FARBE_WERKZEUG)
        maler.drawRect(QtCore.QRectF(links, boden - schneide, breite, schneide))
        # Gewendelte Schneiden andeuten.
        schritt = max(breite * 0.8, 6)
        y = boden - schritt
        while y > boden - schneide:
            maler.drawLine(
                QtCore.QPointF(links, y + schritt * 0.5), QtCore.QPointF(links + breite, y)
            )
            y -= schritt

        # Der arbeitende Teil der Schneide.
        if ap > 0:
            maler.setPen(_dicker_stift())
            x = links + breite - 2
            maler.drawLine(QtCore.QPointF(x, boden), QtCore.QPointF(x, boden - ap))


def _dicker_stift():
    """Der rote Strich für den Eingriff: breit, mit geraden Enden."""
    stift = QtGui.QPen(FARBE_EINGRIFF, 5)
    stift.setCapStyle(QtCore.Qt.FlatCap)
    return stift


def _spitze(maler, punkt, oben):
    """Pfeilspitze an `punkt`, nach oben oder unten."""
    richtung = 1 if oben else -1
    maler.setBrush(FARBE_PFEIL)
    maler.drawPolygon(
        QtGui.QPolygonF(
            [
                punkt,
                QtCore.QPointF(punkt.x() - 5, punkt.y() + 8 * richtung),
                QtCore.QPointF(punkt.x() + 5, punkt.y() + 8 * richtung),
            ]
        )
    )
