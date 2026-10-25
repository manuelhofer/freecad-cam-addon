# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die CAM-Operation „Räumen“ (W-006 S3f) – eine ebene Fläche nach oben (die Oberseite, der
Boden einer Tasche) räumen: bei vollem ap und schmalem ae, ohne Wenden, im Gleichlauf – mit
Ringen (von außen kreisend nach innen, in der Tasche von innen nach außen) oder adaptiv
(FreeCADs Adaptiv-Kern hält den Eingriff): die schnellste Variante, die die Last hält.

Wie „Planfräsen“ (planfraesen) und „Kontur“ (kontur) eine eigene Operation (erbt FreeCADs
ObjectOp) mit Werkzeug-Controller, Kühlmittel und FreeCADs Tiefen und Höhen. Beim Neuberechnen
rechnet sie ihre Bahn aus Modell und Rohteil des Jobs (raeumen_bahn.planen) – in allen
Varianten, die schnellste zählt, wenn sie die Last hält (Grundsatz 0; Variante „ringe“: nur die
Ringe, ohne Blick auf die Last) –, mit dem Fräser aus dem ToolBit des Controllers und den Vorschüben des Controllers für die
Zeit.

Modul- und Klassenname stehen in jeder gespeicherten Datei – sie bleiben. Der Modulname ist
zugleich ihre Art für „Schnittwerte in den Job“ (job_schnittwerte.operationsart): Einsatz
„Schruppen“, sonst „Planen“. Kein Qt hier.

Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass, field

import FreeCAD
import Path
import Path.Op.Base as PathOp

from . import aufloesung as au
from . import bahn as bn
from . import fahrzeit as fz
from . import formteile as ft
from . import freiwege as fw
from . import hoehenfeld as hf
from . import kontur as ko
from . import kontur_bahn as kb
from . import maschinenspeicher as msp
from . import materialstand as mst
from . import namen, uhren
from . import planfraesen as pf
from . import raeumen_bahn as rb
from . import spindel as sp
from . import vierachs_bahn as vb
from . import vierachs_operation as vo
from . import vierachs_schlichten as vs
from .sprache import tr

GRUPPE = "Fräsen"  # die Gruppe der Eigenschaften
ZUSTELLUNG = 2.0  # mm – Vorschlag, solange nichts anderes gesagt ist
AUFMASS = 0.3  # mm – bleibt an Wänden und Inseln stehen
AUSTRITT = 50  # % des Vorschubs beim Austritt aus dem Rohteil
ADAPTIV_FREI = "adaptiv_frei"  # nur auf Wahl; die bisherige automatische Auswahl bleibt gleich
FREIVORSCHUB = fz.EILGANG  # mm/min, einstellbare Obergrenze für die freien G1-Verbindungen
VORBOHREN_NAH = 1.0  # mm – Eintauchstellen näher beieinander: ein Loch
VARIANTEN = ("automatisch", rb.RINGE) + rb.ALLE_VARIANTEN + (ADAPTIV_FREI,)


