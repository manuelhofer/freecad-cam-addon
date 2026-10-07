# SPDX-License-Identifier: LGPL-2.1-or-later
"""Bahn und Werkzeuganstellung gemeinsam vergleichen, bevor der Job geändert wird."""

import math

import FreeCAD
import FreeCADGui as Gui
from PySide import QtCore, QtGui

from . import abfahren as ab
from . import einheiten, symbol
from . import reichweite as rw
from . import schlichten3d as s3
from . import simultan_planung as sp
from . import werkzeuge as wz
from .gui_hilfe import kopfzeile
from .sprache import tr


def richtung_text(richtung):
    """Die angebotene Bahnrichtung in der aktuellen Sprache."""
    return {
        "x": tr("s5p.richtung.x"),
        "y": tr("s5p.richtung.y"),
        "spirale": tr("s5p.richtung.spirale"),
        "flaeche": tr("s5p.richtung.flaeche"),
        "aequidistant": tr("s5p.richtung.aequidistant"),
    }[richtung]


def anstellung_text(um):
    """Die angebotene Anstellung in der aktuellen Sprache."""
    return {"X": tr("s5p.um.X"), "Y": tr("s5p.um.Y"), "frei": tr("s5p.um.frei")}[um]


def ausgewaehlt():
    """Genau eine gewählte 3D-Schlichtoperation."""
    ops = [o for o in Gui.Selection.getSelection() if s3.ist_schlichten3d(o)]
    return ops[0] if len(ops) == 1 else None


class BefehlSimultanPlanen:
    def GetResources(self):
        return {
            "Pixmap": symbol("camaddon.svg"),
            "MenuText": tr("s5p.titel"),
            "ToolTip": tr("s5p.tooltip"),
        }

    def IsActive(self):
        return ausgewaehlt() is not None

    def Activated(self):
        op = ausgewaehlt()
        if op is None:
            return
        from .gui_reichweite import maschine_fuer

        job = sp.job_von(op)
        gefunden = maschine_fuer(job, Gui.getMainWindow())
        if gefunden is None:
            return
        try:
            panel = SimultanPanel(op, rw.Pruefung(*gefunden))
        except (ValueError, OSError) as fehler:
            QtGui.QMessageBox.warning(Gui.getMainWindow(), tr("s5p.titel"), str(fehler))
            return
        Gui.Control.showDialog(panel)


class SimultanPanel:
    """Der Vergleich läuft in Schritten; Übernehmen bleibt bis zum Prüfergebnis gesperrt."""

    offen = None

    def __init__(self, op, pruefung):
        self.op, self.pruefung = op, pruefung
        self.bibliothek = wz.Bibliothek.laden()
        self.plan = None
        self.laeufer = None
        self.abbruch = False
        self._zeilen = {}
        self.form = QtGui.QWidget()
        self.form.setWindowTitle(tr("s5p.titel"))
        layout = QtGui.QVBoxLayout(self.form)
        layout.addWidget(kopfzeile(tr("s5p.titel"), "simultan_planung"))
        text = QtGui.QLabel(tr("s5p.text", operation=op.Label, maschine=pruefung.maschine.Label))
        text.setWordWrap(True)
        layout.addWidget(text)
        self.tabelle = QtGui.QTreeWidget()
        self.tabelle.setColumnCount(6)
        self.tabelle.setHeaderLabels(
            [
                tr("s5p.werkzeug"),
                tr("s5p.bahn"),
                tr("s5p.anstellung"),
                tr("s5p.zeit"),
                tr("s5p.rest"),
                tr("s5p.pruefung"),
            ]
        )
        self.tabelle.setRootIsDecorated(False)
        self.tabelle.setMinimumHeight(260)
        layout.addWidget(self.tabelle)
        self.status = QtGui.QLabel(tr("s5p.bereit"))
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.start = QtGui.QPushButton(tr("s5p.vergleichen"))
        self.start.clicked.connect(self.vergleichen)
        layout.addWidget(self.start)
        self.uebernehmen = QtGui.QPushButton(tr("s5p.uebernehmen"))
        self.uebernehmen.setEnabled(False)
        self.uebernehmen.clicked.connect(self.accept)
        layout.addWidget(self.uebernehmen)
        SimultanPanel.offen = self

    def getStandardButtons(self):
        return getattr(QtGui.QDialogButtonBox.Cancel, "value", QtGui.QDialogButtonBox.Cancel)

    def vergleichen(self):
        self.start.setEnabled(False)
        self.uebernehmen.setEnabled(False)
        self.tabelle.clear()
        self._zeilen.clear()
        self.plan = None
        self.abbruch = False
        self.laeufer = sp.vergleichen(
            self.op, self.pruefung, self.bibliothek, fortschritt=self.fortschritt
        )
        self.status.setText(tr("s5p.rechnet"))
        QtCore.QTimer.singleShot(0, self.schritt)

    def fortschritt(self, anteil):
        self.status.setText(tr("s5p.kollision", prozent=f"{anteil * 100:.0f}"))
        QtGui.QApplication.processEvents()
        return not self.abbruch

    def schritt(self):
        if self.abbruch or self.laeufer is None:
            return
        try:
            self.plan, variante = next(self.laeufer)
            self.zeige(variante)
        except StopIteration:
            self.laeufer = None
            self.start.setEnabled(True)
            beste = self.plan.beste if self.plan else None
            if beste is None:
                self.status.setText(tr("s5p.fehler.keine"))
            else:
                self.uebernehmen.setEnabled(True)
                self.status.setText(
                    tr(
                        "s5p.beste",
                        werkzeug=beste.werkzeug.Label,
                        bahn=richtung_text(beste.richtung),
                        anstellung=anstellung_text(beste.anstellung),
                        zeit=ab.dauer_text(beste.sekunden),
                    )
                )
            return
        except Exception as fehler:
            self.laeufer = None
            self.start.setEnabled(True)
            self.status.setText(str(fehler))
            FreeCAD.Console.PrintError(f"{tr('s5p.titel')}: {fehler}\n")
            return
        QtCore.QTimer.singleShot(0, self.schritt)

    def zeige(self, variante):
        key = (variante.werkzeug.Name, variante.richtung, variante.anstellung)
        if key not in self._zeilen:
            self._zeilen[key] = QtGui.QTreeWidgetItem(self.tabelle)
        zeile = self._zeilen[key]
        rest = (
            f"{max(0, variante.rest):.3f}".replace(
                ".", einheiten.gewaehltes_dezimalzeichen() or "."
            )
            if math.isfinite(variante.rest)
            else "–"
        )
        geprueft = tr("s5p.geprueft") if variante.kollision_geprueft else tr("s5p.kollision_offen")
        werte = [
            variante.werkzeug.Label,
            richtung_text(variante.richtung),
            anstellung_text(variante.anstellung),
            ab.dauer_text(variante.sekunden) if math.isfinite(variante.sekunden) else "–",
            rest,
            variante.grund or geprueft,
        ]
        for i, wert in enumerate(werte):
            zeile.setText(i, wert)
            zeile.setToolTip(i, wert)
        for i in range(5):
            self.tabelle.resizeColumnToContents(i)
        self.status.setText(tr("s5p.rechnet"))

    def accept(self):
        try:
            sp.uebernehmen(self.op, self.plan)
        except (ValueError, RuntimeError) as fehler:
            self.status.setText(str(fehler))
            return False
        SimultanPanel.offen = None
        Gui.Control.closeDialog()
        return True

    def reject(self):
        self.abbruch = True
        SimultanPanel.offen = None
        Gui.Control.closeDialog()
        return True
