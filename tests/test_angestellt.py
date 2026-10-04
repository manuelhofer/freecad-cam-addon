# Prüft den Kugelfräser angestellt (angestellt.py, 5 Achsen simultan S2; Manuel, 2026-10-04: „Ja,
# so bauen“): Die Neigung je Normale – flach verboten ±15°, 20° in der Kippebene geneigt erlaubt ab
# 5°, quer dazu geneigt jede –, so nah an 0 wie erlaubt und höchstens 2° je mm, sonst ein Sprung.
# Dann die Kuppel aus test_schlichten3d (Platte 60 × 60 × 10, Kugel R 25, Kugelfräser Ø 6) als
# „3D-Schlichten“ mit „Anstellen“: je Satz eine Achse; wo die Kugel das Teil berührt, steht die
# Achse mindestens 15° von der Normale weg, an den Flanken senkrecht; die Bahn ist die senkrechte
# (dieselben Mitten der Kugel). Auf der 5-Achs-Maschine Tisch/Tisch kippt nur A (0 … 30°), C steht;
# rechnerisch höchstens 15 % länger als senkrecht. „Programm schreiben“: mit der Maschine G93 und
# A je Satz, ohne sie die senkrechte Bahn und ein Satz dazu.
import math
import os
import pathlib
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
import Part
from Path.Tool.camassets import user_asset_store

from camaddon import abfahren as ab
from camaddon import angestellt as an
from camaddon import beispielmaschine, sprache
from camaddon import job_schnittwerte as js
from camaddon import postprozessor as pp
from camaddon import reichweite as rw
from camaddon import schlichten3d as s3op
from camaddon import schwenken as sw
from camaddon import uebergabe_werkzeuge as ue
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def nah(a, b, genau=1e-6):
    return abs(a - b) <= genau


V = FreeCAD.Vector
sprache.setze_sprache("de")

# --- Die Neigung -------------------------------------------------------------------------------
flach = an.verboten((0.0, 0.0, 1.0), "X")
pruefe(nah(flach[0], -15.0) and nah(flach[1], 15.0), f"flach verboten {flach}")
w = math.radians(20.0)
schraeg = an.verboten((0.0, -math.sin(w), math.cos(w)), "X")  # 20° in Kipprichtung geneigt
pruefe(nah(schraeg[0], 5.0) and nah(schraeg[1], 35.0), f"20° geneigt verboten {schraeg}")
pruefe(an.verboten((math.sin(w), 0.0, math.cos(w)), "X") is None, "quer geneigt verboten")
pruefe(nah(math.degrees(math.acos(an.gekippt(15.0, "X")[2])), 15.0), "gekippt um 15°")
# Flach: der erste Punkt springt auf die Grenze, dann bleibt er dort; danach erlaubt: zurück mit
# 2° je mm.
reihe = an.neigungen([0.0, 0.5, 0.5, 1.0, 1.0], [flach, flach, None, None, None])
pruefe([round(x, 6) for x in reihe] == [-15.0, -15.0, -14.0, -12.0, -10.0], f"Neigungen {reihe}")

# --- Die Kuppel als „3D-Schlichten“ ---------------------------------------------------------------
platte = Part.makeBox(60, 60, 10)
kappe = Part.makeSphere(25, V(30, 30, -5)).common(Part.makeBox(60, 60, 15, V(0, 0, 10)))
teil = platte.fuse(kappe).removeSplitter()
kugel = [f"Face{i + 1}" for i, f in enumerate(teil.Faces) if isinstance(f.Surface, Part.Sphere)]

import Path.Main.Job as PathJob  # noqa: E402

