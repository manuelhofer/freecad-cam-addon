# SPDX-License-Identifier: LGPL-2.1-or-later
"""Konservative räumliche Sweeps aus wirklichen NC-Achsstellungen.

Die Maschine interpoliert ihre Achsen linear. Die Schneide im Grundjob bewegt
sich dagegen auf einer gekrümmten Bahn. Eine Schranke aus den eingelesenen
Kinematikgliedern begrenzt den Fehler eines geraden Sweeps mit fester Mittelachse.
Im Vorschub wird der Körper um diese Schranke erodiert, im Eilgang erweitert.
So erzeugt ein approximierter Schnitt keinen nicht wirklich geschnittenen Raum.
XY-Strahlen bleiben eine Rastervorschau; keine BRep-Fertigteilzulassung.
"""

import math
from dataclasses import dataclass

import numpy as np
from FreeCAD import Vector

from . import reichweite as rw
from .kette import LINEAR
from .sprache import tr

MAX_STUECKE = 500000


@dataclass
class Sweep:
    """Gerade Spitzenbahn, Mittelachse und garantierte Bewegungsabweichungen in mm."""

    von: np.ndarray
    nach: np.ndarray
    achse: np.ndarray
    kugelfehler: float
    schaftfehler: float
    eilgang: bool
    mitte_von: np.ndarray
    mitte_nach: np.ndarray
    stellungen_von: dict
    stellungen_nach: dict


def pose(kinematik, stellungen):
    """Tatsächliche Spitze und Schneidenachse im Grundjob, ohne Dokumentbewegung."""
    p = kinematik.pruefung
    wege = kinematik._wege(stellungen, rundachsen=True)
    werkzeug = p._glied_lage(p._glied(kinematik.aufnahme), wege).multiply(
        p._lage(kinematik.aufnahme)
    )
    lage = p._job_lage(kinematik.nullpunkt, wege).inverse().multiply(werkzeug)
    ein = rw._einspannung(kinematik.laenge)
    spitze = np.array(tuple(lage.multVec(ein.spitze())))
    achse = np.array(tuple(lage.Rotation.multVec(ein.achse())))
    achse /= np.linalg.norm(achse)
    return spitze, achse


def _radius(kin, start, stellungen, schneide, radius):
    """Obere Armlängensumme der beiden gelesenen Ketten über die ganze NC-Folge.

    Abstände benachbarter Gelenkpunkte sind bei Rotation konstant. Veränderungen
    durch Linearachsen werden zusätzlich mit ihrer maximalen Abweichung vom Start
    gezählt. Beide Zweige beginnen im gemeinsamen Assembly-Ursprung. Die Summe
    begrenzt den Abstand jedes Schneidenpunkts zu jedem beteiligten Drehpunkt.
    """
    p, v = kin.pruefung, kin.pruefung.verfahren
    wege = kin._wege(start, rundachsen=True)
    tool = v.pfad(p._glied(kin.aufnahme))
    stock = v.pfad(p._glied(p.werkstueckaufnahme))
    arm = schneide + radius
    vielfach = {}
    for pfad, werkzeugseite in ((tool, True), (stock, False)):
        letzter = Vector()
        for a in pfad:
            vielfach[a] = vielfach.get(a, 0) + 1
            ursprung = p._glied_lage(a.eltern, wege).multVec(v.achslage(a)[1])
            arm += (ursprung - letzter).Length
            letzter = ursprung
        if werkzeugseite:
            arm += (p._spitze(kin.aufnahme, kin.laenge, wege) - letzter).Length
    for a in kin.linear:
        delta = max((abs(s.get(a, start[a]) - start[a]) for s in stellungen), default=0)
        arm += delta * vielfach.get(a, 0)
    return arm, vielfach


def _abweichungen(von, nach, arm, vielfach, koerper):
    """Schranken für Kugelmitten und für eine endliche Schneide mit Mittelrichtung.

    Eine serielle starre Kette hat für jeden Schneidenpunkt die zweite Ableitung
    höchstens arm*theta² + 2*linear*theta. Der Sehnenfehler ist davon 1/8.
    Die feste Mittelrichtung fügt höchstens koerper*theta/2 hinzu. Theta und
    linear summieren die Winkel bzw. Wege beider Kettenzweige über dieses Intervall.
    """
    theta, linear = 0.0, 0.0
    for a, n in vielfach.items():
        delta = abs(nach.get(a, 0) - von.get(a, 0)) * n
        if a.art == LINEAR:
            linear += delta
        else:
            theta += math.radians(delta)
    kugel = (arm * theta**2 + 2 * linear * theta) / 8
    return kugel, koerper * theta / 2


