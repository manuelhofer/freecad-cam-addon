# SPDX-License-Identifier: LGPL-2.1-or-later
"""„Reiben“ aus dem Assistenten (W-006 4.1 Punkt 7): FreeCADs Bohr-Operation (Path.Op.Drilling)
mit einer Reibahle aus der Werkzeugverwaltung, die den Durchmesser der Bohrung hat – G85: im
Vorschub hinein und im Vorschub wieder heraus (im Eilgang herausgezogen hinterließe sie Riefen).

- Vorgebohrt wird kleiner (bohren.REIBZUGABE: 0,15 bis 0,5 mm auf den Durchmesser) – der
  Assistent sagt es dem Block „Bohren“; „Bohrung fräsen“ und die Kontur treten in geriebenen
  Bohrungen nicht an (sie fräsen schon auf Maß).
- Durchgehende Bohrungen reibt sie bis ANSCHNITT unter den Grund (der Anschnitt vorn an der
  Reibahle hat noch nicht den vollen Durchmesser); Sackbohrungen mit Bohrspitze bis zum Grund
  der Wand – den Anschnitt dort reibt keine Reibahle, wie in jeder Zeichnung. Eine Sackbohrung
  mit ebenem Grund kann kein Bohrer vorbohren: Dort geht Reiben nicht.
- Je Tiefe eine Operation (FreeCAD fährt alle Löcher einer Operation bis zu ihrer einen
  Endtiefe); R 3 mm über dem Rohteil, G98.

Hier die Bewegungen zum Schätzen der Zeit und das Anlegen. Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass

from . import bahn as bn
from . import bohren as bh
from . import bohrung_bahn as bb
from . import einheiten
from . import gewinde as gw
from .sprache import tr

ANSCHNITT = 1.0  # mm – so weit reibt sie durch eine durchgehende Bohrung hinaus
GLEICH_D = 0.02  # mm – so genau muss die Reibahle zur Bohrung passen


@dataclass
class Reibbahn:
    """Ergebnis von planen()."""

    punkte: list  # [bahn.Punkt] – die Bewegungen des Zyklus, für die Zeit
    bohrungen: int
    z_min: float  # die tiefste Spitze
    zeit: float  # Minuten (bahn.zeit)


def kann(b, durchmesser):
    """Reibt eine Reibahle mit `durchmesser` die Bohrung `b` – ihr Durchmesser, durchgehend oder
    mit Bohrspitze (vorbohren kann dort ein Bohrer)?"""
    return abs(2 * b.radius - durchmesser) <= GLEICH_D and (b.durch or b.spitze > 0)


def passende(form, namen, durchmesser):
    """[Bohrung] – die Bohrungen `namen`, die eine Reibahle mit `durchmesser` reibt. ValueError
    mit einem Satz, wenn eine nicht passt."""
    liste = bb.bohrungen(form, list(namen) or None)
    if not liste:
        raise ValueError(tr("rb.fehler.keine"))
    for b in liste:
        d = einheiten.text(2 * b.radius, einheiten.LAENGE)
        if abs(2 * b.radius - durchmesser) > GLEICH_D:
            reibahle = einheiten.text(durchmesser, einheiten.LAENGE)
            raise ValueError(tr("rb.fehler.durchmesser", reibahle=reibahle, durchmesser=d))
        if not b.durch and b.spitze <= 0:
            raise ValueError(tr("rb.fehler.sack", durchmesser=d))
    return liste


def endtiefe(b):
    """Bis wohin die Spitze der Reibahle geht: durchgehend ANSCHNITT unter den Grund, sonst der
    Grund der Wand."""
    return b.z_unten - ANSCHNITT if b.durch else b.z_unten


def planen(liste, oben, sicher, vorschub):
    """Die Bewegungen des Zyklus über die Bohrungen `liste` in der Reihenfolge des kürzesten
    Wegs: Eilgang darüber, auf R, im Vorschub hinab und im Vorschub zurück auf R (G85), dann auf
    die sichere Höhe (G98) – für die Zeit."""
    r_ebene = oben + bh.UEBER_R
    offen = list(liste)
    folge = []
    ort = offen[0].mitte if offen else (0.0, 0.0)
    while offen:
        naechste = min(offen, key=lambda b: math.hypot(b.mitte[0] - ort[0], b.mitte[1] - ort[1]))
        offen.remove(naechste)
        folge.append(naechste)
        ort = naechste.mitte
    punkte = []
    z_min = math.inf
    for b in folge:
        x, y = b.mitte
        unten = endtiefe(b)
        punkte.append(bn.Punkt(True, x, y, sicher))
        punkte.append(bn.Punkt(True, x, y, r_ebene))
        punkte.append(bn.Punkt(False, x, y, unten, True))
        punkte.append(bn.Punkt(False, x, y, r_ebene, True))
        punkte.append(bn.Punkt(True, x, y, sicher))
        z_min = min(z_min, unten)
    zeit = bn.zeit(punkte, vorschub, vorschub) if vorschub > 0 else 0.0
    return Reibbahn(punkte, len(folge), z_min, zeit)


def vorschau(job, werkzeug, flaechen, vorschub):
    """Die Bewegungen für den Assistenten: Reiben der Bohrungen `flaechen` mit der Reibahle
    `werkzeug` (werkzeuge.Werkzeug). ValueError mit einem Satz, wenn es nicht geht."""
    from . import planfraesen as pf
    from . import vierachs_schlichten as vs

    liste = passende(vs._teil(job.Model.Group), flaechen, float(werkzeug.durchmesser))
    *_rohteil, oben = pf.rohteil_von_oben(job)
    return planen(liste, oben, oben + 5.0, vorschub)


def lege_an(job, tc, flaechen, name=None):
    """Legt FreeCADs Bohren als „Reiben“ an (G85: heraus im Vorschub) – je Tiefe eine
    Operation; ohne eigene Transaktion. Gibt die erste zurück."""
    from . import vierachs_schlichten as vs

    liste = passende(vs._teil(job.Model.Group), flaechen, float(tc.Tool.Diameter))
    gruppen = gw.je_tiefe(liste, endtiefe)
    titel = name or tr("rb.name", werkzeug=f"T{tc.ToolNumber}")
    ops = [
        bh.bohrzyklus(job, tc, [b.name for b in g], endtiefe(g[0]), titel, heraus_im_vorschub=True)
        for g in gruppen
    ]
    return ops[0]


def ist_reiben(op):
    """Ist `op` FreeCADs Bohren als Reiben (G85, heraus im Vorschub)?"""
    return bh.ist_bohren(op) and bool(getattr(op, "feedRetractEnabled", False))
