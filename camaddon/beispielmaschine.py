# SPDX-License-Identifier: LGPL-2.1-or-later
"""Eine fertig eingerichtete Beispielmaschine zum Ausprobieren (W-001).

Wer das Addon ausprobiert, soll nicht erst eine Maschine bauen müssen
(Manuel, 2026-09-26): „Beispielmaschine laden“ in „Maschine bearbeiten“ und
„Maschine verfahren“ legt ein neues Dokument mit einer Dreiachs-Fräsmaschine
an – Bett mit Ständer, Kreuztisch (Y-Schlitten, X-Tisch), Fräskopf (Z) und
Spindel –, ihr Maschinenobjekt schon ausgefüllt.

Der Baukasten baut auch die Beispielmaschinen der Prüfungen
(tests/beispielmaschinen.py). Die Körper sind grob (Quader, Zylinder), wie
es die Spezifikation für echte Maschinen vorsieht. Flächen eines Part::Box:
Face1 x=0, Face2 x=Länge, Face3 y=0, Face4 y=Breite, Face5 z=0 (unten),
Face6 z=Höhe (oben). Part::Cylinder: Face2 oben, Face3 unten.

Läuft ohne Oberfläche; mit Oberfläche bekommen Körper und Gelenke Farben
und Ansichten.
"""

import FreeCAD as App

from . import maschine as m
from .sprache import tr

DOKUMENT = "Beispielmaschine"

# Farben (RGB 0…1): Guss dunkel, bewegte Teile heller, der Kopf blau.
GUSS = (0.36, 0.38, 0.41)
SCHLITTEN = (0.55, 0.58, 0.62)
TISCH = (0.70, 0.72, 0.75)
KOPF = (0.20, 0.45, 0.70)
SPINDEL = (0.82, 0.82, 0.84)


