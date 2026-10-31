# SPDX-License-Identifier: LGPL-2.1-or-later
"""„Bearbeitung in Schritten“ (Beta): derselbe Assistent, in einzelnen Schritten abgefragt.

Manuel, 2026-10-30: „Ich finde, dass das Gewachsene, dieses Bearbeitungsfenster, … zu groß
geworden ist. Ich finde, wir sollten die Einzelschritte besser abfragen, und zwar einzeln abfragen.
Immer mit einem Weiter und immer nur dann weiter, wenn auch wirklich alles ausgewählt ist und alles
klar ist.“ – und: „Vielleicht machst du noch einen Beta-Knopf rein …, dass wir erstmal das Alte
behalten, was jetzt jeder gewohnt ist“.

Die Schritte:
1. Aufspannung – worin gespannt wird (Spannmittel aus der Sammlung, die passenden zuerst) und wie
   tief, dann welche Fläche unten liegt (oder: wie im Modell). Weiter erst, wenn das klar ist.
2. Flächen – was bearbeitet wird. Weiter erst mit mindestens einer Fläche; gehören die gewählten
   zu einer Tasche, von der nur ein Teil gewählt ist (taschen_wahl), erst nach der Antwort:
   „Ganze Tasche nehmen“ oder „Nur diese Flächen – der Rest ist schon frei“.
3. Schruppen, 4. Löcher, 5. Schlichten, 6. Kanten – je Schritt nur seine Strategien
   (SCHRUPPEN_ZUERST) mit ihren Einstellungen darunter. Ein Schritt ohne passende Strategie wird
   übersprungen. „Anlegen“ geht ab dem Schruppen und legt nur an, was in den gesehenen Schritten
   angehakt ist; gerechnet wird trotzdem mit allem (das Schruppen lässt Aufmaß, wenn geschlichtet
   wird).
Danach „Weiter bearbeiten“ (Beta) am Job: dieselben Flächen, die Aufspannung fest, weiter mit dem
Schritt nach dem zuletzt angelegten.

Die Rechnerei ist die des Assistenten „Bearbeitung“ (gui_bearbeitung.BearbeitungPanel); hier
werden nur seine Teile auf die Schritte verteilt.
"""

import html

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import PARAMETER_PFAD, symbol
from . import reichweite as rw
from . import spannmittel as sm
from . import taschen_wahl as tw
from . import vierachs_rohteil as vr
from .gui_bearbeitung import (
    SCHRUPPEN_ZUERST,
    BearbeitungPanel,
    BefehlBearbeitung,
    _grau,
    _klappknopf,
)
from .gui_teile import knopf
from .gui_zahlen import dezimal
from .sprache import tr

BETA_AN = "BetaZeigen"  # Parameter: die Beta-Befehle in Menü und Werkzeugleiste
SCHRUPPEN, LOECHER, SCHLICHTEN, KANTEN = 0, 1, 2, 3
ABSCHNITTE = (SCHRUPPEN, LOECHER, SCHLICHTEN, KANTEN)
ERSTER_ABSCHNITT = 2  # die Seite des Schruppens; davor Aufspannung und Flächen
# Was am Job steht, damit „Weiter bearbeiten“ dort weitermacht.
EIGENSCHAFT_FLAECHEN = "CamAddonBetaFlaechen"
EIGENSCHAFT_ABSCHNITT = "CamAddonBetaAbschnitt"
GRUPPE = "CAM-Addon Beta"
TASCHE_REST = 1.0  # mm über einem Boden: so viel darf stehen, und die Tasche gilt als ausgeräumt


def beta_an():
    return FreeCAD.ParamGet(PARAMETER_PFAD).GetBool(BETA_AN, False)


def beta_setzen(an):
    FreeCAD.ParamGet(PARAMETER_PFAD).SetBool(BETA_AN, bool(an))


def _abschnitt_namen():
    return (
        tr("beta.schritt.schruppen"),
        tr("beta.schritt.loecher"),
        tr("beta.schritt.schlichten"),
        tr("beta.schritt.kanten"),
    )


def abschnitt(block):
    return SCHRUPPEN_ZUERST.get(block.s.kennung, SCHLICHTEN)


def _aus_layout(layout, widget):
    """Nimmt `widget` aus `layout` oder einem seiner inneren Layouts – True, wenn es dort war."""
    if layout is None:
        return False
    for i in range(layout.count()):
        eintrag = layout.itemAt(i)
        if eintrag.widget() is widget:
            layout.takeAt(i)
            return True
        if eintrag.layout() is not None and _aus_layout(eintrag.layout(), widget):
            return True
    return False


def _umsetzen(widget, ziel, alt):
    _aus_layout(alt, widget)
    ziel.addWidget(widget)


