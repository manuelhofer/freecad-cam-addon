# SPDX-License-Identifier: LGPL-2.1-or-later
# Der Postprozessor des Addons (W-005, P-2026-10-03-10): Musterausgaben aus Abschnitten – eine
# Fräse mit LinuxCNC, eine Drehmaschine mit C-Achse und angetriebenem Werkzeug für Siemens,
# Haas und Fanuc – und ein echter 4-Achs-Job (Rundum schruppen) durch abschnitte(). Wie Manuels
# Drehmaschine (P-2026-10-03-25): die Hauptspindel S4/C4, die angetriebenen Werkzeuge S1/C1 –
# C4 positioniert („SPOS[4]=0“, „C4=…“), S1 dreht („M1=3 S1=…“); die Beispielmaschine mit diesen
# Nummern gibt genau das an den Postprozessor, ihre C1 ist nie die Rundachse der Bahn.
# Ausführen: freecadcmd tests/test_postprozessor.py

import dataclasses
import os
import pathlib
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part
import Path
from Path.Tool.camassets import user_asset_store

from camaddon import beispielmaschine as bm
from camaddon import job_schnittwerte as js
from camaddon import postprozessor as pp
from camaddon import sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import vierachs_achsen as va
from camaddon import vierachs_operation as vo
from camaddon import vierachs_rohteil as vr
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


sprache.setze_sprache("de")
V = FreeCAD.Vector
C = Path.Command

# --- Fräse, LinuxCNC: Kopf, Werkzeug, Spindel, Kühlung, F mal 60, Ende -----------------------
tasche = pp.Abschnitt(
    "Tasche",
    3,
    2000.0,
    False,
    "Flood",
    [
        C("(Tasche)"),
        C("G0", {"X": 10.0, "Y": 5.0, "Z": 5.0}),
        C("G1", {"Z": -2.0, "F": 5.0}),  # FreeCAD: mm/s – im Programm mm/min
        C("G2", {"X": 20.0, "Y": 5.0, "I": 5.0, "J": 0.0, "F": 10.0}),
    ],
    "Fräser Ø 12",
)
prog = pp.programm([tasche], pp.steuerung("linuxcnc"), pp.Maschineninfo("Fräse"), "Platte")
z = prog.zeilen
pruefe(z[:3] == ["%", "(Platte)", "G17 G21 G40 G49 G80 G90"], f"Kopf: {z[:3]}")
pruefe("T3 M6" in z and "M3 S2000" in z and "M8" in z, f"Wechsel/Spindel/Kühlung: {z[3:10]}")
pruefe("G1 Z-2.000 F300.000" in z, f"F mal 60: {[x for x in z if x.startswith('G1')]}")
pruefe("G2 X20.000 Y5.000 I5.000 J0.000 F600.000" in z, "Bogen")
pruefe(z[-4:] == ["M5", "M9", "M30", "%"], f"Ende: {z[-4:]}")
pruefe(prog.saetze == 3 and not prog.hinweise, f"Sätze {prog.saetze}, Hinweise {prog.hinweise}")
ohne = pp.programm([tasche], pp.steuerung("linuxcnc"), None, "Platte")
pruefe(ohne.hinweise and "Ohne Maschine" in ohne.hinweise[0], f"ohne Maschine: {ohne.hinweise}")
# Die Werkzeuglänge (P-2026-10-04-51): Der Kopf hebt sie mit G49 auf – nach dem Wechsel schaltet
# der erste Satz mit Z sie ein, an LinuxCNC, Fanuc, Haas und Mach mit G43 H; Siemens nimmt D1
# mit dem Wechsel. Ohne sie stünde die Spitze um die Werkzeuglänge tiefer.
pruefe("G0 G43 H3 X10.000 Y5.000 Z5.000" in z, f"LinuxCNC ohne G43: {z[3:12]}")
for kennung in ("fanuc", "haas", "mach"):
    zeilen_k = pp.programm([tasche], pp.steuerung(kennung), pp.Maschineninfo("Fräse"), "P").zeilen
    mit_z = [x for x in zeilen_k if x.startswith(("G0 ", "G1 ")) and " Z" in x]
    pruefe(
        mit_z and "G43 H3" in mit_z[0] and sum("G43" in x for x in zeilen_k) == 1,
        f"{kennung}: G43 {[x for x in zeilen_k if 'G43' in x]}",
    )
siemens_t = pp.programm([tasche], pp.steuerung("siemens"), pp.Maschineninfo("Fräse"), "P").zeilen
pruefe(not any("G43" in x for x in siemens_t), "Siemens mit G43")
# Erst X und Y, dann Z: G43 kommt in den Satz mit Z; zwei Werkzeuge: je Wechsel einmal.
xy_zuerst = dataclasses.replace(
    tasche,
    befehle=[C("G0", {"X": 10.0, "Y": 5.0}), C("G0", {"Z": 5.0}), C("G1", {"Z": -2.0, "F": 5.0})],
)
zwei = pp.programm(
    [xy_zuerst, dataclasses.replace(xy_zuerst, name="Zwei", werkzeug=4)],
    pp.steuerung("linuxcnc"),
    pp.Maschineninfo("Fräse"),
    "P",
).zeilen
pruefe(
    [x for x in zwei if "G43" in x] == ["G0 G43 H3 Z5.000", "G0 G43 H4 Z5.000"]
    and "G0 X10.000 Y5.000" in zwei,
    f"zwei Werkzeuge: {[x for x in zwei if 'G43' in x or 'M6' in x]}",
)

