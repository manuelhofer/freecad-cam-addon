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
import math
import re
from dataclasses import dataclass, field

from . import messstopp as ms
from . import schwenken as sw
from . import simultan as si
from . import simultan_operation as so
from .sprache import tr

STELLEN = 3  # Nachkommastellen der Koordinaten und des Vorschubs je Minute
STELLEN_G93 = 5  # in G93 ist F 1 ÷ Zeit – oft kleiner als 1
SATZNUMMER_SCHRITT = 10  # N10, N20 …
MARKE_LAENGE = 32  # Zeichen einer Sprungmarke höchstens (Siemens)
TOLERANZ_BEREICH = (0.001, 1.0)  # mm – die Toleranz fürs Glätten
BEWEGUNG = ("G0", "G00", "G1", "G01", "G2", "G02", "G3", "G03")
BOGEN = ("G2", "G02", "G3", "G03")
# Die Achse quer zur Ebene des Bogens: ihr Mittelpunktsmaß (FreeCAD schreibt „K0“ in G17) lehnen
# Mach3 und LinuxCNC ab („K word given for arc in XY plane“) – bei 0 entfällt es.
QUER_ZUR_EBENE = {"G17": "K", "G18": "J", "G19": "I"}
_EBENE = re.compile(r"\bG1([789])\b")
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
    (Drehrichtung), {n} Nummer des Antriebs, {h} Nummer der Hauptspindel, {name} Programmname,
    {werkzeug} der Name des Werkzeugs (im Wechsel – Siemens mit Werkzeugverwaltung: T="{werkzeug}").
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
    # Der Programmanfang an der Drehmaschine statt `kopf` – leer: `kopf` auch dort. An Fanuc
    # (G-Code-System A) und Haas ist G90 an der Drehmaschine kein „absolut“, sondern der
    # Längsdrehzyklus (absolut/inkremental sagen X/U und Z/W), G49 gibt es dort nicht.
    kopf_drehmaschine: str = ""
    # Kennt die Steuerung an der Drehmaschine G90/G91 als absolut/inkrementell? Nein an Fanuc
    # und Haas: G90 aus einer Bahn (FreeCADs Bohren) entfällt dort, G91 bleibt mit Hinweis
    # (die Steuerung hält mit Alarm an, statt inkrementell falsch zu fahren).
    g90_drehen: bool = True
    # Wie X an der Drehmaschine zu lesen ist – passend zu „X im Durchmesser“ der Maschine in den
    # Kopf geschrieben, damit die Steuerung es so liest, wie das Programm es schreibt (LinuxCNC
    # G7/G8, Siemens DIAMON/DIAMOF). Leer: ein Parameter der Maschine (Fanuc, Haas).
    durchmesser_ein: str = ""
    radius_ein: str = ""
    kuehlung_flut: str = "M8"
    kuehlung_nebel: str = "M7"
    kuehlung_aus: str = "M9"
    # Beim Messstopp (W-010, W-023): die Tür auf vor dem Halt (M0) und zu nach dem Start – je
    # Steuerung und Maschine ihre eigenen Befehle (Manuel, 2026-10-17: „es geht um alle maschinen,
    # es muss variabel bleiben“); leer: nichts, der Bediener öffnet von Hand.
    tuer_auf: str = ""
    tuer_zu: str = ""
    # … und eine Meldung für den Bediener vor dem Halt ({text}: „Messstopp: messen, dann
    # NC-Start“), nach dem Start wieder weg – Siemens MSG, LinuxCNC „(MSG, …)“; leer: keine.
    meldung: str = ""
    meldung_aus: str = ""
    # Zum Wechselpunkt der Maschine – {achsen}: „X200.000 Z300.000“; in MKS bzw. WKS.
    wechselpunkt_mks: str = "G53 G0 {achsen}"
    wechselpunkt_wks: str = "G0 {achsen}"
    # Die Werkzeuglänge nach dem Wechsel an der Fräse ({t}: Werkzeugnummer) – im ersten Satz
    # danach, der Z fährt („G0 G43 H1 Z15.000“): Allein stünde sie am Wechselpunkt oben, und
    # manche Steuerung führe dort um die Länge hinauf. Leer: die Steuerung nimmt sie mit dem
    # Wechsel (Siemens: D1). Ohne sie stünde die Spitze um die ganze Werkzeuglänge tiefer als
    # programmiert (bis P-2026-10-04-51 fehlte sie – der Kopf hebt sie mit G49 sogar auf).
    laenge_ein: str = ""
    # … an der Drehmaschine, im ersten Fahrsatz nach dem Wechsel: LinuxCNC nimmt die Korrektur
    # (X und Z) auch dort erst mit G43; Fanuc, Haas und Mach mit T0101, Siemens mit T1 D1.
    laenge_ein_drehen: str = ""
    # … und wieder nach dem Wechselpunkt, wenn kein Wechsel folgt (Messstopp, eine andere Ebene
    # ohne Zyklus): Siemens fährt ihn mit „SUPA D0“ – D0 schaltet die Korrektur ab, danach
    # fräste das Programm ohne Länge weiter. Leer: der Weg dorthin lässt sie stehen (G53).
    laenge_wieder: str = ""
    # Die Sprungmarke vor jeder Bearbeitung (D-4) – {marke}: ihr Name („RAEUMEN_T1“), {n}: ihre
    # Nummer (1, 2 …). Leer: nur der Kommentar (die Steuerung kennt keine Marken).
    marke: str = ""
    gleich_bei_nummer: bool = False  # Siemens: Adresse mit Nummer schreibt „C4=…“
    nur_buchstabe: bool = True  # die Rundachse nur mit ihrem Buchstaben (C statt C4)
    # Befehle, die ein Maschinenhersteller festlegt – im Fenster gelb, im Programm ein Hinweis.
    vom_hersteller: tuple = ()
    glaetten_angebot: tuple = ()  # [Glaetten] – was die Steuerung dafür hat
    wechselpunkt_vorschlaege: tuple = ()  # Befehle zur Wahl für „Zum Wechselpunkt (MKS)“
    # Die Haken (Manuel, 2026-10-03: „die Optionen im Postprozessor besser beschreiben,
    # darstellen, mit Haken machen“; Spezifikation Steuerung, Abschnitte 7 und 8).
    kommentare: bool = True  # Operation und Werkzeug als Kommentar
    # Kommentare nur in ASCII (ä → ae, Ø → D, – → -): Fanuc, Haas und Mach lesen Programme im
    # ASCII-Zeichensatz und brechen bei anderen Zeichen mit „Illegal character“ ab.
    nur_ascii: bool = True
    # Kommentare in Großbuchstaben: ältere Fanuc-Steuerungen nehmen in Kommentaren keine kleinen
    # (Fanuc, Mazak vorbelegt an).
    grossbuchstaben: bool = False
    satznummern: bool = False  # N10, N20 … vor jedem Satz
    # Die Wörter mit Leerzeichen trennen („G1 X10.000“); aus: „G1X10.000“ – die Datei rund 10 %
    # kleiner (kleiner Programmspeicher, DNC). Nur, wo jedes Wort ein Buchstabe mit Zahl ist
    # (`ohne_leerzeichen_moeglich`) – an der Siemens hieße „SUPA D0“ sonst „SUPAD0“.
    leerzeichen: bool = True
    ohne_leerzeichen_moeglich: bool = False
    # Die höchste Satznummer – Fanuc, Haas, Mazak: fünf Stellen (eine sechste ist ein Alarm);
    # darüber geht es wieder bei N10 los (Satznummern dürfen sich wiederholen, Marken nicht).
    satznummer_max: int = 99999
    # Die Programmnummer im Kopf ({nummer}, je Job im Fenster): Fanuc „O1234“ – bis zu dieser
    # Nummer; 0: die Steuerung hat keine (der Name steht in der Datei).
    programmnummer_max: int = 0
    # Die größte Zahl, die die Steuerung liest – Fanuc und Mazak: acht Ziffern (±99999.999, sonst
    # Alarm „zu viele Ziffern“). Eine Rundachse, die fortlaufend zählt, kommt im langen Rundum-
    # Schlichten darüber; 0: ohne Grenze.
    zahl_max: float = 0.0
    kuehlung: bool = True  # M8/M7 und M9 wie an der Operation
    wechselpunkt: bool = True  # vor jedem Werkzeugwechsel und am Ende zum Wechselpunkt
    # Je Bearbeitung eine Sprungmarke und danach ein vollständiger Einstieg – Wechselpunkt,
    # Werkzeug, Spindel, Kühlung, Ebene –, so dass man sie direkt anspringen kann (D-4, Manuel
    # 2026-10-04: „Ja, jede Marke vollständig“); im Kopf die Marken und die Werkzeuge.
    marken: bool = True
    # Nach dem Einschalten der Spindel warten, bis sie ihre Drehzahl hat – die Hochlaufzeit der
    # Spindel an der Maschine ({sek}: Sekunden, immer mit Dezimalpunkt; Fanuc und Mazak zählen X
    # ohne Punkt in Tausendstel). An bei Steuerungen, die selbst nicht warten (GRBL, LinuxCNC,
    # Mach); Siemens, Fanuc, Haas, Heidenhain, Mazak warten meist von sich aus.
    verweilen: str = "G4 P{sek}"
    hochlauf_warten: bool = False
    # Das nächste Werkzeug gleich nach dem Wechsel vorwählen ({t}, {werkzeug}): Das Magazin holt es
    # heran, während das jetzige fräst – „T2“ nach „T1 M6“, Heidenhain „TOOL DEF 2“. Leer oder
    # Haken aus: keine Vorwahl; an der Drehmaschine nie (T dreht dort den Revolver).
    vorwahl: str = ""
    werkzeug_vorwahl: bool = True
    # Eigene Befehle vor und nach dem Werkzeugwechsel ({t}, {werkzeug}) – etwa ein wahlweiser Halt
    # (M1) davor, an GRBL das Antasten mit der Tastplatte danach (G38.2 …, G10 L20 …). Leer: nichts.
    vor_wechsel: str = ""
    nach_wechsel: str = ""
    # Der Nullpunkt, den der Job nennt (CAM: Fixtures, „G54“) – am Anfang und hinter jeder Marke,
    # vor dem Wechselpunkt und dem Schwenken. Die ersten `nullpunkt_grund` mit `nullpunkt`, die
    # übrigen mit `nullpunkt_weitere`: {g} G54 … G59, {nr} die Nummer (G54 = 1, G59.1 und
    # G54.1 P1 = 7), {e} die Nummer nach G59 (G59.1 = 1), {nn} zweistellig (Siemens G505). Haken
    # aus (vorbelegt): das Programm nimmt den Nullpunkt, der an der Maschine aktiv ist.
    nullpunkt: str = "{g}"
    nullpunkt_weitere: str = ""
    nullpunkt_grund: int = 6
    nullpunkt_setzen: bool = False
    # Hinter jeder Marke ein vollständiger Einstieg (Werkzeug neu) – nein bei GRBL: Dort ist der
    # Wechsel ein Halt (M0); die Marken stehen als Namen im Kommentar zum Suchen.
    einstieg_je_marke: bool = True
    # Im Kopf die Werkzeugliste: je Werkzeug Name, Ø, Auskragung, Länge ab Spindelnase, Halter und
    # seine Bearbeitungen (Manuel, 2026-10-25) – mit `kommentare`.
    werkzeugliste: bool = True
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
    # Fanuc G68.2: vor dem Wechselpunkt (G53), dem Nullpunkt und einer neuen Ebene erst zurück
    # (G69) – und G53.1 fährt nicht frei, G69 die Rundachsen nicht zurück: dazwischen hoch und die
    # Rundachsen auf 0.
    schwenken_aus_zuerst: bool = False
    # Dreht `schwenken_aus` die Rundachsen selbst zurück (Heidenhain PLANE RESET TURN)? Nein bei
    # Siemens: CYCLE800() löscht nur die Schwenkframes – geht es ohne Ebene weiter, fährt das
    # Programm erst zum Wechselpunkt, dann die Rundachsen auf 0.
    schwenken_aus_dreht: bool = False
    # 5 Achsen simultan mit TCPM (Manuel, 2026-10-03: „TCPM bleibt aus … später als Haken“): die
    # Steuerung führt die Spitze – im Programm die Spitze im Werkstück und die Rundachsen je
    # Punkt, F in mm/min statt G93 ({t}: Werkzeugnummer). Aus oder leer: ohne TCPM, die
    # Rundachsen und X, Y, Z der Maschine gerechnet, in G93 (simultan.befehle_auf_maschine).
    tcpm: bool = False
    tcpm_ein: str = ""
    tcpm_aus: str = ""
    # TCPM bei Rundachsen auf 0 einschalten und erst danach auf die Stellung drehen (Haas G234:
    # „The rotary axes must be at 0 before commanding G234“).
    tcpm_bei_null: bool = False
    # Bohrzyklen (Spezifikation Steuerung, E8): FreeCADs G81, G82, G83, G73 und G85 als Befehl
    # der Steuerung – je Bohrung über dem Loch („G0 X… Y…“), dann der Befehl mit {rtp}
    # Rückzugsebene (G98: die Höhe davor, G99: R), {rfp} Bezugsebene (R), {dp} Tiefe (Z),
    # {fdep} erste Tiefe (R − Q), {q} Zustellung, {dtb} Verweilen (P, s), {f} Vorschub (mm/min).
    # Leer: der Zyklus bleibt als G-Code. Ist einer gesetzt, entfallen G80, G98 und G99.
    bohren: str = ""
    bohren_verweilen: str = ""
    tiefbohren: str = ""
    spaenebrechen: str = ""
    reiben: str = ""
    # Gewindebohren (G84 rechts, G74 links; FreeCADs Gewinde schreibt in F die Steigung, in S die
    # Drehzahl): {pit} die Steigung mit Vorzeichen (+ rechts, − links), {s} die Drehzahl, {sdac}
    # die Drehrichtung danach (3 rechts, 4 links – die Spindel läuft weiter wie vorher), dazu
    # die Platzhalter der Bohrzyklen. Leer: G84/G74 bleiben, F ist dann Steigung · Drehzahl.
    gewinde: str = ""
    # Vor dem ersten G84/G74 einer Folge ({s}: die Drehzahl) – Fanuc „M29 S…“: Gewindebohren ohne
    # Ausgleichsfutter. Leer: nichts.
    gewinde_vorher: str = ""
    # Ohne `gewinde`: so heißen Gewindebohren rechts und links im Programm (Mazak G84.2/G84.3:
    # synchron), und ob F dort die Steigung ist (Mazak: „Feed rate (in pitch)“) statt des
    # Vorschubs Steigung · Drehzahl.
    gewinde_g: tuple = ("G84", "G74")
    gewinde_f_steigung: bool = False
    # Gewindebohren synchron – ohne Ausgleichsfutter (die Spindel führt Z; `gewinde`,
    # `gewinde_vorher`, `gewinde_g`, `gewinde_f_steigung`) – oder mit Ausgleichsfutter: dann
    # `gewinde_ausgleich` (leer: G84/G74 mit F = Steigung · Drehzahl), ohne `gewinde_vorher`.
    gewinde_synchron: bool = True
    gewinde_ausgleich: str = ""
    # Gilt `gewinde` auch an der Drehmaschine (längs Z, unabhängig von der Ebene)? Ja bei LinuxCNC
    # G33.1; sonst steht dort ein Hinweis (Siemens CYCLE84 und Fanuc G84 bohren in G18 nicht
    # längs Z).
    gewinde_drehen: bool = False
    # Eine endlos drehende Rundachse als Moduloachse (0 … unter 360°; Manuel, 2026-10-05, Siemens:
    # „Fehler 16830 … falsche Position bei Achse/Spindel C4 programmiert“): {wert} die Position
    # im Bereich, je nach Drehrichtung der Bahn (Siemens ACP/ACN). Leer: der Winkel fortlaufend,
    # wie ihn die Bahn zählt (−450°, eine Achse ohne Modulo). Nur für Rundachsen, die an der
    # Maschine endlos drehen (Maschineninfo.modulo).
    rundachse_plus: str = ""
    rundachse_minus: str = ""
    # Das Rohteil für die Simulation der Steuerung (Manuel, 2026-10-05: „WORKPIECE muss doch mit
    # rein!“) – aus dem Rohteil des Jobs: {z0} oben bzw. vorn, {z1} unten bzw. hinten, {zb} das
    # Bearbeitungsmaß (hier {z1}), {x0} {y0} {x1} {y1} die Ecken des Quaders, {d} der Ø der
    # Stange. Leer oder Haken aus: keins (Heidenhain schreibt sein BLK FORM selbst).
    rohteil_fraesen: str = ""
    rohteil_drehen: str = ""
    rohteil: bool = True
    # „gcode“ oder „klartext“ (Heidenhain): Klartext schreibt der Postprozessor erst als G-Code und
    # übersetzt ihn am Schluss (klartext.uebersetzen) – ohne G93, Satznummern ab 0 immer.
    dialekt: str = "gcode"
    # Heidenhain: die Bohrzyklen als Zyklen der TNC (200, 201, 203, Gewinde 207) – aus: G81 ff. in
    # L-Sätzen ausgeschrieben, wie bis P-2026-10-25-65 (Gewinde gibt es nur als Zyklus).
    bohrzyklen: bool = True
    # Eine Steuerung ohne Bohrzyklen (GRBL): G81, G82, G83, G73, G85 in G0/G1/G4 ausgeschrieben,
    # G80/G98/G99 entfallen, Gewindebohren geht nicht (Hinweis).
    zyklen_ausschreiben: bool = False
    # Fährt die Steuerung Rundachsen? Nein (GRBL: X, Y, Z): ein Hinweis, wenn eine im Programm steht.
    rundachsen: bool = True

    def ersetzt(self, **werte):
        """Eine Kopie mit geänderten Befehlen."""
        return dataclasses.replace(self, **werte)

    def gewinde_waehlbar(self):
        """Schreibt die Steuerung synchrones Gewindebohren anders als mit Ausgleichsfutter? Sonst
        braucht es den Haken nicht (Haas: G84 ist immer synchron)."""
        return self.dialekt == "klartext" or bool(
            self.gewinde != self.gewinde_ausgleich
            or self.gewinde_vorher
            or tuple(self.gewinde_g) != GEWINDE
            or self.gewinde_f_steigung
        )

    def wirksam(self):
        """Die Befehle, wie sie gelten: ohne „Gewindebohren synchron“ die mit Ausgleichsfutter."""
        if self.gewinde_synchron or self.dialekt == "klartext":
            return self
        return self.ersetzt(
            gewinde=self.gewinde_ausgleich,
            gewinde_vorher="",
            gewinde_g=GEWINDE,
            gewinde_f_steigung=False,
        )

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
    "kopf_drehmaschine",
    "kopf_drehen",
    "rohteil_fraesen",
    "rohteil_drehen",
    "durchmesser_ein",
    "radius_ein",
    "ende",
    "nullpunkt",
    "nullpunkt_weitere",
    "vor_wechsel",
    "wechsel_fraesen",
    "vorwahl",
    "nach_wechsel",
    "laenge_ein",
    "wechsel_drehen",
    "laenge_ein_drehen",
    "wechselpunkt_mks",
    "laenge_wieder",
    "wechselpunkt_wks",
    "marke",
    "spindel_ein",
    "spindel_aus",
    "verweilen",
    "angetrieben_ein",
    "angetrieben_aus",
    "c_ein",
    "c_aus",
    "rundachse_plus",
    "rundachse_minus",
    "vorschub_zeit",
    "vorschub_minute",
    "vorschub_minute_drehen",
    "kuehlung_flut",
    "kuehlung_nebel",
    "kuehlung_aus",
    "tuer_auf",
    "tuer_zu",
    "meldung",
    "meldung_aus",
    "schwenken",
    "schwenken_aus",
    "tcpm_ein",
    "tcpm_aus",
    "bohren",
    "bohren_verweilen",
    "tiefbohren",
    "spaenebrechen",
    "reiben",
    "gewinde",
    "gewinde_vorher",
    "gewinde_ausgleich",
)