class Raeumen(PathOp.ObjectOp):
    """Proxy der Operation „Räumen“."""

    def opFeatures(self, obj):
        return (
            PathOp.FeatureTool
            | PathOp.FeatureDepths
            | PathOp.FeatureHeights
            | PathOp.FeatureCoolant
        )

    def initOperation(self, obj):
        self._eigenschaften(obj)
        obj.Zustellung = ZUSTELLUNG
        obj.Zeilenabstand = 1.5
        obj.Aufmass = AUFMASS
        obj.AufmassBoden = 0.0
        obj.Gleichlauf = True
        obj.Variante = "automatisch"
        obj.Einfahrradius = 0.0  # 0: der Vorschlag (der Fräserradius)
        obj.Sicherheitsabstand = vb.SICHERHEIT
        obj.Eintauchwinkel = vb.EINTAUCHWINKEL
        obj.VorschubAustritt = AUSTRITT
        self._editormodi(obj)

    def opOnDocumentRestored(self, obj):
        self._eigenschaften(obj)
        self._editormodi(obj)

    @staticmethod
    def _eigenschaften(obj):
        """Legt die Eigenschaften an, die fehlen; gibt ihre Namen zurück."""
        au.eigenschaft(obj, GRUPPE)
        neu = []
        for typ, name, text in (
            ("App::PropertyStringList", "Flaechen", tr("ra.eigenschaft.flaechen")),
            ("App::PropertyLength", "Zustellung", tr("ra.eigenschaft.zustellung")),
            ("App::PropertyLength", "Zeilenabstand", tr("ra.eigenschaft.zeilenabstand")),
            ("App::PropertyLength", "Aufmass", tr("ra.eigenschaft.aufmass")),
            ("App::PropertyLength", "AufmassBoden", tr("ra.eigenschaft.aufmass_boden")),
            ("App::PropertyBool", "Gleichlauf", tr("ra.eigenschaft.gleichlauf")),
            ("App::PropertyEnumeration", "Variante", tr("ra.eigenschaft.variante")),
            ("App::PropertySpeed", "Freivorschub", tr("ra.eigenschaft.freivorschub")),
            ("App::PropertyBool", "EngLassen", tr("ra.eigenschaft.eng_lassen")),
            ("App::PropertyLength", "NurEngVon", tr("ra.eigenschaft.nur_eng")),
            ("App::PropertyLength", "Einfahrradius", tr("ko.eigenschaft.einfahrradius")),
            ("App::PropertyLength", "Sicherheitsabstand", tr("pf.eigenschaft.sicherheit")),
            ("App::PropertyAngle", "Eintauchwinkel", tr("vo.eigenschaft.eintauchwinkel")),
            ("App::PropertyPercent", "VorschubAustritt", tr("ko.eigenschaft.austritt")),
            ("App::PropertyInteger", "Ebenen", tr("pf.eigenschaft.ebenen")),
            ("App::PropertyInteger", "Lagen", tr("pf.eigenschaft.lagen")),
            ("App::PropertyInteger", "Ringe", tr("ra.eigenschaft.ringe")),
            ("App::PropertyInteger", "Laeufe", tr("ra.eigenschaft.laeufe")),
            ("App::PropertyString", "Gerechnet", tr("ra.eigenschaft.gerechnet")),
            ("App::PropertyString", "Materialstand", tr("ms.eigenschaft.materialstand")),
        ):
            if name not in obj.PropertiesList:
                obj.addProperty(typ, name, GRUPPE, text)
                neu.append(name)
                if name == "Variante":
                    obj.Variante = list(VARIANTEN)
                elif name == "Freivorschub":
                    obj.Freivorschub = FREIVORSCHUB / 60.0  # FreeCAD speichert mm/s
        # Auch alte Dateien bekommen die zusätzliche Wahl, ohne ihre bisherige zu verlieren.
        if obj.getEnumerationsOfProperty("Variante") != list(VARIANTEN):
            variante = str(obj.Variante)
            obj.Variante = list(VARIANTEN)
            obj.Variante = variante if variante in VARIANTEN else "automatisch"
        return neu

    @staticmethod
    def _editormodi(obj):
        for name in ("Ebenen", "Lagen", "Ringe", "Laeufe", "Gerechnet"):
            obj.setEditorMode(name, 1)  # nur lesen: das Ergebnis
        obj.setEditorMode("Materialstand", 2)  # woraus gerechnet (gui_materialstand)
        obj.setEditorMode("Freivorschub", 0 if str(obj.Variante) == ADAPTIV_FREI else 2)

    @uhren.atmend_rechnen
    def opExecute(self, obj):
        self._editormodi(obj)
        try:
            if not self.horizFeed or self.horizFeed <= 0:
                raise ValueError(tr("vo.fehler.vorschub"))
            ergebnis = rechne(
                obj, self.job, self.model, self.horizFeed * 60.0, vo.eintauchvorschub(self)
            )
        except ValueError as fehler:
            obj.Ebenen = obj.Lagen = obj.Ringe = obj.Laeufe = 0
            obj.Gerechnet = ""
            FreeCAD.Console.PrintError(f"{obj.Label}: {fehler}\n")
            self.commandlist.append(Path.Command(f"({vo._ascii(str(fehler))})"))
            return
        obj.Ebenen, obj.Lagen = ergebnis.flaechen, ergebnis.lagen
        obj.Ringe, obj.Laeufe = ergebnis.ringe, ergebnis.laeufe
        obj.Gerechnet = gerechnet_text(ergebnis)
        if not ergebnis.haelt:  # keine Bahn hält die Last – Werkzeugbruch, laut sagen
            last = ergebnis.ueberlastet.get(ergebnis.variante, 0.0)
            FreeCAD.Console.PrintWarning(
                tr("ra.warnung.last", operation=obj.Label, last=f"{last:.1f}") + "\n"
            )
        # Im Freien mit dem Freivorschub, kurz vor dem Material langsam (freiwege, Manuel
        # 2026-10-04: „gib Gas bis kurz davor … bei allen Strategien“).
        # Mit „Adaptiv – schneller Freivorschub“ ist er die Obergrenze, sonst die Vorgabe.
        frei = float(obj.Freivorschub) * 60.0 if str(obj.Variante) == ADAPTIV_FREI else None
        punkte, _schnell = fw.fuer_operation(
            self.job, obj, ergebnis.punkte, self.horizFeed * 60.0, freivorschub=frei
        )
        self.commandlist.extend(
            bn.befehle(
                punkte,
                self.horizFeed * 60.0,  # CAM führt mm/s
                vo.eintauchvorschub(self),
            )
        )


def gerechnet_text(ergebnis):
    """„adaptiv 1,4 min · inseln 0,8 min (Last 4,1 ae)“ – die Varianten mit ihrer Zeit, die
    gewählte vorn; in Klammern die Last derer, die schneller wären, sie aber nicht halten."""
    teile = [f"{ergebnis.variante} {ergebnis.zeit:.1f} min"]
    if getattr(ergebnis, "gebremst", 0):
        teile[0] += f" ({tr('ra.gerechnet.gebremst', saetze=ergebnis.gebremst)})"
    for name, zeit in ergebnis.zeiten.items():
        if name != ergebnis.variante:
            teil = f"{name} {zeit:.1f} min"
            if name in ergebnis.ueberlastet:
                teil += f" (Last {ergebnis.ueberlastet[name]:.1f} ae)"
            teile.append(teil)
    return " · ".join(teile)


