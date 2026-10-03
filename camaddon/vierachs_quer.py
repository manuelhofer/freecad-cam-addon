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

Damit Stellungen sich die Rechnung teilen, rastet ψ auf PSI_RASTER ein – die Mitte bleibt, wo
sie war, ihr Versatz quer folgt; die Hüllfläche rechnet genau diese Stellung, die Maschine fährt
genau sie. Je Richtung rechnet je_stellung alle Versätze in einem Zug.

Läuft ohne Oberfläche.
"""

import math

import numpy as np

from . import fraeserform as ff
from . import vierachs_huelle as vh

PSI_RASTER = 0.25  # Grad – darauf rastet die Richtung der Werkzeugachse ein


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
    ψ eingerastet, der Versatz der Mitte in diesem Rahmen, die Spitze aus der Hüllfläche des Fräsers in dieser Stellung plus
    `zugabe` (Aufmaß und Vernetzung, wie vierachs_bahn._spirale_rechnen). Längs rechnet sie
    zwischen a_von und a_bis (das Teil): davor und dahinter wie an seinem Ende – gerade weiter
    (wie _auffuellen). Wo der Fräser in seiner Stellung nichts trifft, steht die Spitze dort, wo
    die der Kugel stünde."""
    radius = form.radius
    psi = np.asarray(psi, dtype=float)
    mitte_x = np.asarray(x_kugel, dtype=float) + radius
    mitte_q = np.asarray(q_kugel, dtype=float)
    psi_s = np.round(psi / psi_raster) * psi_raster
    drehen = np.radians(psi - psi_s)  # die Mitte im eingerasteten Rahmen
    c, s = np.cos(drehen), np.sin(drehen)
    mx = mitte_x * c - mitte_q * s
    q_s = mitte_x * s + mitte_q * c
    stelle = np.clip(np.asarray(a, dtype=float), a_von, a_bis)
    # Gleiche Richtungen exakt gleich: ψ auf dem Raster und auf eine Umdrehung gebracht (ψ zählt
    # fortlaufend, die Hüllfläche nicht), als Zahl in Bogenmaß.
    stufen = int(round(360.0 / psi_raster))
    richtung = np.radians(np.mod(np.round(psi_s / psi_raster), stufen) * psi_raster)
    # Der Schaftfräser mit Aufmaß wäre ein Torus mit Eckradius = Aufmaß – der teure Weg der Kerne;
    # eine Scheibe mit Radius + Aufmaß liegt außen um ihn herum (bleibt höchstens so viel höher).
    geformt = ff.scheibe(radius + zugabe) if form.eben else form.mit_aufmass(zugabe)
    hoehe = vh.je_stellung(netz, laengs, radial, geformt, richtung, q_s, stelle)
    x = np.where(np.isfinite(hoehe), hoehe + zugabe, mx - radius)
    return psi_s, x, q_s


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
