# SPDX-License-Identifier: LGPL-2.1-or-later
"""Der Reitstock an der 4. Achse (Manuel, 2026-11-15: „die 4te achse würde es eher in ein drei
backenfutter horizonal entlang der x oder y achse … spannen ! und vll sogar mit einem reitstock
stützen“).

Eine lange Stange im Futter des Teilapparats federt unter dem Fräser weg; vorn stützt sie die
Spitze des Reitstocks in einer Zentrierbohrung. Drei Dinge hängen daran:

- Die Stange ist vorn länger: mindestens der Zapfen für die Zentrierbohrung
  (vierachs_rohteil.REITSTOCK_ZAPFEN), am Job gemerkt (vierachs_rohteil.EIGENSCHAFT_REITSTOCK).
- Die Bahn hält Abstand zur Spitze wie zum Futter, vorn statt hinten (mit_schutz): Zum Teil kommt
  für die Hüllfläche der Schutz, gestuft (schutz) – im Zapfen ein Prisma so dick wie das Teil
  vorn (mindestens ZAPFEN_RADIUS_MIN), ab der Stirn der Stange bis SCHUTZ_VORN davor ein
  Zylinder mit dem Radius der Pinole plus dem Abstand zum Futter der Operation. Über ihn hebt jede
  Bahn ab, wie über das Teil: Das Teil wird bis an seine Stirn fertig, der Zapfen bleibt stehen,
  und vor der Stange bleibt der Fräser über Spitze und Pinole. Die Bahn kennt die Maschine nicht;
  sie rechnet mit einer üblichen Pinole (PINOLE_RADIUS, so baut sie die Beispielmaschine) – was an
  einer dickeren anstößt, zeigt die Kollision.
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
# Die Zentrierbohrung DIN 332-1 A 4 × 8,5: Die Senkung (60°) ist an der Stirn der Stange Ø 8,5 –
# so weit belegt die Spitze den Zapfen (beispielmaschine.ZENTRIER_RAND).
ZENTRIER_RADIUS = 4.25
# So dünn wird der Zapfen höchstens gefräst: doppelt so dick wie die Senkung (Ø 17), damit um die
# Spitze ein Ring stehen bleibt, der die Stange trägt. Dicker ist er, wo das Teil vorn dicker ist
# (schutz) – an der Welle Ø 30 r 15, am Rohr Ø 60 r 30.
ZAPFEN_RADIUS_MIN = 2.0 * ZENTRIER_RADIUS
STRAHLEN = 360  # je 1° ein Strahl für den Zapfen; die Sehne liegt am Ø 60 0,001 mm innen
SCHNITT_TIEFE = 0.1  # mm hinter der Stirn des Teils: dort misst schutz() das Teil vorn
STRAHLEN_JE_SCHRITT = 2_000_000  # Strahl × Strecke je Rechenschritt (Speicher, _radien_vorn)
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
    wenn der Reitstock nicht bis an die Stange reicht ("" sonst) – dann `fehlt` (mm) und
    `zu_lang` (die Stange müsste kürzer sein, sonst länger). `gestuetzt`: Der Job rechnet mit
    Reitstock (vierachs_rohteil.mit_reitstock)."""

    vorher: float
    nachher: float
    meldung: str = ""
    fehlt: float = 0.0
    zu_lang: bool = False
    gestuetzt: bool = False

    @property
    def bewegt(self):
        return abs(self.nachher - self.vorher) > GENAU

    @property
    def reicht(self):
        """Liegt die Spitze an der Stange (oder braucht der Job keinen Reitstock)?"""
        return not self.meldung


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
        return Anstellung(vorher, vorher, gestuetzt=True)
    rohteil = grund.Stock
    vorne_im_job = rohteil.Placement.multVec(FreeCAD.Vector(0, 0, float(rohteil.Height)))
    nullpunkt = rw.nullpunkt(grund, pruefung)
    ziel = pruefung._job_lage(nullpunkt, {}).multVec(vorne_im_job)  # in der Assembly
    spitze = assembly.Placement.inverse().multVec(m.globale_platzierung(gefunden.lcs).Base)
    richtung, _ursprung = verfahren.achslage(achse)
    weg = (ziel - spitze).dot(richtung)
    soll = verfahren.stellung_bei(achse, weg)
    nachher = verfahren.begrenzt(achse, soll) if nur_rechnen else verfahren.setze(achse, soll)
    meldung, fehlt, zu_lang = "", 0.0, False
    if abs(nachher - soll) > 1e-3:
        # Reicht er nicht weiter vom Futter weg, ist die Stange zu lang – sonst zu kurz.
        zu_lang = (ziel - spitze).dot(weg_vom_futter) > 0
        fehlt = abs(soll - nachher)
        meldung = tr(
            "rs.reicht_nicht",
            fehlt=rw.weg_text(fehlt),
            richtung=tr("rs.kuerzer") if zu_lang else tr("rs.laenger"),
        )
    return Anstellung(vorher, nachher, meldung, fehlt, zu_lang, True)