# --- Drehmaschine mit C4 und angetriebenem T1 an S3 -------------------------------------------
dreh = pp.Maschineninfo("Drehmaschine", True, True, {"C": "C4"}, {1: "3"})
rundum = pp.Abschnitt(
    "Rundum schruppen T1",
    1,
    3000.0,
    False,
    "None",
    [
        C("G0", {"X": 42.0, "Z": 3.0, "C": 0.0}),
        C("G93"),
        C("G1", {"X": 38.0, "Z": 0.0, "C": 90.0, "F": 0.05}),
        C("G94"),
        C("G0", {"X": 42.0}),
    ],
)
siemens = pp.programm([rundum], pp.steuerung("siemens"), dreh, "Welle").zeilen
pruefe(siemens[0] == "; Welle" and "G18" in siemens, f"Siemens Kopf: {siemens[:4]}")
pruefe("T1 D1" in siemens, f"Siemens Wechsel: {siemens}")
# Ohne bekannte Hauptspindel: Spindel 1.
pruefe("SPOS[1]=0" in siemens and "M3=3 S3=3000" in siemens, f"Siemens C/Antrieb: {siemens}")
pruefe("G1 X76.000 Z0.000 C4=90.000 F3.00000" in siemens, f"Siemens Satz: {siemens}")
pruefe(siemens.index("SPOS[1]=0") < siemens.index("G0 X84.000 Z3.000 C4=0.000"), "C vor der Bahn")
pruefe(
    "M3=5" in siemens
    and "SPCOF(1)" in siemens
    and siemens.index("M3=5") < siemens.index("SPCOF(1)"),
    f"Siemens aus: {siemens[-6:]}",
)
# Wie Manuels Maschine: Hauptspindel 4, angetrieben an S1.
manuel = pp.Maschineninfo("Drehmaschine", True, True, {"C": "C4"}, {1: "1"}, hauptspindel="4")
siemens_4 = pp.programm([rundum], pp.steuerung("siemens"), manuel, "Welle").zeilen
pruefe(
    siemens_4.index("SPOS[4]=0") < siemens_4.index("M1=3 S1=3000")
    and "G1 X76.000 Z0.000 C4=90.000 F3.00000" in siemens_4
    and siemens_4.index("M1=5") < siemens_4.index("SPCOF(4)"),
    f"Siemens S4/C4 und S1: {siemens_4}",
)
# Eine Rundum-Bahn trägt −Drehsinn · φ – so zeigt FreeCAD sie. Nach DIN 66217 dreht +C das
# Werkstück andersherum (Manuel, 2026-10-05: Futter von vorn im Uhrzeigersinn; „das Einzige, was
# du anpassen musst, ist der Postprozessor“): Mit Drehsinn +1 schreibt das Programm C umgedreht,
# mit −1 wie die Bahn; ohne den Haken „dreht nach DIN 66217“ wie die Bahn.
mit_drehsinn = dataclasses.replace(rundum, drehsinn=("C", 1))
din = pp.programm([mit_drehsinn], pp.steuerung("siemens"), manuel, "Welle").zeilen
pruefe("G1 X76.000 Z0.000 C4=-90.000 F3.00000" in din, f"nach DIN nicht umgedreht: {din}")
gegen = dataclasses.replace(rundum, drehsinn=("C", -1))
din = pp.programm([gegen], pp.steuerung("siemens"), manuel, "Welle").zeilen
pruefe("G1 X76.000 Z0.000 C4=90.000 F3.00000" in din, f"Drehsinn −1 umgedreht: {din}")
ohne_din = dataclasses.replace(manuel, nach_din={"C": False})
wie_bahn = pp.programm([mit_drehsinn], pp.steuerung("siemens"), ohne_din, "Welle").zeilen
pruefe("G1 X76.000 Z0.000 C4=90.000 F3.00000" in wie_bahn, f"ohne DIN umgedreht: {wie_bahn}")
# Eine endlos drehende C-Achse ist an der Siemens eine Moduloachse (Manuel, 2026-10-05: „Fehler
# 16830 … falsche Position bei Achse/Spindel C4 programmiert“): die Position im Bereich 0 … unter
# 360°, die Richtung der Bahn mit ACP/ACN – nie −90 oder −450. Ohne Moduloachse und an LinuxCNC
# bleibt der Winkel fortlaufend.
spirale = pp.Abschnitt(
    "Rundum schruppen T1",
    1,
    3000.0,
    False,
    "None",
    [
        C("G0", {"X": 42.0, "Z": 3.0, "C": 0.0}),
        C("G93"),
        C("G1", {"X": 38.0, "Z": 0.0, "C": -90.0, "F": 0.05}),
        C("G1", {"Z": -1.0, "C": -180.0, "F": 0.05}),
        C("G1", {"Z": -2.0, "C": -270.0, "F": 0.05}),
        C("G1", {"Z": -3.0, "C": -360.0, "F": 0.05}),
        C("G1", {"Z": -4.0, "C": -450.0, "F": 0.05}),
        C("G1", {"Z": -5.0, "C": -360.0, "F": 0.05}),
        C("G94"),
        C("G0", {"X": 42.0}),
    ],
)
modulo = dataclasses.replace(manuel, modulo={"C"})
negativer_anfang = dataclasses.replace(spirale, befehle=[C("G0", {"C": -90.0})])
anfang_programm = pp.programm([negativer_anfang], pp.steuerung("siemens"), modulo, "Anfang")
pruefe(
    any("C4=ACN(270.000)" in z for z in anfang_programm.zeilen),
    "Erste negative Rundstellung fährt von Null eine unnötige positive Umdrehung",
)
mit_modulo = pp.programm([spirale], pp.steuerung("siemens"), modulo, "Welle")
c_woerter = [w for z in mit_modulo.zeilen for w in z.split() if w.startswith("C4=")]
pruefe(
    c_woerter
    == [
        "C4=ACP(0.000)",
        "C4=ACN(270.000)",
        "C4=ACN(180.000)",
        "C4=ACN(90.000)",
        "C4=ACN(0.000)",
        "C4=ACN(270.000)",
        "C4=ACP(0.000)",
    ],
    f"Siemens Moduloachse: {c_woerter}",
)
befunde, _saetze = pp.nachlesen(mit_modulo, pp.steuerung("siemens"), modulo)
pruefe(not befunde, f"Moduloachse nachgelesen: {[(b.art, b.satz) for b in befunde]}")
ohne_modulo = pp.programm([spirale], pp.steuerung("siemens"), manuel, "Welle").zeilen
pruefe(any("C4=-450.000" in z for z in ohne_modulo), "ohne Moduloachse nicht fortlaufend")
lcnc_modulo = pp.programm([spirale], pp.steuerung("linuxcnc"), modulo, "Welle").zeilen
pruefe(any("C-450.000" in z for z in lcnc_modulo), "LinuxCNC nicht fortlaufend")
weit = dataclasses.replace(
    spirale,
    befehle=[C("G0", {"X": 42.0, "Z": 3.0, "C": 0.0}), C("G1", {"C": -400.0, "F": 0.05})],
)
pruefe(
    any("Umdrehung" in h for h in pp.programm([weit], pp.steuerung("siemens"), modulo).hinweise),
    "kein Hinweis bei einer ganzen Umdrehung in einem Satz",
)
eilgang = dataclasses.replace(spirale, befehle=[C("G0", {"C": 0.0}), C("G0", {"C": -4000.0})])
pruefe(
    not any(
        "Umdrehung" in h for h in pp.programm([eilgang], pp.steuerung("siemens"), modulo).hinweise
    ),
    "Hinweis bei einem Eilgang (dort ist die Richtung gleich)",
)
# Das Rohteil für die Simulation (Manuel, 2026-10-05: „WORKPIECE muss doch mit rein!“): an der
# Fräse ein Quader, an der Drehmaschine die Stange – aus dem Rohteil des Jobs; Haken aus oder eine
# andere Steuerung: keins; an der Fräse mit Bahnen um eine Rundachse auch keins.
quader = ((-30.0, -20.0, 0.0), (30.0, 20.0, 25.0))
mit_rohteil = pp.programm([tasche], pp.steuerung("siemens"), rohteil=quader).zeilen
pruefe(
    'WORKPIECE(,"",,"BOX",240,25.000,0.000,0.000,-30.000,-20.000,30.000,20.000)' in mit_rohteil
    and mit_rohteil.index("G17 G71 G90 G40")
    < mit_rohteil.index(
        'WORKPIECE(,"",,"BOX",240,25.000,0.000,0.000,-30.000,-20.000,30.000,20.000)'
    )
    < min(i for i, z in enumerate(mit_rohteil) if z.startswith(("G0 ", "G1 "))),
    f"Siemens Rohteil Fräse: {mit_rohteil[:8]}",
)
stange_box = ((-22.5, -22.5, -80.0), (22.5, 22.5, 21.0))
dreh_rohteil = pp.programm([rundum], pp.steuerung("siemens"), dreh, "Welle", rohteil=stange_box)
pruefe(
    'WORKPIECE(,,,"CYLINDER",192,21.000,-80.000,-80.000,45.000)' in dreh_rohteil.zeilen,
    f"Siemens Rohteil Drehmaschine: {dreh_rohteil.zeilen[:8]}",
)
befunde, _saetze = pp.nachlesen(dreh_rohteil, pp.steuerung("siemens"), dreh)
pruefe(not befunde, f"Rohteil nachgelesen: {[(b.art, b.satz) for b in befunde]}")
ohne_haken = pp.steuerung("siemens").ersetzt(rohteil=False)
pruefe(
    not any("WORKPIECE" in z for z in pp.programm([tasche], ohne_haken, rohteil=quader).zeilen),
    "Rohteil trotz Haken aus",
)
pruefe(
    not any(
        "WORKPIECE" in z
        for z in pp.programm([tasche], pp.steuerung("linuxcnc"), rohteil=quader).zeilen
    ),
    "Rohteil an LinuxCNC",
)
fraese_4 = pp.Maschineninfo("Fräse 4 Achsen", False, False, {"A": "A1"})
rund_4 = dataclasses.replace(
    rundum, befehle=[C("G0", {"X": 0.0, "Y": 0.0, "Z": 30.0, "A": 0.0}), C("G1", {"A": 90.0})]
)
pruefe(
    not any(
        "WORKPIECE" in z
        for z in pp.programm([rund_4], pp.steuerung("siemens"), fraese_4, rohteil=quader).zeilen
    ),
    "Quader an der Fräse mit Rundachse",
)
haas = pp.programm([rundum], pp.steuerung("haas"), dreh, "Welle").zeilen
pruefe("T101" in haas and "M154" in haas and "M133 P3000" in haas, f"Haas: {haas[:9]}")
pruefe("G98" in haas and "G94" not in haas, "Haas: G98 statt G94 an der Drehmaschine")
pruefe("G1 X76.000 Z0.000 C90.000 F3.00000" in haas, "Haas: C ohne Nummer")
pruefe("M135" in haas and "M155" in haas, f"Haas aus: {haas[-7:]}")
fanuc = pp.programm([rundum], pp.steuerung("fanuc"), dreh, "Welle")
pruefe("T0101" in fanuc.zeilen, f"Fanuc Wechsel: {fanuc.zeilen[:6]}")
pruefe(
    len(fanuc.hinweise) == 2 and all("Maschinenhersteller" in x for x in fanuc.hinweise),
    f"Fanuc Hinweise (C-Achse und Antrieb): {fanuc.hinweise}",
)
# Zum Wechselpunkt (Manuel, 2026-10-03): vor jedem Werkzeugwechsel und am Ende, zuerst X allein
# (an der Drehmaschine zieht X das Werkzeug weg), X im Durchmesser; in MKS mit G53 bzw. Siemens
# SUPA, in WKS als G0.
dreh_wp = pp.Maschineninfo(
    "Drehmaschine", True, True, {"C": "C4"}, {1: "3"}, {"X": 150.0, "Z": 300.0}
)
zweites = dataclasses.replace(rundum, name="Rundum schlichten T2", werkzeug=2)
siemens_wp = pp.programm([rundum, zweites], pp.steuerung("siemens"), dreh_wp, "Welle").zeilen
wp = [z for z in siemens_wp if z.startswith("G0 SUPA D0")]
pruefe(
    wp == ["G0 SUPA D0 X300.000", "G0 SUPA D0 X300.000 Z300.000"] * 3,
    f"Siemens Wechselpunkt: {wp}",
)
pruefe(
    siemens_wp.index("G0 SUPA D0 X300.000 Z300.000") < siemens_wp.index("T1 D1")
    and siemens_wp.index("T1 D1") < siemens_wp.index("T2 D1"),
    "Wechselpunkt nicht vor dem Wechsel",
)
haas_wp = pp.programm([rundum], pp.steuerung("haas"), dreh_wp, "Welle").zeilen
pruefe("G53 G0 X300.000" in haas_wp and "G53 G0 X300.000 Z300.000" in haas_wp, f"Haas: {haas_wp}")
wks = dataclasses.replace(dreh_wp, wechsel_wks=True)
lcnc_wks = pp.programm([rundum], pp.steuerung("linuxcnc"), wks, "Welle").zeilen
pruefe(
    "G0 X300.000 Z300.000" in lcnc_wks and not any("G53" in z for z in lcnc_wks),
    f"WKS: {lcnc_wks}",
)
pruefe(not any("SUPA" in z for z in siemens), "ohne Wechselpunkt trotzdem SUPA")
# Ein Befehl ohne {achsen} (ShopTurns F_HOME kennt den Punkt selbst): einmal je Wechsel und am
# Ende – auch ohne Wechselpunkt an der Maschine.
f_home = pp.steuerung("siemens", {"wechselpunkt_mks": "F_HOME"})
mit_f_home = pp.programm([rundum, zweites], f_home, dreh, "Welle").zeilen
pruefe(
    mit_f_home.count("F_HOME") == 3
    and mit_f_home.index("F_HOME") < mit_f_home.index("T1 D1")
    and not any("SUPA" in z for z in mit_f_home),
    f"F_HOME: {[z for z in mit_f_home if 'F_HOME' in z or z.startswith('T')]}",
)
# --- Die Haken und das Glätten (P-2026-10-03-27; Spezifikation Steuerung, Abschnitte 5, 7, 8) ---
# Siemens vorbelegt: G64, G642, CTOL mit der Toleranz, SOFT im Kopf – COMPCAD (Option) nicht.
kopf = siemens[: siemens.index("; Rundum schruppen T1")]
pruefe(
    all(z in kopf for z in ("G64", "G642", "CTOL=0.010", "SOFT")) and "COMPCAD" not in kopf,
    f"Siemens-Kopf: {kopf}",
)
lcnc = pp.programm([tasche], pp.steuerung("linuxcnc"), None, "Platte").zeilen
pruefe("G64 P0.010 Q0.010" in lcnc, f"LinuxCNC G64: {lcnc[:5]}")
mit_compcad = pp.programm(
    [rundum],
    pp.steuerung("siemens", {"glaetten": ["g64", "compcad"], "toleranz": 0.02}),
    dreh,
    "Welle",
)
pruefe(
    "COMPCAD" in mit_compcad.zeilen
    and "G642" not in mit_compcad.zeilen
    and any("COMPCAD" in h for h in mit_compcad.hinweise),
    f"COMPCAD: {mit_compcad.zeilen[:8]} {mit_compcad.hinweise}",
)
pruefe(
    pp.steuerung("siemens", {"toleranz": 5.0, "kuehlung": "nein", "g93": 1}).toleranz == 1.0
    and pp.steuerung("siemens", {"kuehlung": "nein"}).kuehlung is True,
    "falsche Werte angenommen",
)
# Alles aus: keine Kommentare, keine Kühlung, kein Wechselpunkt, keine C-Achse ein/aus.
aus = {"kommentare": False, "kuehlung": False, "wechselpunkt": False, "c_achse": False}
ohne_alles = pp.programm([rundum, tasche], pp.steuerung("siemens", aus), dreh_wp, "Welle").zeilen
pruefe(
    not any(z.startswith(";") for z in ohne_alles)
    and "M8" not in ohne_alles
    and not any("SUPA" in z or "SPOS" in z or "SPCOF" in z for z in ohne_alles),
    f"alles aus: {ohne_alles[:12]}",
)
# Satznummern: N10, N20 … – nicht vor „%“, „O0001“ und Kommentaren.
fanuc_n = pp.programm([tasche], pp.steuerung("fanuc", {"satznummern": True}), None, "P").zeilen
pruefe(
    fanuc_n[:3] == ["%", "O0001 (P)", "N10 G17 G21 G40 G49 G80 G90"]
    and fanuc_n[-1] == "%"
    and all(z.startswith(("N", "(", "%", "O")) for z in fanuc_n),
    f"Satznummern: {fanuc_n[:6]} … {fanuc_n[-3:]}",
)
# Ohne G93 (S5): F in mm/min, so dass die Zeit stimmt – von X42 Z3 C0 nach X38 Z0 C90 in
# 1/3 min: √(4² + 3² + 90²) · 3 = 270,416 mm/min; kein G93, kein G94.
ohne_g93 = pp.programm([rundum], pp.steuerung("siemens", {"g93": False}), dreh, "Welle").zeilen
pruefe(
    "G1 X76.000 Z0.000 C4=90.000 F270.416" in ohne_g93
    and "G93" not in ohne_g93
    and "G94" not in ohne_g93,
    f"ohne G93: {[z for z in ohne_g93 if z.startswith(('G1', 'G9'))]}",
)

