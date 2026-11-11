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

from . import PARAMETER_PFAD, einheiten, symbol
from . import reichweite as rw
from . import spannmittel as sm
from . import taschen_wahl as tw
from . import vierachs_rohteil as vr
from . import werkzeugwahl as ww
from .gui_bearbeitung import (
    SCHRUPPEN_ZUERST,
    BearbeitungPanel,
    BefehlBearbeitung,
    _grau,
    _klappknopf,
)
from .gui_teile import knopf
from .gui_zahlen import Zahlenpruefer, dezimal, groesse_lesen, groesse_zeigen
from .sprache import tr

_KURZER_WEG = {
    "an": False
}  # „Alles vorschlagen“ geklickt: die Ebenen der Kette zeigen die Übersicht
WARUM_FARBE = "color: #d08000;"  # der Satz, warum „Weiter“ noch nicht geht
BETONT_MS = 1800  # so lange bleibt der Rahmen um das, was fehlt (_warum_betonen)
BETA_AN = "BetaZeigen"  # Parameter: die Beta-Befehle in Menü und Werkzeugleiste
SCHRUPPEN, LOECHER, SCHLICHTEN, KANTEN = 0, 1, 2, 3
ABSCHNITTE = (SCHRUPPEN, LOECHER, SCHLICHTEN, KANTEN)
ERSTER_ABSCHNITT = 2  # die Seite des Schruppens; davor Aufspannung und Flächen
UEBERSICHT = ERSTER_ABSCHNITT + len(ABSCHNITTE)  # die Seite nach den Schritten (alles_vorschlagen)
# Was am Job steht, damit „Weiter bearbeiten“ dort weitermacht.
EIGENSCHAFT_FLAECHEN = "CamAddonBetaFlaechen"
EIGENSCHAFT_ABSCHNITT = "CamAddonBetaAbschnitt"
GRUPPE = "CAM-Addon Beta"
AUFMASS_STUFE = 1.0  # mm: so viel weniger Aufmaß schlägt „Weiter bearbeiten“ je Gang vor
TASCHE_REST = 1.0  # mm über einem Boden: so viel darf stehen, und die Tasche gilt als ausgeräumt
FERTIG_ZEIGEN = "BetaFertigZeigen"  # Parameter: nach „Anlegen“ das Fenster „Angelegt“ (an)
FERTIG_ZEILEN = 14  # so viele Operationen zeigt es ohne Blättern
KATALOG_NACHSEHEN_MS = 150  # „Was gäbe es im Katalog?“: so oft sehen, ob der Faden fertig ist


ALTES_FENSTER = (
    "AltesFensterBearbeitung"  # Parameter: „Bearbeitung“ öffnet das Fenster auf einer Seite
)


def beta_an():
    return FreeCAD.ParamGet(PARAMETER_PFAD).GetBool(BETA_AN, False)


def altes_fenster():
    """Öffnet „Bearbeitung“ das alte Fenster auf einer Seite statt der Schritte? Vorgabe: nein."""
    return FreeCAD.ParamGet(PARAMETER_PFAD).GetBool(ALTES_FENSTER, False)


def altes_fenster_setzen(an):
    FreeCAD.ParamGet(PARAMETER_PFAD).SetBool(ALTES_FENSTER, bool(an))


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


