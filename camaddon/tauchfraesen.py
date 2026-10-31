# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die CAM-Operation „Tauchfräsen“ (Plan C2; Manuel, 2026-10-31: „man bohrt ein loch und kaut
stechend dann das zeug mit einem messerkopf raus … alles möglichkeiten die der benutzer haben muss“;
zum Bild `docs/bilder/tauchfraesen_entwurf.png`: „ja.. so ists ok“).

Im Assistenten ein Weg im Schruppen, den man anhakt – von sich aus wählt er weiter Räumen
(Gedächtnis „Strategiewahl erst besprechen“).

Der Fräser (ein Tauchfräser oder ein mittenschneidender Schaftfräser mit Wendeplatten) taucht
senkrecht ins Volle, Stelle an Stelle:

- **Wo:** über dem Boden, soweit dort Rohteil und kein Teil ist (gebiet: in einer Tasche ihre
  Öffnung, um einen Zapfen bis an den Rand des Rohteils). Die Mitte des Fräsers bleibt um Radius +
  Aufmaß von der Kontur weg (makeOffset2D); über den Rand des Rohteils darf sie hinaus. Darin
  liegen die Stellen in einem Raster (`schritt`, höchstens 0,7 × D – dann bleiben zwischen vier
  Stellen nur kleine Zwickel), dazu Stellen längs der versetzten Kontur im selben Abstand, damit
  die Wände gleichmäßig Aufmaß behalten.
- **Reihenfolge:** von der Mitte (dort wird vorgebohrt) nach außen, jede neue Stelle neben dem
  schon Offenen (von_innen_nach_aussen).
- **Wie:** im Eilgang über die Stelle (knapp über der Oberkante), senkrecht mit dem
  Eintauchvorschub bis auf den Boden + Aufmaß, im Eilgang zurück nach oben, zur nächsten – kein
  Zickzack, kein Rampen.
- **Lagen:** Ist die Tasche tiefer als die Schneide lang, in gleich tiefen Lagen, je Lage alle
  Stellen; ab der zweiten im Eilgang bis knapp über die Lage davor (das Loch ist offen).

Die Operation (wie „Nut“, nut.py) erbt FreeCADs ObjectOp: Werkzeug-Controller, Kühlmittel, Tiefen
und Höhen; beim Neuberechnen rechnet sie ihre Bahn aus Modell und Rohteil des Jobs. Modul- und
Klassenname stehen in jeder gespeicherten Datei – sie bleiben. Kein Qt hier.

Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass

from . import bahn as bh
from .sprache import tr

SCHRITT_ANTEIL = 0.7  # × D: größter Abstand der Stellen
ABHEBEN = 1.0  # mm über der Oberkante zwischen den Stellen (und über der Lage davor)
AUFMASS = 0.5  # mm – bleibt an der Wand fürs Schlichten
SCHNITT_UEBER = 0.01  # mm über dem Boden: dort schneidet gebiet() das Teil
GRUPPE = "Fräsen"


def stellen(boden, radius, aufmass=0.0, schritt=None):
    """[(x, y)] der Tauchstellen über der ebenen, waagerechten Fläche `boden` (Part.Face), in der
    Reihenfolge des Fräsens – leer, wenn der Fräser nicht hineinpasst."""
    import FreeCAD

    schritt = schritt or SCHRITT_ANTEIL * 2 * radius
    try:
        innen = boden.makeOffset2D(-(radius + aufmass), join=0)
    except Exception:  # Part.OCCError: zu eng für den Fräser
        return []
    if innen.isNull() or not innen.Faces or innen.Area < 1e-6:
        return []
    z = boden.BoundBox.ZMax
    box = innen.BoundBox
    punkte = []
    zeilen = max(1, math.ceil(box.YLength / schritt))
    for zeile in range(zeilen + 1):
        y = box.YMin + min(zeile * box.YLength / zeilen, box.YLength)
        spalten = max(1, math.ceil(box.XLength / schritt))
        for spalte in range(spalten + 1):
            x = box.XMin + spalte * box.XLength / spalten
            if innen.isInside(FreeCAD.Vector(x, y, z), 1e-6, True):
                punkte.append((x, y))
    # Längs der Kontur der versetzten Fläche, damit die Wände gleichmäßig Aufmaß behalten.
    for kante in innen.Edges:
        anzahl = max(1, math.ceil(kante.Length / schritt))
        for i in range(anzahl):
            p = kante.valueAt(
                kante.FirstParameter + i * (kante.LastParameter - kante.FirstParameter) / anzahl
            )
            if all(math.hypot(p.x - a, p.y - b) > 0.5 * schritt for a, b in punkte):
                punkte.append((p.x, p.y))
    if len(boden.Wires) > 1:
        # Um eine Insel (eine Außenkontur): von außen nach innen – die erste Stelle an einer Ecke
        # des Gebiets, am Rand des Rohteils, wo es frei ist.
        return von_innen_nach_aussen(punkte, (box.XMin, box.YMin))
    mitte = innen.CenterOfMass if innen.isInside(innen.CenterOfMass, 1e-6, True) else None
    return von_innen_nach_aussen(punkte, (mitte.x, mitte.y) if mitte is not None else None)


