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
import re
from collections import OrderedDict
from dataclasses import dataclass

import FreeCAD
import numpy as np
import Part

from .sprache import tr

EIGENSCHAFT_STL = "CamAddonAusStl"
EIGENSCHAFT_NETZ = "CamAddonNetz"  # das vorbereitete Netz, aus dem der Körper besteht
EIGENSCHAFT_FLAECHEN = "CamAddonNetzFlaechen"  # je Dreieck des Netzes die Nummer seiner Fläche
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
    return _koerper(netz)[0]


def _koerper(netz):
    """(koerper(), liegt Fläche i auf Dreieck i?) – geschlossen ohne Nähen (_schale), sonst
    genäht: Das Nähen ordnet die Flächen um."""
    schale = _schale(netz) if netz.isSolid() else None
    if schale is None:
        huelle = Part.Shape()
        huelle.makeShapeFromMesh(netz.Topology, NAEHEN)
    else:
        huelle = schale
    if not netz.isSolid():  # offen: nur die Hülle (ein Solid daraus wäre keiner)
        return huelle, False
    try:
        form = Part.makeSolid(huelle)
    except Part.OCCError:
        return huelle, False
    # Kein isValid(): am Geist (68.242 Dreiecke) 4 s – das Netz ist schon als geschlossen geprüft.
    # Das Vorzeichen aus dem Netz (dieselben Dreiecke, dieselbe Richtung): am Geist 0,001 statt
    # 0,7 s für form.Volume.
    volumen = netz.Volume
    if volumen < 0:  # die Dreiecke zeigen nach innen
        form.reverse()
    return (form, schale is not None) if volumen != 0 else (huelle, False)


# Der Verbund im BRep-Text: „Co“, eine leere Zeile, die sieben Merkmale (frei, geändert,
# geprüft, orientierbar, geschlossen, unendlich, konvex).
_VERBUND = re.compile(r"\nCo\n\n([01]{7})\n")


def _schale(netz):
    """Die Schale eines geschlossenen Netzes ohne Nähen – None, wenn es so nicht geht.
    `makeShapeFromMesh` ohne Nähen teilt Ecken und Kanten schon über die Nummern der Punkte und
    legt Fläche i auf Dreieck i, gibt aber nur einen Verbund der Flächen; im BRep-Text wird er
    zur Schale. Am Geist (68.242 Dreiecke) 2,1 + 1,0 s statt 3,7 s fürs Nähen und 1,7 s, die
    flaechen_der_dreiecke danach suchte; `Part.Shell` aus den Flächen braucht dort 30 s (die
    Namen der Elemente). Gleich in FreeCAD 1.1.4, 26.3 und 27.1."""
    try:
        verbund = Part.Shape()
        verbund.makeShapeFromMesh(netz.Topology, NAEHEN, False)
        text = verbund.exportBrepToString()
    except Exception:  # noqa: BLE001 – ältere Fassung ohne den dritten Wert, OCC: genäht
        return None
    treffer = list(_VERBUND.finditer(text))
    if len(treffer) != 1:
        return None
    merkmale = treffer[0].group(1)
    merkmale = merkmale[:3] + "11" + merkmale[5:]  # orientierbar, geschlossen
    text = f"{text[: treffer[0].start()]}\nSh\n\n{merkmale}\n{text[treffer[0].end() :]}"
    schale = Part.Shape()
    try:
        schale.importBrepFromString(text, False)
    except Exception:  # noqa: BLE001 – OCC
        return None
    if (
        schale.ShapeType != "Shell"
        or schale.countElement("Face") != netz.CountFacets
        or not schale.isClosed()  # aus den Kanten, nicht aus dem Merkmal
    ):
        return None
    return schale


def koerper_und_bericht(netz, massstab=1.0):
    """(Form, vorbereitetes Netz, Bericht, Fläche je Dreieck): vorbereiten(), koerper() und
    flaechen_der_dreiecke() in einem."""
    netz, bericht = vorbereiten(netz, massstab)
    form, der_reihe_nach = _koerper(netz)
    bericht.geschlossen = form.ShapeType == "Solid"
    if der_reihe_nach and _stichprobe_der_reihe_nach(form, netz):
        return form, netz, bericht, np.arange(netz.CountFacets, dtype=np.int64)
    return form, netz, bericht, flaechen_der_dreiecke(form, netz)