class _Zeitbalken(QtGui.QWidget):
    """Die Zeit einer Strategie als Balken mit der Zahl daneben – so lang wie ihre Zeit gegen die
    längste des Schritts. Zeigen statt beschreiben (Manuel, 2026-11-11): Dass Planfräsen hier
    dreimal so lang braucht wie Räumen, sieht man, statt „319 % langsamer als Räumen“ zu lesen.
    Angehakt in der Farbe der Auswahl, sonst grau. Der graue Satz der Strategie ist der Tooltip."""

    BALKEN = 70  # Pixel für die längste Zeit

    def __init__(self):
        super().__init__()
        self._anteil, self._text, self._an = 0.0, "", True
        self.setFixedWidth(self.BALKEN + 78)
        self.setMinimumHeight(18)

    def setzen(self, minuten, groesste, an):
        """`minuten` der Strategie (None: keine), `groesste` des Schritts, `an`: angehakt."""
        if minuten is None:
            self._anteil, self._text = 0.0, ""
        else:
            self._anteil = min(1.0, minuten / groesste) if groesste > 0 else 0.0
            self._text = tr("beta.anlegen.minuten", min=_zehntel(minuten))
        self._an = bool(an)
        self.update()

    def text(self):
        return self._text

    def paintEvent(self, _ereignis):  # noqa: N802 – Qt-Name
        if not self._text:
            return
        maler = QtGui.QPainter(self)
        maler.setRenderHint(QtGui.QPainter.Antialiasing)
        palette = self.palette()
        farbe = QtGui.QColor(BALKEN_FARBE if self._an else BLASS)
        hoehe = 8
        oben = (self.height() - hoehe) // 2
        maler.setPen(QtCore.Qt.NoPen)
        maler.setBrush(farbe)
        maler.drawRoundedRect(0, oben, max(4, int(self.BALKEN * self._anteil)), hoehe, 3, 3)
        maler.setPen(palette.color(QtGui.QPalette.WindowText) if self._an else QtGui.QColor(BLASS))
        flaeche = QtCore.QRect(self.BALKEN + 6, 0, self.width() - self.BALKEN - 6, self.height())
        maler.drawText(flaeche, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight, self._text)
        maler.end()


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
        self._beta_nicht_dabei = {}  # Kennung → (Titel, Satz): in der Übersicht abgehakt
        self._tisch = None  # gui_tisch.Tisch: Schritt 1 zeigt, wie das Teil liegt
        self._beta_nur = None  # Übersicht: nur die Wege dieser Bearbeitung im Teil (Kennung)
        self._beta_wege_stand = None  # was die Übersicht gerade im Teil zeigt
        self._farben_basis = None  # (Flächen, Kanten) ohne das, was die Schritte dazu färben
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
        elif self._ebene_der_kette():
            self._bei_der_ebene_beginnen()
        else:
            _KURZER_WEG["an"] = False  # ein neuer Anfang: der kurze Weg gilt erst mit seinem Knopf

    def _ebene_der_kette(self):
        """Ist das der Assistent einer Ebene, den „Anlegen“ davor geöffnet hat (3+2, oder „von
        oben“ an der waagerechten Spindel)? Nicht eine Aufspannung der N-Eck-Stange: Dort wird
        umgespannt, Schritt 1 sagt, wie."""
        from . import schwenken as sw

        return bool(self._folge) and self.job is not None and sw.ist_ebene(self.job)

    def _bei_der_ebene_beginnen(self):
        """Die Ebene einer Kette: Aufspannung, Maschine und Rohteil stehen fest, die Flächen hat der
        Assistent davor gewählt – Schritt 1 wäre eine Seite voller grauer Felder und „Flächen“
        fragte noch einmal nach der Tasche (Manuel, 2026-11-08, an der G550: „geendet bin ich hier
        bei der nächsten aufspannung oder was soll das nun sein ??“). Darum beginnt sie beim
        Schruppen, und über jedem Schritt steht, welche Ebene das ist; „Zurück“ geht zu den Flächen
        und zur Aufspannung."""
        self._beta_unten_klar = True
        kopf, strich, rest = str(self._folge).partition(
            " – "
        )  # „Ebene 1 von 2 aus der Aufspannung“
        self.folge_text.setText(f"<b>{html.escape(kopf)}</b>{html.escape(strich + rest)}")
        self.folge_text.show()
        self.dazu_text.setText(self.dazu_text.text().replace(f"{self._folge}\n", ""))
        if self.gewaehlte:
            self._beta_tasche_ok.add(frozenset(self.gewaehlte))
            # Wer den kurzen Weg genommen hat („Alles vorschlagen“), bekommt auch in der Ebene
            # gleich die Übersicht – sonst die Schritte ab dem Schruppen.
            kurz = _KURZER_WEG.get("an", False)
            self.seite_zeigen(UEBERSICHT if kurz else self._abschnitt_seite(SCHRUPPEN))
        else:
            self.seite_zeigen(1)

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
        self.tasche_text.setTextFormat(QtCore.Qt.RichText)
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
        self._beta_balken = {}  # Kennung → _Zeitbalken neben dem Haken
        self._beta_grund = {}  # Kennung → grauer Halbsatz neben einem nicht angehakten Haken
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
        # Welche Werkzeuge für die Tasche passen – eigene und aus dem Katalog (Plan C2).
        self.werkzeuge_box = QtGui.QWidget()
        box = QtGui.QVBoxLayout(self.werkzeuge_box)
        box.setContentsMargins(0, 4, 0, 4)
        self.werkzeuge_text = QtGui.QLabel()
        self.werkzeuge_text.setWordWrap(True)
        self.werkzeuge_text.setTextFormat(QtCore.Qt.RichText)
        self.werkzeuge_text.setOpenExternalLinks(True)
        box.addWidget(self.werkzeuge_text)
        self.knopf_katalog = knopf(
            tr("beta.werkzeuge.katalog"), tr("beta.werkzeuge.katalog.tooltip"), self.im_katalog
        )
        box.addWidget(self.knopf_katalog, 0, QtCore.Qt.AlignLeft)
        self.werkzeuge_box.hide()
        schruppen.addWidget(self.werkzeuge_box)
        self._beta_masse = None  # (Wahl, werkzeugwahl.Masse) der Tasche
        self._beta_katalog_an = False
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
            # Der graue Satz („→ 6 Lagen, 206 Zeilen … 319 % langsamer als Räumen“) und der zum
            # Material stehen bei den Werten und als Tooltip – in der Zeile steht die Zeit als
            # Balken.
            block.ergebnis.einklappen(True)
            block.material.einklappen(True)
            balken = _Zeitbalken()
            block.widget.layout().itemAt(0).layout().insertWidget(1, balken)
            self._beta_balken[block.s.kennung] = balken
            # Nicht angehakt, aber gerechnet (der Wettbewerb): kein Balken – seine Zeit allein
            # täuschte (Planfräsen 8,1 min neben Räumen 9,8 min, dabei braucht es das Räumen der
            # Böden dazu) –, sondern der eine Halbsatz, warum es nicht der Vorschlag ist.
            grund = _grau()
            grund.setWordWrap(False)
            grund.hide()
            block.widget.layout().itemAt(0).layout().insertWidget(2, grund)
            self._beta_grund[block.s.kennung] = grund
        _aus_layout(self._block_aufbau, self.passt_nicht)
        self.passt_nicht.hide()
        self._reihe = []
        for seite in self._beta_seiten.values():
            seite.layout().addStretch()
        alt_strategien.hide()
        aufbau.removeWidget(alt_strategien)
        self.seiten = [self.seiten[0], flaechen] + [self._beta_seiten[a] for a in ABSCHNITTE]
        # Nach den Schritten die Übersicht: was der Assistent für die Aufspannung vorschlägt, je
        # Bearbeitung Werkzeug und Zeit – dorthin führt „Alles vorschlagen“ (alles_vorschlagen).
        self.uebersicht_seite = QtGui.QWidget()
        uebersicht = QtGui.QVBoxLayout(self.uebersicht_seite)
        uebersicht.setContentsMargins(0, 0, 0, 0)
        self.uebersicht_text = QtGui.QLabel()
        self.uebersicht_text.setWordWrap(True)
        self.uebersicht_text.setTextFormat(QtCore.Qt.RichText)
        self.uebersicht_text.linkActivated.connect(self._uebersicht_verweis)
        uebersicht.addWidget(self.uebersicht_text)
        aufbau.insertWidget(aufbau.indexOf(self._beta_seiten[KANTEN]) + 1, self.uebersicht_seite)
        self.seiten.append(self.uebersicht_seite)
        self._spannmittel_bauen()
        # „Liegt so, wie modelliert“: macht Schritt 1 ohne Klick auf eine Fläche klar.
        self.knopf_wie_modell = knopf(
            tr("beta.unten.modell"), tr("beta.unten.modell.tooltip"), self.wie_modelliert
        )
        self.knopf_unten_waehlen.parentWidget().layout().addWidget(self.knopf_wie_modell)
        self.knopf_unten_modell.hide()  # „Wie modelliert“ – das macht jetzt „Liegt wie im Modell“
        # Die Ebene einer Kette: über jedem Schritt, welche Ebene das ist (_bei_der_ebene_beginnen).
        self.folge_text = QtGui.QLabel()
        self.folge_text.setWordWrap(True)
        self.folge_text.setTextFormat(QtCore.Qt.RichText)
        self.folge_text.hide()
        aufbau.insertWidget(aufbau.indexOf(self.schritt_text), self.folge_text)
        # Unter dem Schritt grau die ganze Folge, der eigene fett.
        self.schrittleiste = _grau()
        self.schrittleiste.setTextFormat(QtCore.Qt.RichText)
        aufbau.insertWidget(aufbau.indexOf(self.schritt_text) + 1, self.schrittleiste)
        # Über den Knöpfen: warum „Weiter“ noch nicht geht – als nächster Schritt zum Lesen.
        self.warum_text = QtGui.QLabel()
        self.warum_text.setWordWrap(True)
        self.warum_text.setStyleSheet(WARUM_FARBE)
        zeile = self.knopf_weiter.parentWidget()
        aufbau.insertWidget(aufbau.indexOf(zeile), self.warum_text)
        # Neu installiert, noch kein Fräser in der Werkzeugverwaltung: Statt viermal rot „leg dort
        # einen an“ ein Knopf, der vier übliche Fräser mit Beispielwerten anlegt – damit steht der
        # Vorschlag sofort (der nächste Schritt ist ein Knopf, Arbeitsregeln Abschnitt 8).
        self.beispiel_box = QtGui.QWidget()
        kasten = QtGui.QVBoxLayout(self.beispiel_box)
        kasten.setContentsMargins(0, 4, 0, 4)
        satz = QtGui.QLabel(tr("beta.beispielwerkzeuge.text"))
        satz.setWordWrap(True)
        kasten.addWidget(satz)
        self.knopf_beispielwerkzeuge = knopf(
            tr("beta.beispielwerkzeuge"),
            tr("beta.beispielwerkzeuge.tooltip"),
            self.beispielwerkzeuge_anlegen,
        )
        kasten.addWidget(self.knopf_beispielwerkzeuge, 0, QtCore.Qt.AlignLeft)
        self.beispiel_box.hide()
        aufbau.insertWidget(aufbau.indexOf(self.warum_text), self.beispiel_box)
        # Der kurze Weg (Manuel, 2026-11-11: „ultra easy … ohne gross nachzudenken“): ein Klick
        # statt sechs Schritte – alles aus der Aufspannung, vorgeschlagen, mit Übersicht.
        self.knopf_alles = knopf(tr("beta.alles"), tr("beta.alles.tooltip"), self.alles_vorschlagen)
        zeile.layout().insertWidget(zeile.layout().indexOf(self.knopf_weiter), self.knopf_alles)
        # Der eine Knopf, der zum Ziel führt, fällt auf (fett) – „Weiter“ ist der Weg für den, der
        # Schritt für Schritt entscheiden will.
        schrift = self.knopf_alles.font()
        schrift.setBold(True)
        self.knopf_alles.setFont(schrift)
        # Was „Anlegen“ in diesem Schritt anlegt – es legt ja nur bis hier an – und was danach
        # noch angehakt ist (kommt mit „Weiter bearbeiten“).
        self.anlegen_text = _grau()
        self.anlegen_text.setWordWrap(True)
        aufbau.insertWidget(aufbau.indexOf(zeile), self.anlegen_text)
        # Danach das Fenster „Angelegt“ (Konzept B6) – hier ab- und wieder anzuhaken.
        self.haken_fertig = QtGui.QCheckBox(tr("beta.fertig.zeigen"))
        self.haken_fertig.setToolTip(tr("beta.fertig.zeigen.tooltip"))
        self.haken_fertig.setChecked(fertig_zeigen_an())
        self.haken_fertig.toggled.connect(
            lambda an: FreeCAD.ParamGet(PARAMETER_PFAD).SetBool(FERTIG_ZEIGEN, bool(an))
        )
        aufbau.insertWidget(aufbau.indexOf(zeile), self.haken_fertig)
        # Er steht im Fenster „Angelegt“ selbst und in den Einstellungen – in jedem Schritt war er
        # eine Zeile mehr zu lesen, die mit dem Schritt nichts zu tun hat.
        self.haken_fertig.hide()
        # Im letzten Schritt: anlegen und dasselbe Teil anders gespannt weiter (Plan C4).
        self.knopf_umspannen = knopf(
            tr("beta.umspannen"), tr("beta.umspannen.tooltip"), self.umspannen
        )
        self.knopf_umspannen.hide()
        aufbau.insertWidget(aufbau.indexOf(zeile), self.knopf_umspannen, 0, QtCore.Qt.AlignRight)
        # Schritt „Flächen“: Der Satz „ebene nach oben werden plan gefräst …“ und die Zeile zu
        # Maschine, Rohteil und Nullpunkt sind Tooltips (der Liste, der Schrittleiste) – nicht
        # Lesestoff über der Liste.
        self.flaechen_text.hide()
        self.rohteil_kurz.hide()
        self.unfertig.setStyleSheet("")  # der Satz trägt das Kästchen in der Farbe der Flächen
        self.unfertig.setTextFormat(QtCore.Qt.RichText)
        self._rohteil_einklappen()
        return form

    def _rohteil_einklappen(self):
        """Schritt 1: Rohteil und Nullpunkt als eine Zeile („Aufmaß 1 mm rundum · Nullpunkt: Mitte
        oben“) mit einem Knopf, der ihre Felder aufklappt. Sie sind vorbelegt und werden meist nur
        geprüft – offen machten ihre sieben Felder den ersten Schritt zur längsten Seite (Manuel,
        2026-10-30: das Fenster „zu groß geworden“). Offen bleiben sie, sobald etwas anderes als der
        Quader mit Aufmaß gewählt ist: Dann gibt es dort etwas einzutragen."""
        seite = self.seiten[0].layout()
        anfang = next(
            (
                i
                for i in range(seite.count())
                if isinstance(seite.itemAt(i).widget(), QtGui.QLabel)
                and seite.itemAt(i).widget().text() == tr("ba.rohteil")
            ),
            None,
        )
        if anfang is None:
            return
        self.rohteil_huelle = QtGui.QWidget()
        innen = QtGui.QVBoxLayout(self.rohteil_huelle)
        innen.setContentsMargins(0, 0, 0, 0)
        # Umhängen ohne takeAt: Das gäbe Python den Eintrag zu eigen – ein inneres Layout würde
        # dann zweimal freigegeben (Python und sein neues Eltern-Layout), FreeCAD stürzte beim
        # Schließen des Fensters ab (gesehen 2026-11-11 in szenario_beta_schritte).
        while seite.count() > anfang:
            eintrag = seite.itemAt(anfang)
            if eintrag.widget() is not None:
                widget = eintrag.widget()
                seite.removeWidget(widget)
                innen.addWidget(widget)
            elif eintrag.layout() is not None:
                inneres = eintrag.layout()
                seite.removeItem(inneres)
                innen.addLayout(inneres)
            else:
                seite.removeItem(eintrag)  # ein Abstandhalter
        zeile = QtGui.QWidget()
        reihe = QtGui.QHBoxLayout(zeile)
        reihe.setContentsMargins(0, 0, 0, 0)
        self.knopf_rohteil_aendern = _klappknopf(
            tr("beta.rohteil.aendern"), tr("beta.rohteil.aendern.tooltip")
        )
        self.rohteil_zeile = _grau()
        self.rohteil_zeile.setWordWrap(True)
        reihe.addWidget(self.knopf_rohteil_aendern)
        reihe.addWidget(self.rohteil_zeile, 1)
        seite.addWidget(zeile)
        seite.addWidget(self.rohteil_huelle)
        seite.addStretch()
        self.knopf_rohteil_aendern.toggled.connect(lambda _an: self._rohteil_klappen())
        for wahl in (
            self.knopf_rohteil_quader,
            self.knopf_rohteil_masse,
            self.knopf_rohteil_zylinder,
            self.knopf_rohteil_teil,
        ):
            wahl.toggled.connect(lambda _an: self._rohteil_klappen())
        self._rohteil_klappen()

    def _rohteil_klappen(self):
        """Die Felder für Rohteil und Nullpunkt: offen auf Klick – und immer, wenn nicht der Quader
        mit Aufmaß gewählt ist."""
        if not hasattr(self, "rohteil_huelle"):
            return
        offen = self.knopf_rohteil_aendern.isChecked() or not self.knopf_rohteil_quader.isChecked()
        self.rohteil_huelle.setVisible(offen)
        self.rohteil_zeile.setVisible(not offen)
        self.knopf_rohteil_aendern.setArrowType(
            QtCore.Qt.DownArrow if offen else QtCore.Qt.RightArrow
        )

    def _rohteil_kurz_zeigen(self):
        super()._rohteil_kurz_zeigen()
        self._tisch_zeigen()
        if hasattr(self, "rohteil_zeile") and hasattr(self, "rohteil_kurz"):
            teile = self.rohteil_kurz.text().split(" · ")
            eintrag = self.maschine() if hasattr(self, "wahl_maschine") else None
            if eintrag is not None and len(teile) > 1:
                teile = teile[1:]  # die Maschine steht in Schritt 1 gleich darüber
            self.rohteil_zeile.setText(" · ".join(teile))

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
        self.spannmittel_text.setTextFormat(QtCore.Qt.RichText)
        self.spannmittel_text.linkActivated.connect(self._katalog_spannmittel_nehmen)
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
        self._tisch_zeigen()
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

    def _maschine_gewaehlt(self):
        """Ohne eigene Maschine sagt die Auswahl selbst, womit der Assistent rechnet („3-Achs-Fräse
        – keine eigene gewählt“) – die vier Zeilen dazu sind ihr Tooltip statt Lesestoff."""
        super()._maschine_gewaehlt()
        if getattr(self, "_maschinen_fuellt", False) or not hasattr(self, "maschine_hinweis"):
            return
        leer = self.wahl_maschine.findData("")
        if leer >= 0:
            self.wahl_maschine.setItemText(leer, tr("beta.maschine.standard"))
        ohne = self.maschine() is None
        self.wahl_maschine.setToolTip(tr("ba.maschine.leer") if ohne else "")
        if ohne:
            self.maschine_hinweis.hide()

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
        # Im Fenster steht nur, was gewählt ist oder sich anklicken lässt; „noch keine in der
        # Sammlung“ und „3 von 5 nehmen dieses Rohteil“ sind der Tooltip der Auswahl (die ✓ und ✗
        # stehen dort schon).
        satz, dazu = "", tr("beta.spannmittel.tooltip")
        if not self._sammlung().spannmittel:
            dazu = tr("beta.spannmittel.leer")
        elif jetzt is not None:
            satz = sm.beschreibung(jetzt)
            if box is not None and sm.hinweise(jetzt, box):
                satz += " – " + " ".join(sm.hinweise(jetzt, box))
        elif box is not None:
            dazu = tr("beta.spannmittel.anzahl", passend=passend, alle=len(eintraege))
        self.wahl_spannmittel.setToolTip(dazu)
        self._beta_katalog_spannmittel = []
        satz = html.escape(satz, quote=False)
        if box is not None and jetzt is None and not passend:
            # Ein rundes Rohteil (Zylinder) zuerst im Futter (Manuel: „vorschläge … wo das bauteil
            # reinpassen würde vom spannmitel her“).
            rund = getattr(getattr(self.job, "Stock", None), "Radius", None) is not None
            arten = (sm.FUTTER, sm.ZENTRISCH, sm.SCHRAUBSTOCK) if rund else None
            vorschlaege = sm.aus_dem_katalog(box, arten=arten) if arten else sm.aus_dem_katalog(box)
            self._beta_katalog_spannmittel = vorschlaege
            if vorschlaege:
                # Je Vorschlag ein Verweis: übernimmt ihn in die Sammlung und wählt ihn
                # (Gedächtnis „Nächster Schritt als Knopf“).
                namen = " · ".join(
                    f'<a href="spannmittel:{i}">{html.escape(v.text)}</a>'
                    for i, v in enumerate(vorschlaege)
                )
                satz = html.escape(tr("beta.spannmittel.katalog_waehlen"), quote=False)
                satz += " " + namen
        elif box is None:
            # Noch kein Rohteil: Es gibt nichts zu sagen – der Satz „steht hier, sobald …“ war nur
            # Lesestoff. Er bleibt als Tooltip der Auswahl.
            satz = ""
            if self._sammlung().spannmittel:
                self.wahl_spannmittel.setToolTip(tr("beta.spannmittel.ohne_rohteil"))
        self.spannmittel_text.setText(satz)
        self.spannmittel_text.setVisible(bool(satz))

    def _katalog_spannmittel_nehmen(self, verweis):
        """Ein Vorschlag aus dem Katalog („spannmittel:<n>“): in die Sammlung (gespeichert, wie im
        Fenster „Spannmittel …“) und gleich gewählt – gibt es ihn dort schon, der vorhandene."""
        if not str(verweis).startswith("spannmittel:"):
            return
        try:
            s = self._beta_katalog_spannmittel[int(str(verweis).split(":", 1)[1])]
        except (ValueError, IndexError, AttributeError):
            return
        sammlung = self._sammlung()
        vorhanden = sammlung.gleiches(s)
        if vorhanden is None:
            vorhanden = sammlung.dazu(sm.Spannmittel.aus_dict(s.als_dict()))
            sammlung.speichern()
        self._spannmittel_anbieten()
        index = self.wahl_spannmittel.findData(vorhanden.kennung)
        if index >= 0:
            self.wahl_spannmittel.setCurrentIndex(index)
            # setCurrentIndex meldet kein „activated“: Der Vorschlag stand sonst nur in der Liste,
            # am Job galt er nicht (gesehen 2026-11-11 – das Spannmittel fehlte im 3D).
            self._spannmittel_gewaehlt()

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
        self._tisch_zeigen()  # das Spannmittel steht im 3D um das Rohteil

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
        if self._seite != UEBERSICHT:
            self._uebersicht_wege([])  # sie gehören zur Übersicht
        if self._farben_basis is not None:
            self._farben_neu()  # die Übersicht färbt mehr als die Schritte
        namen = [tr("ba.schritt.aufspannung"), tr("beta.schritt.flaechen")]
        namen += [*_abschnitt_namen(), tr("beta.schritt.uebersicht")]
        self.schritt_text.setText(tr("beta.schritt", name=namen[self._seite]))
        self.schrittleiste.setText(self._schrittleiste())
        if self.zu_aendern is None:
            anleitungen = [
                (
                    tr("beta.anleitung.aufspannung")
                    if self.job is not None
                    else (
                        tr("beta.anleitung.ein_teil")
                        if self._einziges_teil() is not None
                        else tr("beta.anleitung.teil")
                    )
                ),
                tr("beta.anleitung.flaechen"),
                tr("beta.anleitung.schruppen"),
                tr("beta.anleitung.loecher"),
                tr("beta.anleitung.schlichten"),
                tr("beta.anleitung.kanten"),
                tr("beta.anleitung.uebersicht"),
            ]
            self.anleitung.setText(anleitungen[self._seite])
        if self._seite == 0 and self.job is not None and not self._aufspannung_fest():
            # Gleich bereit: der nächste Klick ist die Fläche, die unten liegt.
            if not self._beta_unten_klar:
                self.knopf_unten_waehlen.setChecked(True)
        elif self.knopf_unten_waehlen.isChecked():
            self.knopf_unten_waehlen.setChecked(False)
        if self._seite == ERSTER_ABSCHNITT + SCHRUPPEN:
            self._werkzeuge_zeigen()
        self._rohteil_kurz_zeigen()
        self._beta_knoepfe()
        self.nichts_angehakt.hide()

    def _tisch_zeigen(self):
        """Schritt 1 zeigt, wie das Teil liegt: eine Platte unter dem Rohteil (vor dem Job unter
        dem Teil, wie es modelliert ist) mit einem Pfeil nach +X – statt es in Worten zu fragen.
        Wer es sieht, klickt nur, wenn es nicht stimmt. Nicht an der Drehmaschine (dort ist es
        eine Stange im Futter), nicht beim Ändern und nicht in der Ebene einer Kette."""
        if not hasattr(self, "_beta_seiten"):
            return
        box = None
        if (
            getattr(self, "_seite", 0) == 0
            and not getattr(self, "geschlossen", False)
            and self.zu_aendern is None
            and not self.nur_vierachs()
            and not self._ebene_der_kette()
        ):
            box = self._tisch_kasten()
        if box is None:
            if self._tisch is not None:
                self._tisch.weg()
            return
        if self._tisch is None:
            from . import gui_tisch

            self._tisch = gui_tisch.Tisch(self.doc)
        # Mit gewähltem Spannmittel steht das Rohteil darin (sm.koerper_im_job, wie die Kollision
        # es nimmt) – sonst liegt es auf der Platte.
        auf = sm.aufspannung(self.job) if self.job is not None else None
        if auf is None:
            self._tisch.zeigen(box)
        else:
            job = self.job
            self._tisch.zeigen(box, repr(auf.als_dict()), lambda: sm.koerper_im_job(job))

    def _tisch_kasten(self):
        """(xmin, ymin, zmin, xmax, ymax, zmax) dessen, was auf dem Tisch liegt: das Rohteil des
        Jobs, sonst das einzige Teil des Dokuments – None ohne beides."""
        form = None
        if self.job is not None:
            form = getattr(getattr(self.job, "Stock", None), "Shape", None)
            if form is None or form.isNull():
                form = vr.modell(self.job).Shape
        else:
            teil = self._einziges_teil()
            form = teil.Shape if teil is not None else None
        if form is None or form.isNull() or not form.BoundBox.isValid():
            return None
        b = form.BoundBox
        return (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)

    def _vor_dem_schliessen(self):
        if self._tisch is not None:
            self._tisch.weg()
        super()._vor_dem_schliessen()

    def _schrittleiste(self):
        """„Aufspannung › **Flächen** › Schruppen …“ – ohne die Schritte, die nichts haben."""
        teile = []
        kurz = [
            tr("ba.schritt.aufspannung"),
            tr("beta.schritt.flaechen"),
            *_abschnitt_namen(),
            tr("beta.schritt.uebersicht"),
        ]
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
        self.flaechen_liste.setToolTip(self.flaechen_text.text())
        self.schrittleiste.setToolTip(self.rohteil_kurz.text())
        self.knopf_zurueck.setVisible(self._seite > 0 and self._seite > self._erste_erlaubte())
        weiter_da = self._seite < ERSTER_ABSCHNITT or self._naechste_seite() is not None
        self.knopf_weiter.setVisible(weiter_da)
        self.beispiel_box.setVisible(self._seite >= ERSTER_ABSCHNITT and self._ohne_fraeser())
        self.knopf_alles.setVisible(
            self._seite < ERSTER_ABSCHNITT
            and (self.job is not None or self._einziges_teil() is not None)
            and self.zu_aendern is None
            and self._beta_ab is None
            and not self.nur_vierachs()
            and not self._ebene_der_kette()
        )
        # Nicht grau, weil etwas fehlt (Arbeitsregeln, Abschnitt 8): Der Klick zeigt, was fehlt
        # (_warum_betonen). Grau nur ohne Teil und an der Drehmaschine – das sagt Schritt 1.
        self.knopf_weiter.setEnabled(geht or bool(warum))
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
            self._zeitbalken_setzen()
            self._anlegen_zeigen()

    def _zeitbalken_setzen(self):
        """Je Strategie ihre Zeit als Balken, gemessen an der längsten ihres Schritts; ihr grauer
        Satz (und beim Schruppen das Ziel) als Tooltip. Das Ziel selbst steht nicht mehr als Satz
        über dem Schritt."""
        self.ziel_text.hide()
        groesste = {}
        for block in self.bloecke:
            if block.moeglich and block.zeit is not None:
                a = abschnitt(block)
                groesste[a] = max(groesste.get(a, 0.0), block.zeit)
        ziel = _ohne_marken(self.ziel_text.text())
        for block in self.bloecke:
            balken = self._beta_balken.get(block.s.kennung)
            if balken is None:
                continue
            zeit = block.zeit if block.moeglich else None
            balken.setzen(zeit, groesste.get(abschnitt(block), 0.0), block.aktiv())
            saetze = [_ohne_marken(block.ergebnis.text()), _ohne_marken(block.material.text())]
            if abschnitt(block) == SCHRUPPEN:
                saetze.append(ziel)
            tooltip = "\n".join(s for s in saetze if s)
            balken.setToolTip(tooltip)
            an = block.aktiv()
            balken.setVisible(zeit is not None and an)
            grund = self._beta_grund[block.s.kennung]
            halbsatz = (
                saetze[0].rsplit(" – ", 1)[1] if zeit is not None and " – " in saetze[0] else ""
            )
            grund.setText(grund.fontMetrics().elidedText(halbsatz, QtCore.Qt.ElideRight, 300))
            grund.setToolTip(tooltip)
            grund.setVisible(bool(halbsatz) and not an)

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
                    teile.append(tr("beta.anlegen.minuten", min=_zehntel(block.zeit)))
                    zeit += block.zeit
                jetzt.append(
                    f"{block.s.titel()} ({', '.join(teile)})" if teile else block.s.titel()
                )
            elif abschnitt(block) > a:
                spaeter.append(block.s.titel())
        nur_ebene = not jetzt and bool(self._beta_geschwenkt)
        if nur_ebene:
            # Hier ist nichts angehakt, aber „Anlegen“ legt die Ebene an und öffnet ihren
            # Assistenten – der Satz „legt hier nichts an“ stand daneben und widersprach.
            text = tr("beta.anlegen.ebene")
            self.knopf_fertig.setText(tr("beta.anlegen.ebene.knopf"))
            self.knopf_fertig.setToolTip(tr("beta.anlegen.ebene"))
        elif not jetzt:
            text = tr("beta.anlegen.nichts")
        elif zeit > 0:
            text = tr("beta.anlegen.liste", liste=", ".join(jetzt), min=dezimal(f"{zeit:.1f}"))
        else:
            text = tr("beta.anlegen.liste_ohne_zeit", liste=", ".join(jetzt))
        if spaeter:
            text += " " + tr("beta.anlegen.spaeter", liste=", ".join(spaeter))
        self.anlegen_text.setToolTip(text)
        if jetzt and zeit > 0 and not nur_ebene:
            # Die Liste steht schon da – als Haken mit Zeitbalken. Hier nur die Summe.
            text = tr("beta.anlegen.kurz", min=dezimal(f"{zeit:.1f}"))
        self.anlegen_text.setText(text)
        self.anlegen_text.show()
        self.beispiel_box.setVisible(self._seite >= ERSTER_ABSCHNITT and self._ohne_fraeser())
        if self._seite == UEBERSICHT:
            self.anlegen_text.hide()  # dasselbe steht dort als Tabelle
            if not self.vorschau_laeuft() and not self._ohne_fraeser():
                self._nicht_machbares_abhaken()
            self._uebersicht_zeigen()

    def alles_vorschlagen(self):
        """Der kurze Weg: alles, was in dieser Aufspannung von oben geht (aus_der_aufspannung),
        mit den Strategien und Werkzeugen, die der Assistent auch in den Schritten vorschlägt –
        und gleich zur Übersicht. Ohne Antwort zur Lage gilt „Liegt wie im Modell“. Angelegt wird
        erst mit „Anlegen“; „Zurück“ führt in die Schritte."""
        if not self._mit_einzigem_teil_beginnen() or self.nur_vierachs():
            return
        if not (self._beta_unten_klar or self._aufspannung_fest()):
            self.wie_modelliert()
        self._beta_nicht_dabei = {}
        self.aus_der_aufspannung()
        if not self.gewaehlte:
            self.seite_zeigen(1)  # dort steht je Fläche, warum sie hier nicht geht
            return
        if self._fuenfachs():
            # An der 5-Achs-Maschine gehören die Wände einer Tasche dazu, auch wenn sie von oben
            # nicht zu erreichen sind (unter einem Rand): wie „Ganze Tasche nehmen“ – der Assistent
            # schlägt für sie Flanke oder 3D-Schlichten vor.
            self._tasche_pruefen()
            if self._beta_fehlende:
                self.ganze_tasche()
        self._beta_tasche_ok.add(frozenset(self.gewaehlte))
        _KURZER_WEG["an"] = True  # gilt auch für die Ebenen, die „Anlegen“ danach öffnet
        self.seite_zeigen(UEBERSICHT)

    def _nicht_machbares_abhaken(self):
        """In der Übersicht: Was sich nicht anlegen lässt (kein passendes Werkzeug, zu kurz …),
        verliert den Haken und steht unter „Nicht dabei“ mit seinem Satz – „Anlegen“ geht für
        den Rest. Sonst sperrte eine einzige rote Zeile den ganzen Vorschlag."""
        raus = [
            b
            for b in self.aktive_bloecke()
            if b.moeglich and b.vorschau is None and b.hinweis.text() and not b.kann_anlegen()
        ]
        if not raus:
            return
        self._fuellt = True
        try:
            for block in raus:
                self._beta_nicht_dabei[block.s.kennung] = (block.s.titel(), block.hinweis.text())
                block.haken.setChecked(False)
                block.zustand_zeigen()
        finally:
            self._fuellt = False
        self.vorschau_starten()

    def _unfertig_ohne(self):
        return tuple(self._beta_nicht_dabei)

    def _ohne_fraeser(self):
        """Hat die Werkzeugverwaltung für das, was angehakt ist, gar keinen Fräser (neu
        installiert)? Dann sagt es jede Strategie mit demselben Satz."""
        satz = tr("va.planfraeser.keiner")
        return any(b.moeglich and b.aktiv() and satz in b.hinweis.text() for b in self.bloecke)

    def beispielwerkzeuge_anlegen(self):
        """Legt die vier Beispiel-Fräser (werkzeuge.starterkiste: Ø 12, Planfräser Ø 50, Ø 6, Ø 20 mit
        angenommenen Schnittwerten) in die Werkzeugverwaltung – auf freie Nummern, was schon da
        ist, bleibt – und rechnet den Vorschlag damit neu."""
        from . import werkzeuge as wz

        bibliothek = wz.Bibliothek.laden()
        belegt = {w.nummer for w in bibliothek.werkzeuge}
        for werkzeug in wz.starterkiste():
            if werkzeug.nummer in belegt:
                werkzeug.nummer = bibliothek.naechste_nummer()
            bibliothek.werkzeuge.append(werkzeug)
            belegt.add(werkzeug.nummer)
        bibliothek.speichern()
        self._beta_nicht_dabei = {}
        self._werkzeuge_gespeichert()
        if self.job is not None and self.gewaehlte:
            # Mit Werkzeugen neu vorschlagen: Haken und je Strategie der passende Fräser.
            self._haken_vorschlagen(vr.modell(self.job).Shape)
            self.vorschau_starten()
        self._beta_knoepfe()

    def _uebersicht_zeigen(self):
        """Die Übersicht: je Bearbeitung, die „Anlegen“ anlegt, eine Zeile in der Farbe ihrer Wege
        im Teil, mit Werkzeug und Zeit, und die Summe. Ein Klick auf eine Zeile zeigt nur ihre
        Wege. Was nicht fertig wird oder von oben nicht geht, steht als Farbe im Teil – die Zeile
        dazu trägt dieselbe Farbe statt einer Liste „Face1, Face2 …“."""
        from . import gui_bahnvorschau as gb
        from . import werkzeuge as wz

        zeilen, summe, achtung, bahnen = [], 0.0, [], []
        schrift = self.uebersicht_text.palette().color(QtGui.QPalette.WindowText).name()
        for block in self._in_anlege_reihe(self.aktive_bloecke()):
            if not block.moeglich:
                continue
            fraeser = block.fraeser()
            werkzeug = ""
            if fraeser is not None:
                nummer = getattr(fraeser, "nummer", None)
                werkzeug = (f"T{nummer} " if nummer is not None else "") + wz.anzeigename(fraeser)
            if block.zeit is not None:
                zeit = tr("beta.anlegen.minuten", min=_zehntel(block.zeit))
                summe += block.zeit
            else:
                zeit = "…"
            kennung, farbe = block.s.kennung, gb.farbe_hex(len(zeilen))
            if block.vorschau is not None:
                bahnen.append((block.vorschau, gb.farbe(len(zeilen)), kennung))
            blass = self._beta_nur not in (None, kennung)
            ziel = f"href='{ZEIGE}{kennung}' style='text-decoration: none; color: "
            zeilen.append(
                f"<tr><td><a {ziel}{BLASS if blass else farbe};'>■</a>&nbsp;</td>"
                f"<td><a {ziel}{BLASS if blass else schrift};'>"
                f"<b>{html.escape(block.s.titel())}</b></a>&nbsp;&nbsp;</td>"
                f"<td>{html.escape(werkzeug)}&nbsp;&nbsp;</td>"
                f"<td align='right'>{html.escape(zeit)}</td></tr>"
            )
            hinweis = _ohne_marken(block.hinweis.text())
            if hinweis and tr("va.planfraeser.keiner") in block.hinweis.text():
                continue  # dafür steht der Knopf „Beispiel-Werkzeuge anlegen“ darunter
            if hinweis:
                achtung.append(f"<b>{html.escape(block.s.titel())}:</b> {html.escape(hinweis)}")
        rest = self._uebersicht_rest()
        mit_ebene = bool(self._beta_geschwenkt and self.ebene_text.text())
        if zeilen:
            if self.vorschau_laeuft():
                zeilen.append(
                    f"<tr><td></td><td colspan='3'><i>"
                    f"{html.escape(tr('beta.uebersicht.rechnet'))}</i></td></tr>"
                )
            elif summe > 0:
                zeilen.append(
                    f"<tr><td></td><td colspan='2'>{html.escape(tr('beta.uebersicht.zusammen'))}"
                    f"</td><td align='right'><b>{html.escape(_minuten_text(summe))}</b></td></tr>"
                )
            teile = [f"<table cellspacing='2'>{''.join(zeilen)}</table>"]
            if mit_ebene:
                teile.append(html.escape(self.ebene_text.text()))
        elif mit_ebene:
            # Nichts in diesem Job – aber in einer Ebene, die „Anlegen“ gleich öffnet.
            teile = [html.escape(self.ebene_text.text())]
        else:
            teile = [html.escape(tr("beta.uebersicht.nichts"))]
        if rest:
            teile.append(f"<span style='color: {REST_FARBE};'>■</span> {html.escape(rest)}")
        if self._beta_nicht_dabei:
            # Der Satz der Strategie mit seinen Verweisen („T1 auf 51 mm ausspannen“, „So
            # einrichten“): Ein Klick hier behebt es, die Strategie kommt wieder dazu.
            nicht = "<br>".join(
                f"<b>{html.escape(titel)}:</b> {_verweise_fuer(kennung, satz)}"
                for kennung, (titel, satz) in self._beta_nicht_dabei.items()
            )
            teile.append(
                f"<span style='color: #c03030;'>{html.escape(tr('beta.uebersicht.nicht_dabei'))}"
                f"</span><br>{nicht}"
            )
        if achtung:
            teile.append(
                f"<span style='color: #c03030;'>{html.escape(tr('beta.uebersicht.achtung'))}"
                f"<br>{'<br>'.join(achtung)}</span>"
            )
        self.uebersicht_text.setText("<br><br>".join(teile))
        self._uebersicht_wege(bahnen)

    def _uebersicht_wege(self, bahnen):
        """Die Wege der Übersicht im Teil: je Bearbeitung in der Farbe ihrer Zeile – oder nur die
        der angeklickten Zeile (`_beta_nur`). `bahnen` ist [(Vorschau, Farbe, Kennung)]; leer nimmt
        sie weg. Neu gezeichnet wird nur, wenn sich etwas geändert hat."""
        from . import gui_bahnvorschau as gb

        gezeigt = getattr(self._bahnvorschau, "kennung", None)
        unsere = bool(gezeigt) and gezeigt[0] == "uebersicht"
        if self._beta_nur is not None and all(k != self._beta_nur for _b, _f, k in bahnen):
            self._beta_nur = None
        zeige = [(b, f) for b, f, k in bahnen if self._beta_nur in (None, k)]
        if not zeige:
            if unsere:
                self._bahnvorschau.weg()
                self._vorschau_knoepfe_setzen()
            self._beta_wege_stand = None
            return
        stand = tuple((id(b), f) for b, f in zeige)
        if unsere and stand == self._beta_wege_stand:
            return
        if self._bahnvorschau is None:
            self._bahnvorschau = gb.Bahnvorschau(self.doc)
        self._bahnvorschau.zeigen(
            ("uebersicht", self._beta_nur),
            [b for b, _f in zeige],
            self._job_zum_teil(),
            [f for _b, f in zeige],
        )
        self._beta_wege_stand = stand
        self._vorschau_knoepfe_setzen()

    # --- Zeigen statt beschreiben: Farben im Teil ---------------------------------------------

    def _farben_zeigen(self, farben, kanten=None):
        self._farben_basis = (dict(farben or {}), dict(kanten or {}))
        super()._farben_zeigen(self._mit_eigenen_farben(farben), kanten)

    def _farben_neu(self):
        """Färbt das Teil neu – nach dem Rechnen (was nicht fertig wird) und beim Seitenwechsel."""
        if self._farben_basis is not None and self.job is not None:
            flaechen, kanten = self._farben_basis
            super()._farben_zeigen(self._mit_eigenen_farben(flaechen), kanten)

    def _mit_eigenen_farben(self, farben):
        """`farben` (Nummer der Fläche → Farbe) und dazu: orange, was am Ende keine genaue Bahn
        hätte; in der Übersicht violett, was in dieser Aufspannung von oben nicht geht."""
        neu = dict(farben or {})
        if self.job is None or self._ist_stl():
            return neu
        eigene = []
        if getattr(self, "_seite", 0) == 1:
            # Schritt „Flächen“: was zur Tasche der Auswahl noch gehört (die Frage darunter).
            eigene += [(n, TASCHE_FARBE) for n in getattr(self, "_beta_fehlende", None) or ()]
        eigene += [(n, UNFERTIG_FARBE) for n, _k in getattr(self, "_unfertig_liste", None) or ()]
        if getattr(self, "_seite", 0) == UEBERSICHT:
            eigene += [(n, REST_FARBE) for n in self._rest_flaechen()]
        for name, farbe in eigene:
            if name.startswith("Face") and name[4:].isdigit():
                neu[int(name[4:]) - 1] = farbe
        return neu

    def _unfertig_zeigen(self, form):
        """Wie im alten Fenster – aber gezeigt statt beschrieben: Die Flächen stehen orange im
        Teil, der Satz nennt nur ihre Zahl (der lange mit den Namen ist sein Tooltip), und der
        Haken, der sie fertig macht, ist ein Knopf."""
        super()._unfertig_zeigen(form)
        self._farben_neu()
        if self.unfertig.isHidden():
            return
        anzahl = len(self._unfertig_liste)
        self.unfertig.setToolTip(self.unfertig.text())
        if anzahl == 1:
            kurz = tr("beta.unfertig.kurz.eine")
        else:
            kurz = tr("beta.unfertig.kurz", anzahl=anzahl)
        self.unfertig.setText(
            f"<span style='color: {UNFERTIG_FARBE};'>■</span> {html.escape(kurz)}"
        )
        bloecke = self._unfertig_haken()
        if bloecke and self.unfertig_angebot.isHidden():
            titel = ", ".join(f"„{b.s.titel()}“" for b in bloecke)
            self.unfertig_satz.setText("")
            self.unfertig_knopf.setText(tr("beta.unfertig.anhaken", bloecke=titel))
            self.unfertig_knopf.setToolTip(tr("beta.unfertig.anhaken.tooltip"))
            self._unfertig_aktion = lambda b=tuple(bloecke): self._unfertige_anhaken(b)
            self.unfertig_angebot.show()

    def _unfertig_haken(self):
        """Die wenigsten Strategien, die alles Unfertige fertig machen – je Fläche die erste, die
        es kann, wenn nicht schon eine gewählte sie mitnimmt. Ohne die unter „Nicht dabei“."""
        wahl = []
        for _name, koennten in self._unfertig_liste:
            koennten = [b for b in koennten if b.s.kennung not in self._beta_nicht_dabei]
            if koennten and not any(b in wahl for b in koennten):
                wahl.append(koennten[0])
        return wahl

    def _unfertige_anhaken(self, bloecke):
        for block in bloecke:
            block.haken.setChecked(True)  # wie von Hand: rechnet neu (haken_geklickt)
        self._beta_knoepfe()

    def _uebersicht_verweis(self, ziel):
        """Ein Verweis unter „Nicht dabei“ angeklickt: Die Strategie bekommt ihren Haken wieder und
        führt ihren Verweis aus (ausspannen, die Empfehlung einrichten) – danach rechnet die
        Vorschau neu; geht es dann, steht sie in der Tabelle."""
        if ziel.startswith(ZEIGE):
            # Eine Zeile angeklickt: nur ihre Wege im Teil – noch ein Klick zeigt wieder alle.
            kennung = ziel[len(ZEIGE) :]
            self._beta_nur = None if self._beta_nur == kennung else kennung
            self._uebersicht_zeigen()
            return
        if not ziel.startswith(VERWEIS_BLOCK):
            return
        _marke, kennung, rest = ziel.split("|", 2)
        block = next((b for b in self.bloecke if b.s.kennung == kennung), None)
        if block is None:
            return
        self._beta_nicht_dabei.pop(kennung, None)
        self._fuellt = True
        try:
            block.haken.setChecked(True)
            block.zustand_zeigen()
        finally:
            self._fuellt = False
        block._hinweis_verweis(rest)
        self.vorschau_starten()
        self._beta_knoepfe()

    def _rest_flaechen(self):
        """Die Flächen, die der kurze Weg nicht nimmt, weil sie in dieser Aufspannung von oben
        nicht zu erreichen sind (Wände unter einem Rand, die Unterseite)."""
        zugang = getattr(self, "_zugang", None)
        offen = set(getattr(zugang, "unerreichbar", None) or ()) - set(self.gewaehlte)
        return sorted((n for n in offen if n.startswith("Face")), key=lambda n: int(n[4:]))

    def _uebersicht_rest(self):
        """Ein Satz zu diesen Flächen – sie stehen violett im Teil; „“ ohne."""
        namen = self._rest_flaechen()
        if not namen:
            return ""
        return tr("beta.uebersicht.rest", anzahl=len(namen))

    def _frage_passt(self, frage, widget, passt):
        # Die Schritte sind die Reihenfolge: Die Frage danach hängt hier in keinem Layout mehr –
        # eingeblendet läge sie quer über dem Schritt „Flächen“ (gesehen am Bild, 2026-11-11).
        super()._frage_passt(frage, widget, passt and frage != "reihenfolge")

    def _erste_erlaubte(self):
        """„Weiter bearbeiten“ beginnt hinter dem, was schon angelegt ist: nicht davor zurück."""
        return getattr(self, "_beta_start", 0)

    def weiter(self):
        geht, warum = self._weiter_geht()
        if not geht:
            if warum:
                self._warum_betonen()
            return
        naechste = self._naechste_seite()
        if naechste is not None:
            self.seite_zeigen(naechste)

    def _warum_ziele(self):
        """Womit es in diesem Schritt weitergeht – die Knöpfe oder die Liste, die noch fehlen."""
        if self._seite == 0:
            return [self.knopf_unten_waehlen, self.knopf_wie_modell]
        if self._seite == 1 and self.tasche_box.isVisible():
            knoepfe = (self.knopf_tasche_schruppen, self.knopf_ganze_tasche, self.knopf_nur_diese)
            return [k for k in knoepfe if k.isVisible()]
        if self._seite == 1:
            return [self.flaechen_liste]
        return []

    def _warum_betonen(self):
        """„Weiter“ geklickt, aber etwas fehlt: der Satz darüber fett, und was zu tun ist, bekommt
        für einen Moment einen Rahmen – so führt der Knopf hin, statt grau zu sein."""
        self.warum_text.setStyleSheet(WARUM_FARBE + " font-weight: bold;")
        if not getattr(self, "_beta_stile", None):  # nicht noch einmal über den Rahmen von eben
            self._beta_stile = [(w, w.styleSheet()) for w in self._warum_ziele()]
            for w, stil in self._beta_stile:
                w.setStyleSheet(stil + " border: 2px solid #d08000;")
        self._beta_betont = getattr(self, "_beta_betont", 0) + 1
        nummer = self._beta_betont

        def zurueck():
            if self.geschlossen or nummer != self._beta_betont:
                return
            self.warum_text.setStyleSheet(WARUM_FARBE)
            for w, stil in self._beta_stile:
                w.setStyleSheet(stil)
            self._beta_stile = []

        QtCore.QTimer.singleShot(BETONT_MS, zurueck)

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

    def _einziges_teil(self):
        """Das Teil des Dokuments, wenn es nur eines gibt: ein Körper mit Volumen, der zu nichts
        anderem gehört (kein Formelement eines Körpers, kein Rohteil oder Klon eines Jobs). Dann
        braucht der Assistent keinen Klick ins Teil, um zu wissen, worum es geht."""
        kandidaten = []
        for objekt in self.doc.Objects:
            if hasattr(objekt, "Operations") or not objekt.isDerivedFrom("Part::Feature"):
                continue
            if objekt.InList:
                continue
            form = getattr(objekt, "Shape", None)
            if form is None or form.isNull() or not form.Solids:
                continue
            kandidaten.append(objekt)
        return kandidaten[0] if len(kandidaten) == 1 else None

    def _mit_einzigem_teil_beginnen(self):
        """Noch kein Job, aber nur ein Teil im Dokument: mit ihm beginnen (der Job entsteht) –
        True, wenn es danach einen Job gibt."""
        if self.job is None:
            teil = self._einziges_teil()
            if teil is not None:
                self._beta_erster_klick_unten = False
                self._beginnen((teil, None), teil)
        return self.job is not None

    def wie_modelliert(self):
        if not self._mit_einzigem_teil_beginnen():
            return
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
            self._farben_neu()
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
        # Gezeigt statt gezählt: Die übrigen Flächen der Tasche stehen blau im Teil
        # (_mit_eigenen_farben), der Satz trägt das Kästchen in derselben Farbe.
        self.tasche_text.setText(
            f"<span style='color: {TASCHE_FARBE};'>■</span> "
            + html.escape(self.tasche_text.text(), quote=False)
        )
        self.tasche_text.setStyleSheet("")
        self.knopf_nur_diese.setVisible(not entschieden)
        self.knopf_tasche_schruppen.setVisible(not entschieden and self._beta_voll)
        self.knopf_ganze_tasche.setVisible(True)
        # Der naheliegende Weg zuerst: voll – ausräumen; leer – nur diese Wände.
        zeile = self._tasche_zeile
        erster = self.knopf_tasche_schruppen if self._beta_voll else self.knopf_nur_diese
        zeile.removeWidget(erster)
        zeile.insertWidget(0, erster)
        self.tasche_box.show()
        self._farben_neu()

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

    def _tasche_masse(self):
        """Die Maße der Tasche, zu der die gewählten Flächen gehören – None ohne Tasche."""
        wahl = frozenset(self.gewaehlte)
        if self._beta_masse is not None and self._beta_masse[0] == wahl:
            return self._beta_masse[1]
        masse = None
        if self.job is not None and self.gewaehlte and not self._ist_stl():
            try:
                form = vr.modell(self.job).Shape
                kennung = form.hashCode()
                if self._beta_nachbarn is None or self._beta_nachbarn[0] != kennung:
                    self._beta_nachbarn = (kennung, tw.nachbarn(form))
                tasche = tw.vertiefung(form, self.gewaehlte, self._beta_nachbarn[1])
                if len(tasche) > 1:  # Boden und Wände: eine Tasche
                    masse = ww.masse(form, tasche)
            except Exception as fehler:  # nie das Fenster sperren
                FreeCAD.Console.PrintLog(f"Beta: Tasche nicht gemessen: {fehler}\n")
        self._beta_masse = (wahl, masse)
        return masse

    def _werkzeuge_zeigen(self):
        """Im Schruppen: je Weg das größte passende eigene Werkzeug; mit „Was gäbe es im
        Katalog?“ dazu größere aus dem Katalog der Hersteller."""
        masse = self._tasche_masse()
        if masse is None or masse.frei <= 0:
            self.werkzeuge_box.hide()
            return
        from . import magazin as mg

        bibliothek = self.bibliothek if self.bibliothek is not None else mg.bibliothek_laden()
        eigene = list(getattr(bibliothek, "werkzeuge", []) or [])
        katalog = ww.katalog_werkzeuge() if self._beta_katalog_an else []
        zeilen = [
            tr(
                "beta.werkzeuge.tasche",
                tiefe=dezimal(f"{masse.tiefe:.1f}"),
                frei=dezimal(f"{masse.frei:.0f}"),
            )
        ]
        for v in ww.vorschlaege(masse, eigene, katalog):
            zeilen.append(_vorschlag_zeile(v))
        self.werkzeuge_text.setText("<br>".join(zeilen))
        self.knopf_katalog.setVisible(not self._beta_katalog_an)
        self.werkzeuge_box.show()

    def im_katalog(self):
        """„Was gäbe es im Katalog?“ – den Katalog einmal lesen: in einem Faden, das Fenster bleibt
        frei (ohne Zwischenspeicher der Werkzeugkiste 7 s, sonst unter 1 s); danach die Vorschläge.
        """
        if ww.katalog_bereit():
            self._beta_katalog_an = True
            self._werkzeuge_zeigen()
            return
        self.knopf_katalog.setEnabled(False)
        self.knopf_katalog.setText(tr("beta.werkzeuge.katalog.liest"))
        ww.katalog_laden_im_hintergrund()

        def nachsehen():
            if self.geschlossen:
                return
            if not ww.katalog_bereit():
                ww.katalog_laden_im_hintergrund()  # nach dem Nebenrechner: jetzt der Faden
                QtCore.QTimer.singleShot(KATALOG_NACHSEHEN_MS, nachsehen)
                return
            self.knopf_katalog.setEnabled(True)
            self.knopf_katalog.setText(tr("beta.werkzeuge.katalog"))
            self._beta_katalog_an = True
            self._werkzeuge_zeigen()

        QtCore.QTimer.singleShot(KATALOG_NACHSEHEN_MS, nachsehen)

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
                stopp = ms.lege_an(self.job, tc, tc, messmerkmal(self.job, davor))
        vorher = {o.Name for o in self.job.Operations.Group} if stopp is not None else set()
        ergebnis = super()._anlegen()
        if stopp is not None and not ergebnis:
            self.job.Document.removeObject(stopp.Name)
        elif stopp is not None:
            self._beta_messstopp = False  # nur einmal
            if getattr(self, "_beta_korrigieren", False):
                # Das Schlichtwerkzeug danach – das erste neue mit Radiuskorrektur.
                neu = [o for o in self.job.Operations.Group if o.Name not in vorher]
                mit = next((o for o in neu if getattr(o, "Radiuskorrektur", False)), None)
                tc = getattr(mit, "ToolController", None)
                if tc is not None:
                    ms.korrektur_setzen(stopp, int(tc.ToolNumber))
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
        self._beta_bis = min(self._aktueller_abschnitt(), KANTEN)  # die Übersicht: alles
        job = self.job
        vorher = {o.Name for o in job.Operations.Group} if job is not None else set()
        try:
            ergebnis = super().accept()
        finally:
            bis, self._beta_bis = self._beta_bis, None
        if ergebnis is not False and job is not None and bis is not None:
            self._am_job_merken(job, bis)
        if ergebnis is not False and _UMSPANNEN:
            QtCore.QTimer.singleShot(500, _umspannen_wenn_frei)
        elif ergebnis is not False and job is not None and fertig_zeigen_an():
            neu = {o.Name for o in job.Operations.Group} - vorher
            if neu:
                _FERTIG.append((job, neu))
                QtCore.QTimer.singleShot(300, _fertig_wenn_frei)
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
            weiter_bearbeiten(
                job,
                frage.abschnitt(),
                frage.messstopp.isChecked(),
                frage.aufmass_wert(),
                frage.korrigieren_wert(),
            )


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
        self.setMinimumWidth(460)  # sonst schneiden die umbrochenen Sätze unten ab
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
        # Das Aufmaß dieses Gangs (Manuel, 2026-10-31: „3 mm aufmass beim schruppen … schlichten auf
        # 2mm … nochmal … auf 1 mm“): vorgeschlagen AUFMASS_STUFE weniger als beim Gang davor.
        zeile = QtGui.QHBoxLayout()
        self.aufmass_beschriftung = QtGui.QLabel(tr("beta.weiter.aufmass.feld"))
        zeile.addWidget(self.aufmass_beschriftung)
        self.aufmass = QtGui.QLineEdit(
            groesse_zeigen(aufmass_vorschlag(job), einheiten.LAENGE) or "0"
        )
        self.aufmass.setValidator(Zahlenpruefer(self.aufmass))
        self.aufmass.setToolTip(tr("beta.weiter.aufmass.tooltip"))
        self.aufmass.setMaximumWidth(80)
        zeile.addWidget(self.aufmass)
        zeile.addWidget(QtGui.QLabel(einheiten.einheit(einheiten.LAENGE)))
        zeile.addStretch()
        aufbau.addLayout(zeile)
        hinweis = _grau(tr("beta.weiter.aufmass"))
        hinweis.setWordWrap(True)
        aufbau.addWidget(hinweis)
        for knopf_ in self.wahl.values():
            knopf_.toggled.connect(self._aufmass_zeigen)
        self._aufmass_zeigen()
        self.messstopp = QtGui.QCheckBox(tr("beta.weiter.messstopp"))
        self.messstopp.setToolTip(tr("beta.weiter.messstopp.tooltip"))
        self.messstopp.setChecked(bool(list(job.Operations.Group)))
        aufbau.addWidget(self.messstopp)
        self._messen_bauen(aufbau, job)
        knoepfe = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        knoepfe.button(QtGui.QDialogButtonBox.Ok).setText(tr("beta.weiter.los"))
        knoepfe.accepted.connect(self.accept)
        knoepfe.rejected.connect(self.reject)
        aufbau.addWidget(knoepfe)

    def _aufmass_zeigen(self, *_):
        an = self.abschnitt() in (SCHRUPPEN, SCHLICHTEN)
        self.aufmass.setVisible(an)
        self.aufmass_beschriftung.setVisible(an)

    def aufmass_wert(self):
        """Das Aufmaß dieses Gangs (mm) – None, wenn der Schritt keins hat oder das Feld leer ist."""
        if self.abschnitt() not in (SCHRUPPEN, SCHLICHTEN) or not self.aufmass.text().strip():
            return None
        try:
            return max(0.0, groesse_lesen(self.aufmass.text(), einheiten.LAENGE))
        except ValueError:
            return None

    def _messen_bauen(self, aufbau, job):
        """Unter „Messstopp davor“: was dort gemessen wird – mit Taster und Zyklus der Steuerung
        des Jobs, sonst warum es hält –, dazu die T-Nummer des Tasters zum Eintragen (an der
        Steuerung gemerkt, wie im Fenster „Programm schreiben“)."""
        from . import gui_programm as gp
        from . import postprozessor as pp

        self.merkmal = messmerkmal(job)
        self._kennung = gp.steuerung_des_jobs(job)
        s = pp.steuerung(self._kennung, gp.gespeicherte_aenderungen(self._kennung))
        self._zyklus = bool(self.merkmal is not None and getattr(s, f"messen_{self.merkmal.art}"))
        self.messen_text = _grau()
        self.messen_text.setWordWrap(True)
        self.messen_text.setContentsMargins(22, 0, 0, 0)
        aufbau.addWidget(self.messen_text)
        zeile = QtGui.QHBoxLayout()
        zeile.setContentsMargins(22, 0, 0, 0)
        self.taster_beschriftung = QtGui.QLabel(tr("beta.weiter.messen.taster"))
        zeile.addWidget(self.taster_beschriftung)
        self.taster = QtGui.QLineEdit(s.taster)
        self.taster.setValidator(QtGui.QIntValidator(0, 99999, self.taster))
        self.taster.setToolTip(tr("beta.weiter.messen.taster.tooltip"))
        self.taster.setMaximumWidth(80)
        self.taster.textChanged.connect(self._messen_zeigen)
        zeile.addWidget(self.taster)
        zeile.addStretch()
        aufbau.addLayout(zeile)
        # Manuel, 2026-10-31: „ja mach das so“ – der Messzyklus trägt die Abweichung selbst als
        # Radius-Verschleiß des Schlichtfräsers ein (vorbelegt an, wie Neues sonst auch).
        self.korrigieren = QtGui.QCheckBox(tr("beta.weiter.korrigieren"))
        self.korrigieren.setToolTip(tr("beta.weiter.korrigieren.tooltip"))
        self.korrigieren.setChecked(True)
        self.korrigieren.setContentsMargins(22, 0, 0, 0)
        self.korrigieren.toggled.connect(self._messen_zeigen)
        aufbau.addWidget(self.korrigieren)
        self._steuerung_name = s.name
        self.messstopp.toggled.connect(self._messen_zeigen)
        self._messen_zeigen()

    def _messen_zeigen(self, *_):
        an = self.messstopp.isChecked()
        mit_zyklus = an and self._zyklus
        self.taster.setVisible(mit_zyklus)
        self.taster_beschriftung.setVisible(mit_zyklus)
        self.korrigieren.setVisible(mit_zyklus and bool(self.taster.text().strip()))
        if not an:
            self.messen_text.setText("")
        elif self.merkmal is None:
            self.messen_text.setText(tr("beta.weiter.messen.keins"))
        elif not self._zyklus:
            self.messen_text.setText(
                tr(
                    "beta.weiter.messen.kein_zyklus",
                    was=_merkmal_text(self.merkmal),
                    steuerung=self._steuerung_name,
                )
            )
        elif self.taster.text().strip():
            werte = {"was": _merkmal_text(self.merkmal), "t": self.taster.text().strip()}
            if self.korrigieren.isChecked():
                self.messen_text.setText(tr("beta.weiter.messen.mit_korrektur", **werte))
            else:
                self.messen_text.setText(tr("beta.weiter.messen.mit", **werte))
        else:
            self.messen_text.setText(
                tr("beta.weiter.messen.ohne_taster", was=_merkmal_text(self.merkmal))
            )
        self.messen_text.setVisible(an)
        self.adjustSize()

    def korrigieren_wert(self):
        """Soll der Messzyklus den Schlichtfräser korrigieren? (nur mit Taster und Zyklus)"""
        return bool(
            self.messstopp.isChecked()
            and self._zyklus
            and self.taster.text().strip()
            and self.korrigieren.isChecked()
        )

    def taster_merken(self):
        """Die T-Nummer an der Steuerung des Jobs merken (gui_programm.gespeicherte_aenderungen)."""
        from . import gui_programm as gp

        if not self._zyklus:
            return
        aenderungen = dict(gp.gespeicherte_aenderungen(self._kennung))
        neu = self.taster.text().strip()
        if aenderungen.get("taster", "") != neu:
            aenderungen["taster"] = neu
            gp.aenderungen_merken(self._kennung, aenderungen)

    def abschnitt(self):
        return next((a for a, k in self.wahl.items() if k.isChecked()), SCHLICHTEN)

    def done(self, ergebnis):
        if ergebnis == QtGui.QDialog.Accepted:
            self.taster_merken()
        WeiterFrage.offen = None
        super().done(ergebnis)


