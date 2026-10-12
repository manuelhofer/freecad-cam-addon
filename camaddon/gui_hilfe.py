# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die ausführliche Hilfe im Dialog: Knopf (?) und Hilfefenster.

Die Seiten liegen als HTML in help/<sprache>/ (siehe hilfe.py). Jeder Bereich
des Dialogs hat rechts in seiner Überschrift einen Knopf (?), der die Seite
zu seinem Thema öffnet.
"""

from PySide import QtCore, QtGui

from . import hilfe, symbol
from .sprache import tr

FENSTER_GROESSE = (560, 520)  # Breite, Höhe in Pixeln


def lebt(panel):
    """Ist das Aufgabenfenster `panel` (ein Assistent mit `doc` und `geschlossen`) noch offen und
    sein Dokument da? Ein Beobachter der Auswahl, dessen Fenster ohne „Abbrechen“ verschwand (das
    Dokument zugemacht), rief sonst bei jedem Klick ins Leere – „Cannot access attribute ‚Name‘ of
    deleted object“ (Manuel, 2026-10-12) –, und seine Sperre ließ nur noch Flächen anklicken."""
    import FreeCAD

    if getattr(panel, "geschlossen", False):
        return False
    try:
        name = panel.doc.Name
    except Exception:  # noqa: BLE001 – das Dokument ist weg
        return False
    return name in FreeCAD.listDocuments()


def dialog_schliessen(dokument):
    """Schließt das Aufgabenfenster in `dokument`. In FreeCAD 26.3 gehört ein Aufgabenfenster zu
    einem Dokument, und `Control.closeDialog()` schließt nur das des aktiven: Öffnete „Anlegen“
    die Maschinendatei, war sie aktiv, das Fenster im Teil blieb stehen („Cannot close dialog of
    nullptr document“), und die erste Ebene von „Alles aus dieser Aufspannung“ ging nicht auf
    („Active task dialog found“). Deshalb erst das eigene Dokument aktiv – in 1.1 ändert das
    nichts."""
    import FreeCAD
    import FreeCADGui

    try:
        name = dokument.Name
    except Exception:  # noqa: BLE001 – das Dokument ist weg
        name = None
    if name in FreeCAD.listDocuments() and FreeCAD.ActiveDocument is not dokument:
        FreeCAD.setActiveDocument(name)
        if FreeCADGui.getDocument(name) is not None:
            FreeCADGui.setActiveDocument(name)
    FreeCADGui.Control.closeDialog()


def arbeitsdokument():
    """Das Dokument, in dem ein Assistent anlegen soll – None ohne offenes Dokument. Liegt die
    Auswahl in genau einem Dokument, dieses; sonst das aktive – ist das aber nur eine Maschine
    (eine Baugruppe mit Maschine, kein Job) und gibt es genau ein anderes Dokument, das andere.
    Es wird das aktive (dort legt FreeCAD an). Manuel (2026-10-12): Nach „Auf der Maschine
    prüfen“ war die CLX550 aktiv, der Geist in „Unbenannt“ gewählt – „4-Achs-Bearbeitung“ legte
    den Werkzeug-Controller in der Maschine an und scheiterte mit „PropertyLink does not support
    external object“."""
    import FreeCAD
    import FreeCADGui

    dokumente = {
        o.Document.Name: o.Document
        for o in FreeCADGui.Selection.getSelection("*")
        if getattr(o, "Document", None) is not None
    }
    if len(dokumente) == 1:
        dokument = next(iter(dokumente.values()))
    else:
        dokument = FreeCAD.ActiveDocument
        if dokument is not None and _nur_maschine(dokument):
            andere = [d for d in FreeCAD.listDocuments().values() if d is not dokument]
            andere = [d for d in andere if not _nur_maschine(d)]
            if len(andere) == 1:
                dokument = andere[0]
    if dokument is not None and dokument is not FreeCAD.ActiveDocument:
        FreeCAD.setActiveDocument(dokument.Name)  # die Oberfläche folgt (auch ihre Ansicht)
    return dokument


def _nur_maschine(dokument):
    """Ist das Dokument eine Maschine (eine Baugruppe mit Maschine) ohne CAM-Job?"""
    from . import maschine as mm

    objekte = dokument.Objects
    if any(o.TypeId == "Path::FeaturePython" and hasattr(o, "Operations") for o in objekte):
        return False
    return any(
        o.TypeId == "Assembly::AssemblyObject" and mm.finde_maschine(o) is not None for o in objekte
    )


def kopfzeile(titel, thema=None, anker=None):
    """Überschrift eines Bereichs; mit `thema` rechts der Knopf (?) zu dieser Hilfeseite –
    mit `anker` gleich an die Stelle <a name="anker"> darin."""
    zeile = QtGui.QWidget()
    aufbau = QtGui.QHBoxLayout(zeile)
    aufbau.setContentsMargins(0, 0, 0, 0)
    aufbau.addWidget(QtGui.QLabel(f"<b>{titel}</b>"))
    aufbau.addStretch()
    if thema:
        knopf = QtGui.QToolButton()
        knopf.setText("?")
        knopf.setToolTip(tr("hilfe.knopf.tooltip"))
        knopf.setObjectName("hilfe_" + thema)  # daran finden ihn die Szenarien
        knopf.clicked.connect(lambda: zeige_hilfe(zeile, thema, anker))
        aufbau.addWidget(knopf)
    return zeile


class BefehlSoGehts:
    """Öffnet „So geht’s“ – der Weg vom Teil zum Programm in sechs Schritten (D-54)."""

    def GetResources(self):
        return {
            "Pixmap": symbol("so_gehts.svg"),
            "MenuText": tr("befehl.so_gehts.titel"),
            "ToolTip": tr("befehl.so_gehts.tooltip"),
        }

    def IsActive(self):
        return True

    def Activated(self):
        import FreeCADGui

        zeige_hilfe(FreeCADGui.getMainWindow(), "so_gehts")


def zeige_hilfe(eltern, thema, anker=None):
    """Öffnet die Hilfeseite `thema` – mit `anker` an dieser Stelle.

    Nicht modal: Man soll lesen und gleichzeitig im Dialog weiterarbeiten
    können.
    """
    fenster = HilfeFenster(eltern, thema, anker)
    fenster.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    fenster.show()


class HilfeFenster(QtGui.QDialog):
    """Zeigt eine Hilfeseite; Verweise zwischen den Seiten funktionieren."""

    offen = None  # das zuletzt geöffnete Fenster – für die Oberflächen-Szenarien

    def __init__(self, eltern, thema, anker=None):
        super().__init__(eltern)
        HilfeFenster.offen = self
        self.setWindowTitle(tr("hilfe.titel"))
        self.resize(*FENSTER_GROESSE)
        self.browser = QtGui.QTextBrowser()
        # Verweise wie href="beschleunigung.html" sucht der Browser hier.
        self.browser.setSearchPaths([hilfe.hilfe_ordner()])
        self.browser.setOpenExternalLinks(True)
        pfad = hilfe.hilfe_datei(thema)
        if pfad:
            adresse = QtCore.QUrl.fromLocalFile(pfad)
            if anker:
                adresse.setFragment(anker)
            self.browser.setSource(adresse)
        knoepfe = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Close)
        knoepfe.rejected.connect(self.close)
        aufbau = QtGui.QVBoxLayout(self)
        aufbau.addWidget(self.browser)
        aufbau.addWidget(knoepfe)