# Welcher Befehl der Steuerung für welchen Bohrzyklus steht.
ZYKLUS_FELDER = {
    "G81": "bohren",
    "G82": "bohren_verweilen",
    "G83": "tiefbohren",
    "G73": "spaenebrechen",
    "G85": "reiben",
    "G84": "gewinde",
    "G74": "gewinde",
}
GEWINDE = ("G84", "G74")  # Gewindebohren rechts, links
AUSGESCHRIEBEN = ("G81", "G82", "G83", "G73", "G85")  # was zyklen_ausschreiben in G0/G1 schreibt

# Die Haken – (Name, Typ) wie in Steuerung; im Fenster je eine Zeile mit Erklärung.
HAKEN = (
    "kommentare",
    "nur_ascii",
    "grossbuchstaben",
    "satznummern",
    "leerzeichen",
    "rohteil",
    "kuehlung",
    "wechselpunkt",
    "marken",
    "werkzeugliste",
    "werkzeug_vorwahl",
    "nullpunkt_setzen",
    "hochlauf_warten",
    "c_achse",
    "g93",
    "schwenkzyklus",
    "tcpm",
    "bohrzyklen",
    "gewinde_synchron",
)

# G94 im Kopf: Stand vom Programm davor G95 (Vorschub je Umdrehung), hieße F187 sonst 187 mm je
# Umdrehung – Fanuc behält den Zustand nach dem Reset.
_KOPF_FRAESEN = "%\n{kommentar_name}\nG17 G21 G40 G49 G80 G90 G94"
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
        hochlauf_warten=True,  # LinuxCNC wartet nicht von selbst (ohne „spindle at speed“)
        ohne_leerzeichen_moeglich=True,
        vorwahl="T{t}",  # das nächste Werkzeug vorbereiten (T ohne M6)
        nullpunkt_weitere="G59.{e}",  # G59.1 … G59.3 (LinuxCNC: neun Nullpunkte)
        meldung="(MSG, {text})",  # LinuxCNC zeigt „(MSG, …)“ in der Oberfläche
        glaetten_angebot=(Glaetten("g64", "G64 P{toleranz} Q{toleranz}", True),),
        wechselpunkt_vorschlaege=_MKS,
        laenge_ein="G43 H{t}",
        laenge_ein_drehen="G43 H{t}",
        durchmesser_ein="G7",
        radius_ein="G8",
        # Synchron mit G33.1 (spindelsynchron hinein und zurück, K die Steigung – braucht einen
        # Drehgeber); vorbelegt aus: G84 mit F = Steigung · Drehzahl (ohne Gleichlauf, für ein
        # Ausgleichsfutter; LinuxCNC-Handbuch: „G84 does not use synchronized motion“).
        gewinde="G0 Z{rfp}\nG33.1 Z{dp} K{pit_abs}\nG0 Z{rtp}",
        gewinde_synchron=False,
        gewinde_drehen=True,
    ),
    "siemens": Steuerung(
        "siemens",
        "Siemens 840D",
        ".mpf",
        "; ",
        "{kommentar_name}\nG17 G71 G90 G40 G94",
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
        verweilen="G4 F{sek}",  # Siemens: G4 F – Sekunden (G4 S: Umdrehungen)
        meldung='MSG("{text}")',  # in der Meldezeile, bis MSG() sie löscht
        meldung_aus="MSG()",
        satznummer_max=99999999,
        vorwahl="T{t}",  # vorwählen; „T{t} M6“ wechselt (mit Werkzeugverwaltung: T="{werkzeug}")
        # Einstellbare Nullpunkte G54 … G57, ab dem fünften G505 … G599 – G58 und G59 sind an der
        # 840D axiale Verschiebungen (Grundlagen, „Einstellbare Nullpunktverschiebung“).
        nullpunkt_grund=4,
        nullpunkt_weitere="G5{nn}",
        # SUPA: Maschinenkoordinaten ohne Verschiebungen; D0 ohne Werkzeugkorrektur – der
        # Wechselpunkt gilt für den Werkzeugträger.
        wechselpunkt_mks="G0 SUPA D0 {achsen}",
        laenge_wieder="D1",  # nach „SUPA D0“ ohne Wechsel: die Schneide wieder an
        # Moduloachse (Alarm 16830 sonst): absolut im Bereich, positiv bzw. negativ drehend.
        rundachse_plus="ACP({wert})",
        rundachse_minus="ACN({wert})",
        # Rohteil (SINUMERIK Operate, „Rohteil definieren“): Typ, dann ein Bit-Wert – Bit 4/5:
        # X/Y absolut, Bit 6: Länge Z absolut, Bit 7: Bearbeitungsmaß absolut (240 = alle,
        # 192 = Z und ZB) –, dann Z0, Z1, ZB und die Maße.
        rohteil_fraesen='WORKPIECE(,"",,"BOX",240,{z0},{z1},{zb},{x0},{y0},{x1},{y1})',
        rohteil_drehen='WORKPIECE(,,,"CYLINDER",192,{z0},{z1},{zb},{d})',
        nur_ascii=False,  # SINUMERIK Operate zeigt Umlaute
        durchmesser_ein="DIAMON",
        radius_ein="DIAMOF",
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
        schwenken='CYCLE800(1,"{tc}",0,27,{x0},{y0},{z0},{a},{b},{c},0,0,0,{dir},0,1)',
        # Sprungmarke: anspringen mit GOTOF/GOTOB (Name aus Buchstaben, Ziffern und „_“, die
        # ersten zwei Buchstaben, höchstens 32 Zeichen).
        marke="{marke}:",
        schwenken_aus="CYCLE800()",
        # TRAORI: Transformation mit Orientierung – X, Y, Z sind die Spitze im Werkstück, die
        # Rundachsen stehen je Satz; TRAFOOF schaltet sie ab (Grundlagen, „Fünfachs-Transformation“).
        tcpm_ein="TRAORI",
        tcpm_aus="TRAFOOF",
        # G81 ff. gibt es nur im ISO-Sprachmodus G291 (Grundlagen 03/2010, S. 535); nach dem
        # Handbuch (Arbeitsvorbereitung 10/2015, S. 651–663): CYCLE81(RTP, RFP, SDIS, DP),
        # CYCLE82(…, DPR, DTB), CYCLE83(…, DPR, FDEP, FDPR, _DAM, DTB, DTS, FRF, VARI) mit
        # Degression 0, FRF 1 und VARI 1 Entspanen (G83) bzw. 0 Spänebrechen (G73),
        # CYCLE85(…, DPR, DTB, FFR, RFF) heraus im Vorschub. SDIS 0: R enthält ihn schon.
        bohren="CYCLE81({rtp},{rfp},0,{dp})",
        bohren_verweilen="CYCLE82({rtp},{rfp},0,{dp},,{dtb})",
        tiefbohren="CYCLE83({rtp},{rfp},0,{dp},,{fdep},,0,0,0,1,1)",
        spaenebrechen="CYCLE83({rtp},{rfp},0,{dp},,{fdep},,0,0,0,1,0)",
        reiben="CYCLE85({rtp},{rfp},0,{dp},,0,{f},{f})",
        # Gewindebohren ohne Ausgleichsfutter (Kurzanleitung Programmierung 10.00, S. 6-65):
        # CYCLE84(RTP, RFP, SDIS, DP, DPR, DTB, SDAC, MPIT, PIT, POSS, SST, SST1) – die Steigung
        # als Wert (PIT, das Vorzeichen die Drehrichtung im Gewinde), SDAC wie vorher, SST und
        # SST1 die Drehzahl hinein und heraus.
        gewinde="CYCLE84({rtp},{rfp},0,{dp},,{dtb},{sdac},,{pit},0,{s},{s})",
        # Mit Ausgleichsfutter (S. 6-66): CYCLE840(RTP, RFP, SDIS, DP, DPR, DTB, SDR, SDAC, ENC,
        # MPIT, PIT) – SDR 0: die Drehrichtung kehrt sich selbst um, ENC 1: ohne Geber, mit dem F
        # davor (Steigung · Drehzahl).
        gewinde_ausgleich="CYCLE840({rtp},{rfp},0,{dp},,{dtb},0,{sdac},1,,{pit})",
    ),
    "fanuc": Steuerung(
        "fanuc",
        "Fanuc",
        ".nc",
        "(",
        "%\nO{nummer:04d} {kommentar_name}\nG17 G21 G40 G49 G80 G90 G94",
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
        verweilen="G4 X{sek}",  # X mit Punkt: Sekunden (P: Tausendstel)
        vorwahl="T{t}",  # Fanuc: T wählt vor, M6 wechselt
        programmnummer_max=9999,  # O0001 … O9999
        grossbuchstaben=True,
        ohne_leerzeichen_moeglich=True,
        zahl_max=99999.999,
        nullpunkt_weitere="G54.1 P{e}",  # zusätzliche Werkstückkoordinatensysteme P1 … P48
        marke="N{n}",  # die Satznummer der Bearbeitung – für die Satzsuche
        vom_hersteller=("angetrieben_ein", "angetrieben_aus", "c_ein", "c_aus"),
        # Vorausschau und AI-Konturregelung sind bei Fanuc Optionen – vorbelegt aus.
        glaetten_angebot=(
            Glaetten("g08", "G08 P1", False, True),
            Glaetten("g051", "G05.1 Q1", False, True),
        ),
        wechselpunkt_vorschlaege=_MKS,
        laenge_ein="G43 H{t}",
        # Gewindebohren ohne Ausgleichsfutter: M29 mit der Drehzahl vor G84/G74 (Fanuc „Rigid
        # Tapping“; ohne M29 hieße G84 mit Ausgleichsfutter).
        gewinde_vorher="M29 S{s}",
        # G43.4: Werkzeugspitzensteuerung Typ 1 (Rundachsen im Satz); G49 schaltet sie ab.
        tcpm_ein="G43.4 H{t}",
        tcpm_aus="G49",
        # 3+2 mit „Tilted Working Plane“ (eine Option): G68.2 mit dem Ursprung der Ebene und den
        # Eulerwinkeln Z, X', Z'' ({i} {j} {k}), G53.1 stellt das Werkzeug senkrecht darauf; G69
        # zurück. Vorbelegt aus – ohne die Option rechnet das Programm die Rundachsen selbst.
        schwenken="G68.2 X{x0} Y{y0} Z{z0} I{i} J{j} K{k}\nG53.1",
        schwenken_aus="G69",
        schwenkzyklus=False,
        schwenken_aus_zuerst=True,
        g90_drehen=False,
        # Drehmaschine: metrisch, ohne Schneidenradiuskorrektur und Zyklus, feste Drehzahl,
        # Vorschub je Minute – ohne G90 (Längsdrehzyklus) und G49.
        kopf_drehmaschine="%\nO{nummer:04d} {kommentar_name}\nG21 G40 G80 G97 G98",
    ),
    # Mazak EIA/ISO, G-Code-Reihe M (Programmierhandbuch MAZATROL MATRIX EIA/ISO, H740PB0030E):
    # wie Fanuc; Gewindebohren synchron als G84.2/G84.3 mit F = Steigung (14-5-21: „G84.2 [Xx Yy]
    # Rr Zz [Ptc] Ff0 … f0 : Feed rate (in pitch)“ – ohne die Option Alarm 952), Werkzeugspitze
    # mit G43.4 (Tabelle 3: „Tool tip point control (Type 1) ON G43.4“), die Bohrzyklen G73, G81–G85
    # mit denselben Adressen.
    "mazak": Steuerung(
        "mazak",
        "Mazak (EIA/ISO)",
        ".eia",
        "(",
        "%\nO{nummer:04d} {kommentar_name}\nG17 G21 G40 G49 G80 G90 G94",
        _ENDE,
        "G18",
        "T{t} M6",
        "T{t} M6",
        "M{m} S{s}",
        "M5",
        "M{m} S{s}",
        "M5",
        "",
        "",
        "G93",
        "G94",
        "G98",
        marke="N{n}",  # die Satznummer der Bearbeitung – für die Satzsuche
        vom_hersteller=("angetrieben_ein", "angetrieben_aus", "c_ein", "c_aus"),
        wechselpunkt_vorschlaege=_MKS,
        laenge_ein="G43 H{t}",
        tcpm_ein="G43.4 H{t}",
        tcpm_aus="G49",
        verweilen="G4 X{sek}",  # „G04 X5. … Dwell time = 5.0 sec“ (Handbuch 8-1)
        vorwahl="T{t}",
        nullpunkt_weitere="G54.1 P{e}",  # zusätzliche Werkstückkoordinatensysteme (wie Fanuc)
        programmnummer_max=9999,
        grossbuchstaben=True,
        ohne_leerzeichen_moeglich=True,
        zahl_max=99999.999,
        gewinde_g=("G84.2", "G84.3"),
        gewinde_f_steigung=True,
        # Mit Ausgleichsfutter: G84 (G74 links) asynchron – H0 („h0 = 0 … Asynchronous tapping“),
        # F der Vorschub. Ohne H entschiede Parameter F94.
        gewinde_ausgleich="{g} Z{dp} R{rfp} F{f} H0",
        g90_drehen=False,
        kopf_drehmaschine="%\nO{nummer:04d} {kommentar_name}\nG21 G40 G80 G97 G98",
    ),
    "haas": Steuerung(
        "haas",
        "Haas",
        ".nc",
        "(",
        "%\nO{nummer:05d} {kommentar_name}\nG17 G21 G40 G49 G80 G90 G94",
        _ENDE,
        "G18",
        "T{t} M6",
        "T{t}{t:02d}",
        "M{m} S{s}",
        "M5",
        "M13{m} P{s}",  # M133 vorwärts, M134 rückwärts, P die Drehzahl (haascnc.com, M133)
        "M135",
        "M154",
        "M155",
        "G93",
        "G94",
        "G98",
        marke="N{n}",  # die Satznummer der Bearbeitung – für die Satzsuche
        nullpunkt_weitere="G154 P{e}",  # Haas: G154 P1 … P99 (zusätzliche Werkstückoffsets)
        programmnummer_max=99999,  # O00001 … O99999
        ohne_leerzeichen_moeglich=True,
        # Ohne G187 gilt die Glättung aus Einstellung 191 der Maschine.
        glaetten_angebot=(Glaetten("g187", "G187 P3", False),),
        wechselpunkt_vorschlaege=_MKS,
        laenge_ein="G43 H{t}",
        # G234: Tool Center Point Control (TCPC); G49 schaltet sie ab.
        tcpm_ein="G234 H{t}",
        tcpm_aus="G49",
        tcpm_bei_null=True,
        g90_drehen=False,
        # Drehmaschine: metrisch, ohne Schneidenradiuskorrektur und Zyklus, feste Drehzahl,
        # Vorschub je Minute – ohne G90 (Längsdrehzyklus) und G49.
        kopf_drehmaschine="%\nO{nummer:05d} {kommentar_name}\nG21 G40 G80 G97 G98",
    ),
    # GRBL 1.1 (README „List of Supported G-Codes in Grbl v1.1“): kein M6, keine Bohrzyklen, kein
    # G98/G99, kein G43 H, kein G64, keine Rundachsen, M7 meist nicht einkompiliert. Der Wechsel
    # ist ein Halt (M0) – der Kommentar davor nennt das Werkzeug, danach Z neu antasten.
    "grbl": Steuerung(
        "grbl",
        "GRBL 1.1",
        ".nc",
        "(",
        # Ohne G49: GRBL kennt keine Länge je Werkzeug (nur G43.1) – Z wird je Werkzeug angetastet.
        "{kommentar_name}\nG17 G21 G40 G80 G90 G94",
        "M5\nM9\nM30",
        "G18",
        "M0",
        "M0",
        "M{m} S{s}",
        "M5",
        "M{m} S{s}",
        "M5",
        "",
        "",
        "G93",
        "G94",
        "G94",
        hochlauf_warten=True,  # GRBL wartet nie auf die Drehzahl
        ohne_leerzeichen_moeglich=True,
        kuehlung_nebel="M8",
        wechselpunkt_vorschlaege=_MKS,
        # Die Marken als Namen im Kommentar (suchen, ANFANG) – ohne vollständigen Einstieg, der hieße
        # je Bearbeitung ein Halt.
        einstieg_je_marke=False,
        zyklen_ausschreiben=True,
        rundachsen=False,
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
        hochlauf_warten=True,
        vorwahl="T{t}",
        nullpunkt_weitere="G59 P{nr}",  # Mach3/Mach4: ab dem siebten „G59 P7“
        ohne_leerzeichen_moeglich=True,
        glaetten_angebot=(Glaetten("g64", "G64", True),),
        wechselpunkt_vorschlaege=_MKS,
        laenge_ein="G43 H{t}",
    ),
}
# Heidenhain im Klartext (Manuel, 2026-10-05: „Heidenhain muss mit rein, aber gibt ja verschiedene,
# vor allem iTNC 530“): die Befehle, die der Postprozessor einsetzt, schon als Klartext; seine
# Bahn übersetzt klartext.uebersetzen. iTNC 530 schaltet TCPM mit M128/M129, die TNC 640, 620 und
# 320 mit FUNCTION TCPM. Zyklus 32 (Toleranz) zum Glätten; die Texte der Zyklen wie an einer
# deutschen Steuerung.
_HEIDENHAIN = {
    "endung": ".h",
    "kommentar": "; ",
    "kopf": "",
    "ende": "M5\nM9\nM30",
    "kopf_drehen": "",
    "wechsel_fraesen": "TOOL CALL {t} Z",
    "vorwahl": "TOOL DEF {t}",  # das nächste Werkzeug vorwählen
    # Bezugspunkt aus der Preset-Tabelle (Zyklus 247, Q339 die Zeile – G54 = 1); setzt Zyklus 7
    # zurück, PLANE bleibt: darum vor dem Schwenken.
    "nullpunkt": "CYCL DEF 247 BEZUGSPUNKT SETZEN ~\nQ339=+{nr} ;BEZUGSPUNKT-NUMMER",
    "nullpunkt_grund": 999,
    "wechsel_drehen": "TOOL CALL {t} Z",
    "spindel_ein": "M{m} S{s}",
    "spindel_aus": "M5",
    # An einer TNC mit Drehen treibt die Frässpindel das Werkzeug: M3/M4 mit der Drehzahl.
    "angetrieben_ein": "M{m} S{s}",
    "angetrieben_aus": "M5",
    "c_ein": "",
    "c_aus": "",
    "vorschub_zeit": "",
    "vorschub_minute": "",
    "vorschub_minute_drehen": "",
    "wechselpunkt_mks": "L {achsen} R0 FMAX M91",
    "wechselpunkt_wks": "L {achsen} R0 FMAX",
    "wechselpunkt_vorschlaege": ("L {achsen} R0 FMAX M91", "L {achsen} R0 FMAX M92"),
    "marke": "* - {marke}",
    "glaetten_angebot": (
        Glaetten("zyklus32", "CYCL DEF 32.0 TOLERANZ\nCYCL DEF 32.1 T{toleranz}", True),
    ),
    # 3+2 (Spezifikation Steuerung, „PLANE SPATIAL“): der Nullpunkt auf den Ursprung der Ebene
    # (Zyklus 7), dann die Raumwinkel – SPA um X, SPB um Y, SPC um Z, maschinenfest in dieser
    # Reihenfolge; das sind die Winkel von CYCLE800 achsweise Z, Y, X ({c} {b} {a}). TURN fährt
    # die Rundachsen, MB MAX zieht vorher ganz zurück; SEQ wie CYCLE800 _DIR. Die Vorzeichen setzt
    # klartext.uebersetzen.
    "schwenken": (
        "CYCL DEF 7.0 NULLPUNKT\nCYCL DEF 7.1 X{x0}\nCYCL DEF 7.2 Y{y0}\nCYCL DEF 7.3 Z{z0}\n"
        "PLANE SPATIAL SPA{c} SPB{b} SPC{a} TURN MB MAX FMAX SEQ{seq}"
    ),
    "schwenken_aus": (
        "PLANE RESET TURN MB MAX FMAX\nCYCL DEF 7.0 NULLPUNKT\nCYCL DEF 7.1 X0\n"
        "CYCL DEF 7.2 Y0\nCYCL DEF 7.3 Z0"
    ),
    "g93": False,
    "schwenken_aus_dreht": True,  # PLANE RESET TURN MB MAX: zieht zurück und dreht auf 0
    "dialekt": "klartext",
}