def _werkzeug_text(w):
    """„Gühring 5510 32,000 (Bohrer Ø 32)“ mit Link, wenn es einen gibt."""
    from . import werkzeuge as wz

    text = dezimal(wz.kurz(w))
    if getattr(w, "name", ""):  # der Name aus dem Katalog: Reihe und Größe, Artikel
        text = f"{w.name} ({text})"
    text = html.escape(text)
    hersteller = getattr(w, "hersteller", "")
    if hersteller and hersteller.split()[0].lower() not in text.lower():
        text = f"{html.escape(hersteller)} {text}"
    if getattr(w, "link", ""):
        text = f'<a href="{html.escape(w.link)}">{text}</a>'
    return text


def _vorschlag_zeile(v):
    """Eine Zeile je Weg: „Vorbohren (bis Ø 38): deiner T3 Bohrer Ø 20 · im Katalog: …“."""
    weg = {
        "vorbohren": tr("beta.werkzeuge.vorbohren"),
        "schruppen": tr("beta.werkzeuge.schruppen"),
        "ecken": tr("beta.werkzeuge.ecken"),
        "bohrfraesen": tr("beta.werkzeuge.bohrfraesen"),
        "tauchfraesen": tr("beta.werkzeuge.tauchfraesen"),
    }[v.weg]
    teile = []
    if v.eigenes is not None:
        nummer = getattr(v.eigenes, "nummer", 0)
        name = _werkzeug_text(v.eigenes)
        teile.append(tr("beta.werkzeuge.eigenes", name=f"T{nummer} {name}" if nummer else name))
    elif v.weg not in ("bohrfraesen", "tauchfraesen"):
        teile.append(tr("beta.werkzeuge.keins"))
    if v.katalog:
        teile.append(
            tr("beta.werkzeuge.aus_katalog", namen=", ".join(_werkzeug_text(w) for w in v.katalog))
        )
    grenze = dezimal(f"{v.grenze:.0f}")
    return f"<b>{weg}</b> ({tr('beta.werkzeuge.bis', d=grenze)}): " + " · ".join(teile)


