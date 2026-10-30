# SPDX-License-Identifier: LGPL-2.1-or-later
"""„Bearbeitung in Schritten“ (Beta): derselbe Assistent, in einzelnen Schritten abgefragt.

Manuel, 2026-10-30: „Ich finde, dass das Gewachsene, dieses Bearbeitungsfenster, … zu groß
geworden ist. Ich finde, wir sollten die Einzelschritte besser abfragen, und zwar einzeln abfragen.
Immer mit einem Weiter und immer nur dann weiter, wenn auch wirklich alles ausgewählt ist und alles
klar ist.“ – und: „Vielleicht machst du noch einen Beta-Knopf rein …, dass wir erstmal das Alte
behalten, was jetzt jeder gewohnt ist“.

Die Schritte:
1. Aufspannung – welche Fläche liegt unten (oder: wie im Modell). Weiter erst, wenn das klar ist.
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
from .sprache import tr

BETA_AN = "BetaZeigen"  # Parameter: die Beta-Befehle in Menü und Werkzeugleiste
SCHRUPPEN, LOECHER, SCHLICHTEN, KANTEN = 0, 1, 2, 3
ABSCHNITTE = (SCHRUPPEN, LOECHER, SCHLICHTEN, KANTEN)
ERSTER_ABSCHNITT = 2  # die Seite des Schruppens; davor Aufspannung und Flächen
# Was am Job steht, damit „Weiter bearbeiten“ dort weitermacht.
EIGENSCHAFT_FLAECHEN = "CamAddonBetaFlaechen"
EIGENSCHAFT_ABSCHNITT = "CamAddonBetaAbschnitt"
GRUPPE = "CAM-Addon Beta"


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
        self._beta_nachbarn = None  # (Form, taschen_wahl.nachbarn) – gerechnet einmal je Form
        self._beta_bis = None  # beim Anlegen: bis zu welchem Abschnitt
        super().__init__(dokument, wahl, **kwargs)
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
        zeile.addWidget(self.knopf_ganze_tasche)
        zeile.addWidget(self.knopf_nur_diese)
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
        return form

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
        for block in self.bloecke:
            zeile, huelle, klapp = self._beta_werte[block.s.kennung]
            an = block.moeglich and block.aktiv()
            zeile.setVisible(an)
            huelle.setVisible(an and klapp.isChecked())
        self.knopf_fertig.setVisible(self._seite >= ERSTER_ABSCHNITT)
        self._knoepfe_beschriften()

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
        for a, leer in self._beta_leer.items():
            leer.setVisible(not self._abschnitt_hat_etwas(a))
        self.passt_nicht.hide()
        self.nichts_angehakt.hide()
        if hasattr(self, "_seite"):
            self._beta_knoepfe()

    def haken_geklickt(self, block):
        super().haken_geklickt(block)
        if hasattr(self, "_beta_seiten") and hasattr(self, "_seite"):
            self._beta_knoepfe()

    def _vorwahl_nehmen(self, form, flaeche):
        # „Weiter bearbeiten“: genau die Flächen von vorher – auch Rundungen, die allein keine
        # Strategie nähme (die Tasche wurde als Ganzes gewählt).
        if self._beta_ab is not None and self._vorwahl:
            return [n for n in self._vorwahl if n.startswith("Face")]
        return super()._vorwahl_nehmen(form, flaeche)

    # --- Schritt 1: was unten liegt ---------------------------------------------------------

    def unten_waehlen(self, flaeche):
        super().unten_waehlen(flaeche)
        if flaeche is not None and self._unten == flaeche:
            self._beta_unten_klar = True
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
            self._beta_knoepfe()

    def _tasche_pruefen(self):
        """Gehören die gewählten Flächen zu einer Tasche, von der nur ein Teil gewählt ist: der
        Satz mit „Ganze Tasche nehmen“ / „Nur diese Flächen“."""
        self._beta_fehlende = []
        if self.job is None or not self.gewaehlte or self._ist_stl():
            self.tasche_box.hide()
            return
        try:
            form = vr.modell(self.job).Shape
            kennung = form.hashCode()
            if self._beta_nachbarn is None or self._beta_nachbarn[0] != kennung:
                self._beta_nachbarn = (kennung, tw.nachbarn(form))
            self._beta_fehlende = tw.fehlende(form, self.gewaehlte, self._beta_nachbarn[1])
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
        else:
            self.tasche_text.setText(tr("beta.tasche.satz", **anzahl))
        self.tasche_text.setStyleSheet("" if entschieden else "color: #d08000;")
        self.knopf_nur_diese.setVisible(not entschieden)
        self.tasche_box.show()

    def ganze_tasche(self):
        for name in list(self._beta_fehlende):
            if name not in self.gewaehlte:
                self.flaeche_umschalten(name)

    def nur_diese(self):
        self._beta_tasche_ok.add(frozenset(self.gewaehlte))
        self._tasche_pruefen()
        self._beta_knoepfe()

    # --- Anlegen ----------------------------------------------------------------------------

    def _nur_diese_anlegen(self, aktive):
        bis = self._beta_bis
        if bis is None:
            return aktive
        von = self._beta_ab or 0
        return [b for b in aktive if von <= abschnitt(b) <= bis]

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
        return ergebnis

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

    def panel(self, *args, **kwargs):
        return BetaPanel(*args, **kwargs)


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
        ab = naechster_abschnitt(job)
        if ab is None:
            QtGui.QMessageBox.information(
                FreeCADGui.getMainWindow(), tr("befehl.beta.weiter.titel"), tr("beta.weiter.fertig")
            )
            return
        weiter_bearbeiten(job, ab)


def weiter_bearbeiten(job, ab):
    """Öffnet die Beta am Job `job` beim Abschnitt `ab` – mit den gemerkten Flächen."""
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
    FreeCADGui.Control.showDialog(panel)
    return panel


BEFEHLE = {
    "CamAddon_BearbeitungBeta": BefehlBearbeitungBeta,
    "CamAddon_WeiterBearbeitenBeta": BefehlWeiterBearbeiten,
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
