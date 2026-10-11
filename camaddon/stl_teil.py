# SPDX-License-Identifier: LGPL-2.1-or-later
"""Ein STL als Teil (W-017; Manuel, 2026-10-11: „sowas … auf der 4-Achs aus einem Rundstahl
rausfräsen, soweit es eben möglich ist … einfach dass STL-Dateien funktionieren würden“).

Aus dem Netz wird ein Körper aus genau seinen Dreiecken (`makeShapeFromMesh`, ohne Glätten): Was man
sieht, ist, was gefräst wird (Manuel: „die Bahn … wenn nicht das abbildet, was ich sehe … ist doch
Quatsch“). Der vorhandene Code rechnet darauf wie auf jedem Körper; eine Standfläche ist eine Menge
ebener Dreiecke, ihr Anklicken wählt die Achse wie an jedem Teil.

Vorher, gemeldet im Bericht (Manuel, 2026-10-11):
- skalieren – ein STL hat keine Einheit, gelesen in mm; der Maßstab macht es passend („vielleicht
  kann man es skalieren“);
- reparieren – doppelte Punkte und Dreiecke, entartete Dreiecke, Normalen einheitlich; Löcher
  schließen („Löcher schließen?“) – bleibt es offen, rechnet es trotzdem, der Bericht sagt es;
- vereinfachen ab VEREINFACHEN_AB Dreiecken, aber nur so weit, wie die Abweichung nachgemessen
  höchstens ABWEICHUNG bleibt („Ja, bis 0,01 mm“) – FreeCADs `decimate` hält seine eigene Toleranz
  nicht ein (am Geist 0,85 mm an einer Kante bei „0,01“), darum je Stufe geprüft, sonst genau.

Das Netz bleibt im Dokument (ausgeblendet), der Körper verweist darauf (EIGENSCHAFT_STL). Das
vorbereitete Netz trägt der Körper selbst (EIGENSCHAFT_NETZ): Wer ihn vernetzen will – Hüllfläche,
Schlichten –, nimmt dessen Dreiecke in der Lage der Form (netz_fuer), statt 68.242 Flächen von
OpenCascade vernetzen zu lassen (am Geist 1 GB je Nebenrechner, P-2026-10-11-100). Läuft ohne
Oberfläche; das Fenster dazu in gui_stl.
"""

import math
from dataclasses import dataclass

import FreeCAD
import numpy as np
import Part

from .sprache import tr

EIGENSCHAFT_STL = "CamAddonAusStl"
EIGENSCHAFT_NETZ = "CamAddonNetz"  # das vorbereitete Netz, aus dem der Körper besteht
NETZ_AB = 500  # Flächen: erst so große Formen sucht netz_fuer() (kleine vernetzt OCC schnell)
NETZ_GENAU = 1e-3  # mm: so genau deckt sich das Netz mit dem Hüllquader der Form
VEREINFACHEN_AB = 200_000  # Dreiecke
ABWEICHUNG = 0.01  # mm – so weit darf ein vereinfachtes Netz höchstens vom gelesenen abweichen
STUFEN = (0.8, 0.6, 0.4, 0.2)  # „decimate“: um so viel höchstens weniger Dreiecke, je Versuch
PROBEN = 3000  # so viele Punkte des gelesenen Netzes prüfen die Abweichung
NAEHEN = 1e-4  # mm – so nah gelten Ecken als dieselbe beim Zusammennähen der Dreiecke
LOCH_RAND = 10_000  # so viele Kanten darf der Rand eines Lochs haben, das geschlossen wird


@dataclass
class Bericht:
    """Was mit dem Netz geschah – für den Satz im Fenster."""

    dreiecke_gelesen: int = 0
    dreiecke: int = 0
    massstab: float = 1.0
    geschlossen: bool = True  # ein geschlossener Körper (sonst nur die Hülle)
    loecher_geschlossen: bool = False  # es war offen und ist es nicht mehr
    vereinfacht: bool = False
    abweichung: float = 0.0  # mm, nachgemessen, wenn vereinfacht
    masse: tuple = (0.0, 0.0, 0.0)  # Breite, Tiefe, Höhe in mm (nach dem Maßstab)

    def text(self):
        """Ein Satz, was geschah."""
        teile = [tr("stl.bericht.dreiecke", anzahl=f"{self.dreiecke:,}".replace(",", "\u202f"))]
        if self.massstab != 1.0:
            teile.append(tr("stl.bericht.massstab", faktor=f"{self.massstab:g}"))
        if self.vereinfacht:
            teile.append(
                tr(
                    "stl.bericht.vereinfacht",
                    vorher=f"{self.dreiecke_gelesen:,}".replace(",", "\u202f"),
                    abweichung=f"{self.abweichung:.4f}",
                )
            )
        if self.loecher_geschlossen:
            teile.append(tr("stl.bericht.loecher"))
        if not self.geschlossen:
            teile.append(tr("stl.bericht.offen"))
        return " ".join(teile)


