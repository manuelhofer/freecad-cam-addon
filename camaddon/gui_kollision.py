# SPDX-License-Identifier: LGPL-2.1-or-later
"""Der Bereich „Kollision“ im Fenster „Auf der Maschine prüfen“ (W-001, Stufe 4c).

Warnabstand und der Knopf „Kollision prüfen“: Er fährt die ganze Bahn ab
(kollision.py) – mit Fortschritt, der Knopf heißt solange „Abbrechen“. Danach
das Urteil – grün „Nichts berührt sich …“, rot, wenn etwas anstößt, gelb, wenn
nur etwas näher kommt als der Warnabstand – und je Befund ein Satz, rot oder
gelb. Ein Klick auf einen Satz stellt den Abspieler an die Stelle, eine rote
Kugel zeigt sie in der 3D-Ansicht. Ändert sich Job, Nullpunkt oder
Werkstückaufnahme, ist das Ergebnis veraltet und verschwindet.
"""

import html

import FreeCAD
from PySide import QtCore, QtGui

from . import PARAMETER_PFAD, einheiten, farben
from . import kollision as kb
from . import reichweite as rw
from .gui_hilfe import kopfzeile
from .gui_teile import GRAU, ROT, mit_einheit
from .gui_zahlen import Zahlenpruefer, groesse_lesen, groesse_zeigen
from .sprache import tr

GRUEN = farben.GRUEN
GELB = farben.GELB  # Warnung – lesbar im hellen wie im dunklen Theme (farben.py)
WARNABSTAND = "KollisionWarnabstand"  # gemerkt in den Einstellungen des Addons, mm


def hinweis_label():
    """Grau, zum Markieren – und mit Verweisen „T1 öffnen …“ (hinweise_html)."""
    label = QtGui.QLabel()
    label.setWordWrap(True)
    label.setTextFormat(QtCore.Qt.RichText)
    label.setStyleSheet(f"color: {GRAU.name()};")
    label.setTextInteractionFlags(
        QtCore.Qt.TextSelectableByMouse | QtCore.Qt.LinksAccessibleByMouse
    )
    return label


def hinweise_html(hinweise):
    """Die Hinweise als HTML, je Satz eine Zeile. Geht es um ein Werkzeug (reichweite.Hinweis
    mit Nummer), folgt der Verweis „T1 öffnen …“ – „werkzeug:1“ (D-11)."""
    zeilen = []
    for satz in hinweise:
        zeile = html.escape(satz, quote=False)
        nummer = getattr(satz, "werkzeug", None)
        if nummer is not None:
            text = html.escape(tr("rw.werkzeug_oeffnen", werkzeug=f"T{nummer}"), quote=False)
            zeile += f' <a href="werkzeug:{nummer}">{text}</a>'
        zeilen.append(zeile)
    return "<br>".join(zeilen)


