# SPDX-License-Identifier: LGPL-2.1-or-later
"""Abfahren (W-001, Stufe 4b): die Körper in der 3D-Ansicht und der Abspieler.

Werkzeug, Rohteil, Modell und Bahn sind Coin-Knoten in der 3D-Ansicht der
Maschine – nichts davon steht im Dokument (spezifikation_simulation.md, 4b).
Das Werkzeug hängt an der Werkzeugaufnahme der laufenden Operation, das
Werkstück dort, wo der Nullpunkt des Jobs liegt; beide folgen der Maschine
(Bild.folge). Der Abspieler ist ein Bereich im Fenster „Auf der Maschine
prüfen“ (gui_reichweite.py): Operation, Anfang, Punkt zurück, Abspielen,
Punkt vor, Tempo, Schieber – darunter, wo die Bahn gerade ist, und die
Stellung jeder Achse, rot am Anschlag. Gerechnet wird in abfahren.py.
"""

import html
import math

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import kollision as kb
from . import maschine as m
from . import reichweite as rw
from .abfahren import zeit_text
from .gui_hilfe import kopfzeile
from .gui_teile import GRAU, ROT
from .kette import LINEAR
from .sprache import tr
from .verfahren import namen

TAKT = 40  # ms je Bild beim Abspielen
TEMPI = (1, 5, 20, 100)
SCHIEBER_SCHRITTE = 10000
# Farben (r, g, b) von 0 bis 1.
SCHNEIDE = (0.95, 0.75, 0.10)
SCHAFT = (0.62, 0.62, 0.65)
HALTER = (0.35, 0.35, 0.40)  # angedeutet, ohne Halter aus der Werkzeugverwaltung
HALTER_ECHT = (0.60, 0.63, 0.67)  # der Halter mit seiner Kontur
ROHTEIL = (0.85, 0.65, 0.35)
MODELL = (0.45, 0.60, 0.80)
VORSCHUB_LINIE = (0.10, 0.35, 0.90)
EILGANG_LINIE = (0.90, 0.15, 0.10)
HALTER_MINDESTENS = 25.0  # mm Ø des angedeuteten Halters
HINSEHEN_RAND = 1.3  # so viel mehr als Werkstück und Werkzeug zeigt „Hinsehen“


# --- Die Körper ---------------------------------------------------------------------------


