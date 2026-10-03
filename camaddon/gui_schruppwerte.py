# SPDX-License-Identifier: LGPL-2.1-or-later
"""Dialog „Schruppwerte planen“ (W-002, Stufe 3).

Links, wie geschnitten wird (vc, Spandicke, ap, ae-Grenze), rechts, was die
Maschine hergibt – vorbelegt aus der gewählten Zeile und aus dem, was beim
letzten Mal in den Feldern stand. Darunter je ae eine Zeile mit fz, vf, Q und
Leistung, der Vorschlag hervorgehoben und in einem Satz begründet. „Als
Einsatz übernehmen“ legt die gewählte Zeile als „Schruppen dynamisch“ an.
Gerechnet wird in schruppwerte.py.
"""

import FreeCAD
from PySide import QtCore, QtGui

from . import PARAMETER_PFAD, einheiten
from . import reichweite as rw
from . import schnittdaten as sd
from . import schruppwerte as sw
from . import werkzeuge as wz
from .gui_hilfe import kopfzeile
from .gui_teile import GRAU, ROT, hinweiszeile, knopf, mit_einheit
from .gui_zahlen import (
    Zahlenpruefer,
    dezimal,
    groesse_fest,
    groesse_zeigen,
    zahl_lesen,
    zahl_zeigen,
    zahlenformat,
)
from .sprache import tr

# Spalten der Tabelle.
AE, PROZENT, FZ, VF, Q, LEISTUNG, HINWEIS = range(7)
FENSTER_GROESSE = (820, 700)  # Pixel
FELD_BREITE = 90  # Pixel
FARBE_VORSCHLAG = QtGui.QColor("#d5f5dc")  # Hintergrund der vorgeschlagenen Zeile

# Was der Planer sich für die Maschine merkt: Feld → Schlüssel in den
# Einstellungen. Die Warngrenze für ae gehört zum Werkzeug.
GEMERKT = {
    "drehzahl": "PlanerDrehzahl",
    "vorschub": "PlanerVorschub",
    "leistung": "PlanerLeistung",
}


def _parameter():
    return FreeCAD.ParamGet(PARAMETER_PFAD)


def _zahl(wert, stellen):
    return zahlenformat().toString(float(wert), "f", stellen)


def _prozent(wert):
    """% von D: ganze Zahl, wenn es eine ist, sonst eine Nachkommastelle."""
    return _zahl(wert, 0 if abs(wert - round(wert)) < 0.05 else 1)