class BetaPanel(BearbeitungPanel):
    """Der Assistent „Bearbeitung“ in Schritten (siehe oben). `ab`: der Abschnitt, mit dem
    „Weiter bearbeiten“ beginnt (0 Schruppen … 3 Kanten) – None: von vorn."""

    def __init__(self, dokument, wahl=None, ab=None, **kwargs):
        self._beta_ab = ab
        self._beta_unten_klar = False
        self._beta_tasche_ok = set()  # Flächen-Wahlen, bei denen „Nur diese Flächen“ gilt
        self._beta_fehlende = []
        self._beta_voll = True  # steht in der Tasche noch Material (Plan C1)?
        self._beta_schlichten = None  # (die ganze Tasche, nur diese schlichten) – Plan C1
        self._beta_nachbarn = None  # (Form, taschen_wahl.nachbarn) – gerechnet einmal je Form
        self._beta_bis = None  # beim Anlegen: bis zu welchem Abschnitt
        # Ohne Auswahl gestartet: der erste Klick ins Teil ist die Fläche, die unten liegt (Manuel:
        # „erstmal, wo ist die eingespannte Fläche, abfragen“) – damit entsteht auch der Job.
        self._beta_erster_klick_unten = wahl is None and kwargs.get("operation") is None
        super().__init__(dokument, wahl, **kwargs)
        self._nach_rohteil()
        self._weg["reihenfolge"] = "schruppen"  # die Schritte sind die Reihenfolge
        self._beta_start = 0  # vor diese Seite geht „Zurück“ nicht
        if ab is not None and self.job is not None:
            self._beta_unten_klar = True
            self._beta_tasche_ok.add(frozenset(self.gewaehlte))
            self._beta_start = self._abschnitt_seite(ab, vorwaerts=True)
            self.seite_zeigen(self._beta_start)

    # --- Aufbau ---------------------------------------------------------------------------

    def _baue(self):
        form = super()._baue()
        aufbau = form.layout()
        flaechen, alt_strategien = self.seiten[1], self.seiten[2]
        alt = flaechen.layout()
        # Auf der Seite „Flächen“ bleibt die Wahl; die Fragen und Strategien kommen auf ihre
        # Schritte. Darunter der Satz zur Tasche, mit zwei Knöpfen.
        self.tasche_box = QtGui.QWidget()
        box = QtGui.QVBoxLayout(self.tasche_box)
        box.setContentsMargins(0, 0, 0, 0)
        self.tasche_text = QtGui.QLabel()
        self.tasche_text.setWordWrap(True)
        box.addWidget(self.tasche_text)
        zeile = QtGui.QHBoxLayout()
        self.knopf_ganze_tasche = knopf(
            tr("beta.tasche.ganz"), tr("beta.tasche.ganz.tooltip"), self.ganze_tasche
        )
        self.knopf_nur_diese = knopf(
            tr("beta.tasche.nur_diese"), tr("beta.tasche.nur_diese.tooltip"), self.nur_diese
        )
        self.knopf_tasche_schruppen = knopf(
            tr("beta.tasche.schruppen"),
            tr("beta.tasche.schruppen.tooltip"),
            self.tasche_schruppen_waende_schlichten,
        )
        zeile.addWidget(self.knopf_tasche_schruppen)
        zeile.addWidget(self.knopf_ganze_tasche)
        zeile.addWidget(self.knopf_nur_diese)
        self._tasche_zeile = zeile
        zeile.addStretch()
        box.addLayout(zeile)
        self.tasche_box.hide()
        alt.insertWidget(alt.indexOf(self.flaechen_text) + 1, self.tasche_box)

        self._beta_seiten = {}
        self._beta_leer = {}
        self._beta_werte = {}  # Kennung → (Zeile mit Fräser und Klappknopf, Hülle, Klappknopf)
        position = aufbau.indexOf(alt_strategien)
        for nummer, a in enumerate(ABSCHNITTE):
            seite = QtGui.QWidget()
            seiten_aufbau = QtGui.QVBoxLayout(seite)
            seiten_aufbau.setContentsMargins(0, 0, 0, 0)
            leer = _grau(tr("beta.abschnitt.leer"))
            seiten_aufbau.addWidget(leer)
            self._beta_leer[a] = leer
            aufbau.insertWidget(position + nummer, seite)
            self._beta_seiten[a] = seite
        schruppen = self._beta_seiten[SCHRUPPEN].layout()
        for widget in (self.ziel_text, self.passt_text, self.knopf_passt, self.knopf_schneller):
            _umsetzen(widget, schruppen, alt)
        _umsetzen(self.frage_eintauchen.widget, schruppen, alt)
        # Kommt Gewähltes in einer Ebene dran (schräg, oder von oben an der waagerechten Spindel),
        # sagt es der Schritt – sonst fiele das Schruppen hier still weg (Manuels Teil „tief“ an
        # der G550: der Boden wird in der Ebene „von oben“ geräumt).
        self.ebene_text = QtGui.QLabel()
        self.ebene_text.setWordWrap(True)
        self.ebene_text.hide()
        schruppen.addWidget(self.ebene_text)
        self._beta_geschwenkt = []
        _umsetzen(self.frage_waende.widget, self._beta_seiten[SCHLICHTEN].layout(), alt)
        _aus_layout(alt, self.frage_reihenfolge.widget)
        self.frage_reihenfolge.widget.hide()
        einstellungen = alt_strategien.layout()
        for block in self.bloecke:
            ziel = self._beta_seiten[abschnitt(block)].layout()
            _aus_layout(self._block_aufbau, block.widget)
            ziel.addWidget(block.widget)
            _aus_layout(einstellungen, block.einstellungen)
            # Die Werte eingeklappt hinter „Werte ändern“ – sonst wird die Seite so lang wie der
            # alte Schritt „Einstellungen“ (Manuel: „das ist zu groß geworden“).
            klapp = _klappknopf(tr("beta.werte"), tr("beta.werte.tooltip"))
            klapp.setFont(QtGui.QLabel().font())
            huelle = QtGui.QWidget()
            huelle_aufbau = QtGui.QVBoxLayout(huelle)
            huelle_aufbau.setContentsMargins(16, 0, 0, 0)
            huelle_aufbau.addWidget(block.einstellungen)
            huelle.hide()
            klapp.toggled.connect(lambda offen, k=klapp, w=huelle: self._werte_klappen(k, w, offen))
            # Der Fräser gleich in der Zeile (Manuel: „Wie willst du schruppen? … welches
            # Werkzeug“): dieselbe Liste wie in den Werten (ein Modell), die Wahl hin und her.
            zeile = QtGui.QWidget()
            zeilen_aufbau = QtGui.QHBoxLayout(zeile)
            zeilen_aufbau.setContentsMargins(16, 0, 0, 0)
            zeilen_aufbau.addWidget(QtGui.QLabel(tr("va.fraeser")))
            fraeser = QtGui.QComboBox()
            fraeser.setModel(block.wahl_fraeser.model())
            fraeser.setToolTip(block.wahl_fraeser.toolTip())
            fraeser.setCurrentIndex(block.wahl_fraeser.currentIndex())
            fraeser.activated.connect(lambda i, b=block: b.wahl_fraeser.setCurrentIndex(i))
            block.wahl_fraeser.currentIndexChanged.connect(
                lambda i, f=fraeser: f.setCurrentIndex(i) if f.currentIndex() != i else None
            )
            zeilen_aufbau.addWidget(fraeser, 1)
            zeilen_aufbau.addWidget(klapp)
            ziel.addWidget(zeile)
            ziel.addWidget(huelle)
            self._beta_werte[block.s.kennung] = (zeile, huelle, klapp)
        _aus_layout(self._block_aufbau, self.passt_nicht)
        self.passt_nicht.hide()
        self._reihe = []
        for seite in self._beta_seiten.values():
            seite.layout().addStretch()
        alt_strategien.hide()
        aufbau.removeWidget(alt_strategien)
        self.seiten = [self.seiten[0], flaechen] + [self._beta_seiten[a] for a in ABSCHNITTE]
        self._spannmittel_bauen()
        # „Liegt so, wie modelliert“: macht Schritt 1 ohne Klick auf eine Fläche klar.
        self.knopf_wie_modell = knopf(
            tr("beta.unten.modell"), tr("beta.unten.modell.tooltip"), self.wie_modelliert
        )
        self.knopf_unten_waehlen.parentWidget().layout().addWidget(self.knopf_wie_modell)
        self.knopf_unten_modell.hide()  # „Wie modelliert“ – das macht jetzt „Liegt wie im Modell“
        # Unter dem Schritt grau die ganze Folge, der eigene fett.
        self.schrittleiste = _grau()
        self.schrittleiste.setTextFormat(QtCore.Qt.RichText)
        aufbau.insertWidget(aufbau.indexOf(self.schritt_text) + 1, self.schrittleiste)
        # Über den Knöpfen: warum „Weiter“ noch nicht geht – als nächster Schritt zum Lesen.
        self.warum_text = QtGui.QLabel()
        self.warum_text.setWordWrap(True)
        self.warum_text.setStyleSheet("color: #d08000;")
        zeile = self.knopf_weiter.parentWidget()
        aufbau.insertWidget(aufbau.indexOf(zeile), self.warum_text)
        # Was „Anlegen“ in diesem Schritt anlegt – es legt ja nur bis hier an – und was danach
        # noch angehakt ist (kommt mit „Weiter bearbeiten“).
        self.anlegen_text = _grau()
        self.anlegen_text.setWordWrap(True)
        aufbau.insertWidget(aufbau.indexOf(zeile), self.anlegen_text)
        # Im letzten Schritt: anlegen und dasselbe Teil anders gespannt weiter (Plan C4).
        self.knopf_umspannen = knopf(
            tr("beta.umspannen"), tr("beta.umspannen.tooltip"), self.umspannen
        )
        self.knopf_umspannen.hide()
        aufbau.insertWidget(aufbau.indexOf(zeile), self.knopf_umspannen, 0, QtCore.Qt.AlignRight)
        return form

    def _spannmittel_bauen(self):
        """Oben in Schritt 1: „Worin gespannt?“ und die Spanntiefe – vor der Unterseite (Plan C5;
        Manuel, 2026-10-31: „die aufspannung sollte man … wählen ja am besten vor dem man die unten
        fläche auswählt und wie tief das teil eingespannt ist“)."""
        self._beta_sammlung = None
        self._beta_aufspannung = None  # gewählt, bevor es einen Job gibt
        box = QtGui.QWidget()
        aufbau = QtGui.QVBoxLayout(box)
        aufbau.setContentsMargins(0, 0, 0, 6)
        zeile = QtGui.QHBoxLayout()
        zeile.addWidget(QtGui.QLabel(tr("beta.spannmittel")))
        self.wahl_spannmittel = QtGui.QComboBox()
        self.wahl_spannmittel.setToolTip(tr("beta.spannmittel.tooltip"))
        self.wahl_spannmittel.activated.connect(lambda _i: self._spannmittel_gewaehlt())
        zeile.addWidget(self.wahl_spannmittel, 1)
        self.knopf_spannmittel = knopf(
            tr("beta.spannmittel.fenster"),
            tr("beta.spannmittel.fenster.tooltip"),
            self.spannmittel_fenster,
        )
        zeile.addWidget(self.knopf_spannmittel)
        aufbau.addLayout(zeile)
        self.spannmittel_text = _grau()
        self.spannmittel_text.setWordWrap(True)
        aufbau.addWidget(self.spannmittel_text)
        seite = self.seiten[0].layout()
        _aus_layout(seite, self.spannungfelder)  # die Spanntiefe gleich darunter
        aufbau.addWidget(self.spannungfelder)
        oben = self.knopf_unten_waehlen.parentWidget().parentWidget()
        seite.insertWidget(max(seite.indexOf(oben), 0), box)
        self.spannmittel_box = box
        self._spannmittel_anbieten()

    def _nach_rohteil(self):
        """Job oder Rohteil sind neu: eine vorher gewählte Aufspannung an den Job, die Auswahl
        neu sortiert (was passt, hängt am Rohteil)."""
        if not hasattr(self, "wahl_spannmittel"):
            return
        if (
            self.job is not None
            and self._beta_aufspannung is not None
            and sm.aufspannung(self.job) is None
        ):
            self._aufspannung_setzen(self._beta_aufspannung)  # gewählt, bevor es den Job gab
        else:
            self._spannmittel_anbieten()

    def teil_waehlen(self, teil, flaeche=None):
        ergebnis = super().teil_waehlen(teil, flaeche)
        self._nach_rohteil()
        return ergebnis

    def _rohteil_anwenden(self):
        super()._rohteil_anwenden()
        self._nach_rohteil()

    def _sammlung(self):
        if self._beta_sammlung is None:
            try:
                self._beta_sammlung = sm.Sammlung.laden()
            except sm.BeschaedigteDatei:
                self._beta_sammlung = sm.Sammlung()
        return self._beta_sammlung

    def _rohteil_box(self):
        rohteil = getattr(getattr(self.job, "Stock", None), "Shape", None)
        return rohteil.BoundBox if rohteil is not None and not rohteil.isNull() else None

    def _jetzige_aufspannung(self):
        if self.job is not None:
            return sm.aufspannung(rw.grundjob_von(self.job))
        return getattr(self, "_beta_aufspannung", None)

    def _spannmittel_anbieten(self):
        """Die Auswahl: „keins (wie bisher)“, dann die Spannmittel der Sammlung – die, die das
        Rohteil nehmen, zuerst; bei den anderen steht, warum nicht. Darunter ein Satz."""
        if not hasattr(self, "wahl_spannmittel"):
            return
        box = self._rohteil_box()
        jetzt = self._jetzige_aufspannung()
        eintraege = []
        for s in self._sammlung().sortiert():
            if box is None:
                eintraege.append((1, s, None, ""))
                continue
            drehung, warum = sm.passt(s, box)
            eintraege.append((0 if drehung is not None else 2, s, drehung, " ".join(warum)))
        eintraege.sort(key=lambda e: e[0])
        self.wahl_spannmittel.blockSignals(True)
        self.wahl_spannmittel.clear()
        self.wahl_spannmittel.addItem(tr("beta.spannmittel.keins"), None)
        self._beta_lagen = {}
        for stufe, s, drehung, warum in eintraege:
            if stufe == 0:
                text = tr("beta.spannmittel.passt", name=s.text)
            elif stufe == 2:
                text = tr("beta.spannmittel.passt_nicht", name=s.text)
            else:
                text = s.text
            self.wahl_spannmittel.addItem(text, s.kennung)
            index = self.wahl_spannmittel.count() - 1
            self.wahl_spannmittel.setItemData(index, warum or s.bezeichnung, QtCore.Qt.ToolTipRole)
            self._beta_lagen[s.kennung] = drehung
        if jetzt is not None and self.wahl_spannmittel.findData(jetzt.spannmittel.kennung) < 0:
            self.wahl_spannmittel.addItem(
                tr("sm.auf.im_job", name=jetzt.spannmittel.text), jetzt.spannmittel.kennung
            )
        index = self.wahl_spannmittel.findData(jetzt.spannmittel.kennung) if jetzt else 0
        self.wahl_spannmittel.setCurrentIndex(max(index, 0))
        self.wahl_spannmittel.blockSignals(False)
        self.wahl_spannmittel.setEnabled(not self._aufspannung_fest())
        passend = sum(1 for e in eintraege if e[0] == 0)
        satz = ""
        if not self._sammlung().spannmittel:
            satz = tr("beta.spannmittel.leer")
        elif jetzt is not None:
            satz = sm.beschreibung(jetzt)
            if box is not None and sm.hinweise(jetzt, box):
                satz += " – " + " ".join(sm.hinweise(jetzt, box))
        elif box is not None:
            satz = tr("beta.spannmittel.anzahl", passend=passend, alle=len(eintraege))
        if box is not None and jetzt is None and not passend:
            vorschlaege = sm.aus_dem_katalog(box)
            if vorschlaege:
                satz += " " + tr(
                    "beta.spannmittel.katalog", namen=", ".join(v.text for v in vorschlaege)
                )
        else:
            satz = tr("beta.spannmittel.ohne_rohteil")
        self.spannmittel_text.setText(satz)

    def _spannmittel_gewaehlt(self):
        """Die Wahl wird gleich die Aufspannung am Job (Lage: die, in der es passt, sonst die
        Vorgabe der Art; Spanntiefe: was im Feld steht, sonst die übliche)."""
        kennung = self.wahl_spannmittel.currentData()
        auf = None
        if kennung:
            s = self._sammlung().mit(kennung)
            jetzt = self._jetzige_aufspannung()
            if s is None and jetzt is not None and jetzt.spannmittel.kennung == kennung:
                s = jetzt.spannmittel
            if s is None:
                return
            drehung = self._beta_lagen.get(kennung)
            if drehung is None:
                drehung = sm.lagen(s.art)[0]
            tiefe = self._gespannt() if self.felder_spannung["gespannt"].text().strip() else -1.0
            auf = sm.Aufspannung(sm.Spannmittel.aus_dict(s.als_dict()), drehung=drehung)
            auf.spanntiefe = tiefe
        self._aufspannung_setzen(auf)

    def _aufspannung_setzen(self, auf):
        self._beta_aufspannung = auf
        if self.job is not None and not self._aufspannung_fest():
            grund = rw.grundjob_von(self.job)
            sm.setze(grund, auf)
            if auf is not None and auf.spannmittel.art in sm.MIT_BACKEN:
                self._fuellt = True
                self.felder_spannung["gespannt"].setText(dezimal(f"{auf.tiefe:g}"))
                self._fuellt = False
                self._rohteil_kurz_zeigen()
        self._spannmittel_anbieten()

    def _spannung_geaendert(self):
        """Die Spanntiefe gilt auch für die Aufspannung (Backen und Nullpunkt)."""
        super()._spannung_geaendert()
        if not hasattr(self, "wahl_spannmittel"):
            return  # noch im Aufbau
        auf = self._jetzige_aufspannung()
        if self._fuellt or auf is None or getattr(self, "geschlossen", False):
            return
        auf.spanntiefe = self._gespannt()
        self._aufspannung_setzen(auf)

    def spannmittel_fenster(self):
        """„Spannmittel …“: die Sammlung bearbeiten; danach die Auswahl neu."""
        from . import gui_spannmittel

        job = rw.grundjob_von(self.job) if self.job is not None else None
        dialog = gui_spannmittel.oeffne(job)

        def danach():
            self._beta_sammlung = None
            if job is not None:
                self._beta_aufspannung = sm.aufspannung(job)
            self._spannmittel_anbieten()

        dialog.finished.connect(lambda _e: danach())
        return dialog

    def _werte_klappen(self, klapp, huelle, offen):
        klapp.setArrowType(QtCore.Qt.DownArrow if offen else QtCore.Qt.RightArrow)
        huelle.setVisible(offen)

    # --- Schritte -------------------------------------------------------------------------

    def _abschnitt_seite(self, a, vorwaerts=True):
        """Die Seite des Abschnitts `a` – oder der nächste mit passender Strategie."""
        reihe = ABSCHNITTE[a:] if vorwaerts else tuple(reversed(ABSCHNITTE[: a + 1]))
        for b in reihe:
            if self._abschnitt_hat_etwas(b):
                return ERSTER_ABSCHNITT + b
        return ERSTER_ABSCHNITT + a

    def _abschnitt_hat_etwas(self, a):
        if a == SCHRUPPEN and getattr(self, "_beta_geschwenkt", None):
            return True  # der Satz, dass es in der Ebene drankommt
        return any(b.moeglich and abschnitt(b) == a for b in self.bloecke)

    def _aktueller_abschnitt(self):
        return self._seite - ERSTER_ABSCHNITT if self._seite >= ERSTER_ABSCHNITT else None

    def _vor_anlegen(self):
        return getattr(self, "_seite", 0) < ERSTER_ABSCHNITT

    def _weiter_geht(self):
        """Ob „Weiter“ geht – und wenn nicht, warum (ein Satz)."""
        if self.job is None or self.nur_vierachs():
            return False, ""
        if self._seite == 0:
            if not (self._beta_unten_klar or self._aufspannung_fest()):
                return False, tr("beta.warum.unten")
        elif self._seite == 1:
            if not self.gewaehlte:
                return False, tr("beta.warum.flaechen")
            if self._beta_fehlende and frozenset(self.gewaehlte) not in self._beta_tasche_ok:
                return False, tr("beta.warum.tasche")
        return self._naechste_seite() is not None, ""

    def _naechste_seite(self):
        if self._seite < ERSTER_ABSCHNITT:
            if self._seite == 0:
                return 1
            return self._abschnitt_seite(SCHRUPPEN, vorwaerts=True)
        a = self._seite - ERSTER_ABSCHNITT
        for b in ABSCHNITTE[a + 1 :]:
            if self._abschnitt_hat_etwas(b):
                return ERSTER_ABSCHNITT + b
        return None

    def seite_zeigen(self, nummer):
        if not hasattr(self, "_beta_seiten"):  # noch im Aufbau (BearbeitungPanel.__init__)
            return super().seite_zeigen(min(int(nummer), 2))
        self._seite = max(0, min(int(nummer), len(self.seiten) - 1))
        vorwahl = getattr(self, "_beta_vorwahl", None)
        if self._seite == 1 and vorwahl and self.job is not None and not self.gewaehlte:
            # Umgespannt: die Flächen, die in der Aufspannung davor nicht gingen und jetzt von oben
            # gehen (die Rundungen am Boden einer Tasche „sieht“ der Zugang von oben nicht – nach
            # dem Umspannen hingen sie nach unten).
            self._beta_vorwahl = None
            jetzt = self._von_oben_erreichbar()
            self.gewaehlte = [n for n in vorwahl if n != self._unten and n in jetzt]
            if self.gewaehlte:
                self._flaechen_zeigen()
                self.vorschau_starten()
        for i, seite in enumerate(self.seiten):
            seite.setVisible(i == self._seite)
        namen = [tr("ba.schritt.aufspannung"), tr("beta.schritt.flaechen")]
        namen += list(_abschnitt_namen())
        self.schritt_text.setText(tr("beta.schritt", name=namen[self._seite]))
        self.schrittleiste.setText(self._schrittleiste())
        if self.zu_aendern is None:
            anleitungen = [
                (
                    tr("beta.anleitung.aufspannung")
                    if self.job is not None
                    else tr("beta.anleitung.teil")
                ),
                tr("beta.anleitung.flaechen"),
                tr("beta.anleitung.schruppen"),
                tr("beta.anleitung.loecher"),
                tr("beta.anleitung.schlichten"),
                tr("beta.anleitung.kanten"),
            ]
            self.anleitung.setText(anleitungen[self._seite])
        if self._seite == 0 and self.job is not None and not self._aufspannung_fest():
            # Gleich bereit: der nächste Klick ist die Fläche, die unten liegt.
            if not self._beta_unten_klar:
                self.knopf_unten_waehlen.setChecked(True)
        elif self.knopf_unten_waehlen.isChecked():
            self.knopf_unten_waehlen.setChecked(False)
        self._rohteil_kurz_zeigen()
        self._beta_knoepfe()
        self.nichts_angehakt.hide()

    def _schrittleiste(self):
        """„Aufspannung › **Flächen** › Schruppen …“ – ohne die Schritte, die nichts haben."""
        teile = []
        kurz = [
            tr("ba.schritt.aufspannung"),
            tr("beta.schritt.flaechen"),
        ] + list(_abschnitt_namen())
        for i, name in enumerate(kurz):
            if i == self._seite:
                teile.append(f"<b>{html.escape(name)}</b>")
                continue
            ohne = i >= ERSTER_ABSCHNITT and self.job is not None
            if not ohne or self._abschnitt_hat_etwas(i - ERSTER_ABSCHNITT):
                teile.append(html.escape(name))
        return " › ".join(teile)

    def _beta_knoepfe(self):
        geht, warum = self._weiter_geht()
        self.knopf_zurueck.setVisible(self._seite > 0 and self._seite > self._erste_erlaubte())
        weiter_da = self._seite < ERSTER_ABSCHNITT or self._naechste_seite() is not None
        self.knopf_weiter.setVisible(weiter_da)
        self.knopf_weiter.setEnabled(geht)
        self.knopf_weiter.setToolTip(warum or tr("beta.weiter.tooltip"))
        self.warum_text.setText(warum)
        self.warum_text.setVisible(bool(warum))
        for a, leer in self._beta_leer.items():
            leer.setVisible(not self._abschnitt_hat_etwas(a))
        for block in self.bloecke:
            zeile, huelle, klapp = self._beta_werte[block.s.kennung]
            an = block.moeglich and block.aktiv()
            zeile.setVisible(an)
            huelle.setVisible(an and klapp.isChecked())
        self.knopf_fertig.setVisible(self._seite >= ERSTER_ABSCHNITT)
        self.knopf_umspannen.setVisible(
            self._seite >= ERSTER_ABSCHNITT
            and not weiter_da
            and self.zu_aendern is None
            and self.job is not None
            and not self.nur_vierachs()
        )
        self._knoepfe_beschriften()

    def _knoepfe_beschriften(self):
        super()._knoepfe_beschriften()
        if hasattr(self, "anlegen_text"):
            self._anlegen_zeigen()

    def _anlegen_zeigen(self):
        """„Anlegen legt an: Räumen (T1, 2 min), Kontur (T1, 1 min) – zusammen etwa 3 min.
        Später: 3D-Schlichten.“ – nur ab dem Schruppen."""
        a = self._aktueller_abschnitt()
        if a is None or self.zu_aendern is not None:
            self.anlegen_text.hide()
            return
        von = self._beta_ab or 0
        jetzt, spaeter, zeit = [], [], 0.0
        for block in self._in_anlege_reihe(self.aktive_bloecke()):
            if not block.moeglich:
                continue
            if von <= abschnitt(block) <= a:
                fraeser = block.fraeser()
                nummer = getattr(fraeser, "nummer", None)
                teile = [f"T{nummer}"] if nummer is not None else []
                if block.zeit is not None:
                    teile.append(tr("beta.anlegen.minuten", min=dezimal(f"{block.zeit:.1f}")))
                    zeit += block.zeit
                jetzt.append(
                    f"{block.s.titel()} ({', '.join(teile)})" if teile else block.s.titel()
                )
            elif abschnitt(block) > a:
                spaeter.append(block.s.titel())
        if not jetzt:
            text = tr("beta.anlegen.nichts")
        elif zeit > 0:
            text = tr("beta.anlegen.liste", liste=", ".join(jetzt), min=dezimal(f"{zeit:.1f}"))
        else:
            text = tr("beta.anlegen.liste_ohne_zeit", liste=", ".join(jetzt))
        if spaeter:
            text += " " + tr("beta.anlegen.spaeter", liste=", ".join(spaeter))
        self.anlegen_text.setText(text)
        self.anlegen_text.show()

    def _erste_erlaubte(self):
        """„Weiter bearbeiten“ beginnt hinter dem, was schon angelegt ist: nicht davor zurück."""
        return getattr(self, "_beta_start", 0)

    def weiter(self):
        geht, _warum = self._weiter_geht()
        if not geht:
            return
        naechste = self._naechste_seite()
        if naechste is not None:
            self.seite_zeigen(naechste)

    def zurueck(self):
        if self._seite <= ERSTER_ABSCHNITT:
            self.seite_zeigen(self._seite - 1)
            return
        for b in reversed(ABSCHNITTE[: self._seite - ERSTER_ABSCHNITT]):
            if self._abschnitt_hat_etwas(b):
                self.seite_zeigen(ERSTER_ABSCHNITT + b)
                return
        self.seite_zeigen(1)

    def _bloecke_ordnen(self):
        """Je Schritt seine Blöcke – sichtbar, was zur Wahl passt; was nicht passt, bleibt weg
        (die Beta zeigt nur, was geht). Ein Schritt ohne passende Strategie sagt das."""
        if not hasattr(self, "_beta_seiten"):
            return super()._bloecke_ordnen()
        for block in self.bloecke:
            block.widget.setVisible(block.moeglich)
        self.passt_nicht.hide()
        self.nichts_angehakt.hide()
        if hasattr(self, "_seite"):
            self._beta_knoepfe()

    def haken_geklickt(self, block):
        super().haken_geklickt(block)
        if hasattr(self, "_beta_seiten") and hasattr(self, "_seite"):
            self._beta_knoepfe()

    def _neues_fenster(self, dokument, wahl):
        flaechen = list(self.gewaehlte) or None
        return lambda: BetaPanel(dokument, wahl, neu=True, flaechen=flaechen)

    def _vorwahl_nehmen(self, form, flaeche):
        # „Weiter bearbeiten“: genau die Flächen von vorher – auch Rundungen, die allein keine
        # Strategie nähme (die Tasche wurde als Ganzes gewählt).
        if self._beta_ab is not None and self._vorwahl:
            return [n for n in self._vorwahl if n.startswith("Face")]
        return super()._vorwahl_nehmen(form, flaeche)

    # --- Schritt 1: was unten liegt ---------------------------------------------------------

    def _beginnen(self, wahl, angeklickt=None):
        if not getattr(self, "_beta_erster_klick_unten", False):
            return super()._beginnen(wahl, angeklickt)
        self._beta_erster_klick_unten = False
        teil, flaeche = wahl
        super()._beginnen((teil, None), angeklickt)
        if self.job is None or flaeche is None:
            return
        if self._aufspannung_fest():  # das Teil hat schon einen Job: die Fläche ist zu bearbeiten
            if flaeche not in self.gewaehlte:
                self.flaeche_umschalten(flaeche)
            return
        self.unten_waehlen(flaeche)

    def unten_waehlen(self, flaeche):
        super().unten_waehlen(flaeche)
        self._nach_rohteil()
        if flaeche is not None and self._unten == flaeche:
            self._beta_unten_klar = True
            self.knopf_unten_waehlen.setChecked(False)  # der nächste Klick wählt wieder Flächen
        if hasattr(self, "_beta_seiten"):
            self._beta_knoepfe()

    def wie_modelliert(self):
        if self._unten is not None:
            super().unten_waehlen(None)
        self._beta_unten_klar = True
        self.knopf_unten_waehlen.setChecked(False)
        self._beta_knoepfe()

    # --- Schritt 2: die Flächen und die Tasche ----------------------------------------------

    def _flaechen_zeigen(self):
        super()._flaechen_zeigen()
        if hasattr(self, "_beta_seiten"):
            self._tasche_pruefen()
            self._ebene_zeigen()
            self._beta_knoepfe()

    def _ebene_zeigen(self):
        """Im Schruppen: welche gewählten Flächen in einer Ebene drankommen – dort fragt nach
        „Anlegen“ der Assistent der Ebene nach dem Schruppen."""
        self._beta_geschwenkt = []
        if self.job is not None and self.gewaehlte and not self._ist_stl():
            try:
                self._beta_geschwenkt = list(self._geschwenkt(vr.modell(self.job).Shape))
            except Exception as fehler:
                FreeCAD.Console.PrintLog(f"Beta: Ebenen nicht geprüft: {fehler}\n")
        if not self._beta_geschwenkt:
            self.ebene_text.hide()
            return
        namen = ", ".join(self._beta_geschwenkt[:6])
        if len(self._beta_geschwenkt) > 6:
            namen += " …"
        self.ebene_text.setText(
            tr("beta.ebene.satz", anzahl=len(self._beta_geschwenkt), namen=namen)
        )
        self.ebene_text.show()

    def _tasche_pruefen(self):
        """Gehören die gewählten Flächen zu einer Tasche, von der nur ein Teil gewählt ist: ein Satz
        und die Wege dazu (Plan C1; Manuel, 2026-10-31: „wenn wir vorher keinerlei bearbeitung
        haben .. muss halt erstmal etwas rausgeschruppt werden … wenn vorher schon eine schrupp
        operation stattgefunden hat … vll will er wirklich nur die wände geschlichtet haben ... das
        muss irgendwie unterschieden werden“). Steht in der Tasche noch Material, ist der erste Weg
        „ganze Tasche schruppen, diese Wände schlichten“; ist sie schon ausgeräumt, „nur diese“."""
        self._beta_fehlende = []
        # In einer Ebene der Kette (nach „Anlegen“) sind die Flächen schon im ersten Fenster
        # gewählt – die Wände der Tasche bleiben dort im Grundjob, gefragt wird nicht noch einmal.
        kette = bool(getattr(self, "_folge", None))
        if (
            self._beta_schlichten is not None
            and frozenset(self.gewaehlte) == self._beta_schlichten[0]
        ):
            self._tasche_zeigen_entschieden()
            return
        self._beta_schlichten = None  # die Wahl ist eine andere geworden
        if self.job is None or not self.gewaehlte or self._ist_stl() or kette:
            self.tasche_box.hide()
            return
        try:
            form = vr.modell(self.job).Shape
            kennung = form.hashCode()
            if self._beta_nachbarn is None or self._beta_nachbarn[0] != kennung:
                self._beta_nachbarn = (kennung, tw.nachbarn(form))
            self._beta_fehlende = tw.fehlende(form, self.gewaehlte, self._beta_nachbarn[1])
            if self._beta_fehlende:
                self._beta_voll, wer = self._tasche_voll(form, self.gewaehlte + self._beta_fehlende)
        except Exception as fehler:  # nie das Fenster sperren, weil die Prüfung scheitert
            FreeCAD.Console.PrintLog(f"Beta: Tasche nicht geprüft: {fehler}\n")
            self._beta_fehlende = []
        if not self._beta_fehlende:
            self.tasche_box.hide()
            return
        entschieden = frozenset(self.gewaehlte) in self._beta_tasche_ok
        anzahl = {"gewaehlt": len(self.gewaehlte), "fehlen": len(self._beta_fehlende)}
        if entschieden:
            self.tasche_text.setText(tr("beta.tasche.ok", **anzahl))
        elif self._beta_voll:
            self.tasche_text.setText(tr("beta.tasche.voll", **anzahl))
        else:
            von = tr("beta.tasche.von", wer=", ".join(wer)) if wer else ""
            self.tasche_text.setText(tr("beta.tasche.leer", von=von, **anzahl))
        self.tasche_text.setStyleSheet("" if entschieden else "color: #d08000;")
        self.knopf_nur_diese.setVisible(not entschieden)
        self.knopf_tasche_schruppen.setVisible(not entschieden and self._beta_voll)
        self.knopf_ganze_tasche.setVisible(True)
        # Der naheliegende Weg zuerst: voll – ausräumen; leer – nur diese Wände.
        zeile = self._tasche_zeile
        erster = self.knopf_tasche_schruppen if self._beta_voll else self.knopf_nur_diese
        zeile.removeWidget(erster)
        zeile.insertWidget(0, erster)
        self.tasche_box.show()

    def _tasche_voll(self, form, namen):
        """(Steht in der Tasche noch Material?, wer sie ausgeräumt hat). Ohne Operation im Job ist
        sie voll; sonst fragt es den Materialstand über den Böden der Tasche – mehr als
        TASCHE_REST über einem Boden heißt: noch zu."""
        job = rw.grundjob_von(self.job)
        if not list(getattr(getattr(job, "Operations", None), "Group", []) or []):
            return True, []
        from . import materialstand as mst
        from . import schwenken as sw

        if sw.ist_ebene(self.job):
            return True, []
        stand = mst.fuer(job)
        if stand is None:
            return True, []
        voll, wer = False, []
        for name in namen:
            flaeche = form.getElement(name)
            if flaeche.Surface.__class__.__name__ != "Plane":
                continue
            u0, u1, v0, v1 = flaeche.ParameterRange
            mitte = flaeche.valueAt((u0 + u1) / 2, (v0 + v1) / 2)
            if flaeche.normalAt((u0 + u1) / 2, (v0 + v1) / 2).z < 0.7:
                continue  # nur die Böden
            hoehe = stand.hoehen_an([mitte.x], [mitte.y], naechste=True)[0][0]
            if hoehe > mitte.z + TASCHE_REST:
                voll = True
            maske = stand.maske_um((mitte.x, mitte.y), (mitte.x, mitte.y), 2 * stand.schritt)
            wer += [w for w in stand.wer(maske) if w not in wer]
        return voll, wer

    def tasche_schruppen_waende_schlichten(self):
        """„Ganze Tasche schruppen, diese Wände schlichten“ (B1): das Schruppen bekommt die ganze
        Tasche, Schlichten und Kanten nur die gewählten Flächen (_wahl)."""
        nur = frozenset(self.gewaehlte)
        for name in list(self._beta_fehlende):
            if name not in self.gewaehlte:
                self.flaeche_umschalten(name)
        ganz = frozenset(self.gewaehlte)
        self._beta_schlichten = (ganz, nur)
        self._beta_tasche_ok.add(ganz)
        self._tasche_zeigen_entschieden()
        self._beta_knoepfe()

    def _tasche_zeigen_entschieden(self):
        ganz, nur = self._beta_schlichten
        self.tasche_text.setText(tr("beta.tasche.geteilt", ganz=len(ganz), nur=len(nur)))
        self.tasche_text.setStyleSheet("")
        for k in (self.knopf_tasche_schruppen, self.knopf_ganze_tasche, self.knopf_nur_diese):
            k.setVisible(False)
        self.tasche_box.show()

    def _wahl(self, block):
        """Mit „ganze Tasche schruppen, diese Wände schlichten“: Schlichten und Kanten nur die
        gewählten Flächen (und Kanten)."""
        wahl = super()._wahl(block)
        geteilt = self._beta_schlichten
        if (
            geteilt is not None
            and frozenset(self.gewaehlte) == geteilt[0]
            and abschnitt(block) in (SCHLICHTEN, KANTEN)
        ):
            return [n for n in wahl if n in geteilt[1] or not str(n).startswith("Face")]
        return wahl

    def ganze_tasche(self):
        for name in list(self._beta_fehlende):
            if name not in self.gewaehlte:
                self.flaeche_umschalten(name)

    def nur_diese(self):
        self._beta_tasche_ok.add(frozenset(self.gewaehlte))
        self._tasche_pruefen()
        self._beta_knoepfe()

    # --- Anlegen ----------------------------------------------------------------------------

    def _anlegen(self):
        """Mit „Messstopp davor“ (Weiter bearbeiten): erst der Messstopp, dann die Operationen –
        geht das Anlegen nicht, kommt er wieder heraus."""
        stopp = None
        ops = list(self.job.Operations.Group) if self.job is not None else []
        if getattr(self, "_beta_messstopp", False) and ops:
            from . import messstopp as ms

            davor = next((op for op in reversed(ops) if getattr(op, "ToolController", None)), None)
            tc = getattr(davor, "ToolController", None)
            if tc is not None:
                stopp = ms.lege_an(self.job, tc, tc)
        ergebnis = super()._anlegen()
        if stopp is not None and not ergebnis:
            self.job.Document.removeObject(stopp.Name)
        elif stopp is not None:
            self._beta_messstopp = False  # nur einmal
        return ergebnis

    def _nur_diese_anlegen(self, aktive):
        bis = self._beta_bis
        if bis is None:
            return aktive
        von = self._beta_ab or 0
        return [b for b in aktive if von <= abschnitt(b) <= bis]

    def _kann_anlegen(self):
        """Wie im gewohnten Assistenten – aber nur mit dem, was „Anlegen“ hier anlegt: Ein roter
        Satz an der Flanke (später) sperrt das Schruppen nicht. Kommt hier nur eine Ebene dran,
        legt „Anlegen“ sie an."""
        a = self._aktueller_abschnitt() if hasattr(self, "_beta_seiten") else None
        if a is None or self.zu_aendern is not None:
            return super()._kann_anlegen()
        if self.hinweis.text():
            return False
        von = self._beta_ab or 0
        hier = [b for b in self.aktive_bloecke() if von <= abschnitt(b) <= a]
        if not hier:
            return bool(self._beta_geschwenkt) or self._folge_ohne_operation()
        return all(b.kann_anlegen() for b in hier)

    def accept(self):
        if self._vor_anlegen() and self.zu_aendern is None:
            self._oben_weiter = False
            self.weiter()
            return False
        self._beta_bis = self._aktueller_abschnitt()
        job = self.job
        try:
            ergebnis = super().accept()
        finally:
            bis, self._beta_bis = self._beta_bis, None
        if ergebnis is not False and job is not None and bis is not None:
            self._am_job_merken(job, bis)
        if ergebnis is not False and _UMSPANNEN:
            QtCore.QTimer.singleShot(500, _umspannen_wenn_frei)
        return ergebnis

    def reject(self):
        ergebnis = super().reject()
        if _UMSPANNEN:
            QtCore.QTimer.singleShot(500, _umspannen_wenn_frei)
        return ergebnis

    def umspannen(self):
        """„Anlegen und Teil umspannen …“ (Plan C4; Manuel, 2026-10-31: „das find ich irgendwie
        sinnvoll … sollten wir austesten“): legt an wie „Anlegen“ und öffnet danach – wenn auch
        die Ebenen der Kette fertig sind – dasselbe Teil in einer neuen Aufspannung, vorgewählt die
        Flächen, die in dieser nicht zu erreichen sind."""
        job = rw.grundjob_von(self.job)
        rest = self._nicht_erreichbar()
        _UMSPANNEN.update({"job": job, "flaechen": rest})
        if self.accept() is False:
            _UMSPANNEN.clear()  # nichts angelegt: hier bleiben

    def _von_oben_erreichbar(self):
        """Die Flächen, die in dieser Aufspannung von oben zu erreichen sind (zugang)."""
        from . import zugang as zg

        try:
            form = vr.modell(self.job).Shape
            ergebnis = zg.zugang(form, spannflaeche=self._unten or zg.spannflaeche_unten(form))
        except Exception as fehler:
            FreeCAD.Console.PrintLog(f"Beta: Zugang nicht gerechnet: {fehler}\n")
            return set()
        oben = ergebnis.richtungen[0] if ergebnis.richtungen else None
        if oben is None or oben.achse[2] < 1 - 1e-6:
            return set()
        return set(oben.flaechen)

    def _nicht_erreichbar(self):
        """Die Flächen des Teils, die in dieser Aufspannung nicht zu erreichen sind (zugang) –
        ohne 5-Achs-Maschine alles, was nicht von oben geht."""
        from . import zugang as zg

        try:
            form = vr.modell(self.job).Shape
            ergebnis = zg.zugang(form, spannflaeche=self._unten or zg.spannflaeche_unten(form))
            if not self._fuenfachs():
                ergebnis = zg.ohne_schwenken(ergebnis)
            namen = set(ergebnis.unerreichbar)
            spann = ergebnis.spannflaeche  # die Fläche im Spannmittel – erst umgespannt frei
            if isinstance(spann, str) and spann.startswith("Face"):
                namen.add(spann)
            return sorted(namen, key=lambda n: int(n[4:]) if n[4:].isdigit() else 0)
        except Exception as fehler:  # dann eben ohne Vorwahl
            FreeCAD.Console.PrintLog(f"Beta: Zugang nicht gerechnet: {fehler}\n")
            return []

    def _am_job_merken(self, job, bis):
        try:
            if not hasattr(job, EIGENSCHAFT_FLAECHEN):
                job.addProperty("App::PropertyStringList", EIGENSCHAFT_FLAECHEN, GRUPPE, "")
                job.addProperty("App::PropertyInteger", EIGENSCHAFT_ABSCHNITT, GRUPPE, "")
                for name in (EIGENSCHAFT_FLAECHEN, EIGENSCHAFT_ABSCHNITT):
                    job.setEditorMode(name, 2)
            vorher = list(getattr(job, EIGENSCHAFT_FLAECHEN))
            setattr(job, EIGENSCHAFT_FLAECHEN, sorted(set(vorher) | set(self.gewaehlte)))
            setattr(job, EIGENSCHAFT_ABSCHNITT, max(int(bis), self._beta_ab or 0))
        except Exception as fehler:
            FreeCAD.Console.PrintWarning(f"Beta: am Job nicht gemerkt: {fehler}\n")


