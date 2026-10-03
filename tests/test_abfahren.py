# Prüft das Abfahren (W-001, Stufe 4b und 4d; abfahren.py): Aus der Bahn eines Jobs werden
# Stationen mit ihrer Zeit – Vorschubsätze mit F (mm/s), Eilgang je Achse aus der
# Maschine, die langsamste bestimmt; Kreise in 5°-Schritten, nach dem Bohrzyklus
# der Rückzug. Dazu die Beschleunigung der Maschine (fahrzeit): ein Satz vom Stand in den
# Stand mit dem Tempo v und der Beschleunigung a dauert L ÷ v + v ÷ a (reicht der Weg nicht,
# 2·√(L ÷ a)); durch den Kreis fährt die Maschine durch, vor und nach einem Eilgang und an
# Ecken hält sie. Die Zeiten gegen Handrechnung an der Beispiel-Fräse; zwischen zwei
# Stationen fährt die Maschine geradlinig (stellungen_bei); eine Rundachse im
# Vorschub zählt in Grad; ohne F gilt 1000 mm/min mit Hinweis; der Revolver
# schwenkt zwischen zwei Werkzeugen, auch in einem Vorschubsatz ohne Weg; Kreise
# halten auch an den Umkehrstellen der Achsen, sodass jede Überschreitung eine
# Station ist; Punkte, die eine Drehmaschine ohne Y nicht erreicht, lassen sie
# stehen.
import math
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)
sys.path.insert(0, os.path.join(ADDON, "tests"))

import beispielmaschinen
import FreeCAD

from camaddon import abfahren as ab
from camaddon import beispielmaschine, sprache
from camaddon import maschine as m
from camaddon import reichweite as rw
from camaddon import verfahren as vf
from camaddon import werkzeuge as wz

sprache.setze_sprache("de")
fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def nahe(a, b, genau=1e-6):
    return a is not None and b is not None and abs(a - b) < genau


def neuer_job(ops, name="Teil"):
    """Ein Dokument mit einem Quader und einem Job; `ops`: je Operation (G-Code, T-Nummer)."""
    import Path.Main.Job as PathJob
    import Path.Op.Custom as PathCustom

    doc = FreeCAD.newDocument(name)
    quader = doc.addObject("Part::Box", "Teil")
    quader.Length, quader.Width, quader.Height = 100, 60, 20
    doc.recompute()
    job = PathJob.Create("Job", [quader])
    for i, (zeilen, nummer) in enumerate(ops):
        op = PathCustom.Create(f"Op{i + 1}")
        op.Gcode = zeilen
        if nummer != 1:
            from Path.Tool import Controller

            tc = Controller.Create(f"TC{nummer}", toolNumber=nummer)
            job.Proxy.addToolController(tc)
            op.ToolController = tc
    doc.recompute()
    return doc, job


def namen(maschine, stellungen):
    return {vf.namen(maschine, a): round(s, 6) for a, s in stellungen.items()}


# --- 3-Achs-Fräse: Zeiten gegen Handrechnung ---------------------------------------------
asm, ma = beispielmaschine.fraesmaschine()
p = rw.Pruefung(asm, ma)
A = 3000.0  # mm/s²: die Achsen der Beispiel-Fräse beschleunigen mit 3 m/s²


def satz(weg, v, a=A):
    """Vom Stand in den Stand: Trapez L ÷ v + v ÷ a, Dreieck 2·√(L ÷ a)."""
    return weg / v + v / a if weg >= v * v / a else 2 * math.sqrt(weg / a)


