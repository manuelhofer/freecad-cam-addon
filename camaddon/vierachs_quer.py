# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Spirale mit der Querachse für jeden Fräser (Spezifikation W-003, V5e).

Manuel (2026-10-03): „das Spiralisieren um das Bauteil herum nicht nur mit X und Z und C,
sondern eben auch Y mitnehmen … die lange Gerade exakt vom Winkel her zur Y-Achse … mit der
Y-Achse fahren, ohne C zu bewegen“; danach: „ja, mach weiter“ – für Schaft- und Torusfräser und
fürs Schruppen.

Der Plan kommt von einer Kugel mit dem Radius des Fräsers (vierachs_bahn.normale_quer): je Punkt
die Richtung ψ der Werkzeugachse (die Normale der Hüllfläche im Querschnitt) und die Mitte der
Kugel. Für die Kugel ist das schon die Stellung. Ein anderer Fräser steht mit seiner Achse durch
dieselbe Mitte: Auf einer ebenen Fläche liegt seine Stirn dann flach auf (die Mitte steht um R
über dem Berührpunkt, die Stirn genau darauf), um eine Außenkante dreht er sich um die Kante. Wie
tief seine Spitze darf, rechnet die Hüllfläche des echten Fräsers in genau dieser Stellung
(vierachs_huelle.je_stellung) – so schneidet er nirgends ins Teil, auch nicht in Kehlen, in die
die Kugel passt und die Scheibe nicht.

Damit Stellungen sich die Rechnung teilen, rechnet die Hüllfläche nur Richtungen auf dem Raster
PSI_RASTER – je Punkt die beiden neben ψ –, die Maschine fährt ψ selbst mit der Spitze
dazwischen (stellungen); je Richtung rechnet je_stellung alle Versätze in einem Zug.

