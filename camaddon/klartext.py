# SPDX-License-Identifier: LGPL-2.1-or-later
"""Heidenhain-Klartext (W-005; Manuel, 2026-10-05: „Heidenhain muss mit rein, aber gibt ja
verschiedene, vor allem iTNC 530“). Der Postprozessor schreibt das Programm wie für jede
Steuerung – Wechselpunkt, Marken, Spindel, Kühlung, geschwenkte Ebenen, Vorschub ohne G93 –,
übersetzen() macht daraus Klartext, pruefe() liest es wie die Steuerung nach.

Die Sätze, wie ein Programm für die iTNC 530 sie schreibt (Nachwuchsstiftung Maschinenbau,
„Fussteil Pos. 1“): „0 BEGIN PGM FussteilA MM“, „BLK FORM 0.1 Z X-1 Y-20 Z-40“ / „BLK FORM 0.2 X+39
Y+20 Z-3“, Kommentare „;…“, „TOOL CALL 10 Z S5000 F2000“, „M3“ allein, „L X+55 Y+35 FMAX“,
„CC X+39.5 Y+0“ und „C X+34 Y-13.955 DR+“, „M30“, „END PGM FussteilA MM“; jeder Satz mit Nummer ab 0.

Übersetzt:
- G0 → „L … R0 FMAX“, G1 → „L … R0 F…“ (F nur, wenn er sich ändert); jede Zahl mit Vorzeichen.
- G2/G3 in der Ebene XY → „CC“ (Mitte) und „C … DR-“ bzw. „DR+“; ein Vollkreis in zwei Hälften.
  Eine Schraube (Z ändert sich) als „CC“ und „CP IPA… IZ… DR±“; ein Bogen in XZ/YZ und eine
  Schraube mit verschiedenem Abstand von Anfang und Ende zur Mitte in Geraden (SEHNE).
- Werkzeugwechsel „TOOL CALL n Z“, die Drehzahl kommt dazu („TOOL CALL n Z S…“), M3/M4 allein.
  Eine andere Drehzahl mit demselben Werkzeug: „TOOL CALL n Z S…“ noch einmal (so ändert die
  TNC sie). Die Länge nimmt TOOL CALL mit – kein G43.
- „G53 G0 …“ (Maschinenkoordinaten) → „L … R0 FMAX M91“.
- Bohrzyklen G81, G82, G83 als Zyklus 200 BOHREN, G73 als 203 UNIVERSAL-BOHREN, G85 als 201
  REIBEN (Zyklenhandbuch iTNC 530, Kapitel 3; P-2026-10-25-65) mit „L X… Y… R0 FMAX M99“ je Loch;
  ohne `zyklen` ausgeschrieben in L-Sätzen (G98: zurück auf die Höhe davor, G99: auf R),
  Verweilen mit Zyklus 9.
- Gewindebohren G84/G74 als Zyklus 207 „Gewindebohren GS“ (ohne Ausgleichsfutter; Zyklenhandbuch
  iTNC 530, 4.3) mit „L X… Y… R0 FMAX M99“ je Loch – ausgeschrieben ginge es nicht, die Spindel
  muss mit Z laufen. Die Q-Zeilen setzen den Satz fort („~“, ohne eigene Nummer). Am Zyklusende
  steht die Spindel: danach wieder M3 bzw. M4.
- Zeilen, die schon Klartext sind (aus den Befehlen der Steuerung: TOOL CALL, „L … M91“, „* -“
  Gliederung, CYCL DEF, M128, FUNCTION TCPM, PLANE …), bleiben – Zahlen in L-Sätzen bekommen ihr
  Vorzeichen.

Läuft ohne Oberfläche und ohne FreeCAD.
"""

import math
import re
from dataclasses import dataclass, field

STELLEN = 3
SEHNE = 0.002  # mm – so weit darf eine Gerade von einem Bogen abweichen, der zerlegt wird
KREIS_TOLERANZ = 0.002  # mm
KOMMENTAR_LAENGE = 200  # Zeichen je Kommentarsatz höchstens
PECK_LUFT = 0.5  # mm – beim Tiefbohren so weit über der letzten Tiefe wieder im Vorschub
SPAN_BRECHEN = 0.5  # mm – G73: so weit zurück nach jeder Zustellung
ACHSEN = ("X", "Y", "Z", "A", "B", "C")
KLARTEXT = (
    "TOOL CALL",
    "TOOL DEF",
    "L ",
    "CC ",
    "C ",
    "CR ",
    "CT ",
    "CYCL ",
    "TCH PROBE",  # Messzyklen des Tasters (Plan C3b: 421–424)
    "PLANE ",
    "FUNCTION ",
    "BLK FORM",
    "LBL ",
    "CALL ",
    "STOP",
    "FN ",
    "*",
    ";",
)
# Was der Klartext nicht braucht: Ebene, mm, Radiuskorrektur aus, Länge, Zyklus aus, absolut,
# Vorschub je Minute, Bahnmodi.
OHNE = {"G17", "G21", "G40", "G49", "G80", "G90", "G94", "G64", "G61", "G642", "G43"}