geaendert = pp.steuerung("fanuc", {"angetrieben_ein": "M{m}3 S{s}", "unbekannt": "x"})
pruefe("M33 S3000" in pp.programm([rundum], geaendert, dreh).zeilen, "geänderter Befehl gilt nicht")
vorschau = pp.programm([tasche, tasche], pp.steuerung("linuxcnc"), None, vorschau=2)
pruefe(vorschau.saetze == 2 and "Vorschau endet" in vorschau.zeilen[-1], "Vorschau")

# --- Aus der Maschine: die Beispiel-Drehmaschine mit den Nummern von Manuels Maschine ---------
for nummern, erwartet in (
    ((4, 1), ("4", "S4", {"C": "C4"}, "1", {"1": "C1"})),
    ((1, 3), ("1", "S1", {"C": "C1"}, "3", {"3": "C3"})),
):
    asm, ma = bm.drehmaschine(
        bm.DrehmaschinenMasse(hauptspindel=nummern[0], werkzeugantrieb=nummern[1])
    )
    info = pp.maschineninfo_dokument(asm.Document)
    antriebe = set(info.angetrieben.values())
    ist = (info.hauptspindel, info.hauptspindel_name, info.rundachsen, *antriebe, info.antrieb_c)
    pruefe(
        info.drehmaschine
        and len(antriebe) == 1
        and len(info.angetrieben) == 12
        and ist == erwartet,
        f"Maschine {nummern}: {ist}",
    )
    FreeCAD.closeDocument(asm.Document.Name)