def ohne_reitstock(job):
    """Der nächste Schritt, wenn der Reitstock nicht an die Stange reicht: Der Job rechnet ohne
    ihn – die Eigenschaft aus, seine 4-Achs-Operationen neu (ihre Bahnen hielten Abstand zur
    Spitze). Die Stange bleibt so lang, der Zapfen ist dann Planaufmaß. Die Transaktion hält der
    Aufrufer."""
    from . import vierachs_operation as vo

    grund = _grundjob(job)
    if grund is None or not vr.mit_reitstock(grund):
        return False
    setattr(grund, vr.EIGENSCHAFT_REITSTOCK, False)
    for op in getattr(getattr(grund, "Operations", None), "Group", []):
        if vo.ist_rundum(op):
            op.touch()
    grund.Document.recompute()
    return True


def _grundjob(job):
    from . import reichweite as rw

    return rw.grundjob_von(job) if job is not None else None


def schutz_radius(abstand):
    """Der Radius des Schutzzylinders vor der Stange (mm): Pinole plus `abstand` (der Abstand zum
    Futter der Operation – so weit bleibt der Rand des Fräsers auch von der Spitze)."""
    return PINOLE_RADIUS + max(float(abstand), 0.0)


@dataclass
class Schutz:
    """Was die Bahnen mit Reitstock nicht anfahren (schutz), längs `laengs` im Job (mm):

    - der Zapfen zwischen der Stirn des Teils (`a_teil`) und der Stirn der Stange (`a_stange`):
      je Strahl um die Achse (`winkel`, rad) so dick wie das Teil vorn (`radien`), mindestens
      ZAPFEN_RADIUS_MIN – die Spitze sitzt darin nur mit ZENTRIER_RADIUS;
    - davor bis SCHUTZ_VORN der Zylinder um Spitze und Pinole (`radius_vorn`, schutz_radius).

    `zu_duenn`: so viel (mm am Radius) ist der Zapfen an der dünnsten Stelle dicker als das Teil
    vorn – dort bleibt vorn am Teil Material stehen; 0: nirgends."""

    laengs: object
    achse: object  # ein Punkt auf der Achse der Stange
    quer: tuple  # zwei Richtungen quer zur Achse (u, v): Strahl k zeigt nach cos·u + sin·v
    a_teil: float
    a_stange: float
    winkel: np.ndarray
    radien: np.ndarray
    radius_vorn: float
    zu_duenn: float


def _quer(laengs):
    """Zwei Richtungen senkrecht zu `laengs` und zueinander (FreeCAD.Vector)."""
    hilfe = FreeCAD.Vector(0, 0, 1) if abs(laengs.z) < 0.9 else FreeCAD.Vector(1, 0, 0)
    u = laengs.cross(hilfe)
    u.normalize()
    v = laengs.cross(u)
    v.normalize()
    return u, v


