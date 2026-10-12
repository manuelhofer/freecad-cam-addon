# SPDX-License-Identifier: LGPL-2.1-or-later
"""Das Fenster „STL als Teil“ (W-017): bevor der 4-Achs-Assistent ein Netz bekommt, sieht man seine
Maße und Dreiecke und stellt den Maßstab ein – „× 25,4 (Zoll)“ oder eine Höhe in mm (Manuel,
2026-10-11: „vielleicht kann man es skalieren“). „Umwandeln“ macht daraus den Körper aus seinen
Dreiecken (stl_teil.koerper_aus_netz), ein Schritt Rückgängig; das Netz wird ausgeblendet, der Körper
ohne die Kanten der Dreiecke gezeigt – er sieht aus wie das Netz."""

import FreeCADGui
from PySide import QtCore, QtGui

from . import stl_anzeige, stl_teil
from .gui_teile import ruhiges_mausrad
from .gui_zahlen import dezimal, zahlenformat
from .sprache import tr


class StlDialog(QtGui.QDialog):
    """Maße, Dreiecke und Maßstab eines Netzes; `massstab()` nach „Umwandeln“. Mit `n_eck` (aus
    dem Assistenten „Bearbeitung“) darunter das Rohteil: wie bisher oder eine N-Eck-Stange im
    Schraubstock (W-018) – `n_eck_wahl()`; `nur_rohteil`: der Körper ist schon da, nur das."""

    offen = None  # für die Szenarien

    def __init__(self, netzobjekt, eltern=None, n_eck=False, nur_rohteil=False):
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
        self.n_eck = None
        if n_eck:
            self.n_eck = self._n_eck_gruppe()
            aufbau.addWidget(self.n_eck)
        if nur_rohteil:
            for i in range(raster.count()):
                raster.itemAt(i).widget().setVisible(False)
            self.masse_text.setVisible(False)
        knoepfe = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        knoepfe.button(QtGui.QDialogButtonBox.Ok).setText(
            tr("stl.weiter") if nur_rohteil else tr("stl.umwandeln")
        )
        knoepfe.accepted.connect(self.accept)
        knoepfe.rejected.connect(self.reject)
        aufbau.addWidget(knoepfe)
        self._masse_zeigen()
        ruhiges_mausrad(self)

    def _n_eck_gruppe(self):
        """„Aus einer N-Eck-Stange im Schraubstock“ (W-018): N, die Achse des Teils längs der
        Stange, Umdrehen, die Spannlänge."""
        from . import n_eck as ne

        gruppe = QtGui.QGroupBox(tr("stl.neck"))
        gruppe.setCheckable(True)
        gruppe.setChecked(False)
        gruppe.setToolTip(tr("stl.neck.tooltip"))
        raster = QtGui.QGridLayout(gruppe)
        raster.addWidget(QtGui.QLabel(tr("stl.neck.n")), 0, 0)
        self.feld_n = QtGui.QSpinBox()
        self.feld_n.setRange(4, 24)
        self.feld_n.setSingleStep(2)
        self.feld_n.setValue(ne.VORGABE_N)
        self.feld_n.setToolTip(tr("stl.neck.n.tooltip"))
        raster.addWidget(self.feld_n, 0, 1)
        raster.addWidget(QtGui.QLabel(tr("stl.neck.achse")), 1, 0)
        self.feld_achse = QtGui.QComboBox()
        for name in ne.TEILACHSEN:
            self.feld_achse.addItem(name, name)
        self.feld_achse.setCurrentIndex(self.feld_achse.findData("Z"))
        self.feld_achse.setToolTip(tr("stl.neck.achse.tooltip"))
        raster.addWidget(self.feld_achse, 1, 1)
        self.feld_umgedreht = QtGui.QCheckBox(tr("stl.neck.umgedreht"))
        raster.addWidget(self.feld_umgedreht, 1, 2)
        raster.addWidget(QtGui.QLabel(tr("stl.neck.spannlaenge")), 2, 0)
        self.feld_spannlaenge = QtGui.QDoubleSpinBox()
        self.feld_spannlaenge.setLocale(zahlenformat())
        self.feld_spannlaenge.setDecimals(1)
        self.feld_spannlaenge.setRange(1.0, 500.0)
        self.feld_spannlaenge.setValue(ne.SPANNLAENGE)
        self.feld_spannlaenge.setSuffix(" mm")
        raster.addWidget(self.feld_spannlaenge, 2, 1)
        return gruppe

    def n_eck_wahl(self):
        """{n, achse, umgedreht, spannlaenge} – oder None, wenn die N-Eck-Stange nicht gewählt
        ist."""
        if self.n_eck is None or not self.n_eck.isChecked():
            return None
        n = int(self.feld_n.value())
        return {
            "n": n + (n % 2),
            "achse": self.feld_achse.currentData(),
            "umgedreht": self.feld_umgedreht.isChecked(),
            "spannlaenge": float(self.feld_spannlaenge.value()),
        }

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


