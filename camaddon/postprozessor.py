# SPDX-License-Identifier: LGPL-2.1-or-later
"""Der Postprozessor des Addons (W-005; Spezifikation Steuerung, Stufen S1–S3).

Manuel (2026-10-03): „ich möchte nicht den Postprozessor-Generator von FreeCAD nutzen … ich
hätte gern einen guten Postprozessor-Manager … außerdem funktioniert der mit 4 Achs nicht und
für 5 Achs wird's auch nix – darum sollten wir vll unsere eigenen bauen?“ – und zu den
Entscheidungen E1–E7: „ja, die Spezifikationen nehmen“ (je die Empfehlung (a)).

Er schreibt alle aktiven Operationen eines Jobs – auch FreeCADs eigene – mit den Befehlen der
gewählten Steuerung (STEUERUNGEN: LinuxCNC, Siemens 840D, Fanuc, Haas, Mach3/Mach4; E1):

- Kopf und Ende je Steuerung, Kommentare in ihrer Form („(…)“ bzw. „; …“).
- Werkzeugwechsel an der Fräse „T1 M6“, an der Drehmaschine je Steuerung („T1 D1“, „T0101“,
  „T101“); die Spindel „M3 S…“ – ein angetriebenes Werkzeug mit dem Befehl der Steuerung und
  der Nummer seines Antriebs (S3 → 3: Siemens „M3=3 S3=…“, Haas „M133 P…“).
- An der Drehmaschine vor der ersten Bahn mit der Rundachse „C-Achse ein“, danach „aus“ – mit
  der Nummer der Hauptspindel (Siemens „SPOS[4]=0“); X im Durchmesser, wenn die Maschine X so
  zählt (E4: wie die Steuerung von Haus aus zählt); die Rundachse mit dem NC-Namen der C-Achse
  der Hauptspindel (Siemens mit „=“ bei einer Nummer: „C4=90.000“). Welche Spindel was tut,
  sagt maschine.spindeln() (Manuel, 2026-10-03: „in meinem Beispiel: C4 muss sich
  positionieren, das ist die Hauptspindel, und S1 muss die Drehzahl anmachen“): Die C-Achse
  eines Werkzeugantriebs richtet nur das Werkzeug aus und ist nie die Rundachse der Bahn.
- Vorschub: G93 (1 ÷ Zeit) und zurück auf Vorschub je Minute mit dem Befehl der Steuerung –
  bei Fanuc und Haas an der Drehmaschine G98 (G94 ist dort ein Plandrehzyklus).
- F wie FreeCAD es speichert (mm/s bzw. 1 ÷ s) mal 60; in G93 mit mehr Stellen.
- Vor jedem Werkzeugwechsel und am Ende zum Wechselpunkt der Maschine (Manuel, 2026-10-03:
  „was wir hier aber noch benötigen: einen Werkzeugwechselpunkt … MKS, nicht WKS … oder
  wechselbar“): zuerst die Achse, die das Werkzeug wegzieht (an der Drehmaschine X, sonst Z),
  dann die anderen – in MKS mit dem Befehl der Steuerung („G53 G0“, Siemens „G0 SUPA D0“), in
  WKS als „G0“ im Programm.

Ohne Maschine schreibt er für eine Fräse – nichts schlechter als FreeCADs Postprozessoren.
Die Befehle jeder Steuerung lassen sich ändern (Steuerung ist ein dataclass, ersetzt wird mit
dataclasses.replace; gui_programm speichert Änderungen je Steuerung). Was nicht aus einer
Herstelleranleitung nachgeprüft ist (Fanuc: angetriebenes Werkzeug und C-Achse legt der
Maschinenhersteller fest), steht als Kommentar im Programm und gelb im Fenster.

Der Kern rechnet nur mit Daten (Abschnitt, Maschineninfo) – programm(); abschnitte() und
maschineninfo() holen sie aus FreeCAD. Läuft ohne Oberfläche.
"""

import dataclasses
import re
from dataclasses import dataclass, field

from . import schwenken as sw
from .sprache import tr

STELLEN = 3  # Nachkommastellen der Koordinaten und des Vorschubs je Minute
STELLEN_G93 = 5  # in G93 ist F 1 ÷ Zeit – oft kleiner als 1
SATZNUMMER_SCHRITT = 10  # N10, N20 …
TOLERANZ_BEREICH = (0.001, 1.0)  # mm – die Toleranz fürs Glätten
BEWEGUNG = ("G0", "G00", "G1", "G01", "G2", "G02", "G3", "G03")
WEG_ADRESSEN = ("X", "Y", "Z", "A", "B", "C")  # zählen beim Vorschub ohne G93
# Die Reihenfolge der Adressen in einem Satz.
ADRESSEN = ("X", "Y", "Z", "A", "B", "C", "U", "V", "W", "I", "J", "K", "R", "P", "Q", "L", "F")
ROTATION = ("A", "B", "C")


@dataclass(frozen=True)
class Glaetten:
    """Ein Befehl für Vorausschau und Glätten (Spezifikation Steuerung, Abschnitt 7): die
    Zeilen im Programmkopf ({toleranz}: die Toleranz in mm), ob er vorbelegt an ist und ob er
    eine Option der Steuerung sein kann – ohne sie bleibt die Steuerung mit Alarm stehen."""

    kennung: str
    befehl: str
    an: bool
    option: bool = False