STEUERUNGEN["heidenhain"] = Steuerung(
    "heidenhain",
    "Heidenhain iTNC 530 (Klartext)",
    tcpm_ein="M128",
    tcpm_aus="M129",
    **_HEIDENHAIN,
)
STEUERUNGEN["heidenhain_tnc640"] = Steuerung(
    "heidenhain_tnc640",
    "Heidenhain TNC 640/620/320 (Klartext)",
    tcpm_ein="FUNCTION TCPM F TCP AXIS POS PATHCTRL AXIS",
    tcpm_aus="FUNCTION RESET TCPM",
    **_HEIDENHAIN,
)
# woodWOP (Homag, Weeke; Manuel, 2026-10-25: „mach das einfach“): kein G-Code, sondern MPR – der
# Postprozessor schreibt die Bahn wie sonst, mpr.uebersetzen macht Konturen und Bearbeitungen
# daraus. Wechselpunkt, Kühlung, Marken, Glätten und G93 gibt es dort nicht (woodWOP fährt selbst
# frei, die Maschine kennt ihre Werkzeuge).
_WOODWOP = {
    "endung": ".mpr",
    "kommentar": "(",
    "kopf": "",
    "ende": "",
    "kopf_drehen": "",
    "wechsel_fraesen": "T{t} M6",
    "wechsel_drehen": "T{t} M6",
    "spindel_ein": "M{m} S{s}",
    "spindel_aus": "M5",
    "angetrieben_ein": "",
    "angetrieben_aus": "",
    "c_ein": "",
    "c_aus": "",
    "vorschub_zeit": "",
    "vorschub_minute": "",
    "vorschub_minute_drehen": "",
    "g93": False,
    "kuehlung": False,
    "wechselpunkt": False,
    "marken": False,
    "rohteil": False,
    "schwenkzyklus": False,
    "nullpunkt": "",  # woodWOP kennt kein G54
    "dialekt": "mpr",
}
STEUERUNGEN["woodwop"] = Steuerung("woodwop", "Homag woodWOP (MPR)", **_WOODWOP)
STEUERUNGEN["woodwop_weeke"] = Steuerung("woodwop_weeke", "Weeke woodWOP (MPR)", **_WOODWOP)
VORGABE = "linuxcnc"  # ohne Wahl: wie LinuxCNC (Spezifikation Steuerung, Abschnitt 4)
# Am Job, gemerkt von „Programm schreiben“ (gui_programm), gelesen auch vom Einrichtblatt:
EIGENSCHAFT_STEUERUNG = "CamAddonSteuerung"  # die Kennung der Steuerung
EIGENSCHAFT_DATEI = "CamAddonProgrammdatei"  # wohin sein Programm zuletzt kam
EIGENSCHAFT_NUMMER = "CamAddonProgrammnummer"  # seine Programmnummer (Fanuc „O1234“)


def programm_des_jobs(job):
    """„W.nc · O1234 · Fanuc“ – das Programm, das „Programm schreiben“ für den Job zuletzt
    gespeichert hat (Datei, Programmnummer, wo die Steuerung eine hat, Steuerung); "" ohne."""
    import os

    datei = str(getattr(job, EIGENSCHAFT_DATEI, "") or "")
    if not datei:
        return ""
    teile = [os.path.basename(datei)]
    s = STEUERUNGEN.get(str(getattr(job, EIGENSCHAFT_STEUERUNG, "") or ""))
    if s is not None and s.programmnummer_max and "{nummer" in s.kopf:
        nummer = min(max(1, int(getattr(job, EIGENSCHAFT_NUMMER, 1) or 1)), s.programmnummer_max)
        teile.append(f"O{nummer:0{len(str(s.programmnummer_max))}d}")
    if s is not None:
        teile.append(s.name)
    return " · ".join(teile)


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
    schwenkdatensatz: str = ""  # Name des Schwenkdatensatzes (CYCLE800 _TC); leer: der einzige
    # U/min – die Höchstdrehzahl der Spindel, die das Werkzeug antreibt; 0: unbekannt. Darüber
    # schreibt das Programm sie und die Vorschübe im selben Maß kleiner (fz bleibt): Die
    # Steuerung begrenzte sonst nur S, und der Span je Zahn wüchse um das Verhältnis.
    drehzahl_max: float = 0.0
    # s – die Hochlaufzeit je Spindel („haupt“ oder die Nummer des Antriebs); fehlt: unbekannt.
    hochlauf: dict = field(default_factory=dict)
    # Die Linearachsen der Maschine („X“, „Z“ an einer Drehmaschine ohne Y); leer: unbekannt.
    linear: set = field(default_factory=set)
    # Die Rundachsen (Buchstaben), die an der Maschine endlos drehen – an der Steuerung eine
    # Moduloachse: Steuerung.rundachse_plus/_minus.
    modulo: set = field(default_factory=set)
    # Buchstabe → zählt die Steuerung die Rundachse nach DIN 66217 (Haken „dreht nach DIN 66217“
    # an ihrer Betriebsart)? Ohne Angabe ja (_c_umdrehen).
    nach_din: dict = field(default_factory=dict)
    # Die Rundachsen (Buchstaben), deren Stellung das Programm mit dem anderen Vorzeichen schreibt
    # (verfahren.im_programm_umgekehrt) – für Bahnen, die mit den Stellungen der Maschine rechnen:
    # 3+2 ohne Zyklus, 5 Achsen simultan (_rund_umdrehen).
    umgekehrt: set = field(default_factory=set)
    # Die Drehmaschine mit C an der Hauptspindel: wo die Spitze bei C 0 hinkommt (stirnseite.Rahmen,
    # Y bis zum eingestellten Anteil) – an der Stirnseite hilft C, wo Y nicht reicht. None: nie.
    stirn: object = None


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
    hinweis: str = ""  # ein Satz zur Operation im Fenster und als Kommentar
    # Für den Kopf (D-4): das Werkzeug mit seiner Einspannung („Schaftfräser Ø 12 – Auskragung
    # 35 mm, ER25“) und, wo es knapp wird, ein Satz dazu.
    einspannung: str = ""
    knapp: str = ""
    messstopp: bool = False  # ein Messstopp: keine Bearbeitung – kein erzwungener Wechsel
    # 5 Achsen simultan: eine Funktion ohne Argumente, die die Sätze für eine Steuerung mit TCPM
    # gibt (simultan.befehle_mit_tcpm) – erst beim Schreiben gerechnet, nur mit Haken „TCPM“.
    befehle_tcpm: object = None
    # Mit Magazin der Maschine (W-002 Stufe H3): der Name an der Steuerung für {werkzeug} im
    # Wechsel (Siemens T="…") und was an der Maschine zu tun ist (magazin.ruesten: Art, Satz).
    name_steuerung: str = ""
    ruesten_art: str = ""
    ruesten: str = ""
    # Eine Rundum-Operation: (Rundachse, Drehsinn), mit dem ihre Bahn gerechnet ist (_c_nach_din).
    drehsinn: tuple = ()
    # An der Stirnseite (stirnseite.ist_stirn): (Modus, sichere Höhe) – an der Drehmaschine mit
    # C rechnet das Programm sie um (stirnseite.befehle).
    stirn: tuple = ()
    koordinatenstellen: int = STELLEN  # fein geprüfte Simultanbahnen reservieren 6 Stellen
    # Für die Werkzeugliste im Kopf (Manuel, 2026-10-25: „werkzeugliste am anfang mit
    # ausspannlängen, durchmesser, und länge von spindelnase“): {"name", "d", "auskragung",
    # "nase", "halter", "geschaetzt"} – leer, wenn das Werkzeug nicht in der Werkzeugverwaltung
    # steht (dann wären Länge und Halter geraten).
    masse: dict = field(default_factory=dict)
    # Die Nullpunkte des Jobs (CAM: Fixtures; bei einer Ebene die des Grundjobs) – „G54“ …
    nullpunkte: tuple = ()


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
        "kopf_drehmaschine": (
            tr("pp.feld.kopf_drehmaschine"),
            tr("pp.feld.kopf_drehmaschine.tooltip"),
        ),
        "kopf_drehen": (tr("pp.feld.kopf_drehen"), tr("pp.feld.kopf_drehen.tooltip")),
        "rohteil_fraesen": (tr("pp.feld.rohteil_fraesen"), tr("pp.feld.rohteil_fraesen.tooltip")),
        "rohteil_drehen": (tr("pp.feld.rohteil_drehen"), tr("pp.feld.rohteil_drehen.tooltip")),
        "durchmesser_ein": (tr("pp.feld.durchmesser_ein"), tr("pp.feld.durchmesser_ein.tooltip")),
        "radius_ein": (tr("pp.feld.radius_ein"), tr("pp.feld.radius_ein.tooltip")),
        "ende": (tr("pp.feld.ende"), tr("pp.feld.ende.tooltip")),
        "wechsel_fraesen": (tr("pp.feld.wechsel_fraesen"), tr("pp.feld.wechsel_fraesen.tooltip")),
        "vorwahl": (tr("pp.feld.vorwahl"), tr("pp.feld.vorwahl.tooltip")),
        "vor_wechsel": (tr("pp.feld.vor_wechsel"), tr("pp.feld.vor_wechsel.tooltip")),
        "nach_wechsel": (tr("pp.feld.nach_wechsel"), tr("pp.feld.nach_wechsel.tooltip")),
        "nullpunkt": (tr("pp.feld.nullpunkt"), tr("pp.feld.nullpunkt.tooltip")),
        "nullpunkt_weitere": (
            tr("pp.feld.nullpunkt_weitere"),
            tr("pp.feld.nullpunkt_weitere.tooltip"),
        ),
        "verweilen": (tr("pp.feld.verweilen"), tr("pp.feld.verweilen.tooltip")),
        "wechsel_drehen": (tr("pp.feld.wechsel_drehen"), tr("pp.feld.wechsel_drehen.tooltip")),
        "laenge_ein": (tr("pp.feld.laenge_ein"), tr("pp.feld.laenge_ein.tooltip")),
        "laenge_wieder": (tr("pp.feld.laenge_wieder"), tr("pp.feld.laenge_wieder.tooltip")),
        "laenge_ein_drehen": (
            tr("pp.feld.laenge_ein_drehen"),
            tr("pp.feld.laenge_ein_drehen.tooltip"),
        ),
        "wechselpunkt_mks": (
            tr("pp.feld.wechselpunkt_mks"),
            tr("pp.feld.wechselpunkt_mks.tooltip"),
        ),
        "wechselpunkt_wks": (
            tr("pp.feld.wechselpunkt_wks"),
            tr("pp.feld.wechselpunkt_wks.tooltip"),
        ),
        "marke": (tr("pp.feld.marke"), tr("pp.feld.marke.tooltip")),
        "spindel_ein": (tr("pp.feld.spindel_ein"), tr("pp.feld.spindel_ein.tooltip")),
        "spindel_aus": (tr("pp.feld.spindel_aus"), tr("pp.feld.spindel_aus.tooltip")),
        "angetrieben_ein": (tr("pp.feld.angetrieben_ein"), tr("pp.feld.angetrieben_ein.tooltip")),
        "rundachse_plus": (tr("pp.feld.rundachse_plus"), tr("pp.feld.rundachse_plus.tooltip")),
        "rundachse_minus": (tr("pp.feld.rundachse_minus"), tr("pp.feld.rundachse_minus.tooltip")),
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
        "tuer_auf": (tr("pp.feld.tuer_auf"), tr("pp.feld.tuer_auf.tooltip")),
        "tuer_zu": (tr("pp.feld.tuer_zu"), tr("pp.feld.tuer_zu.tooltip")),
        "meldung": (tr("pp.feld.meldung"), tr("pp.feld.meldung.tooltip")),
        "meldung_aus": (tr("pp.feld.meldung_aus"), tr("pp.feld.meldung_aus.tooltip")),
        "schwenken": (tr("pp.feld.schwenken"), tr("pp.feld.schwenken.tooltip")),
        "schwenken_aus": (tr("pp.feld.schwenken_aus"), tr("pp.feld.schwenken_aus.tooltip")),
        "tcpm_ein": (tr("pp.feld.tcpm_ein"), tr("pp.feld.tcpm_ein.tooltip")),
        "tcpm_aus": (tr("pp.feld.tcpm_aus"), tr("pp.feld.tcpm_aus.tooltip")),
        "bohren": (tr("pp.feld.bohren"), tr("pp.feld.bohren.tooltip")),
        "bohren_verweilen": (
            tr("pp.feld.bohren_verweilen"),
            tr("pp.feld.bohren_verweilen.tooltip"),
        ),
        "tiefbohren": (tr("pp.feld.tiefbohren"), tr("pp.feld.tiefbohren.tooltip")),
        "spaenebrechen": (tr("pp.feld.spaenebrechen"), tr("pp.feld.spaenebrechen.tooltip")),
        "reiben": (tr("pp.feld.reiben"), tr("pp.feld.reiben.tooltip")),
        "gewinde": (tr("pp.feld.gewinde"), tr("pp.feld.gewinde.tooltip")),
        "gewinde_vorher": (tr("pp.feld.gewinde_vorher"), tr("pp.feld.gewinde_vorher.tooltip")),
        "gewinde_ausgleich": (
            tr("pp.feld.gewinde_ausgleich"),
            tr("pp.feld.gewinde_ausgleich.tooltip"),
        ),
    }.get(feld, (feld, ""))