bahn = [
    "G0 X0 Y0 Z10",
    "G1 Z-5 F10",  # 15 mm mit 10 mm/s: 1,5 s + 10/3000 s fürs Anfahren und Bremsen
    "G1 X100",  # 100 mm: 10 s + 10/3000 s (Ecke davor und danach: der Kreis beginnt zurück)
    "G2 X120 Y20 I0 J20",  # 270° um (100, 20), r 20: 54 Sehnen zu 5° – in einem Zug
    "G0 Z10",  # Z1 15 mm im Eilgang 15 000 mm/min = 250 mm/s: Dreieck 2·√(15/3000)
    "G81 X50 Y30 Z-8 R3 F5",  # hin (X1 70 mm), auf R (7 mm), 11 mm mit 5 mm/s, zurück 18 mm
    "G80",
]
teil, job = neuer_job([(bahn, 1)])
fahrt = ab.abfahrt(p, job, FreeCAD.Vector())
namen_achsen = [vf.namen(ma, a) for a in fahrt.achsen]
pruefe(namen_achsen == ["Y1", "Z1", "X1"], f"Achsen: {namen_achsen}")
st = fahrt.stationen
pruefe(len(st) == 1 + 1 + 1 + 53 + 1 + 1 + 4, f"Stationen: {len(st)}")
gerade_1, gerade_2 = satz(15, 10), satz(15, 10) + satz(100, 10)
pruefe(
    nahe(st[1].zeit, gerade_1) and nahe(st[2].zeit, gerade_2),
    f"Geraden: {st[1].zeit}, {st[2].zeit}",
)
sehne = 2 * 20 * math.sin(math.radians(2.5))
ende_kreis = gerade_2 + satz(54 * sehne, 10)
pruefe(nahe(st[56].zeit, ende_kreis), f"Kreis: {st[56].zeit} statt {ende_kreis}")
# Satz 6: FreeCAD stellt der Operation „Eigene“ zwei Kommentare voran.
pruefe(st[56].satz == 6 and st[30].satz == 6 and not st[30].eilgang, "Kreis: Satz 6, Vorschub")
pruefe(nahe(st[57].zeit - st[56].zeit, satz(15, 250)), f"Eilgang Z: {st[57].zeit - st[56].zeit}")
bohren = [round(st[i].zeit - st[i - 1].zeit, 6) for i in range(58, 62)]
# Hin: X1 70 mm mit 20 000 mm/min (Y1 30 mm ist schneller fertig), dann Z1 im Eilgang.
erwartet = [satz(70, 20000 / 60), satz(7, 250), satz(11, 5), satz(18, 250)]
pruefe(bohren == [round(z, 6) for z in erwartet], f"Bohrzyklus: {bohren} statt {erwartet}")
pruefe([s.eilgang for s in st[58:62]] == [True, True, False, True], "Bohrzyklus: Eilgang")
pruefe(st[61].punkt == (50, 30, 10), f"Rückzug auf die Ausgangshöhe: {st[61].punkt}")
gesamt = ende_kreis + satz(15, 250) + sum(erwartet)
pruefe(nahe(fahrt.dauer, gesamt), f"Dauer: {fahrt.dauer} statt {gesamt}")
pruefe(fahrt.hinweise == [], f"Hinweise: {fahrt.hinweise}")
op = fahrt.operationen[0]
pruefe(
    op.name == "Op1" and op.erste == 0 and op.saetze == len(job.Operations.Group[0].Path.Commands),
    "",
)

# Dazwischen geradlinig: Mitten auf der Geraden X 0 → 100 steht X1 auf −50.
mitte = namen(ma, fahrt.stellungen_bei((st[1].zeit + st[2].zeit) / 2))
pruefe(mitte == {"X1": -50, "Y1": 0, "Z1": -85}, f"Mitte der Geraden: {mitte}")
pruefe(fahrt.index_bei(0) == 0 and fahrt.index_bei(st[1].zeit) == 1, "index_bei")
pruefe(fahrt.index_bei(-1) == 0 and fahrt.index_bei(1e9) == len(st) - 1, "index_bei außerhalb")
anfang = namen(ma, fahrt.stellungen_bei(0))
pruefe(anfang == {"X1": 0, "Y1": 0, "Z1": -70}, f"Anfang: {anfang}")
# Jede Station trifft: dieselben Stellungen wie die Reichweite für ihren Punkt.
spindel = p.werkzeugaufnahme(1)
for i in (0, 20, 57, 60):
    erwartet = namen(ma, p.stellungen(st[i].punkt, spindel, 50, FreeCAD.Vector()))
    pruefe(namen(ma, fahrt.stellungen_bei(st[i].zeit)) == erwartet, f"Station {i}")
    pruefe(namen(ma, fahrt.stellungen_an(i)) == erwartet, f"stellungen_an({i})")

