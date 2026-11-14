# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die CAM-Operation „Dichtnut hobeln“ – Schritt 4 des Bauplans (Spezifikation Strategien 13.10).

Ein Stoßwerkzeug (werkzeuge.STOSSWERKZEUG) steht in der Spindel und wird längs der Mittellinie
einer umlaufenden Nut gezogen; die Spindel dreht nicht, sie stellt die Schneide je Satz in
Fahrtrichtung (hobeln_bahn). Sie macht die Nut **aus dem Vollen** – Breite und Tiefe ganz mit der
Klinge, ohne Fräser davor (Manuel, 2026-11-14: „das hobeln sollte auch bei nicht vor gefraeseter
Nut funktionieren oder?? Also das ja Sinn der Sache das man es nicht fräst“): von der Oberkante des
Materials (StartDepth: Teil oder Rohteil über der Nut) in Umläufen bis zum Grund, mit Leerumläufen
am Ende – die Riefen laufen längs der Nut. Mit „Vorgefraest“ ist die Nut davor bis auf den Rest
über dem Grund gefräst, und nur der Rest wird gehobelt.

Wie „Ringnut fräsen“ (ringnut) eine eigene Operation (FreeCADs ObjectOp) mit Werkzeug-Controller,
Kühlmittel und FreeCADs Tiefen und Höhen. Den Spindelwinkel trägt jeder Satz als Kommentar
„(SPINDEL …)“ davor; das Programm (postprozessor) macht daraus je Steuerung den Winkel der
stehenden Spindel. Der Vorschub ist der des Controllers (beim Hobeln die Schnittgeschwindigkeit).

Von oben gesehen nimmt die Klinge nicht mehr weg als ein Fräser so breit wie sie – für Materialstand
und Abfahren zählt sie so; ob sie in der Nut bleibt, prüft hobeln_bahn (die Klinge als Rechteck).