class Bild:
    """Werkzeug und Werkstück in der 3D-Ansicht der Maschine.

    `ansicht`: die 3D-Ansicht (View3DInventor) des Dokuments der Maschine.
    """

    def __init__(self, ansicht, abfahrt, job, nullpunkt, bibliothek):
        from pivy import coin

        self._coin = coin
        self.ansicht = ansicht
        self.werkstueckaufnahme = abfahrt.pruefung.werkstueckaufnahme
        self.nullpunkt = FreeCAD.Vector(nullpunkt)
        self.aufnahmen = [op.aufnahme for op in abfahrt.operationen]
        self.operation = 0 if self.aufnahmen else -1
        self.wurzel = coin.SoSeparator()

        werkstueck = coin.SoSeparator()
        self.werkstueck_lage = coin.SoTransform()
        werkstueck.addChild(self.werkstueck_lage)
        for objekt in getattr(getattr(job, "Model", None), "Group", []):
            form = getattr(objekt, "Shape", None)
            if form is not None and not form.isNull():
                werkstueck.addChild(self._flaechen(form, MODELL, 0.0))
        rohteil = getattr(getattr(job, "Stock", None), "Shape", None)
        if rohteil is not None and not rohteil.isNull():
            werkstueck.addChild(self._flaechen(rohteil, ROHTEIL, 0.75))
        werkstueck.addChild(self._bahnlinien(abfahrt))
        self.wurzel.addChild(werkstueck)

        werkzeug = coin.SoSeparator()
        self.werkzeug_lage = coin.SoTransform()
        werkzeug.addChild(self.werkzeug_lage)
        self.werkzeug_wahl = coin.SoSwitch()
        # Je Operation ihr Halter aus der Werkzeugverwaltung – None: angedeutet.
        self.halter = [rw.werkzeughalter(op.tc, bibliothek) for op in abfahrt.operationen]
        for op, halter in zip(abfahrt.operationen, self.halter, strict=True):
            masse = rw.werkzeugmasse(op.tc, bibliothek, op.laenge)
            self.werkzeug_wahl.addChild(self._werkzeug(op.laenge, masse, halter))
        self.werkzeug_wahl.whichChild = self.operation
        werkzeug.addChild(self.werkzeug_wahl)
        self.wurzel.addChild(werkzeug)

        ansicht.getSceneGraph().addChild(self.wurzel)
        self.folge()

    def zeige_operation(self, nummer):
        """Das Werkzeug der Operation `nummer` an ihrer Werkzeugaufnahme."""
        if nummer != self.operation and 0 <= nummer < len(self.aufnahmen):
            self.operation = nummer
            self.werkzeug_wahl.whichChild = nummer

    def folge(self):
        """Werkzeug und Werkstück dorthin, wo ihre Aufnahmen gerade stehen."""
        job = m.globale_platzierung(self.werkstueckaufnahme.Lcs).multiply(
            FreeCAD.Placement(self.nullpunkt, FreeCAD.Rotation())
        )
        self._setze(self.werkstueck_lage, job)
        if 0 <= self.operation < len(self.aufnahmen):
            self._setze(
                self.werkzeug_lage, m.globale_platzierung(self.aufnahmen[self.operation].Lcs)
            )

    def hinsehen(self):
        """Richtet die Kamera auf Werkstück und Werkzeug – die Maschine ist meist viel
        größer als das Teil."""
        region = self.ansicht.getViewer().getSoRenderManager().getViewportRegion()
        self.ansicht.getCameraNode().viewAll(self.wurzel, region, HINSEHEN_RAND)

    def weg(self):
        """Nimmt die Körper aus der Ansicht."""
        wurzel = self.ansicht.getSceneGraph()
        if wurzel.findChild(self.wurzel) >= 0:
            wurzel.removeChild(self.wurzel)

    # --- Bauen ----------------------------------------------------------------------

    @staticmethod
    def _setze(knoten, lage):
        knoten.translation.setValue(lage.Base.x, lage.Base.y, lage.Base.z)
        q = lage.Rotation.Q  # (x, y, z, w) – dieselbe Reihenfolge wie bei Coin
        knoten.rotation.setValue(q[0], q[1], q[2], q[3])

    def _material(self, farbe, transparenz=0.0):
        material = self._coin.SoMaterial()
        material.diffuseColor.setValue(*farbe)
        material.transparency.setValue(transparenz)
        return material

    def _zylinder(self, radius, von, bis, farbe, transparenz=0.0):
        """Ein Zylinder entlang Z von `von` bis `bis`."""
        coin = self._coin
        teil = coin.SoSeparator()
        teil.addChild(self._material(farbe, transparenz))
        lage = coin.SoTransform()
        lage.translation.setValue(0, 0, (von + bis) / 2)
        lage.rotation.setValue(coin.SbVec3f(1, 0, 0), math.pi / 2)  # SoCylinder steht in Y
        teil.addChild(lage)
        zylinder = coin.SoCylinder()
        zylinder.radius = radius
        zylinder.height = abs(bis - von)
        teil.addChild(zylinder)
        return teil

    def _werkzeug(self, laenge, masse, halter):
        """Das Werkzeug im LCS seiner Aufnahme – dieselben Körper, die die Kollision prüft
        (kollision.werkzeugkoerper): Schneide gelb, Hals und Schaft grau, der Halter mit
        seiner Kontur. Ohne Halter ist einer angedeutet, durchscheinend von der Gesamtlänge
        bis zur Aufnahme."""
        teil = self._coin.SoSeparator()
        farben = {kb.SCHNEIDE: SCHNEIDE, kb.HALS: SCHAFT, kb.SCHAFT: SCHAFT, kb.HALTER: HALTER_ECHT}
        for art, form in kb.werkzeugkoerper(masse, laenge, halter):
            teil.addChild(self._flaechen(form, farben[art], 0.0))
        gesamt = min(masse.gesamt, laenge) if masse.gesamt > 0 else laenge
        if halter is None and laenge - gesamt > 0.5:
            radius = max(2 * masse.schaft, HALTER_MINDESTENS) / 2
            teil.addChild(self._zylinder(radius, -laenge + gesamt, 0.0, HALTER, 0.6))
        return teil

    def _flaechen(self, form, farbe, transparenz):
        """Eine Form als Dreiecke, in ihren eigenen Koordinaten (denen des Jobs)."""
        coin = self._coin
        teil = coin.SoSeparator()
        teil.addChild(self._material(farbe, transparenz))
        hinweise = coin.SoShapeHints()
        hinweise.creaseAngle = 0.5
        teil.addChild(hinweise)
        genauigkeit = max(form.BoundBox.DiagonalLength / 300, 0.05)
        punkte, dreiecke = form.tessellate(genauigkeit)
        koordinaten = coin.SoCoordinate3()
        koordinaten.point.setValues(0, len(punkte), [(p.x, p.y, p.z) for p in punkte])
        teil.addChild(koordinaten)
        flaechen = coin.SoIndexedFaceSet()
        index = []
        for a, b, c in dreiecke:
            index += [a, b, c, -1]
        flaechen.coordIndex.setValues(0, len(index), index)
        teil.addChild(flaechen)
        return teil

    def _bahnlinien(self, abfahrt):
        """Die Bahn als Linien in Koordinaten des Jobs: Vorschub blau, Eilgang rot."""
        coin = self._coin
        teil = coin.SoSeparator()
        stil = coin.SoDrawStyle()
        stil.lineWidth = 2
        teil.addChild(stil)
        punkte = [s.punkt for s in abfahrt.stationen]
        koordinaten = coin.SoCoordinate3()
        koordinaten.point.setValues(0, len(punkte), punkte)
        teil.addChild(koordinaten)
        for eilgang, farbe in ((False, VORSCHUB_LINIE), (True, EILGANG_LINIE)):
            index = []
            for i in range(1, len(punkte)):
                if abfahrt.stationen[i].eilgang == eilgang:
                    index += [i - 1, i, -1]
            if not index:
                continue
            linien = coin.SoIndexedLineSet()
            linien.coordIndex.setValues(0, len(index), index)
            teil.addChild(self._material(farbe))
            teil.addChild(linien)
        return teil


