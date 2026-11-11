# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Werkzeugwege eines Wegs im 3D (W-039; Manuel, 2026-10-25: „weg 1 ist so und so [vorschau
button] weg 2 ist so und so [vorschau button]“ – „die vorschau muss die werkzeugwege halt nur sehr
schnell berechnen grob .. auf +-0.3mm oder so“): die groben Bahnen der Vorschau (bahn.Punkt, mm
im Job) als Linien in der Ansicht des Dokuments, vor dem Teil – je Operation eine Farbe im
Vorschub, der Eilgang grau. Eine Ansicht trägt höchstens eine solche Vorschau."""

import math

from . import gui_abfahren as ga

FARBEN = (
    (0.10, 0.35, 0.90),
    (0.95, 0.55, 0.05),
    (0.15, 0.65, 0.20),
    (0.75, 0.15, 0.75),
    (0.00, 0.65, 0.70),
    (0.85, 0.10, 0.25),
    (0.45, 0.30, 0.10),
    (0.40, 0.40, 0.95),
)


def farbe(nummer):
    """Die Farbe der Bahn Nummer `nummer` (0, 1, …) als (r, g, b) von 0 bis 1."""
    return FARBEN[nummer % len(FARBEN)]


def farbe_hex(nummer):
    """Dieselbe Farbe als „#rrggbb“ – für die Zeile, die im Fenster zu der Bahn gehört."""
    return "#" + "".join(f"{int(round(255 * wert)):02x}" for wert in farbe(nummer))


EILGANG = (0.60, 0.60, 0.60)
BOGEN_STUECKE = 12  # so viele Geraden je Bogen – grob genügt


def _linienpunkte(punkte):
    """[(x, y, z, eilgang)] – Bögen (bahn.Punkt.bogen) in BOGEN_STUECKE Geraden; die Stellen der
    Flanke (flanke_bahn.Stelle) mit ihrer Spitze."""
    aus = []
    for i, p in enumerate(punkte):
        spitze = getattr(p, "spitze", None)
        if spitze is not None:
            aus.append((float(spitze[0]), float(spitze[1]), float(spitze[2]), bool(p.eilgang)))
            continue
        bogen = getattr(p, "bogen", None)
        if bogen and i > 0:
            vorher = punkte[i - 1]
            mx, my, uhrzeiger = bogen
            r = math.hypot(vorher.x - mx, vorher.y - my)
            w0 = math.atan2(vorher.y - my, vorher.x - mx)
            w1 = math.atan2(p.y - my, p.x - mx)
            winkel = (w0 - w1) if uhrzeiger else (w1 - w0)
            winkel %= 2 * math.pi
            winkel = winkel if winkel > 1e-9 else 2 * math.pi
            vorzeichen = -1.0 if uhrzeiger else 1.0
            for k in range(1, BOGEN_STUECKE):
                t = k / BOGEN_STUECKE
                w = w0 + vorzeichen * winkel * t
                z = vorher.z + (p.z - vorher.z) * t
                aus.append((mx + r * math.cos(w), my + r * math.sin(w), z, False))
        aus.append((p.x, p.y, p.z, bool(p.eilgang)))
    return aus


class Bahnvorschau:
    """Die gezeigte Vorschau eines Dokuments: zeigen() hängt sie ein (die alte fällt weg), weg()
    nimmt sie heraus. `kennung` sagt, was gerade zu sehen ist (None: nichts)."""

    def __init__(self, dokument):
        self.dokument = dokument
        self.wurzel = None
        self.ansicht = None
        self.kennung = None

    def zeigen(self, kennung, bahnen, lage=None, farben=None):
        """Zeigt die Punkte der `bahnen` (je eine Vorschau mit `punkte`, mm im Job) – `lage`
        (FreeCAD.Placement) bringt sie vom Job ans Teil, wie es in der Ansicht liegt. `farben`
        gibt je Bahn ihre Farbe vor (sonst der Reihe nach) – so behält eine Bahn ihre Farbe, wenn
        sie allein gezeigt wird. Gibt zurück, ob es eine Ansicht dafür gab."""
        from pivy import coin

        self.weg()
        ansicht = ga.ansicht_von(self.dokument)
        if ansicht is None:
            return False
        # Vorne gezeichnet (SoAnnotation): Unter einem Rand verdeckte das Teil sonst die Wege.
        wurzel = coin.SoAnnotation()
        if lage is not None:
            versatz = coin.SoTransform()
            versatz.translation.setValue(lage.Base.x, lage.Base.y, lage.Base.z)
            q = lage.Rotation.Q  # (x, y, z, w) – dieselbe Reihenfolge wie bei Coin
            versatz.rotation.setValue(q[0], q[1], q[2], q[3])
            wurzel.addChild(versatz)
        stil = coin.SoDrawStyle()
        stil.lineWidth = 2
        wurzel.addChild(stil)
        for nummer, bahn in enumerate(bahnen):
            punkte = _linienpunkte(getattr(bahn, "punkte", None) or [])
            if len(punkte) < 2:
                continue
            teil = coin.SoSeparator()
            koordinaten = coin.SoCoordinate3()
            koordinaten.point.setValues(0, len(punkte), [p[:3] for p in punkte])
            teil.addChild(koordinaten)
            vorschub, eilgang = [], []
            for i in range(1, len(punkte)):
                (eilgang if punkte[i][3] else vorschub).extend((i - 1, i, -1))
            eigene = farben[nummer] if farben else farbe(nummer)
            for stellen, f in ((vorschub, eigene), (eilgang, EILGANG)):
                if not stellen:
                    continue
                linien = coin.SoIndexedLineSet()
                linien.coordIndex.setValues(0, len(stellen), stellen)
                teil.addChild(ga.material(f))
                teil.addChild(linien)
            wurzel.addChild(teil)
        ansicht.getSceneGraph().addChild(wurzel)
        self.wurzel, self.ansicht, self.kennung = wurzel, ansicht, kennung
        return True

    def weg(self):
        if self.wurzel is not None and self.ansicht is not None:
            try:
                graph = self.ansicht.getSceneGraph()
                if graph.findChild(self.wurzel) >= 0:
                    graph.removeChild(self.wurzel)
            except Exception:  # noqa: BLE001 – die Ansicht ist schon zu
                pass
        self.wurzel = self.ansicht = self.kennung = None