@dataclass(frozen=True)
class Steuerung:
    """Die Befehle einer Steuerung. Platzhalter: {t} Werkzeugnummer, {s} Drehzahl, {m} 3 oder 4
    (Drehrichtung), {n} Nummer des Antriebs, {h} Nummer der Hauptspindel, {name} Programmname.
    Leer: der Befehl entfällt."""

    kennung: str
    name: str
    endung: str  # Dateiendung des Programms
    kommentar: str  # „(“ … „)“ oder „; “
    kopf: str  # Zeilen am Anfang (mit \n getrennt)
    ende: str  # Zeilen am Ende
    kopf_drehen: str  # Zusatz im Kopf an der Drehmaschine (Ebene)
    wechsel_fraesen: str
    wechsel_drehen: str
    spindel_ein: str
    spindel_aus: str
    angetrieben_ein: str
    angetrieben_aus: str
    c_ein: str  # Drehmaschine: Hauptspindel als Rundachse
    c_aus: str
    vorschub_zeit: str  # G93
    vorschub_minute: str  # G94 an der Fräse
    vorschub_minute_drehen: str  # an der Drehmaschine
    kuehlung_flut: str = "M8"
    kuehlung_nebel: str = "M7"
    kuehlung_aus: str = "M9"
    # Zum Wechselpunkt der Maschine – {achsen}: „X200.000 Z300.000“; in MKS bzw. WKS.
    wechselpunkt_mks: str = "G53 G0 {achsen}"
    wechselpunkt_wks: str = "G0 {achsen}"
    gleich_bei_nummer: bool = False  # Siemens: Adresse mit Nummer schreibt „C4=…“
    nur_buchstabe: bool = True  # die Rundachse nur mit ihrem Buchstaben (C statt C4)
    # Befehle, die ein Maschinenhersteller festlegt – im Fenster gelb, im Programm ein Hinweis.
    vom_hersteller: tuple = ()
    glaetten_angebot: tuple = ()  # [Glaetten] – was die Steuerung dafür hat
    wechselpunkt_vorschlaege: tuple = ()  # Befehle zur Wahl für „Zum Wechselpunkt (MKS)“
    # Die Haken (Manuel, 2026-10-03: „die Optionen im Postprozessor besser beschreiben,
    # darstellen, mit Haken machen“; Spezifikation Steuerung, Abschnitte 7 und 8).
    kommentare: bool = True  # Operation und Werkzeug als Kommentar
    satznummern: bool = False  # N10, N20 … vor jedem Satz
    kuehlung: bool = True  # M8/M7 und M9 wie an der Operation
    wechselpunkt: bool = True  # vor jedem Werkzeugwechsel und am Ende zum Wechselpunkt
    c_achse: bool = True  # Drehmaschine: C-Achse ein und aus
    g93: bool = True  # Bahnen mit Rundachse in G93; aus: F in mm/min, Zeit wie G93 (S5)
    glaetten: tuple = None  # Kennungen der eingeschalteten Glaetten; None: die vorbelegten
    toleranz: float = 0.01  # mm – fürs Glätten (G642/CTOL, G64 P)
    # 3+2 (W-014, Spezifikation Strategien 15): die Ebene mit dem Schwenkzyklus der Steuerung
    # schwenken – {x0} {y0} {z0}: der Ursprung der Ebene im Grundjob, {a} {b} {c}: ihre Winkel
    # achsweise um Z, Y, X. Leer oder Haken aus: ohne Zyklus, die Rundachsen und X, Y, Z im
    # Programm gerechnet (schwenken.befehle_ohne_zyklus).
    schwenken: str = ""
    schwenken_aus: str = ""
    schwenkzyklus: bool = True

    def ersetzt(self, **werte):
        """Eine Kopie mit geänderten Befehlen."""
        return dataclasses.replace(self, **werte)

    def glaetten_an(self):
        """Die eingeschalteten Glaetten, in der Reihenfolge des Angebots."""
        an = (
            {g.kennung for g in self.glaetten_angebot if g.an}
            if self.glaetten is None
            else set(self.glaetten)
        )
        return [g for g in self.glaetten_angebot if g.kennung in an]


# Felder, die man im Fenster ändern kann – in dieser Reihenfolge, mit ihrem Text.
BEFEHLSFELDER = (
    "kopf",
    "kopf_drehen",
    "ende",
    "wechsel_fraesen",
    "wechsel_drehen",
    "wechselpunkt_mks",
    "wechselpunkt_wks",
    "spindel_ein",
    "spindel_aus",
    "angetrieben_ein",
    "angetrieben_aus",
    "c_ein",
    "c_aus",
    "vorschub_zeit",
    "vorschub_minute",
    "vorschub_minute_drehen",
    "kuehlung_flut",
    "kuehlung_nebel",
    "kuehlung_aus",
    "schwenken",
    "schwenken_aus",
)

# Die Haken – (Name, Typ) wie in Steuerung; im Fenster je eine Zeile mit Erklärung.
HAKEN = ("kommentare", "satznummern", "kuehlung", "wechselpunkt", "c_achse", "g93", "schwenkzyklus")

_KOPF_FRAESEN = "%\n{kommentar_name}\nG17 G21 G40 G49 G80 G90"
_MKS = ("G53 G0 {achsen}",)
_ENDE = "M5\nM9\nM30\n%"