t3 = wz.Werkzeug(
    nummer=3,
    name="Kugel 6",
    art=wz.KUGELFRAESER,
    durchmesser=6.0,
    schneiden=2,
    schneidenlaenge=12.0,
    schneidstoff=wz.VHM,
)
t3.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=0.3, vc=150.0, fz=0.05)]
user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))
ue.uebergeben(wz.Bibliothek([wz.standardwerkzeug(), t3]))
doc = FreeCAD.newDocument("Angestellt")
objekt = doc.addObject("Part::Feature", "Teil")
objekt.Shape = teil
doc.recompute()
job = PathJob.Create("Job", [objekt])
job.Stock.ExtZpos = 0.0
doc.recompute()
tc = js.controller_ohne_transaktion(doc, job, t3, t3.schnittwerte[wz.ALLE][0])
doc.recompute()
op = s3op.lege_an(job, tc, 0.01, flaechen=kugel)
doc.recompute()
pruefe(not op.Anstellen and len(op.Werkzeugachsen) == 0, "ohne Anstellen schon Achsen")
pruefe(not an.ist_angestellt(op), "ohne Anstellen angestellt")
op.Anstellen = True
op.recompute()
befehle = list(op.Path.Commands)
achsen = [tuple(v) for v in op.Werkzeugachsen]
pruefe(len(achsen) == len(befehle), f"{len(achsen)} Achsen zu {len(befehle)} Sätzen")
pruefe(an.ist_angestellt(op), "mit Anstellen nicht angestellt")
pruefe(not any(b.Name in ("G2", "G3") for b in befehle), "angestellt noch Bögen in der Bahn")