def rechne(obj, job, modell, vorschub=0.0, eintauchen=0.0):
    """Die Bahn (raeumen_bahn.Raeumbahn) für die Operation `obj` im Job; `vorschub` und
    `eintauchen` (mm/min) für die Zeit, nach der die Variante fällt. ValueError mit einem Satz,
    wenn es nicht geht."""
    form = vs.form_des_controllers(obj.ToolController)
    if form is None:
        raise ValueError(tr("ra.fehler.form"))
    # Was die Operationen davor schon weggenommen haben (W-012) – und woraus das gerechnet ist:
    # Ändert sich davor etwas, rechnet gui_materialstand das Räumen neu.
    stand = mst.fuer(job, vor=obj)
    if "Materialstand" in obj.PropertiesList:
        obj.Materialstand = mst.kennung_vor(job, obj)
    einfahrradius = float(obj.Einfahrradius)
    variante = str(obj.Variante)
    return bahn_fuer(
        job,
        modell,
        form,
        float(obj.Zustellung),
        float(obj.Zeilenabstand),
        float(obj.Aufmass),
        vo.flaechen(obj),
        aufmass_boden=float(obj.AufmassBoden),
        gleichlauf=sp.fuer_m3(obj.Gleichlauf, obj.ToolController),
        variante=variante if variante in VARIANTEN[1:] else None,
        einfahrradius=einfahrradius if einfahrradius > 0 else None,
        schneidenlaenge=ko.schneidenlaenge(obj.ToolController),
        oben=min(float(obj.StartDepth), pf.rohteil_von_oben(job)[4]),  # nie über dem Rohteil
        sicher=float(obj.SafeHeight),
        sicherheit=float(obj.Sicherheitsabstand),
        eintauchwinkel=float(obj.Eintauchwinkel),
        austritt=float(obj.VorschubAustritt) / 100.0,
        vorschub=vorschub,
        eintauchen=eintauchen,
        stand=stand,
        freivorschub=float(obj.Freivorschub) * 60.0,
        schritt=au.wert(obj, rb.SCHRITT),
        eng_lassen=bool(getattr(obj, "EngLassen", False)),
        nur_eng=float(getattr(obj, "NurEngVon", 0.0)),
    )


def bahn_fuer(
    job,
    modell,
    form,
    zustellung,
    zeilenabstand,
    aufmass=AUFMASS,
    flaechen=(),
    aufmass_boden=0.0,
    gleichlauf=True,
    variante=None,
    einfahrradius=None,
    schneidenlaenge=0.0,
    oben=None,
    sicher=None,
    sicherheit=vb.SICHERHEIT,
    eintauchwinkel=vb.EINTAUCHWINKEL,
    austritt=rb.AUSTRITT_ANTEIL,
    toleranz=hf.TOLERANZ,
    schritt=rb.SCHRITT,
    vorschub=0.0,
    eintauchen=0.0,
    stand=None,
    freivorschub=FREIVORSCHUB,
    eng_lassen=False,
    nur_eng=0.0,
):
    """Die Bahn „Räumen“ für Modell und Rohteil des Jobs. `flaechen`: die gewählten Flächen
    („Face6“ …) – geräumt werden die ebenen nach oben darunter; leer: die Oberseite des Teils.
    `oben`: z, wo die Lagen beginnen (None: die Oberkante des Rohteils); `sicher`: z für den
    Eilgang (None: Oberkante + Sicherheitsabstand + 3 mm); `vorschub` und `eintauchen` (mm/min)
    für die Zeit, nach der die Variante fällt; `stand`: der Materialstand davor (materialstand)
    – was die Operationen davor weggenommen haben, fräst es nicht noch einmal. ValueError mit
    einem Satz, wenn es nicht geht."""
    schnell_frei = variante == ADAPTIV_FREI
    if schnell_frei and (not math.isfinite(freivorschub) or freivorschub <= 0):
        raise ValueError(tr("ra.fehler.freivorschub"))
    form_teil = vs._teil(modell)
    x_von, x_bis, y_von, y_bis, z_oben = pf.rohteil_von_oben(job)
    if oben is None:
        oben = z_oben
    if sicher is None:
        sicher = oben + sicherheit + 3.0
    namen = list(flaechen) or hf.oberseite(form_teil)
    ebenen = hf.ebenen_oben(form_teil, namen)
    # Wände, die durch das Teil gehen: gedachte Böden an seiner Unterkante (Frage 4).
    gebiete = durch_gebiete(
        form_teil, [n for n in namen if durchgehend(form_teil, n)], (x_von, x_bis, y_von, y_bis)
    )
    durch = [g[0] for g in gebiete]
    durch_umrisse = {g[0].name: g[1] for g in gebiete}
    durch_waende = {g[0].name: list(g[2]) for g in gebiete}
    ebenen = ebenen + durch
    if not ebenen:
        raise ValueError(tr("ra.fehler.keine_ebene"))
    dynamik = msp.dynamik_des_jobs(job)
    # Gewählte Flächen unter der Oberseite (ein Nutgrund, ein Absatz): nur über ihnen räumen
    # (Manuel, 2026-10-16). Über der Oberseite gehört alles Rohteil zu ihr, und ohne Wahl ist es
    # die Oberseite: wie bisher vom Rand des Rohteils her.
    nur_ueber = None
    if flaechen:
        hoechste = form_teil.BoundBox.ZMax - hf.TOLERANZ
        nur_ueber = umrisse(
            form_teil, [e.name for e in ebenen if e.z < hoechste and e not in durch]
        )
        if durch_umrisse:
            nur_ueber = {**(nur_ueber or {}), **durch_umrisse}
    werte = rb.Raeumwerte(
        form=form,
        zustellung=zustellung,
        zeilenabstand=zeilenabstand,
        aufmass=aufmass,
        oben=oben,
        sicher=sicher,
        rohteil=(x_von, x_bis, y_von, y_bis),
        aufmass_boden=aufmass_boden,
        gleichlauf=gleichlauf,
        variante="adaptiv" if schnell_frei else variante,
        einfahrradius=einfahrradius,
        schneidenlaenge=schneidenlaenge,
        sicherheit=sicherheit,
        eintauchwinkel=eintauchwinkel,
        austritt=austritt,
        vorschub=vorschub,
        eintauchen=eintauchen,
        freivorschub=freivorschub if schnell_frei else 0.0,
        eilgang=dynamik[0],
        beschleunigung=dynamik[1],
        nur_ueber=nur_ueber,
        eng_lassen=bool(eng_lassen),
        nur_eng=float(nur_eng or 0.0),
    )
    netz = hf.netze_je_hoehe(form_teil, ebenen, toleranz)
    konturen = konturen_des_teils(form_teil)
    konturen = konturen + taschen_unter_oeffnungen(form_teil, ebenen, konturen)
    bahn = rb.planen(netz, werte, ebenen, konturen, schritt, stand)
    if durch:
        # Ein gedachter Boden ist keine Fläche des Teils: „Rest räumen“ bekommt statt seiner die
        # Wände, die ihn begrenzen – darunter räumt es wieder bis durch (W-034, ein enges Gebiet
        # für den kleineren Fräser).
        ausgelassen = []
        for name in bahn.ausgelassen:
            for flaeche in durch_waende.get(name, []) if name.startswith(DURCH) else [name]:
                if flaeche not in ausgelassen:
                    ausgelassen.append(flaeche)
        bahn.ausgelassen = ausgelassen
    return bahn