def gebiet(form, boden, rohteil, rand):
    """[Part.Face] – wo über dem Boden `boden` (ebene Fläche nach oben) getaucht werden darf: der
    Umriss des Rohteils (x_von, x_bis, y_von, y_bis), um `rand` größer (der Fräser darf über den
    Rand hinaus, ins Freie), ohne den Schnitt des Teils knapp über dem Boden – davon die Stücke,
    die am Boden liegen. So taucht es in einer Tasche in ihrer Öffnung, um eine Außenkontur (Manuel,
    2026-10-31: „geht auch für ne ausen kontur“) zwischen ihr und dem Rand des Rohteils. Geht der
    Schnitt nicht: [boden]."""
    import FreeCAD
    import Part

    try:
        z = boden.BoundBox.ZMax
        x0, x1, y0, y1 = rohteil
        V = FreeCAD.Vector
        rahmen = Part.Face(
            Part.makePolygon(
                [
                    V(x0 - rand, y0 - rand, z),
                    V(x1 + rand, y0 - rand, z),
                    V(x1 + rand, y1 + rand, z),
                    V(x0 - rand, y1 + rand, z),
                    V(x0 - rand, y0 - rand, z),
                ]
            )
        )
        drahte = form.slice(V(0, 0, 1), z + SCHNITT_UEBER)
        if drahte:
            teil = Part.makeFace(drahte, "Part::FaceMakerBullseye")
            teil.translate(V(0, 0, z - teil.BoundBox.ZMin))
            frei = rahmen.cut(teil)
        else:
            frei = rahmen
        stuecke = [f for f in frei.Faces if f.common(boden).Area > 1e-6]
        return stuecke or [boden]
    except Exception:  # Part.OCCError – dann wie bisher: der Boden selbst
        return [boden]


def von_innen_nach_aussen(punkte, mitte=None):
    """Die Reihenfolge (Manuel, 2026-10-31: „bohrt mittig ein loch und fräst dann“; zum ersten
    Entwurf: „wieso zuickzack bahn ?“): zuerst die Stelle an der Mitte (dort wird vorgebohrt),
    dann immer die, die dem schon Offenen am nächsten liegt – so greift jede neue Stelle neben
    Offenem an und schneidet nur zum Teil ins Volle; bei Gleichstand die nächste zur letzten."""
    if not punkte:
        return []
    if mitte is None:
        mitte = (sum(p[0] for p in punkte) / len(punkte), sum(p[1] for p in punkte) / len(punkte))
    offen = list(punkte)
    erste = min(offen, key=lambda p: math.hypot(p[0] - mitte[0], p[1] - mitte[1]))
    folge = [erste]
    offen.remove(erste)
    while offen:
        letzte = folge[-1]
        naechste = min(
            offen,
            key=lambda p: (
                round(min(math.hypot(p[0] - a, p[1] - b) for a, b in folge), 3),
                math.hypot(p[0] - letzte[0], p[1] - letzte[1]),
            ),
        )
        folge.append(naechste)
        offen.remove(naechste)
    return folge


