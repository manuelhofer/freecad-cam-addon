# SPDX-License-Identifier: LGPL-2.1-or-later
"""Das Fenster „STL als Teil“ (W-017): bevor der 4-Achs-Assistent ein Netz bekommt, sieht man seine
Maße und Dreiecke und stellt den Maßstab ein – „× 25,4 (Zoll)“ oder eine Höhe in mm (Manuel,
2026-10-11: „vielleicht kann man es skalieren“). „Umwandeln“ macht daraus den Körper aus seinen
Dreiecken (stl_teil.koerper_aus_netz), ein Schritt Rückgängig; das Netz wird ausgeblendet, der Körper
ohne die Kanten der Dreiecke gezeigt – er sieht aus wie das Netz."""

import FreeCADGui
from PySide import QtCore, QtGui

from . import stl_teil
from .gui_teile import ruhiges_mausrad
from .gui_zahlen import dezimal, zahlenformat
from .sprache import tr


class StlDialog(QtGui.QDialog):
    """Maße, Dreiecke und Maßstab eines Netzes; `massstab()` nach „Umwandeln“."""

    offen = None  # für die Szenarien

    def __init__(self, netzobjekt, eltern=None):
        super().__init__(eltern or FreeCADGui.getMainWindow())
        StlDialog.offen = self
        self.netzobjekt = netzobjekt
        self.setWindowTitle(tr("stl.titel"))
        breite, tiefe, hoehe = stl_teil.masse(netzobjekt.Mesh)
        self._hoehe = hoehe
        aufbau = QtGui.QVBoxLayout(self)
        text = QtGui.QLabel(
            dezimal(
                tr(
                    "stl.text",
                    name=netzobjekt.Label,
                    anzahl=f"{netzobjekt.Mesh.CountFacets:,}".replace(",", "\u202f"),
                    b=f"{breite:.1f}",
                    t=f"{tiefe:.1f}",
                    h=f"{hoehe:.1f}",
                )
            )
        )
        text.setWordWrap(True)
        aufbau.addWidget(text)
        raster = QtGui.QGridLayout()
        raster.addWidget(QtGui.QLabel(tr("stl.massstab")), 0, 0)
        self.feld_massstab = QtGui.QDoubleSpinBox()
        self.feld_massstab.setLocale(zahlenformat())
        self.feld_massstab.setDecimals(4)
        self.feld_massstab.setRange(0.0001, 10000.0)
        self.feld_massstab.setValue(1.0)
        self.feld_massstab.setToolTip(tr("stl.massstab.tooltip"))
        self.feld_massstab.valueChanged.connect(lambda _w: self._masse_zeigen())
        raster.addWidget(self.feld_massstab, 0, 1)
        zoll = QtGui.QPushButton(tr("stl.zoll"))
        zoll.setToolTip(tr("stl.zoll.tooltip"))
        zoll.setAutoDefault(False)
        zoll.clicked.connect(lambda: self.feld_massstab.setValue(25.4))
        raster.addWidget(zoll, 0, 2)
        raster.addWidget(QtGui.QLabel(tr("stl.hoehe")), 1, 0)
        self.feld_hoehe = QtGui.QDoubleSpinBox()
        self.feld_hoehe.setLocale(zahlenformat())
        self.feld_hoehe.setDecimals(2)
        self.feld_hoehe.setRange(0.01, 100000.0)
        self.feld_hoehe.setSuffix(
            " mm"
        )  # wie das STL gelesen wird – auch bei Zoll in der Oberfläche
        self.feld_hoehe.setValue(round(hoehe, 2) if hoehe > 0 else 1.0)
        self.feld_hoehe.setToolTip(tr("stl.hoehe.tooltip"))
        raster.addWidget(self.feld_hoehe, 1, 1)
        auf_hoehe = QtGui.QPushButton(tr("stl.auf_hoehe"))
        auf_hoehe.setAutoDefault(False)
        auf_hoehe.clicked.connect(self._auf_hoehe)
        raster.addWidget(auf_hoehe, 1, 2)
        aufbau.addLayout(raster)
        self.masse_text = QtGui.QLabel()
        self.masse_text.setWordWrap(True)
        aufbau.addWidget(self.masse_text)
        knoepfe = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        knoepfe.button(QtGui.QDialogButtonBox.Ok).setText(tr("stl.umwandeln"))
        knoepfe.accepted.connect(self.accept)
        knoepfe.rejected.connect(self.reject)
        aufbau.addWidget(knoepfe)
        self._masse_zeigen()
        ruhiges_mausrad(self)

    def massstab(self):
        return float(self.feld_massstab.value())

    def _auf_hoehe(self):
        if self._hoehe > 0:
            self.feld_massstab.setValue(self.feld_hoehe.value() / self._hoehe)

    def _masse_zeigen(self):
        f = self.massstab()
        breite, tiefe, hoehe = (x * f for x in stl_teil.masse(self.netzobjekt.Mesh))
        self.masse_text.setText(
            dezimal(tr("stl.danach", b=f"{breite:.1f}", t=f"{tiefe:.1f}", h=f"{hoehe:.1f}"))
        )

    def done(self, ergebnis):
        StlDialog.offen = None
        super().done(ergebnis)


