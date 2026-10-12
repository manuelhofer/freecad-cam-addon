# SPDX-License-Identifier: LGPL-2.1-or-later
"""Schruppen in der N-Eck-Stange (W-018): wie „Rundum schruppen“ der 4 Achsen, nur ohne vierte
Achse – je Aufspannung von oben, von der Stirn zum Schraubstock, je Lage ohne abzuheben.

Manuel (2026-10-12) zum 3D-Schruppen in Ringen: „die Stiche, die du da fährst … Wahnsinn und
unnötig … man fängt an dem Kopf an, schruppt mit dem 12er Schaftfräser die grobe Struktur raus,
und da muss man nicht einmal abheben … ap muss eingehalten werden, und dann wird einmal abgehoben,
um von vorne wieder anzufangen … einfach von vorne, weit weg vom Schraubstock, hin zum
Schraubstock arbeiten“; „effektiv wie die 4-Achs-Strategie, nur ohne 4. Achse“.

- **Lagen** von oben je höchstens ap (und die Schneidenlänge) bis auf die Achse der Stange (z 0):
  Darunter liegt, was die gegenüberliegenden Aufspannungen von ihrer Oberseite her nehmen – jede
  Stelle neben dem Teil liegt in einer Aufspannung über der Achse.
- **In einer Lage** Zeilen quer zur Stange (längs y) im Abstand ae, von der Stirn zum
  Schraubstock, im Zickzack; die Spitze auf der Lage, wo das Teil höher steht auf seiner
  Hüllfläche (sie klettert darüber, statt abzuheben). Jede Zeile nur so breit, wie unter dem
  Fräser Material über der Spitze steht; eine Zeile ohne fällt weg. Von Zeile zu Zeile so hoch,
  wie die Hüllfläche dazwischen es verlangt (ein feineres Raster von Zeilen).
- **Am Ende der Lage** einmal abheben, im Eilgang zurück nach vorn, die nächste Lage.
- **Zum Schraubstock** höchstens bis `x_ende` (die Mitte des Fräsers; n_eck: vor den Backen).
- Das Material: der Materialstand (W-012: die N-Eck-Stange, in einer weiteren Aufspannung, was
  die davor übrig ließen); ohne ihn das Rohteil als Kasten bis `oben`.

Gerechnet in x, y, z des Jobs (bahn.Punkt). Läuft ohne Oberfläche.
"""

import math

import numpy as np

from . import bahn as bn
from . import fraeserform as ff
from . import hoehenfeld as hf
from . import vierachs_bahn as vb

SCHRITT = 0.5  # mm – das Raster längs der Zeilen und der feineren Zeilen dazwischen
VORSCHAU_SCHRITT = 1.0
BODEN = 0.0  # z der tiefsten Lage: die Achse der Stange
MATERIAL = 0.5  # mm – so viel muss über der Spitze stehen, damit es als Material zählt (dünner:
# Treppchen der Aufspannung davor; bleibt fürs Schlichten)
TIEF = -1e9  # „keine Hüllfläche“ als Zahl (KEIN_TREFFER ist −inf)


