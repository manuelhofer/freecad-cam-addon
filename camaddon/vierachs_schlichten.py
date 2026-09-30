# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die CAM-Operation „Rundum schlichten“ (Spezifikation W-003, Stufe V5c).

Wie „Rundum schruppen“ (vierachs_operation) eine Operation mit Werkzeug-Controller und
Kühlmittel, ohne Höhen und Tiefen in Z. Beim Neuberechnen rechnet sie ihre Spirale aus
Modell und Stange des Jobs (vierachs_bahn.schlichten) – mit der Form ihres Fräsers, gelesen
aus dem ToolBit des Controllers (werkzeuge_aus_cam, fraeserform), so wie CAM damit fräst.

Was die „Rundum schruppen“ des Jobs stehen ließen, rechnet sie mit: deren Bahnen trägt sie
von der Stange ab (restmaterial), und tiefer als den Radius ihres Fräsers schneidet sie
nirgends. Ohne „Rundum schruppen“ im Job geht sie nicht – sie nähme die ganze Stange in
einem Zug.

Modul- und Klassenname stehen in jeder gespeicherten Datei – sie bleiben. Der Modulname ist
zugleich ihre Art für „Schnittwerte in den Job“ (job_schnittwerte.operationsart): Einsatz
„Schlichten“. Kein Qt hier; die Anzeige ist die von „Rundum schruppen“
(gui_vierachs_operation).