def messmerkmal(job, davor=None):
    """Was ein Taster am Messstopp messen würde (messen.merkmal, Plan C3b): das Merkmal der am Job
    gemerkten Flächen, mit dem Aufmaß der Operation `davor` (ohne: die letzte mit Werkzeug) – None,
    wenn sie keins ergeben."""
    from . import messen

    flaechen = list(getattr(job, EIGENSCHAFT_FLAECHEN, []))
    if not flaechen:
        return None
    if davor is None:
        ops = list(job.Operations.Group)
        davor = next((op for op in reversed(ops) if getattr(op, "ToolController", None)), None)
    try:
        m = messen.merkmal(vr.modell(job).Shape, flaechen)
    except Exception:  # Part.OCCError: ein Name passt nicht mehr zum Modell
        return None
    if m is None:
        return None
    aufmass = getattr(davor, "Aufmass", 0.0)
    return messen.soll(m, float(getattr(aufmass, "Value", aufmass) or 0.0))


def _merkmal_text(m):
    """„Tasche 59,4 × 39,4 mm“, „Bohrung Ø 18 mm“ (messen.text)."""
    from . import messen

    return messen.text(m)


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


def aufmass_vorschlag(job):
    """Das Aufmaß für den nächsten Gang: das der letzten Operation mit Werkzeug (ihre Eigenschaft
    „Aufmass“) weniger AUFMASS_STUFE, nicht unter 0."""
    ops = list(job.Operations.Group)
    davor = next((op for op in reversed(ops) if getattr(op, "ToolController", None)), None)
    aufmass = getattr(davor, "Aufmass", 0.0)
    aufmass = float(getattr(aufmass, "Value", aufmass) or 0.0)
    return max(0.0, round(aufmass - AUFMASS_STUFE, 3))


