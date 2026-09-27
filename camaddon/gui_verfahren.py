# SPDX-License-Identifier: LGPL-2.1-or-later
"""Aufgabenfenster „Maschine verfahren“ (Spezifikation W-001, Stufe 3).

Je Achse eine Zeile: Name (NC-Name der Betriebsart, sonst das Gelenk), ein
Regler, ein Zahlenfeld mit Einheit und darunter die Grenzen. Die Assembly
bewegt sich beim Ziehen mit, über die Grenzen des Gelenks hinaus geht es
nicht. OK behält die Stellung (ein Schritt Rückgängig), Abbrechen stellt
alles zurück, „Grundstellung“ fährt alle Achsen auf den Stand beim Öffnen.
Gerechnet wird in verfahren.py.

Hat die Maschine eine schräge Achse (W-001, Abschnitt 7c), gibt es oben
einen Umschalter: „wie im Programm“ – zuerst gewählt (Manuel) – zeigt statt
der beiden Schlitten X und Y des Programms, und für Y fahren beide
(schraege_achse.Programm); „der Maschine“ je Schlitten einen Regler. Grau
darunter steht jeweils die andere Sicht, und hält ein Schlitten an seiner
Grenze, sagt eine rote Zeile, welcher.
"""

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import beispielmaschine, einheiten, schraege_achse, symbol
from . import maschine as m
from . import verfahren as vf
from .gui_hilfe import kopfzeile
from .gui_maschine import beispiel_waehlen, gewaehlte_assembly
from .gui_teile import GRAU, RuhigerRegler, fett, hinweiszeile, ruhiges_mausrad
from .gui_zahlen import zahlenformat
from .kette import LINEAR
from .sprache import tr

# Feinheit der Regler: Schritte je mm bzw. je Grad.
SCHRITTE_JE_EINHEIT = 10
# Reichweite, wenn das Gelenk keine Begrenzung hat: so weit um die Stellung beim Öffnen.
OHNE_GRENZE_LINEAR = 1000.0  # mm
OHNE_GRENZE_DREH = 360.0  # Grad
FELD_GRENZE = 99999.0  # größter Betrag im Zahlenfeld ohne Begrenzung
PLATZ_TOLERANZ = 0.05  # Grad – so nah, und der Platz gilt als eingeschwenkt


class BefehlMaschineVerfahren:
    """Befehl in der Werkzeugleiste: öffnet das Fenster für die gewählte Assembly."""

    def GetResources(self):
        return {
            "Pixmap": symbol("verfahren.svg"),
            "MenuText": tr("befehl.verfahren.titel"),
            "ToolTip": tr("befehl.verfahren.tooltip"),
        }

    def IsActive(self):
        # Wie „Maschine bearbeiten“: bedienbar, solange kein anderes
        # Aufgabenfenster offen ist – was fehlt, sagt der Befehl selbst.
        return not FreeCADGui.Control.activeDialog()

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        assembly = gewaehlte_assembly(doc) if doc else None
        if assembly is None:
            gewaehlt = beispiel_waehlen(tr("vf.titel"))
            if gewaehlt is None:
                return
            assembly, _maschine = beispielmaschine.lade(*gewaehlt)
            doc = assembly.Document
        verfahren = vf.Verfahren(assembly)
        if not verfahren.achsen:
            QtGui.QMessageBox.information(
                FreeCADGui.getMainWindow(), tr("vf.titel"), tr("vf.keine_achsen")
            )
            return
        # Ein Schritt für alles, was bis OK passiert; Abbrechen verwirft ihn.
        doc.openTransaction(tr("vf.titel"))
        # Gewählt leuchtete sonst die ganze Maschine, solange das Fenster offen ist.
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Control.showDialog(VerfahrPanel(assembly, verfahren))


def _anzeige(achse, wert):
    """Stellung fürs Feld: Linearachsen in mm oder inch, Drehachsen in Grad."""
    return einheiten.anzeige(wert, einheiten.LAENGE) if achse.art == LINEAR else wert


def _metrisch(achse, wert):
    """Stellung aus dem Feld zurück in mm bzw. Grad – so fährt die Achse."""
    return einheiten.metrisch(wert, einheiten.LAENGE) if achse.art == LINEAR else wert