Läuft ohne Oberfläche.
"""

import re
from dataclasses import replace

import FreeCAD
import Path
import Path.Op.Base as PathOp

from . import fraeserform as ff
from . import restmaterial as rm
from . import vierachs_bahn as vb
from . import vierachs_huelle as vh
from . import vierachs_operation as vo
from . import vierachs_rohteil as vr
from .sprache import tr

AUFMASS = 0.0  # mm – Schlichten macht fertig
SCHRITTWEITE_ANTEIL = 0.02  # ohne ae im Einsatz: D/50 – wie die Vorlage „Schlichten“
# Die Vorschau im Assistenten rechnet grob: Umdrehungen, Zeit und ob es geht – schnell genug
# für jede Eingabe. Die Operation rechnet dann genau.
VORSCHAU_TOLERANZ = 0.05  # mm – Vernetzung
VORSCHAU_SCHRITT_PHI = 2.0  # Grad je Punkt


class RundumSchlichten(PathOp.ObjectOp):
    """Proxy der Operation „Rundum schlichten“."""

    def opFeatures(self, obj):
        return PathOp.FeatureTool | PathOp.FeatureCoolant

    def initOperation(self, obj):
        self._eigenschaften(obj)
        obj.Rundachse = "C"
        obj.Stangenachse = FreeCAD.Vector(0, 0, 1)
        obj.Werkzeugrichtung = FreeCAD.Vector(1, 0, 0)
        obj.Drehsinn = 1
        obj.QuerAufNull = True
        obj.Schrittweite = 0.1
        obj.Aufmass = AUFMASS
        obj.Sicherheitsabstand = vb.SICHERHEIT
        obj.Ueberlauf = vb.ueberlauf_vorschlag(0.0)  # lege_an setzt ihn mit dem Fräser
        obj.AbstandFutter = vb.ABSTAND_FUTTER
        self._editormodi(obj)

    def opOnDocumentRestored(self, obj):
        self._eigenschaften(obj)
        self._editormodi(obj)

    @staticmethod
    def _eigenschaften(obj):
        """Legt die Eigenschaften an, die fehlen; gibt ihre Namen zurück."""
        return vo.eigenschaften_anlegen(
            obj,
            vo.achs_eigenschaften()
            + (
                ("App::PropertyLength", "Schrittweite", tr("vs.eigenschaft.schrittweite")),
                ("App::PropertyLength", "Aufmass", tr("vs.eigenschaft.aufmass")),
            )
            + vo.abstand_eigenschaften()
            + (
                ("App::PropertyLength", "Kammhoehe", tr("vs.eigenschaft.kammhoehe")),
                ("App::PropertyFloat", "Umdrehungen", tr("vs.eigenschaft.umdrehungen")),
                ("App::PropertyLength", "BleibtStehen", tr("vs.eigenschaft.bleibt_stehen")),
            ),
        )

    @staticmethod
    def _editormodi(obj):
        for name in ("Kammhoehe", "Umdrehungen", "BleibtStehen"):
            obj.setEditorMode(name, 1)  # nur lesen: das Ergebnis
        if "Workplane" in obj.PropertiesList:  # Wochen-Build: die Bahn dreht selbst
            obj.setEditorMode("Workplane", 2)

    def opExecute(self, obj):
        try:
            if not self.horizFeed or self.horizFeed <= 0:
                raise ValueError(tr("vo.fehler.vorschub"))
            bahn = rechne(obj, self.job, self.model)
        except ValueError as fehler:
            obj.Umdrehungen = 0.0
            FreeCAD.Console.PrintError(f"{obj.Label}: {fehler}\n")
            self.commandlist.append(Path.Command(f"({vo._ascii(str(fehler))})"))
            return
        obj.Kammhoehe = bahn.kammhoehe
        obj.Umdrehungen = round(bahn.umdrehungen, 1)
        obj.BleibtStehen = round(bahn.stehen, 3)
        for hinweis in hinweise(bahn):
            FreeCAD.Console.PrintWarning(f"{obj.Label}: {hinweis}\n")
        self.commandlist.extend(
            vb.befehle(
                bahn,
                obj.Stangenachse,
                obj.Werkzeugrichtung,
                obj.Rundachse,
                obj.Drehsinn,
                self.horizFeed * 60.0,  # CAM führt mm/s
                obj.QuerAufNull,
            )
        )


def hinweise(bahn):
    """Die Sätze zur Bahn: was hinten nicht erreicht wird, was in engen Stellen stehen bleibt."""
    from .reichweite import weg_text

    ergebnis = []
    if bahn.hinten_frei > 0:
        ergebnis.append(tr("vb.hinten_frei", laenge=weg_text(bahn.hinten_frei)))
    if bahn.stehen > 0.01:
        ergebnis.append(tr("vb.stehen", tiefe=weg_text(bahn.stehen), grenze=weg_text(bahn.grenze)))
    return ergebnis


def form_des_controllers(tc):
    """Die Form des Fräsers eines Werkzeug-Controllers (fraeserform.Form), oder None."""
    from .werkzeuge_aus_cam import vom_controller

    werkzeug = vom_controller(tc)
    return ff.von_werkzeug(werkzeug) if werkzeug is not None else None


def rechne(obj, job, modell):
    """Die Bahn (vierachs_bahn.Schlichtbahn) für die Operation `obj` im Job – nach den
    „Rundum schruppen“ des Jobs. ValueError mit einem Satz, wenn es nicht geht."""
    form = form_des_controllers(obj.ToolController)
    if form is None:
        raise ValueError(tr("vs.fehler.form"))
    return bahn_fuer(
        job,
        modell,
        obj.Stangenachse,
        obj.Werkzeugrichtung,
        form,
        float(obj.Schrittweite),
        float(obj.Aufmass),
        vo.abstaende(obj),
        schruppbahnen(job, modell),
    )


def schruppbahnen(job, modell):
    """[(Bahn, Fräserradius, Aufmaß)] der aktiven „Rundum schruppen“ im Job, deren Bahn geht."""
    ergebnis = []
    for op in getattr(getattr(job, "Operations", None), "Group", []):
        if not vo.ist_schruppen(op) or not getattr(op, "Active", True):
            continue
        radius = float(op.OpToolDiameter) / 2
        try:
            ergebnis.append((vo.rechne(op, job, modell, radius), radius, float(op.Aufmass)))
        except ValueError:
            continue  # ohne Bahn nimmt sie nichts weg
    return ergebnis


def bahn_fuer(job, modell, laengs, radial, form, schrittweite, aufmass, abstaende, schruppen):
    """Die Schlichtbahn für Modell und Stange des Jobs. `abstaende`: (Überlauf, Abstand zum
    Futter, Sicherheitsabstand); `schruppen`: [(Bahn, Fräserradius, Aufmaß)] der Schruppbahnen
    davor (schruppbahnen()). ValueError mit einem Satz, wenn es nicht geht."""
    if not schruppen:
        raise ValueError(tr("vs.fehler.ohne_schruppen"))
    laengs, radius, a_vorne, a_futter = _stange(job, laengs)
    werte = _werte(form, schrittweite, aufmass, abstaende, radius, a_vorne, a_futter)
    werte = replace(
        werte,
        rest=rest_nach(schruppen, radius, a_futter, a_vorne),
        aufmass_schruppen=max(auf for _bahn, _radius, auf in schruppen),
    )
    teil = vh.vernetze(_teil(modell), vb.TOLERANZ_SCHLICHTEN)
    return vb.schlichten(teil, laengs, radial, werte)


def vorschau(job, modell, laengs, radial, form, schrittweite, aufmass, abstaende):
    """Die Schlichtbahn grob – für Umdrehungen, Zeit und ob es geht, im Assistenten, bevor es
    die Operationen gibt: ohne den Rest nach dem Schruppen, gröber vernetzt, alle
    VORSCHAU_SCHRITT_PHI Grad ein Punkt. ValueError wie bahn_fuer()."""
    laengs, radius, a_vorne, a_futter = _stange(job, laengs)
    werte = _werte(form, schrittweite, aufmass, abstaende, radius, a_vorne, a_futter)
    teil = vh.vernetze(_teil(modell), VORSCHAU_TOLERANZ)
    return vb.schlichten(teil, laengs, radial, werte, VORSCHAU_SCHRITT_PHI)


def _stange(job, laengs):
    """(Stangenachse normiert, Radius, a vorne, a der Spannfläche) des Jobs."""
    laengs = FreeCAD.Vector(laengs)
    if laengs.Length < vo.GERADE:
        raise ValueError(tr("vo.fehler.achse"))
    laengs.normalize()
    radius, a_hinten, a_vorne = vo.stange(job, laengs)
    return laengs, radius, a_vorne, a_hinten + (vr.spannlaenge(job) or vr.SPANNLAENGE)


def _werte(form, schrittweite, aufmass, abstaende, radius, a_vorne, a_futter):
    ueberlauf, abstand_futter, sicherheit = abstaende
    return vb.Schlichtwerte(
        form=form,
        stange_radius=radius,
        schrittweite=schrittweite,
        aufmass=aufmass,
        a_stange_vorne=a_vorne,
        a_futter=a_futter,
        sicherheit=sicherheit,
        ueberlauf=ueberlauf,
        abstand_futter=abstand_futter,
    )


def _teil(modell):
    formen = [o.Shape for o in modell if not o.Shape.isNull()]
    if not formen:
        raise ValueError(tr("vo.fehler.modell"))
    return formen[0] if len(formen) == 1 else vo._verbunden(formen)


def rest_nach(schruppen, radius, a_von, a_bis):
    """Was von der Stange (Radius, von a_von bis a_bis) nach den Schruppbahnen bleibt:
    (a, φ in rad, r) wie restmaterial.Stange."""
    stange = rm.Stange(radius, a_von, a_bis)
    for bahn, fraeser_radius, _aufmass in schruppen:
        vorher = None
        for punkt in bahn.punkte:
            if punkt.eilgang:
                vorher = None
            elif vorher is None:  # aus dem Eilgang: bis hierher in der Luft
                stange.schnitt(punkt.a, punkt.r, punkt.phi, fraeser_radius)
            else:
                stange.fahre(
                    (vorher.a, vorher.r, vorher.phi),
                    (punkt.a, punkt.r, punkt.phi),
                    fraeser_radius,
                )
            if not punkt.eilgang:
                vorher = punkt
    return stange.a, stange.phi, stange.r


def schrittweite_vorschlag(werkzeug, einsatz):
    """Die Schrittweite, wenn nichts anderes gesagt ist: ae des Einsatzes aus der
    Werkzeugtabelle (Manuel, 2026-09-30), sonst D/50 wie die Vorlage „Schlichten“ – höchstens
    der Durchmesser."""
    durchmesser = werkzeug.durchmesser
    if einsatz is not None and 0 < einsatz.ae <= durchmesser:
        return einsatz.ae
    return SCHRITTWEITE_ANTEIL * durchmesser


def lege_an(
    job,
    tc,
    achse,
    schrittweite,
    aufmass=AUFMASS,
    quer_auf_null=True,
    name=None,
    abstaende=None,
):
    """Legt „Rundum schlichten“ im Job an – ohne eigene Transaktion, die hält der Aufrufer (der
    Assistent). `achse`: vierachs_achsen.Stangenachse; `abstaende`: (Überlauf, Abstand zum
    Futter, Sicherheitsabstand) – ohne: die Vorschläge. Gibt die Operation zurück. Angelegt wie
    „Rundum schruppen“ (vierachs_operation.lege_an), mit DoNotSetDefaultValues."""
    dokument = job.Document
    obj = dokument.addObject("Path::FeaturePython", "RundumSchlichten")
    obj.addProperty("App::PropertyBool", "DoNotSetDefaultValues", "Path")
    obj.DoNotSetDefaultValues = True
    proxy = RundumSchlichten(obj, "RundumSchlichten", job)
    obj.removeProperty("DoNotSetDefaultValues")
    obj.Proxy = proxy
    job.Proxy.addOperation(obj)
    obj.Active = True
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.CoolantMode = job.SetupSheet.CoolantMode
    obj.StartDepth = 1.0
    vo.setze_achse(obj, achse, quer_auf_null)
    obj.Schrittweite = schrittweite
    obj.Aufmass = aufmass
    radius = float(tc.Tool.Diameter) / 2
    obj.Ueberlauf, obj.AbstandFutter, obj.Sicherheitsabstand = (
        abstaende or vo.vorgeschlagene_abstaende(radius)
    )
    obj.Label = name or tr("vs.name", werkzeug=f"T{tc.ToolNumber}")
    if FreeCAD.GuiUp:
        from . import gui_vierachs_operation

        gui_vierachs_operation.Ansicht(obj.ViewObject)
    return obj


def aendere(obj, tc, schrittweite, aufmass, abstaende=None):
    """Gibt der Operation einen (anderen) Werkzeug-Controller und neue Werte – ohne eigene
    Transaktion. Der Name folgt dem Werkzeug, solange es der vorgeschlagene ist."""
    if _vorgeschlagener_name(obj.Label):
        obj.Label = tr("vs.name", werkzeug=f"T{tc.ToolNumber}")
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.Schrittweite = schrittweite
    obj.Aufmass = aufmass
    if abstaende is not None:
        obj.Ueberlauf, obj.AbstandFutter, obj.Sicherheitsabstand = abstaende


def _vorgeschlagener_name(name):
    """Ist `name` einer, wie lege_an ihn vergibt („Rundum schlichten T2“)?"""
    vorne, _mitte, hinten = tr("vs.name", werkzeug="\0").partition("\0")
    return re.fullmatch(re.escape(vorne) + r"T\d+" + re.escape(hinten), name) is not None


def ist_schlichten(op):
    """Ist `op` eine Operation dieses Moduls – „Rundum schlichten“?"""
    return isinstance(getattr(op, "Proxy", None), RundumSchlichten)