STEUERUNGEN = {
    "linuxcnc": Steuerung(
        "linuxcnc",
        "LinuxCNC",
        ".ngc",
        "(",
        _KOPF_FRAESEN,
        _ENDE,
        "G18",
        "T{t} M6",
        "T{t} M6",
        "M{m} S{s}",
        "M5",
        "M{m} ${n} S{s}",
        "M5 ${n}",
        "",
        "",
        "G93",
        "G94",
        "G94",
        # LinuxCNC: G64 P (Toleranz der Bahn) Q (gerade Stücke zusammenfassen).
        glaetten_angebot=(Glaetten("g64", "G64 P{toleranz} Q{toleranz}", True),),
        wechselpunkt_vorschlaege=_MKS,
    ),
    "siemens": Steuerung(
        "siemens",
        "Siemens 840D",
        ".mpf",
        "; ",
        "{kommentar_name}\nG17 G71 G90 G40",
        "M5\nM9\nM30",
        "G18",
        "T{t} M6",
        "T{t} D1",
        "M{m} S{s}",
        "M5",
        "M{n}={m} S{n}={s}",
        "M{n}=5",
        "SPOS[{h}]=0",
        "SPCOF({h})",
        "G93",
        "G94",
        "G94",
        # SUPA: Maschinenkoordinaten ohne Verschiebungen; D0 ohne Werkzeugkorrektur – der
        # Wechselpunkt gilt für den Werkzeugträger.
        wechselpunkt_mks="G0 SUPA D0 {achsen}",
        gleich_bei_nummer=True,
        nur_buchstabe=False,
        # Programmierhandbuch Arbeitsvorbereitung 10/2015 (S. 470–471: CTOL) und Grundlagen
        # (G64, G642, SOFT); COMPCAD ist der Satzkompressor – oft eine Option.
        glaetten_angebot=(
            Glaetten("g64", "G64", True),
            Glaetten("g642", "G642", True),
            Glaetten("ctol", "CTOL={toleranz}", True),
            Glaetten("soft", "SOFT", True),
            Glaetten("compcad", "COMPCAD", False, True),
        ),
        # S. 109: „G0 G40 G60 G90 SUPA X450 Y300 Z300 D0 … Werkzeugwechselpunkt anfahren“;
        # F_HOME ist ShopTurns Zyklus, G75 „Festpunkt anfahren“ (P-2026-10-03-26).
        wechselpunkt_vorschlaege=("G0 SUPA D0 {achsen}", "F_HOME", "G75 {achsen} FP=1"),
        # S. 678–681: CYCLE800(_FR, _TC, _ST, _MODE, _X0, _Y0, _Z0, _A, _B, _C, _X1, _Y1, _Z1,
        # _DIR, _FR_I, _DMODE) – Freifahren Maschinenachse Z, Schwenkdatensatz "" (nur einer),
        # neu, Modus 27 (achsweise, Reihenfolge Z, Y, X), Bezugspunkt vor der Drehung, die
        # Winkel, Richtung −1, G17. Zurück: CYCLE800() (Grundlagen, Beispiel N10).
        schwenken='CYCLE800(1,"",0,27,{x0},{y0},{z0},{a},{b},{c},0,0,0,-1,0,1)',
        schwenken_aus="CYCLE800()",
    ),
    "fanuc": Steuerung(
        "fanuc",
        "Fanuc",
        ".nc",
        "(",
        "%\nO0001 {kommentar_name}\nG17 G21 G40 G49 G80 G90",
        _ENDE,
        "G18",
        "T{t} M6",
        "T{t:02d}{t:02d}",
        "M{m} S{s}",
        "M5",
        "M{m} S{s}",
        "M5",
        "",
        "",
        "G93",
        "G94",
        "G98",
        vom_hersteller=("angetrieben_ein", "angetrieben_aus", "c_ein", "c_aus"),
        # Vorausschau und AI-Konturregelung sind bei Fanuc Optionen – vorbelegt aus.
        glaetten_angebot=(
            Glaetten("g08", "G08 P1", False, True),
            Glaetten("g051", "G05.1 Q1", False, True),
        ),
        wechselpunkt_vorschlaege=_MKS,
    ),
    "haas": Steuerung(
        "haas",
        "Haas",
        ".nc",
        "(",
        "%\nO00001 {kommentar_name}\nG17 G21 G40 G49 G80 G90",
        _ENDE,
        "G18",
        "T{t} M6",
        "T{t}{t:02d}",
        "M{m} S{s}",
        "M5",
        "M133 P{s}",
        "M135",
        "M154",
        "M155",
        "G93",
        "G94",
        "G98",
        # Ohne G187 gilt die Glättung aus Einstellung 191 der Maschine.
        glaetten_angebot=(Glaetten("g187", "G187 P3", False),),
        wechselpunkt_vorschlaege=_MKS,
    ),
    "mach": Steuerung(
        "mach",
        "Mach3/Mach4",
        ".tap",
        "(",
        _KOPF_FRAESEN,
        _ENDE,
        "G18",
        "T{t} M6",
        "T{t:02d}{t:02d}",
        "M{m} S{s}",
        "M5",
        "M{m} S{s}",
        "M5",
        "",
        "",
        "G93",
        "G94",
        "G94",
        glaetten_angebot=(Glaetten("g64", "G64", True),),
        wechselpunkt_vorschlaege=_MKS,
    ),
}
VORGABE = "linuxcnc"  # ohne Wahl: wie LinuxCNC (Spezifikation Steuerung, Abschnitt 4)


@dataclass
class Maschineninfo:
    """Was der Postprozessor von der Maschine wissen muss – ohne Maschine: eine Fräse."""

    name: str = ""
    drehmaschine: bool = False
    x_durchmesser: bool = False  # X im Programm als Durchmesser (Drehmaschine)
    rundachsen: dict = field(default_factory=dict)  # Buchstabe → NC-Name („C“ → „C4“)
    angetrieben: dict = field(default_factory=dict)  # Werkzeugnummer → Nummer des Antriebs
    # Der Wechselpunkt: Buchstabe → Stellung (mm; X als Radius, wie gespeichert); leer: keiner.
    wechselpunkt: dict = field(default_factory=dict)
    wechsel_wks: bool = False  # er zählt in Werkstückkoordinaten (sonst MKS)
    hauptspindel: str = ""  # ihre Nummer („4“ bei S4/C4); leer: keine bekannt
    hauptspindel_name: str = ""  # ihr NC-Name („S4“)
    antrieb_c: dict = field(default_factory=dict)  # Nummer des Antriebs → seine C-Achse („C1“)


@dataclass
class Abschnitt:
    """Eine Operation: Name, Werkzeug, Spindel und ihre Befehle (Path.Command oder
    (Name, {Adresse: Wert}))."""

    name: str
    werkzeug: int  # T-Nummer; 0: keins
    drehzahl: float
    rueckwaerts: bool  # Spindel links (M4)
    kuehlung: str = "None"  # FreeCADs CoolantMode: None, Flood, Mist
    befehle: list = field(default_factory=list)
    werkzeugname: str = ""
    # 3+2: die Schwenkung des Jobs (schwenken.Schwenkung) – die Befehle in Koordinaten der Ebene.
    schwenkung: object = None


@dataclass
class Programm:
    zeilen: list
    hinweise: list  # Sätze für den Menschen (Herstellerbefehle, ohne Maschine …)
    saetze: int  # Bewegungssätze

    @property
    def text(self):
        return "\n".join(self.zeilen) + "\n"


