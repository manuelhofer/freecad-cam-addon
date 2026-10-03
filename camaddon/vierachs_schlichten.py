# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die CAM-Operation „Rundum schlichten“ (Spezifikation W-003, Stufe V5c).

Wie „Rundum schruppen“ (vierachs_operation) eine Operation mit Werkzeug-Controller und
Kühlmittel, ohne Höhen und Tiefen in Z. Beim Neuberechnen rechnet sie ihre Spirale aus
Modell und Stange des Jobs (vierachs_bahn.schlichten) – mit der Form ihres Fräsers, gelesen
aus dem ToolBit des Controllers (werkzeuge_aus_cam, fraeserform), so wie CAM damit fräst.

Ihr Muster (V4c, Eigenschaft „Muster“) ist die Spirale oder „Linien“ längs der Achse bei
festem Winkel – für Flächen, die nicht rundum gehen (vierachs_bahn, Muster LINIEN); der
Assistent schlägt es nach den gewählten Flächen vor.

Was die „Rundum schruppen“ des Jobs stehen ließen, rechnet sie mit: deren Bahnen trägt sie
von der Stange ab (restmaterial), und tiefer als den Radius ihres Fräsers schneidet sie
nie – wo mehr stehen blieb, fährt sie in Stufen vor. Ohne „Rundum schruppen“ im Job geht
sie nicht – sie nähme die ganze Stange in einem Zug.

Modul- und Klassenname stehen in jeder gespeicherten Datei – sie bleiben. Der Modulname ist
zugleich ihre Art für „Schnittwerte in den Job“ (job_schnittwerte.operationsart): Einsatz
„Schlichten“. Kein Qt hier; die Anzeige ist die von „Rundum schruppen“
(gui_vierachs_operation).