class BefehlBearbeitungBeta(BefehlBearbeitung):
    """„Bearbeitung in Schritten (Beta)“ – wie „Bearbeitung“, mit dem Fenster in Schritten."""

    def GetResources(self):
        return {
            "Pixmap": symbol("bearbeitung.svg"),
            "MenuText": tr("befehl.beta.bearbeitung.titel"),
            "ToolTip": tr("befehl.beta.bearbeitung.tooltip"),
        }

    def panel(self, dokument, wahl=None, **kwargs):
        # Alle vorher angeklickten Flächen des Teils kommen mit (der gewohnte Assistent nimmt die
        # erste) – Manuel klickt etwa zwei Wände an und dann den Befehl.
        flaechen = _angeklickte_flaechen(dokument, wahl)
        if len(flaechen) > 1 and "flaechen" not in kwargs:
            kwargs["flaechen"] = flaechen
        return BetaPanel(dokument, wahl, **kwargs)


def _angeklickte_flaechen(dokument, wahl):
    """Alle in `dokument` angeklickten Flächen des Teils aus `wahl` („Face2“, „Face3“ …)."""
    from .gui_vierachs import _entlang

    if not wahl or wahl[0] is None:
        return []
    namen = []
    for auswahl in FreeCADGui.Selection.getSelectionEx(dokument.Name, 0):
        for unterelement in auswahl.SubElementNames or []:
            teil, flaeche = _entlang(dokument, auswahl.Object, unterelement)
            passt = flaeche and teil is not None and vr.original(teil) is wahl[0]
            if passt and flaeche not in namen:
                namen.append(flaeche)
    return namen


