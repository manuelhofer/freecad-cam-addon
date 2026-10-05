# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Felder der gewählten Zeile im Dialog „Maschine bearbeiten“: Betriebsart,
Aufnahme oder schräge Achse.

Der Kasten steht unter der Liste, in der gerade etwas gewählt ist. Jede
Eingabe geht sofort ins Dokument (über `setze`), damit Hinweise und
3D-Ansicht den aktuellen Stand zeigen; OK oder Abbrechen des Dialogs
entscheidet am Ende über alles zusammen.
"""

from PySide import QtGui

from . import einheiten, export, schraege_achse
from . import maschine as m
from .gui_hilfe import zeige_hilfe
from .gui_teile import hinweiszeile, mit_einheit, ruhiges_mausrad
from .gui_winkelbild import WinkelBild
from .gui_zahlen import (
    Zahlenpruefer,
    groesse_fest,
    groesse_lesen,
    groesse_zeigen,
    winkel_zeigen,
    zahl_lesen,
    zahl_zeigen,
)
from .sprache import tr

# Einheiten neben dem Feld – bei den übrigen Kennwerten steht die Einheit
# schon im Namen. Beschleunigung und Ruck hängen davon ab, ob die Achse fährt
# oder dreht.
EINHEIT_LINEAR = {"Beschleunigung": "m/s²", "Ruck": "m/s³"}
EINHEIT_DREH = {"Vdi": "mm", "Beschleunigung": "U/s²", "Ruck": "U/s³"}
# Kennwerte, die in mm/min gespeichert sind – gezeigt in mm/min oder ipm.
VORSCHUEBE = ("Eilgang", "VorschubMax")

GROESSTE_PLATZNUMMER = 999
VORSCHUB = einheiten.VORSCHUB


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

    def zeige_betriebsart(self, ba, linear, lage=None):
        """NC-Name und die Kennwerte, die zur Art gehören; Pflichtwerte fett. Bei Linear
        und Positionieren dazu der Verfahrweg bzw. Schwenkbereich – die Begrenzung am
        Gelenk (Manuel, 2026-09-29: „man müsste schon auch editieren können was die
        maschine kann die verfahrwege“).

        `linear`: Das Gelenk fährt (sonst dreht es) – davon hängen die
        Einheiten von Beschleunigung und Ruck ab. `lage`: gibt die Sätze, wo die
        Achse gerade steht und was das an der Maschine heißt – nach jeder
        geänderten Grenze neu gefragt.
        """
        gelenk = ba.Gelenk.Label if ba.Gelenk is not None else "?"
        self.titel.setText(tr("dialog.detail_betriebsart", art=m.art_text(ba.Art), gelenk=gelenk))
        self.formular.addRow(tr("dialog.ncname"), self._ncname_feld(ba))

        feste_einheiten = EINHEIT_LINEAR if linear else EINHEIT_DREH
        for eigenschaft, pflicht in m.WERTE[ba.Art]:
            text = m.wert_text(eigenschaft)
            if eigenschaft in feste_einheiten:
                text += f" ({feste_einheiten[eigenschaft]})"
            if eigenschaft in ("Endlos", "Gegenlaeufig", "Durchmesser"):
                feld = self._schalter(ba, eigenschaft)
            else:
                feld = self._zahlenfeld(ba, eigenschaft, pflicht, _vorgabe(eigenschaft, linear))
            feld.setToolTip(ba.getDocumentationOfProperty(eigenschaft))
            self.formular.addRow(_beschriftung(text, fett=pflicht), feld)

        if ba.Art in (m.ART_LINEAR, m.ART_POSITIONIEREN) and ba.Gelenk is not None:
            # Im Durchmesser zeigen die Felder das Doppelte – wie die Steuerung (P-2026-09-30-54).
            faktor = 2.0 if linear and getattr(ba, "Durchmesser", False) else 1.0
            self._verfahrweg(ba.Gelenk, linear, lage, faktor)
            if ba.Art == m.ART_LINEAR:
                self._punkte(ba, faktor)
        if any(eigenschaft == "Beschleunigung" for eigenschaft, _pflicht in m.WERTE[ba.Art]):
            self.formular.addRow(self._verweis_beschleunigung())
        self.show()

    def _verfahrweg(self, gelenk, linear, lage, faktor=1.0):
        """Zwei Zeilen „… von“ und „… bis“ für die Begrenzung am Gelenk (mm bzw. °);
        leer: keine Grenze. Darunter grau, was die Zahlen heißen. `faktor` 2: Die Achse zählt
        im Durchmesser – die Felder zeigen das Doppelte, das Gelenk bekommt den Radius."""
        erklaerung = QtGui.QLabel()
        erklaerung.setWordWrap(True)
        erklaerung.setStyleSheet("color: gray;")

        def erklaeren():
            saetze = (
                tr("dialog.verfahrweg.null") if linear else tr("dialog.schwenkbereich.null"),
                lage() if lage is not None else "",
            )
            erklaerung.setText(" ".join(satz for satz in saetze if satz))

        einheit = einheiten.einheit(einheiten.LAENGE)
        if linear and faktor != 1.0:
            titel = {
                "Min": tr("dialog.verfahrweg.min_durchmesser", einheit=einheit),
                "Max": tr("dialog.verfahrweg.max_durchmesser", einheit=einheit),
            }
        elif linear:
            titel = {
                "Min": tr("dialog.verfahrweg.min", einheit=einheit),
                "Max": tr("dialog.verfahrweg.max", einheit=einheit),
            }
        else:
            titel = {"Min": tr("dialog.schwenkbereich.min"), "Max": tr("dialog.schwenkbereich.max")}
        for ende in ("Min", "Max"):
            self.formular.addRow(
                titel[ende], self._grenzfeld(gelenk, ende, linear, erklaeren, faktor)
            )
        erklaeren()
        self.formular.addRow(erklaerung)

    def _grenzfeld(self, gelenk, ende, linear, danach, faktor=1.0):
        """Ein Ende der Begrenzung: „Min“ oder „Max“. Leer schaltet die Grenze aus –
        darum steht eine Grenze bei 0 als „0“ da, nicht leer wie ein unbekannter Wert.
        `danach`: wird nach jeder Änderung gerufen. `faktor` 2: im Durchmesser."""
        schalter, name = ("EnableLength", "Length") if linear else ("EnableAngle", "Angle")
        an = bool(getattr(gelenk, schalter + ende, False))
        wert = getattr(gelenk, name + ende, None)
        text = ""
        if an and wert is not None:
            zahl = float(wert.getValueAs("mm" if linear else "deg"))
            if linear:
                text = groesse_zeigen(zahl * faktor, einheiten.LAENGE, metrisch_stellen=4)
            else:
                text = zahl_zeigen(round(zahl, 4))
            text = text or "0"
        feld = QtGui.QLineEdit(text)
        feld.setValidator(Zahlenpruefer(feld, mit_minus=True))
        feld.setPlaceholderText(tr("dialog.keine_grenze"))
        feld.setToolTip(tr("dialog.grenze.tooltip"))
        ruhiges_mausrad(feld)

        def uebernehmen():
            text = feld.text().strip()
            if not text:
                self._setze(gelenk, schalter + ende, False)
            else:
                try:
                    if linear:
                        neu = groesse_lesen(text, einheiten.LAENGE) / faktor
                    else:
                        neu = zahl_lesen(text)
                except ValueError:  # nur „-“ oder „,“: bleibt wie es war
                    return
                self._setze(gelenk, name + ende, neu)
                self._setze(gelenk, schalter + ende, True)
            danach()

        feld.editingFinished.connect(uebernehmen)
        return feld

    def _punkte(self, ba, faktor=1.0):
        """Home- und Wechselpunkt der Linearachse (Spezifikation Simulation 13; Manuel,
        2026-10-02: „Daher muss es einen Home-Punkt geben … und vielleicht einen
        Werkzeugwechselpunkt … damit auch die Simulation korrekt ablaufen kann“) – gezählt wie
        der Verfahrweg; leer: keiner, der Wechselpunkt leer: wie der Home-Punkt."""
        einheit = einheiten.einheit(einheiten.LAENGE)
        maschine = next((o for o in ba.InList if getattr(o, "Typ", "") == m.TYP_MASCHINE), None)
        wks = maschine is not None and m.wechsel_bezug(maschine) == m.WECHSEL_WKS
        if wks:
            wechsel = tr("dialog.wechsel_wks", einheit=einheit)
            wechsel_leer = tr("dialog.wechsel.leer_wks")
        else:
            wechsel = tr("dialog.wechsel", einheit=einheit)
            wechsel_leer = tr("dialog.wechsel.leer")
        for name, text, leer, tooltip in (
            ("Home", tr("dialog.home", einheit=einheit), tr("dialog.home.leer"),
             tr("dialog.home.tooltip")),
            ("Wechsel", wechsel, wechsel_leer, tr("dialog.wechsel.tooltip")),
        ):  # fmt: skip
            self.formular.addRow(text, self._punktfeld(ba, name, leer, tooltip, faktor))

    def _punktfeld(self, ba, name, leer, tooltip, faktor=1.0):
        """Ein Feld für Home- oder Wechselpunkt: Zahl – oder leer, dann ist „…An“ aus.
        `faktor` 2: im Durchmesser."""
        an = bool(getattr(ba, name + "An", False))
        text = ""
        if an:
            wert = float(getattr(ba, name)) * faktor
            text = groesse_zeigen(wert, einheiten.LAENGE, metrisch_stellen=4) or "0"
        feld = QtGui.QLineEdit(text)
        feld.setValidator(Zahlenpruefer(feld, mit_minus=True))
        feld.setPlaceholderText(leer)
        feld.setToolTip(tooltip)
        ruhiges_mausrad(feld)

        def uebernehmen():
            eingabe = feld.text().strip()
            if not eingabe:
                self._setze(ba, name + "An", False)
                return
            try:
                neu = groesse_lesen(eingabe, einheiten.LAENGE) / faktor
            except ValueError:  # nur „-“ oder „,“: bleibt wie es war
                return
            self._setze(ba, name, neu)
            self._setze(ba, name + "An", True)

        feld.editingFinished.connect(uebernehmen)
        return feld

    def zeige_aufnahme(self, aufnahme, alle_lcs, spindeln, auf_revolver=False):
        """Bezeichnung und LCS; bei Werkzeugaufnahmen auch der Antrieb.

        `alle_lcs`: die Koordinatensysteme zur Auswahl; `spindeln`: die
        Betriebsarten „Spindel“, die ein Werkzeug antreiben können.
        `auf_revolver`: Die Aufnahme sitzt auf einem Revolver – nur dann gibt
        es das Feld „Revolverplatz“ (Manuel: „hier ist noch kein Revolver zu
        sehen, also wieso Revolverplatz?“).
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
            if auf_revolver:
                self.formular.addRow(tr("dialog.aufnahme_platz"), self._platzfeld(aufnahme))
        self.show()

    def zeige_schraege_achse(self, trafo, linearachsen, alpha, winkel_setzen):
        """Schräge und ausgleichende Achse, ihre Namen im Programm, der Winkel aus der
        Baugruppe mit Bild und ein Beispiel (Spezifikation W-001, Abschnitt 7c).

        `linearachsen`: die Betriebsarten, die zur Wahl stehen; `alpha`: der
        Winkel in Grad, None, solange eine Achse fehlt oder nicht passt.
        `winkel_setzen(trafo, grad)` dreht die Führung in der Baugruppe.
        """
        schraeg, ausgleich = (_name(ba) for ba in (trafo.Schraeg, trafo.Ausgleich))
        name = m.name_von(trafo)
        self.titel.setText(
            tr("dialog.detail_schraege_achse", name=name, schraeg=schraeg, ausgleich=ausgleich)
        )
        wahl = [(tr("dialog.keine_achse"), None)] + [(m.name_von(ba), ba) for ba in linearachsen]
        self.formular.addRow(tr("dialog.schraeg"), self._achswahl(trafo, "Schraeg", wahl))
        self.formular.addRow(tr("dialog.ausgleich"), self._achswahl(trafo, "Ausgleich", wahl))
        self.formular.addRow(
            tr("dialog.programmname", achse=schraeg), self._programmname_feld(trafo, "NameSchraeg")
        )
        self.formular.addRow(
            tr("dialog.programmname", achse=ausgleich),
            self._programmname_feld(trafo, "NameAusgleich"),
        )
        if alpha is None:
            self.formular.addRow(tr("dialog.winkel"), QtGui.QLabel(tr("dialog.winkel_unbekannt")))
        else:
            hinweis = hinweiszeile()
            hinweis.hide()
            feld = self._winkelfeld(trafo, alpha, winkel_setzen, hinweis)
            feld.setToolTip(tr("dialog.winkel.tooltip", schraeg=schraeg, ausgleich=ausgleich))
            self.formular.addRow(tr("dialog.winkel"), mit_einheit(feld, "°"))
            self.formular.addRow(hinweis)
        self.formular.addRow(WinkelBild(alpha, schraeg, ausgleich, name))
        if alpha is not None:
            beispiel = QtGui.QLabel(_beispiel(trafo, alpha, schraeg, ausgleich))
            beispiel.setWordWrap(True)
            beispiel.setToolTip(tr("dialog.beispiel_schraeg.tooltip"))
            self.formular.addRow(beispiel)
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

    def _zahlenfeld(self, objekt, eigenschaft, pflicht, vorgabe=None):
        # Eilgang und Vorschub in mm/min oder ipm; gespeichert in mm/min.
        if eigenschaft in VORSCHUEBE:
            feld = QtGui.QLineEdit(groesse_zeigen(getattr(objekt, eigenschaft), VORSCHUB))

            def lesen():
                return groesse_lesen(feld.text(), VORSCHUB)

        else:
            feld = QtGui.QLineEdit(zahl_zeigen(getattr(objekt, eigenschaft)))

            def lesen():
                return zahl_lesen(feld.text())

        feld.setValidator(Zahlenpruefer(feld))
        # Leer gilt die Vorgabe, grau im Feld (D-14).
        if vorgabe is None:
            platzhalter = tr("feld.pflicht") if pflicht else tr("feld.unbekannt")
        elif eigenschaft in VORSCHUEBE:
            platzhalter = tr("feld.vorgabe", wert=groesse_zeigen(vorgabe, VORSCHUB))
        else:
            platzhalter = tr("feld.vorgabe", wert=zahl_zeigen(vorgabe))
        feld.setPlaceholderText(platzhalter)
        feld.editingFinished.connect(lambda: self._setze(objekt, eigenschaft, lesen()))
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
        return ruhiges_mausrad(liste)

    def _achswahl(self, trafo, eigenschaft, wahl):
        """Auswahl der schrägen bzw. ausgleichenden Achse.

        Stand im Namen im Programm noch der Vorschlag zur bisherigen Achse
        (Y1 → Y), wandert er mit: Wer Z1 wählt, bekommt Z.
        """
        name_eigenschaft = "Name" + eigenschaft
        vorher = getattr(trafo, eigenschaft)
        liste = self._verweisliste(trafo, eigenschaft, wahl, _tooltip_achse(eigenschaft))

        def name_mitnehmen(_index):
            neu = getattr(trafo, eigenschaft)
            if getattr(trafo, name_eigenschaft) == m.programmname(vorher) and neu is not None:
                self._setze(trafo, name_eigenschaft, m.programmname(neu), beschriften=True)

        # Nach _verweisliste verbunden: Dann steht die neue Achse schon im Objekt.
        liste.currentIndexChanged.connect(name_mitnehmen)
        return liste

    def _winkelfeld(self, trafo, alpha, winkel_setzen, hinweis):
        """Der Winkel aus der Baugruppe – ein anderer eingetragen dreht die Führung.

        Über ±89° sagt `hinweis`, warum nicht, und das Feld zeigt wieder den
        Winkel der Baugruppe.
        """
        gezeigt = winkel_zeigen(alpha)[:-1]  # ohne „°“ – das steht neben dem Feld
        feld = QtGui.QLineEdit(gezeigt)
        feld.setValidator(Zahlenpruefer(feld, mit_minus=True))

        def uebernehmen():
            if feld.text().strip() in ("", gezeigt):
                feld.setText(gezeigt)  # leer oder unverändert: bleibt, wie gebaut
                return
            try:
                grad = zahl_lesen(feld.text())
            except ValueError:
                grad = None
            if grad is None or abs(grad) > schraege_achse.GROESSTER_WINKEL:
                hinweis.setText(tr("dialog.winkel_zu_gross", name=m.name_von(trafo)))
                hinweis.show()
                feld.setText(gezeigt)
                return
            hinweis.hide()
            winkel_setzen(trafo, grad)

        feld.editingFinished.connect(uebernehmen)
        return feld

    def _programmname_feld(self, trafo, eigenschaft):
        feld = QtGui.QLineEdit(getattr(trafo, eigenschaft))
        feld.setToolTip(trafo.getDocumentationOfProperty(eigenschaft))

        def uebernehmen():
            text = feld.text().strip()
            if text:
                self._setze(trafo, eigenschaft, text, beschriften=True)
            else:  # ein geleertes Feld behält den bisherigen Namen
                feld.setText(getattr(trafo, eigenschaft))

        feld.editingFinished.connect(uebernehmen)
        return feld

    def _platzfeld(self, aufnahme):
        feld = QtGui.QSpinBox()
        feld.setRange(0, GROESSTE_PLATZNUMMER)
        feld.setSpecialValueText(tr("dialog.kein_platz"))  # steht statt „P0“ da
        feld.setPrefix("P")
        feld.setValue(aufnahme.Platz)
        feld.setToolTip(tr("eigenschaft.platz"))
        feld.valueChanged.connect(lambda wert: self._setze(aufnahme, "Platz", int(wert)))
        return ruhiges_mausrad(feld)

    def _verweis_beschleunigung(self):
        """Verweis auf die Hilfeseite „Beschleunigung ermitteln“ direkt bei den Feldern."""
        verweis = QtGui.QLabel(
            f'<a href="beschleunigung">{tr("dialog.beschleunigung_ermitteln")}</a>'
        )
        verweis.linkActivated.connect(lambda thema: zeige_hilfe(self, thema))
        return verweis