# Ohne F: 1000 mm/min, mit Hinweis.
op2 = job.Operations.Group[0]
op2.Gcode = ["G0 X0 Y0 Z10", "G1 Z0"]
teil.recompute()
fahrt = ab.abfahrt(p, job, FreeCAD.Vector())
pruefe(nahe(fahrt.dauer, satz(10, 1000 / 60)), f"ohne F: {fahrt.dauer}")
pruefe(
    fahrt.hinweise
    == [
        "„Op1“ hat keinen Vorschub – abgefahren mit 1000 mm/min. Den Vorschub setzt der "
        "Werkzeug-Controller (oder „Schnittwerte in den Job“)."
    ],
    f"Hinweis ohne F: {fahrt.hinweise}",
)

# Die Umkehrstellen eines Kreises sind Stationen, auch abseits der 5°-Schritte: Jede
# Überschreitung der Reichweite liegt genau auf einer Station (dorthin springt ein Klick
# im Fenster). Vollkreis um (−240, 3) mit r = √109 ≈ 10,44: ganz links X −250,44, also
# X1 250,44 – über der Grenze 250.
op2.Gcode = ["G0 X-230 Y0 Z10", "G2 X-230 Y0 I-10 J3 F10"]
teil.recompute()
fahrt = ab.abfahrt(p, job, FreeCAD.Vector())
pruefe(len(fahrt.stationen) == 1 + 71 + 4 + 1, f"Vollkreis, Stationen: {len(fahrt.stationen)}")
ueber = p.pruefe_job(job, FreeCAD.Vector()).ueberschreitungen
pruefe([u.name for u in ueber] == ["X1"], f"Vollkreis, Überschreitungen: {ueber}")
index = fahrt.station_von(ueber[0]) if ueber else None
pruefe(
    index is not None and nahe(fahrt.stationen[index].punkt[0], -240 - math.sqrt(109)),
    f"Station der Überschreitung: {index}",
)
anschlag = fahrt.stellungen_bei(fahrt.stationen[index].zeit) if index is not None else {}
x1 = next(a for a in fahrt.achsen if vf.namen(ma, a) == "X1")
pruefe(nahe(anschlag.get(x1), 240 + math.sqrt(109)), f"X1 dort: {anschlag.get(x1)}")
# So fährt der Abspieler: alle Achsen auf einmal, jede höchstens bis zu ihrer Grenze –
# zurück kommen die, die an einer Grenze halten.
y1 = next(a for a in fahrt.achsen if vf.namen(ma, a) == "Y1")
angehalten = p.verfahren.setze_alle(anschlag)
pruefe(angehalten == [x1], f"setze_alle, angehalten: {angehalten}")
pruefe(
    nahe(p.verfahren.stellung(x1), 250) and nahe(p.verfahren.stellung(y1), anschlag[y1]),
    f"setze_alle: X1 {p.verfahren.stellung(x1)}, Y1 {p.verfahren.stellung(y1)}",
)
p.verfahren.grundstellung()
FreeCAD.closeDocument(teil.Name)
FreeCAD.closeDocument(asm.Document.Name)

# --- Home- und Wechselpunkt (Spezifikation Simulation 13, P-2026-10-02-48) -----------------
# Mit Home-Punkt beginnt das Abfahren dort, fährt erst X und Y über den ersten Punkt, dann Z
# hinunter; vor dem Werkzeugwechsel erst Z zum Wechselpunkt, dann X und Y; am Ende zurück
# zum Home-Punkt, wieder Z zuerst. Ohne Home-Punkt bleibt alles wie zuvor.
asm, ma = beispielmaschine.fraesmaschine()
p = rw.Pruefung(asm, ma)
heim = {"X1": 100.0, "Y1": 50.0, "Z1": 0.0}
for ba in m.betriebsarten(ma):
    if ba.Art == m.ART_LINEAR and ba.NcName in heim:
        ba.Home, ba.HomeAn = heim[ba.NcName], True
        if ba.NcName == "X1":
            ba.Wechsel, ba.WechselAn = 200.0, True  # Y1 und Z1: wie Home
