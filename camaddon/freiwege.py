# SPDX-License-Identifier: LGPL-2.1-or-later
"""Im Freien schnell – für jede Strategie (Manuel, 2026-10-04: „wenn es frei ist und da kein
Material ist … muss ich nicht langsam fahren, gib Gas bis kurz davor, bevor es wieder langsam
weiter geht .. bei allen Strategien .. egal was das ist“).

Die Bahn (bahn.Punkt) wird im Materialstand vor der Operation abgefahren (restmaterial.Quader,
wie raeumen_bahn.last). Ein Stück im Vorschub auf gleicher Höhe ist frei, wenn im Umkreis
R + RAND um seinen Weg nichts über der Spitze steht – vorsichtig gerechnet: An einer Wand oder
über einem Aufmaß zählt das Teil selbst als Material, dort bleibt der Schnittvorschub. Freie
Stücke, zusammen mindestens MINDEST mm lang, fahren mit dem Freivorschub (G1 – ein G0 fährt
auf vielen Steuerungen keine Gerade); die letzten VORLAUF mm vor dem nächsten Material bleiben
langsam – das Bremsen davor macht die Vorausschau der Steuerung. Eilgänge, Eintauchen und
Rampen bleiben, wie sie sind; ein Bogen wird nur ganz schnell oder gar nicht.

Unten bleiben (unnoetiges Abheben weg, Manuel: „unnötige Bewegungen … kannst du auch ohne mich
einfach wegbügeln“): Hebt die Bahn am Ende eines Laufs im Eilgang ab, fährt hinüber und taucht
an einem Punkt auf derselben Höhe oder tiefer wieder ein (am Testteil beim 3D-Schruppen jeder
Lagenwechsel in der Mulde: 15–23 mm hinauf und wieder hinab für 3–10 mm hinüber), fährt sie
stattdessen auf ihrer Höhe hinüber – wenn der gerade Weg dort im Umkreis R + RAND frei ist und
ganz über dem Rohteil liegt (daneben könnten Spannmittel stehen). Ist er dort nicht frei (am
Ende einer Lage berührt der Fräser die Wand), hebt sie nur LINK_LUFT über das höchste Material im
Umkreis R + RAND des Weges ab, statt bis zur Sicherheitshöhe. Und: Folgt auf einen senkrechten
Eilgang hinab ein senkrechtes Eintauchen, geht der Eilgang bis LINK_LUFT über das Material dort
– die Bahn weiß nicht, was sie selbst schon geräumt hat (an der Platte tauchte das Räumen viermal
23 mm durch die schon geräumte Tasche).
"""

import math

import numpy as np

from . import bahn as bn
from . import fahrzeit as fz

FREIVORSCHUB = fz.EILGANG  # mm/min – ohne Maschine (oder ohne ihren Höchstvorschub)
VORLAUF = 2.0  # mm vor dem Material bleibt der Schnittvorschub
MINDEST = 5.0  # mm – kürzere freie Stücke lohnen das Beschleunigen nicht
RAND = 1.0  # mm über den Radius hinaus muss es frei sein
SEHNE = 1.0  # mm – so fein wird nachgesehen
GLEICH = 0.05  # mm
LINK_LUFT = (
    2.0  # mm – so hoch über dem höchsten Material fährt ein Weg, der nicht unten bleibt (wie der
)
# Sicherheitsabstand der Strategien; das Raster des Materialstands ist 0,5 mm)


def _frei(q, a, b, weite):
    """Steht im Umkreis `weite` um den Weg a → b (die Spitze) nichts über der Spitze?"""
    z = min(a[2], b[2])
    x0, x1 = min(a[0], b[0]) - weite, max(a[0], b[0]) + weite
    y0, y1 = min(a[1], b[1]) - weite, max(a[1], b[1]) + weite
    i0, i1 = np.searchsorted(q.x, x0), np.searchsorted(q.x, x1, side="right")
    j0, j1 = np.searchsorted(q.y, y0), np.searchsorted(q.y, y1, side="right")
    if i1 <= i0 or j1 <= j0:
        return True  # neben dem Rohteil
    h = q.h[i0:i1, j0:j1]
    hoch = h > z + GLEICH
    if not hoch.any():
        return True
    gx, gy = np.meshgrid(q.x[i0:i1], q.y[j0:j1], indexing="ij")
    dx, dy = b[0] - a[0], b[1] - a[1]
    laenge2 = dx * dx + dy * dy
    if laenge2 > 1e-12:
        t = np.clip(((gx - a[0]) * dx + (gy - a[1]) * dy) / laenge2, 0.0, 1.0)
    else:
        t = np.zeros_like(gx)
    abstand = np.hypot(gx - (a[0] + t * dx), gy - (a[1] + t * dy))
    return not bool((hoch & (abstand <= weite)).any())