def planen(netz, w, stand=None, x_ende=None, schritt=SCHRITT, boden=BODEN):
    """Die Bahn (schruppen3d_bahn.Schruppbahn, Variante „zeilen“) für das Netz `netz` des Teils
    (vierachs_huelle.Netz, im Job) mit den Werten `w` (raeumen_bahn.Raeumwerte); `stand`
    (materialstand.Materialstand) oder None; `x_ende`: die Mitte des Fräsers höchstens so weit
    zum Schraubstock (None: bis hinter das Teil). ValueError mit einem Satz, wenn nichts zu tun
    ist."""
    from . import schruppen3d_bahn as sb
    from .sprache import tr

    r = float(w.form.radius)
    zugabe = max(float(w.aufmass), 0.0) + netz.toleranz + vb.RAND
    geformt = ff.scheibe(r + zugabe) if w.form.eben else w.form.mit_aufmass(zugabe)
    x_von, x_bis, y_von, y_bis = w.rohteil
    if x_ende is None:
        x_ende = float(netz.punkte[:, 0].max()) + r
    x_ende = min(float(x_ende), x_bis + r)
    # Fein (schritt) in x – jede k-te Zeile wird gefahren, die dazwischen sichern den Weg. Die
    # erste feine Zeile steht ganz vor der Stirn, die erste gefahrene ae dahinter.
    xs = np.arange(x_von - r, x_ende + 1e-9, schritt)
    y0 = y_von - r - schritt
    anzahl = int(math.ceil((y_bis + r + schritt - y0) / schritt)) + 1
    ys = y0 + schritt * np.arange(anzahl)
    huelle = hf.je_zeile(netz, geformt, ys, float(xs[0]), schritt, len(xs), laengs_x=True)
    # je_zeile: [k, j] – k längs x, j die Zeile in y; hier [x, y].
    spitze = np.where(np.isfinite(huelle), huelle + zugabe, TIEF)
    material = _material(stand, xs, ys, w)
    unter = _umkreis_max(material, int(math.ceil(r / schritt)))  # unter dem Fräser das Höchste
    zustellung = float(w.zustellung)
    if w.schneidenlaenge > 0:
        zustellung = min(zustellung, float(w.schneidenlaenge))
    hoechstes = float(np.max(unter))
    if not math.isfinite(hoechstes):
        raise ValueError(tr("r3.fehler.nichts"))
    lagen = _lagen(min(float(w.oben), hoechstes), boden, zustellung)
    jede = max(1, int(round(float(w.zeilenabstand) / schritt)))
    gefahren_x = list(range(jede, len(xs), jede))
    if gefahren_x and gefahren_x[-1] != len(xs) - 1:
        gefahren_x.append(len(xs) - 1)
    punkte = [bn.Punkt(True, float(xs[0]), float(ys[0]), float(w.sicher))]
    zeilen = gefahrene_lagen = 0
    z_min = math.inf
    for z_lage in lagen:
        tief = np.maximum(spitze, z_lage)  # [x, y]: die Spitze in dieser Lage
        schnitt = unter > tief + MATERIAL
        stuecke = []
        for i in gefahren_x:
            spalten = np.flatnonzero(schnitt[i])
            if spalten.size:
                stuecke.append(
                    (i, max(int(spalten[0]) - 1, 0), min(int(spalten[-1]) + 1, anzahl - 1))
                )
        if not stuecke:
            continue
        gefahrene_lagen += 1
        vorwaerts = True
        vorige = None
        for i, a, b in stuecke:
            spalten = np.arange(a, b + 1) if vorwaerts else np.arange(b, a - 1, -1)
            x = float(xs[i])
            anfang = int(spalten[0])
            if vorige is None:
                # Anfang der Lage: neben dem Material im Eilgang hinab, dann hinein.
                ueber = min(float(w.sicher), float(tief[i, anfang]) + float(w.sicherheit))
                punkte.append(bn.Punkt(True, x, float(ys[anfang]), float(w.sicher)))
                punkte.append(bn.Punkt(True, x, float(ys[anfang]), ueber))
                punkte.append(
                    bn.Punkt(False, x, float(ys[anfang]), float(tief[i, anfang]), eintauchen=True)
                )
            else:
                # Zur nächsten Zeile: über dem höchsten Punkt der Hüllfläche im Rechteck dazwischen.
                i0, k0 = vorige
                k_lo, k_hi = min(k0, anfang), max(k0, anfang)
                z_weg = float(np.max(tief[i0 : i + 1, k_lo : k_hi + 1]))
                if z_weg > punkte[-1].z + 1e-9:
                    punkte.append(bn.Punkt(False, punkte[-1].x, punkte[-1].y, z_weg))
                punkte.append(bn.Punkt(False, x, float(ys[anfang]), max(z_weg, punkte[-1].z)))
                if float(tief[i, anfang]) < punkte[-1].z - 1e-9:
                    punkte.append(bn.Punkt(False, x, float(ys[anfang]), float(tief[i, anfang])))
            for k in spalten[1:]:
                punkte.append(bn.Punkt(False, x, float(ys[k]), float(tief[i, k])))
            z_min = min(z_min, float(np.min(tief[i, a : b + 1])))
            zeilen += 1
            vorige = (i, int(spalten[-1]))
            vorwaerts = not vorwaerts
        punkte.append(bn.Punkt(True, punkte[-1].x, punkte[-1].y, float(w.sicher)))
    if not zeilen:
        raise ValueError(tr("r3.fehler.nichts"))
    punkte = _zusammen(punkte)
    laenge = sum(
        math.dist((a.x, a.y, a.z), (b.x, b.y, b.z))
        for a, b in zip(punkte, punkte[1:], strict=False)
        if not b.eilgang
    )
    zeit = bn.zeit(
        punkte,
        w.vorschub if w.vorschub > 0 else 1000.0,
        w.eintauchen or None,
        w.eilgang or None,
        w.beschleunigung or None,
    )
    return sb.Schruppbahn(
        punkte, gefahrene_lagen, 0, zeilen, gefahrene_lagen, z_min, laenge, zeit, "zeilen"
    )