DURCH = "Durch"  # so beginnen die Namen der gedachten Böden (durch_ebenen)


def durchgehend(form_teil, name):
    """Geht die Wand `name` durch das Teil – liegt ihre Unterkante auf seinem tiefsten Punkt? Dann
    hat sie keinen Boden; das Räumen räumt bis an die Unterkante (durch_ebenen)."""
    waende = kb.waende(form_teil, [name])
    return bool(waende) and waende[0].z_unten <= form_teil.BoundBox.ZMin + hf.HOEHE_GLEICH


def _punkt_im_gebiet(gebiet, abstand=0.5):
    """(x, y) eines Punkts in der ebenen Fläche `gebiet`, mindestens `abstand` von ihrem Rand –
    auf einem Gitter über ihren Kasten gesucht, von der Mitte nach außen; None, wenn keiner."""
    import Part

    bb = gebiet.BoundBox
    z = bb.ZMin
    anzahl = 24
    punkte = [
        (bb.XMin + bb.XLength * (i + 0.5) / anzahl, bb.YMin + bb.YLength * (j + 0.5) / anzahl)
        for i in range(anzahl)
        for j in range(anzahl)
    ]
    mitte = (bb.Center.x, bb.Center.y)
    punkte.sort(key=lambda p: (p[0] - mitte[0]) ** 2 + (p[1] - mitte[1]) ** 2)
    rand = Part.Compound(gebiet.Wires)
    for x, y in punkte:
        punkt = FreeCAD.Vector(x, y, z)
        if not gebiet.isInside(punkt, 1e-6, True):
            continue
        if rand.distToShape(Part.Vertex(punkt))[0] >= abstand:
            return x, y
    return None


def durch_ebenen(form_teil, namen, rohteil):
    """([hoehenfeld.Ebene], {Name: Umriss-Schleifen}) aus durch_gebiete()."""
    gebiete = durch_gebiete(form_teil, namen, rohteil)
    return [g[0] for g in gebiete], {g[0].name: g[1] for g in gebiete}