TEXTE = {
    True: {
        "verweil": ("CYCL DEF 9.0 VERWEILZEIT", "CYCL DEF 9.1 V.ZEIT {s}"),
        "gewinde": (
            "CYCL DEF 207 GEW.-BOHREN GS NEU",
            "SICHERHEITS-ABST.",
            "TIEFE",
            "GEWINDESTEIGUNG",
            "KOOR. OBERFLAECHE",
            "2. SICHERHEITS-ABST.",
        ),
        "gewinde_ausgleich": (
            "CYCL DEF 206 GEWINDEBOHREN NEU",
            "SICHERHEITS-ABST.",
            "GEWINDETIEFE",
            "VORSCHUB TIEFENZUST.",
            "VERWEILZEIT UNTEN",
            "KOOR. OBERFLAECHE",
            "2. SICHERHEITS-ABST.",
        ),
    },
    False: {
        "verweil": ("CYCL DEF 9.0 DWELL TIME", "CYCL DEF 9.1 DWELL {s}"),
        "gewinde": (
            "CYCL DEF 207 RIGID TAPPING NEW",
            "SET-UP CLEARANCE",
            "DEPTH",
            "THREAD PITCH",
            "SURFACE COORDINATE",
            "2ND SET-UP CLEARANCE",
        ),
        "gewinde_ausgleich": (
            "CYCL DEF 206 TAPPING NEW",
            "SET-UP CLEARANCE",
            "DEPTH OF THREAD",
            "FEED RATE FOR PLNGNG",
            "DWELL TIME AT DEPTH",
            "SURFACE COORDINATE",
            "2ND SET-UP CLEARANCE",
        ),
    },
}
FORTSETZUNG = "  "  # eine Zeile, die den Satz davor fortsetzt (Q-Parameter eines Zyklus)
# Die Bohrzyklen der TNC: Nummer → (Name deutsch, englisch); je Q-Parameter sein Kommentar.
BOHRZYKLEN = {
    200: ("BOHREN", "DRILLING"),
    201: ("REIBEN", "REAMING"),
    203: ("UNIVERSAL-BOHREN", "UNIVERSAL DRILLING"),
}
Q_TEXTE = {
    "Q200": ("SICHERHEITS-ABST.", "SET-UP CLEARANCE"),
    "Q201": ("TIEFE", "DEPTH"),
    "Q202": ("ZUSTELL-TIEFE", "PLUNGING DEPTH"),
    "Q203": ("KOOR. OBERFLAECHE", "SURFACE COORDINATE"),
    "Q204": ("2. SICHERHEITS-ABST.", "2ND SET-UP CLEARANCE"),
    "Q205": ("MIN. ZUSTELL-TIEFE", "MIN. PLUNGING DEPTH"),
    "Q206": ("VORSCHUB TIEFENZ.", "FEED RATE FOR PLNGNG"),
    "Q208": ("VORSCHUB RUECKZUG", "RETRACTION FEED RATE"),
    "Q210": ("VERWEILZEIT OBEN", "DWELL TIME AT TOP"),
    "Q211": ("VERWEILZEIT UNTEN", "DWELL TIME AT DEPTH"),
    "Q212": ("ABNAHMEBETRAG", "DECREMENT"),
    "Q213": ("SPANBRUECHE", "BREAKS"),
    "Q256": ("RZ BEI SPANBRUCH", "DIST FOR CHIP BRKNG"),
    "Q395": ("BEZUG TIEFE", "DEPTH REFERENCE"),
}
SPANBRUECHE = 99  # G73: so viele Spanbrüche, bevor 203 ganz herausfährt – G73 fährt nie heraus
RUECKZUG_EILGANG = 99999  # mm/min – Q208 bei G73: heraus so schnell es geht


def zahl(wert, stellen=STELLEN):
    """„+12.500“ – im Klartext steht vor jeder Zahl ihr Vorzeichen."""
    text = f"{float(wert):+.{stellen}f}"
    return "+" + "0." + "0" * stellen if float(text) == 0.0 else text


def q_zahl(wert):
    """Ein Q-Parameter wie im Zyklenhandbuch: „+2“, „-15“, „+0.1“ – ohne Nullen am Ende."""
    text = f"{float(wert):+.4f}".rstrip("0").rstrip(".")
    return "+0" if text in ("+0", "-0") else text


def _mit_vorzeichen(roh, stellen=STELLEN):
    """„CYCL DEF 7.1 X+12.500“, „PLANE SPATIAL SPA+30.000 …“ – die Zahlen nach X, Y, Z, SPA, SPB,
    SPC mit ihrem Vorzeichen, wie der Klartext sie verlangt."""
    return re.sub(
        r"(?<![A-Z])(SPA|SPB|SPC|X|Y|Z)([-+]?\d+(?:\.\d+)?)",
        lambda m: f"{m.group(1)}{zahl(float(m.group(2)), stellen)}",
        roh,
    )


def vorschub(wert):
    """„F318“ – ab 10 mm/min ganz, darunter mit einer Stelle (nie F0)."""
    wert = max(float(wert), 0.1)
    return f"F{wert:.0f}" if wert >= 10.0 else f"F{wert:.1f}"


def pgm_name(text):
    """Der Programmname im BEGIN/END PGM – wie die Datei: nur Buchstaben, Ziffern und „_“."""
    from .postprozessor import ascii_text

    name = re.sub(r"[^A-Za-z0-9_]+", "_", ascii_text(str(text or ""))).strip("_")
    return name or "PGM"


@dataclass
class Uebersetzt:
    zeilen: list
    hinweise: list = field(default_factory=list)
    saetze: int = 0  # L- und C-Sätze


_WORT = re.compile(r"([A-Z])\s*([-+]?(?:\d+\.?\d*|\.\d+))")


def _woerter(zeile):
    """[(Buchstabe, Zahl)] eines G-Code-Satzes."""
    return [(b, float(z)) for b, z in _WORT.findall(zeile.upper())]