def ist_netz(objekt):
    """Ein Netz-Objekt (Mesh::Feature, etwa ein eingelesenes STL)?"""
    return str(getattr(objekt, "TypeId", "")).startswith("Mesh::") and hasattr(objekt, "Mesh")


def aus_stl(objekt):
    """Stammt der Körper aus einem Netz (koerper_aus_netz)?"""
    return objekt is not None and EIGENSCHAFT_STL in getattr(objekt, "PropertiesList", ())


def masse(netz):
    """(Breite, Tiefe, Höhe) in mm des Netzes (Mesh.Mesh)."""
    bb = netz.BoundBox
    return bb.XLength, bb.YLength, bb.ZLength


def vorbereiten(netz, massstab=1.0):
    """(Mesh.Mesh, Bericht): eine Kopie, skaliert, repariert, wenn nötig vereinfacht."""
    if not math.isfinite(massstab) or massstab <= 0:
        raise ValueError(tr("stl.fehler.massstab"))
    m = netz.copy()
    bericht = Bericht(dreiecke_gelesen=m.CountFacets, massstab=massstab)
    if massstab != 1.0:
        # Um die Mitte der Unterseite: Eine Figur steht danach weiter, wo sie stand.
        bb = m.BoundBox
        bezug = FreeCAD.Vector(bb.Center.x, bb.Center.y, bb.ZMin)
        matrix = FreeCAD.Matrix()
        matrix.move(bezug * -1)
        skaliert = FreeCAD.Matrix()
        skaliert.scale(massstab, massstab, massstab)
        zurueck = FreeCAD.Matrix()
        zurueck.move(bezug)
        m.transform(zurueck.multiply(skaliert.multiply(matrix)))
    m.removeDuplicatedPoints()
    m.removeDuplicatedFacets()
    m.fixDegenerations(1e-9)
    m.harmonizeNormals()
    if _volumen(m) < 0:  # einheitlich, aber nach innen
        m.flipNormals()
    if not m.isSolid():
        m.fillupHoles(LOCH_RAND)
        bericht.loecher_geschlossen = m.isSolid()
    if m.CountFacets > VEREINFACHEN_AB:
        m, bericht.abweichung = vereinfachen(m)
        bericht.vereinfacht = m.CountFacets < bericht.dreiecke_gelesen
    bericht.dreiecke = m.CountFacets
    bericht.masse = masse(m)
    return m, bericht


def _volumen(netz):
    """Das Volumen mit Vorzeichen – negativ, wenn die Dreiecke nach innen zeigen (Mesh.Volume hat
    keins)."""
    p, d = netz.Topology
    if not d:
        return 0.0
    p = np.array([(q.x, q.y, q.z) for q in p], dtype=float)
    d = np.array(d, dtype=np.int64)
    a, b, c = p[d[:, 0]], p[d[:, 1]], p[d[:, 2]]
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)


def vereinfachen(netz, grenze=ABWEICHUNG):
    """(Mesh.Mesh, Abweichung in mm): so viel weniger Dreiecke, wie es mit höchstens `grenze`
    Abweichung geht – nachgemessen an PROBEN Punkten des gelesenen Netzes und an allen Ecken des
    vereinfachten; geht keine Stufe, das Netz selbst (Abweichung 0)."""
    punkte = _punkte(netz)
    rng = np.random.default_rng(0)
    proben = punkte[rng.choice(len(punkte), min(PROBEN, len(punkte)), replace=False)]
    for stufe in STUFEN:
        kandidat = netz.copy()
        kandidat.decimate(grenze, stufe)
        if kandidat.CountFacets >= netz.CountFacets:
            continue
        hin = _abstaende(proben, kandidat)
        her = _abstaende(_punkte(kandidat)[:PROBEN], netz)
        abweichung = float(max(hin.max(initial=0.0), her.max(initial=0.0)))
        if abweichung <= grenze:
            return kandidat, abweichung
    return netz, 0.0


def _punkte(netz):
    return np.array([(p.x, p.y, p.z) for p in netz.Topology[0]], dtype=float)