def feld_text(feld):
    """(Name, Erklärung) eines Befehls für das Fenster – die Schlüssel wörtlich, damit die
    Sprachprüfung sie findet."""
    return {
        "kopf": (tr("pp.feld.kopf"), tr("pp.feld.kopf.tooltip")),
        "kopf_drehen": (tr("pp.feld.kopf_drehen"), tr("pp.feld.kopf_drehen.tooltip")),
        "ende": (tr("pp.feld.ende"), tr("pp.feld.ende.tooltip")),
        "wechsel_fraesen": (tr("pp.feld.wechsel_fraesen"), tr("pp.feld.wechsel_fraesen.tooltip")),
        "wechsel_drehen": (tr("pp.feld.wechsel_drehen"), tr("pp.feld.wechsel_drehen.tooltip")),
        "wechselpunkt_mks": (
            tr("pp.feld.wechselpunkt_mks"),
            tr("pp.feld.wechselpunkt_mks.tooltip"),
        ),
        "wechselpunkt_wks": (
            tr("pp.feld.wechselpunkt_wks"),
            tr("pp.feld.wechselpunkt_wks.tooltip"),
        ),
        "spindel_ein": (tr("pp.feld.spindel_ein"), tr("pp.feld.spindel_ein.tooltip")),
        "spindel_aus": (tr("pp.feld.spindel_aus"), tr("pp.feld.spindel_aus.tooltip")),
        "angetrieben_ein": (tr("pp.feld.angetrieben_ein"), tr("pp.feld.angetrieben_ein.tooltip")),
        "angetrieben_aus": (tr("pp.feld.angetrieben_aus"), tr("pp.feld.angetrieben_aus.tooltip")),
        "c_ein": (tr("pp.feld.c_ein"), tr("pp.feld.c_ein.tooltip")),
        "c_aus": (tr("pp.feld.c_aus"), tr("pp.feld.c_aus.tooltip")),
        "vorschub_zeit": (tr("pp.feld.vorschub_zeit"), tr("pp.feld.vorschub_zeit.tooltip")),
        "vorschub_minute": (tr("pp.feld.vorschub_minute"), tr("pp.feld.vorschub_minute.tooltip")),
        "vorschub_minute_drehen": (
            tr("pp.feld.vorschub_minute_drehen"),
            tr("pp.feld.vorschub_minute_drehen.tooltip"),
        ),
        "kuehlung_flut": (tr("pp.feld.kuehlung_flut"), tr("pp.feld.kuehlung_flut.tooltip")),
        "kuehlung_nebel": (tr("pp.feld.kuehlung_nebel"), tr("pp.feld.kuehlung_nebel.tooltip")),
        "kuehlung_aus": (tr("pp.feld.kuehlung_aus"), tr("pp.feld.kuehlung_aus.tooltip")),
        "schwenken": (tr("pp.feld.schwenken"), tr("pp.feld.schwenken.tooltip")),
        "schwenken_aus": (tr("pp.feld.schwenken_aus"), tr("pp.feld.schwenken_aus.tooltip")),
    }.get(feld, (feld, ""))


def haken_text(feld):
    """(Name, Erklärung) eines Hakens fürs Fenster – die Schlüssel wörtlich."""
    return {
        "kommentare": (tr("pp.haken.kommentare"), tr("pp.haken.kommentare.erklaerung")),
        "satznummern": (tr("pp.haken.satznummern"), tr("pp.haken.satznummern.erklaerung")),
        "kuehlung": (tr("pp.haken.kuehlung"), tr("pp.haken.kuehlung.erklaerung")),
        "wechselpunkt": (tr("pp.haken.wechselpunkt"), tr("pp.haken.wechselpunkt.erklaerung")),
        "c_achse": (tr("pp.haken.c_achse"), tr("pp.haken.c_achse.erklaerung")),
        "g93": (tr("pp.haken.g93"), tr("pp.haken.g93.erklaerung")),
        "schwenkzyklus": (tr("pp.haken.schwenkzyklus"), tr("pp.haken.schwenkzyklus.erklaerung")),
    }.get(feld, (feld, ""))


def glaetten_text(steuerung_kennung, kennung):
    """(Name, Erklärung) eines Befehls zum Glätten der Steuerung – die Schlüssel wörtlich."""
    return {
        ("linuxcnc", "g64"): (
            tr("pp.glaetten.linuxcnc.g64"),
            tr("pp.glaetten.linuxcnc.g64.erklaerung"),
        ),
        ("siemens", "g64"): (
            tr("pp.glaetten.siemens.g64"),
            tr("pp.glaetten.siemens.g64.erklaerung"),
        ),
        ("siemens", "g642"): (
            tr("pp.glaetten.siemens.g642"),
            tr("pp.glaetten.siemens.g642.erklaerung"),
        ),
        ("siemens", "ctol"): (
            tr("pp.glaetten.siemens.ctol"),
            tr("pp.glaetten.siemens.ctol.erklaerung"),
        ),
        ("siemens", "soft"): (
            tr("pp.glaetten.siemens.soft"),
            tr("pp.glaetten.siemens.soft.erklaerung"),
        ),
        ("siemens", "compcad"): (
            tr("pp.glaetten.siemens.compcad"),
            tr("pp.glaetten.siemens.compcad.erklaerung"),
        ),
        ("fanuc", "g08"): (tr("pp.glaetten.fanuc.g08"), tr("pp.glaetten.fanuc.g08.erklaerung")),
        ("fanuc", "g051"): (tr("pp.glaetten.fanuc.g051"), tr("pp.glaetten.fanuc.g051.erklaerung")),
        ("haas", "g187"): (tr("pp.glaetten.haas.g187"), tr("pp.glaetten.haas.g187.erklaerung")),
        ("mach", "g64"): (tr("pp.glaetten.mach.g64"), tr("pp.glaetten.mach.g64.erklaerung")),
    }.get((steuerung_kennung, kennung), (kennung, ""))


