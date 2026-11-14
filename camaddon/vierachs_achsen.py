# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wohin die Stange im Job zeigt – von der Maschine oder zugewiesen (Spezifikation W-003,
Abschnitte 4 und 13, V2a).

Ohne Maschine weist man der Stange eine Rundachse zu: A liegt in X, B in Y, C
in Z (vierachs_rohteil.ACHSEN). Mit einer W-001-Maschine gibt sie die Achse
vor: Eine Rundachse im Tisch – ein Gelenk mit der Betriebsart „Positionieren“
auf dem Weg von der Werkstückaufnahme zum Bett – dreht die Stange. Ihre
Richtung in den Achsen der Werkstückaufnahme ist die Stangenachse im Job:
„Auf der Maschine prüfen“ rechnet in genau diesen Achsen. An der Drehmaschine
ist das Z – die Stange liegt längs der Spindel, nicht quer im Futter (Manuels
Test, 2026-09-27). Vorne zeigt vom Futter weg, also wie Z der
Werkstückaufnahme.

Der Drehsinn sagt, wohin ein positiver Wert der Rundachse das Teil dreht:
+1 rechtshändig um die Stangenachse nach vorne – so zeigt FreeCAD Bahnen mit
A, B und C (PathSegmentWalker dreht den Punkt um −C) –, −1 andersherum.
Ohne Maschine gilt +1. Das Werkzeug kommt radial aus der Richtung, die
radial() nennt: bei A und B von oben (+Z), bei C aus +X (Abschnitt 4).