def strecken(fahrt, materialdaten, radius, schneide, fehler, fortschritt=None):
    """Sweeps der einzelnen tatsächlichen Abfahrt, mit Schranke und ursprünglichem Eilgang.

    Unbekannte Achsstellungen erzeugen keinen gedachten Verbindungsschnitt.
    Ressourcenüberschreitung und Abbruch werfen ValueError; der Aufrufer darf einen
    teilweise gerechneten Materialstand dann nicht veröffentlichen.
    """
    if (
        len(fahrt.operationen) != 1
        or not math.isfinite(fehler)
        or fehler <= 0
        or len(materialdaten) != fahrt.operationen[0].saetze
    ):
        raise ValueError(tr("rm3.fehler.geometrie"))
    kin = fahrt.kinematik(0)
    benoetigt = [
        *kin.linear,
        *(a for a in kin.drehachsen if kin.pruefung.programmbuchstabe(a) is not None),
    ]
    states = [fahrt.stellungen_an(i) for i in range(len(fahrt.stationen))]
    gueltig = [
        s.stellungen is not None and all(a in w for a in benoetigt)
        for s, w in zip(fahrt.stationen, states, strict=True)
    ]
    if not any(gueltig):
        raise ValueError(tr("rm3.fehler.geometrie"))
    start = states[gueltig.index(True)]
    arm, vielfach = _radius(kin, start, states, schneide, radius)
    ziel = min(fehler, radius / 8, schneide / 8)
    letzter, pose_vorher, anzahl = None, None, 0
    for i, (station, werte, bekannt) in enumerate(
        zip(fahrt.stationen, states, gueltig, strict=True)
    ):
        if fortschritt is not None and not fortschritt(i / max(1, len(states))):
            raise ValueError(tr("s5p.fehler.unvollstaendig"))
        if not bekannt:
            letzter, pose_vorher = None, None
            continue
        eil = station.eilgang or not station.satz or materialdaten[station.satz - 1][0]
        jetzt = pose(kin, werte)
        if letzter is None:
            tip, u = jetzt
            yield Sweep(tip, tip, u, 0, 0, eil, tip + radius * u, tip + radius * u, werte, werte)
            letzter, pose_vorher = werte, jetzt
            continue
        kugel, winkel = _abweichungen(letzter, werte, arm, vielfach, schneide + radius)
        n = max(1, math.ceil(math.sqrt(2 * kugel / ziel)), math.ceil(2 * winkel / ziel))
        anzahl += n
        if anzahl > MAX_STUECKE:
            raise ValueError(tr("rm3.fehler.bahn_budget"))
        a, u_a = pose_vorher
        w_vorher = letzter
        for k in range(1, n + 1):
            # Auch ein einzelner großer NC-Schwenk muss während der vielen
            # räumlichen Teilstücke abbrechbar bleiben.
            if (
                fortschritt is not None
                and k % 32 == 1
                and not fortschritt((i + (k - 1) / n) / max(1, len(states)))
            ):
                raise ValueError(tr("s5p.fehler.unvollstaendig"))
            if k == n:
                b, u_b = jetzt
                w = werte
            else:
                w = {achse: val + (werte[achse] - val) * k / n for achse, val in letzter.items()}
                b, u_b = pose(kin, w)
            if winkel:
                w_mitte = {
                    achse: val + (werte[achse] - val) * (k - 0.5) / n
                    for achse, val in letzter.items()
                }
                _, mitte = pose(kin, w_mitte)
            else:
                mitte = u_a
            yield Sweep(
                a,
                b,
                mitte,
                kugel / n**2,
                kugel / n**2 + winkel / n,
                eil,
                a + radius * u_a,
                b + radius * u_b,
                w_vorher,
                w,
            )
            a, u_a = b, u_b
            w_vorher = w
        letzter, pose_vorher = werte, jetzt


def abtragen(material, fahrt, daten, form, schneide, fortschritt=None):
    """True bei sicher nachlesbarer Folge, False bei möglichem Eilgangabtrag.

    Der Vorschub erodiert Kugel und Zylinder um ihre eigene Fehlerschranke. Der
    Eilgang prüft die größere äußere Hülle in einer unabhängigen Materialkopie.
    Diese Änderungen bleiben lokal bis zur vollständigen Freigabe des Aufrufers.
    """
    r = form.radius
    if not (form.eben or form.nur_kugel) or schneide < (2 * r if form.nur_kugel else r / 4):
        raise ValueError(tr("rm3.fehler.geometrie"))
    for s in strecken(fahrt, daten, r, schneide, material.schritt / 8, fortschritt):
        q = material.kopie() if s.eilgang else material
        vorzeichen = 1 if s.eilgang else -1
        volumen = 0.0
        if form.nur_kugel:
            volumen += q.kugel(s.mitte_von, s.mitte_nach, r + vorzeichen * s.kugelfehler)
            von, nach = s.von + r * s.achse, s.nach + r * s.achse
            laenge = schneide - r
        else:
            von, nach, laenge = s.von, s.nach, schneide
        e = s.schaftfehler
        volumen += q.schaft(
            von - vorzeichen * e * s.achse,
            nach - vorzeichen * e * s.achse,
            s.achse,
            r + vorzeichen * e,
            laenge + 2 * vorzeichen * e,
        )
        if s.eilgang and volumen > 1e-7:
            return False
        material.bewegungsfehler = max(getattr(material, "bewegungsfehler", 0), e)
    return True