def _vorgabe(eigenschaft, linear):
    """Womit das Addon rechnet, solange das Feld leer ist (export.VORGABE_*, wie bei der
    Übergabe an CAM und im Prüffenster) – grau im Feld (D-14, Manuel 2026-10-03: „graue
    Standardwerte kann man hinterlegen, ja“); None, wenn es keine gibt."""
    if eigenschaft == "Eilgang":
        return export.VORGABE_EILGANG
    if eigenschaft == "Geschwindigkeit":
        return export.VORGABE_DREHGESCHWINDIGKEIT
    if eigenschaft == "Beschleunigung":
        return export.VORGABE_BESCHLEUNIGUNG if linear else export.VORGABE_DREHBESCHLEUNIGUNG
    return None


def _name(ba):
    """NC-Name einer Betriebsart – „?“, solange keine gewählt ist."""
    return m.name_von(ba) if ba is not None else "?"


def _tooltip_achse(eigenschaft):
    return tr("eigenschaft.schraeg") if eigenschaft == "Schraeg" else tr("eigenschaft.ausgleich")


def _beispiel(trafo, alpha, schraeg, ausgleich):
    """„Beispiel: Y +10,0 mm → Y1 +11,5 mm, X1 −5,8 mm“ – in inch mit 1 in."""
    schritt = einheiten.metrisch(1.0 if einheiten.in_zoll() else 10.0, einheiten.LAENGE)
    x1, y1 = schraege_achse.schlitten_aus_programm(alpha, 0.0, schritt)
    return tr(
        "dialog.beispiel_schraeg",
        name=m.name_von(trafo),
        weg=_weg(schritt),
        schraeg=schraeg,
        weg_schraeg=_weg(y1),
        ausgleich=ausgleich,
        weg_ausgleich=_weg(x1),
    )


def _weg(wert):
    """Ein Weg mit Vorzeichen und Einheit: „+11,5 mm“, „−5,8 mm“, „0,0 mm“."""
    stellen = einheiten.stellen(einheiten.LAENGE, 1)
    gezeigt = round(einheiten.anzeige(wert, einheiten.LAENGE), stellen)
    zeichen = "+" if gezeigt > 0 else "−" if gezeigt < 0 else ""
    zahl = groesse_fest(abs(wert), einheiten.LAENGE, 1)
    return f"{zeichen}{zahl} {einheiten.einheit(einheiten.LAENGE)}"


def _beschriftung(text, fett=False):
    beschriftung = QtGui.QLabel(text)
    if fett:
        schrift = beschriftung.font()
        schrift.setBold(True)
        beschriftung.setFont(schrift)
    return beschriftung
