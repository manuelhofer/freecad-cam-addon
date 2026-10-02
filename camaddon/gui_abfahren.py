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

from . import abfahren as ab
from . import bestueckung as bs
from . import kollision as kb
from . import maschine as m
from . import reichweite as rw
from . import restmaterial as rm
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
MARKE = (0.85, 0.10, 0.10)  # die rote Kugel an einer Kollision
MARKE_RADIUS = 2.0  # mm; dazu ein durchscheinender Hof, viermal so groß
# Rohteil und Fertigteil (W-003 V3g): die Stange beim Abtragen, am Ende in Farben.
REST_DURCHSICHT = 0.35
REST_FARBEN = {
    rm.OHNE_TEIL: ROHTEIL,
    rm.GRUEN: (0.30, 0.75, 0.30),
    rm.GELB: (0.95, 0.80, 0.15),
    rm.ROT: (0.90, 0.20, 0.15),
    rm.BLAU: (0.20, 0.40, 0.95),
}
STELLE_AUSSCHNITT = 400.0  # mm: so hoch zeigt die Ansicht höchstens, wenn sie auf eine Stelle geht
BAHN_ZEIGEN = "AbfahrenBahnZeigen"  # der Haken „Bahn“ im Abspieler, gemerkt
TEIL_ZEIGEN = "AbfahrenTeilZeigen"  # der Haken „Teil“ im Abspieler, gemerkt
TEIL_AM_ENDE = (0.55, 0.55, 0.58)  # das fertige Teil am Ende, grau unter der Stange


