# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die CAM-Operation „Rundum schlichten“ (Spezifikation W-003, Stufe V5c).

Wie „Rundum schruppen“ (vierachs_operation) eine Operation mit Werkzeug-Controller und
Kühlmittel, ohne Höhen und Tiefen in Z. Beim Neuberechnen rechnet sie ihre Spirale aus
Modell und Stange des Jobs (vierachs_bahn.schlichten) – mit der Form ihres Fräsers, gelesen
aus dem ToolBit des Controllers (werkzeuge_aus_cam, fraeserform), so wie CAM damit fräst.

Ihr Muster (V4c, Eigenschaft „Muster“) ist die Spirale oder „Linien“ längs der Achse bei
festem Winkel – für Flächen, die nicht rundum gehen (vierachs_bahn, Muster LINIEN); der
Assistent schlägt es nach den gewählten Flächen vor.

Was die „Rundum schruppen“ des Jobs stehen ließen, rechnet sie mit (rest_nach): Die Spirale
nimmt es in einem Zug, „Rest höchstens“ sagt, wie viel das ist (Manuel, 2026-10-03: „einfach
spiralisiert, mit einer seitlichen Zustellung von der Angabe“; bis P-2026-10-03-17 fuhr sie
dort vorher in Stufen und fing mittendrin an). Ohne „Rundum schruppen“ im Job geht sie
nicht – sie nähme die ganze Stange in einem Zug.

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

