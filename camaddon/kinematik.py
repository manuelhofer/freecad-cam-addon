# SPDX-License-Identifier: LGPL-2.1-or-later
"""Achsstellungen und Werkzeugspitze – die eine Stelle, an der das Addon zwischen
Programm und Maschine rechnet (Spezifikation W-001, Stufe 4e).

Manuel (2026-09-29): „das x-60 ist ja nur die maschinen koordinate .. nicht wenn nen
fräser mit dabei ist .. der TCP muss schon mit berechnet werden .. generell immer …
es muss einfach genial gebaut sein das du das nicht jedes mal neu erfinden musst“.

Eine Kinematik gilt für ein Werkzeug auf einer Maschine: die Werkzeugaufnahme, die
Länge bis zur Spitze und der Nullpunkt des Jobs an der Werkstückaufnahme. Sie
rechnet

- rückwärts: Punkt im Programm (X, Y, Z und die Rundachsen) → Stellung jeder Achse
  (stellungen) – so prüfen Reichweite, Abfahren und Kollision;
- vorwärts: Stellungen → wo die Spitze im Programm steht (programm) – etwa wenn eine
  Achse am Anschlag steht und die Spitze nicht hinkommt –, und wo sie am gedrehten
  Werkstück steht (am_werkstueck) – so zeigt das Prüffenster die Bahn.

Wie eine Steuerung ohne TCPM: X, Y und Z sind die Linearachsen, gelöst mit den
Rundachsen auf 0 – die Rundachsen drehen das Werkstück darunter. So zeigt FreeCAD
eine Bahn mit A, B und C, und so schreibt „Rundum schruppen“ sein Programm
(vierachs_bahn). Eine Steuerung mit TCPM (Siemens TRAORI, Heidenhain M128, Fanuc
RTCP) läse X, Y, Z als Spitze am gedrehten Werkstück – dafür bräuchte es auch eine
eigene Ausgabe der Bahnen; kommt sie, wird es hier eine Einstellung.

Gerechnet wird mit der Kette der Maschine (reichweite.Pruefung); neue Prüfungen und
Bahnen bauen hierauf auf, statt es neu zu erfinden.

Läuft ohne Oberfläche.
"""

import FreeCAD
import numpy as np

from .kette import LINEAR


