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
from . import simultan_folge as sf
from . import simultan_planung as sp
from . import werkzeuge as wz
from .gui_hilfe import kopfzeile
from .gui_teile import GRAU, mit_einheit, weiter
from .gui_zahlen import dezimalzeichen, groesse_fest, groesse_lesen, groesse_zeigen
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
    return {
        "X": tr("s5p.um.X"),
        "Y": tr("s5p.um.Y"),
        "frei": tr("s5p.um.frei"),
        "frei_gesamt": tr("s5p.um.frei_gesamt"),
    }[um]


def ausgewaehlt():
    """Genau eine gewählte 3D-Schlichtoperation."""
    ops = [o for o in Gui.Selection.getSelection() if s3.ist_schlichten3d(o)]
    return ops[0] if len(ops) == 1 else None


def im_dokument():
    """Die 3D-Schlichtoperationen des aktiven Dokuments."""
    dokument = FreeCAD.ActiveDocument
    return [o for o in dokument.Objects if s3.ist_schlichten3d(o)] if dokument else []


class BefehlSimultanPlanen:
    def GetResources(self):
        return {
            "Pixmap": symbol("camaddon.svg"),
            "MenuText": tr("s5p.titel"),
            "ToolTip": tr("s5p.tooltip"),
        }

    def IsActive(self):
        # Bedienbar, solange kein anderes Aufgabenfenster offen ist – was fehlt, sagt der Befehl
        # selbst und führt hin (Manuel, 2026-10-10: „warum kann ich den nicht anklicken?“).
        return not Gui.Control.activeDialog()

    def Activated(self):
        op = ausgewaehlt()
        alle = im_dokument()
        if op is None and len(alle) == 1:
            op = alle[0]  # die einzige: keine Auswahl nötig
        if op is None:
            if alle:
                QtGui.QMessageBox.information(
                    Gui.getMainWindow(), tr("s5p.titel"), tr("s5p.mehrere")
                )
            else:  # der Knopf führt gleich zum Assistenten, der die Operation anlegt
                weiter(
                    tr("s5p.titel"),
                    tr("s5p.keine_op"),
                    tr("weiter.bearbeitung"),
                    lambda: Gui.runCommand("CamAddon_Bearbeitung"),
                    Gui.getMainWindow(),
                )
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
        grob = sf.schruppen_vor(op)
        self.mit_schruppen = QtGui.QCheckBox(tr("s5f.mit_schruppen"))
        self.mit_schruppen.setToolTip(tr("s5f.tooltip"))
        self.mit_schruppen.setEnabled(grob is not None)
        self.mit_schruppen.setChecked(grob is not None)
        layout.addWidget(self.mit_schruppen)
        self.alle = QtGui.QCheckBox(tr("s5p.alle"))
        self.alle.setToolTip(tr("s5p.alle.tooltip"))
        layout.addWidget(self.alle)
        # Die Bahnfeinheit (P-2026-10-09-14): leer heißt Vorschlag – ein Viertel der Grathöhe; eine
        # frühere Übernahme steht schon an der Operation (BahnGrathoehe) und wird gezeigt.
        feinheit_zeile = QtGui.QHBoxLayout()
        feinheit_zeile.setContentsMargins(0, 0, 0, 0)
        beschriftung = QtGui.QLabel(tr("s5p.feinheit"))
        beschriftung.setToolTip(tr("s5p.feinheit.tooltip"))
        feinheit_zeile.addWidget(beschriftung)
        self.feinheit = QtGui.QLineEdit()
        self.feinheit.setToolTip(tr("s5p.feinheit.tooltip"))
        self.feinheit.setMaximumWidth(110)
        vorschlag = float(op.Grathoehe) * sp.VORGABE_FEINHEIT
        self.feinheit.setPlaceholderText(groesse_zeigen(vorschlag, einheiten.LAENGE, 4))
        bisher = float(getattr(op, "BahnGrathoehe", 0.0) or 0.0)
        if bisher > 0:
            self.feinheit.setText(groesse_zeigen(bisher, einheiten.LAENGE, 4))
        feinheit_zeile.addWidget(mit_einheit(self.feinheit, einheiten.einheit(einheiten.LAENGE)))
        feinheit_zeile.addStretch()
        layout.addLayout(feinheit_zeile)
        self.feinheit_hinweis = QtGui.QLabel(
            tr(
                "s5p.feinheit.hinweis",
                vorschlag=groesse_fest(vorschlag, einheiten.LAENGE, 4),
                grathoehe=groesse_fest(float(op.Grathoehe), einheiten.LAENGE, 4),
            )
        )
        self.feinheit_hinweis.setWordWrap(True)
        self.feinheit_hinweis.setStyleSheet(f"color: {GRAU.name()};")
        layout.addWidget(self.feinheit_hinweis)
        self.lagenbereich = QtGui.QWidget()
        zeile = QtGui.QGridLayout(self.lagenbereich)
        zeile.setContentsMargins(0, 0, 0, 0)
        self.von, self.bis, self.lagenschritt = (QtGui.QDoubleSpinBox() for _ in range(3))
        grenze = max(float(grob.Zustellung), float(grob.Zwischenlagen)) if grob else 25
        for feld, beschriftung, wert, reihe, spalte in (
            (self.von, tr("s5f.von"), min(1, grenze), 0, 0),
            (self.bis, tr("s5f.bis"), min(4, grenze), 0, 2),
            (self.lagenschritt, tr("s5f.schritt"), min(0.5, grenze), 1, 0),
        ):
            zeile.addWidget(QtGui.QLabel(beschriftung), reihe, spalte)
            feld.setDecimals(2)
            feld.setRange(0.01, grenze)
            feld.setSingleStep(0.5)
            feld.setSuffix(" mm")
            feld.setValue(wert)
            feld.setMaximumWidth(110)
            zeile.addWidget(feld, reihe, spalte + 1)
        self.lagenbereich.setEnabled(grob is not None)
        self.mit_schruppen.toggled.connect(self.lagenbereich.setEnabled)
        layout.addWidget(self.lagenbereich)
        self.tabelle = QtGui.QTreeWidget()
        self.tabelle.setColumnCount(7)
        self.tabelle.setHeaderLabels(
            [
                tr("s5f.zwischenlage"),
                tr("s5p.werkzeug"),
                tr("s5p.bahn"),
                tr("s5p.anstellung"),
                tr("s5p.zeit"),
                tr("s5p.rest"),
                tr("s5p.pruefung"),
            ]
        )
        self.tabelle.setRootIsDecorated(False)
        self.tabelle.setMinimumHeight(180)
        layout.addWidget(self.tabelle)
        self.status = QtGui.QLabel(tr("s5p.bereit"))
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.start = QtGui.QPushButton(tr("s5p.vergleichen"))
        self.start.clicked.connect(self.vergleichen)
        layout.addWidget(self.start)
        self.uebernehmen = QtGui.QPushButton(
            tr("s5f.uebernehmen") if self.mit_schruppen.isChecked() else tr("s5p.uebernehmen")
        )
        self.mit_schruppen.toggled.connect(
            lambda an: self.uebernehmen.setText(
                tr("s5f.uebernehmen") if an else tr("s5p.uebernehmen")
            )
        )
        self.uebernehmen.setEnabled(False)
        self.uebernehmen.clicked.connect(self.accept)
        layout.addWidget(self.uebernehmen)
        self.mit_schruppen.toggled.connect(self.bereich_pruefen)
        for feld in (self.von, self.bis, self.lagenschritt):
            feld.valueChanged.connect(self.bereich_pruefen)
        SimultanPanel.offen = self

    def bereich_pruefen(self, *_werte):
        """Ungültige Bereiche sofort erklären; geänderte Suchwahl erneut rechnen."""
        if self.laeufer is not None:
            return
        self.plan = None
        self.uebernehmen.setEnabled(False)
        try:
            if self.mit_schruppen.isChecked():
                sf.zwischenlagen(
                    self.von.value(),
                    self.bis.value(),
                    self.lagenschritt.value(),
                    float(sf.schruppen_vor(self.op).Zwischenlagen),
                )
        except (ValueError, AttributeError) as fehler:
            self.start.setEnabled(False)
            self.status.setText(str(fehler))
        else:
            self.start.setEnabled(True)
            self.status.setText(tr("s5p.bereit"))

    def getStandardButtons(self):
        return getattr(QtGui.QDialogButtonBox.Cancel, "value", QtGui.QDialogButtonBox.Cancel)

    def vergleichen(self):
        self.start.setEnabled(False)
        self.uebernehmen.setEnabled(False)
        self.tabelle.clear()
        self._zeilen.clear()
        self.plan = None
        self.abbruch = False
        try:
            feinheit = self.bahnfeinheit()
            if self.mit_schruppen.isChecked():
                lagen = sf.zwischenlagen(
                    self.von.value(),
                    self.bis.value(),
                    self.lagenschritt.value(),
                    float(sf.schruppen_vor(self.op).Zwischenlagen),
                )
                self.laeufer = sf.vergleichen(
                    self.op,
                    self.pruefung,
                    self.bibliothek,
                    lagen,
                    fortschritt=self.fortschritt,
                    alle=self.alle.isChecked(),
                    feinheit=feinheit,
                )
            else:
                self.laeufer = sp.vergleichen(
                    self.op,
                    self.pruefung,
                    self.bibliothek,
                    fortschritt=self.fortschritt,
                    alle=self.alle.isChecked(),
                    feinheit=feinheit,
                )
        except (ValueError, AttributeError) as fehler:
            self.start.setEnabled(True)
            self.status.setText(str(fehler))
            return
        self.mit_schruppen.setEnabled(False)
        self.lagenbereich.setEnabled(False)
        self.alle.setEnabled(False)
        self.status.setText(tr("s5p.rechnet"))
        QtCore.QTimer.singleShot(0, self.schritt)

    def bahnfeinheit(self):
        """Die eingetragene Bahnfeinheit in mm, None für den Vorschlag; ValueError mit einem
        Satz, wenn das Feld nicht lesbar ist oder über der Grathöhe liegt."""
        text = self.feinheit.text().strip()
        if not text:
            return None
        try:
            wert = groesse_lesen(text, einheiten.LAENGE)
        except ValueError:
            raise ValueError(tr("s5p.fehler.feinheit")) from None
        if wert <= 0 or wert > float(self.op.Grathoehe) + 1e-9:
            raise ValueError(tr("s5p.fehler.feinheit"))
        return wert

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
            self.alle.setEnabled(True)
            self.mit_schruppen.setEnabled(sf.schruppen_vor(self.op) is not None)
            self.lagenbereich.setEnabled(self.mit_schruppen.isChecked())
            beste = self.plan.beste if self.plan else None
            if beste is None:
                self.status.setText(tr("s5p.fehler.keine"))
            else:
                self.uebernehmen.setEnabled(True)
                if not self.feinheit.text().strip() and beste.bahngrathoehe > 0:
                    # Der Wert, mit dem die Bahn bestand – sichtbar, und fest für den nächsten Lauf.
                    self.feinheit.setText(groesse_zeigen(beste.bahngrathoehe, einheiten.LAENGE, 4))
                werte = {
                    "werkzeug": beste.werkzeug.Label,
                    "bahn": richtung_text(beste.richtung),
                    "anstellung": anstellung_text(beste.anstellung),
                    "zeit": ab.dauer_text(beste.sekunden),
                    "lage": f"{beste.zwischenlagen:g}".replace(".", dezimalzeichen()),
                }
                self.status.setText(
                    tr("s5f.beste", **werte)
                    if self.plan.schruppen is not None
                    else tr("s5p.beste", **werte)
                )
            return
        except Exception as fehler:
            self.laeufer = None
            self.start.setEnabled(True)
            self.alle.setEnabled(True)
            self.mit_schruppen.setEnabled(sf.schruppen_vor(self.op) is not None)
            self.lagenbereich.setEnabled(self.mit_schruppen.isChecked())
            self.status.setText(str(fehler))
            FreeCAD.Console.PrintError(f"{tr('s5p.titel')}: {fehler}\n")
            return
        QtCore.QTimer.singleShot(0, self.schritt)

    def zeige(self, variante):
        # Je Stufe der Bahnfeinheit eine eigene Zeile (P-2026-10-09-15): So sieht man, warum
        # 75 % abgelehnt wurden und wo es bestand.
        key = (
            variante.zwischenlagen,
            variante.werkzeug.Name,
            variante.richtung,
            variante.anstellung,
            round(variante.bahngrathoehe, 6),
        )
        if key not in self._zeilen:
            self._zeilen[key] = QtGui.QTreeWidgetItem(self.tabelle)
        zeile = self._zeilen[key]
        rest = (
            f"{max(0, variante.rest):.3f}".replace(".", dezimalzeichen())
            if math.isfinite(variante.rest)
            else "–"
        )
        geprueft = tr("s5p.geprueft") if variante.kollision_geprueft else tr("s5p.kollision_offen")
        werte = [
            (
                f"{variante.zwischenlagen:g}".replace(".", dezimalzeichen())
                if variante.zwischenlagen
                else "–"
            ),
            variante.werkzeug.Label,
            (
                richtung_text(variante.richtung)
                + (
                    f" ({groesse_fest(variante.bahngrathoehe, einheiten.LAENGE, 4)} mm)"
                    if variante.bahngrathoehe > 0
                    else ""
                )
                if variante.richtung
                else tr("s5f.schruppen")
            ),
            anstellung_text(variante.anstellung) if variante.anstellung else "–",
            ab.dauer_text(variante.sekunden) if math.isfinite(variante.sekunden) else "–",
            rest,
            variante.grund or geprueft,
        ]
        for i, wert in enumerate(werte):
            zeile.setText(i, wert)
            zeile.setToolTip(i, wert)
        for i in range(6):
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