def _stichprobe_der_reihe_nach(form, netz):
    """Liegt Fläche i auf Dreieck i – nachgesehen an einigen (_schale legt sie so)?"""
    punkte, dreiecke = netz.Topology
    n = len(dreiecke)
    for i in sorted({0, n // 3, n // 2, n - 1}):
        ecken = form.getElement(f"Face{i + 1}").Vertexes
        soll = np.array([(punkte[k].x, punkte[k].y, punkte[k].z) for k in dreiecke[i]])
        ist = np.array([(v.X, v.Y, v.Z) for v in ecken])
        if ist.shape != (3, 3) or not np.allclose(
            np.sort(np.round(ist, 4), axis=0), np.sort(np.round(soll, 4), axis=0)
        ):
            return False
    return True


def flaechen_der_dreiecke(form, netz):
    """Je Dreieck des Netzes die Nummer seiner Fläche im Körper (0 ist „Face1“; −1: keine) –
    `makeShapeFromMesh` ordnet die Flächen anders als die Dreiecke. Zugeordnet über die Ecken
    (auf 0,1 µm gerundet); am Geist 1,1 s (_ecken_der_flaechen), einmal beim Umwandeln."""
    ecken = _ecken_der_flaechen(form)
    p, d = netz.Topology
    punkte = np.array([(q.x, q.y, q.z) for q in p], dtype=float).reshape(-1, 3)
    dreiecke = np.array(d, dtype=np.int64).reshape(-1, 3)
    zuordnung = np.full(len(dreiecke), -1, dtype=np.int64)
    if ecken.ndim != 3 or ecken.shape[1:] != (3, 3):
        return zuordnung  # nicht jede Fläche ein Dreieck
    nummer = {k: i for i, k in enumerate(_eckenschluessel(ecken))}
    for j, k in enumerate(_eckenschluessel(punkte[dreiecke])):
        zuordnung[j] = nummer.get(k, -1)
    return zuordnung


def _ecken_der_flaechen(form):
    """(n, 3, 3): je Fläche ihre drei Ecken – aus einer Vernetzung des ganzen Körpers auf einmal:
    Jede Fläche ist ein ebenes Dreieck und gibt genau eins, in der Reihenfolge der Flächen (am
    Geist 1,1 s; je Fläche `Vertexes` in Python 3,9 s auf einem Kern). Stimmt die Zahl nicht oder
    eine Stichprobe nicht, je Fläche wie bisher."""
    flaechen = form.Faces
    try:
        punkte, dreiecke = form.tessellate(1.0)
    except Exception:  # noqa: BLE001 – OCC: dann je Fläche
        dreiecke = ()
    if len(dreiecke) == len(flaechen) and len(flaechen):
        p = np.array([(q.x, q.y, q.z) for q in punkte], dtype=float).reshape(-1, 3)
        ecken = p[np.array(dreiecke, dtype=np.int64).reshape(-1, 3)]
        stichprobe = sorted({0, len(flaechen) // 3, len(flaechen) // 2, len(flaechen) - 1})
        if all(
            np.allclose(
                np.sort(np.round(ecken[i], 4), axis=0),
                np.sort(
                    np.round(np.array([(v.X, v.Y, v.Z) for v in flaechen[i].Vertexes]), 4),
                    axis=0,
                ),
            )
            for i in stichprobe
            if len(flaechen[i].Vertexes) == 3
        ):
            return ecken
    return np.array(
        [[(v.X, v.Y, v.Z) for v in flaeche.Vertexes] for flaeche in flaechen], dtype=float
    )


def _eckenschluessel(dreiecke):
    """Je Dreieck (m, 3, 3) ein Schlüssel aus seinen gerundeten Ecken, unabhängig von ihrer
    Reihenfolge."""
    gerundet = np.round(np.asarray(dreiecke, dtype=float), 4) + 0.0  # −0,0 wird 0,0
    zeilen = gerundet.view([("x", float), ("y", float), ("z", float)]).reshape(len(gerundet), 3)
    return [z.tobytes() for z in np.sort(zeilen, axis=1)]


def koerper_rechnen(datei, massstab=1.0):
    """Auf einem Nebenrechner: (nebenrechner.Form, Bericht, Fläche je Dreieck als Liste) zum Netz
    in der STL-Datei `datei` – koerper_und_bericht(); das vorbereitete Netz steht danach in
    `datei` (FreeCAD hält Netze in float32 wie das STL, nichts geht verloren). Am Geist (68.242
    Dreiecke) 5 s, die das Fenster sonst stünde (bis 0.280.5 mit dem Nähen 7 s)."""
    import Mesh

    from . import nebenrechner as nr

    form, netz, bericht, zuordnung = koerper_und_bericht(Mesh.Mesh(datei), massstab)
    netz.write(datei)
    return nr.Form.von(form), bericht, zuordnung.tolist()


def koerper_aus_netz(dokument, netzobjekt, massstab=1.0, gerechnet=None):
    """(Part::Feature, Bericht): der Körper des Netzes `netzobjekt` im Dokument – ohne eigene
    Transaktion (der Aufrufer hält sie). `gerechnet`: (Form, vorbereitetes Netz, Bericht, Fläche
    je Dreieck), schon woanders gerechnet (koerper_rechnen). Die Punkte des Netzes enthalten seine
    Platzierung schon; der Körper liegt deshalb ohne eigene da – das vorbereitete Netz ist so
    zugleich sein Netz im eigenen Koordinatensystem (EIGENSCHAFT_NETZ)."""
    form, netz, bericht, zuordnung = gerechnet or koerper_und_bericht(netzobjekt.Mesh, massstab)
    teil = dokument.addObject("Part::Feature", "TeilAusStl")
    teil.Label = tr("stl.teil", name=netzobjekt.Label)
    if getattr(teil, "ViewObject", None) is not None:
        # Erst ausgeblendet: FreeCADs Anzeige der 68.242 Flächen des Geists kostete 1,7 s – die
        # Oberfläche zeigt ihn als Netz (stl_anzeige).
        teil.ViewObject.Visibility = False
    teil.Shape = form
    teil.addProperty("App::PropertyLink", EIGENSCHAFT_STL, "CAM-Addon", tr("stl.eigenschaft"))
    setattr(teil, EIGENSCHAFT_STL, netzobjekt)
    teil.setEditorMode(EIGENSCHAFT_STL, 1)  # nur lesen
    teil.addProperty("Mesh::PropertyMeshKernel", EIGENSCHAFT_NETZ, "CAM-Addon", tr("stl.netz"))
    setattr(teil, EIGENSCHAFT_NETZ, netz)
    teil.setEditorMode(EIGENSCHAFT_NETZ, 2)  # versteckt
    teil.addProperty("App::PropertyIntegerList", EIGENSCHAFT_FLAECHEN, "CAM-Addon", tr("stl.netz"))
    setattr(teil, EIGENSCHAFT_FLAECHEN, [int(n) for n in zuordnung])
    teil.setEditorMode(EIGENSCHAFT_FLAECHEN, 2)
    return teil, bericht


_ARRAYS = {}  # (Dokument, Objekt, Dreiecke, Punkte) -> (Punkte (n, 3), Dreiecke (m, 3))
_ARRAYS_HOECHSTENS = 4


_ERKANNT = OrderedDict()  # hashCode der Form -> (die Form, netz_fuer, flaechennetz_fuer oder …)
_ERKANNT_HOECHSTENS = 8
_NOCH_NICHT = object()


def _gemerkt(form):
    """Der Eintrag zur Form in _ERKANNT – die Form hält er fest, damit OpenCascade ihren Speicher
    (und so ihren hashCode) keiner anderen gibt; None ohne."""
    try:
        kennung = form.hashCode()
    except Exception:  # noqa: BLE001 – keine Form, die sich merken lässt
        return None, None
    eintrag = _ERKANNT.get(kennung)
    if eintrag is not None and eintrag[0].isSame(form):
        _ERKANNT.move_to_end(kennung)
        return kennung, eintrag
    return kennung, None


def _merken(kennung, eintrag):
    if kennung is None:
        return
    _ERKANNT[kennung] = eintrag
    while len(_ERKANNT) > _ERKANNT_HOECHSTENS:
        _ERKANNT.popitem(last=False)


def netz_fuer(form):
    """netz_fuer_rechnen(), gemerkt je Form: Der Assistent „Bearbeitung“ fragt je Vorschau oft
    nach derselben."""
    kennung, eintrag = _gemerkt(form)
    if eintrag is None:
        eintrag = [form, netz_fuer_rechnen(form), _NOCH_NICHT]
        _merken(kennung, eintrag)
    return _kopie(eintrag[1])


def _kopie(ergebnis):
    """Die Punkte als eigene Kopie – wer sie verschiebt, verschiebt nicht die gemerkten."""
    if ergebnis is None:
        return None
    return (ergebnis[0].copy(), *ergebnis[1:])


def netz_fuer_rechnen(form):
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
    if form.ShapeType == "Compound":  # die Kollision verbindet die Modelle (_teil_form)
        kinder = form.childShapes()  # mit der Lage des Verbunds
        if len(kinder) != 1:
            return None
        form = kinder[0]
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


def flaechennetz_fuer(form):
    """flaechennetz_fuer_rechnen(), gemerkt je Form."""
    kennung, eintrag = _gemerkt(form)
    if eintrag is not None and eintrag[2] is not _NOCH_NICHT:
        return _kopie(eintrag[2])
    ergebnis = flaechennetz_fuer_rechnen(form)
    kennung, eintrag = _gemerkt(form)  # netz_fuer() hat ihn eben angelegt
    if eintrag is not None:
        eintrag[2] = ergebnis
    else:
        _merken(kennung, [form, netz_fuer_rechnen(form), ergebnis])
    return _kopie(ergebnis)


def flaechennetz_fuer_rechnen(form):
    """(Punkte, Dreiecke, Fläche je Dreieck) wie netz_fuer() – mit der Nummer der Fläche je
    Dreieck (0 ist „Face1“), für vierachs_flaechen.vernetze; None, wenn die Form kein solcher
    Körper ist oder die Zuordnung fehlt oder nicht stimmt (an zwei Dreiecken nachgesehen)."""
    gefunden = netz_fuer(form)
    if gefunden is None:
        return None
    punkte, dreiecke = gefunden
    flaeche = _zuordnung(len(dreiecke), form)
    if flaeche is None:
        return None
    for j in (0, len(dreiecke) // 2):
        ecken = form.getElement(f"Face{flaeche[j] + 1}").Vertexes
        soll = _eckenschluessel(punkte[dreiecke[j]][None])[0]
        ist = _eckenschluessel(np.array([[(v.X, v.Y, v.Z) for v in ecken]], dtype=float))[0]
        if ist != soll:
            return None
    return punkte, dreiecke, flaeche


@dataclass
class Dreiecksdaten:
    """Je Fläche eines Körpers aus einem STL (jede ein Dreieck) was die Strategien sonst Fläche für
    Fläche bei OpenCascade erfragen – einmal mit numpy gerechnet (daten()): Bei 68.242 Flächen
    kostete jede Frage ein `getElement`, das alle Flächen durchgeht."""

    punkte: np.ndarray  # (n, 3) in der Lage der Form
    dreiecke: np.ndarray  # (m, 3)
    flaeche: np.ndarray  # (m,) die Fläche je Dreieck (0 ist „Face1“)
    dreieck: np.ndarray  # (m,) das Dreieck je Fläche
    normale: np.ndarray  # (m, 3) je Fläche die Außennormale, Einheitsvektor (0 bei entarteten)
    unten: np.ndarray  # (m, 3) je Fläche die kleinsten x, y, z
    oben: np.ndarray  # (m, 3) je Fläche die größten x, y, z

    def nummern(self, namen):
        """Die Flächennummern zu den Namen („Face3“ → 2), die es gibt."""
        anzahl = len(self.dreieck)
        ergebnis = []
        for name in namen:
            if name.startswith("Face") and name[4:].isdigit() and 0 < int(name[4:]) <= anzahl:
                ergebnis.append(int(name[4:]) - 1)
        return np.asarray(ergebnis, dtype=np.int64)

    def kasten(self, nummern):
        """(x von, x bis, y von, y bis, z von, z bis) über die Flächen `nummern` – None ohne."""
        nummern = np.asarray(nummern, dtype=np.int64)
        if not len(nummern):
            return None
        u, o = self.unten[nummern].min(axis=0), self.oben[nummern].max(axis=0)
        return (float(u[0]), float(o[0]), float(u[1]), float(o[1]), float(u[2]), float(o[2]))


def daten(form):
    """Dreiecksdaten der Form, wenn sie ein Körper aus einem STL ist (flaechennetz_fuer) – je Form
    gemerkt; sonst None."""
    kennung, eintrag = _gemerkt(form)
    if eintrag is not None and len(eintrag) > 3:
        return eintrag[3]
    netz = flaechennetz_fuer(form)
    ergebnis = None
    if netz is not None:
        punkte, dreiecke, flaeche = netz
        ecken = punkte[dreiecke]
        normale = np.cross(ecken[:, 1] - ecken[:, 0], ecken[:, 2] - ecken[:, 0])
        laenge = np.linalg.norm(normale, axis=1)
        normale = np.where(
            laenge[:, None] > 1e-12, normale / np.maximum(laenge, 1e-300)[:, None], 0
        )
        dreieck = np.empty(len(flaeche), dtype=np.int64)
        dreieck[flaeche] = np.arange(len(flaeche))
        ergebnis = Dreiecksdaten(
            punkte,
            dreiecke,
            flaeche,
            dreieck,
            normale[dreieck],
            ecken.min(axis=1)[dreieck],
            ecken.max(axis=1)[dreieck],
        )
    kennung, eintrag = _gemerkt(form)
    if eintrag is not None:
        while len(eintrag) < 4:
            eintrag.append(None)
        eintrag[3] = ergebnis
    return ergebnis


def _zuordnung(anzahl, form):
    """Die gespeicherte Fläche je Dreieck (EIGENSCHAFT_FLAECHEN) des Körpers mit `anzahl`
    Dreiecken, dessen Netz zur Form passt – None ohne, oder wenn ein Dreieck keine hat."""
    for dokument in FreeCAD.listDocuments().values():
        for objekt in dokument.Objects:
            liste = getattr(objekt, EIGENSCHAFT_FLAECHEN, None)
            if liste is not None and len(liste) == anzahl:
                flaeche = np.asarray(liste, dtype=np.int64)
                return flaeche if len(flaeche) and flaeche.min() >= 0 else None
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