class Abspieler:
    """Lässt in der Ansicht ein Werkzeug die Wege der Vorschau abfahren – so sieht man, was der
    Vorschlag tut, statt es sich aus Linien zusammenzureimen (Manuel, 2026-11-11: „gibts vll einfach
    ne andere möglichkeit das gesagte … zu zeigen oder dem benutzer schmackhaft zu machen“). Nur
    Anzeige: ein Zylinder in der Farbe der Bearbeitung, der in DAUER Sekunden alle Wege abläuft
    (Eilgänge fünfmal so schnell); kein Abtrag, keine Maschine – dafür gibt es „Auf der Maschine
    prüfen“."""

    DAUER = 12.0  # Sekunden für alle Wege zusammen
    TAKT = 33  # ms
    EILGANG = 0.2  # ein Eilgang zählt so viel seiner Länge

    def __init__(self, dokument):
        from PySide import QtCore

        self.dokument = dokument
        self.wurzel = None
        self.ansicht = None
        self._uhr = QtCore.QTimer()
        self._uhr.setInterval(self.TAKT)
        self._uhr.timeout.connect(self._schritt)
        self._strecken = []  # [(Anfang, Ende, gewichtete Länge, Nummer der Bahn)]
        self._gesamt = 0.0
        self._weg = 0.0
        self._fertig = None
        self._lagen = []
        self._schalter = None

    def laeuft(self):
        return self._uhr.isActive()

    def starten(self, bahnen, lage=None, fertig=None):
        """`bahnen`: [(Vorschau mit `punkte`, Farbe (r, g, b), Radius des Werkzeugs in mm)].
        `lage` wie bei Bahnvorschau.zeigen; `fertig()` wird gerufen, wenn es durch ist oder
        angehalten wird. Gibt zurück, ob es etwas abzufahren gibt."""
        from pivy import coin

        self.anhalten()
        ansicht = ga.ansicht_von(self.dokument)
        if ansicht is None:
            return False
        strecken, werkzeuge = [], []
        for nummer, (bahn, farbe_, radius) in enumerate(bahnen):
            punkte = _linienpunkte(getattr(bahn, "punkte", None) or [])
            for a, b in zip(punkte, punkte[1:], strict=False):
                laenge = math.dist(a[:3], b[:3])
                if laenge > 1e-9:
                    strecken.append(
                        (a[:3], b[:3], laenge * (self.EILGANG if b[3] else 1.0), nummer)
                    )
            radius = max(float(radius or 0.0), 0.5)
            werkzeuge.append(ga.zylinder(radius, 0.0, max(6.0 * radius, 10.0), farbe_, 0.15))
        if not strecken:
            return False
        wurzel = coin.SoAnnotation()
        if lage is not None:
            versatz = coin.SoTransform()
            versatz.translation.setValue(lage.Base.x, lage.Base.y, lage.Base.z)
            q = lage.Rotation.Q
            versatz.rotation.setValue(q[0], q[1], q[2], q[3])
            wurzel.addChild(versatz)
        self._ort = coin.SoTranslation()
        wurzel.addChild(self._ort)
        self._schalter = coin.SoSwitch()
        for werkzeug in werkzeuge:
            self._schalter.addChild(werkzeug)
        wurzel.addChild(self._schalter)
        ansicht.getSceneGraph().addChild(wurzel)
        self.wurzel, self.ansicht = wurzel, ansicht
        self._strecken, self._gesamt = strecken, sum(s[2] for s in strecken)
        self._weg, self._stelle, self._davor, self._fertig = 0.0, 0, 0.0, fertig
        self._schritt()
        self._uhr.start()
        return True

    def _schritt(self):
        if self.wurzel is None:
            return
        self._weg += self._gesamt * self.TAKT / (1000.0 * self.DAUER)
        while self._stelle < len(self._strecken):
            a, b, laenge, nummer = self._strecken[self._stelle]
            if self._weg <= self._davor + laenge:
                t = (self._weg - self._davor) / laenge
                self._ort.translation.setValue(*(a[i] + (b[i] - a[i]) * t for i in range(3)))
                self._schalter.whichChild = nummer
                return
            self._davor += laenge
            self._stelle += 1
        self.anhalten()

    def anhalten(self):
        """Nimmt das Werkzeug aus der Ansicht; meldet `fertig`, wenn es lief."""
        lief = self.wurzel is not None
        self._uhr.stop()
        if self.wurzel is not None and self.ansicht is not None:
            try:
                graph = self.ansicht.getSceneGraph()
                if graph.findChild(self.wurzel) >= 0:
                    graph.removeChild(self.wurzel)
            except Exception:  # noqa: BLE001 – die Ansicht ist schon zu
                pass
        self.wurzel = self.ansicht = None
        fertig, self._fertig = self._fertig, None
        if lief and fertig is not None:
            fertig()