def bahn(punkte, z_oben, z_unten, z_frei=None):
    """[bahn.Punkt]: je Stelle im Eilgang darüber (ABHEBEN über `z_oben`), mit Eintauchvorschub
    auf `z_unten`, im Eilgang zurück. `z_frei`: bis dahin ist das Loch schon offen (die Lage
    davor) – im Eilgang bis ABHEBEN darüber."""
    ergebnis = []
    oben = z_oben + ABHEBEN
    for x, y in punkte:
        ergebnis.append(bh.Punkt(True, x, y, oben))
        if z_frei is not None and z_frei + ABHEBEN < oben:
            ergebnis.append(bh.Punkt(True, x, y, z_frei + ABHEBEN))
        ergebnis.append(bh.Punkt(False, x, y, z_unten, eintauchen=True))
        ergebnis.append(bh.Punkt(True, x, y, oben))
    return ergebnis


@dataclass
class Tauchbahn:
    punkte: list  # [bahn.Punkt]
    stellen: int  # Tauchstellen je Lage, über alle Böden
    lagen: int  # die meisten Lagen eines Bodens
    boeden: int
    namen: list = None  # die Böden, über denen getaucht wird („Face7“ …)
    vorbohren: object = None  # raeumen.Vorbohren – in der Mitte jeder Tasche vorgebohrt


def bahn_fuer(
    job,
    modell,
    radius,
    flaechen,
    aufmass=AUFMASS,
    aufmass_boden=0.0,
    schritt=None,
    schneidenlaenge=0.0,
    oben=None,
    vorbohren=None,
):
    """Die Bahn „Tauchfräsen“ (Tauchbahn) über den ebenen Flächen nach oben unter `flaechen`
    („Face7“ …) – von oben nach unten, je Boden die Stellen (stellen) in Lagen bis auf den Boden +
    `aufmass_boden`. Mit `vorbohren` ({kennung, durchmesser, spitzenwinkel, schneidenlaenge,
    vorschub} eines Bohrers): an der ersten Stelle jeder Tasche ein Loch bis auf den Boden (Manuel,
    2026-10-31: „bohrt mittig ein loch“) – um eine Insel nicht, dort beginnt es im Freien.
    ValueError mit einem Satz, wenn es nicht geht."""
    from . import hoehenfeld as hf
    from . import planfraesen as pf
    from . import vierachs_schlichten as vs

    form = vs._teil(modell)
    ebenen = hf.ebenen_oben(form, list(flaechen))
    if not ebenen:
        raise ValueError(tr("tf.fehler.keine"))
    rohteil = None
    try:
        *rohteil, z_rohteil = pf.rohteil_von_oben(job)
    except ValueError:  # ohne Rohteil: nur über den Böden selbst
        z_rohteil = max(e.z for e in ebenen)
    if oben is None:
        oben = z_rohteil
    punkte, stellen_zahl, lagen_zahl, boeden, namen = [], 0, 0, 0, []
    loecher = []  # (x, y, z) – vorgebohrt
    for ebene in sorted(ebenen, key=lambda e: -e.z):
        z_unten = ebene.z + aufmass_boden
        tiefe = oben - z_unten
        if tiefe <= 1e-6:
            continue
        boden = form.getElement(ebene.name)
        stellen_ = []
        for stueck in gebiet(form, boden, rohteil, radius + aufmass) if rohteil else [boden]:
            hier = stellen(stueck, radius, aufmass, schritt)
            if hier and vorbohren and len(stueck.Wires) == 1:
                loecher.append((hier[0][0], hier[0][1], z_unten))
            stellen_ += hier
        if not stellen_:
            continue
        lagen = max(1, math.ceil(tiefe / schneidenlaenge - 1e-9)) if schneidenlaenge > 0 else 1
        frei = None
        for lage in range(1, lagen + 1):
            z = max(z_unten, oben - lage * tiefe / lagen)
            punkte += bahn(stellen_, oben, z, frei)
            frei = z
        stellen_zahl += len(stellen_)
        lagen_zahl = max(lagen_zahl, lagen)
        boeden += 1
        namen.append(ebene.name)
    if not punkte:
        raise ValueError(tr("tf.fehler.eng", d=f"{2 * radius:g}"))
    bahn_ = Tauchbahn(punkte, stellen_zahl, lagen_zahl, boeden, namen)
    if loecher:
        from . import raeumen as ra

        d = float(vorbohren["durchmesser"])
        winkel = float(vorbohren.get("spitzenwinkel") or 118.0)
        bohrung = ra.vorbohr_bahn(
            loecher, d, winkel, oben, oben + 5.0, float(vorbohren.get("vorschub") or 0.0)
        )
        laenge = float(vorbohren.get("schneidenlaenge") or 0.0)
        tiefe = max(oben - z for _x, _y, z in loecher)
        bahn_.vorbohren = ra.Vorbohren(
            loecher,
            d,
            bohrung.zeit,
            0.0,
            bohrung.hube,
            tiefe,
            zu_kurz=0 < laenge < tiefe,
            kennung=str(vorbohren.get("kennung") or ""),
        )
    return bahn_


