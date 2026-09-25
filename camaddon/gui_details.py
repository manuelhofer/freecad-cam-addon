# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Felder der gewählten Betriebsart oder Aufnahme im Dialog „Maschine bearbeiten“.

Der Kasten steht unter der Liste, in der gerade etwas gewählt ist. Jede
Eingabe geht sofort ins Dokument (über `setze`), damit Hinweise und
3D-Ansicht den aktuellen Stand zeigen; OK oder Abbrechen des Dialogs
entscheidet am Ende über alles zusammen.
"""

from PySide import QtCore, QtGui

from . import maschine as m
from .gui_hilfe import zeige_hilfe
from .sprache import tr

# Einheiten neben dem Feld – bei den übrigen Kennwerten steht die Einheit
# schon im Namen. Beschleunigung und Ruck hängen davon ab, ob die Achse fährt
# oder dreht.
EINHEIT_LINEAR = {"Beschleunigung": "m/s²", "Ruck": "m/s³"}
EINHEIT_DREH = {"Beschleunigung": "U/s²", "Ruck": "U/s³"}

GROESSTER_WERT = 1e9  # obere Grenze der Zahlenfelder
NACHKOMMASTELLEN = 6
GROESSTE_PLATZNUMMER = 999


class DetailKasten(QtGui.QFrame):
    """Überschrift und Formular zur gewählten Zeile.

    `setze(objekt, eigenschaft, wert, beschriften=False)` übernimmt eine
    Eingabe ins Dokument; der Dialog frischt danach seine Listen auf.
    """

    def __init__(self, setze):
        super().__init__()
        self._setze = setze
        self.setFrameShape(QtGui.QFrame.StyledPanel)
        self.titel = QtGui.QLabel()
        self.titel.setWordWrap(True)
        self.formular = QtGui.QFormLayout()
        self.formular.setContentsMargins(0, 0, 0, 0)
        aufbau = QtGui.QVBoxLayout(self)
        aufbau.addWidget(self.titel)
        aufbau.addLayout(self.formular)
        self.hide()

    def leeren(self):
        self.titel.setText("")
        while self.formular.rowCount():
            self.formular.removeRow(0)
        self.hide()

    def feld(self, zeile):
        """Das Eingabefeld in Zeile `zeile` des Formulars, oder None."""
        eintrag = self.formular.itemAt(zeile, QtGui.QFormLayout.FieldRole)
        return eintrag.widget() if eintrag is not None else None

    def zeige_betriebsart(self, ba, linear):
        """NC-Name und die Kennwerte, die zur Art gehören; Pflichtwerte fett.

        `linear`: Das Gelenk fährt (sonst dreht es) – davon hängen die
        Einheiten von Beschleunigung und Ruck ab.
        """
        gelenk = ba.Gelenk.Label if ba.Gelenk is not None else "?"
        self.titel.setText(tr("dialog.detail_betriebsart", art=m.art_text(ba.Art), gelenk=gelenk))
        self.formular.addRow(tr("dialog.ncname"), self._ncname_feld(ba))

        einheiten = EINHEIT_LINEAR if linear else EINHEIT_DREH
        for eigenschaft, pflicht in m.WERTE[ba.Art]:
            text = m.wert_text(eigenschaft)
            if eigenschaft in einheiten:
                text += f" ({einheiten[eigenschaft]})"
            if eigenschaft == "Endlos":
                feld = self._schalter(ba, eigenschaft)
            else:
                feld = self._zahlenfeld(ba, eigenschaft, pflicht)
            feld.setToolTip(ba.getDocumentationOfProperty(eigenschaft))
            self.formular.addRow(_beschriftung(text, fett=pflicht), feld)

        if any(eigenschaft == "Beschleunigung" for eigenschaft, _pflicht in m.WERTE[ba.Art]):
            self.formular.addRow(self._verweis_beschleunigung())
        self.show()

    def zeige_aufnahme(self, aufnahme, alle_lcs, spindeln):
        """Bezeichnung und LCS; bei Werkzeugaufnahmen auch Antrieb und Revolverplatz.

        `alle_lcs`: die Koordinatensysteme zur Auswahl; `spindeln`: die
        Betriebsarten „Spindel“, die ein Werkzeug antreiben können.
        """
        if aufnahme.Art == m.AUFNAHME_WERKZEUG:
            titel = tr("dialog.detail_werkzeugaufnahme", name=m.name_von(aufnahme))
        else:
            titel = tr("dialog.detail_werkstueckaufnahme", name=m.name_von(aufnahme))
        self.titel.setText(titel)
        self.formular.addRow(tr("dialog.aufnahme_name"), self._bezeichnungsfeld(aufnahme))
        lcs_liste = [(lcs.Label, lcs) for lcs in alle_lcs]
        self.formular.addRow(
            tr("dialog.aufnahme_lcs"),
            self._verweisliste(aufnahme, "Lcs", lcs_liste, tr("eigenschaft.lcs")),
        )
        if aufnahme.Art == m.AUFNAHME_WERKZEUG:
            antriebe = [(tr("dialog.kein_antrieb"), None)]
            antriebe += [(m.name_von(ba), ba) for ba in spindeln]
            self.formular.addRow(
                tr("dialog.aufnahme_antrieb"),
                self._verweisliste(aufnahme, "Spindel", antriebe, tr("eigenschaft.spindel")),
            )
            self.formular.addRow(tr("dialog.aufnahme_platz"), self._platzfeld(aufnahme))
        self.show()

    # --- die einzelnen Felder -------------------------------------------------

    def _ncname_feld(self, ba):
        feld = QtGui.QLineEdit(ba.NcName)
        feld.setPlaceholderText(tr("dialog.ncname.platzhalter"))
        feld.setToolTip(tr("eigenschaft.ncname"))
        feld.editingFinished.connect(
            lambda: self._setze(ba, "NcName", feld.text().strip(), beschriften=True)
        )
        return feld

    def _zahlenfeld(self, objekt, eigenschaft, pflicht):
        feld = QtGui.QLineEdit(_zahl_zeigen(getattr(objekt, eigenschaft)))
        feld.setValidator(_Zahlenpruefer(feld))
        feld.setPlaceholderText(tr("feld.pflicht") if pflicht else tr("feld.unbekannt"))
        feld.editingFinished.connect(
            lambda: self._setze(objekt, eigenschaft, _zahl_lesen(feld.text()))
        )
        return feld

    def _schalter(self, objekt, eigenschaft):
        feld = QtGui.QCheckBox()
        feld.setChecked(bool(getattr(objekt, eigenschaft)))
        feld.toggled.connect(lambda an: self._setze(objekt, eigenschaft, bool(an)))
        return feld

    def _bezeichnungsfeld(self, aufnahme):
        feld = QtGui.QLineEdit(m.name_von(aufnahme))
        feld.setToolTip(tr("eigenschaft.bezeichnung"))

        def uebernehmen():
            text = feld.text().strip()
            if text:  # ein geleertes Feld behält die bisherige Bezeichnung
                self._setze(aufnahme, "Bezeichnung", text, beschriften=True)

        feld.editingFinished.connect(uebernehmen)
        return feld

    def _verweisliste(self, objekt, eigenschaft, eintraege, tooltip):
        """Auswahlliste für einen Verweis; `eintraege` = [(Text, Objekt oder None), …].

        In der Liste steht der interne Name des Objekts, nicht das Objekt
        selbst – über den Namen findet das Dokument es sicher wieder.
        """
        liste = QtGui.QComboBox()
        for text, ziel in eintraege:
            liste.addItem(text, ziel.Name if ziel is not None else "")
        aktuell = getattr(objekt, eigenschaft)
        liste.setCurrentIndex(max(liste.findData(aktuell.Name if aktuell is not None else ""), 0))
        liste.setToolTip(tooltip)

        def uebernehmen(_index):
            name = liste.currentData()
            self._setze(objekt, eigenschaft, objekt.Document.getObject(name) if name else None)

        liste.currentIndexChanged.connect(uebernehmen)
        return liste

    def _platzfeld(self, aufnahme):
        feld = QtGui.QSpinBox()
        feld.setRange(0, GROESSTE_PLATZNUMMER)
        feld.setSpecialValueText(tr("dialog.kein_platz"))  # steht statt „P0“ da
        feld.setPrefix("P")
        feld.setValue(aufnahme.Platz)
        feld.setToolTip(tr("eigenschaft.platz"))
        feld.valueChanged.connect(lambda wert: self._setze(aufnahme, "Platz", int(wert)))
        return feld

    def _verweis_beschleunigung(self):
        """Verweis auf die Hilfeseite „Beschleunigung ermitteln“ direkt bei den Feldern."""
        verweis = QtGui.QLabel(
            f'<a href="beschleunigung">{tr("dialog.beschleunigung_ermitteln")}</a>'
        )
        verweis.linkActivated.connect(lambda thema: zeige_hilfe(self, thema))
        return verweis


def _beschriftung(text, fett=False):
    beschriftung = QtGui.QLabel(text)
    if fett:
        schrift = beschriftung.font()
        schrift.setBold(True)
        beschriftung.setFont(schrift)
    return beschriftung


# --- Zahlen -------------------------------------------------------------------


def _zahlenformat():
    """Das Zahlenformat der Oberfläche, aber ohne Tausendertrennzeichen.

    Auf einem deutschen System stellt FreeCAD das deutsche Format ein. Mit
    Tausenderpunkten zeigte das Feld „30.000“, und zurückgelesen ergab das 30
    statt 30000 (B-004). Ohne sie ist jede Eingabe eindeutig: Auf Deutsch ist
    das Komma das Dezimalzeichen, einen Punkt lässt das Feld nicht zu.
    """
    zahlenformat = QtCore.QLocale()
    zahlenformat.setNumberOptions(
        QtCore.QLocale.OmitGroupSeparator | QtCore.QLocale.RejectGroupSeparator
    )
    return zahlenformat


class _Zahlenpruefer(QtGui.QDoubleValidator):
    """Lässt nur Zahlen ab 0 im Zahlenformat der Oberfläche zu – und ein leeres Feld.

    Leer heißt „unbekannt“ (0). QDoubleValidator allein hält ein leeres Feld
    für unfertig und meldet es nicht – den Wert zu löschen, bliebe wirkungslos.
    """

    def __init__(self, feld):
        # feld als Qt-Eltern: Der Prüfer lebt so lange wie das Feld.
        super().__init__(0, GROESSTER_WERT, NACHKOMMASTELLEN, feld)
        self.setLocale(_zahlenformat())

    def validate(self, text, position):
        if not text.strip():
            return QtGui.QValidator.Acceptable, text, position
        return super().validate(text, position)


def _zahl_lesen(text):
    """Liest eine Zahl im Zahlenformat der Oberfläche; ein leeres Feld ist 0 (unbekannt)."""
    text = text.strip()
    if not text:
        return 0.0
    wert, gelesen = _zahlenformat().toDouble(text)
    if not gelesen:  # hinter dem _Zahlenpruefer nicht möglich
        raise ValueError(f"keine Zahl: {text!r}")
    return wert


def _zahl_zeigen(wert):
    """Zeigt eine Zahl im Zahlenformat der Oberfläche; 0 (unbekannt) als leeres Feld."""
    if not wert:
        return ""
    return _zahlenformat().toString(float(wert), "g", 12)  # 12 gültige Stellen