def durch_gebiete(form_teil, namen, rohteil):
    """[(hoehenfeld.Ebene, Umriss-Schleifen, [Wände])] – die gedachten Böden unter den Wänden
    `namen`, die durch das Teil gehen (Manuel, 2026-10-17, Frage 4: „Ja, Räumen tritt an“ – an
    durchgehenden Wänden gegen die Kontur, am C-Ring 4,2 statt 7,1 min). Je Gebiet neben dem
    Teil an seiner Unterkante (das Rechteck des Rohteils ohne den Fußabdruck), das an eine der
    Wände stößt und nur von gewählten Wänden und dem Rand des Rohteils begrenzt ist – sonst
    räumte das Räumen Wände mit, die niemand gewählt hat. Die Höhe: die Unterkante des Teils, so
    tief wie die Kontur dort fährt; dazu je Gebiet die Wände, die es begrenzen. Leer ohne solche
    Wände oder Gebiete."""
    import Part

    if not namen:
        return []
    z = form_teil.BoundBox.ZMin
    gewaehlt = kb.waende(form_teil, namen)
    waende = [w.flaeche for w in gewaehlt]
    if not waende:
        return []
    hoehe = z + min(0.05, 0.5 * min(w.BoundBox.ZLength for w in waende))
    try:
        draehte = form_teil.slice(FreeCAD.Vector(0, 0, 1), hoehe)
        fuss = Part.makeFace(draehte, "Part::FaceMakerBullseye")
        x0, x1, y0, y1 = rohteil
        rand = 1.0
        rechteck = Part.makePlane(
            x1 - x0 + 2 * rand, y1 - y0 + 2 * rand, FreeCAD.Vector(x0 - rand, y0 - rand, hoehe)
        )
        gebiete = rechteck.cut(fuss).Faces
    except Exception as fehler:  # noqa: BLE001 – OCC: dann ohne gedachte Böden (die Kontur)
        FreeCAD.Console.PrintLog(f"CAM-Addon: Räumen bis durch: {fehler}\n")
        return []

    def am_rand(p):
        return (
            min(
                abs(p.x - (x0 - rand)),
                abs(p.x - (x1 + rand)),
                abs(p.y - (y0 - rand)),
                abs(p.y - (y1 + rand)),
            )
            < 1e-6
        )

    def wand_an(p):
        """Der Name der gewählten Wand, auf der `p` liegt – oder None."""
        punkt = Part.Vertex(p)
        return next((w.name for w in gewaehlt if w.flaeche.distToShape(punkt)[0] < 0.02), None)

    ergebnis = []
    for gebiet in gebiete:
        mitten = [k.valueAt(0.5 * (k.FirstParameter + k.LastParameter)) for k in gebiet.Edges]
        innen = [wand_an(p) for p in mitten if not am_rand(p)]
        if not innen or None in innen:
            continue
        name = f"{DURCH}{len(ergebnis) + 1}"
        punkt = _punkt_im_gebiet(gebiet)
        if punkt is None:
            continue
        schleifen = [
            [(float(p.x), float(p.y)) for p in draht.discretize(Deflection=0.05)]
            for draht in gebiet.Wires
        ]
        # Der Kasten der Ebene: ein Punkt im Gebiet. Seine Mitte sagt raeumen_bahn._tasche_um, ob
        # die Fläche in einer Tasche liegt – die Mitte des ganzen Gebiets um das Teil läge in
        # einer Bohrung in der Mitte (ein Flansch), und es räumte die Bohrung statt außen herum.
        ebene = hf.Ebene(name, float(z), punkt[0], punkt[0], punkt[1], punkt[1])
        ergebnis.append((ebene, schleifen, sorted(set(innen), key=lambda n: int(n[4:]))))
    return ergebnis


UMRISSE_HOECHSTENS = 200  # mehr Flächen (ein Teil aus einem STL): ohne Umrisse, wie bisher


def umrisse(form_teil, namen):
    """{Fläche: [Schleife [(x, y) …] …]} – der Umriss jeder ebenen Fläche `namen` von oben, ihre
    Drähte auf 0,05 mm genau (raeumen_bahn.Raeumwerte.nur_ueber). None bei zu vielen Flächen."""
    if not namen or len(namen) > UMRISSE_HOECHSTENS:
        return None
    ergebnis = {}
    for name in namen:
        try:
            flaeche = form_teil.getElement(name)
            ergebnis[name] = [
                [(float(p.x), float(p.y)) for p in draht.discretize(Deflection=0.05)]
                for draht in flaeche.Wires
            ]
        except Exception:  # eine Fläche, deren Umriss sich nicht holen lässt: ohne Grenze
            continue
    return ergebnis or None