def _einstellungen():
    from . import PARAMETER_PFAD

    return FreeCAD.ParamGet(PARAMETER_PFAD)


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
        self._marke = None  # die rote Kugel (kollision), oder None

        werkstueck = coin.SoSeparator()
        self.werkstueck_lage = coin.SoTransform()
        werkstueck.addChild(self.werkstueck_lage)
        # Das fertige Teil – beim Vergleich am Ende grau unter der halb durchsichtigen Stange,
        # solange der Haken „Teil“ gesetzt ist (Manuel, 2026-09-30: „nach dem bearbeiten sieht
        # man das "soll" teil nicht mehr“). Ohne den Haken ist es am Ende ausgeblendet: Wo nichts
        # mehr steht, liegt die Stange genau auf ihm, sein Hellblau schiene durch und sähe aus
        # wie „blau: im Teil“ (Manuels Testteil, P-2026-09-30-45).
        self.modell_schalter = coin.SoSwitch()
        modell = coin.SoGroup()
        self._teil_materialien = []  # je Körper sein SoMaterial – am Ende grau
        for objekt in getattr(getattr(job, "Model", None), "Group", []):
            form = getattr(objekt, "Shape", None)
            if form is not None and not form.isNull():
                knoten = self._flaechen(form, MODELL, 0.0)
                self._teil_materialien.append(knoten.getChild(0))
                modell.addChild(knoten)
        self.modell_schalter.addChild(modell)
        self.modell_schalter.whichChild = 0
        self._teil_an = _einstellungen().GetBool(TEIL_ZEIGEN, True)
        werkstueck.addChild(self.modell_schalter)
        punkte = abfahrt.am_werkstueck()
        # Eine runde Stange mit „Rundum schruppen“ wird beim Abspielen abgetragen (V3g), ein
        # Kasten als Rohteil mit Werkzeugen senkrecht von oben ebenso (W-006 S3d).
        try:
            self.abtrag = rm.fuer(abfahrt, job, punkte)
        except Exception as fehler:  # ohne Abtrag geht alles andere weiter
            FreeCAD.Console.PrintLog(f"CAM-Addon: Restmaterial: {fehler}\n")
            self.abtrag = None
        rohteil = getattr(getattr(job, "Stock", None), "Shape", None)
        if self.abtrag is not None:
            werkstueck.addChild(self._restmaterial())
        elif rohteil is not None and not rohteil.isNull():
            werkstueck.addChild(self._flaechen(rohteil, ROHTEIL, 0.75))
        # Die Bahn – beim Vergleich am Ende ausgeblendet, sonst verdeckt sie die Farben; ohne
        # den Haken „Bahn“ im Abspieler immer (Manuel, 2026-09-30: „irgendwo einen hacken für
        # werkzeugwege ausblenden“).
        self.bahn_schalter = coin.SoSwitch()
        self.bahn_schalter.addChild(self._bahnlinien(abfahrt, punkte))
        self._bahn_an = True
        self._am_ende = False
        self._bahn_schalten()
        werkstueck.addChild(self.bahn_schalter)
        self.wurzel.addChild(werkstueck)

        self._werkstueck = werkstueck
        # Alle Werkzeuge des Jobs auf ihren Plätzen – die Bestückung des Jobs (W-002 Stufe G;
        # Manuel, 2026-09-30: „die bestückung wird nicht dargestellt auf der maschine“). Je
        # Aufnahme ein Knoten, der ihr folgt – so schwenken sie mit dem Revolver; stecken im
        # Job zwei Werkzeuge auf einem Platz, zeigt er das der laufenden Operation.
        self._plaetze = []  # [(Aufnahme, Knoten, SoTransform, SoSwitch, [Schlüssel …])]
        self._op_platz = []  # je Operation: (Index in _plaetze, Kind in dessen SoSwitch)
        # Je Operation ihr Halter aus der Werkzeugverwaltung – None: angedeutet.
        self.halter = [rw.werkzeughalter(op.tc, bibliothek) for op in abfahrt.operationen]
        index = {}
        for op, halter in zip(abfahrt.operationen, self.halter, strict=True):
            k = index.get(op.aufnahme)
            if k is None:
                knoten, lage, wahl = coin.SoSeparator(), coin.SoTransform(), coin.SoSwitch()
                knoten.addChild(lage)
                knoten.addChild(wahl)
                self.wurzel.addChild(knoten)
                k = index[op.aufnahme] = len(self._plaetze)
                self._plaetze.append((op.aufnahme, knoten, lage, wahl, []))
            _aufnahme, _knoten, _lage, wahl, schluessel = self._plaetze[k]
            werkzeug = bs.schluessel(op.tc, bibliothek)
            if werkzeug not in schluessel:
                masse = rw.werkzeugmasse(op.tc, bibliothek, op.laenge)
                wahl.addChild(self._werkzeug(op.laenge, masse, halter))
                schluessel.append(werkzeug)
            self._op_platz.append((k, schluessel.index(werkzeug)))
        for _aufnahme, _knoten, _lage, wahl, _schluessel in self._plaetze:
            wahl.whichChild = 0
        if self._op_platz:
            k, kind = self._op_platz[0]
            self._plaetze[k][3].whichChild = kind

        ansicht.getSceneGraph().addChild(self.wurzel)
        self.folge()

    # --- Rohteil und Fertigteil (V3g) ------------------------------------------------

    def abtragen(self, index):
        """Trägt die Stange bis Station `index` ab und zeigt sie; an der letzten Station
        eingefärbt gegen das fertige Teil. Gibt den Satz dazu zurück („“ ohne Abtrag)."""
        if self.abtrag is None:
            return ""
        self.abtrag.bis_station(index)
        ende = index >= self.abtrag.letzte()
        vergleich = self.abtrag.vergleich() if ende else None
        self._am_ende = ende
        self._rest_zeigen(vergleich)
        self._bahn_schalten()
        self._teil_schalten()
        return _rest_satz(vergleich, self.abtrag.aufmass, self._im_quader())

    def zeige_bahn(self, an):
        """Die Bahn zeigen (Haken „Bahn“ im Abspieler) – am Ende mit den Farben nie."""
        self._bahn_an = bool(an)
        self._bahn_schalten()

    def _bahn_schalten(self):
        self.bahn_schalter.whichChild = 0 if self._bahn_an and not self._am_ende else -1

    def zeige_teil(self, an):
        """Das fertige Teil auch am Ende zeigen (Haken „Teil“ im Abspieler)."""
        self._teil_an = bool(an)
        self._teil_schalten()

    def _teil_schalten(self):
        """Vor dem Ende das Teil hellblau unter der halb durchsichtigen Stange; am Ende grau
        unter ihr – oder, ohne den Haken „Teil“, weg und die Stange deckend in den Farben."""
        am_ende = self._am_ende and self.abtrag is not None
        self.modell_schalter.whichChild = 0 if self._teil_an or not am_ende else -1
        farbe = TEIL_AM_ENDE if am_ende else MODELL
        for material in self._teil_materialien:
            material.diffuseColor.setValue(*farbe)
        if self.abtrag is not None:
            deckend = am_ende and not self._teil_an
            self._rest_material.transparency.setValue(0.0 if deckend else REST_DURCHSICHT)

    def _im_quader(self):
        """Das Rohteil ist ein Kasten (restmaterial.QuaderAbtrag), keine Stange."""
        return hasattr(self.abtrag, "quader")

    def _restmaterial(self):
        """Die Stange als Fläche über (a, φ) – oder der Quader als Fläche über (x, y) mit
        Seitenwänden; Punkte und Farben setzt _rest_zeigen()."""
        coin = self._coin
        teil = coin.SoSeparator()
        self._rest_bindung = coin.SoMaterialBinding()
        teil.addChild(self._rest_bindung)
        self._rest_material = coin.SoMaterial()
        self._rest_material.transparency.setValue(REST_DURCHSICHT)
        teil.addChild(self._rest_material)
        hinweise = coin.SoShapeHints()
        hinweise.creaseAngle = 0.8
        teil.addChild(hinweise)
        self._rest_punkte = coin.SoCoordinate3()
        teil.addChild(self._rest_punkte)
        self._rest_netz = coin.SoQuadMesh()
        teil.addChild(self._rest_netz)
        if self._im_quader():
            # Der Boden des Kastens – die Seitenwände hängen am Netz (_quader_punkte).
            q = self.abtrag.quader
            boden = coin.SoSeparator()
            boden.addChild(material(ROHTEIL, REST_DURCHSICHT))
            ecken = coin.SoCoordinate3()
            ecken.point.setValues(
                0,
                4,
                [
                    (q.x[0], q.y[0], q.z_von),
                    (q.x[-1], q.y[0], q.z_von),
                    (q.x[-1], q.y[-1], q.z_von),
                    (q.x[0], q.y[-1], q.z_von),
                ],
            )
            boden.addChild(ecken)
            boden.addChild(coin.SoFaceSet())
            teil.addChild(boden)
        else:
            self._rest_rahmen = rm.vh.rahmen(self.abtrag.laengs, self.abtrag.radial)
        self._rest_zeigen(None)
        return teil

    def _stangen_punkte(self):
        """(Punkte (n_a, n_phi, 3), Farben je Punkt oder None) der Stange aus dem Abtrag."""
        import numpy as np

        a, phi, r = rm.darstellung(self.abtrag.stange)
        l_, u_, v_ = self._rest_rahmen
        richtung = np.cos(phi)[:, None] * u_[None, :] + np.sin(phi)[:, None] * v_[None, :]
        punkte = a[:, None, None] * l_[None, None, :] + r[:, :, None] * richtung[None, :, :]
        return punkte, lambda vergleich: rm.farben(vergleich)

    def _quader_punkte(self):
        """(Punkte (n_x + 2, n_y + 2, 3), Farben je Punkt) des Quaders: die Oberseite, außen
        herum ein Rand aus denselben x und y auf der Unterseite – die Seitenwände."""
        import numpy as np

        q = self.abtrag.quader
        x, y, h = rm.darstellung_quader(q)
        xr = np.concatenate([x[:1], x, x[-1:]])
        yr = np.concatenate([y[:1], y, y[-1:]])
        hr = np.full((len(xr), len(yr)), q.z_von)
        hr[1:-1, 1:-1] = h
        punkte = np.stack(
            [np.broadcast_to(xr[:, None], hr.shape), np.broadcast_to(yr[None, :], hr.shape), hr],
            axis=2,
        )
        return punkte, lambda vergleich: np.pad(rm.farben_quader(vergleich), 1, mode="edge")

    def _rest_zeigen(self, vergleich):
        """Die Punkte des Rohteils aus dem Abtrag; mit `vergleich` in den Farben des
        Vergleichs, sonst in der Farbe des Rohteils."""
        punkte, farben_von = self._quader_punkte() if self._im_quader() else self._stangen_punkte()
        liste = punkte.reshape(-1, 3).tolist()
        self._rest_punkte.point.setValues(0, len(liste), liste)
        self._rest_punkte.point.setNum(len(liste))
        self._rest_netz.verticesPerColumn = punkte.shape[0]
        self._rest_netz.verticesPerRow = punkte.shape[1]
        material = self._rest_material
        if vergleich is None:
            self._rest_bindung.value = self._coin.SoMaterialBinding.OVERALL
            material.diffuseColor.setValue(*ROHTEIL)
            material.transparency.setValue(REST_DURCHSICHT)
            return
        farben = [REST_FARBEN[f] for f in farben_von(vergleich).reshape(-1).tolist()]
        self._rest_bindung.value = self._coin.SoMaterialBinding.PER_VERTEX
        material.diffuseColor.setValues(0, len(farben), farben)
        material.diffuseColor.setNum(len(farben))
        # Deckend oder halb durchsichtig über dem grauen Teil: _teil_schalten().

    def zeige_operation(self, nummer):
        """Das Werkzeug der Operation `nummer` an ihrer Werkzeugaufnahme – stecken dort im Job
        zwei, ihres."""
        if nummer != self.operation and 0 <= nummer < len(self.aufnahmen):
            self.operation = nummer
            k, kind = self._op_platz[nummer]
            self._plaetze[k][3].whichChild = kind

    @property
    def werkzeug_lage(self):
        """Die Lage (SoTransform) des Werkzeugs der laufenden Operation, oder None."""
        if not 0 <= self.operation < len(self._op_platz):
            return None
        return self._plaetze[self._op_platz[self.operation][0]][2]

    def folge(self):
        """Werkzeuge und Werkstück dorthin, wo ihre Aufnahmen gerade stehen."""
        job = m.globale_platzierung(self.werkstueckaufnahme.Lcs).multiply(
            FreeCAD.Placement(self.nullpunkt, FreeCAD.Rotation())
        )
        self._setze(self.werkstueck_lage, job)
        for aufnahme, _knoten, lage, _wahl, _schluessel in self._plaetze:
            self._setze(lage, m.globale_platzierung(aufnahme.Lcs))

    def markiere(self, stelle):
        """Eine rote Kugel an `stelle` (Weltkoordinaten) – mit None keine."""
        coin = self._coin
        if self._marke is not None:
            self.wurzel.removeChild(self._marke)
            self._marke = None
        if stelle is None:
            return
        marke = coin.SoSeparator()
        # Obenauf gezeichnet: Die Stelle liegt oft unter der Spindel oder im Teil.
        tiefe = coin.SoDepthBuffer()
        tiefe.test = False
        marke.addChild(tiefe)
        ort = coin.SoTranslation()
        ort.translation.setValue(stelle.x, stelle.y, stelle.z)
        marke.addChild(ort)
        for radius, transparenz in ((MARKE_RADIUS, 0.0), (4 * MARKE_RADIUS, 0.7)):
            marke.addChild(self._material(MARKE, transparenz))
            kugel = coin.SoSphere()
            kugel.radius = radius
            marke.addChild(kugel)
        self.wurzel.addChild(marke)
        self._marke = marke

    def zeige_stelle(self, stelle):
        """Rückt die Ansicht so, dass `stelle` (Weltkoordinaten) in der Mitte liegt – bei
        paralleler Ansicht höchstens STELLE_AUSSCHNITT hoch, sonst im selben Maßstab."""
        coin = self._coin
        kamera = self.ansicht.getCameraNode()
        richtung = kamera.orientation.getValue().multVec(coin.SbVec3f(0, 0, -1))
        abstand = kamera.focalDistance.getValue()
        ziel = coin.SbVec3f(stelle.x, stelle.y, stelle.z)
        kamera.position.setValue(ziel - richtung * abstand)
        if hasattr(kamera, "height"):
            kamera.height.setValue(min(kamera.height.getValue(), STELLE_AUSSCHNITT))

    def hinsehen(self):
        """Richtet die Kamera auf Werkstück und Werkzeug der laufenden Operation – die
        Maschine ist meist viel größer als das Teil, und die anderen Werkzeuge im Revolver
        zeigen woandershin."""
        blick = self._coin.SoGroup()
        blick.addChild(self._werkstueck)
        if 0 <= self.operation < len(self._op_platz):
            blick.addChild(self._plaetze[self._op_platz[self.operation][0]][1])
        region = self.ansicht.getViewer().getSoRenderManager().getViewportRegion()
        self.ansicht.getCameraNode().viewAll(blick, region, HINSEHEN_RAND)

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
        return material(farbe, transparenz)

    def _zylinder(self, radius, von, bis, farbe, transparenz=0.0):
        return zylinder(radius, von, bis, farbe, transparenz)

    def _werkzeug(self, laenge, masse, halter):
        return werkzeug_knoten(laenge, masse, halter)

    def _flaechen(self, form, farbe, transparenz):
        return flaechen(form, farbe, transparenz)

    def _bahnlinien(self, abfahrt, punkte):
        """Die Bahn als Linien in Koordinaten des Jobs, am Werkstück (mit Rundachsen um das
        Teil herum; `punkte`: Abfahrt.am_werkstueck()): Vorschub blau, Eilgang rot."""
        coin = self._coin
        teil = coin.SoSeparator()
        stil = coin.SoDrawStyle()
        stil.lineWidth = 2
        teil.addChild(stil)
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


