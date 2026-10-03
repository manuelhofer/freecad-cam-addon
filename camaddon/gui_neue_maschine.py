# SPDX-License-Identifier: LGPL-2.1-or-later
"""Befehl und Dialog „Neue Maschine …“ (W-001, Stufe 3b, Schritt 7).

Man wählt eine Bauart und bekommt sie fertig eingerichtet in einem neuen
Dokument – bei der Drehmaschine mit den eigenen Maßen: Name, Bettneigung,
Winkel der Y-Achse, Wege, Revolverplätze, Höchstdrehzahl (Manuel: „so, dass
es ein Leichtes ist, so etwas zu erstellen“). Steht Y schräg, kommt die
schräge Achse gleich mit (beispielmaschine.drehmaschine). Die übrigen
Bauarten haben feste Maße. Danach öffnet sich „Maschine bearbeiten“.

Derselbe Dialog öffnet sich hinter dem Knopf „Neue Maschine …“ in der Meldung
von „Maschine bearbeiten“ und „Maschine verfahren“, wenn es keine Baugruppe
gibt.
"""

import FreeCADGui
from PySide import QtCore, QtGui

from . import beispielmaschine, einheiten, symbol
from .gui_hilfe import kopfzeile
from .gui_teile import GRAU, hinweiszeile, ruhiges_mausrad
from .gui_zahlen import zahlenformat
from .sprache import tr

ROLLE = QtCore.Qt.UserRole
GROESSTE_DREHZAHL = 100000  # U/min im Feld


class BefehlNeueMaschine:
    """Befehl in der Werkzeugleiste: Bauart wählen, Maße eintragen, bauen."""

    def GetResources(self):
        return {
            "Pixmap": symbol("neue_maschine.svg"),
            "MenuText": tr("befehl.neue_maschine.titel"),
            "ToolTip": tr("befehl.neue_maschine.tooltip"),
        }

    def IsActive(self):
        return not FreeCADGui.Control.activeDialog()

    def Activated(self):
        gewaehlt = waehle(tr("neu.titel"))
        if gewaehlt is None:
            return
        assembly, _maschine = beispielmaschine.lade(*gewaehlt)
        # Gleich „Maschine bearbeiten“ – dort steht, was gebaut wurde.
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(assembly)
        FreeCADGui.runCommand("CamAddon_MaschineBearbeiten")


def waehle(titel):
    """Zeigt den Dialog; gibt (Bauart, Maße oder None) zurück – oder None bei Abbrechen."""
    dialog = NeueMaschineDialog(FreeCADGui.getMainWindow(), titel)
    if not dialog.exec():
        return None
    return dialog.gewaehlt(), dialog.masse()