pruefe(
    bm.DrehmaschinenMasse(hauptspindel=2, werkzeugantrieb=2).fehler()
    and bm.DrehmaschinenMasse(hauptspindel=0).fehler(),
    "gleiche oder ungültige Spindelnummern gehen durch",
)

# --- Ein echter Job: Welle, Rundum schruppen, durch abschnitte() -------------------------------
user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
schaft = wz.Werkzeug(nummer=1, durchmesser=12, schneiden=3, schneidenlaenge=26)
schaft.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=4.8, ap=2, vc=120, fz=0.05)]
ue.uebergeben(wz.Bibliothek([schaft]))
doc = FreeCAD.newDocument("Post")
welle = doc.addObject("Part::Feature", "Welle")
welle.Shape = Part.makeCylinder(30, 60, V(), V(1, 0, 0))
doc.recompute()
stirn = next(
    f
    for f in welle.Shape.Faces
    if vr.ist_eben(f) and (vr.aussennormale(f) - V(1, 0, 0)).Length < 1e-9
)
achse = va.zugewiesen("C")
lage = vr.berechne(welle.Shape, stirn, achse, durchmesser=70)
job = vr.richte_ein(doc, welle, lage, vr.Stange(70.0, frei_hinten=20.0), achse, beschriftung="W")
tc = js.controller_ohne_transaktion(doc, job, schaft, schaft.einsaetze(wz.ALLE)[0])
op = vo.lege_an(job, tc, achse, zustellung=2.0, steigung=4.8, aufmass=0.3)
doc.recompute()
teile = pp.abschnitte(job)
pruefe(len(teile) == 1 and teile[0].werkzeug == 1, f"Abschnitte: {[a.name for a in teile]}")
p_job = pp.programm(teile, pp.steuerung("siemens"), dreh, job.Label)
saetze_g93 = [x for x in p_job.zeilen if x.startswith("G1") and "C4=" in x]
pruefe(saetze_g93 and all(" F" in x for x in saetze_g93), "G93-Sätze ohne F oder ohne C4")
pruefe(p_job.saetze > 100, f"Sätze: {p_job.saetze}")
pruefe(pp.dateiname(job, pp.steuerung("siemens")).endswith(".mpf"), "Dateiname")
print(ascii(f"Job: {p_job.saetze} Saetze, {len(p_job.zeilen)} Zeilen"))
# Nachgelesen wie an der Steuerung (programm_pruefen): an jeder Steuerung nichts; an Fanuc und
# Haas kein G90 (dort an der Drehmaschine der Längsdrehzyklus) – auch nicht aus der Bahn.
for kennung in pp.STEUERUNGEN:
    s = pp.steuerung(kennung)
    if s.dialekt == "klartext":
        continue  # Heidenhain-Klartext nur an der Fräse – unten eigens
    p_k = pp.programm(teile, s, dreh, job.Label)
    befunde, _saetze = pp.nachlesen(p_k, s, dreh)
    pruefe(not befunde, f"Job {kennung}: {[(b.art, b.satz) for b in befunde[:3]]}")
    if kennung in ("fanuc", "haas"):
        g90 = [x for x in p_k.zeilen if "G90" in x.split() or "G91" in x.split()]
        pruefe(not g90, f"Job {kennung}: {g90[:3]}")

