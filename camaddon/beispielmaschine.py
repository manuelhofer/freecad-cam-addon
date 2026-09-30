# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fertig eingerichtete Beispielmaschinen zum Ausprobieren (W-001).

Wer das Addon ausprobiert, soll nicht erst eine Maschine bauen müssen
(Manuel, 2026-09-26). „Neue Maschine …“ – als Befehl und in „Maschine bearbeiten“
und „Maschine verfahren“ – bietet die üblichen Bauarten an (ARTEN) und legt die
gewählte in einem neuen Dokument an, ihr Maschinenobjekt schon ausgefüllt:

- Drehmaschine mit Y-Achse, Schrägbett wie eine CLX: Hauptspindel S1/C1 –
  ihre Achse ist Z –, Revolver T mit zwölf Plätzen, jeder eine VDI30-Aufnahme
  am Werkzeugantrieb S3; wie das Werkzeug steht (radial, axial), sagt sein
  Halter aus der Werkzeugverwaltung (W-002 Stufe E);
- 3-Achs-Fräse: Kreuztisch X/Y, Fräskopf Z;
- 5-Achs Tisch/Tisch: Schwenkbrücke A mit Rundtisch C, X, Y, Z im Kopf;
- 5-Achs Kopf/Kopf: Portal mit Gabelkopf A/B, der Tisch steht;
- 5-Achs Kopf/Tisch: Schwenkkopf B, Rundtisch C.

Die Achsen heißen wie an Siemens-Steuerungen (X1, Y1, Z1, A1 …, Spindel S1);
umbenennen geht in „Maschine bearbeiten“. Jedes Gelenk zeigt in die Richtung
seiner NC-Achse, so wie die Maschinen von FreeCAD-CAM sie beschreiben.

Der Baukasten baut auch die Maschinen der Prüfungen
(tests/beispielmaschinen.py). Die Körper sind grob (Quader, Zylinder), wie
es die Spezifikation für echte Maschinen vorsieht. Flächen eines Part::Box:
Face1 x=0, Face2 x=Länge, Face3 y=0, Face4 y=Breite, Face5 z=0 (unten),
Face6 z=Höhe (oben). Part::Cylinder: Face2 unten, Face3 oben (nachgesehen in
1.1.3) – für ein Drehgelenk gleich, beide Mitten liegen auf der Achse.

Die Drehmaschine hat Maße zum Eintragen (DrehmaschinenMasse): Bettneigung,
Winkel der Y-Achse, Wege, Revolverplätze, Drehzahl, Name – so baut
„Neue Maschine …“ aus wenigen Zahlen eine eigene (Manuel, 2026-09-26:
„so, dass es ein Leichtes ist, so etwas zu erstellen“). Steht Y schräg, legt
der Bauplan die schräge Achse gleich mit an.

