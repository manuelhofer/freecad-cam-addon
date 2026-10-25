# SPDX-License-Identifier: LGPL-2.1-or-later
# Der Postprozessor des Addons (W-005, P-2026-10-03-10): Musterausgaben aus Abschnitten – eine
# Fräse mit LinuxCNC, eine Drehmaschine mit C-Achse und angetriebenem Werkzeug für Siemens,
# Haas und Fanuc – und ein echter 4-Achs-Job (Rundum schruppen) durch abschnitte(). Wie Manuels
# Drehmaschine (P-2026-10-03-25): die Hauptspindel S4/C4, die angetriebenen Werkzeuge S1/C1 –
# C4 positioniert („SPOS[4]=0“, „C4=…“), S1 dreht („M1=3 S1=…“); die Beispielmaschine mit diesen
# Nummern gibt genau das an den Postprozessor, ihre C1 ist nie die Rundachse der Bahn.
# Ausführen: freecadcmd tests/test_postprozessor.py

import dataclasses
import math
import os
import pathlib
import re
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
pruefe(z[:3] == ["%", "(Platte)", "G17 G21 G40 G49 G80 G90 G94"], f"Kopf: {z[:3]}")
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
    and mit_rohteil.index("G17 G71 G90 G40 G94")
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
    fanuc_n[:3] == ["%", "O0001 (P)", "N10 G17 G21 G40 G49 G80 G90 G94"]
    and fanuc_n[-1] == "%"
    and all(z.startswith(("N", "(", "%", "O")) for z in fanuc_n),
    f"Satznummern: {fanuc_n[:6]} … {fanuc_n[-3:]}",
)
# Eigene Befehle vor und nach dem Wechsel: „M1“ davor, an GRBL das Antasten danach.
mit_eigen = pp.steuerung(
    "grbl", {"vor_wechsel": "M1 (T{t})", "nach_wechsel": "G38.2 Z-50 F100\nG10 L20 P1 Z5\nG0 Z10"}
)
z_e = pp.programm([tasche], mit_eigen, None, "E").zeilen
k = z_e.index("M0") if "M0" in z_e else -1
pruefe(
    k > 0 and z_e[k - 1] == "M1 (T3)" and z_e[k + 1 : k + 4] == ["G38.2 Z-50 F100", "G10 L20 P1 Z5", "G0 Z10"],
    f"vor/nach dem Wechsel: {z_e[k - 3 : k + 5]}",
)  # fmt: skip
# Ohne Leerzeichen (Haken aus): „G1X…“ – Kommentare bleiben; nachgelesen ohne Befund; die Siemens
# bleibt mit Leerzeichen (SUPA D0).
ohne_l = pp.programm([tasche], pp.steuerung("fanuc", {"leerzeichen": False}), None, "P")
pruefe(
    "G17G21G40G49G80G90G94" in ohne_l.zeilen
    and any(x.startswith("G1Z") or x.startswith("G1X") for x in ohne_l.zeilen)
    and "O0001(P)" in ohne_l.zeilen
    and any(x.startswith("(") and " " in x for x in ohne_l.zeilen),
    f"ohne Leerzeichen: {ohne_l.zeilen[:14]}",
)
pruefe(
    not pp.nachlesen(ohne_l, pp.steuerung("fanuc", {"leerzeichen": False}), None)[0], "nachgelesen"
)
mit_s = pp.programm([tasche], pp.steuerung("siemens", {"leerzeichen": False}), None, "P").zeilen
pruefe("G17 G71 G90 G40 G94" in mit_s, f"Siemens ohne Leerzeichen: {mit_s[:3]}")
# Die Programmnummer des Jobs im Kopf: Fanuc vierstellig, Haas fünfstellig, höchstens die größte.
pruefe(
    pp.programm([tasche], pp.steuerung("fanuc"), None, "P", nummer=1234).zeilen[1] == "O1234 (P)",
    "Fanuc O1234",
)
pruefe(
    pp.programm([tasche], pp.steuerung("haas"), None, "P", nummer=7).zeilen[1] == "O00007 (P)",
    "Haas O00007",
)
pruefe(
    pp.programm([tasche], pp.steuerung("fanuc"), None, "P", nummer=123456).zeilen[1] == "O9999 (P)",
    "Fanuc über O9999",
)
# Mit Marken N1 … N12 bekommt kein Satz die Nummer einer Marke (sonst fände die Suche nach N10
# den Satz); über der höchsten Nummer (Fanuc: fünf Stellen) wieder ab N10.
zwoelf = [pp.Abschnitt(f"Op{i}", i, 1000.0, False, "None", tasche.befehle) for i in range(1, 13)]
s_n = pp.steuerung("fanuc", {"satznummern": True}).ersetzt(satznummer_max=200)
z_nn = pp.programm(zwoelf, s_n, None, "P").zeilen
nummern = [int(z.split()[0][1:]) for z in z_nn if re.match(r"N\d+ ", z)]
pruefe("N10" in z_nn and "N12" in z_nn, f"Marken N10, N12: {z_nn[:30]}")
pruefe(
    10 not in nummern and 20 in nummern and max(nummern) <= 200 and nummern.count(30) >= 2,
    f"Satznummern neben Marken, bis 200: {nummern[:40]}",
)
# Fanuc liest höchstens acht Ziffern (±99999.999): eine fortlaufend gezählte Rundachse darüber –
# ein Hinweis; LinuxCNC kennt keine Grenze.
weit_rund = pp.Abschnitt(
    "Rund", 1, 1000.0, False, "None", [C("G1", {"X": 1.0, "A": 120000.0, "F": 1.0})]
)
p_weit = pp.programm([weit_rund], pp.steuerung("fanuc"), None, "W")
pruefe(any("A120000.000" in h for h in p_weit.hinweise), f"Fanuc A120000: {p_weit.hinweise}")
pruefe(
    not any(
        "99999" in h for h in pp.programm([weit_rund], pp.steuerung("linuxcnc"), None, "W").hinweise
    ),
    "LinuxCNC: Hinweis Ziffern",
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
    if s.dialekt in ("klartext", "mpr"):
        continue  # Heidenhain-Klartext und woodWOP nur an der Fräse – eigens (test_mpr)
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
# Das nächste Werkzeug gleich nach dem Wechsel vorwählen (Fanuc „T2“, Heidenhain „TOOL DEF 2“),
# beim letzten keins; Haken aus: keine Vorwahl; an der Drehmaschine nie.

zwei = pp.programm([tasche, bohren], pp.steuerung("fanuc"), fraese, "V").zeilen
k = zwei.index("T3 M6") if "T3 M6" in zwei else -1
pruefe(
    k > 0 and zwei[k + 1] == "T2" and zwei.count("T2") == 1, f"Fanuc Vorwahl: {zwei[k - 1 : k + 3]}"
)
ohne_v = pp.programm(
    [tasche, bohren], pp.steuerung("fanuc", {"werkzeug_vorwahl": False}), fraese, "V"
)
pruefe("T2" not in ohne_v.zeilen, "Vorwahl trotz Haken aus")
p_hv = pp.programm([tasche, bohren], pp.steuerung("heidenhain"), fraese, "V")
s_hv = [re.sub(r"^\d+ ", "", x) for x in p_hv.zeilen]
k = s_hv.index("TOOL CALL 3 Z S2000") if "TOOL CALL 3 Z S2000" in s_hv else -1
pruefe(k > 0 and s_hv[k + 1] == "TOOL DEF 2", f"Heidenhain Vorwahl: {s_hv[k - 1 : k + 3]}")
pruefe(
    not pp.nachlesen(p_hv, pp.steuerung("heidenhain"), fraese)[0], "Heidenhain Vorwahl nachgelesen"
)
pruefe(
    not any(
        x == "T2" for x in pp.programm([tasche, bohren], pp.steuerung("fanuc"), dreh, "V").zeilen
    ),
    "Vorwahl an der Drehmaschine",
)
# Warten, bis die Spindel läuft (die Hochlaufzeit an der Maschine): GRBL, LinuxCNC, Mach von
# selbst „G4 P2.000“ nach M3; Fanuc erst mit dem Haken, dann „G4 X2.000“ (X mit Punkt: Sekunden);
# Siemens „G4 F2.000“; Heidenhain Zyklus 9. Ohne Hochlaufzeit ein Hinweis statt einer Wartezeit.
hoch = pp.Maschineninfo("Fräse")
hoch.hochlauf = {"haupt": 2.0}
for kennung, soll in (("linuxcnc", "G4 P2.000"), ("grbl", "G4 P2.000"), ("mach", "G4 P2.000")):
    z_h = pp.programm([tasche], pp.steuerung(kennung), hoch, "H").zeilen
    k = z_h.index("M3 S2000") if "M3 S2000" in z_h else -1
    pruefe(k > 0 and z_h[k + 1] == soll, f"{kennung} Hochlauf: {z_h[k : k + 3]}")
pruefe(
    "G4 X2.000" not in pp.programm([tasche], pp.steuerung("fanuc"), hoch, "H").zeilen, "Fanuc aus"
)
an = {"hochlauf_warten": True}
for kennung, soll in (("fanuc", "G4 X2.000"), ("mazak", "G4 X2.000"), ("siemens", "G4 F2.000")):
    z_h = pp.programm([tasche], pp.steuerung(kennung, an), hoch, "H").zeilen
    pruefe(soll in z_h, f"{kennung} Hochlauf an: {z_h}")
z_h = [
    re.sub(r"^\d+ ", "", x)
    for x in pp.programm([tasche], pp.steuerung("heidenhain", an), hoch, "H").zeilen
]
pruefe("CYCL DEF 9.1 V.ZEIT 2" in z_h, f"Heidenhain Hochlauf: {z_h}")
null = pp.Maschineninfo("Fräse")
null.hochlauf = {"haupt": 0.0}  # die Spindel ist da, ihre Hochlaufzeit nicht eingetragen
ohne_h = pp.programm([tasche], pp.steuerung("linuxcnc"), null, "H")
pruefe(
    not any(x.startswith("G4") for x in ohne_h.zeilen)
    and any("Hochlaufzeit" in h for h in ohne_h.hinweise),
    f"ohne Hochlaufzeit: {ohne_h.hinweise}",
)
# Eine Vorlage geleert (Tiefbohren im ISO-Modus): die anderen gelten weiter, G98/G99 bleiben.
teil_b = pp.programm([bohren], pp.steuerung("siemens", {"tiefbohren": ""}), fraese, "B").zeilen
pruefe(
    "CYCLE81(5.000,2.000,0,-8.000)" in teil_b
    and any(x.startswith("G83 ") for x in teil_b)
    and "G98" in teil_b,
    f"Siemens ohne Tiefbohr-Vorlage: {teil_b}",
)
lcnc_b = pp.programm([bohren], pp.steuerung("linuxcnc"), fraese, "B").zeilen
pruefe(
    any(x.startswith("G83 ") and "Q5.000" in x for x in lcnc_b) and "G98" in lcnc_b,
    f"LinuxCNC Bohrzyklen: {lcnc_b}",
)
# An der Drehmaschine ausgeschrieben (Siemens kennt G81 nur im ISO-Modus, Fanuc-Drehmaschinen
# haben kein G81, LinuxCNC bohrte in G18 längs Y): X im Durchmesser, Verweilen wie die Steuerung.
for kennung in ("siemens", "fanuc", "linuxcnc"):
    dreh_b = pp.programm([bohren], pp.steuerung(kennung), dreh, "B").zeilen
    nach_kopf = dreh_b[next(i for i, x in enumerate(dreh_b) if x.startswith("M3")) :]
    woerter_b = " ".join(x for x in nach_kopf if not x.startswith(("(", ";"))).split()
    pruefe(
        not set(woerter_b) & {"G80", "G81", "G82", "G83", "G85", "G98", "G99"}
        and "G0 X20.000 Y10.000" in dreh_b
        and "G1 Z-8.000 F120.000" in dreh_b,
        f"{kennung} Drehmaschine Bohren: {dreh_b}",
    )
# Eine Drehmaschine ohne Y: „Y0“ fällt weg, ein anderes Y bleibt (Alarm statt falscher Stelle) –
# mit Hinweis.
ohne_y = pp.Maschineninfo("Drehmaschine", True, True, {"C": "C4"}, {1: "3"})
ohne_y.linear = {"X", "Z"}
mitte = dataclasses.replace(
    bohren,
    befehle=[C("G0", {"X": 0.0, "Y": 0.0, "Z": 5.0}), C("G81", {"X": 0.0, "Y": 0.0, "Z": -8.0, "R": 2.0, "F": 2.0})],
)  # fmt: skip
p_my = pp.programm([mitte], pp.steuerung("siemens"), ohne_y, "Y")
pruefe(
    not any(" Y" in x for x in p_my.zeilen if not x.startswith(";")) and not p_my.hinweise,
    f"Y0 ohne Y-Achse: {p_my.zeilen[-12:]} {p_my.hinweise}",
)
# Eine Fräse mit anders benannter Achse („Hub“ statt Z): nichts fällt weg, auch nicht Z0.
hub = pp.Maschineninfo("Fräse")
hub.linear = {"X", "Y", "H"}
z_hub = pp.programm([mitte], pp.steuerung("linuxcnc"), hub, "H").zeilen
pruefe(
    any(" Y0.000" in x for x in z_hub)
    and not pp.programm([mitte], pp.steuerung("linuxcnc"), hub, "H").hinweise,
    f"Fräse ohne Z-Name: {z_hub[-8:]}",
)
p_y5 = pp.programm([bohren], pp.steuerung("siemens"), ohne_y, "Y")
pruefe(any("keine Y-Achse" in h for h in p_y5.hinweise), f"Y10 ohne Y-Achse: {p_y5.hinweise}")
gewinde_d = pp.Abschnitt(
    "Gewinde", 4, 255.0, False, "None",
    [C("G0", {"X": 0.0, "Z": 24.0}), C("G84", {"X": 0.0, "Z": 6.5, "R": 24.0, "S": 255.0, "F": 1.5}),
     C("G80")],
    "M10",
)  # fmt: skip
p_gd = pp.programm([gewinde_d], pp.steuerung("siemens"), dreh, "G")
pruefe(
    not any("G84" in x or "CYCLE84" in x for x in p_gd.zeilen if not x.startswith(";"))
    and any("Drehmaschine" in h for h in p_gd.hinweise),
    f"Gewinde an der Drehmaschine: {p_gd.zeilen[-8:]} {p_gd.hinweise}",
)
# LinuxCNC mit „synchron“: G33.1 längs Z auch an der Drehmaschine, X im Durchmesser.
gewinde_x = dataclasses.replace(
    gewinde_d,
    befehle=[C("G0", {"X": 0.0, "Z": 24.0}),
             C("G84", {"X": 5.0, "Z": 6.5, "R": 24.0, "S": 255.0, "F": 1.5}), C("G80")],
)  # fmt: skip
z_lg = pp.programm(
    [gewinde_x], pp.steuerung("linuxcnc", {"gewinde_synchron": True}), dreh, "G"
).zeilen
k = z_lg.index("G33.1 Z6.500 K1.500") if "G33.1 Z6.500 K1.500" in z_lg else -1
pruefe(
    k > 2 and z_lg[k - 3] == "G0 X10.000",
    f"LinuxCNC G33.1 an der Drehmaschine: {z_lg[k - 3 : k + 2]}",
)


# Der Nullpunkt aus dem Job (Fixtures): vorbelegt aus; an: am Anfang und in jedem Einstieg vor
# dem Wechselpunkt, je Steuerung ihr Befehl – Siemens ab dem fünften G505 (G58 ist dort axial),
# Fanuc G54.1 P, Haas G154 P, Mach G59 P, Heidenhain Zyklus 247; GRBL kennt nach G59 keinen.
def mit_nullpunkt(*register):
    return [dataclasses.replace(a, nullpunkte=register) for a in (tasche, bohren)]


oben = pp.Maschineninfo("Fräse", wechselpunkt={"Z": 250.0})
aus_n = pp.programm(mit_nullpunkt("G54"), pp.steuerung("linuxcnc"), oben, "N").zeilen
pruefe("G54" not in aus_n, f"Nullpunkt ohne Haken: {aus_n}")
an_n = {"nullpunkt_setzen": True}
z_n = pp.programm(mit_nullpunkt("G54"), pp.steuerung("linuxcnc", an_n), oben, "N").zeilen
k = z_n.index("G54") if "G54" in z_n else -1
pruefe(
    k > 0 and z_n[k + 1] == "G53 G0 Z250.000" and z_n.count("G54") == 2,
    f"LinuxCNC Nullpunkt je Einstieg vor dem Wechselpunkt: {z_n}",
)
pruefe("(Nullpunkt: G54)" in z_n, f"Nullpunkt im Kopf: {z_n[:12]}")
for kennung, register, soll in (
    ("siemens", "G56", "G56"),
    ("siemens", "G58", "G505"),
    ("siemens", "G59.1", "G507"),
    ("linuxcnc", "G59.2", "G59.2"),
    ("fanuc", "G59.2", "G54.1 P2"),
    ("fanuc", "G54.1 P3", "G54.1 P3"),
    ("mazak", "G59.1", "G54.1 P1"),
    ("haas", "G59.2", "G154 P2"),
    ("mach", "G59.2", "G59 P8"),
    ("grbl", "G55", "G55"),
):
    p_n = pp.programm(mit_nullpunkt(register), pp.steuerung(kennung, an_n), oben, "N")
    pruefe(soll in p_n.zeilen, f"{kennung} {register} → {soll}: {p_n.zeilen}")
    pruefe(not p_n.hinweise, f"{kennung} {register} Hinweis: {p_n.hinweise}")
    befunde_n = pp.nachlesen(p_n, pp.steuerung(kennung, an_n), oben)[0]
    pruefe(not befunde_n, f"{kennung} {register} nachgelesen: {[b.art for b in befunde_n]}")
k_s = pp.programm(mit_nullpunkt("G58"), pp.steuerung("siemens", an_n), oben, "N").zeilen
pruefe("; Nullpunkt: G58 – im Programm G505" in k_s, f"Siemens Kopf: {k_s[:6]}")
p_g = pp.programm(mit_nullpunkt("G59.1"), pp.steuerung("grbl", an_n), oben, "N")
pruefe(
    not any(x.startswith("G59") for x in p_g.zeilen) and any("G59.1" in h for h in p_g.hinweise),
    f"GRBL G59.1: {p_g.hinweise}",
)
p_m = pp.programm(mit_nullpunkt("G54", "G55"), pp.steuerung("linuxcnc", an_n), oben, "N")
pruefe(
    "G55" not in p_m.zeilen and any("G54, G55" in h for h in p_m.hinweise),
    f"mehrere Nullpunkte: {p_m.hinweise}",
)
p_hn = pp.programm(mit_nullpunkt("G55"), pp.steuerung("heidenhain", an_n), oben, "N")
s_hn = [re.sub(r"^\d+ ", "", x) for x in p_hn.zeilen]
k = (
    s_hn.index("CYCL DEF 247 BEZUGSPUNKT SETZEN ~")
    if "CYCL DEF 247 BEZUGSPUNKT SETZEN ~" in s_hn
    else -1
)
pruefe(
    k > 0 and s_hn[k + 1] == "  Q339=+2 ;BEZUGSPUNKT-NUMMER" and "M91" in s_hn[k + 2],
    f"Heidenhain Zyklus 247: {s_hn[k - 1 : k + 4]}",
)
pruefe(
    not pp.nachlesen(p_hn, pp.steuerung("heidenhain", an_n), oben)[0],
    "Heidenhain Zyklus 247 nachgelesen",
)

# --- Heidenhain im Klartext (P-2026-10-05-01; Manuel: „Heidenhain muss mit rein … vor allem
# iTNC 530“): Sätze wie im Programm einer iTNC 530 – BEGIN/END PGM wie die Datei, BLK FORM,
# TOOL CALL mit Drehzahl, M3 allein, L mit Vorzeichen, FMAX, CC/C, M91 zum Wechselpunkt; die
# Bohrzyklen ausgeschrieben (G98: zurück auf die Höhe davor, G99: auf R); Satznummern ab 0.

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
    all(x.startswith(f"{i} ") for i, x in enumerate(z for z in z_hh if not z.startswith("  "))),
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
nach_call = [x for x in saetze_hh[k + 1 : k + 4] if not x.startswith("TOOL DEF")]  # die Vorwahl
pruefe(k > 0 and nach_call[:2] == ["M3", "M8"], f"TOOL CALL: {saetze_hh[k - 2 : k + 4]}")
pruefe(
    "L Z+0.000 R0 FMAX M91" in saetze_hh and "L X-200.000 Z+0.000 R0 FMAX M91" in saetze_hh,
    f"Wechselpunkt M91: {saetze_hh[:16]}",
)
for satz in (
    "L Z-2.000 R0 F300",
    "CC X+15.000 Y+5.000",
    "C X+20.000 Y+5.000 DR- R0 F600",
    "C X+10.000 Y+5.000 DR+ R0",  # der Vollkreis in zwei Hälften
    # Die Schraube um den Pol (P-2026-10-25-73): von X20 Y5 um −90° nach X25 Y10, Z −2 → −4.
    "CC X+25.0000 Y+5.0000",
    "CP IPA-90 IZ-2.000 DR- R0",
):
    pruefe(satz in saetze_hh, f"Heidenhain fehlt „{satz}“")
pruefe(
    not any("Bogen" in h for h in p_hh.hinweise),
    f"Schraube trotzdem in Geraden: {p_hh.hinweise}",
)
# Ein Bogen über 0,005° (Sehne 0,0004 mm): gerundet stünden Anfang und Ende gleich – jede
# Steuerung führe einen Vollkreis. Er wird eine Gerade; ein Bogen über 359,995° bleibt der
# Vollkreis, der ihm am nächsten ist.
for grad, soll_g in ((0.005, "G1"), (-0.005, "G2")):  # −0,005°: im Uhrzeigersinn 359,995°
    a_w = math.radians(180.0 - grad)
    bogen_w = pp.Abschnitt(
        "W", 1, 1000.0, False, "None",
        [C("G0", {"X": 20.0, "Y": 5.0, "Z": 5.0}), C("G1", {"Z": -2.0, "F": 5.0}),
         C("G2", {"X": 25.0 + 5.0 * math.cos(a_w), "Y": 5.0 + 5.0 * math.sin(a_w), "I": 5.0, "J": 0.0})],
    )  # fmt: skip
    z_bw = pp.programm([bogen_w], pp.steuerung("fanuc"), None, "W").zeilen
    letzter = next(x for x in reversed(z_bw) if x.startswith(("G1 X", "G2 ", "G1 Y")))
    pruefe(letzter.startswith(soll_g), f"Bogen {grad}°: {letzter!r}")
# Eine Schraube mit kaum Drehung (0,005°) ist eine Gerade, kein „CP IPA+0“.
winzig = dataclasses.replace(
    kreise,
    befehle=[C("G0", {"X": 20.0, "Y": 5.0, "Z": 15.0}), C("G1", {"Z": -2.0, "F": 5.0}),
             C("G2", {"X": 20.0 - 5.0 * (1 - math.cos(math.radians(0.005))),
                      "Y": 5.0 + 5.0 * math.sin(math.radians(0.005)), "Z": -2.1, "I": 5.0, "J": 0.0})],
)  # fmt: skip
z_w = [re.sub(r"^\d+ ", "", x) for x in pp.programm([winzig], hh, wp, "W").zeilen]
pruefe(not any(x.startswith("CP ") for x in z_w), f"winzige Schraube: {z_w[-8:]}")
# Die Bohrzyklen als Zyklen der TNC (P-2026-10-25-65): G81 → 200 (eine Zustellung, Q204 zurück
# auf 5), G83 → 200 mit Q202 = 5, G85 → 201 (heraus im Vorschub, G99: Q204 0); je Loch M99.


def zyklus(nummer, name):
    k = (
        saetze_hh.index(f"CYCL DEF {nummer} {name} ~")
        if f"CYCL DEF {nummer} {name} ~" in saetze_hh
        else -1
    )
    if k < 0:
        return k, []
    ende = next(i for i in range(k + 1, len(saetze_hh)) if not saetze_hh[i].startswith("  "))
    return ende, [x.strip().split(" ;")[0] for x in saetze_hh[k + 1 : ende]]


ende, q = zyklus(200, "BOHREN")
pruefe(
    q[:7] == ["Q200=+0", "Q201=-10", "Q206=+120", "Q202=+10", "Q210=+0",
              "Q203=+2", "Q204=+3"]
    and saetze_hh[ende] == "CYCL CALL",
    f"Zyklus 200 (G81): {q} {saetze_hh[ende:ende + 2]}",
)  # fmt: skip
pruefe(
    "  Q202=+5 ;ZUSTELL-TIEFE ~" in saetze_hh and "L X+30.000 R0 FMAX M99" in saetze_hh,
    f"Zyklus 200 (G83): {saetze_hh}",
)
ende, q = zyklus(201, "REIBEN")
pruefe(
    q == ["Q200=+0", "Q201=-8", "Q206=+60", "Q211=+0", "Q208=+60",
          "Q203=+2", "Q204=+0"],
    f"Zyklus 201 (G85): {q}",
)  # fmt: skip
# Ohne den Haken „Bohrzyklen der TNC“: ausgeschrieben wie bisher.
saetze_l = [
    re.sub(r"^\d+ ", "", x)
    for x in pp.programm(
        [bohren], pp.steuerung("heidenhain", {"bohrzyklen": False}), wp, "L"
    ).zeilen
]
for satz in (
    "L Z-8.000 R0 F120",  # G81
    "L Z-20.000 R0",  # G83 bis zur Tiefe
    "L Z-17.500 R0 FMAX",  # G83: im Eilgang bis knapp über die letzte Tiefe
    "L Z-6.000 R0 F60",  # G85 hinein …
):
    pruefe(satz in saetze_l, f"Heidenhain ausgeschrieben fehlt „{satz}“")
g85 = saetze_l.index("L Z-6.000 R0 F60") if "L Z-6.000 R0 F60" in saetze_l else -1
pruefe(saetze_l[g85 + 1] == "L Z+2.000 R0", f"G85 im Vorschub heraus: {saetze_l[g85:g85 + 3]}")
pruefe(
    not any(
        x.split()[0] in ("G0", "G1", "G2", "G3", "G81", "G83", "G85")
        for x in saetze_hh
        if x.strip()
    ),
    "Heidenhain: G-Code übrig",
)
befunde, saetze = pp.nachlesen(p_hh, hh, wp)
pruefe(not befunde and saetze > 10, f"Heidenhain nachgelesen: {[(b.art, b.satz) for b in befunde]}")
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


# --- Gewindebohren (P-2026-10-25-64): FreeCADs Gewinde schreibt in F die Steigung, in S die
# Drehzahl – der Vorschub ist ihr Produkt (bis dahin stand für M10 × 1,5 bei 255 1/min „F90“ da,
# die Steigung als mm/s). Siemens CYCLE84 (SDAC wie vorher), Fanuc M29 davor, Heidenhain Zyklus
# 207 mit M99/CYCL CALL und danach wieder M3; links (G74) die Steigung negativ.
def gewinde_abschnitt(g, rueckwaerts):
    return pp.Abschnitt(
        "Gewinde",
        4,
        255.0,
        rueckwaerts,
        "None",
        [
            C("G90"),
            C("G0", {"Z": 26.0}),
            C("G98"),
            C("G0", {"X": 60.0, "Y": 30.0, "Z": 24.0}),
            C(g, {"X": 60.0, "Y": 30.0, "Z": 6.5, "R": 24.0, "S": 255.0, "F": 1.5}),
            C("G80"),
            C("G0", {"Z": 26.0}),
        ],
        "M10",
    )


rechts, links = gewinde_abschnitt("G84", False), gewinde_abschnitt("G74", True)
g84 = "G84 X60.000 Y30.000 Z6.500 R24.000 F382.500"
for kennung in ("linuxcnc", "haas", "mach"):
    z_g = pp.programm([rechts], pp.steuerung(kennung), fraese, "G").zeilen
    pruefe(g84 in z_g and not any(x.startswith("M29") for x in z_g), f"{kennung} G84: {z_g}")
z_g = pp.programm([rechts], pp.steuerung("fanuc"), fraese, "G").zeilen
i_g = z_g.index(g84) if g84 in z_g else -1
pruefe(i_g > 0 and z_g[i_g - 1] == "M29 S255", f"Fanuc M29 vor G84: {z_g[i_g - 2 : i_g + 1]}")
z_g = pp.programm([rechts], pp.steuerung("siemens"), fraese, "G").zeilen
pruefe(
    "CYCLE84(24.000,24.000,0,6.500,,0.000,3,,1.500,0,255,255)" in z_g
    and not any(x.startswith("G84") for x in z_g),
    f"Siemens CYCLE84: {z_g}",
)
# Mazak (Series M): synchron als G84.2 / G84.3, F ist die Steigung (Handbuch 14-5-21).
z_m = pp.programm([rechts], pp.steuerung("mazak"), fraese, "G")
pruefe("G84.2 X60.000 Y30.000 Z6.500 R24.000 F1.5000" in z_m.zeilen, f"Mazak G84.2: {z_m.zeilen}")
pruefe(not pp.nachlesen(z_m, pp.steuerung("mazak"), fraese)[0], "Mazak nachgelesen")
z_m = pp.programm([links], pp.steuerung("mazak"), fraese, "G").zeilen
pruefe("G84.3 X60.000 Y30.000 Z6.500 R24.000 F1.5000" in z_m, f"Mazak G84.3: {z_m}")
z_g = pp.programm([links], pp.steuerung("siemens"), fraese, "G").zeilen
pruefe("CYCLE84(24.000,24.000,0,6.500,,0.000,4,,-1.500,0,255,255)" in z_g, f"links: {z_g}")
# „Gewindebohren synchron“ aus – für ein Ausgleichsfutter: Siemens CYCLE840, Fanuc ohne M29, Mazak
# G84 … H0 mit F = Steigung · Drehzahl, Heidenhain Zyklus 206 (danach kein M3: Er kehrt die
# Drehrichtung selbst um); LinuxCNC mit dem Haken an: G33.1 – G81 behält dabei G98.
aus = {"gewinde_synchron": False}
z_g = pp.programm([rechts], pp.steuerung("siemens", aus), fraese, "G").zeilen
pruefe("CYCLE840(24.000,24.000,0,6.500,,0.000,0,3,1,,1.500)" in z_g, f"Siemens CYCLE840: {z_g}")
z_g = pp.programm([rechts], pp.steuerung("fanuc", aus), fraese, "G").zeilen
pruefe(g84 in z_g and not any(x.startswith("M29") for x in z_g), f"Fanuc ohne M29: {z_g}")
z_g = pp.programm([rechts, links], pp.steuerung("mazak", aus), fraese, "G").zeilen
pruefe(
    "G84 Z6.500 R24.000 F382.500 H0" in z_g and "G74 Z6.500 R24.000 F382.500 H0" in z_g,
    f"Mazak mit Ausgleichsfutter: {z_g}",
)
z_g = pp.programm(
    [rechts, bohren], pp.steuerung("linuxcnc", {"gewinde_synchron": True}), fraese, "G"
).zeilen
k = z_g.index("G33.1 Z6.500 K1.500") if "G33.1 Z6.500 K1.500" in z_g else -1
pruefe(
    k > 0
    and z_g[k - 1] == "G0 Z24.000"
    and z_g[k + 1] == "G0 Z24.000"
    and "G98" in z_g
    and any(x.startswith("G81 ") for x in z_g),
    f"LinuxCNC G33.1: {z_g}",
)
pruefe(
    not pp.steuerung("haas").gewinde_waehlbar() and pp.steuerung("mazak").gewinde_waehlbar(),
    "Haken nur, wo er etwas ändert",
)
p_g = pp.programm([rechts], pp.steuerung("heidenhain", aus), fraese, "G")
saetze_g = [re.sub(r"^\d+ ", "", x) for x in p_g.zeilen]
k = (
    saetze_g.index("CYCL DEF 206 GEWINDEBOHREN NEU ~")
    if "CYCL DEF 206 GEWINDEBOHREN NEU ~" in saetze_g
    else -1
)
pruefe(
    k > 0
    and "  Q206=+382.5 ;VORSCHUB TIEFENZUST. ~" in saetze_g[k : k + 7]
    and saetze_g[k + 7] == "CYCL CALL"
    and saetze_g[k + 8] != "M3",
    f"Heidenhain 206: {saetze_g[k : k + 10]}",
)
pruefe(
    not pp.nachlesen(p_g, pp.steuerung("heidenhain", aus), fraese)[0], "Heidenhain 206 nachgelesen"
)
langsam = pp.Maschineninfo("Fräse")
langsam.drehzahl_max = 200.0  # über der Höchstdrehzahl: S und F im selben Maß
z_g = pp.programm([rechts], pp.steuerung("linuxcnc"), langsam, "G").zeilen
pruefe(any(x.startswith("G84") and x.endswith("F300.000") for x in z_g), f"begrenzt: {z_g}")
for g, abschnitt, m, q239 in (("G84", rechts, "M3", "+1.5"), ("G74", links, "M4", "-1.5")):
    p_g = pp.programm([abschnitt], hh, fraese, "G")
    saetze_g = [re.sub(r"^\d+ ", "", x) for x in p_g.zeilen]
    k = (
        saetze_g.index("CYCL DEF 207 GEW.-BOHREN GS NEU ~")
        if saetze_g.count("CYCL DEF 207 GEW.-BOHREN GS NEU ~")
        else -1
    )
    pruefe(
        k > 0
        and saetze_g[k + 1 : k + 6]
        == [
            "  Q200=+0 ;SICHERHEITS-ABST. ~",
            "  Q201=-17.5 ;TIEFE ~",
            f"  Q239={q239} ;GEWINDESTEIGUNG ~",
            "  Q203=+24 ;KOOR. OBERFLAECHE ~",
            "  Q204=+0 ;2. SICHERHEITS-ABST.",
        ]
        and saetze_g[k + 6 : k + 8] == ["CYCL CALL", m],
        f"Heidenhain {g}: {saetze_g[k - 2 : k + 9]}",
    )
    befunde, _n = pp.nachlesen(p_g, hh, fraese)
    pruefe(not befunde, f"Heidenhain {g} nachgelesen: {[(b.art, b.satz) for b in befunde]}")
    pruefe(
        not any(x.split()[0] in ("G84", "G74") for x in saetze_g if x.strip()),
        f"Heidenhain {g}: G-Code übrig",
    )

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
MSG = "(MSG, Messstopp: messen, dann NC-Start)"  # LinuxCNC zeigt die Meldung in der Oberfläche
pruefe(
    z_lcnc[k + 1 : k + 6] == ["G53 G0 Z150.000", "M5", "M9", MSG, "M0"], f"Messstopp: {z_lcnc[k:]}"
)
# Nach dem Halt kein rohes „M3“: Die Spindel schaltet die nächste Bearbeitung ein (P-2026-10-18-54).
pruefe(
    not any(x == "M3" or x.startswith("M3 ") for x in z_lcnc[k:]), f"Messstopp, M3: {z_lcnc[k:]}"
)
pruefe(ms.zeilen(25.0, 900.0, kuehlung="Flood")[-1] == "M8", "Messstopp: Kühlung wieder an")
# Tür auf und zu je Steuerung (W-023; Manuel: „es muss variabel bleiben“): vor M0 auf, danach zu.
mit_tuer = pp.steuerung("linuxcnc", {"tuer_auf": "M80\nM81", "tuer_zu": "M82"})
z_tuer = pp.programm([bohren, messen], mit_tuer, fraese, "M").zeilen
k = z_tuer.index("(MESSSTOPP)") if "(MESSSTOPP)" in z_tuer else -1
pruefe(
    z_tuer[k + 2 : k + 9] == ["M5", "M9", "M80", "M81", MSG, "M0", "M82"],
    f"Messstopp Tür: {z_tuer[k:k + 9]}",
)
fhome = pp.steuerung("siemens", {"wechselpunkt_mks": "F_HOME"})
z_sie = pp.programm([bohren, messen], fhome, mit_wp, "M").zeilen
k = z_sie.index("; MESSSTOPP") if "; MESSSTOPP" in z_sie else -1
pruefe(z_sie[k + 1 : k + 3] == ["F_HOME", "M5"], f"Siemens F_HOME: {z_sie[k:]}")
# Siemens: die Meldung in der Meldezeile vor dem Halt, nach dem Start weg.
k = z_sie.index("M0") if "M0" in z_sie else -1
pruefe(
    z_sie[k - 1 : k + 2] == ['MSG("Messstopp: messen, dann NC-Start")', "M0", "MSG()"],
    f"Siemens MSG: {z_sie[k - 2 : k + 3]}",
)
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

# An der Drehmaschine mit angetriebenem Werkzeug (Manuels CLX, Siemens): Der Messstopp schaltet
# den Antrieb aus („M3=5“ der Spindel 3), nicht die Hauptspindel („M5“); nach dem Halt schaltet die
# nächste Bearbeitung ihren Antrieb mit ihrer Drehzahl wieder ein (P-2026-10-18-54).
messen_dreh = pp.Abschnitt(
    "Messstopp", 1, 3000.0, False, "None", [C(z) for z in ms.zeilen(25.0, 2000.0)], "Fräser"
)
schlichten_dreh = dataclasses.replace(rundum, name="Rundum schlichten T1", drehzahl=2000.0)
z_dreh = pp.programm(
    [rundum, messen_dreh, schlichten_dreh], pp.steuerung("siemens"), dreh, "Welle"
).zeilen
k = z_dreh.index("; MESSSTOPP") if "; MESSSTOPP" in z_dreh else -1
nach = z_dreh[k:]
halt = nach.index("M0") if "M0" in nach else -1
pruefe(
    k >= 0 and "M3=5" in nach[:halt] and "M5" not in nach[:halt],
    f"Drehmaschine Messstopp aus: {nach[:halt + 1]}",
)
pruefe(
    halt >= 0 and "M3=3 S3=2000" in nach[halt:] and not any(x.startswith("M3 ") for x in nach),
    f"Drehmaschine nach dem Halt: {nach[halt:halt + 8]}",
)

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

# Brennschneiden wie FreeCADs Plasma-Postprozessor in 26.3 (Leon im Forum, t=107926): „G1 F0“
# ohne Weg (Zünden) fällt weg, F0 kommt in keinen Vorschubsatz, das Mittelpunktsmaß quer zur
# Ebene (K0 in G17, J0 in G18) entfällt – Mach3 und LinuxCNC lehnen beides ab. Ein K, das nicht 0
# ist, bleibt (das wäre eine andere Bahn).
brennen = pp.Abschnitt(
    "Brennen",
    1,
    0.0,
    False,
    "None",
    [
        C("G0", {"X": 0.824, "Y": 0.835}),
        C("G1", {"F": 0.0}),
        C("G3", {"X": 0.949, "Y": 0.710, "I": 0.125, "J": 0.0, "F": 50 / 60}),
        C("G3", {"X": 1.237, "Y": 0.998, "I": 0.0, "J": 0.289, "K": 0.0, "F": 50 / 60}),
        C("G0", {"X": 1.498, "Y": 2.490}),
        C("G1", {"X": 1.498, "Y": 2.490, "F": 0.0}),
        C("G1", {"X": 2.0, "Y": 2.490, "F": 0.0}),
        C("G2", {"X": 3.0, "Y": 2.490, "I": 0.5, "J": 0.0, "K": 0.3, "F": 50 / 60}),
    ],
    "Brenner",
)
for kennung in ("mach", "linuxcnc"):
    zb = [
        re.sub(r"^N\d+ ", "", x)
        for x in pp.programm(
            [brennen], pp.steuerung(kennung), pp.Maschineninfo("Fräse"), "P"
        ).zeilen
    ]
    bewegt = [x for x in zb if x.split()[:1] in (["G0"], ["G1"], ["G2"], ["G3"])]
    pruefe(not any(re.search(r"F0\.0+\b", x) for x in zb), f"{kennung}: F0 {bewegt}")
    pruefe("G3 X1.237 Y0.998 I0.000 J0.289 F50.000" in zb, f"{kennung}: K0 in G17 {bewegt}")
    pruefe("G2 X3.000 Y2.490 I0.500 J0.000 K0.300 F50.000" in zb, f"{kennung}: K≠0 {bewegt}")
    pruefe(
        [x for x in bewegt if x.split()[0] == "G1"] == ["G1 X2.000 Y2.490"],
        f"{kennung}: G1 ohne Weg {bewegt}",
    )
drehbogen = pp.Abschnitt(
    "Drehbogen",
    1,
    1000.0,
    False,
    "None",
    [
        C("G0", {"X": 10.0, "Z": 2.0}),
        C("G2", {"X": 12.0, "Z": 0.0, "I": 2.0, "J": 0.0, "K": 0.0, "F": 1.0}),
    ],
    "Drehmeißel",
)
zd = pp.programm(
    [drehbogen], pp.steuerung("linuxcnc"), pp.Maschineninfo("Drehmaschine", True), "P"
).zeilen
pruefe(
    any(x.startswith("G2 ") and " J" not in x and " K0.000" in x for x in zd),
    f"J0 in G18: {[x for x in zd if x.startswith('G2')]}",
)

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