Läuft ohne Oberfläche.
"""

from dataclasses import dataclass

import FreeCAD

from . import maschine as m
from . import verfahren as vf
from . import vierachs_rohteil as vr
from .kette import LINEAR

GERADE = 1e-6  # so wenig darf eine Richtung von einer Achse des Jobs abweichen


@dataclass(frozen=True)
class Stangenachse:
    """Wie die Stange im Job liegt: um welche Rundachse sie dreht und wohin sie zeigt."""

    buchstabe: str  # so heißt die Rundachse im Programm: A, B oder C
    laengs: FreeCAD.Vector  # Stangenachse nach vorne, in den Achsen des Jobs
    maschine: str = ""  # die Maschine, von der sie kommt; leer: zugewiesen
    drehsinn: int = 1  # +1: ein positiver Wert dreht das Teil rechtshändig um `laengs`
    quer: bool = True  # hat die Maschine eine Linearachse quer zur Stange (bei C das Y)?
    # In geschwenkter Lage (geschwenkt()): die Rundachsen, die fest stehen, solange die Stange
    # dreht – ((Buchstabe, Stellung wie das Gelenk), …), etwa (("A", 90.0),) –, und woher das
    # Werkzeug dann kommt (in den Achsen des Jobs). Leer bzw. None: Grundstellung, radial().
    schwenk: tuple = ()
    von: object = None
    anzeige: str = ""  # die feste Stellung, wie die Steuerung sie zeigt: „A −90°“ (Liste, Bericht)


def zugewiesen(buchstabe):
    """Die Stangenachse ohne Maschine: A in X, B in Y, C in Z."""
    laengs, _radial = vr.ACHSEN[buchstabe]
    return Stangenachse(buchstabe, FreeCAD.Vector(laengs))


def von_maschine(assembly, maschine, kette=None):
    """[Stangenachse] – eine je Rundachse im Tisch der Maschine, die positionieren kann.

    Leer, wenn die Maschine keine solche Achse hat oder keine Werkstückaufnahme.
    """
    from . import reichweite as rw

    pruefung = rw.Pruefung(assembly, maschine, kette=kette)
    aufnahme = pruefung.werkstueckaufnahme
    if aufnahme is None or aufnahme.Lcs is None:
        return []
    # Achsrichtungen stehen in Weltkoordinaten – wie die Lage des LCS.
    in_job = m.globale_platzierung(aufnahme.Lcs).Rotation.inverted()
    rollen, _meldungen = m.rollen(pruefung.kette, maschine)
    linear = {vf.namen(maschine, a)[:1].upper() for a in pruefung.kette.achsen if a.art == LINEAR}
    ergebnis = []
    for achse in pruefung.kette.achsen:
        if achse.art == LINEAR or rollen.get(achse.gelenk) != m.TISCH:
            continue
        buchstabe = rw._programmbuchstabe(maschine, achse)
        if buchstabe is None:
            continue  # eine Spindel, die nicht positionieren kann
        laengs = _nach_vorne(gerade(in_job.multVec(achse.richtung)))
        # Wohin dreht ein positiver Wert das Teil – um `laengs` oder andersherum?
        plus = in_job.multVec(vf.plusrichtung(achse))
        drehsinn = 1 if plus.dot(laengs) > 0 else -1
        achse_der_stange = Stangenachse(buchstabe, laengs, maschine.Label, drehsinn)
        quer = achsbuchstabe(laengs.cross(radial(achse_der_stange)))
        ergebnis.append(
            Stangenachse(buchstabe, laengs, maschine.Label, drehsinn, not quer or quer in linear)
        )
    geschwenkt_ = geschwenkt(pruefung, maschine, ergebnis, linear, rollen)
    if not geschwenkt_:
        return ergebnis
    # Vorn die geschwenkte Lage; die Achse, die dafür fest steht, als Stangenachse zuletzt – das
    # Rohr auf dem Tisch liegend mit A drehen ist kein Weg (Manuel, 2026-11-15: „wenn man so etwas
    # auf einem tisch bearbeitetet spand man das meistens am mantel in ein drei backenfutter
    # senkrcht zum tisch“).
    fest = {b for a in geschwenkt_ for b, _w in a.schwenk}
    return (
        geschwenkt_
        + [a for a in ergebnis if a.buchstabe not in fest]
        + [a for a in ergebnis if a.buchstabe in fest]
    )


SCHWENK = 90.0  # Grad: so weit schwenkt die äußere Rundachse, damit der Rundtisch quer liegt
UNBEGRENZT = 1e6  # mm – so weit „reicht“ eine Linearachse ohne Grenze


def geschwenkt(pruefung, maschine, achsen, linear, rollen):
    """[Stangenachse] in geschwenkter Lage – „C, A auf 90°“ an einer Tisch/Tisch (Manuel,
    2026-11-15): Das Rohr steht im Dreibackenfutter mittig auf dem Rundtisch; für den Mantel
    schwenkt die Rundachse, die den Rundtisch trägt (A bzw. B), fest auf ±SCHWENK – dann liegt der
    Rundtisch quer zum Werkzeug, er dreht das Rohr, und das Werkzeug kommt von oben.

    Nur, wo es ohne Schwenken nicht geht: Die innere Rundachse im Tisch (die die Werkstückaufnahme
    trägt) liegt in Grundstellung längs des Werkzeugs, geschwenkt quer dazu. Von +SCHWENK und
    −SCHWENK die in den Grenzen der äußeren Achse, und von beiden die, in deren Richtung der Kopf
    von der äußeren Achse aus weiter kommt (dorthin ragt das Rohr; an der Beispiel-Tisch/Tisch
    A +90: das Rohr nach vorn, 250 statt 200 mm). `achsen`: die Stangenachsen in Grundstellung
    (von_maschine), `linear`: die Buchstaben der Linearachsen, `rollen`: maschine.rollen."""
    aufnahme = pruefung.werkstueckaufnahme
    werkzeug = next(iter(pruefung.werkzeugaufnahmen), None)
    if aufnahme is None or werkzeug is None or werkzeug.Lcs is None:
        return []
    drehend = [
        a
        for a in pruefung.verfahren.pfad(pruefung._glied(aufnahme))
        if a.art != LINEAR and rollen.get(a.gelenk) == m.TISCH and pruefung.programmbuchstabe(a)
    ]
    if len(drehend) < 2:
        return []
    innen = drehend[-1]
    stange = next((a for a in achsen if a.buchstabe == pruefung.programmbuchstabe(innen)), None)
    lage_werkzeug = m.globale_platzierung(werkzeug.Lcs)
    z_werkzeug = lage_werkzeug.Rotation.multVec(FreeCAD.Vector(0, 0, 1))  # von der Spitze weg
    if stange is None or abs(abs(innen.richtung.dot(z_werkzeug)) - 1.0) > GERADE:
        return []  # schon in Grundstellung quer zum Werkzeug: Schwenken braucht es nicht
    in_job = m.globale_platzierung(aufnahme.Lcs).Rotation.inverted()
    ergebnis = []
    for aussen in drehend[:-1]:
        kandidaten = []
        for winkel in (SCHWENK, -SCHWENK):
            if pruefung.verfahren.begrenzt(aussen, winkel) != winkel:  # über die Grenze
                continue
            # Ein positiver Wert dreht um die Plus-Richtung des Gelenks – ab seiner Stellung jetzt.
            weiter = winkel - pruefung.verfahren.stellung(aussen)
            drehung = FreeCAD.Rotation(vf.plusrichtung(aussen), weiter)
            c_welt = drehung.multVec(innen.richtung)
            if abs(c_welt.dot(z_werkzeug)) > GERADE:
                continue
            # Wohin die Stange ragt: vom Futter weg, wie `laengs` (in der Aufnahme +Z).
            ragt = drehung.multVec(in_job.inverted().multVec(stange.laengs))
            raum = _reichweite(pruefung, maschine, rollen, ragt) + (
                lage_werkzeug.Base - aussen.ursprung
            ).dot(ragt)
            von = gerade(in_job.multVec(drehung.inverted().multVec(z_werkzeug)))
            kandidaten.append((raum, winkel, von, ragt))
        if not kandidaten:
            continue
        _raum, winkel, von, ragt = max(kandidaten, key=lambda k: k[0])
        quer = achsbuchstabe(gerade(ragt.cross(z_werkzeug)))
        buchstabe = pruefung.programmbuchstabe(aussen)
        im_programm = vf.programm_vorzeichen(aussen, pruefung.kette) * winkel  # DIN 66217
        anzeige = f"{buchstabe} {'−' if im_programm < 0 else ''}{abs(im_programm):g}°"
        ergebnis.append(
            Stangenachse(
                stange.buchstabe,
                FreeCAD.Vector(stange.laengs),
                maschine.Label,
                stange.drehsinn,
                not quer or quer in linear,
                ((buchstabe, winkel),),
                von,
                anzeige,
            )
        )
    return ergebnis


def _reichweite(pruefung, maschine, rollen, richtung):
    """So weit (mm) fahren die Linearachsen das Werkzeug gegenüber dem Werkstück in `richtung`
    (Welt) aus ihrer Stellung – eine Achse im Tisch fährt das Werkstück, also andersherum."""
    summe = 0.0
    verfahren = pruefung.verfahren
    for achse in pruefung.kette.achsen:
        if achse.art != LINEAR:
            continue
        plus = vf.plusrichtung(achse) * (-1.0 if rollen.get(achse.gelenk) == m.TISCH else 1.0)
        anteil = plus.dot(richtung)
        if abs(anteil) < GERADE:
            continue
        unten, oben = verfahren.grenzen(achse)
        jetzt = verfahren.stellung(achse)
        if anteil > 0:
            weg = UNBEGRENZT if oben is None else oben - jetzt
        else:
            weg = UNBEGRENZT if unten is None else jetzt - unten
        summe += max(weg, 0.0) * abs(anteil)
    return summe


def schwenk_text(achse_oder_schwenk):
    """Die feste Schwenkstellung als Text, wie sie an der Operation steht: „A90“, „A-90 B0“ –
    leer in Grundstellung. Nimmt eine Stangenachse oder ihr `schwenk`."""
    return vr.schwenk_als_text(getattr(achse_oder_schwenk, "schwenk", achse_oder_schwenk))


def schwenk_aus_text(text):
    """Umkehrung von schwenk_text: „A90“ → (("A", 90.0),); leer oder unlesbar: ()."""
    ergebnis = []
    for wort in str(text or "").split():
        try:
            ergebnis.append((wort[0].upper(), float(wort[1:])))
        except (ValueError, IndexError):
            return ()
    return tuple(ergebnis)


@dataclass(frozen=True)
class Maschinenwahl:
    """Eine offene Maschine zur Wahl im Assistenten – und was sie für die Stange kann."""

    name: str
    assembly: object
    maschine: object
    achsen: tuple  # [Stangenachse]: die Rundachsen, die die Stange drehen (von_maschine)
    linear: tuple  # die Linearachsen im Programm: „X1“, „Y1“, „Z1“
    plaetze: int  # Werkzeugplätze (Werkzeugaufnahmen)


def maschinen(zuerst=None):
    """[Maschinenwahl] aller Maschinen in offenen Dokumenten – die im Dokument `zuerst`
    vorn. Auch eine ohne passende Rundachse ist dabei (achsen leer): Der Assistent zeigt
    sie, damit man sieht, warum sie nicht geht."""
    gefunden = []
    for dokument in FreeCAD.listDocuments().values():
        for objekt in dokument.Objects:
            if objekt.TypeId == "Assembly::AssemblyObject":
                maschine = m.finde_maschine(objekt)
                if maschine is not None:
                    gefunden.append((objekt, maschine))
    gefunden.sort(key=lambda e: e[0].Document is not zuerst)
    ergebnis = []
    for assembly, maschine in gefunden:
        try:
            achsen = tuple(von_maschine(assembly, maschine))
        except Exception as fehler:  # eine halb eingerichtete Maschine soll nicht stören
            FreeCAD.Console.PrintLog(f"CAM-Addon: Achsen von {maschine.Label}: {fehler}\n")
            achsen = ()
        linear = sorted(
            m.name_von(ba) for ba in m.betriebsarten(maschine) if ba.Art == m.ART_LINEAR
        )
        plaetze = sum(1 for a in m.aufnahmen(maschine) if a.Art == m.AUFNAHME_WERKZEUG)
        ergebnis.append(
            Maschinenwahl(maschine.Label, assembly, maschine, achsen, tuple(linear), plaetze)
        )
    namen = [e.name for e in ergebnis]
    return [
        (
            e
            if namen.count(e.name) == 1
            else Maschinenwahl(
                f"{e.name} ({e.assembly.Document.Label})",
                e.assembly,
                e.maschine,
                e.achsen,
                e.linear,
                e.plaetze,
            )
        )
        for e in ergebnis
    ]


def radial(achse):
    """Woher das Werkzeug kommt, wenn die Rundachse auf 0 steht – in den Achsen des Jobs,
    quer zur Stange: bei A und B von oben (+Z), bei C aus +X (vierachs_rohteil.ACHSEN).
    Liegt die Stange genau so, nimmt es die nächste Achse des Jobs. In geschwenkter Lage
    (Stangenachse.von): von dort."""
    if getattr(achse, "von", None) is not None:
        return gerade(achse.von)
    laengs = FreeCAD.Vector(achse.laengs)
    for kandidat in (
        vr.ACHSEN[achse.buchstabe][1],
        FreeCAD.Vector(0, 0, 1),
        FreeCAD.Vector(1, 0, 0),
        FreeCAD.Vector(0, 1, 0),
    ):
        quer = FreeCAD.Vector(kandidat) - laengs * FreeCAD.Vector(kandidat).dot(laengs)
        if quer.Length > 0.5:
            return gerade(quer)
    return FreeCAD.Vector(1, 0, 0)  # nicht erreichbar: eine der drei steht immer quer


def gerade(richtung):
    """Die Richtung als Einheitsvektor; liegt sie auf einer Achse des Jobs, genau darauf."""
    richtung = FreeCAD.Vector(richtung)
    richtung.normalize()
    werte = [richtung.x, richtung.y, richtung.z]
    for i, wert in enumerate(werte):
        if abs(abs(wert) - 1.0) < GERADE:
            genau = [0.0, 0.0, 0.0]
            genau[i] = 1.0 if wert > 0 else -1.0
            return FreeCAD.Vector(*genau)
    return richtung


def _nach_vorne(richtung):
    """Vorne ist vom Futter weg: wie Z der Werkstückaufnahme. Liegt die Achse quer dazu
    (ein Drehtisch unter einer Fräse), zeigt sie wie die Achse des Jobs, der sie am
    nächsten liegt, in Plus-Richtung – wie A in X."""
    if abs(richtung.z) > 0.5:
        return richtung if richtung.z > 0 else richtung * -1
    groesste = max((richtung.x, richtung.y, richtung.z), key=abs)
    return richtung if groesste > 0 else richtung * -1


def achsbuchstabe(laengs):
    """„X“, „Y“ oder „Z“, wenn die Stange längs einer Achse des Jobs liegt, sonst ""."""
    for buchstabe, wert in zip("XYZ", (laengs.x, laengs.y, laengs.z), strict=True):
        if abs(abs(wert) - 1.0) < GERADE:
            return buchstabe
    return ""