# --- Bausteine (auch für das Fenster „Bestückung“) ------------------------------------


def material(farbe, transparenz=0.0):
    from pivy import coin

    knoten = coin.SoMaterial()
    knoten.diffuseColor.setValue(*farbe)
    knoten.transparency.setValue(transparenz)
    return knoten


def zylinder(radius, von, bis, farbe, transparenz=0.0):
    """Ein Zylinder entlang Z von `von` bis `bis`."""
    from pivy import coin

    teil = coin.SoSeparator()
    teil.addChild(material(farbe, transparenz))
    lage = coin.SoTransform()
    lage.translation.setValue(0, 0, (von + bis) / 2)
    lage.rotation.setValue(coin.SbVec3f(1, 0, 0), math.pi / 2)  # SoCylinder steht in Y
    teil.addChild(lage)
    koerper = coin.SoCylinder()
    koerper.radius = radius
    koerper.height = abs(bis - von)
    teil.addChild(koerper)
    return teil


def werkzeug_knoten(laenge, masse, halter):
    """Das Werkzeug im LCS seiner Aufnahme – dieselben Körper, die die Kollision prüft
    (kollision.werkzeugkoerper): Schneide gelb, Hals und Schaft grau, der Halter mit seiner
    Kontur. Ohne Halter ist einer angedeutet, durchscheinend von der Gesamtlänge bis zur
    Aufnahme."""
    from pivy import coin

    teil = coin.SoSeparator()
    farben = {kb.SCHNEIDE: SCHNEIDE, kb.HALS: SCHAFT, kb.SCHAFT: SCHAFT, kb.HALTER: HALTER_ECHT}
    for art, form in kb.werkzeugkoerper(masse, laenge, halter):
        teil.addChild(flaechen(form, farben[art], 0.0))
    gesamt = min(masse.gesamt, laenge) if masse.gesamt > 0 else laenge
    if halter is None and laenge - gesamt > 0.5:
        radius = max(2 * masse.schaft, HALTER_MINDESTENS) / 2
        teil.addChild(zylinder(radius, -laenge + gesamt, 0.0, HALTER, 0.6))
    return teil


