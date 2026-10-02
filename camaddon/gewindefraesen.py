# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die CAM-Operation „Gewinde fräsen“ (W-006 S3g) – metrische Innengewinde mit einem
Gewindefräser in einer Helix, im Gleichlauf, der Vorschub an der Schneide (gewinde_bahn).

Eine eigene Operation (erbt FreeCADs ObjectOp) wie „Bohrung fräsen“ (bohrung) – nicht FreeCADs
Gewindefräsen: Das fährt den Vorschub des Controllers mit der Mitte des Fräsers, auf der kleinen
Kreisbahn in der Bohrung an der Schneide ein Vielfaches davon, und fräst mit einem Fräser mit
mehreren Zähnen trotzdem Gang für Gang. Beim Neuberechnen rechnet sie ihre Bahn aus Modell und
Rohteil des Jobs, mit Durchmesser, Spitze, Flankenwinkel, Hals und Reichweite aus dem ToolBit
des Controllers; Steigung und Zähne stehen an der Operation (CAM kennt beim Gewindefräser keine
Steigung).

Modul- und Klassenname stehen in jeder gespeicherten Datei – sie bleiben. Der Modulname ist
zugleich ihre Art für „Schnittwerte in den Job“ (job_schnittwerte.operationsart): Einsatz
„Gewindefräsen“. Kein Qt hier.

