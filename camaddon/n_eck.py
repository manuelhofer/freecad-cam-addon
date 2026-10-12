# SPDX-License-Identifier: LGPL-2.1-or-later
"""Das Teil aus einer N-Eck-Stange im Schraubstock (W-018, Spezifikation 4 Achsen, Abschnitt 17).

Manuel (2026-10-12): „das N-Eck in den Schraubstock setzen … jeweils eine Seite des N-Ecks
bearbeiten … dann das N-Eck weiter drehen … so bekomme ich zwar nicht das perfekte Teil, aber ein
Teilergebnis … oder man nimmt ein 8-Eck“ – eine vierte Achse von Hand an einer 3-Achs-Fräse.

Die Stange liegt waagerecht längs X des Jobs, ihre Stirn bei x 0, das Ende, das im Schraubstock
steckt, bei +X; ihre Achse ist die X-Achse des Jobs (y 0, z 0) – dort liegt auch der Nullpunkt:
X an der Stirn, Y und Z in der Mitte der Stange. Die Flächen sind von 1 bis N gezählt, Fläche 1
zeigt in der ersten Aufspannung nach +Y (an die Backe). Jede Aufspannung k (1 … N) ist die Stange
um (k − 1) · 360°/N gedreht, gefräst wird von oben. Die erste ist der Grundjob, die anderen sind
Jobs wie die Ebenen der 5-Achs-Kette (schwenken.lege_an: Grundjob, Lage darin) – aber mit
„Umspannen“: keine Rundachsen, ein eigenes Programm, die Maschine dieselbe 3-Achs-Fräse; das
Restmaterial der Aufspannungen davor rechnet raum_material wie bei den Ebenen.

Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass

import FreeCAD
import numpy as np

from .sprache import tr

VORGABE_N = 8  # Manuel, 2026-10-12: N frei wählbar, gerade; ab 8 werden die Flächen kaum flacher
SPANNLAENGE = 20.0  # mm im Schraubstock (Manuel: „20 mm … einstellbar natürlich“)
ABSTAND = 10.0  # mm zwischen dem Teil und den Backen – Platz für den Fräser
ZUGABE = 1.0  # mm Rohteil rundum ums Teil und vor seiner Stirn
EIGENSCHAFT_N = "NEck"
EIGENSCHAFT_AUFSPANNUNG = "Aufspannung"
TEILACHSEN = {"X": (1.0, 0.0, 0.0), "Y": (0.0, 1.0, 0.0), "Z": (0.0, 0.0, 1.0)}


@dataclass
class Stange:
    """Die N-Eck-Stange: `n` Flächen, `schluesselweite` (mm, zwischen zwei gegenüberliegenden
    Flächen), `laenge` (mm, von der Stirn bei x 0 bis ins Ende im Schraubstock), `spannlaenge`
    (mm davon im Schraubstock)."""

    n: int
    schluesselweite: float
    laenge: float
    spannlaenge: float = SPANNLAENGE


def pruefe_n(n):
    """N als ganze gerade Zahl ab 4 – sonst ValueError mit einem Satz: Im Schraubstock liegen
    zwei Flächen parallel an den Backen, das gibt es nur bei geraden."""
    n = int(n)
    if n < 4 or n % 2:
        raise ValueError(tr("ne.fehler.n", n=n))
    return n


def lage(punkte, achse="Z", umgedreht=False, zugabe=ZUGABE):
    """Das Placement vom Teil in den Job (Job = Lage · Teil): Die Achse `achse` des Teils („X“,
    „Y“, „Z“; `umgedreht`: andersherum) zeigt zur Stirn (−X des Jobs), das andere Ende zum
    Schraubstock; die Mitte des Querschnitts auf der X-Achse, die Spitze `zugabe` hinter der
    Stirn. `punkte`: (n, 3) Punkte des Teils in seinen Koordinaten (ein Netz)."""
    a = np.array(TEILACHSEN[achse], dtype=float) * (-1.0 if umgedreht else 1.0)
    # Nach oben (+Z im Job) die nächste Achse im Kreis: zu Z die Y-Achse, zu X die Z-Achse …
    oben = np.roll(np.abs(a), 1)
    x_job, z_job = -a, oben
    y_job = np.cross(z_job, x_job)
    drehung = np.array([x_job, y_job, z_job])  # Zeilen: die Achsen des Jobs im Teil
    p = np.asarray(punkte, dtype=float) @ drehung.T
    lo, hi = p.min(axis=0), p.max(axis=0)
    mitte_quer = (lo[1:] + hi[1:]) / 2
    verschiebung = np.array([zugabe - lo[0], -mitte_quer[0], -mitte_quer[1]])
    werte = []
    for i in range(3):
        werte += [float(drehung[i, j]) for j in range(3)] + [float(verschiebung[i])]
    matrix = FreeCAD.Matrix(*werte, 0.0, 0.0, 0.0, 1.0)
    return FreeCAD.Placement(matrix)


def stange_fuer(
    punkte_im_job, n=VORGABE_N, zugabe=ZUGABE, abstand=ABSTAND, spannlaenge=SPANNLAENGE
):
    """Die Stange um das Teil (`punkte_im_job`: schon in der Lage des Jobs): Ihr Inkreis faßt den
    Querschnitt des Teils mit `zugabe` rundum, die Schlüsselweite auf ganze Millimeter
    aufgerundet; lang von der Stirn über das Teil, `abstand` bis zu den Backen und
    `spannlaenge` im Schraubstock."""
    n = pruefe_n(n)
    p = np.asarray(punkte_im_job, dtype=float)
    quer = float(np.max(np.hypot(p[:, 1], p[:, 2])))
    schluesselweite = math.ceil(2 * (quer + zugabe) - 1e-9)
    laenge = float(p[:, 0].max()) + abstand + spannlaenge
    return Stange(n, float(schluesselweite), laenge, float(spannlaenge))


def ecken(stange):
    """Die Ecken des Querschnitts (y, z) – Fläche 1 zeigt nach +Y, die anderen im Gegensinn des
    Uhrzeigers (von der Stirn aus gesehen)."""
    umkreis = stange.schluesselweite / 2 / math.cos(math.pi / stange.n)
    return [
        (
            umkreis * math.cos(math.radians((k + 0.5) * 360.0 / stange.n)),
            umkreis * math.sin(math.radians((k + 0.5) * 360.0 / stange.n)),
        )
        for k in range(-1, stange.n - 1)
    ]


def form(stange):
    """Die Stange als Körper (Part.Shape) im Job: von x 0 bis zur Länge."""
    import Part

    punkte = [FreeCAD.Vector(0.0, y, z) for y, z in ecken(stange)]
    flaeche = Part.Face(Part.makePolygon([*punkte, punkte[0]]))
    return flaeche.extrude(FreeCAD.Vector(stange.laenge, 0.0, 0.0))


def drehwinkel(n, aufspannung):
    """Um wie viel Grad die Stange in der Aufspannung `aufspannung` (1 … n) gegen die erste
    gedreht ist."""
    return (aufspannung - 1) * 360.0 / n


def werkzeugachse(n, aufspannung):
    """Die Richtung im Grundjob, aus der das Werkzeug in dieser Aufspannung kommt
    (Einheitsvektor): +Z, um die Stangenachse gedreht."""
    w = math.radians(drehwinkel(n, aufspannung))
    return FreeCAD.Vector(0.0, -math.sin(w), math.cos(w))


def backenflaechen(n, aufspannung):
    """Die beiden Flächen (1 … n) an den Backen in der Aufspannung."""
    erste = (aufspannung - 1) % n + 1
    return erste, (erste - 1 + n // 2) % n + 1


def richte_ein(dokument, teil, punkte, n=VORGABE_N, achse="Z", umgedreht=False, job=None, **masse):
    """Legt den Grundjob an (oder nimmt `job`): das Teil in der Stange (lage), das Rohteil die
    N-Eck-Stange (ein Körper im Dokument, als Klon das Rohteil des Jobs). `punkte`: das Netz des
    Teils, wie es im Dokument liegt (teil.Shape). `masse`: zugabe, abstand, spannlaenge. Keine
    eigene Transaktion. Gibt (Job, Stange) zurück."""
    import Path.Main.Job as PathJob
    import Path.Main.Stock as PathStock

    from . import vierachs_rohteil as vr

    n = pruefe_n(n)
    FreeCAD.setActiveDocument(dokument.Name)
    if job is None:
        job = PathJob.Create("Job", [teil])
    lage_ = lage(punkte, achse, umgedreht, masse.get("zugabe", ZUGABE))
    vr.modell(job).Placement = lage_.multiply(teil.Placement)
    m = np.array(lage_.toMatrix().A, dtype=float).reshape(4, 4)  # die Punkte sind schon gesetzt
    im_job = np.asarray(punkte, dtype=float) @ m[:3, :3].T + m[:3, 3]
    stange = stange_fuer(im_job, n, **masse)
    koerper = dokument.addObject("Part::Feature", "NEckStange")
    koerper.Shape = form(stange)
    koerper.Label = tr("ne.stange", n=n, sw=_zahl(stange.schluesselweite))
    if getattr(koerper, "ViewObject", None) is not None:
        koerper.ViewObject.Visibility = False
    rohteil = PathJob.createResourceClone(job, koerper, "Stock", "Stock")
    PathStock.SetupStockObject(rohteil, PathStock.StockType.Unknown)
    alt = job.Stock
    job.Stock = rohteil
    if alt is not None and alt is not rohteil:
        dokument.removeObject(alt.Name)
    _merke(job, EIGENSCHAFT_N, n, "App::PropertyInteger", tr("ne.eigenschaft.neck"))
    _merke(
        job, EIGENSCHAFT_AUFSPANNUNG, 1, "App::PropertyInteger", tr("ne.eigenschaft.aufspannung")
    )
    job.Label = tr("ne.job", job=job.Label, k=1, n=n)
    dokument.recompute()
    return job, stange


def aufspannungen_anlegen(grundjob, n=None):
    """Die Aufspannungen 2 … N als Jobs (schwenken.lege_an mit „Umspannen“) – keine eigene
    Transaktion. Gibt die Jobs zurück, in ihrer Reihenfolge."""
    from . import schwenken as sw

    n = pruefe_n(n if n is not None else getattr(grundjob, EIGENSCHAFT_N))
    jobs = []
    for k in range(2, n + 1):
        w = drehwinkel(n, k)
        neigung, richtung = (w, -90.0) if w <= 180.0 else (360.0 - w, 90.0)
        name = tr("ne.job", job=grundjob.Label.split(" – ")[0], k=k, n=n)
        job = sw.lege_an(
            grundjob, "", None, name=name, x_richtung=FreeCAD.Vector(1, 0, 0),
            winkel=(neigung, richtung),
        )  # fmt: skip
        sw.umspannen_setzen(job)
        _merke(job, EIGENSCHAFT_N, n, "App::PropertyInteger", tr("ne.eigenschaft.neck"))
        _merke(
            job,
            EIGENSCHAFT_AUFSPANNUNG,
            k,
            "App::PropertyInteger",
            tr("ne.eigenschaft.aufspannung"),
        )
        jobs.append(job)
    grundjob.Document.recompute()
    return jobs


def ist_n_eck(job):
    """Gehört der Job zu einer N-Eck-Stange (Grundjob oder Aufspannung)?"""
    return bool(getattr(job, EIGENSCHAFT_N, 0))


def einrichten_text(job):
    """Der Satz fürs Einrichten der Aufspannung des Jobs – leer, wenn er keine ist."""
    if not ist_n_eck(job):
        return ""
    n = int(getattr(job, EIGENSCHAFT_N))
    k = int(getattr(job, EIGENSCHAFT_AUFSPANNUNG, 1))
    a, b = backenflaechen(n, k)
    return tr(
        "ne.einrichten",
        k=k,
        n=n,
        winkel=_zahl(drehwinkel(n, k)),
        a=a,
        b=b,
    )


def _zahl(wert):
    from . import einheiten

    return einheiten.text(wert, einheiten.LAENGE, 1)


def _merke(job, name, wert, art, tooltip):
    if name not in job.PropertiesList:
        job.addProperty(art, name, "CAM-Addon", tooltip)
        job.setEditorMode(name, 1)
    setattr(job, name, wert)
