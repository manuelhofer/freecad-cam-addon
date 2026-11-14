# SPDX-License-Identifier: LGPL-2.1-or-later
"""Der Reitstock an der 4. Achse (Manuel, 2026-11-15: „die 4te achse würde es eher in ein drei
backenfutter horizonal entlang der x oder y achse … spannen ! und vll sogar mit einem reitstock
stützen“).

Eine lange Stange im Futter des Teilapparats federt unter dem Fräser weg; vorn stützt sie die
Spitze des Reitstocks in einer Zentrierbohrung. Drei Dinge hängen daran:

- Die Stange ist vorn länger: mindestens der Zapfen für die Zentrierbohrung
  (vierachs_rohteil.REITSTOCK_ZAPFEN), am Job gemerkt (vierachs_rohteil.EIGENSCHAFT_REITSTOCK).
- Die Bahn hält Abstand zur Spitze wie zum Futter, vorn statt hinten (mit_schutz): Zum Teil kommt
  für die Hüllfläche ein Zylinder um die Achse – vom Zapfen bis SCHUTZ_VORN vor die Stirn der
  Stange, mit dem Radius der Pinole plus dem Abstand zum Futter der Operation. Über ihn hebt jede
  Bahn ab, wie über das Teil: Der Zapfen bleibt stehen, und vor der Stange bleibt der Fräser über
  Spitze und Pinole. Die Bahn kennt die Maschine nicht; sie rechnet mit einer üblichen Pinole
  (PINOLE_RADIUS, so baut sie die Beispielmaschine) – was an einer dickeren anstößt, zeigt die
  Kollision.
- „Auf der Maschine prüfen“ stellt den Reitstock an die Stange (anstellen): Ein Bauteil mit einem
  LCS „Reitstockspitze“, das an einem Schiebegelenk ohne Betriebsart hängt, ist der Reitstock;
  das LCS liegt dort, wo die Stirn der Stange an der Spitze anliegt, seine Z-Achse zeigt vom Futter
  weg. Danach liegt er in der Maschine – Abfahren und Kollision nehmen ihn mit wie jedes Bauteil.
  Ohne Reitstock im Job fährt er ans hintere Ende, aus dem Weg.

Läuft ohne Oberfläche.
"""

from dataclasses import dataclass

import FreeCAD
import numpy as np

from . import kette as kette_modul
from . import maschine as m
from . import vierachs_rohteil as vr
from .kette import LINEAR
from .sprache import tr

LCS_SPITZE = "Reitstockspitze"  # Name (oder Beschriftung) des LCS an der Spitze
PINOLE_RADIUS = 17.5  # mm – Pinole Ø 35, wie an üblichen Reitstöcken für Teilapparate
# mm vor der Stirn der Stange: so weit reicht der Schutz über Spitze (13,4 mm) und Pinole. Die
# Schruppspirale beginnt Fräserradius + Sicherheitsabstand vor der Stirn – bis Ø 28 deckt er ihren
# ganzen Fräser; davor füllt das Schlichten die Hüllfläche mit der Tiefe seines Endes auf. Mehr
# schöbe den Anfang des Schlichtens (Ende des „Teils“ + Radius) zu nah an den Körper des
# Reitstocks: an der Beispielmaschine 73 mm vor der Stirn.
SCHUTZ_VORN = 30.0
GENAU = 1e-6


@dataclass
class Reitstock:
    """Der Reitstock einer Maschine: sein Schiebegelenk (kette.Achse) und das LCS an der Spitze."""

    achse: object
    lcs: object


def _heisst_spitze(objekt):
    return objekt.Name.startswith(LCS_SPITZE) or str(objekt.Label).startswith(LCS_SPITZE)


def finde(assembly, kette=None):
    """Der Reitstock der Maschine in `assembly` (Reitstock) – None, wenn sie keinen hat."""
    if assembly is None:
        return None
    kette = kette or kette_modul.lies_kette(assembly)
    for objekt in assembly.Document.Objects:
        if objekt.TypeId != "App::LocalCoordinateSystem" or not _heisst_spitze(objekt):
            continue
        glied = kette.glied_von(objekt)
        if glied is None:
            continue
        achse = next((a for a in kette.achsen if a.kind is glied and a.art == LINEAR), None)
        if achse is not None:
            return Reitstock(achse, objekt)
    return None


def hat_reitstock(assembly, kette=None):
    """Hat die Maschine einen Reitstock (finde)? Für den Haken im 4-Achs-Assistenten."""
    try:
        return finde(assembly, kette) is not None
    except Exception as fehler:  # eine halb eingerichtete Maschine soll nicht stören
        FreeCAD.Console.PrintLog(f"CAM-Addon: Reitstock: {fehler}\n")
        return False


@dataclass
class Anstellung:
    """Was anstellen() getan hat: Stellung vorher und nachher (mm, wie am Gelenk), und ein Satz,
    wenn der Reitstock nicht bis an die Stange reicht ("" sonst)."""

    vorher: float
    nachher: float
    meldung: str = ""

    @property
    def bewegt(self):
        return abs(self.nachher - self.vorher) > GENAU