# --- Bohrzyklen (Spezifikation Steuerung, E8): Siemens CYCLE81/83/85 statt G81 ff. -------------
# G98: Rückzug auf die Höhe davor (5), G99: auf R (2); Tiefbohren mit der ersten Tiefe R − Q.
# LinuxCNC und die Drehmaschine behalten den G-Code.
bohren = pp.Abschnitt(
    "Bohren",
    2,
    900.0,
    False,
    "None",
    [
        C("G90"),
        C("G0", {"Z": 20.0}),
        C("G98"),
        C("G0", {"X": 10.0, "Y": 10.0}),
        C("G0", {"Z": 5.0, "F": 0.0}),  # wie FreeCADs Bohren: F0 im Eilgang fällt weg
        C("G81", {"X": 10.0, "Y": 10.0, "Z": -8.0, "R": 2.0, "F": 2.0}),
        C("G83", {"X": 30.0, "Y": 10.0, "Z": -20.0, "R": 2.0, "Q": 5.0, "F": 2.0}),
        C("G80"),
        C("G99"),
        C("G85", {"X": 50.0, "Y": 10.0, "Z": -6.0, "R": 2.0, "F": 1.0}),
        C("G80"),
        C("G0", {"Z": 20.0}),
    ],
    "Bohrer",
)
fraese = pp.Maschineninfo("Fräse")
siemens_b = pp.programm([bohren], pp.steuerung("siemens"), fraese, "B").zeilen
soll = [
    "G0 Z5.000",
    "F120.000",
    "CYCLE81(5.000,2.000,0,-8.000)",
    "G0 X30.000 Y10.000",
    "F120.000",
    "CYCLE83(5.000,2.000,0,-20.000,,-3.000,,0,0,0,1,1)",
    "G0 X50.000 Y10.000",
    "F60.000",
    "CYCLE85(2.000,2.000,0,-6.000,,0,60.000,60.000)",
]
erste = siemens_b.index(soll[0]) if soll[0] in siemens_b else -1
pruefe(siemens_b[erste : erste + len(soll)] == soll, f"Siemens Bohrzyklen: {siemens_b}")
pruefe(
    not any(x.split(" ")[0] in ("G80", "G81", "G83", "G85", "G98", "G99") for x in siemens_b),
    f"Siemens: G8x/G98/G99 übrig: {siemens_b}",
)
lcnc_b = pp.programm([bohren], pp.steuerung("linuxcnc"), fraese, "B").zeilen
pruefe(
    any(x.startswith("G83 ") and "Q5.000" in x for x in lcnc_b) and "G98" in lcnc_b,
    f"LinuxCNC Bohrzyklen: {lcnc_b}",
)
dreh_b = pp.programm([bohren], pp.steuerung("siemens"), dreh, "B").zeilen
pruefe(any(x.startswith("G81 ") for x in dreh_b), "Drehmaschine: G81 nicht behalten")