def _gewaehlter_job():
    from .gui_vierachs import job_von

    for objekt in FreeCADGui.Selection.getSelection():
        job = job_von(objekt) if not hasattr(objekt, "Operations") else objekt
        if job is not None:
            return job
    return None


def naechster_abschnitt(job):
    """Der Abschnitt nach dem zuletzt angelegten – None, wenn nichts mehr kommt."""
    zuletzt = int(getattr(job, EIGENSCHAFT_ABSCHNITT, -1))
    return zuletzt + 1 if zuletzt + 1 <= KANTEN else None


class BefehlWeiterBearbeiten:
    """„Weiter bearbeiten (Beta)“: am gewählten Job mit dem nächsten Schritt weiter – dieselben
    Flächen, die Aufspannung fest."""

    def GetResources(self):
        return {
            "Pixmap": symbol("bearbeitung.svg"),
            "MenuText": tr("befehl.beta.weiter.titel"),
            "ToolTip": tr("befehl.beta.weiter.tooltip"),
        }

    def IsActive(self):
        if FreeCADGui.Control.activeDialog():
            return False
        job = _gewaehlter_job()
        return job is not None and hasattr(job, EIGENSCHAFT_FLAECHEN)

    def Activated(self):
        job = _gewaehlter_job()
        if job is None or not hasattr(job, EIGENSCHAFT_FLAECHEN):
            QtGui.QMessageBox.information(
                FreeCADGui.getMainWindow(),
                tr("befehl.beta.weiter.titel"),
                tr("beta.weiter.kein_job"),
            )
            return
        frage = WeiterFrage(FreeCADGui.getMainWindow(), job)
        if frage.exec():
            weiter_bearbeiten(job, frage.abschnitt(), frage.messstopp.isChecked())