def _sehnen(von, nach):
    """Die Sehnen von `von` nach `nach` (Bögen gesehnt), je höchstens SEHNE lang."""
    from . import materialstand as mst

    ergebnis = []
    for a, b in mst.sehnen(von, nach):
        n = max(1, int(math.ceil(math.dist(a[:2], b[:2]) / SEHNE)))
        for k in range(n):
            ergebnis.append(
                (
                    tuple(a[i] + (b[i] - a[i]) * k / n for i in range(3)),
                    tuple(a[i] + (b[i] - a[i]) * (k + 1) / n for i in range(3)),
                )
            )
    return ergebnis


def schneller(punkte, form, quader, vorschub, freivorschub=FREIVORSCHUB):
    """(Punkte, Weg in mm, der jetzt schnell fährt): die Bahn `punkte` mit dem Freivorschub
    (mm/min) auf den freien Stücken – `quader` (restmaterial.Quader, wird verändert) ist das
    Material vor der Operation, `vorschub` ihr Schnittvorschub (mm/min)."""
    if vorschub <= 0 or freivorschub <= vorschub * 1.01 or len(punkte) < 2:
        return list(punkte), 0.0
    anteil_frei = freivorschub / vorschub
    weite = float(form.radius) + RAND
    punkte = list(punkte)
    # 1. Abfahren: je Satz seine Sehnen, je Sehne (Länge, frei, kommt in Frage). Davor, wo die
    # Bahn unnötig abhebt, unten bleiben (_abheben) – gegen das Material genau an dieser Stelle.
    saetze = []
    i = 0
    while i < len(punkte) - 1:
        _unten_bleiben(punkte, i, quader, weite)
        _tiefer_im_eilgang(punkte, i, quader, float(form.radius))
        von, nach = punkte[i], punkte[i + 1]
        i += 1
        sehnen = _sehnen(von, nach)
        frage = not nach.eilgang and not nach.eintauchen and abs(nach.z - von.z) <= GLEICH
        # Schon schneller als der Vorschub (ein Rückweg durchs Freie, den die Strategie geprüft
        # hat – raeumen_bahn, nut_bahn: RUECKWEG): frei.
        schon = frage and float(nach.anteil) > 1.0 + 1e-9
        # Je Satz gegen das Material vor ihm geprüft (was er selbst wegnimmt, zählt noch – das
        # ist vorsichtiger), dann auf einmal abgetragen.
        eintraege = [
            [a, b, math.dist(a[:2], b[:2]), frage and (schon or _frei(quader, a, b, weite))]
            for a, b in sehnen
        ]
        if not nach.eilgang and sehnen:
            quader.fahre_stuecke([a for a, _b in sehnen], [b for _a, b in sehnen], form)
        saetze.append((frage, eintraege))
    # 2. Rückwärts: wie weit bis zum nächsten Material (ein Eilgang beendet die Fahrt); vorwärts:
    # wie lang das freie Stück ist, in dem eine Sehne liegt.
    flach = [e for _f, eintraege in saetze for e in eintraege]
    grenze = []
    for (_f, eintraege), nach in zip(saetze, punkte[1:], strict=True):
        grenze.extend([nach.eilgang] * len(eintraege))
    bis = [0.0] * len(flach)
    weiter = math.inf
    for k in range(len(flach) - 1, -1, -1):
        if grenze[k]:
            weiter = math.inf
        elif not flach[k][3]:
            weiter = 0.0
        bis[k] = weiter
        if not grenze[k] and flach[k][3]:
            weiter += flach[k][2]
    lauf = [0.0] * len(flach)
    k = 0
    while k < len(flach):
        if not flach[k][3]:
            k += 1
            continue
        m = k
        while m < len(flach) and flach[m][3]:
            m += 1
        summe = sum(e[2] for e in flach[k:m])
        for i in range(k, m):
            lauf[i] = summe
        k = m
    schnell_flags = [
        flach[i][3] and lauf[i] >= MINDEST and bis[i] >= VORLAUF for i in range(len(flach))
    ]
    # 3. Neue Punkte: ein Satz, wo schnell und langsam wechseln, geteilt (Geraden); ein Bogen
    # nur ganz.
    neu = [punkte[0]]
    schnell_weg = 0.0
    k = 0
    for (frage, eintraege), nach in zip(saetze, punkte[1:], strict=True):
        flags = schnell_flags[k : k + len(eintraege)]
        k += len(eintraege)
        if not frage or not any(flags):
            neu.append(nach)
            continue
        if nach.bogen is not None:
            if all(flags):
                anteil = max(anteil_frei, float(nach.anteil))
                neu.append(bn.Punkt(False, nach.x, nach.y, nach.z, False, nach.bogen, anteil))
                schnell_weg += sum(e[2] for e in eintraege)
            else:
                neu.append(nach)
            continue
        for i, (_a, b, _laenge, _ist_frei) in enumerate(eintraege):
            letzte = i == len(eintraege) - 1
            if not letzte and flags[i] == flags[i + 1]:
                continue
            anteil = max(anteil_frei, float(nach.anteil)) if flags[i] else float(nach.anteil)
            neu.append(bn.Punkt(False, b[0], b[1], nach.z, False, None, anteil))
        schnell_weg += sum(e[2] for e, f in zip(eintraege, flags, strict=True) if f)
    return neu, schnell_weg