class NeueMaschineDialog(QtGui.QDialog):
    """Die Bauarten als Liste, darunter, was die gewählte zeigt, und bei der
    Drehmaschine ihre Maße. Vorgewählt ist die zuletzt gebaute; Doppelklick baut."""

    offen = None  # der gerade offene Dialog – für die Prüfungen

    def __init__(self, eltern=None, titel=None):
        super().__init__(eltern)
        self.setWindowTitle(titel or tr("neu.titel"))
        self.setMinimumWidth(520)
        text = QtGui.QLabel(tr("beispiel.auswahl.text"))
        text.setWordWrap(True)
        self.liste = QtGui.QListWidget()
        for art in beispielmaschine.ARTEN:
            eintrag = QtGui.QListWidgetItem(beispielmaschine.titel(art))
            eintrag.setData(ROLLE, art)
            self.liste.addItem(eintrag)
        # So hoch, dass alle Bauarten ohne Rollbalken hineinpassen.
        self.liste.setFixedHeight(
            self.liste.sizeHintForRow(0) * self.liste.count() + 2 * self.liste.frameWidth() + 4
        )
        self.beschreibung = QtGui.QLabel()
        self.beschreibung.setWordWrap(True)
        self.beschreibung.setMinimumHeight(3 * self.fontMetrics().lineSpacing())
        self.beschreibung.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.masse_bereich = self._baue_masse()
        self.fest = QtGui.QLabel(tr("neu.masse.fest"))
        self.fest.setWordWrap(True)
        self.fehler = hinweiszeile()
        self.fehler.hide()
        self.knoepfe = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel
        )
        self.knoepfe.button(QtGui.QDialogButtonBox.Ok).setText(tr("neu.bauen"))
        self.knoepfe.accepted.connect(self.accept)
        self.knoepfe.rejected.connect(self.reject)
        self.liste.currentItemChanged.connect(self._gewechselt)
        self.liste.itemDoubleClicked.connect(lambda _eintrag: self.accept())

        aufbau = QtGui.QVBoxLayout(self)
        # Nie kleiner als der Inhalt: Sonst quetschte Qt die Zeilen der Drehmaschine übereinander.
        aufbau.setSizeConstraint(QtGui.QLayout.SetMinimumSize)
        for widget in (text, self.liste, self.beschreibung):
            aufbau.addWidget(widget)
        aufbau.addWidget(kopfzeile(tr("neu.masse"), "neue_maschine"))
        for widget in (self.masse_bereich, self.fest, self.fehler):
            aufbau.addWidget(widget)
        # Hat die Bauart weniger Felder, bleibt der Platz über den Knöpfen – nicht als Lücke
        # über „Maße“.
        aufbau.addStretch(1)
        aufbau.addWidget(self.knoepfe)
        zuletzt = beispielmaschine.zuletzt_gewaehlt()
        self.liste.setCurrentRow(beispielmaschine.ARTEN.index(zuletzt))
        ruhiges_mausrad(self)
        NeueMaschineDialog.offen = self

    # --- Aufbau ---------------------------------------------------------------------

    def _baue_masse(self):
        """Die Felder der Maße – vorbelegt wie das Beispiel der Drehmaschine; was nur sie hat,
        blendet die 3-Achs-Fräse aus (D-26)."""
        vorgabe = beispielmaschine.DrehmaschinenMasse()
        bereich = QtGui.QWidget()
        formular = QtGui.QFormLayout(bereich)
        self._formular = formular
        formular.setContentsMargins(0, 0, 0, 0)

        self.feld_name = QtGui.QLineEdit()
        self.feld_name.setPlaceholderText(beispielmaschine.titel(beispielmaschine.DREHMASCHINE))
        self.feld_name.setToolTip(tr("neu.name.tooltip"))
        formular.addRow(tr("neu.name"), self.feld_name)

        self.feld_bett = _winkelfeld(vorgabe.bettneigung, beispielmaschine.BETTNEIGUNG_BEREICH)
        self.feld_bett.setToolTip(tr("neu.bettneigung.tooltip"))
        formular.addRow(tr("neu.bettneigung"), self.feld_bett)
        self.feld_y_winkel = _winkelfeld(vorgabe.y_winkel, beispielmaschine.Y_WINKEL_BEREICH)
        self.feld_y_winkel.setToolTip(tr("neu.y_winkel.tooltip"))
        formular.addRow(tr("neu.y_winkel"), self.feld_y_winkel)

        # X im Durchmesser oder im Radius – wie die Steuerung X zeigt (Manuel, 2026-09-30,
        # P-2026-09-30-54). Die X-Wege darunter zählen genauso.
        self.wahl_x = QtGui.QComboBox()
        self.wahl_x.addItem(tr("neu.x.durchmesser"), True)
        self.wahl_x.addItem(tr("neu.x.radius"), False)
        self.wahl_x.setCurrentIndex(self.wahl_x.findData(vorgabe.x_durchmesser))
        self.wahl_x.setToolTip(tr("neu.x.tooltip"))
        formular.addRow(tr("neu.x"), self.wahl_x)
        self._x_faktor_gezeigt = 1.0  # so zeigen die Felder von X gerade: 2 im Durchmesser

        self.felder_weg = {}
        self._weg_zeilen = {}
        # „von“ zählt ins Minus: Das Minus steht fest vor dem Feld, eingetragen wird nur die
        # Zahl (Manuel, 2026-10-01: „man versucht, einen Wert einzutragen“). Nur Z der
        # Drehmaschine zählt ab der Spindelnase, beide Enden ohne Minus (_gewechselt).
        self._negativ = {"X": True, "Y": True, "Z": True}
        for achse, weg in (("X", vorgabe.weg_x), ("Y", vorgabe.weg_y), ("Z", vorgabe.weg_z)):
            von, bis = _wegfeld(weg[0], negativ=True), _wegfeld(weg[1], negativ=False)
            zeile = QtGui.QWidget()
            reihe = QtGui.QHBoxLayout(zeile)
            reihe.setContentsMargins(0, 0, 0, 0)
            reihe.addWidget(von)
            reihe.addWidget(QtGui.QLabel(tr("neu.bis")))
            reihe.addWidget(bis)
            zeile.setToolTip(tr("neu.weg.tooltip"))
            formular.addRow(tr("neu.weg", achse=achse), zeile)
            self.felder_weg[achse] = (von, bis)
            self._weg_zeilen[achse] = zeile
        self._x_beschriftung = formular.labelForField(self._weg_zeilen["X"])
        # Wovon die Wege der Drehmaschine zählen – wie an der Maschine (Manuel, 2026-09-30:
        # „ich glaube man muss das etwas konkretisieren“).
        self.wege_drehmaschine = QtGui.QLabel(tr("neu.wege.drehmaschine"))
        self.wege_drehmaschine.setWordWrap(True)
        self.wege_drehmaschine.setStyleSheet(f"color: {GRAU.name()};")
        # Im Formular bekäme die umbrochene Zeile nur die Höhe einer – zwei Zeilen fest.
        self.wege_drehmaschine.setMinimumHeight(2 * self.fontMetrics().lineSpacing() + 4)
        formular.addRow(self.wege_drehmaschine)

        self.feld_plaetze = QtGui.QSpinBox()
        self.feld_plaetze.setRange(*beispielmaschine.PLAETZE_BEREICH)
        self.feld_plaetze.setValue(vorgabe.plaetze)
        self.feld_plaetze.setToolTip(tr("neu.plaetze.tooltip"))
        formular.addRow(tr("neu.plaetze"), self.feld_plaetze)

        # Der Revolver (Manuel, 2026-09-30, P-2026-09-30-52): Aufnahmen an der Stirn oder am
        # Umfang, Scheiben-Ø, VDI-Größe.
        self.wahl_revolver = QtGui.QComboBox()
        self.wahl_revolver.addItem(tr("neu.revolver.stirn"), beispielmaschine.REVOLVER_STIRN)
        self.wahl_revolver.addItem(tr("neu.revolver.umfang"), beispielmaschine.REVOLVER_UMFANG)
        self.wahl_revolver.setCurrentIndex(self.wahl_revolver.findData(vorgabe.revolver))
        self.wahl_revolver.setToolTip(tr("neu.revolver.tooltip"))
        formular.addRow(tr("neu.revolver"), self.wahl_revolver)
        self.feld_scheibe = QtGui.QDoubleSpinBox()
        self.feld_scheibe.setLocale(zahlenformat())
        self.feld_scheibe.setDecimals(einheiten.stellen(einheiten.LAENGE, 0))
        self.feld_scheibe.setRange(
            *(einheiten.anzeige(w, einheiten.LAENGE) for w in beispielmaschine.SCHEIBE_BEREICH)
        )
        self.feld_scheibe.setSuffix(f" {einheiten.einheit(einheiten.LAENGE)}")
        self.feld_scheibe.setValue(einheiten.anzeige(vorgabe.scheibe, einheiten.LAENGE))
        self.feld_scheibe.setToolTip(tr("neu.scheibe.tooltip"))
        formular.addRow(tr("neu.scheibe"), self.feld_scheibe)
        self.wahl_vdi = QtGui.QComboBox()
        for groesse in beispielmaschine.VDI_GROESSEN:
            self.wahl_vdi.addItem(f"VDI {groesse}", groesse)
        self.wahl_vdi.setCurrentIndex(self.wahl_vdi.findData(vorgabe.vdi))
        self.wahl_vdi.setToolTip(tr("neu.vdi.tooltip"))
        formular.addRow(tr("neu.vdi"), self.wahl_vdi)

        # Höchstdrehzahl der Hauptspindel und – an der Drehmaschine – der angetriebenen
        # Werkzeuge (Manuel, 2026-09-30: „höchstdrehzahl von was ?“).
        self.feld_drehzahl = _drehzahlfeld(vorgabe.drehzahl, tr("neu.drehzahl.tooltip"))
        self.feld_drehzahl_werkzeuge = _drehzahlfeld(
            vorgabe.drehzahl_werkzeuge, tr("neu.drehzahl.werkzeuge.tooltip")
        )
        self.drehzahl_spindel = QtGui.QLabel()
        self.drehzahl_werkzeuge = QtGui.QLabel(tr("neu.drehzahl.werkzeuge"))
        zeile = QtGui.QWidget()
        reihe = QtGui.QHBoxLayout(zeile)
        reihe.setContentsMargins(0, 0, 0, 0)
        for teil in (
            self.drehzahl_spindel,
            self.feld_drehzahl,
            self.drehzahl_werkzeuge,
            self.feld_drehzahl_werkzeuge,
        ):
            reihe.addWidget(teil)
        formular.addRow(tr("neu.drehzahl"), zeile)

        # Die Nummern der Spindeln: je ein S und ein C (Manuel, 2026-10-03: „ein S und ein C für die
        # Hauptspindel … und ein S und ein C für die angetriebenen Werkzeuge“).
        self.feld_hauptspindel = _nummernfeld(
            vorgabe.hauptspindel, tr("neu.spindeln.haupt.tooltip")
        )
        self.feld_werkzeugantrieb = _nummernfeld(
            vorgabe.werkzeugantrieb, tr("neu.spindeln.antrieb.tooltip")
        )
        self.spindeln = QtGui.QWidget()
        reihe = QtGui.QHBoxLayout(self.spindeln)
        reihe.setContentsMargins(0, 0, 0, 0)
        for teil in (
            QtGui.QLabel(tr("neu.spindeln.haupt")),
            self.feld_hauptspindel,
            QtGui.QLabel(tr("neu.spindeln.antrieb")),
            self.feld_werkzeugantrieb,
        ):
            reihe.addWidget(teil)
        reihe.addStretch(1)
        formular.addRow(tr("neu.spindeln"), self.spindeln)

        self._nur_drehmaschine = [
            self.feld_bett,
            self.feld_y_winkel,
            self.wahl_x,
            self.feld_plaetze,
            self.wahl_revolver,
            self.feld_scheibe,
            self.wahl_vdi,
            self.spindeln,
        ]
        # Wer etwas ändert, bekommt den alten roten Satz nicht mehr zu sehen.
        felder = [
            self.feld_bett,
            self.feld_y_winkel,
            self.feld_plaetze,
            self.feld_drehzahl,
            self.feld_drehzahl_werkzeuge,
            self.feld_scheibe,
            self.feld_hauptspindel,
            self.feld_werkzeugantrieb,
        ]
        felder += [f for paar in self.felder_weg.values() for f in paar]
        for feld in felder:
            feld.valueChanged.connect(lambda _wert: self.fehler.hide())
        for wahl in (self.wahl_revolver, self.wahl_vdi, self.wahl_x):
            wahl.currentIndexChanged.connect(lambda _index: self.fehler.hide())
        self.wahl_x.currentIndexChanged.connect(lambda _index: self._x_umgeschaltet())
        return bereich

    def _x_faktor(self):
        """2, wenn X im Durchmesser zählt – nur an der Drehmaschine; sonst 1."""
        drehmaschine = self.gewaehlt() == beispielmaschine.DREHMASCHINE
        return 2.0 if drehmaschine and self.wahl_x.currentData() else 1.0

    def _x_umgeschaltet(self):
        """Durchmesser ↔ Radius: Die X-Wege bleiben dieselben, nur anders gezählt."""
        faktor = self._x_faktor()
        if faktor == self._x_faktor_gezeigt:
            return
        werte = [feld.value() * faktor / self._x_faktor_gezeigt for feld in self.felder_weg["X"]]
        self._x_zeigen(werte, faktor)

    def _x_zeigen(self, werte, faktor):
        """Die X-Wege (von, bis) in den Feldern, gezählt mit `faktor` – „von“ als Zahl hinter
        dem festen Minus."""
        von, bis = self.felder_weg["X"]
        _minus_setzen(von, self._negativ["X"], faktor)
        _minus_setzen(bis, False, faktor)
        von.setValue(abs(werte[0]))
        bis.setValue(werte[1])
        self._x_faktor_gezeigt = faktor
        if faktor != 1.0:
            self._x_beschriftung.setText(tr("neu.weg_durchmesser", achse="X"))
        else:
            self._x_beschriftung.setText(tr("neu.weg", achse="X"))

    # --- Auswahl und Ergebnis -------------------------------------------------------

    def _gewechselt(self, aktuell, _vorher):
        art = aktuell.data(ROLLE) if aktuell is not None else None
        self.beschreibung.setText(beispielmaschine.beschreibung(art) if art else "")
        vorgabe = _vorgabe(art)
        self.masse_bereich.setVisible(vorgabe is not None)
        self.fest.setVisible(vorgabe is None)
        if vorgabe is not None:
            # Jede Bauart zeigt ihre eigenen Beispielwerte.
            self.feld_name.setPlaceholderText(beispielmaschine.titel(art))
            for achse, (von, bis) in self.felder_weg.items():
                weg = getattr(vorgabe, f"weg_{achse.lower()}")
                # Z der Drehmaschine zählt ab der Spindelnase: beide Enden ohne Minus.
                self._negativ[achse] = not (achse == "Z" and art == beispielmaschine.DREHMASCHINE)
                _minus_setzen(von, self._negativ[achse])
                von.setValue(einheiten.anzeige(abs(weg[0]), einheiten.LAENGE))
                bis.setValue(einheiten.anzeige(weg[1], einheiten.LAENGE))
            faktor = self._x_faktor()
            self._x_zeigen(
                [einheiten.anzeige(w * faktor, einheiten.LAENGE) for w in vorgabe.weg_x], faktor
            )
            self.feld_drehzahl.setValue(round(vorgabe.drehzahl))
            drehmaschine = art == beispielmaschine.DREHMASCHINE
            if drehmaschine:
                self.drehzahl_spindel.setText(tr("neu.drehzahl.hauptspindel"))
                self.feld_drehzahl_werkzeuge.setValue(round(vorgabe.drehzahl_werkzeuge))
                self.feld_hauptspindel.setValue(vorgabe.hauptspindel)
                self.feld_werkzeugantrieb.setValue(vorgabe.werkzeugantrieb)
            else:
                self.drehzahl_spindel.setText(tr("neu.drehzahl.spindel"))
            self.drehzahl_werkzeuge.setVisible(drehmaschine)
            self.feld_drehzahl_werkzeuge.setVisible(drehmaschine)
            for feld in self._nur_drehmaschine:
                feld.setVisible(drehmaschine)
                self._formular.labelForField(feld).setVisible(drehmaschine)
            self.wege_drehmaschine.setVisible(drehmaschine)
            # Wovon die Wege der Drehmaschine zählen, je Achse (P-2026-09-30-50).
            tooltips = {
                "X": tr("neu.weg_x.drehmaschine.tooltip"),
                "Y": tr("neu.weg_y.drehmaschine.tooltip"),
                "Z": tr("neu.weg_z.drehmaschine.tooltip"),
            }
            for achse, zeile in self._weg_zeilen.items():
                zeile.setToolTip(tooltips[achse] if drehmaschine else tr("neu.weg.tooltip"))
        self.fehler.hide()
        # Mit den Zeilen der Drehmaschine braucht das Fenster mehr Höhe – es wächst mit, sonst
        # quetschte Qt die Zeilen übereinander (P-2026-09-30-52).
        QtCore.QTimer.singleShot(0, self._groesse_anpassen)

    def _groesse_anpassen(self):
        hinweis = self.sizeHint()
        if hinweis.height() > self.height() or hinweis.width() > self.width():
            self.resize(max(self.width(), hinweis.width()), max(self.height(), hinweis.height()))

    def gewaehlt(self):
        """Die gewählte Bauart, oder None."""
        eintrag = self.liste.currentItem()
        return eintrag.data(ROLLE) if eintrag is not None else None

    def masse(self):
        """Die eingetragenen Maße – DrehmaschinenMasse bei der Drehmaschine, FraesenMasse
        bei der 3-Achs-Fräse, sonst None. Ein Weg, der noch wie vorbelegt dasteht, gilt
        genau – in inch ohne Rundung."""
        art = self.gewaehlt()
        vorgabe = _vorgabe(art)
        if vorgabe is None:
            return None
        wege = {
            achse: tuple(
                _wert(
                    feld,
                    getattr(vorgabe, f"weg_{achse.lower()}")[ende],
                    self._x_faktor_gezeigt if achse == "X" else 1.0,
                    negativ=ende == 0 and self._negativ[achse],
                )
                for ende, feld in enumerate(felder)
            )
            for achse, felder in self.felder_weg.items()
        }
        if art == beispielmaschine.FRAESE_3:
            return beispielmaschine.FraesenMasse(
                name=self.feld_name.text().strip(),
                weg_x=wege["X"],
                weg_y=wege["Y"],
                weg_z=wege["Z"],
                drehzahl=float(self.feld_drehzahl.value()),
            )
        return beispielmaschine.DrehmaschinenMasse(
            name=self.feld_name.text().strip(),
            bettneigung=self.feld_bett.value(),
            y_winkel=self.feld_y_winkel.value(),
            weg_x=wege["X"],
            weg_y=wege["Y"],
            weg_z=wege["Z"],
            plaetze=self.feld_plaetze.value(),
            drehzahl=float(self.feld_drehzahl.value()),
            drehzahl_werkzeuge=float(self.feld_drehzahl_werkzeuge.value()),
            revolver=self.wahl_revolver.currentData(),
            scheibe=_wert(self.feld_scheibe, vorgabe.scheibe),
            vdi=self.wahl_vdi.currentData(),
            x_durchmesser=bool(self.wahl_x.currentData()),
            hauptspindel=self.feld_hauptspindel.value(),
            werkzeugantrieb=self.feld_werkzeugantrieb.value(),
        )

    def accept(self):
        """Baut erst, wenn die Maße passen; sonst sagt die rote Zeile, was nicht passt."""
        masse = self.masse()
        fehler = masse.fehler() if masse is not None else []
        if fehler:
            # Derselbe Satz für mehrere Wege steht nur einmal da.
            saetze = dict.fromkeys(satz for _feld, satz in fehler)
            self.fehler.setText(" ".join(saetze))
            self.fehler.show()
            return
        super().accept()

    def done(self, ergebnis):
        NeueMaschineDialog.offen = None
        super().done(ergebnis)