Läuft ohne Oberfläche.
"""

import math
from dataclasses import replace

import FreeCAD
import numpy as np
import Path
import Path.Op.Base as PathOp

from . import fraeserform as ff
from . import namen
from . import restmaterial as rm
from . import spindel as sp
from . import vierachs_bahn as vb
from . import vierachs_flaechen as vf
from . import vierachs_huelle as vh
from . import vierachs_operation as vo
from . import vierachs_rohteil as vr
from .sprache import tr

AUFMASS = 0.0  # mm – Schlichten macht fertig
# Die Werte der Eigenschaft „Muster“ (Aufzählung, bleibt in jeder Datei) und das Muster der
# Bahn dazu (vierachs_bahn.SPIRALE, LINIEN).
MUSTER_WERTE = {"Spirale": vb.SPIRALE, "Linien": vb.LINIEN}
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
        obj.Muster = muster_wert(vb.SPIRALE)
        obj.Sicherheitsabstand = vb.SICHERHEIT
        obj.Ueberlauf = vb.ueberlauf_vorschlag(0.0)  # lege_an setzt ihn mit dem Fräser
        obj.AbstandFutter = vb.ABSTAND_FUTTER
        self._editormodi(obj)

    def opOnDocumentRestored(self, obj):
        self._eigenschaften(obj)
        self._editormodi(obj)

    @staticmethod
    def _eigenschaften(obj):
        """Legt die Eigenschaften an, die fehlen; gibt ihre Namen zurück. Das Muster (seit
        0.34) bekommen ältere Operationen als Spirale – ihre Bahn bleibt."""
        neu = vo.eigenschaften_anlegen(
            obj,
            vo.achs_eigenschaften()
            + (
                ("App::PropertyLength", "Schrittweite", tr("vs.eigenschaft.schrittweite")),
                ("App::PropertyLength", "Aufmass", tr("vs.eigenschaft.aufmass")),
                ("App::PropertyEnumeration", "Muster", tr("vs.eigenschaft.muster")),
                ("App::PropertyBool", "NurGleichlauf", tr("pf.eigenschaft.nur_gleichlauf")),
            )
            + vo.abstand_eigenschaften()
            + vo.flaechen_eigenschaften()
            + (
                ("App::PropertyLength", "Kammhoehe", tr("vs.eigenschaft.kammhoehe")),
                ("App::PropertyFloat", "Umdrehungen", tr("vs.eigenschaft.umdrehungen")),
                ("App::PropertyInteger", "Vorstufen", tr("vs.eigenschaft.vorstufen")),
                ("App::PropertyInteger", "Linien", tr("vs.eigenschaft.linien")),
            ),
        )
        if "Muster" in neu:
            obj.Muster = list(MUSTER_WERTE)  # die Werte der Aufzählung; gewählt ist der erste
        return neu

    @staticmethod
    def _editormodi(obj):
        for name in ("Kammhoehe", "Umdrehungen", "Vorstufen", "Linien"):
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
            obj.Linien = 0
            FreeCAD.Console.PrintError(f"{obj.Label}: {fehler}\n")
            self.commandlist.append(Path.Command(f"({vo._ascii(str(fehler))})"))
            return
        obj.Kammhoehe = bahn.kammhoehe
        obj.Umdrehungen = round(bahn.umdrehungen, 1)
        obj.Vorstufen = bahn.vorstufen
        obj.Linien = bahn.linien
        if bahn.hinten_frei > 0:
            from .reichweite import weg_text

            hinweis = tr("vb.hinten_frei", laenge=weg_text(bahn.hinten_frei))
            FreeCAD.Console.PrintWarning(f"{obj.Label}: {hinweis}\n")
        if bahn.vorstufen:
            from .reichweite import weg_text

            hinweis = tr("vb.vorstufen", stufen=bahn.vorstufen, grenze=weg_text(bahn.grenze))
            FreeCAD.Console.PrintMessage(f"{obj.Label}: {hinweis}\n")
        self.commandlist.extend(
            vb.befehle(
                bahn,
                obj.Stangenachse,
                obj.Werkzeugrichtung,
                obj.Rundachse,
                obj.Drehsinn,
                self.horizFeed * 60.0,  # CAM führt mm/s
                obj.QuerAufNull,
                vo.eintauchvorschub(self),
            )
        )


def muster_wert(muster):
    """Der Wert der Eigenschaft „Muster“ zu einem Muster der Bahn (vierachs_bahn.SPIRALE …)."""
    for wert, bahn_muster in MUSTER_WERTE.items():
        if bahn_muster == muster:
            return wert
    raise ValueError(tr("vb.fehler.muster", muster=muster))


def muster_der_operation(obj):
    """Das Muster der Bahn (vierachs_bahn.SPIRALE, LINIEN) aus der Eigenschaft „Muster“."""
    return MUSTER_WERTE.get(getattr(obj, "Muster", None), vb.SPIRALE)


form_des_controllers = vo.form_des_controllers  # die Form des Fräsers eines Controllers


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
        vo.halter_zum_futter(obj),
        vo.flaechen(obj),
        muster_der_operation(obj),
        gleichlauf=sp.fuer_m3(True, obj.ToolController),
        nur_gleichlauf=bool(getattr(obj, "NurGleichlauf", False)),
    )


def schruppbahnen(job, modell):
    """[(Bahn, Fräser, Aufmaß)] der aktiven „Rundum schruppen“ im Job, deren Bahn geht – der
    Fräser als seine Form (fraeserform.Form), sonst als Radius: So nimmt rest_nach() mit der
    Kugel weg, was die Kugel wegnimmt (P-2026-10-03-07)."""
    ergebnis = []
    for op in getattr(getattr(job, "Operations", None), "Group", []):
        if not vo.ist_schruppen(op) or not getattr(op, "Active", True):
            continue
        radius = float(op.OpToolDiameter) / 2
        fraeser = form_des_controllers(op.ToolController) or radius
        try:
            ergebnis.append((vo.rechne(op, job, modell, radius), fraeser, float(op.Aufmass)))
        except ValueError:
            continue  # ohne Bahn nimmt sie nichts weg
    return ergebnis


def bahn_fuer(
    job,
    modell,
    laengs,
    radial,
    form,
    schrittweite,
    aufmass,
    abstaende,
    schruppen,
    halter=0.0,
    flaechen=(),
    muster=vb.SPIRALE,
    gleichlauf=True,
    nur_gleichlauf=False,
):
    """Die Schlichtbahn für Modell und Stange des Jobs. `abstaende`: (Überlauf, Abstand zum
    Futter, Sicherheitsabstand); `schruppen`: [(Bahn, Fräserradius, Aufmaß)] der Schruppbahnen
    davor (schruppbahnen()); `halter`: so weit reicht der Halter seitlich über die
    Werkzeugachse (halter.seitlich); `flaechen`: die gewählten Flächen („Face3“ …), leer:
    rundum; `muster`: vierachs_bahn.SPIRALE oder LINIEN; `gleichlauf`: die Spirale im Gleichlauf
    für M3 (spindel.fuer_m3 mit dem Controller); `nur_gleichlauf`: Linien längs jede für sich im
    Gleichlauf statt hin und her (P-2026-10-02-28). ValueError mit einem Satz, wenn es nicht
    geht."""
    if not schruppen:
        raise ValueError(tr("vs.fehler.ohne_schruppen"))
    laengs, radius, a_vorne, a_futter = _stange(job, laengs)
    werte = _werte(form, schrittweite, aufmass, abstaende, radius, a_vorne, a_futter, halter)
    form_teil = _teil(modell)
    werte = replace(
        werte,
        rest=rest_nach(schruppen, radius, a_futter, a_vorne),
        aufmass_schruppen=max(auf for _bahn, _radius, auf in schruppen),
        waende=vo.waende(form_teil, laengs),
        bereich=vf.bereich_fuer(form_teil, laengs, radial, flaechen, form.radius),
        muster=muster,
        gleichlauf=gleichlauf,
        nur_gleichlauf=nur_gleichlauf,
    )
    teil = vh.vernetze(form_teil, vb.TOLERANZ_SCHLICHTEN)
    return vb.schlichten(teil, laengs, radial, werte)


def vorschau(
    job,
    modell,
    laengs,
    radial,
    form,
    schrittweite,
    aufmass,
    abstaende,
    halter=0.0,
    flaechen=(),
    muster=vb.SPIRALE,
    nur_gleichlauf=False,
):
    """Die Schlichtbahn grob – für Umdrehungen, Zeit und ob es geht, im Assistenten, bevor es
    die Operationen gibt: ohne den Rest nach dem Schruppen, gröber vernetzt, alle
    VORSCHAU_SCHRITT_PHI Grad ein Punkt. ValueError wie bahn_fuer()."""
    laengs, radius, a_vorne, a_futter = _stange(job, laengs)
    werte = _werte(form, schrittweite, aufmass, abstaende, radius, a_vorne, a_futter, halter)
    form_teil = _teil(modell)
    werte = replace(
        werte,
        waende=vo.waende(form_teil, laengs),
        bereich=vf.bereich_fuer(form_teil, laengs, radial, flaechen, form.radius),
        muster=muster,
        nur_gleichlauf=nur_gleichlauf,
    )
    teil = vh.vernetze(form_teil, VORSCHAU_TOLERANZ)
    return vb.schlichten(teil, laengs, radial, werte, VORSCHAU_SCHRITT_PHI)


def _stange(job, laengs):
    """(Stangenachse normiert, Radius, a vorne, a der Spannfläche) des Jobs."""
    laengs = FreeCAD.Vector(laengs)
    if laengs.Length < vo.GERADE:
        raise ValueError(tr("vo.fehler.achse"))
    laengs.normalize()
    radius, a_hinten, a_vorne = vo.stange(job, laengs)
    return laengs, radius, a_vorne, a_hinten + (vr.spannlaenge(job) or vr.SPANNLAENGE)


def _werte(form, schrittweite, aufmass, abstaende, radius, a_vorne, a_futter, halter):
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
        halter=halter,
    )


def _teil(modell):
    formen = [o.Shape for o in modell if not o.Shape.isNull()]
    if not formen:
        raise ValueError(tr("vo.fehler.modell"))
    return formen[0] if len(formen) == 1 else vo._verbunden(formen)


def rest_nach(schruppen, radius, a_von, a_bis):
    """Was nach den Schruppbahnen aus jeder Richtung noch steht: je (a, φ) der Radius, bis zu
    dem die Spitze eines Schruppfräsers aus dieser Richtung kam – zwischen den Umdrehungen um
    seine Form höher (die Rillen) –, sonst der Stangenradius. (a, φ in rad, r) wie
    restmaterial.Stange, für vierachs_bahn._nicht_tiefer.

    Bis P-2026-10-03-07 simulierte das restmaterial.Stange: ein Außenradius je Strahl. Der
    kennt keinen Kern an der Achse, der weg ist, und keine Fahrt über die Mitte – an Manuels
    Teil neben der Achse sah das Schlichten einen Kern, der nicht da war, und fuhr 7 Vorstufen
    mit 0,2 mm Schritt (115 min). Was aus einer Richtung steht, sagt die Bahn aus dieser
    Richtung selbst."""
    schritt_a, schritt_phi = rm.SCHRITT_A, math.radians(rm.SCHRITT_PHI)
    a = np.arange(a_von, a_bis + schritt_a / 2, schritt_a)
    phi = vh.raster_phi(rm.SCHRITT_PHI)
    r = np.full((len(a), len(phi)), float(radius))
    for bahn, fraeser, _aufmass in schruppen:
        form = fraeser if isinstance(fraeser, ff.Form) else ff.scheibe(float(fraeser))
        pa, pr, pphi = _im_vorschub(bahn, schritt_a, radius * schritt_phi)
        if not len(pa):
            continue
        spalten = np.rint(pphi / schritt_phi).astype(np.int64) % len(phi)
        reichweite = int(math.ceil(form.radius / schritt_a))
        for versatz in range(-reichweite, reichweite + 1):
            zeilen = np.rint((pa - a_von) / schritt_a).astype(np.int64) + versatz
            drin = (zeilen >= 0) & (zeilen < len(a))
            if not drin.any():
                continue
            hoehe = form.hoehe(np.abs(a[zeilen[drin]] - pa[drin]))
            steht = np.isfinite(hoehe)
            np.minimum.at(
                r, (zeilen[drin][steht], spalten[drin][steht]), pr[drin][steht] + hoehe[steht]
            )
    return a, phi, r


def _im_vorschub(bahn, schritt_a, schritt_bogen):
    """Die Punkte der Bahn im Vorschub als (a, r, φ in rad), dicht genug fürs Raster: zwischen
    zwei Punkten so viele Zwischenpunkte, dass kein Schritt länger als `schritt_a` längs oder
    `schritt_bogen` im Bogen ist."""
    a, r, phi = [], [], []
    vorher = None
    for punkt in bahn.punkte:
        if punkt.eilgang:
            vorher = None
            continue
        jetzt = (punkt.a, punkt.r, math.radians(punkt.phi))
        if vorher is not None:
            weg = max(
                abs(jetzt[0] - vorher[0]),
                abs(jetzt[2] - vorher[2]) * max(abs(jetzt[1]), abs(vorher[1]), 1.0),
            )
            anzahl = max(1, int(math.ceil(weg / min(schritt_a, schritt_bogen))))
            for k in range(1, anzahl + 1):
                t = k / anzahl
                a.append(vorher[0] + t * (jetzt[0] - vorher[0]))
                r.append(vorher[1] + t * (jetzt[1] - vorher[1]))
                phi.append(vorher[2] + t * (jetzt[2] - vorher[2]))
        else:
            a.append(jetzt[0])
            r.append(jetzt[1])
            phi.append(jetzt[2])
        vorher = jetzt
    return np.array(a), np.array(r), np.array(phi)


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
    halter=0.0,
    flaechen=(),
    muster=vb.SPIRALE,
    nur_gleichlauf=False,
):
    """Legt „Rundum schlichten“ im Job an – ohne eigene Transaktion, die hält der Aufrufer (der
    Assistent). `achse`: vierachs_achsen.Stangenachse; `abstaende`: (Überlauf, Abstand zum
    Futter, Sicherheitsabstand) – ohne: die Vorschläge; `halter`: so weit reicht der Halter
    seitlich über die Werkzeugachse (halter.seitlich); `flaechen`: die gewählten Flächen
    („Face3“ …), leer: rundum; `muster`: vierachs_bahn.SPIRALE oder LINIEN; `nur_gleichlauf`:
    Linien längs jede für sich im Gleichlauf (P-2026-10-02-28). Gibt die
    Operation zurück. Angelegt wie „Rundum schruppen“ (vierachs_operation.lege_an), mit
    DoNotSetDefaultValues."""
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
    obj.HalterZumFutter = halter
    obj.Flaechen = list(flaechen)
    obj.Muster = muster_wert(muster)
    obj.NurGleichlauf = bool(nur_gleichlauf)
    obj.Label = namen.eindeutig(
        obj.Document, name or tr("vs.name", werkzeug=f"T{tc.ToolNumber}"), obj
    )
    if FreeCAD.GuiUp:
        from . import gui_vierachs_operation

        gui_vierachs_operation.Ansicht(obj.ViewObject)
    return obj


def aendere(
    obj,
    tc,
    schrittweite,
    aufmass,
    abstaende=None,
    halter=None,
    flaechen=None,
    muster=None,
    nur_gleichlauf=None,
):
    """Gibt der Operation einen (anderen) Werkzeug-Controller und neue Werte – ohne eigene
    Transaktion; `abstaende`, `halter`, `flaechen`, `muster` und `nur_gleichlauf` wie bei
    lege_an, ohne bleiben sie. Der Name folgt dem Werkzeug, solange es der vorgeschlagene ist."""
    if _vorgeschlagener_name(obj.Label):
        obj.Label = namen.eindeutig(obj.Document, tr("vs.name", werkzeug=f"T{tc.ToolNumber}"), obj)
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.Schrittweite = schrittweite
    obj.Aufmass = aufmass
    if abstaende is not None:
        obj.Ueberlauf, obj.AbstandFutter, obj.Sicherheitsabstand = abstaende
    if halter is not None:
        obj.HalterZumFutter = halter
    if flaechen is not None and list(flaechen) != list(obj.Flaechen):
        obj.Flaechen = list(flaechen)
    if muster is not None and muster_wert(muster) != obj.Muster:
        obj.Muster = muster_wert(muster)
    if nur_gleichlauf is not None and bool(nur_gleichlauf) != bool(obj.NurGleichlauf):
        obj.NurGleichlauf = bool(nur_gleichlauf)


def _vorgeschlagener_name(name):
    """Ist `name` einer, wie lege_an ihn vergibt („Rundum schlichten T2“) – auch mit „ (2)“ dahinter?"""
    return namen.nach_vorlage(name, tr("vs.name", werkzeug="\0"))


def ist_schlichten(op):
    """Ist `op` eine Operation dieses Moduls – „Rundum schlichten“?"""
    return isinstance(getattr(op, "Proxy", None), RundumSchlichten)