def steuerung(kennung, aenderungen=None):
    """Die Steuerung mit dieser Kennung (sonst die Vorgabe), mit den Änderungen `aenderungen`
    des Benutzers: {Befehl: Text, Haken: bool, "toleranz": mm, "glaetten": [Kennung]} – was
    nicht passt, zählt nicht."""
    s = STEUERUNGEN.get(kennung) or STEUERUNGEN[VORGABE]
    return s.ersetzt(**gueltige_aenderungen(aenderungen)) if aenderungen else s


def gueltige_aenderungen(aenderungen):
    """Die Änderungen, die zu einer Steuerung passen (steuerung())."""
    werte = {}
    for feld, wert in (aenderungen or {}).items():
        passt = (feld in BEFEHLSFELDER and isinstance(wert, str)) or (
            feld in HAKEN and isinstance(wert, bool)
        )
        if passt:
            werte[feld] = wert
        elif feld == "toleranz" and isinstance(wert, (int, float)) and not isinstance(wert, bool):
            werte[feld] = min(max(float(wert), TOLERANZ_BEREICH[0]), TOLERANZ_BEREICH[1])
        elif feld == "glaetten" and isinstance(wert, (list, tuple)):
            werte[feld] = tuple(str(k) for k in wert)
    return werte


def _zahl(wert, stellen=STELLEN):
    text = f"{wert:.{stellen}f}"
    return "0." + "0" * stellen if text.startswith("-") and float(text) == 0.0 else text


def _kommentar(s, text):
    text = text.replace("(", "[").replace(")", "]")
    return f"; {text}" if s.kommentar.strip() == ";" else f"({text})"


def _fuellen(vorlage, **werte):
    """Ein Befehl mit seinen Platzhaltern – {t:02d} geht nur mit Zahlen."""
    if not vorlage:
        return ""
    try:
        return vorlage.format(**werte)
    except (KeyError, ValueError, IndexError):
        return vorlage


def _zeilen(text):
    return [z.rstrip() for z in (text or "").split("\n") if z.strip()]


def _adresse(s, buchstabe, info):
    """Wie die Adresse im Programm heißt: die Rundachse mit dem NC-Namen der Maschine, wenn
    die Steuerung ihn nimmt (Siemens), sonst ihr Buchstabe."""
    if buchstabe in ROTATION and not s.nur_buchstabe:
        return info.rundachsen.get(buchstabe, buchstabe)
    return buchstabe


def _wort(s, adresse, zahl):
    """„X12.000“ – bei Siemens eine Adresse mit Nummer mit „=“: „C4=90.000“."""
    if s.gleich_bei_nummer and re.search(r"\d$", adresse):
        return f"{adresse}={zahl}"
    return f"{adresse}{zahl}"


def _befehl(eintrag):
    """(Name, {Adresse: Wert}) aus einem Path.Command oder einem Paar."""
    if isinstance(eintrag, tuple):
        return eintrag[0], dict(eintrag[1])
    return eintrag.Name, dict(eintrag.Parameters)