def _drehzahlfeld(wert, tooltip):
    """Eine Drehzahl in U/min, in Hunderterschritten."""
    feld = QtGui.QSpinBox()
    feld.setRange(1, GROESSTE_DREHZAHL)
    feld.setSingleStep(100)
    feld.setValue(round(wert))
    feld.setSuffix(" " + tr("neu.drehzahl.einheit"))
    feld.setToolTip(tooltip)
    return feld


def _nummernfeld(wert, tooltip):
    """Die Nummer einer Spindel: S und C heißen danach (4 → S4 und C4)."""
    feld = QtGui.QSpinBox()
    feld.setRange(*beispielmaschine.SPINDELNUMMER_BEREICH)
    feld.setValue(int(wert))
    feld.setPrefix("S/C ")
    feld.setToolTip(tooltip)
    return feld


def _winkelfeld(wert, bereich):
    feld = QtGui.QDoubleSpinBox()
    feld.setLocale(zahlenformat())
    feld.setDecimals(1)
    feld.setRange(*bereich)
    feld.setSuffix(" °")
    feld.setValue(wert)
    return feld


def _vorgabe(art):
    """Die Beispielmaße der Bauart – nur Drehmaschine und 3-Achs-Fräse haben welche."""
    if art == beispielmaschine.DREHMASCHINE:
        return beispielmaschine.DrehmaschinenMasse()
    if art == beispielmaschine.FRAESE_3:
        return beispielmaschine.FraesenMasse()
    return None