Läuft ohne Oberfläche; mit Oberfläche bekommen Körper und Gelenke Farben
und Ansichten.
"""

import math
from dataclasses import dataclass

import FreeCAD as App

from . import PARAMETER_PFAD, schraege_achse
from . import kette as kette_modul
from . import maschine as m
from .sprache import tr

DOKUMENT = "Beispielmaschine"

# Farben (RGB 0…1): Guss dunkel, bewegte Teile heller, der Kopf blau.
GUSS = (0.36, 0.38, 0.41)
SCHLITTEN = (0.55, 0.58, 0.62)
TISCH = (0.70, 0.72, 0.75)
KOPF = (0.20, 0.45, 0.70)
SPINDEL = (0.82, 0.82, 0.84)
REVOLVER = (0.93, 0.93, 0.95)  # hell, damit er sich von Schlitten und Bett abhebt

# Die Bauarten, in der Reihenfolge der Auswahl (wie Manuel sie aufzählte).
DREHMASCHINE = "drehmaschine"
FRAESE_3 = "fraese3"
TISCH_TISCH = "tisch_tisch"
KOPF_KOPF = "kopf_kopf"
KOPF_TISCH = "kopf_tisch"
ARTEN = (DREHMASCHINE, FRAESE_3, TISCH_TISCH, KOPF_KOPF, KOPF_TISCH)

_ZULETZT = "Beispielmaschine"  # Schlüssel in den Einstellungen: zuletzt gewählte Bauart


class Baukasten:
    """Baut eine Assembly Schritt für Schritt: Körper, Bauteile mit LCS, Gelenke.

    Maße und Lagen in mm; x, y, z ist die Lage der Ecke bzw. der Mitte unten.
    Alles liegt im `rahmen`: ohne ihn in Weltkoordinaten; die Drehmaschine
    baut ihr Schrägbett in einem gekippten Rahmen, dort liegt die Bettfläche
    waagrecht. Richtungen (Zylinderachse, LCS, Gelenk) gelten im Rahmen.
    """

    def __init__(self, name):
        self.doc = App.newDocument(name)
        self.assembly = self.doc.addObject("Assembly::AssemblyObject", "Assembly")
        self.gelenke = self.assembly.newObject("Assembly::JointGroup", "Joints")
        self.rahmen = App.Placement()
        self.bezug = {}  # je Gelenk (Name) sein Koordinatensystem, wie gebaut, global

    def quader(self, name, laenge, breite, hoehe, x=0, y=0, z=0, farbe=None, gedreht=None):
        """Ein Quader mit der Ecke bei (x, y, z); `gedreht` (App.Placement im Rahmen)
        dreht ihn danach, etwa um die Revolverachse."""
        teil = self.assembly.newObject("Part::Box", name)
        teil.Length, teil.Width, teil.Height = laenge, breite, hoehe
        # Placement als Ganzes zuweisen: teil.Placement.Base = … änderte nur eine Kopie.
        teil.Placement = self._lage(x, y, z, gedreht=gedreht)
        _faerbe(teil, farbe)
        return teil

    def zylinder(self, name, radius, hoehe, x=0, y=0, z=0, farbe=None, achse=None):
        """Ein Zylinder mit der Mitte unten bei (x, y, z). `achse` ist die Richtung
        von unten nach oben, (1, 0, 0) etwa für einen liegenden; ohne steht er."""
        teil = self.assembly.newObject("Part::Cylinder", name)
        teil.Radius, teil.Height = radius, hoehe
        teil.Placement = self._lage(x, y, z, achse)
        _faerbe(teil, farbe)
        return teil

    def bauteil(self, name, koerper, lcs_name=None, lcs_hoehe=0, lcs_x=0, lcs_y=0):
        """Ein Part mit Körper (oder einer Liste von Körpern) und optional einem LCS
        darin – so, wie man eine Werkzeug- oder Werkstückaufnahme markiert.
        Gelenke greifen dann auf "<Körpername>.FaceN". Das Part liegt wie der
        erste Körper; das LCS bei (lcs_x, lcs_y, lcs_hoehe) in diesem Körper, von
        seiner Ecke bzw. der Mitte unten aus. Weitere LCS: lcs()."""
        liste = list(koerper) if isinstance(koerper, (list, tuple)) else [koerper]
        teil = self.assembly.newObject("App::Part", name)
        teil.Placement = liste[0].Placement
        for k in liste:
            lage = teil.Placement.inverse() * k.Placement
            self.assembly.removeObject(k)
            teil.addObject(k)
            k.Placement = lage
        lcs = None
        if lcs_name:
            lcs = self.doc.addObject("App::LocalCoordinateSystem", lcs_name)
            lcs.Placement = App.Placement(App.Vector(lcs_x, lcs_y, lcs_hoehe), App.Rotation())
            teil.addObject(lcs)
        return teil, lcs

    def lcs(self, teil, name, x, y, z, richtung=None, x_richtung=None):
        """Ein LCS im Bauteil, Ursprung bei (x, y, z); seine Z-Achse zeigt in
        `richtung` – die Werkzeugrichtung (von der Spitze zur Aufnahme) bzw. die
        Normale der Spannfläche. Ohne `richtung` zeigt sie nach oben.
        `x_richtung` legt die X-Achse fest – an einer Werkstückaufnahme die
        X-Richtung des Jobs."""
        lcs = self.doc.addObject("App::LocalCoordinateSystem", name)
        teil.addObject(lcs)
        lcs.Placement = self.lage_im_teil(teil, x, y, z, richtung, x_richtung)
        return lcs

    def lage_im_teil(self, teil, x, y, z, richtung=None, x_richtung=None):
        """Die Lage (x, y, z) mit Z-Achse in `richtung` (und X in `x_richtung`), bezogen
        auf das Bauteil."""
        return teil.Placement.inverse() * self._lage(x, y, z, richtung, x_richtung)

    def _lage(self, x, y, z, richtung=None, x_richtung=None, gedreht=None):
        drehung = App.Rotation()
        if richtung is not None and x_richtung is not None:
            z_achse, x_achse = App.Vector(*richtung), App.Vector(*x_richtung)
            drehung = App.Rotation(x_achse, z_achse.cross(x_achse), z_achse, "ZXY")
        elif richtung is not None:
            drehung = App.Rotation(App.Vector(0, 0, 1), App.Vector(*richtung))
        lage = App.Placement(App.Vector(x, y, z), drehung)
        if gedreht is not None:
            lage = gedreht * lage
        return self.rahmen * lage

    def fixieren(self, teil):
        import JointObject

        gelenk = self.gelenke.newObject("App::FeaturePython", "Fixiert_" + teil.Name)
        JointObject.GroundedJoint(gelenk, teil)
        if App.GuiUp:
            JointObject.ViewProviderGroundedJoint(gelenk.ViewObject)
        return gelenk

    def gelenk(self, name, art, teil1, flaeche1, teil2, flaeche2):
        """Ein Gelenk zwischen den Mitten zweier Flächen; die Normale der ersten
        ist seine Achse. Der Löser legt die Mitten aufeinander und verschiebt
        dafür Teile."""
        import JointObject

        # Flächen gibt es erst nach dem Neuberechnen der Körper.
        self.doc.recompute()
        gelenk = self.gelenke.newObject("App::FeaturePython", name)
        JointObject.Joint(gelenk, JointObject.JointTypes.index(art))
        if App.GuiUp:
            JointObject.ViewProviderJoint(gelenk.ViewObject)
        # Zweiter Eintrag = Bezugspunkt; die Fläche selbst heißt „Flächenmitte“.
        gelenk.Proxy.setJointConnectors(
            gelenk, [[teil1, [flaeche1, flaeche1]], [teil2, [flaeche2, flaeche2]]]
        )
        return gelenk

    def gelenk_wie_gebaut(
        self, name, art, teil1, flaeche1, teil2, flaeche2, richtung=None, stellung=0.0
    ):
        """Ein Gelenk, das die Teile lässt, wo sie gebaut sind – Stellung `stellung` (sonst 0):
        So zählen X und Z der Drehmaschine wie an der Maschine (P-2026-09-30-50).

        Beim Anlegen legt der Löser die Mitten der Flächen aufeinander, und
        jede Änderung am Versatz (Offset) löst vorab (preSolve) – mit einer
        Seite schon versetzt, der anderen noch nicht, klappt FreeCAD dabei
        Teile um (so hing der Fräskopf mit Oberfläche hinter dem Ständer).
        Deshalb kommen die Teile danach jedes Mal zurück. Der Versatz beider
        Seiten legt den Bezugspunkt auf die Mitte der Fläche von Seite 2 –
        bei einem Drehgelenk liegt dort die Drehachse. `richtung` (im Rahmen)
        dreht die Achse, etwa waagrecht für einen Tisch, der auf seinem
        Schlitten gleitet; ohne ist es die Normale der Flächen.
        """
        import UtilsAssembly

        lagen = {o: App.Placement(o.Placement) for o in self._teile()}
        gelenk = self.gelenk(name, art, teil1, flaeche1, teil2, flaeche2)
        self._zurueck(lagen)
        seite1 = UtilsAssembly.getJcsGlobalPlc(gelenk.Placement1, gelenk.Reference1)
        seite2 = UtilsAssembly.getJcsGlobalPlc(gelenk.Placement2, gelenk.Reference2)
        if richtung is None:
            drehung = seite2.Rotation
        else:
            achse = self.rahmen.Rotation.multVec(App.Vector(*richtung))
            drehung = App.Rotation(App.Vector(0, 0, 1), achse)
        ziel = App.Placement(seite2.Base, drehung)
        # Seite 1 um `stellung` längs der Achse zurück: So steht das Gelenk wie gebaut dort.
        zurueck = drehung.multVec(App.Vector(0, 0, 1)) * stellung
        gelenk.Offset1 = seite1.inverse() * App.Placement(ziel.Base - zurueck, drehung)
        gelenk.Offset2 = seite2.inverse() * ziel
        self._zurueck(lagen)
        self.bezug[name] = ziel
        return gelenk

    @staticmethod
    def _zurueck(lagen):
        for teil, lage in lagen.items():
            teil.Placement = lage

    def begrenze(self, gelenk, minimum, maximum):
        """Weg eines Gelenks: mm beim Schiebe-, Grad beim Drehgelenk – wie
        „Minimale/Maximale Länge“ bzw. „… Winkel“ am Gelenk."""
        if gelenk.JointType == "Revolute":
            gelenk.EnableAngleMin, gelenk.AngleMin = True, minimum
            gelenk.EnableAngleMax, gelenk.AngleMax = True, maximum
        else:
            gelenk.EnableLengthMin, gelenk.LengthMin = True, minimum
            gelenk.EnableLengthMax, gelenk.LengthMax = True, maximum

    def fertig(self):
        self.doc.recompute()
        return self.assembly

    def _teile(self):
        """Was der Löser verschieben kann – nicht Gelenke und nicht ihre Gruppe."""
        return [
            o
            for o in self.assembly.Group
            if hasattr(o, "Placement") and o.TypeId != "Assembly::JointGroup"
        ]


def _faerbe(teil, farbe):
    if farbe is not None and App.GuiUp:
        teil.ViewObject.ShapeColor = farbe


# --- Texte ----------------------------------------------------------------------


def titel(art):
    """Name der Bauart, wie in der Auswahl und am Maschinenobjekt."""
    return {
        DREHMASCHINE: tr("beispiel.drehmaschine"),
        FRAESE_3: tr("beispiel.fraese3"),
        TISCH_TISCH: tr("beispiel.tisch_tisch"),
        KOPF_KOPF: tr("beispiel.kopf_kopf"),
        KOPF_TISCH: tr("beispiel.kopf_tisch"),
    }[art]


def beschreibung(art):
    """Ein, zwei Sätze zur Bauart für die Auswahl."""
    return {
        DREHMASCHINE: tr("beispiel.drehmaschine.beschreibung"),
        FRAESE_3: tr("beispiel.fraese3.beschreibung"),
        TISCH_TISCH: tr("beispiel.tisch_tisch.beschreibung"),
        KOPF_KOPF: tr("beispiel.kopf_kopf.beschreibung"),
        KOPF_TISCH: tr("beispiel.kopf_tisch.beschreibung"),
    }[art]


def _dokument(art):
    """Name des Dokuments – ohne „/“, er wird beim Speichern der Dateiname."""
    return {
        DREHMASCHINE: tr("beispiel.drehmaschine.dokument"),
        FRAESE_3: tr("beispiel.fraese3.dokument"),
        TISCH_TISCH: tr("beispiel.tisch_tisch.dokument"),
        KOPF_KOPF: tr("beispiel.kopf_kopf.dokument"),
        KOPF_TISCH: tr("beispiel.kopf_tisch.dokument"),
    }[art]


def _neu(art):
    b = Baukasten(DOKUMENT)
    b.doc.Label = _dokument(art)
    return b


def _maschine(asm, art):
    ma = m.lege_maschine_an(asm)
    ma.Label = titel(art)
    return ma


def _linear(ma, gelenk, nc_name, eilgang, vorschub_max, beschleunigung):
    achse = m.neue_betriebsart(ma, gelenk, m.ART_LINEAR, nc_name)
    achse.Eilgang, achse.VorschubMax, achse.Beschleunigung = eilgang, vorschub_max, beschleunigung
    return achse


def _positionieren(ma, gelenk, nc_name, geschwindigkeit, endlos=False):
    achse = m.neue_betriebsart(ma, gelenk, m.ART_POSITIONIEREN, nc_name)
    achse.Geschwindigkeit, achse.Endlos = geschwindigkeit, endlos
    return achse


def _spindel(ma, gelenk, nc_name, drehzahl, hochlaufzeit):
    spindel = m.neue_betriebsart(ma, gelenk, m.ART_SPINDEL, nc_name)
    spindel.Drehzahl, spindel.Hochlaufzeit = drehzahl, hochlaufzeit
    return spindel


# --- Fräsmaschinen --------------------------------------------------------------


@dataclass
class FraesenMasse:
    """Die Maße der 3-Achs-Fräse, vorbelegt wie das Beispiel (Durchsicht W-004, D-26).

    Wege in mm als (Minimum, Maximum), gezählt ab der Stellung, in der die Maschine
    gebaut ist – 0 muss darin liegen.
    """

    name: str = ""  # leer: der Name des Beispiels
    weg_x: tuple = (-250.0, 250.0)
    weg_y: tuple = (-150.0, 120.0)
    weg_z: tuple = (-100.0, 250.0)
    drehzahl: float = 12000.0  # U/min der Spindel

    def fehler(self):
        """Was nicht passt, als Liste von (Feld, Satz); leer: alles gut."""
        ergebnis = _wege_fehler(self)
        if self.drehzahl <= 0:
            ergebnis.append(("drehzahl", tr("neu.drehzahl_fehlt")))
        return ergebnis


def _wege_fehler(masse, ohne_null=()):
    """(Feld, Satz) für jeden Weg, der leer oder zu lang ist oder 0 nicht umschließt – außer
    den Feldern in `ohne_null`: Z der Drehmaschine zählt ab der Spindelnase, dort liegt 0 nie
    im Weg (P-2026-09-30-50)."""
    ergebnis = []
    for feld in ("weg_x", "weg_y", "weg_z"):
        unten, oben = getattr(masse, feld)
        if not -GROESSTER_WEG <= unten < oben <= GROESSTER_WEG:
            ergebnis.append((feld, tr("neu.weg_leer")))
        elif feld not in ohne_null and not unten <= 0 <= oben:
            ergebnis.append((feld, tr("neu.weg_bereich")))
    return ergebnis


def _benenne(asm, ma, name):
    """Gibt Maschine und Dokument den eingetragenen Namen – leer bleibt der des Beispiels."""
    if name.strip():
        ma.Label = name.strip()
        # Der Name des Dokuments wird beim Speichern der Dateiname – ohne „/“.
        asm.Document.Label = name.strip().replace("/", "-").replace("\\", "-")


def fraesmaschine(masse=None, spanneisen=True):
    """3-Achs-Fräse: Kreuztisch X/Y, Fräskopf Z, Spindel S1.

    Maschinenobjekt ausgefüllt: X1, Y1, Z1 mit Eilgang, Höchstvorschub und
    Beschleunigung, S1 mit Drehzahl, Werkzeugaufnahme an der Spindelnase,
    Werkstückaufnahme mitten auf dem Tisch. Links und rechts vom Spannplatz je
    ein Spanneisen (40 × 40 × 60 mm mit Mutter, 100 mm von der Mitte bis zu
    seiner Innenseite) – etwas, woran man in der Kollisionsprüfung (W-001 4c)
    anstoßen kann: Die Spindelnase kommt bis 30 mm über den Tisch.
    `masse` (FraesenMasse) ändert Wege, Drehzahl und Name; `spanneisen=False` lässt die
    Spanneisen weg. Gibt (Assembly, Maschine) zurück.
    """
    masse = masse or FraesenMasse()
    b = _neu(FRAESE_3)
    bett = b.quader("Bett", 800, 900, 120, farbe=GUSS)
    staender = b.quader("Staender", 260, 250, 1000, x=270, y=650, z=120, farbe=GUSS)
    sattel = b.quader("Sattel", 460, 320, 70, x=170, y=190, z=120, farbe=SCHLITTEN)
    tisch, spannplatz = b.bauteil(
        "Tisch",
        b.quader("Tischplatte", 700, 280, 60, x=50, y=210, z=190, farbe=TISCH),
        lcs_name="Spannplatz",
        lcs_x=350,
        lcs_y=140,
        lcs_hoehe=60,
    )
    eisen = []
    if spanneisen:
        # Der Spannplatz liegt bei x 400, y 350 auf der Tischplatte (z 250).
        for name, x in (("Spanneisen_links", 400 - 100 - 40), ("Spanneisen_rechts", 400 + 100)):
            eisen.append(b.quader(name, 40, 40, 60, x=x, y=350 - 20, z=250, farbe=SPINDEL))
    kopf = b.quader("Fraeskopf", 200, 400, 300, x=300, y=250, z=520, farbe=KOPF)
    spindel, spindelnase = b.bauteil(
        "Spindel",
        b.zylinder("Spindelkoerper", 45, 140, x=400, y=350, z=380, farbe=SPINDEL),
        lcs_name="Spindelnase",
    )

    b.fixieren(bett)
    b.gelenk_wie_gebaut("Staender_fest", "Fixed", bett, "Face6", staender, "Face5")
    y = b.gelenk_wie_gebaut("Y", "Slider", bett, "Face6", sattel, "Face5", richtung=(0, 1, 0))
    b.begrenze(y, *masse.weg_y)
    x = b.gelenk_wie_gebaut(
        "X", "Slider", sattel, "Face6", tisch, "Tischplatte.Face5", richtung=(1, 0, 0)
    )
    b.begrenze(x, *masse.weg_x)
    for teil in eisen:
        b.gelenk_wie_gebaut(
            f"{teil.Label}_fest", "Fixed", tisch, "Tischplatte.Face6", teil, "Face5"
        )
    z = b.gelenk_wie_gebaut("Z", "Slider", staender, "Face3", kopf, "Face4", richtung=(0, 0, 1))
    b.begrenze(z, *masse.weg_z)
    s = b.gelenk_wie_gebaut(
        "Spindelachse", "Revolute", kopf, "Face5", spindel, "Spindelkoerper.Face2"
    )
    asm = b.fertig()

    ma = _maschine(asm, FRAESE_3)
    _linear(ma, x, "X1", 20000, 10000, 3)
    _linear(ma, y, "Y1", 20000, 10000, 3)
    _linear(ma, z, "Z1", 15000, 10000, 3)
    s1 = _spindel(ma, s, "S1", masse.drehzahl, 1.5)
    m.neue_aufnahme(ma, spindelnase, m.AUFNAHME_WERKZEUG, tr("beispiel.spindel"), spindel=s1)
    m.neue_aufnahme(ma, spannplatz, m.AUFNAHME_WERKSTUECK, tr("beispiel.tisch"))
    _benenne(asm, ma, masse.name)
    asm.Document.recompute()
    return asm, ma


def _fahrstaender(b, bett):
    """Fahrender Ständer (X) mit Stößel (Y) und Kopfschlitten (Z): Alle drei
    Linearachsen sitzen im Kopf, der Tisch bleibt für die Drehachsen frei.
    Gibt (Kopfschlitten, X, Y, Z) zurück; die Wege von Y und Z begrenzt die
    Maschine, je nach Kopf und Tisch."""
    staender = b.quader("Staender", 420, 420, 1050, x=440, y=760, z=250, farbe=GUSS)
    stoessel = b.quader("Stoessel", 300, 700, 220, x=500, y=380, z=1300, farbe=SCHLITTEN)
    kopf = b.quader("Kopfschlitten", 260, 200, 560, x=520, y=180, z=1000, farbe=KOPF)
    x = b.gelenk_wie_gebaut("X", "Slider", bett, "Face6", staender, "Face5", richtung=(1, 0, 0))
    b.begrenze(x, -320, 320)
    y = b.gelenk_wie_gebaut("Y", "Slider", staender, "Face6", stoessel, "Face5", richtung=(0, 1, 0))
    z = b.gelenk_wie_gebaut("Z", "Slider", stoessel, "Face3", kopf, "Face4", richtung=(0, 0, 1))
    return kopf, x, y, z


def _fuenfachs_werte(ma, x, y, z, s, spindelnase, spannplatz):
    """Was alle 5-Achs-Beispiele gleich haben: X1, Y1, Z1, S1 und die Aufnahmen."""
    _linear(ma, x, "X1", 30000, 15000, 5)
    _linear(ma, y, "Y1", 30000, 15000, 5)
    _linear(ma, z, "Z1", 30000, 15000, 5)
    s1 = _spindel(ma, s, "S1", 18000, 2)
    m.neue_aufnahme(ma, spindelnase, m.AUFNAHME_WERKZEUG, tr("beispiel.spindel"), spindel=s1)
    m.neue_aufnahme(ma, spannplatz, m.AUFNAHME_WERKSTUECK, tr("beispiel.rundtisch"))


def fuenfachs_tisch_tisch():
    """5-Achs-Fräse Tisch/Tisch: Schwenkbrücke (A, um X) mit Rundtisch (C);
    X, Y, Z im Kopf. Gibt (Assembly, Maschine) zurück."""
    b = _neu(TISCH_TISCH)
    bett = b.quader("Bett", 1300, 1200, 250, farbe=GUSS)
    b.fixieren(bett)
    kopf, x, y, z = _fahrstaender(b, bett)
    b.begrenze(y, -200, 250)
    b.begrenze(z, -260, 150)
    spindel, spindelnase = b.bauteil(
        "Spindel",
        b.zylinder("Spindelkoerper", 55, 160, x=650, y=280, z=840, farbe=SPINDEL),
        lcs_name="Spindelnase",
    )
    s = b.gelenk_wie_gebaut(
        "Spindelachse", "Revolute", kopf, "Face5", spindel, "Spindelkoerper.Face2"
    )

    # Die Wiege hängt mit Zapfen in zwei Lagerböcken; ein Drehgelenk hat nur
    # der linke – ein zweites am rechten kann die Assembly nicht lösen.
    lager_l = b.quader("LagerbockLinks", 130, 260, 440, x=100, y=200, z=250, farbe=GUSS)
    lager_r = b.quader("LagerbockRechts", 130, 260, 440, x=1070, y=200, z=250, farbe=GUSS)
    wiege, _ = b.bauteil(
        "Wiege",
        [
            b.quader("Wiegenboden", 700, 300, 70, x=300, y=180, z=390, farbe=SCHLITTEN),
            b.quader("WangeLinks", 70, 300, 310, x=230, y=180, z=390, farbe=SCHLITTEN),
            b.quader("WangeRechts", 70, 300, 310, x=1000, y=180, z=390, farbe=SCHLITTEN),
            b.zylinder("ZapfenLinks", 55, 150, x=90, y=330, z=620, achse=(1, 0, 0), farbe=SPINDEL),
            b.zylinder(
                "ZapfenRechts", 55, 150, x=1060, y=330, z=620, achse=(1, 0, 0), farbe=SPINDEL
            ),
        ],
    )
    rundtisch, spannplatz = b.bauteil(
        "Rundtisch",
        b.zylinder("Tischscheibe", 140, 80, x=650, y=330, z=460, farbe=TISCH),
        lcs_name="Spannplatz",
        lcs_hoehe=80,
    )
    b.gelenk_wie_gebaut("LagerLinks_fest", "Fixed", bett, "Face6", lager_l, "Face5")
    b.gelenk_wie_gebaut("LagerRechts_fest", "Fixed", bett, "Face6", lager_r, "Face5")
    a = b.gelenk_wie_gebaut(
        "A", "Revolute", lager_l, "Face2", wiege, "ZapfenLinks.Face3", richtung=(1, 0, 0)
    )
    b.begrenze(a, -120, 120)
    c = b.gelenk_wie_gebaut(
        "C",
        "Revolute",
        wiege,
        "Wiegenboden.Face6",
        rundtisch,
        "Tischscheibe.Face3",
        richtung=(0, 0, 1),
    )
    asm = b.fertig()

    ma = _maschine(asm, TISCH_TISCH)
    _positionieren(ma, a, "A1", 25)
    _positionieren(ma, c, "C1", 50, endlos=True)
    _fuenfachs_werte(ma, x, y, z, s, spindelnase, spannplatz)
    asm.Document.recompute()
    return asm, ma


def fuenfachs_kopf_tisch():
    """5-Achs-Fräse Kopf/Tisch: Schwenkkopf (B, um Y) vorn am Kopfschlitten,
    Rundtisch (C) im Maschinentisch; X, Y, Z im Kopf. Gibt (Assembly, Maschine) zurück."""
    b = _neu(KOPF_TISCH)
    bett = b.quader("Bett", 1300, 1200, 250, farbe=GUSS)
    b.fixieren(bett)
    kopf, x, y, z = _fahrstaender(b, bett)
    b.begrenze(y, -150, 300)
    b.begrenze(z, -280, 100)
    schwenkkopf = b.quader("Schwenkkopf", 200, 180, 300, x=550, y=0, z=950, farbe=KOPF)
    spindel, spindelnase = b.bauteil(
        "Spindel",
        b.zylinder("Spindelkoerper", 55, 160, x=650, y=90, z=790, farbe=SPINDEL),
        lcs_name="Spindelnase",
    )
    unterbau = b.quader("Tischunterbau", 600, 600, 150, x=350, y=20, z=250, farbe=GUSS)
    rundtisch, spannplatz = b.bauteil(
        "Rundtisch",
        b.zylinder("Tischscheibe", 260, 90, x=650, y=320, z=400, farbe=TISCH),
        lcs_name="Spannplatz",
        lcs_hoehe=90,
    )
    # Der Schwenkkopf dreht um die Mitte seiner Rückseite – dort sitzt er am Kopfschlitten.
    schwenk = b.gelenk_wie_gebaut(
        "B", "Revolute", kopf, "Face3", schwenkkopf, "Face4", richtung=(0, 1, 0)
    )
    b.begrenze(schwenk, -110, 110)
    s = b.gelenk_wie_gebaut(
        "Spindelachse", "Revolute", schwenkkopf, "Face5", spindel, "Spindelkoerper.Face2"
    )
    b.gelenk_wie_gebaut("Tischunterbau_fest", "Fixed", bett, "Face6", unterbau, "Face5")
    c = b.gelenk_wie_gebaut(
        "C", "Revolute", unterbau, "Face6", rundtisch, "Tischscheibe.Face3", richtung=(0, 0, 1)
    )
    asm = b.fertig()

    ma = _maschine(asm, KOPF_TISCH)
    _positionieren(ma, schwenk, "B1", 30)
    _positionieren(ma, c, "C1", 50, endlos=True)
    _fuenfachs_werte(ma, x, y, z, s, spindelnase, spannplatz)
    asm.Document.recompute()
    return asm, ma


def fuenfachs_kopf_kopf():
    """5-Achs-Fräse Kopf/Kopf: Portal (Y) mit Querschlitten (X) und Stößel (Z),
    unten am Stößel ein Gabelkopf – A dreht um X, darin B um Y. Der Tisch
    steht fest. Gibt (Assembly, Maschine) zurück."""
    b = _neu(KOPF_KOPF)
    bett = b.quader("Bett", 1600, 1500, 250, farbe=GUSS)
    b.fixieren(bett)
    tisch, spannplatz = b.bauteil(
        "Tisch",
        b.quader("Tischplatte", 1000, 800, 120, x=300, y=250, z=250, farbe=TISCH),
        lcs_name="Spannplatz",
        lcs_x=500,
        lcs_y=400,
        lcs_hoehe=120,
    )
    portal, _ = b.bauteil(
        "Portal",
        [
            b.quader("SaeuleLinks", 160, 240, 1550, x=40, y=1000, z=250, farbe=GUSS),
            b.quader("SaeuleRechts", 160, 240, 1550, x=1400, y=1000, z=250, farbe=GUSS),
            b.quader("Traverse", 1520, 240, 250, x=40, y=1000, z=1800, farbe=GUSS),
        ],
    )
    querschlitten = b.quader("Querschlitten", 360, 160, 400, x=620, y=840, z=1700, farbe=SCHLITTEN)
    # Unten am Stößel die Gabel für A, am A-Kopf die Gabel für B; die Zapfen
    # gehen durch beide Wangen, ihre Stirnseiten liegen auf den Drehachsen.
    stoessel, _ = b.bauteil(
        "Stoessel",
        [
            b.quader("Stoesselkoerper", 240, 240, 900, x=680, y=600, z=1220, farbe=KOPF),
            b.quader("GabelLinks", 40, 160, 160, x=685, y=640, z=1060, farbe=KOPF),
            b.quader("GabelRechts", 40, 160, 160, x=875, y=640, z=1060, farbe=KOPF),
        ],
    )
    a_kopf, _ = b.bauteil(
        "AKopf",
        [
            b.quader("AGehaeuse", 140, 200, 160, x=730, y=620, z=990, farbe=KOPF),
            b.zylinder("AZapfen", 35, 250, x=675, y=720, z=1120, achse=(1, 0, 0), farbe=SPINDEL),
            b.quader("GabelVorn", 110, 35, 140, x=745, y=620, z=850, farbe=KOPF),
            b.quader("GabelHinten", 110, 35, 140, x=745, y=785, z=850, farbe=KOPF),
        ],
    )
    b_kopf, _ = b.bauteil(
        "BKopf",
        [
            b.quader("BGehaeuse", 120, 120, 170, x=740, y=660, z=770, farbe=KOPF),
            b.zylinder("BZapfen", 30, 220, x=800, y=610, z=910, achse=(0, 1, 0), farbe=SPINDEL),
        ],
    )
    spindel, spindelnase = b.bauteil(
        "Spindel",
        b.zylinder("Spindelkoerper", 40, 120, x=800, y=720, z=650, farbe=SPINDEL),
        lcs_name="Spindelnase",
    )

    b.gelenk_wie_gebaut("Tisch_fest", "Fixed", bett, "Face6", tisch, "Tischplatte.Face5")
    y = b.gelenk_wie_gebaut(
        "Y", "Slider", bett, "Face6", portal, "SaeuleLinks.Face5", richtung=(0, 1, 0)
    )
    b.begrenze(y, -650, 250)
    x = b.gelenk_wie_gebaut(
        "X", "Slider", portal, "Traverse.Face3", querschlitten, "Face4", richtung=(1, 0, 0)
    )
    b.begrenze(x, -560, 560)
    z = b.gelenk_wie_gebaut(
        "Z", "Slider", querschlitten, "Face3", stoessel, "Stoesselkoerper.Face4", richtung=(0, 0, 1)
    )
    b.begrenze(z, -250, 300)
    a = b.gelenk_wie_gebaut(
        "A", "Revolute", stoessel, "GabelLinks.Face2", a_kopf, "AZapfen.Face3", richtung=(1, 0, 0)
    )
    b.begrenze(a, -100, 100)
    schwenk = b.gelenk_wie_gebaut(
        "B", "Revolute", a_kopf, "GabelVorn.Face4", b_kopf, "BZapfen.Face3", richtung=(0, 1, 0)
    )
    b.begrenze(schwenk, -100, 100)
    s = b.gelenk_wie_gebaut(
        "Spindelachse", "Revolute", b_kopf, "BGehaeuse.Face5", spindel, "Spindelkoerper.Face2"
    )
    asm = b.fertig()

    ma = _maschine(asm, KOPF_KOPF)
    _linear(ma, x, "X1", 40000, 20000, 4)
    _linear(ma, y, "Y1", 40000, 20000, 3)
    _linear(ma, z, "Z1", 30000, 15000, 4)
    _positionieren(ma, a, "A1", 30)
    _positionieren(ma, schwenk, "B1", 30)
    s1 = _spindel(ma, s, "S1", 24000, 2)
    m.neue_aufnahme(ma, spindelnase, m.AUFNAHME_WERKZEUG, tr("beispiel.spindel"), spindel=s1)
    m.neue_aufnahme(ma, spannplatz, m.AUFNAHME_WERKSTUECK, tr("beispiel.tisch"))
    asm.Document.recompute()
    return asm, ma


# --- Drehmaschine ---------------------------------------------------------------

# Das Schrägbett steigt nach hinten an, im Beispiel um 45°. In seinem Rahmen
# liegt die Bettfläche waagrecht: x ist die Spindelachse (Z der Maschine), y
# quer im Bett (X, weg von der Spindelachse), z senkrecht zum Bett (Y).
# Gekippt um die Spindelachse, angehoben auf Spitzenhöhe.
SPITZENHOEHE = 800  # mm über dem Boden, wo der Rahmen beginnt
# Die Revolverachse im Rahmen (bei x = 0) und die Plätze auf der Scheibe.
REVOLVERACHSE = App.Vector(0, 405, 350)
STIRN_SCHEIBE = 710.0  # x der Stirn der Revolverscheibe, zum Futter hin
DICKE_SCHEIBE = 110.0  # mm
HOEHE_AUFNAHME = 10.0  # mm – so weit steht der Ring einer Aufnahme vor der Scheibe
ABSTAND_AUFNAHMEN_RAND = 40.0  # mm vom Rand der Scheibe bis zur Mitte der Aufnahmen (Stirn)
# Die Bauarten des Revolvers (P-2026-09-30-52): Aufnahmen an der Stirn oder am Umfang.
REVOLVER_STIRN, REVOLVER_UMFANG = "stirn", "umfang"
REVOLVERARTEN = (REVOLVER_STIRN, REVOLVER_UMFANG)
VDI_GROESSEN = (20, 25, 30, 40, 50, 60)  # mm – Schaft-Ø der Halter
SCHEIBE_BEREICH = (240.0, 600.0)  # mm Ø der Revolverscheibe

# Was sich in „Neue Maschine …“ eintragen lässt, und in welchen Grenzen.
BETTNEIGUNG_BEREICH = (0.0, 60.0)  # Grad; 0 ist ein Flachbett
Y_WINKEL_BEREICH = (-60.0, 60.0)  # Grad; 0 heißt Y rechtwinklig zu X
PLAETZE_BEREICH = (4, 24)
# mm, je Richtung – auch lange Maschinen (Manuel, 2026-09-30: Z ließ sich nur bis 999
# eintippen, „es gibt maschinen die sind deutlich länger“)
GROESSTER_WEG = 10000.0


@dataclass
class DrehmaschinenMasse:
    """Die Maße der Drehmaschine, vorbelegt wie das Beispiel.

    Wege in mm als (Minimum, Maximum), gezählt wie an der Maschine – bis zum Bezugspunkt
    des Revolvers, der Mitte der VDI-Aufnahme in Arbeitsstellung an ihrer Stirn: X ab der
    Spindelachse (Radius, 0 muss darin liegen), Z ab der Spindelnase, Y ab der Mitte der
    Spindel (0 muss darin liegen). Manuel (2026-09-30): „bei MEINER maschine ... ist x 0 genau
    die MITTE von der Vdi aufnahme“. Gebaut steht die Maschine bei X 275 und Z 220; liegt das
    außerhalb der Wege, fährt sie hinein. `y_winkel` ungleich 0 macht Y zur schrägen Achse
    (W-001, Abschnitt 7c). `x_durchmesser`: X zählt an der Steuerung im Durchmesser, wie an
    fast jeder Drehmaschine – X1 merkt es sich; `weg_x` bleibt trotzdem der Radius.
    """

    name: str = ""  # leer: der Name des Beispiels
    bettneigung: float = 45.0
    y_winkel: float = 0.0
    # Bis über die Spindelachse hinaus: Ein axiales Werkzeug bohrt bei X 0 mitten ins Teil,
    # ein radiales erreicht jeden Radius.
    weg_x: tuple = (-25.0, 425.0)
    weg_y: tuple = (-60.0, 60.0)
    # Bis vor das Futter (90 mm vor der Spindelnase): Eine Stange aus der 4-Achs-Bearbeitung
    # (W-003) muss bis dorthin erreichbar sein.
    weg_z: tuple = (0.0, 520.0)
    plaetze: int = 12
    drehzahl: float = 5000.0  # U/min der Hauptspindel
    # Der Revolver (P-2026-09-30-52): Aufnahmen an der Stirn oder am Umfang, Scheiben-Ø,
    # VDI-Größe (der Ring um die Bohrung).
    revolver: str = REVOLVER_STIRN
    scheibe: float = 340.0
    vdi: int = 30
    # X im Durchmesser (Manuel, 2026-09-30: „Ja mit Umschalter wichtig ist ja nur was dann
    # beim Postprozess raus kommt“, P-2026-09-30-54).
    x_durchmesser: bool = True

    def fehler(self):
        """Was nicht passt, als Liste von (Feld, Satz); leer: alles gut."""
        ergebnis = []
        if not BETTNEIGUNG_BEREICH[0] <= self.bettneigung <= BETTNEIGUNG_BEREICH[1]:
            ergebnis.append(("bettneigung", tr("neu.bettneigung_bereich")))
        if not Y_WINKEL_BEREICH[0] <= self.y_winkel <= Y_WINKEL_BEREICH[1]:
            ergebnis.append(("y_winkel", tr("neu.y_winkel_bereich")))
        ergebnis += _wege_fehler(self, ohne_null=("weg_z",))
        if not PLAETZE_BEREICH[0] <= self.plaetze <= PLAETZE_BEREICH[1]:
            ergebnis.append(("plaetze", tr("neu.plaetze_bereich")))
        if self.drehzahl <= 0:
            ergebnis.append(("drehzahl", tr("neu.drehzahl_fehlt")))
        if self.revolver not in REVOLVERARTEN:
            ergebnis.append(("revolver", tr("neu.revolver_unbekannt")))
        if not SCHEIBE_BEREICH[0] <= self.scheibe <= SCHEIBE_BEREICH[1]:
            ergebnis.append(("scheibe", tr("neu.scheibe_bereich")))
        if self.vdi not in VDI_GROESSEN:
            ergebnis.append(("vdi", tr("neu.vdi_unbekannt")))
        return ergebnis


def _schraegbett(neigung):
    """Der Rahmen des Betts: um `neigung` Grad um die Spindelachse gekippt, auf Spitzenhöhe."""
    return App.Placement(App.Vector(0, 0, SPITZENHOEHE), App.Rotation(App.Vector(1, 0, 0), neigung))


def _auf_der_scheibe(winkel, radius):
    """Punkt (0, y, z) im Rahmen: `radius` von der Revolverachse, um `winkel` Grad
    vom Platz P1 aus gedreht. P1 zeigt zur Spindelachse."""
    return REVOLVERACHSE + _nach_aussen(winkel) * radius


def _nach_aussen(winkel):
    """Die Richtung von der Revolverachse zum Platz, der um `winkel` Grad von P1 aus gedreht
    ist – bei P1 zur Spindelachse hin."""
    return App.Rotation(App.Vector(1, 0, 0), winkel).multVec(App.Vector(0, -1, 0))


def _revolver(b, masse):
    """Die Revolverscheibe mit ihren Aufnahmen (VDI) und das LCS von P1; gibt (Revolver,
    LCS) zurück. Zwei Bauarten (Manuel, 2026-09-30, P-2026-09-30-52):

    - **VDI in der Stirn** (REVOLVER_STIRN, wie Manuels): die Aufnahmen im Kreis an der
      Stirn der Scheibe, zum Futter hin; ein gerader Halter steht längs Z, ein gewinkelter
      („VDI30 angetrieben radial“) radial. Am Umfang nichts – dort stieß vorher eine
      angedeutete Station ans Teil, die es an so einem Revolver nicht gibt.
    - **VDI am Umfang** (REVOLVER_UMFANG, Sternrevolver): die Aufnahmen am Umfang, radial;
      ein gerader Halter steht radial zur Spindelachse, ein gewinkelter längs Z, zum Futter
      hin („vorne parallel zur Maschinen-Z-Achse fräsen“).

    P1 zeigt zur Spindelachse. Das LCS liegt auf der Achse der Aufnahme an ihrer Stirn (dort
    liegt der Halter an – der Bezugspunkt, bis zu dem X und Z zählen); Z von der Spitze eines
    geraden Werkzeugs zur Aufnahme, X in die Richtung, in die ein gewinkelter Halter das
    Werkzeug kippt (halter.lage)."""
    achse = REVOLVERACHSE
    radius = masse.scheibe / 2
    ring = masse.vdi  # mm – Radius des Rings um die Bohrung
    teilung = 2 * math.pi * radius / masse.plaetze
    scheibe = b.zylinder(
        "Revolverscheibe",
        radius,
        DICKE_SCHEIBE,
        x=STIRN_SCHEIBE,
        y=achse.y,
        z=achse.z,
        achse=(1, 0, 0),
        farbe=REVOLVER,
    )
    aufnahmen = []
    if masse.revolver == REVOLVER_UMFANG:
        mitte_x = STIRN_SCHEIBE + DICKE_SCHEIBE / 2
        ring = min(ring, 0.42 * teilung)  # Luft dazwischen, auch bei 24 Plätzen
        for nummer in range(1, masse.plaetze + 1):
            winkel = (nummer - 1) * 360.0 / masse.plaetze
            fuss = _auf_der_scheibe(winkel, radius)
            aussen = _nach_aussen(winkel)
            aufnahmen.append(
                b.zylinder(
                    f"Aufnahme{nummer:02d}",
                    ring,
                    HOEHE_AUFNAHME,
                    x=mitte_x,
                    y=fuss.y,
                    z=fuss.z,
                    achse=(0, aussen.y, aussen.z),
                    farbe=SCHLITTEN,
                )
            )
        stirn1 = _auf_der_scheibe(0.0, radius + HOEHE_AUFNAHME)
        ursprung, richtung, x_richtung = (mitte_x, stirn1.y, stirn1.z), (0, 1, 0), (-1, 0, 0)
    else:
        kreis = radius - ABSTAND_AUFNAHMEN_RAND
        ring = min(ring, 0.42 * 2 * math.pi * kreis / masse.plaetze)
        for nummer in range(1, masse.plaetze + 1):
            mitte = _auf_der_scheibe((nummer - 1) * 360.0 / masse.plaetze, kreis)
            aufnahmen.append(
                b.zylinder(
                    f"Aufnahme{nummer:02d}",
                    ring,
                    HOEHE_AUFNAHME,
                    x=STIRN_SCHEIBE - HOEHE_AUFNAHME,
                    y=mitte.y,
                    z=mitte.z,
                    achse=(1, 0, 0),
                    farbe=SCHLITTEN,
                )
            )
        mitte1 = _auf_der_scheibe(0.0, kreis)
        ursprung = (STIRN_SCHEIBE - HOEHE_AUFNAHME, mitte1.y, mitte1.z)
        richtung, x_richtung = (1, 0, 0), (0, -1, 0)
    revolver, _ = b.bauteil("Revolver", [scheibe, *aufnahmen])
    platz1 = b.lcs(revolver, "Platz", *ursprung, richtung=richtung, x_richtung=x_richtung)
    return revolver, platz1


def drehmaschine(masse=None):
    """Drehmaschine mit Y-Achse, Schrägbett wie eine CLX.

    Hauptspindel S1 (Drehzahl) und C1 (positionieren) – ihre Achse ist Z.
    Auf dem Bett Z-Schlitten, X-Schlitten, darauf Y-Schlitten mit dem
    Revolver T (12 Plätze). Jeder Platz ist eine Aufnahme (VDI30), alle am
    Werkzeugantrieb S3 – an der Stirn der Scheibe oder an ihrem Umfang (_revolver()).
    Halter trägt der Revolver nicht fest: Sie kommen mit den Werkzeugen aus der
    Werkzeugverwaltung (W-002 Stufe E, Manuel 2026-09-30) und stellen das Werkzeug zur
    Aufnahme. Die Werkzeuge selbst zeigt das Prüffenster. Das Futter ist die
    Werkstückaufnahme. `masse` (DrehmaschinenMasse) ändert Bettneigung, Wege, Plätze,
    Drehzahl, Revolver und Name; steht Y schräg, kommt die schräge Achse dazu. Gibt
    (Assembly, Maschine) zurück.
    """
    masse = masse or DrehmaschinenMasse()
    b = _neu(DREHMASCHINE)
    fuss = b.quader("Maschinenfuss", 1700, 1400, 500, x=-100, y=-300, farbe=GUSS)
    rueckwand = b.quader("Rueckwand", 1700, 400, 450, x=-100, y=700, z=500, farbe=GUSS)
    b.fixieren(fuss)
    b.gelenk_wie_gebaut("Rueckwand_fest", "Fixed", fuss, "Face6", rueckwand, "Face5")

    b.rahmen = _schraegbett(masse.bettneigung)
    bett = b.quader("Bett", 1500, 1200, 700, y=-350, z=-700, farbe=GUSS)
    spindelkasten = b.quader("Spindelkasten", 380, 520, 620, y=-260, farbe=GUSS)
    spindel, _ = b.bauteil(
        "Spindel",
        [
            b.zylinder("Spindelnase", 110, 100, x=380, z=350, achse=(1, 0, 0), farbe=SPINDEL),
            b.zylinder("Futter", 140, 90, x=480, z=350, achse=(1, 0, 0), farbe=SPINDEL),
        ],
    )
    # Das LCS am Futter ist das Koordinatensystem des Jobs: Z aus der
    # Spannfläche heraus, X von der Spindelachse zum Werkzeug – wie X1.
    spannflaeche = b.lcs(
        spindel, "Spannflaeche", 570, 0, 350, richtung=(1, 0, 0), x_richtung=(0, 1, 0)
    )
    z_schlitten = b.quader("ZSchlitten", 350, 680, 90, x=800, y=120, farbe=SCHLITTEN)
    x_schlitten = b.quader("XSchlitten", 310, 160, 510, x=820, y=480, z=90, farbe=SCHLITTEN)
    y_schlitten = b.quader("YSchlitten", 280, 150, 280, x=820, y=330, z=210, farbe=KOPF)

    revolver, platz1 = _revolver(b, masse)
    antrieb, _ = b.bauteil(
        "Antrieb",
        b.zylinder(
            "Antriebsmotor",
            60,
            120,
            x=1100,
            y=REVOLVERACHSE.y,
            z=REVOLVERACHSE.z,
            achse=(1, 0, 0),
            farbe=KOPF,
        ),
    )

    b.gelenk_wie_gebaut("Bett_fest", "Fixed", fuss, "Face6", bett, "Face5")
    b.gelenk_wie_gebaut("Spindelkasten_fest", "Fixed", bett, "Face6", spindelkasten, "Face5")
    hauptspindel = b.gelenk_wie_gebaut(
        "Hauptspindel",
        "Revolute",
        spindelkasten,
        "Face2",
        spindel,
        "Spindelnase.Face3",
        richtung=(1, 0, 0),
    )
    # X und Z zählen wie an der Maschine: bis zum Bezugspunkt des Revolvers (P1, die Mitte
    # der Aufnahme an ihrer Stirn), X ab der Spindelachse, Z ab der Spindelnase – so weit
    # stehen sie gebaut. Die Wege bekommen die Gelenke erst in _in_die_wege(), falls die
    # gebaute Stellung außerhalb liegt.
    abstand = m.globale_platzierung(platz1).Base - b.bezug["Hauptspindel"].Base
    richtung_z = b.rahmen.Rotation.multVec(App.Vector(1, 0, 0))
    richtung_x = b.rahmen.Rotation.multVec(App.Vector(0, 1, 0))
    z = b.gelenk_wie_gebaut(
        "Z",
        "Slider",
        bett,
        "Face6",
        z_schlitten,
        "Face5",
        richtung=(1, 0, 0),
        stellung=abstand.dot(richtung_z),
    )
    x = b.gelenk_wie_gebaut(
        "X",
        "Slider",
        z_schlitten,
        "Face6",
        x_schlitten,
        "Face5",
        richtung=(0, 1, 0),
        stellung=abstand.dot(richtung_x),
    )
    y = b.gelenk_wie_gebaut(
        "Y", "Slider", x_schlitten, "Face3", y_schlitten, "Face4", richtung=(0, 0, 1)
    )
    b.begrenze(y, *masse.weg_y)
    revolverachse = b.gelenk_wie_gebaut(
        "Revolverachse",
        "Revolute",
        y_schlitten,
        "Face1",
        revolver,
        "Revolverscheibe.Face2",
        richtung=(1, 0, 0),
    )
    werkzeugantrieb = b.gelenk_wie_gebaut(
        "Werkzeugantrieb",
        "Revolute",
        y_schlitten,
        "Face2",
        antrieb,
        "Antriebsmotor.Face3",
        richtung=(1, 0, 0),
    )
    asm = b.fertig()

    ma = _maschine(asm, DREHMASCHINE)
    x1 = _linear(ma, x, "X1", 30000, 10000, 6)
    x1.Durchmesser = bool(masse.x_durchmesser)
    y1 = _linear(ma, y, "Y1", 12000, 5000, 4)
    _linear(ma, z, "Z1", 30000, 10000, 6)
    _spindel(ma, hauptspindel, "S1", masse.drehzahl, 2.5)
    _positionieren(ma, hauptspindel, "C1", 100, endlos=True)
    t = m.neue_betriebsart(ma, revolverachse, m.ART_REVOLVER, "T")
    t.Schaltzeit = 0.25
    s3 = _spindel(ma, werkzeugantrieb, "S3", 4000, 0.5)
    m.neue_aufnahme(ma, spannflaeche, m.AUFNAHME_WERKSTUECK, tr("beispiel.futter"))
    plaetze = m.verteile_plaetze(ma, kette_modul.lies_kette(asm), t, platz1, masse.plaetze)
    for platz in plaetze:  # angetrieben: jeder Platz am Werkzeugantrieb
        platz.Spindel = s3
    _benenne(asm, ma, masse.name)
    asm.Document.recompute()
    if masse.y_winkel:
        # Die schräge Achse: Die Y-Führung dreht sich, der Revolver bleibt gerade.
        trafo = m.neue_schraege_achse(ma, y1, x1)
        kette = kette_modul.lies_kette(asm)
        schraege_achse.drehe_fuehrung(asm, kette, ma, trafo, masse.y_winkel)
    _in_die_wege(b, asm, {z: masse.weg_z, x: masse.weg_x})
    return asm, ma


def _in_die_wege(b, asm, wege):
    """Gibt den Gelenken ihre Wege ({Gelenk: (von, bis)}). Steht eines gebaut außerhalb, fährt
    die Maschine es erst hinein – etwa X gebaut 275, der Weg bis 250."""
    from . import verfahren as vf

    kette = kette_modul.lies_kette(asm)
    fahrt = vf.Verfahren(asm, kette)
    ziele = {}
    for gelenk, (unten, oben) in wege.items():
        achse = kette.achse_von(gelenk)
        jetzt = fahrt.stellung(achse)
        if not unten <= jetzt <= oben:
            ziele[achse] = min(max(jetzt, unten), oben)
    if ziele:
        fahrt.setze_alle(ziele)
    for gelenk, weg in wege.items():
        b.begrenze(gelenk, *weg)
    asm.Document.recompute()


BAUPLAENE = {
    DREHMASCHINE: drehmaschine,
    FRAESE_3: fraesmaschine,
    TISCH_TISCH: fuenfachs_tisch_tisch,
    KOPF_KOPF: fuenfachs_kopf_kopf,
    KOPF_TISCH: fuenfachs_kopf_tisch,
}


def zuletzt_gewaehlt():
    """Die zuletzt geladene Bauart – so steht die Auswahl beim nächsten Mal dort."""
    art = App.ParamGet(PARAMETER_PFAD).GetString(_ZULETZT, "")
    return art if art in ARTEN else ARTEN[0]


def lade(art, masse=None):
    """Baut die Beispielmaschine der Bauart in einem neuen Dokument und zeigt sie;
    gibt (Assembly, Maschine) zurück. `masse`: die eingetragenen Maße – bisher
    nur bei der Drehmaschine (DrehmaschinenMasse)."""
    App.ParamGet(PARAMETER_PFAD).SetString(_ZULETZT, art)
    asm, ma = BAUPLAENE[art](masse) if masse is not None else BAUPLAENE[art]()
    if App.GuiUp:
        import FreeCADGui

        # Die Gelenke bleiben im Baum; ihre Markierungen (weiße Scheiben mit Achsen)
        # verdeckten Revolver und Spindel. Wieder zeigen: im Baum „Joints“, Leertaste.
        for objekt in asm.Group:
            if objekt.TypeId == "Assembly::JointGroup":
                objekt.Visibility = False
        FreeCADGui.ActiveDocument.ActiveView.viewIsometric()
        FreeCADGui.SendMsgToActiveView("ViewFit")
    return asm, ma