def _abstaende(punkte, netz):
    """Je Punkt sein Abstand zum Netz (genau: der nächste Punkt auf einem Dreieck, Ericson) –
    gegen die Dreiecke, deren Umriss ±1 mm um den Punkt liegt."""
    p_netz, dreiecke = netz.Topology
    p = np.array([(q.x, q.y, q.z) for q in p_netz], dtype=float)
    d = np.array(dreiecke, dtype=np.int64).reshape(-1, 3)
    a, b, c = p[d[:, 0]], p[d[:, 1]], p[d[:, 2]]
    unten = np.minimum(np.minimum(a, b), c) - 1.0
    oben = np.maximum(np.maximum(a, b), c) + 1.0
    ergebnis = np.full(len(punkte), np.inf)
    for i, q in enumerate(punkte):
        nah = np.flatnonzero(np.all((q >= unten) & (q <= oben), axis=1))
        if len(nah):
            ergebnis[i] = float(np.min(_punkt_dreieck(q, a[nah], b[nah], c[nah])))
    return ergebnis


def _punkt_dreieck(q, a, b, c):
    """Abstand des Punkts q zu den Dreiecken (a, b, c) – je Dreieck der nächste Punkt (Ericson,
    Real-Time Collision Detection 5.1.5), vektorisiert."""
    ab, ac, ap = b - a, c - a, q - a
    d1, d2 = np.einsum("ij,ij->i", ab, ap), np.einsum("ij,ij->i", ac, ap)
    bp = q - b
    d3, d4 = np.einsum("ij,ij->i", ab, bp), np.einsum("ij,ij->i", ac, bp)
    cp = q - c
    d5, d6 = np.einsum("ij,ij->i", ab, cp), np.einsum("ij,ij->i", ac, cp)
    va = d3 * d6 - d5 * d4
    vb = d5 * d2 - d1 * d6
    vc = d1 * d4 - d3 * d2
    nenner = va + vb + vc
    sicher = np.where(np.abs(nenner) > 1e-300, nenner, 1.0)
    v = vb / sicher
    w = vc / sicher
    naechster = a + ab * v[:, None] + ac * w[:, None]  # innen
    # Die Fälle außen, in der Reihenfolge von Ericson (die spätere Zuweisung gewinnt nicht –
    # deshalb von hinten nach vorn: der zuerst zutreffende Fall setzt sich zuletzt durch).
    faelle = []
    t_bc = np.clip((d4 - d3) / np.where((d4 - d3) + (d5 - d6) != 0, (d4 - d3) + (d5 - d6), 1), 0, 1)
    faelle.append(((va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0), b + (c - b) * t_bc[:, None]))
    t_ac = d2 / np.where(d2 - d6 != 0, d2 - d6, 1)
    faelle.append(((vb <= 0) & (d2 >= 0) & (d6 <= 0), a + ac * t_ac[:, None]))
    faelle.append(((d6 >= 0) & (d5 <= d6), c))
    t_ab = d1 / np.where(d1 - d3 != 0, d1 - d3, 1)
    faelle.append(((vc <= 0) & (d1 >= 0) & (d3 <= 0), a + ab * t_ab[:, None]))
    faelle.append(((d3 >= 0) & (d4 <= d3), b))
    faelle.append(((d1 <= 0) & (d2 <= 0), a))
    for maske, punkt in faelle:
        naechster = np.where(maske[:, None], punkt, naechster)
    return np.linalg.norm(q - naechster, axis=1)


def koerper(netz):
    """Der Körper aus genau den Dreiecken des Netzes (Mesh.Mesh) – ein Solid, wenn das Netz
    geschlossen ist, sonst die Hülle."""
    huelle = Part.Shape()
    huelle.makeShapeFromMesh(netz.Topology, NAEHEN)
    if not netz.isSolid():  # offen: nur die Hülle (ein Solid daraus wäre keiner)
        return huelle
    try:
        form = Part.makeSolid(huelle)
    except Part.OCCError:
        return huelle
    # Kein isValid(): am Geist (68.242 Dreiecke) 4 s – das Netz ist schon als geschlossen geprüft.
    volumen = form.Volume
    if volumen < 0:  # die Dreiecke zeigen nach innen
        form.reverse()
    return form if volumen != 0 else huelle


def koerper_und_bericht(netz, massstab=1.0):
    """(Form, vorbereitetes Netz, Bericht): vorbereiten() und koerper() in einem."""
    netz, bericht = vorbereiten(netz, massstab)
    form = koerper(netz)
    bericht.geschlossen = form.ShapeType == "Solid"
    return form, netz, bericht


def koerper_rechnen(datei, massstab=1.0):
    """Auf einem Nebenrechner: (nebenrechner.Form, Bericht) zum Netz in der STL-Datei `datei` –
    koerper_und_bericht(); das vorbereitete Netz steht danach in `datei` (FreeCAD hält Netze in
    float32 wie das STL, nichts geht verloren). Am Geist (68.242 Dreiecke) 5 s, die das Fenster
    sonst stünde."""
    import Mesh

    from . import nebenrechner as nr

    form, netz, bericht = koerper_und_bericht(Mesh.Mesh(datei), massstab)
    netz.write(datei)
    return nr.Form.von(form), bericht