class Kinematik:
    """Achsen und Spitze für ein Werkzeug auf einer Maschine (siehe oben)."""

    def __init__(self, pruefung, werkzeugaufnahme, laenge, nullpunkt_des_jobs):
        self.pruefung = pruefung
        self.aufnahme = werkzeugaufnahme
        self.laenge = laenge
        self.nullpunkt = FreeCAD.Vector(nullpunkt_des_jobs)
        self.linear, self.drehachsen = pruefung.achsen_fuer(werkzeugaufnahme)
        self._loesung = pruefung.loeser(werkzeugaufnahme, laenge, self.nullpunkt)

    # --- rückwärts ----------------------------------------------------------------------

    def stellungen(self, punkt, rund=None):
        """{Achse: Stellung} für den Punkt im Programm `punkt` (x, y, z) mit den Rundachsen
        `rund` ({"C": Grad}) – None, wenn die Linearachsen nicht dorthin kommen oder sich
        nicht eindeutig auflösen lassen."""
        geloest, dreh = self._loesung(rund or {})
        if geloest is None or not geloest.erreichbar(*punkt):
            return None
        ergebnis = dict(dreh)
        ergebnis.update(zip(self.linear, geloest.werte(*punkt), strict=True))
        return ergebnis

    # --- vorwärts -----------------------------------------------------------------------

    def programm(self, stellungen):
        """Wo die Spitze bei diesen Stellungen im Programm steht: (x, y, z) – mit den
        Rundachsen auf 0 gerechnet, so liest die Steuerung X, Y und Z. Fehlende Achsen
        stehen in Grundstellung."""
        return self._im_job(self._wege(stellungen, rundachsen=False))

    def am_werkstueck(self, stellungen):
        """Wo die Spitze bei diesen Stellungen am gedrehten Werkstück steht: (x, y, z) in
        Koordinaten des Jobs – so liegt die Bahn um das Teil."""
        return self._im_job(self._wege(stellungen, rundachsen=True))

    def am_werkstueck_felder(self, stellungen):
        """am_werkstueck für viele Stationen zugleich: `stellungen` {Achse: Feld der Stellungen}
        – NaN (oder eine fehlende Achse) heißt Grundstellung wie ein fehlender Schlüssel in
        am_werkstueck. Gibt ein Feld (n, 3) zurück. Dieselben Rechenschritte, Achse für Achse
        mit numpy statt je Station mit Placements: Das Prüffenster stand am Simultanbeispiel
        1,6 s still, am 4-Achs-Testteil rechneten dafür die Nebenrechner (P-2026-10-18-66)."""
        p = self.pruefung
        v = p.verfahren
        anzahl = len(next(iter(stellungen.values()))) if stellungen else 0
        grund = p._dreh_wege(self.aufnahme, self.drehachsen, {})

        def weg(achse):
            vorgabe = grund.get(achse, 0.0)
            feld = stellungen.get(achse)
            if feld is None:
                return np.full(anzahl, vorgabe)
            feld = np.asarray(feld, dtype=float)
            return np.where(np.isnan(feld), vorgabe, v.weg_bei(achse, feld))

        def bewege(punkte, glied, rueckwaerts):
            # Vorwärts wie _glied_lage: B1·B2·…·Bn, also Bn zuerst; rückwärts die Umkehrung:
            # B1⁻¹ zuerst, jede Achse um den negativen Weg.
            pfad = v.pfad(glied)
            for achse in pfad if rueckwaerts else reversed(pfad):
                w = weg(achse)
                if not w.any():
                    continue
                if rueckwaerts:
                    w = -w
                richtung, ursprung = v.achslage(achse)
                if achse.art == LINEAR:
                    punkte = punkte + w[:, None] * np.array(tuple(richtung), dtype=float)
                else:
                    punkte = _gedreht(punkte, richtung, ursprung, w)
            return punkte

        spitze_im_glied = p._lage(self.aufnahme).multVec(_einspannung(self.laenge).spitze())
        spitze = np.tile(np.array(tuple(spitze_im_glied), dtype=float), (anzahl, 1))
        spitze = bewege(spitze, p._glied(self.aufnahme), rueckwaerts=False)
        am_glied = bewege(spitze, p._glied(p.werkstueckaufnahme), rueckwaerts=True)
        # Vom Glied der Werkstückaufnahme in den Job: (Lage der Aufnahme · Nullpunkt)⁻¹.
        zum_job = (
            p._lage(p.werkstueckaufnahme)
            .multiply(FreeCAD.Placement(self.nullpunkt, FreeCAD.Rotation()))
            .inverse()
            .toMatrix()
        )
        r = np.array(
            [
                [zum_job.A11, zum_job.A12, zum_job.A13],
                [zum_job.A21, zum_job.A22, zum_job.A23],
                [zum_job.A31, zum_job.A32, zum_job.A33],
            ]
        )
        return am_glied @ r.T + np.array([zum_job.A14, zum_job.A24, zum_job.A34])

    def rundachsen(self, stellungen):
        """Die Rundachsen im Programm bei diesen Stellungen: {"C": Grad} – nur die, die
        positionieren (keine Spindel, kein Revolver)."""
        ergebnis = {}
        for achse, stellung in stellungen.items():
            if achse.art == LINEAR:
                continue
            buchstabe = self.pruefung.programmbuchstabe(achse)
            if buchstabe is not None:
                ergebnis[buchstabe] = stellung
        return ergebnis

    def _wege(self, stellungen, rundachsen):
        """Die Wege aller Achsen seit dem Ausgang. `rundachsen`: die Drehachsen wie in
        `stellungen`; sonst in Grundstellung (Revolver in Arbeitsstellung, Rundachsen 0)."""
        p = self.pruefung
        wege = dict(p._dreh_wege(self.aufnahme, self.drehachsen, {}))
        for achse, stellung in stellungen.items():
            if achse.art == LINEAR or rundachsen:
                wege[achse] = p.verfahren.weg_bei(achse, stellung)
        return wege

    def _im_job(self, wege):
        p = self.pruefung
        spitze = p._spitze(self.aufnahme, self.laenge, wege)
        return tuple(p._job_lage(self.nullpunkt, wege).inverse().multVec(spitze))


def _einspannung(laenge):
    from .reichweite import _einspannung as einspannung

    return einspannung(laenge)


def _gedreht(punkte, richtung, ursprung, grad):
    """Die Punkte (n, 3) je um `grad` (Feld, Grad, rechtsherum um `richtung`) um die Achse durch
    `ursprung` gedreht – wie FreeCAD.Placement(Vector(), Rotation(richtung, grad), ursprung)."""
    k = np.array(tuple(richtung), dtype=float)
    k = k / np.linalg.norm(k)
    c = np.array(tuple(ursprung), dtype=float)
    winkel = np.radians(grad)
    cos, sin = np.cos(winkel)[:, None], np.sin(winkel)[:, None]
    q = punkte - c
    return c + q * cos + np.cross(k, q) * sin + k * (q @ k)[:, None] * (1.0 - cos)