def teil_aus_netz(dokument, netzobjekt, frage=True):
    """Der Körper zum Netz: einer, der schon daraus gemacht ist, sonst – nach dem Fenster (`frage`)
    – ein neuer (ein Schritt Rückgängig). None, wenn man abbricht oder es nicht geht (die Meldung
    sagt warum)."""
    vorhanden = next(
        (
            o
            for o in dokument.Objects
            if stl_teil.aus_stl(o) and getattr(o, stl_teil.EIGENSCHAFT_STL, None) is netzobjekt
        ),
        None,
    )
    if vorhanden is not None:
        return vorhanden
    massstab = 1.0
    if frage:
        dialog = StlDialog(netzobjekt)
        if dialog.exec() != QtGui.QDialog.Accepted:
            return None
        massstab = dialog.massstab()
    dokument.openTransaction(tr("stl.titel"))
    QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
    try:
        gerechnet = _im_hintergrund(netzobjekt, massstab)
        teil, bericht = stl_teil.koerper_aus_netz(dokument, netzobjekt, massstab, gerechnet)
        dokument.recompute()
    except (ValueError, RuntimeError) as fehler:
        dokument.abortTransaction()
        QtGui.QApplication.restoreOverrideCursor()
        QtGui.QMessageBox.warning(
            FreeCADGui.getMainWindow(), tr("stl.titel"), tr("stl.fehler", fehler=str(fehler))
        )
        return None
    QtGui.QApplication.restoreOverrideCursor()
    dokument.commitTransaction()
    ansicht = getattr(teil, "ViewObject", None)
    if ansicht is not None and "Shaded" in ansicht.getEnumerationsOfProperty("DisplayMode"):
        ansicht.DisplayMode = "Shaded"  # ohne die Kanten der Dreiecke: wie das Netz
    if getattr(netzobjekt, "ViewObject", None) is not None:
        netzobjekt.ViewObject.Visibility = False
    FreeCADGui.Selection.clearSelection()
    FreeCADGui.Selection.addSelection(teil)
    teil_aus_netz.bericht = dezimal(bericht.text())
    return teil


teil_aus_netz.bericht = ""  # der Satz zum letzten Umwandeln – zeigt der Assistent


def _im_hintergrund(netzobjekt, massstab):
    """(Form, Bericht) vom Nebenrechner – das Fenster zeichnet sich dabei weiter (nur Klicks
    wartet es ab); None ohne Nebenrechner, dann rechnet der Aufrufer selbst. Das Netz geht als
    STL-Datei hinüber: FreeCAD hält Netze in float32 wie das STL, nichts geht verloren."""
    import os
    import tempfile

    import Mesh

    from . import nebenrechner as nr

    pool = nr.pool()
    if not pool.verfuegbar():
        return None
    griff, datei = tempfile.mkstemp(suffix=".stl", prefix="camaddon_")
    os.close(griff)
    try:
        netzobjekt.Mesh.write(datei)
        auftrag = pool.auftrag("stl_teil", "koerper_rechnen", datei, massstab)
        nebenbei = QtCore.QEventLoop.ExcludeUserInputEvents
        ((form, bericht, zuordnung),) = pool.warten(
            [auftrag], zwischendurch=lambda: QtGui.QApplication.processEvents(nebenbei) or True
        )
        netz = Mesh.Mesh(datei)  # das vorbereitete, vom Nebenrechner zurückgeschrieben
    except nr.NichtVerfuegbar:
        return None
    except nr.Fehler as fehler:
        if fehler.art == "ValueError":
            raise ValueError(fehler.satz or str(fehler)) from fehler
        return None  # gescheitert: hier noch einmal, mit der Meldung von hier
    finally:
        os.remove(datei)
    return form.form(), netz, bericht, zuordnung
