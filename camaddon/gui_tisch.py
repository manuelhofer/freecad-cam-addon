# SPDX-License-Identifier: LGPL-2.1-or-later
"""Zeigt in Schritt 1 des Assistenten „Bearbeitung“, wie das Teil liegt: eine Platte unter dem Teil
(der Tisch, der Schraubstockboden) und ein Pfeil in X – in der 3D-Ansicht, nicht als Satz.

Manuel, 2026-11-11: „kürzerer text ist ja nicht besser gibts vll einfach ne andere möglichkeit das
gesagte umzusetzten oder zu zeigen“. Schritt 1 fragte in Worten „Welche Fläche liegt unten?“ und
„X zeigt …“ – wer das Teil auf seiner Platte sieht, sieht die Antwort, die gerade gilt, und klickt
nur, wenn sie falsch ist. Nur Anzeige (Coin-Knoten in der Ansicht), nichts im Dokument."""

from . import gui_abfahren as ga

PLATTE = (0.55, 0.60, 0.68)
PFEIL = (0.85, 0.15, 0.15)  # X – rot, wie FreeCADs Achsenkreuz
DURCHSICHT = 0.55
RAND = 0.25  # die Platte steht um so viel der größeren Kante über
DICKE = 0.04  # ihrer Diagonale


def masse(box):
    """(Mitte x, Mitte y, Oberkante z, Länge x, Länge y, Dicke) der Platte unter einem Kasten
    (xmin, ymin, zmin, xmax, ymax, zmax): rundum RAND der größeren Kante größer, DICKE der
    Diagonale dick, ihre Oberkante an der Unterkante des Kastens."""
    xmin, ymin, zmin, xmax, ymax, _zmax = box
    lx, ly = xmax - xmin, ymax - ymin
    rand = RAND * max(lx, ly)
    dicke = max(DICKE * (lx * lx + ly * ly) ** 0.5, 0.5)
    return ((xmin + xmax) / 2, (ymin + ymax) / 2, zmin, lx + 2 * rand, ly + 2 * rand, dicke)


class Tisch:
    """Die gezeigte Platte eines Dokuments: zeigen() hängt sie ein (die alte fällt weg), weg()
    nimmt sie heraus."""

    def __init__(self, dokument):
        self.dokument = dokument
        self.wurzel = None
        self.ansicht = None
        self.stand = None  # der Kasten, zu dem die Platte gerade gehört

    def zeigen(self, box):
        """Die Platte unter `box` (xmin, ymin, zmin, xmax, ymax, zmax – so, wie das Teil in der
        Ansicht liegt), vorn an ihr ein Pfeil nach +X. Gibt zurück, ob es eine Ansicht gab."""
        from pivy import coin

        box = tuple(round(float(wert), 3) for wert in box)
        if self.wurzel is not None and self.stand == box:
            return True
        self.weg()
        ansicht = ga.ansicht_von(self.dokument)
        if ansicht is None:
            return False
        mx, my, oben, lx, ly, dicke = masse(box)
        wurzel = coin.SoSeparator()
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
        self.wurzel, self.ansicht, self.stand = wurzel, ansicht, box
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