class Baukasten:
    """Baut eine Assembly Schritt für Schritt: Körper, Bauteile mit LCS, Gelenke.

    Maße und Lagen in mm; x, y, z ist die Lage der Ecke bzw. der Mitte unten.
    """

    def __init__(self, name):
        self.doc = App.newDocument(name)
        self.assembly = self.doc.addObject("Assembly::AssemblyObject", "Assembly")
        self.gelenke = self.assembly.newObject("Assembly::JointGroup", "Joints")

    def quader(self, name, laenge, breite, hoehe, x=0, y=0, z=0, farbe=None):
        teil = self.assembly.newObject("Part::Box", name)
        teil.Length, teil.Width, teil.Height = laenge, breite, hoehe
        _stelle(teil, x, y, z)
        _faerbe(teil, farbe)
        return teil

    def zylinder(self, name, radius, hoehe, x=0, y=0, z=0, farbe=None):
        teil = self.assembly.newObject("Part::Cylinder", name)
        teil.Radius, teil.Height = radius, hoehe
        _stelle(teil, x, y, z)
        _faerbe(teil, farbe)
        return teil

    def bauteil(self, name, koerper, lcs_name=None, lcs_hoehe=0, lcs_x=0, lcs_y=0):
        """Ein Part mit Körper und optional einem LCS darin – so, wie man eine
        Werkzeug- oder Werkstückaufnahme markiert. Gelenke greifen dann auf
        "<Körpername>.FaceN". Das LCS liegt bei (lcs_x, lcs_y, lcs_hoehe) im
        Körper, von seiner Ecke bzw. der Mitte unten aus."""
        teil = self.assembly.newObject("App::Part", name)
        self.assembly.removeObject(koerper)
        teil.addObject(koerper)
        teil.Placement = koerper.Placement
        koerper.Placement = App.Placement()
        lcs = None
        if lcs_name:
            lcs = self.doc.addObject("App::LocalCoordinateSystem", lcs_name)
            lcs.Placement = App.Placement(App.Vector(lcs_x, lcs_y, lcs_hoehe), App.Rotation())
            teil.addObject(lcs)
        return teil, lcs

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

    def gelenk_wie_gebaut(self, name, art, teil1, flaeche1, teil2, flaeche2, richtung=None):
        """Ein Gelenk, das die Teile lässt, wo sie gebaut sind – Stellung 0.

        Beim Anlegen legt der Löser die Mitten der Flächen aufeinander, und
        jede Änderung am Versatz (Offset) löst vorab (preSolve) – mit einer
        Seite schon versetzt, der anderen noch nicht, klappt FreeCAD dabei
        Teile um (so hing der Fräskopf mit Oberfläche hinter dem Ständer).
        Deshalb kommen die Teile danach jedes Mal zurück. Der Versatz beider
        Seiten legt den Bezugspunkt auf die Mitte der Fläche von Seite 2;
        `richtung` (global) dreht die Achse, etwa waagrecht für einen Tisch,
        der auf seinem Schlitten gleitet; ohne ist es die Normale der Flächen.
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
            drehung = App.Rotation(App.Vector(0, 0, 1), App.Vector(*richtung))
        ziel = App.Placement(seite2.Base, drehung)
        gelenk.Offset1 = seite1.inverse() * ziel
        gelenk.Offset2 = seite2.inverse() * ziel
        self._zurueck(lagen)
        return gelenk

    @staticmethod
    def _zurueck(lagen):
        for teil, lage in lagen.items():
            teil.Placement = lage

    def begrenze(self, gelenk, minimum, maximum):
        """Weg eines Schiebegelenks in mm – wie „Minimale/Maximale Länge“ am Gelenk."""
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


def _stelle(teil, x, y, z):
    # Placement als Ganzes zuweisen: teil.Placement.Base = … änderte nur eine Kopie.
    teil.Placement = App.Placement(App.Vector(x, y, z), App.Rotation())


def _faerbe(teil, farbe):
    if farbe is not None and App.GuiUp:
        teil.ViewObject.ShapeColor = farbe


def fraesmaschine():
    """Die Beispiel-Fräsmaschine: Kreuztisch X/Y, Fräskopf Z, Spindel S1.

    Maschinenobjekt ausgefüllt: X1, Y1, Z1 mit Eilgang, Höchstvorschub und
    Beschleunigung, S1 mit Drehzahl, Werkzeugaufnahme an der Spindelnase,
    Werkstückaufnahme mitten auf dem Tisch. Gibt (Assembly, Maschine) zurück.
    """
    b = Baukasten(DOKUMENT)
    b.doc.Label = tr("beispiel.dokument")
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
    kopf = b.quader("Fraeskopf", 200, 400, 300, x=300, y=250, z=520, farbe=KOPF)
    spindel, spindelnase = b.bauteil(
        "Spindel",
        b.zylinder("Spindelkoerper", 45, 140, x=400, y=350, z=380, farbe=SPINDEL),
        lcs_name="Spindelnase",
    )

    b.fixieren(bett)
    b.gelenk_wie_gebaut("Staender_fest", "Fixed", bett, "Face6", staender, "Face5")
    y = b.gelenk_wie_gebaut("Y", "Slider", bett, "Face6", sattel, "Face5", richtung=(0, 1, 0))
    b.begrenze(y, -150, 120)
    x = b.gelenk_wie_gebaut(
        "X", "Slider", sattel, "Face6", tisch, "Tischplatte.Face5", richtung=(1, 0, 0)
    )
    b.begrenze(x, -250, 250)
    z = b.gelenk_wie_gebaut("Z", "Slider", staender, "Face3", kopf, "Face4", richtung=(0, 0, 1))
    b.begrenze(z, -100, 250)
    s = b.gelenk_wie_gebaut(
        "Spindelachse", "Revolute", kopf, "Face5", spindel, "Spindelkoerper.Face2"
    )
    asm = b.fertig()

    ma = m.lege_maschine_an(asm)
    ma.Label = tr("beispiel.maschine")
    for gelenk, name, eilgang in ((x, "X1", 20000), (y, "Y1", 20000), (z, "Z1", 15000)):
        achse = m.neue_betriebsart(ma, gelenk, m.ART_LINEAR, name)
        achse.Eilgang, achse.VorschubMax, achse.Beschleunigung = eilgang, 10000, 3
    s1 = m.neue_betriebsart(ma, s, m.ART_SPINDEL, "S1")
    s1.Drehzahl, s1.Hochlaufzeit = 12000, 1.5
    m.neue_aufnahme(ma, spindelnase, m.AUFNAHME_WERKZEUG, tr("beispiel.spindel"), spindel=s1)
    m.neue_aufnahme(ma, spannplatz, m.AUFNAHME_WERKSTUECK, tr("beispiel.tisch"))
    asm.Document.recompute()
    return asm, ma


def lade():
    """Baut die Beispielmaschine in einem neuen Dokument und zeigt sie; gibt (Assembly, Maschine)."""
    asm, ma = fraesmaschine()
    if App.GuiUp:
        import FreeCADGui

        FreeCADGui.ActiveDocument.ActiveView.viewIsometric()
        FreeCADGui.SendMsgToActiveView("ViewFit")
    return asm, ma
