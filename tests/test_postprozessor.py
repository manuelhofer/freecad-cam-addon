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

if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