def programm(abschnitte, s, info=None, name="", vorschau=None):
    """Das Programm (Programm) für die Abschnitte mit der Steuerung `s` und der Maschine
    `info`. `vorschau`: höchstens so viele Bewegungssätze, dann ein Hinweis – fürs Fenster."""
    info = info or Maschineninfo()
    zeilen, hinweise = [], []

    def notiz(text):
        if s.kommentare:
            zeilen.append(_kommentar(s, text))

    kommentar_name = _kommentar(s, name or tr("pp.programm")) if s.kommentare else ""
    for zeile in _zeilen(_fuellen(s.kopf, kommentar_name=kommentar_name, name=name)):
        zeilen.append(zeile)
    if info.drehmaschine:
        zeilen.extend(_zeilen(s.kopf_drehen))
    for glaetten in s.glaetten_an():
        zeilen.extend(_zeilen(_fuellen(glaetten.befehl, toleranz=_zahl(s.toleranz))))
        if glaetten.option:
            hinweise.append(tr("pp.hinweis.option", befehl=glaetten.befehl.split("\n")[0]))
    if not info.name:
        hinweise.append(tr("pp.hinweis.ohne_maschine"))
    werkzeug = None
    spindel_an = None  # ("haupt" oder Nummer des Antriebs, Drehzahl, Richtung)
    c_an = False
    g93 = False
    stand = {}  # Adresse → Wert, wie zuletzt angefahren (für den Vorschub ohne G93)
    saetze = 0
    gesehen = set()
    geschwenkt = None  # die Schwenkung, in der die Maschine gerade steht
    zyklus = bool(s.schwenkzyklus and s.schwenken)
    for abschnitt in abschnitte:
        notiz(abschnitt.name)
        befehle_roh = abschnitt.befehle
        if abschnitt.schwenkung is not None and not zyklus:
            try:
                befehle_roh = sw.befehle_ohne_zyklus(befehle_roh, abschnitt.schwenkung)
            except ValueError as grund:
                hinweise.append(f"{abschnitt.name}: {grund}")
                zeilen.append(_kommentar(s, f"{abschnitt.name}: {grund}"))
                continue
        befehle = [_befehl(b) for b in befehle_roh]
        gewechselt = False
        if abschnitt.werkzeug and abschnitt.werkzeug != werkzeug:
            if spindel_an is not None:
                zeilen.extend(_spindel_aus(s, spindel_an))
                spindel_an = None
            zeilen.extend(_zum_wechselpunkt(s, info))
            if geschwenkt is not None and not sw.gleiche(geschwenkt, abschnitt.schwenkung):
                zeilen.extend(_schwenken_aus(s, geschwenkt, zyklus))
                geschwenkt = None
            if abschnitt.werkzeugname:
                notiz(f"T{abschnitt.werkzeug} {abschnitt.werkzeugname}")
            vorlage = s.wechsel_drehen if info.drehmaschine else s.wechsel_fraesen
            zeilen.append(_fuellen(vorlage, t=int(abschnitt.werkzeug)))
            werkzeug = abschnitt.werkzeug
            gewechselt = True
        if not sw.gleiche(geschwenkt, abschnitt.schwenkung):
            # Eine andere Ebene: erst weg vom Teil (ohne Zyklus; CYCLE800 fährt selbst frei).
            if not gewechselt and not zyklus:
                if spindel_an is not None:
                    zeilen.extend(_spindel_aus(s, spindel_an))
                    spindel_an = None
                zeilen.extend(_zum_wechselpunkt(s, info))
            if geschwenkt is not None and abschnitt.schwenkung is None:
                zeilen.extend(_schwenken_aus(s, geschwenkt, zyklus))
            if abschnitt.schwenkung is not None:
                rund = sw.text_rundachsen(abschnitt.schwenkung.rund, programm=True)
                notiz(tr("pp.ebene", rundachsen=rund))
                if zyklus:
                    zeilen.extend(_schwenken_ein(s, abschnitt.schwenkung))
            geschwenkt = abschnitt.schwenkung
        mit_rundachse = any(set(p) & set(ROTATION) for _n, p in befehle)
        if info.drehmaschine and mit_rundachse and not c_an and s.c_achse:
            # Auch ohne Befehl der Hinweis: Gerade dann muss ihn jemand eintragen (Fanuc).
            _hersteller(s, "c_ein", hinweise, gesehen, zeilen)
            if s.c_ein:
                zeilen.extend(_zeilen(_fuellen(s.c_ein, h=_haupt(info))))
                c_an = True
        antrieb = info.angetrieben.get(int(abschnitt.werkzeug or 0)) if info.drehmaschine else None
        soll = (antrieb or "haupt", round(abschnitt.drehzahl, 3), abschnitt.rueckwaerts)
        if abschnitt.drehzahl > 0 and soll != spindel_an:
            if spindel_an is not None:
                zeilen.extend(_spindel_aus(s, spindel_an))
            m = 4 if abschnitt.rueckwaerts else 3
            drehzahl = f"{abschnitt.drehzahl:.0f}"
            if antrieb:
                zeilen.append(_fuellen(s.angetrieben_ein, m=m, s=drehzahl, n=antrieb))
                _hersteller(s, "angetrieben_ein", hinweise, gesehen, zeilen)
            else:
                zeilen.append(_fuellen(s.spindel_ein, m=m, s=drehzahl))
            spindel_an = soll
        kuehlung = {"Flood": s.kuehlung_flut, "Mist": s.kuehlung_nebel}.get(abschnitt.kuehlung)
        if not s.kuehlung:
            kuehlung = None
        if kuehlung:
            zeilen.append(kuehlung)
        for name_, parameter in befehle:
            if name_.startswith("("):
                notiz(name_.strip("()"))
                continue
            gross = name_.upper()
            if gross == "G93":
                g93 = True
                if s.g93:
                    zeilen.append(s.vorschub_zeit)
                continue
            if gross == "G94":
                g93 = False
                if s.g93:
                    vorlage = s.vorschub_minute_drehen if info.drehmaschine else s.vorschub_minute
                    zeilen.append(vorlage)
                continue
            if info.drehmaschine and gross in ("G98", "G99") and s.vorschub_minute_drehen == "G98":
                # An Fanuc- und Haas-Drehmaschinen heißt G98/G99 Vorschub je Minute/Umdrehung,
                # nicht Rückzug im Bohrzyklus – weglassen.
                continue
            woerter = [gross]
            bewegung = gross in BEWEGUNG
            weg = _weg(stand, parameter) if bewegung else 0.0
            if bewegung:
                stand.update({a: float(parameter[a]) for a in WEG_ADRESSEN if a in parameter})
            for adresse in ADRESSEN:
                if adresse not in parameter:
                    continue
                wert = float(parameter[adresse])
                if adresse == "F":
                    wert *= 60.0
                    if g93 and not s.g93:
                        # Ohne G93 (S5): F in mm/min so, dass die Zeit des Satzes stimmt – der Weg
                        # aus X, Y, Z und den Rundachsen in Grad (Spezifikation, Abschnitt 5).
                        if weg > 1e-9:
                            woerter.append(_wort(s, "F", _zahl(weg * wert)))
                        continue
                    woerter.append(_wort(s, "F", _zahl(wert, STELLEN_G93 if g93 else STELLEN)))
                    continue
                if adresse == "X" and info.drehmaschine and info.x_durchmesser:
                    wert *= 2.0
                woerter.append(_wort(s, _adresse(s, adresse, info), _zahl(wert)))
            zeilen.append(" ".join(woerter))
            if bewegung:
                saetze += 1
                if vorschau is not None and saetze >= vorschau:
                    zeilen = _nummeriert(zeilen, s)
                    zeilen.append(_kommentar(s, tr("pp.vorschau_ende")))
                    return Programm(zeilen, hinweise, saetze)
        if kuehlung:
            zeilen.append(s.kuehlung_aus)
    if spindel_an is not None:
        zeilen.extend(_spindel_aus(s, spindel_an))
    if werkzeug is not None:
        zeilen.extend(_zum_wechselpunkt(s, info))
    if geschwenkt is not None:
        zeilen.extend(_schwenken_aus(s, geschwenkt, zyklus))
    if c_an and s.c_aus:
        zeilen.extend(_zeilen(_fuellen(s.c_aus, h=_haupt(info))))
    zeilen.extend(_zeilen(s.ende))
    return Programm(_nummeriert(zeilen, s), hinweise, saetze)


def _schwenken_ein(s, schwenkung):
    """Der Schwenkzyklus für die Ebene (Steuerung.schwenken)."""
    (x0, y0, z0), (a, b, c) = sw.zyklus_winkel(schwenkung.ebene)
    werte = {"x0": x0, "y0": y0, "z0": z0, "a": a, "b": b, "c": c}
    return _zeilen(_fuellen(s.schwenken, **{k: _zahl(v) for k, v in werte.items()}))


def _schwenken_aus(s, schwenkung, zyklus):
    """Zurück aus der Ebene: der Zyklus zurück – ohne Zyklus erst hoch genug
    (Schwenkung.hoehe), dann die Rundachsen auf 0."""
    if zyklus:
        return _zeilen(s.schwenken_aus)
    zeilen = []
    if schwenkung.hoehe is not None:
        zeilen.append(f"G0 {_wort(s, 'Z', _zahl(schwenkung.hoehe))}")
    woerter = [_wort(s, b, _zahl(0.0)) for b in sorted(schwenkung.rund)]
    if woerter:
        zeilen.append(" ".join(["G0", *woerter]))
    return zeilen


