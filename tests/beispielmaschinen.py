# Baut Beispielmaschinen als Assembly, ohne Oberfläche – Grundlage der
# Prüfungen. Die Körper sind grob (Quader, Zylinder), wie es die
# Spezifikation für echte Maschinen vorsieht.
#
# Flächen eines Part::Box: Face1 x=0, Face2 x=Länge, Face3 y=0, Face4 y=Breite,
# Face5 z=0 (unten), Face6 z=Höhe (oben). Part::Cylinder: Face2 oben,
# Face3 unten. Die Normale der ersten Fläche eines Gelenks ist seine Achse.
import FreeCAD as App
import JointObject


class Baukasten:
    """Baut eine Assembly Schritt für Schritt: Körper, Bauteile mit LCS, Gelenke.

    Maße und Lagen in mm; x, y, z ist die Lage der Ecke bzw. der Mitte unten.
    """

    def __init__(self, name):
        self.doc = App.newDocument(name)
        self.assembly = self.doc.addObject("Assembly::AssemblyObject", "Assembly")
        self.gelenke = self.assembly.newObject("Assembly::JointGroup", "Joints")

    def quader(self, name, laenge, breite, hoehe, x=0, y=0, z=0):
        teil = self.assembly.newObject("Part::Box", name)
        teil.Length, teil.Width, teil.Height = laenge, breite, hoehe
        _stelle(teil, x, y, z)
        return teil

    def zylinder(self, name, radius, hoehe, x=0, y=0, z=0):
        teil = self.assembly.newObject("Part::Cylinder", name)
        teil.Radius, teil.Height = radius, hoehe
        _stelle(teil, x, y, z)
        return teil

    def bauteil(self, name, koerper, lcs_name=None, lcs_hoehe=0):
        """Ein Part mit Körper und optional einem LCS darin – so, wie man eine
        Werkzeug- oder Werkstückaufnahme markiert. Gelenke greifen dann auf
        "<Körpername>.FaceN"."""
        teil = self.assembly.newObject("App::Part", name)
        self.assembly.removeObject(koerper)
        teil.addObject(koerper)
        teil.Placement = koerper.Placement
        koerper.Placement = App.Placement()
        lcs = None
        if lcs_name:
            lcs = self.doc.addObject("App::LocalCoordinateSystem", lcs_name)
            lcs.Placement = App.Placement(App.Vector(0, 0, lcs_hoehe), App.Rotation())
            teil.addObject(lcs)
        return teil, lcs

    def fixieren(self, teil):
        gelenk = self.gelenke.newObject("App::FeaturePython", "Fixiert_" + teil.Name)
        JointObject.GroundedJoint(gelenk, teil)
        return gelenk

    def gelenk(self, name, art, teil1, flaeche1, teil2, flaeche2):
        # Flächen gibt es erst nach dem Neuberechnen der Körper.
        self.doc.recompute()
        gelenk = self.gelenke.newObject("App::FeaturePython", name)
        JointObject.Joint(gelenk, JointObject.JointTypes.index(art))
        # Zweiter Eintrag = Bezugspunkt; die Fläche selbst heißt „Flächenmitte“.
        gelenk.Proxy.setJointConnectors(
            gelenk, [[teil1, [flaeche1, flaeche1]], [teil2, [flaeche2, flaeche2]]]
        )
        return gelenk

    def fertig(self):
        self.doc.recompute()
        return self.assembly


def _stelle(teil, x, y, z):
    # Placement als Ganzes zuweisen: teil.Placement.Base = … änderte nur eine Kopie.
    teil.Placement = App.Placement(App.Vector(x, y, z), App.Rotation())


def drehmaschine():
    """Bett mit Spindelstock, Hauptspindel mit Futter, Z- und X-Schlitten mit
    drehbarem Revolver (ein Werkzeugplatz als LCS)."""
    b = Baukasten("Drehmaschine")
    bett = b.quader("Bett", 600, 200, 50)
    spindelstock = b.quader("Spindelstock", 150, 200, 250, z=50)
    spindel = b.zylinder("Hauptspindel", 60, 80, x=75, y=100, z=300)
    futter, spannflaeche = b.bauteil(
        "Futter",
        b.zylinder("FutterKoerper", 90, 40, x=75, y=100, z=380),
        lcs_name="Spannflaeche",
        lcs_hoehe=40,
    )
    z_schlitten = b.quader("ZSchlitten", 150, 200, 40, x=300, z=50)
    x_schlitten = b.quader("XSchlitten", 100, 150, 40, x=300, z=90)
    revolver, werkzeugplatz = b.bauteil(
        "Revolver",
        b.quader("RevolverKoerper", 80, 80, 80, x=300, z=130),
        lcs_name="Werkzeugplatz",
        lcs_hoehe=80,
    )

    b.fixieren(bett)
    b.gelenk("Spindelstock_fest", "Fixed", bett, "Face6", spindelstock, "Face5")
    b.gelenk("Spindel", "Revolute", spindelstock, "Face6", spindel, "Face3")
    b.gelenk("Futter_fest", "Fixed", spindel, "Face2", futter, "FutterKoerper.Face3")
    b.gelenk("Z", "Slider", bett, "Face6", z_schlitten, "Face5")
    x = b.gelenk("X", "Slider", z_schlitten, "Face2", x_schlitten, "Face1")
    x.EnableLengthMin, x.LengthMin = True, 0
    x.EnableLengthMax, x.LengthMax = True, 200
    # Revolver schaltet um die senkrechte Achse (Werkzeugplatz sitzt außen).
    b.gelenk("Revolverachse", "Revolute", x_schlitten, "Face6", revolver, "RevolverKoerper.Face5")
    return b.fertig()