wechsel = dict(heim, X1=200.0)
erste = ["G0 X0 Y0 Z10", "G1 Z-5 F10", "G0 Z10"]
zweite = ["G0 X50 Y30 Z10", "G1 Z-5 F10", "G0 Z10"]
teil, job = neuer_job([(erste, 1), (zweite, 2)], "Heim")
fahrt = ab.abfahrt(p, job, FreeCAD.Vector())
st = fahrt.stationen
ziele = [s.ziel for s in st]
H, W = ab.HOME, ab.WECHSEL
pruefe(
    ziele == [H, H, "", "", "", W, W, W, "", "", "", H, H],
    f"Home/Wechsel: {ziele}",
)
if len(st) == 13:
    pruefe(
        namen(ma, fahrt.stellungen_an(0)) == heim, f"Anfang: {namen(ma, fahrt.stellungen_an(0))}"
    )
    an_1, an_2 = namen(ma, fahrt.stellungen_an(1)), namen(ma, fahrt.stellungen_an(2))
    pruefe(
        an_1["Z1"] == heim["Z1"] and (an_1["X1"], an_1["Y1"]) == (an_2["X1"], an_2["Y1"]),
        f"Anfahrt: erst X/Y {an_1}, dann Z {an_2}",
    )
    an_5 = namen(ma, fahrt.stellungen_an(5))
    pruefe(
        an_5["Z1"] == wechsel["Z1"] and an_5["X1"] == namen(ma, fahrt.stellungen_an(4))["X1"],
        f"Wechsel: erst Z {an_5}",
    )
    pruefe(namen(ma, fahrt.stellungen_an(6)) == wechsel, f"Wechselpunkt: {fahrt.stellungen_an(6)}")
    pruefe(
        [s.operation for s in st[4:8]] == [0, 0, 0, 1] and fahrt.operationen[1].erste == 7,
        f"Operationen: {[s.operation for s in st]}, erste {fahrt.operationen[1].erste}",
    )
    pruefe(namen(ma, fahrt.stellungen_an(12)) == heim, f"Ende: {fahrt.stellungen_an(12)}")
    pruefe(all(s.eilgang for s in st if s.ziel), "Home/Wechsel nicht im Eilgang")
    pruefe(all(st[i].zeit > st[i - 1].zeit for i in range(1, len(st))), "Zeiten steigen nicht")
    # Die Spitze im Programm am Home-Punkt: X/Y wie die Anfahrt darüber nicht, Z darüber.
    pruefe(st[0].punkt[2] > 10 and st[1].punkt[:2] == st[2].punkt[:2], f"Punkte: {st[0].punkt}")
mit_heim = fahrt.dauer
# Die Zeit des Wechsels selbst (Spezifikation Simulation 13): 10 s je Wechsel – T1 → T2 einmal.
ma.Wechselzeit = 10.0
mit_zeit = ab.abfahrt(p, job, FreeCAD.Vector())
pruefe(
    mit_zeit.werkzeugwechsel == 1 and abs(mit_zeit.dauer - mit_heim - 10.0) < 1e-6,
    f"Wechselzeit: {mit_zeit.dauer - mit_heim:.3f} s mehr, {mit_zeit.werkzeugwechsel} Wechsel",
)
vor_v, vor_e = fahrt.anteile()
mit_v, mit_e = mit_zeit.anteile()
pruefe(
    abs(mit_v - vor_v) < 1e-6 and abs(mit_e - vor_e) < 1e-6,
    f"Wechselzeit in Vorschub/Eilgang: {mit_v - vor_v:.3f}, {mit_e - vor_e:.3f}",
)
ma.Wechselzeit = 0.0
# Ein Messstopp zwischen zwei Operationen (Spezifikation Strategien 12.4): Er fährt an den
# Wechselpunkt wie der Postprozessor – erst Z, dann alle –, die Operation danach kommt von dort;
# sein eigenes „G0 Z…“ fährt er nicht.
from camaddon import messstopp as ms  # noqa: E402

