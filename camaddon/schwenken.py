# SPDX-License-Identifier: LGPL-2.1-or-later
"""5 Achsen, 3+2 indexiert (W-014, Spezifikation Strategien 15): eine schräge Ebene schwenken.

Ein Zerspaner an einer 5-Achs-Fräse spannt das Teil einmal und schwenkt die Ebene – die
Rundachsen drehen das Teil (oder den Kopf), bis das Werkzeug senkrecht auf der schrägen Fläche
steht; dann fräst er dort wie an einer 3-Achs-Maschine. Im Addon ist eine geschwenkte Ebene eine
Aufspannung, die die Maschine selbst dreht: ein eigener Job (lege_an), dessen Modell so liegt,
dass die gewählte Fläche nach oben zeigt – darin rechnet jede Strategie unverändert.

- **Ebene** (`ebene_aus_flaeche`): ein Placement von der Ebene in den Grundjob – Z ist die
  Außennormale der Fläche (die Werkzeugachse), X die Richtung von X des Grundjobs in der Ebene,
  der Ursprung der Punkt der Ebene, der dem Ursprung des Grundjobs am nächsten liegt.
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
    """Die Ebene der ebenen Fläche `name` („Face6“) von `form` (im Grundjob) – ValueError mit
    einem Satz, wenn es sie nicht gibt oder sie nicht eben ist."""
    nummer = int(name[4:]) - 1 if name.startswith("Face") and name[4:].isdigit() else -1
    if not 0 <= nummer < len(form.Faces):
        raise ValueError(tr("sw.fehler.flaeche", name=name))
    flaeche = form.Faces[nummer]
    normale = aussennormale(flaeche)
    if normale is None:
        raise ValueError(tr("sw.fehler.nicht_eben", name=name))
    return ebene(normale, flaeche.Vertexes[0].Point, bezug, x_richtung)


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
        from .reichweite import _programmbuchstabe

        self.pruefung = pruefung
        self.aufnahme = werkzeugaufnahme
        self.laenge = laenge
        self.nullpunkt = FreeCAD.Vector(nullpunkt)
        self.linear, self.drehachsen = pruefung.achsen_fuer(werkzeugaufnahme)
        self.rundachsen = []
        for achse in pruefung._dreh_wege(werkzeugaufnahme, self.drehachsen, {}):
            buchstabe = _programmbuchstabe(pruefung.maschine, achse)
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
        Beträge). Leer, wenn keine Stellung die Normale trifft."""
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
            drinnen = all(a.erlaubt(rund[a.buchstabe]) for a in achsen)
            return (not drinnen, sum(abs(rund[a.buchstabe]) for a in achsen))

        return sorted(loesungen, key=guete)

    def abbildung(self, rund):
        """Die Abbildung Grundjob → Programm ohne TCPM bei den Rundachsen `rund`: Mit `rund`
        stehen die Linearachsen so, dass die Spitze auf dem Punkt p des gedrehten Werkstücks
        steht; der Punkt im Programm ist, wo die Spitze mit denselben Linearachsen und den
        Rundachsen auf 0 stünde (kinematik). None, wenn die Maschine keine drei Linearachsen
        hat."""
        import numpy

        p = self.pruefung
        null = p._loese(
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


def befehle_ohne_zyklus(befehle, schwenkung):
    """Die Sätze einer Ebene (Path.Command in Koordinaten der Ebene) als Sätze im Programm ohne
    Schwenkzyklus: X, Y, Z durch die Abbildung, die Rundachsen der Ebene im ersten Satz mit
    Bewegung (davor ein eigener Satz G0 mit ihnen). Bögen bleiben Bögen, wenn die Ebene im
    Programm in XY liegt, sonst Geraden (höchstens SEHNE daneben); Bohrzyklen nur in XY –
    sonst ValueError."""
    import Path

    gesamt = schwenkung.gesamt()
    in_xy = schwenkung.in_xy()
    gespiegelt = in_xy and gesamt.richtung((0.0, 0.0, 1.0))[2] < 0
    stand = [0.0, 0.0, 0.0]
    gefahren = False
    ergebnis = []
    rund = dict(schwenkung.rund)
    for befehl in befehle:
        name = befehl.Name.upper()
        werte = dict(befehl.Parameters)
        if name in BEWEGUNG + BOGEN + ZYKLEN and not gefahren:
            ergebnis.append(Path.Command("G0", dict(rund)))
            gefahren = True
        if name in BEWEGUNG:
            ziel = [float(werte.get(k, stand[i])) for i, k in enumerate("XYZ")]
            neu = {k: v for k, v in werte.items() if k not in "XYZ"}
            neu.update(zip("XYZ", gesamt.punkt(ziel), strict=True))
            ergebnis.append(Path.Command(befehl.Name, neu))
            stand = ziel
        elif name in BOGEN:
            ziel = [float(werte.get(k, stand[i])) for i, k in enumerate("XYZ")]
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
            if not in_xy:
                raise ValueError(tr("sw.fehler.zyklus"))
            ziel = [float(werte.get(k, stand[i])) for i, k in enumerate("XYZ")]
            neu = dict(werte)
            p = gesamt.punkt(ziel)
            neu.update(zip("XYZ", p, strict=True))
            if "R" in werte:
                neu["R"] = gesamt.punkt((ziel[0], ziel[1], float(werte["R"])))[2]
            ergebnis.append(Path.Command(befehl.Name, neu))
            stand = ziel
        else:
            ergebnis.append(befehl)
    return ergebnis


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