# --- Heidenhain im Klartext (P-2026-10-05-01; Manuel: „Heidenhain muss mit rein … vor allem
# iTNC 530“): Sätze wie im Programm einer iTNC 530 – BEGIN/END PGM wie die Datei, BLK FORM,
# TOOL CALL mit Drehzahl, M3 allein, L mit Vorzeichen, FMAX, CC/C, M91 zum Wechselpunkt; die
# Bohrzyklen ausgeschrieben (G98: zurück auf die Höhe davor, G99: auf R); Satznummern ab 0.
import re  # noqa: E402

from camaddon import klartext as kt  # noqa: E402
from camaddon import programm_pruefen as prp  # noqa: E402

kreise = pp.Abschnitt(
    "Kreise",
    3,
    2000.0,
    False,
    "Flood",
    [
        C("G0", {"Z": 15.0}),
        C("G0", {"X": 10.0, "Y": 5.0}),
        C("G1", {"Z": -2.0, "F": 5.0}),
        C("G2", {"X": 20.0, "Y": 5.0, "I": 5.0, "J": 0.0, "F": 10.0}),
        C("G3", {"X": 20.0, "Y": 5.0, "I": -5.0, "J": 0.0}),  # Vollkreis
        C("G2", {"X": 25.0, "Y": 10.0, "Z": -4.0, "I": 5.0, "J": 0.0}),  # Schraube
        C("G0", {"Z": 15.0}),
    ],
    "Fräser Ø 12",
)
wp = pp.Maschineninfo("Fräse", wechselpunkt={"Z": 0.0, "X": -200.0})
hh = pp.steuerung("heidenhain")
p_hh = pp.programm(
    [kreise, bohren], hh, wp, "Teil", datei="/x/Teil_1.h", rohteil=((0, 0, -20), (60, 40, 0))
)
z_hh = p_hh.zeilen
saetze_hh = [re.sub(r"^\d+ ", "", x) for x in z_hh]
pruefe(
    all(x.startswith(f"{i} ") for i, x in enumerate(z_hh)),
    f"Heidenhain Nummern: {z_hh[:3]}",
)
pruefe(
    saetze_hh[0] == "BEGIN PGM Teil_1 MM"
    and saetze_hh[-1] == "END PGM Teil_1 MM"
    and saetze_hh[-2] == "M30"
    and saetze_hh[1:3] == ["BLK FORM 0.1 Z X+0.000 Y+0.000 Z-20.000", "BLK FORM 0.2 X+60.000 Y+40.000 Z+0.000"],
    f"Heidenhain Anfang/Ende: {saetze_hh[:3]} … {saetze_hh[-2:]}",
)  # fmt: skip
k = saetze_hh.index("TOOL CALL 3 Z S2000") if "TOOL CALL 3 Z S2000" in saetze_hh else -1
pruefe(k > 0 and saetze_hh[k + 1 : k + 3] == ["M3", "M8"], f"TOOL CALL: {saetze_hh[k - 2 : k + 4]}")
pruefe(
    "L Z+0.000 R0 FMAX M91" in saetze_hh and "L X-200.000 Z+0.000 R0 FMAX M91" in saetze_hh,
    f"Wechselpunkt M91: {saetze_hh[:16]}",
)
for satz in (
    "L Z-2.000 R0 F300",
    "CC X+15.000 Y+5.000",
    "C X+20.000 Y+5.000 DR- R0 F600",
    "C X+10.000 Y+5.000 DR+ R0",  # der Vollkreis in zwei Hälften
    "L Z-8.000 R0 F120",  # G81
    "L Z-20.000 R0",  # G83 bis zur Tiefe
    "L Z-17.500 R0 FMAX",  # G83: im Eilgang bis knapp über die letzte Tiefe
    "L Z-6.000 R0 F60",  # G85 hinein …
):
    pruefe(satz in saetze_hh, f"Heidenhain fehlt „{satz}“")
