# SPDX-License-Identifier: LGPL-2.1-or-later
"""Hüllfläche und ebene Flächen von oben (W-006 S3, Abschnitt 7) – der Rechenkern für 2,5D:
Das Werkzeug steht senkrecht (z nach oben), die Spitze darf nur so tief, dass seine Form das
Teil nicht verletzt.

- ebenen_oben(): die ebenen Flächen des Teils, die nach oben schauen – Höhe und Ausdehnung.
- oberseite(): die davon, die am höchsten liegen – die Oberseite des Teils.
- netz_ohne(): das Teil ohne die gewählten Flächen – dagegen rechnet die Hüllfläche: Die
  Fläche selbst gibt die Tiefe vor, das Netz nur, was sonst im Weg ist.
- je_zeile(): die Hüllfläche je Zeile – wie vierachs_huelle.je_versatz, nur senkrecht: je
  Zeile (ein Versatz quer) die Höhen längs an Stellen im Raster, genau gegen Ecken, Kanten und
  Dreiecke des Netzes mit der Form des Fräsers (fraeserform). Ohne OCL, mit numpy.
- hoehen(): die Oberseite eines Netzes im Raster – je Zelle das höchste Dreieck über ihrer
  Mitte (das fertige Teil für den Vergleich im Quader, restmaterial, S3d).

Rahmen: x und y wie im Job, z nach oben; die Zeilen laufen längs x oder längs y. Läuft ohne
Oberfläche.
"""

import hashlib
from collections import OrderedDict
from dataclasses import dataclass

import FreeCAD
import numpy as np

from . import vierachs_huelle as vh

TOLERANZ = vh.TOLERANZ  # mm – so fein wird das Teil vernetzt
VORSCHAU_TOLERANZ = 0.05  # mm – für die Vorschau im Assistenten
HOEHE_GLEICH = 1e-3  # mm – ebene Flächen auf dieser Höhe gelten als eine Höhe
SCHRITT = vh.SCHRITT_A  # mm – Raster längs einer Zeile
KEIN_TREFFER = vh.KEIN_TREFFER  # die Spitze trifft das Teil an dieser Stelle nicht
GERADE = 1e-6  # so wenig darf eine Normale von „nach oben“ abweichen
_UEBER_NULL = 1.0  # mm – die Hüllfläche rechnet nur über 0: so weit hebt je_zeile() das Netz
# So viel darf das Rohteil über dem Ziel stehen, ohne eine Lage mehr zu bekommen: Die Hüllbox
# eines Zylinders liegt in OCC bis 0,05 mm neben der Form – ein Zapfen oben am Rohteil machte
# aus einer Lage von 20 zwei von 10 (Manuels Platte, P-2026-10-01-20).
LAGEN_SPIEL = 0.05  # mm


@dataclass(frozen=True)
class Ebene:
    """Eine ebene Fläche des Teils, die nach oben schaut (ebenen_oben())."""

    name: str  # „Face3“
    z: float  # ihre Höhe (mm)
    x_von: float
    x_bis: float
    y_von: float
    y_bis: float


def ebenen_oben(form, namen=(), toleranz=VORSCHAU_TOLERANZ):
    """[Ebene] – die Flächen `namen` („Face3“ …; leer: alle) von `form` (Part.Shape), die eben
    sind und nach oben schauen (Außennormale +z). Die Ausdehnung kommt aus der Vernetzung der
    Fläche (`toleranz`). Je Fläche einmal gerechnet (_EBENE): Der Assistent fragt je Vorschau
    über tausendmal nach denselben Flächen."""
    from . import vierachs_flaechen as vf

    nummern = vf.nummern(namen) if namen else range(len(form.Faces))
    ergebnis = []
    for nummer in nummern:
        if nummer >= len(form.Faces):
            continue
        ebene = _ebene(form, nummer, toleranz)
        if ebene is not None:
            ergebnis.append(ebene)
    return ergebnis


_EBENE = {}  # (Prüfsumme der Form, Nummer, Toleranz) → Ebene oder None
_EBENE_HOECHSTENS = 20000