class _Uebersetzer:
    def __init__(self, deutsch, stellen=STELLEN, zyklen=True, gewinde_synchron=True):
        self.stellen = stellen
        self.gewinde_synchron = gewinde_synchron  # Zyklus 207, sonst 206 (Ausgleichsfutter)
        self.deutsch = bool(deutsch)
        self.zyklen = zyklen  # Bohrzyklen als Zyklen der TNC, sonst in L-Sätzen
        self.aus = []
        self.hinweise = []
        self.texte = TEXTE[bool(deutsch)]
        self.pos = dict.fromkeys(ACHSEN)  # wo die Maschine steht (Werkstück) – None: unbekannt
        self.art = "G0"  # die modale Bewegungsart
        self.f_satz = None  # F aus dem Programm (mm/min), modal
        self.f_geschrieben = None  # F, wie zuletzt im Klartext geschrieben
        self.inkrementell = False
        self.ebene = "G17"
        self.rueckzug_r = False  # G99
        self.zyklus = None  # ein Bohrzyklus, modal: (G, {Adresse: Wert})
        self.drehzahl = None  # S, zuletzt geschrieben
        self.spindel_m = 3  # M3 oder M4, zuletzt geschrieben
        self.gewinde_def = None  # was Zyklus 207 zuletzt hieß (Tiefe, Steigung, R, Rückzug)
        self.zyklus_def = None  # der zuletzt definierte Bohrzyklus: (Nummer, Q-Werte)
        self.werkzeug = None
        self.wechsel_offen = None  # Index des TOOL CALL, dem die Drehzahl noch fehlt
        self.saetze = 0
        self.schrauben = 0
        # Der Pol (CC), zuletzt geschrieben – er gilt, bis ein neuer kommt; nach einer Marke, einem
        # TOOL CALL oder einem Zyklus wieder, damit jeder Einstieg ihn selbst setzt.
        self.pol = None

    # --- Ausgabe ----------------------------------------------------------------------------

    def _pol(self, cc):
        if cc != self.pol:
            self.aus.append(cc)
            self.pol = cc

    def kommentar(self, text):
        text = text.strip()
        while text:
            self.aus.append(";" + text[:KOMMENTAR_LAENGE])
            text = text[KOMMENTAR_LAENGE:]

    def gerade(self, ziel, eilgang, m=None):
        """Ein L-Satz zum Punkt `ziel` ({Achse: Wert}, absolut) – nur, was sich ändert."""
        teile = []
        for achse in ACHSEN:
            # Nur, was sich gerundet ändert – sonst stünde derselbe Satz zweimal (Bögen in XZ/YZ
            # in Geraden mit Punkten unter der letzten Stelle).
            if ziel.get(achse) is not None and (
                self.pos[achse] is None
                or zahl(self.pos[achse], self.stellen) != zahl(ziel[achse], self.stellen)
            ):
                teile.append(f"{achse}{zahl(ziel[achse], self.stellen)}")
        if not teile and m is None:
            return
        satz = "L " + " ".join(teile) + (" " if teile else "") + "R0"
        if eilgang:
            satz += " FMAX"
        else:
            satz += self._f()
        if m:
            satz += f" {m}"
        self.aus.append(satz)
        self.saetze += 1
        self.wechsel_offen = None
        for achse in ACHSEN:
            if achse in ziel and ziel[achse] is not None:
                self.pos[achse] = ziel[achse]

    def _f(self):
        if self.f_satz is None:
            return ""
        if self.f_geschrieben is None or abs(self.f_geschrieben - self.f_satz) > 1e-6:
            self.f_geschrieben = self.f_satz
            return " " + vorschub(self.f_satz)
        return ""

    # --- Lesen ------------------------------------------------------------------------------

    def zeile(self, roh):
        roh = roh.strip()
        if not roh:
            return
        if roh.startswith(("TOOL CALL", "CYCL DEF", "TCH PROBE", "PLANE", "*")):
            self.pol = None
        if roh.startswith(";"):
            self.kommentar(roh[1:])
            return
        if roh.startswith("("):
            self.kommentar(roh.strip("()"))
            return
        if re.match(r"Q\d+\s*=", roh) and self.aus and self.aus[-1].endswith("~"):
            # Ein Q-Parameter des Zyklus davor – aus den Befehlen der Steuerung (Zyklus 247).
            self.aus.append(FORTSETZUNG + roh)
            return
        if roh.startswith("TOOL CALL"):
            m = re.match(r"TOOL CALL\s+(\d+)", roh)
            if m:
                self.werkzeug = int(m.group(1))
            self.aus.append(roh)
            self.wechsel_offen = len(self.aus) - 1 if " S" not in roh else None
            return
        if roh.startswith("L ") or roh == "L":
            self._klartext_gerade(roh)
            return
        if roh.upper().startswith(KLARTEXT):
            if roh.startswith(("CYCL DEF 7.", "PLANE SPATIAL")):
                roh = _mit_vorzeichen(roh, self.stellen)
            self.aus.append(roh)
            if roh.startswith(("CYCL DEF", "TCH PROBE", "PLANE")):
                self.wechsel_offen = None  # der Taster dreht nicht: keine Drehzahl in den Aufruf
            return
        woerter = _woerter(roh)
        if not woerter:
            self.hinweise.append(roh)
            self.kommentar(roh)
            return
        self._gcode(roh, woerter)

    def _klartext_gerade(self, roh):
        """Ein L-Satz aus den Befehlen der Steuerung (Wechselpunkt): die Zahlen mit Vorzeichen."""

        def mit_vorzeichen(m):
            return f"{m.group(1)}{zahl(float(m.group(2)), self.stellen)}"

        satz = re.sub(r"\b([XYZABC])([-+]?\d+\.?\d*)", mit_vorzeichen, roh)
        maschine = bool(re.search(r"\bM9[12]\b", satz))
        for achse, wert in re.findall(r"\b([XYZABC])([-+]\d+\.?\d*)", satz):
            self.pos[achse] = None if maschine else float(wert)
        self.aus.append(satz)
        self.saetze += 1
        self.wechsel_offen = None

    def _gcode(self, roh, woerter):
        g = [int(z) if z == int(z) else z for b, z in woerter if b == "G"]
        m = [int(z) for b, z in woerter if b == "M"]
        werte = {b: z for b, z in woerter if b not in ("G", "M", "N")}
        maschine = 53 in g
        for code in g:
            name = f"G{code:g}" if isinstance(code, float) else f"G{code}"
            if name in ("G17", "G18", "G19"):
                self.ebene = name
            elif name == "G90":
                self.inkrementell = False
            elif name == "G91":
                self.inkrementell = True
            elif name == "G98":
                self.rueckzug_r = False
            elif name == "G99":
                self.rueckzug_r = True
            elif name == "G80":
                self.zyklus = None
        if "F" in werte:
            self.f_satz = werte.pop("F")
        bewegung = [c for c in g if c in (0, 1, 2, 3, 81, 82, 83, 73, 85, 84, 74)]
        if 4 in g:
            sekunden = werte.get("P", 0.0)
            for text in self.texte["verweil"]:
                self.aus.append(text.format(s=f"{sekunden:g}"))
            return
        if "T" in werte and 6 in m:
            self.pol = None
            self.werkzeug = int(werte["T"])
            self.aus.append(f"TOOL CALL {self.werkzeug} Z")
            self.wechsel_offen = len(self.aus) - 1
            m = [x for x in m if x != 6]
        if "S" in werte and not bewegung:
            self._drehzahl(werte["S"])
        for code in m:
            self.aus.append(f"M{code}")
            if code in (3, 4):
                self.wechsel_offen = None
                self.spindel_m = code
        if bewegung:
            self.art = f"G{bewegung[-1]}"
            if bewegung[-1] in (81, 82, 83, 73, 85, 84, 74):
                self.zyklus = (bewegung[-1], dict(werte))
        ziel = self._ziel(werte)
        if maschine:
            # Maschinenkoordinaten: im Klartext M91 – wo das Werkstück dann steht, weiß keiner.
            teile = [f"{a}{zahl(werte[a], self.stellen)}" for a in ACHSEN if a in werte]
            if teile:
                self.aus.append("L " + " ".join(teile) + " R0 FMAX M91")
                self.saetze += 1
                for a in ACHSEN:
                    if a in werte:
                        self.pos[a] = None
            return
        if not any(a in werte for a in ACHSEN + ("I", "J", "K", "R")):
            return
        if self.zyklus is not None and self.art in ("G81", "G82", "G83", "G73", "G85"):
            if self.zyklen:
                self._bohrzyklus(ziel, werte)
            else:
                self._bohren(ziel, werte)
            return
        if self.zyklus is not None and self.art in ("G84", "G74"):
            self._gewinde(ziel, werte)
            return
        if self.art in ("G0", "G1"):
            self.gerade(ziel, self.art == "G0")
        elif self.art in ("G2", "G3"):
            self._bogen(ziel, werte, self.art == "G2")

    def _drehzahl(self, s):
        self.drehzahl = float(s)
        drehzahl = f"S{float(s):.0f}"
        if self.wechsel_offen is not None:
            self.aus[self.wechsel_offen] += f" {drehzahl}"
            self.wechsel_offen = None
        elif self.werkzeug is not None:
            self.aus.append(f"TOOL CALL {self.werkzeug} Z {drehzahl}")
        else:
            self.aus.append(f"TOOL CALL Z {drehzahl}")

    def _ziel(self, werte):
        """Der Zielpunkt absolut – bei G91 vom Stand aus (unbekannt: None)."""
        ziel = {}
        for achse in ACHSEN:
            if achse not in werte:
                continue
            if self.inkrementell:
                ziel[achse] = None if self.pos[achse] is None else self.pos[achse] + werte[achse]
            else:
                ziel[achse] = werte[achse]
        return ziel

    # --- Bögen ------------------------------------------------------------------------------

    def _bogen(self, ziel, werte, uhrzeiger):
        x0, y0, z0 = self.pos["X"], self.pos["Y"], self.pos["Z"]
        if x0 is None or y0 is None or z0 is None:
            self.hinweise.append("Bogen ohne bekannten Anfang")
            self.gerade(ziel, False)
            return
        x1 = ziel.get("X", x0) if ziel.get("X") is not None else x0
        y1 = ziel.get("Y", y0) if ziel.get("Y") is not None else y0
        z1 = ziel.get("Z", z0) if ziel.get("Z") is not None else z0
        if self.ebene == "G17":
            mitte = self._mitte((x0, y0), (x1, y1), werte.get("I", 0.0), werte.get("J", 0.0),
                                werte.get("R"), uhrzeiger)  # fmt: skip
            if abs(z1 - z0) < 1e-9 and mitte is not None:
                self._kreis_xy(mitte, (x0, y0), (x1, y1), uhrzeiger, ziel)
                return
            if mitte is not None and self._schraube(mitte, (x0, y0, z0), (x1, y1, z1), uhrzeiger):
                for achse in ("A", "B", "C"):
                    if ziel.get(achse) is not None:
                        self.gerade({achse: ziel[achse]}, False)
                return
        self._in_geraden(ziel, werte, uhrzeiger)

    @staticmethod
    def _mitte(anfang, ende, i, j, r, uhrzeiger):
        if r is None:
            return anfang[0] + i, anfang[1] + j
        dx, dy = ende[0] - anfang[0], ende[1] - anfang[1]
        sehne = math.hypot(dx, dy)
        if sehne < 1e-12 or abs(r) < sehne / 2 - 1e-9:
            return None
        h = math.sqrt(max(r * r - sehne * sehne / 4, 0.0))
        mx, my = anfang[0] + dx / 2, anfang[1] + dy / 2
        # Links oder rechts der Sehne: G2 mit R > 0 der kurze Bogen (Mitte rechts der Fahrt).
        links = (not uhrzeiger) == (r > 0)
        s = 1.0 if links else -1.0
        return mx - s * h * dy / sehne, my + s * h * dx / sehne

    def _kreis_xy(self, mitte, anfang, ende, uhrzeiger, ziel):
        richtung = "DR-" if uhrzeiger else "DR+"
        cc = f"CC X{zahl(mitte[0], self.stellen)} Y{zahl(mitte[1], self.stellen)}"
        voll = math.hypot(ende[0] - anfang[0], ende[1] - anfang[1]) < 1e-6
        punkte = [ende]
        if voll:  # ein Vollkreis: zwei Hälften
            punkte = [(2 * mitte[0] - anfang[0], 2 * mitte[1] - anfang[1]), ende]
        for px, py in punkte:
            self._pol(cc)
            self.aus.append(
                f"C X{zahl(px, self.stellen)} Y{zahl(py, self.stellen)} {richtung} R0{self._f()}"
            )
            self.saetze += 1
            self.pos["X"], self.pos["Y"] = px, py
        for achse in ("A", "B", "C"):
            if ziel.get(achse) is not None:
                self.gerade({achse: ziel[achse]}, False)
        self.wechsel_offen = None

    def _schraube(self, mitte, anfang, ende, uhrzeiger):
        """Eine Schraubenlinie in der Ebene XY: der Pol CC, dann „CP IPA… IZ… DR±“ – der Winkel um
        den Pol ab dem Anfang, Z inkrementell (iTNC 530, „Schraubenlinie“). Die TNC hält den
        Abstand zum Pol: Sind Anfang und Ende verschieden weit weg, False (dann in Geraden)."""
        r0 = math.hypot(anfang[0] - mitte[0], anfang[1] - mitte[1])
        r1 = math.hypot(ende[0] - mitte[0], ende[1] - mitte[1])
        if r0 < 1e-6 or abs(r0 - r1) > SEHNE:
            return False
        # Anfang, Ende und Mitte stehen auf 0,001 mm gerundet im Programm – die TNC käme bis
        # 0,0016 mm neben dem Ende an. Der Pol auf die Mittelsenkrechte von Anfang und Ende (mit
        # vier Stellen): beide gleich weit weg, die Schraube endet, wo sie soll.
        sx, sy = ende[0] - anfang[0], ende[1] - anfang[1]
        sehne = math.hypot(sx, sy)
        if sehne > 1e-9:
            nx, ny = -sy / sehne, sx / sehne
            mx, my = (anfang[0] + ende[0]) / 2, (anfang[1] + ende[1]) / 2
            abstand = (mitte[0] - mx) * nx + (mitte[1] - my) * ny
            mitte = (round(mx + abstand * nx, 4), round(my + abstand * ny, 4))
        r0 = math.hypot(anfang[0] - mitte[0], anfang[1] - mitte[1])
        w0 = math.atan2(anfang[1] - mitte[1], anfang[0] - mitte[0])
        winkel = math.atan2(ende[1] - mitte[1], ende[0] - mitte[0]) - w0
        if uhrzeiger:
            winkel = winkel - 2 * math.pi if winkel > -1e-12 else winkel
        else:
            winkel = winkel + 2 * math.pi if winkel < 1e-12 else winkel
        if math.hypot(ende[0] - anfang[0], ende[1] - anfang[1]) > 1e-6 and (
            abs(abs(winkel) - 2 * math.pi) < 1e-9
        ):
            return False  # ein winziger Bogen, kein Umlauf
        if abs(math.degrees(winkel)) < 0.01:
            return False  # kaum Drehung: „CP IPA+0“ nähme die TNC nicht – eine Gerade
        ipa = q_zahl(math.degrees(winkel))
        iz = zahl(ende[2] - anfang[2], self.stellen)
        pol = max(self.stellen, 4)
        self._pol(f"CC X{zahl(mitte[0], pol)} Y{zahl(mitte[1], pol)}")
        richtung = "DR-" if uhrzeiger else "DR+"
        self.aus.append(f"CP IPA{ipa} IZ{iz} {richtung} R0{self._f()}")
        self.saetze += 1
        # Wo die TNC ankommt: um den gerundeten Winkel gedreht, Z um das gerundete IZ.
        w1 = w0 + math.radians(float(ipa))
        self.pos["X"] = mitte[0] + r0 * math.cos(w1)
        self.pos["Y"] = mitte[1] + r0 * math.sin(w1)
        self.pos["Z"] = anfang[2] + float(iz)
        self.wechsel_offen = None
        return True

    def _in_geraden(self, ziel, werte, uhrzeiger):
        """Ein Bogen, den der Klartext so nicht kennt (Schraube, Ebene XZ/YZ): in Geraden."""
        ebenen = {"G17": ("X", "Y", "Z", "I", "J"), "G18": ("Z", "X", "Y", "K", "I"),
                  "G19": ("Y", "Z", "X", "J", "K")}  # fmt: skip
        u, v, w, iu, iv = ebenen[self.ebene]
        a0 = (self.pos[u], self.pos[v], self.pos[w])
        a1 = tuple(ziel.get(k) if ziel.get(k) is not None else self.pos[k] for k in (u, v, w))
        # Je Ebene (u, v) so, dass u → v um die dritte Achse positiv dreht (X→Y um Z, Z→X um Y,
        # Y→Z um X): G2 ist dort überall im Uhrzeigersinn, von ihrem positiven Ende gesehen.
        mitte = self._mitte(a0[:2], a1[:2], werte.get(iu, 0.0), werte.get(iv, 0.0),
                            werte.get("R"), uhrzeiger)  # fmt: skip
        if mitte is None:
            self.gerade(ziel, False)
            return
        r = math.hypot(a0[0] - mitte[0], a0[1] - mitte[1])
        w0 = math.atan2(a0[1] - mitte[1], a0[0] - mitte[0])
        w1 = math.atan2(a1[1] - mitte[1], a1[0] - mitte[0])
        winkel = w1 - w0
        if uhrzeiger:
            winkel = winkel - 2 * math.pi if winkel > -1e-12 else winkel
        else:
            winkel = winkel + 2 * math.pi if winkel < 1e-12 else winkel
        if abs(a1[0] - a0[0]) + abs(a1[1] - a0[1]) > 1e-6 and abs(abs(winkel) - 2 * math.pi) < 1e-9:
            winkel = 0.0
        schritt = 2 * math.acos(max(-1.0, 1 - SEHNE / r)) if r > SEHNE else math.pi / 4
        n = max(1, int(math.ceil(abs(winkel) / max(schritt, 1e-3))))
        for k in range(1, n + 1):
            t = k / n
            w_k = w0 + winkel * t
            punkt = {
                u: mitte[0] + r * math.cos(w_k),
                v: mitte[1] + r * math.sin(w_k),
                w: a0[2] + (a1[2] - a0[2]) * t,
            }
            if k == n:
                punkt[u], punkt[v] = a1[0], a1[1]
            self.gerade(punkt, False)
        self.schrauben += 1

    # --- Bohren -----------------------------------------------------------------------------

    def _bohren(self, ziel, werte):
        code, zyklus = self.zyklus
        werte = {**zyklus, **werte}
        z_vorher = self.pos["Z"]
        r = werte.get("R", z_vorher)
        tiefe = werte.get("Z")
        if r is None or tiefe is None:
            self.hinweise.append(f"G{code} ohne R oder Z")
            return
        rueck = r if self.rueckzug_r or z_vorher is None else max(z_vorher, r)
        xy = {a: ziel[a] for a in ("X", "Y") if a in ziel}
        self.gerade(xy, True)
        self.gerade({"Z": r}, True)
        if code in (83, 73) and werte.get("Q", 0.0) > 1e-9:
            q = werte["Q"]
            z = r
            while z - q > tiefe + 1e-9:
                z -= q
                if code == 83 and z + q < r - 1e-9:
                    self.gerade({"Z": z + q + PECK_LUFT}, True)
                self.gerade({"Z": z}, False)
                if code == 83:
                    self.gerade({"Z": r}, True)
                else:
                    self.gerade({"Z": z + SPAN_BRECHEN}, True)
            if code == 83 and z < r - 1e-9:
                self.gerade({"Z": z + PECK_LUFT}, True)
        self.gerade({"Z": tiefe}, False)
        if code == 82 and werte.get("P", 0.0) > 0:
            for text in self.texte["verweil"]:
                self.aus.append(text.format(s=f"{werte['P']:g}"))
        if code == 85:
            self.gerade({"Z": r}, False)
        self.gerade({"Z": rueck}, True)

    def _bohrzyklus(self, ziel, werte):
        """G81, G82, G83, G73, G85 als Zyklus der TNC: 200 BOHREN (G81; G82 mit Verweilen Q211;
        G83 mit der Zustellung Q202 = Q, zurück auf den Sicherheitsabstand), 203 UNIVERSAL-BOHREN
        (G73: Spanbruch, um SPAN_BRECHEN zurück), 201 REIBEN (G85: heraus im Vorschub). Q200 0 (R
        hat den Abstand schon), Q203 = R, Q201 die Tiefe ab R, Q204 zurück auf die Höhe davor
        (G98) oder R (G99) – neu definiert, wenn sich etwas ändert; dann über dem Loch „M99“
        (schon darüber: CYCL CALL)."""
        code, zyklus = self.zyklus
        werte = {**zyklus, **werte}
        z_vorher = self.pos["Z"]
        r = werte.get("R", z_vorher)
        tiefe = werte.get("Z")
        f = self.f_satz
        if r is None or tiefe is None or not f:
            self.hinweise.append(f"G{code} ohne R, Z oder Vorschub")
            return
        rueck = r if self.rueckzug_r or z_vorher is None else max(z_vorher, r)
        t = tiefe - r
        q = werte.get("Q", 0.0)
        zustellung = q if code in (83, 73) and q > 1e-9 else abs(t)
        oben = (("Q200", 0.0), ("Q201", t), ("Q206", f))
        unten = (("Q203", r), ("Q204", rueck - r))
        if code == 85:
            nummer = 201
            q_werte = (*oben, ("Q211", 0.0), ("Q208", f), *unten)
        elif code == 73:
            nummer = 203
            q_werte = (
                *oben,
                ("Q202", zustellung),
                ("Q210", 0.0),
                *unten,
                ("Q212", 0.0),
                ("Q213", SPANBRUECHE),
                ("Q205", 0.0),
                ("Q211", 0.0),
                ("Q208", RUECKZUG_EILGANG),
                ("Q256", SPAN_BRECHEN),
                ("Q395", 0.0),
            )
        else:
            nummer = 200
            verweil = werte.get("P", 0.0) if code == 82 else 0.0
            q_werte = (*oben, ("Q202", zustellung), ("Q210", 0.0), *unten,
                       ("Q211", verweil), ("Q395", 0.0))  # fmt: skip
        definition = (nummer, tuple((n, round(w, 6)) for n, w in q_werte))
        if definition != self.zyklus_def:
            sprache = 0 if self.deutsch else 1
            self.aus.append(f"CYCL DEF {nummer} {BOHRZYKLEN[nummer][sprache]} ~")
            for k, (name, wert) in enumerate(q_werte):
                ende = "" if k == len(q_werte) - 1 else " ~"
                text = Q_TEXTE[name][sprache]
                self.aus.append(f"{FORTSETZUNG}{name}={q_zahl(wert)} ;{text}{ende}")
            self.zyklus_def = definition
            self.wechsel_offen = None
        self._zyklus_rufen(ziel)
        self.pos["Z"] = rueck

    def _zyklus_rufen(self, ziel):
        """Über dem Loch „L X… Y… R0 FMAX M99“ – steht das Werkzeug schon darüber: CYCL CALL."""
        xy = {a: ziel[a] for a in ("X", "Y") if ziel.get(a) is not None}
        if any(self.pos[a] is None or abs(self.pos[a] - w) > 1e-9 for a, w in xy.items()):
            self.gerade(xy, True, m="M99")
        else:
            self.aus.append("CYCL CALL")
            self.saetze += 1

    def _gewinde(self, ziel, werte):
        """Gewindebohren (G84 rechts, G74 links) als Zyklus 207: die Steigung aus F ÷ Drehzahl
        (links negativ), Q203 = R mit Sicherheitsabstand 0 (R hat ihn schon), Q201 die Tiefe ab
        R, Q204 zurück auf die Höhe davor (G98) oder R (G99) – neu definiert, wenn sich etwas
        davon ändert; dann über dem Loch „M99“ (schon darüber: CYCL CALL) und die Spindel wieder
        an."""
        code, zyklus = self.zyklus
        werte = {**zyklus, **werte}
        z_vorher = self.pos["Z"]
        r = werte.get("R", z_vorher)
        tiefe = werte.get("Z")
        if r is None or tiefe is None or not self.drehzahl or not self.f_satz:
            self.hinweise.append(f"G{code} ohne R, Z, Drehzahl oder Vorschub")
            return
        steigung = self.f_satz / self.drehzahl * (-1.0 if code == 74 else 1.0)
        rueck = r if self.rueckzug_r or z_vorher is None else max(z_vorher, r)
        verweil = werte.get("P", 0.0)
        definition = tuple(
            round(w, 6) for w in (tiefe - r, steigung, r, rueck - r, verweil, self.f_satz)
        )
        if definition != self.gewinde_def:
            if self.gewinde_synchron:
                texte = self.texte["gewinde"]
                q = (
                    ("Q200", 0.0, texte[1]),
                    ("Q201", tiefe - r, texte[2]),
                    ("Q239", steigung, texte[3]),
                    ("Q203", r, texte[4]),
                    ("Q204", rueck - r, texte[5]),
                )
            else:
                # Mit Ausgleichsfutter (Zyklus 206): der Vorschub statt der Steigung, die
                # Drehrichtung aus M3/M4 – am Ende kehrt die TNC sie selbst wieder um.
                texte = self.texte["gewinde_ausgleich"]
                q = (
                    ("Q200", 0.0, texte[1]),
                    ("Q201", tiefe - r, texte[2]),
                    ("Q206", self.f_satz, texte[3]),
                    ("Q211", verweil, texte[4]),
                    ("Q203", r, texte[5]),
                    ("Q204", rueck - r, texte[6]),
                )
            self.aus.append(texte[0] + " ~")
            for k, (name, wert, text) in enumerate(q):
                ende = "" if k == len(q) - 1 else " ~"
                self.aus.append(f"{FORTSETZUNG}{name}={q_zahl(wert)} ;{text}{ende}")
            self.gewinde_def = definition
            self.wechsel_offen = None
        self._zyklus_rufen(ziel)
        self.pos["Z"] = rueck
        if self.gewinde_synchron:
            self.aus.append(f"M{self.spindel_m}")  # „Am Zyklusende steht die Spindel“