g85 = saetze_hh.index("L Z-6.000 R0 F60") if "L Z-6.000 R0 F60" in saetze_hh else -1
pruefe(saetze_hh[g85 + 1] == "L Z+2.000 R0", f"G85 im Vorschub heraus: {saetze_hh[g85:g85 + 3]}")
pruefe(
    not any(x.split()[0] in ("G0", "G1", "G2", "G3", "G81", "G83", "G85") for x in saetze_hh),
    "Heidenhain: G-Code übrig",
)
pruefe(any("Schraube" in h for h in p_hh.hinweise), f"Schraube: {p_hh.hinweise}")
befunde, saetze = pp.nachlesen(p_hh, hh, wp)
pruefe(not befunde and saetze > 20, f"Heidenhain nachgelesen: {[(b.art, b.satz) for b in befunde]}")
pruefe(
    pp.dateiname(job, hh).endswith(".h") and pp.dateiname(job, pp.steuerung("heidenhain_tnc640")).endswith(".h"),
    "Heidenhain Endung",
)  # fmt: skip
# Der Prüfer findet: einen falschen Kreis, eine springende Nummer, F fehlt, die Spindel steht.
kaputt = "\n".join(
    [
        "0 BEGIN PGM K MM",
        "1 TOOL CALL 1 Z S1000",
        "2 L X+0.000 Y+0.000 Z+5.000 R0 FMAX",
        "3 L Z-1.000 R0",
        "4 M3",
        "5 L X+10.000 R0 F100",
        "6 CC X+15.000 Y+0.000",
        "7 C X+15.000 Y+6.000 DR+ R0",
        "9 M30",
        "10 END PGM K MM",
    ]
)
arten = {b.art for b in kt.pruefe(kaputt).befunde}
pruefe(
    {prp.SPINDEL, prp.VORSCHUB, prp.KREIS, kt.NUMMER} <= arten,
    f"Klartext-Prüfer: {sorted(arten)}",
)
# An der Drehmaschine: der Hinweis, dass Klartext hier für Fräsen gebaut ist.
p_hd = pp.programm([kreise], hh, dreh, "W")
pruefe(
    any("Fräsmaschinen" in h for h in p_hd.hinweise), f"Heidenhain Drehmaschine: {p_hd.hinweise}"
)
print(ascii(f"Heidenhain: {len(z_hh)} Saetze, {saetze} nachgelesen"))

# --- Messstopp (Spezifikation Strategien 12.4): zum Messen an den Wechselpunkt ----------------
# Mit Wechselpunkt Z 150 (MKS) statt „G0 Z25“ der Weg dorthin, dann M5, M0, M3; an der Siemens
# mit „F_HOME“ als Befehl genau das; ohne Wechselpunkt bleibt „G0 Z25“.
from camaddon import messstopp as ms  # noqa: E402