def _lagen(oben, boden, zustellung):
    """Die Höhen der Lagen von oben – je höchstens `zustellung`, die letzte auf `boden`."""
    if oben <= boden + 1e-6:
        return [boden]
    anzahl = int(math.ceil((oben - boden) / zustellung - 1e-9))
    return [oben - (oben - boden) * (k + 1) / anzahl for k in range(anzahl)]


def _material(stand, xs, ys, w):
    """Je Stelle [x, y], bis wohin das Material steht (−inf: keins) – aus dem Materialstand,
    sonst das Rohteil als Kasten bis `w.oben`."""
    x_von, x_bis, y_von, y_bis = w.rohteil
    quader = getattr(stand, "quader", None)
    if quader is None:
        drin = (
            (xs[:, None] >= x_von)
            & (xs[:, None] <= x_bis)
            & (ys[None, :] >= y_von)
            & (ys[None, :] <= y_bis)
        )
        return np.where(drin, float(w.oben), -np.inf)
    i = _naechste(quader.x, xs)
    j = _naechste(quader.y, ys)
    h = quader.h[np.ix_(i, j)]
    halb_x = (quader.x[1] - quader.x[0]) / 2 if len(quader.x) > 1 else 0.0
    halb_y = (quader.y[1] - quader.y[0]) / 2 if len(quader.y) > 1 else 0.0
    aussen = (
        (xs[:, None] < quader.x[0] - halb_x)
        | (xs[:, None] > quader.x[-1] + halb_x)
        | (ys[None, :] < quader.y[0] - halb_y)
        | (ys[None, :] > quader.y[-1] + halb_y)
    )
    return np.where(aussen, -np.inf, h)


def _naechste(raster, werte):
    """Je Wert die Nummer des nächsten Punkts im (gleichmäßigen) Raster."""
    if len(raster) < 2:
        return np.zeros(len(werte), dtype=int)
    k = np.rint((werte - raster[0]) / (raster[1] - raster[0])).astype(int)
    return np.clip(k, 0, len(raster) - 1)


def _umkreis_max(feld, n):
    """Das Höchste im Quadrat ±n Zellen um jede Zelle (eine Schranke für den Kreis darin) –
    getrennt je Richtung, in Verdopplungsschritten."""
    ergebnis = feld
    for achse in (0, 1):
        breite = 0
        while breite < n:
            k = min(breite + 1, n - breite)  # [−breite, breite] → [−breite − k, breite + k]
            ergebnis = np.maximum(
                ergebnis, np.maximum(_schieben(ergebnis, k, achse), _schieben(ergebnis, -k, achse))
            )
            breite += k
    return ergebnis


def _schieben(feld, k, achse):
    """Das Feld um k Zellen längs `achse` verschoben, frei werdende Zellen −inf."""
    ergebnis = np.full_like(feld, -np.inf)
    if achse == 0:
        if k > 0:
            ergebnis[k:, :] = feld[:-k, :]
        else:
            ergebnis[:k, :] = feld[-k:, :]
    elif k > 0:
        ergebnis[:, k:] = feld[:, :-k]
    else:
        ergebnis[:, :k] = feld[:, -k:]
    return ergebnis


def _zusammen(punkte, toleranz=1e-4):
    """Vorschub-Punkte auf einer Geraden zusammenfassen."""
    if len(punkte) < 3:
        return punkte
    ergebnis = [punkte[0], punkte[1]]
    for p in punkte[2:]:
        a, b = ergebnis[-2], ergebnis[-1]
        gleich = not (b.eilgang or p.eilgang or b.eintauchen or p.eintauchen or a.eilgang)
        if gleich:
            v1 = np.array([b.x - a.x, b.y - a.y, b.z - a.z])
            v2 = np.array([p.x - b.x, p.y - b.y, p.z - b.z])
            n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
            if (
                n1 > 1e-12
                and n2 > 1e-12
                and np.dot(v1, v2) > 0
                and np.linalg.norm(np.cross(v1 / n1, v2 / n2)) < toleranz
            ):
                ergebnis[-1] = p
                continue
        ergebnis.append(p)
    return ergebnis