def _ebene(form, nummer, toleranz):
    """Die Ebene der Fläche `nummer`, wenn sie eben ist und nach oben schaut – sonst None."""
    from . import vierachs_rohteil as vr

    flaeche = form.Faces[nummer]
    try:
        # Die Prüfsumme hängt am Speicher – mit dem Kasten der Fläche dazu verwechselt eine neue
        # Form an derselben Stelle ihre Flächen nicht mit den alten.
        kasten = flaeche.BoundBox
        schluessel = (
            form.hashCode(),
            nummer,
            tuple(round(v, 6) for v in (kasten.XMin, kasten.XMax, kasten.YMin, kasten.YMax,
                                        kasten.ZMin, kasten.ZMax)),
            round(float(toleranz), 6),
        )  # fmt: skip
    except Exception:  # eine Form ohne Prüfsumme: rechnen
        schluessel = None
    if schluessel is not None and schluessel in _EBENE:
        return _EBENE[schluessel]
    ebene = None
    if vr.ist_eben(flaeche) and vr.aussennormale(flaeche).z >= 1.0 - GERADE:
        punkte, _dreiecke = flaeche.copy().tessellate(toleranz)
        if punkte:
            p = np.array([[q.x, q.y, q.z] for q in punkte], dtype=float)
            ebene = Ebene(
                f"Face{nummer + 1}",
                float(p[:, 2].mean()),
                float(p[:, 0].min()),
                float(p[:, 0].max()),
                float(p[:, 1].min()),
                float(p[:, 1].max()),
            )
    if schluessel is not None:
        if len(_EBENE) >= _EBENE_HOECHSTENS:
            _EBENE.clear()
        _EBENE[schluessel] = ebene
    return ebene


def oberseite(form, toleranz=VORSCHAU_TOLERANZ):
    """Die Namen der ebenen Flächen nach oben, die am höchsten liegen („Face6“ …) – die
    Oberseite des Teils; [] ohne solche."""
    alle = ebenen_oben(form, (), toleranz)
    if not alle:
        return []
    hoch = max(e.z for e in alle)
    return [e.name for e in alle if e.z >= hoch - GERADE]


def netz_ohne(form, namen, toleranz=TOLERANZ):
    """Das Netz des Teils ohne die Flächen `namen` (vierachs_huelle.Netz)."""
    return netze_ohne(form, [namen], toleranz)[0]


def netze_ohne(form, namen_je, toleranz=TOLERANZ):
    """[Netz] – das Teil je Liste in `namen_je` ohne diese Flächen, einmal vernetzt. Nur die
    Punkte, die noch ein Dreieck braucht: Eine Ecke allein zählte sonst weiter (die Hüllfläche
    rechnet auch gegen Ecken – so sah die Kontur die Taschenwände, die sie ausgelassen hatte,
    P-2026-10-01-19)."""
    from . import vierachs_flaechen as vf

    fnetz = vf.vernetze(form, toleranz)
    ergebnis = []
    for namen in namen_je:
        bleibt = ~np.isin(fnetz.flaeche, np.asarray(vf.nummern(namen), dtype=np.int64))
        dreiecke = fnetz.netz.dreiecke[bleibt]
        benutzt = np.unique(dreiecke)
        neu = np.full(len(fnetz.netz.punkte), -1, dtype=np.int64)
        neu[benutzt] = np.arange(len(benutzt))
        ergebnis.append(vh.Netz(fnetz.netz.punkte[benutzt], neu[dreiecke], toleranz))
    return ergebnis


def netze_je_hoehe(form, ebenen, toleranz=TOLERANZ):
    """{Name der Fläche: Netz} – je gewählter ebener Fläche (Ebene) das Teil ohne die gewählten
    Flächen auf ihrer Höhe. Flächen auf anderen Höhen bleiben im Netz: Sie werden nur bis auf
    ihre eigene Höhe gefräst und stehen für eine tiefere noch als Material da. Aus einem Netz
    ohne alle gewählten Flächen sah der Boden einer Tasche neben sich keine Platte mehr – die
    Bahn wäre neben der Tasche ins Teil gefahren (P-2026-10-01-26)."""
    hoehen = []
    for e in ebenen:
        if not any(abs(e.z - z) <= HOEHE_GLEICH for z in hoehen):
            hoehen.append(e.z)
    namen_je = [[e.name for e in ebenen if abs(e.z - z) <= HOEHE_GLEICH] for z in hoehen]
    netze = netze_ohne(form, namen_je, toleranz) if hoehen else []
    ergebnis = {}
    for z, netz in zip(hoehen, netze, strict=True):
        for e in ebenen:
            if abs(e.z - z) <= HOEHE_GLEICH:
                ergebnis[e.name] = netz
    return ergebnis


def netz_fuer(netz, ebene):
    """Das Netz für die Fläche: aus netze_je_hoehe() (dict) oder das eine für alle."""
    return netz[ebene.name] if isinstance(netz, dict) else netz


# Die letzten Hüllflächen (je_zeile) – je Netz, Form und Raster. Die Vorschau im Assistenten
# rechnete dieselbe bis zu neunmal: Der Wettbewerb rechnet Blöcke noch einmal, und jede neue
# Vorschau alle (am Testteil 5,4 von 8,5 s in zwei Läufen, P-2026-10-03-28).
_ZWISCHEN = OrderedDict()
_ZWISCHEN_HOECHSTENS = 96


