# SPDX-License-Identifier: LGPL-2.1-or-later
"""Bahnen für die 4-Achs-Bearbeitung: rundum schruppen und rundum schlichten
(Spezifikation W-003, Abschnitt 9, Stufen V3b und V5b).

„Rundum schruppen“ nimmt die Stange in Lagen ab, bis aufs Schlichtaufmaß:
Lage k liegt auf dem Radius R_Stange − k · ap. Je Lage läuft eine Spirale mit
der Steigung „Vorschub je Umdrehung“ von vorne – der Fräser ganz vor der
Stange – bis vor das Futter; die Spitze folgt dem höheren von Lage und
Hüllfläche plus Aufmaß (vierachs_huelle, mit dem Radius R + Aufmaß). Danach
geht es radial hinaus und im Eilgang nach vorne zur nächsten Lage.

- Wo die Stirn das Teil nicht trifft, schneidet die Lage.
- Hinten läuft die Spirale über das Teil hinaus: Die Mitte des Fräsers kommt den Überlauf
  hinter das Teil und fährt dort das Profil des Teilendes gerade weiter – die Kante hinten
  wird fertig, und das Stechschwert trifft beim Abstechen auf ein gerades Stück statt auf eine
  Schräge, an der es verläuft (Manuel, 2026-10-03: „nach dem Teil einfach noch die
  Abstechlänge als gerades Stück weiter“). Vorschlag: Abstechbreite + UEBERLAUF_ZUGABE; bis
  P-2026-10-03-08 Fräserradius + 0,5 (Manuel, 2026-09-29: „mindestens mal 6.5 drüber
  fahren“) – mit dem geraden Stück ist die Kante schon fertig, sobald die Mitte das Teilende
  erreicht; mehr Überlauf nähme hinten nur Material weg, das das Teil hält. Der Rand des Fräsers
  bleibt aber immer den Abstand zum Futter vor der Spannfläche; wie weit die
  Stange dafür herausragen muss, rechnet der Assistent (vierachs_rohteil).
- Die Spitze folgt der Hüllfläche auch über die Drehmitte hinaus (r < 0: der Fräser
  kreuzt die Achse – auf der Drehmaschine ein X unter null). Bis P-2026-10-03-07 blieb sie
  einen Fräserradius von der Achse weg; an Manuels Teil, das neben der Achse liegt, blieb
  dadurch ein Kern Ø 2 R stehen, und eine Fläche unter der Mitte bekam eine Wulst
  („Hubbel“). `r_tiefste` begrenzt es, wenn eine Maschine nicht über die Mitte kann.
- Ein Fräser mit runder Stirn (Kugel, Torus) rechnet mit seiner Form (fraeserform) –
  genau, wie beim Schlichten; bis dahin wie ein Schaftfräser gleichen Durchmessers, was auf
  schrägen Flächen bis 0,6 R stehen ließ.
- Liegen Punkte auf einer Geraden in (a, r, φ) – eine Lage ohne Teil darunter
  –, bleiben nur ihre Enden und alle HOECHSTENS_GRAD einer.
- Wie viele Lagen es braucht, sagt der tiefste Punkt über dem Teil; vor dem
  Teil (Planaufmaß) schneidet jede Lage nur so tief wie sie selbst.

„Rundum schlichten“ fährt eine Spirale mit der Schrittweite als Steigung, die
Spitze auf der Hüllfläche des Schlichtfräsers mit seiner Form (fraeserform) plus
Aufmaß – genau an den Stellen der Spirale gerechnet (vierachs_huelle.je_winkel),
alle SCHRITT_PHI_SCHLICHTEN Grad ein Punkt. Wo die Bahn sich zwischen zwei
Punkten nach außen wölbt, hebt sie sich um den Sehnenfehler; gerade Stücke fasst
sie zusammen, solange die Bahn höchstens BAHN_TOLERANZ über den Punkten bleibt
und nie darunter. Vor und hinter dem Teil bleibt die Spitze auf der Tiefe seines
Endes, wie beim Schruppen. Was das Schruppen stehen ließ (vierachs_schlichten.rest_nach),
nimmt sie in einem Zug – eine Spirale von vorne nach hinten; Schlichtbahn.rest_ueber sagt,
wie viel das höchstens ist (Manuel, 2026-10-03; bis P-2026-10-03-17 fuhr sie dort vorher in
Stufen).

„Linien längs“ (V4c, Muster LINIEN) schlichtet statt mit der Spirale in Linien längs der
Achse bei festem Winkel: für Flächen, die nicht rundum gehen – eine Abflachung, eine Nut, eine
Nocke – mit dem Kugel- oder Torusfräser. Die Linien liegen rundum gleich weit auseinander,
höchstens Schrittweite ÷ größter Radius (so bleibt zwischen zweien nicht mehr stehen als
zwischen zwei Umdrehungen der Spirale), und laufen gegenläufig: Am Ende einer Linie dreht die
Rundachse in der Tiefe zur nächsten weiter, wo die dort auch fräst – sonst hebt der Fräser ab.
Mit gewählten Flächen nur die Linien und Stücke über dem Bereich.

Mit gewählten Flächen (Stufe V4, vierachs_flaechen) fräsen beide nur im Bereich, in dem
der Fräser eine von ihnen berührt; gerechnet wird weiter gegen das ganze Teil. Dazwischen hebt
er über die Stange ab und fährt im Eilgang weiter (Manuel, 2026-09-30: „je nach Rohteil
abheben und irgendwo wieder einsetzen, so dass er nicht kaputt geht“). Wieder hinein geht es
im Eilgang bis knapp über das, was dort noch steht, dann:

- beim Schruppen senkrecht mit dem Eintauchvorschub, wo die Umdrehung davor an derselben
  Stelle schon gefräst hat – die Mitte des Fräsers steht dann über Freiem, er taucht nur mit
  dem Rand ein –, sonst über eine Rampe mit dem Eintauchwinkel längs der Bahn, hin und her,
  bis er unten ist, und auf der Bahn zurück zum Anfang. Jede Lage fährt dieselben Stellen wie
  die davor; so steht über jeder Stelle höchstens noch die Tiefe der Lage davor.
- beim Schlichten senkrecht mit dem Eintauchvorschub: Dort steht nur das Aufmaß.

Gerechnet wird in Rundachs-Koordinaten (a, r, φ) wie in vierachs_huelle.
befehle() macht daraus Path-Befehle: X, Y und Z der Spitze im Rahmen der
Maschine – die Rundachse dreht das Teil darunter, so zeigt FreeCAD die Bahn –,
die Rundachse mit ihrem Buchstaben und der Vorschub nach G93.

Im Freien schnell (Manuel, 2026-10-05: eine Scheibe Ø 40 in der Stange Ø 40 – „er bearbeitet
beim Schruppen auch die Ø 40 und beim Schlichten auch“; „nicht pauschalisieren“): Je Punkt wird
gerechnet, ob dort noch Material steht – beim Schruppen in der Spirale, ob die Hüllfläche unter
der Stange liegt; beim Schlichten in der Spirale, ob der Rest nach dem Schruppen (ohne Schruppen:
die Stange) irgendwo unter dem Fräser über die Bahn reicht (_nicht_tiefer). Wo
nicht, ist das Stück frei (Punkt.frei, _frei): zusammen mindestens freiwege.MINDEST mm lang, bis
freiwege.VORLAUF mm vor dem nächsten Material – befehle() schreibt dort den Freivorschub der
Maschine. Die Bahn bleibt, wo sie ist; nur schneller.

Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass, replace

import numpy as np

from . import fraeserform as ff
from . import spindel as sp
from . import vierachs_huelle as vh
from . import vierachs_quer as vq
from .sprache import tr

SICHERHEIT = 2.0  # mm – so weit über und vor der Stange fährt der Fräser im Eilgang
# mm – so weit bleibt der Rand des Fräsers vor der Spannfläche (Vorschlag): deutlich mehr
# als der Warnabstand der Kollisionsprüfung (1 mm).
ABSTAND_FUTTER = 5.0
UEBERLAUF_ZUGABE = 0.5  # mm – Überlauf = Abstechbreite + das
ABSTECHBREITE = 3.0  # mm – wie vierachs_rohteil.ABSTECHBREITE, ohne Job
RAND = 0.005  # mm – zum Aufmaß dazu, für Rundungen im Raster
GLEICH = 1e-9  # mm – so wenig Unterschied gilt als derselbe Radius
LEER = 1e-3  # mm – so knapp über dem Material gilt eine Stelle als frei (nichts weg)
# So tief bliebe ein Hindernis zwischen zwei Zeilen im Abstand g höchstens unentdeckt, wenn nur
# auf den Zeilen geprüft wird: g² ÷ (8 R). Mehr – ein großer Fräser mit großem ae – und auch
# dazwischen wird geprüft, ob der Weg von Zeile zu Zeile frei ist (_zwischen; P-2026-10-02-30:
# Ø 50 mit ae 35 schnitt beim Planfräsen auf Manuels Platte quer in den Zapfen).
ZWISCHEN_GENAU = 0.05  # mm
# So weit dreht die Rundachse höchstens in einem Satz: FreeCAD 1.1.3 zeigt einen Satz
# über mehrere Umdrehungen als Gerade (PathSegmentWalker rechnet den Winkel modulo 360°).
HOECHSTENS_GRAD = 90.0
SCHRITT_PHI_SCHLICHTEN = 0.5  # Grad – so dicht liegen die Punkte der Schlichtspirale
# Mit der Querachse: Springt ψ zwischen zwei Punkten um mehr als so viele Winkelschritte, ist
# es eine Innenecke – das Werkzeug dreht dort um die ruhende Kugelmitte (_spirale_quer).
QUER_SPRUNG = 4
# Springt die Mitte der Kugel zwischen zwei Punkten des Plans mehr als so viel mal so weit, wie
# die Spirale je Schritt vorrückt, kommen Zwischenstellungen dazu – alle QUER_UEBERGANG mm.
QUER_SPRUNG_MITTE = 3.0
QUER_UEBERGANG = 0.05  # mm
QUER_UMGEBUNG = 3  # Schritte davor und danach
QUER_MEHR_LAGEN = 3  # so viele Lagen mehr als rundum höchstens beim Schruppen mit der Querachse
# Beim Zusammenfassen mit der Querachse (_zusammen_quer): so weit darf die Kugelmitte zwischen
# zwei bleibenden Punkten nach innen (zum Teil) und seitlich (an eine andere Stelle derselben
# Bahn) von den ausgelassenen Punkten abweichen; nach außen BAHN_TOLERANZ.
# Die Normale wird über so viele Punkte zu jeder Seite geglättet (normale_quer): bei 0,5° je
# Punkt 8,5° – mehr als eine Facette des Netzes (5° bei R 5 mm).
QUER_GLATT = 8
QUER_INNEN = 0.0005  # mm
# Beim Schruppen hat die zusammengefasste Bahn Spiel: ein Zehntel des Aufmaßes, höchstens
# SCHRUPP_SPIEL_HOECHSTENS – so weit darf die Gerade zwischen zwei bleibenden Punkten beim
# Auswählen über und unter den ausgelassenen liegen; danach werden die bleibenden Punkte so
# weit angehoben, dass nichts ins Aufmaß schneidet (höchstens das Spiel bleibt mehr stehen).
# Die Hüllfläche folgt den Facetten des Netzes um Tausendstel; mit BAHN_TOLERANZ allein und
# ohne Spiel nach innen blieb davon in der letzten Lage alle 1–2° ein Satz (Manuel, 2026-10-09:
# „ein Grad … eine sehr große Zahl“). So reicht rundum ein Satz je HOECHSTENS_GRAD, und die
# Sätze werden von selbst kürzer, wo sich das Teil krümmt. Ohne Aufmaß gibt es kein Spiel.
SCHRUPP_SPIEL_ANTEIL = 0.1
SCHRUPP_SPIEL_HOECHSTENS = 0.05  # mm
QUER_SEITLICH = 0.5  # mm – fünf Punkte weit; längs rückt die Spirale dabei um Tausendstel
# … bei Schaft- und Torusfräsern (geprüft am Weg der Spitze): Seitlich verschoben läge die
# ebene Stirn in einer Kehle tiefer – so wenig nur.
QUER_SEITLICH_SPITZE = 0.02  # mm
# Grad – so weit steht die Kugel mit der Querachse neben der Normalen, in Vorschubrichtung geneigt
# (ziehend): Sie schneidet nicht mit der Spitze (Manuel, 2026-10-04: „als Haken, der aber pauschal
# angehakt ist“) – wie das Anstellen beim 5-Achs-Schlichten (angestellt.WINKEL).
ANSTELLEN_QUER = 15.0
TOLERANZ_SCHLICHTEN = 0.005  # mm – so fein wird das Teil fürs Schlichten vernetzt
BAHN_TOLERANZ = 0.002  # mm – so weit darf die zusammengefasste Bahn über den Punkten liegen
# mm – höchstens so viel hebt der Sehnenfehler einen Punkt: Er gilt für Rundungen; an einer
# Kante springt die Hüllfläche, dort dringt die Gerade kaum ein (längs, um Tausendstel).
SEHNE_HOECHSTENS = 0.02
# Wölbt sich die Hüllfläche zwischen zwei Punkten der Spirale um mehr als so viel nach außen,
# rechnet _verfeinert dort Zwischenpunkte – höchstens FEIN_HOECHSTENS je Schritt.
SEHNE_FEIN = 0.002  # mm
FEIN_HOECHSTENS = 32
FEIN_DURCHGAENGE = 3
FEIN_KLEINSTER = 1.0 / 256  # so fein (in Punkten der Spirale) teilt _verfeinert höchstens
# mm – so viel weiter als Fräser, Aufmaß und Vernetzung steht ein Ring vor der Wand (D-42)
RING_LUFT = 0.01
EINTAUCHWINKEL = 5.0  # Grad – so steil taucht die Rampe ein, wenn das Werkzeug nichts sagt
RAMPE_MINDESTENS = 0.5  # mm – ein kürzeres Stück hat keinen Platz für eine Rampe
RAMPE_HOECHSTENS = 200  # so oft läuft eine Rampe höchstens hin und her
# So viele Nachkommastellen behält FreeCAD von F, wenn es die Bahn im Dokument speichert.
F_STELLEN = 6
# Das Muster beim Schlichten (V4c): die Spirale, oder Linien längs der Achse bei festem Winkel.
SPIRALE = "spirale"
LINIEN = "linien"
MUSTER = (SPIRALE, LINIEN)
SCHRITT_A_LINIEN = vh.SCHRITT_A  # mm – so dicht liegen die Punkte einer Linie längs


@dataclass(frozen=True)
class Schruppwerte:
    """Was das Schruppen braucht; Längen in mm, a längs der Stangenachse im Job."""

    fraeser_radius: float
    stange_radius: float
    zustellung: float  # ap: so tief je Lage, radial
    steigung: float  # so weit längs je Umdrehung der Spirale (ae)
    aufmass: float  # bleibt fürs Schlichten stehen
    a_stange_vorne: float  # das vordere Ende der Stange
    a_futter: float  # die Spannfläche: dahinter steckt die Stange im Futter
    sicherheit: float = SICHERHEIT
    ueberlauf: float = None  # so weit hinter das Teil (Mitte des Fräsers); None: Vorschlag
    abstand_futter: float = ABSTAND_FUTTER  # Rand des Fräsers bis zur Spannfläche
    # So weit reicht der Halter seitlich über die Werkzeugachse (halter.seitlich): Reicht er
    # weiter als der Fräser, gilt der Abstand zum Futter von seinem Rand.
    halter: float = 0.0
    # (a, Seite) der Wände des Teils quer zur Achse (vierachs_operation.waende): Vor jeder
    # hält die Spirale eine Umdrehung an – der Ringgang (D-42).
    waende: tuple = ()
    # Wo die Mitte des Fräsers fräst (vierachs_flaechen.Bereich, V4); None: überall – rundum.
    bereich: object = None
    eintauchwinkel: float = EINTAUCHWINKEL  # Grad, für die Rampe ins Material
    # Die Spirale im Gleichlauf für M3 (spindel.fuer_m3): False – andersherum (M4, Gegenlauf).
    gleichlauf: bool = True
    # Mit gewählten Flächen die Zeilen nur im Gleichlauf: jede für sich, dazwischen abheben
    # (P-2026-10-02-26); sonst hin und her.
    nur_gleichlauf: bool = False
    # Die Form des Fräsers (fraeserform.Form); None oder eben: die Scheibe mit fraeser_radius.
    form: object = None
    # So nah darf die Spitze der Achse kommen – negativ: darüber hinaus (P-2026-10-03-07).
    r_tiefste: float = -math.inf
    # Die Spirale mit der Querachse (V5e, P-2026-10-03-23): je Punkt die Werkzeugachse längs der
    # Normalen – auf einer ebenen Fläche hält die Rundachse, die Querachse fährt die Gerade; je
    # Lage höchstens die Zustellung unter die Stange (vierachs_quer.lagen_grenze).
    querachse: bool = False


@dataclass(frozen=True)
class Schlichtwerte:
    """Was das Schlichten braucht; Längen in mm, a längs der Stangenachse im Job."""

    form: object  # fraeserform.Form des Schlichtfräsers
    stange_radius: float
    schrittweite: float  # so weit längs je Umdrehung der Spirale
    aufmass: float  # bleibt stehen (0: fertig)
    a_stange_vorne: float
    a_futter: float
    sicherheit: float = SICHERHEIT
    ueberlauf: float = None  # so weit hinter das Teil (Mitte des Fräsers); None: Vorschlag
    abstand_futter: float = ABSTAND_FUTTER
    halter: float = 0.0  # wie bei Schruppwerte
    waende: tuple = ()  # wie bei Schruppwerte
    # Der Rest nach dem Schruppen: (a, φ in rad, r) wie restmaterial.Stange; None: kein Schutz.
    rest: tuple = None
    r_tiefste: float = -math.inf  # wie bei Schruppwerte
    bereich: object = None  # wie bei Schruppwerte
    muster: str = SPIRALE  # SPIRALE oder LINIEN (Linien längs, V4c)
    gleichlauf: bool = True  # wie bei Schruppwerte
    nur_gleichlauf: bool = False  # Linien längs jede für sich im Gleichlauf (P-2026-10-02-28)
    # Die Spirale mit der Querachse (V5e, Manuels Y-Gedanke): Die Werkzeugachse steht an
    # jedem Punkt längs der Normalen der Hüllfläche – auf einer ebenen Fläche hält die
    # Rundachse, die Querachse (bei C das Y) fährt die Gerade. Nur mit dem Kugelfräser.
    querachse: bool = False
    # Grad – mit der Querachse steht die Kugel so weit neben der Normalen, in Vorschubrichtung
    # geneigt (ANSTELLEN_QUER); 0: auf der Normalen, sie schneidet mit der Spitze.
    anstellen: float = 0.0


@dataclass
class Schlichtbahn:
    """Ergebnis von schlichten()."""

    punkte: list  # [Punkt], der erste ist der Start (Eilgang, vor der Stange)
    umdrehungen: float
    r_min: float  # so nah kommt die Spitze der Achse (mm)
    kammhoehe: float  # so hoch bleibt zwischen zwei Bahnen stehen (auf ebener Fläche, mm)
    hinten_frei: float = 0.0  # so viel vom hinteren Ende des Teils erreicht der Fräser nicht
    # So viel steht nach dem Schruppen höchstens über der Bahn (mm; 0 ohne Rest): das nimmt
    # Schlichten in einem Zug – Aufmaß des Schruppens, seine Rillen und was sein Fräser nicht
    # erreicht hat (Manuel, 2026-10-03: „einfach spiralisiert, mit einer seitlichen Zustellung
    # von der Angabe“; bis P-2026-10-03-17 fuhr es dort vorher in Stufen).
    rest_ueber: float = 0.0
    linien: int = 0  # Linien längs (Muster LINIEN): so viele Linien hat die Bahn
    querachse: bool = False  # die Spirale fährt mit der Querachse (Schlichtwerte.querachse)


def schrupp_spiel(aufmass):
    """So weit (mm) darf die zusammengefasste Schruppbahn vom Raster abweichen: ein Zehntel des
    Aufmaßes `aufmass`, höchstens SCHRUPP_SPIEL_HOECHSTENS; 0 ohne Aufmaß."""
    return min(SCHRUPP_SPIEL_HOECHSTENS, max(0.0, float(aufmass)) * SCHRUPP_SPIEL_ANTEIL)


def _gehoben(r, bleibt, t=None):
    """Je bleibendem Punkt (Stellen `bleibt` in `r`) sein Radius, so weit angehoben, dass die
    Gerade zu den bleibenden Nachbarn über jedem ausgelassenen Punkt liegt – um das, was
    _zusammengefasst mit `innen` darunter ließ (höchstens das Spiel; 0, wo nichts darunter lag).
    `t` wie dort: a und φ sind dann linear in t."""
    r = np.asarray(r, dtype=float)
    stelle = np.arange(len(r), dtype=float) if t is None else np.asarray(t, dtype=float)
    hebung = np.zeros(len(bleibt))
    for k in range(len(bleibt) - 1):
        i, j = bleibt[k], bleibt[k + 1]
        if j <= i + 1:
            continue
        zwischen = np.arange(i + 1, j)
        anteil = (stelle[zwischen] - stelle[i]) / max(stelle[j] - stelle[i], 1e-12)
        fehlt = float(np.max(r[zwischen] - (r[i] + anteil * (r[j] - r[i]))))
        if fehlt > 0.0:
            hebung[k] = max(hebung[k], fehlt)
            hebung[k + 1] = max(hebung[k + 1], fehlt)
    return (r[list(bleibt)] + hebung).tolist()


def rillenhoehe(fraeser_radius, eckradius, steigung):
    """So hoch bleiben Rillen zwischen zwei Bahnen der Spirale stehen, wenn die Stirn des
    Fräsers mit `eckradius` gerundet ist (beim Kugelfräser: sein Radius), in mm. Die
    Hüllfläche rechnet mit der Stirn als flacher Scheibe – das Teil bleibt sicher, an den
    Rundungen bleibt mehr stehen: in der Mitte zwischen zwei Bahnen am meisten."""
    seitlich = steigung / 2 - (fraeser_radius - eckradius)
    if eckradius <= 0 or seitlich <= 0:
        return 0.0
    seitlich = min(seitlich, eckradius)
    return eckradius - math.sqrt(eckradius * eckradius - seitlich * seitlich)


def ueberlauf_vorschlag(_fraeser_radius=0.0, abstechbreite=ABSTECHBREITE):
    """Der Überlauf hinter dem Teil: das gerade Stück fürs Abstechen, Abstechbreite +
    UEBERLAUF_ZUGABE – gleich für jeden Fräser (bis P-2026-10-03-08: Radius + 0,5)."""
    return abstechbreite + UEBERLAUF_ZUGABE


def _ende(teil_hinten, ueberlauf, radius, w):
    """Bis wohin die Mitte des Fräsers längs fährt (a): den Überlauf hinter das Teil, aber
    nicht näher ans Futter, als Fräser oder Halter (der weiter reicht) mit Abstand erlauben."""
    return max(teil_hinten - ueberlauf, w.a_futter + max(radius, w.halter) + w.abstand_futter)


def _kein_platz(radius, w):
    """Der Satz, wenn zwischen Futter und Teil kein Platz ist – mit dem Halter, wenn er es
    ist, der weiter reicht."""
    if w.halter > radius:
        return tr("vb.fehler.platz_halter")
    return tr("vb.fehler.platz")


def _ringe(waende, abstand, a_von, a_bis, ende=False):
    """Wo die Spirale eine Umdrehung anhält (Ringgang, D-42): vor jeder Wand (a, Seite) so
    weit, dass der Fräser sie berührt – `abstand` (Radius plus Aufmaß) zu der Seite hin, zu
    der sie schaut; nur zwischen a_von und a_bis, von vorn nach hinten, jede Stelle einmal.
    Mit `ende` auch am Ende (a_von): Dort hört die Spirale sonst mitten in der Umdrehung auf,
    und das gerade Stück zum Abstechen (P-2026-10-03-08) wäre ein Schraubenstück mit der
    Steigung der Spirale; mit dem Ring ist das Ende rund (P-2026-10-03-17)."""
    stellen = {round(a + seite * abstand, 6) for a, seite in waende}
    ringe = sorted((s for s in stellen if a_von < s < a_bis), reverse=True)
    return ringe + [a_von] if ende else ringe


def _mit_ringen(a, ringe, je_umdrehung):
    """Die Spirale `a` (je Punkt, fallend) mit einem Ring je Stelle in `ringe`:
    (a, Winkelschritte, Herkunft). Ein Ring sind je_umdrehung Punkte bei festem a; danach läuft
    die Spirale eine Umdrehung später weiter. Herkunft: die Nummer des Punkts der Spirale,
    beim Ring −1 − seine Nummer."""
    k = np.arange(len(a))
    teile_a, teile_k, teile_h = [], [], []
    versatz = 0
    anfang = 0
    for nummer, stelle in enumerate(ringe):
        i = int(np.searchsorted(-a, -stelle, side="left"))  # der erste Punkt mit a <= stelle
        if stelle <= a[-1] + GLEICH:  # der Ring am Ende: nach dem letzten Punkt
            i = len(a)
        k_ring = k[i] if i < len(a) else k[-1] + 1
        teile_a += [a[anfang:i], np.full(je_umdrehung, stelle)]
        teile_k += [k[anfang:i] + versatz, k_ring + versatz + np.arange(je_umdrehung)]
        teile_h += [k[anfang:i], np.full(je_umdrehung, -1 - nummer)]
        versatz += je_umdrehung
        anfang = i
    teile_a.append(a[anfang:])
    teile_k.append(k[anfang:] + versatz)
    teile_h.append(k[anfang:])
    return np.concatenate(teile_a), np.concatenate(teile_k), np.concatenate(teile_h)


def _ring_radien(r, herkunft, schritte, ring_r, je_umdrehung):
    """Die Radien der Spirale mit Ringen (_mit_ringen): je Ring seine Zeile
    `ring_r[nummer]` (je Winkel) an seinen Punkten, sonst `r` – je Punkt der Spirale mit
    Ringen, oder (so lang wie `herkunft` nicht) je Punkt der Spirale ohne sie."""
    ergebnis = np.array(r, dtype=float)
    if len(ergebnis) != len(herkunft):
        ergebnis = np.empty(len(herkunft))
        spirale = herkunft >= 0
        ergebnis[spirale] = np.asarray(r)[herkunft[spirale]]
    for nummer, zeile in enumerate(ring_r):
        drin = herkunft == -1 - nummer
        ergebnis[drin] = zeile[schritte[drin] % je_umdrehung]
    return ergebnis


@dataclass(frozen=True)
class Punkt:
    """Ein Punkt der Bahn: Stelle längs, Radius der Spitze, Winkel (Grad, fortlaufend);
    `eintauchen`: hierher mit dem Eintauchvorschub (senkrecht ins Material). `q`: der Versatz
    der Spitze quer zur Werkzeugachse (mm, bei C das Y) – 0 bei den Rundum-Bahnen, deren
    Spitze auf dem Strahl von der Achse steht; „Plan indexiert“ (vierachs_planbahn) fährt
    damit Zeilen über eine ebene Fläche. Der Radius ist dann die Höhe der Spitze längs der
    Werkzeugachse, der Winkel der der Rundachse."""

    eilgang: bool
    a: float
    r: float
    phi: float
    eintauchen: bool = False
    q: float = 0.0
    anteil: float = 1.0  # so viel vom Vorschub (die Nut in voller Breite: weniger)
    frei: bool = False  # hierher durchs Freie: mit dem Freivorschub (_frei)


@dataclass
class Bahn:
    """Ergebnis von schruppen()."""

    punkte: list  # [Punkt], der erste ist der Start (Eilgang, vor der Stange)
    lagen: int
    r_min: float  # so nah kommt die Spitze der Achse (mm)
    hinten_frei: float = 0.0  # so viel vom hinteren Ende des Teils erreicht der Fräser nicht


def _drehung(a_anfang, a_ende, gleichlauf):
    """+1, wenn der Winkel der Spirale steigen muss, sonst −1 (P-2026-10-02-23). Im Rahmen des
    Teils – radial (φ = 0), quer, längs – zeigt der Fräser zur Achse, fährt mit steigendem φ
    quer, und das Material liegt dort, wohin die Spirale längs vorrückt: spindel.ist_gleichlauf
    sagt, ob das für M3 Gleichlauf ist. Welche Richtung der Rundachse das an der Maschine ist,
    rechnet befehle() mit ihrem Drehsinn – so stimmt es auf jeder Maschine."""
    vor = 1.0 if a_ende > a_anfang else -1.0
    steigend = sp.ist_gleichlauf((-1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, vor))
    return 1 if steigend == bool(gleichlauf) else -1


def schruppen(netz, laengs, radial, werte, schritt_a=vh.SCHRITT_A, schritt_phi=vh.SCHRITT_PHI):
    """Die Schruppbahn (Bahn) für `netz` (vierachs_huelle.vernetze, im Job) mit den
    Schruppwerten `werte`; `laengs` und `radial` wie in vierachs_huelle.

    ValueError, wenn die Werte nicht gehen – mit einem Satz für den Menschen.
    """
    w = werte
    if w.fraeser_radius <= 0 or w.zustellung <= 0 or w.steigung <= 0:
        raise ValueError(tr("vb.fehler.werte"))
    if w.steigung > 2 * w.fraeser_radius:
        raise ValueError(tr("vb.fehler.steigung"))
    l_, _u, _v = vh.rahmen(laengs, radial)
    a_teil = netz.punkte @ l_
    teil_vorne, teil_hinten = float(a_teil.max()), float(a_teil.min())
    radius = w.fraeser_radius
    ueberlauf = ueberlauf_vorschlag(radius) if w.ueberlauf is None else w.ueberlauf
    a_anfang = w.a_stange_vorne + radius + w.sicherheit
    a_ende = _ende(teil_hinten, ueberlauf, radius, w)
    if a_ende >= teil_vorne + radius:
        raise ValueError(_kein_platz(radius, w))
    hinten_frei = max(0.0, a_ende - radius - teil_hinten)

    # Die Spirale: gleich viele Punkte je Umdrehung wie das Raster Winkel hat.
    phi_werte = vh.raster_phi(schritt_phi)
    je_umdrehung = len(phi_werte)
    anzahl = max(1, int(math.ceil((a_anfang - a_ende) / w.steigung * je_umdrehung)))
    k = np.arange(anzahl + 1)
    a = a_anfang - (a_anfang - a_ende) * k / anzahl
    # Mit gewählten Flächen reicht die Hüllfläche über ihren Bereich – dort liegen alle Zeilen.
    a_von, a_bis = a_ende, a_anfang
    if w.bereich is not None and w.bereich.drin.any():
        belegt = w.bereich.a[w.bereich.drin.any(axis=1)]
        a_von = max(a_von, min(float(belegt.min()), a_bis))
        a_bis = min(a_bis, max(float(belegt.max()), a_von))
    a_werte = vh.raster_a(a_von - schritt_a, a_bis + schritt_a, schritt_a)
    rund = w.form is not None and not w.form.eben  # Kugel, Torus: mit ihrer Form
    form = w.form.mit_aufmass(w.aufmass) if rund else None

    def huelle_bei(stellen):
        if rund:
            return vh.fraeser(netz, laengs, radial, form, stellen, phi_werte)
        return vh.schaftfraeser(netz, laengs, radial, radius + w.aufmass, stellen, phi_werte)

    huelle = _hinten_gerade(huelle_bei(a_werte).sicher(), teil_hinten)
    zugabe = w.aufmass + netz.toleranz + RAND
    # Vor jeder Wand hält die Spirale eine Umdrehung an: Sonst kommt der Fräser nur auf
    # einem Teil des Umfangs bis an die Wand (D-42). Die Hüllfläche dort genau an der Stelle
    # des Rings – das Raster nähme den höheren Nachbarn, und der liegt schon an der Wand.
    ringe = _ringe(w.waende, radius + w.aufmass + netz.toleranz + RING_LUFT, a_ende, a_anfang)
    ringe_spirale = ringe + [a_ende]  # und am Ende eine Umdrehung: das Ende rund
    a, k, herkunft = _mit_ringen(a, ringe_spirale, je_umdrehung)
    ring_r = [huelle_bei(np.array([stelle])).sicher().r[0] for stelle in ringe_spirale]
    # Der Ring am Ende hinter dem Teil: das Profil des Teilendes gerade weiter, wie die
    # Spirale dort (_hinten_gerade) – nicht die Stange, und nicht die Stirn hinter der Kante
    # hinab (eine Kugel sänke dort bis zu ihrem Radius tiefer: die Kerbe aus P-2026-10-03-08).
    rundum = np.arange(je_umdrehung)
    ring_r = [
        (
            zeile
            if stelle >= teil_hinten
            else np.where(
                np.isfinite(gerade := huelle.bei(np.full(je_umdrehung, stelle), rundum)),
                gerade,
                zeile,
            )
        )
        for stelle, zeile in zip(ringe_spirale, ring_r, strict=True)
    ]

    drehung = _drehung(a_anfang, a_ende, w.gleichlauf)

    def boden(versatz):
        """Wie tief die Spitze an jedem Punkt der Spirale darf, wenn sie beim Winkel
        phi[versatz] beginnt (drehung: mit steigendem oder fallendem Winkel)."""
        winkel = (drehung * (versatz + k)) % je_umdrehung
        ergebnis = _ring_radien(huelle.bei(a, winkel), herkunft, winkel, ring_r, je_umdrehung)
        ergebnis = ergebnis + zugabe
        # Trifft die Stirn rundum nichts: hinter dem Teil bleibt die Spitze oben, sonst
        # reicht die Achse – mit der Spitze dort ist in dieser Lage alles weg.
        nichts = ~np.isfinite(ergebnis)
        ergebnis = np.where(nichts, np.where(a < teil_hinten, w.stange_radius, 0.0), ergebnis)
        return np.maximum(ergebnis, w.r_tiefste)

    # Wie viele Lagen: bis zum tiefsten Punkt über dem Teil, egal wo die Spirale ihn trifft –
    # mit gewählten Flächen im Bereich.
    auswahl = np.broadcast_to(
        ((huelle.a >= a_ende) & (huelle.a <= a_anfang))[:, None], huelle.r.shape
    )
    if w.bereich is not None:
        auswahl = auswahl & w.bereich.bei(huelle.a[:, None], huelle.phi[None, :])
    ueber_dem_teil = huelle.r[auswahl]
    ueber_dem_teil = ueber_dem_teil[np.isfinite(ueber_dem_teil)]
    r_min = max(float(ueber_dem_teil.min()) + zugabe, w.r_tiefste) if ueber_dem_teil.size else 0.0
    lagen = 0
    if ueber_dem_teil.size:
        lagen = max(0, int(math.ceil((w.stange_radius - r_min) / w.zustellung - GLEICH)))
    sicher = w.stange_radius + w.sicherheit
    punkte = [Punkt(True, a_anfang, sicher, 0.0)]
    if w.bereich is not None:  # gewählte Flächen: Zeilen hin und her (V4)
        zeilen_a = _zeilen(w.bereich, a_ende, a_anfang, w.steigung, ringe)

        def boden_bei(stellen, j):
            """Wie tief die Spitze an den Stellen längs beim Winkelschritt j darf – ein Ring
            genau an seiner Stelle."""
            j = np.broadcast_to(j, np.shape(stellen))
            ergebnis = huelle.bei(stellen, j) + zugabe
            for stelle, zeile in zip(ringe_spirale, ring_r, strict=True):
                ergebnis = np.where(np.abs(stellen - stelle) < GLEICH, zeile[j] + zugabe, ergebnis)
            nichts = ~np.isfinite(ergebnis)
            ergebnis = np.where(
                nichts, np.where(stellen < teil_hinten, w.stange_radius, 0.0), ergebnis
            )
            return np.maximum(ergebnis, w.r_tiefste)

        boden_zeilen = np.array(
            [boden_bei(np.full(je_umdrehung, z), rundum) for z in zeilen_a]
        ).reshape(len(zeilen_a), je_umdrehung)
        _schruppen_zeilen(punkte, zeilen_a, boden_zeilen, boden_bei, lagen, w, schritt_phi)
        _eilgang(punkte, a_anfang, sicher, punkte[-1].phi)
        return Bahn(punkte, lagen, r_min, hinten_frei)
    if w.querachse:
        lagen = _schruppen_quer(
            punkte,
            netz,
            laengs,
            radial,
            w,
            (a, k, herkunft, ringe_spirale, je_umdrehung, drehung, phi_werte),
            (a_werte, teil_hinten, teil_vorne, a_anfang, a_ende, sicher),
            lagen,
            schritt_phi,
        )
        return Bahn(punkte, lagen, r_min, hinten_frei)
    versatz = 0  # die Spirale einer Lage beginnt, wo die letzte endete
    abstand = int(round(HOECHSTENS_GRAD / schritt_phi))
    spiel = schrupp_spiel(w.aufmass)
    for lage in range(1, lagen + 1):
        unten = boden(versatz)
        r = np.maximum(unten, w.stange_radius - lage * w.zustellung)
        phi = drehung * (versatz + k) * schritt_phi
        # Frei, wo die Hüllfläche nicht unter der Stange liegt: Dort steht nie etwas. (Dass die
        # Lage davor schon bis auf die Hüllfläche kam, reicht nicht – an steilen Flanken lässt
        # die Spirale bis 0,7 mm stehen, nachgefahren im Modell der Stange.)
        frei = _frei(a, r, phi, unten >= w.stange_radius - LEER)
        # Es bleiben die Punkte, zwischen denen die Gerade über allen anderen liegt – höchstens
        # das Spiel darüber (schrupp_spiel): Die Hüllfläche folgt den Facetten des Netzes um
        # Tausendstel, und jeder davon als Knick ließ alle 1–2° einen Satz stehen. Dazu, wo ein
        # Ring beginnt oder endet (a knickt) und wo es frei wird oder aufhört, frei zu sein.
        fest = set((np.flatnonzero(_a_knicke(a)) + 1).tolist()) if len(a) > 2 else set()
        fest.update(np.flatnonzero(frei[:-1] != frei[1:]).tolist())
        bleibt = _zusammengefasst(r, max(BAHN_TOLERANZ, spiel), abstand, sorted(fest), innen=spiel)
        for i, r_i in zip(bleibt, _gehoben(r, bleibt), strict=True):
            punkte.append(Punkt(False, float(a[i]), r_i, float(phi[i]), frei=bool(frei[i])))
        versatz += int(k[-1])
        punkte.append(Punkt(True, a_ende, sicher, float(phi[-1])))
        punkte.append(Punkt(True, a_anfang, sicher, float(phi[-1])))
    return Bahn(punkte, lagen, r_min, hinten_frei)


def _schruppen_quer(punkte, netz, laengs, radial, w, spirale, rahmen_, lagen, schritt_phi):
    """Die Lagen von „Rundum schruppen“ mit der Querachse (P-2026-10-03-23): je Lage der Plan
    einer Kugel mit dem Radius des Fräsers (_quer_plan auf ihrer Hüllfläche mit Aufmaß), die
    Stellungen und Höhen des Fräsers aus seiner Hüllfläche (vierachs_quer.stellungen), je Lage
    nicht tiefer als die Zustellung unter die Stange (vierachs_quer.lagen_grenze). Mehr Lagen als
    rundum, wenn die Grenze die letzte noch über dem Teil hält. Gibt die Zahl der Lagen zurück."""
    a, k, herkunft, ringe_spirale, je_umdrehung, drehung, phi_werte = spirale
    a_werte, teil_hinten, teil_vorne, a_anfang, a_ende, sicher = rahmen_
    radius = w.fraeser_radius
    form = w.form if w.form is not None else ff.scheibe(radius)
    kugel = ff.kugel(radius).mit_aufmass(w.aufmass)
    zugabe = w.aufmass + netz.toleranz + RAND
    huelle = _hinten_gerade(
        vh.fraeser(netz, laengs, radial, kugel, a_werte, phi_werte), teil_hinten
    )
    rundum = np.arange(je_umdrehung)
    ring_r = []
    for stelle in ringe_spirale:
        zeile = vh.fraeser(netz, laengs, radial, kugel, np.array([stelle]), phi_werte).r[0]
        if stelle < teil_hinten:  # hinter dem Teil: das Ende gerade weiter
            gerade = huelle.bei(np.full(je_umdrehung, stelle), rundum)
            zeile = np.where(np.isfinite(gerade), gerade, zeile)
        ring_r.append(zeile)
    abstand = int(round(HOECHSTENS_GRAD / schritt_phi))
    kugelform = form.nur_kugel
    spiel = schrupp_spiel(w.aufmass)

    def lage_rechnen(versatz, tiefer):
        winkel_i = (drehung * (versatz + k)) % je_umdrehung
        r = _ring_radien(huelle.bei(a, winkel_i), herkunft, winkel_i, ring_r, je_umdrehung)
        r = r + zugabe
        r = np.where(np.isfinite(r), r, w.stange_radius)  # trifft nichts: oben
        winkel = drehung * (versatz + k) * schritt_phi
        a_p, x_p, q_p, psi_p, fest, _neu = _quer_plan(a, r, winkel, radius, schritt_phi)
        psi_p, x_p, q_p = vq.stellungen(
            netz, laengs, radial, form, zugabe, a_p, x_p, q_p, psi_p, teil_hinten, teil_vorne
        )
        grenze = vq.lagen_grenze(w.stange_radius, q_p, radius, tiefer)
        x = np.maximum(np.maximum(x_p, grenze), w.r_tiefste)
        return a_p, x, q_p, psi_p, fest, bool(np.any(grenze > x_p + BAHN_TOLERANZ))

    versatz = 0
    lage = 0
    while True:
        lage += 1
        a_p, x, q_p, psi_p, fest, noch = lage_rechnen(versatz, lage * w.zustellung)
        _quer_ausgeben(
            punkte,
            a_p,
            x,
            q_p,
            psi_p,
            fest,
            sicher,
            abstand,
            drehung,
            radius if kugelform else 0.0,
            toleranz=max(BAHN_TOLERANZ, spiel),
            innen=max(QUER_INNEN, spiel),
        )
        punkte.append(Punkt(True, a_anfang, sicher, punkte[-1].phi))
        versatz += int(k[-1])
        if lage >= lagen and not noch:
            return lage
        if lage >= lagen + QUER_MEHR_LAGEN:
            return lage


def _rampe(a, r, phi, von, bis, oben, w):
    """Die Rampe ins Material am Anfang des Stücks von..bis: von `oben` über dem Punkt von längs
    der Bahn hinab, mit dem Eintauchwinkel gegen sie, hin und her, bis sie die Bahn r erreicht
    – dann auf ihr zurück zum Anfang: [(a, r, φ)] ohne den Anfang. So fräst sie weg, was unter
    ihr stehen blieb."""
    steil = math.tan(math.radians(w.eintauchwinkel if w.eintauchwinkel > 0 else EINTAUCHWINKEL))
    hoehe = oben
    ergebnis = []
    i, richtung = von, 1
    for _ in range(RAMPE_HOECHSTENS * (bis - von + 1)):
        j = i + richtung
        if not von <= j <= bis:  # am Ende des Stücks: kehrt um
            richtung = -richtung
            j = i + richtung
        bogen = max(hoehe, float(r[j])) * math.radians(float(phi[j] - phi[i]))
        hoehe -= steil * math.hypot(float(a[j] - a[i]), bogen)
        if hoehe <= r[j]:
            zurueck = range(j, von - 1, -1)
            ergebnis.extend((float(a[m]), float(r[m]), float(phi[m])) for m in zurueck)
            return ergebnis
        ergebnis.append((float(a[j]), hoehe, float(phi[j])))
        i = j
    ergebnis.append((float(a[von]), float(r[von]), float(phi[von])))  # nie unten: senkrecht
    return ergebnis


def _laenge(a, r, phi, von, bis):
    """Wie lang das Stück von..bis der Bahn an der Spitze ist (mm)."""
    bogen = r[von:bis] * np.diff(np.radians(phi[von : bis + 1]))
    return float(np.sum(np.hypot(np.diff(a[von : bis + 1]), bogen)))


def _stuecke(im):
    """[(von, bis)] – die Läufe, in denen `im` wahr ist (Punktnummern, bis einschließlich)."""
    rand = np.diff(np.concatenate([[0], np.asarray(im, dtype=np.int8), [0]]))
    return list(
        zip(
            np.flatnonzero(rand == 1).tolist(),
            (np.flatnonzero(rand == -1) - 1).tolist(),
            strict=True,
        )
    )


def _eilgang(punkte, a, r, phi):
    """Im Eilgang nach (a, r, φ) – eine lange Drehung in Schritten von höchstens
    HOECHSTENS_GRAD, wie die Bahn selbst."""
    vorher = punkte[-1]
    schritte = max(1, int(math.ceil(abs(phi - vorher.phi) / HOECHSTENS_GRAD - 1e-9)))
    for m in range(1, schritte + 1):
        t = m / schritte
        punkt = Punkt(
            True,
            vorher.a + t * (a - vorher.a),
            vorher.r + t * (r - vorher.r),
            vorher.phi + t * (phi - vorher.phi),
        )
        if punkt != punkte[-1]:
            punkte.append(punkt)


# --- Mit gewählten Flächen: Zeilen hin und her (V4) -----------------------------------------
# Manuel (2026-09-30, zum Bild der Spirale mit Eilgängen rundum): „man kann ja auch einfach
# zurück drehen für so eine Fläche“. Jede Zeile liegt bei festem a und fährt nur über ihre
# Stücke im Bereich; am Ende geht es in der Tiefe einen Schritt längs zur nächsten Zeile und
# die Rundachse dreht zurück. Abgehoben wird nur, wo die nächste Zeile nicht dort weitergeht.


def _zeilen(bereich, a_von, a_bis, abstand, ringe=()):
    """Die Stellen längs der Zeilen im Bereich, von vorn nach hinten: gleich weit auseinander,
    höchstens `abstand`, die erste an seinem vorderen, die letzte an seinem hinteren Ende –
    nur zwischen a_von und a_bis; dazu die Ringe vor den Wänden (`ringe`)."""
    belegt = bereich.drin.any(axis=1)
    if not belegt.any():
        return np.zeros(0)
    oben = min(float(bereich.a[belegt].max()), a_bis)
    unten = max(float(bereich.a[belegt].min()), a_von)
    if oben < unten - GLEICH:
        return np.zeros(0)
    anzahl = max(1, int(math.ceil((oben - unten) / abstand - 1e-9)))
    stellen = list(oben - (oben - unten) * np.arange(anzahl + 1) / anzahl)
    stellen += [ring for ring in ringe if unten - GLEICH <= ring <= oben + GLEICH]
    ergebnis = []
    for stelle in sorted(stellen, reverse=True):
        if not ergebnis or ergebnis[-1] - stelle > 1e-6:
            ergebnis.append(stelle)
    return np.array(ergebnis)


def _bereiche(drin):
    """Die Stücke einer Zeile im Bereich: [(Anfang, Länge)] in Winkelschritten, nach dem Anfang
    geordnet; ein Stück über die Naht bei 0° reicht über das Ende hinaus; rundum [(0, N)]."""
    n = len(drin)
    if not drin.any():
        return []
    if drin.all():
        return [(0, n)]
    frei = int(np.flatnonzero(~drin)[0])  # die Stücke von einer Lücke aus gezählt
    gedreht = np.roll(drin, -frei)
    return sorted(((von + frei) % n, bis - von + 1) for von, bis in _stuecke(gedreht))


def _von_bis(von, bis):
    """Die Winkelschritte von `von` bis `bis`, beide dabei, in Schritten von ±1."""
    return np.arange(von, bis + (1 if bis >= von else -1), 1 if bis >= von else -1)


def _einzeln(drin, steigend, absteigend=False):
    """Die Fahrten für „nur im Gleichlauf“ (P-2026-10-02-24): jedes Stück jeder Zeile eine
    Fahrt für sich, alle in dieselbe Richtung (`steigend`: mit wachsenden Winkelschritten oder
    Stellen) – dazwischen hebt der Fräser ab und setzt am Anfang der nächsten neu ein. Die
    Zeilen der Reihe nach, `absteigend` von der letzten an. `drin` wie bei _fahrten()."""
    fahrten = []
    zeilen = range(drin.shape[0] - 1, -1, -1) if absteigend else range(drin.shape[0])
    n = drin.shape[1]
    for m in zeilen:
        for anfang, laenge in _bereiche(drin[m]):
            if laenge >= n:  # rundum: einmal ganz herum, endet, wo er begann
                js = _von_bis(0, n) if steigend else _von_bis(0, -n)
            else:
                letzte = anfang + laenge - 1
                js = _von_bis(anfang, letzte) if steigend else _von_bis(letzte, anfang)
            fahrten.append([("zeile", m, js)])
    return fahrten


def _fahrten(drin):
    """Wie die Zeilen hin und her gefahren werden: [[Teil, …], …] – je Fahrt, was ohne Abheben
    am Stück geht. Ein Teil ist ("zeile", m, js): Zeile m über die Winkelschritte js
    (fortlaufend), oder ("schritt", m, j): von Zeile m zur nächsten beim Winkelschritt j. Die
    Richtung wechselt von Zeile zu Zeile. `drin`: (Zeilen, N) – wo gefräst wird. Getrennte
    Stücke des Bereichs (zwei Abflachungen) fährt es nacheinander ganz – so hebt der Fräser nur
    zwischen ihnen ab, nicht in jeder Zeile."""
    ergebnis = []
    for teil in _zusammenhaengend(drin):
        ergebnis += _fahrten_eines(teil)
    return ergebnis


def _zwischen(v_zeilen, radius):
    """Die Prüfzeilen zwischen den Zeilen: (v, je die Nummer der Zeile davor) – nur, wo ein
    Hindernis zwischen zwei Zeilen tiefer als ZWISCHEN_GENAU unentdeckt bliebe, so dicht,
    dass es auch zwischen den Prüfzeilen nicht mehr ist."""
    dicht = math.sqrt(8.0 * radius * ZWISCHEN_GENAU)
    werte, von = [], []
    for m in range(len(v_zeilen) - 1):
        luecke = abs(float(v_zeilen[m + 1]) - float(v_zeilen[m]))
        if luecke * luecke <= 8.0 * radius * ZWISCHEN_GENAU:
            continue
        anzahl = int(math.ceil(luecke / dicht - 1e-9))
        for i in range(1, anzahl):
            werte.append(
                float(v_zeilen[m]) + (float(v_zeilen[m + 1]) - float(v_zeilen[m])) * i / anzahl
            )
            von.append(m)
    return np.array(werte), von


def _geteilt(fahrten, zwischen):
    """Die Fahrten, an jedem Schritt geteilt, der nicht frei ist (`zwischen`: (Zeilen − 1, N),
    zwischen Zeile m und m + 1 an der Stelle frei) – dort hebt der Fräser ab und setzt an der
    nächsten Zeile neu ein."""
    ergebnis = []
    for fahrt in fahrten:
        stueck = []
        for teil in fahrt:
            art, m, js = teil
            if art == "schritt" and not bool(zwischen[m, int(js) - 1]):
                if stueck:
                    ergebnis.append(stueck)
                stueck = []
                continue
            stueck.append(teil)
        if stueck:
            ergebnis.append(stueck)
    return ergebnis


def _zusammenhaengend(drin):
    """Die zusammenhängenden Stücke des Bereichs (Zeilen, N): je eins ein Feld wie `drin`, das
    nur sie hat – zusammen hängen Stücke benachbarter Zeilen, die sich rundum überlappen;
    geordnet nach ihrer ersten Zeile und ihrem ersten Winkel."""
    anzahl, n = drin.shape
    stuecke = [_bereiche(drin[m]) for m in range(anzahl)]
    eltern = {(m, k): (m, k) for m in range(anzahl) for k in range(len(stuecke[m]))}

    def wurzel(x):
        while eltern[x] != x:
            eltern[x] = eltern[eltern[x]]
            x = eltern[x]
        return x

    for m in range(1, anzahl):
        for k, (anfang, laenge) in enumerate(stuecke[m]):
            for k0, (anfang0, laenge0) in enumerate(stuecke[m - 1]):
                if (anfang0 - anfang) % n < laenge or (anfang - anfang0) % n < laenge0:
                    eltern[wurzel((m, k))] = wurzel((m - 1, k0))
    gruppen = {}
    for schluessel in sorted(eltern):
        gruppen.setdefault(wurzel(schluessel), []).append(schluessel)
    ergebnis = []
    for mitglieder in sorted(gruppen.values()):
        feld = np.zeros(drin.shape, dtype=bool)
        for m, k in mitglieder:
            anfang, laenge = stuecke[m][k]
            feld[m, (anfang + np.arange(laenge)) % n] = True
        ergebnis.append(feld)
    return ergebnis


def _fahrten_eines(drin):
    """_fahrten() für ein zusammenhängendes Stück des Bereichs."""
    anzahl, n = drin.shape
    fahrten, fahrt, ende, richtung = [], None, 0, 1
    for m in range(anzahl):
        stuecke = _bereiche(drin[m])
        if not stuecke:
            if fahrt:
                fahrten.append(fahrt)
            fahrt = None
        for nummer, (anfang, laenge) in enumerate(stuecke[::richtung]):
            teile = None
            if nummer == 0 and fahrt:
                teile = _anschluss(drin[m - 1], ende, anfang, laenge, richtung, m, n)
            if teile is None:
                if fahrt:
                    fahrten.append(fahrt)
                if laenge >= n:  # rundum
                    js = _von_bis(0, richtung * n)
                else:
                    letzte = anfang + laenge - 1
                    js = _von_bis(anfang, letzte) if richtung > 0 else _von_bis(letzte, anfang)
                fahrt = [("zeile", m, js)]
            else:
                fahrt.extend(teile)
            ende = int(fahrt[-1][2][-1])
        richtung = -richtung
    if fahrt:
        fahrten.append(fahrt)
    return fahrten


def _anschluss(davor, ende, anfang, laenge, richtung, m, n):
    """Die Teile, mit denen es in der Tiefe von Zeile m − 1 (endet beim Winkelschritt `ende`,
    `davor`: wo sie im Bereich ist) in Zeile m weitergeht, die über das Stück (anfang, laenge)
    in `richtung` fährt – oder None, wenn es nicht geht: dann hebt der Fräser ab. Liegt das
    Ende über dem Stück, geht es dort hinüber, fährt das Stück erst bis zu seinem Anfang und
    dann ganz; sonst zurück auf der alten Zeile bis über den Anfang des Stücks."""
    if laenge >= n:  # rundum: gleich hinüber und einmal herum
        return [("schritt", m - 1, ende), ("zeile", m, _von_bis(ende, ende + richtung * n))]
    anfang_ = anfang if richtung > 0 else anfang + laenge - 1  # wo das Stück beginnt
    darin = (ende - anfang) % n < laenge
    if darin:  # hinüber, bis zum Anfang des Stücks, dann ganz hindurch
        weit = ((ende - anfang_) * richtung) % n
        start = ende - richtung * weit
        teile = [("schritt", m - 1, ende)]
        if start != ende:
            teile.append(("zeile", m, _von_bis(ende, start)))
    else:  # auf der alten Zeile zurück bis über den Anfang – sie muss dort im Bereich sein
        weit = ((anfang_ - ende) * richtung) % n
        start = ende + richtung * weit
        zurueck = _von_bis(ende, start)
        if not davor[zurueck % n].all():
            return None
        teile = [("zeile", m - 1, zurueck), ("schritt", m - 1, start)]
    return teile + [("zeile", m, _von_bis(start, start + richtung * (laenge - 1)))]


def _folge(fahrt, zeilen_a, hoehe, schritt_hoehe, schritt_laengs=vh.SCHRITT_A):
    """Die Punkte einer Fahrt: (a, r, j, m) – j fortlaufende Winkelschritte, m die Zeile (−1
    auf dem Weg zwischen zwei Zeilen). `hoehe`: (Zeilen, N) die Tiefe auf den Zeilen;
    `schritt_hoehe(m, j, stellen)`: die Tiefe auf dem Weg von Zeile m zur nächsten."""
    n = hoehe.shape[1]
    teile = []
    for art, m, js in fahrt:
        if art == "zeile":
            teile.append((np.full(len(js), zeilen_a[m]), hoehe[m, js % n], js, np.full(len(js), m)))
            continue
        von, bis = zeilen_a[m], zeilen_a[m + 1]
        anzahl = max(1, int(math.ceil(abs(von - bis) / schritt_laengs - 1e-9)))
        stellen = von + (bis - von) * np.arange(1, anzahl) / anzahl
        if len(stellen):
            tiefe = schritt_hoehe(m, int(js), stellen)
            teile.append((stellen, tiefe, np.full(len(stellen), js), np.full(len(stellen), -1)))
    return tuple(np.concatenate([t[i] for t in teile]) for i in range(4))


def _winkel(j, schritt_phi, jetzt):
    """Die Winkel (Grad) der Winkelschritte j – um ganze Umdrehungen so verschoben, dass der
    erste dem jetzigen Winkel der Rundachse am nächsten liegt."""
    phi = j * schritt_phi
    return phi + 360.0 * round((jetzt - float(phi[0])) / 360.0)


def _einfahrt(punkte, a, r, phi, oben, offen, w):
    """Über den Anfang der Fahrt, im Eilgang bis knapp über `oben` (höher steht dort nichts),
    hinein: senkrecht mit dem Eintauchvorschub, wo es `offen` ist, nichts zu fräsen ist oder
    die ganze Fahrt für eine Rampe zu kurz ist – sonst über die Rampe längs der Fahrt (auch
    über den Schritt zur nächsten Zeile, wenn die erste kurz ist)."""
    sicher = w.stange_radius + w.sicherheit
    a0, r0, p0 = float(a[0]), float(r[0]), float(phi[0])
    _eilgang(punkte, a0, sicher, p0)
    knapp = min(sicher, oben + w.sicherheit)
    if knapp < sicher:
        punkte.append(Punkt(True, a0, knapp, p0))
    rampe = getattr(w, "eintauchwinkel", None) is not None and not offen and r0 < oben - GLEICH
    if rampe and _laenge(a, r, phi, 0, len(a) - 1) >= RAMPE_MINDESTENS:
        punkte.append(Punkt(False, a0, oben, p0, True))  # bis ans Material
        punkte.extend(Punkt(False, *stelle) for stelle in _rampe(a, r, phi, 0, len(a) - 1, oben, w))
    else:
        punkte.append(Punkt(False, a0, r0, p0, True))


def _schruppen_zeilen(punkte, zeilen_a, boden, boden_bei, lagen, w, schritt_phi):
    """Die Lagen, wenn nur im Bereich gefräst wird (V4): Zeilen hin und her (_fahrten), jede Lage
    auf denselben Stellen – so steht über jeder höchstens die Tiefe der Lage davor. `boden`:
    (Zeilen, N) wie tief die Spitze darf, `boden_bei(stellen, j)` dasselbe dazwischen. Senkrecht
    hinein geht es, wo die Zeile davor (höchstens einen Fräserradius weiter vorn) in dieser Lage
    schon fräste, sonst über die Rampe."""
    if not len(zeilen_a):
        return
    n = boden.shape[1]
    phi_werte = np.radians(schritt_phi * np.arange(n))
    drin = w.bereich.bei(zeilen_a[:, None], phi_werte[None, :])
    if w.nur_gleichlauf:
        # Jede Zeile für sich, der Winkel so, dass das Material – bei der nächsten Zeile längs –
        # für den Gleichlauf auf der richtigen Seite liegt (P-2026-10-02-26).
        vor = 1.0 if len(zeilen_a) > 1 and zeilen_a[1] > zeilen_a[0] else -1.0
        steigend = sp.ist_gleichlauf((-1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, vor))
        fahrten = _einzeln(drin, steigend == bool(w.gleichlauf))
    else:
        fahrten = _fahrten(drin)
    sicher = w.stange_radius + w.sicherheit
    abstand = int(round(HOECHSTENS_GRAD / schritt_phi))
    spiel = schrupp_spiel(w.aufmass)
    nah = np.concatenate([[False], np.diff(-zeilen_a) <= w.fraeser_radius + GLEICH])
    davor = np.full(boden.shape, float(w.stange_radius))
    for lage in range(1, lagen + 1):
        ebene = w.stange_radius - lage * w.zustellung
        hoehe = np.maximum(boden, ebene)
        gefraest = np.zeros(boden.shape, dtype=bool)

        def schritt_hoehe(_m, j, stellen, ebene=ebene):
            return np.maximum(boden_bei(stellen, j % n), ebene)

        for fahrt in fahrten:
            a, r, j, m = _folge(fahrt, zeilen_a, hoehe, schritt_hoehe)
            phi = _winkel(j, schritt_phi, punkte[-1].phi)
            m0, j0 = fahrt[0][1], int(j[0]) % n
            offen = nah[m0] and gefraest[m0 - 1, j0]
            _einfahrt(punkte, a, r, phi, davor[m0, j0], offen, w)
            # Zusammengefasst mit dem Spiel wie die Spirale rundum; fest bleibt, wo a knickt
            # (ein Ring beginnt oder endet) und wo die Rundachse umkehrt (phi, hin und her).
            fest = (
                (np.flatnonzero(_a_knicke(a) | _a_knicke(phi)) + 1).tolist() if len(a) > 2 else []
            )
            bleibt = _zusammengefasst(r, max(BAHN_TOLERANZ, spiel), abstand, fest, innen=spiel)
            for i, r_i in zip(bleibt, _gehoben(r, bleibt), strict=True):
                punkte.append(Punkt(False, float(a[i]), r_i, float(phi[i])))
            punkte.append(Punkt(True, float(a[-1]), sicher, float(phi[-1])))
            auf_zeile = m >= 0
            gefraest[m[auf_zeile], j[auf_zeile] % n] = True
        davor = hoehe


def _schlichten_zeilen(
    netz, laengs, radial, w, a_anfang, a_ende, teil_vorne, teil_hinten, hinten_frei, schritt_phi
):
    """Schlichten nur im Bereich (V4): Zeilen im Abstand der Schrittweite hin und her
    (_fahrten), die Spitze auf der Hüllfläche genau an den Stellen der Zeilen, vor den Wänden
    eine Zeile als Ring; hinein senkrecht mit dem Eintauchvorschub, knapp über dem Rest."""
    form = w.form
    radius = form.radius
    s = w.schrittweite
    zugabe = w.aufmass + netz.toleranz
    geformt = form.mit_aufmass(zugabe)
    phi = vh.raster_phi(schritt_phi)
    n = len(phi)
    sicher = w.stange_radius + w.sicherheit
    abstand = int(round(HOECHSTENS_GRAD / schritt_phi))
    punkte = [Punkt(True, a_anfang, sicher, 0.0)]
    ringe = _ringe(w.waende, radius + zugabe + RING_LUFT, a_ende, a_anfang)
    gleichmaessig = _zeilen(w.bereich, a_ende, a_anfang, s)
    if not len(gleichmaessig):
        punkte.append(Punkt(True, a_anfang, sicher, 0.0))
        return Schlichtbahn(punkte, 0.0, 0.0, form.kammhoehe(s), hinten_frei)
    # Die gleichmäßigen Zeilen auf einmal (aufsteigend gerechnet), die Ringe je für sich.
    unten = float(gleichmaessig[-1])
    weite = (
        (float(gleichmaessig[0]) - unten) / (len(gleichmaessig) - 1)
        if len(gleichmaessig) > 1
        else s
    )
    anfang = np.full(n, unten)
    huelle = vh.je_winkel(netz, laengs, radial, geformt, anfang, weite, len(gleichmaessig), phi)
    huelle = _auffuellen(huelle, anfang, weite, teil_vorne, teil_hinten)[::-1] + zugabe
    zeilen = dict(zip(gleichmaessig.tolist(), huelle, strict=True))
    for ring in ringe:
        if unten - GLEICH <= ring <= gleichmaessig[0] + GLEICH:
            zeile = vh.je_winkel(netz, laengs, radial, geformt, np.full(n, ring), s, 1, phi)[0]
            zeilen[ring] = zeile + zugabe
    zeilen_a = np.array(sorted(zeilen, reverse=True))
    zeilen_a = zeilen_a[np.concatenate([[True], np.diff(-zeilen_a) > 1e-6])]
    hoehe = np.array([zeilen[z] for z in zeilen_a.tolist()])
    hoehe = np.maximum(np.where(np.isfinite(hoehe), hoehe, w.stange_radius), radius)
    drin = w.bereich.bei(zeilen_a[:, None], phi[None, :])

    def schritt_hoehe(m, j, stellen, ebene=None):
        """Die Hüllfläche genau auf dem Weg von Zeile m zur nächsten beim Winkelschritt j –
        vor und hinter dem Teil die höhere der beiden Zeilen."""
        wert = vh.je_winkel(
            netz,
            laengs,
            radial,
            geformt,
            np.array([stellen[-1]]),
            float(stellen[0] - stellen[1]) if len(stellen) > 1 else 1.0,
            len(stellen),
            phi[[j % n]],
        )[::-1, 0]
        daneben = max(hoehe[m, j % n], hoehe[m + 1, j % n])
        wert = np.where(np.isfinite(wert), wert + zugabe, daneben)
        if ebene is not None:
            wert = np.maximum(wert, np.maximum(ebene[m, j % n], ebene[m + 1, j % n]))
        return np.maximum(wert, radius)

    umdrehungen = 0.0

    def fahren(ziel, wo, stand, ebene=None):
        """Die Zeilen über `wo` auf der Tiefe `ziel`; `stand`: so hoch steht dort noch etwas.
        Gibt zurück, wo gefräst wurde."""
        nonlocal umdrehungen
        gefraest = np.zeros(ziel.shape, dtype=bool)
        fahrten, jetzt = [], punkte[-1].phi
        for fahrt in _fahrten(wo):
            a, r, j, m = _folge(
                fahrt, zeilen_a, ziel, lambda mm, jj, st: schritt_hoehe(mm, jj, st, ebene)
            )
            winkel = _winkel(j, schritt_phi, jetzt)
            jetzt = float(winkel[-1])
            m0, j0 = fahrt[0][1], int(j[0]) % n
            oben = w.stange_radius if stand is None else max(float(stand[m0, j0]), float(r[0]))
            fahrten.append((a, r, winkel, oben))
            auf_zeile = m >= 0
            gefraest[m[auf_zeile], j[auf_zeile] % n] = True
            umdrehungen += float(np.sum(np.abs(np.diff(winkel)))) / 360.0
        fein = _verfeinert_je_fahrt(
            netz, laengs, radial, form, w, fahrten, teil_hinten, teil_vorne, radius
        )
        for (a, r, winkel, t), (*_, oben) in zip(fein, fahrten, strict=True):
            _einfahrt(punkte, a, r, winkel, oben, True, w)
            gehoben = r + _sehnenfehler(r, t)
            knicke = _a_knicke(a, t) | _a_knicke(winkel, t) if len(a) > 2 else []
            fest = np.flatnonzero(knicke) + 1
            for i in _zusammengefasst(gehoben, BAHN_TOLERANZ, abstand, list(fest), t):
                punkte.append(Punkt(False, float(a[i]), float(gehoben[i]), float(winkel[i])))
            punkte.append(Punkt(True, float(a[-1]), sicher, float(winkel[-1])))
        return gefraest

    # Nach dem Schruppen: so hoch steht noch etwas (für die Einfahrt), und wie viel über der
    # Zeile höchstens – das nimmt sie in einem Zug.
    stand, rest_ueber = None, 0.0
    if w.rest is not None:
        gitter_a = np.repeat(zeilen_a, n)
        gitter_phi = np.tile(phi, len(zeilen_a))
        oben = _nicht_tiefer(w.rest, form, 0.0, gitter_a, gitter_phi).reshape(hoehe.shape)
        stand = np.maximum(oben, hoehe)
        rest_ueber = max(0.0, float(np.max(np.where(drin, oben - hoehe, 0.0))))
    fahren(hoehe, drin, stand)
    _eilgang(punkte, a_anfang, sicher, punkte[-1].phi)
    r_min = float(np.min(hoehe[drin])) if drin.any() else 0.0
    return Schlichtbahn(punkte, umdrehungen, r_min, form.kammhoehe(s), hinten_frei, rest_ueber)


def schlichten(netz, laengs, radial, werte, schritt_phi=SCHRITT_PHI_SCHLICHTEN):
    """Die Schlichtbahn (Schlichtbahn) für `netz` (vierachs_huelle.vernetze, im Job, fein:
    TOLERANZ_SCHLICHTEN) mit den Schlichtwerten `werte`; `laengs` und `radial` wie in
    vierachs_huelle.

    ValueError, wenn die Werte nicht gehen – mit einem Satz für den Menschen.
    """
    w = werte
    form = w.form
    radius = form.radius
    if radius <= 0 or w.schrittweite <= 0:
        raise ValueError(tr("vb.fehler.schrittweite"))
    if w.schrittweite > 2 * radius:
        raise ValueError(tr("vb.fehler.schrittweite_gross"))
    if w.muster not in MUSTER:
        raise ValueError(tr("vb.fehler.muster", muster=w.muster))
    l_, _u, _v = vh.rahmen(laengs, radial)
    a_teil = netz.punkte @ l_
    teil_vorne, teil_hinten = float(a_teil.max()), float(a_teil.min())
    ueberlauf = ueberlauf_vorschlag(radius) if w.ueberlauf is None else w.ueberlauf
    a_anfang = w.a_stange_vorne + radius + w.sicherheit
    a_ende = _ende(teil_hinten, ueberlauf, radius, w)
    if a_ende >= teil_vorne + radius:
        raise ValueError(_kein_platz(radius, w))
    hinten_frei = max(0.0, a_ende - radius - teil_hinten)
    if w.muster == LINIEN:  # Linien längs (V4c)
        return _schlichten_linien(
            netz, laengs, radial, w, a_anfang, a_ende, teil_vorne, teil_hinten, hinten_frei
        )
    if w.bereich is not None:  # gewählte Flächen: Zeilen hin und her (V4)
        return _schlichten_zeilen(
            netz,
            laengs,
            radial,
            w,
            a_anfang,
            a_ende,
            teil_vorne,
            teil_hinten,
            hinten_frei,
            schritt_phi,
        )

    s = w.schrittweite
    quer = bool(w.querachse)
    # Mit der Querachse plant eine Kugel mit dem Radius des Fräsers (vierachs_quer) – die Spirale
    # des Fräsers selbst braucht es dann nicht.
    plan = w if not quer or form.nur_kugel else replace(w, form=ff.kugel(radius))
    spirale = _spirale_rechnen(
        netz, laengs, radial, plan, s, a_anfang, a_ende, teil_vorne, teil_hinten, schritt_phi
    )
    a, r, winkel, anzahl, je_umdrehung, drehung = spirale
    # Eine Spirale, von vorne nach hinten, mit der Schrittweite – was das Schruppen stehen
    # ließ, nimmt sie in einem Zug (rest_ueber sagt, wie viel das höchstens ist).
    sicher = w.stange_radius + w.sicherheit
    abstand = int(round(HOECHSTENS_GRAD / schritt_phi))
    punkte = [Punkt(True, a_anfang, sicher, 0.0)]
    rest_ueber = _rest_ueber(w, form, r, a, np.radians(winkel))
    if quer:
        # Der Plan von der Kugel, die Stellungen und die Höhe der Spitze aus der Hüllfläche des
        # Fräsers (vierachs_quer).
        zugabe = w.aufmass + netz.toleranz

        def umrechnen(a_p, x_p, q_p, psi_p):
            return vq.stellungen(
                netz, laengs, radial, form, zugabe, a_p, x_p, q_p, psi_p, teil_hinten, teil_vorne
            )

        r_min = _spirale_quer(
            punkte,
            a,
            r,
            winkel,
            sicher,
            abstand,
            drehung,
            radius,
            schritt_phi,
            umrechnen,
            form.nur_kugel,
            w.anstellen if form.nur_kugel else 0.0,
        )
    else:
        a, r, winkel, t, _ = _verfeinert(
            netz, laengs, radial, form, w, a, r, winkel, teil_hinten, teil_vorne
        )
        frei = _frei(a, r, winkel, r >= _material_oben(w, form, a, winkel) - LEER)
        _spirale(punkte, a, r, winkel, 0, len(a) - 1, sicher, abstand, drehung, t, frei)
        r_min = float(np.min(r))
    punkte.append(Punkt(True, a_anfang, sicher, punkte[-1].phi))
    return Schlichtbahn(
        punkte,
        anzahl / je_umdrehung,
        r_min,
        form.kammhoehe(s),
        hinten_frei,
        rest_ueber,
        querachse=quer,
    )


def _material_oben(w, form, a, winkel):
    """Wie hoch die Spitze an den Punkten (a, Winkel in Grad) stehen muss, damit der Fräser das
    Material vor dem Schlichten gerade berührt: der Rest nach dem Schruppen (_nicht_tiefer),
    ohne ihn – und außerhalb seines Rasters – die Stange."""
    a = np.asarray(a, dtype=float)
    if w.rest is None:
        return np.full(len(a), float(w.stange_radius))
    oben = _nicht_tiefer(w.rest, form, 0.0, a, np.radians(np.asarray(winkel, dtype=float)))
    return np.where(np.isfinite(oben), oben, float(w.stange_radius))


def _rest_ueber(w, form, r, a, phi):
    """So viel steht nach dem Schruppen höchstens über der Spitze an den Stellen (a, φ in rad)
    der Bahn mit den Radien `r` (mm) – 0 ohne Rest."""
    if w.rest is None:
        return 0.0
    oben = _nicht_tiefer(w.rest, form, 0.0, np.asarray(a, dtype=float), np.asarray(phi))
    oben = np.where(np.isfinite(oben), oben, -math.inf)
    return max(0.0, float(np.max(oben - r)))


def _spirale_rechnen(
    netz, laengs, radial, w, s, a_anfang, a_ende, teil_vorne, teil_hinten, schritt_phi
):
    """Die Spirale mit der Steigung `s` von a_anfang bis a_ende: Punkt k liegt bei a_anfang −
    s · k / N unter dem Winkel k · Δφ; je Winkel j kommt sie an a_anfang − s · (j / N + m)
    vorbei – dort rechnet die Hüllfläche, mit Aufmaß, vor und hinter dem Teil aufgefüllt, vor
    jeder Wand ein Ringgang. Gibt (a, r, Winkel in Grad, Anzahl, Punkte je Umdrehung, Drehung)
    zurück."""
    form = w.form
    radius = form.radius
    phi = vh.raster_phi(schritt_phi)
    je_umdrehung = len(phi)
    anzahl = int(math.ceil((a_anfang - a_ende) / s * je_umdrehung - 1e-9))
    umdrehungen = int(math.ceil(anzahl / je_umdrehung))
    zugabe = w.aufmass + netz.toleranz  # das Netz liegt bis zu seiner Toleranz innen
    # Mit fallendem Winkel (drehung −1) kommt die Spirale am Winkel j vorbei, wo k ≡ −j.
    drehung = _drehung(a_anfang, a_ende, w.gleichlauf)
    erster = (drehung * np.arange(je_umdrehung)) % je_umdrehung
    anfang_je_winkel = a_anfang - s * (erster / je_umdrehung + umdrehungen)
    huelle = vh.je_winkel(
        netz,
        laengs,
        radial,
        form.mit_aufmass(zugabe),
        anfang_je_winkel,
        s,
        umdrehungen + 1,
        phi,
    )
    huelle = _auffuellen(huelle, anfang_je_winkel, s, teil_vorne, teil_hinten) + zugabe
    k = np.arange(anzahl + 1)
    a = a_anfang - s * k / je_umdrehung
    r = huelle[umdrehungen - k // je_umdrehung, (drehung * k) % je_umdrehung]
    # Vor jeder Wand hält die Spirale eine Umdrehung an (Ringgang, D-42) – die Hüllfläche
    # dort genau an dieser Stelle gerechnet; so weit vor der Wand, dass der um Aufmaß und
    # Vernetzung größere Fräser sie nicht streift.
    ringe = _ringe(w.waende, radius + zugabe + RING_LUFT, a_ende, a_anfang, ende=True)
    a, k, herkunft = _mit_ringen(a, ringe, je_umdrehung)
    ring_r = [
        vh.je_winkel(
            netz,
            laengs,
            radial,
            form.mit_aufmass(zugabe),
            np.full(je_umdrehung, stelle),
            s,
            1,
            phi,
        )[0]
        + zugabe
        for stelle in ringe
    ]
    # Ein Ring hinter dem Teil (der am Ende): die Tiefe am Teilende je Winkel, wie die Spirale
    # dort (_auffuellen: ihre hinterste Zeile) – nicht die Stange, und nicht die Kugel hinter
    # der Kante hinab (die Kerbe aus P-2026-10-03-08).
    ring_r = [
        zeile if stelle >= teil_hinten else np.where(np.isfinite(huelle[0]), huelle[0], zeile)
        for stelle, zeile in zip(ringe, ring_r, strict=True)
    ]
    r = _ring_radien(r, herkunft, drehung * k, ring_r, je_umdrehung)
    anzahl = len(a) - 1
    r = np.where(np.isfinite(r), r, w.stange_radius)  # trifft rundum nichts: bleibt oben
    r = np.maximum(r, w.r_tiefste)
    winkel = drehung * k * schritt_phi
    return a, r, winkel, anzahl, je_umdrehung, drehung


# --- Linien längs (V4c) ---------------------------------------------------------------------
# Manuel (2026-09-30): „mehrere Strategien, je nach Werkzeug kann das anders ausfallen“. Jede
# Linie liegt bei festem Winkel und fährt längs über ihre Stücke im Bereich; am Ende dreht die
# Rundachse in der Tiefe zur nächsten Linie, die Richtung wechselt. Die Fahrten kommen von
# _fahrten() wie beim Hin und Her – nur mit Linie statt Zeile und Stelle längs statt
# Winkelschritt; längs gibt es keine Naht, deshalb rechnet es mit einer Lücke an beiden Enden.


def linienwinkel(r_max, schrittweite):
    """Die Winkel (Grad) der Linien längs: rundum gleich weit auseinander, höchstens
    `schrittweite` ÷ `r_max` weit (im Bogenmaß) – so bleibt zwischen zwei Linien auf dem
    größten Radius nicht mehr stehen als zwischen zwei Umdrehungen der Spirale."""
    anzahl = max(1, int(math.ceil(2.0 * math.pi * max(r_max, GLEICH) / schrittweite - 1e-9)))
    return 360.0 * np.arange(anzahl) / anzahl


def _schlichten_linien(
    netz, laengs, radial, w, a_anfang, a_ende, teil_vorne, teil_hinten, hinten_frei
):
    """Schlichten in Linien längs (Muster LINIEN): die Spitze auf der Hüllfläche genau auf den
    Linien, alle SCHRITT_A_LINIEN ein Punkt; mit Bereich nur die Linien und Stücke darüber;
    hinein senkrecht mit dem Eintauchvorschub, knapp über dem Rest."""
    form = w.form
    radius = form.radius
    s = w.schrittweite
    zugabe = w.aufmass + netz.toleranz
    geformt = form.mit_aufmass(zugabe)
    sicher = w.stange_radius + w.sicherheit
    punkte = [Punkt(True, a_anfang, sicher, 0.0)]
    # Die Linien: im Winkelabstand s ÷ r_max – r_max der größte Radius des Teils plus Aufmaß.
    _l, u_, v_ = vh.rahmen(laengs, radial)
    r_teil = np.hypot(netz.punkte @ u_, netz.punkte @ v_)
    r_max = max(float(r_teil.max()) + zugabe if len(r_teil) else 0.0, radius)
    winkel = linienwinkel(r_max, s)
    phi = np.radians(winkel)
    # Die Stellen längs: von hinten nach vorn, höchstens SCHRITT_A_LINIEN auseinander.
    anzahl = max(2, int(math.ceil((a_anfang - a_ende) / SCHRITT_A_LINIEN - 1e-9)) + 1)
    a_stellen = np.linspace(a_ende, a_anfang, anzahl)
    schritt = float(a_stellen[1] - a_stellen[0])
    # Wo gefräst wird: über dem Bereich, ohne Bereich überall. Linien ohne Stück bleiben als
    # Lücke stehen – so hängen nur Nachbarn zusammen; die Reihe beginnt nach einer Lücke, damit
    # ein Stück über die Naht bei 0° ein Stück bleibt.
    if w.bereich is not None:
        drin = w.bereich.bei(a_stellen[None, :], phi[:, None])
    else:
        drin = np.ones((len(winkel), anzahl), dtype=bool)
    belegt = drin.any(axis=1)
    if not belegt.any():
        punkte.append(Punkt(True, a_anfang, sicher, 0.0))
        return Schlichtbahn(punkte, 0.0, 0.0, form.kammhoehe(s), hinten_frei)
    if not belegt.all():
        reihe = (np.arange(len(winkel)) + int(np.flatnonzero(~belegt)[0])) % len(winkel)
        winkel, phi, drin, belegt = winkel[reihe], phi[reihe], drin[reihe], belegt[reihe]
    n = len(winkel)
    # Die Hüllfläche nur auf den Linien, über denen etwas liegt.
    huelle = vh.je_winkel(
        netz,
        laengs,
        radial,
        geformt,
        np.full(int(belegt.sum()), a_ende),
        schritt,
        anzahl,
        phi[belegt],
    )
    anfang = np.full(int(belegt.sum()), a_ende)
    huelle = _auffuellen(huelle, anfang, schritt, teil_vorne, teil_hinten).T + zugabe
    hoehe = np.full((n, anzahl), float(w.stange_radius))
    hoehe[belegt] = np.where(np.isfinite(huelle), huelle, w.stange_radius)
    hoehe = np.maximum(hoehe, radius)

    def folge(fahrt, ziel):
        """Die Punkte einer Fahrt: (a, r, Winkel in Grad, Linie, Stelle) – Linie und Stelle −1
        auf der Drehung zur nächsten Linie, in der Tiefe der höheren von beiden."""
        teile = []
        for art, m, js in fahrt:
            if art == "zeile":
                k = np.asarray(js) - 1  # ohne die Lücke am Anfang
                teile.append(
                    (a_stellen[k], ziel[m, k], np.full(len(k), winkel[m]), np.full(len(k), m), k)
                )
                continue
            k = int(js) - 1
            r = max(float(ziel[m, k]), float(ziel[m + 1, k]))
            teile.append(
                (
                    a_stellen[[k]],
                    np.array([r]),
                    np.array([winkel[m + 1]]),
                    np.array([-1]),
                    np.array([-1]),
                )
            )
        return tuple(np.concatenate([t[i] for t in teile]) for i in range(5))

    umdrehungen = 0.0

    def fahren(ziel, wo, stand):
        """Die Linien über `wo` auf der Tiefe `ziel`; `stand`: so hoch steht dort noch etwas.
        Gibt zurück, wo gefräst wurde."""
        nonlocal umdrehungen
        gefraest = np.zeros(ziel.shape, dtype=bool)
        mit_luecke = np.zeros((n, anzahl + 2), dtype=bool)
        mit_luecke[:, 1:-1] = wo
        if w.nur_gleichlauf:
            # Jede Linie für sich, längs so, dass das Material – bei der nächsten Linie, mit
            # wachsendem Winkel – für den Gleichlauf auf der richtigen Seite liegt.
            steigend = sp.ist_gleichlauf((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0))
            fahrten = _einzeln(mit_luecke, steigend == bool(w.gleichlauf))
        else:
            fahrten = _fahrten(mit_luecke)
        for fahrt in fahrten:
            a, r, grad, m, k = folge(fahrt, ziel)
            grad = np.degrees(np.unwrap(np.radians(grad)))  # über die Naht bei 0° hinweg
            grad = grad + 360.0 * round((punkte[-1].phi - float(grad[0])) / 360.0)
            m0, k0 = int(m[0]), int(k[0])
            oben = w.stange_radius if stand is None else max(float(stand[m0, k0]), float(r[0]))
            _einfahrt(punkte, a, r, grad, oben, True, w)
            gehoben = r + _sehnenfehler(r)
            fest = np.flatnonzero(_a_knicke(a) | _a_knicke(grad)) + 1 if len(a) > 2 else []
            for i in _zusammengefasst(gehoben, BAHN_TOLERANZ, len(a), list(fest)):
                punkte.append(Punkt(False, float(a[i]), float(gehoben[i]), float(grad[i])))
            punkte.append(Punkt(True, float(a[-1]), sicher, float(grad[-1])))
            auf_linie = m >= 0
            gefraest[m[auf_linie], k[auf_linie]] = True
            umdrehungen += float(np.sum(np.abs(np.diff(grad)))) / 360.0
        return gefraest

    # Nach dem Schruppen: so hoch steht noch etwas (für die Einfahrt), und wie viel über der
    # Linie höchstens – das nimmt sie in einem Zug.
    stand, rest_ueber = None, 0.0
    if w.rest is not None:
        gitter_a = np.tile(a_stellen, n)
        gitter_phi = np.repeat(phi, anzahl)
        oben = _nicht_tiefer(w.rest, form, 0.0, gitter_a, gitter_phi).reshape(hoehe.shape)
        stand = np.maximum(oben, hoehe)
        rest_ueber = max(0.0, float(np.max(np.where(drin, oben - hoehe, 0.0))))
    fahren(hoehe, drin, stand)
    _eilgang(punkte, a_anfang, sicher, punkte[-1].phi)
    r_min = float(np.min(hoehe[drin]))
    return Schlichtbahn(
        punkte,
        umdrehungen,
        r_min,
        form.kammhoehe(s),
        hinten_frei,
        rest_ueber,
        linien=int(belegt.sum()),
    )


def _verfeinert(
    netz, laengs, radial, form, w, a, r, winkel, teil_hinten, teil_vorne, stueck=None, unten=None
):
    """Die Spirale (a, r, Winkel) mit Zwischenpunkten, wo die Hüllfläche sich zwischen zwei
    Punkten um mehr als SEHNE_FEIN nach außen wölbt (geschätzt: ein Viertel dessen, was ein Punkt
    über der Sehne seiner Nachbarn liegt – bei gleichen Abständen die zweite Differenz / 8):
    dort 2, 4 … FEIN_HOECHSTENS Teilschritte, die Hüllfläche je Zwischenpunkt genau
    (vierachs_huelle.je_stellung); bis zu FEIN_DURCHGAENGE Mal, denn an einem Knick der
    Hüllfläche (die Stirn springt von einer Fläche auf eine Kante) bleibt nach einem Durchgang
    ein Rest. Gibt (a, r, Winkel, t, Stück) zurück – t die gebrochene Nummer je Punkt (für
    _spirale). `stueck`: je Punkt die Nummer der Fahrt (_verfeinert_je_fahrt) – Punkte zweier
    Fahrten sind keine Nachbarn; `unten`: tiefer nicht (ohne: Schlichtwerte.r_tiefste).
    Gefunden an Manuels Teil (P-2026-10-03-22): Von der Achse aus gesehen steigt die Hüllfläche
    an den Kanten seiner ebenen Seite um 3–4 mm je Grad und biegt dabei – die Gerade zwischen
    zwei Punkten 0,5° auseinander lag bis 0,22 mm (Kugel) und 0,38 mm (Schaftfräser) unter ihr,
    der Fräser schnitt ins Teil (der Sehnenfehler hebt höchstens SEHNE_HOECHSTENS)."""
    t = np.arange(len(r), dtype=float)
    stueck = np.zeros(len(r), dtype=np.int64) if stueck is None else np.asarray(stueck)
    unten = w.r_tiefste if unten is None else unten
    zugabe = w.aufmass + netz.toleranz
    geformt = form.mit_aufmass(zugabe)
    for _ in range(FEIN_DURCHGAENGE):
        if len(r) < 3:
            break
        anteil = (t[1:-1] - t[:-2]) / (t[2:] - t[:-2])
        ueber = np.zeros(len(r))
        ueber[1:-1] = r[1:-1] - (r[:-2] + anteil * (r[2:] - r[:-2]))
        innen = (stueck[:-2] == stueck[1:-1]) & (stueck[1:-1] == stueck[2:])
        ueber[1:-1] = np.where(innen, ueber[1:-1], 0.0)
        wolbung = np.maximum(ueber[:-1], ueber[1:]) / 4.0  # je Schritt i … i + 1
        weite = np.diff(t)
        noetig = np.isfinite(wolbung) & (wolbung > SEHNE_FEIN) & (weite > FEIN_KLEINSTER * 2)
        noetig &= stueck[:-1] == stueck[1:]
        if not noetig.any():
            break
        stufen = int(round(math.log2(FEIN_HOECHSTENS)))
        exponent = np.ceil(np.log2(np.sqrt(wolbung[noetig] / SEHNE_FEIN)))
        teile = (2 ** np.clip(exponent, 1, stufen)).astype(np.int64)
        schritte = np.flatnonzero(noetig)
        teile = np.minimum(
            teile, np.maximum(2, (weite[schritte] / FEIN_KLEINSTER).astype(np.int64))
        )
        je = teile - 1
        welcher = np.repeat(schritte, je)
        bruch = (np.arange(int(je.sum())) - np.repeat(np.cumsum(je) - je, je) + 1) / np.repeat(
            teile, je
        )
        a_z = a[welcher] + bruch * (a[welcher + 1] - a[welcher])
        winkel_z = winkel[welcher] + bruch * (winkel[welcher + 1] - winkel[welcher])
        t_z = t[welcher] + bruch * (t[welcher + 1] - t[welcher])
        # Die Richtung auf eine Umdrehung gebracht und gerundet: gleiche Richtungen rechnen
        # zusammen; davor und dahinter wie am Ende des Teils.
        richtung = np.radians(np.round(np.mod(winkel_z, 360.0), 6))
        stelle = np.clip(a_z, teil_hinten, teil_vorne)
        r_z = (
            vh.je_stellung(netz, laengs, radial, geformt, richtung, np.zeros(len(a_z)), stelle)
            + zugabe
        )
        r_z = np.where(np.isfinite(r_z), r_z, w.stange_radius)
        r_z = np.maximum(r_z, unten)
        t_alle = np.concatenate([t, t_z])
        ordnung = np.argsort(t_alle, kind="stable")
        a = np.concatenate([a, a_z])[ordnung]
        r = np.concatenate([r, r_z])[ordnung]
        winkel = np.concatenate([winkel, winkel_z])[ordnung]
        stueck = np.concatenate([stueck, stueck[welcher]])[ordnung]
        t = t_alle[ordnung]
    return a, r, winkel, t, stueck


def _verfeinert_je_fahrt(netz, laengs, radial, form, w, fahrten, teil_hinten, teil_vorne, unten):
    """_verfeinert für die Fahrten [(a, r, Winkel, …)] der Zeilen auf einmal – je Fahrt (a, r,
    Winkel, t). Dort lag die Gerade zwischen zwei Punkten genauso unter der Hüllfläche wie bei
    der Spirale, denn die Zeilen laufen über den Winkel: an Manuels Teil bis 0,19 mm (Kugel)
    und 0,30 mm (Schaftfräser), danach 0,002 mm (P-2026-10-03-24). Linien längs brauchen es
    nicht – längs ist die Gerade eine Gerade im Raum, dort lagen sie ohne schon 0,007 mm."""
    if not fahrten:
        return []
    stueck = np.repeat(np.arange(len(fahrten)), [len(f[0]) for f in fahrten])
    a, r, winkel = (np.concatenate([f[i] for f in fahrten]) for i in range(3))
    a, r, winkel, t, stueck = _verfeinert(
        netz, laengs, radial, form, w, a, r, winkel, teil_hinten, teil_vorne, stueck, unten
    )
    grenzen = np.flatnonzero(np.diff(stueck)) + 1
    return list(zip(*(np.split(x, grenzen) for x in (a, r, winkel, t)), strict=True))


def _spirale(punkte, a, r, winkel, von, bis, sicher, abstand, drehung=1, t=None, frei=None):
    """Hängt das Stück von..bis der Spirale an `punkte`: im Eilgang über den Anfang, hinein,
    die Spirale mit Sehnenfehler und zusammengefasst, radial hinaus. Der Winkel zählt weiter,
    wo die Rundachse steht – sie dreht nicht zurück (`drehung`: −1, wenn er fällt). `t`: mit
    Zwischenpunkten (_verfeinert) die gebrochene Nummer je Punkt; `frei` je Punkt (_frei): das
    Stück dorthin durchs Freie."""
    weiter = punkte[-1].phi
    if drehung > 0:
        versatz = 360.0 * math.ceil((weiter - winkel[von]) / 360.0 - 1e-9)
    else:
        versatz = -360.0 * math.ceil((winkel[von] - weiter) / 360.0 - 1e-9)
    stueck = r[von : bis + 1]
    teil_t = None if t is None else t[von : bis + 1]
    stueck = stueck + _sehnenfehler(stueck, teil_t)
    anfahren = Punkt(True, float(a[von]), sicher, float(winkel[von] + versatz))
    if anfahren != punkte[-1]:
        punkte.append(anfahren)
    ringe = np.flatnonzero(_a_knicke(a[von : bis + 1], teil_t)) + 1
    fest = ringe.tolist()
    teil_frei = None
    if frei is not None:
        teil_frei = np.asarray(frei[von : bis + 1], dtype=bool)
        fest += np.flatnonzero(teil_frei[:-1] != teil_frei[1:]).tolist()  # die Wechsel bleiben
    for i in _zusammengefasst(stueck, BAHN_TOLERANZ, abstand, sorted(set(fest)), teil_t):
        j = von + i
        punkte.append(
            Punkt(
                False,
                float(a[j]),
                float(stueck[i]),
                float(winkel[j] + versatz),
                frei=bool(teil_frei[i]) if teil_frei is not None and i > 0 else False,
            )
        )
    punkte.append(Punkt(True, float(a[bis]), sicher, float(winkel[bis] + versatz)))


def normale_quer(r, winkel, radius, a=None, neigung=0.0):
    """Die Spirale mit der Querachse (V5e): Je Punkt steht die Werkzeugachse längs der
    Normalen der Hüllfläche – im Querschnitt. Die Mitte der Kugel liegt auf dem Strahl φ im
    Abstand ρ = r + R von der Achse; die Normale der Kurve ρ(φ) hat den Winkel ψ = φ − β mit
    β = atan(ρ′ ÷ ρ). Steht das Werkzeug unter ψ zum Teil, liegt die Mitte quer um ρ · sin β
    neben seiner Achse und längs der Achse bei ρ · cos β – die Spitze um R darunter. Auf einem
    Zylinder ist β = 0 (ψ = φ, kein Versatz); auf einer ebenen Fläche in der Tiefe d ist
    ψ ihre Normale (die Rundachse hält), die Spitze steht bei d, der Versatz quer ist
    (d + R) · tan(φ − ψ) – die Gerade über die Fläche (Manuel, 2026-10-03: „die Drehung und
    X so, dass die lange Gerade exakt vom Winkel her zur Y-Achse steht, und dann mit der
    Y-Achse fahren, ohne C zu bewegen“). Gibt (ψ in Grad, Spitze längs der Werkzeugachse,
    Versatz quer) je Punkt zurück; `winkel` in Grad, fortlaufend; `a`: die Stellen längs –
    wo ein Ring beginnt oder endet, springt die Hüllfläche, dort wird nicht über die Grenze
    hinweg abgeleitet. `neigung` (Grad): Die Werkzeugachse steht so weit neben der Normalen –
    ψ = φ − β + Neigung, die Mitte quer um ρ · sin(β − Neigung); positiv zu wachsendem φ hin
    (die Kugel schneidet dann nicht mit der Spitze, ANSTELLEN_QUER)."""
    rho = np.asarray(r, dtype=float) + radius
    phi = np.radians(np.asarray(winkel, dtype=float))
    if len(rho) < 2:
        return np.asarray(winkel, dtype=float), np.asarray(r, dtype=float), np.zeros(len(rho))
    grenzen = [0, len(rho)]
    if a is not None and len(a) > 2:
        grenzen = [0] + (np.flatnonzero(_a_knicke(np.asarray(a, dtype=float))) + 1).tolist()
        grenzen = sorted(set(grenzen) | {len(rho)})
    beta = np.zeros(len(rho))
    for von, bis in zip(grenzen, grenzen[1:], strict=False):
        if bis - von < 2:
            continue
        steigung = _ableitung(rho[von:bis], phi[von:bis])
        stueck = np.where(
            rho[von:bis] > GLEICH, np.arctan2(steigung, np.maximum(rho[von:bis], GLEICH)), 0.0
        )
        # Geglättet über QUER_GLATT Punkte zu jeder Seite: Das Netz ist facettiert (0,005 mm),
        # die Normale einer Facettenkante springt um Zehntelgrad – die Rundachse liefe sonst bei
        # jeder Kante ein Stück zurück. Auf einer Ebene ist β gerade (bleibt), an einer
        # Innenecke verschmiert der Sprung über das Fenster – auch das ist eine gültige Stellung.
        if len(stueck) > 2 * QUER_GLATT + 1:
            kern = np.ones(2 * QUER_GLATT + 1) / (2 * QUER_GLATT + 1)
            innen = np.convolve(stueck, kern, mode="valid")
            stueck = np.concatenate([stueck[:QUER_GLATT], innen, stueck[-QUER_GLATT:]])
        beta[von:bis] = stueck
    # ψ muss nicht genau die Normale sein: Die Kugelmitte liegt für jedes ψ auf der
    # Hüllfläche (x + R und q sind ihre Lage im Rahmen unter ψ) – ψ bestimmt nur, wie das
    # Werkzeug dabei steht, und ob die Gerade über eine Ebene eine ist.
    beta = beta - math.radians(neigung)
    psi = np.degrees(phi - beta)
    return psi, rho * np.cos(beta) - radius, rho * np.sin(beta)


def _ableitung(werte, stellen):
    """dwerte/dstellen je Punkt: innen über vier Nachbarn (Fehler ~ h⁴ – mit zwei Nachbarn
    driftete ψ auf einer Ebene um Tausendstelgrad, und die Punkte fassten sich nicht zusammen),
    an den Rändern wie np.gradient."""
    ergebnis = np.gradient(werte, stellen)
    if len(werte) >= 5:
        h = stellen[3:-1] - stellen[1:-3]  # 2 h, wenn die Stellen gleich weit liegen
        ergebnis[2:-2] = (-werte[4:] + 8.0 * werte[3:-1] - 8.0 * werte[1:-3] + werte[:-4]) / (
            6.0 * h
        )
    return ergebnis


def _spirale_quer(
    punkte,
    a,
    r,
    winkel,
    sicher,
    abstand,
    drehung,
    radius,
    schritt_phi,
    umrechnen,
    kugel,
    anstellen=0.0,
):
    """Hängt die ganze Spirale mit der Querachse an `punkte` (_quer_plan, normale_quer): die
    Rundachse steht auf ψ, die Spitze bei x längs der Werkzeugachse, quer um q versetzt.
    `umrechnen`: (a, x, q, ψ) → (ψ, x, q) – die Stellungen des Fräsers mit der Höhe aus seiner
    Hüllfläche (vierachs_quer.stellungen); auch für die Kugel, denn ihre Zwischenstellungen
    (_uebergaenge) liegen nicht auf ihr. Geprüft wird der Weg der Kugelmitte (`kugel`) bzw. der
    Spitze. `anstellen`: die Kugel so viele Grad neben der Normalen (Schlichtwerte.anstellen).
    Gibt die tiefste Spitze zurück."""
    neigung = math.copysign(float(anstellen), drehung) if kugel else 0.0
    a_p, x_p, q_p, psi_p, fest, eingefuegt = _quer_plan(a, r, winkel, radius, schritt_phi, neigung)
    pruef_radius = radius if kugel else 0.0
    if not kugel or neigung:
        # Angestellt steht der Schaft der Kugel schräg: In einer Innenecke des Querschnitts käme
        # er der zweiten Wand näher als die Kugel – die Hüllfläche in genau dieser Stellung
        # rechnet ihn mit (dort hebt die Kugel ab, statt in die Wand zu schneiden).
        psi_p, x_p, q_p = umrechnen(a_p, x_p, q_p, psi_p)
    elif eingefuegt.any():  # die Kugel: ihr Plan liegt auf der Hüllfläche, die Übergänge nicht
        w = np.flatnonzero(eingefuegt)
        psi_w, x_w, q_w = umrechnen(a_p[w], x_p[w], q_p[w], psi_p[w])
        psi_p, x_p, q_p = psi_p.copy(), x_p.copy(), q_p.copy()
        psi_p[w], x_p[w], q_p[w] = psi_w, x_w, q_w
    _quer_ausgeben(
        punkte, a_p, x_p, q_p, psi_p, fest, sicher, abstand, drehung, pruef_radius, neigung
    )
    return float(np.min(x_p))


def _quer_plan(a, r, winkel, radius, schritt_phi, neigung=0.0):
    """Der Plan der Spirale mit der Querachse für eine Kugel mit `radius` (normale_quer):
    (a, Spitze x, Versatz q, ψ in Grad, Punkte, die bleiben, eingefügte Zwischenstellungen). Springt ψ zwischen zwei Punkten um
    mehr als QUER_SPRUNG Schritte (eine Innenecke: dort liegt die Kugel in der Ecke, die Normale
    ist nicht eindeutig; um eine Außenkante rollt sie mit 1–3° je Punkt, das bleibt), dreht das
    Werkzeug um die ruhende Kugelmitte in Schritten von `schritt_phi`. `neigung`: die Kugel so
    viele Grad neben der Normalen (normale_quer)."""
    psi, x, q = normale_quer(r, winkel, radius, a, neigung)
    rho = np.asarray(r, dtype=float) + radius
    phi = np.radians(np.asarray(winkel, dtype=float))
    teile_a, teile_x, teile_q, teile_psi, teile_neu, fest = [], [], [], [], [], []
    anzahl = 0
    for k in range(len(psi)):
        if k > 0:
            sprung = psi[k] - psi[k - 1]
            schritte = int(math.ceil(abs(sprung) / schritt_phi - 1e-9))
            if schritte > QUER_SPRUNG:
                t = np.arange(1, schritte) / schritte
                zwischen = psi[k - 1] + sprung * t
                um_kante = _um_die_kante(a, x, q, psi, k, radius, t, zwischen)
                if um_kante is not None:
                    # Um eine Außenkante: Der Berührpunkt bleibt liegen, die Mitte wandert mit
                    # (Manuel, 2026-10-05: „es hackt … an den Kanten“ – um die ruhende Mitte
                    # gedreht und dann weiter, pendelte Y alle fünf Sätze zurück).
                    a_t, x_t, q_t = um_kante
                    teile_neu.append(np.ones(schritte - 1, dtype=bool))
                else:
                    # In einer Innenecke: Die Kugel liegt in der Ecke, das Werkzeug dreht um
                    # die ruhende Mitte.
                    beta = phi[k - 1] - np.radians(zwischen)
                    a_t = np.full(schritte - 1, a[k - 1])
                    x_t = rho[k - 1] * np.cos(beta) - radius
                    q_t = rho[k - 1] * np.sin(beta)
                    teile_neu.append(np.zeros(schritte - 1, dtype=bool))
                teile_a.append(a_t)
                teile_x.append(x_t)
                teile_q.append(q_t)
                teile_psi.append(zwischen)
                fest.extend(range(anzahl - 1, anzahl + schritte))
                anzahl += schritte - 1
        teile_a.append(a[k : k + 1])
        teile_x.append(x[k : k + 1])
        teile_q.append(q[k : k + 1])
        teile_psi.append(psi[k : k + 1])
        teile_neu.append(np.zeros(1, dtype=bool))
        anzahl += 1
    a_alle, x_alle, q_alle, psi_alle, fest, eingefuegt = _uebergaenge(
        np.concatenate(teile_a),
        np.concatenate(teile_x),
        np.concatenate(teile_q),
        np.concatenate(teile_psi),
        fest,
        radius,
        np.concatenate(teile_neu),
    )
    fest.extend((np.flatnonzero(_a_knicke(a_alle)) + 1).tolist())
    fest = sorted({i for i in fest if 0 < i < len(a_alle) - 1})
    return a_alle, x_alle, q_alle, psi_alle, fest, eingefuegt


def _um_die_kante(a, x, q, psi, k, radius, t, zwischen):
    """Die Zwischenstellungen von Punkt k − 1 zu k des Plans, wenn die Kugel dort um eine
    Außenkante rollt – ihr Berührpunkt (die Mitte um den Radius gegen die Normale ψ) wandert
    weniger als ihre Mitte: Der Berührpunkt zieht gerade von einem zum anderen, ψ dreht in den
    Schritten `zwischen` (Anteile `t`), die Mitte steht um den Radius darüber. (a, x, q) – oder
    None in einer Innenecke (dort ruht die Mitte, _quer_plan)."""

    def mitte(i):
        w = math.radians(psi[i])
        u = (math.cos(w), math.sin(w))
        return (
            (x[i] + radius) * u[0] - q[i] * u[1],
            (x[i] + radius) * u[1] + q[i] * u[0],
        ), u

    (c1, u1), (c2, u2) = mitte(k - 1), mitte(k)
    p1 = (c1[0] - radius * u1[0], c1[1] - radius * u1[1])
    p2 = (c2[0] - radius * u2[0], c2[1] - radius * u2[1])
    if math.dist(p1, p2) > math.dist(c1, c2):
        return None
    w = np.radians(zwischen)
    cu, su = np.cos(w), np.sin(w)
    cx = p1[0] + t * (p2[0] - p1[0]) + radius * cu
    cy = p1[1] + t * (p2[1] - p1[1]) + radius * su
    a_t = a[k - 1] + t * (a[k] - a[k - 1])
    return a_t, cx * cu + cy * su - radius, cy * cu - cx * su


def _uebergaenge(a, x, q, psi, fest, radius, eingefuegt=None):
    """Wo die Mitte der Kugel zwischen zwei Punkten des Plans springt – viel weiter als die
    Schritte um sie herum (QUER_SPRUNG_MITTE) –, Zwischenstellungen auf der Geraden
    zwischen den beiden Mitten, alle QUER_UEBERGANG; ihre Höhe rechnet danach die Hüllfläche
    (vierachs_quer.stellungen). Das geschieht, wo das Teil unter die Drehmitte geht: Von der Achse
    aus sieht die Spirale dort nicht jede Stelle der Hüllfläche, die Mitte springt (an Manuels
    Teil hinten um gut 1 mm – die Gerade darüber schnitt 0,05 mm ins Teil, P-2026-10-03-22).
    Gibt (a, x, q, ψ, fest, eingefügt) zurück, die Nummern in `fest` verschoben, `eingefügt` je
    Punkt, ob er dazukam – mit denen, die schon `eingefuegt` waren (um eine Außenkante)."""
    eingefuegt = (
        np.zeros(len(a), dtype=bool) if eingefuegt is None else np.asarray(eingefuegt, dtype=bool)
    )
    if len(a) < 2:
        return a, x, q, psi, fest, eingefuegt
    rad = np.radians(psi)
    mx = (x + radius) * np.cos(rad) - q * np.sin(rad)
    my = (x + radius) * np.sin(rad) + q * np.cos(rad)
    sprung = np.hypot(np.diff(mx), np.diff(my))
    # Ein Sprung ist ein Schritt, viel weiter als die Schritte um ihn herum (je QUER_UMGEBUNG
    # davor und danach, ihr Median) – auf einer ebenen Fläche wandert die Mitte quer, ohne dass
    # ψ sich dreht, das ist kein Sprung.
    breit = np.pad(sprung, QUER_UMGEBUNG, mode="edge")
    fenster = np.lib.stride_tricks.sliding_window_view(breit, 2 * QUER_UMGEBUNG + 1)
    umgebung = np.median(fenster, axis=1)
    noetig = sprung > QUER_SPRUNG_MITTE * umgebung + QUER_UEBERGANG
    if not noetig.any():
        return a, x, q, psi, fest, eingefuegt
    schritte = np.flatnonzero(noetig)
    teile = np.ceil(sprung[schritte] / QUER_UEBERGANG).astype(np.int64)
    je = teile - 1
    welcher = np.repeat(schritte, je)
    bruch = (np.arange(int(je.sum())) - np.repeat(np.cumsum(je) - je, je) + 1) / np.repeat(
        teile, je
    )
    a_z = a[welcher] + bruch * (a[welcher + 1] - a[welcher])
    psi_z = psi[welcher] + bruch * (psi[welcher + 1] - psi[welcher])
    mx_z = mx[welcher] + bruch * (mx[welcher + 1] - mx[welcher])
    my_z = my[welcher] + bruch * (my[welcher + 1] - my[welcher])
    rad_z = np.radians(psi_z)
    x_z = mx_z * np.cos(rad_z) + my_z * np.sin(rad_z) - radius
    q_z = my_z * np.cos(rad_z) - mx_z * np.sin(rad_z)
    t_alle = np.concatenate([np.arange(len(a), dtype=float), welcher + bruch])
    ordnung = np.argsort(t_alle, kind="stable")
    neue_nummer = np.empty(len(t_alle), dtype=np.int64)
    neue_nummer[ordnung] = np.arange(len(t_alle))
    return (
        np.concatenate([a, a_z])[ordnung],
        np.concatenate([x, x_z])[ordnung],
        np.concatenate([q, q_z])[ordnung],
        np.concatenate([psi, psi_z])[ordnung],
        [int(neue_nummer[i]) for i in fest],
        np.concatenate([eingefuegt, np.ones(len(a_z), dtype=bool)])[ordnung],
    )


def _quer_ausgeben(
    punkte,
    a,
    x,
    q,
    psi,
    fest,
    sicher,
    abstand,
    drehung,
    radius,
    neigung=0.0,
    toleranz=BAHN_TOLERANZ,
    innen=QUER_INNEN,
):
    """Hängt die Stellungen (a, x, q, ψ) an `punkte`: im Eilgang über den Anfang, die Punkte
    zusammengefasst (_zusammen_quer, geprüft am Weg des Punkts `radius` über der Spitze, längs der
    Normalen ψ − `neigung`, höchstens `toleranz` außen und `innen` innen – was `innen` über
    QUER_INNEN hinausgeht, ist das Spiel beim Schruppen, und darum rücken die bleibenden Punkte
    nach außen), am Ende radial hinaus. Der Winkel zählt weiter, wo die Rundachse steht."""
    weiter = punkte[-1].phi
    if drehung > 0:
        versatz = 360.0 * math.ceil((weiter - psi[0]) / 360.0 - 1e-9)
    else:
        versatz = -360.0 * math.ceil((psi[0] - weiter) / 360.0 - 1e-9)
    anfahren = Punkt(True, float(a[0]), sicher, float(psi[0] + versatz), q=float(q[0]))
    if anfahren != punkte[-1]:
        punkte.append(anfahren)
    bleibt = _zusammen_quer(x, q, psi, radius, toleranz, abstand, fest, neigung, innen)
    # Mit Spiel beim Schruppen: die bleibenden Punkte so weit hinaus, dass nichts ins Aufmaß
    # schneidet; sonst (Schlichten) wie bisher.
    hebung = (
        _quer_hebung(x, q, psi, radius, bleibt, neigung)
        if innen > QUER_INNEN
        else np.zeros(len(bleibt))
    )
    for i, h in zip(bleibt, hebung, strict=True):
        punkte.append(
            Punkt(
                False, float(a[i]), float(x[i]) + float(h), float(psi[i] + versatz), q=float(q[i])
            )
        )
    letzter = len(a) - 1
    punkte.append(
        Punkt(True, float(a[letzter]), sicher, float(psi[letzter] + versatz), q=float(q[letzter]))
    )


class _QuerAbstand:
    """Wie weit die Kurve, die die Maschine zwischen zwei Punkten der Spirale mit der Querachse
    fährt (x, q und ψ zugleich geradlinig; die Kugelmitte im Teil auf Rot(ψ(t)) · (x(t) + R,
    q(t))), an den ausgelassenen Punkten dazwischen von diesen abweicht – längs ihrer Normalen
    ψ − `neigung` (außen positiv) und quer dazu (_zusammen_quer, _quer_hebung)."""

    def __init__(self, x, q, psi, radius, neigung=0.0):
        self.x = np.asarray(x, dtype=float)
        self.q = np.asarray(q, dtype=float)
        self.psi = np.asarray(psi, dtype=float)
        self.radius = radius
        rad = np.radians(self.psi)
        self.mitte_x = (self.x + radius) * np.cos(rad) - self.q * np.sin(rad)
        self.mitte_y = (self.x + radius) * np.sin(rad) + self.q * np.cos(rad)
        normale = rad - math.radians(neigung)
        self.c, self.s = np.cos(normale), np.sin(normale)

    def zwischen(self, i, j):
        """(längs, seitlich) je Punkt zwischen i und j (beide nicht dabei)."""
        x, q, psi, radius = self.x, self.q, self.psi, self.radius
        k = np.arange(i + 1, j)
        t = (k - i) / (j - i)
        xt = x[i] + t * (x[j] - x[i])
        qt = q[i] + t * (q[j] - q[i])
        pt = np.radians(psi[i] + t * (psi[j] - psi[i]))
        ct, st = np.cos(pt), np.sin(pt)
        dx = (xt + radius) * ct - qt * st - self.mitte_x[k]
        dy = (xt + radius) * st + qt * ct - self.mitte_y[k]
        return dx * self.c[k] + dy * self.s[k], dy * self.c[k] - dx * self.s[k]


def _quer_hebung(x, q, psi, radius, bleibt, neigung=0.0):
    """Je bleibendem Punkt: so weit nach außen (längs seiner Normalen), dass die Kurve zu seinen
    bleibenden Nachbarn an keinem ausgelassenen Punkt innen liegt – um das, was _zusammen_quer
    mit `innen` beim Schruppen darunter ließ (höchstens das Spiel; 0, wo nichts darunter lag).
    x ist der Radius im mitdrehenden Rahmen: beide Enden angehoben, hebt es das ganze Stück."""
    abstand = _QuerAbstand(x, q, psi, radius, neigung)
    hebung = np.zeros(len(bleibt))
    for k in range(len(bleibt) - 1):
        i, j = bleibt[k], bleibt[k + 1]
        if j <= i + 1:
            continue
        laengs, _seitlich = abstand.zwischen(i, j)
        fehlt = float(max(0.0, -np.min(laengs)))
        if fehlt > 0.0:
            hebung[k] = max(hebung[k], fehlt)
            hebung[k + 1] = max(hebung[k + 1], fehlt)
    return hebung


def _zusammen_quer(x, q, psi, radius, toleranz, hoechstens, fest=(), neigung=0.0, innen=QUER_INNEN):
    """Die Punkte, die von der Spirale mit der Querachse bleiben (wie _zusammengefasst, nur
    im Rahmen des Teils gemessen). Die Maschine fährt zwischen zwei Punkten x, q und ψ
    zugleich geradlinig; die Kugelmitte läuft dabei im Teil auf der Kurve Rot(ψ(t)) · (x(t) +
    R, q(t)) – auf einer Ebene (ψ hält) eine Gerade, auf einem Zylinder (x und q halten) ein
    Bogen, beides genau. Ein Punkt kann weg, wenn diese Kurve an ihm längs seiner Normalen
    höchstens `toleranz` außen und `innen` innen liegt und quer dazu höchstens
    QUER_SEITLICH – quer heißt nur: an einer anderen Stelle derselben Bahn. Je Lauf das
    längste Stück, das passt (verdoppeln, dann halbieren), höchstens `hoechstens` Punkte;
    die Punkte in `fest` bleiben (Ringe, Innenecken). Mit radius 0 (die Spitze eines Fräsers,
    der keine Kugel ist) seitlich höchstens QUER_SEITLICH_SPITZE. Steht die Kugel um `neigung`
    neben der Normalen (normale_quer), zählt längs und quer zur Normalen ψ − `neigung`."""
    seitlich_hoechstens = QUER_SEITLICH if radius > 0 else QUER_SEITLICH_SPITZE
    n = len(x)
    abstand = _QuerAbstand(x, q, psi, radius, neigung)

    def passt(i, j):
        if j <= i + 1:
            return True
        laengs, seitlich = abstand.zwischen(i, j)
        return bool(
            np.all(laengs <= toleranz)
            and np.all(laengs >= -innen)
            and np.all(np.abs(seitlich) <= seitlich_hoechstens)
        )

    grenzen = sorted({0, n - 1} | {i for i in fest if 0 < i < n - 1})
    bleibt = [0]
    for von, bis in zip(grenzen, grenzen[1:], strict=False):
        anfang = von
        while anfang < bis:
            ende = min(bis, anfang + hoechstens)
            # Verdoppeln, bis es nicht mehr passt, dann halbieren.
            gut, schlecht = anfang + 1, None
            schritt = 1
            while schlecht is None:
                j = min(gut + schritt, ende)
                if passt(anfang, j):
                    gut = j
                    if j == ende:
                        break
                    schritt *= 2
                else:
                    schlecht = j
            while schlecht is not None and schlecht - gut > 1:
                j = (gut + schlecht) // 2
                if passt(anfang, j):
                    gut = j
                else:
                    schlecht = j
            bleibt.append(gut)
            anfang = gut
    return bleibt


def _auffuellen(huelle, anfang_je_winkel, schritt, teil_vorne, teil_hinten):
    """Vor und hinter dem Teil – wo die Mitte des Fräsers über das Teil hinaus ist – die Tiefe
    an seinem Ende: Der Fräser fährt so an und aus dem Teil heraus, wie er an dessen Ende war,
    statt mit dem Rand an der Kante hinabzurollen (wie das Schruppen, V3f)."""
    ergebnis = huelle.copy()
    zeilen = np.arange(len(huelle))[:, None]
    spalten = np.arange(huelle.shape[1])
    vorne = np.floor((teil_vorne - anfang_je_winkel) / schritt + 1e-9).astype(np.int64)
    hinten = np.ceil((teil_hinten - anfang_je_winkel) / schritt - 1e-9).astype(np.int64)
    vorne = np.clip(vorne, 0, len(huelle) - 1)
    hinten = np.clip(hinten, 0, len(huelle) - 1)
    wert_vorne = huelle[vorne, spalten]
    wert_hinten = huelle[hinten, spalten]
    davor = (zeilen > vorne[None, :]) & np.isfinite(wert_vorne)[None, :]
    dahinter = (zeilen < hinten[None, :]) & np.isfinite(wert_hinten)[None, :]
    ergebnis = np.where(davor, wert_vorne[None, :], ergebnis)
    return np.where(dahinter, wert_hinten[None, :], ergebnis)


def _nicht_tiefer(rest, form, grenze, a, phi):
    """Wie tief die Spitze an den Punkten (a, φ in rad) höchstens darf, damit der Fräser
    nirgends mehr als `grenze` unter den Rest nach dem Schruppen schneidet: je Stelle des
    Rests unter dem Fräser seine Höhe dort minus Profil – der höchste Wert, minus `grenze`.
    Zwischen den Rasterpunkten gilt der höchste Nachbar."""
    rest_a, rest_phi, rest_r = rest
    schritt_a = rest_a[1] - rest_a[0]
    schritt_phi = rest_phi[1] - rest_phi[0]
    radius = form.radius
    n_a = int(math.ceil(radius / schritt_a))
    klein = max(float(np.min(rest_r)), radius)
    n_phi = min(len(rest_phi) // 2, int(math.ceil(math.asin(radius / klein) / schritt_phi)) + 1)
    rand = np.full((n_a, rest_r.shape[1]), -math.inf)
    breit = np.concatenate([rand, rest_r, rand])
    tiefste = np.full(rest_r.shape, -math.inf)
    with np.errstate(invalid="ignore"):
        for i in range(-n_a, n_a + 1):
            zeilen = breit[n_a + i : n_a + i + len(rest_a)]
            for j in range(-n_phi, n_phi + 1):
                r_p = np.roll(zeilen, -j, axis=1)
                delta = j * schritt_phi
                seitlich = r_p * abs(math.sin(delta))
                abstand = np.sqrt((i * schritt_a) ** 2 + seitlich * seitlich)
                # Genau am Rand berührt die Stirn nur – ohne Volumen. Mitgezählt meldete das
                # Schlichten an Manuels Teil 35 mm Rest hinter dem Teil, wo der Rand der Kugel
                # die stehende Stange am Abstich streifte (P-2026-10-03-30).
                unter = abstand < radius - 1e-9
                wert = r_p * math.cos(delta) - form.hoehe(np.minimum(abstand, radius))
                np.maximum(tiefste, np.where(unter, wert, -math.inf), out=tiefste)
    tiefste -= grenze
    lage_a = (a - rest_a[0]) / schritt_a
    lage_phi = np.mod(phi - rest_phi[0], 2 * math.pi) / schritt_phi
    ergebnis = np.full(len(a), -math.inf)
    for i in (np.floor(lage_a), np.ceil(lage_a)):
        drin = (i >= 0) & (i < len(rest_a))
        zeile = np.clip(i, 0, len(rest_a) - 1).astype(np.int64)
        for j in (np.floor(lage_phi), np.ceil(lage_phi)):
            spalte = j.astype(np.int64) % len(rest_phi)
            ergebnis = np.maximum(ergebnis, np.where(drin, tiefste[zeile, spalte], -math.inf))
    return ergebnis


def _sehnenfehler(r, t=None):
    """Um so viel heben sich die Punkte, damit die Gerade zwischen zwei Punkten nicht unter die
    Hüllfläche fällt, wo sie sich nach außen wölbt: ein Achtel der zweiten Differenz, je
    Punkt das größte der Nachbarschaft, höchstens SEHNE_HOECHSTENS. `t`: wo die Punkte liegen
    (Nummer der Spirale, mit Zwischenpunkten gebrochen – _verfeinert); ohne: gleich weit."""
    wolbung = np.zeros(len(r))
    if len(r) >= 3 and t is None:
        zweite = -(r[:-2] - 2.0 * r[1:-1] + r[2:])
        wolbung[1:-1] = np.clip(zweite / 8.0, 0.0, SEHNE_HOECHSTENS)
    elif len(r) >= 3:  # über der Sehne der Nachbarn – gleich weit ist das die zweite Differenz/2
        t = np.asarray(t, dtype=float)
        anteil = (t[1:-1] - t[:-2]) / (t[2:] - t[:-2])
        ueber = r[1:-1] - (r[:-2] + anteil * (r[2:] - r[:-2]))
        wolbung[1:-1] = np.clip(ueber / 4.0, 0.0, SEHNE_HOECHSTENS)
    heben = wolbung.copy()
    heben[1:] = np.maximum(heben[1:], wolbung[:-1])
    heben[:-1] = np.maximum(heben[:-1], wolbung[1:])
    return heben


def _zusammengefasst(r, toleranz, hoechstens, fest=(), t=None, innen=0.0):
    """Die Punkte, die bleiben: Anfang, Ende, die Punkte in `fest` und so wenige dazwischen,
    dass die Gerade zwischen zwei bleibenden Punkten über keinem ausgelassenen liegt (höchstens
    `innen` darunter – beim Schruppen das Spiel im Aufmaß, sonst 0) und höchstens `toleranz`
    darüber – zwischen ihnen sind a und φ linear (an den Punkten in `fest` knickt a: ein Ring
    beginnt oder endet). Höchstens `hoechstens` Punkte weit. `t` wie bei _sehnenfehler: a und
    φ sind dann linear in t, die Weite zählt in t."""
    werte = r.tolist()
    stelle = list(range(len(werte))) if t is None else np.asarray(t, dtype=float).tolist()
    fest = set(fest)
    bleibt = [0]
    anfang = 0
    unten, oben = -math.inf, math.inf  # erlaubte Steigung ab dem Anfang
    for i in range(1, len(werte)):
        schritte = stelle[i] - stelle[anfang]
        steigung = (werte[i] - werte[anfang]) / schritte
        if schritte > hoechstens or not unten <= steigung <= oben:
            anfang = i - 1
            bleibt.append(anfang)
            schritte = stelle[i] - stelle[anfang]
            unten, oben = -math.inf, math.inf
        # Ab hier muss die Gerade über Punkt i liegen (höchstens `innen` darunter), höchstens
        # `toleranz` darüber.
        unten = max(unten, (werte[i] - innen - werte[anfang]) / schritte)
        oben = min(oben, (werte[i] + toleranz - werte[anfang]) / schritte)
        if i in fest and i < len(werte) - 1:
            bleibt.append(i)
            anfang = i
            unten, oben = -math.inf, math.inf
    if bleibt[-1] != len(werte) - 1:
        bleibt.append(len(werte) - 1)
    return bleibt


def _hinten_gerade(huelle, teil_hinten):
    """Hinter dem Teil (a < teil_hinten) je Winkel die Tiefe am Teilende: Im Überlauf fährt der
    Fräser das Profil des Teilendes gerade weiter, statt hinter der Kante hinabzurollen – eine
    Kugel sank dort bis zu ihrem Radius tiefer und schnitt eine Kerbe hinter das Teil
    (P-2026-10-03-08; wie _auffuellen beim Schlichten). Wo er am Teilende nichts trifft, bleibt
    es leer – dort bleibt er oben."""
    r = huelle.r.copy()
    hinten = np.flatnonzero(huelle.a < teil_hinten)
    if len(hinten) and hinten[-1] + 1 < len(huelle.a):
        r[hinten] = r[hinten[-1] + 1]
    return vh.Huelle(huelle.a, huelle.phi, r)


def _frei(a, r, phi, leer):
    """Je Punkt i: Ist das Stück dorthin frei (Punkt.frei)? `leer` je Punkt: steht dort nichts
    mehr über der Spitze? Frei ist ein Stück zwischen zwei leeren Punkten in einem Lauf, der
    zusammen mindestens freiwege.MINDEST mm lang ist – bis freiwege.VORLAUF mm vor seinem Ende:
    Davor bremst die Steuerung auf den Schnittvorschub (wie bei den Strategien im Quader)."""
    from . import freiwege as fw

    a, r, phi = (np.asarray(x, dtype=float) for x in (a, r, phi))
    frei = np.zeros(len(a), dtype=bool)
    if len(a) < 2:
        return frei
    mitte = np.maximum((r[1:] + r[:-1]) / 2, 0.0)
    laenge = np.sqrt(np.diff(a) ** 2 + np.diff(r) ** 2 + (mitte * np.radians(np.diff(phi))) ** 2)
    leer = np.asarray(leer, dtype=bool)
    for von, bis in _stuecke(leer[1:] & leer[:-1]):
        lauf = laenge[von : bis + 1]
        if float(lauf.sum()) < fw.MINDEST:
            continue
        bis_zum_ende = np.cumsum(lauf[::-1])[::-1] - lauf  # vom Ende des Stücks bis zum Material
        frei[von + 1 : bis + 2] = bis_zum_ende >= fw.VORLAUF
    return frei


def _a_knicke(a, t=None):
    """Je innerem Punkt: Ändert `a` dort seine Steigung – beginnt oder endet ein Ring? `t` wie
    bei _sehnenfehler: die Steigung über t."""
    if t is None:
        return np.abs(np.diff(a, 2)) > GLEICH
    steigung = np.diff(a) / np.diff(np.asarray(t, dtype=float))
    return np.abs(np.diff(steigung)) > GLEICH


def befehle(
    bahn,
    laengs,
    radial,
    buchstabe,
    drehsinn,
    vorschub,
    quer_auf_null=True,
    eintauchen=None,
    freivorschub=None,
    fraeser_radius=0.0,
):
    """Die Bahn als Path-Befehle.

    X, Y und Z sind die Spitze im Rahmen der Maschine: a längs, r radial (die
    Richtung `radial`). Die Rundachse `buchstabe` dreht das Teil darunter:
    Steht das Werkzeug unter φ zum Teil, ist ihr Wert −drehsinn · φ. `drehsinn`
    +1 heißt, ein positiver Wert dreht das Teil rechtshändig um `laengs` – so
    zeigt FreeCAD die Bahn. Vorschübe stehen zwischen G93 und G94: F = 1 ÷ Zeit,
    damit der Fräser am Werkstück mit `vorschub` (mm/min) fährt, egal wie weit er
    von der Achse weg ist. CAM führt F in mm/s, der Postprozessor schreibt ×60 –
    deshalb steht hier F ÷ 60. `quer_auf_null`: die Achse quer (bei C das Y) am
    Anfang auf 0, damit das Werkzeug auf der Mitte steht. `eintauchen`: der Vorschub
    (mm/min) zu Punkten, an denen der Fräser senkrecht eintaucht; ohne: `vorschub`.
    `freivorschub` (mm/min): zu freien Punkten (Punkt.frei); ohne: wie die anderen.
    `fraeser_radius`: Kippt der Fräser um eine Kante, läuft seine Stirn höchstens mit dem
    Vorschub (_weg_im_vorschub).
    """
    import Path

    l_, u_, v_ = vh.rahmen(laengs, radial)
    genutzt = [i for i in range(3) if abs(l_[i]) > GLEICH or abs(u_[i]) > GLEICH]
    quer = [i for i in range(3) if i not in genutzt]
    radial_achsen = [i for i in range(3) if abs(u_[i]) > GLEICH]
    # Fährt die Bahn quer versetzt (Plan indexiert), steht die Querachse in jedem Satz.
    mit_quer = any(abs(p.q) > GLEICH for p in bahn.punkte)

    def lage(punkt):
        spitze = l_ * punkt.a + u_ * punkt.r + v_ * punkt.q
        werte = {"XYZ"[i]: float(spitze[i]) for i in genutzt}
        if mit_quer:
            werte.update({"XYZ"[i]: float(spitze[i]) for i in quer})
        werte[buchstabe] = -drehsinn * punkt.phi
        return werte

    ergebnis = [
        Path.Command(
            f"(4-Achs rundum: {buchstabe} dreht das Teil, Radius in "
            f"{''.join('XYZ'[i] for i in radial_achsen)}, Vorschub G93)"
        )
    ]
    if not bahn.punkte:
        return ergebnis
    start = bahn.punkte[0]
    spitze = l_ * start.a + u_ * start.r
    ergebnis.append(Path.Command("G0", {"XYZ"[i]: float(spitze[i]) for i in radial_achsen}))
    anfang = lage(start)
    if quer_auf_null:
        anfang.update({"XYZ"[i]: 0.0 for i in quer})
    ergebnis.append(Path.Command("G0", anfang))
    ergebnis.append(Path.Command("G93"))
    vorher = start
    f_vorher = None
    for punkt in bahn.punkte[1:]:
        if punkt.eilgang:
            ergebnis.append(Path.Command("G0", lage(punkt)))
        else:
            weg = _weg_im_vorschub(vorher, punkt, fraeser_radius)
            if weg < 1e-6:
                continue
            werte = lage(punkt)
            f = _vorschub_zu(punkt, vorschub, eintauchen, freivorschub)
            werte["F"] = f_vorher = _anderes_f(f / weg / 60.0, f_vorher)
            ergebnis.append(Path.Command("G1", werte))
        vorher = punkt
    ergebnis.append(Path.Command("G94"))
    return ergebnis


def _anderes_f(f, vorher):
    """F für G93 auf F_STELLEN Stellen – gleicht es dem F davor, eine Einheit der letzten
    Stelle mehr. In G93 muss F in jedem Satz stehen, doch manche Postprozessoren (Fanuc,
    UCCNC) lassen ein F weg, das dem vorigen gleicht (P-2026-09-30-39, Manuel: „Es muss ja für
    alle funktionieren“). So bleibt es verschieden, auch nach Speichern und Laden; im Programm
    (F × 60 auf 3 Stellen) sieht man den Unterschied nicht."""
    f = round(f, F_STELLEN)
    if vorher is not None and f == vorher:
        f = round(f + 10.0**-F_STELLEN, F_STELLEN)
    return f


def _weg(von, nach):
    """Der Weg der Spitze am Werkstück von einem Punkt zum nächsten (mm): die Sehne im Rahmen
    des Teils (die Spitze unter dem Winkel φ, quer um q versetzt), gestreckt zum Bogen, so weit
    die Rundachse dreht – dreht nur sie, ist es genau der Bogen; fährt nur die Querachse (ψ
    hält, V5e), genau die Gerade."""
    winkel = math.radians(nach.phi - von.phi)
    laengs = nach.a - von.a
    if abs(winkel) > math.pi / 2:  # ein weiter Bogen: Sehne und Bogen sagen nichts mehr
        r = math.hypot((von.r + nach.r) / 2, (von.q + nach.q) / 2)
        return math.sqrt(
            laengs * laengs + (nach.r - von.r) ** 2 + (nach.q - von.q) ** 2 + (r * winkel) ** 2
        )
    c0, s0 = math.cos(math.radians(von.phi)), math.sin(math.radians(von.phi))
    c1, s1 = math.cos(math.radians(nach.phi)), math.sin(math.radians(nach.phi))
    dx = (nach.r * c1 - nach.q * s1) - (von.r * c0 - von.q * s0)
    dy = (nach.r * s1 + nach.q * c1) - (von.r * s0 + von.q * c0)
    sehne = math.hypot(dx, dy)
    halb = abs(winkel) / 2.0
    if halb > 1e-9:
        sehne *= halb / math.sin(halb)
    return math.hypot(laengs, sehne)


def _weg_im_vorschub(von, nach, fraeser_radius=0.0):
    """Der Weg, den der Vorschub von einem Punkt zum nächsten fährt (mm): der der Spitze
    (_weg) – kippt der Fräser dabei um eine Kante, mindestens der seines Umfangs um sie,
    Radius · Drehwinkel. Sonst rechnete G93 das Kippen fast ohne Zeit, und die Rundachse
    peitschte herum (Manuel, 2026-10-05: „es hackt ziemlich extrem beim Schwenken, vor allem an
    den Kanten“ – in seinem Programm C kurz 75 U/min statt sonst 15). Auf einem Bogen um die
    Achse fährt die Spitze ohnehin weiter."""
    weg = _weg(von, nach)
    if fraeser_radius > 0.0:
        weg = max(weg, fraeser_radius * abs(math.radians(nach.phi - von.phi)))
    return weg


def _vorschub_zu(punkt, vorschub, eintauchen=None, freivorschub=None):
    """Der Vorschub (mm/min) zum Punkt: frei der Freivorschub, eintauchend der Eintauchvorschub,
    sonst der Vorschub – mal Punkt.anteil (nicht im Freien)."""
    if punkt.frei and freivorschub:
        return freivorschub
    return (eintauchen if punkt.eintauchen and eintauchen else vorschub) * punkt.anteil


def dauer(bahn, vorschub, eintauchen=None, freivorschub=None, fraeser_radius=0.0):
    """So lange fährt die Bahn im Vorschub (Minuten) – ohne Eilgänge; `eintauchen`,
    `freivorschub` und `fraeser_radius` wie bei befehle()."""
    zeit = 0.0
    for von, nach in zip(bahn.punkte, bahn.punkte[1:], strict=False):
        if not nach.eilgang:
            weg = _weg_im_vorschub(von, nach, fraeser_radius)
            zeit += weg / _vorschub_zu(nach, vorschub, eintauchen, freivorschub)
    return zeit