def fuenfachser(zweites_lager=True):
    """Schwenkbrücke: Wiege mit zwei Schenkeln in zwei Lagerböcken (A), Rundtisch (C);
    dazu Ständer mit Schlitten und Spindel, ein loser Körper und ein nicht
    unterstütztes Gelenk."""
    b = Baukasten("Fuenfachser")
    bett = b.quader("Bett", 600, 300, 50)
    lager_l = b.quader("LagerbockLinks", 50, 100, 150, y=100, z=50)
    lager_r = b.quader("LagerbockRechts", 50, 100, 150, x=450, y=100, z=50)
    wiege = b.quader("Wiege", 400, 100, 150, x=50, y=100, z=50)
    schenkel_l = b.quader("SchenkelLinks", 30, 100, 120, x=50, y=100, z=200)
    schenkel_r = b.quader("SchenkelRechts", 30, 100, 120, x=420, y=100, z=200)
    rundtisch = b.zylinder("Rundtisch", 80, 30, x=250, y=150, z=200)
    staender = b.quader("Staender", 100, 100, 500, x=250, z=50)
    schlitten = b.quader("Schlitten", 80, 80, 100, x=260, y=20, z=400)
    spindel = b.zylinder("Spindel", 30, 100, x=300, y=60, z=300)
    b.quader("Spaenefoerderer", 100, 50, 30, x=700)
    abdeckung = b.quader("Abdeckung", 100, 10, 100, x=250, y=100, z=550)

    b.fixieren(bett)
    b.gelenk("LagerLinks_fest", "Fixed", bett, "Face6", lager_l, "Face5")
    b.gelenk("LagerRechts_fest", "Fixed", bett, "Face6", lager_r, "Face5")
    b.gelenk("A", "Revolute", lager_l, "Face2", wiege, "Face1")
    if zweites_lager:
        b.gelenk("A_Lager2", "Revolute", lager_r, "Face1", wiege, "Face2")
    b.gelenk("SchenkelLinks_fest", "Fixed", wiege, "Face6", schenkel_l, "Face5")
    b.gelenk("SchenkelRechts_fest", "Fixed", wiege, "Face6", schenkel_r, "Face5")
    b.gelenk("C", "Revolute", wiege, "Face6", rundtisch, "Face3")
    b.gelenk("Staender_fest", "Fixed", bett, "Face6", staender, "Face5")
    b.gelenk("Z", "Slider", staender, "Face6", schlitten, "Face5")
    b.gelenk("S", "Revolute", schlitten, "Face5", spindel, "Face2")
    b.gelenk("Abdeckung_zylindrisch", "Cylindrical", staender, "Face4", abdeckung, "Face3")
    return b.fertig()


def drehmaschine_komplett():
    """Die Drehmaschine mit fertig ausgefülltem Maschinenobjekt: Z1, X1, S4/C4
    an der Spindel, Revolver T mit 12 Plätzen, Futter als Werkstückaufnahme."""
    from camaddon import kette
    from camaddon import maschine as m

    asm = drehmaschine()
    obj = asm.Document.getObject
    ma = m.lege_maschine_an(asm)
    ma.Label = "Testdrehmaschine"
    z1 = m.neue_betriebsart(ma, obj("Z"), m.ART_LINEAR, "Z1")
    z1.Eilgang = 30000
    x1 = m.neue_betriebsart(ma, obj("X"), m.ART_LINEAR, "X1")
    x1.Eilgang, x1.Beschleunigung = 24000, 5
    s4 = m.neue_betriebsart(ma, obj("Spindel"), m.ART_SPINDEL, "S4")
    s4.Drehzahl = 4000
    c4 = m.neue_betriebsart(ma, obj("Spindel"), m.ART_POSITIONIEREN, "C4")
    c4.Geschwindigkeit = 100
    rev = m.neue_betriebsart(ma, obj("Revolverachse"), m.ART_REVOLVER, "T")
    m.neue_aufnahme(ma, obj("Spannflaeche"), m.AUFNAHME_WERKSTUECK, "Futter")
    m.verteile_plaetze(ma, kette.lies_kette(asm), rev, obj("Werkzeugplatz"), 12)
    asm.Document.recompute()
    return asm, ma
