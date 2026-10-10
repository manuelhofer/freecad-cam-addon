# SPDX-License-Identifier: LGPL-2.1-or-later
"""Verwaiste Rohteil- und Modellklone nach einem Rückgängig wegräumen (B-016).

FreeCADs Job-Anlage (`Path.Main.Job.Create`) legt einen Werkzeug-Controller an, und das schließt
die laufende Transaktion – nachgestellt am 2026-10-10 (P-2026-10-10-20): Alles, was danach in
derselben Transaktion entsteht, kennt das Rückgängig nicht mehr. So blieb nach dem Zurücknehmen
eines geschwenkten Ebenenjobs sein Rohteilklon („Clone002“) ohne Job im Dokument. Am Anlegen
lässt sich das nicht ändern (auch eine Vorlage ohne Werkzeug hilft nicht); darum räumt dieser
Beobachter auf: Nach einem Rückgängig merkt er sich das Dokument, und sobald die nächste
Transaktion abgeschlossen ist – dann gibt es kein Wiederholen mehr, das den Klon bräuchte –,
entfernt er jeden Klon mit `PathResource`, den kein Objekt mehr verwendet.

Läuft ohne Oberfläche (beobachten() ist für die Oberfläche gedacht, verwaiste() rechnet auch ohne).
"""

import FreeCAD

_vorgemerkt = set()  # Dokumente (Name), in denen seit dem letzten Rückgängig aufzuräumen ist
_BEOBACHTER = []


def verwaiste(dokument):
    """Die Klone mit `PathResource` (Rohteil, Modell eines Jobs), die kein Objekt mehr verwendet."""
    return [o for o in dokument.Objects if "PathResource" in o.PropertiesList and not o.InList]


def aufraeumen(dokument):
    """Entfernt die verwaisten Klone; gibt ihre Namen zurück."""
    weg = []
    for objekt in verwaiste(dokument):
        weg.append(objekt.Name)
        dokument.removeObject(objekt.Name)
    if weg:
        FreeCAD.Console.PrintLog(f"CAM-Addon: verwaiste Klone entfernt: {', '.join(weg)}\n")
    return weg


class _Beobachter:
    def slotUndoDocument(self, dokument):
        _vorgemerkt.add(dokument.Name)

    def slotCommitTransaction(self, dokument):
        if dokument.Name not in _vorgemerkt or getattr(dokument, "RedoNames", []):
            return
        _vorgemerkt.discard(dokument.Name)
        # Nicht mitten im Abschluss der Transaktion am Dokument arbeiten.
        from PySide import QtCore

        name = dokument.Name
        QtCore.QTimer.singleShot(0, lambda: _spaeter(name))

    def slotDeletedDocument(self, dokument):
        _vorgemerkt.discard(dokument.Name)


def _spaeter(name):
    dokument = FreeCAD.getDocument(name) if name in FreeCAD.listDocuments() else None
    if dokument is not None:
        aufraeumen(dokument)


def beobachten():
    """Meldet den Beobachter einmal an (gui_start.starten)."""
    if not _BEOBACHTER:
        _BEOBACHTER.append(_Beobachter())
        FreeCAD.addDocumentObserver(_BEOBACHTER[0])