def ansicht_von(dokument):
    """Die 3D-Ansicht eines Dokuments, oder None."""
    gui_dokument = FreeCADGui.getDocument(dokument.Name)
    ansichten = gui_dokument.mdiViewsOfType("Gui::View3DInventor") if gui_dokument else []
    return ansichten[0] if ansichten else None


# --- Der Abspieler ------------------------------------------------------------------------


class Abspieler(QtGui.QWidget):
    """Der Bereich „Abfahren“ im Fenster „Auf der Maschine prüfen“.

    `fahren(stellungen, operation)` bewegt die Maschine und das Werkzeug der
    Operation und gibt die Achsen zurück, die an einer Grenze halten – das
    Fenster öffnet dafür seinen Schritt Rückgängig. `hinsehen()` richtet die
    Ansicht auf Werkstück und Werkzeug.
    """

    def __init__(self, fahren, hinsehen):
        super().__init__()
        self._fahren = fahren
        self._hinsehen = hinsehen
        self.abfahrt = None
        self.zeit = 0.0
        self.station = 0  # die letzte Station, die die Bahn erreicht hat
        self.werte = {}  # {Achse: Stellung}, wie das Programm sie will
        self.angehalten = []
        self._uhr = QtCore.QTimer(self)
        self._uhr.setInterval(TAKT)
        self._uhr.timeout.connect(self._takt)
        self._baue()
        self.zeige(None)

    def _baue(self):
        aufbau = QtGui.QVBoxLayout(self)
        aufbau.setContentsMargins(0, 0, 0, 0)
        aufbau.addWidget(kopfzeile(tr("ab.titel"), "reichweite"))
        self.wahl_operation = QtGui.QComboBox()
        self.wahl_operation.setToolTip(tr("ab.operation.tooltip"))
        self.wahl_operation.activated.connect(self.springe_zu_operation)
        aufbau.addWidget(self.wahl_operation)

        zeile = QtGui.QHBoxLayout()
        self.knopf_anfang = self._knopf(
            QtGui.QStyle.SP_MediaSkipBackward, tr("ab.anfang.tooltip"), self.anfang
        )
        self.knopf_zurueck = self._knopf(
            QtGui.QStyle.SP_MediaSeekBackward, tr("ab.zurueck.tooltip"), self.schritt_zurueck
        )
        self.knopf_spielen = QtGui.QPushButton()
        self.knopf_spielen.setAutoDefault(False)
        self.knopf_spielen.clicked.connect(self.umschalten)
        self.knopf_vor = self._knopf(
            QtGui.QStyle.SP_MediaSeekForward, tr("ab.vor.tooltip"), self.schritt_vor
        )
        self.wahl_tempo = QtGui.QComboBox()
        for tempo in TEMPI:
            self.wahl_tempo.addItem(f"×{tempo}", tempo)
        self.wahl_tempo.setToolTip(tr("ab.tempo.tooltip"))
        self.knopf_hinsehen = QtGui.QToolButton()
        self.knopf_hinsehen.setIcon(QtGui.QIcon(":/icons/zoom-selection.svg"))
        self.knopf_hinsehen.setToolTip(tr("ab.hinsehen.tooltip"))
        self.knopf_hinsehen.clicked.connect(lambda: self._hinsehen())
        for widget in (self.knopf_anfang, self.knopf_zurueck, self.knopf_spielen, self.knopf_vor):
            zeile.addWidget(widget)
        zeile.addStretch()
        zeile.addWidget(self.knopf_hinsehen)
        zeile.addWidget(self.wahl_tempo)
        aufbau.addLayout(zeile)

        self.schieber = QtGui.QSlider(QtCore.Qt.Horizontal)
        self.schieber.setRange(0, SCHIEBER_SCHRITTE)
        self.schieber.setToolTip(tr("ab.schieber.tooltip"))
        self.schieber.valueChanged.connect(self._geschoben)
        aufbau.addWidget(self.schieber)
        self.stelle = QtGui.QLabel()
        self.stelle.setWordWrap(True)
        aufbau.addWidget(self.stelle)
        self.achswerte = QtGui.QLabel()
        self.achswerte.setWordWrap(True)
        self.achswerte.setTextFormat(QtCore.Qt.RichText)
        aufbau.addWidget(self.achswerte)
        self.hinweise = QtGui.QLabel()
        self.hinweise.setWordWrap(True)
        self.hinweise.setStyleSheet(f"color: {GRAU.name()};")
        aufbau.addWidget(self.hinweise)
        self._knopf_zeigen()

    def _knopf(self, symbol, tooltip, aktion):
        knopf = QtGui.QToolButton()
        knopf.setIcon(self.style().standardIcon(symbol))
        knopf.setToolTip(tooltip)
        knopf.clicked.connect(lambda: aktion())
        return knopf

    def _knopf_zeigen(self):
        stil = self.style()
        if self._uhr.isActive():
            self.knopf_spielen.setIcon(stil.standardIcon(QtGui.QStyle.SP_MediaPause))
            self.knopf_spielen.setText(tr("ab.anhalten"))
        else:
            self.knopf_spielen.setIcon(stil.standardIcon(QtGui.QStyle.SP_MediaPlay))
            self.knopf_spielen.setText(tr("ab.abspielen"))

    # --- Daten ----------------------------------------------------------------------

    def zeige(self, abfahrt, zeit=None):
        """Eine neue Abfahrt – oder None: nichts abzufahren. Ohne `zeit` steht sie am
        Anfang, und die Maschine bewegt sich erst, wenn man abspielt, springt oder
        schiebt. Mit `zeit` fährt sie gleich dorthin (etwa nach einem neuen Nullpunkt);
        lief das Abspielen, läuft es weiter."""
        lief = self._uhr.isActive()
        self.anhalten()
        self.abfahrt = abfahrt
        self.zeit = 0.0
        self.station = 0
        self.werte = {}
        self.angehalten = []
        leer = abfahrt is None or not abfahrt.stationen
        self.wahl_operation.clear()
        if not leer:
            for op in abfahrt.operationen:
                self.wahl_operation.addItem(op.name)
        for widget in (
            self.wahl_operation,
            self.knopf_anfang,
            self.knopf_zurueck,
            self.knopf_spielen,
            self.knopf_vor,
            self.knopf_hinsehen,
            self.wahl_tempo,
            self.schieber,
        ):
            widget.setEnabled(not leer)
        self.hinweise.setText("\n".join(abfahrt.hinweise) if abfahrt else "")
        self.hinweise.setVisible(bool(abfahrt and abfahrt.hinweise))
        if zeit is None or leer:
            self._anzeigen()
            return
        self.setze_zeit(zeit)
        if lief and self.zeit < abfahrt.dauer:
            self._uhr.start()
            self._knopf_zeigen()

    # --- Bedienen -------------------------------------------------------------------

    def setze_zeit(self, zeit, station=None):
        """Stellt die Bahn auf `zeit` (s) – die Maschine fährt dorthin. `station`: genau
        diese Station (mehrere können dieselbe Zeit haben, etwa zwei Punkte an derselben
        Stelle)."""
        if self.abfahrt is None or not self.abfahrt.stationen:
            return
        abfahrt = self.abfahrt
        self.zeit = min(max(zeit, 0.0), abfahrt.dauer)
        if station is None:
            self.station = abfahrt.index_bei(self.zeit)
            self.werte = abfahrt.stellungen_bei(self.zeit)
        else:
            self.station = station
            self.werte = abfahrt.stellungen_an(station)
        operation = abfahrt.stationen[self.laufend()].operation
        self.angehalten = self._fahren(self.werte, operation)
        self._anzeigen()

    def laufend(self):
        """Die Station, auf die die Maschine gerade zufährt – an einer Station diese selbst.
        Ihr Satz ist der, der gerade läuft."""
        stationen = self.abfahrt.stationen
        if self.station + 1 < len(stationen) and self.zeit > stationen[self.station].zeit + 1e-9:
            return self.station + 1
        return self.station

    def anfang(self):
        self.springe_zu_station(0)

    def schritt_vor(self):
        """Zum nächsten Punkt der Bahn."""
        if self.abfahrt is not None and self.abfahrt.stationen:
            self.springe_zu_station(min(self.station + 1, len(self.abfahrt.stationen) - 1))

    def schritt_zurueck(self):
        """Zum Punkt davor – steht die Bahn zwischen zwei Punkten, zum vorderen."""
        if self.abfahrt is None or not self.abfahrt.stationen:
            return
        i = self.station
        if self.zeit <= self.abfahrt.stationen[i].zeit + 1e-9:
            i = max(i - 1, 0)
        self.springe_zu_station(i)

    def springe_zu_operation(self, nummer):
        """An den Anfang der Operation `nummer`."""
        if self.abfahrt is not None and 0 <= nummer < len(self.abfahrt.operationen):
            self.springe_zu_station(self.abfahrt.operationen[nummer].erste)

    def springe_zu_station(self, index):
        """Auf die Station `index` (etwa die einer Überschreitung); das Abspielen hält an."""
        if self.abfahrt is not None and 0 <= index < len(self.abfahrt.stationen):
            self.anhalten()
            self.setze_zeit(self.abfahrt.stationen[index].zeit, index)

    def umschalten(self):
        """Abspielen oder anhalten; am Ende beginnt es von vorn."""
        if self._uhr.isActive():
            self.anhalten()
            return
        if self.abfahrt is None or not self.abfahrt.stationen:
            return
        if self.zeit >= self.abfahrt.dauer - 1e-9:
            self.setze_zeit(0.0, 0)
        self._uhr.start()
        self._knopf_zeigen()

    def anhalten(self):
        if self._uhr.isActive():
            self._uhr.stop()
        self._knopf_zeigen()

    def tempo(self):
        return self.wahl_tempo.currentData() or 1

    def _takt(self):
        neu = self.zeit + TAKT / 1000.0 * self.tempo()
        if neu >= self.abfahrt.dauer:
            neu = self.abfahrt.dauer
            self.anhalten()
        self.setze_zeit(neu)

    def _geschoben(self, wert):
        if self.abfahrt is None or not self.abfahrt.stationen:
            return
        self.setze_zeit(self.abfahrt.dauer * wert / SCHIEBER_SCHRITTE)

    # --- Zeigen ---------------------------------------------------------------------

    def _anzeigen(self):
        """Schieber, Operation, Satz, Zeit und die Stellung jeder Achse."""
        abfahrt = self.abfahrt
        if abfahrt is None or not abfahrt.stationen:
            self.stelle.setText(tr("ab.keine_bahn"))
            self.achswerte.setVisible(False)
            return
        station = abfahrt.stationen[self.laufend()]
        op = abfahrt.operationen[station.operation]
        self.wahl_operation.blockSignals(True)
        self.wahl_operation.setCurrentIndex(station.operation)
        self.wahl_operation.blockSignals(False)
        self.schieber.blockSignals(True)
        anteil = self.zeit / abfahrt.dauer if abfahrt.dauer > 0 else 0.0
        self.schieber.setValue(round(anteil * SCHIEBER_SCHRITTE))
        self.schieber.blockSignals(False)
        self.stelle.setText(
            tr(
                "ab.stelle",
                operation=op.name,
                satz=station.satz,
                saetze=op.saetze,
                zeit=zeit_text(self.zeit),
                dauer=zeit_text(abfahrt.dauer),
            )
        )
        werte = self.werte
        pruefung = abfahrt.pruefung
        teile = []
        for achse in sorted(werte, key=lambda a: (a.art != LINEAR, namen(pruefung.maschine, a))):
            # So steht die Maschine wirklich: höchstens an der Grenze.
            wert = pruefung.verfahren.begrenzt(achse, werte[achse])
            text = html.escape(f"{namen(pruefung.maschine, achse)} {rw.stellung_text(achse, wert)}")
            if achse in self.angehalten:
                text = f"<span style='color:{ROT}'>{text} ({html.escape(tr('ab.anschlag'))})</span>"
            teile.append(text)
        if station.stellungen is None:
            teile.append(
                f"<span style='color:{ROT}'>{html.escape(tr('ab.nicht_erreichbar'))}</span>"
            )
        # Leer, solange die Maschine nicht auf der Bahn steht (vor dem ersten Abspielen).
        self.achswerte.setText(" · ".join(teile))
        self.achswerte.setVisible(bool(teile))