from . import aufloesung as au
from . import fraeserform as ff
from . import freiwege as fw
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
# Steht nach dem Schruppen mehr als Aufmaß + das über der Bahn, sagt es die Operation: Dort
# schneidet der Schlichtfräser in einem Zug tief – das Schruppen kam nicht hin.
REST_VIEL = 1.0  # mm


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
        au.eigenschaft_rundum(obj, vo.GRUPPE)  # die Auflösung rundum (Grad je Punkt), T-009
        neu = vo.eigenschaften_anlegen(
            obj,
            vo.achs_eigenschaften()
            + (
                ("App::PropertyLength", "Schrittweite", tr("vs.eigenschaft.schrittweite")),
                ("App::PropertyLength", "Aufmass", tr("vs.eigenschaft.aufmass")),
                ("App::PropertyEnumeration", "Muster", tr("vs.eigenschaft.muster")),
                ("App::PropertyBool", "NurGleichlauf", tr("pf.eigenschaft.nur_gleichlauf")),
                ("App::PropertyBool", "Querachse", tr("vs.eigenschaft.querachse")),
                ("App::PropertyBool", "Anstellen", tr("vs.eigenschaft.anstellen")),
            )
            + vo.abstand_eigenschaften()
            + vo.flaechen_eigenschaften()
            + (
                ("App::PropertyLength", "Kammhoehe", tr("vs.eigenschaft.kammhoehe")),
                ("App::PropertyFloat", "Umdrehungen", tr("vs.eigenschaft.umdrehungen")),
                ("App::PropertyLength", "RestHoechstens", tr("vs.eigenschaft.rest_hoechstens")),
                ("App::PropertyInteger", "Linien", tr("vs.eigenschaft.linien")),
            ),
        )
        if "Muster" in neu:
            obj.Muster = list(MUSTER_WERTE)  # die Werte der Aufzählung; gewählt ist der erste
        if "Anstellen" in neu:
            obj.Anstellen = True  # auch in älteren Operationen (Manuel: „pauschal angehakt“)
        return neu

    @staticmethod
    def _editormodi(obj):
        for name in ("Kammhoehe", "Umdrehungen", "RestHoechstens", "Linien"):
            obj.setEditorMode(name, 1)  # nur lesen: das Ergebnis
        if "Vorstufen" in obj.PropertiesList:  # bis 0.140: die Stufen vor der Spirale
            obj.setEditorMode("Vorstufen", 2)
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
        obj.RestHoechstens = bahn.rest_ueber
        obj.Linien = bahn.linien
        if bahn.hinten_frei > 0:
            from .reichweite import weg_text

            hinweis = tr("vb.hinten_frei", laenge=weg_text(bahn.hinten_frei))
            FreeCAD.Console.PrintWarning(f"{obj.Label}: {hinweis}\n")
        if bahn.rest_ueber > float(obj.Aufmass) + REST_VIEL:
            from .reichweite import weg_text

            hinweis = tr("vb.rest_viel", rest=weg_text(bahn.rest_ueber))
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
                vo.eintauchvorschub(self),
                fw.freivorschub_fuer(self.job),  # im Freien schnell (vierachs_bahn._frei)
                fraeser_radius=float(obj.OpToolDiameter) / 2,
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
        querachse=bool(getattr(obj, "Querachse", False)),
        anstellen=bool(getattr(obj, "Anstellen", True)),
        schritt_phi=au.wert_rundum(obj, vb.SCHRITT_PHI_SCHLICHTEN),
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
    querachse=False,
    anstellen=True,
    schritt_phi=vb.SCHRITT_PHI_SCHLICHTEN,
):
    """Die Schlichtbahn für Modell und Stange des Jobs. `abstaende`: (Überlauf, Abstand zum
    Futter, Sicherheitsabstand); `schruppen`: [(Bahn, Fräserradius, Aufmaß)] der Schruppbahnen
    davor (schruppbahnen()); `halter`: so weit reicht der Halter seitlich über die
    Werkzeugachse (halter.seitlich); `flaechen`: die gewählten Flächen („Face3“ …), leer:
    rundum; `muster`: vierachs_bahn.SPIRALE oder LINIEN; `gleichlauf`: die Spirale im Gleichlauf
    für M3 (spindel.fuer_m3 mit dem Controller); `nur_gleichlauf`: Linien längs jede für sich im
    Gleichlauf statt hin und her (P-2026-10-02-28); `querachse`: die Spirale mit der Querachse
    (vierachs_bahn.Schlichtwerte.querachse, nur mit dem Kugelfräser); `anstellen`: die Kugel
    dabei vierachs_bahn.ANSTELLEN_QUER neben der Normalen. ValueError mit einem
    Satz, wenn es nicht geht."""
    if not schruppen:
        raise ValueError(tr("vs.fehler.ohne_schruppen"))
    laengs, radius, a_vorne, a_futter = _stange(job, laengs)
    werte = _werte(form, schrittweite, aufmass, abstaende, radius, a_vorne, a_futter, halter)
    form_teil = _teil(modell)
    werte = replace(
        werte,
        rest=rest_nach(schruppen, radius, a_futter, a_vorne),
        waende=vo.waende(form_teil, laengs),
        bereich=vf.bereich_fuer(form_teil, laengs, radial, flaechen, form.radius),
        muster=muster,
        gleichlauf=gleichlauf,
        nur_gleichlauf=nur_gleichlauf,
        querachse=querachse,
        anstellen=vb.ANSTELLEN_QUER if anstellen else 0.0,
    )
    teil = vh.vernetze(form_teil, vb.TOLERANZ_SCHLICHTEN)
    return vb.schlichten(teil, laengs, radial, werte, schritt_phi)


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
    querachse=False,
    anstellen=True,
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
        querachse=querachse,
        anstellen=vb.ANSTELLEN_QUER if anstellen else 0.0,
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
    """Was nach den Schruppbahnen noch steht: je (a, φ) der kleinste Radius, bis zu dem die
    Stirn eines Schruppfräsers kam, sonst der Stangenradius. (a, φ in rad, r) wie
    restmaterial.Stange – für den Rest über dem Schlichten (rest_ueber) und die Lagen von
    „Plan indexiert“ (vierachs_planbahn._oben_je_zeile).

    Die Stirn zählt ganz – längs und quer: Ein Punkt der Stirn im Abstand ρ von der
    Werkzeugachse liegt um form.hoehe(ρ) über der Spitze; quer um Δt versetzt steht er vom
    Strahl der Spitze aus unter dem Winkel δ = atan(Δt ÷ (r + h)) im Radius (r + h) ÷ cos δ. Je
    Spalte des Rasters (Winkel δ) und Stelle längs (Δa) rechnet es diesen Radius für alle Punkte
    der Bahn zugleich. Bis P-2026-10-03-17 zählte nur das Längsprofil auf dem Strahl der Spitze:
    Der Schaftfräser Ø 12 schien auf Manuels ebener Fläche bis 6 mm stehen zu lassen (R · tan δ),
    die er längst weg hatte – daraus wurden Vorstufen beim Schlichten und Lagen in der Luft bei
    „Plan indexiert“. Vorher (bis P-2026-10-03-07) simulierte es restmaterial.Stange, die keinen
    Kern an der Achse kennt, der weg ist.
    """
    schritt_a, schritt_phi = rm.SCHRITT_A, math.radians(rm.SCHRITT_PHI)
    a = np.arange(a_von, a_bis + schritt_a / 2, schritt_a)
    phi = vh.raster_phi(rm.SCHRITT_PHI)
    n_phi = len(phi)
    r = np.full((len(a), n_phi), float(radius))
    for bahn, fraeser, _aufmass in schruppen:
        form = fraeser if isinstance(fraeser, ff.Form) else ff.scheibe(float(fraeser))
        pa, pr, pphi, pq = _im_vorschub(bahn, schritt_a, radius * schritt_phi)
        if not len(pa):
            continue
        stirn = form.radius
        zeile0 = np.rint((pa - a_von) / schritt_a).astype(np.int64)
        spalte0 = np.rint(pphi / schritt_phi).astype(np.int64)
        # So weit reicht die Stirn seitlich, als Winkel von der Achse aus – nur zur eigenen
        # Seite (δ unter 90°): Was eine Stirn jenseits der Achse wegnimmt, ist auf den Strahlen
        # dort ein Kern an der Achse, und den kennt ein Außenradius je Strahl nicht. Mit der
        # Querachse (Versatz q, V5e) liegt die Stirn von q − R bis q + R quer.
        hoehe0 = np.maximum(pr, 1e-9)
        unten = np.where(pr > 0, np.arctan2(pq - stirn, hoehe0), -math.pi / 2)
        oben = np.where(pr > 0, np.arctan2(pq + stirn, hoehe0), math.pi / 2)
        reichweite = int(math.ceil(stirn / schritt_a))
        j_von = max(-(n_phi // 4), int(math.floor(float(np.min(unten)) / schritt_phi)))
        j_bis = min(n_phi // 4, int(math.ceil(float(np.max(oben)) / schritt_phi)))
        for j in range(j_von, j_bis + 1):
            delta = j * schritt_phi
            cos_d, tan_d = math.cos(delta), math.tan(delta)
            if cos_d < 1e-6:
                continue
            drin = (delta >= unten - 1e-9) & (delta <= oben + 1e-9)
            if not drin.any():
                continue
            r0, z0, s0, q0 = pr[drin], zeile0[drin], spalte0[drin], pq[drin]
            spalten = (s0 + j) % n_phi
            for i in range(-reichweite, reichweite + 1):
                zeilen = z0 + i
                im_raster = (zeilen >= 0) & (zeilen < len(a))
                if not im_raster.any():
                    continue
                da = i * schritt_a
                # Die Höhe der Stirn dort, wo sie den Strahl trifft – mit der Höhe steigt der
                # Versatz quer, deshalb zweimal; die höhere zählt (der Fräser bleibt höher).
                dt = np.maximum(r0, 0.0) * tan_d - q0
                h = form.hoehe(np.hypot(da, dt))
                dt = np.maximum(r0 + np.where(np.isfinite(h), h, 0.0), 0.0) * tan_d - q0
                h2 = form.hoehe(np.hypot(da, dt))
                h = np.maximum(h, h2)
                steht = np.isfinite(h) & im_raster
                # Steht die Spitze über der Achse (r + h ≤ 0), nimmt die Stirn auf diesem Strahl
                # alles bis zur Achse – es bleibt nichts (negativ, wie die Spitze selbst).
                hoch = r0 + h
                wert = np.where(hoch > 0, hoch / cos_d, hoch)
                if steht.any():
                    np.minimum.at(r, (zeilen[steht], spalten[steht]), wert[steht])
    return a, phi, r


def _im_vorschub(bahn, schritt_a, schritt_bogen):
    """Die Punkte der Bahn im Vorschub als (a, r, φ in rad, q), dicht genug fürs Raster: zwischen
    zwei Punkten so viele Zwischenpunkte, dass kein Schritt länger als `schritt_a` längs oder
    quer oder `schritt_bogen` im Bogen ist."""
    a, r, phi, q = [], [], [], []
    vorher = None
    for punkt in bahn.punkte:
        if punkt.eilgang:
            vorher = None
            continue
        jetzt = (punkt.a, punkt.r, math.radians(punkt.phi), punkt.q)
        if vorher is not None:
            weg = max(
                abs(jetzt[0] - vorher[0]),
                abs(jetzt[3] - vorher[3]),
                abs(jetzt[2] - vorher[2]) * max(abs(jetzt[1]), abs(vorher[1]), 1.0),
            )
            anzahl = max(1, int(math.ceil(weg / min(schritt_a, schritt_bogen))))
            for k in range(1, anzahl + 1):
                t = k / anzahl
                a.append(vorher[0] + t * (jetzt[0] - vorher[0]))
                r.append(vorher[1] + t * (jetzt[1] - vorher[1]))
                phi.append(vorher[2] + t * (jetzt[2] - vorher[2]))
                q.append(vorher[3] + t * (jetzt[3] - vorher[3]))
        else:
            a.append(jetzt[0])
            r.append(jetzt[1])
            phi.append(jetzt[2])
            q.append(jetzt[3])
        vorher = jetzt
    return np.array(a), np.array(r), np.array(phi), np.array(q)


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
    querachse=False,
    anstellen=True,
):
    """Legt „Rundum schlichten“ im Job an – ohne eigene Transaktion, die hält der Aufrufer (der
    Assistent). `achse`: vierachs_achsen.Stangenachse; `abstaende`: (Überlauf, Abstand zum
    Futter, Sicherheitsabstand) – ohne: die Vorschläge; `halter`: so weit reicht der Halter
    seitlich über die Werkzeugachse (halter.seitlich); `flaechen`: die gewählten Flächen
    („Face3“ …), leer: rundum; `muster`: vierachs_bahn.SPIRALE oder LINIEN; `nur_gleichlauf`:
    Linien längs jede für sich im Gleichlauf (P-2026-10-02-28); `querachse`, `anstellen` wie bei
    bahn_fuer. Gibt die Operation zurück. Angelegt wie „Rundum schruppen“ (vierachs_operation.lege_an), mit
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
        abstaende or vo.vorgeschlagene_abstaende(radius, job)
    )
    obj.HalterZumFutter = halter
    obj.Flaechen = list(flaechen)
    obj.Muster = muster_wert(muster)
    obj.NurGleichlauf = bool(nur_gleichlauf)
    obj.Querachse = bool(querachse)
    obj.Anstellen = bool(anstellen)
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
    querachse=None,
    anstellen=None,
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
    if querachse is not None and bool(querachse) != bool(getattr(obj, "Querachse", False)):
        obj.Querachse = bool(querachse)
    if anstellen is not None and bool(anstellen) != bool(getattr(obj, "Anstellen", True)):
        obj.Anstellen = bool(anstellen)


def _vorgeschlagener_name(name):
    """Ist `name` einer, wie lege_an ihn vergibt („Rundum schlichten T2“) – auch mit „ (2)“ dahinter?"""
    return namen.nach_vorlage(name, tr("vs.name", werkzeug="\0"))


def ist_schlichten(op):
    """Ist `op` eine Operation dieses Moduls – „Rundum schlichten“?"""
    return isinstance(getattr(op, "Proxy", None), RundumSchlichten)