class KollisionsBereich(QtGui.QWidget):
    """`daten()` liefert (Abfahrt, Job, Nullpunkt, Bibliothek) vom Fenster; `hin(befund)`
    stellt den Abspieler an die Stelle eines Befunds; `sperren(ja)` sperrt den Rest des
    Fensters, solange gerechnet wird; `gemeldet(text, farbe, fett)` bekommt das Urteil für
    oben im Fenster, sobald es sich ändert (kurzurteil); `ausspannen(Nummer, Länge, heraus)`
    setzt die Länge ab Spindelnase eines Werkzeugs, dessen Halter anstößt, und gibt den Satz
    dazu zurück (P-2026-10-11-63) – ohne sie bietet der Bereich das nicht an."""

    def __init__(self, daten, hin, sperren, gemeldet=None, ausspannen=None):
        super().__init__()
        self._daten = daten
        self._hin = hin
        self._sperren = sperren
        self._gemeldet = gemeldet or (lambda *_urteil: None)
        self._ausspannen = ausspannen
        self.ergebnis = None
        self.laeuft = False
        self._abbrechen = False
        self.lebt = True  # False, sobald das Fenster zu ist
        self._baue()
        self.veraltet()

    def _baue(self):
        aufbau = QtGui.QVBoxLayout(self)
        aufbau.setContentsMargins(0, 0, 0, 0)
        aufbau.addWidget(kopfzeile(tr("kb.titel"), "reichweite"))
        zeile = QtGui.QHBoxLayout()
        beschriftung = QtGui.QLabel(tr("kb.warnabstand"))
        beschriftung.setToolTip(tr("kb.warnabstand.tooltip"))
        zeile.addWidget(beschriftung)
        self.feld_warnabstand = QtGui.QLineEdit()
        self.feld_warnabstand.setValidator(Zahlenpruefer(self.feld_warnabstand))
        self.feld_warnabstand.setToolTip(tr("kb.warnabstand.tooltip"))
        self.feld_warnabstand.setPlaceholderText(groesse_zeigen(kb.WARNABSTAND, einheiten.LAENGE))
        gemerkt = FreeCAD.ParamGet(PARAMETER_PFAD).GetFloat(WARNABSTAND, 0.0)
        if gemerkt > 0:
            self.feld_warnabstand.setText(groesse_zeigen(gemerkt, einheiten.LAENGE))
        self.feld_warnabstand.setMaximumWidth(80)
        zeile.addWidget(mit_einheit(self.feld_warnabstand, einheiten.einheit(einheiten.LAENGE)))
        zeile.addStretch()
        self.knopf = QtGui.QPushButton(tr("kb.pruefen"))
        self.knopf.setToolTip(tr("kb.pruefen.tooltip"))
        self.knopf.setAutoDefault(False)
        self.knopf.clicked.connect(self.pruefen)
        zeile.addWidget(self.knopf)
        aufbau.addLayout(zeile)
        self.balken = QtGui.QProgressBar()
        self.balken.setRange(0, 1000)
        self.balken.setTextVisible(False)
        self.balken.hide()
        aufbau.addWidget(self.balken)
        self.urteil = QtGui.QLabel()
        self.urteil.setWordWrap(True)
        aufbau.addWidget(self.urteil)
        self.liste = QtGui.QListWidget()
        self.liste.setWordWrap(True)
        self.liste.setSizeAdjustPolicy(QtGui.QAbstractScrollArea.AdjustToContents)
        self.liste.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Maximum)
        self.liste.setToolTip(tr("kb.liste.tooltip"))
        self.liste.itemClicked.connect(lambda _eintrag: self._befund_gewaehlt())
        aufbau.addWidget(self.liste)
        # Stößt ein Halter an: „T1 auf … mm ausspannen“ (der nächste Schritt als Verweis); danach
        # grau, was gesetzt ist – bis zur nächsten Prüfung.
        self.ausspannen_zeile = QtGui.QLabel()
        self.ausspannen_zeile.setWordWrap(True)
        self.ausspannen_zeile.setTextFormat(QtCore.Qt.RichText)
        self.ausspannen_zeile.linkActivated.connect(self._ausspannen_geklickt)
        self.ausspannen_zeile.hide()
        aufbau.addWidget(self.ausspannen_zeile)
        self.notiz = QtGui.QLabel()
        self.notiz.setWordWrap(True)
        self.notiz.setStyleSheet(f"color: {GRAU.name()};")
        self.notiz.hide()
        aufbau.addWidget(self.notiz)
        self.hinweise = hinweis_label()
        aufbau.addWidget(self.hinweise)

    # --- Rechnen ------------------------------------------------------------------------

    def _eingetragen(self):
        """Der eingetragene Warnabstand in mm; 0, wenn das Feld leer oder unlesbar ist („,“)."""
        try:
            return max(groesse_lesen(self.feld_warnabstand.text(), einheiten.LAENGE), 0.0)
        except ValueError:
            return 0.0

    def warnabstand(self):
        """Der Warnabstand in mm: eingetragen, sonst die Vorgabe."""
        return self._eingetragen() or kb.WARNABSTAND

    def pruefen(self):
        """Prüft die Bahn – oder bricht ab, wenn es schon läuft."""
        if self.laeuft:
            self._abbrechen = True
            return
        abfahrt, job, nullpunkt, bibliothek = self._daten()
        if abfahrt is None or not abfahrt.stationen:
            return
        warnabstand = self.warnabstand()
        FreeCAD.ParamGet(PARAMETER_PFAD).SetFloat(WARNABSTAND, self._eingetragen())
        self.laeuft, self._abbrechen = True, False
        self.knopf.setText(tr("kb.abbrechen"))
        self.balken.setValue(0)
        self.balken.show()
        self.liste.hide()
        self.hinweise.hide()
        self.ausspannen_zeile.hide()
        self.notiz.hide()
        self._urteil(tr("kb.laeuft"), GRAU.name())
        self._sperren(True)
        self._melde()
        try:
            ergebnis = kb.kollision_parallel(
                abfahrt, job, nullpunkt, bibliothek, warnabstand, self._fortschritt, rohteil=True
            )
        finally:
            self.laeuft = False
            if self.lebt:
                self._sperren(False)
                self.knopf.setText(tr("kb.pruefen"))
                self.balken.hide()
        if self.lebt:
            self.zeige(ergebnis)

    def _fortschritt(self, anteil):
        if self.lebt:
            self.balken.setValue(round(anteil * 1000))
        QtGui.QApplication.processEvents()
        return not self._abbrechen and self.lebt

    def abbrechen(self):
        """Das Fenster schließt: Eine laufende Prüfung hört auf, nichts wird mehr gezeigt."""
        self._abbrechen = True
        self.lebt = False

    # --- Zeigen -------------------------------------------------------------------------

    def veraltet(self):
        """Job, Nullpunkt oder Aufnahme haben sich geändert – das Ergebnis gilt nicht mehr."""
        if self.laeuft:
            self._abbrechen = True
        self.ergebnis = None
        self.liste.clear()
        self.liste.hide()
        self.hinweise.hide()
        self.ausspannen_zeile.hide()
        self._urteil(tr("kb.noch_nicht"), GRAU.name(), fett=False)
        self._melde()

    def zeige(self, ergebnis):
        self.ergebnis = ergebnis
        self.liste.clear()
        for befund in ergebnis.befunde:
            eintrag = QtGui.QListWidgetItem(befund.text())
            eintrag.setForeground(QtGui.QColor(ROT if befund.beruehrung else GELB))
            self.liste.addItem(eintrag)
        self.liste.setVisible(bool(ergebnis.befunde))
        abstand = rw.weg_text(ergebnis.warnabstand)
        if ergebnis.abgebrochen:
            self._urteil(tr("kb.abgebrochen.urteil"), GRAU.name())
        elif ergebnis.beruehrungen:
            self._urteil(tr("kb.beruehrt"), ROT)
        elif ergebnis.befunde:
            self._urteil(tr("kb.nahe", abstand=abstand), GELB)
        else:
            self._urteil(tr("kb.frei", abstand=abstand), GRUEN)
        self.hinweise.setText(hinweise_html(ergebnis.hinweise))
        self.hinweise.setVisible(bool(ergebnis.hinweise))
        self._ausspannen_zeigen(ergebnis)
        self._melde()

    def _ausspannen_zeigen(self, ergebnis):
        """Je Werkzeug der Werkzeugverwaltung, dessen Halter anstößt (Befund.mindestens): „T1 auf
        … mm ausspannen“ – oder dass es dafür zu kurz ist (reichweite.ausspannen_auf)."""
        from . import job_schnittwerte as js

        verweise = []
        abfahrt, _job, _nullpunkt, bibliothek = self._daten()
        if self._ausspannen is not None and abfahrt is not None and bibliothek is not None:
            je_werkzeug = {}
            for befund in ergebnis.befunde:
                if befund.mindestens <= befund.heraus or befund.halter_am_teil < 0:
                    continue
                tc = abfahrt.operationen[befund.halter_am_teil].tc
                werkzeug = js.werkzeug_von(tc, bibliothek)
                if werkzeug is None:
                    continue
                schluessel = (werkzeug.nummer, getattr(werkzeug, "magazin_nummer", None))
                bisher = je_werkzeug.get(schluessel)
                if bisher is None or befund.mindestens > bisher[2]:
                    je_werkzeug[schluessel] = (werkzeug, befund.heraus, befund.mindestens)
            for werkzeug, heraus, mindestens in je_werkzeug.values():
                kennung = rw.ausspannen_kennung(werkzeug)
                auf = rw.ausspannen_auf(werkzeug, bibliothek, heraus, mindestens)
                if auf is None:
                    gesamt = einheiten.text(float(werkzeug.gesamtlaenge), einheiten.LAENGE, 0)
                    satz = tr("va.halter_zu_kurz", werkzeug=kennung, gesamt=gesamt)
                    verweise.append(html.escape(satz, quote=False))
                    continue
                ziel, laenge = auf
                text = tr(
                    "va.halter_ausspannen",
                    werkzeug=kennung,
                    heraus=einheiten.text(ziel, einheiten.LAENGE, 0),
                )
                ziel_verweis = rw.ausspannen_ziel(werkzeug, laenge, ziel)
                verweise.append(f'<a href="{ziel_verweis}">{html.escape(text)}</a>')
        self.ausspannen_zeile.setText(" · ".join(verweise))
        self.ausspannen_zeile.setVisible(bool(verweise))

    def _ausspannen_geklickt(self, ziel):
        """„ausspannen:1:111.000:41“: T1 so weit ausspannen (das Fenster setzt es und rechnet
        neu); grau darunter, was gesetzt ist."""
        nummer, laenge, heraus, platz = rw.ausspannen_lesen(ziel)
        satz = self._ausspannen(nummer, laenge, int(heraus), platz)
        if satz:
            self.notiz.setText(satz)
            self.notiz.show()

    def _melde(self):
        self._gemeldet(*self.kurzurteil())

    def kurzurteil(self):
        """Das Urteil für oben im Fenster (D-10): (Text, Farbe, fett). Der Text ist HTML und
        hat Verweise: „kollision:pruefen“ prüft, „kollision:wo“ führt zu diesem Bereich –
        mit Doppelpunkt, damit sie nicht wie ein Hilfethema aussehen."""
        if self.laeuft:
            return tr("kb.laeuft"), GRAU.name(), False
        e = self.ergebnis
        pruefen = f'<a href="kollision:pruefen">{tr("kb.kurz.pruefen")}</a>'
        if e is None:
            return f"{tr('kb.kurz.noch_nicht')} – {pruefen}", GRAU.name(), False
        if e.abgebrochen:
            nochmal = f'<a href="kollision:pruefen">{tr("kb.kurz.nochmal")}</a>'
            return f"{tr('kb.abgebrochen.urteil')} {nochmal}", GRAU.name(), False
        wo = f' – <a href="kollision:wo">{tr("kb.kurz.wo")}</a>'
        abstand = rw.weg_text(e.warnabstand)
        if e.beruehrungen:
            return tr("kb.kurz.beruehrt") + wo, ROT, True
        if e.befunde:
            return tr("kb.kurz.nahe", abstand=abstand) + wo, GELB, True
        return tr("kb.frei", abstand=abstand), GRUEN, True

    def _urteil(self, text, farbe, fett=True):
        self.urteil.setText(text)
        gewicht = "font-weight: bold;" if fett else ""
        self.urteil.setStyleSheet(f"color: {farbe}; {gewicht}")

    def _befund_gewaehlt(self):
        zeile = self.liste.currentRow()
        if self.ergebnis is not None and 0 <= zeile < len(self.ergebnis.befunde):
            self._hin(self.ergebnis.befunde[zeile])