def zeit(punkte, eintauchen, eilgang=None, beschleunigung=None):
    """Minuten für die Bahn (bahn.zeit); `eintauchen`: der Eintauchvorschub (mm/min)."""
    return bh.zeit(punkte, eintauchen, eintauchen, eilgang, beschleunigung)


try:  # die Operation braucht FreeCADs CAM; die Rechnung oben nicht
    import FreeCAD
    import Path
    import Path.Op.Base as PathOp
except ImportError:  # pragma: no cover – nur ohne FreeCAD
    PathOp = None


if PathOp is not None:

    class Tauchfraesen(PathOp.ObjectOp):
        """Proxy der Operation „Tauchfräsen“."""

        def opFeatures(self, obj):
            return (
                PathOp.FeatureTool
                | PathOp.FeatureDepths
                | PathOp.FeatureHeights
                | PathOp.FeatureCoolant
            )

        def initOperation(self, obj):
            self._eigenschaften(obj)
            obj.Aufmass = AUFMASS
            obj.AufmassBoden = 0.0
            obj.Schritt = 0.0
            self._editormodi(obj)

        def opOnDocumentRestored(self, obj):
            self._eigenschaften(obj)
            self._editormodi(obj)

        @staticmethod
        def _eigenschaften(obj):
            for typ, name, text in (
                ("App::PropertyStringList", "Flaechen", tr("tf.eigenschaft.flaechen")),
                ("App::PropertyLength", "Aufmass", tr("bo.eigenschaft.aufmass")),
                ("App::PropertyLength", "AufmassBoden", tr("tf.eigenschaft.aufmass_boden")),
                ("App::PropertyLength", "Schritt", tr("tf.eigenschaft.schritt")),
                ("App::PropertyInteger", "Stellen", tr("tf.eigenschaft.stellen")),
                ("App::PropertyInteger", "Lagen", tr("pf.eigenschaft.lagen")),
            ):
                if name not in obj.PropertiesList:
                    obj.addProperty(typ, name, GRUPPE, text)

        @staticmethod
        def _editormodi(obj):
            for name in ("Stellen", "Lagen"):
                obj.setEditorMode(name, 1)  # nur lesen: das Ergebnis

        def opExecute(self, obj):
            from . import vierachs_operation as vo

            try:
                ergebnis = rechne(obj, self.job, self.model)
            except ValueError as fehler:
                obj.Stellen = obj.Lagen = 0
                FreeCAD.Console.PrintError(f"{obj.Label}: {fehler}\n")
                self.commandlist.append(Path.Command(f"({vo._ascii(str(fehler))})"))
                return
            obj.Stellen, obj.Lagen = ergebnis.stellen, ergebnis.lagen
            punkte = [
                bh.Punkt(True, ergebnis.punkte[0].x, ergebnis.punkte[0].y, float(obj.SafeHeight))
            ]
            punkte += ergebnis.punkte
            punkte.append(bh.Punkt(True, punkte[-1].x, punkte[-1].y, float(obj.SafeHeight)))
            vorschub = (self.horizFeed or 0.0) * 60.0
            self.commandlist.extend(bh.befehle(punkte, vorschub, vo.eintauchvorschub(self)))