teil_m, job_m = neuer_job([(erste, 1), (ms.zeilen(25.0, 900.0), 1), (zweite, 1)], "Messen")
fahrt_m = ab.abfahrt(p, job_m, FreeCAD.Vector())
im_messstopp = [s.ziel for s in fahrt_m.stationen if s.operation == 1]
pruefe(im_messstopp == [W, W], f"Messstopp: {im_messstopp}")
pruefe(fahrt_m.werkzeugwechsel == 0, f"Messstopp als Wechsel gezählt: {fahrt_m.werkzeugwechsel}")
pruefe(
    namen(ma, fahrt_m.stellungen_an(fahrt_m.operationen[1].erste + 1)) == wechsel,
    "Messstopp nicht am Wechselpunkt",
)
FreeCAD.closeDocument(teil_m.Name)
# Der Wechselpunkt in WKS (Manuel, 2026-10-03: „sollte MKS sein … oder wechselbar“): X 200 ist
# dann die Spitze im Programm – die Operation davor endete bei (0, 0, 10), zum Wechsel fährt
# nur X, auf (200, 0, 10); Y und Z haben keinen eigenen Wechselpunkt und bleiben stehen.
pruefe(m.wechsel_bezug(ma) == m.WECHSEL_MKS, f"Vorgabe: {m.wechsel_bezug(ma)}")
ma.WechselBezug = m.WECHSEL_WKS
fahrt = ab.abfahrt(p, job, FreeCAD.Vector())
am_wechsel = [s for s in fahrt.stationen if s.ziel == ab.WECHSEL]
# Die Stationen zum Wechsel: am Wechselpunkt (Z hat keinen Wert – kein Schritt „erst Z“), dann
# über den ersten Punkt der nächsten Operation.
pruefe(
    len(am_wechsel) == 2
    and all(
        abs(a - b) < 1e-6 for a, b in zip(am_wechsel[0].punkt, (200.0, 0.0, 10.0), strict=True)
    ),
    f"WKS: Spitze am Wechselpunkt {[s.punkt for s in am_wechsel]}",
)
pruefe(m.wechselpunkt(ma) == {"X": 200.0}, f"WKS: wechselpunkt {m.wechselpunkt(ma)}")
ma.WechselBezug = m.WECHSEL_MKS
pruefe(
    m.wechselpunkt(ma) == {"X": 200.0, "Y": 50.0, "Z": 0.0},
    f"MKS: wechselpunkt {m.wechselpunkt(ma)} (Y und Z wie Home)",
)
for ba in m.betriebsarten(ma):
    if ba.Art == m.ART_LINEAR:
        ba.HomeAn = ba.WechselAn = False
fahrt = ab.abfahrt(p, job, FreeCAD.Vector())
pruefe(
    len(fahrt.stationen) == 6 and not any(s.ziel for s in fahrt.stationen),
    f"ohne Home: {[s.ziel for s in fahrt.stationen]}",
)
pruefe(fahrt.dauer < mit_heim, f"ohne Home nicht kürzer: {fahrt.dauer} / {mit_heim}")
FreeCAD.closeDocument(teil.Name)
FreeCAD.closeDocument(asm.Document.Name)

# --- Rundachse im Vorschub: Grad durch F ---------------------------------------------------
# A1 ohne eingetragene Beschleunigung: die Vorgabe 1 U/s² = 360 °/s², einmal anfahren und
# bremsen auf dem ganzen Schwenk (die 1°-Schritte liegen in einer Richtung).
asm, ma = beispielmaschine.fuenfachs_tisch_tisch()
p = rw.Pruefung(asm, ma)
teil, job = neuer_job([(["G0 X0 Y0 Z50 A0", "G1 A90 F10"], 1)], "Schwenkteil")
fahrt = ab.abfahrt(p, job, FreeCAD.Vector())
pruefe(len(fahrt.stationen) == 1 + 90, f"A in 1°-Schritten: {len(fahrt.stationen)}")
pruefe(nahe(fahrt.dauer, satz(90, 10, 360)), f"A 90° mit 10 °/s: {fahrt.dauer}")
halb = namen(ma, fahrt.stellungen_bei(fahrt.stationen[45].zeit))
pruefe(nahe(halb["A1"], 45) and nahe(halb["C1"], 0), f"halb geschwenkt: {halb}")
FreeCAD.closeDocument(teil.Name)
FreeCAD.closeDocument(asm.Document.Name)