def taschen_unter_oeffnungen(form_teil, ebenen, konturen=()):
    """[kb.Kontur] für die Böden in `ebenen`, um die keine Kontur aus senkrechten Wänden eine
    Tasche bildet, die aber unter einer Öffnung liegen – einem Loch in einer ebenen Fläche nach
    oben darüber –, in die bis zum Boden nichts vom Teil hineinragt: Ihre Wände stehen nicht
    senkrecht, sie hängen über (unten weiter als oben; Manuels tiefe Tasche, 2026-10-25: „oben
    angefangen … in einer helix … dann mit morphkreisen von da aus rauskaut“). Von oben ist die
    Öffnung die Wand der Tasche: ihr Umriss, senkrecht auf den Boden gelegt. Den Rest unter dem
    Rand nimmt das Anstellen."""
    import Part

    ergebnis = []
    oeffnungen = []  # (z, Draht, Namen der Flächen daran)
    kanten_je_flaeche = {}
    for i, f in enumerate(form_teil.Faces):
        kanten_je_flaeche[f"Face{i + 1}"] = {k.hashCode() for k in f.Edges}
    for i, f in enumerate(form_teil.Faces):
        if not isinstance(f.Surface, Part.Plane) or len(f.Wires) < 2:
            continue
        n = f.normalAt(*f.Surface.parameter(f.CenterOfMass))
        if f.Orientation == "Reversed":
            n = -n
        if n.z < 1.0 - 1e-6:
            continue
        for draht in f.Wires:
            if draht.isSame(f.OuterWire):
                continue
            kanten = {k.hashCode() for k in draht.Edges}
            namen = tuple(
                name
                for name, k in kanten_je_flaeche.items()
                if k & kanten and name != f"Face{i + 1}"
            )
            oeffnungen.append((f.BoundBox.ZMax, draht, namen))
    if not oeffnungen:
        return []
    for e in ebenen:
        mitte = ((e.x_von + e.x_bis) / 2, (e.y_von + e.y_bis) / 2)
        schon = False
        for k in konturen:
            if not k.geschlossen or abs(k.z_unten - e.z) > kb.NAH:
                continue
            flaeche = rb.kontur_flaeche(k)
            if flaeche is not None and rb.ist_tasche(k, flaeche) and rb.innerhalb(flaeche, *mitte):
                schon = True
                break
        if schon:
            continue
        beste = None
        for z, draht, namen in oeffnungen:
            if z <= e.z + hf.HOEHE_GLEICH or (beste is not None and z >= beste[0]):
                continue
            try:
                unten = draht.copy()
                unten.translate(FreeCAD.Vector(0, 0, -z))
                flaeche = Part.Face(unten)
            except Exception:  # noqa: BLE001 – OCC: kein Gesicht aus dem Draht
                continue
            if rb.innerhalb(flaeche, *mitte):
                beste = (z, draht, namen, flaeche)
        if beste is None:
            continue
        z, draht, namen, flaeche = beste
        try:
            boden = draht.copy()
            boden.translate(FreeCAD.Vector(0, 0, e.z - z))
            saeule = Part.Face(boden).extrude(FreeCAD.Vector(0, 0, z - e.z))
            # Ragt das Teil in die Öffnung hinein (eine Formschräge, oben weiter als unten)? Dann
            # ist sie nicht die Wand – das macht der Rest des Räumens wie bisher.
            if saeule.common(form_teil).Volume > 1e-6 * max(saeule.Volume, 1.0):
                continue
        except Exception:  # noqa: BLE001 – OCC
            continue
        laengste = max(boden.Edges, key=lambda k: k.Length)
        mitte_kante = laengste.valueAt(
            laengste.FirstParameter + 0.5 * (laengste.LastParameter - laengste.FirstParameter)
        )
        t = laengste.tangentAt(
            laengste.FirstParameter + 0.5 * (laengste.LastParameter - laengste.FirstParameter)
        )
        normale = (-t.y, t.x)
        laenge = math.hypot(*normale) or 1.0
        normale = (normale[0] / laenge, normale[1] / laenge)
        if not rb.innerhalb(
            flaeche, mitte_kante.x + normale[0] * 0.01, mitte_kante.y + normale[1] * 0.01
        ):
            normale = (-normale[0], -normale[1])
        ergebnis.append(
            kb.Kontur(
                draht=boden,
                z_unten=e.z,
                z_oben=z,
                geschlossen=True,
                stelle=(mitte_kante.x, mitte_kante.y),
                normale=normale,
                waende=namen,
            )
        )
    return ergebnis


def konturen_des_teils(form_teil):
    """Die Unterkanten aller Wände des Teils als Konturen – leer, wenn es keine Wand gibt."""
    namen = [f"Face{i + 1}" for i in range(ft.anzahl(form_teil))]
    try:
        return kb.konturen(form_teil, namen)
    except ValueError:
        return []


def vorschau(
    job,
    modell,
    form,
    zustellung,
    zeilenabstand,
    aufmass,
    flaechen,
    aufmass_boden=0.0,
    gleichlauf=True,
    schneidenlaenge=0.0,
    vorschub=0.0,
    eintauchen=0.0,
    stand=None,
    variante=None,
    freivorschub=FREIVORSCHUB,
    eng_lassen=False,
    nur_eng=0.0,
):
    """Die Bahn grob – für Lagen, Ringe, Zeit und ob es geht, im Assistenten: gröber vernetzt,
    gröberes Raster. ValueError wie bahn_fuer()."""
    return bahn_fuer(
        job,
        modell,
        form,
        zustellung,
        zeilenabstand,
        aufmass,
        flaechen,
        aufmass_boden=aufmass_boden,
        gleichlauf=gleichlauf,
        schneidenlaenge=schneidenlaenge,
        toleranz=hf.VORSCHAU_TOLERANZ,
        schritt=rb.VORSCHAU_SCHRITT,
        vorschub=vorschub,
        eintauchen=eintauchen,
        stand=stand,
        variante=variante,
        freivorschub=freivorschub,
        eng_lassen=eng_lassen,
        nur_eng=nur_eng,
    )


@dataclass
class Vorbohren:
    """Was das Vorbohren fürs Räumen bringt (vorschau_fuer_assistent mit `vorbohren`)."""

    stellen: list  # [(x, y, z)] – je Loch, z: so tief mit vollem Durchmesser
    durchmesser: float
    zeit: float  # Minuten Bohren
    ohne: float  # Minuten Räumen ohne Vorbohren
    hube: int
    tiefe: float  # mm – das tiefste Loch ab der Oberkante des Rohteils
    zu_kurz: bool = False  # tiefer als die Schneide des Bohrers
    geholfen: int = 0  # so viele Eintauchstellen ins Volle weniger
    kennung: str = ""  # der Bohrer (Werkzeugverwaltung)
    # Je Loch (x, y, z, Ø, Kennung des Bohrers) – verschiedene Bohrer (die Nuten verschieden
    # breit); leer: alle `stellen` mit `durchmesser` und `kennung`.
    loecher: list = field(default_factory=list)
    # Die Bahn ohne Vorbohren (ihre Punkte) und ihre Zeit im Freien (freiwege, min; None: noch
    # nicht gerechnet) – für die Frage „Eintauchen“ im Assistenten (W-039): beide Wege, ohne
    # dass einer noch einmal gerechnet wird.
    ohne_punkte: list = field(default_factory=list)
    ohne_frei: float = None

    def je_loch(self):
        """[(x, y, z, Ø, Kennung)] je Loch."""
        if self.loecher:
            return list(self.loecher)
        return [(x, y, z, self.durchmesser, self.kennung) for x, y, z in self.stellen]