def rechne(obj, job, modell):
    """Die Bahn (Tauchbahn) für die Operation `obj` im Job – ValueError mit einem Satz."""
    from . import kontur as ko
    from . import planfraesen as pf
    from . import vierachs_schlichten as vs

    form = vs.form_des_controllers(obj.ToolController)
    if form is None or float(getattr(form, "radius", 0.0) or 0.0) <= 0:
        raise ValueError(tr("nt.fehler.form"))
    return bahn_fuer(
        job,
        modell,
        float(form.radius),
        list(obj.Flaechen),
        aufmass=float(obj.Aufmass),
        aufmass_boden=float(obj.AufmassBoden),
        schritt=float(obj.Schritt) or None,
        schneidenlaenge=ko.schneidenlaenge(obj.ToolController),
        oben=min(float(obj.StartDepth), pf.rohteil_von_oben(job)[4]),
    )


def lege_an(job, tc, flaechen, aufmass=AUFMASS, aufmass_boden=0.0, schritt=0.0, name=None):
    """Legt „Tauchfräsen“ im Job an – ohne eigene Transaktion, die hält der Aufrufer. Gibt die
    Operation zurück."""
    from . import namen
    from . import planfraesen as pf

    dokument = job.Document
    obj = dokument.addObject("Path::FeaturePython", "Tauchfraesen")
    obj.addProperty("App::PropertyBool", "DoNotSetDefaultValues", "Path")
    obj.DoNotSetDefaultValues = True
    proxy = Tauchfraesen(obj, "Tauchfraesen", job)
    obj.removeProperty("DoNotSetDefaultValues")
    obj.Proxy = proxy
    job.Proxy.addOperation(obj)
    obj.Active = True
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.CoolantMode = job.SetupSheet.CoolantMode
    pf._hoehen(obj, proxy, job)
    _werte(obj, flaechen, aufmass, aufmass_boden, schritt)
    _endtiefe(obj, job)
    obj.Label = namen.eindeutig(
        obj.Document, name or tr("tf.name", werkzeug=f"T{tc.ToolNumber}"), obj
    )
    if FreeCAD.GuiUp:
        from . import gui_vierachs_operation

        gui_vierachs_operation.Ansicht(obj.ViewObject)
    return obj


def _werte(obj, flaechen, aufmass, aufmass_boden, schritt):
    obj.Flaechen = list(flaechen)
    obj.Aufmass = aufmass
    obj.AufmassBoden = aufmass_boden
    obj.Schritt = schritt or 0.0


def _endtiefe(obj, job):
    """Die Endtiefe: der tiefste der Böden plus Aufmaß – zum Lesen; die Bahn rechnet aus den
    Flächen."""
    from . import hoehenfeld as hf
    from . import vierachs_schlichten as vs

    try:
        ebenen = hf.ebenen_oben(vs._teil(job.Model.Group), list(obj.Flaechen))
    except ValueError:
        ebenen = []
    if ebenen:
        obj.setExpression("FinalDepth", None)
        obj.FinalDepth = min(e.z for e in ebenen) + float(obj.AufmassBoden)


def aendere(obj, tc, flaechen, aufmass, aufmass_boden, schritt=0.0):
    """Gibt der Operation einen (anderen) Werkzeug-Controller und neue Werte – ohne eigene
    Transaktion. Der Name folgt dem Werkzeug, solange es der vorgeschlagene ist."""
    from . import namen

    if namen.nach_vorlage(obj.Label, tr("tf.name", werkzeug="\0")):
        obj.Label = namen.eindeutig(obj.Document, tr("tf.name", werkzeug=f"T{tc.ToolNumber}"), obj)
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    _werte(obj, flaechen, aufmass, aufmass_boden, schritt)
    job = getattr(obj.Proxy, "job", None)
    if job is not None:
        _endtiefe(obj, job)


def ist_tauchfraesen(op):
    """Ist `op` eine Operation dieses Moduls – „Tauchfräsen“?"""
    return PathOp is not None and isinstance(getattr(op, "Proxy", None), Tauchfraesen)
