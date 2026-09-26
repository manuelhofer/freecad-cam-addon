# SPDX-License-Identifier: LGPL-2.1-or-later
"""Das Bild des Werkzeugs neben seinen Feldern in der Werkzeugverwaltung (W-002).

Jede Art als Umriss aus ihren Maßen (werkzeugform.py), im richtigen
Verhältnis: Kugel, Eckradius, Kegel, Hals, Gewindezähne, Senkung,
Wendeplatte am Halter, Tastkugel. Was nicht eingetragen ist – geschätzt
(Gesamtlänge, Schaft, Schneidenlänge) oder noch Beispielwert –, ist
gestrichelt. Fehlen die Maße, zeigt es die Form der Art mit ihren
Beispielmaßen, damit man beim Durchblättern immer sieht, was für ein
Werkzeug es ist. So sieht man beim Tippen, ob die Maße zusammenpassen. Ohne
Text, damit es in jeder Sprache passt (Arbeitsregeln, Abschnitt 8). Klein
gemalt ist es das Symbol der Art in der Auswahl (symbol()).
"""

import copy

from PySide import QtCore, QtGui

from . import werkzeuge as wz
from . import werkzeugform as wf
from .gui_eingriff import FARBE_KANTE, FARBE_SCHAFT, FARBE_WERKZEUG, FARBE_WERKZEUG_RAND

BREITE, HOEHE = 90, 140  # Pixel – so hoch wie die Felder daneben
RAND = 8  # Pixel
# Tastkugeln sind meist aus Rubin.
FARBE_TASTKUGEL = QtGui.QColor("#cc0000")
FARBE_TASTKUGEL_RAND = QtGui.QColor("#7a0000")
FARBEN = {  # Teil -> (Füllung, Rand)
    wf.SCHAFT: (FARBE_SCHAFT, FARBE_KANTE),
    wf.SCHNEIDE: (FARBE_WERKZEUG, FARBE_WERKZEUG_RAND),
    wf.KUGEL: (FARBE_TASTKUGEL, FARBE_TASTKUGEL_RAND),
}


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
            muster, fremd = mit_beispielmassen(self.werkzeug)
            zeichne(maler, wf.teile(muster, fremd), QtCore.QRectF(self.rect()), RAND)
        maler.end()


def zeichne(maler, teile, rechteck, rand, klein=False):
    """Malt die Teile eingepasst und mittig ins Rechteck; `klein`: als Symbol, ohne Striche
    und ohne Spannuten."""
    if not teile:
        return
    x0, y0, x1, y1 = wf.grenzen(teile)
    breite = max(x1 - x0, 1e-6)
    if klein:
        # Im Symbol nur das schneidende Ende – lang und dünn wäre es ein Strich.
        y1 = min(y1, y0 + 1.6 * breite)
        maler.save()
        maler.setClipRect(rechteck)
    hoehe = max(y1 - y0, 1e-6)
    massstab = min((rechteck.width() - 2 * rand) / breite, (rechteck.height() - 2 * rand) / hoehe)
    # Mittig; y wächst im Bild nach unten, im Werkzeug nach oben (zum Schaft).
    links = rechteck.left() + (rechteck.width() - breite * massstab) / 2
    unten = rechteck.top() + (rechteck.height() + hoehe * massstab) / 2

    def punkt(x, y):
        return QtCore.QPointF(links + (x - x0) * massstab, unten - (y - y0) * massstab)

    for teil in teile:
        umriss = QtGui.QPolygonF([punkt(x, y) for x, y in teil.punkte])
        fuellung, rand_farbe = FARBEN[teil.stoff]
        stift = QtGui.QPen(rand_farbe, 1.0 if klein else 1.5)
        if teil.geschaetzt and not klein:
            stift.setStyle(QtCore.Qt.DashLine)
        maler.setPen(stift)
        maler.setBrush(fuellung)
        maler.drawPolygon(umriss)
        if teil.wendel and not klein:
            _wendel(maler, umriss, teil.wendel)
    if klein:
        maler.restore()


def _wendel(maler, umriss, wendel):
    """Spannuten andeuten – nur innerhalb des Umrisses: schräg wie eine Rechts- oder
    Linkswendel, bei der Reibahle gerade."""
    kasten = umriss.boundingRect()
    pfad = QtGui.QPainterPath()
    pfad.addPolygon(umriss)
    maler.save()
    maler.setClipPath(pfad)
    if wendel == wf.WENDEL_GERADE:
        for anteil in (0.3, 0.7):
            x = kasten.left() + kasten.width() * anteil
            maler.drawLine(QtCore.QPointF(x, kasten.top()), QtCore.QPointF(x, kasten.bottom()))
    else:
        schritt = max(kasten.width() * 0.8, 6.0)
        steigt = schritt * 0.5 if wendel == wf.WENDEL_RECHTS else -schritt * 0.5
        y = kasten.bottom() - schritt * 0.3
        while y > kasten.top() - schritt:
            maler.drawLine(
                QtCore.QPointF(kasten.left(), y + steigt), QtCore.QPointF(kasten.right(), y)
            )
            y -= schritt
    maler.restore()


def mit_beispielmassen(werkzeug):
    """(Werkzeug zum Zeichnen, Maße, die nicht eingetragen sind).

    Fehlt das Maß, nach dem sich alles richtet (der Durchmesser – bei
    Drehwerkzeugen gibt es keinen), eine Kopie, deren leere Maße die Beispiele
    der Art sind; sonst das Werkzeug selbst mit seinen noch grauen
    Beispielfeldern.
    """
    fremd = set(werkzeug.beispiel)
    if wz.hat_feld(werkzeug, "durchmesser") and werkzeug.durchmesser > 0:
        return werkzeug, fremd
    muster = copy.copy(werkzeug)
    for feld, wert in wz.beispiele(werkzeug.art).items():
        if not getattr(muster, feld):
            setattr(muster, feld, wert)
            fremd.add(feld)
    return muster, fremd


def symbol(art, groesse=24):
    """Das Bild der Art mit ihren Beispielmaßen als kleines Symbol – für die Auswahl."""
    muster = wz.Werkzeug(art=art)
    wz.beispielwerte_setzen(muster, neu=True)
    bild = QtGui.QPixmap(groesse, groesse)
    bild.fill(QtCore.Qt.transparent)
    maler = QtGui.QPainter(bild)
    maler.setRenderHint(QtGui.QPainter.Antialiasing)
    zeichne(maler, wf.teile(muster), QtCore.QRectF(0, 0, groesse, groesse), 1, klein=True)
    maler.end()
    return QtGui.QIcon(bild)