def _kennung(netz):
    """Ein Fingerabdruck des Netzes: seine Punkte und Dreiecke."""
    pruef = hashlib.blake2b(digest_size=16)
    for teil in (netz.punkte, netz.dreiecke):
        feld = np.ascontiguousarray(teil)
        pruef.update(str(feld.shape).encode())
        pruef.update(feld.tobytes())
    return pruef.digest()


def je_zeile(netz, form, v_werte, u0, schritt, anzahl, laengs_x=True):
    """Die Hüllfläche je Zeile: z[k, j] (mm) – so tief darf die Spitze eines Fräsers mit der
    Form `form` (fraeserform.Form) an der Stelle u0 + k · schritt auf der Zeile v_werte[j];
    KEIN_TREFFER, wo er das Teil nicht trifft. `u` ist die Stelle längs der Zeile – x mit
    `laengs_x`, sonst y –, `v` der Versatz quer. Dieselbe Rechnung kommt aus dem Zwischenspeicher
    (eine Kopie – wer sie ändert, ändert nicht das Gemerkte)."""
    v = np.ascontiguousarray(v_werte, dtype=float)
    schluessel = (
        _kennung(netz),
        form,
        v.tobytes(),
        float(u0),
        float(schritt),
        int(anzahl),
        bool(laengs_x),
    )
    gemerkt = _ZWISCHEN.get(schluessel)
    if gemerkt is not None:
        _ZWISCHEN.move_to_end(schluessel)
        return gemerkt.copy()
    ergebnis = _je_zeile(netz, form, v, u0, schritt, anzahl, laengs_x)
    _ZWISCHEN[schluessel] = ergebnis.copy()
    while len(_ZWISCHEN) > _ZWISCHEN_HOECHSTENS:
        _ZWISCHEN.popitem(last=False)
    return ergebnis


# Nebenrechner (P-2026-10-09-11): ab so vielen Zeilen und Dreiecken gehen die Zeilen in Stücken an
# sie – eine Zeile am Rand ist billig, eine in der Mitte teuer, deshalb viele kleine Stücke.
PARALLEL_AB_ZEILEN = 24
PARALLEL_AB_DREIECKE = 2000
STUECKE_JE_ARBEITER = 6


def _je_zeile(netz, form, v_werte, u0, schritt, anzahl, laengs_x):
    """je_zeile() ohne Zwischenspeicher – auf den Nebenrechnern, wenn es sich lohnt."""
    if len(v_werte) >= PARALLEL_AB_ZEILEN and len(netz.dreiecke) >= PARALLEL_AB_DREIECKE:
        ergebnis = _je_zeile_verteilt(netz, form, v_werte, u0, schritt, anzahl, laengs_x)
        if ergebnis is not None:
            return ergebnis
    return zeilen_stueck(netz, form, v_werte, u0, schritt, anzahl, laengs_x)