def _weg(stand, parameter):
    """Der Weg eines Satzes von `stand` aus: √(ΔX² + ΔY² + ΔZ² + ΔA² + ΔB² + ΔC²), die Rundachsen
    in Grad – so zählen Steuerungen ohne G93 den Vorschub; ein Bogen zählt als Sehne."""
    summe = 0.0
    for adresse in WEG_ADRESSEN:
        if adresse in parameter and adresse in stand:
            summe += (float(parameter[adresse]) - stand[adresse]) ** 2
    return summe**0.5


def _nummeriert(zeilen, s):
    """Mit Satznummern (N10, N20 …), wenn die Steuerung sie schreiben soll – nicht vor „%“, der
    Programmnummer (O…) und reinen Kommentaren."""
    if not s.satznummern:
        return zeilen
    ergebnis, nummer = [], 0
    for zeile in zeilen:
        roh = zeile.strip()
        if roh == "%" or re.match(r"O\d", roh) or roh.startswith(("(", ";")):
            ergebnis.append(zeile)
            continue
        nummer += SATZNUMMER_SCHRITT
        ergebnis.append(f"N{nummer} {zeile}")
    return ergebnis


def _zum_wechselpunkt(s, info):
    if not s.wechselpunkt:
        return []
    return _wechselpunkt_saetze(s, info)


def _wechselpunkt_saetze(s, info):
    """Die Sätze zum Wechselpunkt: zuerst die Achse, die das Werkzeug wegzieht (an der
    Drehmaschine X, sonst Z), dann die anderen – leer ohne Wechselpunkt oder Befehl. Ein Befehl
    ohne {achsen} kennt den Punkt selbst – etwa ShopTurns Zyklus F_HOME, der zum
    Werkzeugwechselpunkt aus dem Programmkopf fährt (Manuel, 2026-10-03: „aber was ist mit
    F_HOME?“): Er steht einmal da, auch ohne Wechselpunkt an der Maschine."""
    vorlage = s.wechselpunkt_wks if info.wechsel_wks else s.wechselpunkt_mks
    if not vorlage:
        return []
    if "{achsen}" not in vorlage:
        return _zeilen(vorlage) if info.name else []
    if not info.wechselpunkt:
        return []
    zuerst = "X" if info.drehmaschine else "Z"

    def woerter(buchstaben):
        ergebnis = []
        for b in buchstaben:
            wert = float(info.wechselpunkt[b])
            if b == "X" and info.drehmaschine and info.x_durchmesser:
                wert *= 2.0
            ergebnis.append(_wort(s, b, _zahl(wert)))
        return " ".join(ergebnis)

    reihenfolge = [b for b in ("X", "Y", "Z") if b in info.wechselpunkt]
    zeilen = []
    if zuerst in reihenfolge and len(reihenfolge) > 1:
        zeilen.extend(_zeilen(_fuellen(vorlage, achsen=woerter([zuerst]))))
    zeilen.extend(_zeilen(_fuellen(vorlage, achsen=woerter(reihenfolge))))
    return zeilen


def _haupt(info):
    """Die Nummer der Hauptspindel für {h} – ohne bekannte die 1."""
    return info.hauptspindel or "1"


def _spindel_aus(s, an):
    antrieb = an[0]
    if antrieb == "haupt":
        return _zeilen(s.spindel_aus)
    return _zeilen(_fuellen(s.angetrieben_aus, n=antrieb))


def _hersteller(s, feld, hinweise, gesehen, zeilen):
    """Ein Befehl, den der Maschinenhersteller festlegt: ein Kommentar im Programm und ein
    Satz im Fenster – je Befehl einmal."""
    if feld not in s.vom_hersteller or feld in gesehen:
        return
    gesehen.add(feld)
    satz = tr("pp.hinweis.hersteller", befehl=feld_text(feld)[0], steuerung=s.name)
    hinweise.append(satz)
    if s.kommentare:
        zeilen.append(_kommentar(s, satz))


# --- Aus FreeCAD ---------------------------------------------------------------------------


def abschnitte(job, maschine=None, mit_ebenen=True):
    """[Abschnitt] – die aktiven Operationen des Jobs mit Bahn, in ihrer Reihenfolge. Ist der
    Job eine geschwenkte Ebene (3+2), tragen sie ihre Schwenkung; hat er Ebenen
    (`mit_ebenen`), folgen deren Operationen – ein Programm für die Aufspannung (Spezifikation
    Strategien 15, F3). `maschine`: schwenken.Maschine für das Programm ohne Schwenkzyklus –
    oder eine Funktion Operation → schwenken.Maschine (oder None), je Werkzeug mit seiner Länge:
    Am Schwenkkopf hängen die Punkte im Programm davon ab."""
    ergebnis = _abschnitte_des_jobs(job, maschine)
    if mit_ebenen and not sw.ist_ebene(job):
        for ebene in sw.ebenen_von(job):
            ergebnis += _abschnitte_des_jobs(ebene, maschine)
    return ergebnis


def _abschnitte_des_jobs(job, maschine):
    ergebnis = []
    geschwenkt = sw.ist_ebene(job)
    gerechnet = {}  # id(Maschine) → (Maschine, Schwenkung): je Werkzeug einmal
    for op in getattr(getattr(job, "Operations", None), "Group", []):
        if not getattr(op, "Active", True) or getattr(op, "Path", None) is None:
            continue
        schwenkung = None
        if geschwenkt:
            fuer_op = maschine(op) if callable(maschine) else maschine
            if id(fuer_op) not in gerechnet:
                gerechnet[id(fuer_op)] = (fuer_op, sw.schwenkung_fuer(job, fuer_op))
            schwenkung = gerechnet[id(fuer_op)][1]
        tc = getattr(op, "ToolController", None)
        nummer = int(getattr(tc, "ToolNumber", 0) or 0) if tc is not None else 0
        drehzahl = float(getattr(tc, "SpindleSpeed", 0.0) or 0.0) if tc is not None else 0.0
        richtung = str(getattr(tc, "SpindleDir", "Forward")) if tc is not None else "Forward"
        werkzeug = getattr(tc, "Tool", None) if tc is not None else None
        ergebnis.append(
            Abschnitt(
                op.Label,
                nummer,
                drehzahl if richtung != "None" else 0.0,
                richtung == "Reverse",
                str(getattr(op, "CoolantMode", "None")),
                list(op.Path.Commands),
                getattr(werkzeug, "Label", "") if werkzeug is not None else "",
                schwenkung,
            )
        )
    return ergebnis