def _hoechstes(q, a, b, weite):
    """Das höchste Material (z) im Umkreis `weite` um den Weg a → b (xy) – −inf ohne."""
    x0, x1 = min(a[0], b[0]) - weite, max(a[0], b[0]) + weite
    y0, y1 = min(a[1], b[1]) - weite, max(a[1], b[1]) + weite
    i0, i1 = np.searchsorted(q.x, x0), np.searchsorted(q.x, x1, side="right")
    j0, j1 = np.searchsorted(q.y, y0), np.searchsorted(q.y, y1, side="right")
    if i1 <= i0 or j1 <= j0:
        return -math.inf
    gx, gy = np.meshgrid(q.x[i0:i1], q.y[j0:j1], indexing="ij")
    dx, dy = b[0] - a[0], b[1] - a[1]
    laenge2 = dx * dx + dy * dy
    if laenge2 > 1e-12:
        t = np.clip(((gx - a[0]) * dx + (gy - a[1]) * dy) / laenge2, 0.0, 1.0)
    else:
        t = np.zeros_like(gx)
    nah = np.hypot(gx - (a[0] + t * dx), gy - (a[1] + t * dy)) <= weite
    return float(q.h[i0:i1, j0:j1][nah].max()) if nah.any() else -math.inf


def _tiefer_im_eilgang(punkte, i, quader, radius):
    """Endet der Eilgang zu Punkt i + 1 über einem senkrechten Eintauchen (Punkt i + 2): ein
    Eilgang senkrecht hinab bis LINK_LUFT über das höchste Material unter der Stirn (`radius` und
    eine halbe Zelle des Rasters – senkrecht hinab streift der Fräser nur, was unter ihr liegt;
    taucht er neben einer Wand mit Aufmaß ein, zählt sie nicht) – nur über dem Rohteil, nie
    tiefer als das Eintauchen endet."""
    weite = radius + 0.5 * float(quader.x[1] - quader.x[0])
    if i + 2 >= len(punkte):
        return
    oben, ein = punkte[i + 1], punkte[i + 2]
    if not oben.eilgang or ein.eilgang or ein.bogen is not None:
        return
    if math.hypot(ein.x - oben.x, ein.y - oben.y) > GLEICH or ein.z >= oben.z - GLEICH:
        return
    if not (
        quader.x[0] <= oben.x - weite
        and oben.x + weite <= quader.x[-1]
        and quader.y[0] <= oben.y - weite
        and oben.y + weite <= quader.y[-1]
    ):
        return
    stelle = (oben.x, oben.y, oben.z)
    ziel = max(_hoechstes(quader, stelle, stelle, weite) + LINK_LUFT, ein.z)
    if ziel < oben.z - GLEICH:
        punkte.insert(i + 2, bn.Punkt(True, oben.x, oben.y, ziel))