def _wert(feld, vorgabe, faktor=1.0, negativ=False):
    """Der Weg eines Felds in mm – im Durchmesser (`faktor` 2) zurück in den Radius; steht
    dort noch die Vorgabe, genau sie. `negativ`: Das Feld zeigt die Zahl hinter dem festen
    Minus – der Weg ist ihr Gegenteil."""
    vorzeichen = -1.0 if negativ else 1.0
    gezeigt = einheiten.anzeige(vorgabe * faktor * vorzeichen, einheiten.LAENGE)
    if abs(feld.value() - gezeigt) < 1e-9:
        return vorgabe
    return vorzeichen * einheiten.metrisch(feld.value(), einheiten.LAENGE) / faktor


def _wegfeld(wert, negativ):
    """Ein Ende eines Wegs in mm oder inch, eingetragen als Zahl ab 0. `negativ`: Das Feld
    zählt ins Minus – das Minus steht fest davor (_minus_setzen), man trägt nur die Zahl
    ein (Manuel, 2026-10-01)."""
    feld = QtGui.QDoubleSpinBox()
    feld.setLocale(zahlenformat())
    feld.setDecimals(einheiten.stellen(einheiten.LAENGE, 0))
    feld.setSuffix(f" {einheiten.einheit(einheiten.LAENGE)}")
    _minus_setzen(feld, negativ)
    feld.setValue(einheiten.anzeige(abs(wert), einheiten.LAENGE))
    return feld


def _minus_setzen(feld, negativ, faktor=1.0):
    """Das feste Minus vor dem Feld – oder keins – und der Bereich 0 … GROESSTER_WEG (mit
    `faktor` 2 im Durchmesser)."""
    feld.setPrefix("−" if negativ else "")
    grenze = einheiten.anzeige(beispielmaschine.GROESSTER_WEG * faktor, einheiten.LAENGE)
    feld.setRange(0.0, grenze)
