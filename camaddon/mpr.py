# SPDX-License-Identifier: LGPL-2.1-or-later
"""woodWOP-MPR für Homag und Weeke (Manuel, 2026-10-25, zu Herbert im Forum, der an einer Homag
unter woodWOP fräst: „es gibt mit sicherheit unterlagen … mach das einfach“). Der Postprozessor
schreibt das Programm wie für jede Steuerung, uebersetzen() macht daraus eine MPR-Datei,
pruefe() liest sie nach.

Das Format nach HOMAGs „woodWOP FILE-Description (MPR-Format)“ 4.x und einer Ausgabe, die an
einer Homag BOF 211 lief:
- „[H“ der Kopf (VERSION, MAT – HOMAG oder WEEKE –, INCH), „[001“ die Variablen L, B, D je mit
  KM, „<100 \\Werkstck\\“ das Werkstück (LA, BR, DI).
- Konturen „]n“, je Element „$Em“ und KP (Anfang), KL (Gerade) oder KA (Bogen in XY) mit X=, Y=,
  Z= in eigenen Zeilen; der Bogen mit R= und DS= (0 im Uhrzeigersinn bis 180°, 1 gegen den
  Uhrzeigersinn, 2 und 3 über 180°) – geschrieben in Stücken bis 90° (BOGEN_HOECHSTENS), also nur
  0 und 1.
- „<105 \\Konturfraesen\\“ fährt eine Kontur: EA/EE erstes und letztes Element („1:0“),
  MDA="SEN" senkrecht an, MDE="SEN_AB" senkrecht ab, RK="NOWRK" ohne Radiuskorrektur (die
  Mittelbahn, wie die Bahn gerechnet ist), ZA="@0" die Höhe aus der Kontur, TNO das Werkzeug,
  F_ der Vorschub in m/min, SM="1" und S_A die Drehzahl in U/min.
- „<102 \\BohrVert\\“ eine senkrechte Bohrung: XA, YA, TI (Tiefe ab Oberseite), TNO, F_.
- „<101 \\Kommentar\\“ mit KM-Zeilen; „!“ am Ende. Erst alle Konturen, dann die Bearbeitungen in
  ihrer Folge. Zeilen mit CR LF, nur ASCII.
Koordinaten zählt woodWOP ab der Ecke des Werkstücks, Z vom Boden (Z=D ist die Oberseite) – das
Rohteil des Jobs gibt den Versatz.

Eine Kontur endet mit jedem Eilgang, Werkzeugwechsel oder Bohrzyklus. Sie hat nur einen Vorschub:
Wechselt er in ihr (Eintauchen langsamer als Fräsen), gilt der kleinere – das Programm sagt, wie
oft. Bögen außerhalb XY und Schrauben werden zu Geraden (SEHNE); Rundachsen kann MPR so nicht.

Läuft ohne Oberfläche und ohne FreeCAD.
"""

import math
import re
from dataclasses import dataclass, field

STELLEN = 3
SEHNE = 0.002  # mm – so weit darf eine Gerade von einem Bogen abweichen, der zerlegt wird
# Ein Bogen höchstens so weit in einem Element: woodWOP rechnet die Mitte aus Anfang, Ende und R –
# nahe 180° verschiebt schon die letzte Stelle von R sie weit (am Vollkreis Ø 100 in zwei Hälften
# 0,32 mm neben der Bahn). Bis 90° bleibt es unter 2 µm.
BOGEN_HOECHSTENS = math.pi / 2
KM_LAENGE = 80  # Zeichen je Kommentarzeile höchstens (woodWOP)
KOMMENTARE_HOECHSTENS = 40
ACHSEN = ("X", "Y", "Z", "A", "B", "C")
BOHRZYKLEN = (81, 82, 83, 73, 85)
ZEILENENDE = "\r\n"
MASCHINENTYPEN = ("HOMAG", "WEEKE")


@dataclass
class Uebersetzt:
    zeilen: list
    hinweise: list = field(default_factory=list)  # [(Art, Wert)]
    saetze: int = 0  # Elemente der Konturen und Bohrungen


@dataclass
class _Kontur:
    werkzeug: int
    drehzahl: float
    elemente: list  # [("KP"|"KL", x, y, z) | ("KA", x, y, z, r, ds)]
    vorschuebe: list  # mm/min je Element (ohne KP)