class WeiterFrage(QtGui.QDialog):
    """„Womit weiter?“ (Plan C3; Manuel, 2026-10-31: „einen knopf "weiter bearbeiten" … wo dann die
    selbe ausgewälte kontor nochmal … entgratet … geschlichtet oder nochmal geschlichtet oder
    vorgeschlcihtet ... 3 mm aufmass beim schruppen … schlichten auf 2mm … nochmal … auf 1 mm … und
    jedes mal dazwischen messschritte“): je Schritt eine Wahl – vorgewählt der nach dem zuletzt
    angelegten, sonst noch einmal Schlichten –, dazu „Messstopp davor“, vorbelegt an."""

    offen = None  # für die Oberflächen-Szenarien

    def __init__(self, eltern, job):
        super().__init__(eltern)
        WeiterFrage.offen = self
        self.setWindowTitle(tr("befehl.beta.weiter.titel"))
        aufbau = QtGui.QVBoxLayout(self)
        text = QtGui.QLabel(tr("beta.weiter.frage"))
        text.setWordWrap(True)
        aufbau.addWidget(text)
        zuletzt = int(getattr(job, EIGENSCHAFT_ABSCHNITT, -1))
        loecher = _hat_loecher(job)
        vorwahl = naechster_abschnitt(job)
        if vorwahl == LOECHER and not loecher:
            vorwahl = SCHLICHTEN
        if vorwahl is None:
            vorwahl = SCHLICHTEN
        self.wahl = {}
        texte = {
            SCHRUPPEN: tr("beta.weiter.schruppen"),
            LOECHER: tr("beta.weiter.loecher"),
            SCHLICHTEN: tr("beta.weiter.schlichten"),
            KANTEN: tr("beta.weiter.kanten"),
        }
        for a in ABSCHNITTE:
            knopf_ = QtGui.QRadioButton(texte[a])
            if a <= zuletzt:
                knopf_.setText(tr("beta.weiter.nochmal", text=texte[a]))
            knopf_.setChecked(a == vorwahl)
            if a == LOECHER and not loecher:
                knopf_.setEnabled(False)
                knopf_.setText(tr("beta.weiter.keine_loecher"))
            aufbau.addWidget(knopf_)
            self.wahl[a] = knopf_
        hinweis = _grau(tr("beta.weiter.aufmass"))
        hinweis.setWordWrap(True)
        aufbau.addWidget(hinweis)
        self.messstopp = QtGui.QCheckBox(tr("beta.weiter.messstopp"))
        self.messstopp.setToolTip(tr("beta.weiter.messstopp.tooltip"))
        self.messstopp.setChecked(bool(list(job.Operations.Group)))
        aufbau.addWidget(self.messstopp)
        knoepfe = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        knoepfe.button(QtGui.QDialogButtonBox.Ok).setText(tr("beta.weiter.los"))
        knoepfe.accepted.connect(self.accept)
        knoepfe.rejected.connect(self.reject)
        aufbau.addWidget(knoepfe)

    def abschnitt(self):
        return next((a for a, k in self.wahl.items() if k.isChecked()), SCHLICHTEN)

    def done(self, ergebnis):
        WeiterFrage.offen = None
        super().done(ergebnis)


