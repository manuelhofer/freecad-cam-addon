# SPDX-License-Identifier: LGPL-2.1-or-later
"""Zeigt in Schritt 1 des Assistenten „Bearbeitung“, wie das Teil liegt: eine Platte unter dem Teil
(der Tisch, der Schraubstockboden) und ein Pfeil in X – in der 3D-Ansicht, nicht als Satz.

Manuel, 2026-11-11: „kürzerer text ist ja nicht besser gibts vll einfach ne andere möglichkeit das
gesagte umzusetzten oder zu zeigen“. Schritt 1 fragte in Worten „Welche Fläche liegt unten?“ und
„X zeigt …“ – wer das Teil auf seiner Platte sieht, sieht die Antwort, die gerade gilt, und klickt
nur, wenn sie falsch ist. Nur Anzeige (Coin-Knoten in der Ansicht), nichts im Dokument."""

from . import gui_abfahren as ga

PLATTE = (0.55, 0.60, 0.68)
SPANNMITTEL = (0.35, 0.42, 0.55)
PFEIL = (0.85, 0.15, 0.15)  # X – rot, wie FreeCADs Achsenkreuz
DURCHSICHT = 0.55
RAND = 0.25  # die Platte steht um so viel der größeren Kante über
DICKE = 0.04  # ihrer Diagonale
RAND_SPANNMITTEL = 0.05  # unter einem Spannmittel nur ein schmaler Rand – es ist selbst groß


def masse(box, rand=RAND):
    """(Mitte x, Mitte y, Oberkante z, Länge x, Länge y, Dicke) der Platte unter einem Kasten
    (xmin, ymin, zmin, xmax, ymax, zmax): rundum `rand` der größeren Kante größer, DICKE der
    Diagonale dick, ihre Oberkante an der Unterkante des Kastens."""
    xmin, ymin, zmin, xmax, ymax, _zmax = box
    lx, ly = xmax - xmin, ymax - ymin
    rand = rand * max(lx, ly)
    dicke = max(DICKE * (lx * lx + ly * ly) ** 0.5, 0.5)
    return ((xmin + xmax) / 2, (ymin + ymax) / 2, zmin, lx + 2 * rand, ly + 2 * rand, dicke)


def _netz(form):
    """Ein Körper (Part.Shape) als Dreiecksnetz für die Ansicht – grob genügt (0,5 mm)."""
    from pivy import coin

    punkte, dreiecke = form.tessellate(0.5)
    knoten = coin.SoSeparator()
    knoten.addChild(
        ga.material(SPANNMITTEL)
    )  # deckend: durchsichtig überlagern sich die Flächen fleckig
    hinweis = (
        coin.SoShapeHints()
    )  # beide Seiten beleuchtet – die Richtung der Dreiecke ist gemischt
    hinweis.vertexOrdering = coin.SoShapeHints.UNKNOWN_ORDERING
    hinweis.shapeType = coin.SoShapeHints.UNKNOWN_SHAPE_TYPE
    knoten.addChild(hinweis)
    koordinaten = coin.SoCoordinate3()
    koordinaten.point.setValues(0, len(punkte), [(p.x, p.y, p.z) for p in punkte])
    knoten.addChild(koordinaten)
    stellen = []
    for a, b, c in dreiecke:
        stellen.extend((a, b, c, -1))
    netz = coin.SoIndexedFaceSet()
    netz.coordIndex.setValues(0, len(stellen), stellen)
    knoten.addChild(netz)
    return knoten


class Tisch:
    """Die gezeigte Platte eines Dokuments: zeigen() hängt sie ein (die alte fällt weg), weg()
    nimmt sie heraus."""

    def __init__(self, dokument):
        self.dokument = dokument
        self.wurzel = None
        self.ansicht = None
        self.stand = None  # der Kasten, zu dem die Platte gerade gehört

    def zeigen(self, box, schluessel=None, spannmittel=None):
        """Die Platte unter `box` (xmin, ymin, zmin, xmax, ymax, zmax – so, wie das Teil in der
        Ansicht liegt), vorn an ihr ein Pfeil nach +X. Mit `spannmittel` (eine Funktion, die
        seinen Körper als Part.Shape gibt, oder None) steht das Teil darin: der Schraubstock mit
        den Backen am Rohteil, die Platte darunter. `schluessel` sagt, wann er neu zu holen ist
        (die Aufspannung als Text). Gibt zurück, ob es eine Ansicht gab."""
        from pivy import coin

        box = tuple(round(float(wert), 3) for wert in box)
        stand = (box, schluessel)
        if self.wurzel is not None and self.stand == stand:
            return True
        self.weg()
        ansicht = ga.ansicht_von(self.dokument)
        if ansicht is None:
            return False
        wurzel = coin.SoSeparator()
        form = None
        if spannmittel is not None:
            try:
                form = spannmittel()
            except Exception:  # noqa: BLE001 – dann die Platte allein
                form = None
        if form is not None and not form.isNull():
            wurzel.addChild(_netz(form))
            k = form.BoundBox
            # Die Platte unter Spannmittel und Rohteil zusammen.
            box = (
                min(box[0], k.XMin),
                min(box[1], k.YMin),
                min(box[2], k.ZMin),
                max(box[3], k.XMax),
                max(box[4], k.YMax),
                box[5],
            )
        hat_spannmittel = form is not None and not form.isNull()
        mx, my, oben, lx, ly, dicke = masse(box, RAND_SPANNMITTEL if hat_spannmittel else RAND)
        platte = coin.SoSeparator()
        lage = coin.SoTranslation()
        lage.translation.setValue(mx, my, oben - dicke / 2)
        platte.addChild(lage)
        platte.addChild(ga.material(PLATTE, DURCHSICHT))
        quader = coin.SoCube()
        quader.width, quader.height, quader.depth = lx, ly, dicke
        platte.addChild(quader)
        wurzel.addChild(platte)
        # Der Pfeil nach +X: vorn (−Y) auf der Platte, ein Drittel so lang wie sie.
        laenge = lx / 3
        y = my - ly / 2 + 0.06 * ly
        pfeil = coin.SoSeparator()
        pfeil.addChild(ga.material(PFEIL))
        stil = coin.SoDrawStyle()
        stil.lineWidth = 3
        pfeil.addChild(stil)
        punkte = coin.SoCoordinate3()
        spitze = mx + laenge / 2
        kopf = 0.2 * laenge
        punkte.point.setValues(
            0,
            5,
            [
                (mx - laenge / 2, y, oben),
                (spitze, y, oben),
                (spitze - kopf, y + kopf / 2, oben),
                (spitze, y, oben),
                (spitze - kopf, y - kopf / 2, oben),
            ],
        )
        pfeil.addChild(punkte)
        linie = coin.SoLineSet()
        linie.numVertices.setValue(5)
        pfeil.addChild(linie)
        wurzel.addChild(pfeil)
        ansicht.getSceneGraph().addChild(wurzel)
        self.wurzel, self.ansicht, self.stand = wurzel, ansicht, stand
        return True

    def weg(self):
        if self.wurzel is not None and self.ansicht is not None:
            try:
                graph = self.ansicht.getSceneGraph()
                if graph.findChild(self.wurzel) >= 0:
                    graph.removeChild(self.wurzel)
            except Exception:  # noqa: BLE001 – die Ansicht ist schon zu
                pass
        self.wurzel = self.ansicht = self.stand = None