def aufmass_setzen(panel, ab, aufmass):
    """Trägt `aufmass` bei den Strategien des Abschnitts `ab` ein, die ein Feld „aufmass“ haben,
    und rechnet die Vorschau neu."""
    for block in panel.bloecke:
        if abschnitt(block) == ab and "aufmass" in block.felder:
            block.felder["aufmass"].setText(groesse_zeigen(aufmass, einheiten.LAENGE) or "0")
    panel.vorschau_starten()


def weiter_bearbeiten(job, ab, messstopp=False, aufmass=None, korrigieren=False):
    """Öffnet die Beta am Job `job` beim Abschnitt `ab` – mit den gemerkten Flächen; `messstopp`:
    vor den neuen Operationen ein Messstopp (messstopp.py); `aufmass` (mm): das Aufmaß dieses Gangs
    für die Strategien des Abschnitts; `korrigieren`: der Messzyklus korrigiert den Schlichtfräser
    – dafür schlichten die Strategien mit Radiuskorrektur (Haken „korrektur“)."""
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
    panel._beta_korrigieren = bool(messstopp and korrigieren)
    if panel._beta_korrigieren:
        for block in panel.bloecke:
            if abschnitt(block) == ab and "korrektur" in block.haken_felder:
                block.haken_felder["korrektur"].setChecked(True)
    if aufmass is not None:
        aufmass_setzen(panel, ab, aufmass)
    FreeCADGui.Control.showDialog(panel)
    return panel