def _hat_loecher(job):
    """Ob unter den gemerkten Flächen eine Bohrung ist: ein hohler Zylinder über mindestens einen
    halben Umfang (Rundungen in Ecken sind Viertel)."""
    import math

    try:
        form = vr.modell(job).Shape
        for name in getattr(job, EIGENSCHAFT_FLAECHEN, []):
            flaeche = form.getElement(name)
            if flaeche.Surface.__class__.__name__ != "Cylinder" or tw.gewoelbt(flaeche):
                continue
            u0, u1, _v0, _v1 = flaeche.ParameterRange
            if u1 - u0 >= math.pi - 1e-6:
                return True
    except Exception:  # noqa: BLE001 – im Zweifel anbieten
        return True
    return False


def weiter_bearbeiten(job, ab, messstopp=False):
    """Öffnet die Beta am Job `job` beim Abschnitt `ab` – mit den gemerkten Flächen; `messstopp`:
    vor den neuen Operationen ein Messstopp (messstopp.py)."""
    klon = vr.modell(job)
    teil = vr.original(klon)
    flaechen = list(getattr(job, EIGENSCHAFT_FLAECHEN, []))
    panel = BetaPanel(
        job.Document,
        (teil, flaechen[0] if flaechen else None),
        ab=ab,
        angeklickt=klon,
        flaechen=flaechen,
    )
    panel._beta_messstopp = messstopp
    FreeCADGui.Control.showDialog(panel)
    return panel