@dataclass
class _Bohrung:
    werkzeug: int
    drehzahl: float
    x: float
    y: float
    z: float  # die Spitze
    vorschub: float


_WORT = re.compile(r"([A-Z])\s*([-+]?(?:\d+\.?\d*|\.\d+))")


def zahl(wert, stellen=STELLEN):
    """3,1400 → „3.14“, −0,0001 → „0“."""
    text = f"{wert:.{stellen}f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def _ascii(text):
    from .postprozessor import ascii_text

    return ascii_text(text).replace('"', "'")


class _Leser:
    def __init__(self):
        self.pos = dict.fromkeys(ACHSEN)
        self.art = "G0"
        self.f = None
        self.inkrementell = False
        self.ebene = "G17"
        self.zyklus = None
        self.werkzeug = None
        self.drehzahl = 0.0
        self.kette = None
        self.arbeit = []  # [_Kontur | _Bohrung] in der Folge
        self.kommentare = []
        self.rundachsen = False
        self.unbekannt = []
        self.zerlegt = 0

    # --- Ketten -----------------------------------------------------------------------------

    def _ende(self):
        if self.kette is not None and len(self.kette.elemente) > 1:
            self.arbeit.append(self.kette)
        self.kette = None

    def _element(self, element):
        if self.kette is None:
            x, y, z = self.pos["X"], self.pos["Y"], self.pos["Z"]
            if x is None or y is None or z is None:
                self.unbekannt.append("Bahn ohne bekannten Anfang")
                return
            self.kette = _Kontur(self.werkzeug or 0, self.drehzahl, [("KP", x, y, z)], [])
        self.kette.elemente.append(element)
        self.kette.vorschuebe.append(self.f or 0.0)

    # --- Lesen ------------------------------------------------------------------------------

    def zeile(self, roh):
        roh = roh.strip()
        if not roh:
            return
        if roh.startswith("("):
            if len(self.kommentare) < KOMMENTARE_HOECHSTENS:
                self.kommentare.append(roh.strip("()").strip())
            return
        if roh.startswith(";"):
            return
        woerter = [(b, float(z)) for b, z in _WORT.findall(roh.upper())]
        if not woerter:
            self.unbekannt.append(roh)
            return
        g = [int(z) if z == int(z) else z for b, z in woerter if b == "G"]
        m = [int(z) for b, z in woerter if b == "M"]
        werte = {b: z for b, z in woerter if b not in ("G", "M", "N")}
        if 53 in g:  # Maschinenkoordinaten (Wechselpunkt): woodWOP fährt selbst frei
            self._ende()
            for a in ACHSEN:
                if a in werte:
                    self.pos[a] = None
            return
        for code in g:
            if code in (17, 18, 19):
                self.ebene = f"G{code}"
            elif code == 90:
                self.inkrementell = False
            elif code == 91:
                self.inkrementell = True
            elif code == 80:
                self.zyklus = None
        if "F" in werte:
            self.f = werte.pop("F")
        if "T" in werte and (6 in m or not any(a in werte for a in ACHSEN)):
            self._ende()
            self.werkzeug = int(werte.pop("T"))
        if "S" in werte:
            self.drehzahl = float(werte.pop("S"))
        if 5 in m or 30 in m or 2 in m:
            self._ende()
        bewegung = [c for c in g if c in (0, 1, 2, 3, *BOHRZYKLEN)]
        if bewegung:
            self.art = f"G{bewegung[-1]}"
            if bewegung[-1] in BOHRZYKLEN:
                self.zyklus = (bewegung[-1], dict(werte))
        if any(a in werte for a in ("A", "B", "C")):
            self.rundachsen = True
        if not any(a in werte for a in ("X", "Y", "Z", "I", "J", "K", "R")):
            return
        ziel = self._ziel(werte)
        if self.zyklus is not None and self.art in {f"G{c}" for c in BOHRZYKLEN}:
            self._bohren(ziel, werte)
        elif self.art == "G0":
            self._ende()
            self._setzen(ziel)
        elif self.art == "G1":
            self._gerade(ziel)
        elif self.art in ("G2", "G3"):
            self._bogen(ziel, werte, self.art == "G2")

    def _ziel(self, werte):
        ziel = {}
        for achse in ("X", "Y", "Z"):
            if achse not in werte:
                continue
            if self.inkrementell:
                ziel[achse] = None if self.pos[achse] is None else self.pos[achse] + werte[achse]
            else:
                ziel[achse] = werte[achse]
        return ziel

    def _setzen(self, ziel):
        for achse, wert in ziel.items():
            self.pos[achse] = wert

    def _voll(self, ziel):
        return tuple(
            ziel.get(a) if ziel.get(a) is not None else self.pos[a] for a in ("X", "Y", "Z")
        )

    def _gerade(self, ziel):
        x, y, z = self._voll(ziel)
        if None in (x, y, z):
            self._setzen(ziel)
            return
        if (x, y, z) == (self.pos["X"], self.pos["Y"], self.pos["Z"]):
            return
        self._element(("KL", x, y, z))
        self._setzen({"X": x, "Y": y, "Z": z})

    # --- Bögen ------------------------------------------------------------------------------

    def _bogen(self, ziel, werte, uhrzeiger):
        x0, y0, z0 = self.pos["X"], self.pos["Y"], self.pos["Z"]
        x1, y1, z1 = self._voll(ziel)
        if None in (x0, y0, z0, x1, y1, z1):
            self._gerade(ziel)
            return
        if self.ebene == "G17" and abs(z1 - z0) < 1e-9:
            mitte = _mitte((x0, y0), (x1, y1), werte.get("I", 0.0), werte.get("J", 0.0),
                           werte.get("R"), uhrzeiger)  # fmt: skip
            if mitte is not None:
                self._kreis_xy(mitte, (x0, y0), (x1, y1), z1, uhrzeiger)
                return
        self._in_geraden((x1, y1, z1), werte, uhrzeiger)

    def _kreis_xy(self, mitte, anfang, ende, z, uhrzeiger):
        """Ein Bogen in XY – in Stücken bis BOGEN_HOECHSTENS (ein Vollkreis in vier), je mit R und
        DS (0 im Uhrzeigersinn, 1 gegen ihn; über 180° gibt es so nicht mehr)."""
        winkel = _winkel(mitte, anfang, ende, uhrzeiger)
        r = max(math.hypot(anfang[0] - mitte[0], anfang[1] - mitte[1]),
                math.hypot(ende[0] - mitte[0], ende[1] - mitte[1]))  # fmt: skip
        n = max(1, math.ceil(winkel / BOGEN_HOECHSTENS - 1e-9))
        w0 = math.atan2(anfang[1] - mitte[1], anfang[0] - mitte[0])
        vorzeichen = -1.0 if uhrzeiger else 1.0
        for k in range(1, n + 1):
            if k == n:
                px, py = ende
            else:
                w_k = w0 + vorzeichen * winkel * k / n
                px, py = mitte[0] + r * math.cos(w_k), mitte[1] + r * math.sin(w_k)
            self._element(("KA", px, py, z, r, 0 if uhrzeiger else 1))
            self._setzen({"X": px, "Y": py, "Z": z})

    def _in_geraden(self, ende, werte, uhrzeiger):
        """Ein Bogen, den MPR so nicht kennt (Schraube, Ebene XZ/YZ): in Geraden."""
        ebenen = {"G17": ("X", "Y", "Z", "I", "J"), "G18": ("Z", "X", "Y", "K", "I"),
                  "G19": ("Y", "Z", "X", "J", "K")}  # fmt: skip
        u, v, w, iu, iv = ebenen[self.ebene]
        ziel = dict(zip(("X", "Y", "Z"), ende, strict=True))
        a0 = (self.pos[u], self.pos[v], self.pos[w])
        a1 = (ziel[u], ziel[v], ziel[w])
        mitte = _mitte(a0[:2], a1[:2], werte.get(iu, 0.0), werte.get(iv, 0.0), werte.get("R"),
                       uhrzeiger)  # fmt: skip
        if mitte is None:
            self._gerade(ziel)
            return
        r = math.hypot(a0[0] - mitte[0], a0[1] - mitte[1])
        winkel = _winkel(mitte, a0[:2], a1[:2], uhrzeiger)
        if abs(a1[0] - a0[0]) + abs(a1[1] - a0[1]) < 1e-6 and abs(a1[2] - a0[2]) < 1e-9:
            winkel = 2 * math.pi
        schritt = 2 * math.acos(max(-1.0, 1 - SEHNE / r)) if r > SEHNE else math.pi / 4
        n = max(1, int(math.ceil(winkel / max(schritt, 1e-3))))
        w0 = math.atan2(a0[1] - mitte[1], a0[0] - mitte[0])
        vorzeichen = -1.0 if uhrzeiger else 1.0
        for k in range(1, n + 1):
            t = k / n
            w_k = w0 + vorzeichen * winkel * t
            punkt = {
                u: mitte[0] + r * math.cos(w_k),
                v: mitte[1] + r * math.sin(w_k),
                w: a0[2] + (a1[2] - a0[2]) * t,
            }
            if k == n:
                punkt[u], punkt[v] = a1[0], a1[1]
            self._gerade(punkt)
        self.zerlegt += 1

    # --- Bohren -----------------------------------------------------------------------------

    def _bohren(self, ziel, werte):
        code, zyklus = self.zyklus
        werte = {**zyklus, **werte}
        self._ende()
        x = ziel.get("X", self.pos["X"])
        y = ziel.get("Y", self.pos["Y"])
        tiefe = werte.get("Z")
        if x is None or y is None or tiefe is None:
            self.unbekannt.append(f"G{code} ohne X, Y oder Z")
            return
        self.arbeit.append(
            _Bohrung(self.werkzeug or 0, self.drehzahl, float(x), float(y), float(tiefe),
                     self.f or 0.0)  # fmt: skip
        )
        self._setzen({"X": x, "Y": y, "Z": werte.get("R", self.pos["Z"])})


