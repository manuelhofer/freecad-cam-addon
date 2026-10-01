# SPDX-License-Identifier: LGPL-2.1-or-later
"""Zahlen des Addons: Maßsystem, Dezimalzeichen, Lesen von Eingaben (Stufe B des Plans).

Maßsystem (mm oder inch) und Dezimalzeichen wählt man beim ersten Start und
in den Einstellungen des Addons (Manuel: „bei der Installation auswählbar …
mit Beispielzahlen … und in den Einstellungen wieder ändern“); bis dahin
gilt, was FreeCAD eingestellt hat – sein Einheitensystem und sein
Zahlenformat. Eingaben nehmen immer Punkt und Komma – wer „12.5“ tippt,
meint 12,5, egal was eingestellt ist. Tausendertrennzeichen gibt es nicht
(B-004).

Gespeichert und gerechnet wird immer metrisch; umgerechnet wird nur beim
Zeigen und Lesen, verlustfrei: 1 in = 25,4 mm, und ein halber Zoll bleibt
0,5 in. Läuft ohne Oberfläche; das Zahlenformat für Qt baut gui_zahlen.
"""

import math
import re

import FreeCAD

from . import PARAMETER_PFAD

KOMMA, PUNKT = ",", "."
DEZIMALZEICHEN = (KOMMA, PUNKT)
METRISCH, ZOLL = "metrisch", "zoll"
MASSSYSTEME = (METRISCH, ZOLL)

# Größen, die das Addon zeigt: je (metrische Einheit, Zoll-Einheit, metrischer
# Wert je Zoll-Einheit, Nachkommastellen in Zoll).
LAENGE = "laenge"  # Durchmesser, Längen, ae, ap
SPAN = "span"  # fz, f, Spandicke – feiner
SCHNITT = "schnitt"  # vc
VORSCHUB = "vorschub"  # vf, Eilgang
ABTRAG = "abtrag"  # Q
VOLUMEN = "volumen"
WEG_JE_VOLUMEN = "weg_je_volumen"  # Schneidenweg je Volumen: m je cm³, ft je in³
GROESSEN = {
    LAENGE: ("mm", "in", 25.4, 4),
    SPAN: ("mm", "in", 25.4, 5),
    SCHNITT: ("m/min", "SFM", 0.3048, 0),
    VORSCHUB: ("mm/min", "ipm", 25.4, 1),
    ABTRAG: ("cm³/min", "in³/min", 16.387064, 2),
    VOLUMEN: ("cm³", "in³", 16.387064, 2),
    WEG_JE_VOLUMEN: ("m", "ft", 0.3048 / 16.387064, 2),
}
# „Zeit für 100 cm³“ macht Q greifbar – in inch 5 in³ statt krummer 6,1 in³.
VERGLEICHSVOLUMEN = {METRISCH: 100, ZOLL: 5}
# Vor einer Stellung im Durchmesser (X einer Drehmaschine): „Ø 550,00 mm“.
DURCHMESSER = "Ø "

_DEZIMALZEICHEN = "Dezimalzeichen"  # Schlüssel in den Einstellungen
_MASSSYSTEM = "Masssystem"
# Eine Zahl, wie sie in einem Feld stehen darf: Ziffern, höchstens ein
# Dezimalzeichen (Punkt oder Komma), vorn ein Minus.
_ZAHL = re.compile(r"-?(\d+([.,]\d*)?|[.,]\d+)")


def _parameter():
    return FreeCAD.ParamGet(PARAMETER_PFAD)


def gewaehltes_dezimalzeichen():
    """Das gewählte Dezimalzeichen („,“ oder „.“), oder None – dann gilt FreeCADs Zahlenformat."""
    zeichen = _parameter().GetString(_DEZIMALZEICHEN, "")
    return zeichen if zeichen in DEZIMALZEICHEN else None


def setze_dezimalzeichen(zeichen):
    """Merkt das Dezimalzeichen; alles andere als „,“ oder „.“ vergisst es."""
    if zeichen in DEZIMALZEICHEN:
        _parameter().SetString(_DEZIMALZEICHEN, zeichen)
    else:
        _parameter().RemString(_DEZIMALZEICHEN)


def gewaehltes_masssystem():
    """METRISCH oder ZOLL, wenn gewählt – sonst None, dann gilt FreeCADs Einheitensystem."""
    wahl = _parameter().GetString(_MASSSYSTEM, "")
    return wahl if wahl in MASSSYSTEME else None


def setze_masssystem(wahl):
    """Merkt das Maßsystem; alles andere als METRISCH oder ZOLL vergisst es."""
    if wahl in MASSSYSTEME:
        _parameter().SetString(_MASSSYSTEM, wahl)
    else:
        _parameter().RemString(_MASSSYSTEM)


def freecad_masssystem():
    """Das Maßsystem von FreeCADs Einheitensystem: Zoll bei allen „Imperial“-Systemen."""
    try:
        name = FreeCAD.Units.listSchemas()[FreeCAD.Units.getSchema()]
    except (AttributeError, IndexError, TypeError):
        return METRISCH
    return ZOLL if "imperial" in name.lower() else METRISCH


