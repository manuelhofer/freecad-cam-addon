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

    def rundachsen(self, stellungen):
        """Die Rundachsen im Programm bei diesen Stellungen: {"C": Grad} – nur die, die
        positionieren (keine Spindel, kein Revolver)."""
        from .reichweite import _programmbuchstabe

        ergebnis = {}
        for achse, stellung in stellungen.items():
            if achse.art == LINEAR:
                continue
            buchstabe = _programmbuchstabe(self.pruefung.maschine, achse)
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