def flaechen(form, farbe, transparenz):
    """Eine Form als Dreiecke, in ihren eigenen Koordinaten."""
    from pivy import coin

    teil = coin.SoSeparator()
    teil.addChild(material(farbe, transparenz))
    hinweise = coin.SoShapeHints()
    hinweise.creaseAngle = 0.5
    teil.addChild(hinweise)
    genauigkeit = max(form.BoundBox.DiagonalLength / 300, 0.05)
    punkte, dreiecke = form.tessellate(genauigkeit)
    koordinaten = coin.SoCoordinate3()
    koordinaten.point.setValues(0, len(punkte), [(p.x, p.y, p.z) for p in punkte])
    teil.addChild(koordinaten)
    netz = coin.SoIndexedFaceSet()
    index = []
    for a, b, c in dreiecke:
        index += [a, b, c, -1]
    netz.coordIndex.setValues(0, len(index), index)
    teil.addChild(netz)
    return teil


def _rest_satz(vergleich, aufmass, quader=False):
    """Der Satz unter dem Abspieler: beim Abtragen, was passiert; am Ende, was auf dem Teil
    bleibt – mit den Farben. `quader`: das Rohteil ist ein Kasten, keine Stange."""
    if vergleich is None:
        return tr("rm.laeuft_quader") if quader else tr("rm.laeuft")
    mm = rw.weg_text
    if vergleich.kleinster < -rm.BLAU_AB:
        satz = tr("rm.ins_teil", bis=mm(vergleich.groesster), tief=mm(-vergleich.kleinster))
    else:
        satz = tr(
            "rm.ergebnis",
            von=mm(max(vergleich.kleinster, 0.0)),
            bis=mm(vergleich.groesster),
            aufmass=mm(aufmass),
        )
    if vergleich.groesster >= aufmass + rm.ROT_AB:
        satz += " " + tr("rm.zu_viel", grenze=mm(aufmass + rm.ROT_AB))
    if vergleich.nur_gewaehlte:  # V4: der Rest ist Stange (oder Kasten), mit Absicht
        satz += " " + (tr("rm.nur_gewaehlte_quader") if quader else tr("rm.nur_gewaehlte"))
    if vergleich.ohne_vergleich:  # P-2026-09-30-44: das Teil liegt dort nicht rund um die Achse
        stellen = tr("rm.und_von").join(
            tr("rm.von_bis", von=mm(von), bis=mm(bis)) for von, bis in vergleich.ohne_vergleich[:3]
        )
        if len(vergleich.ohne_vergleich) > 3:
            stellen += " …"
        satz += " " + tr("rm.nicht_rundum", stellen=stellen)
    return satz + " " + tr("rm.farben")


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
        # Rohteil und Fertigteil (V3g): bekommt die Station, gibt den Satz dazu zurück.
        self.bei_station = None
        self.bei_bahn = None  # bekommt True/False, wenn jemand den Haken „Bahn“ setzt
        self.bei_teil = None  # dasselbe für den Haken „Teil“
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
        # Die Bahn aus- und einblenden – gemerkt fürs nächste Mal.
        self.haken_bahn = QtGui.QCheckBox(tr("ab.bahn"))
        self.haken_bahn.setToolTip(tr("ab.bahn.tooltip"))
        self.haken_bahn.setChecked(_einstellungen().GetBool(BAHN_ZEIGEN, True))
        self.haken_bahn.toggled.connect(self._bahn_umgeschaltet)
        # Das fertige Teil auch am Ende zeigen – grau unter der halb durchsichtigen Stange.
        self.haken_teil = QtGui.QCheckBox(tr("ab.teil"))
        self.haken_teil.setToolTip(tr("ab.teil.tooltip"))
        self.haken_teil.setChecked(_einstellungen().GetBool(TEIL_ZEIGEN, True))
        self.haken_teil.toggled.connect(self._teil_umgeschaltet)
        for widget in (self.knopf_anfang, self.knopf_zurueck, self.knopf_spielen, self.knopf_vor):
            zeile.addWidget(widget)
        zeile.addStretch()
        zeile.addWidget(self.haken_bahn)
        zeile.addWidget(self.haken_teil)
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
        # Wo die Werkzeugspitze im Programm steht (4e, Manuel: „der TCP muss schon mit
        # berechnet werden .. generell immer“) – die Achsen oben sind die Schlitten.
        self.spitze = QtGui.QLabel()
        self.spitze.setWordWrap(True)
        self.spitze.setTextFormat(QtCore.Qt.RichText)
        self.spitze.setToolTip(tr("ab.spitze.tooltip"))
        aufbau.addWidget(self.spitze)
        self.hinweise = QtGui.QLabel()
        self.hinweise.setWordWrap(True)
        self.hinweise.setStyleSheet(f"color: {GRAU.name()};")
        aufbau.addWidget(self.hinweise)
        self.rest = QtGui.QLabel()  # Rohteil und Fertigteil: was auf dem Teil bleibt
        self.rest.setWordWrap(True)
        self.rest.setVisible(False)
        aufbau.addWidget(self.rest)
        self._knopf_zeigen()

    def _bahn_umgeschaltet(self, an):
        _einstellungen().SetBool(BAHN_ZEIGEN, bool(an))
        if self.bei_bahn is not None:
            self.bei_bahn(bool(an))

    def _teil_umgeschaltet(self, an):
        _einstellungen().SetBool(TEIL_ZEIGEN, bool(an))
        if self.bei_teil is not None:
            self.bei_teil(bool(an))

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
            self.haken_bahn,
            self.haken_teil,
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
        if self.bei_station is not None:
            satz = self.bei_station(self.station)
            self.rest.setText(satz)
            self.rest.setVisible(bool(satz))
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
            self.spitze.setVisible(False)
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
        if station.ziel == ab.HOME:  # außerhalb des Programms (Spezifikation Simulation 13)
            stelle = tr(
                "ab.stelle_home",
                operation=op.name,
                zeit=zeit_text(self.zeit),
                dauer=zeit_text(abfahrt.dauer),
            )
        elif station.ziel == ab.WECHSEL:
            stelle = tr(
                "ab.stelle_wechsel",
                operation=op.name,
                zeit=zeit_text(self.zeit),
                dauer=zeit_text(abfahrt.dauer),
            )
        else:
            stelle = tr(
                "ab.stelle",
                operation=op.name,
                satz=station.satz,
                saetze=op.saetze,
                zeit=zeit_text(self.zeit),
                dauer=zeit_text(abfahrt.dauer),
            )
        self.stelle.setText(stelle)
        werte = self.werte
        pruefung = abfahrt.pruefung
        teile = []
        for achse in sorted(werte, key=lambda a: (a.art != LINEAR, namen(pruefung.maschine, a))):
            # So steht die Maschine wirklich: höchstens an der Grenze.
            wert = pruefung.verfahren.begrenzt(achse, werte[achse])
            stellung = rw.stellung_text(achse, wert, achse in pruefung.durchmesser)
            text = html.escape(f"{namen(pruefung.maschine, achse)} {stellung}")
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
        self.spitze.setText(self._spitze_text(station, werte))
        self.spitze.setVisible(bool(self.spitze.text()))

    def _spitze_text(self, station, werte):
        """„Spitze: X 16, Y 0, Z −28, C −3900“ – wo die Werkzeugspitze im Programm steht, so
        wie die Maschine wirklich steht (höchstens an der Grenze). Hält eine Achse am
        Anschlag, dazu, wo sie hin sollte."""
        if not werte:
            return ""
        pruefung = self.abfahrt.pruefung
        wirklich = {achse: pruefung.verfahren.begrenzt(achse, w) for achse, w in werte.items()}
        try:
            spitze = self.abfahrt.spitze(self.laufend(), wirklich)
        except Exception as fehler:  # eine halb eingerichtete Maschine soll nicht stören
            FreeCAD.Console.PrintLog(f"CAM-Addon: Spitze: {fehler}\n")
            return ""
        text = html.escape(tr("ab.spitze", punkt=rw.punkt_text(spitze, pruefung.x_durchmesser)))
        if self.angehalten:
            soll = rw.punkt_text(
                rw._programmpunkt(station.punkt, station.rund), pruefung.x_durchmesser
            )
            text += (
                f" <span style='color:{ROT}'>{html.escape(tr('ab.spitze_soll', punkt=soll))}</span>"
            )
        return text
