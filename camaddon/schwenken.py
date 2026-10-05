# SPDX-License-Identifier: LGPL-2.1-or-later
"""5 Achsen, 3+2 indexiert (W-014, Spezifikation Strategien 15): eine schräge Ebene schwenken.

Ein Zerspaner an einer 5-Achs-Fräse spannt das Teil einmal und schwenkt die Ebene – die
Rundachsen drehen das Teil (oder den Kopf), bis das Werkzeug senkrecht auf der schrägen Fläche
steht; dann fräst er dort wie an einer 3-Achs-Maschine. Im Addon ist eine geschwenkte Ebene eine
Aufspannung, die die Maschine selbst dreht: ein eigener Job (lege_an), dessen Modell so liegt,
dass die gewählte Fläche nach oben zeigt – darin rechnet jede Strategie unverändert.

- **Ebene** (`ebene_aus_flaeche`): ein Placement von der Ebene in den Grundjob – Z ist die
  Außennormale der Fläche (die Werkzeugachse; an der Wand einer Bohrung ihre Achse zum offenen
  Ende), X die Richtung von X des Grundjobs in der Ebene, der Ursprung der Punkt der Ebene, der
  dem Ursprung des Grundjobs am nächsten liegt.
- **Rundachsen** (`Maschine.loese`, `rundachsen_ohne_maschine`): die Stellung, in der die
  Werkzeugachse gegen das Werkstück die Normale ist – aus der Kette der Maschine
  (reichweite.Pruefung), sonst für einen Tisch/Tisch A (um X), C (um Z) mit dem Drehpunkt im
  Ursprung des Grundjobs.
- **Ins Programm ohne Schwenkzyklus** (`Abbildung`, `befehle_ohne_zyklus`): je Punkt der Ebene
  der Punkt, wie eine Steuerung ohne TCPM ihn liest (kinematik: X, Y, Z mit den Rundachsen auf
  0) – Bögen bleiben Bögen, wenn die Ebene im Programm in XY liegt.
- **Mit Schwenkzyklus** (`zyklus_winkel`): Bezugspunkt und Winkel der Ebene achsweise Z, Y, X –
  für Siemens CYCLE800 (Arbeitsvorbereitung 10/2015, S. 678–681, Modus 27).

Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass, field

import FreeCAD

from .sprache import tr

GRUPPE = "5-Achs"  # die Gruppe der Eigenschaften am Job
GLEICH = 1e-9
WINKEL_GENAU = 1e-4  # Grad – so genau stimmen Werkzeugachse und Normale nach dem Lösen
RASTER = 10.0  # Grad – das grobe Raster über beide Rundachsen
SEHNE = 0.01  # mm – so weit weicht ein Bogen als Geraden höchstens ab
BEWEGUNG = ("G0", "G00", "G1", "G01")
BOGEN = ("G2", "G02", "G3", "G03")
ZYKLEN = ("G73", "G81", "G82", "G83", "G85", "G86", "G89")
# Diese Bohrzyklen schreibt befehle_ohne_zyklus als Bewegungen aus, wenn die Ebene im Programm
# nicht in XY liegt (Schwenkkopf); G86 (Spindel steht beim Heraus) nicht.
AUSGESCHRIEBEN = ("G73", "G81", "G82", "G83", "G85", "G89")
FREI = 0.5  # mm – so weit über der letzten Tiefe setzt ein Hub (G83) wieder an, so weit bricht G73


# --- Die Ebene ------------------------------------------------------------------------------


def aussennormale(flaeche):
    """Die Normale der ebenen Fläche vom Material weg (Einheitsvektor) – None, wenn sie nicht
    eben ist."""
    if flaeche.findPlane() is None:
        return None
    u0, u1, v0, v1 = flaeche.ParameterRange
    normale = flaeche.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
    normale.normalize()
    return normale


def ebene(normale, punkt, bezug=None, x_richtung=None):
    """Das Placement der Ebene durch `punkt` mit der Normalen `normale` – von Koordinaten der
    Ebene in die des Grundjobs. X ist `x_richtung` (ohne: X des Grundjobs) in die Ebene gelegt,
    steht sie senkrecht darauf, Y; der Ursprung ist der Punkt der Ebene, der `bezug` (ohne: dem
    Ursprung) am nächsten liegt."""
    n = FreeCAD.Vector(normale)
    n.normalize()
    bezug = FreeCAD.Vector() if bezug is None else FreeCAD.Vector(bezug)
    kandidaten = [FreeCAD.Vector(x_richtung)] if x_richtung is not None else []
    kandidaten += [FreeCAD.Vector(1, 0, 0), FreeCAD.Vector(0, 1, 0)]
    for k in kandidaten:
        x = k - n * k.dot(n)
        if x.Length > 1e-6:
            break
    x.normalize()
    y = n.cross(x)
    matrix = FreeCAD.Matrix(x.x, y.x, n.x, 0, x.y, y.y, n.y, 0, x.z, y.z, n.z, 0, 0, 0, 0, 1)
    ursprung = bezug - n * (bezug - FreeCAD.Vector(punkt)).dot(n)
    return FreeCAD.Placement(ursprung, FreeCAD.Rotation(matrix))


def ebene_aus_flaeche(form, name, bezug=None, x_richtung=None):
    """Die Ebene der ebenen Fläche `name` („Face6“) von `form` (im Grundjob) – oder, ist sie die
    Wand einer Bohrung (eines Zapfens), die Ebene senkrecht zu ihrer Achse durch ihr offenes Ende
    (achse_der_wand): Dann steht das Werkzeug in der Achse, auch wenn um den Eintritt keine ebene
    Fläche ist. ValueError mit einem Satz, wenn es die Fläche nicht gibt oder sie beides nicht
    ist."""
    nummer = int(name[4:]) - 1 if name.startswith("Face") and name[4:].isdigit() else -1
    if not 0 <= nummer < len(form.Faces):
        raise ValueError(tr("sw.fehler.flaeche", name=name))
    flaeche = form.Faces[nummer]
    normale = aussennormale(flaeche)
    if normale is not None:
        return ebene(normale, flaeche.Vertexes[0].Point, bezug, x_richtung)
    achse = achse_der_wand(form, flaeche)
    if achse is None:
        raise ValueError(tr("sw.fehler.nicht_eben", name=name))
    return ebene(achse[0], achse[1], bezug, x_richtung)


def achse_der_wand(form, flaeche):
    """(Richtung, Punkt) für die Zylinderfläche einer Bohrung oder eines Zapfens: die Achse zum
    offenen Ende hin und dessen Mitte. Offen ist ein Ende, hinter dem auf der Achse – zwei
    Durchmesser weiter, über eine Bohrspitze hinaus – kein Material ist; sind es beide
    (Durchgangsbohrung), das, das mehr nach oben zeigt. None, wenn sie kein Zylinder ist oder
    kein Ende offen."""
    import Part

    zylinder = flaeche.Surface
    if not isinstance(zylinder, Part.Cylinder):
        return None
    achse = FreeCAD.Vector(zylinder.Axis)
    achse.normalize()
    mitte = FreeCAD.Vector(zylinder.Center)
    u0, _u1, v0, v1 = flaeche.ParameterRange
    enden = [(flaeche.valueAt(u0, v) - mitte).dot(achse) for v in (v0, v1)]
    weit = 2.0 * float(zylinder.Radius) + 1.0
    offen = []
    for t, seite in ((max(enden), 1.0), (min(enden), -1.0)):
        punkt = mitte + achse * t
        if not form.isInside(punkt + achse * (seite * weit), 1e-6, True):
            offen.append((achse * seite, punkt))
    if not offen:
        return None
    return max(offen, key=lambda o: o[0].z)


def normale_aus_winkeln(neigung, richtung):
    """Die Werkzeugachse (Einheitsvektor im Grundjob), um `neigung` Grad gegen die Senkrechte
    gekippt, der Kopf nach `richtung` Grad (von oben gesehen, 0 = +X, 90 = +Y)."""
    n, r = math.radians(float(neigung)), math.radians(float(richtung))
    return FreeCAD.Vector(math.sin(n) * math.cos(r), math.sin(n) * math.sin(r), math.cos(n))


def text_winkel(neigung, richtung):
    """„15° nach 90°“ – eine Ebene ohne Fläche, aus ihren Winkeln."""
    from . import einheiten

    zeichen = einheiten.gewaehltes_dezimalzeichen() or "."

    def zahl(wert):
        return f"{float(wert):.1f}".rstrip("0").rstrip(".").replace(".", zeichen).replace("-", "−")

    return tr("sw.winkel", neigung=zahl(neigung), richtung=zahl(richtung))


def normale_der(ebene_):
    """Die Werkzeugachse der Ebene im Grundjob (Z der Ebene)."""
    return ebene_.Rotation.multVec(FreeCAD.Vector(0, 0, 1))


def schwenkwinkel(ebene_):
    """Wie weit die Ebene gegen den Grundjob gekippt ist (Grad, 0 … 180)."""
    n = normale_der(ebene_)
    return math.degrees(math.acos(max(-1.0, min(1.0, n.z))))


def zyklus_winkel(ebene_):
    """(Bezugspunkt (x, y, z), (um Z, um Y, um X)) – die Ebene achsweise in der Reihenfolge Z,
    Y, X, jede Drehung um die schon gedrehten Achsen (wie AROT): für CYCLE800 mit Modus 27
    (Arbeitsvorbereitung 10/2015, S. 681: „Drehreihenfolge ZYX … Dezimal 27“)."""
    gier, nick, roll = ebene_.Rotation.getYawPitchRoll()
    return tuple(ebene_.Base), (gier, nick, roll)


# --- Rundachsen ----------------------------------------------------------------------------


def rundachsen_ohne_maschine(normale):
    """{"A": Grad, "C": Grad} für einen Tisch/Tisch A (um X), C (um Z), Drehpunkt im Ursprung des
    Grundjobs: Die Werkzeugachse gegen das gedrehte Werkstück ist Rz(−C) · Rx(−A) · Z =
    (sin A sin C, sin A cos C, cos A). Von den zwei Lösungen (A, C) und (−A, C ± 180) die mit dem
    kleineren Drehen des Rundtischs."""
    n = FreeCAD.Vector(normale)
    n.normalize()
    a = math.degrees(math.acos(max(-1.0, min(1.0, n.z))))
    c = math.degrees(math.atan2(n.x, n.y)) if math.hypot(n.x, n.y) > 1e-9 else 0.0
    if abs(c) > 90.0:
        a, c = -a, _auf_180(c + 180.0)
    return {"A": _rund(a), "C": _rund(c)}


def abbildung_ohne_maschine(rund):
    """Die Abbildung Grundjob → Programm für rundachsen_ohne_maschine: das Werkstück um den
    Ursprung gedreht, erst C um Z, dann A um X."""
    a, c = rund.get("A", 0.0), rund.get("C", 0.0)
    drehung = FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), a).multiply(
        FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), c)
    )
    return Abbildung.aus_placement(FreeCAD.Placement(FreeCAD.Vector(), drehung))


def _rund(wert):
    """Auf 1e-6 gerundet, −0 als 0."""
    wert = round(float(wert), 6)
    return 0.0 if wert == 0 else wert


@dataclass
class Rundachse:
    """Eine Rundachse der Maschine, die positioniert: die Achse der Kette, ihr Buchstabe im
    Programm („A“), ihre Grenzen (None: keine) und ob sie endlos dreht."""

    achse: object
    buchstabe: str
    minimum: float = None
    maximum: float = None

    def erlaubt(self, wert):
        return (self.minimum is None or wert >= self.minimum - 1e-6) and (
            self.maximum is None or wert <= self.maximum + 1e-6
        )


@dataclass
class Abbildung:
    """Punkt im Grundjob → Punkt im Programm (ohne TCPM): P = A · p + b."""

    a: list  # 3 Zeilen
    b: tuple

    @classmethod
    def aus_placement(cls, placement):
        m = placement.toMatrix()
        return cls(
            [[m.A11, m.A12, m.A13], [m.A21, m.A22, m.A23], [m.A31, m.A32, m.A33]],
            (m.A14, m.A24, m.A34),
        )

    def punkt(self, p):
        return tuple(sum(self.a[i][k] * p[k] for k in range(3)) + self.b[i] for i in range(3))

    def richtung(self, v):
        return tuple(sum(self.a[i][k] * v[k] for k in range(3)) for i in range(3))


class Maschine:
    """Die Rundachsen einer Maschine für ein Werkzeug (Spezifikation Strategien 15.2): aus der
    Kette (reichweite.Pruefung), der Werkzeugaufnahme, der Länge bis zur Spitze und dem Nullpunkt
    des Grundjobs an der Werkstückaufnahme."""

    def __init__(self, pruefung, werkzeugaufnahme, laenge, nullpunkt):
        self.pruefung = pruefung
        self.aufnahme = werkzeugaufnahme
        self.laenge = laenge
        self.nullpunkt = FreeCAD.Vector(nullpunkt)
        self.linear, self.drehachsen = pruefung.achsen_fuer(werkzeugaufnahme)
        self.rundachsen = []
        for achse in pruefung._dreh_wege(werkzeugaufnahme, self.drehachsen, {}):
            buchstabe = pruefung.programmbuchstabe(achse)
            if buchstabe is not None:
                minimum, maximum = pruefung.verfahren.grenzen(achse)
                self.rundachsen.append(Rundachse(achse, buchstabe, minimum, maximum))

    def richtung(self, rund):
        """Die Werkzeugachse (von der Spitze weg) in Koordinaten des Grundjobs bei den
        Rundachsen `rund` ({"A": Grad, …})."""
        p = self.pruefung
        wege = p._dreh_wege(self.aufnahme, self.drehachsen, rund)
        werkzeug = p._glied_lage(p._glied(self.aufnahme), wege).multiply(p._lage(self.aufnahme))
        werkstueck = p._glied_lage(p._glied(p.werkstueckaufnahme), wege).multiply(
            p._lage(p.werkstueckaufnahme)
        )
        z = werkzeug.Rotation.multVec(FreeCAD.Vector(0, 0, 1))
        return werkstueck.Rotation.inverted().multVec(z)

    def loese(self, normale):
        """Die Stellungen der Rundachsen ([{"A": Grad, …}]), in denen die Werkzeugachse die
        Normale ist – die beste zuerst: innerhalb der Grenzen, der kleinste Schwenk (Summe der
        Beträge), bei Gleichstand der kleinere Wert der ersten Rundachse. Leer, wenn keine
        Stellung die Normale trifft."""
        n = FreeCAD.Vector(normale)
        n.normalize()
        achsen = self.rundachsen
        if not achsen:
            return []

        def fehler(werte):
            rund = {a.buchstabe: w for a, w in zip(achsen, werte, strict=True)}
            d = self.richtung(rund)
            return max(0.0, 1.0 - d.dot(n))

        def bereich(a):
            von = a.minimum if a.minimum is not None else -180.0
            bis = a.maximum if a.maximum is not None else 180.0
            if bis - von > 360.0:
                von, bis = -180.0, 180.0
            return von, bis

        gitter = [[]]
        for a in achsen:
            von, bis = bereich(a)
            anzahl = max(1, int(math.ceil((bis - von) / RASTER)))
            stellen = [von + (bis - von) * i / anzahl for i in range(anzahl + 1)]
            gitter = [g + [s] for g in gitter for s in stellen]
        grob = sorted(gitter, key=fehler)[: 8 * len(achsen)]
        grenze = 1.0 - math.cos(math.radians(WINKEL_GENAU))
        loesungen = []
        for start in grob:
            werte = _genau(fehler, list(start))
            if werte is None or fehler(werte) > grenze:
                continue
            # Am Pol (die Werkzeugachse auf einer Rundachse) dreht die andere frei: dann auf 0.
            for i in range(len(werte)):
                versuch = list(werte)
                versuch[i] = 0.0
                if fehler(versuch) <= grenze:
                    werte = versuch
            werte = [_auf_180(w) if (a.minimum is None and a.maximum is None) or bereich(a)[1]
                     - bereich(a)[0] >= 360.0 else w for a, w in zip(achsen, werte, strict=True)]  # fmt: skip
            rund = {a.buchstabe: _rund(w) for a, w in zip(achsen, werte, strict=True)}
            if any(all(abs(rund[k] - r[k]) < 1e-3 for k in rund) for r in loesungen):
                continue
            loesungen.append(rund)

        def guete(rund):
            # Bei gleich weitem Schwenk die kleineren Werte der Rundachsen der Reihe nach – wie
            # CYCLE800 mit _DIR −1 (Spezifikation 15.4, D-2); sonst entschiede die Suche.
            drinnen = all(a.erlaubt(rund[a.buchstabe]) for a in achsen)
            schwenk = round(sum(abs(rund[a.buchstabe]) for a in achsen), 6)
            return (not drinnen, schwenk, tuple(rund[a.buchstabe] for a in achsen))

        return sorted(loesungen, key=guete)

    def abbildung(self, rund):
        """Die Abbildung Grundjob → Programm ohne TCPM bei den Rundachsen `rund`: Mit `rund`
        stehen die Linearachsen so, dass die Spitze auf dem Punkt p des gedrehten Werkstücks
        steht; der Punkt im Programm ist, wo die Spitze mit denselben Linearachsen und den
        Rundachsen auf 0 stünde (kinematik). None, wenn die Maschine keine drei Linearachsen
        hat."""
        import numpy

        p = self.pruefung
        null = getattr(self, "_null", None)
        if null is None:  # für jede Stellung dieselbe – einmal (simultan: je Punkt der Bahn)
            null = self._null = p._loese(
                self.aufnahme, self.laenge, self.nullpunkt, self.linear,
                p._dreh_wege(self.aufnahme, self.drehachsen, {}),
            )  # fmt: skip
        gedreht = p._loese(
            self.aufnahme, self.laenge, self.nullpunkt, self.linear,
            p._dreh_wege(self.aufnahme, self.drehachsen, rund),
        )  # fmt: skip
        if null is None or gedreht is None or not (null.voll and gedreht.voll):
            return None
        s0 = numpy.array(null.s, dtype=float)
        sg = numpy.array(gedreht.s, dtype=float)
        inv = numpy.linalg.inv(s0)
        a = inv @ sg
        b = inv @ (numpy.array(gedreht.s0, dtype=float) - numpy.array(null.s0, dtype=float))
        return Abbildung(a.tolist(), tuple(b.tolist()))


def _auf_180(wert):
    """Den Winkel in −180 … 180."""
    wert = math.fmod(wert + 180.0, 360.0)
    if wert < 0:
        wert += 360.0
    return wert - 180.0


def _genau(fehler, werte, schritte=60):
    """Verfeinert `werte` (Grad), bis `fehler` (≥ 0, 0 = getroffen) nicht mehr sinkt: je Achse
    halbierte Schritte in beide Richtungen (Musterverfahren) – ohne Ableitung, robust an den
    Polen. Gibt die Werte zurück (None, wenn nichts geht)."""
    schritt = RASTER / 2.0
    besser = fehler(werte)
    for _ in range(schritte):
        geaendert = False
        for i in range(len(werte)):
            for richtung in (1.0, -1.0):
                versuch = list(werte)
                versuch[i] += richtung * schritt
                f = fehler(versuch)
                if f < besser - 1e-15:
                    werte, besser, geaendert = versuch, f, True
        if not geaendert:
            schritt /= 2.0
            if schritt < 1e-7:
                break
    return werte


# --- Sätze ins Programm ohne Schwenkzyklus ----------------------------------------------------


@dataclass
class Schwenkung:
    """Was die Sätze einer Ebene ins Programm bringt: die Ebene (Placement Ebene → Grundjob),
    die Rundachsen und die Abbildung Grundjob → Programm."""

    ebene: object
    rund: dict
    abbildung: Abbildung
    hinweise: list = field(default_factory=list)
    # Ohne Schwenkzyklus: Z im Programm, auf das das Werkzeug vor dem Schwenken fährt – über dem
    # Raum, den das Rohteil beim Schwenken überstreicht (schwenkhoehe); None: keine Fahrt davor.
    hoehe: float = None
    # Mit Schwenkzyklus: die Vorzugsrichtung (CYCLE800 _DIR) – −1 die Stellung mit dem kleineren
    # Wert der Bezugsrundachse, +1 die mit dem größeren –, so dass die Steuerung die Stellung
    # nimmt, die „Auf der Maschine prüfen“ gefahren ist (zyklus_richtung).
    richtung: int = -1
    richtung_achse: str = ""  # der Buchstabe der Bezugsrundachse dazu (postprozessor dreht um)

    def gesamt(self):
        """Die Abbildung Ebene → Programm."""
        e = Abbildung.aus_placement(self.ebene)
        a = [
            [sum(self.abbildung.a[i][k] * e.a[k][j] for k in range(3)) for j in range(3)]
            for i in range(3)
        ]
        b = self.abbildung.punkt(e.b)
        return Abbildung(a, b)

    def in_xy(self):
        """Liegt die Ebene im Programm in XY (Z der Ebene → ±Z, Tisch/Tisch)? Dann bleiben
        Bögen und Bohrzyklen, was sie sind."""
        z = self.gesamt().richtung((0.0, 0.0, 1.0))
        return abs(abs(z[2]) - 1.0) < 1e-9


def befehle_ohne_zyklus(befehle, schwenkung, schon_oben=False):
    """Die Sätze einer Ebene (Path.Command in Koordinaten der Ebene) als Sätze im Programm ohne
    Schwenkzyklus: X, Y, Z durch die Abbildung, die Rundachsen der Ebene im ersten Satz mit
    Bewegung (davor ein eigener Satz G0 mit ihnen). Bögen bleiben Bögen, wenn die Ebene im
    Programm in XY liegt, sonst Geraden (höchstens SEHNE daneben); Bohrzyklen ebenso – sonst
    ausgeschrieben als Eilgang und Vorschub die Achse der Ebene entlang (AUSGESCHRIEBEN; die
    übrigen: ValueError). Nach einem Zyklus steht das Werkzeug auf seiner Rückzugshöhe (G98: wo
    es davor stand, G99: auf R), nicht auf der Tiefe.

    Wo das Werkzeug nach dem Schwenken steht, weiß die Ebene nicht: Sätze, bevor X, Y und Z der
    Ebene bekannt sind (der übliche erste „G0 Z…“ ohne X, Y), fallen weg – das Werkzeug steht
    schon auf der Schwenkhöhe darüber. Zum ersten bekannten Punkt fährt es auf der Schwenkhöhe
    über ihn (auf der Achse der Ebene) und dann die Achse entlang hinunter. `schon_oben`: Die
    Maschine steht am Wechselpunkt ganz oben – kein „G0 Z…“ auf die Schwenkhöhe davor."""
    import Path

    if schwenkung.abbildung is None:
        raise ValueError(tr("sw.fehler.ohne_maschine", rundachsen=text_rundachsen(schwenkung.rund)))
    gesamt = schwenkung.gesamt()
    in_xy = schwenkung.in_xy()
    gespiegelt = in_xy and gesamt.richtung((0.0, 0.0, 1.0))[2] < 0
    stand = [None, None, None]
    gefahren = angefahren = False
    auf_r = False  # G99: nach dem Zyklus auf R, sonst (G98) zurück auf die Höhe davor
    zyklus = {}  # Z, R, Q, P des letzten Bohrzyklus (modal)
    ergebnis = []
    rund = dict(schwenkung.rund)

    def anfahren(ziel):
        """Vor dem ersten bekannten Punkt: über ihn auf die Schwenkhöhe (die Achse der Ebene
        entlang), von dort fährt der Satz selbst hinunter."""
        achse = gesamt.richtung((0.0, 0.0, 1.0))
        p = gesamt.punkt(ziel)
        if schwenkung.hoehe is None or achse[2] < 0.1 or p[2] >= schwenkung.hoehe:
            return
        t = (float(schwenkung.hoehe) - p[2]) / achse[2]
        oben = gesamt.punkt((ziel[0], ziel[1], ziel[2] + t))
        ergebnis.append(Path.Command("G0", dict(zip("XYZ", oben, strict=True))))

    for befehl in befehle:
        name = befehl.Name.upper()
        werte = dict(befehl.Parameters)
        if name in BEWEGUNG + BOGEN + ZYKLEN and not gefahren:
            if schwenkung.hoehe is not None and not schon_oben:
                # Erst hoch genug, dass sich das Rohteil frei dreht (wie CYCLE800 _FR = 1).
                ergebnis.append(Path.Command("G0", {"Z": float(schwenkung.hoehe)}))
            ergebnis.append(Path.Command("G0", dict(rund)))
            gefahren = True
        if name in ("G98", "G99"):
            auf_r = name == "G99"
        if name in ZYKLEN:
            zyklus.update({k: float(werte[k]) for k in "ZRQP" if k in werte})
            werte.update({k: zyklus[k] for k in "ZR" if k in zyklus})
        if name in BEWEGUNG + BOGEN + ZYKLEN:
            ziel = [werte[k] if k in werte else stand[i] for i, k in enumerate("XYZ")]
            if None in ziel:  # noch nicht bekannt, wo in der Ebene: merken, nicht fahren
                stand = ziel
                continue
            ziel = [float(w) for w in ziel]
            if not angefahren:
                oben = ziel[2] if "R" not in werte else max(ziel[2], float(werte["R"]))
                anfahren([ziel[0], ziel[1], oben])
                angefahren = True
        if name in BEWEGUNG or (name in BOGEN and None in stand):  # Bogen von unbekannt: gerade
            neu = {k: v for k, v in werte.items() if k not in "XYZIJK"}
            neu.update(zip("XYZ", gesamt.punkt(ziel), strict=True))
            ergebnis.append(Path.Command(befehl.Name if name in BEWEGUNG else "G1", neu))
            stand = ziel
        elif name in BOGEN:
            mitte = [stand[0] + float(werte.get("I", 0.0)), stand[1] + float(werte.get("J", 0.0))]
            uhr = name in ("G2", "G02")
            if in_xy:
                anfang_p = gesamt.punkt(stand)
                mitte_p = gesamt.punkt((mitte[0], mitte[1], stand[2]))
                neu = {k: v for k, v in werte.items() if k not in "XYZIJK"}
                neu.update(zip("XYZ", gesamt.punkt(ziel), strict=True))
                neu["I"] = mitte_p[0] - anfang_p[0]
                neu["J"] = mitte_p[1] - anfang_p[1]
                art = name if not gespiegelt else ("G3" if uhr else "G2")
                ergebnis.append(Path.Command(art, neu))
            else:
                rest = {k: v for k, v in werte.items() if k not in "XYZIJK"}
                for punkt in _bogen_punkte(stand, ziel, mitte, uhr):
                    satz = dict(rest)
                    satz.update(zip("XYZ", gesamt.punkt(punkt), strict=True))
                    ergebnis.append(Path.Command("G1", satz))
            stand = ziel
        elif name in ZYKLEN:
            r = float(werte.get("R", ziel[2]))
            davor = stand[2] if stand[2] is not None else r
            if in_xy:
                neu = dict(werte)
                neu.update(zip("XYZ", gesamt.punkt(ziel), strict=True))
                if "R" in werte:
                    neu["R"] = gesamt.punkt((ziel[0], ziel[1], r))[2]
                ergebnis.append(Path.Command(befehl.Name, neu))
            elif name in AUSGESCHRIEBEN:
                for art, punkt, satz in _zyklus_ausgeschrieben(name, werte, zyklus, davor, auf_r):
                    if punkt is not None:
                        satz.update(zip("XYZ", gesamt.punkt(punkt), strict=True))
                    ergebnis.append(Path.Command(art, satz))
            else:
                raise ValueError(tr("sw.fehler.zyklus"))
            stand = [ziel[0], ziel[1], r if auf_r else davor]
        elif not in_xy and name in ("G80", "G98", "G99"):
            continue  # ohne Zyklen im Programm ohne Sinn
        else:
            ergebnis.append(befehl)
    return ergebnis


def _zyklus_ausgeschrieben(name, werte, zyklus, davor, auf_r):
    """Ein Bohrzyklus als [(Befehl, Punkt in der Ebene oder None, {Adresse: Wert})]: über dem
    Loch auf der Höhe davor, im Eilgang auf R, im Vorschub auf die Tiefe – G83 in Hüben von Q,
    zwischen ihnen zurück auf R und im Eilgang bis FREI über die letzte Tiefe, G73 in Hüben mit
    FREI zurück (Spänebrechen) –, G82/G89 mit Verweilen (G4 P), G85/G89 im Vorschub heraus;
    dann auf die Rückzugshöhe (G99: R, sonst die Höhe davor)."""
    x, y = float(werte["X"]), float(werte["Y"])
    tief, r = float(werte["Z"]), float(werte.get("R", davor))
    vorschub = {"F": werte["F"]} if "F" in werte else {}
    q = float(zyklus.get("Q", 0.0)) if name in ("G73", "G83") else 0.0
    saetze = [("G0", (x, y, davor), {})]
    if abs(r - davor) > GLEICH:
        saetze.append(("G0", (x, y, r), {}))
    if q > GLEICH:
        tiefe = r
        while tiefe > tief + GLEICH:
            if name == "G83" and tiefe < r - GLEICH:
                saetze.append(("G0", (x, y, tiefe + FREI), {}))
            tiefe = max(tief, tiefe - q)
            saetze.append(("G1", (x, y, tiefe), dict(vorschub)))
            if tiefe > tief + GLEICH:
                saetze.append(("G0", (x, y, r if name == "G83" else tiefe + FREI), {}))
    else:
        saetze.append(("G1", (x, y, tief), dict(vorschub)))
    if name in ("G82", "G89") and zyklus.get("P", 0.0) > 0.0:
        saetze.append(("G4", None, {"P": zyklus["P"]}))
    if name in ("G85", "G89"):
        saetze.append(("G1", (x, y, r), dict(vorschub)))
    zurueck = r if auf_r else davor
    if saetze[-1][1] is None or abs(saetze[-1][1][2] - zurueck) > GLEICH:
        saetze.append(("G0", (x, y, zurueck), {}))
    return saetze


def _bogen_punkte(anfang, ende, mitte, uhr):
    """Punkte (x, y, z) längs des Bogens von `anfang` nach `ende` um `mitte` (x, y) in der Ebene
    – ohne den Anfang, höchstens SEHNE von der Sehne; z linear (Schraube)."""
    r = math.hypot(anfang[0] - mitte[0], anfang[1] - mitte[1])
    a0 = math.atan2(anfang[1] - mitte[1], anfang[0] - mitte[0])
    a1 = math.atan2(ende[1] - mitte[1], ende[0] - mitte[0])
    winkel = (a0 - a1) if uhr else (a1 - a0)
    winkel %= 2 * math.pi
    if winkel < 1e-12:
        winkel = 2 * math.pi
    if r <= SEHNE:
        return [tuple(ende)]
    schritt = 2.0 * math.acos(max(0.0, 1.0 - SEHNE / r))
    anzahl = max(1, int(math.ceil(winkel / max(schritt, 1e-3))))
    punkte = []
    for i in range(1, anzahl + 1):
        t = i / anzahl
        a = a0 - winkel * t if uhr else a0 + winkel * t
        punkte.append(
            (
                mitte[0] + r * math.cos(a),
                mitte[1] + r * math.sin(a),
                anfang[2] + (ende[2] - anfang[2]) * t,
            )
        )
    punkte[-1] = tuple(ende)
    return punkte


# --- Die Ebene als Job (F2) ------------------------------------------------------------------


def text_rundachsen(rund, programm=False):
    """„A−30 C0“ – die Rundachsen in der Reihenfolge A, B, C, ohne Nullen hinter dem Komma.
    `programm`: für einen Kommentar im Programm – Punkt und „-“, nur ASCII."""
    from . import einheiten

    zeichen = einheiten.PUNKT if programm else einheiten.gewaehltes_dezimalzeichen() or "."
    minus = "-" if programm else "−"
    teile = []
    for buchstabe in sorted(rund):
        zahl = f"{_rund(rund[buchstabe]):.3f}".rstrip("0").rstrip(".")
        teile.append(f"{buchstabe}{zahl.replace('.', zeichen).replace('-', minus)}")
    return " ".join(teile)


def ist_ebene(job):
    """Ist der Job eine geschwenkte Ebene (hat er einen Grundjob)?"""
    return getattr(job, "Grundjob", None) is not None and hasattr(job, "Ebene")


def ebene_von(job):
    """Das Placement der Ebene des Jobs im Grundjob – None, wenn der Job keine Ebene ist."""
    return FreeCAD.Placement(job.Ebene) if ist_ebene(job) else None


def rundachsen_von(job):
    """Die Rundachsen der Ebene des Jobs ({"A": Grad, …}) – leer ohne Ebene."""
    text = getattr(job, "Rundachsen", "") if ist_ebene(job) else ""
    rund = {}
    for teil in text.replace("−", "-").replace(",", ".").split():
        if len(teil) > 1 and teil[0] in "ABC":
            try:
                rund[teil[0]] = float(teil[1:])
            except ValueError:
                continue
    return rund


def _eigenschaften(job):
    for art, name, tip in (
        ("App::PropertyLink", "Grundjob", tr("sw.eigenschaft.grundjob")),
        ("App::PropertyPlacement", "Ebene", tr("sw.eigenschaft.ebene")),
        ("App::PropertyString", "Flaeche", tr("sw.eigenschaft.flaeche")),
        ("App::PropertyString", "Rundachsen", tr("sw.eigenschaft.rundachsen")),
    ):
        if name not in job.PropertiesList:
            job.addProperty(art, name, GRUPPE, tip)
    for name in ("Ebene", "Flaeche", "Rundachsen"):
        job.setEditorMode(name, 1)  # nur lesen: gerechnet


def lege_an(grundjob, flaeche, maschine=None, name=None, x_richtung=None, winkel=None):
    """Legt die geschwenkte Ebene der Fläche `flaeche` („Face12“, am Modell des Grundjobs) als
    neuen Job an (Spezifikation Strategien 15.1) – ohne eigene Transaktion: Das Modell liegt so,
    dass die Fläche nach oben zeigt und auf z 0 liegt, das Rohteil ist das des Grundjobs, mit
    ihm gedreht (ein Klon); dazu die Eigenschaften „5-Achs“. Statt einer Fläche `winkel`
    (Neigung, Richtung in Grad, normale_aus_winkeln): die Ebene durch den Nullpunkt des
    Grundjobs, etwa für einen angestellten Kugelfräser. `maschine`: sw.Maschine für die
    Rundachsen – ohne: Tisch/Tisch A, C. Gibt den Job zurück; ValueError mit einem Satz, wenn
    die Fläche nicht eben ist oder die Maschine sie nicht erreicht."""
    import Path.Main.Job as PathJob
    import Path.Main.Stock as PathStock

    from . import vierachs_rohteil as vr

    klon_grund = vr.modell(grundjob)
    if winkel is not None:
        ebene_ = ebene(normale_aus_winkeln(*winkel), FreeCAD.Vector(), x_richtung=x_richtung)
        flaeche = ""
    else:
        ebene_ = ebene_aus_flaeche(klon_grund.Shape, flaeche, x_richtung=x_richtung)
    bezeichnung = flaeche or text_winkel(*winkel)
    normale = normale_der(ebene_)
    if maschine is not None:
        loesungen = maschine.loese(normale)
        if not loesungen:
            raise ValueError(tr("sw.fehler.keine_stellung", flaeche=bezeichnung))
        rund = loesungen[0]
        if not all(a.erlaubt(rund[a.buchstabe]) for a in maschine.rundachsen):
            raise ValueError(
                tr("sw.fehler.grenze", flaeche=bezeichnung, rundachsen=text_rundachsen(rund))
            )
    else:
        rund = rundachsen_ohne_maschine(normale)
    dokument = grundjob.Document
    FreeCAD.setActiveDocument(dokument.Name)
    teil = vr.original(klon_grund)
    job = PathJob.Create("Job", [teil])
    zurueck = ebene_.inverse()
    vr.modell(job).Placement = zurueck.multiply(klon_grund.Placement)
    rohteil_grund = getattr(grundjob, "Stock", None)
    if rohteil_grund is not None:
        rohteil = PathJob.createResourceClone(job, rohteil_grund, "Stock", "Stock")
        PathStock.SetupStockObject(rohteil, PathStock.StockType.Unknown)
        rohteil.Placement = zurueck.multiply(rohteil_grund.Placement)
        alt = job.Stock
        job.Stock = rohteil
        if alt is not None and alt is not rohteil:
            dokument.removeObject(alt.Name)
    from . import reichweite as rw

    maschine_datei = getattr(grundjob, rw.EIGENSCHAFT_MASCHINE, "")
    if maschine_datei:
        rw.merke_maschine(job, maschine_datei)  # dieselbe Maschine wie der Grundjob
    _eigenschaften(job)
    job.Grundjob = grundjob
    job.Ebene = ebene_
    job.Flaeche = flaeche
    job.Rundachsen = text_rundachsen(rund)
    job.Label = name or tr(
        "sw.job", job=grundjob.Label, flaeche=bezeichnung, rundachsen=job.Rundachsen
    )
    dokument.recompute()
    return job


SCHWENK_RAND = 20.0  # mm – so viel Luft über dem Raum, den das Rohteil beim Schwenken überstreicht
SCHWENK_STUFEN = 6  # so viele Stellungen je Rundachse zwischen 0 und dem Ziel werden gerechnet


def schwenkhoehe(rohteil_form, abbildung_bei, rund, rand=SCHWENK_RAND):
    """Z im Programm (ohne TCPM), über dem die Spitze stehen muss, damit sich das Rohteil frei
    von 0 auf die Rundachsen `rund` dreht: die höchste Ecke seines Kastens in allen
    Zwischenstellungen (je Rundachse SCHWENK_STUFEN von 0 bis zum Ziel, alle zusammen), plus
    `rand`. `abbildung_bei`: rund → Abbildung (Grundjob → Programm) oder None."""
    bb = rohteil_form.BoundBox
    ecken = [
        (x, y, z)
        for x in (bb.XMin, bb.XMax)
        for y in (bb.YMin, bb.YMax)
        for z in (bb.ZMin, bb.ZMax)
    ]
    buchstaben = sorted(rund)
    stufen = [
        [rund[b] * k / (SCHWENK_STUFEN - 1) for k in range(SCHWENK_STUFEN)] for b in buchstaben
    ]
    gitter = [[]]
    for werte in stufen:
        gitter = [g + [w] for g in gitter for w in werte]
    hoechste = max(e[2] for e in ecken)
    for werte in gitter:
        abbildung = abbildung_bei(dict(zip(buchstaben, werte, strict=True)))
        if abbildung is None:
            continue
        hoechste = max(hoechste, max(abbildung.punkt(e)[2] for e in ecken))
    return hoechste + rand


def passende_rundachsen(maschine, lage, rund):
    """Die Rundachsen für die Ebene `lage` an `maschine` (sw.Maschine): `rund` (am Job gemerkt),
    wenn sie diese Achsen hat und das Werkzeug damit in der Normalen steht – sonst neu gelöst,
    die beste Stellung; None, wenn keine die Normale trifft."""
    normale = normale_der(lage)
    buchstaben = {a.buchstabe for a in maschine.rundachsen}
    if set(rund) == buchstaben and maschine.richtung(rund).dot(normale) >= 1.0 - 1e-6:
        return rund
    loesungen = maschine.loese(normale)
    return loesungen[0] if loesungen else None


def schwenkung_fuer(job, maschine=None):
    """Die Schwenkung (Ebene, Rundachsen, Abbildung ins Programm ohne Zyklus, Höhe davor) eines
    Jobs mit Ebene – None ohne. Die Abbildung aus `maschine` (sw.Maschine; die Rundachsen passend
    zu ihr); ohne Maschine nur für Tisch/Tisch A, C mit dem Drehpunkt im Nullpunkt des Grundjobs,
    sonst None (dann geht nur der Schwenkzyklus der Steuerung)."""
    if not ist_ebene(job):
        return None
    rund = rundachsen_von(job)
    if maschine is not None:
        rund = passende_rundachsen(maschine, ebene_von(job), rund)
        if rund is None:
            return Schwenkung(ebene_von(job), rundachsen_von(job), None)
        abbildung_bei = maschine.abbildung
    elif set(rund) == {"A", "C"}:
        abbildung_bei = abbildung_ohne_maschine
    else:
        return Schwenkung(ebene_von(job), rund, None)
    rohteil = getattr(getattr(job.Grundjob, "Stock", None), "Shape", None)
    hoehe = None
    if rohteil is not None and not rohteil.isNull():
        hoehe = schwenkhoehe(rohteil, abbildung_bei, rund)
    richtung, richtung_achse = -1, ""
    if maschine is not None:
        from . import maschine as m

        bezug = m.schwenk_bezug(getattr(maschine.pruefung, "maschine", None))
        richtung = zyklus_richtung(maschine, normale_der(ebene_von(job)), rund, bezug)
        reihe = siemens_reihenfolge(maschine)
        richtung_achse = reihe[bezug - 1].buchstabe if len(reihe) >= bezug else ""
    return Schwenkung(
        ebene_von(job),
        rund,
        abbildung_bei(rund),
        hoehe=hoehe,
        richtung=richtung,
        richtung_achse=richtung_achse,
    )


def siemens_reihenfolge(maschine):
    """Die Rundachsen der Maschine (sw.Maschine) als Rundachse 1, 2 wie im Schwenkdatensatz
    einer Siemens-Steuerung: Drehen beide das Werkstück (Tisch/Tisch) oder beide das Werkzeug
    (Kopf/Kopf), ist die erste die, die die zweite trägt – vom Bett aus zuerst; gemischt
    (Kopf/Tisch) dreht die erste das Werkzeug, die zweite das Werkstück."""
    p = maschine.pruefung
    werkzeug = list(p.verfahren.pfad(p._glied(maschine.aufnahme)))
    stueck = list(p.verfahren.pfad(p._glied(p.werkstueckaufnahme)))
    kopf = sorted(
        (a for a in maschine.rundachsen if a.achse in werkzeug),
        key=lambda a: werkzeug.index(a.achse),
    )
    tisch = sorted(
        (a for a in maschine.rundachsen if a.achse in stueck and a.achse not in werkzeug),
        key=lambda a: stueck.index(a.achse),
    )
    return kopf + tisch


def _vergleichswert(rundachse, wert):
    """Wie der Schwenkzyklus Werte einer Rundachse vergleicht: eine endlose (Modulo) in
    0 … 360°, eine begrenzte, wie sie ist."""
    if rundachse.minimum is None and rundachse.maximum is None:
        return wert % 360.0
    return wert


def zyklus_richtung(maschine, normale, rund, bezug=1):
    """Die Vorzugsrichtung (CYCLE800 _DIR) für die Stellung `rund`: −1, wenn sie unter den
    erlaubten Stellungen zur Normale den kleineren Wert der Bezugsrundachse (`bezug`: 1 oder 2,
    siemens_reihenfolge) hat, +1, wenn den größeren – so nimmt die Steuerung dieselbe Stellung,
    die das Addon geprüft hat. −1, wenn es keine andere gibt."""
    reihe = siemens_reihenfolge(maschine)
    if len(reihe) < bezug:
        return -1
    achse = reihe[bezug - 1]
    andere = [
        r
        for r in maschine.loese(normale)
        if all(a.erlaubt(r[a.buchstabe]) for a in maschine.rundachsen)
        and any(abs(r[k] - rund.get(k, 0.0)) > 1e-3 for k in r)
    ]
    if not andere or achse.buchstabe not in rund:
        return -1
    hier = _vergleichswert(achse, rund[achse.buchstabe])
    werte = [_vergleichswert(achse, r[achse.buchstabe]) for r in andere]
    return -1 if all(hier <= w + 1e-6 for w in werte) else 1


def ebenen_von(grundjob):
    """Die Jobs der Ebenen, die aus `grundjob` geschwenkt sind – in der Reihenfolge im
    Dokument."""
    return [
        o
        for o in grundjob.Document.Objects
        if o is not grundjob and ist_ebene(o) and o.Grundjob == grundjob
    ]


def gleiche(a, b):
    """Sind zwei Schwenkungen (oder None) dieselbe Ebene?"""
    if a is None or b is None:
        return a is b
    return a.ebene.isSame(b.ebene, 1e-9) and a.rund == b.rund