Läuft ohne Oberfläche.
"""

import math

import numpy as np

from . import fraeserform as ff
from . import vierachs_huelle as vh

PSI_RASTER = 0.25  # Grad – darauf rastet die Richtung der Werkzeugachse ein
# Grad – so wenig ändert sich ψ über eine ebene Fläche (die Vernetzung: an einer Abflachung
# ±0,035°); dort hält die Rundachse genau (_halten), über mindestens HALTEN_PUNKTE Punkte.
HALTEN = 0.1
HALTEN_PUNKTE = 3


def stellungen(
    netz,
    laengs,
    radial,
    form,
    zugabe,
    a,
    x_kugel,
    q_kugel,
    psi,
    a_von,
    a_bis,
    psi_raster=PSI_RASTER,
):
    """Die Stellungen des Fräsers `form` (fraeserform.Form) zum Plan einer Kugel mit seinem
    Radius: je Punkt die Spitze der Kugel x_kugel und der Versatz ihrer Mitte q_kugel in der
    Richtung psi (Grad). Gibt (ψ in Grad, Spitze längs der Werkzeugachse, Versatz quer) zurück –
    ψ wie gegeben, die Spitze gemittelt aus den beiden Rasterstellungen daneben, je aus der
    Hüllfläche des Fräsers in dieser Stellung plus `zugabe` (Aufmaß und Vernetzung, wie
    vierachs_bahn._spirale_rechnen). Längs rechnet sie
    zwischen a_von und a_bis (das Teil): davor und dahinter wie an seinem Ende – gerade weiter
    (wie _auffuellen). Wo der Fräser in seiner Stellung nichts trifft, steht die Spitze dort, wo
    die der Kugel stünde."""
    radius = form.radius
    psi_plan = np.asarray(psi, dtype=float)  # der Rahmen, in dem die Mitte gegeben ist
    psi = _halten(psi_plan, psi_raster)
    mitte_x = np.asarray(x_kugel, dtype=float) + radius
    mitte_q = np.asarray(q_kugel, dtype=float)
    stelle = np.clip(np.asarray(a, dtype=float), a_von, a_bis)
    # Der Schaftfräser mit Aufmaß wäre ein Torus mit Eckradius = Aufmaß – der teure Weg der Kerne;
    # eine Scheibe mit Radius + Aufmaß liegt außen um ihn herum (bleibt höchstens so viel höher).
    geformt = ff.scheibe(radius + zugabe) if form.eben else form.mit_aufmass(zugabe)
    stufen = int(round(360.0 / psi_raster))
    # Gerechnet wird je Rasterstellung (Gleiche Richtungen exakt gleich – die Rechnung teilt sie);
    # gefahren wird ψ selbst, die Spitze zwischen den beiden Rasterstellungen daneben gemittelt.
    # Eingerastet gefahren hielt ψ Punkt um Punkt oder sprang um den Raster, und Y pendelte jedes
    # Mal zurück (Manuel, 2026-10-05: „es hackt ziemlich extrem beim Schwenken, vor allem an den
    # Kanten“ – in seinem Programm Y ±0,15 mm Satz um Satz, C abwechselnd 0 und 0,25°). Das
    # Mittel weicht um höchstens R · Δψ² / 8 ab (Δψ = Raster: 0,00002 mm bei R 6).
    unten = np.floor(psi / psi_raster) * psi_raster
    anteil = np.clip((psi - unten) / psi_raster, 0.0, 1.0)
    psi_s = np.concatenate([unten, unten + psi_raster])  # beide Rasterstellungen in einem Zug
    drehen = np.radians(np.concatenate([psi_plan, psi_plan]) - psi_s)  # die Mitte im Raster
    c, s = np.cos(drehen), np.sin(drehen)
    mitte_x2, mitte_q2 = np.concatenate([mitte_x, mitte_x]), np.concatenate([mitte_q, mitte_q])
    mx = mitte_x2 * c - mitte_q2 * s
    q_s = mitte_x2 * s + mitte_q2 * c
    # ψ auf dem Raster und auf eine Umdrehung gebracht (ψ zählt fortlaufend, die Hüllfläche
    # nicht), als Zahl in Bogenmaß.
    richtung = np.radians(np.mod(np.round(psi_s / psi_raster), stufen) * psi_raster)
    hoehe = vh.je_stellung(
        netz, laengs, radial, geformt, richtung, q_s, np.concatenate([stelle, stelle])
    )
    x_s = np.where(np.isfinite(hoehe), hoehe + zugabe, mx - radius)
    # Die Spitze im Querschnitt (Achse in Richtung ψ_s, quer dazu q).
    rad_s = np.radians(psi_s)
    sx = x_s * np.cos(rad_s) - q_s * np.sin(rad_s)
    sy = x_s * np.sin(rad_s) + q_s * np.cos(rad_s)
    n = len(psi)
    ux, uy, ox, oy = sx[:n], sy[:n], sx[n:], sy[n:]
    px = (1.0 - anteil) * ux + anteil * ox
    py = (1.0 - anteil) * uy + anteil * oy
    rad = np.radians(psi)
    x = px * np.cos(rad) + py * np.sin(rad)
    q = -px * np.sin(rad) + py * np.cos(rad)
    return psi, x, q


def _halten(psi, psi_raster):
    """ψ, wo es über mehrere Punkte um weniger als HALTEN schwankt (eine ebene Fläche – Manuel,
    2026-10-03: „die lange Gerade … mit der Y-Achse fahren, ohne C zu bewegen“), genau auf einem
    Wert: auf dem Raster, wenn er so nahe liegt, sonst ihrer Mitte. Sonst ψ, wie es ist."""
    psi = np.array(psi, dtype=float)
    n = len(psi)
    i = 0
    while i < n:
        j, unten, oben = i, psi[i], psi[i]
        while j + 1 < n and max(oben, psi[j + 1]) - min(unten, psi[j + 1]) < HALTEN:
            j += 1
            unten, oben = min(unten, psi[j]), max(oben, psi[j])
        if j - i + 1 >= HALTEN_PUNKTE:
            mitte = 0.5 * (unten + oben)
            gerastet = round(mitte / psi_raster) * psi_raster
            psi[i : j + 1] = gerastet if abs(gerastet - mitte) < HALTEN else mitte
        i = j + 1
    return psi


def lagen_grenze(stange_radius, q, radius, tiefer):
    """Beim Schruppen mit der Querachse: so hoch muss die Spitze in einer Lage mindestens
    stehen, damit der Fräser höchstens `tiefer` (mm, Lage · Zustellung) unter die Stange
    schneidet – gemessen an der höchsten Stelle der Stange unter seiner Stirn (quer von
    |q| − R bis |q| + R). Auf dem Strahl (q = 0) ist das stange_radius − tiefer, wie die Lagen
    rundum."""
    naechste = np.maximum(np.abs(np.asarray(q, dtype=float)) - radius, 0.0)
    unter = naechste < stange_radius
    hoch = np.sqrt(np.maximum(stange_radius * stange_radius - naechste * naechste, 0.0))
    return np.where(unter, hoch - tiefer, -math.inf)