class SchruppDialog(QtGui.QDialog):
    """Plant Schruppwerte für ein Werkzeug; nach OK steht der neue Einsatz in `einsatz`."""

    offen = None  # für die Oberflächen-Szenarien

    def __init__(
        self, eltern, werkzeug, einsatz, werkstoff, werkstoff_text, uebernehmen_text, vergleich=None
    ):
        """`einsatz`: die gewählte Zeile, aus der vc, Spandicke und ap vorbelegt werden (oder None).

        `werkstoff` (oder None) braucht es für die Leistung, `uebernehmen_text`
        steht auf dem Knopf, der den Einsatz übernimmt; `vergleich` (eine
        Vollnut der Tabelle, oder None) nennt der Satz unter der Tabelle.
        """
        super().__init__(eltern)
        SchruppDialog.offen = self
        self.werkzeug = werkzeug
        self.werkstoff = werkstoff
        self.einsatz = None
        self.plan = None
        self.vergleich = vergleich
        self.setWindowTitle(tr("sp.titel"))
        self.resize(*FENSTER_GROESSE)

        aufbau = QtGui.QVBoxLayout(self)
        aufbau.addWidget(kopfzeile(tr("sp.titel"), "schruppwerte"))
        # Ohne dezimal() für den Werkstoff: 1.0503 ist keine Kommazahl.
        kopf = QtGui.QLabel(
            tr("wv.strategie.kopf", werkzeug=dezimal(wz.zeile(werkzeug)), werkstoff=werkstoff_text)
        )
        kopf.setWordWrap(True)
        aufbau.addWidget(kopf)
        erklaerung = QtGui.QLabel(tr("sp.erklaerung"))
        erklaerung.setWordWrap(True)
        erklaerung.setStyleSheet(f"color: {GRAU.name()};")
        aufbau.addWidget(erklaerung)

        self._groesse = {}  # Feld -> Größe (einheiten.LAENGE …): mm oder inch, m/min oder SFM
        vc, h, ap = sw.vorgaben(werkzeug, einsatz)
        # Hat die Zeile keine, stehen graue Beispiele da – gerechnet wird schon mit ihnen.
        beispiel_vc, beispiel_h = sw.beispiel_schnitt(werkzeug)
        vc_beispiel, h_beispiel = not vc, not h
        vc, h = vc or beispiel_vc, h or beispiel_h
        felder = QtGui.QHBoxLayout()
        schnitt = QtGui.QGroupBox(tr("sp.gruppe.schnitt"))
        formular = QtGui.QFormLayout(schnitt)
        self.feld_vc = self._feld(
            formular, tr("sp.vc"), tr("sp.vc.tooltip"), vc, groesse=einheiten.SCHNITT
        )
        self.feld_spandicke = self._feld(
            formular, tr("sp.spandicke"), tr("sp.spandicke.tooltip"), h, groesse=einheiten.SPAN
        )
        self.feld_ap = self._feld(
            formular, tr("sp.ap"), tr("sp.ap.tooltip"), ap, groesse=einheiten.LAENGE
        )
        self.feld_ae_grenze = self._feld(
            formular,
            tr("sp.ae_grenze"),
            tr("sp.ae_grenze.tooltip"),
            werkzeug.ae_warngrenze,
            einheit=tr("sp.ae_grenze.einheit"),
        )
        felder.addWidget(schnitt, 1)

        maschine = QtGui.QGroupBox(tr("sp.gruppe.maschine"))
        formular = QtGui.QFormLayout(maschine)
        gemerkt = _parameter()
        gefundene = sw.maschinen()
        drehzahl, vorschub, leistung, von_maschine = sw.vorbelegung(
            gemerkt.GetFloat(GEMERKT["drehzahl"], 0.0),
            gemerkt.GetFloat(GEMERKT["vorschub"], 0.0),
            gefundene,
            leistung=gemerkt.GetFloat(GEMERKT["leistung"], 0.0),
            zuletzt=rw.gemerkte_maschine(),
        )
        self.feld_drehzahl = self._feld(
            formular,
            tr("sp.drehzahl"),
            tr("sp.drehzahl.tooltip"),
            drehzahl,
            einheit=tr("einheit.drehzahl"),
        )
        self.feld_vorschub = self._feld(
            formular,
            tr("sp.vorschub"),
            tr("sp.vorschub.tooltip"),
            vorschub,
            groesse=einheiten.VORSCHUB,
        )
        self.feld_leistung = self._feld(
            formular,
            tr("sp.leistung"),
            tr("sp.leistung.tooltip"),
            leistung,
            einheit="kW",
        )
        self.knopf_maschine = QtGui.QPushButton(tr("sp.von_maschine"))
        self.knopf_maschine.setToolTip(tr("sp.von_maschine.tooltip"))
        self.knopf_maschine.setAutoDefault(False)
        self.menue_maschine = QtGui.QMenu(self.knopf_maschine)
        for werte in gefundene:
            aktion = self.menue_maschine.addAction(werte.text)
            aktion.triggered.connect(
                lambda _an=False, w=werte: self.von_maschine(w.drehzahl, w.vorschub, w.leistung)
            )
        self.knopf_maschine.setMenu(self.menue_maschine)
        self.knopf_maschine.setVisible(not self.menue_maschine.isEmpty())
        formular.addRow("", self.knopf_maschine)
        self.vorbelegt = QtGui.QLabel(
            tr("sp.von_maschine.vorbelegt", maschine=von_maschine) if von_maschine else ""
        )
        self.vorbelegt.setWordWrap(True)
        self.vorbelegt.setStyleSheet(f"color: {GRAU.name()};")
        self.vorbelegt.setVisible(bool(von_maschine))
        formular.addRow("", self.vorbelegt)
        felder.addWidget(maschine, 1)
        aufbau.addLayout(felder)

        self.beispiel_hinweis = QtGui.QLabel(
            tr("sp.beispiel", schneidstoff=wz.schneidstoff_text(werkzeug.schneidstoff))
        )
        self.beispiel_hinweis.setWordWrap(True)
        self.beispiel_hinweis.setStyleSheet(f"color: {GRAU.name()};")
        aufbau.addWidget(self.beispiel_hinweis)
        self.beispiele = {
            feld
            for feld, beispiel in ((self.feld_vc, vc_beispiel), (self.feld_spandicke, h_beispiel))
            if beispiel
        }
        for feld in self.beispiele:
            feld.setStyleSheet(f"color: {GRAU.name()};")
            feld.textEdited.connect(lambda _text, f=feld: self._eigener_wert(f))
        self.beispiel_hinweis.setVisible(bool(self.beispiele))

        self.drehzahl_text = QtGui.QLabel()
        self.drehzahl_text.setWordWrap(True)
        aufbau.addWidget(self.drehzahl_text)

        self.tabelle = QtGui.QTableWidget(0, 7)
        self.tabelle.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tabelle.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.tabelle.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.tabelle.verticalHeader().hide()
        koepfe = [
            ("ae\n" + einheiten.einheit(einheiten.LAENGE), tr("wv.spalte.ae.tooltip")),
            (tr("sp.spalte.prozent"), tr("sp.spalte.prozent.tooltip")),
            ("fz\n" + einheiten.einheit(einheiten.SPAN), tr("sp.spalte.fz.tooltip")),
            ("vf\n" + einheiten.einheit(einheiten.VORSCHUB), tr("wv.spalte.vf.tooltip")),
            ("Q\n" + einheiten.einheit(einheiten.ABTRAG), tr("wv.spalte.q.tooltip")),
            ("P\nkW", tr("sp.spalte.leistung.tooltip")),
            (tr("sp.spalte.hinweis"), ""),
        ]
        for spalte, (text, tooltip) in enumerate(koepfe):
            zelle = QtGui.QTableWidgetItem(text)
            zelle.setToolTip(tooltip)
            self.tabelle.setHorizontalHeaderItem(spalte, zelle)
        kopfleiste = self.tabelle.horizontalHeader()
        kopfleiste.setSectionResizeMode(QtGui.QHeaderView.ResizeToContents)
        kopfleiste.setSectionResizeMode(HINWEIS, QtGui.QHeaderView.Stretch)
        self.tabelle.currentCellChanged.connect(lambda *_: self._auswahl_zeigen())
        aufbau.addWidget(self.tabelle, 1)
        # Rot unter der Tabelle, wenn die gewählte Zeile über der Warngrenze liegt.
        self.warnung = hinweiszeile()
        self.warnung.hide()
        aufbau.addWidget(self.warnung)

        self.ergebnis = QtGui.QLabel()
        self.ergebnis.setWordWrap(True)
        self.ergebnis.setTextFormat(QtCore.Qt.RichText)
        self.ergebnis.setFrameShape(QtGui.QFrame.StyledPanel)
        self.ergebnis.setMargin(8)
        aufbau.addWidget(self.ergebnis)

        self.knoepfe = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Cancel)
        self.knopf_uebernehmen = knopf(
            uebernehmen_text, tr("sp.uebernehmen.tooltip"), self.uebernehmen
        )
        self.knoepfe.addButton(self.knopf_uebernehmen, QtGui.QDialogButtonBox.AcceptRole)
        self.knoepfe.rejected.connect(self.reject)
        aufbau.addWidget(self.knoepfe)

        for feld in self._felder():
            feld.textChanged.connect(lambda *_: self.rechnen())
        self.rechnen()

    def _feld(self, formular, text, tooltip, wert, groesse=None, einheit=""):
        """Ein Zahlenfeld; mit `groesse` im gewählten Maßsystem gezeigt und gelesen."""
        if groesse is not None:
            einheit = einheiten.einheit(groesse)
            feld = QtGui.QLineEdit(groesse_zeigen(wert, groesse, metrisch_stellen=4))
            self._groesse[feld] = groesse
        else:
            feld = QtGui.QLineEdit(zahl_zeigen(round(wert, 4)))
        feld.setValidator(Zahlenpruefer(feld))
        feld.setFixedWidth(FELD_BREITE)
        feld.setToolTip(tooltip)
        beschriftung = QtGui.QLabel(text)
        beschriftung.setToolTip(tooltip)
        formular.addRow(beschriftung, mit_einheit(feld, einheit))
        return feld

    def _eigener_wert(self, feld):
        """Eigene Eingabe statt des grauen Beispiels."""
        self.beispiele.discard(feld)
        feld.setStyleSheet("")
        self.beispiel_hinweis.setVisible(bool(self.beispiele))

    def _felder(self):
        return (
            self.feld_vc,
            self.feld_spandicke,
            self.feld_ap,
            self.feld_ae_grenze,
            self.feld_drehzahl,
            self.feld_vorschub,
            self.feld_leistung,
        )

    def keyPressEvent(self, ereignis):
        # Enter in einem Feld soll nicht übernehmen und schließen.
        if ereignis.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            return
        super().keyPressEvent(ereignis)

    # --- Rechnen --------------------------------------------------------------------

    def _lies(self, feld):
        """Der Wert im Feld, metrisch – so rechnet der Planer."""
        try:
            wert = zahl_lesen(feld.text())
        except ValueError:
            return 0.0
        groesse = self._groesse.get(feld)
        return einheiten.metrisch(wert, groesse) if groesse else wert

    @property
    def grenzen(self):
        return sw.Grenzen(
            ae_prozent=self._lies(self.feld_ae_grenze),
            drehzahl=self._lies(self.feld_drehzahl),
            vorschub=self._lies(self.feld_vorschub),
            leistung=self._lies(self.feld_leistung),
        )

    def rechnen(self):
        """Plant mit den Werten in den Feldern neu und zeigt Tabelle und Vorschlag."""
        vc, h, ap = (self._lies(f) for f in (self.feld_vc, self.feld_spandicke, self.feld_ap))
        self.plan = sw.plane(self.werkzeug, vc, h, ap, self.grenzen, self.werkstoff)
        plan = self.plan
        self._drehzahl_zeigen()
        leistung_bekannt = self.werkstoff is not None and self.werkstoff.kc11 > 0
        self.tabelle.setColumnHidden(LEISTUNG, not leistung_bekannt)
        self.tabelle.setRowCount(len(plan.stufen))
        for zeile, stufe in enumerate(plan.stufen):
            self._zeile_schreiben(zeile, stufe, zeile == plan.beste)
        if plan.stufen:
            self.tabelle.setCurrentCell(max(plan.beste, 0), AE)
        self.ergebnis.setText(self._ergebnis_text(vc, h, ap, leistung_bekannt))
        self._auswahl_zeigen()

    def _drehzahl_zeigen(self):
        plan = self.plan
        if plan.n <= 0:
            self.drehzahl_text.clear()
        elif plan.drehzahl_begrenzt:
            self.drehzahl_text.setText(
                tr(
                    "sp.drehzahl_begrenzt",
                    n=_zahl(plan.n, 0),
                    vc=groesse_fest(plan.vc, einheiten.SCHNITT, 0),
                )
            )
        else:
            self.drehzahl_text.setText(tr("sp.drehzahl_ergebnis", n=_zahl(plan.n, 0)))

    def _zeile_schreiben(self, zeile, stufe, vorschlag):
        werte = {
            AE: groesse_fest(stufe.ae, einheiten.LAENGE, 2),
            PROZENT: _prozent(stufe.prozent),
            FZ: groesse_fest(stufe.fz, einheiten.SPAN, 3),
            VF: groesse_fest(stufe.vf, einheiten.VORSCHUB, 0),
            Q: groesse_fest(stufe.q, einheiten.ABTRAG, 1),
            LEISTUNG: _zahl(stufe.leistung, 2) if stufe.leistung else "",
            HINWEIS: self._hinweis(stufe, vorschlag),
        }
        for spalte, text in werte.items():
            zelle = QtGui.QTableWidgetItem(text)
            if spalte != HINWEIS:
                zelle.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            if vorschlag:
                zelle.setBackground(FARBE_VORSCHLAG)
                schrift = zelle.font()
                schrift.setBold(True)
                zelle.setFont(schrift)
            elif stufe.ueber_leistung:
                zelle.setForeground(GRAU)
            elif stufe.ueber_ae:
                # Über der Warngrenze: rot, aber wählbar.
                zelle.setForeground(QtGui.QColor(ROT))
            self.tabelle.setItem(zeile, spalte, zelle)

    def _hinweis(self, stufe, vorschlag):
        teile = []
        if vorschlag:
            teile.append(tr("sp.hinweis.vorschlag"))
        if stufe.an_grenze:
            teile.append(tr("sp.hinweis.grenze_leistung"))
        if stufe.ueber_ae:
            teile.append(tr("sp.hinweis.ueber_ae", grenze=_prozent(self.grenzen.ae_prozent)))
        if stufe.ueber_leistung:
            teile.append(tr("sp.hinweis.ueber_leistung"))
        if stufe.vorschub_begrenzt:
            teile.append(
                tr("sp.hinweis.vorschub", h=groesse_fest(stufe.spandicke, einheiten.SPAN, 3))
            )
        if 0 < stufe.spandicke < sd.MINDEST_SPANDICKE:
            teile.append(tr("sp.hinweis.span_duenn"))
        return " · ".join(teile)

    def _ergebnis_text(self, vc, h, ap, leistung_bekannt):
        """Der Vorschlag in einem Satz, warum nicht breiter – oder was fehlt."""
        plan = self.plan
        if not plan.stufen:
            return tr("sp.fehlt")
        saetze = []
        vorschlag = plan.vorschlag
        if vorschlag is None:
            saetze.append(
                tr(
                    "sp.kein_vorschlag",
                    ae=groesse_fest(plan.stufen[0].ae, einheiten.LAENGE, 2),
                    leistung=_zahl(self.grenzen.leistung, 1),
                )
            )
        else:
            saetze.append(
                tr(
                    "sp.vorschlag",
                    ae=groesse_fest(vorschlag.ae, einheiten.LAENGE, 2),
                    prozent=_prozent(vorschlag.prozent),
                    ap=groesse_zeigen(ap, einheiten.LAENGE),
                    fz=groesse_fest(vorschlag.fz, einheiten.SPAN, 3),
                    vc=groesse_fest(plan.vc, einheiten.SCHNITT, 0),
                    vf=groesse_fest(vorschlag.vf, einheiten.VORSCHUB, 0),
                    q=groesse_fest(vorschlag.q, einheiten.ABTRAG, 1),
                )
            )
            grund = {
                sw.GRUND_AE: lambda: tr("sp.grund.ae", grenze=_prozent(self.grenzen.ae_prozent)),
                sw.GRUND_LEISTUNG: lambda: tr(
                    "sp.grund.leistung", leistung=_zahl(self.grenzen.leistung, 1)
                ),
                sw.GRUND_ENDE: lambda: tr("sp.grund.ende"),
            }[plan.grund]
            saetze.append(grund())
            vergleich = self._vergleich_text(vorschlag, ap)
            if vergleich:
                saetze.append(vergleich)
            if vorschlag.vorschub_begrenzt:
                saetze.append(
                    tr(
                        "sp.vorschub_begrenzt",
                        h=groesse_fest(vorschlag.spandicke, einheiten.SPAN, 3),
                    )
                )
        lc = self.werkzeug.schneidenlaenge
        if lc and ap > lc:
            saetze.append(
                tr(
                    "wv.hinweis.ap_zu_gross",
                    ap=groesse_zeigen(ap, einheiten.LAENGE),
                    laenge=groesse_zeigen(lc, einheiten.LAENGE),
                )
            )
        if self.grenzen.leistung > 0 and not leistung_bekannt:
            saetze.append(tr("sp.leistung_unbekannt"))
        return " ".join(saetze)

    def _vergleich_text(self, vorschlag, ap):
        """„Zum Vergleich: die Vollnut … schafft … – der Vorschlag das 1,3-Fache …“ oder „“."""
        if self.vergleich is None:
            return ""
        _n, _vf, q_vollnut = sd.rechne(self.werkzeug, self.vergleich)
        if q_vollnut <= 0:
            return ""
        return tr(
            "sp.vergleich",
            name=wz.einsatz_name(self.vergleich),
            ae=groesse_zeigen(self.vergleich.ae, einheiten.LAENGE),
            ap_vollnut=groesse_zeigen(self.vergleich.ap, einheiten.LAENGE),
            q_vollnut=groesse_fest(q_vollnut, einheiten.ABTRAG, 1),
            faktor=_zahl(vorschlag.q / q_vollnut, 1),
            ap=groesse_zeigen(ap, einheiten.LAENGE),
        )

    def _auswahl_zeigen(self):
        """Knopf bedienbar, sobald eine Zeile gewählt ist; über der Warngrenze ein roter Satz."""
        zeile = self.tabelle.currentRow()
        gewaehlt = self.plan is not None and 0 <= zeile < len(self.plan.stufen)
        self.knopf_uebernehmen.setEnabled(gewaehlt)
        stufe = self.plan.stufen[zeile] if gewaehlt else None
        if stufe is not None and stufe.ueber_ae:
            self.warnung.setText(
                tr(
                    "sp.warnung.ueber_ae",
                    ae=groesse_fest(stufe.ae, einheiten.LAENGE, 2),
                    prozent=_prozent(stufe.prozent),
                    grenze=_prozent(self.grenzen.ae_prozent),
                )
            )
        self.warnung.setVisible(stufe is not None and stufe.ueber_ae)

    # --- Aktionen -------------------------------------------------------------------

    def von_maschine(self, drehzahl, vorschub, leistung=0.0):
        """Übernimmt Höchstdrehzahl, höchsten Vorschub und Spindelleistung einer Maschine
        (0 = lässt das Feld)."""
        if drehzahl > 0:
            self.feld_drehzahl.setText(zahl_zeigen(drehzahl))
        if vorschub > 0:
            self.feld_vorschub.setText(groesse_zeigen(vorschub, einheiten.VORSCHUB))
        if leistung > 0:
            self.feld_leistung.setText(zahl_zeigen(leistung))

    def setze(self, feld, text):
        """Tippt `text` in ein Feld (Name wie „vc“, „leistung“) – für die Szenarien."""
        getattr(self, "feld_" + feld).setText(text)

    def uebernehmen(self):
        """Die gewählte Zeile als Einsatz; die Warngrenze bekommt das Werkzeug."""
        zeile = self.tabelle.currentRow()
        if self.plan is None or not 0 <= zeile < len(self.plan.stufen):
            return
        self.einsatz = sw.als_einsatz(self.plan, self.plan.stufen[zeile], self._lies(self.feld_ap))
        self._merken()
        self.accept()

    def reject(self):
        self._merken()
        super().reject()

    def _merken(self):
        """Grenzen fürs nächste Mal – auch nach Abbrechen: Die Maschine ändert sich ja nicht.

        Die Warngrenze bekommt das Werkzeug; gespeichert wird sie mit ihm, wenn
        die Werkzeugverwaltung speichert.
        """
        parameter = _parameter()
        grenzen = self.grenzen
        if grenzen.ae_prozent != self.werkzeug.ae_warngrenze:
            self.werkzeug.ae_warngrenze = grenzen.ae_prozent
        werte = {
            "drehzahl": grenzen.drehzahl,
            "vorschub": grenzen.vorschub,
            "leistung": grenzen.leistung,
        }
        for name, wert in werte.items():
            parameter.SetFloat(GEMERKT[name], float(wert))