def vorbohr_stellen(bahn, nah=VORBOHREN_NAH):
    """[(x, y, z)] – wo das Räumen ins Volle eintaucht (raeumen_bahn.Raeumbahn.eintauchen), je
    Stelle die tiefste Lage: Dort vorgebohrt, taucht es senkrecht ein (Manuel, 2026-10-25, Frage 4:
    „bei egal welchem teil immer wenn man eintauchen muss ists gut wenn vorgebohrt ist“)."""
    stellen = []
    for x, y, z in getattr(bahn, "eintauchen", ()) or ():
        for i, (sx, sy, sz) in enumerate(stellen):
            if math.hypot(x - sx, y - sy) <= nah:
                stellen[i] = (sx, sy, min(sz, z))
                break
        else:
            stellen.append((x, y, z))
    return stellen


def vorbohr_bahn(stellen, durchmesser, spitzenwinkel, oben, sicher, vorschub):
    """Die Bewegungen des Bohrens an den `stellen` (bohren.planen) – für die Zeit."""
    from . import bohren as bh
    from . import bohrung_bahn as bb

    liste = [
        bb.Bohrung("", (x, y), durchmesser / 2.0, oben, z, False, spitzenwinkel)
        for x, y, z in stellen
    ]
    return bh.planen(liste, durchmesser, spitzenwinkel, oben, sicher, vorschub)


def vorschau_fuer_assistent(
    job, form, zustellung, zeilenabstand, aufmass, flaechen, vorbohren=None, **weiter
):  # fmt: skip
    """Die Vorschau im Assistenten „Bearbeitung“ (gui_bearbeitung, auch im Nebenrechner:
    bearbeitung_vorschau): grob (vorschau()) – mit Ringen die genaue Bahn (bahn_fuer()), denn die
    grobe rechnet eine etwas andere und kann die Last unterschätzen: Am Testteil maß sie in der
    dreieckigen Tasche (Ø 6) 1,7 ae, die genaue Bahn, die die Maschine fährt, 4,5 ae
    (Werkzeugbruch; Manuel, 2026-10-04). Adaptiv hält die Last nach seiner Bauart, „ringe“ ohne
    Blick auf sie. `weiter`: die Schlüsselwörter von vorschau(). Mit `vorbohren` ({durchmesser,
    spitzenwinkel, vorschub, schneidenlaenge} des Bohrers) dort vorgebohrt, wo es ins Volle
    eintaucht (vorbohr_stellen): die Bahn mit den Löchern im Materialstand gerechnet, dazu
    `bahn.vorbohren` (Vorbohren)."""
    argumente = (job, job.Model.Group, form, zustellung, zeilenabstand, aufmass, flaechen)

    def rechnen(weiter):
        bahn = vorschau(*argumente, **weiter)
        if bahn.variante == "adaptiv" or weiter.get("variante") == rb.RINGE:
            return bahn
        try:
            return bahn_fuer(*argumente, **weiter)
        except ValueError:
            return bahn

    bahn = rechnen(weiter)
    stand = weiter.get("stand")
    stellen = vorbohr_stellen(bahn) if vorbohren and stand is not None else []
    if not stellen:
        return bahn
    durchmesser = float(vorbohren["durchmesser"])
    *_rohteil, oben = pf.rohteil_von_oben(job)
    bohrung = vorbohr_bahn(
        stellen,
        durchmesser,
        float(vorbohren.get("spitzenwinkel") or 118.0),
        oben,
        oben + 5.0,
        float(vorbohren.get("vorschub") or 0.0),
    )
    mit = loecher_im_stand(stand, stellen, durchmesser, oben)
    neu = rechnen(dict(weiter, stand=mit))
    tiefe = max(oben - z for _x, _y, z in stellen)
    neu.vorbohren = Vorbohren(
        stellen,
        durchmesser,
        bohrung.zeit,
        bahn.zeit,
        bohrung.hube,
        tiefe,
        zu_kurz=0 < float(vorbohren.get("schneidenlaenge") or 0.0) < tiefe,
        geholfen=len(vorbohr_stellen(bahn)) - len(vorbohr_stellen(neu)),
        kennung=str(vorbohren.get("kennung") or ""),
        ohne_punkte=list(bahn.punkte),
    )
    return neu


def loecher_im_stand(stand, stellen, durchmesser, oben):
    """Der Materialstand mit den Löchern des Vorbohrens: je Stelle (x, y, z) – oder (x, y, z, Ø)
    mit eigenem Durchmesser – der volle Durchmesser bis z (die Spitze darunter zählt nicht)."""
    from . import fraeserform as ff

    je_d = {}
    for stelle in stellen:
        x, y, z = stelle[:3]
        d = float(stelle[3]) if len(stelle) > 3 else float(durchmesser)
        je_d.setdefault(round(d, 4), []).append((x, y, z))
    for d, orte in sorted(je_d.items()):
        loecher = []
        for x, y, z in orte:
            loecher += [bn.Punkt(True, x, y, oben + 5.0), bn.Punkt(False, x, y, z, True)]
            loecher.append(bn.Punkt(True, x, y, oben + 5.0))
        stand = mst.mit_bahn(stand, tr("ra.vorbohren.name"), loecher, ff.scheibe(d / 2.0))
    return stand