def uebersetzen(
    zeilen, pgm, rohteil=None, deutsch=True, stellen=STELLEN, zyklen=True, gewinde_synchron=True
):
    """Uebersetzt: die Zeilen des Programms (wie postprozessor.programm sie ohne Satznummern
    schreibt) als Klartext mit Nummern, BEGIN/END PGM `pgm` und – mit `rohteil` ((xmin, ymin,
    zmin), (xmax, ymax, zmax)) – BLK FORM; `deutsch`: die Texte der Zyklen wie an einer deutschen
    Steuerung; `stellen`: Genauigkeit der Koordinaten, auch für fein geprüfte Bahnen; `zyklen`:
    die Bohrzyklen als Zyklen der TNC (sonst in L-Sätzen); `gewinde_synchron`: Gewindebohren als
    Zyklus 207, sonst 206 (mit Ausgleichsfutter)."""
    name = pgm_name(pgm)
    u = _Uebersetzer(deutsch, stellen, zyklen, gewinde_synchron)
    u.aus.append(f"BEGIN PGM {name} MM")
    if rohteil is not None:
        (x0, y0, z0), (x1, y1, z1) = rohteil
        u.aus.append(
            f"BLK FORM 0.1 Z X{zahl(x0, stellen)} Y{zahl(y0, stellen)} Z{zahl(z0, stellen)}"
        )
        u.aus.append(f"BLK FORM 0.2 X{zahl(x1, stellen)} Y{zahl(y1, stellen)} Z{zahl(z1, stellen)}")
    for zeile in zeilen:
        u.zeile(zeile)
    if not any(re.fullmatch(r"M(30|2)", z) or re.search(r"\bM(30|2)$", z) for z in u.aus):
        u.aus.append("M30")
    u.aus.append(f"END PGM {name} MM")
    # Derselbe Eilgang zweimal: nichts zu fahren.
    zeilen_aus = []
    for satz in u.aus:
        if zeilen_aus and satz == zeilen_aus[-1] and satz.startswith("L ") and "FMAX" in satz:
            continue
        zeilen_aus.append(satz)
    nummeriert, nummer = [], 0
    for satz in zeilen_aus:
        if satz.startswith(FORTSETZUNG):
            nummeriert.append(satz)  # setzt den Satz davor fort – ohne eigene Nummer
            continue
        nummeriert.append(f"{nummer} {satz}")
        nummer += 1
    hinweise = []
    if u.schrauben:
        hinweise.append(("schrauben", u.schrauben))
    if u.hinweise:
        hinweise.append(("unbekannt", u.hinweise[:3]))
    return Uebersetzt(nummeriert, hinweise, u.saetze)


