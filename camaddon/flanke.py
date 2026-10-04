# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die CAM-Operation „Flanke“ (5 Achsen simultan, S3; flanke_bahn) – schräge Wände aus Geraden
mit dem Mantel eines Schaftfräsers in einem Umlauf (Manuel, 2026-10-04: „Ja, so bauen“).

Wie „3D-Schlichten“ eine eigene Operation (erbt FreeCADs ObjectOp) mit Werkzeug-Controller,
Kühlmittel und FreeCADs Tiefen und Höhen. Ihre Bahn sind die Spitzen im Job; je Satz steht die
Werkzeugachse in `Werkzeugachsen` – „Auf der Maschine prüfen“, die Kollision und „Programm
schreiben“ rechnen daraus die Rundachsen (befehle, simultan.befehle_auf_maschine). Senkrecht
gefahren wäre die Bahn falsch: Ohne Maschine mit zwei Rundachsen schreibt das Programm sie nicht.

Modul- und Klassenname stehen in jeder gespeicherten Datei – sie bleiben. Der Modulname ist
zugleich ihre Art für „Schnittwerte in den Job“: Einsatz „Schlichten“. Kein Qt hier.

Läuft ohne Oberfläche.
"""

import FreeCAD
import Path
import Path.Op.Base as PathOp

from . import flanke_bahn as fb
from . import fraeserform as ff
from . import namen
from . import planfraesen as pf
from . import simultan as si
from . import spindel as sp
from . import vierachs_operation as vo
from . import vierachs_schlichten as vs
from .sprache import tr

GRUPPE = "Fräsen"
GRUPPE_5ACHS = "5-Achs"
KEINE = (0.0, 0.0, 0.0)  # in `Werkzeugachsen`: ein Satz ohne Bewegung


class Flanke(PathOp.ObjectOp):
    """Proxy der Operation „Flanke“."""

    def opFeatures(self, obj):
        return (
            PathOp.FeatureTool
            | PathOp.FeatureDepths
            | PathOp.FeatureHeights
            | PathOp.FeatureCoolant
        )

    def initOperation(self, obj):
        self._eigenschaften(obj)
        obj.Aufmass = 0.0
        obj.Sicherheitsabstand = fb.SICHERHEIT
        obj.Werkzeugachsen = []
        self._editormodi(obj)

    def opOnDocumentRestored(self, obj):
        self._eigenschaften(obj)
        self._editormodi(obj)

    @staticmethod
    def _eigenschaften(obj):
        """Legt die Eigenschaften an, die fehlen; gibt ihre Namen zurück."""
        neu = []
        for typ, name, gruppe, text in (
            ("App::PropertyStringList", "Flaechen", GRUPPE, tr("fl.eigenschaft.flaechen")),
            ("App::PropertyLength", "Aufmass", GRUPPE, tr("fl.eigenschaft.aufmass")),
            ("App::PropertyLength", "Sicherheitsabstand", GRUPPE, tr("pf.eigenschaft.sicherheit")),
            ("App::PropertyInteger", "Umlaeufe", GRUPPE, tr("fl.eigenschaft.umlaeufe")),
            ("App::PropertyInteger", "Lagen", GRUPPE, tr("fl.eigenschaft.lagen")),
            ("App::PropertyLength", "Schneide", GRUPPE_5ACHS, tr("fl.eigenschaft.schneide")),
            (
                "App::PropertyVectorList",
                "Werkzeugachsen",
                GRUPPE_5ACHS,
                tr("an.eigenschaft.achsen"),
            ),
        ):
            if name not in obj.PropertiesList:
                obj.addProperty(typ, name, gruppe, text)
                neu.append(name)
        return neu

    @staticmethod
    def _editormodi(obj):
        for name in ("Umlaeufe", "Lagen", "Schneide"):
            obj.setEditorMode(name, 1)  # nur lesen: das Ergebnis
        obj.setEditorMode("Werkzeugachsen", 2)  # gerechnet, je Satz – nicht zum Ansehen

    def opExecute(self, obj):
        self._vorne = len(self.commandlist)  # was FreeCAD davor schreibt (der Name)
        self._achsen = []
        try:
            if not self.horizFeed or self.horizFeed <= 0:
                raise ValueError(tr("vo.fehler.vorschub"))
            ergebnis, schneide = rechne(
                obj, self.job, self.model, self.horizFeed * 60.0, vo.eintauchvorschub(self)
            )
        except ValueError as fehler:
            obj.Umlaeufe = obj.Lagen = 0
            FreeCAD.Console.PrintError(f"{obj.Label}: {fehler}\n")
            self.commandlist.append(Path.Command(f"({vo._ascii(str(fehler))})"))
            self._achsen.append(KEINE)
            return
        obj.Umlaeufe, obj.Lagen = ergebnis.umlaeufe, ergebnis.lagen
        obj.Schneide = round(float(schneide), 4)
        vorschub = self.horizFeed
        eintauchen = vo.eintauchvorschub(self) / 60.0 or vorschub
        for stelle in ergebnis.punkte:
            werte = dict(zip("XYZ", (float(x) for x in stelle.spitze), strict=True))
            if stelle.eilgang:
                self.commandlist.append(Path.Command("G0", werte))
            else:
                werte["F"] = float(eintauchen if stelle.eintauchen else vorschub)
                self.commandlist.append(Path.Command("G1", werte))
            self._achsen.append(tuple(stelle.achse))

    def execute(self, obj):
        """Wie jede Operation – danach je Satz der fertigen Bahn die Werkzeugachse: vorn und
        hinten, was FreeCAD dazuschreibt (Name, Rückzug), ohne eigene."""
        self._vorne, self._achsen = 0, []
        ergebnis = super().execute(obj)
        alle = len(obj.Path.Commands) if getattr(obj, "Path", None) else 0
        achsen = [KEINE] * self._vorne + list(self._achsen)
        achsen = (achsen + [KEINE] * alle)[:alle]
        obj.Werkzeugachsen = [FreeCAD.Vector(*a) for a in achsen]
        return ergebnis


def rechne(obj, job, modell, vorschub=0.0, eintauchen=0.0):
    """(flanke_bahn.Flankenbahn, Schneidenlänge) für die Operation `obj` im Job. ValueError mit
    einem Satz, wenn es nicht geht."""
    radius, schneide = fraeser_von(obj.ToolController)
    return (
        bahn_fuer(
            job,
            modell,
            radius,
            schneide,
            vo.flaechen(obj),
            aufmass=float(obj.Aufmass),
            oben=min(float(obj.StartDepth), pf.rohteil_von_oben(job)[4]),
            sicher=float(obj.SafeHeight),
            sicherheit=float(obj.Sicherheitsabstand),
            vorschub=vorschub,
            eintauchen=eintauchen,
            gleichlauf=sp.fuer_m3(True, obj.ToolController),
        ),
        schneide,
    )


def fraeser_von(tc):
    """(Radius, Schneidenlänge) des Schaftfräsers am Controller. ValueError mit einem Satz, wenn
    es keiner mit ebener Stirn ist. Ohne Schneidenlänge: zwei Durchmesser."""
    from .werkzeuge_aus_cam import vom_controller

    werkzeug = vom_controller(tc) if tc is not None else None
    form = ff.von_werkzeug(werkzeug) if werkzeug is not None else None
    if form is None or not form.eben or form.radius <= 0:
        raise ValueError(tr("fl.fehler.fraeser"))
    schneide = float(getattr(werkzeug, "schneidenlaenge", 0.0) or 0.0)
    return float(form.radius), schneide if schneide > 0 else 4.0 * float(form.radius)


def bahn_fuer(
    job,
    modell,
    radius,
    schneide,
    flaechen,
    aufmass=0.0,
    oben=None,
    sicher=None,
    sicherheit=fb.SICHERHEIT,
    vorschub=0.0,
    eintauchen=0.0,
    gleichlauf=True,
):
    """Die Bahn „Flanke“ an den Wänden `flaechen` des Modells. ValueError mit einem Satz, wenn
    es nicht geht."""
    form_teil = vs._teil(modell)
    *_rohteil, z_oben = pf.rohteil_von_oben(job)
    if oben is None:
        oben = z_oben
    if sicher is None:
        sicher = oben + sicherheit + 3.0
    werte = fb.Flankenwerte(
        radius=radius,
        schneide=schneide,
        oben=oben,
        sicher=sicher,
        aufmass=aufmass,
        vorschub=vorschub,
        eintauchen=eintauchen,
        sicherheit=sicherheit,
        gleichlauf=gleichlauf,
    )
    return fb.planen(form_teil, list(flaechen), werte)


def lege_an(job, tc, aufmass=0.0, name=None, flaechen=()):
    """Legt „Flanke“ im Job an – ohne eigene Transaktion, die hält der Aufrufer. Gibt die
    Operation zurück."""
    dokument = job.Document
    obj = dokument.addObject("Path::FeaturePython", "Flanke")
    obj.addProperty("App::PropertyBool", "DoNotSetDefaultValues", "Path")
    obj.DoNotSetDefaultValues = True
    proxy = Flanke(obj, "Flanke", job)
    obj.removeProperty("DoNotSetDefaultValues")
    obj.Proxy = proxy
    job.Proxy.addOperation(obj)
    obj.Active = True
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.CoolantMode = job.SetupSheet.CoolantMode
    pf._hoehen(obj, proxy, job)
    obj.Aufmass = aufmass
    obj.Flaechen = list(flaechen)
    _endtiefe(obj, job)
    obj.Label = namen.eindeutig(obj.Document, name or _name(tc), obj)
    if FreeCAD.GuiUp:
        from . import gui_vierachs_operation

        gui_vierachs_operation.Ansicht(obj.ViewObject)
    return obj


def _endtiefe(obj, job):
    """Die Endtiefe: der tiefste Punkt der gewählten Wände."""
    try:
        form_teil = vs._teil(job.Model.Group)
        namen_ = fb.wandflaechen(form_teil, list(obj.Flaechen))
    except ValueError:
        namen_ = []
    if namen_:
        obj.setExpression("FinalDepth", None)
        obj.FinalDepth = min(form_teil.getElement(n).BoundBox.ZMin for n in namen_)


def _name(tc):
    """„Flanke T5“."""
    return tr("fl.name", werkzeug=f"T{tc.ToolNumber}")


def aendere(obj, tc, aufmass=0.0, flaechen=None):
    """Gibt der Operation einen (anderen) Werkzeug-Controller und neue Werte – ohne eigene
    Transaktion; `flaechen` ohne bleiben. Der Name folgt dem Werkzeug, solange es der
    vorgeschlagene ist."""
    if namen.nach_vorlage(obj.Label, tr("fl.name", werkzeug="\0")):
        obj.Label = namen.eindeutig(obj.Document, _name(tc), obj)
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.Aufmass = aufmass
    if flaechen is not None and list(flaechen) != list(obj.Flaechen):
        obj.Flaechen = list(flaechen)
    job = getattr(obj.Proxy, "job", None)
    if job is not None:
        _endtiefe(obj, job)


def ist_flanke(op):
    """Ist `op` eine Operation dieses Moduls?"""
    return isinstance(getattr(op, "Proxy", None), Flanke)


def hat_achsen(op):
    """Eine Flanke mit Werkzeugachsen (gerechnet)?"""
    return ist_flanke(op) and bool(getattr(op, "Werkzeugachsen", None))


def punkte(befehle, achsen_je_satz):
    """[simultan.Punkt] – die Sätze mit ihren Achsen. Sätze, bevor X, Y und Z bekannt sind,
    fallen weg; ohne eigene Achse (der Rückzug am Ende) gilt die davor."""
    ergebnis = []
    stand = [None, None, None]
    achse = None
    for befehl, neu in zip(befehle, achsen_je_satz, strict=True):
        name = befehl.Name.upper()
        if name not in ("G0", "G00", "G1", "G01"):
            continue
        werte = befehl.Parameters
        stand = [float(werte[k]) if k in werte else stand[j] for j, k in enumerate("XYZ")]
        if tuple(neu) != KEINE:
            achse = tuple(neu)
        if None in stand or achse is None:
            continue
        ergebnis.append(
            si.Punkt(
                tuple(stand),
                achse,
                eilgang=name in ("G0", "G00"),
                vorschub=float(werte.get("F", 0.0)),
            )
        )
    return ergebnis


def befehle(op, maschine, rohteil=None, tcpm=False, bei_null=False):
    """Die Sätze der Operation, wie `maschine` (schwenken.Maschine) sie fährt: die Rundachsen je
    Punkt, die Spitze und das obere Ende der Schneide auf der Geraden (simultan.
    befehle_auf_maschine; mit `tcpm` simultan.befehle_mit_tcpm). ValueError mit einem Satz, wenn
    es nicht geht."""
    from . import angestellt as an

    if rohteil is None:
        rohteil = an.rohteil_von(op)
    alle = list(op.Path.Commands)
    achsen_je_satz = [tuple(v) for v in op.Werkzeugachsen]
    if len(achsen_je_satz) != len(alle):
        raise ValueError(tr("an.fehler.veraltet", operation=op.Label))
    schneide = float(getattr(op, "Schneide", 0.0) or 0.0)
    bezug = (0.0, schneide) if schneide > 0 else 0.0
    if tcpm:
        return si.befehle_mit_tcpm(
            maschine, punkte(alle, achsen_je_satz), rohteil, bezug, bei_null=bei_null
        )
    return si.befehle_auf_maschine(maschine, punkte(alle, achsen_je_satz), rohteil, bezug)