def koerper_aus_netz(dokument, netzobjekt, massstab=1.0, gerechnet=None):
    """(Part::Feature, Bericht): der Körper des Netzes `netzobjekt` im Dokument – ohne eigene
    Transaktion (der Aufrufer hält sie). `gerechnet`: (Form, vorbereitetes Netz, Bericht), schon
    woanders gerechnet (koerper_rechnen). Die Punkte des Netzes enthalten seine Platzierung schon;
    der Körper liegt deshalb ohne eigene da – das vorbereitete Netz ist so zugleich sein Netz im
    eigenen Koordinatensystem (EIGENSCHAFT_NETZ)."""
    form, netz, bericht = gerechnet or koerper_und_bericht(netzobjekt.Mesh, massstab)
    teil = dokument.addObject("Part::Feature", "TeilAusStl")
    teil.Label = tr("stl.teil", name=netzobjekt.Label)
    teil.Shape = form
    teil.addProperty("App::PropertyLink", EIGENSCHAFT_STL, "CAM-Addon", tr("stl.eigenschaft"))
    setattr(teil, EIGENSCHAFT_STL, netzobjekt)
    teil.setEditorMode(EIGENSCHAFT_STL, 1)  # nur lesen
    teil.addProperty("Mesh::PropertyMeshKernel", EIGENSCHAFT_NETZ, "CAM-Addon", tr("stl.netz"))
    setattr(teil, EIGENSCHAFT_NETZ, netz)
    teil.setEditorMode(EIGENSCHAFT_NETZ, 2)  # versteckt
    return teil, bericht


_ARRAYS = {}  # (Dokument, Objekt, Dreiecke, Punkte) -> (Punkte (n, 3), Dreiecke (m, 3))
_ARRAYS_HOECHSTENS = 4


def netz_fuer(form):
    """(Punkte (n, 3), Dreiecke (m, 3)) der Form (Part.Shape), wenn sie ein Körper aus einem STL
    ist oder sein Klon im Job: das Netz, das der Körper trägt (EIGENSCHAFT_NETZ), in der Lage der
    Form – sonst None. Erkannt an der Zahl der Flächen (ein Dreieck je Fläche) und daran, dass
    sich das Netz in dieser Lage mit dem Hüllquader der Form deckt; gesucht in allen offenen
    Dokumenten (auch denen der Nebenrechner). Die Dreiecke zeigen nach außen (vorbereiten)."""
    try:
        anzahl = form.countElement("Face")
    except (AttributeError, RuntimeError, ValueError):
        return None
    if anzahl < NETZ_AB:
        return None
    kasten = None
    for schluessel, netz in _netze_mit(anzahl):
        if kasten is None:
            kasten = form.BoundBox
        punkte, dreiecke = _arrays(schluessel, netz)
        matrix = np.array(form.Placement.toMatrix().A, dtype=float).reshape(4, 4)
        im_job = punkte @ matrix[:3, :3].T + matrix[:3, 3]
        unten, oben = im_job.min(axis=0), im_job.max(axis=0)
        soll = np.array(
            [kasten.XMin, kasten.YMin, kasten.ZMin, kasten.XMax, kasten.YMax, kasten.ZMax]
        )
        if np.all(np.abs(np.concatenate([unten, oben]) - soll) < NETZ_GENAU):
            return im_job, dreiecke
    return None


def _netze_mit(anzahl):
    """[(Schlüssel, Mesh.Mesh)] der Körper aus einem STL mit `anzahl` Dreiecken, in allen offenen
    Dokumenten."""
    gefunden = []
    for dokument in FreeCAD.listDocuments().values():
        for objekt in dokument.Objects:
            netz = getattr(objekt, EIGENSCHAFT_NETZ, None)
            if netz is not None and netz.CountFacets == anzahl:
                schluessel = (dokument.Name, objekt.Name, netz.CountFacets, netz.CountPoints)
                gefunden.append((schluessel, netz))
    return gefunden


def _arrays(schluessel, netz):
    """Punkte und Dreiecke des Netzes als numpy – je Körper einmal gerechnet."""
    eintrag = _ARRAYS.get(schluessel)
    if eintrag is None:
        p, d = netz.Topology
        eintrag = (
            np.array([(q.x, q.y, q.z) for q in p], dtype=float).reshape(-1, 3),
            np.array(d, dtype=np.int64).reshape(-1, 3),
        )
        _ARRAYS[schluessel] = eintrag
        while len(_ARRAYS) > _ARRAYS_HOECHSTENS:
            del _ARRAYS[next(iter(_ARRAYS))]
    return eintrag