# --- Nachlesen ---------------------------------------------------------------------------------


def pruefe(text):
    """Das Klartext-Programm nachgelesen wie an der TNC (programm_pruefen.Pruefung): Nummern ab 0
    lückenlos (NUMMER), BEGIN und END PGM mit demselben Namen und M30/M2 davor (ENDE), ein Weg
    im Werkstück vor dem ersten TOOL CALL (LAENGE – die Länge kommt mit ihm), ein Satz im
    Vorschub ohne Drehzahl und M3/M4 (SPINDEL) oder ohne F (VORSCHUB), ein Kreis ohne CC oder
    mit verschiedenem Abstand von Anfang und Ende zur Mitte (KREIS), derselbe Satz im Vorschub
    zweimal (DOPPELT), Zeichen außerhalb von ASCII (ZEICHEN)."""
    from . import programm_pruefen as prp

    pruefung = prp.Pruefung()

    def befund(art, nummer, satz):
        pruefung.befunde.append(prp.Befund(art, nummer, satz))

    zeilen = [z for z in text.split("\n") if z.strip() and not z.startswith(FORTSETZUNG)]
    pos = dict.fromkeys(ACHSEN)
    werkzeug = False
    drehzahl = 0.0
    spindel = False
    f = None
    mitte = None
    name_anfang = name_ende = None
    ende = False
    vorher = None
    for i, zeile in enumerate(zeilen, start=1):
        if not zeile.isascii():
            befund(prp.ZEICHEN, i, zeile)
        m = re.match(r"(\d+) (.*)$", zeile)
        if not m or int(m.group(1)) != i - 1:
            befund(NUMMER, i, zeile)
            continue
        satz = m.group(2).strip()
        if satz.startswith((";", "*")):
            continue
        k = re.match(r"(BEGIN|END) PGM (\S+) MM$", satz)
        if k:
            if k.group(1) == "BEGIN":
                name_anfang = k.group(2)
            else:
                name_ende = k.group(2)
            continue
        if satz.startswith("TOOL CALL"):
            if re.match(r"TOOL CALL\s+\d+", satz):
                werkzeug = True
                spindel = False
            s_wert = re.search(r"\bS(\d+\.?\d*)", satz)
            if s_wert:
                drehzahl = float(s_wert.group(1))
            continue
        ms = [int(x) for x in re.findall(r"\bM(\d+)\b", satz)]
        if 3 in ms or 4 in ms:
            spindel = drehzahl > 0
        if 5 in ms:
            spindel = False
        if 30 in ms or 2 in ms:
            ende = True
        if satz.startswith("CC "):
            mitte = {a: float(w) for a, w in re.findall(r"\b([XY])([-+]\d+\.?\d*)", satz)}
            continue
        ist_l = satz.startswith("L ") or satz == "L"
        ist_c = satz.startswith("C ")
        ist_cp = satz.startswith("CP ")
        if not (ist_l or ist_c or ist_cp):
            continue
        werte = {a: float(w) for a, w in re.findall(r"\b([XYZABC])([-+]\d+\.?\d*)", satz)}
        if ist_cp:
            # Die Schraubenlinie um den Pol: das Ende aus dem Winkel IPA und IZ.
            ipa = re.search(r"\bIPA([-+]\d+\.?\d*)", satz)
            iz = re.search(r"\bIZ([-+]\d+\.?\d*)", satz)
            werte = {}
            if (
                not mitte
                or "X" not in mitte
                or "Y" not in mitte
                or None
                in (
                    pos["X"],
                    pos["Y"],
                    pos["Z"],
                )
            ):
                befund(prp.KREIS, i, satz)
            elif ipa:
                w = math.atan2(pos["Y"] - mitte["Y"], pos["X"] - mitte["X"])
                w += math.radians(float(ipa.group(1)))
                r = math.hypot(pos["X"] - mitte["X"], pos["Y"] - mitte["Y"])
                werte = {"X": mitte["X"] + r * math.cos(w), "Y": mitte["Y"] + r * math.sin(w)}
                werte["Z"] = pos["Z"] + (float(iz.group(1)) if iz else 0.0)
        maschine = bool(re.search(r"\bM9[12]\b", satz))
        eilgang = "FMAX" in satz
        f_wert = re.search(r"\bF(\d+\.?\d*)\b", satz)
        if f_wert:
            f = float(f_wert.group(1))
        if not eilgang:
            pruefung.saetze += 1
            if not spindel:
                befund(prp.SPINDEL, i, satz)
            if not f:
                befund(prp.VORSCHUB, i, satz)
            if satz == vorher and not ist_cp:  # CP zählt ab dem Stand – gleich ist nicht doppelt
                befund(prp.DOPPELT, i, satz)
        elif ist_l:
            pruefung.saetze += 1
        if not maschine and not werkzeug and (werte or not eilgang):
            befund(prp.LAENGE, i, satz)
        if ist_c:
            if not mitte or "X" not in mitte or "Y" not in mitte or pos["X"] is None:
                befund(prp.KREIS, i, satz)
            else:
                ende_x, ende_y = werte.get("X", pos["X"]), werte.get("Y", pos["Y"])
                r0 = math.hypot(pos["X"] - mitte["X"], pos["Y"] - mitte["Y"])
                r1 = math.hypot(ende_x - mitte["X"], ende_y - mitte["Y"])
                if abs(r0 - r1) > KREIS_TOLERANZ:
                    befund(prp.KREIS, i, satz)
        for a, w in werte.items():
            pos[a] = None if maschine else w
        vorher = satz
    if name_anfang is None or name_anfang != name_ende or not ende:
        befund(prp.ENDE, len(zeilen), zeilen[-1] if zeilen else "")
    return pruefung


NUMMER = "nummer"