def ohne_kanten(objekt):
    """Ein Körper aus einem STL (oder sein Klon) ohne die Kanten seiner Dreiecke – sonst decken
    68.242 schwarze Kanten ihn zu, auch seine Farben."""
    ansicht = getattr(objekt, "ViewObject", None)
    if ansicht is not None and "Shaded" in ansicht.getEnumerationsOfProperty("DisplayMode"):
        ansicht.DisplayMode = "Shaded"


def gewaehltes_netz(dokument):
    """Das gewählte Netz (ein eingelesenes STL) – oder None."""
    return next(
        (o for o in FreeCADGui.Selection.getSelection(dokument.Name) if stl_teil.ist_netz(o)),
        None,
    )


def stl_angebot(dokument, titel):
    """Ist nichts gewählt und liegt im Dokument genau ein Körper aus einem STL – oder ohne ihn
    genau ein Netz –, fragt es, ob man ihn bearbeiten will (Manuel, 2026-10-12: „hey, da ist ein
    STL geöffnet … vielleicht will der Bediener ja die in 4 Achsen bearbeiten, also frag ich
    mal“ – ohne Auswahl ließ sich im Assistenten nichts anklicken, ein Netz hat keine Flächen).
    Gibt das Netz oder den Körper zurück – None ohne Angebot oder mit „Nein“."""
    if FreeCADGui.Selection.getSelection(dokument.Name):
        return None
    koerper = [o for o in dokument.Objects if stl_teil.aus_stl(o)]
    netze = [o for o in dokument.Objects if stl_teil.ist_netz(o)]
    if len(koerper) == 1:
        angebot = koerper[0]
    elif not koerper and len(netze) == 1:
        angebot = netze[0]
    else:
        return None
    antwort = QtGui.QMessageBox.question(
        FreeCADGui.getMainWindow(),
        titel,
        tr("stl.angebot", name=angebot.Label),
        QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
        QtGui.QMessageBox.Yes,
    )
    return angebot if antwort == QtGui.QMessageBox.Yes else None


def teil_aus_netz(dokument, netzobjekt, frage=True, n_eck=False):
    """Der Körper zum Netz: einer, der schon daraus gemacht ist, sonst – nach dem Fenster (`frage`)
    – ein neuer (ein Schritt Rückgängig). None, wenn man abbricht oder es nicht geht (die Meldung
    sagt warum). `n_eck` (der Assistent „Bearbeitung“): Das Fenster fragt auch nach dem Rohteil –
    die Wahl steht danach in `teil_aus_netz.n_eck` (None: wie bisher)."""
    teil_aus_netz.n_eck = None
    vorhanden = next(
        (
            o
            for o in dokument.Objects
            if stl_teil.aus_stl(o) and getattr(o, stl_teil.EIGENSCHAFT_STL, None) is netzobjekt
        ),
        None,
    )
    if vorhanden is not None:
        if n_eck and frage:
            dialog = StlDialog(netzobjekt, n_eck=True, nur_rohteil=True)
            if dialog.exec() != QtGui.QDialog.Accepted:
                return None
            teil_aus_netz.n_eck = dialog.n_eck_wahl()
        return vorhanden
    massstab = 1.0
    if frage:
        dialog = StlDialog(netzobjekt, n_eck=n_eck)
        if dialog.exec() != QtGui.QDialog.Accepted:
            return None
        massstab = dialog.massstab()
        teil_aus_netz.n_eck = dialog.n_eck_wahl()
    dokument.openTransaction(tr("stl.titel"))
    QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
    try:
        gerechnet = _im_hintergrund(netzobjekt, massstab)
        teil, bericht = stl_teil.koerper_aus_netz(dokument, netzobjekt, massstab, gerechnet)
        stl_anzeige.zeigen(teil, True)  # als Netz: 0,06 statt 1,7 s am Geist
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
    ohne_kanten(teil)  # wie das Netz
    if getattr(netzobjekt, "ViewObject", None) is not None:
        netzobjekt.ViewObject.Visibility = False
    FreeCADGui.Selection.clearSelection()
    FreeCADGui.Selection.addSelection(teil)
    teil_aus_netz.bericht = dezimal(bericht.text())
    return teil


teil_aus_netz.bericht = ""  # der Satz zum letzten Umwandeln – zeigt der Assistent
teil_aus_netz.n_eck = None  # die Wahl der N-Eck-Stange im letzten Fenster (W-018)


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
