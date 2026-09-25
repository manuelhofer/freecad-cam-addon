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
    def __init__(self, name):
        self.doc = App.newDocument(name)
        self.assembly = self.doc.addObject("Assembly::AssemblyObject", "Assembly")
        self.gelenke = self.assembly.newObject("Assembly::JointGroup", "Joints")

    def quader(self, name, laenge, breite, hoehe, x=0, y=0, z=0):
        teil = self.assembly.newObject("Part::Box", name)
        teil.Length, teil.Width, teil.Height = laenge, breite, hoehe
        # Placement als Ganzes zuweisen – Placement.Base = … ändert nur eine Kopie.
        teil.Placement = App.Placement(App.Vector(x, y, z), App.Rotation())
        return teil

    def zylinder(self, name, radius, hoehe, x=0, y=0, z=0):
        teil = self.assembly.newObject("Part::Cylinder", name)
        teil.Radius, teil.Height = radius, hoehe
        # Placement als Ganzes zuweisen – Placement.Base = … ändert nur eine Kopie.
        teil.Placement = App.Placement(App.Vector(x, y, z), App.Rotation())
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


def drehmaschine():
    """Bett mit Spindelstock, Hauptspindel mit Futter, Z- und X-Schlitten mit Revolver."""
    b = Baukasten("Drehmaschine")
    bett = b.quader("Bett", 600, 200, 50)
    spindelstock = b.quader("Spindelstock", 150, 200, 250, z=50)
    spindel = b.zylinder("Hauptspindel", 60, 80, 75, 100, 300)
    futter, spannflaeche = b.bauteil(
        "Futter", b.zylinder("FutterKoerper", 90, 40, 75, 100, 380), "Spannflaeche", 40
    )
    z_schlitten = b.quader("ZSchlitten", 150, 200, 40, 300, 0, 50)
    x_schlitten = b.quader("XSchlitten", 100, 150, 40, 300, 0, 90)
    revolver, werkzeugplatz = b.bauteil(
        "Revolver", b.quader("RevolverKoerper", 80, 80, 80, 300, 0, 130), "Werkzeugplatz", 80
    )

    b.fixieren(bett)
    b.gelenk("Spindelstock_fest", "Fixed", bett, "Face6", spindelstock, "Face5")
    b.gelenk("Spindel", "Revolute", spindelstock, "Face6", spindel, "Face3")
    b.gelenk("Futter_fest", "Fixed", spindel, "Face2", futter, "FutterKoerper.Face3")
    b.gelenk("Z", "Slider", bett, "Face6", z_schlitten, "Face5")
    x = b.gelenk("X", "Slider", z_schlitten, "Face2", x_schlitten, "Face1")
    x.EnableLengthMin, x.LengthMin = True, 0
    x.EnableLengthMax, x.LengthMax = True, 200
    b.gelenk("Revolver_fest", "Fixed", x_schlitten, "Face6", revolver, "RevolverKoerper.Face5")
    return b.fertig()


def fuenfachser(zweites_lager=True):
    """Schwenkbrücke: Wiege mit zwei Schenkeln in zwei Lagerböcken (A), Rundtisch (C);
    dazu Ständer mit Schlitten und Spindel, ein loser Körper und ein nicht
    unterstütztes Gelenk."""
    b = Baukasten("Fuenfachser")
    bett = b.quader("Bett", 600, 300, 50)
    lager_l = b.quader("LagerbockLinks", 50, 100, 150, 0, 100, 50)
    lager_r = b.quader("LagerbockRechts", 50, 100, 150, 450, 100, 50)
    wiege = b.quader("Wiege", 400, 100, 150, 50, 100, 50)
    schenkel_l = b.quader("SchenkelLinks", 30, 100, 120, 50, 100, 200)
    schenkel_r = b.quader("SchenkelRechts", 30, 100, 120, 420, 100, 200)
    rundtisch = b.zylinder("Rundtisch", 80, 30, 250, 150, 200)
    staender = b.quader("Staender", 100, 100, 500, 250, 0, 50)
    schlitten = b.quader("Schlitten", 80, 80, 100, 260, 20, 400)
    spindel = b.zylinder("Spindel", 30, 100, 300, 60, 300)
    b.quader("Spaenefoerderer", 100, 50, 30, 700, 0, 0)
    abdeckung = b.quader("Abdeckung", 100, 10, 100, 250, 100, 550)

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