def _radien_vorn(netz, achse, laengs, quer, a, winkel):
    """Je Strahl von der Achse aus (`winkel`) der äußerste Radius des Netzes im Schnitt bei `a`
    längs – 0, wo der Strahl nichts trifft. Der Schnitt aus den Dreiecken, die die Ebene kreuzen;
    je Strahl der weiteste Schnittpunkt mit seinen Strecken (vektorisiert, Strahl × Strecke)."""
    punkte = np.asarray(netz.punkte, dtype=float).reshape(-1, 3)
    dreiecke = np.asarray(netz.dreiecke, dtype=np.int64).reshape(-1, 3)
    ergebnis = np.zeros(len(winkel))
    if not len(dreiecke):
        return ergebnis
    l_v = np.array(tuple(laengs))
    relativ = punkte - np.array(tuple(achse))
    abstand = relativ @ l_v - (a - np.array(tuple(achse)) @ l_v)
    eben = np.stack([relativ @ np.array(tuple(quer[0])), relativ @ np.array(tuple(quer[1]))], 1)
    d = abstand[dreiecke]  # (m, 3) – Abstand der Ecken zur Ebene
    kreuzt = (d.min(axis=1) < 0.0) & (d.max(axis=1) > 0.0)
    if not kreuzt.any():
        return ergebnis
    ecken, d = dreiecke[kreuzt], d[kreuzt]
    stuecke = []
    for i, j in ((0, 1), (1, 2), (2, 0)):
        wechsel = (d[:, i] < 0.0) != (d[:, j] < 0.0)
        t = np.where(wechsel, d[:, i] / np.where(wechsel, d[:, i] - d[:, j], 1.0), 0.0)
        p = eben[ecken[:, i]] + (eben[ecken[:, j]] - eben[ecken[:, i]]) * t[:, None]
        stuecke.append((wechsel, p))
    # Ein kreuzendes Dreieck hat genau zwei Kanten mit Vorzeichenwechsel: deren Punkte sind die
    # Strecke im Schnitt.
    gewechselt = np.stack([w for w, _p in stuecke], 1)
    punkte_2d = np.stack([p for _w, p in stuecke], 1)  # (m, 3, 2)
    reihen = np.argsort(~gewechselt, axis=1, kind="stable")[:, :2]
    p0 = np.take_along_axis(punkte_2d, reihen[:, 0, None, None], 1)[:, 0]
    p1 = np.take_along_axis(punkte_2d, reihen[:, 1, None, None], 1)[:, 0]
    e = p1 - p0
    p0_e = p0[:, 0] * e[:, 1] - p0[:, 1] * e[:, 0]
    schritt = max(1, STRAHLEN_JE_SCHRITT // max(len(e), 1))
    for anfang in range(0, len(winkel), schritt):
        stueck = winkel[anfang : anfang + schritt]
        richtung = np.stack([np.cos(stueck), np.sin(stueck)], 1)  # (k, 2)
        # Strahl t·r = p0 + s·e: t = (p0 × e) / (r × e), s = (p0 × r) / (r × e).
        nenner = richtung[:, None, 0] * e[None, :, 1] - richtung[:, None, 1] * e[None, :, 0]
        p0_r = p0[None, :, 0] * richtung[:, None, 1] - p0[None, :, 1] * richtung[:, None, 0]
        gueltig = np.abs(nenner) > 1e-12
        sicher = np.where(gueltig, nenner, 1.0)
        t = p0_e[None, :] / sicher
        s = p0_r / sicher
        trifft = gueltig & (s >= -1e-9) & (s <= 1.0 + 1e-9) & (t >= 0.0)
        ergebnis[anfang : anfang + schritt] = np.where(trifft, t, 0.0).max(axis=1)
    return ergebnis


def schutz(job, laengs, abstand, teil):
    """Der Schutz vor dem Teil mit Reitstock (Schutz) – None ohne. `teil`: das Netz des ganzen
    Teils (vierachs_huelle.Netz im Job), `abstand` der Abstand zum Futter der Operation.

    Gestuft (Zweifler 2026-11-14): Bis 0.377 begann ein Zylinder r 22,5 schon an der Stirn des
    Teils – an der Welle Ø 30 blieben vorn auf Fräserradius-Länge 5 mm am Radius stehen, eine
    vorn offene Fläche fräste die Bahn 8,25 mm zu kurz. Im Zapfen ist aber Platz: Die Spitze
    belegt an der Stirn der Stange nur r 4,25, erst 13,4 mm davor die Pinole r 17,5. Darum der
    Zapfen so dick wie das Teil vorn – im Schnitt SCHNITT_TIEFE hinter seiner Stirn, je Strahl der
    äußerste Radius –, und Spitze und Pinole erst ab der Stirn der Stange."""
    if job is None or not vr.mit_reitstock(job):
        return None
    rohteil = job.Stock
    laengs = FreeCAD.Vector(laengs)
    laengs.normalize()
    richtung = rohteil.Placement.Rotation.multVec(FreeCAD.Vector(0, 0, 1))
    basis = rohteil.Placement.Base
    a_stange = max(basis.dot(laengs), (basis + richtung * float(rohteil.Height)).dot(laengs))
    punkte = np.asarray(teil.punkte, dtype=float).reshape(-1, 3)
    if not len(punkte):
        return None
    a_teil = float((punkte @ np.array(tuple(laengs))).max())
    a_teil = min(a_teil, a_stange)
    quer = _quer(laengs)
    winkel = np.linspace(0.0, 2.0 * np.pi, STRAHLEN, endpoint=False)
    gemessen = _radien_vorn(teil, basis, laengs, quer, a_teil - SCHNITT_TIEFE, winkel)
    radien = np.maximum(gemessen, ZAPFEN_RADIUS_MIN)
    zu_duenn = float((radien - gemessen).max()) if len(radien) else 0.0
    return Schutz(
        laengs,
        basis,
        quer,
        a_teil,
        a_stange,
        winkel,
        radien,
        schutz_radius(abstand),
        zu_duenn if zu_duenn > 1e-3 else 0.0,
    )


def _prisma(schutz_, a0, a1, radien):
    """(Punkte, Dreiecke) eines Prismas um die Achse von `a0` bis `a1` längs, je Strahl mit
    `radien` – geschlossen, mit einem Punkt auf der Achse je Deckel."""
    u, v = (np.array(tuple(q)) for q in schutz_.quer)
    l_v = np.array(tuple(schutz_.laengs))
    achse = np.array(tuple(schutz_.achse))
    achse = achse - l_v * (achse @ l_v)
    k = len(schutz_.winkel)
    ring = np.cos(schutz_.winkel)[:, None] * u + np.sin(schutz_.winkel)[:, None] * v
    ring = ring * np.asarray(radien, dtype=float)[:, None]
    punkte = np.concatenate(
        [achse + l_v * a0 + ring, achse + l_v * a1 + ring, [achse + l_v * a0, achse + l_v * a1]]
    )
    i = np.arange(k)
    n = (i + 1) % k
    mantel = np.concatenate([np.stack([i, n, k + n], 1), np.stack([i, k + n, k + i], 1)])
    deckel = np.concatenate(
        [np.stack([np.full(k, 2 * k), n, i], 1), np.stack([np.full(k, 2 * k + 1), k + i, k + n], 1)]
    )
    return punkte, np.concatenate([mantel, deckel]).astype(np.int64)


def hat_schutz(job):
    """Rechnen die Bahnen des Jobs mit Schutz vor dem Teil (mit Reitstock)?"""
    return job is not None and vr.mit_reitstock(job)


def mit_schutz(netz, job, laengs, abstand, ganz=None):
    """Das Netz des Teils (vierachs_huelle.Netz) mit dem Schutz (schutz) dazu – ohne Reitstock das
    Netz selbst. Gegen dieses Netz rechnen die Bahnen der Rundum-Operationen ihre Hüllfläche: So
    hält jede Abstand zur Spitze, wie zum Teil. `ganz`: das Netz des ganzen Teils, wenn `netz`
    Flächen auslässt („Plan indexiert“: die zu fräsenden) – daran misst schutz() das Teil vorn.
    Bleibt vorn Material stehen (Schutz.zu_duenn), sagt es ein Satz im Bericht."""
    from . import vierachs_huelle as vh

    gefunden = schutz(job, laengs, abstand, netz if ganz is None else ganz)
    if gefunden is None:
        return netz
    _melde_zu_duenn(job, gefunden)
    vorn = np.full(len(gefunden.winkel), gefunden.radius_vorn)
    teile = [_prisma(gefunden, gefunden.a_stange, gefunden.a_stange + SCHUTZ_VORN, vorn)]
    if gefunden.a_stange - gefunden.a_teil > GENAU:  # der Zapfen (sonst endet die Stange am Teil)
        teile.append(_prisma(gefunden, gefunden.a_teil, gefunden.a_stange, gefunden.radien))
    alle_p = [np.asarray(netz.punkte, dtype=float).reshape(-1, 3)]
    alle_d = [np.asarray(netz.dreiecke, dtype=np.int64).reshape(-1, 3)]
    zahl = len(alle_p[0])
    for punkte, dreiecke in teile:
        alle_p.append(punkte)
        alle_d.append(dreiecke + zahl)
        zahl += len(punkte)
    return vh.Netz(np.concatenate(alle_p), np.concatenate(alle_d), netz.toleranz)


_gemeldet = set()  # (Job, mm) – der Satz zu_duenn je Job einmal, nicht bei jeder Vorschau


def _melde_zu_duenn(job, gefunden):
    if gefunden.zu_duenn <= 0.0:
        return
    from .reichweite import weg_text

    schluessel = (getattr(job, "Name", ""), round(gefunden.zu_duenn, 2))
    if schluessel in _gemeldet:
        return
    _gemeldet.add(schluessel)
    FreeCAD.Console.PrintWarning(
        f"{getattr(job, 'Label', '')}: "
        + tr(
            "rs.zapfen_duenn",
            durchmesser=weg_text(2.0 * ZAPFEN_RADIUS_MIN),
            mehr=weg_text(gefunden.zu_duenn),
        )
        + "\n"
    )