class BefehlNeueAufspannung:
    """„Neue Aufspannung (Beta)“: dasselbe Teil anders gespannt – ein neuer Job, die Beta beginnt
    bei der Aufspannung (Manuel, 2026-10-30: „wenn ich eine weitere Operation haben möchte, das
    heißt irgendwie anders eingespannt, muss ich einfach eine neue … einfügen“)."""

    def GetResources(self):
        return {
            "Pixmap": symbol("bearbeitung.svg"),
            "MenuText": tr("befehl.beta.aufspannung.titel"),
            "ToolTip": tr("befehl.beta.aufspannung.tooltip"),
        }

    def IsActive(self):
        return not FreeCADGui.Control.activeDialog() and _gewaehlter_job() is not None

    def Activated(self):
        job = _gewaehlter_job()
        if job is None:
            QtGui.QMessageBox.information(
                FreeCADGui.getMainWindow(),
                tr("befehl.beta.aufspannung.titel"),
                tr("beta.aufspannung.kein_job"),
            )
            return
        neue_aufspannung(job)


def neue_aufspannung(job, vorwahl=None):
    """Öffnet die Beta mit einem neuen Job für das Teil von `job` – bei Schritt 1; `vorwahl`: die
    Flächen, die in Schritt 2 gewählt sind (umspannen)."""
    teil = vr.original(vr.modell(job))
    panel = BetaPanel(job.Document, (teil, None), neu=True)
    panel._beta_vorwahl = list(vorwahl or [])
    FreeCADGui.Control.showDialog(panel)
    return panel