def masssystem():
    """Das Maßsystem, in dem das Addon zeigt: gewählt, sonst das von FreeCAD."""
    return gewaehltes_masssystem() or freecad_masssystem()


def in_zoll():
    return masssystem() == ZOLL


def einheit(groesse):
    """Die Einheit der Größe im gezeigten Maßsystem: „mm“ oder „in“, „m/min“ oder „SFM“ …"""
    metrisch, zoll, _faktor, _stellen = GROESSEN[groesse]
    return zoll if in_zoll() else metrisch


def anzeige(wert, groesse):
    """Ein metrischer Wert im gezeigten Maßsystem (umgerechnet, nicht gerundet)."""
    return wert / GROESSEN[groesse][2] if in_zoll() else wert


def metrisch(wert, groesse):
    """Ein Wert im gezeigten Maßsystem zurück ins Metrische – so wird gespeichert."""
    return wert * GROESSEN[groesse][2] if in_zoll() else wert


def stellen(groesse, metrisch_stellen):
    """Nachkommastellen für eine Größe: metrisch wie angegeben, in Zoll die der Größe."""
    return GROESSEN[groesse][3] if in_zoll() else metrisch_stellen


def gerundet(wert, groesse):
    """Ein metrischer Wert zum Zeigen in einem Feld: umgerechnet, in Zoll auf die Stellen
    der Größe gerundet – 12,7 mm zeigt 0,5 in, nicht 0,49999999."""
    wert = anzeige(wert, groesse)
    return round(wert, GROESSEN[groesse][3]) if in_zoll() else wert


def text(wert, groesse, metrisch_stellen=2):
    """Ein metrischer Wert für einen Satz: im gezeigten Maßsystem gerundet, mit dem gewählten
    Dezimalzeichen und ohne Nullen am Ende – „Ø 8,5“ statt „Ø 8.50“."""
    from .werkstoffe import mit_dezimalzeichen

    anzahl = stellen(groesse, metrisch_stellen)
    zahl = f"{round(anzeige(wert, groesse), anzahl) + 0.0:.{anzahl}f}"
    if "." in zahl:
        zahl = zahl.rstrip("0").rstrip(".")
    return mit_dezimalzeichen(zahl, gewaehltes_dezimalzeichen() or PUNKT)


def runden(wert, groesse, metrisch_stellen):
    """Rundet einen metrischen Wert so, wie er gezeigt wird – metrisch auf
    `metrisch_stellen`, in Zoll auf die Stellen der Größe – und gibt ihn
    metrisch zurück. So steht in inch 0,375 da, nicht 0,3748."""
    return metrisch(round(anzeige(wert, groesse), stellen(groesse, metrisch_stellen)), groesse)


def abrunden(wert, groesse, metrisch_stellen):
    """Wie runden(), aber ab – für Werte, die unter einer Grenze bleiben müssen."""
    anzahl = stellen(groesse, metrisch_stellen)
    schritt = 10.0**-anzahl
    gezeigt = math.floor(anzeige(wert, groesse) / schritt + 1e-9) * schritt
    return metrisch(round(gezeigt, anzahl), groesse)


def vergleichsvolumen():
    """Das Volumen für „Zeit für …“ in cm³: 100 cm³, in inch 5 in³."""
    return metrisch(VERGLEICHSVOLUMEN[masssystem()], VOLUMEN)


def platzhalter():
    """Was tr() selbst einsetzt: die Einheiten {e_laenge}, {e_span}, {e_schnitt} … und
    {vergleichsvolumen} („100“ bzw. „5“)."""
    werte = {"e_" + groesse: einheit(groesse) for groesse in GROESSEN}
    werte["vergleichsvolumen"] = VERGLEICHSVOLUMEN[masssystem()]
    return werte


def zahl_aus_text(text, dezimalzeichen=PUNKT):
    """Liest eine Eingabe mit Punkt oder Komma („12,5“ wie „12.5“); leer ist 0 (unbekannt).

    `dezimalzeichen` ist das eingestellte – es trennt immer die
    Nachkommastellen. Das andere Zeichen auch, außer die Zahl ist mit
    Tausendertrennzeichen geschrieben: „35.000“ ist bei eingestelltem Komma
    35000 (so meint es, wer so tippt – B-004), „1,500“ bei Punkt 1500. „12.5“
    und „0.125“ bleiben Dezimalzahlen. Wirft ValueError, wenn der Text keine
    Zahl ist.
    """
    text = text.strip()
    if not text:
        return 0.0
    anderes = PUNKT if dezimalzeichen == KOMMA else KOMMA
    if re.fullmatch(rf"-?[1-9]\d{{0,2}}(\{anderes}\d{{3}})+", text):
        text = text.replace(anderes, "")
    if not _ZAHL.fullmatch(text):
        raise ValueError(f"keine Zahl: {text!r}")
    return float(text.replace(",", "."))