def _mitte(anfang, ende, i, j, r, uhrzeiger):
    if r is None:
        return anfang[0] + i, anfang[1] + j
    dx, dy = ende[0] - anfang[0], ende[1] - anfang[1]
    sehne = math.hypot(dx, dy)
    if sehne < 1e-12 or abs(r) < sehne / 2 - 1e-9:
        return None
    h = math.sqrt(max(r * r - sehne * sehne / 4, 0.0))
    mx, my = anfang[0] + dx / 2, anfang[1] + dy / 2
    links = (not uhrzeiger) == (r > 0)
    s = 1.0 if links else -1.0
    return mx - s * h * dy / sehne, my + s * h * dx / sehne


def _winkel(mitte, anfang, ende, uhrzeiger):
    """Der überstrichene Winkel (0 … 2π] von `anfang` nach `ende` um `mitte`."""
    w0 = math.atan2(anfang[1] - mitte[1], anfang[0] - mitte[0])
    w1 = math.atan2(ende[1] - mitte[1], ende[0] - mitte[0])
    winkel = (w0 - w1) if uhrzeiger else (w1 - w0)
    winkel %= 2 * math.pi
    return winkel if winkel > 1e-12 else 2 * math.pi


def uebersetzen(zeilen, name="", rohteil=None, maschinentyp="HOMAG", stellen=STELLEN):
    """Uebersetzt: die Zeilen des Programms (wie postprozessor.programm sie schreibt) als
    MPR-Datei – `rohteil` ((xmin, ymin, zmin), (xmax, ymax, zmax)) ist das Werkstück (ohne: die
    Bahn selbst, mit Hinweis); `maschinentyp` HOMAG oder WEEKE."""
    leser = _Leser()
    for zeile in zeilen:
        leser.zeile(zeile)
    leser._ende()
    hinweise = []
    if rohteil is None:
        hinweise.append(("ohne_rohteil", 0))
        punkte = [e[1:4] for k in leser.arbeit if isinstance(k, _Kontur) for e in k.elemente]
        punkte += [(b.x, b.y, b.z) for b in leser.arbeit if isinstance(b, _Bohrung)]
        if punkte:
            rohteil = (
                tuple(min(p[i] for p in punkte) for i in range(3)),
                tuple(max(p[i] for p in punkte) for i in range(3)),
            )
        else:
            rohteil = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    (x0, y0, z0), (x1, y1, z1) = rohteil
    laenge, breite, dicke = x1 - x0, y1 - y0, z1 - z0

    def z_(wert):
        return zahl(wert, stellen)

    aus = ["[H", 'VERSION="4.0"', f'MAT="{maschinentyp}"', 'INCH="0"', ""]
    aus += ["[001", f'L="{z_(laenge)}"', 'KM="Laenge in X"', f'B="{z_(breite)}"',
            'KM="Breite in Y"', f'D="{z_(dicke)}"', 'KM="Dicke in Z"', ""]  # fmt: skip
    aus += ["<100 \\Werkstck\\", 'LA="L"', 'BR="B"', 'DI="D"', 'FNX="0"', 'FNY="0"',
            'AX="0"', 'AY="0"', ""]  # fmt: skip
    nummer = 0
    nummern = {}
    saetze = 0
    gemischt = 0
    for teil in leser.arbeit:
        if not isinstance(teil, _Kontur):
            continue
        nummer += 1
        nummern[id(teil)] = nummer
        aus += [f"]{nummer}", ""]
        vorher = None
        for k, element in enumerate(teil.elemente):
            punkt = (z_(element[1] - x0), z_(element[2] - y0))
            aus += [f"$E{k}", element[0]]
            aus += [f"X={punkt[0]}", f"Y={punkt[1]}", f"Z={z_(element[3] - z0)}"]
            if element[0] == "KA":
                # R gerundet wie die Punkte; reicht er gerundet nicht bis zur halben Sehne (ein
                # winziger Bogen), aufgerundet.
                r = float(z_(element[4]))
                sehne = math.dist(map(float, vorher), map(float, punkt)) if vorher else 0.0
                if r < sehne / 2:
                    r = math.ceil(sehne / 2 * 10**stellen) / 10**stellen
                aus += [f"R={z_(r)}", f"DS={element[5]}"]
            vorher = punkt
            aus.append("")
            saetze += element[0] != "KP"
    for teil in leser.arbeit:
        if isinstance(teil, _Kontur):
            vorschuebe = [f for f in teil.vorschuebe if f > 0]
            f = min(vorschuebe) if vorschuebe else 0.0
            if vorschuebe and max(vorschuebe) - f > 1e-6:
                gemischt += 1
            n = nummern[id(teil)]
            aus += ["<105 \\Konturfraesen\\", f'EA="{n}:0"', 'MDA="SEN"',
                    f'EE="{n}:{len(teil.elemente) - 1}"', 'MDE="SEN_AB"', 'RK="NOWRK"',
                    f'TNO="{teil.werkzeug}"', 'ZA="@0"', f'F_="{zahl(f / 1000.0, 4)}"']  # fmt: skip
            if teil.drehzahl > 0:
                aus += ['SM="1"', f'S_A="{teil.drehzahl:.0f}"']
            aus.append("")
        else:
            aus += ["<102 \\BohrVert\\", f'XA="{z_(teil.x - x0)}"', f'YA="{z_(teil.y - y0)}"',
                    f'TI="{z_(z1 - teil.z)}"', f'TNO="{teil.werkzeug}"',
                    f'F_="{zahl(teil.vorschub / 1000.0, 4)}"']  # fmt: skip
            if teil.drehzahl > 0:
                aus += ['SM="1"', f'S_A="{teil.drehzahl:.0f}"']
            aus.append("")
            saetze += 1
    kommentare = [_ascii(name)] if name else []
    kommentare += [_ascii(k) for k in leser.kommentare]
    if kommentare:
        aus.append("<101 \\Kommentar\\")
        for text in kommentare:
            while text:
                aus.append(f'KM="{text[:KM_LAENGE]}"')
                text = text[KM_LAENGE:]
        aus.append("")
    aus.append("!")
    if leser.rundachsen:
        hinweise.append(("rundachsen", 0))
    if gemischt:
        hinweise.append(("vorschub", gemischt))
    if leser.zerlegt:
        hinweise.append(("zerlegt", leser.zerlegt))
    if leser.unbekannt:
        hinweise.append(("unbekannt", leser.unbekannt[:3]))
    return Uebersetzt(aus, hinweise, saetze)


