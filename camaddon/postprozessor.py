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

from .sprache import tr

STELLEN = 3  # Nachkommastellen der Koordinaten und des Vorschubs je Minute
STELLEN_G93 = 5  # in G93 ist F 1 ÷ Zeit – oft kleiner als 1
# Die Reihenfolge der Adressen in einem Satz.
ADRESSEN = ("X", "Y", "Z", "A", "B", "C", "U", "V", "W", "I", "J", "K", "R", "P", "Q", "L", "F")
ROTATION = ("A", "B", "C")


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

    def ersetzt(self, **werte):
        """Eine Kopie mit geänderten Befehlen."""
        return dataclasses.replace(self, **werte)


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
)

_KOPF_FRAESEN = "%\n{kommentar_name}\nG17 G21 G40 G49 G80 G90"
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
    ),
    "siemens": Steuerung(
        "siemens",
        "Siemens 840D",
        ".mpf",
        "; ",
        "{kommentar_name}\nG17 G71 G90 G40\nG64",
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
    }.get(feld, (feld, ""))


def steuerung(kennung, aenderungen=None):
    """Die Steuerung mit dieser Kennung (sonst die Vorgabe), mit den Änderungen `aenderungen`
    ({Feld: Text}) des Benutzers."""
    s = STEUERUNGEN.get(kennung) or STEUERUNGEN[VORGABE]
    if aenderungen:
        s = s.ersetzt(**{k: v for k, v in aenderungen.items() if k in BEFEHLSFELDER})
    return s


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
    return [z for z in (text or "").split("\n") if z.strip()]


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
    kommentar_name = _kommentar(s, name or tr("pp.programm"))
    for zeile in _zeilen(_fuellen(s.kopf, kommentar_name=kommentar_name, name=name)):
        zeilen.append(zeile)
    if info.drehmaschine:
        zeilen.extend(_zeilen(s.kopf_drehen))
    if not info.name:
        hinweise.append(tr("pp.hinweis.ohne_maschine"))
    werkzeug = None
    spindel_an = None  # ("haupt" oder Nummer des Antriebs, Drehzahl, Richtung)
    c_an = False
    g93 = False
    saetze = 0
    gesehen = set()
    for abschnitt in abschnitte:
        zeilen.append(_kommentar(s, abschnitt.name))
        befehle = [_befehl(b) for b in abschnitt.befehle]
        if abschnitt.werkzeug and abschnitt.werkzeug != werkzeug:
            if spindel_an is not None:
                zeilen.extend(_spindel_aus(s, spindel_an))
                spindel_an = None
            zeilen.extend(_zum_wechselpunkt(s, info))
            if abschnitt.werkzeugname:
                zeilen.append(_kommentar(s, f"T{abschnitt.werkzeug} {abschnitt.werkzeugname}"))
            vorlage = s.wechsel_drehen if info.drehmaschine else s.wechsel_fraesen
            zeilen.append(_fuellen(vorlage, t=int(abschnitt.werkzeug)))
            werkzeug = abschnitt.werkzeug
        mit_rundachse = any(set(p) & set(ROTATION) for _n, p in befehle)
        if info.drehmaschine and mit_rundachse and not c_an:
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
        if kuehlung:
            zeilen.append(kuehlung)
        for name_, parameter in befehle:
            if name_.startswith("("):
                zeilen.append(_kommentar(s, name_.strip("()")))
                continue
            gross = name_.upper()
            if gross == "G93":
                g93 = True
                zeilen.append(s.vorschub_zeit)
                continue
            if gross == "G94":
                g93 = False
                zeilen.append(s.vorschub_minute_drehen if info.drehmaschine else s.vorschub_minute)
                continue
            if info.drehmaschine and gross in ("G98", "G99") and s.vorschub_minute_drehen == "G98":
                # An Fanuc- und Haas-Drehmaschinen heißt G98/G99 Vorschub je Minute/Umdrehung,
                # nicht Rückzug im Bohrzyklus – weglassen.
                continue
            woerter = [gross]
            for adresse in ADRESSEN:
                if adresse not in parameter:
                    continue
                wert = float(parameter[adresse])
                if adresse == "F":
                    wert *= 60.0
                    woerter.append(_wort(s, "F", _zahl(wert, STELLEN_G93 if g93 else STELLEN)))
                    continue
                if adresse == "X" and info.drehmaschine and info.x_durchmesser:
                    wert *= 2.0
                woerter.append(_wort(s, _adresse(s, adresse, info), _zahl(wert)))
            zeilen.append(" ".join(woerter))
            if gross in ("G0", "G00", "G1", "G01", "G2", "G02", "G3", "G03"):
                saetze += 1
                if vorschau is not None and saetze >= vorschau:
                    zeilen.append(_kommentar(s, tr("pp.vorschau_ende")))
                    return Programm(zeilen, hinweise, saetze)
        if kuehlung:
            zeilen.append(s.kuehlung_aus)
    if spindel_an is not None:
        zeilen.extend(_spindel_aus(s, spindel_an))
    if werkzeug is not None:
        zeilen.extend(_zum_wechselpunkt(s, info))
    if c_an and s.c_aus:
        zeilen.extend(_zeilen(_fuellen(s.c_aus, h=_haupt(info))))
    zeilen.extend(_zeilen(s.ende))
    return Programm(zeilen, hinweise, saetze)


def _zum_wechselpunkt(s, info):
    """Die Sätze zum Wechselpunkt: zuerst die Achse, die das Werkzeug wegzieht (an der
    Drehmaschine X, sonst Z), dann die anderen – leer ohne Wechselpunkt oder Befehl."""
    if not info.wechselpunkt:
        return []
    vorlage = s.wechselpunkt_wks if info.wechsel_wks else s.wechselpunkt_mks
    if not vorlage:
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
    zeilen.append(_kommentar(s, satz))


# --- Aus FreeCAD ---------------------------------------------------------------------------


def abschnitte(job):
    """[Abschnitt] – die aktiven Operationen des Jobs mit Bahn, in ihrer Reihenfolge."""
    ergebnis = []
    for op in getattr(getattr(job, "Operations", None), "Group", []):
        if not getattr(op, "Active", True) or getattr(op, "Path", None) is None:
            continue
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
