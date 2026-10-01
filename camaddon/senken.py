# SPDX-License-Identifier: LGPL-2.1-or-later
"""„Zentrieren“ und „Senken“ aus dem Assistenten (W-006 S3g): FreeCADs Bohr-Operation mit einem
Kegel – dem NC-Anbohrer über den Bohrungen, bevor der Bohrer kommt, und dem Kegelsenker in die
Senkungen, die das Modell hat.

- Zentrieren: über jeder gewählten Bohrung so tief, dass der Kegel oben einen Kreis von
  Ø Bohrung + 2 · FASE schneidet – der Bohrer läuft geführt an, und die Kante bekommt gleich
  eine kleine Fase; oben höchstens HOECHSTENS × Ø des Anbohrers (sonst taucht er ganz ein).
  Hat die Bohrung oben eine Senkung, zählt deren Oberkante: Beim Zentrieren ist sie noch zu.
- Senken: gewählt ist die Kegelfläche einer Senkung (senkungen(): ganz herum, nach oben
  offen, das Material außen, darunter die Bohrung); der Kegelsenker mit ihrem Winkel geht so
  tief, dass sein Kegel oben ihren Ø hat.
- Die Spitze steht (D − d) / 2 / tan(α/2) unter der Kante – D der Kreis oben, d die Spitze des
  Werkzeugs, α sein Spitzenwinkel. Je Tiefe eine Operation (FreeCAD fährt alle Löcher einer
  Operation bis zu ihrer einen Endtiefe); Basis sind die Bohrungen, R 3 mm über dem Rohteil.

Hier die Senkungen im Teil, die Tiefen, die Bewegungen zum Schätzen der Zeit und das Anlegen.
Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass

from . import bahn as bn
from . import bohren as bh
from . import bohrung_bahn as bb
from . import einheiten
from . import gewinde as gw
from .sprache import tr

FASE = 0.2  # mm – so breit die Fase, die das Zentrieren an der Bohrung lässt
HOECHSTENS = 0.9  # × Ø des Anbohrers: so breit schneidet er oben höchstens
GLEICH_WINKEL = 1.0  # Grad – so genau muss der Winkel des Senkers zur Senkung passen
GLEICH_D = 0.02  # mm
SPITZENWINKEL = 90.0  # Grad, wenn das Werkzeug keinen hat


@dataclass(frozen=True)
class Senkung:
    """Eine kegelige Senkung über einer Bohrung (senkungen())."""

    name: str  # die Kegelfläche („Face9“)
    mitte: tuple  # (x, y) der Achse
    durchmesser: float  # oben
    z_oben: float
    winkel: float  # Grad – der ganze Winkel des Kegels
    bohrung: str  # die Zylinderfläche darunter – Basis für FreeCADs Bohren


@dataclass
class Kegelbahn:
    """Ergebnis von planen()."""

    punkte: list  # [bahn.Punkt] – die Bewegungen des Zyklus, für die Zeit
    stellen: int
    tiefe: float  # die größte Tiefe der Spitze unter ihrer Kante
    zeit: float  # Minuten


def tiefe_fuer(durchmesser_oben, spitzenwinkel, spitze=0.0):
    """So tief (mm) unter der Kante steht die Spitze, wenn der Kegel oben `durchmesser_oben`
    schneidet."""
    winkel = spitzenwinkel if 0 < spitzenwinkel < 180 else SPITZENWINKEL
    return max(durchmesser_oben - spitze, 0.0) / 2 / math.tan(math.radians(winkel / 2))


def senkungen(form, namen=None):
    """[Senkung] – die Kegelflächen des Teils (nur `namen`, wenn gegeben), die ganz herum gehen,
    nach oben offen sind, das Material außen haben und unten an einer Bohrung enden."""
    import Part

    index = {f.hashCode(): i for i, f in enumerate(form.Faces)}
    ergebnis = []
    for nummer, flaeche in enumerate(form.Faces):
        name = f"Face{nummer + 1}"
        if namen is not None and name not in namen:
            continue
        kegel = flaeche.Surface
        if not isinstance(kegel, Part.Cone) or abs(abs(kegel.Axis.z) - 1.0) > 1e-6:
            continue
        u0, u1, v0, v1 = flaeche.ParameterRange
        if u1 - u0 < 2 * math.pi - 1e-6:
            continue
        kasten = flaeche.BoundBox
        kreise = [k for k in flaeche.Edges if isinstance(k.Curve, Part.Circle)]
        oben = [k for k in kreise if abs(k.Curve.Center.z - kasten.ZMax) < 1e-6]
        unten = [k for k in kreise if abs(k.Curve.Center.z - kasten.ZMin) < 1e-6]
        if not oben or not unten:
            continue
        r_oben, r_unten = oben[0].Curve.Radius, unten[0].Curve.Radius
        hoehe = kasten.ZMax - kasten.ZMin
        if r_oben <= r_unten + 1e-6 or hoehe <= 1e-6:
            continue  # nach oben nicht offen
        mitte = oben[0].Curve.Center
        punkt = flaeche.valueAt((u0 + u1) / 2, (v0 + v1) / 2)
        normale = flaeche.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
        if normale.x * (mitte.x - punkt.x) + normale.y * (mitte.y - punkt.y) <= 0:
            continue  # das Material innen: ein Kegelstumpf, keine Senkung
        bohrung = ""
        for nachbar in form.ancestorsOfType(unten[0], Part.Face):
            i = index.get(nachbar.hashCode())
            if i is not None and i != nummer and bb.bohrungen(form, [f"Face{i + 1}"]):
                bohrung = f"Face{i + 1}"
                break
        if not bohrung:
            continue
        winkel = 2 * math.degrees(math.atan2(r_oben - r_unten, hoehe))
        ergebnis.append(
            Senkung(
                name,
                (float(mitte.x), float(mitte.y)),
                2 * float(r_oben),
                float(kasten.ZMax),
                winkel,
                bohrung,
            )
        )
    return ergebnis


def ist_senkung(form, name):
    """Ist die Fläche `name` eine Senkung (senkungen())?"""
    return bool(senkungen(form, [name]))


# --- Zentrieren -------------------------------------------------------------------------------


def zentrierstellen(form, namen, durchmesser, spitzenwinkel):
    """[(Bohrung, z der Kante, z der Spitze)] – je gewählte Bohrung, wo der Anbohrer hinab geht.
    ValueError mit einem Satz, wenn keine Bohrung gewählt ist."""
    liste = bb.bohrungen(form, list(namen) or None)
    if not liste:
        raise ValueError(tr("zt.fehler.keine"))
    ueber = {s.bohrung: s.z_oben for s in senkungen(form)}
    ergebnis = []
    for b in liste:
        kante = max(b.z_oben, ueber.get(b.name, b.z_oben))
        oben = min(2 * b.radius + 2 * FASE, HOECHSTENS * durchmesser)
        ergebnis.append((b, kante, kante - tiefe_fuer(oben, spitzenwinkel)))
    return ergebnis


def passende_senkungen(form, namen, durchmesser, spitzenwinkel):
    """[Senkung] – die gewählten Senkungen, die ein Kegelsenker mit `durchmesser` und
    `spitzenwinkel` kann. ValueError mit einem Satz, wenn eine nicht passt."""
    liste = senkungen(form, list(namen) or None)
    if not liste:
        raise ValueError(tr("sk.fehler.keine"))
    for s in liste:
        if abs(s.winkel - spitzenwinkel) > GLEICH_WINKEL:
            raise ValueError(
                tr(
                    "sk.fehler.winkel",
                    senker=f"{spitzenwinkel:g}",
                    senkung=f"{round(s.winkel, 1):g}",
                )
            )
        if s.durchmesser > durchmesser + GLEICH_D:
            raise ValueError(
                tr(
                    "sk.fehler.durchmesser",
                    senker=einheiten.text(durchmesser, einheiten.LAENGE),
                    senkung=einheiten.text(s.durchmesser, einheiten.LAENGE),
                )
            )
    return liste


# --- Bewegungen, Zeit, Anlegen ----------------------------------------------------------------


def planen(stellen, oben, sicher, vorschub):
    """Die Bewegungen des Zyklus über `stellen` ([(x, y, z der Kante, z der Spitze)]) in der
    Reihenfolge des kürzesten Wegs: Eilgang darüber, auf R, im Vorschub hinab, zurück auf die
    sichere Höhe (G98) – für die Zeit; FreeCAD schreibt sie als G81."""
    r_ebene = oben + bh.UEBER_R
    offen = list(stellen)
    folge = []
    ort = offen[0][:2] if offen else (0.0, 0.0)
    while offen:
        naechste = min(offen, key=lambda s: math.hypot(s[0] - ort[0], s[1] - ort[1]))
        offen.remove(naechste)
        folge.append(naechste)
        ort = naechste[:2]
    punkte = []
    tiefe = 0.0
    for x, y, kante, spitze in folge:
        punkte.append(bn.Punkt(True, x, y, sicher))
        punkte.append(bn.Punkt(True, x, y, r_ebene))
        punkte.append(bn.Punkt(False, x, y, spitze, True))
        punkte.append(bn.Punkt(True, x, y, sicher))
        tiefe = max(tiefe, kante - spitze)
    zeit = bn.zeit(punkte, vorschub, vorschub) if vorschub > 0 else 0.0
    return Kegelbahn(punkte, len(folge), tiefe, zeit)


def _oben_sicher(job):
    from . import planfraesen as pf

    *_rohteil, oben = pf.rohteil_von_oben(job)
    return oben, oben + 5.0


def vorschau_zentrieren(job, werkzeug, flaechen, vorschub):
    """Die Bewegungen für den Assistenten: Zentrieren der Bohrungen `flaechen` mit dem
    Anbohrer `werkzeug` (werkzeuge.Werkzeug). ValueError mit einem Satz, wenn es nicht geht."""
    from . import vierachs_schlichten as vs

    winkel = float(werkzeug.spitzenwinkel or SPITZENWINKEL)
    stellen = zentrierstellen(
        vs._teil(job.Model.Group), flaechen, float(werkzeug.durchmesser), winkel
    )
    oben, sicher = _oben_sicher(job)
    return planen([(b.mitte[0], b.mitte[1], k, z) for b, k, z in stellen], oben, sicher, vorschub)


def vorschau_senken(job, werkzeug, flaechen, vorschub):
    """Die Bewegungen für den Assistenten: Senken der Senkungen `flaechen` mit dem
    Kegelsenker `werkzeug`. ValueError mit einem Satz, wenn es nicht geht."""
    from . import vierachs_schlichten as vs

    winkel = float(werkzeug.spitzenwinkel or SPITZENWINKEL)
    spitze = float(werkzeug.spitzen_d or 0.0)
    liste = passende_senkungen(
        vs._teil(job.Model.Group), flaechen, float(werkzeug.durchmesser), winkel
    )
    oben, sicher = _oben_sicher(job)
    stellen = [
        (s.mitte[0], s.mitte[1], s.z_oben, s.z_oben - tiefe_fuer(s.durchmesser, winkel, spitze))
        for s in liste
    ]
    return planen(stellen, oben, sicher, vorschub)


def _werkzeug(tc):
    from .werkzeuge_aus_cam import vom_controller

    werkzeug = vom_controller(tc)
    winkel = float(getattr(werkzeug, "spitzenwinkel", 0.0) or SPITZENWINKEL)
    spitze = float(getattr(werkzeug, "spitzen_d", 0.0) or 0.0)
    return float(tc.Tool.Diameter), winkel, spitze


def zentrieren_anlegen(job, tc, flaechen, name=None):
    """Legt FreeCADs Bohren als „Zentrieren“ an – je Tiefe eine Operation; ohne eigene
    Transaktion. Gibt die erste zurück."""
    from . import vierachs_schlichten as vs

    durchmesser, winkel, _spitze = _werkzeug(tc)
    stellen = zentrierstellen(vs._teil(job.Model.Group), flaechen, durchmesser, winkel)
    spitze_von = {b.name: z for b, _k, z in stellen}
    gruppen = gw.je_tiefe([b for b, _k, _z in stellen], lambda b: spitze_von[b.name])
    titel = name or tr("zt.name", werkzeug=f"T{tc.ToolNumber}")
    ops = [
        bh.bohrzyklus(job, tc, [b.name for b in g], spitze_von[g[0].name], titel) for g in gruppen
    ]
    for op in ops:
        # Die Fase, die es lässt – das Prüffenster lässt sie durch (restmaterial.fuer_quader).
        op.addProperty("App::PropertyLength", "Fase", "Zentrieren", tr("zt.eigenschaft.fase"))
        op.Fase = FASE
        op.setEditorMode("Fase", 1)
    return ops[0]


def senken_anlegen(job, tc, flaechen, name=None):
    """Legt FreeCADs Bohren als „Senken“ an – je Tiefe eine Operation, die Bohrungen unter den
    Senkungen als Basis; ohne eigene Transaktion. Gibt die erste zurück."""
    from . import vierachs_schlichten as vs

    durchmesser, winkel, spitze = _werkzeug(tc)
    liste = passende_senkungen(vs._teil(job.Model.Group), flaechen, durchmesser, winkel)
    z_von = {s.name: s.z_oben - tiefe_fuer(s.durchmesser, winkel, spitze) for s in liste}
    gruppen = gw.je_tiefe(liste, lambda s: z_von[s.name])
    titel = name or tr("sk.name", werkzeug=f"T{tc.ToolNumber}")
    ops = [bh.bohrzyklus(job, tc, [s.bohrung for s in g], z_von[g[0].name], titel) for g in gruppen]
    return ops[0]