def text(zeilen):
    """Die Datei: Zeilen mit CR LF (woodWOP läuft unter Windows)."""
    return ZEILENENDE.join(zeilen) + ZEILENENDE


# --- Nachlesen ---------------------------------------------------------------------------------


def pruefe(text_):
    """Die MPR-Datei nachgelesen (programm_pruefen.Pruefung): Zeichen außerhalb ASCII (ZEICHEN),
    „[H“ am Anfang und „!“ am Ende (ENDE), ein Bogen, dessen Radius nicht bis zur Sehne reicht
    (KREIS), eine Bearbeitung ohne Vorschub (VORSCHUB), eine Kontur, die es nicht gibt, oder
    Elemente außerhalb von ihr (NUMMER)."""
    from . import programm_pruefen as prp

    pruefung = prp.Pruefung()

    def befund(art, nummer, satz):
        pruefung.befunde.append(prp.Befund(art, nummer, satz))

    zeilen = text_.replace("\r\n", "\n").split("\n")
    belegt = [(i, z.strip()) for i, z in enumerate(zeilen, start=1) if z.strip()]
    if not belegt or belegt[0][1] != "[H" or belegt[-1][1] != "!":
        befund(prp.ENDE, belegt[-1][0] if belegt else 1, belegt[-1][1] if belegt else "")
    konturen = {}  # Nummer → Zahl der Elemente
    kontur = None
    element = None
    pos = None
    werte = {}
    makro = None
    makro_zeile = 0
    makro_werte = {}

    def element_fertig():
        nonlocal pos
        if element is None:
            return
        art, i = element
        ziel = (werte.get("X"), werte.get("Y"))
        if art == "KA" and pos is not None and None not in ziel:
            sehne = math.hypot(ziel[0] - pos[0], ziel[1] - pos[1])
            if werte.get("R", 0.0) < sehne / 2 - 1e-9:
                befund(prp.KREIS, i, f"KA R={werte.get('R')}")
        if None not in ziel:
            pos = ziel
        if art in ("KL", "KA"):
            pruefung.saetze += 1

    def makro_fertig():
        if makro is None:
            return
        if makro in ("Konturfraesen", "BohrVert"):
            f = makro_werte.get("F_", "")
            try:
                if float(f) <= 0:
                    befund(prp.VORSCHUB, makro_zeile, f"<{makro}> F_={f}")
            except ValueError:
                if f != "STANDARD":
                    befund(prp.VORSCHUB, makro_zeile, f"<{makro}> F_={f}")
        if makro == "BohrVert":
            pruefung.saetze += 1
        if makro == "Konturfraesen":
            for schluessel in ("EA", "EE"):
                k, _, e = makro_werte.get(schluessel, "").partition(":")
                gibt_es = k.isdigit() and int(k) in konturen and e.isdigit()
                if not gibt_es or int(e) >= konturen[int(k)]:
                    befund(NUMMER, makro_zeile, f"{schluessel}={makro_werte.get(schluessel)}")

    for i, zeile in belegt:
        if not zeile.isascii():
            befund(prp.ZEICHEN, i, zeile)
        if zeile.startswith("]"):
            element_fertig()
            element = None
            kontur = int(zeile[1:]) if zeile[1:].isdigit() else None
            if kontur is not None:
                konturen[kontur] = 0
            pos = None
            continue
        if zeile.startswith("$E"):
            element_fertig()
            element = None
            werte = {}
            if kontur is not None:
                konturen[kontur] += 1
            continue
        if zeile in ("KP", "KL", "KA") and kontur is not None:
            element = (zeile, i)
            continue
        if zeile.startswith("<"):
            element_fertig()
            element = None
            kontur = None
            makro_fertig()
            treffer = re.match(r"<\d+\s+\\(\w+)\\", zeile)
            makro = treffer.group(1) if treffer else None
            makro_zeile = i
            makro_werte = {}
            continue
        if zeile == "!":
            element_fertig()
            makro_fertig()
            makro = None
            continue
        schluessel, gleich, wert = zeile.partition("=")
        if not gleich:
            continue
        if element is not None:
            try:
                werte[schluessel] = float(wert)
            except ValueError:
                befund(NUMMER, i, zeile)
        elif makro is not None:
            makro_werte[schluessel] = wert.strip('"')
    return pruefung


NUMMER = "nummer"
