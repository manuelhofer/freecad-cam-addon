# SPDX-License-Identifier: LGPL-2.1-or-later
"""Rechnet Operationen mit Materialstand neu, wenn sich davor etwas ändert (W-012,
Spezifikation Strategien 12.7).

Eine Operation mit Materialstand (heute die Nut) rechnet mit dem, was die Operationen davor im
Job übrig lassen, und merkt sich, woraus (ihre Eigenschaft „Materialstand“:
materialstand.kennung_vor). Ändert sich davor etwas – eine Bahn, die Reihenfolge, eine
Operation gelöscht –, stimmt ihr Materialstand nicht mehr; im schlimmsten Fall führe ihr
Eilgang dorthin, wo jetzt doch Material steht. Der Beobachter merkt sich das Dokument und prüft,
sobald FreeCAD mit dem Neuberechnen fertig ist (QTimer): Jede Operation, deren Kennung nicht
mehr stimmt, rechnet er neu – der Reihe nach im Job, so sieht jede die neue Bahn ihrer
Vorgänger. Wie in FreeCAD selbst ohne eigenen Schritt Rückgängig: Neuberechnen gehört zur
Änderung, die es auslöste.
"""

import FreeCAD
from PySide import QtCore

from . import job_schnittwerte as js
from . import materialstand as mst
from . import nut as nu


def mit_materialstand(op):
    """Rechnet `op` mit dem Materialstand – oder trägt sie eine solche (eine Nachbearbeitung)?
    Gibt die Operation mit Materialstand zurück, sonst None."""
    basis = op
    for _tiefe in range(16):
        if basis is None:
            return None
        if nu.ist_nut(basis) and "Materialstand" in basis.PropertiesList:
            return basis
        basis = getattr(basis, "Base", None)
        if basis is not None and not hasattr(basis, "Path"):
            return None
    return None


def nachrechnen(dokument):
    """Rechnet im Dokument jede Operation mit Materialstand neu, deren Materialstand nicht mehr
    stimmt – je Job der Reihe nach. Gibt die neu gerechneten zurück."""
    neu = []
    for job in js.jobs(dokument):
        try:
            anfang = mst.kennung_vor(job, None).split("|")[0]
        except Exception:  # kein Rohteil: nichts zu rechnen
            continue
        if not anfang:
            continue
        ops = mst.operationen_vor(job)
        kennungen = [mst._kennung_op(op) for op in ops]
        for k, op in enumerate(ops):
            ziel = mit_materialstand(op)
            if ziel is None:
                continue
            soll = "|".join([anfang] + kennungen[:k])
            if ziel.Materialstand == soll:
                continue
            ziel.touch()
            ziel.recompute()
            if op is not ziel:  # die Nachbearbeitung trägt ihre Bahn weiter
                op.touch()
                op.recompute()
            kennungen[k] = mst._kennung_op(op)
            neu.append(ziel)
    return neu


class _Beobachter:
    """Merkt sich, wo sich eine Bahn oder die Folge der Operationen geändert hat, und rechnet
    danach nach (nachrechnen)."""

    def __init__(self):
        self._dokumente = set()
        self._rechnet = False
        self._uhr = QtCore.QTimer()
        self._uhr.setSingleShot(True)
        self._uhr.setInterval(0)
        self._uhr.timeout.connect(self._pruefen)

    def slotChangedObject(self, objekt, eigenschaft):
        if self._rechnet or eigenschaft not in ("Path", "Group"):
            return
        self._merken(getattr(objekt, "Document", None))

    def slotDeletedObject(self, objekt):
        if self._rechnet or not hasattr(objekt, "Path"):
            return
        self._merken(getattr(objekt, "Document", None))

    def _merken(self, dokument):
        # Beim Laden ändert sich nichts: Die Bahnen kommen, wie sie gespeichert wurden.
        if dokument is None or getattr(dokument, "Restoring", False):
            return
        self._dokumente.add(dokument.Name)
        self._uhr.start()

    def _pruefen(self):
        dokumente, self._dokumente = self._dokumente, set()
        offen = FreeCAD.listDocuments()
        self._rechnet = True
        try:
            for name in dokumente:
                dokument = offen.get(name)
                if dokument is None:
                    continue
                if getattr(dokument, "Recomputing", False):
                    self._dokumente.add(name)  # erst, wenn FreeCAD fertig ist
                    self._uhr.start(100)
                    continue
                try:
                    nachrechnen(dokument)
                except Exception as fehler:  # ein Fehler hier darf FreeCAD nicht stören
                    FreeCAD.Console.PrintWarning(f"CAM-Addon: Materialstand: {fehler}\n")
        finally:
            self._rechnet = False


_BEOBACHTER = []


def beobachten():
    """Meldet den Beobachter einmal an (gui_start.starten)."""
    if not _BEOBACHTER:
        _BEOBACHTER.append(_Beobachter())
        FreeCAD.addDocumentObserver(_BEOBACHTER[0])