def _je_zeile_verteilt(netz, form, v_werte, u0, schritt, anzahl, laengs_x):
    """Die Zeilen in Stücken auf den Nebenrechnern; None ohne sie (dann rechnet der Aufrufer
    selbst). Das Netz geht einmal je Arbeiter hin (Gemeinsam, nach seinem Fingerabdruck)."""
    from . import nebenrechner as nr

    pool = nr.pool()
    if not pool.verfuegbar() or pool.anzahl < 2:
        return None
    netz_gemeinsam = pool.gemeinsam("netz-" + _kennung(netz).hex(), netz)
    zeilen = len(v_werte)
    stuecke = max(1, min(pool.anzahl * STUECKE_JE_ARBEITER, zeilen // 2))
    grenzen = [round(k * zeilen / stuecke) for k in range(stuecke + 1)]
    bereiche = [(a, b) for a, b in zip(grenzen, grenzen[1:], strict=False) if b > a]
    auftraege = [
        pool.auftrag(
            "hoehenfeld",
            "zeilen_stueck",
            netz_gemeinsam,
            form,
            v_werte[a:b],
            u0,
            schritt,
            anzahl,
            laengs_x,
        )
        for a, b in bereiche
    ]
    try:
        teile = pool.warten(auftraege, zwischendurch=_ereignisse)
    except nr.Fehler as fehler:
        FreeCAD.Console.PrintWarning(
            f"CAM-Addon: Hüllfläche auf den Nebenrechnern gescheitert, rechne hier: {fehler}\n"
        )
        return None
    ergebnis = np.full((anzahl, zeilen), KEIN_TREFFER)
    for (a, b), teil in zip(bereiche, teile, strict=True):
        ergebnis[:, a:b] = teil
    return ergebnis


def _ereignisse():
    """Beim Warten auf die Nebenrechner: das Fenster verarbeitet seine Ereignisse – ohne
    Oberfläche nichts."""
    try:
        from PySide import QtGui
    except ImportError:
        return True
    if QtGui.QApplication.instance() is not None:
        QtGui.QApplication.processEvents()
    return True


# (Netz, seine Kanten) – je Netz einmal: Ein Arbeiter rechnet viele Stücke desselben Netzes.
_kanten_gemerkt = (None, None)


def zeilen_stueck(netz, form, v_werte, u0, schritt, anzahl, laengs_x):
    """Die Hüllfläche für diese Zeilen (wie je_zeile, ein Stück) – im Nebenrechner oder hier."""
    global _kanten_gemerkt
    punkte = netz.punkte
    a = punkte[:, 0] if laengs_x else punkte[:, 1]
    quer = punkte[:, 1] if laengs_x else punkte[:, 0]
    z = punkte[:, 2]
    # Die Hüllfläche zählt nur, was über 0 liegt (rundum: vor der Achse) – das Netz so weit
    # heben, dass alles über 0 liegt, und das Ergebnis wieder senken.
    hub = _UEBER_NULL - float(z.min()) if len(z) and z.min() <= 0.0 else 0.0
    x = z + hub
    if _kanten_gemerkt[0] is not netz:
        _kanten_gemerkt = (netz, vh._kanten(netz.dreiecke))
    kanten = _kanten_gemerkt[1]
    r = np.full((anzahl, len(v_werte)), KEIN_TREFFER)
    for j, v in enumerate(v_werte):
        spalte = np.full(anzahl, KEIN_TREFFER)
        vh._form_treffen(
            spalte, a, x, quer - float(v), kanten, netz.dreiecke, form, float(u0), schritt
        )
        r[:, j] = np.where(np.isfinite(spalte), spalte - hub, spalte)
    return r


_RAND = 1e-7  # so weit außerhalb eines Dreiecks zählt eine Zellenmitte noch dazu (Kanten)


def hoehen(netz, x, y, innen=False):
    """z[i, j] (mm): die Oberseite des Netzes über (x[i], y[j]) – das höchste Dreieck, unter
    dem die Zellenmitte liegt; KEIN_TREFFER, wo keins liegt. Senkrechte Dreiecke tragen nichts
    bei; eine Mitte genau auf einer Kante zählt zu beiden Dreiecken – mit `innen` zu keinem
    (die Zellen der gewählten Flächen: am Rand zu einer höheren Fläche wüsste das Raster nicht,
    welche gilt)."""
    rand = -_RAND if innen else _RAND
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    z = np.full((len(x), len(y)), KEIN_TREFFER)
    dreiecke = netz.dreiecke
    if not len(dreiecke) or not len(x) or not len(y):
        return z
    p = netz.punkte
    a, b, c = p[dreiecke[:, 0]], p[dreiecke[:, 1]], p[dreiecke[:, 2]]
    v0, v1 = b - a, c - a
    det = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
    x_min = np.minimum(np.minimum(a[:, 0], b[:, 0]), c[:, 0])
    x_max = np.maximum(np.maximum(a[:, 0], b[:, 0]), c[:, 0])
    y_min = np.minimum(np.minimum(a[:, 1], b[:, 1]), c[:, 1])
    y_max = np.maximum(np.maximum(a[:, 1], b[:, 1]), c[:, 1])
    saum = 1e-9
    i_von = np.searchsorted(x, x_min - saum)
    i_bis = np.searchsorted(x, x_max + saum, "right")
    j_von = np.searchsorted(y, y_min - saum)
    j_bis = np.searchsorted(y, y_max + saum, "right")
    for k in np.flatnonzero((np.abs(det) > 1e-12) & (i_von < i_bis) & (j_von < j_bis)):
        i0, i1, j0, j1 = i_von[k], i_bis[k], j_von[k], j_bis[k]
        px = (x[i0:i1] - a[k, 0])[:, None]
        py = (y[j0:j1] - a[k, 1])[None, :]
        l1 = (px * v1[k, 1] - py * v1[k, 0]) / det[k]
        l2 = (py * v0[k, 0] - px * v0[k, 1]) / det[k]
        drin = (l1 >= -rand) & (l2 >= -rand) & (l1 + l2 <= 1.0 + rand)
        if not drin.any():
            continue
        hoehe = a[k, 2] + l1 * v0[k, 2] + l2 * v1[k, 2]
        block = z[i0:i1, j0:j1]
        np.maximum(block, np.where(drin, hoehe, KEIN_TREFFER), out=block)
    return z