Läuft ohne Oberfläche.
"""

import FreeCAD
import Path
import Path.Op.Base as PathOp

from . import bahn as bn
from . import bohrung_bahn as bb
from . import gewinde_bahn as gb
from . import namen
from . import planfraesen as pf
from . import spindel as sp
from . import vierachs_bahn as vb
from . import vierachs_operation as vo
from . import vierachs_schlichten as vs
from .sprache import tr

GRUPPE = "Fräsen"


class GewindeFraesen(PathOp.ObjectOp):
    """Proxy der Operation „Gewinde fräsen“."""

    def opFeatures(self, obj):
        return (
            PathOp.FeatureTool
            | PathOp.FeatureDepths
            | PathOp.FeatureHeights
            | PathOp.FeatureCoolant
        )

    def initOperation(self, obj):
        self._eigenschaften(obj)
        obj.Steigung = 0.0
        obj.Zaehne = 1
        obj.Gleichlauf = True
        obj.Linksgewinde = False
        obj.Durchgaenge = 1
        obj.Korrektur = 0.0
        obj.Sicherheitsabstand = vb.SICHERHEIT
        self._editormodi(obj)

    def opOnDocumentRestored(self, obj):
        self._eigenschaften(obj)
        self._editormodi(obj)

    @staticmethod
    def _eigenschaften(obj):
        """Legt die Eigenschaften an, die fehlen; gibt ihre Namen zurück."""
        neu = []
        for typ, name, text in (
            ("App::PropertyStringList", "Flaechen", tr("gf.eigenschaft.flaechen")),
            ("App::PropertyLength", "Steigung", tr("gf.eigenschaft.steigung")),
            ("App::PropertyInteger", "Zaehne", tr("gf.eigenschaft.zaehne")),
            ("App::PropertyBool", "Gleichlauf", tr("ra.eigenschaft.gleichlauf")),
            ("App::PropertyBool", "Linksgewinde", tr("gf.eigenschaft.links")),
            ("App::PropertyInteger", "Durchgaenge", tr("gf.eigenschaft.durchgaenge")),
            ("App::PropertyDistance", "Korrektur", tr("gf.eigenschaft.korrektur")),
            ("App::PropertyLength", "Sicherheitsabstand", tr("pf.eigenschaft.sicherheit")),
            ("App::PropertyString", "Gewinde", tr("gf.eigenschaft.gewinde")),
            ("App::PropertyInteger", "Bohrungen", tr("gf.eigenschaft.bohrungen")),
            ("App::PropertyFloat", "Umlaeufe", tr("gf.eigenschaft.umlaeufe")),
        ):
            if name not in obj.PropertiesList:
                obj.addProperty(typ, name, GRUPPE, text)
                neu.append(name)
        return neu

    @staticmethod
    def _editormodi(obj):
        for name in ("Gewinde", "Bohrungen", "Umlaeufe"):
            obj.setEditorMode(name, 1)  # nur lesen: das Ergebnis

    def opExecute(self, obj):
        try:
            if not self.horizFeed or self.horizFeed <= 0:
                raise ValueError(tr("vo.fehler.vorschub"))
            ergebnis = rechne(obj, self.job, self.model, self.horizFeed * 60.0)
        except ValueError as fehler:
            obj.Gewinde = ""
            obj.Bohrungen = 0
            obj.Umlaeufe = 0.0
            FreeCAD.Console.PrintError(f"{obj.Label}: {fehler}\n")
            self.commandlist.append(Path.Command(f"({vo._ascii(str(fehler))})"))
            return
        obj.Gewinde = ergebnis.gewinde_text()
        obj.Bohrungen = ergebnis.bohrungen
        obj.Umlaeufe = round(float(ergebnis.umlaeufe), 2)
        self.commandlist.extend(bn.befehle(ergebnis.punkte, self.horizFeed * 60.0))


def _mm(bit, name):
    wert = getattr(bit, name, None)
    if wert is None:
        return 0.0
    try:
        return float(wert.getValueAs("mm"))
    except AttributeError:
        try:
            return float(wert)
        except (TypeError, ValueError):
            return 0.0


def _grad(bit, name):
    wert = getattr(bit, name, None)
    if wert is None:
        return 0.0
    try:
        return float(wert.getValueAs("deg"))
    except AttributeError:
        try:
            return float(wert)
        except (TypeError, ValueError):
            return 0.0


def werkzeugwerte(tc):
    """{Name: Wert} des Gewindefräsers aus dem ToolBit des Controllers – wie CAM ihn kennt:
    fraeser_radius, spitze, flankenwinkel, hals_radius, reichweite (mm, Grad; 0: unbekannt)."""
    bit = getattr(tc, "Tool", None)
    if bit is None:
        return {"fraeser_radius": 0.0}
    return {
        "fraeser_radius": _mm(bit, "Diameter") / 2,
        "spitze": _mm(bit, "Crest"),
        "flankenwinkel": _grad(bit, "cuttingAngle") or gb.FLANKENWINKEL,
        "hals_radius": _mm(bit, "NeckDiameter") / 2,
        "reichweite": _mm(bit, "NeckLength"),
    }


def rechne(obj, job, modell, vorschub=0.0, mit_hoehen=True):
    """Die Bahn (gewinde_bahn.Gewindefraesbahn) für die Operation `obj` im Job. ValueError mit
    einem Satz, wenn es nicht geht. `mit_hoehen`: mit Starttiefe und sicherer Höhe der Operation
    – ohne (vor dem ersten Neuberechnen stehen sie noch nicht) mit dem Rohteil."""
    oben = min(float(obj.StartDepth), pf.rohteil_von_oben(job)[4]) if mit_hoehen else None
    return bahn_fuer(
        job,
        modell,
        werkzeugwerte(obj.ToolController),
        float(obj.Steigung),
        vo.flaechen(obj),
        zaehne=int(obj.Zaehne),
        gleichlauf=sp.fuer_m3(obj.Gleichlauf, obj.ToolController),
        links=bool(obj.Linksgewinde),
        durchgaenge=int(obj.Durchgaenge),
        korrektur=float(obj.Korrektur),
        oben=oben,
        sicher=float(obj.SafeHeight) if mit_hoehen else None,
        sicherheit=float(obj.Sicherheitsabstand),
        vorschub=vorschub,
    )


def bahn_fuer(
    job,
    modell,
    werkzeug,
    steigung,
    flaechen=(),
    zaehne=1,
    gleichlauf=True,
    links=False,
    durchgaenge=1,
    korrektur=0.0,
    oben=None,
    sicher=None,
    sicherheit=vb.SICHERHEIT,
    vorschub=0.0,
):
    """Die Bahn „Gewinde fräsen“ für Modell und Rohteil des Jobs. `werkzeug`: {Name: Wert} wie
    werkzeugwerte(); `flaechen`: die gewählten Zylinderflächen („Face7“ …), leer: alle Bohrungen
    des Teils. ValueError mit einem Satz, wenn es nicht geht."""
    form_teil = vs._teil(modell)
    *_rohteil, z_oben = pf.rohteil_von_oben(job)
    if oben is None:
        oben = z_oben
    if sicher is None:
        sicher = oben + sicherheit + 3.0
    liste = bb.bohrungen(form_teil, list(flaechen) or None)
    if not liste:
        raise ValueError(tr("gf.fehler.keine"))
    werte = gb.Gewindewerte(
        fraeser_radius=float(werkzeug.get("fraeser_radius", 0.0)),
        steigung=float(steigung),
        oben=oben,
        sicher=sicher,
        zaehne=int(zaehne),
        flankenwinkel=float(werkzeug.get("flankenwinkel", 0.0) or gb.FLANKENWINKEL),
        spitze=float(werkzeug.get("spitze", 0.0)),
        hals_radius=float(werkzeug.get("hals_radius", 0.0)),
        reichweite=float(werkzeug.get("reichweite", 0.0)),
        gleichlauf=bool(gleichlauf),
        links=bool(links),
        durchgaenge=int(durchgaenge),
        korrektur=float(korrektur),
        sicherheit=sicherheit,
        vorschub=vorschub,
    )
    return gb.planen(werte, liste)


def aus_werkzeug(werkzeug):
    """{Name: Wert} wie werkzeugwerte() – für einen Gewindefräser aus der Werkzeugverwaltung
    (werkzeuge.Werkzeug), so wie ihn uebergabe_werkzeuge an CAM gibt."""
    from . import werkzeuge as wz

    steigung = float(werkzeug.steigung or 0.0)
    return {
        "fraeser_radius": float(werkzeug.durchmesser) / 2,
        "spitze": steigung * gb.SPITZE,
        "flankenwinkel": float(wz.wert(werkzeug, "flankenwinkel") or gb.FLANKENWINKEL),
        "hals_radius": wz.mass(werkzeug, "hals_d") / 2,
        "reichweite": wz.mass(werkzeug, "schneidenlaenge") + wz.mass(werkzeug, "hals_laenge"),
    }


def zaehne_von(werkzeug):
    """Wie viele Zähne der Gewindefräser übereinander hat (gewinde_bahn.zaehne_fuer) – aus der
    eingetragenen Schneidenlänge."""
    return gb.zaehne_fuer(float(werkzeug.schneidenlaenge or 0.0), float(werkzeug.steigung or 0.0))


def vorschau(job, werkzeug, flaechen, gleichlauf=True, vorschub=0.0):
    """Die Bahn für den Assistenten mit einem Gewindefräser aus der Werkzeugverwaltung."""
    steigung = float(werkzeug.steigung or 0.0)
    if steigung <= 0:
        raise ValueError(tr("gf.fehler.steigung"))
    return bahn_fuer(
        job,
        job.Model.Group,
        aus_werkzeug(werkzeug),
        steigung,
        flaechen,
        zaehne=zaehne_von(werkzeug),
        gleichlauf=gleichlauf,
        vorschub=vorschub,
    )


def lege_an(job, tc, steigung, zaehne=1, gleichlauf=True, name=None, flaechen=()):
    """Legt „Gewinde fräsen“ im Job an – ohne eigene Transaktion, die hält der Aufrufer. Tiefen
    und Höhen wie FreeCADs Operationen; die Endtiefe ist die tiefste Spitze. Gibt die Operation
    zurück."""
    dokument = job.Document
    obj = dokument.addObject("Path::FeaturePython", "GewindeFraesen")
    obj.addProperty("App::PropertyBool", "DoNotSetDefaultValues", "Path")
    obj.DoNotSetDefaultValues = True
    proxy = GewindeFraesen(obj, "GewindeFraesen", job)
    obj.removeProperty("DoNotSetDefaultValues")
    obj.Proxy = proxy
    job.Proxy.addOperation(obj)
    obj.Active = True
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.CoolantMode = job.SetupSheet.CoolantMode
    pf._hoehen(obj, proxy, job)
    obj.Steigung = float(steigung)
    obj.Zaehne = max(int(zaehne), 1)
    obj.Gleichlauf = bool(gleichlauf)
    obj.Flaechen = list(flaechen)
    _endtiefe(obj, job)
    obj.Label = namen.eindeutig(
        obj.Document, name or tr("gf.name", werkzeug=f"T{tc.ToolNumber}"), obj
    )
    if FreeCAD.GuiUp:
        from . import gui_vierachs_operation

        gui_vierachs_operation.Ansicht(obj.ViewObject)
    return obj


def _endtiefe(obj, job):
    """Die Endtiefe: die tiefste Spitze der Bahn – unter einer durchgehenden Bohrung, in einer
    Sackbohrung knapp über dem Grund. Bleibt, wenn sich die Bahn nicht rechnen lässt."""
    try:
        tief = rechne(obj, job, job.Model.Group, mit_hoehen=False).z_min
    except (ValueError, RuntimeError, AttributeError):
        return
    obj.setExpression("FinalDepth", None)
    obj.FinalDepth = tief


def aendere(obj, tc, steigung, zaehne=1, gleichlauf=True, flaechen=None):
    """Gibt der Operation einen (anderen) Werkzeug-Controller und neue Werte – ohne eigene
    Transaktion; `flaechen` ohne bleibt. Der Name folgt dem Werkzeug, solange es der
    vorgeschlagene ist."""
    if _vorgeschlagener_name(obj.Label):
        obj.Label = namen.eindeutig(obj.Document, tr("gf.name", werkzeug=f"T{tc.ToolNumber}"), obj)
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.Steigung = float(steigung)
    obj.Zaehne = max(int(zaehne), 1)
    obj.Gleichlauf = bool(gleichlauf)
    if flaechen is not None and list(flaechen) != list(obj.Flaechen):
        obj.Flaechen = list(flaechen)
    job = getattr(obj.Proxy, "job", None)
    if job is not None:
        _endtiefe(obj, job)


def ringe(op, job):
    """[(x, y, r)] – um die Achse jeder Bohrung der Operation der Kreis, bis zu dem die Spitze
    des Zahns reicht: Dort darf sie ins fertige Teil (das Gewinde steht nicht im Modell). Leer,
    wenn sich die Bahn nicht rechnen lässt."""
    try:
        return list(rechne(op, job, job.Model.Group).ringe)
    except (ValueError, RuntimeError, AttributeError):
        return []


def _vorgeschlagener_name(name):
    """Ist `name` einer, wie lege_an ihn vergibt („Gewinde fräsen T7“) – auch mit „ (2)“?"""
    return namen.nach_vorlage(name, tr("gf.name", werkzeug="\0"))


def ist_gewindefraesen(op):
    """Ist `op` eine Operation dieses Moduls – „Gewinde fräsen“?"""
    return isinstance(getattr(op, "Proxy", None), GewindeFraesen)