def _zahl(wert, stellen):
    return zahlenformat().toString(float(wert), "f", stellen)


def _weg(wert):
    """Ein Weg zum Lesen: „−5,77 mm“ bzw. in inch."""
    stellen = einheiten.stellen(einheiten.LAENGE, 2)
    # + 0.0 macht aus −0,00 eine 0,00.
    gezeigt = round(einheiten.anzeige(wert, einheiten.LAENGE), stellen) + 0.0
    zahl = _zahl(gezeigt, stellen).replace("-", "−")
    return f"{zahl} {einheiten.einheit(einheiten.LAENGE)}"


class VerfahrPanel:
    """Das Aufgabenfenster. FreeCAD ruft `getStandardButtons`, `accept` und `reject` auf."""

    offen = None  # das gerade offene Fenster – für die Oberflächen-Szenarien

    def __init__(self, assembly, verfahren):
        VerfahrPanel.offen = self
        self.assembly = assembly
        self.doc = assembly.Document
        self.verfahren = verfahren
        self.maschine = m.finde_maschine(assembly)
        self.zeilen = {}  # Achse -> (Regler, Zahlenfeld)
        self.programmzeilen = {}  # "x"/"y" -> (Regler, Zahlenfeld) – wie im Programm
        self.platzwahl = {}  # Revolverachse -> (Auswahl, [(Platz, Stellung)])
        self.programm = self._programm()  # schraege_achse.Programm oder None
        self.wie_im_programm = self.programm is not None  # zuerst wie im Programm (Manuel)
        self.form = self._baue()

    def getStandardButtons(self):
        return QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel

    def accept(self):
        VerfahrPanel.offen = None
        self.doc.commitTransaction()
        FreeCADGui.Control.closeDialog()
        self.doc.recompute()
        return True

    def reject(self):
        VerfahrPanel.offen = None
        # Die Transaktion stellt die Lagen wieder her; zur Sicherheit vorher selbst.
        self.verfahren.grundstellung()
        self.doc.abortTransaction()
        FreeCADGui.Control.closeDialog()
        self.doc.recompute()
        return True

    # --- Aufbau ---------------------------------------------------------------------

    def _baue(self):
        form = QtGui.QWidget()
        form.setWindowTitle(tr("vf.titel"))
        form.setWindowIcon(QtGui.QIcon(symbol("verfahren.svg")))
        aufbau = QtGui.QVBoxLayout(form)
        aufbau.addWidget(kopfzeile(tr("vf.titel"), "verfahren"))
        erklaerung = QtGui.QLabel(tr("vf.erklaerung"))
        erklaerung.setWordWrap(True)
        aufbau.addWidget(erklaerung)
        if self.programm is not None:
            aufbau.addWidget(self._baue_umschalter())

        # Das Raster der Regler wird beim Umschalten neu gebaut – hier steht es.
        self._rasterplatz = QtGui.QVBoxLayout()
        aufbau.addLayout(self._rasterplatz)
        self.raster = None
        self._baue_raster()
        self.anschlag = hinweiszeile()
        self.anschlag.hide()
        aufbau.addWidget(self.anschlag)

        self.knopf_grundstellung = QtGui.QPushButton(tr("vf.grundstellung"))
        self.knopf_grundstellung.setToolTip(tr("vf.grundstellung.tooltip"))
        self.knopf_grundstellung.setAutoDefault(False)
        self.knopf_grundstellung.clicked.connect(self.grundstellung)
        zeile = QtGui.QHBoxLayout()
        zeile.addWidget(self.knopf_grundstellung)
        zeile.addStretch()
        aufbau.addLayout(zeile)
        aufbau.addStretch()
        return ruhiges_mausrad(form)

    def _programm(self):
        """Die erste schräge Achse der Maschine, mit der sich im Programm fahren lässt."""
        if self.maschine is None:
            return None
        for trafo in m.transformationen(self.maschine):
            if schraege_achse.Programm.moeglich(self.verfahren, self.maschine, trafo):
                return schraege_achse.Programm(self.verfahren, self.maschine, trafo)
        return None

    def _baue_umschalter(self):
        """„Achsen: (•) wie im Programm  ( ) der Maschine“."""
        zeile = QtGui.QWidget()
        aufbau = QtGui.QHBoxLayout(zeile)
        aufbau.setContentsMargins(0, 0, 0, 0)
        aufbau.addWidget(QtGui.QLabel(tr("vf.modus")))
        self.knopf_programm = QtGui.QRadioButton(tr("vf.modus.programm"))
        self.knopf_programm.setToolTip(
            tr(
                "vf.modus.programm.tooltip",
                name=self.programm.trafo.NameSchraeg,
                schraeg=vf.namen(self.maschine, self.programm.schraeg),
                ausgleich=vf.namen(self.maschine, self.programm.ausgleich),
            )
        )
        self.knopf_maschine = QtGui.QRadioButton(tr("vf.modus.maschine"))
        self.knopf_maschine.setToolTip(tr("vf.modus.maschine.tooltip"))
        self.knopf_programm.setChecked(self.wie_im_programm)
        self.knopf_maschine.setChecked(not self.wie_im_programm)
        self.knopf_programm.toggled.connect(self._modus_gewechselt)
        aufbau.addWidget(self.knopf_programm)
        aufbau.addWidget(self.knopf_maschine)
        aufbau.addStretch()
        return zeile

    def _modus_gewechselt(self, _an=None):
        self.wie_im_programm = self.knopf_programm.isChecked()
        self.anschlag.hide()
        self._baue_raster()

    def waehle_modus(self, wie_im_programm):
        """Schaltet um: True = wie im Programm, False = der Maschine – für die Szenarien."""
        knopf = self.knopf_programm if wie_im_programm else self.knopf_maschine
        knopf.setChecked(True)

    def _baue_raster(self):
        """Je Achse eine Zeile; wie im Programm X und Y statt der beiden Schlitten."""
        if self.raster is not None:
            self._rasterplatz.removeWidget(self.raster)
            self.raster.deleteLater()
        self.zeilen, self.programmzeilen, self.platzwahl = {}, {}, {}
        self.info = None
        self.raster = QtGui.QWidget()
        gitter = QtGui.QGridLayout(self.raster)
        gitter.setContentsMargins(0, 0, 0, 0)
        gitter.setColumnStretch(1, 1)
        programm = self.programm if self.wie_im_programm else None
        zeile = 0
        for achse in vf.fensterreihenfolge(self.maschine, self.verfahren.achsen):
            if programm is not None and achse is programm.ausgleich:
                zeile = self._baue_programmzeile(gitter, zeile, "x")
            elif programm is not None and achse is programm.schraeg:
                zeile = self._baue_programmzeile(gitter, zeile, "y")
            else:
                zeile = self._baue_zeile(gitter, zeile, achse)
            if self.programm is not None and achse is self.programm.schraeg:
                # Grau darunter die andere Sicht: die Schlitten bzw. das Programm.
                # Umbrechend und bis zum Rand – sonst drückte die Zeile das Fenster
                # breiter als den Aufgabenbereich.
                self.info = QtGui.QLabel()
                self.info.setWordWrap(True)
                self.info.setStyleSheet(f"color: {GRAU.name()};")
                gitter.addWidget(self.info, zeile, 1, 1, -1)
                zeile += 1
        self._rasterplatz.addWidget(ruhiges_mausrad(self.raster))
        self._info_zeigen()

    def _baue_programmzeile(self, gitter, zeile, welche):
        """Wie _baue_zeile, für X oder Y des Programms („x“, „y“); gibt die nächste Zeile zurück.

        Die Regler reichen so weit, wie die Achse überhaupt kommt – wie weit es
        gerade geht, hängt von der anderen ab; dann hält die Bewegung an.
        """
        trafo = self.programm.trafo
        name = trafo.NameAusgleich if welche == "x" else trafo.NameSchraeg
        andere = trafo.NameSchraeg if welche == "x" else trafo.NameAusgleich
        einheit = einheiten.einheit(einheiten.LAENGE)
        stellen = einheiten.stellen(einheiten.LAENGE, 2)
        x, y = self.programm.stellung()
        stellung = x if welche == "x" else y
        bereich_x, bereich_y = self.programm.bereich()
        minimum, maximum = bereich_x if welche == "x" else bereich_y
        unten = minimum if minimum is not None else stellung - OHNE_GRENZE_LINEAR
        oben = maximum if maximum is not None else stellung + OHNE_GRENZE_LINEAR

        beschriftung = fett(name)
        beschriftung.setToolTip(
            tr(
                "vf.programmachse.tooltip",
                schraeg=vf.namen(self.maschine, self.programm.schraeg),
                ausgleich=vf.namen(self.maschine, self.programm.ausgleich),
            )
        )
        regler = RuhigerRegler(QtCore.Qt.Horizontal)
        regler.setRange(round(unten * SCHRITTE_JE_EINHEIT), round(oben * SCHRITTE_JE_EINHEIT))
        regler.setValue(round(stellung * SCHRITTE_JE_EINHEIT))
        regler.setToolTip(tr("vf.regler.tooltip"))
        feld = QtGui.QDoubleSpinBox()
        feld.setLocale(zahlenformat())
        feld.setDecimals(stellen)
        feld.setRange(
            einheiten.anzeige(unten, einheiten.LAENGE) if minimum is not None else -FELD_GRENZE,
            einheiten.anzeige(oben, einheiten.LAENGE) if maximum is not None else FELD_GRENZE,
        )
        feld.setSuffix(f" {einheit}")
        feld.setValue(einheiten.anzeige(stellung, einheiten.LAENGE))
        feld.setKeyboardTracking(False)
        regler.valueChanged.connect(
            lambda wert, w=welche: self.setze_programm(w, wert / SCHRITTE_JE_EINHEIT)
        )
        feld.valueChanged.connect(
            lambda wert, w=welche: self.setze_programm(
                w, einheiten.metrisch(wert, einheiten.LAENGE)
            )
        )
        self.programmzeilen[welche] = (regler, feld)
        gitter.addWidget(beschriftung, zeile, 0)
        gitter.addWidget(regler, zeile, 1)
        gitter.addWidget(feld, zeile, 2)
        if minimum is None or maximum is None:
            text = tr("vf.ohne_grenze")
        else:
            text = tr(
                "vf.grenzen_programm",
                min=_zahl(einheiten.anzeige(minimum, einheiten.LAENGE), stellen),
                max=_zahl(einheiten.anzeige(maximum, einheiten.LAENGE), stellen),
                einheit=einheit,
                andere=andere,
            )
        grenzen = QtGui.QLabel(text)
        grenzen.setWordWrap(True)
        grenzen.setStyleSheet(f"color: {GRAU.name()};")
        grenzen.setToolTip(tr("vf.grenzen.tooltip"))
        gitter.addWidget(grenzen, zeile + 1, 1, 1, -1)
        return zeile + 2

    def _baue_zeile(self, gitter, zeile, achse):
        """Name, Regler und Zahlenfeld; darunter grau die Grenzen. Gibt die nächste Zeile zurück.

        Der Regler zählt in Zehntel mm bzw. Grad; das Feld zeigt
        Linearachsen in mm oder inch (einheiten.py).
        """
        linear = achse.art == LINEAR
        einheit = einheiten.einheit(einheiten.LAENGE) if linear else "°"
        stellen = einheiten.stellen(einheiten.LAENGE, 2) if linear else 1
        stellung = self.verfahren.stellung(achse)
        unten, oben = self._bereich(achse, stellung)

        name = fett(vf.namen(self.maschine, achse))
        name.setToolTip(tr("vf.gelenk.tooltip", gelenk=achse.gelenk.Label))
        regler = RuhigerRegler(QtCore.Qt.Horizontal)
        regler.setRange(round(unten * SCHRITTE_JE_EINHEIT), round(oben * SCHRITTE_JE_EINHEIT))
        regler.setValue(round(stellung * SCHRITTE_JE_EINHEIT))
        regler.setToolTip(tr("vf.regler.tooltip"))
        feld = QtGui.QDoubleSpinBox()
        feld.setLocale(zahlenformat())
        feld.setDecimals(stellen)
        minimum, maximum = self.verfahren.grenzen(achse)
        feld.setRange(
            _anzeige(achse, minimum) if minimum is not None else -FELD_GRENZE,
            _anzeige(achse, maximum) if maximum is not None else FELD_GRENZE,
        )
        feld.setSuffix(f" {einheit}")
        feld.setValue(_anzeige(achse, stellung))
        feld.setKeyboardTracking(False)  # erst nach Enter oder Verlassen fahren
        regler.valueChanged.connect(lambda wert, a=achse: self.setze(a, wert / SCHRITTE_JE_EINHEIT))
        feld.valueChanged.connect(lambda wert, a=achse: self.setze(a, _metrisch(a, wert)))
        self.zeilen[achse] = (regler, feld)

        gitter.addWidget(name, zeile, 0)
        gitter.addWidget(regler, zeile, 1)
        gitter.addWidget(feld, zeile, 2)
        plaetze = vf.platzstellungen(self.verfahren, self.maschine, achse)
        if plaetze:
            wahl = QtGui.QComboBox()
            wahl.addItem("–", None)
            for platz, platz_stellung in plaetze:
                wahl.addItem(platz, platz_stellung)
            wahl.setToolTip(tr("vf.platz.tooltip"))
            wahl.activated.connect(lambda index, a=achse: self._platz_gewaehlt(a, index))
            # Unter dem Zahlenfeld statt in einer vierten Spalte – die kostete
            # jeder Zeile Platz, und die Regler schrumpften auf den Griff.
            gitter.addWidget(wahl, zeile + 1, 2)
            self.platzwahl[achse] = (wahl, plaetze)
            self._platz_zeigen(achse, stellung)
        grenzen = QtGui.QLabel(self._grenzen_text(achse, einheit, stellen))
        # Umbrechend und bis zum Rand – als eine Zeile zwischen Regler und Feld
        # machte sie das Fenster breiter als den Aufgabenbereich.
        grenzen.setWordWrap(True)
        grenzen.setStyleSheet(f"color: {GRAU.name()};")
        grenzen.setToolTip(tr("vf.grenzen.tooltip"))
        gitter.addWidget(grenzen, zeile + 1, 1, 1, 1 if plaetze else -1)
        return zeile + 2

    def _bereich(self, achse, stellung):
        """Von wo bis wo der Regler reicht: die Grenzen, sonst ein Stück um die Stellung."""
        minimum, maximum = self.verfahren.grenzen(achse)
        weite = OHNE_GRENZE_LINEAR if achse.art == LINEAR else OHNE_GRENZE_DREH
        unten = minimum if minimum is not None else min(stellung - weite, maximum or stellung)
        oben = maximum if maximum is not None else max(stellung + weite, minimum or stellung)
        return unten, oben

    def _grenzen_text(self, achse, einheit, stellen):
        minimum, maximum = self.verfahren.grenzen(achse)
        if minimum is None and maximum is None:
            return tr("vf.ohne_grenze")
        if maximum is None:
            return tr("vf.nur_min", min=_zahl(_anzeige(achse, minimum), stellen), einheit=einheit)
        if minimum is None:
            return tr("vf.nur_max", max=_zahl(_anzeige(achse, maximum), stellen), einheit=einheit)
        return tr(
            "vf.grenzen",
            min=_zahl(_anzeige(achse, minimum), stellen),
            max=_zahl(_anzeige(achse, maximum), stellen),
            einheit=einheit,
        )

    # --- Aktionen -------------------------------------------------------------------

    def setze(self, achse, stellung):
        """Fährt eine Achse; Regler und Zahlenfeld zeigen danach, was erreicht ist."""
        erreicht = self.verfahren.setze(achse, stellung)
        self._zeige(achse, erreicht)
        self.anschlag.hide()
        self._info_zeigen()
        return erreicht

    def setze_programm(self, welche, wert):
        """Fährt X oder Y des Programms („x“, „y“) – beide Schlitten, so weit sie kommen.

        Gibt (x, y) zurück, wo das Werkzeug jetzt steht. Hält ein Schlitten an
        seiner Grenze, sagt die rote Zeile, welcher.
        """
        x, y = self.programm.stellung()
        if welche == "x":
            x = wert
        else:
            y = wert
        x, y, anschlag = self.programm.setze(x, y)
        self._programm_zeigen()
        if anschlag is None:
            self.anschlag.hide()
        else:
            achse, grenze = anschlag
            trafo = self.programm.trafo
            self.anschlag.setText(
                tr(
                    "vf.anschlag",
                    name=trafo.NameAusgleich if welche == "x" else trafo.NameSchraeg,
                    achse=vf.namen(self.maschine, achse),
                    grenze=_weg(grenze),
                )
            )
            self.anschlag.show()
        self._info_zeigen()
        return x, y

    def grundstellung(self):
        """Alle Achsen auf den Stand beim Öffnen."""
        self.verfahren.grundstellung()
        for achse in self.zeilen:
            self._zeige(achse, self.verfahren.stellung(achse))
        self._programm_zeigen()
        self.anschlag.hide()
        self._info_zeigen()

    def _programm_zeigen(self):
        """Regler und Felder von X und Y des Programms auf den Stand der Schlitten."""
        if not self.programmzeilen:
            return
        for welche, wert in zip(("x", "y"), self.programm.stellung(), strict=True):
            regler, feld = self.programmzeilen[welche]
            for element in (regler, feld):
                element.blockSignals(True)
            regler.setValue(round(wert * SCHRITTE_JE_EINHEIT))
            feld.setValue(einheiten.anzeige(wert, einheiten.LAENGE))
            for element in (regler, feld):
                element.blockSignals(False)

    def _info_zeigen(self):
        """Grau unter den Achsen der schrägen Achse: die andere Sicht."""
        if self.info is None:
            return
        trafo = self.programm.trafo
        if self.wie_im_programm:
            x1, y1 = self.programm.schlitten()
            text = tr(
                "vf.schlitten",
                ausgleich=vf.namen(self.maschine, self.programm.ausgleich),
                weg_ausgleich=_weg(x1),
                schraeg=vf.namen(self.maschine, self.programm.schraeg),
                weg_schraeg=_weg(y1),
            )
        else:
            x, y = self.programm.stellung()
            text = tr(
                "vf.im_programm",
                x_name=trafo.NameAusgleich,
                x=_weg(x),
                y_name=trafo.NameSchraeg,
                y=_weg(y),
            )
        self.info.setText(text)

    def _zeige(self, achse, stellung):
        regler, feld = self.zeilen[achse]
        for element in (regler, feld):
            element.blockSignals(True)
        regler.setValue(round(stellung * SCHRITTE_JE_EINHEIT))
        feld.setValue(_anzeige(achse, stellung))
        for element in (regler, feld):
            element.blockSignals(False)
        self._platz_zeigen(achse, stellung)

    def waehle_platz(self, achse, platz):
        """Dreht den Revolver, bis `platz` (etwa „P4“) steht, wo beim Öffnen P1 stand."""
        wahl, _plaetze = self.platzwahl[achse]
        self._platz_gewaehlt(achse, wahl.findText(platz))

    def _platz_gewaehlt(self, achse, index):
        wahl, _plaetze = self.platzwahl[achse]
        stellung = wahl.itemData(index)
        if stellung is not None:
            self.setze(achse, stellung)

    def _platz_zeigen(self, achse, stellung):
        """Die Auswahl zeigt den Platz, der gerade an der Stelle von P1 steht – sonst „–“."""
        if achse not in self.platzwahl:
            return
        wahl, plaetze = self.platzwahl[achse]
        index = 0
        for i, (_platz, platz_stellung) in enumerate(plaetze, start=1):
            if abs((stellung - platz_stellung + 180.0) % 360.0 - 180.0) < PLATZ_TOLERANZ:
                index = i
                break
        wahl.blockSignals(True)
        wahl.setCurrentIndex(index)
        wahl.blockSignals(False)

    def achse(self, name):
        """Die Achse mit diesem Namen im Fenster (NC-Name oder Gelenk) – für die Szenarien."""
        return next(a for a in self.verfahren.achsen if vf.namen(self.maschine, a) == name)