def _abheben(punkte, i):
    """Hebt die Bahn nach dem Punkt i (im Vorschub) im Eilgang ab, fährt hinüber und hinab und
    taucht senkrecht auf derselben Höhe oder tiefer wieder ein? Dann der Index des letzten
    Eilgangs, sonst None."""
    a = punkte[i]
    if a.eilgang or i + 2 >= len(punkte):
        return None
    hoch = punkte[i + 1]
    if not hoch.eilgang or math.hypot(hoch.x - a.x, hoch.y - a.y) > GLEICH or hoch.z <= a.z:
        return None
    j = i + 1
    while j + 1 < len(punkte) and punkte[j + 1].eilgang:
        j += 1
    if j + 1 >= len(punkte):
        return None  # das Ende der Bahn: hinauf bleibt
    b, p = punkte[j], punkte[j + 1]
    if p.bogen is not None or math.hypot(p.x - b.x, p.y - b.y) > GLEICH or p.z > a.z + GLEICH:
        return None
    if any(punkte[k].z < a.z - GLEICH for k in range(i + 1, j)):
        return None
    return j


def _unten_bleiben(punkte, i, quader, weite):
    """Ersetzt in `punkte` ein unnötiges Abheben nach Punkt i (_abheben) durch den Weg auf seiner
    Höhe – wenn der frei ist und ganz über dem Rohteil liegt (`quader`: das Material genau hier)."""
    j = _abheben(punkte, i)
    if j is None:
        return
    a, b = punkte[i], punkte[j]
    von, nach = (a.x, a.y, a.z), (b.x, b.y, a.z)
    x0, x1 = min(von[0], nach[0]) - weite, max(von[0], nach[0]) + weite
    y0, y1 = min(von[1], nach[1]) - weite, max(von[1], nach[1]) + weite
    if x0 < quader.x[0] or x1 > quader.x[-1] or y0 < quader.y[0] or y1 > quader.y[-1]:
        return  # nicht ganz über dem Rohteil
    if _frei(quader, von, nach, weite):
        ersatz = [bn.Punkt(False, b.x, b.y, a.z)]
        if b.z < a.z - GLEICH:
            ersatz.append(b)  # tiefer war Luft: im Eilgang dorthin, wie die Strategie es wollte
        punkte[i + 1 : j + 1] = ersatz
        return
    # Nicht frei: nur so hoch, wie das Material im Umkreis es verlangt.
    oben = max(punkte[k].z for k in range(i + 1, j + 1))
    link = max(_hoechstes(quader, von, nach, weite), a.z) + LINK_LUFT
    if link >= oben - GLEICH:
        return
    ersatz = [bn.Punkt(True, a.x, a.y, link), bn.Punkt(True, b.x, b.y, link)]
    if b.z < link - GLEICH:
        ersatz.append(b)
    punkte[i + 1 : j + 1] = ersatz


def freivorschub_fuer(job):
    """Der Freivorschub (mm/min) für einen Job: der kleinste Höchstvorschub der Linearachsen
    seiner Maschine (die gemerkte – maschinenspeicher kennt ihn, ohne die Datei zu öffnen);
    ohne Maschine oder ohne eingetragenen Höchstvorschub FREIVORSCHUB (Manuel, 2026-10-04: „die
    Eilganggeschwindigkeit sollte ja in der Maschine stehen … wenn nichts drinnen steht, dann
    halt 10 m/min“)."""
    from . import maschinenspeicher as msp
    from . import reichweite as rw

    try:
        pfad = rw.gemerkte_maschine(job)
        eintrag = msp.finde(msp.laden(), pfad) if pfad else None
    except Exception:
        eintrag = None
    vorschub = float(getattr(eintrag, "vorschub", 0.0) or 0.0)
    return vorschub if vorschub > 0 else FREIVORSCHUB


def fuer_operation(job, op, punkte, vorschub, form=None, freivorschub=None):
    """schneller() für die Operation `op` im Job: das Material vor ihr (materialstand), ihr
    Fräser, der Freivorschub ihrer Maschine (`freivorschub`: höchstens so viel) – unverändert
    ohne Rohteil im Quader oder ohne Form."""
    from . import materialstand as mst
    from . import vierachs_schlichten as vs

    if form is None:
        form = vs.form_des_controllers(getattr(op, "ToolController", None))
    stand = mst.fuer(job, vor=op) if form is not None else None
    if stand is None:
        return list(punkte), 0.0
    quader = mst._kopie(stand).quader
    maschine = freivorschub_fuer(job)
    frei = min(freivorschub, maschine) if freivorschub else maschine
    return schneller(punkte, form, quader, vorschub, frei)