def fertig_zeigen_an():
    return FreeCAD.ParamGet(PARAMETER_PFAD).GetBool(FERTIG_ZEIGEN, True)


_FERTIG = []  # (Job, neue Operationen) – das Fenster „Angelegt“, sobald die Kette durch ist
RUHIG_TAKTE = 3  # so oft hintereinander frei (je 500 ms), dann kommt das Fenster „Angelegt“


def _fertig_wenn_frei(ruhig=0):
    """Das Fenster „Angelegt“ erst, wenn kein Assistent mehr offen ist und keine Ebene der Kette
    mehr kommt (Manuel, 2026-11-08, an der G550: „ich hab auf maschine prüfen gedrückt geendet bin
    ich hier bei der nächsten aufspannung oder was soll das nun sein ??“ – das Fenster kam mit der
    Ebene „von oben“ zugleich). Die nächste Ebene öffnet sich mit einer Verzögerung: Erst nach
    RUHIG_TAKTE freien Takten hintereinander gilt die Kette als durch. Dann je Job ein Fenster."""
    from .gui_bearbeitung import _FOLGE

    if not _FERTIG:
        return
    if FreeCADGui.Control.activeDialog() or _FOLGE:
        QtCore.QTimer.singleShot(500, _fertig_wenn_frei)
        return
    if ruhig < RUHIG_TAKTE:
        QtCore.QTimer.singleShot(500, lambda: _fertig_wenn_frei(ruhig + 1))
        return
    offen = list(_FERTIG)
    _FERTIG.clear()
    for job, neu in offen:
        _fertig_oeffnen(job, neu)