# --- Drehmaschine: der Revolver schwenkt zwischen zwei Werkzeugen --------------------------
asm, ma = beispielmaschine.drehmaschine()
p = rw.Pruefung(asm, ma)
teil, job = neuer_job([(["G0 X40 Y0 Z80"], 1), (["G0 X40 Y0 Z80"], 2)], "Drehteil")
fahrt = ab.abfahrt(p, job)
revolver = next(a for a in fahrt.achsen if vf.namen(ma, a) == "T")
plaetze = dict(vf.platzstellungen(p.verfahren, ma, revolver))
k = fahrt.achsen.index(revolver)
t = [s.stellungen[k] for s in fahrt.stationen]
pruefe(nahe(t[0], plaetze["P1"]) and nahe(t[1], plaetze["P2"]), f"Revolver: {t} statt {plaetze}")
pruefe([o.name for o in fahrt.operationen] == ["Op1", "Op2"], "zwei Operationen")
pruefe(fahrt.operationen[1].erste == 1 and fahrt.stationen[1].operation == 1, "zweite beginnt")
# Die Schaltzeit von T (0,25 s für 180°) bremst den Wechsel mindestens auf 30°/720°/s.
pruefe(fahrt.dauer >= 30 / 720 - 1e-9, f"Wechsel: {fahrt.dauer}")
# Auch im Vorschub: G1 auf denselben Punkt ist kein Weg, aber der Revolver schwenkt.
job.Operations.Group[1].Gcode = ["G1 X40 Y0 Z80 F10"]
teil.recompute()
fahrt = ab.abfahrt(p, job)
pruefe(
    fahrt.dauer >= 30 / 720 - 1e-9 and not fahrt.stationen[1].eilgang,
    f"Wechsel im Vorschub: {fahrt.dauer}",
)
FreeCAD.closeDocument(teil.Name)
FreeCAD.closeDocument(asm.Document.Name)

# --- Drehmaschine ohne Y: ein Punkt quer daneben lässt die Maschine stehen ------------------
asm, ma = beispielmaschinen.drehmaschine_komplett()
p = rw.Pruefung(asm, ma)
platz = p.werkzeugaufnahme(1)
achsen = {vf.namen(ma, a): a for a in p.kette.achsen}
# Ein erreichbarer Punkt: wo die Spitze steht, wenn X1 um 10 und Z1 um 20 fährt (C4 auf 0,
# wie ohne C in der Bahn) – und einer 5 mm quer zu X1 und Z1.
verfahren = vf.Verfahren(asm, p.kette)
verfahren.setze(achsen["X1"], verfahren.stellung(achsen["X1"]) + 10)
verfahren.setze(achsen["Z1"], verfahren.stellung(achsen["Z1"]) + 20)
verfahren.setze(achsen["C4"], 0.0, grenzen=False)
spitze = m.globale_platzierung(platz.Lcs).multVec(FreeCAD.Vector(0, 0, -30))
job_lage = m.globale_platzierung(p.werkstueckaufnahme.Lcs)
verfahren.grundstellung()
punkt = job_lage.inverse().multVec(spitze)
quer = job_lage.Rotation.inverted().multVec(achsen["X1"].richtung.cross(achsen["Z1"].richtung))
daneben = punkt + quer * 5
teil, job = neuer_job(
    [
        (
            [
                f"G0 X{punkt.x:.6f} Y{punkt.y:.6f} Z{punkt.z:.6f}",
                f"G1 X{daneben.x:.6f} Y{daneben.y:.6f} Z{daneben.z:.6f} F10",
            ],
            1,
        )
    ],
    "OhneY",
)
# Mit 30 mm Werkzeuglänge wie beim Messen oben – über die Werkzeugverwaltung (Ø 5 mm wie
# das CAM-Werkzeug, T1).
bibliothek = wz.Bibliothek([wz.Werkzeug(nummer=1, durchmesser=5.0, laenge_spindelnase=30.0)])
fahrt = ab.abfahrt(p, job, FreeCAD.Vector(), bibliothek)
pruefe(len(fahrt.stationen) == 2, f"ohne Y, Stationen: {len(fahrt.stationen)}")
pruefe(fahrt.stationen[0].stellungen is not None, "ohne Y: erster Punkt nicht erreichbar")
pruefe(fahrt.stationen[1].stellungen is None, "ohne Y: Punkt quer daneben erreichbar?")
pruefe(fahrt.wirksam(1) == fahrt.wirksam(0), "ohne Y: Maschine bleibt nicht stehen")
FreeCAD.closeDocument(teil.Name)
FreeCAD.closeDocument(asm.Document.Name)

assert not fehler, "\n".join(fehler)
print("OK", os.path.basename(__file__))