def maschineninfo(job):
    """Maschineninfo aus der Maschine, die sich der Job gemerkt hat (D-20) – ohne:
    Maschineninfo()."""
    from . import reichweite as rw

    return maschineninfo_datei(rw.gemerkte_maschine(job))


def maschineninfo_datei(pfad):
    """Maschineninfo aus der Maschinendatei `pfad` – ist sie nicht offen, wird sie verborgen
    geöffnet und wieder geschlossen. Ohne Datei: Maschineninfo()."""
    import os

    import FreeCAD

    from . import maschinenspeicher as msp

    if not pfad or not os.path.isfile(pfad):
        return Maschineninfo()
    dok = next(
        (d for d in FreeCAD.listDocuments().values() if msp.gleiche_datei(d.FileName, pfad)),
        None,
    )
    if dok is not None:
        return maschineninfo_dokument(dok)
    try:
        dok = FreeCAD.openDocument(pfad, True)
    except Exception:  # eine beschädigte Datei: ohne Maschine schreiben
        return Maschineninfo()
    try:
        return maschineninfo_dokument(dok)
    finally:
        FreeCAD.closeDocument(dok.Name)


def maschineninfo_dokument(dok):
    """Maschineninfo aus der ersten Maschine im (offenen) Dokument – auch ungespeichert."""
    from . import maschine as m
    from . import maschinenspeicher as msp

    return _info_aus(dok, m, msp)


def maschinen_zur_wahl():
    """[(Name, Pfad, Dokument)] – die Maschinen, für die geschrieben werden kann: erst die offenen
    (auch ungespeicherte – Pfad leer), dann die gemerkten aus der Liste der Maschinen
    (maschinenspeicher), die nicht offen sind (Dokument None). Manuel (2026-10-03) hatte eine
    Drehmaschine angelegt, aber nicht gespeichert – das Fenster schrieb „Keine Maschine am Job“."""
    import FreeCAD

    from . import maschine as m
    from . import maschinenspeicher as msp

    ergebnis = []
    for dok in FreeCAD.listDocuments().values():
        for objekt in dok.Objects:
            if getattr(objekt, "TypeId", "") != "Assembly::AssemblyObject":
                continue
            maschine = m.finde_maschine(objekt)
            if maschine is not None:
                ergebnis.append((maschine.Label, dok.FileName or "", dok))
                break
    offen = [pfad for _name, pfad, _dok in ergebnis if pfad]
    for eintrag in msp.laden():
        if eintrag.vorhanden and not any(msp.gleiche_datei(eintrag.datei, p) for p in offen):
            ergebnis.append((eintrag.name, eintrag.datei, None))
    return ergebnis


def _info_aus(dok, m, msp):
    for objekt in dok.Objects:
        if getattr(objekt, "TypeId", "") != "Assembly::AssemblyObject":
            continue
        maschine = m.finde_maschine(objekt)
        if maschine is None:
            continue
        eintrag = msp.beschreibe(objekt, maschine)
        info = Maschineninfo(
            maschine.Label,
            eintrag.art == msp.DREHMASCHINE,
            m.x_im_durchmesser(maschine),
        )
        info.wechselpunkt = {
            b.upper(): w for b, w in m.wechselpunkt(maschine).items() if b.upper() in "XYZ"
        }
        info.wechsel_wks = m.wechsel_bezug(maschine) == m.WECHSEL_WKS
        spindeln = m.spindeln(maschine)
        info.hauptspindel = m.nc_nummer(spindeln.haupt)
        if spindeln.haupt is not None:
            info.hauptspindel_name = spindeln.haupt.NcName.strip()
        # Die C-Achse der Hauptspindel zuerst: Sie dreht das Teil. Die C-Achse eines
        # Werkzeugantriebs richtet nur das Werkzeug aus – nie die Rundachse der Bahn.
        positionieren = [ba for ba in m.betriebsarten(maschine) if ba.Art == m.ART_POSITIONIEREN]
        if spindeln.haupt_c is not None:
            positionieren.sort(key=lambda ba: ba is not spindeln.haupt_c)
        for ba in positionieren:
            buchstabe = m.programmname(ba).upper()
            if buchstabe in ROTATION and not spindeln.ist_antrieb_c(ba):
                info.rundachsen.setdefault(buchstabe, ba.NcName.strip() or buchstabe)
        for spindel, c in spindeln.antriebe:
            if c is not None and m.nc_nummer(spindel):
                info.antrieb_c[m.nc_nummer(spindel)] = c.NcName.strip()
        for aufnahme in m.aufnahmen(maschine):
            spindel = getattr(aufnahme, "Spindel", None)
            if aufnahme.Art != m.AUFNAHME_WERKZEUG or spindel is None:
                continue
            nummer = re.sub(r"\D", "", getattr(spindel, "NcName", "") or "")
            if nummer and aufnahme.Platz:
                info.angetrieben[int(aufnahme.Platz)] = nummer
        return info
    return Maschineninfo()


def dateiname(job, s):
    """Der Vorschlag für die Programmdatei: neben dem Dokument, der Name des Jobs, die Endung
    der Steuerung."""
    import os

    ordner = os.path.dirname(getattr(job.Document, "FileName", "") or "") or os.path.expanduser("~")
    name = re.sub(r"[^\w\-]+", "_", job.Label).strip("_") or "programm"
    return os.path.join(ordner, name + s.endung)