# Wo die Kugel das Teil berührt: mindestens 15° zwischen Achse und Normale; an den Flanken senkrecht.
vorschub = [(b, a) for b, a in zip(befehle, achsen, strict=True) if b.Name == "G1"]
spitzen = [(b.Parameters["X"], b.Parameters["Y"], b.Parameters["Z"]) for b, _a in vorschub]
normalen = an.normalen(teil, spitzen, 3.0)
winkel = [
    math.degrees(math.acos(max(-1.0, min(1.0, sum(x * y for x, y in zip(n, a, strict=True))))))
    for n, (_b, a) in zip(normalen, vorschub, strict=True)
    if n is not None
]
neigung = [math.degrees(math.acos(a[2])) for _b, a in vorschub]
senkrecht = sum(1 for x in neigung if x < 1e-6)
print(
    ascii(
        f"Kuppel: {len(befehle)} Sätze, kleinster Winkel {min(winkel):.3f}°, Neigung bis "
        f"{max(neigung):.1f}°, senkrecht {senkrecht} von {len(neigung)}"
    )
)
pruefe(min(winkel) >= 15.0 - 1e-6, f"kleinster Winkel zur Normale {min(winkel):.3f}°")
pruefe(max(neigung) <= 31.0, f"Neigung bis {max(neigung):.1f}°")
pruefe(senkrecht > len(neigung) // 4, f"senkrecht nur {senkrecht} von {len(neigung)}")
pruefe(all(abs(a[0]) < 1e-12 for a in achsen), "um X gekippt, aber X der Achse nicht 0")
# Die Kugel fährt die senkrechte Bahn: Mitte = Spitze senkrecht + R.
bahn = an.punkte(befehle, achsen, 3.0)
mitten = [tuple(s + 3.0 * a for s, a in zip(p.spitze, p.achse, strict=True)) for p in bahn]
senkrechte = an.punkte(befehle, [an.SENKRECHT] * len(befehle), 3.0)
abweichung = max(
    math.dist(m, tuple(s + 3.0 * a for s, a in zip(q.spitze, q.achse, strict=True)))
    for m, q in zip(mitten, senkrechte, strict=True)
)
pruefe(abweichung < 1e-9, f"Mitte der Kugel verschoben um {abweichung}")

# --- Auf der 5-Achs-Maschine Tisch/Tisch -----------------------------------------------------------
asm, ma = beispielmaschine.fuenfachs_tisch_tisch()
pruefung = rw.Pruefung(asm, ma)
null = rw.nullpunkt(job)
maschine = sw.Maschine(
    pruefung, pruefung.werkzeugaufnahme(tc.ToolNumber), rw.einspannung(tc, None), null
)
pruefe(an.kippachse(maschine) == "X", f"Kippachse {an.kippachse(maschine)}")
saetze = an.befehle(op, maschine)
bewegt = [b for b in saetze if b.Name in ("G0", "G1")]
a_werte = [float(b.Parameters["A"]) for b in bewegt if "A" in b.Parameters]
c_werte = [float(b.Parameters["C"]) for b in bewegt if "C" in b.Parameters]
print(
    ascii(
        f"Maschine: A {min(a_werte):.1f} ... {max(a_werte):.1f}, C {min(c_werte)} ... {max(c_werte)}"
    )
)
pruefe(max(c_werte) - min(c_werte) < 1e-3, f"C dreht: {min(c_werte)} ... {max(c_werte)}")
pruefe(max(abs(x) for x in a_werte) > 10.0, f"A kippt nicht: {max(abs(x) for x in a_werte)}")
pruefe(saetze[-1].Name == "G0" and nah(float(saetze[-1].Parameters["A"]), 0.0), "am Ende A nicht 0")
pruefe(any(b.Name == "G93" for b in saetze), "kein G93")

ergebnis = rw.Pruefung(asm, ma).pruefe_job(job)
pruefe(
    not any(
        "„3D-Schlichten T3“" in str(h) or "3D-Schlichten T3:" in str(h) for h in ergebnis.hinweise
    ),
    f"Hinweise: {[str(h) for h in ergebnis.hinweise]}",
)
angestellt = ab.abfahrt(pruefung, job, null).stationen[-1].zeit
op.Anstellen = False
op.recompute()
senkrecht_zeit = ab.abfahrt(pruefung, job, null).stationen[-1].zeit
print(ascii(f"Zeit: angestellt {angestellt / 60:.2f} min, senkrecht {senkrecht_zeit / 60:.2f} min"))
pruefe(
    senkrecht_zeit <= angestellt <= 1.15 * senkrecht_zeit,
    f"angestellt {angestellt:.0f} s, senkrecht {senkrecht_zeit:.0f} s",
)

# --- Programm schreiben ------------------------------------------------------------------------
op.Anstellen = True
op.recompute()
mit = pp.abschnitte(job, maschine)
pruefe(
    len(mit) == 1 and not mit[0].hinweis and any("A" in dict(b.Parameters) for b in mit[0].befehle),
    "mit Maschine ohne A",
)
ohne = pp.abschnitte(job)
pruefe(
    len(ohne) == 1
    and ohne[0].hinweis
    and [b.toGCode() for b in ohne[0].befehle] == [b.toGCode() for b in op.Path.Commands],
    "ohne Maschine nicht senkrecht mit Satz",
)
zeilen = pp.programm(mit, pp.steuerung("siemens"), pp.Maschineninfo(), "Kuppel").zeilen
pruefe(
    any(z.startswith("G93") or " G93" in z for z in zeilen) and any(" A" in z for z in zeilen),
    "im Programm kein G93 oder A",
)
# Nachgelesen wie an der Steuerung (programm_pruefen): an jeder Steuerung nichts – auch mit TCPM
# (Haken): die Spitze im Werkstück, F in mm/min; verdichtet nur, wo die Mitte der Kugel sonst
# von ihrer Geraden abwiche – nicht mehr Sätze als ohne (die Bahn hat ohnehin Punkte alle 0,5 mm:
# 10 695 statt 10 699).
for kennung in pp.STEUERUNGEN:
    for aenderung in ({}, {"tcpm": True}):
        s = pp.steuerung(kennung, aenderung)
        befunde, _saetze = pp.nachlesen(pp.programm(mit, s, pp.Maschineninfo(), "Kuppel"), s)
        pruefe(not befunde, f"{kennung} {aenderung}: {[(b.art, b.satz) for b in befunde[:3]]}")
ohne_tcpm = pp.programm(mit, pp.steuerung("siemens"), pp.Maschineninfo(), "Kuppel")
mit_tcpm = pp.programm(mit, pp.steuerung("siemens", {"tcpm": True}), pp.Maschineninfo(), "K")
print(ascii(f"Kuppel: {ohne_tcpm.saetze} Saetze ohne TCPM, {mit_tcpm.saetze} mit"))
pruefe(
    "TRAORI" in mit_tcpm.zeilen
    and "TRAFOOF" in mit_tcpm.zeilen
    and mit_tcpm.saetze <= ohne_tcpm.saetze
    and not any("TCPM" in h for h in mit_tcpm.hinweise),
    f"TCPM: {mit_tcpm.saetze} Sätze, ohne {ohne_tcpm.saetze}, {mit_tcpm.hinweise}",
)

FreeCAD.closeDocument(doc.Name)
if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