def anstellen(assembly, maschine, job, werkstueckaufnahme=None, nur_rechnen=False):
    """Stellt den Reitstock der Maschine an die Stange des Jobs – die Stirn der Stange an die
    Spitze, gerechnet mit dem Nullpunkt, den „Auf der Maschine prüfen“ vorschlägt oder der
    eingetragen ist. Ohne Reitstock im Job ans hintere Ende seines Wegs. Bewegt die Bauteile der
    Maschine (wie „Maschine verfahren“); die Transaktion hält der Aufrufer. `nur_rechnen`: nur
    sagen, wohin er müsste (Anstellung.nachher), ohne ihn zu bewegen. None, wenn die Maschine
    keinen Reitstock hat, sonst Anstellung."""
    from . import reichweite as rw
    from . import verfahren as vf

    kette = kette_modul.lies_kette(assembly)
    gefunden = finde(assembly, kette)
    if gefunden is None:
        return None
    verfahren = vf.Verfahren(assembly, kette)
    achse = gefunden.achse
    vorher = verfahren.stellung(achse)
    # Vom Futter weg: wie die Z-Achse des LCS an der Spitze (in der Assembly).
    weg_vom_futter = (
        assembly.Placement.inverse()
        .multiply(m.globale_platzierung(gefunden.lcs))
        .Rotation.multVec(FreeCAD.Vector(0, 0, 1))
    )
    grund = rw.grundjob_von(job) if job is not None else None
    if grund is None or not vr.mit_reitstock(grund):
        # Aus dem Weg: ans Ende, an dem die Spitze am weitesten vom Futter steht.
        plus = verfahren.achslage(achse)[0] * verfahren.weg_bei(achse, vorher + 1.0)
        ende = achse.maximum if plus.dot(weg_vom_futter) >= 0 else achse.minimum
        ende = vorher if ende is None else ende
        return Anstellung(vorher, ende if nur_rechnen else verfahren.setze(achse, ende))
    pruefung = rw.Pruefung(assembly, maschine, werkstueckaufnahme, kette=kette)
    if pruefung.werkstueckaufnahme is None:
        return Anstellung(vorher, vorher)
    rohteil = grund.Stock
    vorne_im_job = rohteil.Placement.multVec(FreeCAD.Vector(0, 0, float(rohteil.Height)))
    nullpunkt = rw.nullpunkt(grund, pruefung)
    ziel = pruefung._job_lage(nullpunkt, {}).multVec(vorne_im_job)  # in der Assembly
    spitze = assembly.Placement.inverse().multVec(m.globale_platzierung(gefunden.lcs).Base)
    richtung, _ursprung = verfahren.achslage(achse)
    weg = (ziel - spitze).dot(richtung)
    soll = verfahren.stellung_bei(achse, weg)
    nachher = verfahren.begrenzt(achse, soll) if nur_rechnen else verfahren.setze(achse, soll)
    meldung = ""
    if abs(nachher - soll) > 1e-3:
        # Reicht er nicht weiter vom Futter weg, ist die Stange zu lang – sonst zu kurz.
        zu_lang = (ziel - spitze).dot(weg_vom_futter) > 0
        meldung = tr(
            "rs.reicht_nicht",
            fehlt=rw.weg_text(abs(soll - nachher)),
            richtung=tr("rs.kuerzer") if zu_lang else tr("rs.laenger"),
        )
    return Anstellung(vorher, nachher, meldung)


def schutz_radius(abstand):
    """Der Radius des Schutzzylinders (mm): Pinole plus `abstand` (der Abstand zum Futter der
    Operation – so weit bleibt der Rand des Fräsers auch von der Spitze)."""
    return PINOLE_RADIUS + max(float(abstand), 0.0)


def schutz(job, laengs, abstand):
    """Der Schutzzylinder vor der Stange (Part.Shape im Job) – None ohne Reitstock: um die Achse
    `laengs` mit schutz_radius(abstand), vom Zapfen (REITSTOCK_ZAPFEN hinter der Stirn der Stange)
    bis SCHUTZ_VORN davor."""
    import Part

    if job is None or not vr.mit_reitstock(job):
        return None
    rohteil = job.Stock
    laengs = FreeCAD.Vector(laengs)
    laengs.normalize()
    richtung = rohteil.Placement.Rotation.multVec(FreeCAD.Vector(0, 0, 1))
    basis = rohteil.Placement.Base
    enden = (basis.dot(laengs), (basis + richtung * float(rohteil.Height)).dot(laengs))
    a_vorne = max(enden)
    anfang = a_vorne - vr.REITSTOCK_ZAPFEN
    return Part.makeCylinder(
        schutz_radius(abstand),
        vr.REITSTOCK_ZAPFEN + SCHUTZ_VORN,
        laengs * anfang,
        laengs,
    )


def mit_schutz(netz, job, laengs, abstand):
    """Das Netz des Teils (vierachs_huelle.Netz) mit dem Schutzzylinder (schutz) dazu – ohne
    Reitstock das Netz selbst. Gegen dieses Netz rechnen die Bahnen der Rundum-Operationen ihre
    Hüllfläche: So hält jede Abstand zur Spitze, wie zum Teil."""
    from . import vierachs_huelle as vh

    form = schutz(job, laengs, abstand)
    if form is None:
        return netz
    punkte, dreiecke = form.tessellate(max(float(netz.toleranz), 0.01))
    neu_p = np.array([(p.x, p.y, p.z) for p in punkte], dtype=float).reshape(-1, 3)
    neu_d = np.array(dreiecke, dtype=np.int64).reshape(-1, 3) + len(netz.punkte)
    return vh.Netz(
        np.concatenate([np.asarray(netz.punkte, dtype=float).reshape(-1, 3), neu_p]),
        np.concatenate([np.asarray(netz.dreiecke, dtype=np.int64).reshape(-1, 3), neu_d]),
        netz.toleranz,
    )