def lege_an(
    job,
    tc,
    zustellung,
    zeilenabstand,
    aufmass=AUFMASS,
    aufmass_boden=0.0,
    gleichlauf=True,
    name=None,
    flaechen=(),
    variante="automatisch",
    freivorschub=FREIVORSCHUB,
    eng_lassen=False,
    nur_eng=0.0,
):
    """Legt „Räumen“ im Job an – ohne eigene Transaktion, die hält der Aufrufer. Tiefen und
    Höhen wie FreeCADs Operationen (planfraesen._hoehen); die Endtiefe ist die tiefste Fläche
    plus Aufmaß am Boden. Gibt die Operation zurück."""
    dokument = job.Document
    obj = dokument.addObject("Path::FeaturePython", "Raeumen")
    obj.addProperty("App::PropertyBool", "DoNotSetDefaultValues", "Path")
    obj.DoNotSetDefaultValues = True
    proxy = Raeumen(obj, "Raeumen", job)
    obj.removeProperty("DoNotSetDefaultValues")
    obj.Proxy = proxy
    job.Proxy.addOperation(obj)
    obj.Active = True
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.CoolantMode = job.SetupSheet.CoolantMode
    pf._hoehen(obj, proxy, job)
    obj.Zustellung = zustellung
    obj.Zeilenabstand = zeilenabstand
    obj.Aufmass = aufmass
    obj.AufmassBoden = aufmass_boden
    obj.Gleichlauf = bool(gleichlauf)
    obj.Variante = variante
    obj.Freivorschub = freivorschub / 60.0
    obj.EngLassen = bool(eng_lassen)
    obj.NurEngVon = float(nur_eng or 0.0)
    obj.Flaechen = list(flaechen)
    _endtiefe(obj, job)
    obj.Label = namen.eindeutig(
        obj.Document, name or tr("ra.name", werkzeug=f"T{tc.ToolNumber}"), obj
    )
    if FreeCAD.GuiUp:
        from . import gui_vierachs_operation

        gui_vierachs_operation.Ansicht(obj.ViewObject)
    return obj


def _endtiefe(obj, job):
    """Die Endtiefe: die tiefste gewählte Fläche plus Aufmaß am Boden – zum Lesen; die Bahn
    rechnet aus den Flächen."""
    try:
        form_teil = vs._teil(job.Model.Group)
        namen = list(obj.Flaechen) or hf.oberseite(form_teil)
        hoehen = [e.z for e in hf.ebenen_oben(form_teil, namen)]
        if any(durchgehend(form_teil, n) for n in namen):
            hoehen.append(form_teil.BoundBox.ZMin)  # bis durch (durch_ebenen)
    except ValueError:
        hoehen = []
    if hoehen:
        obj.setExpression("FinalDepth", None)
        obj.FinalDepth = min(hoehen) + float(obj.AufmassBoden)


def aendere(
    obj,
    tc,
    zustellung,
    zeilenabstand,
    aufmass,
    aufmass_boden=0.0,
    gleichlauf=True,
    flaechen=None,
    variante=None,
    freivorschub=None,
    eng_lassen=None,
    nur_eng=None,
):
    """Gibt der Operation einen (anderen) Werkzeug-Controller und neue Werte – ohne eigene
    Transaktion; `flaechen` ohne bleibt. Der Name folgt dem Werkzeug, solange es der
    vorgeschlagene ist."""
    if _vorgeschlagener_name(obj.Label):
        obj.Label = namen.eindeutig(obj.Document, tr("ra.name", werkzeug=f"T{tc.ToolNumber}"), obj)
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.Zustellung = zustellung
    obj.Zeilenabstand = zeilenabstand
    obj.Aufmass = aufmass
    obj.AufmassBoden = aufmass_boden
    obj.Gleichlauf = bool(gleichlauf)
    if variante is not None:
        obj.Variante = variante
    if freivorschub is not None:
        obj.Freivorschub = freivorschub / 60.0
    if eng_lassen is not None and "EngLassen" in obj.PropertiesList:
        obj.EngLassen = bool(eng_lassen)
    if nur_eng is not None and "NurEngVon" in obj.PropertiesList:
        obj.NurEngVon = float(nur_eng)
    if flaechen is not None and list(flaechen) != list(obj.Flaechen):
        obj.Flaechen = list(flaechen)
    job = getattr(obj.Proxy, "job", None)
    if job is not None:
        _endtiefe(obj, job)


def _vorgeschlagener_name(name):
    """Ist `name` einer, wie lege_an ihn vergibt („Räumen T1“) – auch mit „ (2)“ dahinter?"""
    return namen.nach_vorlage(name, tr("ra.name", werkzeug="\0"))


def ist_raeumen(op):
    """Ist `op` eine Operation dieses Moduls – „Räumen“?"""
    return isinstance(getattr(op, "Proxy", None), Raeumen)