def _fertig_oeffnen(job, neu):
    try:
        job.Operations  # noqa: B018 – der Job ist noch da (das Dokument nicht geschlossen)
    except (ReferenceError, RuntimeError):
        return
    fenster = FertigFenster(FreeCADGui.getMainWindow(), job, neu)
    fenster.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    fenster.show()


def _knapp_liste(job):
    """(Werkzeugverwaltung, [(Nummer, Werkzeug, heraus, tiefe, [Operationen])]) – je Werkzeug des
    Jobs, das tiefer fräst, als es heraussteht (postprozessor.knapp_tiefe, wie der Kopf des
    Programms warnt): wie weit es heraussteht, die größte Tiefe und die Operationen. Mit dem
    Magazin der Maschine (dort gilt, wie weit es an seinem Platz herausschaut). Leer, wenn alles
    reicht oder es sich nicht lesen lässt."""
    from . import job_schnittwerte as js
    from . import magazin as mg
    from . import postprozessor as pp
    from . import schwenken as sw
    from . import werkzeuge as wz

    je_werkzeug = {}
    bibliothek = None
    try:
        bibliothek = wz.Bibliothek.laden()
        mg.des_jobs(rw.grundjob_von(job), bibliothek)
        geschwenkt = sw.ist_ebene(job)
        merk = {}
        for op in job.Operations.Group:
            tc = getattr(op, "ToolController", None)
            nummer = int(getattr(tc, "ToolNumber", 0) or 0) if tc is not None else 0
            if not nummer:
                continue
            name = getattr(tc, "Name", "")
            if name not in merk:
                merk[name] = pp._einspannung_des_controllers(tc, bibliothek)
            _name, einspannung, heraus, _masse = merk[name]
            if not einspannung:
                continue
            tiefe = pp.knapp_tiefe(job, op, heraus, geschwenkt)
            if tiefe is None:
                continue
            eintrag = je_werkzeug.setdefault(
                nummer, [nummer, js.werkzeug_von(tc, bibliothek), heraus, 0.0, []]
            )
            eintrag[3] = max(eintrag[3], tiefe)
            eintrag[4].append(op)
    except Exception as fehler:  # noqa: BLE001 – die Warnung darf das Fenster nicht verhindern
        FreeCAD.Console.PrintLog(f"Angelegt: Auskragung nicht geprüft: {fehler}\n")
    return bibliothek, [tuple(e) for e in je_werkzeug.values()]


VERWEIS_BLOCK = "block|"  # in der Übersicht: „block|<Kennung>|<Verweis der Strategie>“
ZEIGE = "zeige|"  # Verweis einer Zeile der Übersicht: nur ihre Wege im Teil
# Zeigen statt beschreiben (Manuel, 2026-11-11: „gibts vll einfach ne andere möglichkeit das gesagte
# … zu zeigen“): Was der Satz mit „Face1, Face2, Face4“ sagte, steht als Farbe im Teil.
UNFERTIG_FARBE = "#f08c00"  # hat am Ende keine genaue Bahn
REST_FARBE = "#8e44ad"  # geht in dieser Aufspannung von oben nicht
TASCHE_FARBE = "#2f9be0"  # gehört zur Tasche der Auswahl, ist aber nicht gewählt
BLASS = "#909090"
WARN_ROT = "#c03030"
BALKEN_FARBE = "#3584e4"  # der Zeitbalken einer angehakten Strategie


def _verweise_fuer(kennung, text):
    """Der Satz einer Strategie für die Übersicht: seine Verweise führen über die Übersicht zu
    ihr zurück (BetaPanel._uebersicht_verweis)."""
    import re

    return re.sub(
        r'href="([^"]+)"', lambda m: f'href="{VERWEIS_BLOCK}{kennung}|{m.group(1)}"', text or ""
    )


def _ohne_marken(text):
    """Ein Satz der Oberfläche ohne seine HTML-Marken (Verweise, Farben) – für die Übersicht."""
    import re

    return html.unescape(re.sub(r"<[^>]+>", " ", text or "")).strip()


def _zehntel(minuten):
    """„1,4“ – und „< 0,1“ für alles, was auf 0,0 rundete: „Restmaterial (T3, 0,0 min)“ las sich,
    als gäbe es dort nichts zu tun."""
    if 0.0 < minuten < 0.05:
        return dezimal("< 0.1")
    return dezimal(f"{minuten:.1f}")