Läuft ohne Oberfläche.
"""

import contextlib
import dataclasses
import math
from dataclasses import dataclass

import FreeCAD
import Path
import Path.Op.Base as PathOp

from . import bahn as bn
from . import hobeln_bahn as hb
from . import namen
from . import planfraesen as pf
from . import vierachs_bahn as vb
from . import vierachs_operation as vo
from . import vierachs_schlichten as vs
from .sprache import tr

GRUPPE = "Hobeln"
# mm je Umlauf, wenn das Stoßwerkzeug keinen Wert hat (sonst das ap seines Einsatzes „Hobeln“ –
# Manuel: „Die Zustellung ist ja Werkzeug abhängig“). Manuel, 2026-11-14: „Die Zustellung sind ja
# eh sehr gering je Durchlauf ich glaube 0.08 mm span ist da angesagt beim Nut räumen“ – unter
# Horns Grenze 0,3 je Hub.
ZUSTELLUNG = 0.08
REST = 0.2  # mm, die das Fräsen davor über dem Grund stehen lässt
VORSCHUB = (
    6000.0  # mm/min Hub ohne Einsatz – ein Zehntel von Horns 60 m/min (werkzeugkiste.HOBELN_VC)
)
# mm – so lang wird die Klinge des vorgeschlagenen Stoßwerkzeugs höchstens (wie die Beispielreihe
# „beispiel-stosswerkzeug“ der Werkzeugkiste); kürzer, wenn die engste Kurve es verlangt.
LAENGE_HOECHSTENS = 2.0
LAENGE_MINDESTENS = 0.5  # mm – kürzer schlägt es keine Klinge vor (eine Klinge von 0,2 mm: 14.11.)
# mm – so viel Luft je Seite lässt die vorgeschlagene Schneide wenigstens, über SPIEL hinaus: In
# einer Nut 3,01 blieb mit 3,0 keine, und es gab keinen Vorschlag, obwohl 2,9 × 1,0 ginge.
LUFT_MINDESTENS = 0.02
# Nach dem Hobeln fährt der Fräser der Wände sie unten im Rest nach (gui_bearbeitung
# ._hobeln_wand_unten): bis so hoch über dem gehobelten Grund – er berührt ihn nicht; so breit
# neben der Wand (die Klinge lässt dort höchstens SPIEL + ihren Schwenk, am Deckel ≤ 0,05).
WAND_UNTEN = 0.02
WAND_UNTEN_BREITE = 0.1
VORGEFRAEST = 0.95  # so viel der Mittellinie muss eine Operation davor bis auf den Rest fräsen
# mm – so viel länger als die Nut tief ist (ab der Oberkante des Materials) muss die Klinge nach
# unten reichen (Stechtiefe): Darüber beginnt der Schaft, er darf das Teil nicht berühren.
STECHTIEFE_SICHER = 0.5


class DichtnutHobeln(PathOp.ObjectOp):
    """Proxy der Operation „Dichtnut hobeln“."""

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
        obj.Rest = REST
        obj.Leerumlaeufe = 1
        obj.Satzlaenge = hb.SCHRITT
        obj.Sicherheitsabstand = vb.SICHERHEIT

    def opOnDocumentRestored(self, obj):
        self._eigenschaften(obj)

    @staticmethod
    def _eigenschaften(obj):
        for typ, name, text in (
            ("App::PropertyStringList", "Flaechen", tr("ho.eigenschaft.flaechen")),
            ("App::PropertyLength", "Zustellung", tr("ho.eigenschaft.zustellung")),
            ("App::PropertyBool", "Vorgefraest", tr("ho.eigenschaft.vorgefraest")),
            ("App::PropertyLength", "Rest", tr("ho.eigenschaft.rest")),
            ("App::PropertyLength", "Aufmass", tr("ho.eigenschaft.aufmass")),
            ("App::PropertyLength", "AufmassWand", tr("ho.eigenschaft.aufmass_wand")),
            ("App::PropertyInteger", "Leerumlaeufe", tr("ho.eigenschaft.leerumlaeufe")),
            ("App::PropertyLength", "Satzlaenge", tr("ho.eigenschaft.satzlaenge")),
            ("App::PropertyLength", "Sicherheitsabstand", tr("pf.eigenschaft.sicherheit")),
            ("App::PropertyInteger", "Nuten", tr("ho.eigenschaft.nuten")),
        ):
            if name not in obj.PropertiesList:
                obj.addProperty(typ, name, GRUPPE, text)
        obj.setEditorMode("Nuten", 1)

    def opExecute(self, obj):
        try:
            if not self.horizFeed or self.horizFeed <= 0:
                raise ValueError(tr("vo.fehler.vorschub"))
            ergebnis = rechne(
                obj, self.job, self.model, self.horizFeed * 60.0, self.vertFeed * 60.0
            )
        except ValueError as fehler:
            obj.Nuten = 0
            FreeCAD.Console.PrintError(f"{obj.Label}: {fehler}\n")
            self.commandlist.append(Path.Command(f"({vo._ascii(str(fehler))})"))
            return
        punkte, nuten = ergebnis
        obj.Nuten = nuten
        self.commandlist.extend(
            bn.befehle(punkte, self.horizFeed * 60.0, (self.vertFeed * 60.0) or None)
        )


def werkzeug_des_controllers(tc):
    """Das Stoßwerkzeug des Controllers aus der Werkzeugverwaltung – None, wenn es keins ist."""
    from . import job_schnittwerte as js
    from . import werkzeuge as wz

    try:
        bibliothek = wz.Bibliothek.laden()
    except Exception:  # noqa: BLE001
        return None
    werkzeug = js.werkzeug_von(tc, bibliothek)
    if werkzeug is None or werkzeug.art != wz.STOSSWERKZEUG:
        return None
    return werkzeug


def zustellung_fuer(werkzeug, werkstoff=""):
    """Die Zustellung je Umlauf zum Stoßwerkzeug `werkzeug`: das ap seines Einsatzes „Hobeln“
    (für `werkstoff`, sonst für alle) – ohne Wert ZUSTELLUNG."""
    from . import werkzeuge as wz

    if werkzeug is None:
        return ZUSTELLUNG
    einsatz = next(
        (e for e in werkzeug.einsaetze(werkstoff or wz.ALLE) if e.art == wz.HOBELN and e.ap > 0),
        None,
    )
    return float(einsatz.ap) if einsatz is not None else ZUSTELLUNG


def controller(dokument, job, werkzeug, einsatz=None, werkstoff=""):
    """Legt den Werkzeug-Controller für das Stoßwerkzeug `werkzeug` an – ohne eigene Transaktion
    (job_schnittwerte.controller_ohne_transaktion). Die Spindel steht (SpindleDir „None“,
    0 U/min: kein M3 im Programm); der Vorschub ist der Hub. Ohne `einsatz` der erste
    Einsatz „Hobeln“ des Werkzeugs, sonst einer mit VORSCHUB und ZUSTELLUNG."""
    from . import job_schnittwerte as js
    from . import werkzeuge as wz

    if einsatz is None:
        einsatz = next(
            (e for e in werkzeug.einsaetze(werkstoff or wz.ALLE) if e.art == wz.HOBELN), None
        ) or wz.Einsatz(art=wz.HOBELN, ap=ZUSTELLUNG, vc=VORSCHUB / 1000.0)
    return js.controller_ohne_transaktion(dokument, job, werkzeug, einsatz, werkstoff)


def werte_fuer(werkzeug, sicher, vorschub, eintauchen=0.0, zustellung=ZUSTELLUNG, rest=REST,
               aufmass=0.0, leerumlaeufe=1, satzlaenge=hb.SCHRITT, sicherheit=vb.SICHERHEIT):  # fmt: skip
    """Die Hobelwerte (hobeln_bahn.Hobelwerte) zum Stoßwerkzeug `werkzeug`."""
    return hb.Hobelwerte(
        breite=float(werkzeug.schneidenbreite),
        laenge=float(werkzeug.klingenlaenge),
        versatz=float(werkzeug.spindelwinkel),
        zustellung=float(zustellung),
        rest=float(rest),
        sicher=float(sicher),
        vorschub=float(vorschub),
        eintauchen=float(eintauchen or 0.0),
        aufmass=float(aufmass),
        leerumlaeufe=int(leerumlaeufe),
        sicherheit=float(sicherheit),
        schritt=max(float(satzlaenge), 0.05),
        freiwinkel=float(getattr(werkzeug, "freiwinkel", 0.0) or 0.0),
    )


def rechne(obj, job, modell, vorschub=0.0, eintauchen=0.0):
    """([bahn.Punkt] aller Nuten hintereinander, Anzahl Nuten) für die Operation `obj`.
    ValueError mit einem Satz, wenn es nicht geht."""
    werkzeug = werkzeug_des_controllers(obj.ToolController)
    if werkzeug is None:
        raise ValueError(tr("ho.fehler.werkzeug"))
    form_teil = vs._teil(modell)
    nuten = hb.hobelnuten(form_teil, list(obj.Flaechen) or None)
    if not nuten:
        raise ValueError(tr("ho.fehler.keine"))
    w = werte_fuer(
        werkzeug, float(obj.SafeHeight), vorschub or 1000.0, eintauchen,
        float(obj.Zustellung), float(obj.Rest), float(obj.Aufmass), int(obj.Leerumlaeufe),
        float(obj.Satzlaenge), float(obj.Sicherheitsabstand),
    )  # fmt: skip
    vorgefraest = bool(getattr(obj, "Vorgefraest", False))
    wand = float(getattr(obj, "AufmassWand", 0.0) or 0.0) if vorgefraest else 0.0
    oben = oberkante(obj, job)
    punkte, gehobelt, gruende = [], 0, []
    for nut in nuten:
        # Eine Nut, die nicht geht, nicht mit: Brach die ganze Operation ab, blieb an der, die
        # geht, der Rest des Räumens stehen (Zweifler 14.11.).
        tiefe = max(oben, nut.z_oben) - nut.z_boden
        grund = klinge_grund(nut, werkzeug, wand, tiefe)
        if vorgefraest:
            grund = grund or _nicht_vorgefraest(job, obj, nut, w.rest)
            w_nut = w
        else:
            w_nut = dataclasses.replace(w, rest=tiefe)  # aus dem Vollen: ab der Oberkante
        if not grund:
            try:
                bahn = hb.planen(nut, w_nut)
            except ValueError as fehler:
                grund = str(fehler)
        if grund:
            gruende.append(f"{nut.name}: {grund}")
            FreeCAD.Console.PrintWarning(f"{obj.Label}: {nut.name}: {grund}\n")
            continue
        punkte.extend(bahn.punkte)
        gehobelt += 1
    if not gehobelt:
        raise ValueError(gruende[0])
    return punkte, gehobelt


def oberkante(obj, job):
    """z der Oberkante des Materials über den Nuten: die Starttiefe der Operation, nicht über dem
    Rohteil."""
    oben = float(obj.StartDepth)
    with contextlib.suppress(Exception):  # ohne Rohteil: die Starttiefe
        oben = min(oben, float(pf.rohteil_von_oben(job)[4]))
    return oben


def _stuecke(befehl, von, nach):
    """[(x, y, z)] längs eines Satzes G1/G2/G3 alle 0,5 mm – Bögen um ihre Mitte (I, J)."""
    bogen = befehl.Name in ("G2", "G02", "G3", "G03") and (
        "I" in befehl.Parameters or "J" in befehl.Parameters
    )
    if not bogen:
        teile = max(1, int(math.hypot(nach[0] - von[0], nach[1] - von[1]) / 0.5))
        return [
            tuple(von[k] + (nach[k] - von[k]) * t / teile for k in range(3))
            for t in range(teile + 1)
        ]
    mx = von[0] + float(befehl.Parameters.get("I", 0.0))
    my = von[1] + float(befehl.Parameters.get("J", 0.0))
    r = math.hypot(von[0] - mx, von[1] - my)
    a0 = math.atan2(von[1] - my, von[0] - mx)
    a1 = math.atan2(nach[1] - my, nach[0] - mx)
    uhr = befehl.Name in ("G2", "G02")
    winkel = (a0 - a1) % (2 * math.pi) if uhr else (a1 - a0) % (2 * math.pi)
    if winkel < 1e-9:
        winkel = 2 * math.pi
    teile = max(1, int(r * winkel / 0.5))
    ergebnis = []
    for t in range(teile + 1):
        a = a0 - winkel * t / teile if uhr else a0 + winkel * t / teile
        z = von[2] + (nach[2] - von[2]) * t / teile
        ergebnis.append((mx + r * math.cos(a), my + r * math.sin(a), z))
    return ergebnis


def _schnitt_stellen(op, grenze):
    """([x], [y]) der Schnittsätze von `op` (je 0,5 mm), die bis `grenze` hinab reichen."""
    xs, ys = [], []
    ort = [None, None, None]
    for c in op.Path.Commands:
        neu = list(ort)
        for k, a in enumerate("XYZ"):
            if a in c.Parameters:
                neu[k] = float(c.Parameters[a])
        schnitt = c.Name in ("G1", "G01", "G2", "G02", "G3", "G03") and None not in ort + neu
        if schnitt and min(ort[2], neu[2]) <= grenze:
            for x, y, z in _stuecke(c, ort, neu):
                if z <= grenze:
                    xs.append(x)
                    ys.append(y)
        ort = neu
    return xs, ys


def _nicht_vorgefraest(job, obj, nut, rest):
    """ "" wenn eine Operation vor `obj` im Job die Nut bis auf den Rest fräst – sonst der Satz.
    Gezählt wird die Mittellinie (je mm eine Stelle): Ein Schnittsatz einer aktiven Operation davor
    kommt ihr näher als die halbe Breite und reicht bis Grund + Rest. Sonst tauchte die Klinge bei
    stehender Spindel in volles Material (mit dem Ø 12 der Testkiste im Räumen bis 2,5 mm)."""
    import numpy as np

    from . import kontur_bahn as kb

    if job is None or rest <= 0:
        return ""
    proben = kb._abtasten(nut.segmente, 1.0, True)
    mx, my = proben.x, proben.y
    gedeckt = np.zeros(len(mx), dtype=bool)
    grenze = nut.z_boden + rest + 0.01
    for op in job.Operations.Group:
        if op.Name == obj.Name:
            break
        if not getattr(op, "Active", True) or getattr(op, "Path", None) is None:
            continue
        xs, ys = _schnitt_stellen(op, grenze)
        if not xs:
            continue
        px, py = np.array(xs), np.array(ys)
        nah = nut.breite / 2.0
        for k in range(0, len(px), 2000):
            stueck = slice(k, k + 2000)
            d2 = (mx[:, None] - px[None, stueck]) ** 2 + (my[:, None] - py[None, stueck]) ** 2
            gedeckt |= (d2 <= nah * nah).any(axis=1)
    if gedeckt.mean() >= VORGEFRAEST:
        return ""
    return tr("ho.grund.nicht_vorgefraest", rest=hb._mm(rest))


def klinge_grund(nut, werkzeug, wand_aufmass=0.0, tiefe=None):
    """ "" wenn das Stoßwerkzeug `werkzeug` die Nut `nut` hobeln kann – sonst der Satz, warum
    nicht: die Klinge (hobeln_bahn.klinge_pruefen); sie reicht nicht so tief, wie die Nut ab der
    Oberkante des Materials ist (`tiefe`, ohne: die Nut selbst) – darüber stieße der Schaft ans
    Teil; oder die Wände stehen über dem Rest noch `wand_aufmass` vor (das Fräsen davor ließ
    Aufmaß an der Wand)."""
    grund = hb.klinge_pruefen(
        nut,
        float(werkzeug.schneidenbreite),
        float(werkzeug.klingenlaenge),
        freiwinkel=float(getattr(werkzeug, "freiwinkel", 0.0) or 0.0),
    )
    if grund:
        return grund
    noetig = (nut.tiefe if tiefe is None else float(tiefe)) + STECHTIEFE_SICHER
    stech = float(getattr(werkzeug, "stechtiefe", 0.0) or 0.0)
    if stech < noetig - 1e-9:
        return tr("ho.grund.stechtiefe", stech=hb._mm(stech), noetig=hb._mm(noetig))
    a = max(float(wand_aufmass or 0.0), 0.0)
    if a > 1e-6:
        # Gehobelt wird erst zwischen fertigen Wänden: Die Klinge passte sonst nicht dazwischen,
        # oder ihre äußeren Spuren führen seitlich ins Aufmaß (Nut 4,6, Aufmaß 0,3, Klinge 3,5:
        # 0,295 mm, Zweifler 14.11.) – und unter dem Aufmaß bliebe der Rest am Grund stehen.
        return tr("ho.grund.waende", aufmass=hb._mm(a), b=hb._mm(float(werkzeug.schneidenbreite)))
    return ""


@dataclass
class Hobelvorschau:
    """Die Vorschau im Assistenten: alle Nuten hintereinander (vorschau())."""

    punkte: list  # [bahn.Punkt]
    je_nut: list  # je Nut {name, nut, umlaeufe, spuren, zeit}
    nicht_passend: list  # [(Grund der Nut, Satz)] – gewählt, aber nicht zu hobeln
    namen: list  # die Gründe, die gehobelt werden – sie sind danach fertig
    zeit: float  # Minuten


def vorschau(job, werkzeug, flaechen, zustellung=ZUSTELLUNG, rest=REST, leerumlaeufe=1,
             vorschub=0.0, eintauchen=0.0, wand_aufmass=0.0, vorgefraest=None, oben=None,
             aus_dem_vollen=True):  # fmt: skip
    """Die Hobelbahn für den Assistenten (gui_bearbeitung) – je gewählte Nut planen() (kein
    Nebenrechner). Nuten, die nicht gehen, mit ihrem Satz in `nicht_passend`; geht keine,
    ValueError mit dem ersten Satz. `oben`: die Oberkante des Materials über den Nuten (None: das
    Rohteil). `aus_dem_vollen`: die ganze Nut ab `oben`; sonst nur `rest` über dem Grund, und
    `vorgefraest` sind die Gründe, die ein Block davor bis auf den Rest fräst (None: nicht
    prüfen) – die anderen gehen nicht; `wand_aufmass` zählt nur dann."""
    form_teil = vs._teil(job.Model.Group)
    gewaehlt = list(flaechen)
    alle = [n for n in hb.alle_hobelnuten(form_teil) if set(n.flaechen) & set(gewaehlt)]
    if not alle:
        raise ValueError(tr("ho.fehler.keine"))
    *_rohteil, z_oben = pf.rohteil_von_oben(job)
    if oben is None:
        oben = z_oben
    if aus_dem_vollen:
        wand_aufmass, vorgefraest = 0.0, None
    w = werte_fuer(
        werkzeug, z_oben + vb.SICHERHEIT + 3.0, vorschub or 1000.0, eintauchen, zustellung,
        rest, 0.0, leerumlaeufe,
    )  # fmt: skip
    punkte, je_nut, nicht, namen_ = [], [], [], []
    waende = False  # eine Nut geht nur nicht, weil ihre Wände noch Aufmaß haben
    for nut in alle:
        tiefe = max(oben, nut.z_oben) - nut.z_boden
        ohne_waende = nut.grund or klinge_grund(nut, werkzeug, 0.0, tiefe)
        grund = ohne_waende or klinge_grund(nut, werkzeug, wand_aufmass, tiefe)
        waende = waende or (bool(grund) and not ohne_waende)
        if not grund and vorgefraest is not None and nut.name not in vorgefraest:
            grund = tr("ho.grund.nicht_vorgefraest", rest=hb._mm(rest))
        if not grund:
            try:
                bahn = hb.planen(nut, dataclasses.replace(w, rest=tiefe) if aus_dem_vollen else w)
            except ValueError as fehler:
                grund = str(fehler)
        if grund:
            nicht.append((nut.name, grund))
            continue
        punkte.extend(bahn.punkte)
        namen_.append(nut.name)
        je_nut.append(
            {"name": nut.name, "nut": nut, "umlaeufe": bahn.umlaeufe, "spuren": bahn.spuren,
             "zeit": bahn.zeit}
        )  # fmt: skip
    if not je_nut:
        fehler = ValueError(nicht[0][1])
        fehler.daten = {"waende": waende}  # der Assistent bietet „Schlichten danach“ an
        raise fehler
    zeit = bn.zeit(punkte, w.vorschub, w.eintauchen or None)
    return Hobelvorschau(punkte, je_nut, nicht, namen_, zeit)


def werkzeug_vorschlag(nuten, tiefe=None):
    """Ein Stoßwerkzeug (werkzeuge.Werkzeug, ohne Nummer) für die Nuten `nuten`: die Schneide so
    breit, dass sie in die schmalste passt (Nutbreite − 2 · (SPIEL + LUFT_MINDESTENS), auf 0,1
    abgerundet), die Klinge so lang, dass sie den kleinsten Radius jeder Nut fährt
    (hobeln_bahn.kleinster_radius_fuer), höchstens LAENGE_HOECHSTENS. Wird sie kürzer als
    LAENGE_MINDESTENS, die Schneide 0,1 schmaler (bis zu fünfmal); None, wenn nichts passt. Die
    Stechtiefe: `tiefe` (ab der Oberkante des Materials; ohne: die tiefste Nut) + 1, aufgerundet."""
    from . import werkzeuge as wz

    if not nuten:
        return None
    schmal = min(nuten, key=lambda n: n.breite)
    b0 = math.floor((schmal.breite - 2 * (hb.SPIEL + LUFT_MINDESTENS)) * 10.0 + 1e-6) / 10.0
    for k in range(6):
        b = round(b0 - 0.1 * k, 1)
        if b <= 0:
            return None
        laenge = _laenge_fuer(nuten, b)
        if laenge >= LAENGE_MINDESTENS - 1e-9:
            break
    else:
        return None
    if tiefe is None:
        tiefe = max(n.tiefe for n in nuten)
    name = tr("ho.werkzeug_name", b=hb._mm(b))
    return wz.Werkzeug(
        art=wz.STOSSWERKZEUG, name=name, schneidenbreite=b, klingenlaenge=laenge,
        stechtiefe=float(math.ceil(tiefe + 1.0)), spindelwinkel=0.0, gesamtlaenge=60.0,
        schaft=10.0, schneidstoff=wz.VHM,
    )  # fmt: skip


def _laenge_fuer(nuten, b):
    """Die längste Klinge (auf 0,1 abgerundet, höchstens LAENGE_HOECHSTENS) der Breite `b`, mit
    der jede Nut geht (hobeln_bahn.kleinster_radius_fuer ≤ ihr kleinster Radius); 0: keine."""

    def geht(laenge):
        return all(hb.kleinster_radius_fuer(n.breite, b, laenge) <= n.r_min + 1e-9 for n in nuten)

    for zehntel in range(int(round(LAENGE_HOECHSTENS * 10)), 0, -1):
        if geht(zehntel / 10.0):
            return zehntel / 10.0
    return 0.0


def lege_an(job, tc, flaechen=(), name=None, zustellung=None, rest=REST, aufmass=0.0,
            leerumlaeufe=1, aufmass_wand=0.0, vorgefraest=False, oben=None):  # fmt: skip
    """Legt „Dichtnut hobeln“ im Job an – ohne eigene Transaktion. Gibt die Operation zurück.
    Ohne `zustellung` die des Stoßwerkzeugs (zustellung_fuer, für den Werkstoff des Jobs).
    `vorgefraest`: nur den Rest hobeln (sonst aus dem Vollen); `oben`: die Oberkante des Materials
    (StartDepth; ohne: wie FreeCAD, das Rohteil)."""
    if zustellung is None:
        zustellung = zustellung_fuer(werkzeug_des_controllers(tc), _werkstoff(job, tc))
    dokument = job.Document
    obj = dokument.addObject("Path::FeaturePython", "DichtnutHobeln")
    obj.addProperty("App::PropertyBool", "DoNotSetDefaultValues", "Path")
    obj.DoNotSetDefaultValues = True
    proxy = DichtnutHobeln(obj, "DichtnutHobeln", job)
    obj.removeProperty("DoNotSetDefaultValues")
    obj.Proxy = proxy
    job.Proxy.addOperation(obj)
    obj.Active = True
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.CoolantMode = job.SetupSheet.CoolantMode
    pf._hoehen(obj, proxy, job)
    obj.Flaechen = list(flaechen)
    obj.Vorgefraest = bool(vorgefraest)
    if oben is not None:
        obj.setExpression("StartDepth", None)
        obj.StartDepth = float(oben)
    obj.Zustellung = float(zustellung)
    obj.Rest = float(rest)
    obj.Aufmass = float(aufmass)
    obj.AufmassWand = float(aufmass_wand)
    obj.Leerumlaeufe = int(leerumlaeufe)
    try:
        liste = hb.hobelnuten(vs._teil(job.Model.Group), list(flaechen) or None)
    except ValueError:
        liste = []
    if liste:
        obj.setExpression("FinalDepth", None)
        obj.FinalDepth = min(n.z_boden for n in liste)
    obj.Label = namen.eindeutig(dokument, name or tr("ho.name", werkzeug=f"T{tc.ToolNumber}"), obj)
    if FreeCAD.GuiUp:
        from . import gui_vierachs_operation

        gui_vierachs_operation.Ansicht(obj.ViewObject)
    return obj


def _werkstoff(job, tc):
    """Die Kennung des Werkstoffs, mit dem der Job rechnet ("" : alle)."""
    from . import job_schnittwerte as js
    from . import werkzeuge as wz

    try:
        werkstoff, _gemerkt = js.werkstoff_fuer(job, wz.Bibliothek.laden().alle_werkstoffe(), tc)
    except Exception:  # noqa: BLE001 – ohne Werkzeugverwaltung: für alle Werkstoffe
        return ""
    return getattr(werkstoff, "kennung", "") if werkstoff is not None else ""


def aendere(obj, tc, flaechen=None, zustellung=ZUSTELLUNG, rest=REST, leerumlaeufe=1,
            vorgefraest=None, oben=None):  # fmt: skip
    """Gibt der Operation einen (anderen) Werkzeug-Controller und neue Werte – ohne eigene
    Transaktion; `flaechen` ohne bleibt. Der Name folgt dem Werkzeug, solange es der
    vorgeschlagene ist."""
    if namen.nach_vorlage(obj.Label, tr("ho.name", werkzeug="\0")):
        obj.Label = namen.eindeutig(obj.Document, tr("ho.name", werkzeug=f"T{tc.ToolNumber}"), obj)
    obj.ToolController = tc
    obj.OpToolDiameter = tc.Tool.Diameter
    obj.Zustellung = float(zustellung)
    obj.Rest = float(rest)
    obj.Leerumlaeufe = int(leerumlaeufe)
    if vorgefraest is not None:
        obj.Vorgefraest = bool(vorgefraest)
    if oben is not None:
        obj.setExpression("StartDepth", None)
        obj.StartDepth = float(oben)
    if flaechen is not None and list(flaechen) != list(obj.Flaechen):
        obj.Flaechen = list(flaechen)


def ist_hobeln(op):
    """Ist `op` eine Operation „Dichtnut hobeln“?"""
    return isinstance(getattr(op, "Proxy", None), DichtnutHobeln)