def haken_text(feld):
    """(Name, Erklärung) eines Hakens fürs Fenster – die Schlüssel wörtlich."""
    return {
        "kommentare": (tr("pp.haken.kommentare"), tr("pp.haken.kommentare.erklaerung")),
        "nur_ascii": (tr("pp.haken.nur_ascii"), tr("pp.haken.nur_ascii.erklaerung")),
        "grossbuchstaben": (
            tr("pp.haken.grossbuchstaben"),
            tr("pp.haken.grossbuchstaben.erklaerung"),
        ),
        "satznummern": (tr("pp.haken.satznummern"), tr("pp.haken.satznummern.erklaerung")),
        "leerzeichen": (tr("pp.haken.leerzeichen"), tr("pp.haken.leerzeichen.erklaerung")),
        "rohteil": (tr("pp.haken.rohteil"), tr("pp.haken.rohteil.erklaerung")),
        "kuehlung": (tr("pp.haken.kuehlung"), tr("pp.haken.kuehlung.erklaerung")),
        "wechselpunkt": (tr("pp.haken.wechselpunkt"), tr("pp.haken.wechselpunkt.erklaerung")),
        "marken": (tr("pp.haken.marken"), tr("pp.haken.marken.erklaerung")),
        "werkzeugliste": (tr("pp.haken.werkzeugliste"), tr("pp.haken.werkzeugliste.erklaerung")),
        "werkzeug_vorwahl": (
            tr("pp.haken.werkzeug_vorwahl"),
            tr("pp.haken.werkzeug_vorwahl.erklaerung"),
        ),
        "nullpunkt_setzen": (
            tr("pp.haken.nullpunkt_setzen"),
            tr("pp.haken.nullpunkt_setzen.erklaerung"),
        ),
        "hochlauf_warten": (
            tr("pp.haken.hochlauf_warten"),
            tr("pp.haken.hochlauf_warten.erklaerung"),
        ),
        "c_achse": (tr("pp.haken.c_achse"), tr("pp.haken.c_achse.erklaerung")),
        "g93": (tr("pp.haken.g93"), tr("pp.haken.g93.erklaerung")),
        "schwenkzyklus": (tr("pp.haken.schwenkzyklus"), tr("pp.haken.schwenkzyklus.erklaerung")),
        "tcpm": (tr("pp.haken.tcpm"), tr("pp.haken.tcpm.erklaerung")),
        "bohrzyklen": (tr("pp.haken.bohrzyklen"), tr("pp.haken.bohrzyklen.erklaerung")),
        "gewinde_synchron": (
            tr("pp.haken.gewinde_synchron"),
            tr("pp.haken.gewinde_synchron.erklaerung"),
        ),
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


ASCII_ERSATZ = (
    ("ä", "ae"),
    ("ö", "oe"),
    ("ü", "ue"),
    ("Ä", "Ae"),
    ("Ö", "Oe"),
    ("Ü", "Ue"),
    ("ß", "ss"),
    ("Ø", "D"),
    ("ø", "D"),
    ("–", "-"),
    ("—", "-"),
    ("·", "-"),
    ("×", "x"),
    ("°", " Grad"),
    ("„", '"'),
    ("“", '"'),
    ("”", '"'),
    ("‚", "'"),
    ("‘", "'"),
    ("’", "'"),
    ("…", "..."),
    ("−", "-"),
    ("≈", "~"),
    ("µ", "u"),
)


def ascii_text(text):
    """Der Text nur mit ASCII-Zeichen – Umlaute und Zeichen wie Ø, –, · ersetzt, der Rest „?“."""
    for alt, neu in ASCII_ERSATZ:
        text = text.replace(alt, neu)
    return text.encode("ascii", "replace").decode("ascii")


def _kommentar(s, text):
    text = text.replace("(", "[").replace(")", "]")
    if s.nur_ascii:
        text = ascii_text(text)
    if s.grossbuchstaben:
        text = text.upper()
    return f"; {text}" if s.kommentar.strip() == ";" else f"({text})"


def _werkzeugname(name, nummer):
    """Der Name des Werkzeugs für {werkzeug} im Wechselbefehl: ASCII, ohne Anführungszeichen –
    ohne Namen „T“ und die Nummer."""
    name = ascii_text(str(name or "")).replace('"', "").strip()
    return name or f"T{int(nummer or 0)}"


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


_NULLPUNKT = re.compile(r"G5([4-9])|G59\.([1-9])|G54\.1\s*P(\d+)")


def nullpunkt_nummer(register):
    """Die Nummer des Nullpunkts, wie der Job ihn nennt (FreeCADs Fixtures): G54 … G59 → 1 … 6,
    G59.1 … G59.9 und G54.1 P1 … → 7 …; None, wenn es keiner ist."""
    m = _NULLPUNKT.fullmatch(str(register).strip().upper())
    if m is None:
        return None
    if m.group(1):
        return int(m.group(1)) - 3
    weiter = int(m.group(2) or m.group(3))
    return 6 + weiter if weiter > 0 else None


def nullpunkt_befehl(s, register):
    """Die Zeilen, mit denen die Steuerung `s` den Nullpunkt `register` (wie der Job ihn nennt)
    anwählt – leer, wenn sie dafür keinen Befehl hat."""
    nr = nullpunkt_nummer(register)
    if nr is None:
        return []
    vorlage = s.nullpunkt if nr <= s.nullpunkt_grund else s.nullpunkt_weitere
    g = f"G5{nr + 3}" if nr <= 6 else ""
    return _zeilen(_fuellen(vorlage, g=g, nr=nr, e=nr - 6, nn=f"{nr:02d}"))


def _adresse(s, buchstabe, info):
    """Wie die Adresse im Programm heißt: die Rundachse mit dem NC-Namen der Maschine, wenn
    die Steuerung ihn nimmt (Siemens), sonst ihr Buchstabe."""
    if buchstabe in ROTATION and not s.nur_buchstabe:
        return info.rundachsen.get(buchstabe, buchstabe)
    return buchstabe


_MIT_NUMMER = {}  # Adresse → endet sie mit einer Ziffer? – je Wort gefragt, Hunderttausende Mal


def _wort(s, adresse, zahl):
    """„X12.000“ – bei Siemens eine Adresse mit Nummer mit „=“: „C4=90.000“."""
    if s.gleich_bei_nummer:
        mit_nummer = _MIT_NUMMER.get(adresse)
        if mit_nummer is None:
            mit_nummer = _MIT_NUMMER[adresse] = re.search(r"\d$", adresse) is not None
        if mit_nummer:
            return f"{adresse}={zahl}"
    return f"{adresse}{zahl}"


def _rohteil_befehl(s, info, rohteil, abschnitte):
    """Das Rohteil für die Simulation der Steuerung (Steuerung.rohteil_fraesen/_drehen) aus
    `rohteil` ((x, y, z) unten, (x, y, z) oben – der Quader um das Rohteil des Jobs). An der
    Drehmaschine die Stange längs Z (rund in X und Y, sonst keins); an einer Fräse mit Bahnen
    um eine Rundachse keins – die Stange dort ist kein Quader."""
    (x0, y0, z0), (x1, y1, z1) = rohteil
    if info.drehmaschine:
        if not s.rohteil_drehen or abs((x1 - x0) - (y1 - y0)) > 0.01:
            return ""
        werte = {"z0": z1, "z1": z0, "zb": z0, "d": x1 - x0}
        return _fuellen(s.rohteil_drehen, **{k: _zahl(v) for k, v in werte.items()})
    if not s.rohteil_fraesen:
        return ""
    for abschnitt in abschnitte:
        if any(set(_befehl(b)[1]) & set(ROTATION) for b in abschnitt.befehle):
            return ""
    werte = {"z0": z1, "z1": z0, "zb": z0, "x0": x0, "y0": y0, "x1": x1, "y1": y1}
    return _fuellen(s.rohteil_fraesen, **{k: _zahl(v) for k, v in werte.items()})


def _modulo_wort(s, adresse, wert, davor, stellen=STELLEN):
    """„C4=ACN(270.000)“ – eine Moduloachse: die Position im Bereich 0 … unter 360°, die Vorlage
    nach der Drehrichtung der Bahn (`davor`: der fortlaufende Winkel davor; ohne: ab Null)."""
    zahl = _modulo_zahl(wert, stellen)
    vorlage = (
        s.rundachse_minus if wert < (davor if davor is not None else 0.0) else s.rundachse_plus
    )
    return f"{adresse}={_fuellen(vorlage, wert=zahl)}"


def _modulo_zahl(wert, stellen=STELLEN):
    """Die Position einer Moduloachse, wie sie im Programm steht: 0 … unter 360°."""
    zahl = _zahl(wert % 360.0, stellen)
    return _zahl(0.0, stellen) if float(zahl) >= 360.0 else zahl  # gerundet genau eine Umdrehung: 0


def _rund_umdrehen(abschnitt, info):
    """Die Rundachsen, deren Werte das Programm in diesem Abschnitt mit dem anderen Vorzeichen
    schreibt: eine Rundum-Bahn nach _c_umdrehen; sonst die Rundachsen, die an der Maschine gegen
    ihr Gelenk zählen (Maschineninfo.umgekehrt). Ohne Maschine die Ebene einer Tisch/Tisch-A/C
    (schwenken.rundachsen_ohne_maschine dreht das Werkstück mit +A, +C rechtsherum – nach
    DIN 66217 andersherum)."""
    if abschnitt.drehsinn:
        buchstabe = _c_umdrehen(abschnitt, info)
        return {buchstabe} if buchstabe else set()
    if info.rundachsen:
        return set(info.umgekehrt)
    schwenkung = abschnitt.schwenkung
    if schwenkung is not None and set(schwenkung.rund) == {"A", "C"}:
        return {"A", "C"}
    return set()


def _c_umdrehen(abschnitt, info):
    """Die Rundachse einer Rundum-Operation, deren Werte das Programm umdreht – sonst "".

    Die Bahn trägt −Drehsinn · φ (vierachs_bahn.befehle) – so zeigt FreeCAD sie richtig um das
    Teil: Es dreht bei +C das Teil rechtsherum. Nach DIN 66217 beschreibt +C aber, wie sich das
    Werkzeug um das Werkstück dreht; das Werkstück dreht dabei andersherum – an der Drehmaschine,
    von vorn auf das Futter geschaut, im Uhrzeigersinn (Manuel, 2026-10-05: „wenn ich vom Werkzeug
    aus auf die Spindel schaue, erhöht sich die Gradzahl, wenn ich das Futter rechtsrum drehe“;
    „die Werkzeugwege waren komplett fein – das Einzige, was du anpassen musst, ist der
    Postprozessor“). Nach DIN schreibt das Programm also C = φ: umgedreht, wo die Bahn mit
    Drehsinn +1 gerechnet ist. Ohne den Haken „dreht nach DIN 66217“ zählt die Maschine wie
    FreeCAD: C = −φ."""
    if not abschnitt.drehsinn:
        return ""
    buchstabe, drehsinn = abschnitt.drehsinn
    soll = -1 if info.nach_din.get(buchstabe, True) else 1  # der Drehsinn, der C = Programm gibt
    return buchstabe if drehsinn != soll else ""


def _befehl(eintrag):
    """(Name, {Adresse: Wert}) aus einem Path.Command oder einem Paar."""
    if isinstance(eintrag, tuple):
        return eintrag[0], dict(eintrag[1])
    return eintrag.Name, dict(eintrag.Parameters)


def programm(
    abschnitte, s, info=None, name="", vorschau=None, datei="", rohteil=None, einrichten="",
    nummer=1,
):  # fmt: skip
    """Das Programm (Programm) für die Abschnitte mit der Steuerung `s` und der Maschine
    `info`. `vorschau`: höchstens so viele Bewegungssätze, dann ein Hinweis – fürs Fenster.
    Klartext (Heidenhain): `datei` gibt den Namen im BEGIN/END PGM (wie die Datei, sonst `name`),
    `rohteil` ((xmin, ymin, zmin), (xmax, ymax, zmax)) das BLK FORM. `einrichten`: wie man
    einrichtet (die Aufspannung einer N-Eck-Stange, n_eck.einrichten_text) – als Kommentar im
    Kopf und als Hinweis. `nummer`: die Programmnummer im Kopf (Fanuc „O1234“)."""
    info = info or Maschineninfo()
    s = s.wirksam()  # ohne „Gewindebohren synchron“ die Befehle mit Ausgleichsfutter
    koordinatenstellen = max((a.koordinatenstellen for a in abschnitte), default=STELLEN)
    if koordinatenstellen > STELLEN:
        # Fein geprüfte Bahnen haben nur einen kleinen Vorrat für die Steuerungsglättung.
        s = s.ersetzt(toleranz=min(s.toleranz, 0.0001))
    zeilen, hinweise = [], []
    if s.dialekt == "klartext":
        if info.drehmaschine:
            hinweise.append(tr("pp.hinweis.klartext_drehen"))
        # Klartext immer in ASCII: die TNC nimmt in Kommentaren keine Umlaute (klartext.pruefe).
        s = s.ersetzt(g93=False, satznummern=False, nur_ascii=True)
        fertig = _klartext_fertig(s, name, datei, rohteil, hinweise, koordinatenstellen)
    elif s.dialekt == "mpr":
        s = s.ersetzt(g93=False, satznummern=False, wechselpunkt=False, marken=False)
        fertig = _mpr_fertig(s, name, rohteil, hinweise)
    else:

        def fertig(zeilen_, saetze_):
            return Programm(_ohne_leerzeichen(_nummeriert(zeilen_, s), s), hinweise, saetze_)

    def notiz(text):
        if s.kommentare:
            zeilen.append(_kommentar(s, text))

    kommentar_name = _kommentar(s, name or tr("pp.programm")) if s.kommentare else ""
    kopf = s.kopf_drehmaschine if info.drehmaschine and s.kopf_drehmaschine else s.kopf
    nummer = min(max(1, int(nummer or 1)), s.programmnummer_max or 99999999)
    for zeile in _zeilen(_fuellen(kopf, kommentar_name=kommentar_name, name=name, nummer=nummer)):
        zeilen.append(zeile)
    if info.drehmaschine:
        zeilen.extend(_zeilen(s.kopf_drehen))
        zeilen.extend(_zeilen(s.durchmesser_ein if info.x_durchmesser else s.radius_ein))
    if s.rohteil and rohteil is not None:
        zeilen.extend(_zeilen(_rohteil_befehl(s, info, rohteil, abschnitte)))
    for glaetten in s.glaetten_an():
        zeilen.extend(
            _zeilen(_fuellen(glaetten.befehl, toleranz=_zahl(s.toleranz, koordinatenstellen)))
        )
        if glaetten.option:
            hinweise.append(tr("pp.hinweis.option", befehl=glaetten.befehl.split("\n")[0]))
    if einrichten:
        notiz(einrichten)
        hinweise.append(einrichten)
    if not info.name:
        hinweise.append(tr("pp.hinweis.ohne_maschine"))
    hinweise.extend(_ruest_hinweise(abschnitte))
    vergeben = set()
    marken = [markenname(a.name, vergeben) for a in abschnitte] if s.marken else []
    if s.kommentare:
        zeilen.extend(_kopfzeilen(s, abschnitte, marken))
    if marken:
        # Zurück an den Anfang: eine Marke, wo die Steuerung Namen kennt, sonst der Name als
        # Kommentar – suchen nach ANFANG (Manuel, 2026-10-25).
        if s.marke and "{n}" not in s.marke:
            zeilen.append(_fuellen(s.marke, marke=MARKE_ANFANG, n=0))
        else:
            notiz(MARKE_ANFANG)
    ebene = "G17"  # die Ebene der Bögen: was der Kopf setzt, danach was die Bahn setzt
    for zeile in zeilen:
        for treffer in _EBENE.finditer(zeile.upper()):
            ebene = "G1" + treffer.group(1)
    werkzeug = None
    spindel_an = None  # ("haupt" oder Nummer des Antriebs, Drehzahl, Richtung)
    c_an = False
    g93 = False
    stand = {}  # Adresse → Wert, wie zuletzt angefahren (für den Vorschub ohne G93)
    saetze = 0
    gesehen = set()
    auf_r = False  # G99: Bohrzyklen ziehen auf R zurück, sonst (G98) auf die Höhe davor
    gewinde_folge = False  # G84/G74 schon in diesem Zyklus (Fanuc: M29 nur vor dem ersten)
    wechsel_zahl = 0  # so viele Werkzeugwechsel
    # Nur an der Fräse – an der Drehmaschine bohrte CYCLE83 ohne _AXN entlang der falschen Achse.
    # Mit allen Bohrzyklen als Befehl entfallen G80/G98/G99 (Siemens: nur im ISO-Modus); hat nur
    # das Gewinde eine Vorlage (LinuxCNC G33.1), bleiben sie für die anderen.
    zyklen_als_befehl = not info.drehmaschine and all(
        getattr(s, f)
        for f in ("bohren", "bohren_verweilen", "tiefbohren", "spaenebrechen", "reiben")
    )
    geschwenkt = None  # die Schwenkung, in der die Maschine gerade steht
    zyklus = bool(s.schwenkzyklus and s.schwenken)
    laenge_offen = ""  # die Werkzeuglänge – kommt in den ersten Satz nach dem Wechsel mit Z
    nullpunkt_aktiv = None  # der Nullpunkt, den das Programm zuletzt angewählt hat
    for nummer_ab, abschnitt in enumerate(abschnitte):
        stellen = abschnitt.koordinatenstellen
        # Jede Bearbeitung ein vollständiger Einstieg hinter ihrer Marke (D-4): Wechselpunkt,
        # Werkzeug, Spindel, Kühlung und Ebene neu – auch mit demselben Werkzeug wie davor.
        einstieg = bool(
            s.marken and s.einstieg_je_marke and abschnitt.werkzeug and not abschnitt.messstopp
        )
        if s.marken and s.marke:
            zeilen.append(_fuellen(s.marke, marke=marken[nummer_ab], n=nummer_ab + 1))
        if marken and (not s.marke or "{n}" in s.marke):
            # Ohne Marke mit Namen: der Name im Kommentar – so findet die Suche ihn.
            notiz(f"{marken[nummer_ab]} – {abschnitt.name}")
        else:
            notiz(abschnitt.name)
        if abschnitt.hinweis:
            hinweise.append(f"{abschnitt.name}: {abschnitt.hinweis}")
            if s.kommentare:
                zeilen.append(_kommentar(s, abschnitt.hinweis))
        befehle_roh = abschnitt.befehle
        if s.tcpm and s.tcpm_ein and abschnitt.befehle_tcpm is not None:
            try:
                befehle_roh = abschnitt.befehle_tcpm(bei_null=s.tcpm_bei_null)
            except ValueError as grund:
                hinweise.append(
                    f"{abschnitt.name}: {tr('pp.hinweis.tcpm_fehler', grund=str(grund))}"
                )
        if abschnitt.schwenkung is not None and not zyklus:
            # Fährt die Maschine davor zum Wechselpunkt ganz oben, schwenkt sie dort – nicht
            # erst wieder hinunter auf die Schwenkhöhe.
            wechselt = (
                abschnitt.werkzeug and (abschnitt.werkzeug != werkzeug or einstieg)
            ) or not sw.gleiche(geschwenkt, abschnitt.schwenkung)
            oben = bool(wechselt) and _wechselpunkt_oben(s, info)
            try:
                befehle_roh = sw.befehle_ohne_zyklus(
                    befehle_roh, abschnitt.schwenkung, schon_oben=oben
                )
            except ValueError as grund:
                hinweise.append(f"{abschnitt.name}: {grund}")
                zeilen.append(_kommentar(s, f"{abschnitt.name}: {grund}"))
                continue
        if abschnitt.stirn and info.stirn is not None:
            # An der Stirnseite: Y, so weit es reicht, sonst hilft C (stirnseite).
            from . import stirnseite as st

            try:
                befehle_roh = st.befehle(befehle_roh, info.stirn, *abschnitt.stirn, programm=True)
            except ValueError as grund:
                hinweise.append(f"{abschnitt.name}: {grund}")
                zeilen.append(_kommentar(s, f"{abschnitt.name}: {grund}"))
                continue
        befehle = [_befehl(b) for b in befehle_roh]
        umdrehen = _rund_umdrehen(abschnitt, info)
        if umdrehen:
            for _name, werte in befehle:
                for buchstabe in umdrehen & set(werte):
                    werte[buchstabe] = -werte[buchstabe]
        # Der Nullpunkt des Jobs – am Anfang und in jedem Einstieg, vor dem Wechselpunkt (in WKS)
        # und dem Schwenken (Heidenhain: Zyklus 247 setzt Zyklus 7 zurück).
        nullpunkt = []
        register = abschnitt.nullpunkte[0] if abschnitt.nullpunkte else ""
        if s.nullpunkt_setzen and register and (register != nullpunkt_aktiv or einstieg):
            nullpunkt = nullpunkt_befehl(s, register)
            if register != nullpunkt_aktiv:
                hinweis = ""
                if not nullpunkt:
                    hinweis = tr("pp.hinweis.nullpunkt_fehlt", register=register, steuerung=s.name)
                elif len(abschnitt.nullpunkte) > 1:
                    hinweis = tr(
                        "pp.hinweis.nullpunkte_mehrere",
                        register=register,
                        alle=", ".join(abschnitt.nullpunkte),
                    )
                if hinweis and hinweis not in hinweise:
                    hinweise.append(hinweis)
            nullpunkt_aktiv = register
        gewechselt = False
        if abschnitt.werkzeug and (abschnitt.werkzeug != werkzeug or einstieg):
            if spindel_an is not None:
                zeilen.extend(_spindel_aus(s, spindel_an))
                spindel_an = None
            zurueck = None
            if s.schwenken_aus_zuerst and zyklus and geschwenkt is not None:
                zeilen.extend(_zeilen(s.schwenken_aus))  # Fanuc G69 vor G54 und G53
                zurueck, geschwenkt = geschwenkt, None
            zeilen.extend(nullpunkt)
            nullpunkt = []
            zeilen.extend(_zum_wechselpunkt(s, info))
            if zurueck is not None:  # die Rundachsen oben auf 0
                zeilen.extend(_schwenken_aus(s, zurueck, False, _wechselpunkt_oben(s, info), info))
            if geschwenkt is not None and not sw.gleiche(geschwenkt, abschnitt.schwenkung):
                oben = _wechselpunkt_oben(s, info)
                ohne = abschnitt.schwenkung is None
                zeilen.extend(_schwenken_aus(s, geschwenkt, zyklus, oben, info, ohne))
                geschwenkt = None
            if abschnitt.werkzeugname:
                notiz(f"T{abschnitt.werkzeug} {abschnitt.werkzeugname}")
            vorlage = s.wechsel_drehen if info.drehmaschine else s.wechsel_fraesen
            name_w = _werkzeugname(
                abschnitt.name_steuerung or abschnitt.werkzeugname, abschnitt.werkzeug
            )
            for befehl in (s.vor_wechsel, vorlage):
                zeilen.extend(_zeilen(_fuellen(befehl, t=int(abschnitt.werkzeug), werkzeug=name_w)))
            wechsel_zahl += 1
            naechstes = next(
                (
                    a
                    for a in abschnitte[nummer_ab + 1 :]
                    if a.werkzeug and a.werkzeug != abschnitt.werkzeug
                ),
                None,
            )
            if s.werkzeug_vorwahl and s.vorwahl and naechstes is not None and not info.drehmaschine:
                name_naechstes = naechstes.name_steuerung or naechstes.werkzeugname
                zeilen.extend(
                    _zeilen(
                        _fuellen(
                            s.vorwahl,
                            t=int(naechstes.werkzeug),
                            werkzeug=_werkzeugname(name_naechstes, naechstes.werkzeug),
                        )
                    )
                )
            zeilen.extend(
                _zeilen(_fuellen(s.nach_wechsel, t=int(abschnitt.werkzeug), werkzeug=name_w))
            )
            # Ohne Befehl bringt der Wechsel die Länge mit (Siemens D1, Fanuc T0101).
            laenge_offen = _fuellen(
                s.laenge_ein_drehen if info.drehmaschine else s.laenge_ein,
                t=int(abschnitt.werkzeug),
            )
            werkzeug = abschnitt.werkzeug
            gewechselt = True
        zeilen.extend(nullpunkt)  # ohne Wechsel (Bahn ohne Werkzeug am Anfang)
        if not sw.gleiche(geschwenkt, abschnitt.schwenkung) or (
            einstieg and abschnitt.schwenkung is not None
        ):
            # Eine andere Ebene (oder dieselbe nach der Marke neu): erst weg vom Teil (ohne
            # Zyklus; CYCLE800 fährt selbst frei).
            ins_freie = (  # CYCLE800() dreht nicht zurück: erst nach oben, dann auf 0
                geschwenkt is not None
                and abschnitt.schwenkung is None
                and not s.schwenken_aus_dreht
            )
            if not gewechselt and (not zyklus or s.schwenken_aus_zuerst or ins_freie):
                if spindel_an is not None:
                    zeilen.extend(_spindel_aus(s, spindel_an))
                    spindel_an = None
                zurueck = None
                if zyklus and geschwenkt is not None:  # G69/CYCLE800(), hoch, Rundachsen auf 0
                    zeilen.extend(_zeilen(s.schwenken_aus))
                    zurueck, geschwenkt = geschwenkt, None
                weg = _zum_wechselpunkt(s, info)
                zeilen.extend(weg)
                if zurueck is not None:
                    oben = _wechselpunkt_oben(s, info)
                    zeilen.extend(_schwenken_aus(s, zurueck, False, oben, info))
                if weg and s.laenge_wieder and werkzeug:
                    laenge_offen = _fuellen(s.laenge_wieder, t=int(werkzeug))
            if geschwenkt is not None and abschnitt.schwenkung is None:
                oben = _wechselpunkt_oben(s, info)
                zeilen.extend(_schwenken_aus(s, geschwenkt, zyklus, oben, info))
            if abschnitt.schwenkung is not None:
                umgekehrt = _rund_umdrehen(abschnitt, info)
                rund = sw.text_rundachsen(
                    {b: -w if b in umgekehrt else w for b, w in abschnitt.schwenkung.rund.items()},
                    programm=True,
                )
                notiz(tr("pp.ebene", rundachsen=rund))
                if zyklus:
                    zeilen.extend(_schwenken_ein(s, abschnitt.schwenkung, info, umgekehrt))
            geschwenkt = abschnitt.schwenkung
        mit_rundachse = any(set(p) & set(ROTATION) for _n, p in befehle)
        if info.drehmaschine and mit_rundachse and not c_an and s.c_achse:
            # Auch ohne Befehl der Hinweis: Gerade dann muss ihn jemand eintragen (Fanuc).
            _hersteller(s, "c_ein", hinweise, gesehen, zeilen)
            if s.c_ein:
                zeilen.extend(_zeilen(_fuellen(s.c_ein, h=_haupt(info))))
                c_an = True
        antrieb = info.angetrieben.get(int(abschnitt.werkzeug or 0)) if info.drehmaschine else None
        drehzahl_ab, faktor = abschnitt.drehzahl, 1.0
        if (
            info.drehzahl_max > 0
            and drehzahl_ab > info.drehzahl_max + 0.5
            and (antrieb or not info.drehmaschine)
        ):
            # Über der Höchstdrehzahl: S auf sie, die Vorschübe im selben Maß (fz bleibt).
            faktor = info.drehzahl_max / drehzahl_ab
            hinweis = tr(
                "pp.hinweis.drehzahl_begrenzt",
                operation=abschnitt.name,
                s=f"{drehzahl_ab:.0f}",
                max=f"{info.drehzahl_max:.0f}",
                prozent=f"{faktor * 100:.0f}",
            )
            hinweise.append(hinweis)
            notiz(hinweis)
            drehzahl_ab = info.drehzahl_max
        soll = (antrieb or "haupt", round(drehzahl_ab, 3), abschnitt.rueckwaerts)
        if drehzahl_ab > 0 and soll != spindel_an:
            if spindel_an is not None:
                zeilen.extend(_spindel_aus(s, spindel_an))
            m = 4 if abschnitt.rueckwaerts else 3
            drehzahl = f"{drehzahl_ab:.0f}"
            if antrieb:
                zeilen.append(_fuellen(s.angetrieben_ein, m=m, s=drehzahl, n=antrieb))
                _hersteller(s, "angetrieben_ein", hinweise, gesehen, zeilen)
            else:
                zeilen.append(_fuellen(s.spindel_ein, m=m, s=drehzahl))
            spindel_an = soll
            if s.hochlauf_warten and s.verweilen:
                # Warten, bis die Spindel ihre Drehzahl hat (die Hochlaufzeit an der Maschine).
                sekunden = info.hochlauf.get(antrieb or "haupt", 0.0)
                if sekunden > 0:
                    zeilen.extend(_zeilen(_fuellen(s.verweilen, sek=_zahl(sekunden))))
                elif (antrieb or "haupt") in info.hochlauf:  # die Spindel ist da, die Zeit fehlt
                    hinweis = tr("pp.hinweis.hochlauf_fehlt", maschine=info.name, steuerung=s.name)
                    if hinweis not in hinweise:
                        hinweise.append(hinweis)
        kuehlung = {"Flood": s.kuehlung_flut, "Mist": s.kuehlung_nebel}.get(abschnitt.kuehlung)
        if not s.kuehlung:
            kuehlung = None
        if kuehlung:
            zeilen.append(kuehlung)
        messstopp = False  # nach dem Kommentar des Messstopps: sein „G0 Z…“ kommt noch
        im_messstopp = bool(abschnitt.messstopp)  # … und sein Halt (M0): Tür auf und zu
        for name_, parameter in befehle:
            if name_.startswith("("):
                notiz(name_.strip("()"))
                messstopp = messstopp or name_ == ms.KOMMENTAR
                im_messstopp = im_messstopp or name_ == ms.KOMMENTAR
                continue
            if messstopp and name_.upper() in ("G0", "G00") and set(parameter) <= {"Z", "F"}:
                # Zum Messen an den Wechselpunkt (Spezifikation Strategien 12.4: an Manuels
                # Siemens F_HOME) – ohne einen bleibt es beim Z hoch.
                messstopp = False
                weg = _zum_wechselpunkt(s, info)
                if weg:
                    zurueck = None
                    if s.schwenken_aus_zuerst and zyklus and geschwenkt is not None:
                        zeilen.extend(_zeilen(s.schwenken_aus))  # Fanuc G69 vor G53
                        zurueck, geschwenkt = geschwenkt, None
                    zeilen.extend(weg)
                    if zurueck is not None:
                        oben = _wechselpunkt_oben(s, info)
                        zeilen.extend(_schwenken_aus(s, zurueck, False, oben, info))
                    if s.laenge_wieder and werkzeug:
                        laenge_offen = _fuellen(s.laenge_wieder, t=int(werkzeug))
                    continue
            gross = name_.upper()
            steigung = None
            if gross in GEWINDE and "F" in parameter and float(parameter.get("S", 0) or 0) > 0:
                # FreeCADs Gewinde: in F die Steigung (mm), in S die Drehzahl – der Vorschub ist ihr
                # Produkt. Bis P-2026-10-25-64 stand die Steigung als mm/s da: M10 × 1,5 bei
                # 255 1/min „F90“ statt F382,5 – der Gewindebohrer wäre abgerissen.
                steigung = float(parameter["F"])
                parameter = dict(parameter, F=steigung * float(parameter["S"]) / 60.0)
                if gross == "G74":
                    steigung = -steigung  # Linksgewinde
            if gross in BEWEGUNG or gross == "G80":
                gewinde_folge = False
            if im_messstopp and gross in ("M5", "M05"):
                # Spindel aus – die, die läuft: an der Drehmaschine mit angetriebenem Werkzeug
                # dessen Befehl (Siemens „M3=5“), nicht M5 der Hauptspindel, die als C-Achse
                # steht (P-2026-10-18-54).
                if spindel_an is not None:
                    zeilen.extend(_spindel_aus(s, spindel_an))
                    spindel_an = None
                else:
                    zeilen.append("M5")
                continue
            if im_messstopp and gross in ("M3", "M03", "M4", "M04"):
                # Nach dem Start: Die Spindel schaltet die nächste Bearbeitung selbst ein – mit
                # ihrem Antrieb und ihrer Drehzahl (spindel_an ist dann None); roh hieße es an der
                # Drehmaschine: die Hauptspindel an.
                continue
            if im_messstopp and gross in ("M0", "M00"):
                # Der Halt zum Messen: davor die Tür auf, danach zu – wie die Steuerung es sagt
                # (Steuerung.tuer_auf/tuer_zu; leer: nur der Halt).
                if s.tuer_auf:
                    zeilen.extend(_zeilen(s.tuer_auf))
                if s.meldung:
                    text = tr("pp.meldung.messstopp").replace('"', "")
                    text = ascii_text(text) if s.nur_ascii else text
                    zeilen.extend(_zeilen(_fuellen(s.meldung, text=text)))
                zeilen.append("M0")
                if s.meldung_aus:
                    zeilen.extend(_zeilen(s.meldung_aus))
                if s.tuer_zu:
                    zeilen.extend(_zeilen(s.tuer_zu))
                continue
            if gross in (si.TCPM_EIN, si.TCPM_AUS):
                ein = gross == si.TCPM_EIN
                zeilen.extend(_zeilen(_fuellen(s.tcpm_ein if ein else s.tcpm_aus, t=werkzeug or 0)))
                if not ein and s.laenge_ein and not info.drehmaschine:
                    # G49 hebt mit TCPM auch die Länge auf: im nächsten Satz mit Z wieder an.
                    laenge_offen = _fuellen(s.laenge_ein, t=int(werkzeug or 0))
                continue
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
            if info.drehmaschine and not s.g90_drehen and gross in ("G90", "G91"):
                if gross == "G90":
                    continue  # absolut ist dort, was X und Z schreiben
                hinweise.append(tr("pp.hinweis.g91_drehen", operation=abschnitt.name))
            if info.drehmaschine and gross in ("G98", "G99") and s.vorschub_minute_drehen == "G98":
                # An Fanuc- und Haas-Drehmaschinen heißt G98/G99 Vorschub je Minute/Umdrehung,
                # nicht Rückzug im Bohrzyklus – weglassen.
                continue
            if gross in ("G98", "G99"):
                auf_r = gross == "G99"
            if zyklen_als_befehl and gross in ("G80", "G98", "G99"):
                continue  # die Zyklen der Steuerung kennen sie nicht (Siemens: ISO-Modus)
            # Ausgeschrieben in G0/G1/G4: ohne Zyklen (GRBL) – und an jeder Drehmaschine: Siemens
            # kennt G81 ff. nur im ISO-Modus, Fanuc-Drehmaschinen haben kein G81, LinuxCNC bohrt
            # in G18 entlang Y.
            if s.zyklen_ausschreiben or info.drehmaschine:
                if gross in ("G80", "G98", "G99"):
                    continue  # GRBL kennt G98/G99 nicht, G80 braucht es ohne Zyklus nicht
                if gross in AUSGESCHRIEBEN:
                    zeilen.extend(
                        _zyklus_ausgeschrieben(
                            s, gross, parameter, stand, auf_r, faktor, stellen, info
                        )
                    )
                    saetze += 1
                    continue
                if gross in GEWINDE and info.drehmaschine and s.gewinde_drehen and s.gewinde:
                    # LinuxCNC G33.1: synchron längs Z – in jeder Ebene, auch an der Drehmaschine.
                    zeilen.extend(
                        _zyklus_als_befehl(
                            s,
                            s.gewinde,
                            parameter,
                            stand,
                            auf_r,
                            faktor,
                            steigung,
                            drehzahl_ab,
                            info,
                        )
                    )
                    saetze += 1
                    continue
                if gross in GEWINDE:
                    if info.drehmaschine:
                        hinweis = tr("pp.hinweis.gewinde_drehen", operation=abschnitt.name)
                    else:
                        hinweis = tr(
                            "pp.hinweis.ohne_gewinde", operation=abschnitt.name, steuerung=s.name
                        )
                    if hinweis not in hinweise:
                        hinweise.append(hinweis)
                        notiz(hinweis)
                    continue
            if laenge_offen and gross not in BEWEGUNG and "Z" in parameter:
                # Ein Bohrzyklus als erster Satz mit Z: die Länge davor in einer eigenen Zeile.
                zeilen.append(laenge_offen)
                laenge_offen = ""
            # Jede gesetzte Vorlage gilt (an der Drehmaschine keine: CYCLE83 bohrte dort ohne _AXN
            # längs der falschen Achse) – auch, wenn eine andere leer ist.
            vorlage = "" if info.drehmaschine else getattr(s, ZYKLUS_FELDER.get(gross, ""), "")
            if vorlage:
                zeilen.extend(
                    _zyklus_als_befehl(
                        s, vorlage, parameter, stand, auf_r, faktor, steigung, drehzahl_ab
                    )
                )
                saetze += 1
                continue
            if gross in GEWINDE and s.gewinde_vorher and not gewinde_folge:
                zeilen.extend(_zeilen(_fuellen(s.gewinde_vorher, s=f"{drehzahl_ab:.0f}")))
            if gross in GEWINDE:
                gewinde_folge = True
            if gross in QUER_ZUR_EBENE:
                ebene = gross
            if gross in ("G1", "G01") and _steht(stand, parameter):
                # FreeCADs Brennschneiden (26.3) zündet mit „G1 F0“ an der Stelle, wo es steht –
                # nichts zu fahren, und F0 lehnen Mach3 und LinuxCNC ab (Forum, t=107926).
                continue
            if gross in BOGEN and _winziger_bogen(gross, parameter, stand, ebene, stellen, info):
                # Gerundet stünden Anfang und Ende gleich – jede Steuerung führe einen Vollkreis.
                gross = "G1"
                parameter = {a: w for a, w in parameter.items() if a not in ("I", "J", "K", "R")}
            woerter = [s.gewinde_g[GEWINDE.index(gross)] if gross in GEWINDE else gross]
            bewegung = gross in BEWEGUNG
            if laenge_offen and bewegung and ("Z" in parameter or info.drehmaschine):
                # An der Fräse im Satz mit Z (in X und Y oben fährt nichts an), an der
                # Drehmaschine im ersten Satz – dort zählt die Korrektur auch in X.
                woerter.append(laenge_offen)
                laenge_offen = ""
            weg = _weg(stand, parameter) if bewegung else 0.0
            davor = dict(stand)  # fortlaufend – für die Drehrichtung einer Moduloachse
            if bewegung:
                stand.update({a: float(parameter[a]) for a in WEG_ADRESSEN if a in parameter})
            if not s.rundachsen and bewegung and any(a in parameter for a in ROTATION):
                hinweis = tr(
                    "pp.hinweis.ohne_rundachsen", steuerung=s.name, operation=abschnitt.name
                )
                if hinweis not in hinweise:
                    hinweise.append(hinweis)
            for adresse in ADRESSEN:
                if adresse not in parameter:
                    continue
                wert = float(parameter[adresse])
                if adresse == "F" and bewegung and wert == 0.0:
                    # FreeCADs Bohren schreibt „G0 … F0“ – modal hielte F0 den G1 danach an; im
                    # Vorschub hieße F0 „steh“ (Mach3 und LinuxCNC lehnen es ab): das F davor gilt.
                    continue
                if gross in BOGEN and adresse == QUER_ZUR_EBENE[ebene] and abs(wert) < 1e-9:
                    continue
                if adresse == "F" and steigung is not None and s.gewinde_f_steigung:
                    woerter.append(_wort(s, "F", _zahl(abs(steigung), 4)))  # die Steigung
                    continue
                if adresse == "F":
                    wert *= 60.0 * faktor
                    if g93 and not s.g93:
                        # Ohne G93 (S5): F in mm/min so, dass die Zeit des Satzes stimmt – der Weg
                        # aus X, Y, Z und den Rundachsen in Grad (Spezifikation, Abschnitt 5).
                        if weg > 1e-9:
                            woerter.append(_wort(s, "F", _zahl(weg * wert)))
                        continue
                    woerter.append(_wort(s, "F", _zahl(wert, STELLEN_G93 if g93 else STELLEN)))
                    continue
                if adresse == "Y" and _ohne_y(info):
                    # Die Maschine hat diese Achse nicht (Y an der Drehmaschine): auf 0 weglassen –
                    # FreeCADs Bohren schreibt Y0 –, sonst stehen lassen (die Steuerung hält an)
                    # und sagen.
                    if abs(wert) < 1e-9:
                        continue
                    if f"ohne_{adresse}" not in gesehen:
                        gesehen.add(f"ohne_{adresse}")
                        hinweise.append(
                            tr(
                                "pp.hinweis.achse_fehlt",
                                maschine=info.name,
                                achse=adresse,
                                operation=abschnitt.name,
                            )
                        )
                if adresse == "X" and info.drehmaschine and info.x_durchmesser:
                    wert *= 2.0
                if adresse in info.modulo and s.rundachse_plus and s.rundachse_minus:
                    vorher = davor.get(adresse)
                    if (
                        vorher is not None
                        and abs(wert - vorher) < 180.0
                        and _modulo_zahl(wert, stellen) == _modulo_zahl(vorher, stellen)
                    ):
                        # Dieselbe Position: nicht schreiben. „ACP“ zur Stelle, an der die Achse
                        # schon steht, fährt nicht – aber ein Rundungsrest unter der letzten
                        # Stelle hieße sonst, gelesen wie eine Steuerung, eine ganze Umdrehung.
                        continue
                    woerter.append(
                        _modulo_wort(
                            s, _adresse(s, adresse, info), wert, davor.get(adresse), stellen
                        )
                    )
                    # Im Eilgang ist die Richtung gleich – im Vorschub (G93: die Zeit des Satzes)
                    # führe ACP/ACN weniger als die Bahn.
                    weit = davor.get(adresse) is not None and abs(wert - davor[adresse]) >= 359.999
                    if weit and gross not in ("G0", "G00") and "modulo_weit" not in gesehen:
                        gesehen.add("modulo_weit")
                        hinweise.append(tr("pp.hinweis.modulo_weit", achse=adresse))
                    continue
                if s.zahl_max and abs(wert) > s.zahl_max and "zahl_max" not in gesehen:
                    gesehen.add("zahl_max")
                    hinweise.append(
                        tr(
                            "pp.hinweis.zahl_zu_gross",
                            adresse=adresse,
                            wert=_zahl(wert, stellen),
                            steuerung=s.name,
                            max=_zahl(s.zahl_max, 3),
                        )
                    )
                woerter.append(_wort(s, _adresse(s, adresse, info), _zahl(wert, stellen)))
            zeile = " ".join(woerter)
            if gross in ("G0", "G00") and zeilen and zeilen[-1] == zeile:
                continue  # derselbe Eilgang noch einmal (absolut): nichts zu fahren
            zeilen.append(zeile)
            if bewegung:
                saetze += 1
                if vorschau is not None and saetze >= vorschau:
                    zeilen.append(_kommentar(s, tr("pp.vorschau_ende")))
                    return fertig(zeilen, saetze)
        if kuehlung:
            zeilen.append(s.kuehlung_aus)
    if spindel_an is not None:
        zeilen.extend(_spindel_aus(s, spindel_an))
    zurueck = None
    if s.schwenken_aus_zuerst and zyklus and geschwenkt is not None:
        zeilen.extend(_zeilen(s.schwenken_aus))  # Fanuc G69 vor G53
        zurueck, geschwenkt = geschwenkt, None
    if werkzeug is not None:
        zeilen.extend(_zum_wechselpunkt(s, info))
    if zurueck is not None:  # die Rundachsen oben auf 0
        oben = werkzeug is not None and _wechselpunkt_oben(s, info)
        zeilen.extend(_schwenken_aus(s, zurueck, False, oben, info))
    if geschwenkt is not None:
        oben = werkzeug is not None and _wechselpunkt_oben(s, info)
        zeilen.extend(_schwenken_aus(s, geschwenkt, zyklus, oben, info))
    if c_an and s.c_aus:
        zeilen.extend(_zeilen(_fuellen(s.c_aus, h=_haupt(info))))
    for zeile in _zeilen(s.ende):
        if not (zeilen and zeile == zeilen[-1]):  # „M5“ nach „M5“: schon aus
            zeilen.append(zeile)
    return fertig(zeilen, saetze)


def _klartext_fertig(s, name, datei, rohteil, hinweise, stellen=STELLEN):
    """Für Klartext: eine Funktion, die die Zeilen übersetzt (klartext.uebersetzen) und das
    Programm gibt – mit BEGIN/END PGM wie die Datei, BLK FORM aus dem Rohteil."""
    import os

    from . import klartext as kt
    from .sprache import aktuelle_sprache

    pgm = os.path.splitext(os.path.basename(datei))[0] if datei else name

    def fertig(zeilen, saetze):
        uebersetzt = kt.uebersetzen(
            zeilen,
            pgm,
            rohteil,
            aktuelle_sprache() == "de",
            stellen,
            s.bohrzyklen,
            s.gewinde_synchron,
        )
        for art, wert in uebersetzt.hinweise:
            if art == "schrauben":
                hinweise.append(tr("pp.hinweis.klartext_schrauben", anzahl=wert))
            else:
                hinweise.append(tr("pp.hinweis.klartext_unbekannt", saetze=" | ".join(wert)))
        return Programm(uebersetzt.zeilen, hinweise, saetze)

    return fertig


def _mpr_fertig(s, name, rohteil, hinweise):
    """Für woodWOP: eine Funktion, die die Zeilen übersetzt (mpr.uebersetzen) und das Programm
    gibt – das Werkstück aus dem Rohteil, der Maschinentyp aus der Steuerung."""
    from . import mpr

    typ = "WEEKE" if s.kennung == "woodwop_weeke" else "HOMAG"

    def fertig(zeilen, saetze):
        uebersetzt = mpr.uebersetzen(zeilen, name, rohteil, typ)
        for art, wert in uebersetzt.hinweise:
            if art == "vorschub":
                hinweise.append(tr("pp.hinweis.mpr_vorschub", anzahl=wert))
            elif art == "rundachsen":
                hinweise.append(tr("pp.hinweis.mpr_rundachsen"))
            elif art == "zerlegt":
                hinweise.append(tr("pp.hinweis.mpr_zerlegt", anzahl=wert))
            elif art == "ohne_rohteil":
                hinweise.append(tr("pp.hinweis.mpr_ohne_rohteil"))
            else:
                hinweise.append(tr("pp.hinweis.klartext_unbekannt", saetze=" | ".join(wert)))
        return Programm(uebersetzt.zeilen, hinweise, uebersetzt.saetze)

    return fertig


def _zyklus_als_befehl(
    s, vorlage, parameter, stand, auf_r, faktor=1.0, steigung=None, drehzahl=0.0, info=None
):
    """Ein Bohrzyklus (G81 ff.) als Befehl der Steuerung: über das Loch („G0 X… Y…“), der
    Vorschub, dann `vorlage` mit {rtp} {rfp} {dp} {fdep} {q} {dtb} {f} (Steuerung.bohren …),
    beim Gewindebohren dazu {pit} (`steigung`, links negativ), {s} (`drehzahl`) und {sdac}.
    `stand` folgt: X, Y des Lochs, Z die Rückzugsebene; `faktor`: der Vorschub so viel kleiner
    (die Drehzahl war über der Höchstdrehzahl)."""
    zeilen = []
    lage = [a for a in ("X", "Y") if a in parameter]
    if _ohne_y(info):  # Y0 an der Drehmaschine ohne Y: weg
        lage = [a for a in lage if a != "Y" or abs(float(parameter[a])) > 1e-9]
    durchmesser = info is not None and info.drehmaschine and info.x_durchmesser
    neu = [a for a in lage if stand.get(a) is None or abs(stand[a] - float(parameter[a])) > 1e-9]
    if neu:  # schon über dem Loch: kein Satz
        woerter = (
            _wort(s, a, _zahl(float(parameter[a]) * (2.0 if a == "X" and durchmesser else 1.0)))
            for a in lage
        )
        zeilen.append(" ".join(["G0", *woerter]))
    davor = stand.get("Z")
    tief = float(parameter.get("Z", davor if davor is not None else 0.0))
    r = float(parameter.get("R", davor if davor is not None else tief))
    rtp = r if auf_r or davor is None else max(davor, r)
    q = float(parameter.get("Q", 0.0))
    f = float(parameter.get("F", 0.0)) * 60.0 * faktor
    if f > 0:
        zeilen.append(_wort(s, "F", _zahl(f)))
    werte = {
        "rtp": rtp,
        "rfp": r,
        "dp": tief,
        "fdep": max(tief, r - q) if q > 0 else tief,
        "q": q,
        "dtb": float(parameter.get("P", 0.0)),
        "f": f,
        "pit": steigung or 0.0,
    }
    werte["pit_abs"] = abs(steigung or 0.0)
    werte = {k: _zahl(v) for k, v in werte.items()}
    werte["s"] = f"{drehzahl:.0f}"
    links = steigung is not None and steigung < 0
    werte["sdac"] = "4" if links else "3"
    werte["g"] = "G74" if links else "G84"
    zeilen.extend(_zeilen(_fuellen(vorlage, **werte)))
    stand.update({a: float(parameter[a]) for a in lage})
    stand["Z"] = rtp
    return zeilen


def _zyklus_ausgeschrieben(
    s, gross, parameter, stand, auf_r, faktor, stellen=STELLEN, info=None
):  # fmt: skip
    """Ein Bohrzyklus in G0/G1/G4 – für eine Steuerung ohne Zyklen (GRBL) und an der
    Drehmaschine: über das Loch, im Eilgang auf R, im Vorschub auf die Tiefe – G83 in
    Zustellungen Q mit Rückzug auf R, G73 mit Spanbruch, G82 mit Verweilen P, G85 heraus im
    Vorschub –, dann zurück auf die Höhe davor (G98) oder R (G99). Wie klartext._bohren. `stand`
    folgt; X an der Drehmaschine im Durchmesser, wenn die Maschine so zählt (`info`)."""
    durchmesser = info is not None and info.drehmaschine and info.x_durchmesser
    from . import klartext as kt

    zeilen = []

    def z(befehl, wert, f=None):
        satz = f"{befehl} {_wort(s, 'Z', _zahl(wert, stellen))}"
        zeilen.append(satz + (f" {_wort(s, 'F', _zahl(f))}" if f else ""))

    lage = [a for a in ("X", "Y") if a in parameter]
    if _ohne_y(info):  # Y0 an der Drehmaschine ohne Y: weg
        lage = [a for a in lage if a != "Y" or abs(float(parameter[a])) > 1e-9]
    if any(stand.get(a) is None or abs(stand[a] - float(parameter[a])) > 1e-9 for a in lage):
        woerter = (
            _wort(
                s,
                a,
                _zahl(float(parameter[a]) * (2.0 if a == "X" and durchmesser else 1.0), stellen),
            )
            for a in lage
        )
        zeilen.append(" ".join(["G0", *woerter]))
    davor = stand.get("Z")
    tief = float(parameter.get("Z", davor if davor is not None else 0.0))
    r = float(parameter.get("R", davor if davor is not None else tief))
    rueck = r if auf_r or davor is None else max(davor, r)
    f = float(parameter.get("F", 0.0)) * 60.0 * faktor
    z("G0", r)
    q = float(parameter.get("Q", 0.0))
    if gross in ("G83", "G73") and q > 1e-9:
        jetzt = r
        while jetzt - q > tief + 1e-9:
            jetzt -= q
            if gross == "G83" and jetzt + q < r - 1e-9:
                z("G0", jetzt + q + kt.PECK_LUFT)
            z("G1", jetzt, f)
            f = None  # modal
            z("G0", r if gross == "G83" else jetzt + kt.SPAN_BRECHEN)
        if gross == "G83" and jetzt < r - 1e-9:
            z("G0", jetzt + kt.PECK_LUFT)
    z("G1", tief, f)
    if gross == "G82" and float(parameter.get("P", 0.0)) > 0:
        zeilen.extend(
            _zeilen(_fuellen(s.verweilen or "G4 P{sek}", sek=_zahl(float(parameter["P"]))))
        )
    if gross == "G85":
        z("G1", r)
    z("G0", rueck)
    stand.update({a: float(parameter[a]) for a in lage})
    stand["Z"] = rueck
    return zeilen


def _schwenken_ein(s, schwenkung, info=None, umgekehrt=()):
    """Der Schwenkzyklus für die Ebene (Steuerung.schwenken). `umgekehrt`: die Rundachsen, die
    das Programm umgekehrt schreibt – zählt die Bezugsrundachse der Vorzugsrichtung so, ist der
    kleinere Wert an der Steuerung der größere."""
    (x0, y0, z0), (a, b, c) = sw.zyklus_winkel(schwenkung.ebene)
    _ursprung, (i, j, k) = sw.euler_zxz(schwenkung.ebene)
    werte = {"x0": x0, "y0": y0, "z0": z0, "a": a, "b": b, "c": c, "i": i, "j": j, "k": k}
    werte = {k: _zahl(v) for k, v in werte.items()}
    # D-1, D-2: der Schwenkdatensatz der Maschine und die Vorzugsrichtung, mit der die Steuerung
    # die geprüfte Stellung nimmt.
    werte["tc"] = info.schwenkdatensatz if info is not None else ""
    richtung = int(getattr(schwenkung, "richtung", -1) or -1)
    if getattr(schwenkung, "richtung_achse", "") in umgekehrt:
        richtung = -richtung
    werte["dir"] = str(richtung)
    werte["seq"] = "+" if richtung > 0 else "-"  # Heidenhain PLANE … SEQ
    return _zeilen(_fuellen(s.schwenken, **werte))


def _schwenken_aus(s, schwenkung, zyklus, oben=False, info=None, auf_null=True):
    """Zurück aus der Ebene: der Zyklus zurück – ohne Zyklus erst hoch genug
    (Schwenkung.hoehe; `oben`: die Maschine steht schon am Wechselpunkt ganz oben), dann die
    Rundachsen auf 0, mit ihren Namen an der Maschine (`info`: Siemens „C4=0.000“). Ein Zyklus,
    der sie nicht selbst zurückdreht (Siemens CYCLE800()), danach ebenso – mit `auf_null`: es
    geht ohne Ebene weiter."""
    if zyklus:
        zeilen = _zeilen(s.schwenken_aus)
        if auf_null and not s.schwenken_aus_dreht:
            zeilen.extend(_schwenken_aus(s, schwenkung, False, oben, info))
        return zeilen
    zeilen = []
    if schwenkung.hoehe is not None and not oben:
        zeilen.append(f"G0 {_wort(s, 'Z', _zahl(schwenkung.hoehe))}")
    woerter = [
        _wort(s, _adresse(s, b, info) if info is not None else b, _zahl(0.0))
        for b in sorted(schwenkung.rund)
    ]
    if woerter:
        zeilen.append(" ".join(["G0", *woerter]))
    return zeilen


# Die Ebene der Bögen: (u, v, Mitte u, Mitte v) so, dass u → v um die dritte Achse positiv dreht –
# G2 ist in jeder im Uhrzeigersinn (wie klartext._in_geraden).
_BOGENACHSEN = {
    "G17": ("X", "Y", "I", "J"),
    "G18": ("Z", "X", "K", "I"),
    "G19": ("Y", "Z", "J", "K"),
}


def _winziger_bogen(gross, parameter, stand, ebene, stellen=STELLEN, info=None):
    """Ist der Bogen so kurz, dass Anfang und Ende auf `stellen` gerundet gleich im Programm
    stünden – und ist er kein (fast) voller Kreis, sondern einer über wenige Tausendstel Grad?
    Dann eine Gerade (höchstens seine Bogenhöhe daneben, unter der letzten Stelle). Ein Bogen fast
    ganz herum bleibt: gerundet ist der Vollkreis ihm am nächsten."""
    u, v, iu, iv = _BOGENACHSEN.get(ebene, _BOGENACHSEN["G17"])
    if stand.get(u) is None or stand.get(v) is None or "R" in parameter:
        return False
    ende = {a: float(parameter.get(a, stand[a])) for a in (u, v)}
    faktor = {
        a: 2.0 if a == "X" and info is not None and info.x_durchmesser else 1.0 for a in (u, v)
    }
    if any(
        _zahl(ende[a] * faktor[a], stellen) != _zahl(stand[a] * faktor[a], stellen) for a in (u, v)
    ):
        return False
    if math.hypot(ende[u] - stand[u], ende[v] - stand[v]) < 1e-9:
        return False  # wirklich ein Vollkreis
    mu, mv = stand[u] + float(parameter.get(iu, 0.0)), stand[v] + float(parameter.get(iv, 0.0))
    a0 = math.atan2(stand[v] - mv, stand[u] - mu)
    d = math.atan2(ende[v] - mv, ende[u] - mu) - a0
    d = (d + math.pi) % (2 * math.pi) - math.pi
    uhrzeiger = gross in ("G2", "G02")
    return (d < 0) if uhrzeiger else (d > 0)


def _steht(stand, parameter):
    """Fährt der Satz nicht – nur F0, und jede Achse darin steht schon dort (`stand`)?"""
    if float(parameter.get("F", 1.0)) != 0.0:
        return False
    for adresse, wert in parameter.items():
        if adresse == "F":
            continue
        if adresse not in WEG_ADRESSEN or adresse not in stand:
            return False
        if abs(float(wert) - stand[adresse]) > 1e-9:
            return False
    return True


def _weg(stand, parameter):
    """Der Weg eines Satzes von `stand` aus: √(ΔX² + ΔY² + ΔZ² + ΔA² + ΔB² + ΔC²), die Rundachsen
    in Grad – so zählen Steuerungen ohne G93 den Vorschub; ein Bogen zählt als Sehne."""
    summe = 0.0
    for adresse in WEG_ADRESSEN:
        if adresse in parameter and adresse in stand:
            summe += (float(parameter[adresse]) - stand[adresse]) ** 2
    return summe**0.5


_MARKE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*:")
_NUR_NUMMER = re.compile(r"N\d+")
_PROGRAMMNUMMER = re.compile(r"O\d")


def _nummeriert(zeilen, s):
    """Mit Satznummern (N10, N20 …), wenn die Steuerung sie schreiben soll – nicht vor „%“, der
    Programmnummer (O…) und reinen Kommentaren."""
    if not s.satznummern:
        return zeilen
    # Die Marken der Bearbeitungen mit Nummer (Fanuc „N3“) – kein Satz bekommt ihre Nummer, sonst
    # fände die Suche nach N10 den falschen.
    marken = {int(z.strip()[1:]) for z in zeilen if _NUR_NUMMER.fullmatch(z.strip())}
    ergebnis, nummer = [], 0
    for zeile in zeilen:
        roh = zeile.strip()
        marke = _MARKE.fullmatch(roh) or _NUR_NUMMER.fullmatch(roh)
        if roh == "%" or _PROGRAMMNUMMER.match(roh) or roh.startswith(("(", ";")) or marke:
            ergebnis.append(zeile)
            continue
        nummer += SATZNUMMER_SCHRITT
        while nummer in marken or nummer > s.satznummer_max:
            nummer = (
                SATZNUMMER_SCHRITT if nummer > s.satznummer_max else nummer + SATZNUMMER_SCHRITT
            )
        ergebnis.append(f"N{nummer} {zeile}")
    return ergebnis


def _ohne_leerzeichen(zeilen, s):
    """Die Sätze ohne Leerzeichen zwischen den Wörtern (Haken `leerzeichen` aus) – Kommentare
    („(…)“, „;“) bleiben, wie sie sind."""
    if s.leerzeichen or not s.ohne_leerzeichen_moeglich:
        return zeilen
    ergebnis = []
    for zeile in zeilen:
        if zeile.startswith(("(", ";", "%")):
            ergebnis.append(zeile)
            continue
        satz, klammer, rest = zeile.partition("(")
        ergebnis.append(satz.replace(" ", "") + klammer + rest)
    return ergebnis


# Was ohne Arbeit ist: Eilgang, Kommentare, Ebene, Maße, Vorschubart, Zyklus aus, Rückzugsebene.
_OHNE_ARBEIT = {"G0", "G00", "G17", "G18", "G19", "G20", "G21", "G40", "G49", "G80", "G90", "G91",
                "G93", "G94", "G98", "G99"}  # fmt: skip


def _arbeitet(befehle):
    """Tut die Operation etwas – ein Satz im Vorschub, ein Bohrzyklus, Antasten, ein M-Befehl
    (der Halt des Messstopps, Kühlung …)? Nur Eilgänge und Kommentare: nein."""
    for befehl in befehle:
        name = befehl.Name if hasattr(befehl, "Name") else befehl[0]
        name = str(name).upper()
        if name.startswith("(") or name in _OHNE_ARBEIT:
            continue
        return True
    return False


def _ohne_y(info):
    """Eine Drehmaschine, deren Modell X und Z kennt, aber kein Y? Nur dann fällt „Y0“ weg –
    sonst (eine Fräse, ein Modell mit anders benannten Achsen) bleibt jede Adresse."""
    return bool(
        info is not None
        and info.drehmaschine
        and {"X", "Z"} <= set(info.linear)
        and "Y" not in info.linear
    )


def _zum_wechselpunkt(s, info):
    if not s.wechselpunkt:
        return []
    return _wechselpunkt_saetze(s, info)


def _wechselpunkt_oben(s, info):
    """Steht die Fräse nach _zum_wechselpunkt mit Z ganz oben – höher als jede Schwenkhöhe? Ja
    mit Z im Wechselpunkt in MKS (G53, SUPA: das Ende des Verfahrwegs) oder einem Befehl, der den
    Punkt selbst kennt (F_HOME); in WKS weiß es niemand."""
    if not s.wechselpunkt or info.drehmaschine:
        return False
    vorlage = s.wechselpunkt_wks if info.wechsel_wks else s.wechselpunkt_mks
    if not vorlage:
        return False
    if "{achsen}" not in vorlage:
        return bool(info.name)
    return not info.wechsel_wks and "Z" in info.wechselpunkt


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
    Am Schwenkkopf hängen die Punkte im Programm davon ab. Mit ihr schreiben Operationen mit
    Werkzeugachse je Satz (Kugelfräser angestellt, Flanke) ihre Rundachsen je Punkt (_simultan)."""
    from . import magazin as mg
    from . import werkzeuge as wz

    try:
        bibliothek = wz.Bibliothek.laden()
    except Exception:
        bibliothek = None
    # Das Magazin der Maschine des Jobs (W-002 Stufe H3): Name an der Steuerung, Rüstliste.
    datei = mg.maschine_von(job)
    magazin = mg.des_jobs(None, bibliothek, datei) if bibliothek is not None and datei else None
    revolver = magazin is not None and mg.mit_revolver(datei)
    if not mit_ebenen or sw.ist_ebene(job):
        return _abschnitte_des_jobs(job, maschine, bibliothek, magazin, revolver)
    ergebnis = []
    for teil in sw.aufspannung_der_reihe_nach(job):  # der Grundjob zuerst, an der G550 zuletzt
        ergebnis += _abschnitte_des_jobs(teil, maschine, bibliothek, magazin, revolver)
    return ergebnis


def _abschnitte_des_jobs(job, maschine, bibliothek, magazin=None, revolver=False):
    from . import job_schnittwerte as js
    from . import magazin as mg
    from . import maschinenzugang as mz
    from . import reichweite as rw
    from . import stirnseite as st
    from . import vierachs_operation as vo

    ergebnis = []
    merk = {}  # je Controller: Einspannung und Maße (_einspannung_und_knapp)
    geschwenkt = sw.ist_ebene(job)
    gerechnet = {}  # id(Maschine) → (Maschine, Schwenkung): je Werkzeug einmal
    # Die Nullpunkte des Jobs – eine Ebene liegt in derselben Aufspannung wie ihr Grundjob.
    nullpunkte = tuple(
        str(f).strip()
        for f in (getattr(rw.grundjob_von(job) or job, "Fixtures", None) or [])
        if str(f).strip()
    )
    for op in getattr(getattr(job, "Operations", None), "Group", []):
        if not getattr(op, "Active", True) or getattr(op, "Path", None) is None:
            continue
        schwenkung = None
        fuer_op = maschine(op) if callable(maschine) else maschine
        zugeordnet = bool(
            getattr(job, rw.EIGENSCHAFT_MASCHINE, "")
            or getattr(rw.grundjob_von(job), rw.EIGENSCHAFT_MASCHINE, "")
        )
        if fuer_op is None and maschine is None and zugeordnet:
            geladen = mz._maschine(job, op)
            fuer_op = geladen if geladen is not False else None
        if geschwenkt:
            if id(fuer_op) not in gerechnet:
                gerechnet[id(fuer_op)] = (fuer_op, sw.schwenkung_fuer(job, fuer_op))
            schwenkung = gerechnet[id(fuer_op)][1]
        befehle, hinweis = list(op.Path.Commands), ""
        if (
            fuer_op is None
            and (zugeordnet or maschine is not None)
            and any(set(c.Parameters) & set("XYZABC") for c in befehle)
        ):
            befehle = []
            hinweis = tr("pp.hinweis.simultan_ausgelassen", grund=tr("mz.fehler.zuordnung"))
        if geschwenkt and (fuer_op is None or schwenkung is None or schwenkung.abbildung is None):
            befehle = []
            hinweis = tr("pp.hinweis.ebene_ausgelassen", ebene=job.Flaeche or job.Label)
            schwenkung = None
        if geschwenkt and fuer_op is not None and schwenkung is not None and not schwenkung.rund:
            # Eine feste Spindel hat nur einen anders gerechneten CAM-Bezug, keinen
            # Schwenkzyklus. Alle örtlichen An-/Rückzüge in die echten XYZ-Koordinaten
            # bringen; weder Rundachsen noch einen zusätzlichen Z-Schwenkanlauf erfinden.
            befehle = sw.befehle_ohne_zyklus(befehle, schwenkung, schon_oben=True)
            schwenkung = None
        befehle_tcpm = None
        if not geschwenkt and so.ist_simultan(op):
            befehle, hinweis = _simultan(op, fuer_op)
            befehle_tcpm = _simultan_tcpm(op, fuer_op)
        if befehle and fuer_op is not None:
            try:
                if geschwenkt and schwenkung is not None:
                    gefahren = sw.befehle_ohne_zyklus(befehle, schwenkung, schon_oben=True)
                elif so.ist_simultan(op):
                    gefahren = befehle
                else:
                    gefahren = fuer_op.pruefung.befehle(
                        op, None, fuer_op.aufnahme, fuer_op.laenge, fuer_op.nullpunkt
                    )
                grund = mz.bahn_grund(fuer_op, gefahren, op.Label)
            except (ValueError, RuntimeError) as fehler:
                grund = str(fehler)
            if grund:
                befehle, schwenkung, befehle_tcpm = [], None, None
                hinweis = tr("pp.hinweis.simultan_ausgelassen", grund=grund)
        if not hinweis and not _arbeitet(befehle):
            # Nichts zu fräsen (ein „3D-Schruppen“ ohne Rest): kein Werkzeugwechsel dafür – nur
            # der Hinweis, damit man die leere Operation im Job findet.
            ergebnis.append(
                Abschnitt(op.Label, 0, 0.0, False, hinweis=tr("pp.hinweis.leer", name=op.Label))
            )
            continue
        tc = getattr(op, "ToolController", None)
        nummer = int(getattr(tc, "ToolNumber", 0) or 0) if tc is not None else 0
        drehzahl = float(getattr(tc, "SpindleSpeed", 0.0) or 0.0) if tc is not None else 0.0
        richtung = str(getattr(tc, "SpindleDir", "Forward")) if tc is not None else "Forward"
        werkzeug = getattr(tc, "Tool", None) if tc is not None else None
        name_steuerung, ruesten_art, ruesten = "", "", ""
        if magazin is not None and tc is not None and nummer:
            aus_verwaltung = js.werkzeug_von(tc, bibliothek)
            im = magazin.eintrag_von(aus_verwaltung) if aus_verwaltung is not None else None
            name_steuerung = im.name if im is not None else ""
            ruesten_art, ruesten = mg.ruesten(aus_verwaltung, magazin, nummer, revolver)
        drehsinn = getattr(op, "Drehsinn", None)
        rundachse = str(getattr(op, "Rundachse", "") or "")
        rundum = vo.ist_rundum(op) and drehsinn in (1, -1) and rundachse
        stirn = ()
        if not geschwenkt and st.ist_stirn(op, befehle):
            stirn = (st.modus(job), st.sicher_z(op))
        einspannung = _einspannung_und_knapp(job, op, tc, nummer, bibliothek, geschwenkt, merk)
        ergebnis.append(
            Abschnitt(
                op.Label,
                nummer,
                drehzahl if richtung != "None" else 0.0,
                richtung == "Reverse",
                str(getattr(op, "CoolantMode", "None")),
                befehle,
                getattr(werkzeug, "Label", "") if werkzeug is not None else "",
                schwenkung,
                hinweis,
                *einspannung[:2],
                ms.ist_messstopp(op),
                befehle_tcpm,
                name_steuerung,
                ruesten_art,
                ruesten,
                (rundachse, int(drehsinn)) if rundum else (),
                stirn,
                koordinatenstellen=6 if float(getattr(op, "BahnGrathoehe", 0.0)) > 0 else STELLEN,
                masse=einspannung[2],
                nullpunkte=nullpunkte,
            )
        )
    return ergebnis


SPIEL_KNAPP = 2.0  # mm – so viel muss der Fräser mehr herausstehen, als er tief fräst


def _einspannung_und_knapp(job, op, tc, nummer, bibliothek, geschwenkt, merk=None):
    """(Einspannung, Knapp, Maße) für den Kopf des Programms (D-4): „Schaftfräser Ø 12 –
    Auskragung 35 mm, Spannzangenfutter ER25“; wenn die Operation tiefer fräst, als der Fräser
    abzüglich SPIEL_KNAPP heraussteht, ein Satz dazu – nur ohne Rundachsen und Ebene (dann zählt
    die Tiefe nicht längs Z); die Maße für die Werkzeugliste (Abschnitt.masse). In `merk` ({}
    eines Laufs) je Controller gemerkt – viele Operationen teilen ein Werkzeug."""
    if tc is None or not nummer:
        return "", "", {}
    merk = {} if merk is None else merk
    schluessel = getattr(tc, "Name", "")
    if schluessel not in merk:
        merk[schluessel] = _einspannung_des_controllers(tc, bibliothek)
    name, einspannung, auskragung, masse = merk[schluessel]
    if not einspannung:
        return name, "", dict(masse)
    knapp = ""
    rohteil = getattr(getattr(job, "Stock", None), "Shape", None)
    befehle = list(getattr(getattr(op, "Path", None), "Commands", []) or [])
    rund = any(set(c.Parameters) & set(ROTATION) for c in befehle)
    if rohteil is not None and not rohteil.isNull() and not geschwenkt and not rund:
        zs = [
            float(c.Parameters["Z"])
            for c in befehle
            if c.Name.upper() in ("G1", "G01", "G2", "G02", "G3", "G03") and "Z" in c.Parameters
        ]
        if zs:
            tiefe = float(rohteil.BoundBox.ZMax) - min(zs)
            if tiefe > auskragung - SPIEL_KNAPP:
                knapp = tr(
                    "pp.kopf.knapp_satz",
                    t=nummer,
                    operation=op.Label,
                    tiefe=f"{tiefe:.1f}",
                    auskragung=f"{auskragung:.1f}",
                )
    return einspannung, knapp, dict(masse)


def _einspannung_des_controllers(tc, bibliothek):
    """(Name, Einspannung, Auskragung, Maße) des Werkzeugs am Controller – Einspannung leer, wenn
    es nicht aus der Werkzeugverwaltung kommt oder sich nicht lesen lässt (dann Name leer, in den
    Maßen nur der Ø von FreeCAD)."""
    from . import halter as hl
    from . import job_schnittwerte as js
    from . import reichweite as rw
    from . import wegkippen as wk
    from . import werkzeuge as wz

    try:
        d = float(getattr(tc.Tool, "Diameter", 0.0))
    except (TypeError, ValueError):
        d = 0.0
    nur_d = {"d": d} if d > 0 else {}
    try:
        halter, _schaft, auskragung = wk.einspannung(tc, bibliothek)
    except Exception:
        return "", "", 0.0, nur_d
    werkzeug = js.werkzeug_von(tc, bibliothek) if bibliothek is not None else None
    name = wz.anzeigename(werkzeug) if werkzeug is not None else getattr(tc.Tool, "Label", "")
    if werkzeug is None or auskragung <= 0:
        # Nicht aus der Werkzeugverwaltung: Länge und Halter wären geraten – nur der Ø.
        return name, "", 0.0, nur_d
    halter_text = halter.name or halter.bezeichnung
    if hl.ist_vorschlag(halter):
        halter_text = tr("pp.kopf.halter_vorschlag", halter=halter_text)
    einspannung = tr(
        "pp.kopf.einspannung", werkzeug=name, auskragung=f"{auskragung:.0f}", halter=halter_text
    )
    nase, quelle = rw.werkzeuglaenge(tc, bibliothek)
    masse = {
        "name": name,
        "d": float(werkzeug.durchmesser or 0.0),
        "auskragung": float(auskragung),
        "nase": float(nase),
        "halter": halter_text,
        "geschaetzt": quelle not in (rw.LAENGE_SPINDELNASE, rw.LAENGE_AUSSPANN),
    }
    return name, einspannung, float(auskragung), masse


def _simultan(op, maschine):
    """(Befehle, Hinweis): echte Richtungen oder ausdrücklich unbearbeitet ausgelassen."""
    fuer_op = maschine(op) if callable(maschine) else maschine
    if fuer_op is None:
        return [], tr("pp.hinweis.simultan_ohne_maschine")
    try:
        programm = so.programm(op, fuer_op)
        return programm.befehle, programm.hinweis
    except ValueError as grund:
        return [], tr("pp.hinweis.simultan_ausgelassen", grund=str(grund))


def _simultan_tcpm(op, maschine):
    """Eine Funktion ohne Argumente, die die Sätze der Operation für eine Steuerung mit TCPM gibt
    (simultan_operation.befehle mit tcpm) – None ohne Maschine mit zwei Rundachsen."""
    fuer_op = maschine(op) if callable(maschine) else maschine
    if fuer_op is None or not getattr(fuer_op, "rundachsen", ()):
        return None
    return lambda bei_null=False: so.befehle(op, fuer_op, tcpm=True, bei_null=bei_null)


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
        info.schwenkdatensatz = m.schwenkdatensatz(maschine)
        try:
            from . import schruppwerte as srw

            info.drehzahl_max = float(srw.grenzen_der_maschine(maschine)[0])
        except Exception:
            info.drehzahl_max = 0.0
        spindeln = m.spindeln(maschine)
        info.hauptspindel = m.nc_nummer(spindeln.haupt)
        if spindeln.haupt is not None:
            info.hauptspindel_name = spindeln.haupt.NcName.strip()
        # Die C-Achse der Hauptspindel zuerst: Sie dreht das Teil. Die C-Achse eines
        # Werkzeugantriebs richtet nur das Werkzeug aus – nie die Rundachse der Bahn.
        info.linear = {
            m.programmname(ba).upper()[:1]
            for ba in m.betriebsarten(maschine)
            if ba.Art == m.ART_LINEAR and m.programmname(ba)
        }
        positionieren = [ba for ba in m.betriebsarten(maschine) if ba.Art == m.ART_POSITIONIEREN]
        if spindeln.haupt_c is not None:
            positionieren.sort(key=lambda ba: ba is not spindeln.haupt_c)
        for ba in positionieren:
            buchstabe = m.programmname(ba).upper()
            if buchstabe in ROTATION and not spindeln.ist_antrieb_c(ba):
                if buchstabe not in info.rundachsen and (
                    getattr(ba, "Endlos", False) or ba is spindeln.haupt_c
                ):
                    info.modulo.add(buchstabe)  # endlos: an der Steuerung eine Moduloachse
                info.rundachsen.setdefault(buchstabe, ba.NcName.strip() or buchstabe)
                info.nach_din.setdefault(buchstabe, bool(getattr(ba, "NachDin", True)))
        try:
            from . import reichweite as rw
            from . import stirnseite as st

            pruefung = rw.Pruefung(objekt, maschine)
            info.stirn = st.rahmen(pruefung, pruefung.werkzeugaufnahme(1), 100.0)
        except Exception:
            info.stirn = None
        try:
            from . import kette as kette_modul
            from . import verfahren as vf

            kette = kette_modul.lies_kette(objekt)
            for achse in kette.achsen:
                ba = vf._positionieren(achse.gelenk)
                if ba is None or spindeln.ist_antrieb_c(ba):
                    continue
                buchstabe = m.programmname(ba).upper()[:1]
                if buchstabe in ROTATION and vf.im_programm_umgekehrt(achse, kette):
                    info.umgekehrt.add(buchstabe)
        except Exception:
            info.umgekehrt = set()
        for spindel, c in spindeln.antriebe:
            if c is not None and m.nc_nummer(spindel):
                info.antrieb_c[m.nc_nummer(spindel)] = c.NcName.strip()

        def hochlauf(ba):
            return max(0.0, float(getattr(ba, "Hochlaufzeit", 0.0) or 0.0)) if ba else 0.0

        # An der Fräse treibt die Spindel mit der Werkzeugaufnahme das Werkzeug („haupt“ im
        # Programm), an der Drehmaschine die Hauptspindel das Teil, die Antriebe die Werkzeuge.
        if info.drehmaschine:
            info.hochlauf["haupt"] = hochlauf(spindeln.haupt)
        else:
            werkzeugspindeln = [s for s, _c in spindeln.antriebe] or [spindeln.haupt]
            info.hochlauf["haupt"] = max(hochlauf(s) for s in werkzeugspindeln)
        for spindel, _c in spindeln.antriebe:
            if m.nc_nummer(spindel):
                info.hochlauf[m.nc_nummer(spindel)] = hochlauf(spindel)
        for aufnahme in m.aufnahmen(maschine):
            spindel = getattr(aufnahme, "Spindel", None)
            if aufnahme.Art != m.AUFNAHME_WERKZEUG or spindel is None:
                continue
            nummer = re.sub(r"\D", "", getattr(spindel, "NcName", "") or "")
            if nummer and aufnahme.Platz:
                info.angetrieben[int(aufnahme.Platz)] = nummer
        return info
    return Maschineninfo()


NACHGELESEN_HOECHSTENS = 6  # so viele Befunde nennt nachgelesen() einzeln
# Bytes – größer passt ein Programm an Siemens und Fanuc oft nicht in den NC-Speicher (840D sl,
# 828D: wenige MB; Fanuc 0i: 0,5–2 MB): dann von extern abarbeiten bzw. per DNC.
GROSS = 2_000_000
GROSS_STEUERUNGEN = ("siemens", "fanuc")


def groesse_text(programm, s):
    """„… 3,4 MB“ für die Meldung nach dem Speichern – und bei Siemens und Fanuc über GROSS der
    Hinweis, es von extern abzuarbeiten; leer bei kleinen Programmen."""
    groesse = len(programm.text.encode("utf-8"))
    if groesse <= GROSS or s.kennung not in GROSS_STEUERUNGEN:
        return ""
    from . import einheiten

    mb = f"{groesse / 1e6:.1f}".replace(".", einheiten.gewaehltes_dezimalzeichen() or ".")
    if s.kennung == "siemens":
        return tr("pp.gross.siemens", mb=mb)
    return tr("pp.gross.fanuc", mb=mb)


def nachlesen(programm, s, info=None):
    """Das fertige Programm (Programm) wie die Steuerung `s` es läse nachgelesen
    (programm_pruefen): (Befunde, Bewegungssätze)."""
    from . import programm_pruefen as prp

    if s.dialekt == "klartext":
        from . import klartext as kt

        pruefung = kt.pruefe(programm.text)
        return pruefung.befunde, pruefung.saetze
    if s.dialekt == "mpr":
        from . import mpr

        pruefung = mpr.pruefe(programm.text)
        return pruefung.befunde, pruefung.saetze
    info = info or Maschineninfo()
    laenge = s.laenge_ein_drehen if info.drehmaschine else s.laenge_ein
    pruefung = prp.pruefe(
        programm.text,
        siemens=s.kennung == "siemens",
        drehmaschine=info.drehmaschine,
        laenge_mit_wechsel=not laenge,
        nur_ascii=s.nur_ascii,
    )
    return pruefung.befunde, pruefung.saetze


def nachgelesen_text(befunde, saetze):
    """Ein Satz fürs Fenster: „Nachgelesen: nichts gefunden …“ oder die Befunde mit Zeile."""
    if not befunde:
        return tr("pp.nachgelesen.gut", saetze=saetze)
    zeilen = [tr("pp.nachgelesen.befunde", anzahl=len(befunde))]
    for befund in befunde[:NACHGELESEN_HOECHSTENS]:
        zeilen.append(_befund_text(befund.art, befund.zeile, befund.satz.strip()))
    if len(befunde) > NACHGELESEN_HOECHSTENS:
        zeilen.append(tr("pp.nachgelesen.mehr", anzahl=len(befunde) - NACHGELESEN_HOECHSTENS))
    return "\n".join(zeilen)


def _befund_text(art, zeile, satz):
    """Ein Befund (programm_pruefen) als Satz – die Schlüssel wörtlich für die Sprachprüfung."""
    return {
        "laenge": lambda: tr("pp.befund.laenge", zeile=zeile, satz=satz),
        "spindel": lambda: tr("pp.befund.spindel", zeile=zeile, satz=satz),
        "vorschub": lambda: tr("pp.befund.vorschub", zeile=zeile, satz=satz),
        "kreis": lambda: tr("pp.befund.kreis", zeile=zeile, satz=satz),
        "doppelt": lambda: tr("pp.befund.doppelt", zeile=zeile, satz=satz),
        "ende": lambda: tr("pp.befund.ende"),
        "zeichen": lambda: tr("pp.befund.zeichen", zeile=zeile, satz=satz),
        "nummer": lambda: tr("pp.befund.nummer", zeile=zeile, satz=satz),
    }[art]()


def dateiname(job, s):
    """Der Vorschlag für die Programmdatei: neben dem Dokument, der Name des Jobs, die Endung
    der Steuerung."""
    import os

    ordner = os.path.dirname(getattr(job.Document, "FileName", "") or "") or os.path.expanduser("~")
    name = re.sub(r"[^\w\-]+", "_", job.Label).strip("_") or "programm"
    if s.dialekt == "klartext":  # der Name steht im BEGIN/END PGM – nur Buchstaben, Ziffern, „_“
        from . import klartext as kt

        name = kt.pgm_name(job.Label)
    return os.path.join(ordner, name + s.endung)


def markenname(name, vergeben):
    """Der Name der Sprungmarke für die Bearbeitung `name`: groß, nur Buchstaben, Ziffern und
    „_“ (Umlaute ausgeschrieben), mit zwei Buchstaben vorn, höchstens 32 Zeichen, nicht schon in
    `vergeben` (dann mit „_2“ …). Trägt ihn in `vergeben` ein."""
    text = str(name or "").upper()
    for alt, neu in (("Ä", "AE"), ("Ö", "OE"), ("Ü", "UE"), ("ß", "SS")):
        text = text.replace(alt, neu)
    text = re.sub(r"[^A-Z0-9]+", "_", text).strip("_") or "BEARBEITUNG"
    if not re.match(r"[A-Z]{2}", text):
        text = "OP_" + text
    text = text[:MARKE_LAENGE]
    kandidat, nummer = text, 2
    while kandidat in vergeben:
        zusatz = f"_{nummer}"
        kandidat = text[: MARKE_LAENGE - len(zusatz)] + zusatz
        nummer += 1
    vergeben.add(kandidat)
    return kandidat


def _ruest_hinweise(abschnitte):
    """Die Sätze im Fenster, wenn das Magazin der Maschine etwas anderes sagt als der Job
    (W-002 Stufe H3): ein Werkzeug mit anderer Nummer (das Programm riefe ein anderes), eins,
    das an der Steuerung fehlt, eins, das einzusetzen ist – je Art ein Satz mit den Nummern."""
    from . import magazin as mg

    je_art = {}
    for abschnitt in abschnitte:
        if abschnitt.ruesten_art and abschnitt.werkzeug:
            nummern = je_art.setdefault(abschnitt.ruesten_art, [])
            if abschnitt.werkzeug not in nummern:
                nummern.append(abschnitt.werkzeug)

    def nummern(art):
        return ", ".join(f"T{n}" for n in je_art.get(art, []))

    saetze = []
    if nummern(mg.UMNUMMERIEREN):
        saetze.append(tr("pp.hinweis.umnummerieren", werkzeuge=nummern(mg.UMNUMMERIEREN)))
    if nummern(mg.ANLEGEN):
        saetze.append(tr("pp.hinweis.anlegen", werkzeuge=nummern(mg.ANLEGEN)))
    if nummern(mg.EINSETZEN):
        saetze.append(tr("pp.hinweis.einsetzen", werkzeuge=nummern(mg.EINSETZEN)))
    return saetze


MARKE_ANFANG = "ANFANG"  # die Marke am Programmanfang – zurück an den Anfang (Manuel, 2026-10-25)
NAMEN_JE_ZEILE = 4  # so viele Bearbeitungen je Kommentarzeile „für:“ in der Werkzeugliste


def _suchtext(s, marke, n):
    """Wonach man im Programm sucht, um an die Bearbeitung mit der Marke `marke` zu kommen: der
    Name – als Marke (Siemens „RAEUMEN_T1:“, Heidenhain „* - RAEUMEN_T1“) oder als Kommentar
    (Steuerungen ohne Marken) –, mit Nummer (Fanuc, Haas „N3“) „N3 = RAEUMEN_T1“."""
    if s.marke and "{n}" in s.marke:
        return f"{_fuellen(s.marke, marke=marke, n=n).strip()} = {marke}"
    return marke


def _mm(wert):
    """„27“, „27.5“ – Maße im Kopf ohne Nullen am Ende."""
    return f"{float(wert):.1f}".rstrip("0").rstrip(".")


def _kopfzeilen(s, abschnitte, marken):
    """Der Kopf des Programms (D-4, als Kommentare; Manuel, 2026-10-25: „werkzeugliste am anfang
    mit ausspannlängen, durchmesser, und länge von spindelnase … welches werkzeug für welche
    bearbeitung … die sprung namen damit man danach suchen kann … auch am anfang ein Anfang
    sprungpunkt“): die Sprungmarken mit ihrer Bearbeitung und ihrem Werkzeug, vorn ANFANG; je
    Werkzeug sein Name, Ø, Auskragung, Länge ab Spindelnase und Halter, und für welche
    Bearbeitungen (ihre Marken); wo es knapp wird."""
    zeilen = []
    register = next((a.nullpunkte[0] for a in abschnitte if a.nullpunkte), "")
    if s.nullpunkt_setzen and register:
        # Der Befehl in einer Zeile, ohne Fortsetzung und Kommentar (Zyklus 247: „… Q339=+5“).
        befehl = " ".join(
            z.split(" ;")[0].replace(" ~", "").strip() for z in nullpunkt_befehl(s, register)
        )
        if befehl and befehl != register:
            text = tr("pp.kopf.nullpunkt_befehl", register=register, befehl=befehl)
        else:
            text = tr("pp.kopf.nullpunkt", register=register)
        zeilen.append(_kommentar(s, text))
    if marken:
        zeilen.append(_kommentar(s, tr("pp.kopf.marken")))
        zeilen.append(_kommentar(s, f"  {MARKE_ANFANG} – {tr('pp.kopf.anfang')}"))
        for n, (marke, abschnitt) in enumerate(zip(marken, abschnitte, strict=True), start=1):
            mit = f" – T{abschnitt.werkzeug}" if abschnitt.werkzeug else ""
            zeilen.append(_kommentar(s, f"  {_suchtext(s, marke, n)} – {abschnitt.name}{mit}"))
    je_werkzeug = {}
    for i, abschnitt in enumerate(abschnitte):
        if abschnitt.werkzeug and s.werkzeugliste:
            je_werkzeug.setdefault(abschnitt.werkzeug, []).append(i)
    if je_werkzeug:
        zeilen.append(_kommentar(s, tr("pp.kopf.werkzeuge")))
        for nummer, stellen in je_werkzeug.items():
            abschnitt = abschnitte[stellen[0]]
            masse = abschnitt.masse or {}
            text = masse.get("name") or abschnitt.einspannung or abschnitt.werkzeugname
            if abschnitt.name_steuerung:
                text = f'"{abschnitt.name_steuerung}" {text}'
            if abschnitt.ruesten:  # die Rüstliste (W-002 Stufe H3)
                text = f"{text} – {abschnitt.ruesten}"
            zeilen.append(_kommentar(s, f"  T{nummer} {text}".rstrip()))
            teile = []
            ca = tr("pp.kopf.ca") if masse.get("geschaetzt") else ""
            if masse.get("d"):
                teile.append(f"Ø {_mm(masse['d'])} mm")
            if masse.get("auskragung"):
                teile.append(tr("pp.kopf.auskragung", ca=ca, mm=_mm(masse["auskragung"])))
            if masse.get("nase"):
                teile.append(tr("pp.kopf.nase", ca=ca, mm=_mm(masse["nase"])))
            if masse.get("halter"):
                teile.append(masse["halter"])
            if ca:
                teile.append(tr("pp.kopf.geschaetzt"))
            if teile:
                zeilen.append(_kommentar(s, "     " + " · ".join(teile)))
            namen = [marken[i] if marken else abschnitte[i].name for i in stellen]
            for k in range(0, len(namen), NAMEN_JE_ZEILE):
                teil = ", ".join(namen[k : k + NAMEN_JE_ZEILE])
                zeilen.append(_kommentar(s, "     " + tr("pp.kopf.fuer", bearbeitungen=teil)))
    for abschnitt in abschnitte:
        if abschnitt.knapp:
            zeilen.append(_kommentar(s, tr("pp.kopf.knapp", text=abschnitt.knapp)))
    return zeilen