messen = pp.Abschnitt(
    "Messstopp", 2, 900.0, False, "None", [C(z) for z in ms.zeilen(25.0, 900.0)], "Bohrer"
)
mit_wp = pp.Maschineninfo("Fräse")
mit_wp.wechselpunkt = {"Z": 150.0}
z_lcnc = pp.programm([bohren, messen], pp.steuerung("linuxcnc"), mit_wp, "M").zeilen
k = z_lcnc.index("(MESSSTOPP)") if "(MESSSTOPP)" in z_lcnc else -1
pruefe(z_lcnc[k + 1 : k + 5] == ["G53 G0 Z150.000", "M5", "M0", "M3"], f"Messstopp: {z_lcnc[k:]}")
fhome = pp.steuerung("siemens", {"wechselpunkt_mks": "F_HOME"})
z_sie = pp.programm([bohren, messen], fhome, mit_wp, "M").zeilen
k = z_sie.index("; MESSSTOPP") if "; MESSSTOPP" in z_sie else -1
pruefe(z_sie[k + 1 : k + 3] == ["F_HOME", "M5"], f"Siemens F_HOME: {z_sie[k:]}")
# Siemens fährt den Wechselpunkt mit „SUPA D0“ – D0 schaltet die Korrektur ab: Folgt kein Wechsel
# (Sprungmarken aus, dasselbe Werkzeug fräst weiter), schaltet der nächste Satz mit Z „D1“ wieder
# ein (P-2026-10-04-51); mit Wechsel kommt D1 mit M6, kein „D1“ dazu.
weiter = dataclasses.replace(tasche, name="Weiter", werkzeug=2)
ohne_marken = pp.steuerung("siemens", {"marken": False})
z_d1 = pp.programm([bohren, messen, weiter], ohne_marken, mit_wp, "M").zeilen
k = z_d1.index("; MESSSTOPP") if "; MESSSTOPP" in z_d1 else -1
nach_stopp = [x for x in z_d1[k:] if x.startswith(("G0", "G1")) and " Z" in x and "SUPA" not in x]
pruefe(
    k >= 0 and z_d1[k + 1].startswith("G0 SUPA D0") and nach_stopp and " D1 " in nach_stopp[0],
    f"Siemens nach SUPA D0 ohne D1: {z_d1[k:k + 12]}",
)
pruefe(sum(" D1" in x for x in z_d1) == 1, f"D1 zu oft: {[x for x in z_d1 if 'D1' in x]}")
z_ohne = pp.programm([bohren, messen], pp.steuerung("linuxcnc"), fraese, "M").zeilen
k = z_ohne.index("(MESSSTOPP)") if "(MESSSTOPP)" in z_ohne else -1
pruefe(z_ohne[k + 1] == "G0 G43 H2 Z25.000", f"ohne Wechselpunkt: {z_ohne[k:]}")

# --- Keine Dopplungen (P-2026-10-04-15): derselbe Eilgang zweimal hintereinander und „M5“ nach
# „M5“ am Ende schreibt er nur einmal; zwei gleiche G1 bleiben (nicht angefasst).
doppelt = pp.Abschnitt(
    "Doppelt",
    1,
    1000.0,
    False,
    "None",
    [
        C("G0", {"X": 10.0, "Y": 5.0, "Z": 5.0}),
        C("G0", {"X": 10.0, "Y": 5.0, "Z": 5.0}),
        C("G1", {"Z": 0.0, "F": 5.0}),
        C("G1", {"Z": 0.0}),
        C("G0", {"Z": 5.0}),
    ],
    "Fräser",
)
for kennung in ("siemens", "linuxcnc"):
    z = pp.programm([doppelt], pp.steuerung(kennung), pp.Maschineninfo("Fräse"), "D").zeilen
    pruefe(z.count("G0 X10.000 Y5.000 Z5.000") == 1, f"{kennung}: Eilgang doppelt: {z}")
    pruefe(z.count("G1 Z0.000") == 1, f"{kennung}: das zweite G1 fehlt: {z}")
    pruefe(
        not any(a == b == "M5" for a, b in zip(z, z[1:], strict=False)),
        f"{kennung}: M5 nach M5: {z[-6:]}",
    )

# Fein geprüfte Simultanbahnen: lineare und Moduloachsen nicht auf drei Stellen runden;
# die Glättung muss innerhalb des reservierten Qualitätsbudgets bleiben.
fein = pp.Abschnitt(
    "Fein",
    1,
    2000,
    False,
    befehle=[
        C("G0", {"X": 0.0, "Z": 10.0, "C": 0.0}),
        C("G1", {"X": 1.1234564, "Z": 9.9999994, "C": 0.0000006, "F": 5.0}),
    ],
    koordinatenstellen=6,
)
feines_programm = pp.programm(
    [fein],
    pp.steuerung("siemens"),
    pp.Maschineninfo("Fräse", rundachsen={"C": "C4"}, modulo={"C"}),
)
pruefe(
    any("X1.123456" in z and "C4=ACP(0.000001)" in z for z in feines_programm.zeilen),
    "Feine Koordinaten oder kleine Moduloachsfahrt verloren",
)
pruefe("CTOL=0.000100" in feines_programm.zeilen, "Zu große Glättung der geprüften Bahn")
feiner_klartext = pp.programm([fein], pp.steuerung("heidenhain"), pp.Maschineninfo("Fräse"))
pruefe(
    any("X+1.123456" in z and "C+0.000001" in z for z in feiner_klartext.zeilen),
    "Klartext hat die feine Bahn erneut gerundet",
)
pruefe(
    any("CYCL DEF 32.1 T0.000100" in z for z in feiner_klartext.zeilen),
    "Zu große Klartext-Glättung der geprüften Bahn",
)

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