def _minuten_text(minuten):
    """„0,3 min“, „< 0,1 min“, „12 min“, „2 h 05 min“."""
    if minuten < 10:
        return tr("va.zeit.min", min=_zehntel(minuten))
    gesamt = int(round(minuten))
    if gesamt < 60:
        return tr("va.zeit.min", min=gesamt)
    return tr("va.zeit.h", h=gesamt // 60, min=f"{gesamt % 60:02d}")


class FertigFenster(QtGui.QDialog):
    """Nach „Anlegen“ (Konzept B6, Schritt „Prüfen“): was jetzt im Job steht – je Operation ihre
    Zeit (einrichtblatt.minuten), die eben angelegten fett –, zusammen, und die nächsten Schritte
    als Knöpfe (Gedächtnis „Nächster Schritt als Knopf“): „Auf der Maschine prüfen“, „Programm
    schreiben“, „Einrichtblatt“, „Weiter bearbeiten“. Die Zeiten rechnet es eine Operation je
    Uhrtakt – bei großen 3D-Bahnen bleibt das Fenster bedienbar. Ändert nichts am Job."""

    offen = None  # für die Oberflächen-Szenarien

    def __init__(self, eltern, job, neu=()):
        super().__init__(eltern)
        from . import maschinenspeicher as msp

        FertigFenster.offen = self
        self.job = job
        self.setWindowTitle(tr("beta.fertig.titel"))
        self.setMinimumWidth(480)
        aufbau = QtGui.QVBoxLayout(self)
        kopf = QtGui.QLabel(tr("beta.fertig.kopf", job=job.Label, n=len(neu)))
        kopf.setWordWrap(True)
        aufbau.addWidget(kopf)
        self.liste = QtGui.QTreeWidget()
        self.liste.setRootIsDecorated(False)
        self.liste.setHeaderLabels([tr("beta.fertig.operation"), tr("beta.fertig.zeit")])
        self._zeilen = []
        for op, _ebene in rw.operationen_mit_ebene(job):
            zeile = QtGui.QTreeWidgetItem([op.Label, tr("ba.frage.rechnet")])
            zeile.setTextAlignment(1, QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            if op.Name in neu:
                schrift = zeile.font(0)
                schrift.setBold(True)
                zeile.setFont(0, schrift)
            self.liste.addTopLevelItem(zeile)
            self._zeilen.append((op, zeile))
        self.liste.resizeColumnToContents(1)
        self.liste.header().setStretchLastSection(False)
        self.liste.header().setSectionResizeMode(0, QtGui.QHeaderView.Stretch)
        # So hoch wie die Operationen (höchstens FERTIG_ZEILEN), nicht ein leeres Feld darunter.
        hoehe = self.liste.sizeHintForRow(0) if self._zeilen else 18
        self.liste.setFixedHeight(
            self.liste.header().sizeHint().height()
            + hoehe * min(max(len(self._zeilen), 1), FERTIG_ZEILEN)
            + 2 * self.liste.frameWidth()
            + 2
        )
        aufbau.addWidget(self.liste)
        self.summe = _grau(tr("ba.frage.rechnet"))
        aufbau.addWidget(self.summe)
        # Was der Kopf des Programms als „ACHTUNG – knapp“ schriebe, steht schon hier, bevor
        # jemand das Programm schreibt – und zwar gezeigt: die Zeilen der Operationen rot, je
        # Werkzeug ein Satz mit dem Knopf, der es behebt („T3 auf 35 mm ausspannen“).
        self.warnung = QtGui.QLabel()  # der Text aller Sätze – für die Szenarien
        self.warnung.hide()
        self.knapp_box = QtGui.QWidget()
        QtGui.QVBoxLayout(self.knapp_box).setContentsMargins(0, 0, 0, 0)
        aufbau.addWidget(self.knapp_box)
        self.knapp_knoepfe = []
        self._knapp_zeigen()
        zeile = QtGui.QHBoxLayout()
        self.knopf_pruefen = knopf(
            tr("beta.fertig.pruefen"),
            tr("beta.fertig.pruefen.tooltip"),
            lambda: self._befehl("CamAddon_AufMaschinePruefen"),
        )
        self.knopf_programm = knopf(
            tr("beta.fertig.programm"),
            tr("beta.fertig.programm.tooltip"),
            lambda: self._befehl("CamAddon_ProgrammSchreiben"),
        )
        self.knopf_blatt = knopf(
            tr("beta.fertig.blatt"),
            tr("beta.fertig.blatt.tooltip"),
            lambda: self._befehl("CamAddon_Einrichtblatt"),
        )
        self.knopf_weiter = knopf(
            tr("befehl.beta.weiter.titel"),
            tr("beta.fertig.weiter.tooltip"),
            lambda: self._befehl("CamAddon_WeiterBearbeitenBeta"),
        )
        self.knopf_weiter.setVisible(
            hasattr(job, EIGENSCHAFT_FLAECHEN) and naechster_abschnitt(job) is not None
        )
        # Der Knopf zum Ziel fällt auf (wie „Alles vorschlagen →“): Wer nicht liest, findet
        # „Programm schreiben …“.
        schrift = self.knopf_programm.font()
        schrift.setBold(True)
        self.knopf_programm.setFont(schrift)
        for k in (self.knopf_pruefen, self.knopf_programm, self.knopf_blatt, self.knopf_weiter):
            zeile.addWidget(k)
        zeile.addStretch()
        aufbau.addLayout(zeile)
        unten = QtGui.QHBoxLayout()
        self.haken_zeigen = QtGui.QCheckBox(tr("beta.fertig.zeigen"))
        self.haken_zeigen.setToolTip(tr("beta.fertig.zeigen.tooltip"))
        self.haken_zeigen.setChecked(fertig_zeigen_an())
        self.haken_zeigen.toggled.connect(
            lambda an: FreeCAD.ParamGet(PARAMETER_PFAD).SetBool(FERTIG_ZEIGEN, bool(an))
        )
        unten.addWidget(self.haken_zeigen)
        unten.addStretch()
        unten.addWidget(knopf(tr("kg.schliessen"), "", self.accept))
        aufbau.addLayout(unten)
        self._dynamik = msp.dynamik_des_jobs(rw.grundjob_von(job))
        # Die Werkzeugwechsel der Folge, mit der Wechselzeit der Maschine (wie die Fragen, W-040).
        from . import magazin as mg

        pfad = mg.maschine_von(rw.grundjob_von(job))
        eintrag = msp.finde(msp.laden(), pfad) if pfad else None
        nummern = [
            int(getattr(op.ToolController, "ToolNumber", 0))
            for op, _zeile in self._zeilen
            if getattr(op, "ToolController", None) is not None
        ]
        self.wechsel = sum(1 for a, b in zip(nummern, nummern[1:], strict=False) if a != b) + bool(
            nummern
        )
        self._wechsel_minuten = self.wechsel * msp.wechselzeit_von(eintrag) / 60.0
        self._offen = list(self._zeilen)
        self.minuten = 0.0
        self.fertig = False
        QtCore.QTimer.singleShot(0, self._naechste)

    def _naechste(self):
        """Die Zeit der nächsten Operation – eine je Uhrtakt."""
        from . import einrichtblatt as eb

        if FertigFenster.offen is not self or not self._offen:
            return
        op, zeile = self._offen.pop(0)
        tc = getattr(op, "ToolController", None)
        try:
            minuten = eb.minuten(op, tc) if tc is not None else 0.0
        except Exception:  # noqa: BLE001 – dann ohne Zeit, wie im Einrichtblatt
            minuten = 0.0
        zeile.setText(1, _minuten_text(minuten) if minuten > 0 else "–")
        self.minuten += minuten
        if self._offen:
            QtCore.QTimer.singleShot(0, self._naechste)
            return
        self.liste.resizeColumnToContents(1)
        zeit = _minuten_text(self.minuten + self._wechsel_minuten)
        if self.wechsel == 1:
            self.summe.setText(tr("beta.fertig.summe.eins", zeit=zeit))
        else:
            self.summe.setText(tr("beta.fertig.summe", zeit=zeit, wechsel=self.wechsel))
        self.fertig = True

    def _knapp_zeigen(self):
        """Je Werkzeug, das zu kurz heraussteht: seine Operationen rot in der Liste, darunter ein
        Satz und der Knopf „T… auf … mm ausspannen“ – er trägt es in die Werkzeugverwaltung (am
        Platz im Magazin) ein, die Warnung ist weg, und Einrichtblatt und Programmkopf nennen das
        neue Maß. Ist das Werkzeug dafür zu kurz, sagt es der Satz."""
        from . import postprozessor as pp

        box = self.knapp_box.layout()
        while box.count():
            altes = box.takeAt(0).widget()
            if altes is not None:
                altes.deleteLater()
        self.knapp_knoepfe = []
        normal = QtGui.QTreeWidgetItem().foreground(0)
        for _op, zeile in self._zeilen:
            zeile.setForeground(0, normal)
            zeile.setToolTip(0, "")
        bibliothek, liste = _knapp_liste(self.job)
        saetze = []
        for nummer, werkzeug, heraus, tiefe, operationen in liste:
            satz = tr(
                "beta.fertig.knapp.satz",
                t=nummer,
                heraus=dezimal(f"{heraus:.0f}"),
                tiefe=dezimal(f"{tiefe:.1f}"),
            )
            for op, zeile in self._zeilen:
                if op in operationen:
                    zeile.setForeground(0, QtGui.QBrush(QtGui.QColor(WARN_ROT)))
                    zeile.setToolTip(0, satz)
            reihe = QtGui.QWidget()
            aufbau = QtGui.QHBoxLayout(reihe)
            aufbau.setContentsMargins(0, 0, 0, 0)
            ziel = None
            if werkzeug is not None and bibliothek is not None:
                ziel = rw.ausspannen_auf(werkzeug, bibliothek, heraus, tiefe + pp.SPIEL_KNAPP)
            if ziel is None:
                satz += " " + tr("beta.fertig.knapp.zu_kurz")
            etikett = QtGui.QLabel("⚠ " + satz)
            etikett.setWordWrap(True)
            etikett.setStyleSheet(f"color: {WARN_ROT};")
            etikett.setToolTip(tr("beta.fertig.knapp.rat"))
            aufbau.addWidget(etikett, 1)
            if ziel is not None:
                weit, laenge = ziel
                taste = knopf(
                    tr("beta.fertig.ausspannen", t=nummer, mm=dezimal(f"{weit:.0f}")),
                    tr("beta.fertig.ausspannen.tooltip"),
                    lambda w=werkzeug, n=laenge, h=weit, b=bibliothek: self._ausspannen(w, n, h, b),
                )
                aufbau.addWidget(taste)
                self.knapp_knoepfe.append(taste)
            box.addWidget(reihe)
            saetze.append(satz)
        self.warnung.setText("\n".join(saetze))
        self.knapp_box.setVisible(bool(liste))

    def _ausspannen(self, werkzeug, laenge, heraus, bibliothek):
        rw.ausspannen_setzen(werkzeug, laenge, heraus, bibliothek)
        bibliothek.speichern()
        self._knapp_zeigen()

    def _befehl(self, name):
        """Den Job wählen und den Befehl starten – das Fenster geht zu."""
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(self.job.Document.Name, self.job.Name)
        self.accept()
        FreeCADGui.runCommand(name)

    def done(self, ergebnis):
        FertigFenster.offen = None
        super().done(ergebnis)


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
# Die Schritte sind seit 0.350.0 der Assistent „Bearbeitung“; „Weiter bearbeiten“ und „Neue
# Aufspannung“ stehen in der gewohnten Leiste. Hier kommt, was wieder neu zum Ausprobieren ist.
WERKZEUGLEISTE = []


def leiste_anhaengen(arbeitsbereich):
    """Hängt die Beta-Leiste und das Menü „Beta“ an, wenn die Beta an ist – nimmt sie weg, wenn
    nicht. True, wenn sich etwas geändert hat."""
    neu = False
    an = beta_an() and bool(WERKZEUGLEISTE)
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