_UMSPANNEN = {}  # „Anlegen und Teil umspannen“: der Job und die Flächen für die neue Aufspannung


def _umspannen_wenn_frei():
    """Ist kein Aufgabenfenster mehr offen (die Ebenen der Kette sind durch), die neue
    Aufspannung; sonst wartet es auf das Schließen des nächsten Beta-Fensters."""
    if not _UMSPANNEN or FreeCADGui.Control.activeDialog():
        return
    job, flaechen = _UMSPANNEN.get("job"), _UMSPANNEN.get("flaechen")
    _UMSPANNEN.clear()
    try:
        if job is None or job.Document.getObject(job.Name) is None:
            return
    except Exception:  # noqa: BLE001 – das Dokument ist zu
        return
    neue_aufspannung(job, flaechen)


BEFEHLE = {
    "CamAddon_BearbeitungBeta": BefehlBearbeitungBeta,
    "CamAddon_WeiterBearbeitenBeta": BefehlWeiterBearbeiten,
    "CamAddon_NeueAufspannungBeta": BefehlNeueAufspannung,
}
WERKZEUGLEISTE_NAME = "CAM-Addon Beta"
WERKZEUGLEISTE = list(BEFEHLE)


def leiste_anhaengen(arbeitsbereich):
    """Hängt die Beta-Leiste und das Menü „Beta“ an, wenn die Beta an ist – nimmt sie weg, wenn
    nicht. True, wenn sich etwas geändert hat."""
    neu = False
    an = beta_an()
    da = WERKZEUGLEISTE_NAME in arbeitsbereich.listToolbars()
    if an and not da:
        arbeitsbereich.appendToolbar(WERKZEUGLEISTE_NAME, WERKZEUGLEISTE)
        arbeitsbereich.appendMenu(["CAM-Addon", tr("beta.menue")], WERKZEUGLEISTE)
        neu = True
    elif not an and da:
        arbeitsbereich.removeToolbar(WERKZEUGLEISTE_NAME)
        arbeitsbereich.removeMenu(tr("beta.menue"))
        neu = True
    return neu
