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

Rahmen: x und y wie im Job, z nach oben; die Zeilen laufen längs x oder längs y. Läuft ohne
Oberfläche.
"""

from dataclasses import dataclass

import numpy as np

from . import vierachs_huelle as vh

TOLERANZ = vh.TOLERANZ  # mm – so fein wird das Teil vernetzt
VORSCHAU_TOLERANZ = 0.05  # mm – für die Vorschau im Assistenten
SCHRITT = vh.SCHRITT_A  # mm – Raster längs einer Zeile
KEIN_TREFFER = vh.KEIN_TREFFER  # die Spitze trifft das Teil an dieser Stelle nicht
GERADE = 1e-6  # so wenig darf eine Normale von „nach oben“ abweichen
_UEBER_NULL = 1.0  # mm – die Hüllfläche rechnet nur über 0: so weit hebt je_zeile() das Netz


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
    Fläche (`toleranz`)."""
    from . import vierachs_flaechen as vf
    from . import vierachs_rohteil as vr

    nummern = vf.nummern(namen) if namen else range(len(form.Faces))
    ergebnis = []
    for nummer in nummern:
        if nummer >= len(form.Faces):
            continue
        flaeche = form.Faces[nummer]
        if not vr.ist_eben(flaeche):
            continue
        if vr.aussennormale(flaeche).z < 1.0 - GERADE:
            continue
        punkte, _dreiecke = flaeche.copy().tessellate(toleranz)
        if not punkte:
            continue
        p = np.array([[q.x, q.y, q.z] for q in punkte], dtype=float)
        ergebnis.append(
            Ebene(
                f"Face{nummer + 1}",
                float(p[:, 2].mean()),
                float(p[:, 0].min()),
                float(p[:, 0].max()),
                float(p[:, 1].min()),
                float(p[:, 1].max()),
            )
        )
    return ergebnis


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
    from . import vierachs_flaechen as vf

    fnetz = vf.vernetze(form, toleranz)
    bleibt = ~np.isin(fnetz.flaeche, np.asarray(vf.nummern(namen), dtype=np.int64))
    return vh.Netz(fnetz.netz.punkte, fnetz.netz.dreiecke[bleibt], toleranz)


def je_zeile(netz, form, v_werte, u0, schritt, anzahl, laengs_x=True):
    """Die Hüllfläche je Zeile: z[k, j] (mm) – so tief darf die Spitze eines Fräsers mit der
    Form `form` (fraeserform.Form) an der Stelle u0 + k · schritt auf der Zeile v_werte[j];
    KEIN_TREFFER, wo er das Teil nicht trifft. `u` ist die Stelle längs der Zeile – x mit
    `laengs_x`, sonst y –, `v` der Versatz quer."""
    punkte = netz.punkte
    a = punkte[:, 0] if laengs_x else punkte[:, 1]
    quer = punkte[:, 1] if laengs_x else punkte[:, 0]
    z = punkte[:, 2]
    # Die Hüllfläche zählt nur, was über 0 liegt (rundum: vor der Achse) – das Netz so weit
    # heben, dass alles über 0 liegt, und das Ergebnis wieder senken.
    hub = _UEBER_NULL - float(z.min()) if len(z) and z.min() <= 0.0 else 0.0
    x = z + hub
    kanten = vh._kanten(netz.dreiecke)
    r = np.full((anzahl, len(v_werte)), KEIN_TREFFER)
    for j, v in enumerate(v_werte):
        spalte = np.full(anzahl, KEIN_TREFFER)
        vh._form_treffen(
            spalte, a, x, quer - float(v), kanten, netz.dreiecke, form, float(u0), schritt
        )
        r[:, j] = np.where(np.isfinite(spalte), spalte - hub, spalte)
    return r
