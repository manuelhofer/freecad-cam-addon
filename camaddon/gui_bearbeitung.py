# SPDX-License-Identifier: LGPL-2.1-or-later
"""Befehl und Assistent „Bearbeitung (Fräsen)“ für ein Teil im Quader (W-006 S3c, E4).

Der Weg: eine Fläche des Teils anklicken – der Job mit dem Rohteil (ein Quader mit Aufmaß je
Seite, wie FreeCADs Job) entsteht sofort –, die Flächen (ebene nach oben fürs Planfräsen,
ohne Wahl die Oberseite; Wände für die Kontur), Werkstoff, dann je Bearbeitung ein Block mit
Haken: Fräser und Einsatz aus der Werkzeugverwaltung, die Werte mit den Vorschlägen grau,
darunter „→ 3 Lagen, 30 Zeilen, etwa 2 min“ – und „Anlegen“ legt Werkzeug-Controller und die
angehakten Operationen an („Planfräsen“, planfraesen; „Kontur“, kontur). Ein Doppelklick auf
eine Operation öffnet den Assistenten zum Ändern mit ihrem Block (gui_vierachs_operation).

Der Assistent „4-Achs-Bearbeitung“ (gui_vierachs) ist das Vorbild; was dort allgemein ist
(Reihen, Befehl mit Transaktion, Zeit in Worten), kommt von dort. Jede Strategie ist eine
_Strategie (was sie braucht, wie sie rechnet), ihr Block im Fenster ein _Block; weitere
(Tasche adaptiv, Bohren) kommen so dazu (S3f, S3g).
"""

import contextlib
import dataclasses
import functools
import html
import math
import os
import traceback
import types
from collections import OrderedDict

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import PARAMETER_PFAD, einheiten, gui_zeigen, spannung, stl_anzeige, symbol, uhren
from . import aufloesung as au
from . import bahn as bn
from . import bleistift as bst
from . import bohren as bh
from . import bohrung as bo
from . import bohrung_bahn as bb
from . import entgrat_bahn as eb
from . import entgraten as eg
from . import entgraten3d as e3op
from . import fase as fa
from . import fase_bahn as fb
from . import flanke as flop
from . import flanke_bahn as flb
from . import formteile as ft
from . import fraeserform as ff
from . import gewinde as gw
from . import gewinde_bahn as gfb
from . import gewindefraesen as gf
from . import gleiche_flaechen as glf
from . import hinterschnitt_bahn as hsb
from . import hoehenfeld as hf
from . import job_schnittwerte as js
from . import kontur as ko
from . import kontur_bahn as kb
from . import magazin as mg
from . import maschinenspeicher as msp
from . import materialstand as mst
from . import messstopp as ms
from . import nut as nu
from . import nut_bahn as nb
from . import planfraesen as pf
from . import planfraesen_bahn as pfb
from . import postprozessor as pp
from . import raeumen as ra
from . import raeumen_bahn as rb
from . import reiben as rbn
from . import reichweite as rw
from . import schlichten3d as s3op
from . import schlichten3d_bahn as s3b
from . import schruppen3d as r3op
from . import schruppen3d_bahn as r3b
from . import senken as sk
from . import uebergabe_werkzeuge as ue
from . import vierachs_bahn as vb
from . import vierachs_huelle as vh
from . import vierachs_plan as vplan
from . import vierachs_planbahn as vp
from . import vierachs_rohteil as vr
from . import werkzeuge as wz
from . import werkzeugform as wf
from . import zielzeit as zz
from . import zugang as zg
from .gui_hilfe import dialog_schliessen, kopfzeile
from .gui_kollision import GELB
from .gui_maschine import _EnterBleibtImDialog
from .gui_teile import ROT, knopf, mit_einheit, ruhiges_mausrad
from .gui_vierachs import (
    GRAU_TEXT,
    GRUEN,
    _entlang,
    _fehler_im_modell,
    _globale_transaktionen,
    _im_befehl,
    _Reihen,
    _zeit_text,
    gewaehlte_flaeche,
    job_von,
)
from .gui_zahlen import (
    Zahlenpruefer,
    dezimal,
    groesse_fest,
    groesse_lesen,
    groesse_zeigen,
    zahl_zeigen,
)
from .sprache import tr

AUFMASS_ROHTEIL = 1.0  # mm je Seite, wie FreeCADs Job
# Auf diesen Maschinen dreht eine Rundachse das Teil: Das Rohteil ist eine Stange (W-011 S3).
STANGE_ARTEN = (msp.DREHMASCHINE, msp.FRAESE_4)
GEMERKT_FRAESER = "BaFraeser"  # Kennung des zuletzt gewählten Fräsers (Planfräsen)
GEMERKT_KONTURFRAESER = "BaKonturFraeser"  # … für die Kontur
GEMERKT_RAEUMFRAESER = "BaRaeumFraeser"  # … fürs Räumen
GEMERKT_RESTRAEUMFRAESER = "BaRestRaeumFraeser"  # … fürs Rest räumen
GEMERKT_SCHLICHTFRAESER = "BaSchlichtFraeser"  # … fürs Schlichten danach
GEMERKT_NUTFRAESER = "BaNutFraeser"  # … für die Nut
GEMERKT_BOHRFRAESER = "BaBohrFraeser"  # … fürs Bohrungsfräsen
GEMERKT_BOHRER = "BaBohrer"  # … fürs Bohren
GEMERKT_FLANKENFRAESER = "BaFlankenFraeser"  # … für die Flanke (5 Achsen simultan)
GEMERKT_REIBAHLE = "BaReibahle"  # … fürs Reiben
GEMERKT_GEWINDEBOHRER = "BaGewindebohrer"  # … fürs Gewinde
GEMERKT_GEWINDEFRAESER = "BaGewindefraeser"  # … fürs Gewindefräsen
GEMERKT_FASENFRAESER = "BaFasenfraeser"  # … fürs Entgraten
GEMERKT_FASE = "BaFase"  # … für die Fase (W-037)
GEMERKT_ENTGRATEN3D = "BaEntgraten3D"  # … fürs Entgraten 3D
GEMERKT_ANBOHRER = "BaAnbohrer"  # … fürs Zentrieren
GEMERKT_SENKER = "BaSenker"  # … fürs Senken
GEMERKT_RESTFRAESER = "BaRestFraeser"  # … fürs Restmaterial
GEMERKT_FRAESER_3D = "BaFraeser3D"  # … fürs 3D-Schlichten
GEMERKT_RESTFRAESER_3D = "BaRestFraeser3D"  # … fürs Restschlichten
GEMERKT_RESTSCHRUPPFRAESER = "BaRestSchruppFraeser"  # … fürs Restschruppen
# Der zuletzt gewählte Nullpunkt: „modell“ oder „sx,sy,sz“ (nullpunkte()); ohne Eintrag die
# Mitte oben des Rohteils (Manuel, 2026-10-02: „als Auswahl für den Nullpunkt ist Standard
# erstmal oben mittig bitte ausgewählt“).
GEMERKT_NULLPUNKT = "BaNullpunkt"
NULLPUNKT_VORGABE = (0, 0, 1)
# Passt der Fräser des Planfräsens oder Räumens in eine gewählte ebene Fläche (eine Nut enger als
# er)? Erreicht er weniger als ZU_ENG von ihr, kommt er nicht hinein; der Ersatz muss PASST
# erreichen, mit PASST_SPIEL mm Luft je Seite (Manuel, 2026-10-16: Ø 12 in 10 mm breiten Nuten).
ZU_ENG = 0.5
PASST = 0.9
PASST_SPIEL = 0.5
REST_BREITE = 0.01  # mm – „Material neben der Wand“ beim Restmaterial: eine Bahn bei Radius
VORSCHAU_MS = 400  # nach der letzten Eingabe so lange warten, dann die Bahn rechnen
UHR_SCHRITT_MS = 30  # ein Schritt der Vorschau mitten in einer Rechnung: so viel später
NACHZIEHEN_MS = 250  # das Rohteil nach einer Eingabe nachziehen
VORSCHAU_MERK = 60  # so viele Vorschauen merkt sich der Assistent (_Block.vorschau_rechnen)
GENAU_JE_BLOCK = 4  # so viele genaue Bahnen des Räumens rechnen je Block vorab (_genau_starten)
ROHTEIL_FELDER = ("oben", "seite", "unten")
# Quader mit Maßen (W-028; Manuel, 2026-10-18: „wo ich einfach die werte des rohteils reinpacke …
# unterm nullpunkt is das teil direkt wenn oben aufmass 0 ist .. wenn oben aufmass 1 ist liegts 1mm
# drunter ... und unten aufmass brauchts dann ja eigentlich nicht ... auser man will es eingeben dann
# ergibt sich aber das obere aufmass durch die höhe .. also ein switch wäre gut ... wenn das teil dann
# nicht ins rohteil past muss es eine warnung geben“): Länge, Breite, Höhe; das Teil in X und Y
# mittig, in der Höhe das Aufmaß oben – oder unten, dann ergibt sich das obere.
MASSE_FELDER = ("x", "y", "z", "aufmass")
ROHTEIL_MASSE = "CamAddonRohteilMasse"  # am Job: „x;y;z;oben|unten;Aufmaß“ (mm)
VERSATZ_FELDER = ("x", "y", "z")  # der Nullpunkt, vom gewählten Punkt aus verschoben


def _parameter():
    return FreeCAD.ParamGet(PARAMETER_PFAD)


def _mm(wert):
    """Eine Länge des Rohteils (Quantity oder Zahl) in mm."""
    try:
        return float(wert.getValueAs("mm"))
    except AttributeError:
        return float(wert)


def _ziel_minuten(minuten):
    """„0,4 min“, „7,4 min“ unter 10 Minuten, darüber wie _zeit_text („31 min“, „2 h 5 min“)."""
    if minuten < 10.0:
        return tr("ba.ziel.minuten", min=dezimal(f"{minuten:.1f}"))
    return _zeit_text(minuten)


def _ziel_werkzeug(werkzeug):
    """„T2 Messerkopf Ø 50“."""
    d = groesse_zeigen(werkzeug.durchmesser, einheiten.LAENGE) or "0"
    return tr(
        "ba.ziel.werkzeug", nummer=wz.nummer_text(werkzeug), art=wz.art_text(werkzeug.art), d=d
    )


def _grau(text=""):
    """Ein grauer Satz – Erklärungen und gerechnete Werte (wie in gui_vierachs)."""
    etikett = QtGui.QLabel(text)
    etikett.setStyleSheet(f"color: {GRAU_TEXT};")
    etikett.setWordWrap(True)
    return etikett


class _Satz(QtGui.QLabel):
    """Ein Satz, der an zwei Stellen steht – im Überblick (Schritt 2) und bei den Einstellungen
    (Schritt 3): setText schreibt auch in den Spiegel."""

    def __init__(self, farbe):
        super().__init__()
        self.spiegel = QtGui.QLabel()
        self._erlaubt = True
        for etikett in (self, self.spiegel):
            etikett.setWordWrap(True)
            etikett.setStyleSheet(f"color: {farbe};")
        self._sichtbarkeit()

    def setText(self, text):  # noqa: N802 – Qt-Name
        super().setText(text)
        self.spiegel.setText(text)
        self._sichtbarkeit()

    def erlauben(self, an):
        """Im Überblick nur, wenn die Strategie zur Wahl passt."""
        self._erlaubt = bool(an)
        self._sichtbarkeit()

    def _sichtbarkeit(self):
        # Leer nimmt der Satz keinen Platz (ein leeres Etikett ist eine Zeile hoch).
        leer = not self.text()
        self.setVisible(self._erlaubt and not leer)
        self.spiegel.setVisible(not leer)


def _bibliothek_der_pruefung():
    """Die Werkzeugverwaltung, mit der eine Vorschau Halter und Schaft prüft: die des offenen
    Assistenten mit dem Magazin seiner Maschine (Bibliothek.magazin_fuer_pruefung – der Halter und
    wie weit das Werkzeug an seinem Platz herausschaut). Manuel, 2026-10-25, an seiner tiefen
    Tasche: „T1 auf 54 mm ausspannen“ und „So einrichten“ schrieben in den Platz, die Vorschau
    las frisch die Werkzeugliste – „läst sich bei mir immer noch nicht klicken“. Ohne Fenster
    frisch geladen."""
    panel = BearbeitungPanel.offen
    bibliothek = getattr(panel, "bibliothek", None) if panel is not None else None
    if bibliothek is not None:
        panel.magazin()  # hängt das Magazin an (magazin.des_jobs)
        return bibliothek
    try:
        return wz.Bibliothek.laden()
    except (wz.BeschaedigteDatei, OSError):
        return None


class _Frage:
    """Eine Frage im Überblick (W-039; Manuel, 2026-10-25: „mehr abfragen wie der benutzer das
    teil bearbeiten wollen würde … aber wirklich als frage ;) … "weg 1 ist so und so [vorschau
    button] weg 2 ist so und so [vorschau button]"“): ihr Satz, je Weg ein Auswahlknopf mit
    kurzem Titel, darunter grau sein Satz, rechts seine Zeit und „Vorschau“ (die Werkzeugwege im
    3D). `wege`: [(Kennung, Titel, Satz)]; `gewechselt(kennung)` beim Wählen, `vorschau(kennung)`
    beim Klick auf „Vorschau“ (None: kein Knopf). Versteckt, solange sie nicht passt."""

    def __init__(self, titel, wege, gewaehlt, gewechselt, vorschau):
        self.widget = QtGui.QWidget()
        aufbau = QtGui.QVBoxLayout(self.widget)
        aufbau.setContentsMargins(0, 4, 0, 4)
        kopf = QtGui.QLabel(f"<b>{html.escape(titel)}</b>")
        kopf.setWordWrap(True)
        aufbau.addWidget(kopf)
        self.gruppe = QtGui.QButtonGroup(self.widget)
        self.knoepfe, self.zeiten, self.vorschau_knoepfe, self.saetze = {}, {}, {}, {}
        for kennung, kurz, satz in wege:
            zeile = QtGui.QHBoxLayout()
            zeile.setContentsMargins(0, 0, 0, 0)
            auswahl = QtGui.QRadioButton(kurz)
            auswahl.setChecked(kennung == gewaehlt)
            auswahl.toggled.connect(lambda an, k=kennung: an and gewechselt(k))
            self.gruppe.addButton(auswahl)
            zeile.addWidget(auswahl, 1)
            zeit = _grau()
            zeit.setToolTip(tr("ba.frage.zeit.tooltip"))
            zeile.addWidget(zeit)
            if vorschau is not None:  # ohne: die Wege sind dieselben (die Reihenfolge)
                zeigen = knopf(
                    tr("ba.frage.vorschau"),
                    tr("ba.frage.vorschau.tooltip"),
                    lambda k=kennung: vorschau(k),
                )
                zeigen.setCheckable(True)
                zeile.addWidget(zeigen)
                self.vorschau_knoepfe[kennung] = zeigen
            aufbau.addLayout(zeile)
            erklaerung = _grau(satz)
            erklaerung.setWordWrap(True)
            erklaerung.setContentsMargins(22, 0, 0, 2)
            aufbau.addWidget(erklaerung)
            self.knoepfe[kennung] = auswahl
            self.zeiten[kennung] = zeit
            self.saetze[kennung] = erklaerung

    def satz_setzen(self, kennung, satz):
        self.saetze[kennung].setText(satz)

    def waehlen(self, kennung):
        """Zeigt den Weg `kennung` gewählt, ohne `gewechselt` zu rufen – er ist es schon (ein
        Haken bei den Einstellungen sagt dasselbe)."""
        for auswahl in self.knoepfe.values():
            auswahl.blockSignals(True)
        self.knoepfe[kennung].setChecked(True)
        for auswahl in self.knoepfe.values():
            auswahl.blockSignals(False)

    def zeit_setzen(self, kennung, minuten):
        """„etwa 12 min“ – None: „rechnet …“, False: „geht hier nicht“."""
        if minuten is None:
            text = tr("ba.frage.rechnet")
        elif minuten is False:
            text = tr("ba.frage.geht_nicht")
        else:
            text = _zeit_text(minuten)
        self.zeiten[kennung].setText(text)

    def gezeigt(self, kennung):
        """Der Knopf „Vorschau“ des Wegs `kennung` gedrückt, die anderen nicht (None: keiner)."""
        for k, zeigen in self.vorschau_knoepfe.items():
            zeigen.blockSignals(True)
            zeigen.setChecked(k == kennung)
            zeigen.blockSignals(False)


def _keine_empfehlung():
    """empfehlung.KEINE – „auch mit anderen Haltern geht es nicht“."""
    from . import empfehlung as em

    return em.KEINE


def _bohrer_von(gebohrt):
    """Die Bohrer eines Vorbohrens (raeumen.Vorbohren) – ihre Kennungen in ihrer Folge; leer
    ohne."""
    if gebohrt is None:
        return []
    return list(dict.fromkeys(str(lo[4]) for lo in gebohrt.je_loch()))


def _wechsel_zahl(folge):
    """Wie oft in der Folge der Werkzeuge (Kennungen) das Werkzeug wechselt."""
    return sum(1 for a, b in zip(folge, folge[1:], strict=False) if a != b)


class _Bohrlinien:
    """Die Löcher des Vorbohrens (raeumen.Vorbohren) als Bahn für die Vorschau im 3D: je Loch aus
    5 mm über dem Rohteil senkrecht hinab und wieder hinauf. `block`: für wen sie vorbohren."""

    def __init__(self, gebohrt, block=None):
        self.gebohrt = gebohrt
        self.block = block
        loecher = gebohrt.je_loch()
        oben = gebohrt.tiefe + min(float(lo[2]) for lo in loecher) + 5.0
        self.punkte = []
        for x, y, z, *_bohrer in loecher:
            self.punkte += [
                bn.Punkt(True, x, y, oben),
                bn.Punkt(False, x, y, z),
                bn.Punkt(True, x, y, oben),
            ]


class _Angebot:
    """Ein Satz mit Knöpfen (höchstens KNOEPFE), der etwas anbietet – wie _Satz an zwei Stellen:
    im Überblick (nur, wenn die Strategie zur Wahl passt) und bei den Einstellungen. Leer nimmt
    er keinen Platz."""

    KNOEPFE = 2

    def __init__(self):
        self._aktionen = []
        self._erlaubt = True
        self.zeilen = []  # [(Zeile, Satz, [Knopf])] – Überblick, Einstellungen
        for _stelle in range(2):
            zeile = QtGui.QWidget()
            aufbau = QtGui.QVBoxLayout(zeile)
            aufbau.setContentsMargins(0, 0, 0, 0)
            satz = QtGui.QLabel()
            satz.setWordWrap(True)
            aufbau.addWidget(satz)
            reihe = QtGui.QHBoxLayout()
            reihe.setContentsMargins(0, 0, 0, 0)
            knoepfe = []
            for i in range(self.KNOEPFE):
                k = knopf("", "", lambda i=i: self._geklickt(i))
                reihe.addWidget(k)
                knoepfe.append(k)
            reihe.addStretch(1)
            aufbau.addLayout(reihe)
            zeile.hide()
            self.zeilen.append((zeile, satz, knoepfe))

    def zeigen(self, text, knoepfe):
        """`knoepfe`: [(Beschriftung, Aktion)]."""
        self._aktionen = [aktion for _text, aktion in knoepfe[: self.KNOEPFE]]
        for _zeile, satz, eigene in self.zeilen:
            satz.setText(text)
            for i, k in enumerate(eigene):
                k.setVisible(i < len(self._aktionen))
                k.setText(knoepfe[i][0] if i < len(self._aktionen) else "")
        self._sichtbarkeit()

    def leeren(self):
        self._aktionen = []
        for _zeile, satz, _knoepfe in self.zeilen:
            satz.setText("")
        self._sichtbarkeit()

    def text(self):
        return self.zeilen[0][1].text()

    def knoepfe(self):
        """Die sichtbaren Knöpfe im Überblick."""
        return self.zeilen[0][2][: len(self._aktionen)]

    def erlauben(self, an):
        self._erlaubt = bool(an)
        self._sichtbarkeit()

    def _sichtbarkeit(self):
        da = bool(self.text())
        self.zeilen[0][0].setVisible(da and self._erlaubt)
        self.zeilen[1][0].setVisible(da)

    def _geklickt(self, i):
        if i < len(self._aktionen):
            self._aktionen[i]()


def _eintauchwinkel(werkzeug):
    """Der Eintauchwinkel (Grad) für Helix und Rampe: der am Fräser, sonst die Vorgabe – in der
    Vorschau und in der angelegten Operation derselbe (bis P-2026-10-02-65 legte „Anlegen“ Nut
    und Bohrung mit 5° an, die Vorschau rechnete mit den 3° des Standardfräsers)."""
    return float(getattr(werkzeug, "eintauchwinkel", 0.0) or 0.0) or vb.EINTAUCHWINKEL


def _material_text(bahn):
    """„noch 5,6 cm³ – 11,1 cm³ hat „Räumen T1“ schon weggenommen“ – für eine Bahn mit
    Materialstand (W-012), wenn die Operationen davor dort etwas weggenommen haben; dazu beim
    3D-Schruppen, was rings um die gewählten Flächen noch steht (_drumherum_text); sonst ""."""
    saetze = [s for s in (_stand_text(bahn), _drumherum_text(bahn)) if s]
    return "\n".join(saetze)


def _drumherum_text(bahn):
    """Steht rings um die gewählten Flächen laut Rohteil noch Material (schruppen3d_bahn,
    `drumherum`)? Manuel, 2026-10-17, Frage 6: „hey schau mal du das rohteil ist dort noch
    komplett voll mit material .. wir müssen erst die schräge fläche wegplanen und dann können
    wir die tasche fräsen oder ist rohteil schon fertig so das nurnoch die tasche zu fräsen ist“ –
    ohne den Haken „Nur über den gewählten Flächen“, dass es mit weggeht, und wann der Haken
    passt; mit ihm, dass er es als gefräst nimmt. Sonst ""."""
    drumherum = float(getattr(bahn, "drumherum", 0.0) or 0.0)
    if drumherum <= r3b.DRUMHERUM_AB:
        return ""
    volumen = groesse_fest(drumherum / 1000.0, einheiten.VOLUMEN, 1)
    volumen = f"{volumen} {einheiten.einheit(einheiten.VOLUMEN)}"
    if getattr(bahn, "nur_ueber", False):
        return tr("ba.r3.drumherum_nur", volumen=volumen)
    return tr("ba.r3.drumherum", volumen=volumen)


def _stand_text(bahn):
    """Der Satz zum Materialstand aus _material_text."""
    weg, davor = getattr(bahn, "weg", 0.0), getattr(bahn, "davor", None)
    if not davor or weg <= 0:
        return ""
    einheit = einheiten.einheit(einheiten.VOLUMEN)
    noch = f"{groesse_fest(bahn.noch / 1000.0, einheiten.VOLUMEN, 1)} {einheit}"
    weg = f"{groesse_fest(weg / 1000.0, einheiten.VOLUMEN, 1)} {einheit}"
    wer = mst.wer_text(davor)
    if len(davor) == 1:
        return tr("ba.material.einer", noch=noch, weg=weg, wer=wer)
    return tr("ba.material.mehrere", noch=noch, weg=weg, wer=wer)


def _durch_gebiete(form, waende):
    """Die Wände unter `waende` (die durch das Teil gehen), unter denen das Räumen bis durch räumen
    kann (raeumen.durch_gebiete – ein Gebiet nur von gewählten Wänden begrenzt). Nicht ein Gebiet
    nur aus Bohrungen: Ein Loch fräst „Bohrung fräsen“ (Frage 5), dort tritt das Räumen nicht
    an; am C-Ring gehört die Bohrung über den Schlitz zum Gebiet draußen und kommt mit. Je Form
    gemerkt (Prüfsumme und Kasten, wie kontur_bahn._wand); das Rohteil zählt nicht – sein Rand
    begrenzt nie."""
    box = form.BoundBox
    try:
        kasten = tuple(
            round(v, 6) for v in (box.XMin, box.XMax, box.YMin, box.YMax, box.ZMin, box.ZMax)
        )
        schluessel = (form.hashCode(), kasten, waende)
    except Exception:  # noqa: BLE001 – eine Form ohne Prüfsumme: rechnen
        schluessel = None
    if schluessel is not None and schluessel in _DURCH_MERK:
        return list(_DURCH_MERK[schluessel])
    rand = 10.0
    gebiete = ra.durch_gebiete(
        form, list(waende), (box.XMin - rand, box.XMax + rand, box.YMin - rand, box.YMax + rand)
    )
    ergebnis = []
    for _ebene, _schleifen, namen in gebiete:
        if all(bb.ist_bohrung(form, n) for n in namen):
            continue
        ergebnis.extend(n for n in namen if n not in ergebnis)
    if schluessel is not None:
        _DURCH_MERK[schluessel] = list(ergebnis)
    while len(_DURCH_MERK) > 64:
        _DURCH_MERK.pop(next(iter(_DURCH_MERK)))
    return ergebnis


_DURCH_MERK = {}


def _waende_um(form, boeden):
    """Die Wände des Teils, die unten an die Böden `boeden` stoßen – Zapfen und Inseln auf ihnen,
    Absätze davor: die nach dem Räumen das Aufmaß tragen (kontur_bahn.boeden_vor)."""
    boeden = set(boeden)
    return [name for name, vor in _boeden_vor_je_wand(form) if vor & boeden]


_BOEDEN_VOR = {}  # Kennung der Form → [(Wand, frozenset der Böden vor ihr)]


def _boeden_vor_je_wand(form):
    """Je Wand des Teils die Böden vor ihr (kontur_bahn.boeden_vor) – je Form einmal gerechnet:
    Der Assistent fragt je Vorschau mehrmals (am Testteil 0,7 s je Mal). Ein Körper aus einem
    STL hat keine Wände mit Böden davor – nur Dreiecke (sonst 2,6 s je Vorschau am Geist)."""
    from . import stl_teil

    if stl_teil.daten(form) is not None:
        return []
    try:
        kasten = form.BoundBox
        schluessel = (form.hashCode(), ft.anzahl(form), round(form.Volume, 6)) + tuple(
            round(v, 6) for v in (kasten.XMin, kasten.XMax, kasten.YMin, kasten.YMax)
        )
    except Exception:  # eine Form ohne Prüfsumme: rechnen
        schluessel = None
    if schluessel is not None and schluessel in _BOEDEN_VOR:
        return _BOEDEN_VOR[schluessel]
    ergebnis = []
    for i, flaeche in enumerate(form.Faces):
        name = f"Face{i + 1}"
        if not kb.ist_wand(flaeche):
            continue
        vor = kb.boeden_vor(form, [name])
        if vor:
            ergebnis.append((name, frozenset(vor)))
    if schluessel is not None:
        if len(_BOEDEN_VOR) > 16:
            _BOEDEN_VOR.clear()
        _BOEDEN_VOR[schluessel] = ergebnis
    return ergebnis


def _namen_kurz(namen, hoechstens=8):
    """„Face3, Face4, …“ – mehr als `hoechstens` Namen gekürzt auf die ersten und wie viele noch
    (ein STL hat Zehntausende)."""
    namen = list(namen)
    if len(namen) <= hoechstens:
        return ", ".join(namen)
    rest = f"{len(namen) - hoechstens:,}".replace(",", "\u202f")
    return tr("ba.namen.weitere", namen=", ".join(namen[:hoechstens]), anzahl=rest)


def _aussennormale(form, name):
    """Die Normale der ebenen Fläche `name` („Face6“) von `form` aus dem Material heraus – None,
    wenn es sie nicht gibt oder sie nicht eben ist."""
    nummer = int(name[4:]) - 1 if name.startswith("Face") and name[4:].isdigit() else -1
    if not 0 <= nummer < ft.anzahl(form) or not vr.ist_eben(ft.flaeche(form, nummer)):
        return None
    return vr.aussennormale(ft.flaeche(form, nummer))


# Strategien für Freiform – sie nehmen auch eine ebene oder kegelige Fläche, die zu etwas anderem
# gehört (die Spitze einer Bohrung): bei „Alles aus dieser Aufspannung“ nicht für solche.
FREIFORM_STRATEGIEN = {
    "schruppen3d",
    "restschruppen",
    "schlichten3d",
    "restschlichten",
    "bleistift",
}
ANALYTISCH = {"Plane", "Cylinder", "Cone"}
# So viel des äußeren Rands einer Fläche darf eine Wand über sich haben, und sie gilt noch als
# offen fürs Planfräsen (hoehenfeld.wand_anteil; eine Ecke, Rundungen am Rand).
OFFEN_HOECHSTENS = 0.05

# Die nächsten Ebenen aus „Alles aus dieser Aufspannung“: [(Job der Ebene, [Flächen], Satz)].
_FOLGE = []
# Welches Fenster die nächste Ebene der Kette öffnet: das, aus dem „Anlegen“ kam (die Beta öffnet
# wieder die Beta).
_FOLGE_FENSTER = {"klasse": None}


def _ebenen_der_aufspannung(grundjob, richtungen, werkzeug=None, einsatz=None, waagerecht=False):
    """Nach „Anlegen“ mit „Alles aus dieser Aufspannung“ (Frage 14, Schritt 4) oder mit schrägen
    Flächen an einer 5-Achs-Fräse: je weitere Richtung die Ebene (schwenken.lege_an – ein Schritt
    Rückgängig für alle), dann der Assistent für die erste, ihre Flächen gewählt; nach seinem
    „Anlegen“ die nächste (_folge_weiter). Die Maschine des Jobs mit dem ersten Werkzeug rechnet
    die Rundachsen; hat der Grundjob noch keins (nur schräge Flächen gewählt), mit `werkzeug`
    (wz.Werkzeug, übergeben) und `einsatz` – sein Controller nur dafür, danach wieder weg. Ohne
    Maschine keine Ebene. `waagerecht` (die Spindel der Maschine): Mit der Ebene „von oben“
    kommt der Grundjob – dann nur noch die Flanke – nach den Ebenen (schwenken.nach_den_ebenen)."""
    from . import schwenken as sw
    from .gui_schwenken import maschine_fuer

    dokument = grundjob.Document
    dokument.openTransaction(tr("ba.folge.titel"))
    controller = next(iter(js.werkzeug_controller(grundjob)), None)
    hilfe = None
    if controller is None and werkzeug is not None and einsatz is not None:
        try:
            hilfe = controller = js.controller_ohne_transaktion(
                dokument, grundjob, werkzeug, einsatz
            )
        except Exception as fehler:  # noqa: BLE001 – dann ohne Maschine (die Meldung unten)
            FreeCAD.Console.PrintLog(f"CAM-Addon: Ebenen: {fehler}\n")
    maschine, _name = maschine_fuer(grundjob, controller) if controller is not None else (None, "")
    if hilfe is not None:
        js.controller_weg(dokument, [hilfe])
    if maschine is None:
        dokument.abortTransaction()
        QtGui.QMessageBox.information(
            FreeCADGui.getMainWindow(), tr("ba.folge.titel"), tr("ba.folge.ohne_maschine")
        )
        _folge_weiter()  # eine Kette, die schon lief (N-Eck, Ebenen), geht weiter
        return
    angelegt, fehler = [], []
    for r in richtungen:
        vorhanden = _vorhandene_lage(grundjob, r, sw.ebenen_von(grundjob))
        if vorhanden is not None:
            angelegt.append((vorhanden, r))  # dieselbe Ebene gibt es schon: dort weiter
            continue
        try:
            if r.stirn:
                job = sw.lege_an(grundjob, r.stirn, maschine)
            else:
                x, y, z = r.achse
                winkel = (
                    math.degrees(math.acos(max(-1.0, min(1.0, z)))),
                    math.degrees(math.atan2(y, x)),
                )
                job = sw.lege_an(grundjob, "", maschine, winkel=winkel)
        except ValueError as grund:
            fehler.append(str(grund))
            continue
        angelegt.append((job, r))
    if waagerecht and any(abs(float(r.achse[2]) - 1.0) < 1e-9 for _job, r in angelegt):
        sw.grundjob_zuletzt(grundjob)
    dokument.commitTransaction()
    with uhren.still():
        dokument.recompute()
    if fehler:
        QtGui.QMessageBox.information(
            FreeCADGui.getMainWindow(),
            tr("ba.folge.titel"),
            tr("ba.folge.fehler", fehler="\n".join(fehler)),
        )
    # Vorn in die Kette: lief schon eine (die Aufspannungen der N-Eck-Stange, die Ebenen), geht
    # sie danach weiter.
    _FOLGE[:0] = [
        (
            job,
            list(r.flaechen),
            (
                tr("ba.folge.text", nummer=i + 1, anzahl=len(angelegt), winkel=f"{r.neigung:.0f}")
                if r.neigung >= 0.5
                else tr("ba.folge.text_oben", nummer=i + 1, anzahl=len(angelegt))
            ),
        )
        for i, (job, r) in enumerate(angelegt)
    ]
    _folge_weiter()


def _gekippt_anlegen(grundjob, richtungen):
    """Nach „Anlegen“ mit schrägen Flächen an einer 3-Achs-Fräse, „Bahnen dafür anlegen und im
    Einrichtblatt notieren“ angehakt (Manuel, 2026-10-16: „dann muss ich das ding schräg
    einspannen in den schraubstock … sollen wir dafür die werkzeugwege erstellen und das im
    einstellblatt notieren ?“): je
    Richtung eine Aufspannung, das Teil so gekippt, dass ihre Fläche nach oben zeigt
    (schwenken.lege_an, von Hand umgespannt wie die N-Eck-Stange – ein Schritt Rückgängig für
    alle); dann der Assistent für die erste, ihre Flächen gewählt, nach seinem „Anlegen“ die
    nächste (_folge_weiter). Das Einrichtblatt nennt Winkel und Achse."""
    from . import schwenken as sw

    dokument = grundjob.Document
    dokument.openTransaction(tr("ba.gekippt.titel"))
    angelegt, fehler = [], []
    for r in richtungen:
        job = _vorhandene_lage(grundjob, r, sw.aufspannungen_von(grundjob))
        if job is None:
            try:
                job = sw.lege_an(grundjob, r.stirn, None)
            except ValueError as grund:
                fehler.append(str(grund))
                continue
            sw.umspannen_setzen(job)
            neigung, _achse = sw.kippung(sw.normale_der(FreeCAD.Placement(job.Ebene)))
            job.Label = tr(
                "ba.gekippt.job", job=grundjob.Label, flaeche=r.stirn, winkel=f"{neigung:.0f}"
            )
        neigung, achse = sw.kippung(sw.normale_der(FreeCAD.Placement(job.Ebene)))
        angelegt.append((job, r, neigung, achse))
    dokument.commitTransaction()
    with uhren.still():
        dokument.recompute()
    if fehler:
        QtGui.QMessageBox.information(
            FreeCADGui.getMainWindow(),
            tr("ba.gekippt.titel"),
            tr("ba.folge.fehler", fehler="\n".join(fehler)),
        )
    _FOLGE[:0] = [  # vorn in die Kette (wie _ebenen_der_aufspannung)
        (
            job,
            list(r.flaechen),
            tr(
                "ba.gekippt.folge",
                nummer=i + 1,
                anzahl=len(angelegt),
                winkel=f"{neigung:.0f}",
                achse=_achse_text(achse),
            ),
        )
        for i, (job, r, neigung, achse) in enumerate(angelegt)
    ]
    _folge_weiter()


# Datei → Spindel quer? – für Maschinen, deren Eintrag das nicht hat und deren Datei sich nicht
# lesen ließ: nur einmal versuchen.
_SPINDEL = {}


def _spindel_nachrechnen(eintrag):
    """Ein Eintrag aus einer Liste von vorher, ohne „Spindel quer“: die Datei der Maschine einmal
    öffnen (unsichtbar, wenn sie zu ist) und den Eintrag neu schreiben
    (maschinenspeicher.merken_dokument). Gibt den neuen Eintrag zurück; ließ sie sich nicht
    lesen, den alten mit False."""
    if eintrag.datei in _SPINDEL:
        return dataclasses.replace(eintrag, spindel_quer=_SPINDEL[eintrag.datei])
    offen = next(
        (
            d
            for d in FreeCAD.listDocuments().values()
            if msp.gleiche_datei(d.FileName, eintrag.datei)
        ),
        None,
    )
    aktiv = FreeCAD.ActiveDocument
    dokument = offen
    try:
        if dokument is None:
            dokument = FreeCAD.openDocument(eintrag.datei, hidden=True)
        msp.merken_dokument(dokument)
    except Exception as fehler:  # noqa: BLE001 – dann wie eine Maschine mit stehender Spindel
        FreeCAD.Console.PrintLog(f"CAM-Addon: Spindel von {eintrag.name}: {fehler}\n")
    finally:
        if offen is None and dokument is not None:
            with contextlib.suppress(Exception):
                FreeCAD.closeDocument(dokument.Name)
        if aktiv is not None and FreeCAD.ActiveDocument is not aktiv:
            with contextlib.suppress(Exception):
                FreeCAD.setActiveDocument(aktiv.Name)
    neu = msp.finde(msp.laden(), eintrag.datei)
    if neu is None or neu.spindel_quer is None:
        neu = dataclasses.replace(eintrag, spindel_quer=False)
    _SPINDEL[eintrag.datei] = neu.spindel_quer
    return neu


def _vorhandene_lage(grundjob, richtung, jobs):
    """Der Job aus `jobs` (Ebenen oder Aufspannungen von `grundjob`), dessen Werkzeugachse die der
    Richtung ist (zugang.Richtung; ihre Stirn am Modell des Grundjobs, sonst ihre Achse) – eine
    parallele Fläche liegt in derselben Ebene: kein zweiter Job (wie „Ebene schwenken“). None,
    wenn es keinen gibt."""
    from . import schwenken as sw

    try:
        if richtung.stirn:
            lage = sw.ebene_aus_flaeche(vr.modell(grundjob).Shape, richtung.stirn)
            normale = sw.normale_der(lage)
        else:
            normale = FreeCAD.Vector(*richtung.achse)
    except ValueError:
        return None
    return next(
        (j for j in jobs if sw.normale_der(FreeCAD.Placement(j.Ebene)).dot(normale) > 1.0 - 1e-9),
        None,
    )


# mm – so hoch ist eine gezeichnete Fase höchstens, die das Entgraten macht; eine höhere Schräge
# zwischen Oberseite und Wand wird geschwenkt bzw. gekippt gespannt gefräst (_schraege).
FASE_HOECHSTENS = 5.0


_volumen = ft.volumen  # gemerkt, am Geist aus dem Netz (0,8 s → 2 ms je Aufruf)


def _lage_von(form):
    """Die Lage einer Form als Tupel (fürs Merken): ihre Placement-Matrix."""
    try:
        return tuple(round(x, 9) for x in form.Placement.toMatrix().A)
    except Exception:  # noqa: BLE001 – ohne Lage: nichts merken, was nicht stimmt
        return None


def _kleine_fase(form, name):
    """Ist die Fläche eine gezeichnete Fase, klein genug fürs Entgraten – oder eine Fase für den
    Block „Fase“ (auch eine, die vom Grund einer Nut aufsteigt)?"""
    if fb.ist_fase(form, name):
        return True
    if not eb.ist_fase(form, name):
        return False
    return ft.flaeche(form, int(name[4:]) - 1).BoundBox.ZLength <= FASE_HOECHSTENS


def _fase_fuer_block(form, name):
    """Fräst der Block „Fase“ die Fläche – eine Fase (fase_bahn.ist_fase), keine Senkung über
    einer Bohrung (die senkt „Senken“)?"""
    return fb.ist_fase(form, name) and not sk.ist_senkung(form, name)


def _achse_text(achse):
    """„ um Y“, „ um X“ – oder nichts, wenn die Achse schräg liegt (schwenken.kippung)."""
    return tr("ba.gekippt.um", achse=achse) if achse else ""


def _folge_weiter():
    """Der Assistent für die nächste Ebene der Kette – oder nichts mehr. Eine Aufspannung der
    N-Eck-Stange (W-018) kommt ohne gewählte Flächen („Alles aus dieser Aufspannung“ wählt sie)
    und nimmt die Maschine ihres Grundjobs."""
    while _FOLGE:
        job, flaechen, text = _FOLGE.pop(0)
        try:
            if job.Document is not None and job.Document.getObject(job.Name) is not None:
                break
        except Exception:  # noqa: BLE001 – gelöscht oder das Dokument zu: das nächste Glied
            pass
    else:
        return
    klon = vr.modell(job)
    grund = getattr(job, "Grundjob", None)
    datei = getattr(grund, rw.EIGENSCHAFT_MASCHINE, "") if grund is not None else ""
    if datei and not getattr(job, rw.EIGENSCHAFT_MASCHINE, ""):
        rw.merke_maschine(job, datei)
    FreeCADGui.Selection.clearSelection()
    if FreeCAD.ActiveDocument is not job.Document:  # in 26.3 kommt das Fenster ins aktive
        FreeCAD.setActiveDocument(job.Document.Name)
    fenster = _FOLGE_FENSTER.get("klasse") or BearbeitungPanel
    FreeCADGui.Control.showDialog(
        fenster(
            job.Document,
            (vr.original(klon), flaechen[0] if flaechen else None),
            angeklickt=klon,
            flaechen=flaechen or None,
            folge=text,
        )
    )


def _n_eck_anlegen(dokument, teil, wahl):
    """Das Teil aus einer N-Eck-Stange im Schraubstock (W-018): Grundjob und Aufspannungen 2 … N
    (n_eck) – ein Schritt Rückgängig –, dann der Assistent für die erste; nach seinem „Anlegen“
    die nächste (_folge_weiter), jede mit dem Satz fürs Einrichten."""
    _FOLGE_FENSTER["klasse"] = None
    import numpy as np

    from . import n_eck as ne
    from . import stl_teil

    gefunden = stl_teil.netz_fuer(teil.Shape)
    if gefunden is not None:
        punkte = gefunden[0]
    else:
        punkte = np.array([(v.X, v.Y, v.Z) for v in teil.Shape.Vertexes], dtype=float)
    dokument.openTransaction(tr("ne.titel"))
    # Acht Jobs mit je einem Klon des Teils (am Geist 3 s): die Sanduhr dazu.
    QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
    fehler = None
    try:
        try:
            job, _stange = ne.richte_ein(
                dokument, teil, punkte, wahl["n"], wahl["achse"], wahl["umgedreht"],
                spannlaenge=wahl["spannlaenge"],
            )  # fmt: skip
            jobs = ne.aufspannungen_anlegen(job)
        except ValueError as grund:
            dokument.abortTransaction()
            fehler = str(grund)
        else:
            dokument.commitTransaction()
            with uhren.still():
                dokument.recompute()
    finally:
        QtGui.QApplication.restoreOverrideCursor()
    if fehler is not None:
        QtGui.QMessageBox.warning(FreeCADGui.getMainWindow(), tr("ne.titel"), fehler)
        return
    # Zu sehen: das Teil in der Stange, nicht das Original daneben.
    for objekt, sichtbar in ((teil, False), (vr.modell(job), True), (job.Stock, True)):
        if getattr(objekt, "ViewObject", None) is not None:
            stl_anzeige.zeigen(objekt, sichtbar)  # ein Teil aus einem STL als Netz
    _FOLGE[:] = [(j, [], f"{ne.einrichten_text(j)} {tr('ne.folge')}") for j in jobs]
    FreeCADGui.Selection.clearSelection()
    FreeCADGui.Control.showDialog(
        BearbeitungPanel(
            dokument,
            (teil, None),
            angeklickt=vr.modell(job),
            folge=f"{ne.einrichten_text(job)} {tr('ne.folge')}",
        )
    )


# Die Farben der weiteren Richtungen (aus_der_aufspannung) – weder Grün (gewählt) noch Rot.
RICHTUNG_FARBEN = ("#e8962d", "#9b59b6", "#1f9e8f", "#b5651d", "#2e86c1")


def _schraeg(form, name):
    """Wie weit die ebene Fläche `name` gegen die Waagerechte geneigt ist (Grad) – None, wenn sie
    nicht eben ist, gerade nach oben oder gerade nach unten zeigt (das fräst der Job ohne
    Schwenken bzw. eine andere Seite unten) oder eine senkrechte Wand ist. Auch schräg nach unten
    (ein Hinterschnitt, über 90°): Dann geht sie geschwenkt bzw. gekippt gespannt."""
    normale = _aussennormale(form, name)
    if normale is None:
        return None
    winkel = math.degrees(math.acos(max(-1.0, min(1.0, normale.z))))
    if winkel < 0.5 or abs(winkel - 90.0) < 0.5 or winkel > 179.5:
        return None
    return winkel


def _klappknopf(text, tooltip):
    """Ein fetter Knopf mit Pfeil, der einen Bereich auf- und zuklappt."""
    knopf = QtGui.QToolButton()
    knopf.setArrowType(QtCore.Qt.RightArrow)
    knopf.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
    knopf.setText(text)
    knopf.setToolTip(tooltip)
    knopf.setAutoRaise(True)
    knopf.setCheckable(True)
    schrift = knopf.font()
    schrift.setBold(True)
    knopf.setFont(schrift)
    return knopf


def nullpunkte():
    """[(Text, (sx, sy, sz))] – die 22 Punkte des Rohteil-Quaders zur Wahl als Nullpunkt
    (Manuel, 2026-10-01): die 8 Ecken, die 12 Kantenmitten, die Mitte oben und unten;
    sx, sy, sz je −1, 0 oder 1 – links/rechts ist X, vorne/hinten Y, unten/oben Z."""
    x_namen = {-1: tr("np.links"), 1: tr("np.rechts")}
    y_namen = {-1: tr("np.vorne"), 1: tr("np.hinten")}
    z_namen = {-1: tr("np.unten"), 1: tr("np.oben")}
    punkte = []
    for sz in (1, -1):
        for sy in (-1, 1):
            for sx in (-1, 1):
                text = tr("np.ecke", x=x_namen[sx], y=y_namen[sy], z=z_namen[sz])
                punkte.append((text, (sx, sy, sz)))
    for sz in (1, -1):
        for sy in (-1, 1):  # Kanten längs X
            punkte.append((tr("np.kante", a=y_namen[sy], b=z_namen[sz]), (0, sy, sz)))
        for sx in (-1, 1):  # Kanten längs Y
            punkte.append((tr("np.kante", a=x_namen[sx], b=z_namen[sz]), (sx, 0, sz)))
    for sy in (-1, 1):  # die senkrechten Kanten
        for sx in (-1, 1):
            punkte.append((tr("np.kante", a=x_namen[sx], b=y_namen[sy]), (sx, sy, 0)))
    for sz in (1, -1):
        punkte.append((tr("np.mitte", a=z_namen[sz]), (0, 0, sz)))
    return punkte


def nullpunkt_vorgeben(lage):
    """Merkt `lage` ((sx, sy, sz) aus nullpunkte(), None: wie im Modell) als Nullpunkt für den
    nächsten Job – wie nach „Anlegen“ mit dieser Wahl."""
    text = "modell" if lage is None else ",".join(str(int(s)) for s in lage)
    _parameter().SetString(GEMERKT_NULLPUNKT, text)


def _gemerkter_nullpunkt():
    """Der gemerkte Nullpunkt (sx, sy, sz) – None: wie im Modell; ohne Eintrag die Vorgabe."""
    text = _parameter().GetString(GEMERKT_NULLPUNKT, "").strip()
    if text == "modell":
        return None
    try:
        lage = tuple(int(s) for s in text.split(","))
    except ValueError:
        return NULLPUNKT_VORGABE
    return lage if len(lage) == 3 else NULLPUNKT_VORGABE


def ist_bearbeitung(op):
    """Eine Operation dieses Assistenten – „Planfräsen“, „Räumen“, „Nut“, „Bohrung fräsen“,
    „Kontur“, „Entgraten“, „Gewinde fräsen“, „3D-Schruppen“, „3D-Schlichten“ oder
    „Bleistift“?"""
    return (
        s3op.ist_schlichten3d(op)
        or flop.ist_flanke(op)
        or r3op.ist_schruppen3d(op)
        or bst.ist_bleistift(op)
        or pf.ist_planfraesen(op)
        or ra.ist_raeumen(op)
        or nu.ist_nut(op)
        or bo.ist_bohrungsfraesen(op)
        or ko.ist_kontur(op)
        or eg.ist_entgraten(op)
        or fa.ist_fase_op(op)
        or gf.ist_gewindefraesen(op)
    )


class BefehlBearbeitung:
    """Befehl in der Werkzeugleiste: öffnet den Assistenten für die gewählte Fläche – oder
    zum Ändern, wenn „Planfräsen“ oder „Kontur“ gewählt ist."""

    def GetResources(self):
        return {
            "Pixmap": symbol("bearbeitung.svg"),
            "MenuText": tr("befehl.bearbeitung.titel"),
            "ToolTip": tr("befehl.bearbeitung.tooltip"),
        }

    def IsActive(self):
        return not FreeCADGui.Control.activeDialog()

    def panel(self, *args, **kwargs):
        """Das Fenster, das der Befehl öffnet – die Beta (gui_bearbeitung_beta) nimmt ihr eigenes."""
        return BearbeitungPanel(*args, **kwargs)

    def Activated(self):
        from .gui_hilfe import arbeitsdokument

        dokument = arbeitsdokument()  # das der Auswahl – nicht die Maschine, die gerade aktiv ist
        if dokument is None:
            QtGui.QMessageBox.information(
                FreeCADGui.getMainWindow(), tr("ba.titel"), tr("ba.kein_dokument")
            )
            return
        operation = gewaehlte_operation(dokument)
        if operation is not None:
            bearbeiten(operation)
            return
        from . import gui_stl

        netz = gui_stl.gewaehltes_netz(dokument)
        if netz is None:  # nichts gewählt, aber ein STL im Dokument: fragen, ob es das sein soll
            angebot = gui_stl.stl_angebot(dokument, tr("ba.titel"))
            if angebot is not None and gui_stl.stl_teil.ist_netz(angebot):
                netz = angebot
            elif angebot is not None:
                FreeCADGui.Control.showDialog(
                    self.panel(dokument, (angebot, None), angeklickt=angebot)
                )
                return
        if netz is not None:
            # Ein STL (W-017): erst der Körper aus seinen Dreiecken – Maßstab im Fenster davor, dazu
            # das Rohteil: wie bisher oder eine N-Eck-Stange im Schraubstock (W-018).
            teil = gui_stl.teil_aus_netz(dokument, netz, n_eck=True)
            if teil is None:
                return
            if gui_stl.teil_aus_netz.n_eck is not None:
                _n_eck_anlegen(dokument, teil, gui_stl.teil_aus_netz.n_eck)
                return
            FreeCADGui.Control.showDialog(self.panel(dokument, (teil, None), angeklickt=teil))
            return
        wahl, angeklickt = gewaehlte_flaeche(dokument), angeklicktes_teil(dokument)
        if wahl is not None:
            teil = teil_hinter_link(wahl[0])
            if teil is not wahl[0]:  # ein Link in der Maschine (B-020): im Dokument des Teils
                wahl, angeklickt, dokument = (teil, wahl[1]), None, teil.Document
                _aktivieren(dokument)
        FreeCADGui.Control.showDialog(self.panel(dokument, wahl, angeklickt=angeklickt))


def teil_hinter_link(teil):
    """Das Teil hinter einem Link in ein anderes Dokument – etwa in die Baugruppe einer Maschine
    eingelegt (B-020; Manuel, 2026-10-12: „Konnte nicht anlegen: PropertyLink does not support
    external object“, im Baum der neuen 3-Achs-Fräse ein halber Job und ein loses „TC: 5mm
    Endmill“). Der Job gehört ins Dokument des Teils. Sonst `teil` selbst."""
    ziel = teil
    for _ in range(10):  # ein Link auf einen Link …
        weiter = getattr(ziel, "LinkedObject", None) if ziel.TypeId == "App::Link" else None
        if weiter is None:
            break
        ziel = weiter
    if ziel is not teil and getattr(ziel, "Document", None) is not teil.Document:
        return ziel
    return teil


def _aktivieren(dokument):
    """Macht `dokument` aktiv – auch in der Oberfläche: Dort öffnet sich das Aufgabenfenster."""
    FreeCAD.setActiveDocument(dokument.Name)
    if FreeCADGui.getDocument(dokument.Name) is not None:
        FreeCADGui.setActiveDocument(dokument.Name)


def gewaehlte_operation(dokument):
    """Das gewählte „Planfräsen“ oder „Kontur“ – oder, ist ein Job oder sein Ordner
    „Operations“ gewählt, seine erste solche Operation; sonst None."""
    jobs = js.jobs(dokument)
    for objekt in FreeCADGui.Selection.getSelection(dokument.Name):
        if ist_bearbeitung(objekt):
            return objekt
        job = next(
            (j for j in jobs if objekt is j or objekt is getattr(j, "Operations", None)), None
        )
        if job is not None:
            gefunden = [o for o in js.operationen(job) if ist_bearbeitung(o)]
            if gefunden:
                return gefunden[0]
    return None


def angeklicktes_teil(dokument):
    """Das angeklickte Objekt mit Form – ein Modell-Klon eines Jobs bleibt der Klon (so weiß
    man, in welchem Job man geklickt hat); None ohne Auswahl."""
    for auswahl in FreeCADGui.Selection.getSelectionEx(dokument.Name, 0):
        for unterelement in auswahl.SubElementNames or [""]:
            teil, _flaeche = _entlang(dokument, auswahl.Object, unterelement)
            if teil is not None:
                return teil
    return None


def drehmaschine_stirn(job):
    """Ist die Maschine des Jobs eine Drehmaschine mit Y- oder C-Achse? Dann fräst „Bearbeitung“
    an der Stirnseite der Stange mit axialem Werkzeug (W-025; stirnseite: Y bis zum eingestellten
    Anteil, dann hilft C – ohne Y polar mit X und C; Manuel, 2026-10-17: „alle Variationen … nur
    Y … C und X … oder eine Kombi“)."""
    datei = mg.maschine_des_jobs(job)
    try:
        if datei:
            eintraege = [msp.finde(msp.laden(), datei)]
        else:
            # Eine offene, noch ungespeicherte Maschine (die Beispiel-Drehmaschine): wie sie ist.
            from .gui_reichweite import offene_maschinen

            eintraege = [msp.beschreibe(a, m) for a, m in offene_maschinen(job.Document)]
    except Exception:  # noqa: BLE001 – ohne Maschinenspeicher: wie ohne Maschine
        return False
    return any(
        e is not None and e.art == msp.DREHMASCHINE and bool({"Y", "C"} & set(e.achsen))
        for e in eintraege
    )


def _drehmaschine_text(eintrag):
    """Der Satz zur Drehmaschine ohne Stangen-Job: gefräst wird im 4-Achs-Assistenten – mit Y oder
    C dazu, wie die Stirnseite von vorn geht (W-025: Stange dort einrichten, die Stirnfläche, der
    Verweis bringt zurück)."""
    text = tr("ba.maschine.drehmaschine")
    if eintrag is not None and {"Y", "C"} & set(getattr(eintrag, "achsen", ())):
        text += " " + tr("ba.maschine.drehmaschine_von_vorn")
    return text


def wand_ohne_rohteil(form, name, rohteil, abstand=0.5):
    """Steht vor der Wand `name` von `form` kein Rohteil – `abstand` mm vor 16 Punkten auf ihr,
    in Richtung aus dem Teil heraus, liegt keiner in `rohteil` (einer Form)? Dann ist die Wand
    schon fertig, „Schlichten danach“ fährt sie nicht ab: am C-Ring aus Rundmaterial Ø 60 der
    Mantel (Manuel, 2026-10-18, W-034: „wenn rt welle d60 ist muss man ausen nix machen“)."""
    nummer = int(name[4:]) - 1 if name.startswith("Face") and name[4:].isdigit() else -1
    if rohteil is None or rohteil.isNull() or not 0 <= nummer < len(form.Faces):
        return False
    flaeche = form.Faces[nummer]
    u0, u1, v0, v1 = flaeche.ParameterRange
    proben = 0
    for i in range(4):
        for j in range(4):
            u, v = u0 + (u1 - u0) * (i + 0.5) / 4, v0 + (v1 - v0) * (j + 0.5) / 4
            punkt = flaeche.valueAt(u, v)
            if not flaeche.isInside(punkt, 1e-6, True):
                continue
            normale = flaeche.normalAt(u, v)
            if form.isInside(punkt + normale * 0.3, 1e-6, False):
                normale = normale * -1  # ins Teil hinein gezeigt: umdrehen
            proben += 1
            if rohteil.isInside(punkt + normale * abstand, 1e-6, True):
                return False
    return proben > 0


def von_vorn_moeglich(job, bibliothek, werkzeug):
    """Kann `werkzeug` im Job von vorn fräsen? An der Stange der Drehmaschine (W-025) nur im
    geraden (axialen) Halter – im gewinkelten (radialen) zeigt es auf die Achse der Stange, nicht
    auf ihre Stirn (Manuel, 2026-10-18, am Ring: „das bearbeitet man doch von vorne“). Ohne
    bekannten Halter: ja."""
    if job is None or not stangen_job(job):
        return True
    halter = bibliothek.halter_fuer_pruefung(werkzeug) if bibliothek is not None else None
    return halter is None or not halter.gewinkelt


def stangen_job(job):
    """Hat der Job eine Stange als Rohteil, eingerichtet vom 4-Achs-Assistenten
    (vierachs_rohteil.ist_stange)? Ein „Zylinder mit Aufmaß“ auf der Fräse hat auch einen Radius,
    aber keine gemerkte Spannlänge (bis P-2026-10-18-62 hieß er „Stange … im Futter“)."""
    return vr.ist_stange(job)


def vorhandener_job(dokument, teil, angeklickt=None):
    """Der Job, in den ein weiterer Lauf am Teil `teil` geht (W-012 M2; Manuel, 2026-10-02:
    „Frage 1. A“): der, dessen Teil man angeklickt hat (`angeklickt`: sein Modell-Klon), sonst
    der zuletzt angelegte mit diesem Teil. Jobs im Quader – einer mit Stange gehört dem
    4-Achs-Assistenten, außer auf einer Drehmaschine mit Y oder C: Dort fräst „Bearbeitung“ an der
    Stirnseite der Stange (W-025; Manuel, 2026-10-17: die Nut im C-Ring „wie auf der 3-achsigen
    auch“). None, wenn das Teil noch keinen hat."""
    passende = []
    for job in js.jobs(dokument):
        try:
            klon = vr.modell(job)
        except (AttributeError, IndexError):
            continue
        if vr.original(klon) is not teil:
            continue
        if stangen_job(job) and not drehmaschine_stirn(job):
            continue
        if angeklickt is not None and angeklickt is klon:
            return job
        passende.append(job)
    return passende[-1] if passende else None


def bearbeiten(operation):
    """Öffnet den Assistenten zum Ändern von `operation` – mit ihren Werten. Nichts, solange
    ein anderes Aufgabenfenster offen ist."""
    if FreeCADGui.Control.activeDialog():
        return
    FreeCADGui.Control.showDialog(BearbeitungPanel(operation.Document, operation=operation))


class _Beobachter:
    """Meldet dem Assistenten jede angeklickte Fläche."""

    def __init__(self, panel):
        self.panel = panel

    def addSelection(self, _dokument, objekt, unterelement, punkt):
        from .gui_hilfe import lebt

        if not lebt(self.panel):  # das Fenster ist weg: abmelden statt ins Leere zu rufen
            with contextlib.suppress(Exception):
                FreeCADGui.Selection.removeObserver(self)
            return
        if not unterelement:
            return
        # Erst wenn FreeCAD mit der Auswahl fertig ist – der Assistent ändert das Dokument.
        uhren.gleich(lambda: self.panel.angeklickt(objekt, unterelement, punkt, _dokument))


class _NurFlaechen:
    """Anklicken lassen sich Flächen – mit Job nur die des Teils darin, und dort auch Kanten (für
    „Entgraten 3D“; Manuel, 2026-10-05: „Kanten anklicken muss sein“)."""

    def __init__(self, panel):
        self.panel = panel

    def allow(self, _dokument, objekt, unterelement):
        from .gui_hilfe import lebt

        if not lebt(self.panel):  # das Fenster ist weg: die Sperre auch
            with contextlib.suppress(Exception):
                FreeCADGui.Selection.removeSelectionGate()
            return True
        weg = unterelement.split(".") if unterelement else []
        if not weg or not weg[-1].startswith(("Face", "Edge")):
            return False
        job = self.panel.job
        if job is None:
            return weg[-1].startswith("Face")  # ohne Job beginnt ein Klick auf eine Fläche
        klon = vr.modell(job).Name
        return getattr(objekt, "Name", "") == klon or klon in weg


# --- Die Strategien ---------------------------------------------------------------------------


# Was passt(form, name) ergab, je Variante, Form und Fläche (_gemerkt_passt) – höchstens so viele.
_PASST = OrderedDict()
PASST_HOECHSTENS = 20000


_FORMEN = OrderedDict()  # id(Form) -> (Form, vierachs_huelle.form_kennung) – die Form festgehalten


def _form_kennung(form):
    """vierachs_huelle.form_kennung, je Formobjekt einmal: Sie zählt Flächen und Kanten, und der
    Assistent fragt bei einem Klick tausendfach mit derselben Form."""
    eintrag = _FORMEN.get(id(form))
    if eintrag is not None and eintrag[0] is form:
        return eintrag[1]
    kennung = vh.form_kennung(form)
    _FORMEN[id(form)] = (form, kennung)
    while len(_FORMEN) > 8:
        _FORMEN.popitem(last=False)
    return kennung


def _gemerkt_passt(passt):
    """passt(form, name) einer Strategie, gemerkt: Es hängt nur an der Form und der Fläche, und
    der Assistent fragt bei jedem Klick auf eine Fläche alle Strategien nach allen gewählten
    Flächen – am 3-Achs-Testteil stand er für acht Flächen 7 s (Bohrungen, Nuten, Wände je Klick
    neu; P-2026-10-11-66)."""

    @functools.wraps(passt)
    def gemerkt(self, form, name):
        try:
            schluessel = (id(passt), _form_kennung(form), name)
        except Exception:  # noqa: BLE001 – keine Form: ungemerkt
            return passt(self, form, name)
        if schluessel in _PASST:
            _PASST.move_to_end(schluessel)
            return _PASST[schluessel]
        ergebnis = passt(self, form, name)
        _PASST[schluessel] = ergebnis
        while len(_PASST) > PASST_HOECHSTENS:
            _PASST.popitem(last=False)
        return ergebnis

    return gemerkt


class _Strategie:
    """Eine 2,5D-Strategie im Assistenten: ihre Texte, Felder, Vorschläge, Vorschau, Anlegen
    und Ändern. Die Schlüssel stehen wörtlich in tr(…) – so findet sie die Sprachprüfung."""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if "passt" in cls.__dict__:
            cls.passt = _gemerkt_passt(cls.__dict__["passt"])

    kennung = ""
    gemerkt = ""  # Parameter: der zuletzt gewählte Fräser
    nimmt_kanten = False  # bekommt auch angeklickte Kanten („Edge12“) – nur Entgraten 3D
    einsatz_reihenfolge = ()  # welcher Einsatz vorgewählt ist
    bevorzugt = wz.SCHAFTFRAESER  # diese Art vorgewählt, wenn sonst nichts entscheidet
    # mm – das Raster, in dem die Operation ihre Bahn rechnet (aufloesung.py); None: hat keins.
    aufloesung = None

    def aufloesung_erklaerung(self, vorschlag):
        """Die Erklärung zum Feld „Auflösung“ – Kanten haben eine eigene."""
        return tr("ba.aufloesung.tooltip", vorschlag=vorschlag)

    def titel(self):
        return ""

    def text(self):
        return ""

    def fraeser_tooltip(self):
        return ""

    def einsatz_tooltip(self):
        return ""

    def felder(self):
        """((Name, Beschriftung, Tooltip) …) der Zahlenfelder."""
        return ()

    def haken(self):
        """((Name, Beschriftung, Tooltip, Vorgabe) …) der Ja/Nein-Felder."""
        return ()

    def haken_gesperrt(self, feld, block):
        """Warum der Haken `feld` hier nicht geht (ein kurzer Satz) – None, wenn er geht."""
        return None

    def haken_gesperrt_warum(self, feld, block):
        """Warum der Haken `feld` gesperrt ist, ausführlich – für den Tooltip; None: kein Satz."""
        return None

    def haken_verborgen(self, feld, block):
        """Fehlt der Haken `feld` hier ganz (er hätte an dieser Maschine nie Sinn)?"""
        return False

    def zeit(self, bahn, vorschub, eintauchen):
        """Minuten der Vorschau (bahn.zeit über ihre Punkte, mm/min)."""
        return bn.zeit(bahn.punkte, vorschub, eintauchen)

    def passt(self, form, name):
        """Kann die Strategie etwas mit der Fläche `name` von `form` anfangen?"""
        return False

    def werkzeug_passt(self, werkzeug):
        """Arbeitet die Strategie mit diesem Werkzeug? Vorgabe: ein Fräser mit ebener Stirn."""
        form = ff.von_werkzeug(werkzeug)
        return form is not None and vp.ebener_radius(form) > 0

    def flaechen_fuer(self, form, gewaehlte):
        if self.kennung in FREIFORM_STRATEGIEN and len(gewaehlte) > 64:
            from . import stl_teil

            if stl_teil.daten(form) is not None:  # ein STL: alle Dreiecke auf einmal (W-017)
                return s3b.freiformflaechen(form, gewaehlte)
        return [name for name in gewaehlte if self.passt(form, name)]

    def vorgeschlagen(self, form, gewaehlte):
        """Ist der Haken von sich aus gesetzt?"""
        return bool(self.flaechen_fuer(form, gewaehlte))

    def moeglich(self, form, gewaehlte):
        """Geht die Strategie mit dieser Wahl überhaupt?"""
        return bool(self.flaechen_fuer(form, gewaehlte))

    def unmoeglich_text(self):
        return ""

    def vorschlag(self, feld, werkzeug, einsatz):
        return 0.0

    def platzhalter(self, feld, werkzeug, einsatz):
        if feld == "aufloesung":
            return groesse_zeigen(self.aufloesung, einheiten.LAENGE)
        return groesse_zeigen(self.vorschlag(feld, werkzeug, einsatz), einheiten.LAENGE) or "0"

    def vorschau(self, job, werkzeug, werte, flaechen):
        raise NotImplementedError

    def ergebnis_text(self, bahn, zeit):
        return ""

    def lege_an(self, job, tc, werte, flaechen):
        raise NotImplementedError

    def aendere(self, op, tc, werte, flaechen):
        raise NotImplementedError

    def ist(self, op):
        return False

    def werte_von(self, op):
        """{Feld: Wert} der Operation – zum Ändern."""
        return {}


class _Planfraesen(_Strategie):
    kennung = "planfraesen"
    aufloesung = pf.pb.SCHRITT
    gemerkt = GEMERKT_FRAESER
    tief = False  # mit „Schruppen“ schneller als mit „Planen“ (Panel, _planeinsatz_waehlen)

    @property
    def einsatz_reihenfolge(self):
        if self.tief:
            return (wz.SCHRUPPEN, wz.PLANEN, wz.SCHLICHTEN)
        return (wz.PLANEN, wz.SCHRUPPEN, wz.SCHLICHTEN)

    def titel(self):
        return tr("ba.planfraesen")

    def text(self):
        return tr("ba.planfraesen.text")

    def fraeser_tooltip(self):
        return tr("ba.planfraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.planeinsatz.tooltip")

    def felder(self):
        return (
            ("zustellung", tr("ba.zustellung"), tr("ba.zustellung.tooltip")),
            ("zeilenabstand", tr("ba.zeilenabstand"), tr("ba.zeilenabstand.tooltip")),
            ("aufmass", tr("ba.aufmass"), tr("ba.aufmass.tooltip")),
        )

    def haken(self):
        return (
            (
                "nur_gleichlauf",
                tr("ba.nur_gleichlauf"),
                tr("ba.nur_gleichlauf.tooltip"),
                False,
            ),
        )

    def passt(self, form, name):
        # Nur die Oberseite – die ebenen Flächen ganz oben am Teil (Manuel, 2026-10-17:
        # „planfräsen ... ist für mich wenn ich ein bauteil habe das in z 4 mm aufmass hat .. dann
        # kann ich das planfräsen“; eine Kontur herausarbeiten ist Konturfräsen). Den Boden einer
        # Tasche, einer Nut oder eines Absatzes räumt das Räumen (2026-10-16: „das gehört schon
        # eher zum raeumen“).
        if not hf.ebenen_oben(form, [name]):
            return False
        # Rundum offen: an ihrem äußeren Rand steht nirgends eine Wand über ihr – die Oberseite,
        # auch mit einem Zapfen darauf (eine Insel); ein Absatz hat an einer Seite eine Wand.
        return hf.wand_anteil(form, name) <= OFFEN_HOECHSTENS

    def vorgeschlagen(self, form, gewaehlte):
        return not gewaehlte or bool(self.flaechen_fuer(form, gewaehlte))

    def moeglich(self, form, gewaehlte):
        # Ohne ebene Fläche die Oberseite; sind nur Böden von Taschen und Nuten gewählt, nicht.
        ebene = [n for n in gewaehlte if hf.ebenen_oben(form, [n])]
        return not ebene or bool(self.flaechen_fuer(form, gewaehlte))

    def unmoeglich_text(self):
        return tr("ba.planfraesen.eingeschlossen")

    def vorschlag(self, feld, werkzeug, einsatz):
        if feld == "zustellung":
            return einsatz.ap if einsatz is not None and einsatz.ap > 0 else pf.ZUSTELLUNG
        if feld == "zeilenabstand":
            if werkzeug is None:
                return 0.0
            return vplan.zeilenabstand_vorschlag(werkzeug, einsatz, ff.von_werkzeug(werkzeug))
        return pf.AUFMASS

    def _argumente(self, werkzeug, werte, flaechen):
        """(Argumente, Schlüsselwörter) für planfraesen.vorschau nach Job und Modell."""
        return (
            ff.von_werkzeug(werkzeug),
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            list(flaechen),
        ), {
            "vorschub": werte.get("vorschub", 0.0),
            "eintauchen": werte.get("eintauchen", 0.0),
            "nur_gleichlauf": werte.get("nur_gleichlauf", False),
            "stand": werte.get("materialstand"),
        }

    def vorschau(self, job, werkzeug, werte, flaechen):
        argumente, weiter = self._argumente(werkzeug, werte, flaechen)
        return pf.vorschau(job, job.Model.Group, *argumente, **weiter)

    def hintergrund(self, werkzeug, werte, flaechen):
        """Die Vorschau in einem Nebenrechner (bearbeitung_vorschau.strategie)."""
        return "strategie", ("planfraesen", *self._argumente(werkzeug, werte, flaechen))

    def ergebnis_text(self, bahn, zeit):
        lagen = tr("ba.zahl.lage") if bahn.lagen == 1 else tr("ba.zahl.lagen", n=bahn.lagen)
        zeilen = tr("ba.zahl.zeile") if bahn.zeilen == 1 else tr("ba.zahl.zeilen", n=bahn.zeilen)
        if bahn.flaechen > 1:
            flaechen = tr("ba.zahl.flaechen", n=bahn.flaechen)
            text = tr(
                "ba.ergebnis_flaechen", flaechen=flaechen, lagen=lagen, zeilen=zeilen, zeit=zeit
            )
        else:
            text = tr("ba.ergebnis", lagen=lagen, zeilen=zeilen, zeit=zeit)
        # Die Zeilenrichtung ist gerechnet, nicht geraten: beide Richtungen, die schnellere –
        # und wie viel langsamer die andere wäre (Grundsatz 0: die Zeit entscheidet).
        richtungen = set(bahn.richtungen)
        if bahn.zeit_andere is None or len(richtungen) != 1 or bahn.zeit <= 0:
            return text
        laengs_x = richtungen.pop()
        richtung, andere = ("X", "Y") if laengs_x else ("Y", "X")
        prozent = int(round((bahn.zeit_andere / bahn.zeit - 1.0) * 100.0))
        if prozent < 1:
            return tr("ba.richtung.gleich", text=text, richtung=richtung, andere=andere)
        return tr(
            "ba.richtung.langsamer", text=text, richtung=richtung, andere=andere, prozent=prozent
        )

    def lege_an(self, job, tc, werte, flaechen):
        return pf.lege_an(
            job,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            flaechen=flaechen,
            nur_gleichlauf=werte.get("nur_gleichlauf", False),
        )

    def aendere(self, op, tc, werte, flaechen):
        pf.aendere(
            op,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            flaechen=flaechen,
            nur_gleichlauf=werte.get("nur_gleichlauf", False),
        )

    def ist(self, op):
        return pf.ist_planfraesen(op)

    def werte_von(self, op):
        return {
            "zustellung": float(op.Zustellung),
            "zeilenabstand": float(op.Zeilenabstand),
            "aufmass": float(op.Aufmass),
            "nur_gleichlauf": bool(getattr(op, "NurGleichlauf", False)),
        }


class _Raeumen(_Strategie):
    kennung = "raeumen"
    aufloesung = ra.rb.SCHRITT
    gemerkt = GEMERKT_RAEUMFRAESER
    einsatz_reihenfolge = (wz.SCHRUPPEN, wz.PLANEN, wz.SCHLICHTEN)

    def titel(self):
        return tr("ba.raeumen")

    def text(self):
        return tr("ba.raeumen.text")

    def fraeser_tooltip(self):
        return tr("ba.raeumfraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.raeumeinsatz.tooltip")

    def felder(self):
        return (
            ("zustellung", tr("ba.zustellung"), tr("ba.zustellung.tooltip")),
            ("zeilenabstand", tr("ba.zeilenabstand"), tr("ba.raeumen.zeilenabstand.tooltip")),
            ("aufmass", tr("ba.aufmass_wand"), tr("ba.aufmass_wand.tooltip")),
            ("aufmass_boden", tr("ba.aufmass_boden"), tr("ba.aufmass_boden.tooltip")),
        )

    def haken(self):
        # Schlichten und Messstopp danach hat der eigene Block „Schlichten danach“
        # (_SchlichtenDanach; bis 0.126.0 zwei Haken hier). Vorbohren: Manuel, 2026-10-25,
        # Frage 4: „wenn in dem magazin ein passender bohrer vorhanden ist kann man doch vorbohren
        # ... kein problem .. zumidnest sollte man es erfragen“ – vorbelegt an, nur mit Bohrer.
        return (
            ("gleichlauf", tr("ba.gleichlauf"), tr("ba.gleichlauf.tooltip"), True),
            ("vorbohren", tr("ba.raeumen.vorbohren"), tr("ba.raeumen.vorbohren.tooltip"), True),
        )

    def haken_gesperrt(self, feld, block):
        if feld != "vorbohren":
            return None
        fraeser = block.fraeser()
        if fraeser is None or block.panel._vorbohrer(fraeser) is not None:
            return None
        return tr(
            "ba.raeumen.vorbohren.kein_bohrer",
            von=groesse_zeigen(fraeser.durchmesser, einheiten.LAENGE, 1) or "0",
            bis=groesse_zeigen(
                fraeser.durchmesser * VORBOHRER_HOECHSTENS, einheiten.LAENGE, 1
            ) or "0",
        )  # fmt: skip

    def passt(self, form, name):
        return bool(hf.ebenen_oben(form, [name])) or bool(kb.waende(form, [name]))

    def flaechen_fuer(self, form, gewaehlte):
        """Die ebenen Flächen nach oben – und die Böden der Taschen, deren Wände gewählt sind.
        Nicht den Boden einer Bohrung: Den fräst „Bohrung fräsen“. Dazu die Wände, die durch das
        Teil gehen, wenn nur Wände gewählt sind: Unter ihnen räumt es bis an die Unterkante
        (raeumen.durch_ebenen; Manuel, 2026-10-17, Frage 4: „Ja, Räumen tritt an“ – gegen die
        Kontur, die Zeit entscheidet)."""
        ebenen = [
            name
            for name in gewaehlte
            if hf.ebenen_oben(form, [name]) and bb.bohrung_ueber_boden(form, name) is None
        ]
        waende = [name for name in gewaehlte if name not in ebenen and kb.waende(form, [name])]
        for boden in rb.taschenboeden(form, waende):
            if boden not in ebenen and bb.bohrung_ueber_boden(form, boden) is None:
                ebenen.append(boden)
        # Wände bis zur Unterkante: Darunter räumt es bis durch – auch neben Böden („Alles aus
        # dieser Aufspannung“, ein Deckel mit Oberseite und Außenwänden). Manuel, 2026-10-18
        # (W-033/W-034, Grundsatz 5): von außen über alles, keine Luft – die Kontur schruppt
        # diese Wände nicht noch einmal (_flaechen), „Schlichten danach“ macht sie fertig.
        durch = [name for name in waende if ra.durchgehend(form, name)]
        if durch:
            ebenen.extend(f for f in _durch_gebiete(form, tuple(durch)) if f not in ebenen)
        return ebenen

    def vorgeschlagen(self, form, gewaehlte):
        # Von sich aus nur für ebene Flächen (die Oberseite ohne Wahl); für gewählte
        # Taschenwände bleibt die Kontur der Vorschlag – Räumen lässt sich dazu anhaken. Nicht
        # für den Boden eines Lochs: Den fräst „Bohrung fräsen“, und das Räumen nähme ohne
        # eigene Fläche die Oberseite – am Loch in der Schräge räumte es die ganze Schräge mit.
        return not gewaehlte or any(
            hf.ebenen_oben(form, [name]) and bb.bohrung_ueber_boden(form, name) is None
            for name in gewaehlte
        )

    def moeglich(self, form, gewaehlte):
        return True  # ohne ebene Fläche die Oberseite

    def unmoeglich_text(self):
        return tr("ba.raeumen.keine_flaeche")

    def vorschlag(self, feld, werkzeug, einsatz):
        if feld == "zustellung":
            return einsatz.ap if einsatz is not None and einsatz.ap > 0 else ra.ZUSTELLUNG
        if feld == "zeilenabstand":
            if werkzeug is None or werkzeug.durchmesser <= 0:
                return 0.0
            r = werkzeug.durchmesser / 2
            ae = einsatz.ae if einsatz is not None and einsatz.ae > 0 else r / 4
            return min(ae, r)
        if feld == "aufmass":
            return ra.AUFMASS
        return 0.0  # Aufmaß am Boden: die Fläche ist fertig

    def _argumente(self, werkzeug, werte, flaechen):
        """(Form, Zustellung, Zeilenabstand, Aufmaß, Flächen, Schlüsselwörter) für
        raeumen.vorschau_fuer_assistent."""
        weiter = {
            "aufmass_boden": werte["aufmass_boden"],
            "gleichlauf": werte["gleichlauf"],
            "schneidenlaenge": float(werkzeug.schneidenlaenge or 0.0),
            "vorschub": werte.get("vorschub", 0.0),
            "eintauchen": werte.get("eintauchen", 0.0),
            "stand": werte.get("materialstand"),
            "variante": werte.get("variante"),
            "freivorschub": werte.get("freivorschub", ra.FREIVORSCHUB),
            "eng_lassen": bool(werte.get("eng_lassen", False)),
            "nur_eng": float(werte.get("nur_eng", 0.0)),
        }
        if werte.get("vorbohren") and werte.get("vorbohrer"):
            weiter["vorbohren"] = werte["vorbohrer"]  # raeumen.vorschau_fuer_assistent
        return (
            ff.von_werkzeug(werkzeug),
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            list(flaechen),
            weiter,
        )

    def vorschau(self, job, werkzeug, werte, flaechen):
        *argumente, weiter = self._argumente(werkzeug, werte, flaechen)
        return ra.vorschau_fuer_assistent(job, *argumente, **weiter)

    def hintergrund(self, werkzeug, werte, flaechen):
        """(Funktion in bearbeitung_vorschau, ihre Argumente nach Dokument und Job und vor der
        Zeit) – die Vorschau in einem Nebenrechner (P-2026-10-11-23)."""
        return "raeumen", self._argumente(werkzeug, werte, flaechen)

    def ergebnis_text(self, bahn, zeit):
        lagen = tr("ba.zahl.lage") if bahn.lagen == 1 else tr("ba.zahl.lagen", n=bahn.lagen)
        if bahn.variante == "adaptiv":
            ringe = tr("ba.zahl.adaptiv")  # die Zahl seiner Bahnen sagt nichts
        elif bahn.variante == rb.STICHE:
            ringe = tr("ba.zahl.stiche", n=bahn.laeufe)  # Manuels Räumen: Stiche und Ringe
        else:
            ringe = tr("ba.zahl.ring") if bahn.ringe == 1 else tr("ba.zahl.ringe", n=bahn.ringe)
        if bahn.flaechen > 1:
            flaechen = tr("ba.zahl.flaechen", n=bahn.flaechen)
            text = tr(
                "ba.ergebnis_raeumen_flaechen",
                flaechen=flaechen,
                lagen=lagen,
                ringe=ringe,
                zeit=zeit,
            )
        else:
            text = tr("ba.ergebnis_raeumen", lagen=lagen, ringe=ringe, zeit=zeit)
        # Ringe wären schneller gewesen, halten die Last aber nicht (Manuel, 2026-10-02: die
        # schnellste gewinnt nur, wenn der ae im Rahmen bleibt) – das Fenster sagt es.
        ueberlastet = getattr(bahn, "ueberlastet", None) or {}
        schneller = [v for v in ueberlastet if 0 < bahn.zeiten.get(v, 0.0) < bahn.zeit]
        if not getattr(bahn, "haelt", True):
            last = dezimal(f"{ueberlastet.get(bahn.variante, 0.0):.1f}")
            text = tr("ba.raeumen.haelt_nicht", text=text, last=last)
        elif schneller:
            variante = min(schneller, key=lambda v: bahn.zeiten[v])
            prozent = int(round((1.0 - bahn.zeiten[variante] / bahn.zeit) * 100.0))
            last = dezimal(f"{ueberlastet[variante]:.1f}")
            text = tr("ba.raeumen.ueberlastet", text=text, prozent=prozent, last=last)
        if getattr(bahn, "gebremst", 0):
            langsam = min(p.anteil for p in bahn.punkte if not p.eilgang)
            text = tr(
                "ba.raeumen.gebremst",
                text=text,
                saetze=bahn.gebremst,
                prozent=int(round(langsam * 100.0)),
            )
        vorbohren = getattr(bahn, "vorbohren", None)
        if vorbohren is not None:
            werte = {
                "n": len(vorbohren.stellen),
                "d": groesse_zeigen(vorbohren.durchmesser, einheiten.LAENGE, 1) or "0",
                "tiefe": groesse_zeigen(vorbohren.tiefe, einheiten.LAENGE, 0) or "0",
                "zeit": dezimal(f"{vorbohren.zeit:.1f}"),
            }
            if len(vorbohren.stellen) == 1:
                text += ". " + tr("ba.raeumen.vorbohren.ein_loch", **werte)
            else:
                text += ". " + tr("ba.raeumen.vorbohren.loecher", **werte)
            # Adaptiv braucht seinen Kreis für die Helix (1,8 R) frei und fährt sie trotzdem – das
            # Loch nimmt ihr nur die Mitte ab; die Ringe tauchen ins Loch senkrecht ein.
            if vorbohren.geholfen > 0:
                text += " " + tr("ba.raeumen.vorbohren.senkrecht")
            else:
                text += " " + tr("ba.raeumen.vorbohren.helix")
            if vorbohren.zu_kurz:
                text += " " + tr("ba.raeumen.vorbohren.zu_kurz")
        return text

    def lege_an(self, job, tc, werte, flaechen):
        return ra.lege_an(
            job,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            werte["aufmass_boden"],
            werte["gleichlauf"],
            flaechen=flaechen,
            variante=werte.get("variante", "automatisch"),
            freivorschub=werte.get("freivorschub", ra.FREIVORSCHUB),
            eng_lassen=bool(werte.get("eng_lassen", False)),
            nur_eng=float(werte.get("nur_eng", 0.0)),
        )

    def aendere(self, op, tc, werte, flaechen):
        ra.aendere(
            op,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            werte["aufmass_boden"],
            werte["gleichlauf"],
            flaechen=flaechen,
            variante=werte.get("variante"),
            freivorschub=werte.get("freivorschub"),
            eng_lassen=werte.get("eng_lassen"),
            nur_eng=werte.get("nur_eng"),
        )

    def ist(self, op):
        return ra.ist_raeumen(op)

    def werte_von(self, op):
        return {
            "zustellung": float(op.Zustellung),
            "zeilenabstand": float(op.Zeilenabstand),
            "aufmass": float(op.Aufmass),
            "aufmass_boden": float(op.AufmassBoden),
            "gleichlauf": bool(op.Gleichlauf),
        }


class _RestRaeumen(_Raeumen):
    """Rest räumen (W-013 T3, B-007): räumt mit einem kleineren Fräser die Taschen, in die der
    Fräser des Räumens nicht passt – ein zweites „Räumen“, nur dort, gleich nach dem ersten.
    Welche Taschen das sind, sagt die Vorschau des Räumens (Raeumbahn.ausgelassen); Haken und
    Fräser setzt das Fenster (BearbeitungPanel._restraeumen_einrichten)."""

    kennung = "restraeumen"
    gemerkt = GEMERKT_RESTRAEUMFRAESER

    def titel(self):
        return tr("ba.restraeumen")

    def text(self):
        return tr("ba.restraeumen.text")

    def haken(self):
        return (("gleichlauf", tr("ba.gleichlauf"), tr("ba.gleichlauf.tooltip"), True),)

    def vorgeschlagen(self, form, gewaehlte):
        return False  # nach der Vorschau des Räumens: _restraeumen_einrichten

    def moeglich(self, form, gewaehlte):
        return False  # erst, wenn das Räumen eine Tasche auslässt

    def unmoeglich_text(self):
        return tr("ba.restraeumen.nicht")

    def ist(self, op):
        return False  # zum Ändern ist es ein Räumen wie jedes


class _Schlichtbahn:
    """Die Vorschau von „Schlichten danach“: der Boden (raeumen_bahn.Raeumbahn oder None) und die
    Wände (kontur_bahn-Bahn oder None) hintereinander – `punkte` für Zeit und Materialstand."""

    def __init__(
        self,
        boden,
        wand,
        waende,
        aufmass_boden,
        aufmass_wand,
        messstopp,
        ring=None,
        ringe=(),
        eng=None,
        enge=(),
    ):
        self.boden = boden
        self.wand = wand
        self.kontur_waende = list(waende) if wand is not None else []  # die fährt die Kontur
        self.waende = list(self.kontur_waende)  # alle, die auf Maß kommen (für den Satz)
        # Die Ringnuten: ihre Wände macht eine Nut „nur schlichten“ (nut_bahn.Nutwerte) auf Maß –
        # die Kontur führe nur die senkrechten (an Manuels Messspitzenhalter nicht die Fase).
        self.ring = ring
        self.ringe = list(ringe) if ring is not None else []
        # Die Nuten, in die der Fräser des Schlichtens nicht passt (am C-Ring Ø 12 in der 10 mm
        # breiten Nut – die Kontur führe an der einen Wand durch die andere, W-029): ihre Wände
        # schlichtet eine Nut „nur schlichten“ mit dem Fräser der Nut.
        self.eng = eng
        self.enge = list(enge) if eng is not None else []
        self.aufmass_boden = aufmass_boden
        self.aufmass_wand = aufmass_wand
        self.messstopp = messstopp
        self.punkte = (
            list(getattr(boden, "punkte", []))
            + list(getattr(wand, "punkte", []))
            + list(getattr(ring, "punkte", []))
            + list(getattr(eng, "punkte", []))
        )


class _SchlichtenDanach(_Strategie):
    """Schlichten danach (Spezifikation Strategien 12.4, Option A – Manuel, 2026-10-02: „genau
    so“): nach dem Räumen mit eigenem Fräser und Einsatz erst der Boden, dann die Wände, davor
    auf Wunsch ein Messstopp. Der Boden: ein Räumen ohne Aufmaß am Boden auf dem Material, das
    das Räumen ließ – eine Lage, die Ringe des Räumens oder adaptiv, mit dem Zeilenabstand des
    Felds (leer: der halbe Fräserdurchmesser); es lässt das Aufmaß an den Wänden stehen. Die
    Wände: eine Kontur mit Breite = Aufmaß (nur der Zug an der Wand) bis auf den fertigen Boden,
    in Lagen mit der Zustellung des Einsatzes – unten bleibt keine Stufe. Welche Flächen, gibt
    das Fenster vor (BearbeitungPanel._schlichten_danach_zusatz): die Böden, die das Räumen räumt,
    die Wände um sie – ohne die, die die Kontur fährt. Möglich ist der Block, sobald das Räumen
    angehakt ist (BearbeitungPanel._schlichten_danach_einrichten)."""

    kennung = "schlichtendanach"
    gemerkt = GEMERKT_SCHLICHTFRAESER
    einsatz_reihenfolge = (wz.SCHLICHTEN, wz.SCHRUPPEN, wz.PLANEN)

    def titel(self):
        return tr("ba.schlichten_danach")

    def text(self):
        return tr("ba.schlichten_danach.text")

    def fraeser_tooltip(self):
        return tr("ba.schlichten_danach.fraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.schlichten_danach.einsatz.tooltip")

    def felder(self):
        return (
            (
                "zustellung",
                tr("ba.schlichten_danach.zustellung"),
                tr("ba.schlichten_danach.zustellung.tooltip"),
            ),
            (
                "zeilenabstand",
                tr("ba.schlichten_danach.zeilenabstand"),
                tr("ba.schlichten_danach.zeilenabstand.tooltip"),
            ),
        )

    def haken(self):
        return (
            ("boden", tr("ba.schlichten_danach.boden_haken"), tr("ba.schlichten_danach.boden_haken.tooltip"), True),
            ("waende", tr("ba.schlichten_danach.waende_haken"), tr("ba.schlichten_danach.waende_haken.tooltip"), True),
            ("messstopp", tr("ba.schlichten_danach.messstopp"), tr("ba.schlichten_danach.messstopp.tooltip"), False),
        )  # fmt: skip

    def vorgeschlagen(self, form, gewaehlte):
        return False  # von Hand, wenn das Räumen Aufmaß lässt

    def moeglich(self, form, gewaehlte):
        return False  # erst mit dem Räumen: _schlichten_danach_einrichten

    def unmoeglich_text(self):
        return tr("ba.schlichten_danach.nicht")

    def vorschlag(self, feld, werkzeug, einsatz):
        if feld == "zustellung":
            if einsatz is not None and einsatz.ap > 0:
                return einsatz.ap
            return float(getattr(werkzeug, "schneidenlaenge", 0.0) or 0.0) or ra.ZUSTELLUNG
        if feld == "zeilenabstand":
            if werkzeug is None or werkzeug.durchmesser <= 0:
                return 0.0
            return werkzeug.durchmesser / 2  # der Boden: breit, er ist dünn
        return 0.0

    def vorschau(self, job, werkzeug, werte, flaechen):
        form = ff.von_werkzeug(werkzeug)
        stand = werte.get("materialstand")
        schneide = float(werkzeug.schneidenlaenge or 0.0)
        aufmass_boden = float(werte.get("aufmass_boden", 0.0))
        aufmass_wand = float(werte.get("aufmass_wand", 0.0))
        boeden = list(werte.get("boden_flaechen") or [])
        waende = list(werte.get("wand_flaechen") or [])
        boden = wand = None
        if werte["boden"] and boeden and aufmass_boden > 0:
            try:
                boden = ra.vorschau(
                    job, job.Model.Group, form, werte["zustellung"], werte["zeilenabstand"],
                    aufmass_wand, boeden, aufmass_boden=0.0, gleichlauf=werte["gleichlauf"],
                    schneidenlaenge=schneide, vorschub=werte.get("vorschub", 0.0),
                    eintauchen=werte.get("eintauchen", 0.0), stand=stand,
                )  # fmt: skip
            except mst.SchonWeg:
                boden = None
        if werte["waende"] and waende and aufmass_wand > 0:
            try:
                wand = ko.vorschau(
                    job, job.Model.Group, form, werte["zustellung"], aufmass_wand, aufmass_wand,
                    True, waende, breite=aufmass_wand, schneidenlaenge=schneide, stand=stand,
                )  # fmt: skip
            except mst.SchonWeg:
                wand = None
        ringe = list(werte.get("nut_ringe") or [])
        ring = None
        if werte["waende"] and ringe and aufmass_wand > 0:
            try:
                ring = nu.vorschau(
                    job, job.Model.Group, float(form.radius), werte["zustellung"],
                    werte["zeilenabstand"] or float(form.radius), 0.0, ringe, schlichten=True,
                    nur_schlichten=True, gleichlauf=werte["gleichlauf"], schneidenlaenge=schneide,
                    vorschub=werte.get("vorschub", 0.0), eintauchen=werte.get("eintauchen", 0.0),
                    stand=stand,
                )  # fmt: skip
            except mst.SchonWeg:
                ring = None
        enge = list(werte.get("nut_eng") or [])
        eng = None
        if werte["waende"] and enge and aufmass_wand > 0:
            r_eng = float(werte.get("nut_eng_radius") or 0.0)
            try:
                eng = nu.vorschau(
                    job, job.Model.Group, r_eng, werte["zustellung"], r_eng, 0.0, enge,
                    schlichten=True, nur_schlichten=True, gleichlauf=werte["gleichlauf"],
                    schneidenlaenge=float(werte.get("nut_eng_schneide") or 0.0),
                    vorschub=werte.get("vorschub", 0.0), stand=stand,
                )  # fmt: skip
            except mst.SchonWeg:
                eng = None
        if boden is None and wand is None and ring is None and eng is None:
            raise ValueError(tr("ba.schlichten_danach.nichts"))
        bahn = _Schlichtbahn(
            boden, wand, waende, aufmass_boden, aufmass_wand, bool(werte["messstopp"]), ring, ringe,
            eng, enge,
        )  # fmt: skip
        for da, schluessel in ((ring, "nut_ring_waende"), (eng, "nut_eng_waende")):
            if da is not None:
                dazu = list(werte.get(schluessel) or [])
                bahn.waende += [w for w in dazu if w not in bahn.waende]
        return bahn

    def ergebnis_text(self, bahn, zeit):
        einheit = einheiten.einheit(einheiten.LAENGE)

        def mm(wert):
            return f"{groesse_zeigen(wert, einheiten.LAENGE) or '0'} {einheit}"

        teile = []
        if bahn.boden is not None:
            teile.append(tr("ba.schlichten_danach.boden", aufmass=mm(bahn.aufmass_boden)))
        if bahn.waende:
            n = len(bahn.waende)
            waende = tr("ba.zahl.wand") if n == 1 else tr("ba.zahl.waende", n=n)
            teile.append(
                tr("ba.schlichten_danach.waende", waende=waende, aufmass=mm(bahn.aufmass_wand))
            )
        if len(teile) == 2:
            was = tr("ba.schlichten_danach.beides", boden=teile[0], waende=teile[1])
        else:
            was = teile[0] if teile else ""
        text = tr("ba.schlichten_danach.ergebnis", was=was, zeit=zeit)
        if bahn.messstopp:
            text = tr("ba.schlichten_danach.stopp", text=text)
        return text

    def ist(self, op):
        return False  # es legt ein Räumen und eine Kontur an – die ändert man je für sich


class _Nut(_Strategie):
    """Langlöcher in Bögen oder mit der Zickzack-Rampe (nut_bahn) – tritt auf dem Grund gegen
    Räumen und Planfräsen an, an den Wänden gegen die Kontur."""

    kennung = "nut"
    gemerkt = GEMERKT_NUTFRAESER
    vollnut = False  # der gewählte Fräser fräst die gewählten Nuten in voller Breite (Panel)

    @property
    def einsatz_reihenfolge(self):
        if self.vollnut:
            return (wz.VOLLNUT, wz.SCHRUPPEN, wz.DYNAMISCH)
        return (wz.DYNAMISCH, wz.SCHRUPPEN, wz.VOLLNUT)

    def titel(self):
        return tr("ba.nut")

    def text(self):
        return tr("ba.nut.text")

    def fraeser_tooltip(self):
        return tr("ba.nutfraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.nuteinsatz.tooltip")

    def felder(self):
        return (
            ("zustellung", tr("ba.zustellung"), tr("ba.nut.zustellung.tooltip")),
            ("zeilenabstand", tr("ba.zeilenabstand"), tr("ba.nut.zeilenabstand.tooltip")),
            ("aufmass", tr("ba.aufmass_schlichten"), tr("ba.aufmass_schlichten.tooltip")),
        )

    def haken(self):
        return (
            # Aus vorbelegt: Das Aufmaß bleibt stehen, „Schlichten danach“ (eigene Operation, mit
            # Messstopp) macht die Wand fertig (Manuel, 2026-10-17: „schruppen, messen, schlichten
            # … ist meist der Ablauf“).
            (
                "schlichten",
                tr("ba.nut.wand_schlichten"),
                tr("ba.nut.wand_schlichten.tooltip"),
                False,
            ),
            ("gleichlauf", tr("ba.nut.gleichlauf"), tr("ba.nut.gleichlauf.tooltip"), True),
            # Neu als Haken, angehakt (Manuel, 2026-10-16: „gleich und gegenlauf … kaum
            # schnellvorschub … meist schneidet“).
            ("wellen", tr("ba.nut.wellen"), tr("ba.nut.wellen.tooltip"), True),
            # Manuel, 2026-10-25: „immer wenn man eintauchen muss ists gut wenn vorgebohrt ist“.
            ("vorbohren", tr("ba.nut.vorbohren"), tr("ba.nut.vorbohren.tooltip"), True),
        )

    def haken_gesperrt(self, feld, block):
        if feld != "vorbohren":
            return None
        fraeser = block.fraeser()
        if fraeser is None or block.panel._vorbohrer_liste(fraeser):
            return None
        return tr(
            "ba.nut.vorbohren.kein_bohrer",
            d=groesse_zeigen(fraeser.durchmesser, einheiten.LAENGE, 1) or "0",
        )

    def passt(self, form, name):
        # Eine Fase an der Nut (am Messspitzenhalter außen am Ringgrund) fräst der Block „Fase“ –
        # angeklickt allein holte sie sonst die ganze Ringnut (W-037).
        return nb.ist_nut(form, name) and not _fase_fuer_block(form, name)

    def flaechen_fuer(self, form, gewaehlte):
        """Der Grund, wie gewählt – eine Wand aber meint die ganze Nut: alle ihre Wände (so
        auch bei der Kontur, die gegen sie antritt)."""
        return nb.ganze_nuten(form, [n for n in gewaehlte if self.passt(form, n)])

    def vorgeschlagen(self, form, gewaehlte):
        """Von sich aus, wenn alle gewählten Flächen zu Nuten gehören – nur Gründe oder nur
        Wände; beides zusammen ist die Folge Räumen und Kontur. Steht neben dem Grund einer Nut
        auch anderes in der Wahl („Alles aus dieser Aufspannung“), fräst die Nut ihren Grund –
        sonst blieb sie liegen, wenn der Fräser des Räumens nicht hineinpasst (W-034: die
        Ringnut des C-Rings mit Ø 12 in 10 mm)."""
        if not gewaehlte:
            return False
        if not all(self.passt(form, n) for n in gewaehlte):
            return any(self.passt(form, n) and nb.ist_grund(form, n) for n in gewaehlte)
        gruende = [n for n in gewaehlte if nb.ist_grund(form, n)]
        return not gruende or len(gruende) == len(gewaehlte)

    def unmoeglich_text(self):
        return tr("ba.nut.keine")

    def vorschlag(self, feld, werkzeug, einsatz):
        if feld == "zustellung":
            return einsatz.ap if einsatz is not None and einsatz.ap > 0 else nu.ZUSTELLUNG
        if feld == "zeilenabstand":
            if werkzeug is None or werkzeug.durchmesser <= 0:
                return 0.0
            r = werkzeug.durchmesser / 2
            ae = einsatz.ae if einsatz is not None and einsatz.ae > 0 else r / 4
            return min(ae, r)
        return nu.AUFMASS

    def vorschau(self, job, werkzeug, werte, flaechen):
        form = ff.von_werkzeug(werkzeug)
        if form is None or vp.ebener_radius(form) <= 0:
            raise ValueError(tr("nt.fehler.form"))
        return nu.vorschau(
            job,
            job.Model.Group,
            float(form.radius),
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            flaechen,
            schlichten=werte["schlichten"],
            gleichlauf=werte["gleichlauf"],
            wellen=werte.get("wellen", False),
            schneidenlaenge=float(werkzeug.schneidenlaenge or 0.0),
            eintauchwinkel=_eintauchwinkel(werkzeug),
            vorschub=werte.get("vorschub", 0.0),
            eintauchen=werte.get("eintauchen", 0.0),
            stand=werte.get("materialstand"),
            eintauchen_bei=werte.get("eintauchen_bei"),
            vorbohren=werte.get("vorbohrer_liste") if werte.get("vorbohren") else None,
        )

    def ergebnis_text(self, bahn, zeit):
        nuten = tr("ba.zahl.nut") if bahn.nuten == 1 else tr("ba.zahl.nuten", n=bahn.nuten)
        if bahn.vollnut == bahn.nuten:
            text = tr("ba.ergebnis_vollnut", nuten=nuten, zeit=zeit)
        else:
            lagen = tr("ba.zahl.lage") if bahn.lagen == 1 else tr("ba.zahl.lagen", n=bahn.lagen)
            boegen = (
                tr("ba.zahl.bogen") if bahn.boegen == 1 else tr("ba.zahl.boegen", n=bahn.boegen)
            )
            text = tr("ba.ergebnis_nut", nuten=nuten, lagen=lagen, boegen=boegen, zeit=zeit)
        vorbohren = getattr(bahn, "vorbohren", None)
        if vorbohren is not None:
            loecher = vorbohren.je_loch()
            d = " / ".join(
                groesse_zeigen(x, einheiten.LAENGE, 1) or "0"
                for x in sorted({lo[3] for lo in loecher})
            )
            werte = {
                "n": len(loecher),
                "d": d,
                "tiefe": groesse_zeigen(vorbohren.tiefe, einheiten.LAENGE, 0) or "0",
                "zeit": dezimal(f"{vorbohren.zeit:.1f}"),
            }
            if len(loecher) == 1:
                text += ". " + tr("ba.raeumen.vorbohren.ein_loch", **werte)
            else:
                text += ". " + tr("ba.raeumen.vorbohren.loecher", **werte)
            text += " " + tr("ba.nut.vorbohren.senkrecht")
            if vorbohren.zu_kurz:
                text += " " + tr("ba.raeumen.vorbohren.zu_kurz")
        return text

    def lege_an(self, job, tc, werte, flaechen):
        return nu.lege_an(
            job,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            schlichten=werte["schlichten"],
            gleichlauf=werte["gleichlauf"],
            flaechen=flaechen,
            eintauchwinkel=werte.get("eintauchwinkel"),
            eintauchstellen=werte.get("eintauchen_bei"),
            wellen=werte.get("wellen", False),
        )

    def aendere(self, op, tc, werte, flaechen):
        nu.aendere(
            op,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            schlichten=werte["schlichten"],
            gleichlauf=werte["gleichlauf"],
            flaechen=flaechen,
            eintauchwinkel=werte.get("eintauchwinkel"),
            eintauchstellen=werte.get("eintauchen_bei"),
            wellen=werte.get("wellen", False),
        )

    def ist(self, op):
        return nu.ist_nut(op)

    def werte_von(self, op):
        return {
            "zustellung": float(op.Zustellung),
            "zeilenabstand": float(op.Zeilenabstand),
            "aufmass": float(op.Aufmass),
            "schlichten": bool(op.Schlichten),
            "gleichlauf": bool(op.Gleichlauf),
            "wellen": bool(getattr(op, "Wellen", False)),
            "eintauchen_bei": nu.eintauchstellen(op),
        }


class _Kontur(_Strategie):
    kennung = "kontur"
    aufloesung = ko.kb.SCHRITT
    gemerkt = GEMERKT_KONTURFRAESER
    einsatz_reihenfolge = (wz.SCHRUPPEN, wz.SCHLICHTEN, wz.PLANEN)

    def titel(self):
        return tr("ba.kontur")

    def text(self):
        return tr("ba.kontur.text")

    def fraeser_tooltip(self):
        return tr("ba.konturfraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.kontureinsatz.tooltip")

    def felder(self):
        return (
            ("zustellung", tr("ba.zustellung"), tr("ba.kontur.zustellung.tooltip")),
            ("zeilenabstand", tr("ba.zeilenabstand"), tr("ba.kontur.zeilenabstand.tooltip")),
            ("aufmass", tr("ba.aufmass_schlichten"), tr("ba.aufmass_schlichten.tooltip")),
            ("breite", tr("ba.breite"), tr("ba.breite.tooltip")),
        )

    def haken(self):
        return (("schlichten", tr("ba.schlichten"), tr("ba.schlichten.tooltip"), True),)

    def passt(self, form, name):
        return bool(kb.waende(form, [name]))

    def flaechen_fuer(self, form, gewaehlte):
        """Die gewählten Wände – die Wand einer Nut mit allen Wänden der Nut, wie bei der Nut,
        gegen die die Kontur dort antritt (eine Wand meint die Nut)."""
        return nb.ganze_nuten(form, [n for n in gewaehlte if self.passt(form, n)])

    def unmoeglich_text(self):
        return tr("ba.kontur.keine_wand")

    def vorschlag(self, feld, werkzeug, einsatz):
        if feld == "zustellung":
            return einsatz.ap if einsatz is not None and einsatz.ap > 0 else ko.ZUSTELLUNG
        if feld == "zeilenabstand":
            if werkzeug is None:
                return 0.0
            return vplan.zeilenabstand_vorschlag(werkzeug, einsatz, ff.von_werkzeug(werkzeug))
        if feld == "aufmass":
            return ko.AUFMASS
        return 0.0  # Breite: so viel, wie das Rohteil sagt

    def platzhalter(self, feld, werkzeug, einsatz):
        if feld == "breite":
            return tr("ba.breite.leer")
        return super().platzhalter(feld, werkzeug, einsatz)

    def _argumente(self, werkzeug, werte, flaechen):
        """(Argumente, Schlüsselwörter) für kontur.vorschau nach Job und Modell."""
        return (
            ff.von_werkzeug(werkzeug),
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            werte["schlichten"],
            list(flaechen),
            werte["breite"],
        ), {
            "schneidenlaenge": float(werkzeug.schneidenlaenge or 0.0),
            "stand": werte.get("materialstand"),
        }

    def vorschau(self, job, werkzeug, werte, flaechen):
        argumente, weiter = self._argumente(werkzeug, werte, flaechen)
        return ko.vorschau(job, job.Model.Group, *argumente, **weiter)

    def hintergrund(self, werkzeug, werte, flaechen):
        """Die Vorschau in einem Nebenrechner (bearbeitung_vorschau.strategie)."""
        return "strategie", ("kontur", *self._argumente(werkzeug, werte, flaechen))

    def ergebnis_text(self, bahn, zeit):
        lagen = tr("ba.zahl.lage") if bahn.lagen == 1 else tr("ba.zahl.lagen", n=bahn.lagen)
        bahnen = tr("ba.zahl.bahn") if bahn.bahnen == 1 else tr("ba.zahl.bahnen", n=bahn.bahnen)
        if bahn.konturen > 1:
            konturen = tr("ba.zahl.konturen", n=bahn.konturen)
            return tr(
                "ba.ergebnis_konturen", konturen=konturen, lagen=lagen, bahnen=bahnen, zeit=zeit
            )
        return tr("ba.ergebnis_kontur", lagen=lagen, bahnen=bahnen, zeit=zeit)

    def lege_an(self, job, tc, werte, flaechen):
        return ko.lege_an(
            job,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            werte["schlichten"],
            werte["breite"],
            flaechen=flaechen,
        )

    def aendere(self, op, tc, werte, flaechen):
        ko.aendere(
            op,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            werte["schlichten"],
            werte["breite"],
            flaechen=flaechen,
        )

    def ist(self, op):
        return ko.ist_kontur(op) and not ko.ist_rest(op)

    def werte_von(self, op):
        return {
            "zustellung": float(op.Zustellung),
            "zeilenabstand": float(op.Zeilenabstand),
            "aufmass": float(op.Aufmass),
            "breite": float(op.Breite),
            "schlichten": bool(op.Schlichten),
        }


class _Bohren(_Strategie):
    """FreeCADs Bohren mit einem Bohrer aus der Werkzeugverwaltung (bohren)."""

    kennung = "bohren"
    gemerkt = GEMERKT_BOHRER
    einsatz_reihenfolge = (wz.BOHREN,)

    def titel(self):
        return tr("ba.bohren")

    def text(self):
        return tr("ba.bohren.text")

    def fraeser_tooltip(self):
        return tr("ba.bohrer.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.bohren_einsatz.tooltip")

    def felder(self):
        return (("hub", tr("ba.bohren.hub"), tr("ba.bohren.hub.tooltip")),)

    def werkzeug_passt(self, werkzeug):
        return werkzeug.art == wz.BOHRER

    def passt(self, form, name):
        return any(b.durch or b.spitze > 0 for b in bb.bohrungen(form, [name]))

    def unmoeglich_text(self):
        return tr("ba.bohren.nicht")

    def vorschlag(self, feld, werkzeug, einsatz):
        return 0.0  # Hub: automatisch

    def platzhalter(self, feld, werkzeug, einsatz):
        return tr("ba.bohren.hub.leer")

    def vorschau(self, job, werkzeug, werte, flaechen):
        """Die Bohrungen seines Bohrers – und die der weiteren Bohrer (`nebenbohrer`,
        _nebenbohrer) dazu: eine Bahn, die Zeiten zusammen, `dazu` [(T-Nummer, Bohrungen)]."""
        neben = werte.get("nebenbohrer") or []
        andere = {n for gruppe in neben for n in gruppe["flaechen"]}
        bahn = bh.vorschau(
            job,
            werkzeug,
            [f for f in flaechen if f not in andere],
            werte.get("vorschub", 0.0),
            werte["hub"],
            reiben=werte.get("reiben", False),
        )
        dazu = []
        for gruppe in neben:
            weitere = bh.vorschau(
                job, gruppe["werkzeug"], gruppe["flaechen"], gruppe["vorschub"], werte["hub"]
            )
            bahn = bh.Bohrbahn(
                punkte=bahn.punkte + weitere.punkte,
                bohrungen=bahn.bohrungen + weitere.bohrungen,
                hube=bahn.hube + weitere.hube,
                z_min=min(bahn.z_min, weitere.z_min),
                zeit=bahn.zeit + weitere.zeit,
            )
            dazu.append((wz.nummer_text(gruppe["werkzeug"]), weitere.bohrungen))
        bahn.dazu = dazu
        return bahn

    def ergebnis_text(self, bahn, zeit):
        bohrungen = (
            tr("ba.zahl.bohrung")
            if bahn.bohrungen == 1
            else tr("ba.zahl.bohrungen", n=bahn.bohrungen)
        )
        hube = tr("ba.zahl.hub") if bahn.hube == 1 else tr("ba.zahl.hube", n=bahn.hube)
        text = tr("ba.ergebnis_bohren", bohrungen=bohrungen, hube=hube, zeit=zeit)
        dazu = getattr(bahn, "dazu", None)
        if dazu:
            liste = ", ".join(
                f"{nummer}: {tr('ba.zahl.bohrung') if n == 1 else tr('ba.zahl.bohrungen', n=n)}"
                for nummer, n in dazu
            )
            text = tr("ba.bohren.dazu", text=text, liste=liste)
        return text

    def lege_an(self, job, tc, werte, flaechen):
        """Die Bohrungen seines Bohrers; die der weiteren Bohrer legt
        BearbeitungPanel._nebenbohrer_anlegen danach an."""
        andere = {n for gruppe in werte.get("nebenbohrer") or [] for n in gruppe["flaechen"]}
        return bh.lege_an(job, tc, [f for f in flaechen if f not in andere], werte["hub"])

    def ist(self, op):
        return False  # FreeCADs eigene Operation – sie ändert FreeCADs Fenster


class _Bohrung(_Strategie):
    kennung = "bohrung"
    gemerkt = GEMERKT_BOHRFRAESER
    einsatz_reihenfolge = (wz.SCHRUPPEN, wz.SCHLICHTEN, wz.PLANEN)

    def titel(self):
        return tr("ba.bohrung")

    def text(self):
        return tr("ba.bohrung.text")

    def fraeser_tooltip(self):
        return tr("ba.bohrfraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.bohreinsatz.tooltip")

    def felder(self):
        return (
            ("zustellung", tr("ba.zustellung"), tr("ba.bohrung.zustellung.tooltip")),
            ("zeilenabstand", tr("ba.zeilenabstand"), tr("ba.bohrung.zeilenabstand.tooltip")),
            ("aufmass", tr("ba.aufmass_schlichten"), tr("ba.aufmass_schlichten.tooltip")),
        )

    def haken(self):
        return (
            ("schlichten", tr("ba.wand_schlichten"), tr("ba.wand_schlichten.tooltip"), True),
            ("gleichlauf", tr("ba.gleichlauf"), tr("ba.gleichlauf.tooltip"), True),
        )

    def passt(self, form, name):
        return bb.ist_bohrung(form, name) or bb.bohrung_ueber_boden(form, name) is not None

    def flaechen_fuer(self, form, gewaehlte):
        """Die gewählten Bohrungen – ein gewählter Boden meint die Bohrung über ihm (seit
        P-2026-10-16-13 nimmt das Planfräsen ihn nicht mehr, und das Räumen passt in ein Loch
        wenig größer als der Fräser nicht hinein: am Loch Ø 16 in der Schräge mit Ø 12)."""
        namen = []
        for name in gewaehlte:
            wand = name if bb.ist_bohrung(form, name) else bb.bohrung_ueber_boden(form, name)
            if wand is not None and wand not in namen:
                namen.append(wand)
        return namen

    def unmoeglich_text(self):
        return tr("ba.bohrung.keine")

    def vorschlag(self, feld, werkzeug, einsatz):
        if feld == "zustellung":
            return einsatz.ap if einsatz is not None and einsatz.ap > 0 else bo.ZUSTELLUNG
        if feld == "zeilenabstand":
            if werkzeug is None or werkzeug.durchmesser <= 0:
                return 0.0
            r = werkzeug.durchmesser / 2
            ae = einsatz.ae if einsatz is not None and einsatz.ae > 0 else r / 4
            return min(ae, r)
        return bo.AUFMASS

    def vorschau(self, job, werkzeug, werte, flaechen):
        form = ff.von_werkzeug(werkzeug)
        if form is None or vp.ebener_radius(form) <= 0:
            raise ValueError(tr("bo.fehler.form"))
        return bo.vorschau(
            job,
            job.Model.Group,
            float(form.radius),
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            flaechen,
            schlichten=werte["schlichten"],
            gleichlauf=werte["gleichlauf"],
            schneidenlaenge=float(werkzeug.schneidenlaenge or 0.0),
            eintauchwinkel=_eintauchwinkel(werkzeug),
            vorschub=werte.get("vorschub", 0.0),
            eintauchen=werte.get("eintauchen", 0.0),
        )

    def ergebnis_text(self, bahn, zeit):
        bohrungen = (
            tr("ba.zahl.bohrung")
            if bahn.bohrungen == 1
            else tr("ba.zahl.bohrungen", n=bahn.bohrungen)
        )
        lagen = tr("ba.zahl.lage") if bahn.lagen == 1 else tr("ba.zahl.lagen", n=bahn.lagen)
        text = tr(
            "ba.ergebnis_bohrung",
            bohrungen=bohrungen,
            lagen=lagen,
            umlaeufe=f"{bahn.umlaeufe:.0f}",
            zeit=zeit,
        )
        zu_klein = list(getattr(bahn, "zu_klein", ()) or ())
        if zu_klein:
            # Die kleineren bleiben dem Bohrer – der Satz sagt, welche (sie zählen nicht als fertig).
            namen = ", ".join(zu_klein[:4]) + (" …" if len(zu_klein) > 4 else "")
            text = tr("ba.bohrung.zu_klein", text=text, flaechen=namen)
        return text

    def lege_an(self, job, tc, werte, flaechen):
        return bo.lege_an(
            job,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            schlichten=werte["schlichten"],
            gleichlauf=werte["gleichlauf"],
            flaechen=flaechen,
            eintauchwinkel=werte.get("eintauchwinkel"),
        )

    def aendere(self, op, tc, werte, flaechen):
        bo.aendere(
            op,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            schlichten=werte["schlichten"],
            gleichlauf=werte["gleichlauf"],
            flaechen=flaechen,
            eintauchwinkel=werte.get("eintauchwinkel"),
        )

    def ist(self, op):
        return bo.ist_bohrungsfraesen(op)

    def werte_von(self, op):
        return {
            "zustellung": float(op.Zustellung),
            "zeilenabstand": float(op.Zeilenabstand),
            "aufmass": float(op.Aufmass),
            "schlichten": bool(op.Schlichten),
            "gleichlauf": bool(op.Gleichlauf),
        }


class _Gewinde(_Strategie):
    """FreeCADs Gewinde mit einem Gewindebohrer aus der Werkzeugverwaltung (gewinde) – nach
    dem Kernloch, gegen keine Strategie im Wettbewerb; den Haken setzt man selbst."""

    kennung = "gewinde"
    gemerkt = GEMERKT_GEWINDEBOHRER
    einsatz_reihenfolge = (wz.GEWINDEBOHREN,)

    def titel(self):
        return tr("ba.gewinde")

    def text(self):
        return tr("ba.gewinde.text")

    def fraeser_tooltip(self):
        return tr("ba.gewindebohrer.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.gewinde_einsatz.tooltip")

    def werkzeug_passt(self, werkzeug):
        return wz.gewindebohrer(werkzeug.art) and werkzeug.steigung > 0

    def passt(self, form, name):
        return bb.ist_bohrung(form, name)

    def vorgeschlagen(self, form, gewaehlte):
        return False  # ob eine Bohrung ein Gewinde bekommt, sagt das Modell nicht

    def unmoeglich_text(self):
        return tr("ba.gewinde.nicht")

    def vorschau(self, job, werkzeug, werte, flaechen):
        steigung = float(werkzeug.steigung or 0.0)
        drehzahl = werte.get("vorschub", 0.0) / steigung if steigung > 0 else 0.0
        return gw.vorschau(job, werkzeug, flaechen, drehzahl)

    def ergebnis_text(self, bahn, zeit):
        gewinde = tr("ba.zahl.gewinde", n=bahn.gewinde, name=bahn.name)
        return tr("ba.ergebnis_gewinde", gewinde=gewinde, zeit=zeit)

    def lege_an(self, job, tc, werte, flaechen):
        return gw.lege_an(job, tc, flaechen)

    def ist(self, op):
        return False  # FreeCADs eigene Operation – sie ändert FreeCADs Fenster


class _Gewindefraesen(_Strategie):
    """„Gewinde fräsen“ mit einem Gewindefräser aus der Werkzeugverwaltung (gewindefraesen) –
    nach dem Kernloch, statt „Gewinde bohren“; den Haken setzt man selbst."""

    kennung = "gewindefraesen"
    gemerkt = GEMERKT_GEWINDEFRAESER
    einsatz_reihenfolge = (wz.GEWINDEFRAESEN,)

    def titel(self):
        return tr("ba.gewindefraesen")

    def text(self):
        return tr("ba.gewindefraesen.text")

    def fraeser_tooltip(self):
        return tr("ba.gewindefraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.gewindefraesen_einsatz.tooltip")

    def haken(self):
        return (("gleichlauf", tr("ba.gleichlauf"), tr("ba.gleichlauf.tooltip"), True),)

    def werkzeug_passt(self, werkzeug):
        return werkzeug.art == wz.GEWINDEFRAESER and (werkzeug.steigung or 0.0) > 0

    def passt(self, form, name):
        return bb.ist_bohrung(form, name)

    def vorgeschlagen(self, form, gewaehlte):
        return False  # ob eine Bohrung ein Gewinde bekommt, sagt das Modell nicht

    def unmoeglich_text(self):
        return tr("ba.gewindefraesen.nicht")

    def vorschau(self, job, werkzeug, werte, flaechen):
        return gf.vorschau(
            job,
            werkzeug,
            flaechen,
            gleichlauf=werte["gleichlauf"],
            vorschub=werte.get("vorschub", 0.0),
        )

    def ergebnis_text(self, bahn, zeit):
        gewinde = bahn.gewinde_text()
        if abs(bahn.umlaeufe - 1.0) < 0.05:
            return tr("ba.ergebnis_gewindefraesen.einer", gewinde=gewinde, zeit=zeit)
        umlaeufe = f"{bahn.umlaeufe:.1f}".rstrip("0").rstrip(".")
        return tr(
            "ba.ergebnis_gewindefraesen",
            gewinde=gewinde,
            umlaeufe=dezimal(umlaeufe),
            zeit=zeit,
        )

    def lege_an(self, job, tc, werte, flaechen):
        werkzeug = werte["werkzeug"]
        return gf.lege_an(
            job,
            tc,
            float(werkzeug.steigung),
            gf.zaehne_von(werkzeug),
            gleichlauf=werte["gleichlauf"],
            flaechen=flaechen,
        )

    def aendere(self, op, tc, werte, flaechen):
        werkzeug = werte["werkzeug"]
        gf.aendere(
            op,
            tc,
            float(werkzeug.steigung),
            gf.zaehne_von(werkzeug),
            gleichlauf=werte["gleichlauf"],
            flaechen=flaechen,
        )

    def ist(self, op):
        return gf.ist_gewindefraesen(op)

    def werte_von(self, op):
        return {"gleichlauf": bool(op.Gleichlauf)}


class _Fase(_Strategie):
    """Angeklickte Fasen (fase, W-037): der Schaftfräser in Stufen, ein Fasenfräser ihres Winkels
    in einer Runde – gegen keine Strategie im Wettbewerb, vor dem Entgraten. Den Haken setzt eine
    angeklickte Fase; „Alles aus dieser Aufspannung“ nimmt sie nicht mit (Manuel, 2026-10-24: „genau
    wenn sie angeklickt ist und man nur einen schaftfräser hat dann muss der das in stufen machen
    ... wenn nicht wird sie nicht gemacht“)."""

    kennung = "fase"
    aufloesung = fb.SCHRITT
    gemerkt = GEMERKT_FASE
    einsatz_reihenfolge = (wz.SCHLICHTEN, wz.SCHRUPPEN, wz.FASEN)

    def titel(self):
        return tr("ba.fase")

    def text(self):
        return tr("ba.fase.text")

    def fraeser_tooltip(self):
        return tr("ba.fase.fraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.fase.einsatz.tooltip")

    def felder(self):
        return (
            ("stufe", tr("ba.fase.stufe"), tr("ba.fase.stufe.tooltip")),
            ("zustellung", tr("ba.fase.zustellung"), tr("ba.fase.zustellung.tooltip")),
        )

    def werkzeug_passt(self, werkzeug):
        return fa.werkzeug_passt(werkzeug)

    def passt(self, form, name):
        return _fase_fuer_block(form, name)

    def unmoeglich_text(self):
        return tr("ba.fase.nicht")

    def vorschlag(self, feld, werkzeug, einsatz):
        if feld == "stufe":
            return fb.STUFE
        if feld == "zustellung":
            return einsatz.ap if einsatz is not None and einsatz.ap > 0 else fb.ZUSTELLUNG
        return 0.0

    def vorschau(self, job, werkzeug, werte, flaechen):
        return fa.vorschau(
            job,
            werkzeug,
            werte["stufe"],
            werte["zustellung"],
            flaechen,
            stand=werte.get("materialstand"),
        )

    def ergebnis_text(self, bahn, zeit):
        def fasen(n):
            return tr("ba.zahl.fase") if n == 1 else tr("ba.zahl.fasen", n=n)

        lagen = tr("ba.zahl.lage") if bahn.lagen == 1 else tr("ba.zahl.lagen", n=bahn.lagen)
        if bahn.ausgelassen:
            return tr(
                "ba.ergebnis_fase_ausgelassen",
                fasen=fasen(bahn.fasen),
                lagen=lagen,
                zeit=zeit,
                ausgelassen=fasen(bahn.ausgelassen),
            )
        return tr("ba.ergebnis_fase", fasen=fasen(bahn.fasen), lagen=lagen, zeit=zeit)

    def lege_an(self, job, tc, werte, flaechen):
        return fa.lege_an(job, tc, werte["stufe"], werte["zustellung"], flaechen=flaechen)

    def aendere(self, op, tc, werte, flaechen):
        fa.aendere(op, tc, werte["stufe"], werte["zustellung"], flaechen=flaechen)

    def ist(self, op):
        return fa.ist_fase_op(op)

    def werte_von(self, op):
        return {"stufe": float(op.Stufe), "zustellung": float(op.Zustellung)}


class _Entgraten(_Strategie):
    """Ein Fasenfräser bricht die Oberkanten der gewählten Wände (entgraten) – zuletzt, gegen
    keine Strategie im Wettbewerb; den Haken setzt man selbst."""

    kennung = "entgraten"
    aufloesung = eg.eb.SCHRITT
    gemerkt = GEMERKT_FASENFRAESER
    einsatz_reihenfolge = (wz.FASEN, wz.VERRUNDEN)

    def titel(self):
        return tr("ba.entgraten")

    def text(self):
        return tr("ba.entgraten.text")

    def fraeser_tooltip(self):
        return tr("ba.fasenfraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.fasen_einsatz.tooltip")

    def felder(self):
        return (
            ("breite", tr("ba.entgraten.breite"), tr("ba.entgraten.breite.tooltip")),
            ("tiefer", tr("ba.entgraten.tiefer"), tr("ba.entgraten.tiefer.tooltip")),
        )

    def werkzeug_passt(self, werkzeug):
        return werkzeug.art in (wz.FASENFRAESER, wz.RADIENFRAESER)

    def passt(self, form, name):
        return eb.hat_oberkanten(form, name) or eb.hat_fasen(form, name)

    def vorgeschlagen(self, form, gewaehlte):
        # Eine scharfe Kante: ob sie eine Fase bekommt, sagt die Zeichnung. Eine gezeichnete
        # Rundung sagt das Modell – außer einer Senkung über einer Bohrung (die senkt „Senken“).
        # Gezeichnete Fasen fräst der Block „Fase“, und nur angeklickt (Manuel, 2026-10-24: „wenn
        # sie angeklickt ist … wenn nicht wird sie nicht gemacht“); den Haken hier setzt man selbst.
        return any(
            not sk.ist_senkung(form, f"Face{f.nummer + 1}")
            and not fb.ist_fase(form, f"Face{f.nummer + 1}")
            for f in eb._gewaehlte_fasen(form, gewaehlte)
        )

    def unmoeglich_text(self):
        return tr("ba.entgraten.nicht")

    def vorschlag(self, feld, werkzeug, einsatz):
        if feld == "breite":
            return eb.BREITE
        if feld == "tiefer":
            return eb.TIEFER
        return 0.0

    def vorschau(self, job, werkzeug, werte, flaechen):
        return eg.vorschau(job, werkzeug, werte["breite"], werte["tiefer"], flaechen)

    def ergebnis_text(self, bahn, zeit):
        def zuege(n):
            return tr("ba.zahl.kantenzug") if n == 1 else tr("ba.zahl.kantenzuege", n=n)

        if bahn.ausgelassen:
            text = tr(
                "ba.ergebnis_entgraten_ausgelassen",
                zuege=zuege(bahn.ketten),
                zeit=zeit,
                ausgelassen=zuege(bahn.ausgelassen),
            )
        else:
            text = tr("ba.ergebnis_entgraten", zuege=zuege(bahn.ketten), zeit=zeit)
        modell = getattr(bahn, "modell", ())
        einheit = einheiten.einheit(einheiten.LAENGE)
        fasen_ = [groesse_zeigen(b, einheiten.LAENGE, 2) or "0" for a, b in modell if a == "fase"]
        rund = [groesse_zeigen(r, einheiten.LAENGE, 2) or "0" for a, r in modell if a != "fase"]
        if fasen_:
            text += tr("ba.entgraten.aus_modell", breite=f"{', '.join(fasen_)} {einheit}")
        if rund:
            text += tr("ba.entgraten.rundung_modell", radius=", ".join(rund))
        return text

    def lege_an(self, job, tc, werte, flaechen):
        return eg.lege_an(job, tc, werte["breite"], werte["tiefer"], flaechen=flaechen)

    def aendere(self, op, tc, werte, flaechen):
        eg.aendere(op, tc, werte["breite"], werte["tiefer"], flaechen=flaechen)

    def ist(self, op):
        return eg.ist_entgraten(op)

    def werte_von(self, op):
        return {"breite": float(op.Breite), "tiefer": float(op.Tiefer)}


class _Entgraten3D(_Strategie):
    """Fasen an Kanten im Raum (W-015 S5; Manuel, 2026-10-04: „nicht das Werkstück beschädigen“,
    „nicht nur auf den 45-Grad-Fräser“, „auch auf einer Dreiachs-Maschine“): an einer 5-Achs-Maschine
    angestellt (Fasenfräser oder ebene Stirn), sonst der Fasenfräser senkrecht – den Haken setzt
    man selbst."""

    kennung = "entgraten3d"
    gemerkt = GEMERKT_ENTGRATEN3D
    nimmt_kanten = True
    einsatz_reihenfolge = (wz.FASEN, wz.SCHLICHTEN)
    bevorzugt = wz.FASENFRAESER
    aufloesung = e3op.e3.SCHRITT  # der Schritt auf der Kante

    def aufloesung_erklaerung(self, vorschlag):
        return tr("ba.aufloesung.kante.tooltip", vorschlag=vorschlag)

    def titel(self):
        return tr("ba.e3")

    def text(self):
        return tr("ba.e3.text")

    def fraeser_tooltip(self):
        return tr("ba.e3.fraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.fasen_einsatz.tooltip")

    def felder(self):
        return (("breite", tr("ba.e3.breite"), tr("ba.e3.breite.tooltip")),)

    def haken(self):
        return (("fuenf", tr("ba.e3.fuenf"), tr("ba.e3.fuenf.tooltip"), True),)

    def haken_verborgen(self, feld, block):
        return feld == "fuenf" and not block.panel._fuenfachs()

    def werkzeug_passt(self, werkzeug):
        return werkzeug.art == wz.FASENFRAESER or werkzeug.art in e3op.FLACH

    def passt(self, form, name):
        return e3op.passt(form, name)

    def vorgeschlagen(self, form, gewaehlte):
        # Welche Kante eine Fase bekommt, sagt die Zeichnung – hat man Kanten angeklickt, dann
        # dafür (Manuel, 2026-10-05: „Kanten anklicken muss sein“).
        return any(str(n).startswith("Edge") and self.passt(form, n) for n in gewaehlte)

    def unmoeglich_text(self):
        return tr("ba.e3.keine")

    def vorschlag(self, feld, werkzeug, einsatz):
        return e3op.BREITE if feld == "breite" else 0.0

    def _fuenf(self, werte):
        return bool(werte.get("fuenf", False))

    def vorschau(self, job, werkzeug, werte, flaechen):
        return e3op.vorschau(
            job,
            werkzeug,
            werte["breite"],
            flaechen,
            fuenf=self._fuenf(werte),
            vorschub=werte.get("vorschub", 0.0),
        )

    def zeit(self, bahn, vorschub, eintauchen):
        return bahn.laenge / vorschub if vorschub > 0 else bahn.zeit

    def ergebnis_text(self, bahn, zeit):
        kanten_ = tr("ba.e3.kante") if bahn.kanten == 1 else tr("ba.e3.kanten", n=bahn.kanten)
        text = tr("ba.ergebnis_e3", kanten=kanten_, zeit=zeit)
        if bahn.schenkel[1] - bahn.schenkel[0] > 0.01:
            von = groesse_zeigen(bahn.schenkel[0], einheiten.LAENGE, 2) or "0"
            bis = groesse_zeigen(bahn.schenkel[1], einheiten.LAENGE, 2) or "0"
            text += tr("ba.e3.schenkel", von=von, bis=bis)
        if bahn.ausgelassen >= 0.5:
            text += " " + e3op.ausgelassen_text(bahn)
        return text

    def lege_an(self, job, tc, werte, flaechen):
        return e3op.lege_an(job, tc, werte["breite"], self._fuenf(werte), flaechen=flaechen)

    def aendere(self, op, tc, werte, flaechen):
        e3op.aendere(op, tc, werte["breite"], self._fuenf(werte), flaechen=flaechen)

    def ist(self, op):
        return e3op.ist_entgraten3d(op)

    def werte_von(self, op):
        return {"breite": float(op.Fasenbreite), "fuenf": bool(op.FuenfAchsen)}


def _kegel_ergebnis(bahn, zeit):
    stellen = tr("ba.zahl.stelle") if bahn.stellen == 1 else tr("ba.zahl.stellen", n=bahn.stellen)
    tiefe = groesse_zeigen(bahn.tiefe, einheiten.LAENGE, 2) or "0"
    return tr(
        "ba.ergebnis_kegel",
        stellen=stellen,
        tiefe=f"{tiefe} {einheiten.einheit(einheiten.LAENGE)}",
        zeit=zeit,
    )


class _Zentrieren(_Strategie):
    """FreeCADs Bohren mit einem NC-Anbohrer über den Bohrungen (senken) – vor dem Bohren, gegen
    keine Strategie im Wettbewerb; den Haken setzt man selbst."""

    kennung = "zentrieren"
    gemerkt = GEMERKT_ANBOHRER
    einsatz_reihenfolge = (wz.ZENTRIEREN,)

    def titel(self):
        return tr("ba.zentrieren")

    def text(self):
        return tr("ba.zentrieren.text")

    def fraeser_tooltip(self):
        return tr("ba.anbohrer.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.zentrieren_einsatz.tooltip")

    def werkzeug_passt(self, werkzeug):
        return werkzeug.art == wz.NC_ANBOHRER

    def passt(self, form, name):
        return bb.ist_bohrung(form, name)

    def vorgeschlagen(self, form, gewaehlte):
        return False  # ob angebohrt wird, hängt am Bohrer, nicht am Modell

    def unmoeglich_text(self):
        return tr("ba.zentrieren.nicht")

    def vorschau(self, job, werkzeug, werte, flaechen):
        return sk.vorschau_zentrieren(job, werkzeug, flaechen, werte.get("vorschub", 0.0))

    def ergebnis_text(self, bahn, zeit):
        return _kegel_ergebnis(bahn, zeit)

    def lege_an(self, job, tc, werte, flaechen):
        return sk.zentrieren_anlegen(job, tc, flaechen)

    def ist(self, op):
        return False  # FreeCADs eigene Operation – sie ändert FreeCADs Fenster


class _Rest(_Strategie):
    """Restmaterial: eine Kontur mit einem kleineren Fräser nur dort, wo der große davor nicht
    hinkam (kontur, RadiusDavor) – nach der Kontur, den Haken setzt man selbst."""

    kennung = "rest"
    gemerkt = GEMERKT_RESTFRAESER
    einsatz_reihenfolge = (wz.SCHLICHTEN, wz.SCHRUPPEN)

    def titel(self):
        return tr("ba.rest")

    def text(self):
        return tr("ba.rest.text")

    def fraeser_tooltip(self):
        return tr("ba.restfraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.resteinsatz.tooltip")

    def felder(self):
        return (
            ("davor", tr("ba.rest.davor"), tr("ba.rest.davor.tooltip")),
            ("zustellung", tr("ba.zustellung"), tr("ba.rest.zustellung.tooltip")),
        )

    def passt(self, form, name):
        return bool(kb.waende(form, [name]))

    def vorgeschlagen(self, form, gewaehlte):
        return False  # nach den Rundungen und den Fräsern: BearbeitungPanel._rest_vorschlagen

    def unmoeglich_text(self):
        return tr("ba.rest.nicht")

    def vorschlag(self, feld, werkzeug, einsatz):
        if feld == "zustellung":
            if einsatz is not None and einsatz.ap > 0:
                return einsatz.ap
            return float(werkzeug.durchmesser) if werkzeug is not None else ko.ZUSTELLUNG
        return 0.0  # davor: vom Fenster (_zusatz)

    def platzhalter(self, feld, werkzeug, einsatz):
        if feld == "davor":
            return tr("ba.rest.davor.leer")
        return super().platzhalter(feld, werkzeug, einsatz)

    def vorschau(self, job, werkzeug, werte, flaechen):
        davor = float(werte.get("davor", 0.0))
        if davor <= 0:
            raise ValueError(tr("ba.rest.davor.fehlt"))
        form = ff.von_werkzeug(werkzeug)
        return ko.vorschau(
            job,
            job.Model.Group,
            form,
            werte["zustellung"],
            float(form.radius),
            0.0,
            False,
            flaechen,
            REST_BREITE,
            schneidenlaenge=float(werkzeug.schneidenlaenge or 0.0),
            radius_davor=davor / 2,
        )

    def ergebnis_text(self, bahn, zeit):
        stellen_n = max(1, round(bahn.bahnen / max(bahn.lagen, 1)))
        stellen = tr("ba.zahl.stelle") if stellen_n == 1 else tr("ba.zahl.stellen", n=stellen_n)
        lagen = tr("ba.zahl.lage") if bahn.lagen == 1 else tr("ba.zahl.lagen", n=bahn.lagen)
        return tr("ba.ergebnis_rest", stellen=stellen, lagen=lagen, zeit=zeit)

    def lege_an(self, job, tc, werte, flaechen):
        r = float(tc.Tool.Diameter) / 2
        return ko.lege_an(
            job,
            tc,
            werte["zustellung"],
            r,
            0.0,
            False,
            REST_BREITE,
            flaechen=flaechen,
            radius_davor=float(werte["davor"]) / 2,
        )

    def aendere(self, op, tc, werte, flaechen):
        r = float(tc.Tool.Diameter) / 2
        ko.aendere(
            op,
            tc,
            werte["zustellung"],
            r,
            0.0,
            False,
            REST_BREITE,
            flaechen=flaechen,
            radius_davor=float(werte["davor"]) / 2,
        )

    def ist(self, op):
        return ko.ist_rest(op)

    def werte_von(self, op):
        return {"davor": 2 * float(op.RadiusDavor), "zustellung": float(op.Zustellung)}


class _Schruppen3D(_Strategie):
    """Das Rohteil über Freiformflächen in Lagen wegräumen, Zwischenlagen für die Treppe
    (schruppen3d_bahn) – mit dem Fräser fürs Räumen; gegen keine Strategie im Wettbewerb."""

    kennung = "schruppen3d"
    aufloesung = r3op.sr.SCHRITT
    gemerkt = GEMERKT_RAEUMFRAESER
    einsatz_reihenfolge = (wz.SCHRUPPEN, wz.PLANEN, wz.SCHLICHTEN)

    def titel(self):
        return tr("ba.r3")

    def text(self):
        return tr("ba.r3.text")

    def fraeser_tooltip(self):
        return tr("ba.r3.fraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.r3.einsatz.tooltip")

    def felder(self):
        return (
            ("zustellung", tr("ba.zustellung"), tr("ba.zustellung.tooltip")),
            ("zeilenabstand", tr("ba.zeilenabstand"), tr("ba.raeumen.zeilenabstand.tooltip")),
            ("aufmass", tr("ba.aufmass"), tr("ba.r3.aufmass.tooltip")),
            ("zwischen", tr("ba.zwischenlagen"), tr("ba.zwischenlagen.tooltip")),
        )

    def haken(self):
        return (
            ("gleichlauf", tr("ba.gleichlauf"), tr("ba.gleichlauf.tooltip"), True),
            # Nicht angehakt: Ob das Rohteil drumherum schon weg ist, weiß nur der Anwender –
            # angehakt führe der Fräser dort sonst ins Volle; der Satz darunter fragt danach
            # (_material_text, Frage 6).
            ("nur_ueber", tr("ba.r3.nur_ueber"), tr("ba.r3.nur_ueber.tooltip"), False),
        )

    def passt(self, form, name):
        return s3b.ist_freiform(form, name)

    def vorgeschlagen(self, form, gewaehlte):
        # Sobald eine Freiformfläche gewählt ist – auch neben Oberseite und Bohrungen (eine
        # Formplatte, P-2026-10-02-14); gefräst werden nur die Freiformflächen (flaechen_fuer).
        return any(self.passt(form, n) for n in gewaehlte)

    def unmoeglich_text(self):
        return tr("ba.r3.keine")

    def vorschlag(self, feld, werkzeug, einsatz):
        if feld == "zwischen":
            return r3b.ZWISCHEN
        if feld == "aufmass":
            return r3op.AUFMASS
        return _Raeumen().vorschlag(feld, werkzeug, einsatz)

    def _argumente(self, werkzeug, werte, flaechen):
        """(Argumente, Schlüsselwörter) für schruppen3d.vorschau nach Job und Modell."""
        return (
            ff.von_werkzeug(werkzeug),
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            list(flaechen),
        ), {
            "zwischen": werte["zwischen"],
            "gleichlauf": werte["gleichlauf"],
            "schneidenlaenge": float(werkzeug.schneidenlaenge or 0.0),
            "vorschub": werte.get("vorschub", 0.0),
            "eintauchen": werte.get("eintauchen", 0.0),
            "stand": werte.get("materialstand"),
            "nur_ueber": bool(werte.get("nur_ueber", False)),
        }

    def vorschau(self, job, werkzeug, werte, flaechen):
        argumente, weiter = self._argumente(werkzeug, werte, flaechen)
        return r3op.vorschau(job, job.Model.Group, *argumente, **weiter)

    def hintergrund(self, werkzeug, werte, flaechen):
        """Die Vorschau in einem Nebenrechner (bearbeitung_vorschau.strategie)."""
        return "strategie", ("schruppen3d", *self._argumente(werkzeug, werte, flaechen))

    def ergebnis_text(self, bahn, zeit):
        lagen = tr("ba.zahl.lage") if bahn.lagen == 1 else tr("ba.zahl.lagen", n=bahn.lagen)
        if bahn.variante == "zeilen":  # in der N-Eck-Stange (n_eck_schruppen): Zeilen statt Ringe
            zeilen = tr("ba.zahl.zeile") if bahn.ringe == 1 else tr("ba.zahl.zeilen", n=bahn.ringe)
            return tr("ba.ergebnis_raeumen", lagen=lagen, ringe=zeilen, zeit=zeit)
        ringe = tr("ba.zahl.ring") if bahn.ringe == 1 else tr("ba.zahl.ringe", n=bahn.ringe)
        if not bahn.zwischenlagen:
            return tr("ba.ergebnis_raeumen", lagen=lagen, ringe=ringe, zeit=zeit)
        zwischen = (
            tr("ba.zahl.zwischenlage")
            if bahn.zwischenlagen == 1
            else tr("ba.zahl.zwischenlagen", n=bahn.zwischenlagen)
        )
        if not bahn.lagen:  # eine Höhlung: die volle Lage findet nichts, nur die Zwischenlagen
            return tr("ba.ergebnis_raeumen", lagen=zwischen, ringe=ringe, zeit=zeit)
        return tr("ba.ergebnis_r3", lagen=lagen, zwischen=zwischen, ringe=ringe, zeit=zeit)

    def lege_an(self, job, tc, werte, flaechen):
        return r3op.lege_an(
            job,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            werte["zwischen"],
            werte["gleichlauf"],
            flaechen=flaechen,
            nur_ueber=bool(werte.get("nur_ueber", False)),
        )

    def aendere(self, op, tc, werte, flaechen):
        r3op.aendere(
            op,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            werte["zwischen"],
            werte["gleichlauf"],
            flaechen=flaechen,
            nur_ueber=bool(werte.get("nur_ueber", False)),
        )

    def ist(self, op):
        return r3op.ist_schruppen3d(op) and not r3op.ist_restschruppen(op)

    def werte_von(self, op):
        return {
            "zustellung": float(op.Zustellung),
            "zeilenabstand": float(op.Zeilenabstand),
            "aufmass": float(op.Aufmass),
            "zwischen": float(op.Zwischenlagen),
            "gleichlauf": bool(op.Gleichlauf),
            "nur_ueber": bool(getattr(op, "NurUeber", False)),
        }


class _Restschruppen(_Schruppen3D):
    """Restschruppen: das 3D-Schruppen mit einem kleineren Fräser nur dort, wo der größere
    davor Material stehen ließ (schruppen3d mit DurchmesserDavor) – nach dem 3D-Schruppen, den
    Haken setzt man selbst."""

    kennung = "restschruppen"
    gemerkt = GEMERKT_RESTSCHRUPPFRAESER

    def titel(self):
        return tr("ba.rr")

    def text(self):
        return tr("ba.rr.text")

    def fraeser_tooltip(self):
        return tr("ba.rr.fraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.rr.einsatz.tooltip")

    def felder(self):
        return (("davor", tr("ba.rr.davor"), tr("ba.rr.davor.tooltip")),) + super().felder()

    def vorgeschlagen(self, form, gewaehlte):
        return False  # ob der kleine Fräser nachkommt, entscheidet man selbst

    def vorschlag(self, feld, werkzeug, einsatz):
        if feld == "davor":
            return 0.0  # vom Fenster (_zusatz)
        return super().vorschlag(feld, werkzeug, einsatz)

    def platzhalter(self, feld, werkzeug, einsatz):
        if feld == "davor":
            return tr("ba.rr.davor.leer")
        return super().platzhalter(feld, werkzeug, einsatz)

    @staticmethod
    def davor(werte):
        """(Ø, Eckenradius) des Fräsers davor aus den Werten – von Hand eingetragen ein
        Schaftfräser. ValueError mit einem Satz, wenn keiner da ist."""
        durchmesser = float(werte.get("davor", 0.0) or 0.0)
        if durchmesser <= 0:
            raise ValueError(tr("ba.rr.davor.fehlt"))
        return durchmesser, float(werte.get("davor_eck") or 0.0)

    def haken(self):
        # Der Rest ist ohnehin nur, wo der größere Fräser davor stehen ließ.
        return (("gleichlauf", tr("ba.gleichlauf"), tr("ba.gleichlauf.tooltip"), True),)

    def _argumente(self, werkzeug, werte, flaechen):
        """(Argumente, Schlüsselwörter) für schruppen3d.vorschau – mit dem Fräser davor, ohne
        Materialstand (die Zeit im Freien rechnet mit ihm)."""
        durchmesser, eckenradius = self.davor(werte)
        return (
            ff.von_werkzeug(werkzeug),
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            list(flaechen),
        ), {
            "zwischen": werte["zwischen"],
            "gleichlauf": werte["gleichlauf"],
            "schneidenlaenge": float(werkzeug.schneidenlaenge or 0.0),
            "vorschub": werte.get("vorschub", 0.0),
            "eintauchen": werte.get("eintauchen", 0.0),
            "davor": ff.torus(durchmesser / 2, min(eckenradius, durchmesser / 2)),
        }

    def vorschau(self, job, werkzeug, werte, flaechen):
        argumente, weiter = self._argumente(werkzeug, werte, flaechen)
        return r3op.vorschau(job, job.Model.Group, *argumente, **weiter)

    def hintergrund(self, werkzeug, werte, flaechen):
        """Die Vorschau in einem Nebenrechner (bearbeitung_vorschau.strategie)."""
        return "strategie", ("schruppen3d", *self._argumente(werkzeug, werte, flaechen))

    def lege_an(self, job, tc, werte, flaechen):
        return r3op.lege_an(
            job,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            werte["zwischen"],
            werte["gleichlauf"],
            flaechen=flaechen,
            davor=self.davor(werte),
        )

    def aendere(self, op, tc, werte, flaechen):
        r3op.aendere(
            op,
            tc,
            werte["zustellung"],
            werte["zeilenabstand"],
            werte["aufmass"],
            werte["zwischen"],
            werte["gleichlauf"],
            flaechen=flaechen,
            davor=self.davor(werte),
        )

    def ist(self, op):
        return r3op.ist_restschruppen(op)

    def werte_von(self, op):
        werte = dict(super().werte_von(op), davor=float(op.DurchmesserDavor))
        werte.pop("nur_ueber", None)  # den Haken hat das Restschruppen nicht
        return werte


def _kippachse(job):
    """„X“ oder „Y“: um welche Achse des Jobs ein angestellter Kugelfräser kippt – die der ersten
    schwenkenden Rundachse der Maschine des Jobs (A um X, B um Y), sonst „X“."""
    datei = rw.gemerkte_maschine(job) if job is not None else ""
    eintrag = msp.finde(msp.laden(), datei) if datei else None
    for buchstabe in getattr(eintrag, "rundachsen", ()) or ():
        if buchstabe in ("A", "B"):
            return "X" if buchstabe == "A" else "Y"
    return "X"


def _wegkippen_bedarf(job, werkzeug, bahn, form):
    """wegkippen.Bedarf für die Vorschau (wegkippen.bedarf_fuer_bahn)."""
    from . import wegkippen as wk

    return wk.bedarf_fuer_bahn(job, werkzeug, bahn, form)


def _job_der(op):
    """Der Job der Operation – None, wenn sie in keinem steht."""
    return next((j for j in js.jobs(op.Document) if op in js.operationen(j)), None)


# 3D-Schlichten: 5 Achsen
KIPPHAKEN = ("anstellen", "wegkippen", "hinterschnitt", "spirale", "vorschlichten")
# Vorbohren fürs Räumen: der Bohrer zwischen dem Fräser und so viel mal ihm – größer passte er
# nicht mehr in den Kreis, den das Räumen für die Helix braucht (raeumen_bahn.ADAPTIV_HELIX).
VORBOHRER_HOECHSTENS = 1.6
VORBOHRER_LUFT = 0.5  # mm – am liebsten so viel größer als der Fräser, damit er frei hineinfällt
# mm – so viel lässt die Flanke an Wänden unter dem Rand, die danach die Spirale des 3D-Schlichtens
# fertig macht (Manuel, 2026-10-25, Frage 7: „Flanke grob, Spirale fertig“ – in der unteren Lage
# lag der Schaft von T1 sonst an der schon fertigen Wand an).
FLANKE_VOR_SPIRALE = 0.3
# Kegelsenker nach DIN 335 C (Ø, Ø der Spitze, Schaft-Ø; übliche Katalogmaße): „Kegelsenker …
# anlegen“ nimmt den kleinsten, der die Senkung abdeckt und dessen Spitze in die Bohrung passt.
KEGELSENKER_REIHE = (
    (6.3, 1.5, 5.0),
    (8.3, 2.0, 6.0),
    (10.4, 2.5, 6.0),
    (12.4, 2.8, 8.0),
    (16.5, 3.2, 10.0),
    (20.5, 3.5, 10.0),
    (25.0, 3.8, 10.0),
    (31.0, 4.2, 12.0),
)
# Was im Grundjob einer Maschine mit waagerechter Spindel bleibt: die Strategien mit Achse je Satz.
SIMULTAN_IM_GRUNDJOB = ("flanke", "schlichten3d", "restschlichten", "entgraten3d")


def _vorschlichten_bis(werte):
    """z, bis zu der das 3D-Schlichten unter dem Rand vorschlichtet (Haken „Vorschlichten“ und
    eine Höhe aus der Flanke davor, BearbeitungPanel._vorschlichten_zusatz) – sonst None."""
    if not (werte.get("hinterschnitt") and werte.get("vorschlichten", True)):
        return None
    return werte.get("vorschlichten_bis")


class _Schlichten3D(_Strategie):
    """Freiformflächen in parallelen Zeilen auf der Hüllfläche des ganzen Teils
    (schlichten3d_bahn) – am liebsten mit dem Kugelfräser; gegen keine Strategie im Wettbewerb."""

    kennung = "schlichten3d"
    aufloesung = s3op.sb.SCHRITT
    gemerkt = GEMERKT_FRAESER_3D
    einsatz_reihenfolge = (wz.SCHLICHTEN, wz.SCHRUPPEN)
    bevorzugt = wz.KUGELFRAESER
    ARTEN = (wz.KUGELFRAESER, wz.TORUSFRAESER, wz.SCHAFTFRAESER, wz.KONIKFRAESER)

    def titel(self):
        return tr("ba.s3")

    def text(self):
        return tr("ba.s3.text")

    def fraeser_tooltip(self):
        return tr("ba.s3.fraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.s3.einsatz.tooltip")

    def felder(self):
        return (
            ("grathoehe", tr("ba.grathoehe"), tr("ba.grathoehe.tooltip")),
            ("aufmass", tr("ba.aufmass"), tr("ba.s3.aufmass.tooltip")),
        )

    def haken(self):
        # 5 Achsen simultan S2 (angestellt.py; Manuel, 2026-10-04: „Ja, so bauen“) – ohne Vorgabe.
        # Unter dem Rand (hinterschnitt_bahn; Manuel, 2026-10-25: „und dann muss mit einem
        # kurgelfräser die wand geschlichtet werden“) – vorbelegt an, wirkt nur auf überdeckte
        # Flächen.
        return (
            ("anstellen", tr("ba.s3.anstellen"), tr("ba.s3.anstellen.tooltip"), False),
            ("wegkippen", tr("ba.s3.wegkippen"), tr("ba.s3.wegkippen.tooltip"), False),
            ("hinterschnitt", tr("ba.s3.unter"), tr("ba.s3.unter.tooltip"), True),
            # Manuel, 2026-10-25: „sozusagen abzeilen mit halt einer spirale nach unten“.
            ("spirale", tr("ba.s3.spirale"), tr("ba.s3.spirale.tooltip"), True),
            # Manuel, 2026-10-30, Frage 1: „vorschlichten“ – wo die Flanke davor einen Keil ließ.
            (
                "vorschlichten",
                tr("ba.s3.vorschlichten"),
                tr(
                    "ba.s3.vorschlichten.tooltip",
                    ab=groesse_zeigen(s3op.VORSCHLICHTEN_AB, einheiten.LAENGE, 1),
                    aufmass=groesse_zeigen(s3op.VORSCHLICHTEN_AUFMASS, einheiten.LAENGE, 1),
                ),
                True,
            ),
        )

    def haken_verborgen(self, feld, block):
        # Anstellen, Wegkippen und unter dem Rand nur an einer 5-Achs-Maschine – sonst wären sie
        # nur Rauschen; Vorschlichten nur nach „Flanke grob, Spirale fertig“ (Frage „Wände“).
        if feld == "vorschlichten" and getattr(block.panel, "_weg", {}).get("waende") != "spirale":
            return True
        return feld in KIPPHAKEN and not block.panel._fuenfachs()

    def haken_gesperrt(self, feld, block):
        if feld not in KIPPHAKEN:
            return None
        try:
            eintrag = block.panel.maschine()
        except AttributeError:  # die Wahl der Maschine gibt es noch nicht
            eintrag = None
        if eintrag is None or not eintrag.vorhanden or eintrag.art != msp.FRAESE_5:
            return tr("ba.s3.anstellen.ohne_maschine")
        werkzeug = block.fraeser()
        if werkzeug is None or werkzeug.art != wz.KUGELFRAESER:
            return tr("ba.s3.anstellen.ohne_kugel")
        return None

    def haken_gesperrt_warum(self, feld, block):
        # Manuel, 2026-10-16: „warum das anstellen aber nur mit einem kugelfräser geht weis ich
        # nun nicht ?“
        if feld != "wegkippen" and self.haken_gesperrt(feld, block) == tr(
            "ba.s3.anstellen.ohne_kugel"
        ):
            return tr("ba.s3.anstellen.ohne_kugel.warum")
        return None

    def werkzeug_passt(self, werkzeug):
        return werkzeug.art in self.ARTEN and ff.von_werkzeug(werkzeug) is not None

    def passt(self, form, name):
        return s3b.ist_freiform(form, name)

    def vorgeschlagen(self, form, gewaehlte):
        # Sobald eine Freiformfläche gewählt ist – auch neben Oberseite und Bohrungen (eine
        # Formplatte, P-2026-10-02-14); gefräst werden nur die Freiformflächen (flaechen_fuer).
        return any(self.passt(form, n) for n in gewaehlte)

    def unmoeglich_text(self):
        return tr("ba.s3.keine")

    def vorschlag(self, feld, werkzeug, einsatz):
        return s3b.GRATHOEHE if feld == "grathoehe" else 0.0

    def _argumente(self, werkzeug, werte, flaechen):
        """(Argumente, Schlüsselwörter) für schlichten3d.vorschau nach Job und Modell."""
        form = ff.von_werkzeug(werkzeug)
        if form is None:
            raise ValueError(tr("s3.fehler.form"))
        weiter = {
            "aufmass": werte["aufmass"],
            "vorschub": werte.get("vorschub", 0.0),
            "eintauchen": werte.get("eintauchen", 0.0),
        }
        weiter.update(self._unter_dem_rand(werkzeug, werte, form))
        return (form, werte["grathoehe"], list(flaechen)), weiter

    @staticmethod
    def _unter_dem_rand(werkzeug, werte, form):
        """Die Schlüsselwörter für schlichten3d.vorschau mit „Unter dem Rand“ (angehakt, eine
        Kugel): die Richtung, Halter und Schaft – sonst keine. Die Empfehlung rechnet der Block
        danach (_empfehlung_anstossen)."""
        weiter = {}
        if werte.get("hinterschnitt") and form.nur_kugel:
            weiter["richtung"] = s3op.hb.HINTERSCHNITT  # nur überdeckte Flächen, sonst „auto“
            weiter["spirale"] = bool(werte.get("spirale", True))
            if werte.get("vorschlichten", True) and werte.get("vorschlichten_bis") is not None:
                weiter["vorschlichten_bis"] = float(werte["vorschlichten_bis"])
            # Schaft und Halter aus der Werkzeugverwaltung (der Halter in Stücken, Kegel genau) –
            # wie sie im Magazin der Maschine stecken.
            bibliothek = _bibliothek_der_pruefung()
            if bibliothek is not None:
                masse = rw.masse_des_werkzeugs(werkzeug)
                laenge = rw.laenge_des_werkzeugs(werkzeug, bibliothek)[0]
                weiter["koerper"] = s3op.hb.koerper_des_werkzeugs(
                    masse, laenge, bibliothek.halter_fuer_pruefung(werkzeug)
                )
                weiter["schneide"] = float(masse.schneide)
        return weiter

    def _wegkippen(self, werkzeug, werte):
        """Rechnet die Vorschau den Bedarf zum Wegkippen mit (wegkippen.Bedarf)?"""
        form = ff.von_werkzeug(werkzeug)
        return bool(werte.get("wegkippen")) and form is not None and form.nur_kugel

    def vorschau(self, job, werkzeug, werte, flaechen):
        argumente, weiter = self._argumente(werkzeug, werte, flaechen)
        bahn = s3op.vorschau(job, job.Model.Group, *argumente, **weiter)
        if self._wegkippen(werkzeug, werte) and not getattr(bahn, "hinterschnitt", False):
            bahn.wegkippen = _wegkippen_bedarf(job, werkzeug, bahn, argumente[0])
        return bahn

    def zeit(self, bahn, vorschub, eintauchen):
        if getattr(bahn, "hinterschnitt", False):
            return bahn.zeit  # schon mit dem Vorschub (hinterschnitt_bahn)
        return super().zeit(bahn, vorschub, eintauchen)

    def hintergrund(self, werkzeug, werte, flaechen):
        """Die Vorschau in einem Nebenrechner (bearbeitung_vorschau.strategie) – mit dem
        Wegkippen samt dessen Bedarf (bearbeitung_vorschau.schlichten3d_wegkippen: Halter und
        Länge liest der Arbeiter aus der Werkzeugverwaltung desselben Profils)."""
        argumente = self._argumente(werkzeug, werte, flaechen)
        if self._wegkippen(werkzeug, werte):
            return "schlichten3d_wegkippen", (werkzeug, *argumente)
        return "strategie", ("schlichten3d", *argumente)

    def ergebnis_text(self, bahn, zeit):
        text = self._ergebnis_text(bahn, zeit)
        bedarf = getattr(bahn, "wegkippen", None)
        if bedarf is None:
            return text
        werte = {
            "text": text,
            "senkrecht": groesse_zeigen(bedarf.senkrecht, einheiten.LAENGE, 1) or "0",
            "gekippt": groesse_zeigen(bedarf.gekippt, einheiten.LAENGE, 1) or "0",
            "auskragung": groesse_zeigen(bedarf.auskragung, einheiten.LAENGE, 1) or "0",
        }
        if bedarf.auskragung < bedarf.gekippt:
            return tr("ba.s3.wegkippen.zu_kurz", **werte)
        return tr("ba.s3.wegkippen.bedarf", **werte)

    def _ergebnis_text(self, bahn, zeit):
        if getattr(bahn, "hinterschnitt", False):
            werte = {
                "n": bahn.linien,
                "neigung": f"{bahn.neigung:.0f}",
                "abstand": groesse_zeigen(bahn.abstand, einheiten.LAENGE, 2) or "0",
                "zeit": zeit,
            }
            if bahn.spirale:
                text = tr("ba.ergebnis_s3_unter_spirale", **werte)
            else:
                text = tr("ba.ergebnis_s3_unter", **werte)
            vor = getattr(bahn, "vor", None)
            if vor is not None:
                text = tr(
                    "ba.s3.vorschlichten.ergebnis",
                    text=text,
                    n=vor.linien,
                    zeit=_ziel_minuten(vor.zeit),
                )
            ecken = bahn.weggelassen - bahn.anstoesse
            if ecken and getattr(bahn, "ecken_radius", 0.0) > 0:
                d = groesse_zeigen(2.0 * bahn.ecken_radius, einheiten.LAENGE, 1) or "0"
                text += ". " + tr("ba.ergebnis_s3_unter.ecken_d", n=ecken, d=d)
            elif ecken:
                text += ". " + tr("ba.ergebnis_s3_unter.ecken", n=ecken)
            if bahn.anstoesse:
                text += (" " if ecken else ". ") + tr(
                    "ba.ergebnis_s3_unter.anstoss", n=bahn.anstoesse
                )
                if bahn.ausspannen is not None and bahn.ausspannen[1] is not None:
                    text += " " + tr(
                        "ba.ergebnis_s3_unter.mindestens",
                        heraus=f"{bahn.ausspannen[0]:.0f}",
                        mindestens=f"{math.ceil(bahn.ausspannen[1]):.0f}",
                    )
            return text
        zeilen = tr("ba.zahl.zeile") if bahn.zeilen == 1 else tr("ba.zahl.zeilen", n=bahn.zeilen)
        werte = {
            "zeilen": zeilen,
            "richtung": "X" if bahn.laengs_x else "Y",
            "abstand": groesse_zeigen(bahn.abstand, einheiten.LAENGE, 2) or "0",
            "zeit": zeit,
        }
        if getattr(bahn, "aequidistant", False):
            ringe = tr("ba.zahl.ring") if bahn.zeilen == 1 else tr("ba.zahl.ringe", n=bahn.zeilen)
            return tr("ba.ergebnis_s3_aequi", ringe=ringe, **werte)
        if getattr(bahn, "flaeche", False):
            kurven = (
                tr("ba.zahl.kurve") if bahn.zeilen == 1 else tr("ba.zahl.kurven", n=bahn.zeilen)
            )
            return tr("ba.ergebnis_s3_flaeche", kurven=kurven, **werte)
        if bahn.spirale:
            werte["umlaeufe"] = (
                tr("ba.zahl.umlauf")
                if bahn.umlaeufe == 1
                else tr("ba.zahl.umlaeufe", n=bahn.umlaeufe)
            )
            if bahn.hoehenlinien:
                return tr("ba.ergebnis_s3_spirale_steil", n=bahn.hoehenlinien, **werte)
            return tr("ba.ergebnis_s3_spirale", **werte)
        if bahn.hoehenlinien:
            return tr("ba.ergebnis_s3_steil", n=bahn.hoehenlinien, **werte)
        return tr("ba.ergebnis_s3", **werte)

    def lege_an(self, job, tc, werte, flaechen):
        op = s3op.lege_an(job, tc, werte["grathoehe"], werte["aufmass"], flaechen=flaechen)
        s3op.stelle_an(op, werte.get("anstellen", False), _kippachse(job))
        s3op.stelle_weg(op, werte.get("wegkippen", False))
        s3op.unter_dem_rand(op, werte.get("hinterschnitt", False), werte.get("spirale", True))
        s3op.vorschlichten(op, _vorschlichten_bis(werte))
        return op

    def aendere(self, op, tc, werte, flaechen):
        s3op.aendere(op, tc, werte["grathoehe"], werte["aufmass"], flaechen=flaechen)
        s3op.stelle_an(op, werte.get("anstellen", False), _kippachse(_job_der(op)))
        s3op.stelle_weg(op, werte.get("wegkippen", False))
        s3op.unter_dem_rand(op, werte.get("hinterschnitt", False), werte.get("spirale", True))
        s3op.vorschlichten(op, _vorschlichten_bis(werte))

    def ist(self, op):
        return s3op.ist_schlichten3d(op) and not s3op.ist_restschlichten(op)

    def werte_von(self, op):
        return {
            "grathoehe": float(op.Grathoehe),
            "aufmass": float(op.Aufmass),
            "anstellen": bool(getattr(op, "Anstellen", False)),
            "wegkippen": bool(getattr(op, "Wegkippen", False)),
            "hinterschnitt": str(getattr(op, "Richtung", "")) == s3op.hb.HINTERSCHNITT,
            "spirale": bool(getattr(op, "UnterRandSpirale", False)),
        }


class _Flanke(_Strategie):
    """Die Flanke (5 Achsen simultan, flanke_bahn; Manuel, 2026-10-04: „Ja, so bauen“, „selbst
    anhaken, wenn schneller“): schräge Wände aus Geraden mit dem Mantel eines Schaftfräsers in
    einem Umlauf – an einer 5-Achs-Maschine, im Wettbewerb mit dem 3D-Schlichten."""

    kennung = "flanke"
    gemerkt = GEMERKT_FLANKENFRAESER
    einsatz_reihenfolge = (wz.SCHLICHTEN, wz.SCHRUPPEN)
    bevorzugt = wz.SCHAFTFRAESER
    aufloesung = flb.SCHRITT  # der Schritt an gekrümmten Kanten

    def aufloesung_erklaerung(self, vorschlag):
        return tr("ba.aufloesung.kante.tooltip", vorschlag=vorschlag)

    def titel(self):
        return tr("ba.fl")

    def text(self):
        return tr("ba.fl.text")

    def fraeser_tooltip(self):
        return tr("ba.fl.fraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.s3.einsatz.tooltip")

    def felder(self):
        return (
            ("aufmass", tr("ba.aufmass"), tr("ba.fl.aufmass.tooltip")),
            ("quer", tr("ba.fl.quer"), tr("ba.fl.quer.tooltip")),
        )

    def passt(self, form, name):
        return flb.ist_wand(form, name)

    def vorgeschlagen(self, form, gewaehlte):
        return any(self.passt(form, n) for n in gewaehlte)  # die Zeit entscheidet (_wettbewerb)

    def unmoeglich_text(self):
        return tr("ba.fl.keine")

    def vorschlag(self, feld, werkzeug, einsatz):
        if feld == "quer":
            # Am Keil unter einem überhängenden Rand mit voller Flanke: ein schmales ae – das des
            # dynamischen Einsatzes (Manuels T1: 2,4 bei ap 24,7) oder des Schruppens, sonst 20 %.
            durchmesser = float(getattr(werkzeug, "durchmesser", 0.0) or 0.0)
            if einsatz is not None and einsatz.art in (wz.DYNAMISCH, wz.SCHRUPPEN) and einsatz.ae:
                return (
                    min(float(einsatz.ae), 0.5 * durchmesser) if durchmesser else float(einsatz.ae)
                )
            return round(0.2 * durchmesser, 2)
        return 0.0

    def _argumente(self, werkzeug, werte, flaechen):
        """(Argumente, Schlüsselwörter) für flanke.vorschau nach Job und Modell – die Körper über
        der Schneide aus der Werkzeugverwaltung (der Halter in der Wand: „bräuchte mindestens“)."""
        form = ff.von_werkzeug(werkzeug)
        if form is None or not form.eben:
            raise ValueError(tr("fl.fehler.fraeser"))
        radius = float(form.radius)
        schneide = float(getattr(werkzeug, "schneidenlaenge", 0.0) or 0.0) or 4.0 * radius
        bibliothek = _bibliothek_der_pruefung()
        return (form, radius, schneide, list(flaechen)), {
            "aufmass": werte["aufmass"],
            "vorschub": werte.get("vorschub", 0.0),
            "eintauchen": werte.get("eintauchen", 0.0),
            "koerper": flop.koerper_ueber_der_schneide(werkzeug, bibliothek),
            "quer": werte.get("quer", 0.0),
        }

    def vorschau(self, job, werkzeug, werte, flaechen):
        argumente, weiter = self._argumente(werkzeug, werte, flaechen)
        return flop.vorschau(job, job.Model.Group, *argumente, **weiter)

    def hintergrund(self, werkzeug, werte, flaechen):
        """Die Vorschau in einem Nebenrechner (bearbeitung_vorschau.strategie) – am Kegel stand
        das Fenster dafür 2,7 s ohne Klick (P-2026-10-11-53)."""
        return "strategie", ("flanke", *self._argumente(werkzeug, werte, flaechen))

    def zeit(self, bahn, vorschub, eintauchen):
        return bahn.zeit  # mit dem Drehen der Achse (flanke_bahn._laenge_und_zeit)

    def ergebnis_text(self, bahn, zeit):
        umlaeufe = (
            tr("ba.fl.umlauf") if bahn.umlaeufe == 1 else tr("ba.fl.umlaeufe", n=bahn.umlaeufe)
        )
        werte = {"umlaeufe": umlaeufe, "neigung": f"{bahn.neigung:.0f}", "zeit": zeit}
        if bahn.lagen > 1:
            text = tr("ba.ergebnis_fl_lagen", lagen=bahn.lagen, **werte)
        else:
            text = tr("ba.ergebnis_fl", **werte)
        if getattr(bahn, "weiter_stellen", 0):
            # Schaft frei: in der unteren Lage weiter angestellt, an der Wand bleibt ein Keil.
            text = tr(
                "ba.fl.weiter",
                text=text,
                stellen=bahn.weiter_stellen,
                grad=zahl_zeigen(round(bahn.weiter, 2)),
                keil=groesse_zeigen(bahn.keil, einheiten.LAENGE, 2) or "0",
            )
        if getattr(bahn, "streift", 0):
            text = tr("ba.fl.streift", text=text, stellen=bahn.streift)
        return text

    def lege_an(self, job, tc, werte, flaechen):
        return flop.lege_an(
            job, tc, werte["aufmass"], flaechen=flaechen, quer=werte.get("quer", 0.0)
        )

    def aendere(self, op, tc, werte, flaechen):
        flop.aendere(op, tc, werte["aufmass"], flaechen=flaechen, quer=werte.get("quer", 0.0))

    def ist(self, op):
        return flop.ist_flanke(op)

    def werte_von(self, op):
        return {"aufmass": float(op.Aufmass), "quer": float(getattr(op, "Quer", 0.0))}


class _Restschlichten(_Schlichten3D):
    """Restschlichten: das 3D-Schlichten mit einem kleineren Fräser nur dort, wo der größere
    davor nicht hinkam (schlichten3d mit DurchmesserDavor) – nach dem 3D-Schlichten, den Haken
    setzt man selbst."""

    kennung = "restschlichten"
    gemerkt = GEMERKT_RESTFRAESER_3D
    ARTEN = (wz.KUGELFRAESER, wz.TORUSFRAESER)

    def titel(self):
        return tr("ba.rs")

    def text(self):
        return tr("ba.rs.text")

    def fraeser_tooltip(self):
        return tr("ba.rs.fraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.rs.einsatz.tooltip")

    def felder(self):
        return (("davor", tr("ba.rs.davor"), tr("ba.rs.davor.tooltip")),) + super().felder()

    def vorgeschlagen(self, form, gewaehlte):
        return False  # ob der kleine Fräser nachkommt, entscheidet man selbst

    def unmoeglich_text(self):
        return tr("ba.rs.keine")

    def vorschlag(self, feld, werkzeug, einsatz):
        if feld == "davor":
            return 0.0  # vom Fenster (_zusatz)
        return super().vorschlag(feld, werkzeug, einsatz)

    def platzhalter(self, feld, werkzeug, einsatz):
        if feld == "davor":
            return tr("ba.rs.davor.leer")
        return super().platzhalter(feld, werkzeug, einsatz)

    @staticmethod
    def davor(werte):
        """(Ø, Eckenradius) des Fräsers davor aus den Werten – von Hand eingetragen eine Kugel.
        ValueError mit einem Satz, wenn keiner da ist."""
        durchmesser = float(werte.get("davor", 0.0) or 0.0)
        if durchmesser <= 0:
            raise ValueError(tr("ba.rs.davor.fehlt"))
        eckenradius = werte.get("davor_eck")
        return durchmesser, float(durchmesser / 2 if eckenradius is None else eckenradius)

    def _argumente(self, werkzeug, werte, flaechen):
        """(Argumente, Schlüsselwörter) für schlichten3d.vorschau – mit dem Fräser davor."""
        form = ff.von_werkzeug(werkzeug)
        if form is None:
            raise ValueError(tr("s3.fehler.form"))
        durchmesser, eckenradius = self.davor(werte)
        return (form, werte["grathoehe"], list(flaechen)), {
            "aufmass": werte["aufmass"],
            "vorschub": werte.get("vorschub", 0.0),
            "eintauchen": werte.get("eintauchen", 0.0),
            "davor": ff.torus(durchmesser / 2, min(eckenradius, durchmesser / 2)),
            **self._unter_dem_rand(werkzeug, werte, form),
        }

    def vorschau(self, job, werkzeug, werte, flaechen):
        argumente, weiter = self._argumente(werkzeug, werte, flaechen)
        return s3op.vorschau(job, job.Model.Group, *argumente, **weiter)

    def hintergrund(self, werkzeug, werte, flaechen):
        """Die Vorschau in einem Nebenrechner (bearbeitung_vorschau.strategie)."""
        return "strategie", ("schlichten3d", *self._argumente(werkzeug, werte, flaechen))

    def lege_an(self, job, tc, werte, flaechen):
        op = s3op.lege_an(
            job,
            tc,
            werte["grathoehe"],
            werte["aufmass"],
            flaechen=flaechen,
            davor=self.davor(werte),
        )
        s3op.stelle_an(op, werte.get("anstellen", False), _kippachse(job))
        s3op.stelle_weg(op, werte.get("wegkippen", False))
        s3op.unter_dem_rand(op, werte.get("hinterschnitt", False))
        return op

    def aendere(self, op, tc, werte, flaechen):
        s3op.aendere(
            op, tc, werte["grathoehe"], werte["aufmass"], flaechen=flaechen, davor=self.davor(werte)
        )
        s3op.stelle_an(op, werte.get("anstellen", False), _kippachse(_job_der(op)))
        s3op.stelle_weg(op, werte.get("wegkippen", False))
        s3op.unter_dem_rand(op, werte.get("hinterschnitt", False))

    def ist(self, op):
        return s3op.ist_restschlichten(op)

    def werte_von(self, op):
        return {
            "davor": float(op.DurchmesserDavor),
            "grathoehe": float(op.Grathoehe),
            "aufmass": float(op.Aufmass),
            "anstellen": bool(getattr(op, "Anstellen", False)),
            "wegkippen": bool(getattr(op, "Wegkippen", False)),
            "hinterschnitt": str(getattr(op, "Richtung", "")) == s3op.hb.HINTERSCHNITT,
        }


class _Bleistift(_Strategie):
    """Die Kehlen der Freiformflächen nachfahren, wo der Kugelfräser zwei Flächen zugleich
    berührt (bleistift_bahn) – nach dem 3D-Schlichten, mit demselben Fräser; den Haken setzt man
    selbst."""

    kennung = "bleistift"
    aufloesung = bst.bb.RASTER
    gemerkt = GEMERKT_FRAESER_3D
    einsatz_reihenfolge = (wz.SCHLICHTEN, wz.SCHRUPPEN)
    bevorzugt = wz.KUGELFRAESER
    ARTEN = (wz.KUGELFRAESER, wz.TORUSFRAESER)

    def titel(self):
        return tr("ba.bs")

    def text(self):
        return tr("ba.bs.text")

    def fraeser_tooltip(self):
        return tr("ba.bs.fraeser.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.bs.einsatz.tooltip")

    def felder(self):
        return (
            ("aufmass", tr("ba.aufmass"), tr("ba.bs.aufmass.tooltip")),
            ("breite", tr("ba.bs.breite"), tr("ba.bs.breite.tooltip")),
        )

    @staticmethod
    def _bahnen(werkzeug, werte):
        """Bahnen je Seite aus dem Feld „Breite je Seite“ (bleistift.bahnen_fuer)."""
        form = ff.von_werkzeug(werkzeug) if werkzeug is not None else None
        return bst.bahnen_fuer(werte.get("breite", 0.0), form)

    def werkzeug_passt(self, werkzeug):
        return werkzeug.art in self.ARTEN and ff.von_werkzeug(werkzeug) is not None

    def passt(self, form, name):
        return s3b.ist_freiform(form, name)

    def vorgeschlagen(self, form, gewaehlte):
        return False  # ob die Kehle nachgefahren wird, entscheidet man selbst

    def unmoeglich_text(self):
        return tr("ba.bs.keine")

    def _argumente(self, werkzeug, werte, flaechen):
        """((Form, Flächen), weitere) für bleistift.vorschau – hier und im Nebenrechner."""
        form = ff.von_werkzeug(werkzeug)
        if form is None:
            raise ValueError(tr("bs.fehler.form"))
        weiter = {
            "aufmass": werte["aufmass"],
            "vorschub": werte.get("vorschub", 0.0),
            "eintauchen": werte.get("eintauchen", 0.0),
            "bahnen": self._bahnen(werkzeug, werte),
        }
        return (form, list(flaechen)), weiter

    def vorschau(self, job, werkzeug, werte, flaechen):
        argumente, weiter = self._argumente(werkzeug, werte, flaechen)
        return bst.vorschau(job, job.Model.Group, *argumente, **weiter)

    def hintergrund(self, werkzeug, werte, flaechen):
        """Die Vorschau in einem Nebenrechner (bearbeitung_vorschau.strategie) – im Hauptprozess
        stand das Fenster dafür 2,5 s am Stück (P-2026-10-11-71)."""
        return "strategie", ("bleistift", *self._argumente(werkzeug, werte, flaechen))

    def ergebnis_text(self, bahn, zeit):
        kehlen = tr("ba.zahl.kehle") if bahn.linien == 1 else tr("ba.zahl.kehlen", n=bahn.linien)
        laenge = groesse_zeigen(bahn.laenge, einheiten.LAENGE, 0) or "0"
        einheit = einheiten.einheit(einheiten.LAENGE)
        return tr("ba.ergebnis_bs", kehlen=kehlen, laenge=f"{laenge} {einheit}", zeit=zeit)

    def lege_an(self, job, tc, werte, flaechen):
        bahnen = bst.bahnen_fuer(werte.get("breite", 0.0), bst.vs.form_des_controllers(tc))
        return bst.lege_an(job, tc, werte["aufmass"], flaechen=flaechen, bahnen=bahnen)

    def aendere(self, op, tc, werte, flaechen):
        bahnen = bst.bahnen_fuer(werte.get("breite", 0.0), bst.vs.form_des_controllers(tc))
        bst.aendere(op, tc, werte["aufmass"], flaechen=flaechen, bahnen=bahnen)

    def ist(self, op):
        return bst.ist_bleistift(op)

    def werte_von(self, op):
        return {"aufmass": float(op.Aufmass), "breite": bst.breite_von(op)}


class _Senken(_Strategie):
    """FreeCADs Bohren mit einem Kegelsenker in die Senkungen des Modells (senken) – nach dem
    Bohren; das Modell sagt, dass sie kommen, darum vorgeschlagen."""

    kennung = "senken"
    gemerkt = GEMERKT_SENKER
    einsatz_reihenfolge = (wz.SENKEN, wz.FASEN)
    bevorzugt = wz.KEGELSENKER
    # Auch ein Fasenfräser mit dem Winkel der Senkung – erst, wenn man ihn unter „Nicht fertig“
    # nimmt (Panel._senken_angebot; Manuel zur Fase: „wenn in der werkzeugverwaltung
    # einfasenfräser ist .. sollte man fragen .. hey willst du den haben ?“).
    mit_fasenfraeser = False

    def titel(self):
        return tr("ba.senken")

    def text(self):
        return tr("ba.senken.text")

    def fraeser_tooltip(self):
        return tr("ba.senker.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.senken_einsatz.tooltip")

    def werkzeug_passt(self, werkzeug):
        return werkzeug.art == wz.KEGELSENKER or (
            self.mit_fasenfraeser and werkzeug.art == wz.FASENFRAESER
        )

    def passt(self, form, name):
        return sk.ist_senkung(form, name)

    def unmoeglich_text(self):
        return tr("ba.senken.nicht")

    def vorschau(self, job, werkzeug, werte, flaechen):
        return sk.vorschau_senken(job, werkzeug, flaechen, werte.get("vorschub", 0.0))

    def ergebnis_text(self, bahn, zeit):
        return _kegel_ergebnis(bahn, zeit)

    def lege_an(self, job, tc, werte, flaechen):
        return sk.senken_anlegen(job, tc, flaechen)

    def ist(self, op):
        return False  # FreeCADs eigene Operation – sie ändert FreeCADs Fenster


class _Reiben(_Strategie):
    """FreeCADs Bohren mit einer Reibahle, G85 (reiben) – nach Bohren und Senken; der Bohrer
    bohrt dann kleiner vor, Bohrung fräsen und Kontur treten dort nicht an. Den Haken setzt
    man selbst: Ob eine Bohrung gerieben wird, steht nicht im Modell."""

    kennung = "reiben"
    gemerkt = GEMERKT_REIBAHLE
    einsatz_reihenfolge = (wz.REIBEN,)

    def titel(self):
        return tr("ba.reiben")

    def text(self):
        return tr("ba.reiben.text")

    def fraeser_tooltip(self):
        return tr("ba.reibahle.tooltip")

    def einsatz_tooltip(self):
        return tr("ba.reiben_einsatz.tooltip")

    def werkzeug_passt(self, werkzeug):
        return werkzeug.art == wz.REIBAHLE

    def passt(self, form, name):
        return any(b.durch or b.spitze > 0 for b in bb.bohrungen(form, [name]))

    def vorgeschlagen(self, form, gewaehlte):
        return False  # ob gerieben wird (H7), sagt das Modell nicht

    def unmoeglich_text(self):
        return tr("ba.reiben.nicht")

    def vorschau(self, job, werkzeug, werte, flaechen):
        return rbn.vorschau(job, werkzeug, flaechen, werte.get("vorschub", 0.0))

    def ergebnis_text(self, bahn, zeit):
        bohrungen = (
            tr("ba.zahl.bohrung")
            if bahn.bohrungen == 1
            else tr("ba.zahl.bohrungen", n=bahn.bohrungen)
        )
        return tr("ba.ergebnis_reiben", bohrungen=bohrungen, zeit=zeit)

    def lege_an(self, job, tc, werte, flaechen):
        return rbn.lege_an(job, tc, flaechen)

    def ist(self, op):
        return False  # FreeCADs eigene Operation – sie ändert FreeCADs Fenster


STRATEGIEN = (
    _Planfraesen,
    _Raeumen,
    _RestRaeumen,
    _SchlichtenDanach,
    _Nut,
    _Zentrieren,
    _Bohren,
    _Bohrung,
    _Kontur,
    _Rest,
    _Schruppen3D,
    _Restschruppen,
    _Schlichten3D,
    _Flanke,
    _Restschlichten,
    _Bleistift,
    _Senken,
    _Reiben,
    _Gewinde,
    _Gewindefraesen,
    _Fase,
    _Entgraten,
    _Entgraten3D,
)


# „Erst alles schruppen, dann alles schlichten“ (W-039; Manuel, 2026-10-25: „oder sollen wir
# alles rausschruppen und dann schlichten“; abends: Bohren, Senken und Gewinde zwischen Schruppen
# und Schlichten): je Strategie ihr Abschnitt – schruppen, Löcher, schlichten, Kanten; innerhalb
# eines Abschnitts die Folge aus STRATEGIEN. Bohrung fräsen gehört zu den Löchern (danach senkt
# und schneidet es dort); Nut und Kontur zum Schruppen (sie nehmen das meiste weg; fertig macht
# ihre Wände „Schlichten danach“, wenn es angehakt ist).
SCHRUPPEN_ZUERST = {
    "planfraesen": 0,
    "raeumen": 0,
    "restraeumen": 0,
    "nut": 0,
    "kontur": 0,
    "schruppen3d": 0,
    "restschruppen": 0,
    "zentrieren": 1,
    "bohren": 1,
    "bohrung": 1,
    "senken": 1,
    "reiben": 1,
    "gewinde": 1,
    "gewindefraesen": 1,
    "schlichtendanach": 2,
    "rest": 2,
    "schlichten3d": 2,
    "flanke": 2,
    "restschlichten": 2,
    "bleistift": 2,
    "fase": 3,
    "entgraten": 3,
    "entgraten3d": 3,
}


def _zahlenfeld(felder, name, text, tooltip, reihen, geaendert):
    eingabe = QtGui.QLineEdit()
    eingabe.setValidator(Zahlenpruefer(eingabe))
    eingabe.textChanged.connect(lambda _text: geaendert())
    felder[name] = eingabe
    reihen.reihe(text, tooltip, mit_einheit(eingabe, einheiten.einheit(einheiten.LAENGE)))
    return eingabe


class _Block:
    """Der Block einer Strategie im Fenster: der Haken als Titel, die Erklärung, Fräser und
    Einsatz, die Felder, das Ergebnis – und der Zustand dazu (Vorschau, Operation)."""

    def __init__(self, panel, strategie):
        self.panel = panel
        self.s = strategie
        self._fraeser = []  # die Werkzeuge in der Auswahl „Fräser“
        self._einsaetze = []
        self.vorwahl = None  # beim Ändern: Kennung des Fräsers der Operation
        self.tc_vorher = None  # beim Ändern: ihr Controller
        self.vorschau = None  # die grobe Bahn oder None
        self.genau = []  # die genauen Bahnen des Räumens im Nebenrechner (_genau_starten, W-036)
        self.schon_weg = False  # „Hier ist nichts mehr zu tun“ (Materialstand, W-012)
        self.zeit = None  # Minuten der Vorschau (bahn.zeit) – für den Wettbewerb
        self.ergebnis_basis = ""  # die Ergebniszeile ohne den Vergleich
        self.operation = None  # die angelegte Operation
        self.von_hand = False  # der Haken ist von Hand gesetzt – kein Vorschlag mehr
        self.fraeser_von_hand = False  # den Fräser hat man selbst gewählt (der Block „Fase“)
        self._setzt_selbst = False  # der Assistent wählt gerade den Fräser
        self.moeglich = True  # die Strategie geht mit der Wahl der Flächen
        # Schritt 2, der Überblick: der Haken mit dem Titel, das Ergebnis, rot was fehlt – oder,
        # passt die Strategie nicht zur Wahl, eine Zeile „Titel – was man anklicken muss“.
        self.widget = QtGui.QWidget()
        aufbau = QtGui.QVBoxLayout(self.widget)
        aufbau.setContentsMargins(0, 0, 0, 0)
        self.haken = QtGui.QCheckBox(strategie.titel())
        self.haken.setToolTip(strategie.text())
        schrift = self.haken.font()
        schrift.setBold(True)
        self.haken.setFont(schrift)
        self.haken.toggled.connect(lambda _an: self.panel.haken_geklickt(self))
        # Daneben „Vorschau“: die Werkzeugwege des Blocks im 3D (W-039; Manuel: „weg 1 ist so
        # und so [vorschau button]“) – nur, wenn seine Vorschau Punkte hat.
        kopfzeile = QtGui.QHBoxLayout()
        kopfzeile.setContentsMargins(0, 0, 0, 0)
        kopfzeile.addWidget(self.haken, 1)
        self.knopf_vorschau = knopf(
            tr("ba.frage.vorschau"),
            tr("ba.block.vorschau.tooltip"),
            lambda: self.panel._block_zeigen(self),
        )
        self.knopf_vorschau.setCheckable(True)
        self.knopf_vorschau.hide()
        kopfzeile.addWidget(self.knopf_vorschau)
        aufbau.addLayout(kopfzeile)
        self.kurz = _grau()
        self.kurz.setTextFormat(QtCore.Qt.RichText)
        self.kurz.hide()
        aufbau.addWidget(self.kurz)
        self.ergebnis = _Satz(GRAU_TEXT)
        for etikett in (self.ergebnis, self.ergebnis.spiegel):  # „T… auf … mm ausspannen“
            etikett.linkActivated.connect(self._hinweis_verweis)
        aufbau.addWidget(self.ergebnis)
        # Was nach den Operationen davor noch zu tun ist (W-012; Manuel: „Ist überhaupt noch
        # viel Material vorhanden, was ich wegmachen muss“).
        self.material = _Satz(GRAU_TEXT)
        aufbau.addWidget(self.material)
        self.hinweis = _Satz(ROT)
        for etikett in (self.hinweis, self.hinweis.spiegel):
            etikett.linkActivated.connect(self._hinweis_verweis)
        aufbau.addWidget(self.hinweis)
        # Ein Angebot mit Knopf (der Block „Fase“: der Fasenfräser aus der Werkzeugverwaltung).
        self.angebot = _Angebot()
        aufbau.addWidget(self.angebot.zeilen[0][0])
        # Schritt 3, die Einstellungen – nur solange angehakt: der Titel, die Erklärung, Fräser,
        # Einsatz, Felder und Haken, darunter dasselbe Ergebnis.
        self.einstellungen = QtGui.QWidget()
        unten = QtGui.QVBoxLayout(self.einstellungen)
        unten.setContentsMargins(0, 0, 0, 0)
        self.titel = QtGui.QLabel(strategie.titel())
        schrift = self.titel.font()
        schrift.setBold(True)
        self.titel.setFont(schrift)
        unten.addWidget(self.titel)
        self.erklaerung = _grau(strategie.text())
        unten.addWidget(self.erklaerung)
        self.inhalt = QtGui.QWidget()
        innen = QtGui.QVBoxLayout(self.inhalt)
        innen.setContentsMargins(0, 0, 0, 0)
        self.reihen = _Reihen()
        self.wahl_fraeser = QtGui.QComboBox()
        self.wahl_fraeser.currentIndexChanged.connect(lambda _i: self._fraeser_gewaehlt())
        self.reihen.reihe(tr("va.fraeser"), strategie.fraeser_tooltip(), self.wahl_fraeser)
        self.wahl_einsatz = QtGui.QComboBox()
        self.wahl_einsatz.currentIndexChanged.connect(lambda _i: self._einsatz_gewaehlt())
        self.reihen.reihe(tr("va.einsatz"), strategie.einsatz_tooltip(), self.wahl_einsatz)
        self.schnittwerte = _grau()
        self.reihen.ganz(self.schnittwerte)
        # Steht der Fräser nicht im Magazin der Maschine (W-002 Stufe H2, E3 a): gelb, was das
        # heißt, und ein Knopf, der ihn dort einträgt.
        self.magazin_zeile = QtGui.QWidget()
        magazin = QtGui.QVBoxLayout(self.magazin_zeile)
        magazin.setContentsMargins(0, 0, 0, 0)
        self.magazin_satz = QtGui.QLabel()
        self.magazin_satz.setWordWrap(True)
        self.magazin_satz.setStyleSheet(f"color: {GELB};")
        magazin.addWidget(self.magazin_satz)
        self.knopf_magazin = knopf(
            tr("mg.uebernehmen"), tr("mg.uebernehmen.tooltip"), self.ins_magazin
        )
        magazin.addWidget(self.knopf_magazin, 0, QtCore.Qt.AlignLeft)
        self.magazin_zeile.hide()
        self.reihen.ganz(self.magazin_zeile)
        if strategie.kennung == "raeumen":
            self.wahl_bahn = QtGui.QComboBox()
            self.wahl_bahn.addItem(tr("ba.raeumen.bisherig"), "automatisch")
            self.wahl_bahn.addItem(tr("ba.raeumen.schnell_frei"), ra.ADAPTIV_FREI)
            self.reihen.reihe(tr("ba.raeumen.bahn"), tr("ba.raeumen.bahn.tooltip"), self.wahl_bahn)
            self.freivorschub = QtGui.QLineEdit()
            self.freivorschub.setValidator(Zahlenpruefer(self.freivorschub))
            self.freivorschub.setPlaceholderText(
                groesse_zeigen(ra.FREIVORSCHUB, einheiten.VORSCHUB)
            )
            self.freivorschub.textChanged.connect(lambda _text: self.panel.vorschau_starten())
            self.freivorschub_zeile = mit_einheit(
                self.freivorschub, einheiten.einheit(einheiten.VORSCHUB)
            )
            self.reihen.reihe(
                tr("ba.raeumen.freivorschub"),
                tr("ba.raeumen.freivorschub.tooltip"),
                self.freivorschub_zeile,
            )
            self.freivorschub_etikett = self.reihen._beschriftungen[-1]
            self.freivorschub_zeile.hide()
            self.freivorschub_etikett.hide()
            self.wahl_bahn.currentIndexChanged.connect(lambda _i: self._raeumwahl_geaendert())
        self.felder = {}
        for feld, text, tooltip in strategie.felder():
            _zahlenfeld(self.felder, feld, text, tooltip, self.reihen, self.panel.vorschau_starten)
        if strategie.aufloesung:  # T-009: die Auflösung je Strategie, leer = Vorschlag
            _zahlenfeld(
                self.felder,
                "aufloesung",
                tr("ba.aufloesung"),
                strategie.aufloesung_erklaerung(
                    groesse_zeigen(strategie.aufloesung, einheiten.LAENGE)
                ),
                self.reihen,
                self.panel.vorschau_starten,
            )
        self.haken_felder = {}
        self._haken_texte = {}  # Name → (Beschriftung, Tooltip) – gesperrt kommt der Grund dazu
        for feld, text, tooltip, vorgabe in strategie.haken():
            kasten = QtGui.QCheckBox(text)
            kasten.setToolTip(tooltip)
            kasten.setChecked(vorgabe)
            kasten.toggled.connect(lambda _an: self.panel.vorschau_starten())
            self.haken_felder[feld] = kasten
            self._haken_texte[feld] = (text, tooltip)
            self.reihen.ganz(kasten)
        innen.addWidget(self.reihen.widget)
        # Die Eintauchstelle je geschlossener Nut (W-012 E1; Manuel: „an einer von mir aus
        # wählbaren Position in der Nut … aber natürlich mit Vorschlag“, Frage 2: a).
        self.eintauchen = {}  # Schlüssel der Nut → Anteil von A nach B; ohne: der Vorschlag
        self.stelle_waehlt = None  # „Im Bild wählen …“ wartet auf einen Klick: Schlüssel
        self._stellen = []  # aus der letzten Vorschau: (Schlüssel, Anteil, vorgeschlagen, A, B)
        self._stellen_zeilen = {}  # Schlüssel → die Teile ihrer Zeile
        self.stellen_box = QtGui.QWidget()
        self.stellen_aufbau = QtGui.QVBoxLayout(self.stellen_box)
        self.stellen_aufbau.setContentsMargins(0, 0, 0, 0)
        self.stellen_box.setVisible(False)
        innen.addWidget(self.stellen_box)
        unten.addWidget(self.inhalt)
        unten.addWidget(self.ergebnis.spiegel)
        unten.addWidget(self.material.spiegel)
        unten.addWidget(self.hinweis.spiegel)
        unten.addWidget(self.angebot.zeilen[1][0])

    # --- Zustand ---

    def aktiv(self):
        """Angehakt und möglich: Die Strategie wird gerechnet und angelegt (beim Ändern ist der
        Haken gesetzt und gesperrt)."""
        return self.moeglich and self.haken.isChecked()

    def zustand_zeigen(self):
        # Im Überblick (Schritt 2): passt die Strategie, der Haken und ihr Ergebnis – die Zeit
        # und um wie viel langsamer; passt sie nicht, der Titel und der Satz, was man dafür
        # anklicken muss. Ihre Felder stehen in Schritt 3, solange sie angehakt ist (Manuel,
        # 2026-10-02: „Du musst das irgendwie sinnvoll aufteilen … in Schritten“).
        self.haken.setVisible(self.moeglich)
        self.ergebnis.erlauben(self.moeglich)
        self.material.erlauben(self.moeglich)
        self.hinweis.erlauben(self.moeglich)
        self.angebot.erlauben(self.moeglich)
        self.kurz.setVisible(not self.moeglich)
        self.einstellungen.setVisible(self.aktiv())
        if not self.moeglich:
            titel = html.escape(self.s.titel())
            self.kurz.setText(f"<b>{titel}</b> – {html.escape(self.erklaerung.text())}")

    def fraeser(self):
        i = self.wahl_fraeser.currentIndex()
        return self._fraeser[i] if 0 <= i < len(self._fraeser) else None

    def einsatz(self):
        i = self.wahl_einsatz.currentIndex()
        return self._einsaetze[i] if 0 <= i < len(self._einsaetze) else None

    def vorschlag(self, feld):
        return self.s.vorschlag(feld, self.fraeser(), self.einsatz())

    def wert(self, feld):
        """Wert eines Felds (mm); leer oder ungültig gilt der Vorschlag."""
        text = self.felder[feld].text()
        try:
            return groesse_lesen(text, einheiten.LAENGE) if text.strip() else self.vorschlag(feld)
        except ValueError:
            return self.vorschlag(feld)

    def haken_pruefen(self):
        """Haken, die nur mit einer bestimmten Maschine oder einem bestimmten Fräser gehen
        (Strategie.haken_gesperrt): gesperrt, abgehakt, der Grund hinter der Beschriftung."""
        for feld, kasten in getattr(self, "haken_felder", {}).items():
            grund = self.s.haken_gesperrt(feld, self)
            text, tooltip = self._haken_texte[feld]
            verborgen = self.s.haken_verborgen(feld, self)
            kasten.setVisible(not verborgen)
            if verborgen:
                grund = grund or ""
            kasten.setEnabled(grund is None)
            # Selbst abgehakt, weil er nicht ging – geht er wieder (eine andere Maschine), kommt
            # der Haken zurück (Entgraten 3D: „angestellt“ ist an einer 5-Achs-Maschine an).
            selbst_ab = self.__dict__.setdefault("_selbst_abgehakt", set())
            if grund is not None and kasten.isChecked():
                kasten.setChecked(False)
                selbst_ab.add(feld)
            elif grund is None and feld in selbst_ab:
                selbst_ab.discard(feld)
                kasten.setChecked(True)
            kasten.setText(
                text if grund is None else tr("ba.haken.gesperrt", text=text, grund=grund)
            )
            warum = self.s.haken_gesperrt_warum(feld, self) if grund else None
            kasten.setToolTip(f"{tooltip}\n\n{warum}" if warum else tooltip)

    def werte(self):
        werte = {feld: self.wert(feld) for feld in self.felder}
        werte.update({feld: kasten.isChecked() for feld, kasten in self.haken_felder.items()})
        if self.s.kennung in ("schlichten3d", "restschlichten"):
            werte["aufnahme"] = self.panel.werkzeugaufnahme()  # für eine Empfehlung
        if self.s.kennung == "nut":
            werte["eintauchen_bei"] = dict(self.eintauchen)
        elif self.s.kennung == "raeumen":
            werte["variante"] = self.wahl_bahn.currentData()
            text = self.freivorschub.text().strip()
            try:
                werte["freivorschub"] = (
                    groesse_lesen(text, einheiten.VORSCHUB) if text else ra.FREIVORSCHUB
                )
            except ValueError:  # unfertige Eingabe: die Vorschau nennt den ungültigen Vorschub
                werte["freivorschub"] = 0.0
        return werte

    def _raeumwahl_geaendert(self):
        schnell = self.wahl_bahn.currentData() == ra.ADAPTIV_FREI
        self.freivorschub_zeile.setVisible(schnell)
        self.freivorschub_etikett.setVisible(schnell)
        self.panel.vorschau_starten()

    def raeumwahl_von(self, op):
        """Die gespeicherte Räumwahl zeigen; auch eine bisher vorgegebene Variante bleibt."""
        variante = str(op.Variante)
        bisher = "automatisch" if variante == ra.ADAPTIV_FREI else variante
        self.wahl_bahn.setItemData(0, bisher)
        if bisher != "automatisch":
            self.wahl_bahn.setItemText(0, tr("ba.raeumen.bisherig_variante", variante=bisher))
        self.wahl_bahn.setCurrentIndex(1 if variante == ra.ADAPTIV_FREI else 0)
        self.freivorschub.setText(groesse_zeigen(float(op.Freivorschub) * 60.0, einheiten.VORSCHUB))

    # --- Die Eintauchstelle der Nut (W-012 E1) ---

    def stellen_zeigen(self, stellen):
        """Je geschlossener Nut eine Zeile „Eintauchen bei“: die Liste – der Vorschlag, die beiden
        Enden, die Mitte, eine angeklickte Stelle – und „Im Bild wählen …“. Neu gebaut, wenn sich
        die Nuten ändern; sonst nur die Texte."""
        stellen = list(stellen or [])
        gleich = [st[0] for st in stellen] == [st[0] for st in self._stellen]
        self._stellen = stellen
        if not gleich:
            while self.stellen_aufbau.count():
                alt = self.stellen_aufbau.takeAt(0).widget()
                if alt is not None:
                    alt.deleteLater()
            self._stellen_zeilen = {}
            for nummer, (schluessel, *_rest) in enumerate(stellen):
                self._stellen_zeilen[schluessel] = self._stelle_zeile(nummer, len(stellen))
        for schluessel, anteil, vorgeschlagen, a, b in stellen:
            self._stelle_fuellen(schluessel, anteil, vorgeschlagen, a, b)
        self.stellen_box.setVisible(bool(stellen))

    def _stelle_zeile(self, nummer, anzahl):
        zeile = QtGui.QWidget()
        aufbau = QtGui.QHBoxLayout(zeile)
        aufbau.setContentsMargins(0, 0, 0, 0)
        text = tr("ba.nut.eintauchen")
        if anzahl > 1:
            text = tr("ba.nut.eintauchen.nut", n=nummer + 1)
        etikett = QtGui.QLabel(text)
        etikett.setToolTip(tr("ba.nut.eintauchen.tooltip"))
        aufbau.addWidget(etikett)
        wahl = QtGui.QComboBox()
        wahl.setToolTip(tr("ba.nut.eintauchen.tooltip"))
        ruhiges_mausrad(wahl)
        aufbau.addWidget(wahl, 1)
        im_bild = QtGui.QPushButton(tr("ba.nut.im_bild"))
        im_bild.setToolTip(tr("ba.nut.im_bild.tooltip"))
        im_bild.setCheckable(True)
        aufbau.addWidget(im_bild)
        self.stellen_aufbau.addWidget(zeile)
        teile = {"wahl": wahl, "im_bild": im_bild}
        wahl.currentIndexChanged.connect(lambda _i, t=teile: self._stelle_gewaehlt(t))
        im_bild.toggled.connect(lambda an, t=teile: self._im_bild(t, an))
        return teile

    def _stelle_fuellen(self, schluessel, anteil, vorgeschlagen, a, b):
        """Die Liste einer Nut: an erster Stelle der Vorschlag, dann Ende, Ende, Mitte und die
        angeklickte Stelle; gewählt, was im Block steht."""
        teile = self._stellen_zeilen[schluessel]
        teile["schluessel"], teile["a"], teile["b"] = schluessel, a, b
        wahl = teile["wahl"]

        def ort(t):
            x = a[0] + (b[0] - a[0]) * t
            y = a[1] + (b[1] - a[1]) * t
            return {
                "x": groesse_zeigen(x, einheiten.LAENGE) or "0",
                "y": groesse_zeigen(y, einheiten.LAENGE) or "0",
            }

        if vorgeschlagen and anteil is not None:
            vorschlag = tr("ba.nut.vorschlag.stelle", **ort(anteil))
        elif vorgeschlagen:
            vorschlag = tr("ba.nut.vorschlag.enden")
        else:  # gewählt – der Vorschlag rechnet erst ohne Wahl
            vorschlag = tr("ba.nut.vorschlag")
        eintraege = [
            (vorschlag, None),
            (tr("ba.nut.ende", **ort(0.0)), 0.0),
            (tr("ba.nut.ende", **ort(1.0)), 1.0),
            (tr("ba.nut.mitte", **ort(0.5)), 0.5),
        ]
        gewaehlt = self.eintauchen.get(schluessel)
        if gewaehlt is not None and all(abs(gewaehlt - wert) > 1e-6 for _t, wert in eintraege[1:]):
            eintraege.append((tr("ba.nut.angeklickt", **ort(gewaehlt)), gewaehlt))
        wahl.blockSignals(True)
        try:
            wahl.clear()
            for text, wert in eintraege:
                wahl.addItem(text, wert)
            index = 0
            if gewaehlt is not None:
                index = next(
                    (i for i, (_t, w) in enumerate(eintraege) if w is not None
                     and abs(w - gewaehlt) < 1e-6),
                    0,
                )  # fmt: skip
            wahl.setCurrentIndex(index)
        finally:
            wahl.blockSignals(False)

    def _stelle_gewaehlt(self, teile):
        if self.panel._fuellt or "schluessel" not in teile:
            return
        wert = teile["wahl"].currentData()
        if wert is None:
            self.eintauchen.pop(teile["schluessel"], None)
        else:
            self.eintauchen[teile["schluessel"]] = float(wert)
        self.panel.vorschau_starten()

    def _im_bild(self, teile, an):
        """„Im Bild wählen …“: der nächste Klick in die Nut ist ihre Eintauchstelle."""
        for andere in self._stellen_zeilen.values():
            if andere is not teile and andere["im_bild"].isChecked():
                andere["im_bild"].blockSignals(True)
                andere["im_bild"].setChecked(False)
                andere["im_bild"].blockSignals(False)
        self.stelle_waehlt = teile.get("schluessel") if an else None

    def stelle_angeklickt(self, punkt):
        """Der Klick für „Im Bild wählen …“: die Stelle der Mittellinie, die ihm am nächsten
        liegt, wird die Eintauchstelle der Nut."""
        teile = self._stellen_zeilen.get(self.stelle_waehlt)
        self.stelle_waehlt = None
        if teile is None:
            return
        teile["im_bild"].blockSignals(True)
        teile["im_bild"].setChecked(False)
        teile["im_bild"].blockSignals(False)
        a, b = teile["a"], teile["b"]
        dx, dy = b[0] - a[0], b[1] - a[1]
        laenge2 = dx * dx + dy * dy
        anteil = 0.0
        if laenge2 > 1e-12:
            x, y = float(punkt[0]), float(punkt[1])
            anteil = min(1.0, max(0.0, ((x - a[0]) * dx + (y - a[1]) * dy) / laenge2))
        self.eintauchen[teile["schluessel"]] = anteil
        self.panel.vorschau_starten()

    def kann_anlegen(self):
        return self.fraeser() is not None and self.einsatz() is not None and not self.hinweis.text()

    def merken(self):
        if self.fraeser() is not None:
            _parameter().SetString(self.s.gemerkt, self.fraeser().kennung)

    # --- Fräser und Einsatz ---

    @staticmethod
    def _passende_einsaetze(werkzeug, werkstoff):
        """Die Einsätze mit Drehzahl und Vorschub – nur mit ihnen gibt es einen Controller."""
        return [e for e in werkzeug.einsaetze(werkstoff) if js.werte(werkzeug, e)[1] > 0]

    def fraeser_setzen(self, werkzeug):
        """Wählt `werkzeug` in der Auswahl „Fräser“, wenn es dort steht; gibt zurück, ob."""
        kennungen = [w.kennung for w in self._fraeser]
        if werkzeug is None or werkzeug.kennung not in kennungen:
            return False
        self.wahl_fraeser.setCurrentIndex(mg.index_von(self._fraeser, werkzeug))
        return True

    def fraeser_fuellen(self, bibliothek, werkstoff):
        """Die Werkzeuge, mit denen die Strategie arbeitet (_Strategie.werkzeug_passt: Fräser mit
        ebener Stirn, beim Bohren Bohrer), mit Schnittwerten für den Werkstoff; vorgewählt der
        bisher gewählte, beim Ändern der der Operation, sonst der zuletzt benutzte, sonst
        einer mit dem ersten Einsatz der Reihenfolge, sonst ein Schaftfräser."""
        vorher = self.fraeser()
        # Mit Magazin der Maschine (W-002 Stufe H2, E7 a) dessen Werkzeuge vorn, beladene zuerst.
        magazin = self.panel.magazin()
        passende = [
            w
            for w in mg.sortiert(bibliothek.werkzeuge, magazin, bibliothek)
            if w.durchmesser > 0
            and self.s.werkzeug_passt(w)
            and self._passende_einsaetze(w, werkstoff)
        ]
        self._fraeser = [w for w in passende if self.panel.von_vorn_moeglich(w)]
        self._nur_radial = bool(passende) and not self._fraeser
        kennungen = [w.kennung for w in self._fraeser]
        gemerkt = _parameter().GetString(self.s.gemerkt, "")
        erster = self.s.einsatz_reihenfolge[0] if self.s.einsatz_reihenfolge else None
        if vorher is not None and vorher.kennung in kennungen:
            wahl = mg.index_von(self._fraeser, vorher)
        elif self.vorwahl in kennungen:
            wahl = kennungen.index(self.vorwahl)
        elif gemerkt in kennungen and (
            magazin is None
            or mg.rang(self._fraeser[kennungen.index(gemerkt)], magazin) != mg.NICHT_IM_MAGAZIN
        ):
            wahl = kennungen.index(gemerkt)
        else:
            wahl = min(
                range(len(self._fraeser)),
                key=lambda i: (
                    not any(
                        e.art == erster
                        for e in self._passende_einsaetze(self._fraeser[i], werkstoff)
                    ),
                    mg.rang(self._fraeser[i], magazin) == mg.NICHT_IM_MAGAZIN,
                    self._fraeser[i].art != self.s.bevorzugt,
                    i,
                ),
                default=0,
            )
        self.panel._fuellt = True
        try:
            self.wahl_fraeser.clear()
            for werkzeug in self._fraeser:
                self.wahl_fraeser.addItem(dezimal(mg.zeile(werkzeug, magazin)))
            if self._fraeser:
                self.wahl_fraeser.setCurrentIndex(wahl)
        finally:
            self.panel._fuellt = False
        self.magazin_pruefen()
        self.einsatz_fuellen(werkstoff)

    def _fraeser_gewaehlt(self):
        self.haken_pruefen()
        if not self.panel._fuellt:
            if not self._setzt_selbst:
                self.fraeser_von_hand = True
            self.magazin_pruefen()
            self.einsatz_fuellen(self.panel.werkstoff())
            if self.s.kennung == "fase":
                self.panel._fase_angebot()

    def magazin_pruefen(self):
        """Der gelbe Satz, wenn der gewählte Fräser nicht im Magazin der Maschine steht (E3 a):
        Das Programm ruft ihn mit einer freien Nummer auf, an der Steuerung fehlt er."""
        werkzeug = self.fraeser()
        text = mg.fehlt_text(werkzeug, self.panel.magazin()) if werkzeug is not None else ""
        self.magazin_satz.setText(text)
        self.magazin_zeile.setVisible(bool(text))

    def ins_magazin(self):
        """„Ins Magazin übernehmen“: der gewählte Fräser ins Magazin der Maschine – mit der
        Nummer, die er im Job schon hat, sonst der nächsten freien –, die Werkzeugverwaltung
        gespeichert, die Listen neu. Gibt den Eintrag zurück – None, wenn es nicht geht."""
        magazin = self.panel.magazin()
        werkzeug = self.fraeser()
        if magazin is None or werkzeug is None:
            return None
        eintrag = mg.uebernehmen(self.panel.bibliothek, magazin, werkzeug, self.panel.job)
        self.panel._bearbeitung_fuellen()
        return eintrag

    def einsatz_fuellen(self, werkstoff):
        """Die Einsätze des Fräsers; vorgewählt nach der Reihenfolge der Strategie; beim
        Ändern der, mit dem der Controller gesetzt ist."""
        werkzeug = self.fraeser()
        self._einsaetze = (
            self._passende_einsaetze(werkzeug, werkstoff) if werkzeug is not None else []
        )
        arten = [e.art for e in self._einsaetze]
        wahl = next((arten.index(a) for a in self.s.einsatz_reihenfolge if a in arten), 0)
        if self.tc_vorher is not None and werkzeug is not None and werkzeug.kennung == self.vorwahl:
            gemerkt = js.vorgeschlagener_einsatz(self.tc_vorher, self._einsaetze, self.panel.job)
            wahl = gemerkt if gemerkt >= 0 else wahl
        self.panel._fuellt = True
        try:
            self.wahl_einsatz.clear()
            for einsatz in self._einsaetze:
                self.wahl_einsatz.addItem(wz.einsatz_name(einsatz))
            if self._einsaetze:
                self.wahl_einsatz.setCurrentIndex(wahl)
        finally:
            self.panel._fuellt = False
        self._einsatz_gewaehlt()

    def _einsatz_gewaehlt(self):
        """Drehzahl und Vorschub, die Vorschläge in die Felder."""
        if self.panel._fuellt:
            return
        werkzeug, einsatz = self.fraeser(), self.einsatz()
        if werkzeug is None or einsatz is None:
            self.schnittwerte.setText("")
        else:
            n, vf, _senkrecht = js.werte_im_job(werkzeug, einsatz, self.panel.job)
            self.schnittwerte.setText(
                tr("va.schnittwerte", n=f"{n:.0f}", vf=groesse_fest(vf, einheiten.VORSCHUB, 0))
            )
        for feld, eingabe in self.felder.items():
            eingabe.setPlaceholderText(self.s.platzhalter(feld, werkzeug, einsatz))
        self.panel.vorschau_starten()

    # --- Vorschau ---

    def vorschau_rechnen(self, job, flaechen, zusatz=None):
        """Die grobe Bahn – Lagen, Zeilen bzw. Bahnen, Zeit – und damit „Anlegen“ weiß, ob
        es geht; der Grund steht rot. `zusatz`: Werte, die der Assistent vorgibt (die Breite
        der Kontur nach dem Räumen). Am Stück: Rechnet ein Nebenrechner, wartet es auf ihn."""
        for schritt in self.vorschau_schritte(job, flaechen, zusatz):
            _abwarten(schritt)

    def vorschau_schritte(self, job, flaechen, zusatz=None):
        """vorschau_rechnen als Schritte (ein Generator): Rechnet die Strategie in einem
        Nebenrechner (`hintergrund`, P-2026-10-11-23), gibt er den Auftrag aus – weiter geht es,
        wenn er erledigt ist; scheitert er, rechnet es hier."""
        self.vorschau = None
        self.zeit = None
        self.schon_weg = False
        self.ergebnis_basis = ""
        self.ergebnis.setText("")
        self.material.setText("")
        self.hinweis.setText("")
        self._angebot_flaechen = list(flaechen)  # für _bohrer_angebot
        self.zusatz_zuletzt = dict(zusatz or {})  # für den anderen Weg einer Frage (W-039)
        werkzeug, einsatz = self.fraeser(), self.einsatz()
        if werkzeug is None or einsatz is None:
            nur_radial = getattr(self, "_nur_radial", False)
            text = tr("ba.von_vorn.nur_radial") if nur_radial else tr("va.planfraeser.keiner")
            self.hinweis.setText(text)
            return
        _n, vorschub, senkrecht = js.werte_im_job(werkzeug, einsatz, self.panel.job)
        werte = dict(self.werte(), vorschub=vorschub, eintauchen=senkrecht, **(zusatz or {}))
        # Woraus nichts anders ist als beim letzten Mal, kommt dasselbe heraus – nur das ändert
        # sich, wovon die Vorschau abhängt (am Testteil warm 4,2 s je Lauf für alle Blöcke).
        schluessel = _merk_schluessel(self.s.kennung, job, werkzeug, einsatz, werte, flaechen)
        merk = getattr(self.panel, "vorschau_merk", None)
        if schluessel is not None and merk is not None and schluessel in merk:
            merk.move_to_end(schluessel)
            self._gemerkt_zeigen(merk[schluessel])
            fehler_merk = self.panel.__dict__.get("_fehler_merk", {})
            if schluessel in fehler_merk:
                was = ("fehler", *fehler_merk[schluessel])
            elif self.vorschau is not None:
                zeit_ = _zeit_text(self.zeit) if self.zeit is not None else "?"
                was = ("bahn", zeit_, self.vorschau)
            else:
                was = None
            if was is not None:
                self._empfehlung_anstossen(job, werkzeug, flaechen, was)
            return
        frei = mitgerechnet = None
        auftrag = self._im_hintergrund(job, werkzeug, werte, flaechen, vorschub, senkrecht)
        if auftrag is not None:
            yield auftrag
            mitgerechnet = _aus_dem_hintergrund(auftrag)
        if mitgerechnet is not None and mitgerechnet[0] == "fehler":
            self.hinweis.setText(self._fehler_text(mitgerechnet[1], mitgerechnet[3]))
            self.schon_weg = mitgerechnet[2]
            self._merken(merk, schluessel)
            self._fehler_merken(schluessel, mitgerechnet[1], mitgerechnet[3])
            self._vorbohrer_angebot()
            self._empfehlung_anstossen(
                job, werkzeug, flaechen, ("fehler", mitgerechnet[1], mitgerechnet[3])
            )
            return
        if mitgerechnet is not None:
            self.vorschau, frei = mitgerechnet[1]
            # Die Flanke und die Kugel unter dem Rand aus dem Nebenrechner: „Anlegen“ nimmt sie,
            # statt sie noch einmal im Hauptprozess zu rechnen (flanke_bahn.planen,
            # hinterschnitt_bahn.planen; am 5-Achs-Teil „tief“ 30 s).
            if isinstance(self.vorschau, flb.Flankenbahn):
                flb.geplant_merken(self.vorschau)
            elif isinstance(self.vorschau, hsb.Bahn):
                hsb.geplant_merken(self.vorschau)
        else:
            try:
                self.vorschau = self.s.vorschau(job, werkzeug, werte, flaechen)
            except (ValueError, RuntimeError) as fehler:  # RuntimeError: OCC am Netz
                daten = getattr(fehler, "daten", None)
                self.hinweis.setText(self._fehler_text(str(fehler), daten))
                self.schon_weg = isinstance(fehler, mst.SchonWeg)
                self._merken(merk, schluessel)
                self._fehler_merken(schluessel, str(fehler), daten)
                self._vorbohrer_angebot()
                self._empfehlung_anstossen(job, werkzeug, flaechen, ("fehler", str(fehler), daten))
                return
        self.zeit = self.s.zeit(self.vorschau, vorschub, senkrecht) if vorschub > 0 else None
        if self.zeit is not None and self.s.kennung in IM_FREIEN_SCHNELL:
            self.zeit = (
                frei
                if frei is not None
                else _zeit_im_freien(job, werkzeug, werte, self.vorschau, vorschub, senkrecht)
            )
        self._ohne_vorbohren_rechnen(job, werkzeug, werte, vorschub, senkrecht)
        zeit = _zeit_text(self.zeit) if self.zeit is not None else "?"
        self.ergebnis_basis = self._mit_ecken(
            self._mit_ausspannen(self.s.ergebnis_text(self.vorschau, zeit), self.vorschau),
            self.vorschau,
        )
        self.ergebnis.setText(self.ergebnis_basis)
        self.material.setText(_material_text(self.vorschau))
        self._vorschau_knopf_zeigen()
        self._vorbohrer_angebot()
        self._empfehlung_anstossen(job, werkzeug, flaechen, ("bahn", zeit, self.vorschau))
        if self.s.kennung == "nut":
            self.stellen_zeigen(getattr(self.vorschau, "stellen", None))
        if isinstance(self.s, _Raeumen) and getattr(self.vorschau, "variante", None) == "adaptiv":
            self._genau_starten(job, werkzeug, werte, flaechen)
        if isinstance(self.s, _Schlichten3D) and isinstance(self.vorschau, hsb.Bahn):
            self._genau_unter_dem_rand(job, werkzeug, werte, flaechen)
        self._merken(merk, schluessel)

    def _ohne_vorbohren_rechnen(self, job, werkzeug, werte, vorschub, senkrecht):
        """Die Zeit des Wegs ohne Vorbohren (raeumen.Vorbohren.ohne_frei) wie die eigene – im
        Nebenrechner schon gerechnet, sonst hier (die Frage „Eintauchen“, W-039)."""
        vorgebohrt = getattr(self.vorschau, "vorbohren", None)
        if vorgebohrt is None or not vorgebohrt.ohne_punkte or vorgebohrt.ohne_frei is not None:
            return
        if vorschub <= 0:
            return
        ohne = types.SimpleNamespace(punkte=vorgebohrt.ohne_punkte)
        if self.s.kennung in IM_FREIEN_SCHNELL:
            vorgebohrt.ohne_frei = _zeit_im_freien(job, werkzeug, werte, ohne, vorschub, senkrecht)
        else:
            vorgebohrt.ohne_frei = self.s.zeit(ohne, vorschub, senkrecht)

    def _genau_starten(self, job, werkzeug, werte, flaechen):
        """Die genaue Bahn des Räumens schon jetzt in einem Nebenrechner (W-036; Manuel,
        2026-10-23: „bitte immer darauf achten das alle resourcen genutzt werden !“): Die Vorschau
        rechnet adaptiv nur grob, „Anlegen“ dann genau – am Testteil 4 s, in denen nur der
        Adaptiv-Kern rechnet, eine Fläche nach der anderen. So rechnet er, während man noch
        schaut; „Anlegen“ holt die Ergebnisse ab (BearbeitungPanel._genau_abholen). Es bleiben
        die letzten GENAU_JE_BLOCK; ein älterer, der noch wartet, fällt weg."""
        from . import nebenrechner as nr

        pool = nr.pool()
        if not pool.verfuegbar():
            return
        while len(self.genau) >= GENAU_JE_BLOCK:
            alt = self.genau.pop(0)
            if not alt.erledigt and getattr(alt, "arbeiter", None) is None:
                pool.abbrechen(alt)
        try:
            *argumente, weiter = self.s._argumente(werkzeug, werte, flaechen)
            kopie = pool.kopie(job.Document, wiederverwenden=True)
            self.genau.append(
                pool.auftrag(
                    "bearbeitung_vorschau", "raeumen_genau", kopie, job.Name, *argumente, weiter
                )
            )
        except Exception as fehler:  # noqa: BLE001 – dann rechnet „Anlegen“ wie bisher
            FreeCAD.Console.PrintLog(f"CAM-Addon: genaue Bahn im Nebenrechner: {fehler}\n")

    def _genau_unter_dem_rand(self, job, werkzeug, werte, flaechen):
        """Die Bahn unter dem Rand (3D-Schlichten, Restschlichten), wie „Anlegen“ sie rechnet –
        Schritt wie die Operation statt gröber wie die Vorschau, die Sicherheitshöhe wie ihre
        (StartDepth plus SafeHeightOffset des Jobs) – in einem Nebenrechner, während man noch
        schaut; „Anlegen“ holt sie ab (_genau_abholen → hinterschnitt_bahn.geplant_merken). Am
        5-Achs-Teil „tief“ rechnete „Anlegen“ sie sonst 30 s im Hauptprozess. Mit Vorschlichten
        rechnen es und das Schlichten je in einem Nebenrechner, zugleich (nacheinander wartete
        „Anlegen“ dort 23 s)."""
        from . import nebenrechner as nr

        pool = nr.pool()
        if not pool.verfuegbar():
            return
        try:
            argumente, weiter = self.s._argumente(werkzeug, werte, flaechen)
            versatz = getattr(getattr(job, "SetupSheet", None), "SafeHeightOffset", None)
            versatz = float(getattr(versatz, "Value", versatz))
            weiter = dict(weiter, schritt=s3b.SCHRITT, sicher=pf.rohteil_von_oben(job)[4] + versatz)
            teile = [weiter]
            if "vorschlichten_bis" in weiter:
                ohne = {k: v for k, v in weiter.items() if k != "vorschlichten_bis"}
                teile = [ohne, dict(weiter, nur_vorschlichten=True)]
            while self.genau and len(self.genau) + len(teile) > GENAU_JE_BLOCK:
                alt = self.genau.pop(0)
                if not alt.erledigt and getattr(alt, "arbeiter", None) is None:
                    pool.abbrechen(alt)
            kopie = pool.kopie(job.Document, wiederverwenden=True)
            for teil in teile:
                self.genau.append(
                    pool.auftrag(
                        "bearbeitung_vorschau",
                        "schlichten3d_genau",
                        kopie,
                        job.Name,
                        argumente,
                        teil,
                    )
                )
        except Exception as fehler:  # noqa: BLE001 – dann rechnet „Anlegen“ wie bisher
            FreeCAD.Console.PrintLog(f"CAM-Addon: Bahn unter dem Rand im Nebenrechner: {fehler}\n")

    def _fehler_text(self, satz, daten):
        """Der rote Satz zur Vorschau – stößt der Halter an (flanke.vorschau: Daten
        „ausspannen“), mit dem nächsten Schritt dahinter: „T5 auf … mm ausspannen“, oder dass das
        Werkzeug dafür zu kurz ist (reichweite.ausspannen_auf; wie im 4-Achs-Assistenten)."""
        ausspannen = daten.get("ausspannen") if isinstance(daten, dict) else None
        empfehlung = daten.get("empfehlung") if isinstance(daten, dict) else None
        return self._ausspannen_oder_empfehlung(satz, ausspannen, empfehlung) or satz

    def _ausspannen_oder_empfehlung(self, satz, ausspannen, empfehlung):
        """`satz` und der nächste Schritt: „T5 auf … mm ausspannen“, wenn das Werkzeug dafür lang
        genug ist – eine Empfehlung (empfehlung.py: ein anderer Halter, ein anderer Fräser) dann
        als „Oder: …“; sonst die Empfehlung allein (bis P-2026-10-25-67 verdrängte sie das
        Ausspannen und sagte „mit dem Magazin geht es nicht“, obwohl T5 nur weiter heraus musste).
        "" ohne beides."""
        dazu = self._ausspannen_verweis(*ausspannen) if ausspannen else ""
        geht = dazu.startswith("<a ")
        if empfehlung is not None and not (geht and empfehlung == _keine_empfehlung()):
            # Nach „T5 ist dafür zu kurz“ bzw. „… ausspannen“ – sonst allein.
            dazu = f"{dazu} {self._empfehlung_text(empfehlung, oder=geht)}".strip()
        return f"{html.escape(satz, quote=False)} {dazu}" if dazu else ""

    def _empfehlung_text(self, empfehlung, oder=False):
        """Der Satz zur Empfehlung (empfehlung.Empfehlung) mit „So einrichten“ dahinter (Verweis
        „empfehlung:“, _hinweis_verweis) – oder, dass auch nichts anderes ginge (KEINE). `oder`:
        nach „… ausspannen“ – „Oder: …“."""
        from . import empfehlung as em

        if empfehlung == em.KEINE:
            return html.escape(tr("emp.keine"), quote=False)
        self._empfehlung = empfehlung
        dazu = []
        if empfehlung.halter_neu:
            dazu.append(tr("emp.halter_neu"))
        if not empfehlung.im_magazin:
            dazu.append(tr("emp.nicht_im_magazin"))
        werte = {
            "werkzeug": empfehlung.werkzeug_text,
            "halter": empfehlung.halter.name,
            "heraus": einheiten.text(empfehlung.heraus, einheiten.LAENGE, 0),
            "laenge": einheiten.text(empfehlung.laenge, einheiten.LAENGE, 0),
        }
        text = tr("emp.oder", **werte) if oder else tr("emp.text", **werte)
        if dazu:
            text += " " + tr("emp.dazu", dazu="; ".join(dazu))
        knopf = html.escape(tr("emp.einrichten"))
        return f'{html.escape(text, quote=False)} <a href="empfehlung:">{knopf}</a>'

    def _empfehlung_anstossen(self, job, werkzeug, flaechen, was):
        """Unter dem Rand: Stößt etwas an (Bahn.pruefung, auch im Fehler) oder bleiben Ecken
        (Bahn.ecken), die Empfehlung (bearbeitung_vorschau.empfehlung) in einem eigenen Auftrag –
        die Vorschau ist schon zu sehen; je Fräser, Halter, Länge und Flächen einmal gerechnet
        (gemerkt), ein neuer Klick bricht sie nicht ab. Ist sie da, kommt sie in den Satz
        (_empfehlung_zeigen). `was`: ("fehler", Satz, Daten) oder ("bahn", Zeittext, Bahn)."""
        from . import nebenrechner as nr
        from . import reichweite as rw

        self._empfehlung_kontext = None
        if was[0] == "fehler":
            daten = was[2] if isinstance(was[2], dict) else {}
            pruefung = {
                "pruefung": daten.get("pruefung"),
                "ausspannen": daten.get("ausspannen"),
                "flanke": daten.get("flanke"),
            }
            ecken = None
        else:
            bahn = was[2]
            if not getattr(bahn, "hinterschnitt", False):
                return
            pruefung = {"pruefung": bahn.pruefung, "ausspannen": bahn.ausspannen}
            # Einen Fräser für die Ecken schlägt nur das 3D-Schlichten vor (_mit_ecken).
            ecken = (
                bahn.ecken if bahn.ecken_radius > 0 and self.s.kennung == "schlichten3d" else None
            )
        if not pruefung["pruefung"] and not pruefung.get("flanke") and not ecken:
            return
        bibliothek = self.panel.bibliothek
        if bibliothek is None or werkzeug is None:
            return
        halter = bibliothek.halter_fuer_pruefung(werkzeug)
        try:
            laenge = rw.laenge_des_werkzeugs(werkzeug, bibliothek)[0]
        except Exception:  # noqa: BLE001
            laenge = 0.0
        schluessel = (
            self.s.kennung,
            werkzeug.kennung,
            getattr(halter, "kennung", ""),
            round(float(laenge), 2),
            tuple(flaechen),
            bool(pruefung["pruefung"]),
            bool(ecken),
        )
        self._empfehlung_kontext = (schluessel, was)
        gemerkt = self.panel.__dict__.setdefault("_empfehlungen", {})
        if schluessel in gemerkt:
            self._empfehlung_zeigen(schluessel, gemerkt[schluessel])
            return
        laeuft = self.panel.__dict__.setdefault("_empfehlung_laeuft", {})
        if schluessel in laeuft and not laeuft[schluessel].erledigt:
            self._empfehlung_suche_zeigen()
            return
        pool = nr.pool()
        if not pool.verfuegbar():
            return
        try:
            kopie = pool.kopie(job.Document, wiederverwenden=True)
            auftrag = pool.auftrag(
                "bearbeitung_vorschau",
                "empfehlung",
                kopie,
                job.Name,
                pruefung,
                ecken,
                werkzeug.kennung,
                self.panel.werkzeugaufnahme(),
            )
        except Exception as fehler:  # noqa: BLE001 – dann eben ohne Empfehlung
            FreeCAD.Console.PrintLog(f"CAM-Addon: Empfehlung im Nebenrechner: {fehler}\n")
            return
        laeuft[schluessel] = auftrag
        auftrag.bei_fertig = lambda _a, s=schluessel: QtCore.QTimer.singleShot(
            0, functools.partial(self._empfehlung_fertig, s)
        )
        self._empfehlung_suche_zeigen()

    def _fehler_merken(self, schluessel, satz, daten):
        """Satz und Daten eines Fehlers der Vorschau zum Schlüssel – zeigt die Vorschau ihn aus dem
        Gemerkten, rechnet die Empfehlung damit (_empfehlung_anstossen)."""
        if schluessel is None or not isinstance(daten, dict):
            return
        if not daten.get("pruefung") and not daten.get("flanke"):
            return
        merk = self.panel.__dict__.setdefault("_fehler_merk", {})
        merk[schluessel] = (satz, daten)
        while len(merk) > VORSCHAU_MERK:
            merk.pop(next(iter(merk)))

    def _empfehlung_fertig(self, schluessel):
        """Der Auftrag der Empfehlung ist fertig: gemerkt, und gilt er noch, gezeigt."""
        laeuft = self.panel.__dict__.get("_empfehlung_laeuft", {})
        auftrag = laeuft.pop(schluessel, None)
        if auftrag is None or self.panel.geschlossen:
            return
        ergebnis = auftrag.ergebnis if auftrag.fertig else (None, None)
        if not auftrag.fertig and auftrag.fehler is not None:
            FreeCAD.Console.PrintLog(f"CAM-Addon: Empfehlung gescheitert: {auftrag.fehler}\n")
        self.panel.__dict__.setdefault("_empfehlungen", {})[schluessel] = ergebnis
        self._empfehlung_zeigen(schluessel, ergebnis)

    def _empfehlung_suche_zeigen(self):
        """Solange die Empfehlung rechnet: ein grauer Satz dahinter."""
        kontext = getattr(self, "_empfehlung_kontext", None)
        if kontext is None:
            return
        _schluessel, was = kontext
        suche = html.escape(tr("emp.sucht"), quote=False)
        if was[0] == "fehler":
            self.hinweis.setText(f"{self._fehler_text(was[1], was[2])} <i>{suche}</i>")
        else:
            self.ergebnis.setText(f"{self.ergebnis_basis} <i>{suche}</i>")

    def _empfehlung_zeigen(self, schluessel, ergebnis):
        """Die Empfehlung in den Satz – nur, wenn der Block noch dieselbe Vorschau zeigt."""
        kontext = getattr(self, "_empfehlung_kontext", None)
        if kontext is None or kontext[0] != schluessel:
            return
        haupt, ecke = ergebnis if ergebnis else (None, None)
        _s, was = kontext
        if was[0] == "fehler":
            daten = dict(was[2]) if isinstance(was[2], dict) else {}
            if haupt is not None:
                daten["empfehlung"] = haupt
            self.hinweis.setText(self._fehler_text(was[1], daten))
            return
        zeit, bahn = was[1], was[2]
        bahn.empfehlung, bahn.ecken_empfehlung = haupt, ecke
        self.ergebnis_basis = self._mit_ecken(
            self._mit_ausspannen(self.s.ergebnis_text(bahn, zeit), bahn), bahn
        )
        self.ergebnis.setText(self.ergebnis_basis)

    def _ecken_werkzeug_anlegen(self):
        """„In der Werkzeugverwaltung anlegen und Restschlichten anhaken“: der vorgeschlagene
        Kugelfräser für die Ecken (mit Halter und Auskragung, empfehlung.einrichten), gespeichert,
        das Restschlichten mit ihm angehakt."""
        from . import empfehlung as em

        empfehlung = getattr(self, "_ecken_empfehlung", None)
        bibliothek = self.panel.bibliothek
        if empfehlung is None or bibliothek is None:
            return
        self.panel.magazin()
        werkzeug = em.einrichten(empfehlung, bibliothek)
        if werkzeug is None:
            return
        bibliothek.speichern()
        self.panel._werkzeuge_gespeichert()
        self.panel.restschlichten_mit(werkzeug.kennung)

    def _empfehlung_einrichten(self):
        """„So einrichten“: die Empfehlung in die Werkzeugverwaltung (empfehlung.einrichten),
        gespeichert; ein anderer Fräser wird gewählt; der Assistent rechnet neu."""
        from . import empfehlung as em

        empfehlung = getattr(self, "_empfehlung", None)
        bibliothek = self.panel.bibliothek
        if empfehlung is None or bibliothek is None:
            return
        self.panel.magazin()  # das Magazin der Maschine (dort gilt der Halter des Platzes)
        werkzeug = em.einrichten(empfehlung, bibliothek)
        if werkzeug is None:
            return
        bibliothek.speichern()
        self.panel._werkzeuge_gespeichert()
        kennungen = [w.kennung for w in self._fraeser]
        if empfehlung.anderes_werkzeug and werkzeug.kennung in kennungen:
            self.wahl_fraeser.setCurrentIndex(kennungen.index(werkzeug.kennung))
            self.fraeser_von_hand = True

    def _ausspannen_verweis(self, heraus, mindestens):
        """„T5 auf … mm ausspannen“ als Verweis (_hinweis_verweis) – oder, dass das Werkzeug dafür
        zu kurz ist (reichweite.ausspannen_auf); "" ohne Fräser oder Werkzeugverwaltung."""
        from . import reichweite as rw

        werkzeug = self.fraeser()
        bibliothek = self.panel.bibliothek
        if mindestens is None or werkzeug is None or bibliothek is None:
            return ""
        kennung = rw.ausspannen_kennung(werkzeug)
        auf = rw.ausspannen_auf(werkzeug, bibliothek, heraus, mindestens)
        if auf is None:
            gesamt = einheiten.text(float(werkzeug.gesamtlaenge), einheiten.LAENGE, 0)
            return html.escape(
                tr("va.halter_zu_kurz", werkzeug=kennung, gesamt=gesamt), quote=False
            )
        ziel, laenge = auf
        text = tr(
            "va.halter_ausspannen",
            werkzeug=kennung,
            heraus=einheiten.text(ziel, einheiten.LAENGE, 0),
        )
        verweis = rw.ausspannen_ziel(werkzeug, laenge, ziel)
        return f'<a href="{verweis}">{html.escape(text)}</a>'

    def _mit_ecken(self, text, bahn):
        """Hinter der Ergebniszeile unter dem Rand: Bleiben Ecken, für die eine kleinere Kugel
        passte (hinterschnitt_bahn.Bahn.ecken_radius), die größte solche aus der
        Werkzeugverwaltung mit „Restschlichten mit T… anhaken“ (Verweis „restschlichten:“) –
        oder, dass sie fehlt (Manuel: Empfehlungen auch, wenn es das Werkzeug nicht gibt)."""
        radius = float(getattr(bahn, "ecken_radius", 0.0) or 0.0)
        bibliothek = self.panel.bibliothek
        if radius <= 0 or bibliothek is None or self.s.kennung != "schlichten3d":
            return text
        kugeln = [
            w
            for w in bibliothek.werkzeuge
            if w.art == wz.KUGELFRAESER and 0 < float(w.durchmesser) <= 2.0 * radius + 1e-6
        ]
        d = groesse_zeigen(2.0 * radius, einheiten.LAENGE, 1) or "0"
        if not kugeln:
            from . import empfehlung as em

            dazu = html.escape(tr("ba.s3.unter.ecken_fehlt", d=d), quote=False)
            neu = getattr(bahn, "ecken_empfehlung", None)
            if isinstance(neu, em.Empfehlung):  # ein Fräser, den es noch nicht gibt
                self._ecken_empfehlung = neu
                vorschlag = tr(
                    "ba.s3.unter.ecken_neu",
                    werkzeug=neu.werkzeug_text,
                    halter=neu.halter.name,
                    heraus=einheiten.text(neu.heraus, einheiten.LAENGE, 0),
                )
                knopf = html.escape(tr("ba.s3.unter.ecken_anlegen"))
                return (
                    f"{text} {dazu} {html.escape(vorschlag, quote=False)} "
                    f'<a href="eckenwerkzeug:">{knopf}</a>'
                )
            return f"{text} {dazu}"
        rest = self.panel.restschlichten
        jetzt = rest.fraeser() if rest.aktiv() else None
        if jetzt is not None and any(w.kennung == jetzt.kennung for w in kugeln):
            return text  # Restschlichten ist schon mit einer Kugel angehakt, die hineinpasst
        kugel = max(kugeln, key=lambda w: float(w.durchmesser))
        nummer = mg.genannt(kugel, self.panel.magazin()) if self.panel.magazin() else None
        knopf = html.escape(tr("ba.s3.unter.ecken_rest", werkzeug=nummer or wz.nummer_text(kugel)))
        return f'{text} <a href="restschlichten:{kugel.kennung}">{knopf}</a>'

    def _vorbohrer_angebot(self):
        """Unter dem Räumen: Taucht es ins Volle ein und fehlt fürs Vorbohren ein Bohrer im
        Magazin (_vorbohrer), das Angebot „Bohrer Ø … anlegen und vorbohren“ (Manuel: Empfehlungen
        auch, wenn es das Werkzeug nicht gibt – der nächste Schritt als Knopf); sonst leer."""
        if self.s.kennung == "nut":
            self._vorbohrer_angebot_nut()
            return
        if self.s.kennung == "bohrung":
            self._bohrer_angebot()
            return
        if self.s.kennung != "raeumen":
            return
        bahn = self.vorschau
        fraeser = self.fraeser()
        if (
            bahn is None
            or not getattr(bahn, "eintauchen", None)
            or getattr(bahn, "vorbohren", None) is not None
            or fraeser is None
            or self.panel.job is None
            or self.panel._vorbohrer(fraeser) is not None
        ):
            self.angebot.leeren()
            return
        d = math.ceil((float(fraeser.durchmesser) + VORBOHRER_LUFT) * 2.0 - 1e-9) / 2.0
        *_rohteil, oben = pf.rohteil_von_oben(self.panel.job)
        tiefe = max(oben - z for _x, _y, z in bahn.eintauchen)
        text = tr(
            "ba.raeumen.vorbohren.fehlt",
            von=groesse_zeigen(fraeser.durchmesser, einheiten.LAENGE, 1) or "0",
            bis=groesse_zeigen(fraeser.durchmesser * VORBOHRER_HOECHSTENS, einheiten.LAENGE, 1)
            or "0",
        )
        knopf_ = tr("ba.raeumen.vorbohren.anlegen", d=groesse_zeigen(d, einheiten.LAENGE, 1) or "0")
        self.angebot.zeigen(text, [(knopf_, lambda: self.panel._vorbohrer_anlegen(d, tiefe))])

    def _bohrer_angebot(self):
        """Unter „Bohrung fräsen“: Bohrungen, in die sein Fräser nicht kommt, und kein Bohrer
        dafür (panel._fehlende_bohrer) – das Angebot „Bohrer Ø … anlegen“, danach bohrt sie
        „Bohren“ (Manuel: der nächste Schritt als Knopf, auch wenn das Werkzeug fehlt). Gilt, ob
        die Vorschau gelang (die kleineren „für den Bohrer“) oder rot blieb (in keine)."""
        fehlend = self.panel._fehlende_bohrer(self, getattr(self, "_angebot_flaechen", ()))
        if not fehlend:
            self.angebot.leeren()
            return
        namen = [n for _d, _w, _t, liste in fehlend for n in liste]
        durchmesser = [
            f"Ø {groesse_zeigen(d, einheiten.LAENGE, 2) or '0'}"
            + ("" if abs(winkel - bh.SPITZENWINKEL) <= bh.GLEICH_WINKEL else f" {winkel:g}°")
            for d, winkel, _t, _n in fehlend
        ]
        text = tr(
            "ba.bohrung.bohrer_fehlt",
            flaechen=", ".join(namen[:4]) + (" …" if len(namen) > 4 else ""),
        )
        knopf_ = tr("ba.bohrer_anlegen.knopf", d=", ".join(durchmesser))
        self.angebot.zeigen(text, [(knopf_, lambda: self.panel._bohrer_anlegen(fehlend))])

    def _vorbohrer_angebot_nut(self):
        """Unter der Nut: Passt für eine Nut kein Bohrer aus dem Magazin (nut.vorschau:
        `vorbohren_fehlt`), das Angebot, einen anzulegen – der größte in halben Millimetern, der
        hineinpasst."""
        bahn = self.vorschau
        haken = getattr(self, "haken_felder", {}).get("vorbohren")
        offen = [e for e in (getattr(bahn, "eintauchen", None) or []) if not e[5]]
        fehlt = getattr(bahn, "vorbohren_fehlt", None) if bahn is not None else None
        if fehlt is None and offen and haken is not None and not haken.isEnabled():
            fehlt = (offen[0][3], offen[0][4])  # kein Bohrer im Magazin: die erste Nut
        wollen = haken is not None and (haken.isChecked() or not haken.isEnabled())
        if not fehlt or not offen or not wollen or self.panel.job is None:
            self.angebot.leeren()
            return
        von, bis = fehlt
        d = math.floor(bis * 2.0 + 1e-9) / 2.0
        if d < von - 1e-6:
            d = math.floor(bis * 10.0 + 1e-9) / 10.0
        *_rohteil, oben = pf.rohteil_von_oben(self.panel.job)
        tiefe = max(oben - e[2] for e in (bahn.eintauchen or [(0, 0, oben)]))
        text = tr(
            "ba.nut.vorbohren.fehlt",
            von=groesse_zeigen(von, einheiten.LAENGE, 1) or "0",
            bis=groesse_zeigen(bis, einheiten.LAENGE, 1) or "0",
        )
        knopf_ = tr("ba.raeumen.vorbohren.anlegen", d=groesse_zeigen(d, einheiten.LAENGE, 1) or "0")
        self.angebot.zeigen(text, [(knopf_, lambda: self.panel._vorbohrer_anlegen(d, tiefe))])

    def _mit_ausspannen(self, text, bahn):
        """Die Ergebniszeile – stößt die Bahn stellenweise an (hinterschnitt_bahn.Bahn.ausspannen),
        dahinter „T… auf … mm ausspannen“ (Manuel: der nächste Schritt als Knopf)."""
        if not getattr(bahn, "anstoesse", 0):
            return text
        ausspannen = getattr(bahn, "ausspannen", None)
        if ausspannen and ausspannen[1] is None:
            ausspannen = None
        empfehlung = getattr(bahn, "empfehlung", None)
        return self._ausspannen_oder_empfehlung(text, ausspannen, empfehlung) or text

    def _hinweis_verweis(self, ziel):
        """„ausspannen:5:83.000:43“ im roten Satz: T5 in der Werkzeugverwaltung auf 83 mm ab
        Spindelnase, 43 mm heraus (rw.ausspannen_setzen), gespeichert; der Assistent liest es neu
        und rechnet die Vorschau."""
        bibliothek = self.panel.bibliothek
        if (
            not ziel.startswith(("ausspannen:", "empfehlung:", "restschlichten:", "eckenwerkzeug:"))
            or bibliothek is None
        ):
            return
        if ziel.startswith("empfehlung:"):
            self._empfehlung_einrichten()
            return
        if ziel.startswith("restschlichten:"):
            self.panel.restschlichten_mit(ziel.split(":", 1)[1])
            return
        if ziel.startswith("eckenwerkzeug:"):
            self._ecken_werkzeug_anlegen()
            return
        nummer, laenge, heraus, platz = rw.ausspannen_lesen(ziel)
        self.panel.magazin()  # das Magazin der Maschine (dort gilt der Wert des Platzes)
        werkzeug = rw.ausspannen_werkzeug(bibliothek, nummer, platz)
        if werkzeug is None:
            return
        rw.ausspannen_setzen(werkzeug, laenge, heraus, bibliothek)
        bibliothek.speichern()
        self.panel._werkzeuge_gespeichert()

    def _im_hintergrund(self, job, werkzeug, werte, flaechen, vorschub, senkrecht):
        """Gibt die Vorschau einem Nebenrechner, wenn die Strategie das kann (`hintergrund`):
        der Auftrag, oder None – dann rechnet sie hier."""
        hintergrund = getattr(self.s, "hintergrund", None)
        if hintergrund is None or not _hintergrund_passt(type(self.s)):
            return None
        from . import freiwege as fw
        from . import nebenrechner as nr

        pool = nr.pool()
        if not pool.verfuegbar():
            return None
        try:
            ziel = hintergrund(werkzeug, werte, flaechen)
            if ziel is None:  # diesmal nicht (Schlichten 3D mit dem Wegkippen)
                return None
            funktion, argumente = ziel
            zeit = None
            if vorschub > 0 and self.s.kennung in IM_FREIEN_SCHNELL:
                # Wie _zeit_im_freien: im Materialstand, den der Assistent dem Block gibt.
                stand = werte.get("materialstand")
                zeit = (vorschub, senkrecht, fw.freivorschub_fuer(job), stand)
            kopie = pool.kopie(job.Document, wiederverwenden=True)
            return pool.auftrag("bearbeitung_vorschau", funktion, kopie, job.Name, *argumente, zeit)
        except Exception as fehler:  # noqa: BLE001 – dann rechnet sie hier, wie bisher
            FreeCAD.Console.PrintLog(f"CAM-Addon: Vorschau im Nebenrechner: {fehler}\n")
            return None

    def _merken(self, merk, schluessel):
        """Merkt, was die Vorschau ergab – höchstens VORSCHAU_MERK, die ältesten fallen heraus."""
        if schluessel is None or merk is None:
            return
        merk[schluessel] = (
            self.vorschau,
            self.zeit,
            self.schon_weg,
            self.ergebnis_basis,
            self.material.text(),
            self.hinweis.text(),
        )
        while len(merk) > VORSCHAU_MERK:
            merk.popitem(last=False)

    def _vorschau_knopf_zeigen(self):
        """„Vorschau“ neben dem Haken, wenn die Vorschau des Blocks Punkte hat."""
        knopf_ = getattr(self, "knopf_vorschau", None)
        if knopf_ is not None:
            knopf_.setVisible(bool(getattr(self.vorschau, "punkte", None)))

    def _gemerkt_zeigen(self, gemerkt):
        vorschau, zeit, schon_weg, basis, material, hinweis = gemerkt
        self.vorschau, self.zeit, self.schon_weg = vorschau, zeit, schon_weg
        if vorschau is not None and self.s.kennung == "schlichten3d":
            # Der Verweis zum Restschlichten hängt von dessen Haken ab, nicht von der Bahn.
            zeit_ = _zeit_text(zeit) if zeit is not None else "?"
            basis = self._mit_ecken(
                self._mit_ausspannen(self.s.ergebnis_text(vorschau, zeit_), vorschau), vorschau
            )
        self.ergebnis_basis = basis
        self.ergebnis.setText(basis)
        self.material.setText(material)
        self.hinweis.setText(hinweis)
        self._vorschau_knopf_zeigen()
        self._vorbohrer_angebot()
        if self.s.kennung == "nut" and vorschau is not None:
            self.stellen_zeigen(getattr(vorschau, "stellen", None))

    def leeren(self):
        self.vorschau = None
        self.zeit = None
        self.schon_weg = False
        self.ergebnis_basis = ""
        self.ergebnis.setText("")
        self.material.setText("")
        self.hinweis.setText("")
        self._vorschau_knopf_zeigen()
        if self.s.kennung in ("raeumen", "nut", "bohrung"):
            self.angebot.leeren()  # das Angebot des Bohrers (_vorbohrer_angebot)


# Die Blöcke, deren Operationen im Freien mit dem Freivorschub fahren (freiwege) – ihre Zeit im
# Assistenten rechnet ihn mit, und der Wettbewerb vergleicht so die Zeiten der Operationen.
IM_FREIEN_SCHNELL = {
    "planfraesen",
    "raeumen",
    "restraeumen",
    "nut",
    "kontur",
    "fase",
    "entgraten",
    "schruppen3d",
    "restschruppen",
    "schlichten3d",
    "restschlichten",
    "bleistift",
}


def _vorwaermen():
    """Die Nebenrechner starten und laden, was die Vorschau dort braucht, während man noch
    Flächen anklickt – die erste Vorschau wartet dann nicht darauf (wie gui_vierachs)."""
    from . import nebenrechner as nr

    try:
        nr.pool().vorwaermen(["bearbeitung_vorschau", "raeumen_bahn", "hoehenfeld", "freiwege"])
    except Exception as fehler:  # noqa: BLE001 – ohne Vorwärmen rechnet die Vorschau wie bisher
        FreeCAD.Console.PrintLog(f"CAM-Addon: Nebenrechner vorwärmen: {fehler}\n")


def _hintergrund_passt(klasse):
    """Kommen `hintergrund` und `vorschau` der Strategie aus derselben Klasse? Eine Strategie, die
    vorschau() überschreibt, hintergrund() aber erbt, rechnete im Nebenrechner die ihrer
    Elternklasse – sie rechnet hier."""

    def woher(name):
        return next((k for k in klasse.__mro__ if name in vars(k)), None)

    return woher("hintergrund") is not None and woher("hintergrund") is woher("vorschau")


def _abwarten(schritt):
    """Ist der Schritt einer Vorschau ein Auftrag an einen Nebenrechner: auf ihn warten (das
    Fenster zeichnet sich dabei neu, nimmt aber keinen Klick an) – für das Rechnen am Stück."""
    from . import nebenrechner as nr

    if isinstance(schritt, nr.Auftrag) and not schritt.erledigt:
        with contextlib.suppress(nr.Fehler):  # was scheiterte, liest _aus_dem_hintergrund
            nr.pool().warten([schritt], zwischendurch=nr.ereignisse_ohne_eingaben)


def _wartende_zurueck(auftraege):
    """Nimmt die Aufträge zurück, die noch auf einen Nebenrechner warten – laufende rechnen zu
    Ende (ihr Arbeiter endete sonst und müsste neu starten)."""
    from . import nebenrechner as nr

    for auftrag in auftraege:
        if auftrag is None or auftrag.erledigt or getattr(auftrag, "arbeiter", None) is not None:
            continue
        with contextlib.suppress(Exception):
            nr.pool().abbrechen(auftrag)


def _aus_dem_hintergrund(auftrag):
    """Was ein Nebenrechner für die Vorschau gerechnet hat: ("ok", (Bahn, Zeit im Freien)),
    ("fehler", Satz, schon weg?, Daten der Ausnahme) für einen Grund, den die Strategie selbst nennt (ValueError,
    auch materialstand.SchonWeg; RuntimeError aus OpenCascade) – oder None: gescheitert oder
    abgebrochen, dann rechnet der Assistent hier."""
    if auftrag.fertig:
        return ("ok", auftrag.ergebnis)
    eigene = ("ValueError", "RuntimeError", "SchonWeg")  # Gründe der Strategie selbst
    if auftrag.fehler is not None and auftrag.fehlerart in eigene:
        return (
            "fehler",
            auftrag.fehlersatz,
            auftrag.fehlerart == "SchonWeg",
            getattr(auftrag, "fehlerdaten", None),
        )
    if auftrag.fehler is not None:
        FreeCAD.Console.PrintWarning(
            f"CAM-Addon: Vorschau im Nebenrechner gescheitert, rechne hier: {auftrag.fehler}\n"
        )
    return None


def _zeit_im_freien(job, werkzeug, werte, bahn, vorschub, eintauchen):
    """Die Zeit der Vorschau (min) mit dem Freivorschub im Freien – wie die Operation fährt
    (freiwege). Gerechnet im Materialstand, den der Assistent dem Block gibt; ohne ihn wie
    bisher."""
    from . import freiwege as fw

    return fw.zeit_im_freien(
        ff.von_werkzeug(werkzeug),
        werte.get("materialstand"),
        getattr(bahn, "punkte", None),
        vorschub,
        eintauchen,
        fw.freivorschub_fuer(job),
    )


def _merk_schluessel(kennung, job, werkzeug, einsatz, werte, flaechen):
    """Woraus die Vorschau eines Blocks gerechnet wird, als Text: Strategie, Flächen, Werkzeug,
    Einsatz, alle Werte (der Materialstand mit seiner Kennung), Teil und Rohteil im Job (Lage,
    Hüllquader, Volumen, Form). Was sich nicht eindeutig schreiben lässt (eine Adresse im Text),
    trifft nie – dann wird gerechnet. None, wenn es nicht geht."""
    try:
        stand = werte.get("materialstand")
        rein = sorted((k, repr(v)) for k, v in werte.items() if k != "materialstand")
        teile = []
        for objekt in (vr.modell(job), getattr(job, "Stock", None)):
            form = getattr(objekt, "Shape", None)
            if form is None or form.isNull():
                teile.append(None)
                continue
            bb = form.BoundBox
            huelle = (bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax)
            teile.append(
                (repr(objekt.Placement), huelle, round(_volumen(form), 6), form.hashCode())
            )
        text = repr(
            (
                kennung,
                tuple(flaechen),
                repr(werkzeug),
                repr(einsatz),
                rein,
                getattr(stand, "kennung", None) if stand is not None else None,
                teile,
            )
        )
    except Exception:  # ein Wert ohne Text – dann eben rechnen
        return None
    return None if " at 0x" in text else text


def rohteil_kandidaten(dokument, teil=None):
    """Die Körper im Dokument, die das Rohteil sein können (W-011 S4): geschlossene Körper oben
    im Baum – nicht das Teil selbst, nichts aus einem Job (Modell, Rohteil, Werkzeuge,
    Operationen), keine Features in einem Körper, keine Gruppen. Nach dem Namen sortiert."""
    ergebnis = []
    for objekt in dokument.Objects:
        if objekt is teil or not hasattr(objekt, "Shape") or hasattr(objekt, "Path"):
            continue
        if any(hasattr(objekt, e) for e in ("PathResource", "StockType", "ToolBitID", "ExtZpos")):
            continue
        if objekt.isDerivedFrom("App::DocumentObjectGroup"):
            continue
        if objekt.getParentGeoFeatureGroup() is not None:
            continue  # ein Feature in einem Körper – der Körper zählt
        ansicht = getattr(objekt, "ViewObject", None)
        if ansicht is not None and not getattr(ansicht, "ShowInTree", True):
            continue
        try:
            form = objekt.Shape
            fest = not form.isNull() and _volumen(form) > 1e-9 and form.isClosed()
        except Exception:  # eine kaputte Form: kein Rohteil
            fest = False
        if fest:
            ergebnis.append(objekt)
    return sorted(ergebnis, key=lambda o: o.Label)


class BearbeitungPanel:
    """Aufgabenfenster „Bearbeitung (Fräsen)“ – anlegen, oder mit `operation=` ändern."""

    offen = None  # das offene Fenster – für die Oberflächen-Szenarien

    def __init__(
        self, dokument, wahl=None, operation=None, neu=False, angeklickt=None, flaechen=None,
        folge=None,
    ):  # fmt: skip
        BearbeitungPanel.offen = self
        self.doc = dokument
        # Aus „Alles aus dieser Aufspannung“ (_ebenen_der_aufspannung): die Flächen dieser Ebene,
        # gewählt zu Beginn, und der Satz „Ebene 1 von 2 …“ – nach „Anlegen“ kommt die nächste.
        self._vorwahl = list(flaechen) if flaechen else None
        self._folge = folge
        # Hat das Teil schon einen Job, kommen die neuen Operationen dort hinein (W-012 M2) –
        # außer `neu`: „Neuer Job …“ für eine zweite Aufspannung.
        self._neu = bool(neu)
        self._job_dazu = False  # der Job war schon da: Aufspannung fest, nichts zurückzunehmen
        self._wahl_anfang = wahl  # (Teil, „FaceN“) – für den Wechsel zum 4-Achs-Assistenten
        self.job = None
        self.teil = None
        self.bibliothek = None
        self.gewaehlte = []  # die Flächen („Face6“ …) – leer: die Oberseite
        self.kanten = []  # angeklickte Kanten („Edge12“ …) – nur für „Entgraten 3D“
        self.operation = operation  # die erste angelegte Operation – oder die, die man ändert
        self.operationen = []  # alle angelegten
        self.zu_aendern = operation
        self.block_zu_aendern = None
        self._fuellt = False
        self._ruhig = False  # das Fenster setzt selbst einen Fräser: keine neue Vorschau
        self.geschlossen = False
        self._knoepfe = None
        self._beobachter = None
        self._sichtbar_vorher = None  # (Teil, war sichtbar) – das Original
        self._aufspannung_vorher = []  # [(Objekt, war sichtbar)] – gui_schwenken.zeige_job
        self._rohteil_sichtbar_vorher = None  # (Körper, war sichtbar) – das Rohteil-Original
        # Je Block gemerkte Vorschauen über die Läufe hinweg: woraus gerechnet → was herauskam.
        self.vorschau_merk = OrderedDict()
        self._farben_vorher = None  # (Klon, DiffuseColor, ShapeAppearance) vor dem Färben
        self._job_offen = False  # die Transaktion des neuen Jobs ist offen
        self._job_fest = False  # der Job liegt schon als Schritt Rückgängig ab
        self._undo_vorher = len(dokument.UndoNames)
        self._vorschau_uhr = QtCore.QTimer()
        self._vorschau_uhr.setSingleShot(True)
        self._vorschau_uhr.setInterval(VORSCHAU_MS)
        self._vorschau_uhr.timeout.connect(
            uhren.aus_der_schleife(self._vorschau_uhr, self._vorschau_im_takt)
        )
        self._vorschau_lauf = None  # der Lauf, der gerade Block für Block rechnet (_im_takt)
        self._vorschau_auftrag = None  # sein Block in einem Nebenrechner
        _vorwaermen()
        self._rohteil_uhr = QtCore.QTimer()
        self._rohteil_uhr.setSingleShot(True)
        self._rohteil_uhr.setInterval(NACHZIEHEN_MS)
        self._rohteil_uhr.timeout.connect(
            uhren.aus_der_schleife(self._rohteil_uhr, self._rohteil_anwenden)
        )
        self._nullpunkt_uhr = QtCore.QTimer()
        self._nullpunkt_uhr.setSingleShot(True)
        self._nullpunkt_uhr.setInterval(NACHZIEHEN_MS)
        self._nullpunkt_uhr.timeout.connect(
            uhren.aus_der_schleife(self._nullpunkt_uhr, self._nullpunkt_anwenden)
        )
        self._nullpunkte = nullpunkte()
        self._unten = None  # die Fläche des Teils, die unten liegt („Face6“) – None: wie modelliert
        self._zugang = None  # „Alles aus dieser Aufspannung“: zugang.Zugang, bis sich etwas ändert
        self._viertel = 0  # X um so viele Viertel um Z gedreht
        self.bloecke = []
        self.form = self._baue()
        from . import gui_rechnet

        self._rechnet = gui_rechnet.Anzeige(
            self.rechnet,
            lambda: not self.geschlossen and self.vorschau_laeuft(),
            bei_wechsel=self._knoepfe_beschriften,
        )
        self._rechnet.rad(self.rad_unten)
        # Räumt FreeCAD das Fenster ohne „Abbrechen“ weg (das Dokument zu), hier aufräumen – sonst
        # riefen Beobachter und Uhren ins Leere (Manuel, 2026-10-12: „deleted object“).
        self.form.destroyed.connect(lambda *_a: self._verschwunden())
        self.plan = next(b for b in self.bloecke if b.s.kennung == "planfraesen")
        self.raeumen = next(b for b in self.bloecke if b.s.kennung == "raeumen")
        self.restraeumen = next(b for b in self.bloecke if b.s.kennung == "restraeumen")
        self.schlichten_danach = next(b for b in self.bloecke if b.s.kennung == "schlichtendanach")
        self.nut = next(b for b in self.bloecke if b.s.kennung == "nut")
        self._raeumen_boeden = None  # nur diese Taschenböden räumen (_folge); None: alle
        self._raeumen_bei_nut = False  # alle Gründe des Räumens fräst die Nut (_block_schritte)
        self.bohren = next(b for b in self.bloecke if b.s.kennung == "bohren")
        self.bohrung = next(b for b in self.bloecke if b.s.kennung == "bohrung")
        self.kontur = next(b for b in self.bloecke if b.s.kennung == "kontur")
        self.gewinde = next(b for b in self.bloecke if b.s.kennung == "gewinde")
        self.gewindefraesen = next(b for b in self.bloecke if b.s.kennung == "gewindefraesen")
        self.entgraten = next(b for b in self.bloecke if b.s.kennung == "entgraten")
        self.fase = next(b for b in self.bloecke if b.s.kennung == "fase")
        self.entgraten3d = next(b for b in self.bloecke if b.s.kennung == "entgraten3d")
        self.zentrieren = next(b for b in self.bloecke if b.s.kennung == "zentrieren")
        self.senken = next(b for b in self.bloecke if b.s.kennung == "senken")
        self.reiben = next(b for b in self.bloecke if b.s.kennung == "reiben")
        self.schlichten3d = next(b for b in self.bloecke if b.s.kennung == "schlichten3d")
        self.flanke = next(b for b in self.bloecke if b.s.kennung == "flanke")
        self.schruppen3d = next(b for b in self.bloecke if b.s.kennung == "schruppen3d")
        self.bleistift = next(b for b in self.bloecke if b.s.kennung == "bleistift")
        self.rest = next(b for b in self.bloecke if b.s.kennung == "rest")
        self.restschlichten = next(b for b in self.bloecke if b.s.kennung == "restschlichten")
        self.restschruppen = next(b for b in self.bloecke if b.s.kennung == "restschruppen")
        self._beobachter = _Beobachter(self)
        FreeCADGui.Selection.addObserver(self._beobachter)
        FreeCADGui.Selection.addSelectionGate(_NurFlaechen(self))
        if operation is not None:
            self._zum_aendern()
            self.seite_zeigen(2)
            return
        if wahl is not None:
            self._beginnen(wahl, angeklickt)
        self.seite_zeigen(0)
        self._auffrischen()

    # --- Aufbau -------------------------------------------------------------------------

    def _baue(self):
        form = QtGui.QWidget()
        form.setWindowTitle(tr("ba.titel"))
        form.setWindowIcon(QtGui.QIcon(symbol("bearbeitung.svg")))
        self._enter_filter = _EnterBleibtImDialog(form)
        form.installEventFilter(self._enter_filter)
        aufbau = QtGui.QVBoxLayout(form)
        kopf = kopfzeile(tr("ba.kopf"), "bearbeitung")
        aufbau.addWidget(kopf)
        self.rechnet = QtGui.QLabel()  # gui_rechnet: dreht sich, solange es rechnet
        aufbau.addWidget(self.rechnet)
        # Oben, in welchem der drei Schritte man ist; darunter, was dort zu tun ist.
        self.schritt_text = QtGui.QLabel()
        schrift = self.schritt_text.font()
        schrift.setBold(True)
        schrift.setPointSizeF(schrift.pointSizeF() * 1.15)
        self.schritt_text.setFont(schrift)
        aufbau.addWidget(self.schritt_text)
        self.anleitung = QtGui.QLabel(tr("ba.anleitung"))
        self.anleitung.setWordWrap(True)
        aufbau.addWidget(self.anleitung)

        ziel = [aufbau]  # wohin titel() und grautext() setzen

        def titel(text, tooltip=""):
            etikett = QtGui.QLabel(text)
            etikett.setToolTip(tooltip)
            schrift = etikett.font()
            schrift.setBold(True)
            etikett.setFont(schrift)
            ziel[0].addWidget(etikett)
            return etikett

        def grautext(text=""):
            etikett = _grau(text)
            ziel[0].addWidget(etikett)
            return etikett

        # Drei Schritte wie im 4-Achs-Assistenten (Manuel, 2026-10-02: „man fragt es in Schritten
        # ab“, „Rohteil und Nullpunkt … wo man auf Weiter klicken kann, wenn's fertig ist“):
        # Aufspannung – was soll weg – Einstellungen. „Anlegen“ geht aus jedem Schritt.
        self.seiten = []
        for _nummer in range(3):
            seite = QtGui.QWidget()
            seite_aufbau = QtGui.QVBoxLayout(seite)
            seite_aufbau.setContentsMargins(0, 0, 0, 0)
            aufbau.addWidget(seite)
            self.seiten.append(seite)

        # --- Schritt 1: Aufspannung – Maschine, Teil, Rohteil, Nullpunkt ---
        ziel[0] = self.seiten[0].layout()
        # Hat das Teil schon einen Job, kommen die neuen Operationen dort hinein (W-012 M2).
        self.dazu_zeile = QtGui.QWidget()
        dazu = QtGui.QHBoxLayout(self.dazu_zeile)
        dazu.setContentsMargins(0, 0, 0, 0)
        self.dazu_text = QtGui.QLabel()
        self.dazu_text.setWordWrap(True)
        dazu.addWidget(self.dazu_text, 1)
        self.knopf_neuer_job = knopf(
            tr("ba.neuer_job"), tr("ba.neuer_job.tooltip"), lambda: self.neuer_job()
        )
        dazu.addWidget(self.knopf_neuer_job, 0, QtCore.Qt.AlignTop)
        self.dazu_zeile.setVisible(False)
        ziel[0].addWidget(self.dazu_zeile)
        oben = _Reihen()
        # Die Maschine zuerst (W-011 S2; Manuel, 2026-10-02: „Immer wenn ich ein Teil lade,
        # sollte ich die Maschine auswählen“): die Liste aus „Maschinen …“, gemerkt am Job.
        zeile = QtGui.QWidget()
        knoepfe = QtGui.QHBoxLayout(zeile)
        knoepfe.setContentsMargins(0, 0, 0, 0)
        self.wahl_maschine = QtGui.QComboBox()
        knoepfe.addWidget(self.wahl_maschine, 1)
        self.knopf_maschinen = knopf(
            tr("befehl.maschinen.titel"), tr("ba.maschine.liste.tooltip"), self.maschinen_oeffnen
        )
        knoepfe.addWidget(self.knopf_maschinen)
        oben.reihe(tr("ba.maschine"), tr("ba.maschine.tooltip"), zeile)
        self.maschine_hinweis = _grau()
        oben.ganz(self.maschine_hinweis)
        # Welches Magazin der Maschine gilt – verschiedene Standard-Beladungen (Manuel,
        # 2026-10-18); die Fräserlisten sind seine Plätze (magazin.je_platz).
        self.wahl_magazin = QtGui.QComboBox()
        self.wahl_magazin.currentIndexChanged.connect(
            lambda _i: (
                None if getattr(self, "_magazine_fuellt", False) else self._magazin_gewaehlt()
            )
        )
        oben.reihe(tr("mg.wahl"), tr("mg.wahl.tooltip"), self.wahl_magazin)
        self.magazin_zeile = (oben._beschriftungen[-1], self.wahl_magazin)
        # Liegt die Datei nicht mehr dort: gleich hier weiter – wiederfinden oder aus der Liste
        # nehmen, statt über „Maschinen …“ (Manuel, 2026-10-10: im Flow bleiben).
        self.maschine_knoepfe = QtGui.QWidget()
        reihe = QtGui.QHBoxLayout(self.maschine_knoepfe)
        reihe.setContentsMargins(0, 0, 0, 0)
        self.knopf_maschine_suchen = knopf(
            tr("ms.suchen"), tr("ms.suchen.tooltip"), self.maschine_suchen
        )
        self.knopf_maschine_entfernen = knopf(
            tr("ba.maschine.entfernen"),
            tr("ba.maschine.entfernen.tooltip"),
            self.maschine_entfernen,
        )
        reihe.addWidget(self.knopf_maschine_suchen)
        reihe.addWidget(self.knopf_maschine_entfernen)
        reihe.addStretch()
        oben.ganz(self.maschine_knoepfe)
        self.maschine_knoepfe.hide()
        # Drehmaschine oder 4-Achs-Fräse: Das Rohteil ist eine Stange (W-011 S3) – weiter im
        # 4-Achs-Assistenten, mit Teil, Fläche und Maschine.
        self.knopf_vierachs = knopf(
            tr("ba.maschine.vierachs"), tr("ba.maschine.vierachs.tooltip"), self.zum_vierachs
        )
        self.knopf_vierachs.setVisible(False)
        oben.ganz(self.knopf_vierachs)
        self.teil_text = QtGui.QLabel(tr("ba.teil.keins"))
        self.teil_text.setWordWrap(True)
        oben.reihe(tr("ba.teil"), "", self.teil_text)
        # Wie das Teil auf dem Tisch liegt (Manuel, 2026-10-02: „man klickt auf eine Fläche,
        # welche dann sozusagen unten ist … fehlt nur noch die X- und Y-Achse – aber das muss
        # sein“): in Schritt 1 macht ein Klick auf eine ebene Fläche sie zur Unterseite, X dreht
        # in Vierteln um Z; Rohteil und Nullpunkt folgen.
        zeile = QtGui.QWidget()
        knoepfe = QtGui.QHBoxLayout(zeile)
        knoepfe.setContentsMargins(0, 0, 0, 0)
        self.unten_text = QtGui.QLabel(tr("ba.unten.modell"))
        knoepfe.addWidget(self.unten_text, 1)
        # Erst dieser Knopf macht den nächsten Klick zur Unterseite – ein Klick auf die Fläche,
        # die bearbeitet werden soll, dreht so nie aus Versehen das Teil.
        self.knopf_unten_waehlen = QtGui.QPushButton(tr("ba.unten.waehlen"))
        self.knopf_unten_waehlen.setToolTip(tr("ba.unten.waehlen.tooltip"))
        self.knopf_unten_waehlen.setCheckable(True)
        knoepfe.addWidget(self.knopf_unten_waehlen)
        self.knopf_unten_modell = knopf(
            tr("ba.unten.zurueck"), tr("ba.unten.zurueck.tooltip"), lambda: self.unten_waehlen(None)
        )
        knoepfe.addWidget(self.knopf_unten_modell)
        oben.reihe(tr("ba.unten"), tr("ba.unten.tooltip"), zeile)
        zeile = QtGui.QWidget()
        knoepfe = QtGui.QHBoxLayout(zeile)
        knoepfe.setContentsMargins(0, 0, 0, 0)
        self.x_text = QtGui.QLabel(tr("ba.x.modell"))
        knoepfe.addWidget(self.x_text, 1)
        self.knopf_x_links = knopf(tr("ba.x.links"), tr("ba.x.tooltip"), lambda: self.x_drehen(1))
        knoepfe.addWidget(self.knopf_x_links)
        self.knopf_x_rechts = knopf(
            tr("ba.x.rechts"), tr("ba.x.tooltip"), lambda: self.x_drehen(-1)
        )
        knoepfe.addWidget(self.knopf_x_rechts)
        oben.reihe(tr("ba.x"), tr("ba.x.tooltip"), zeile)
        ziel[0].addWidget(oben.widget)
        self._maschinen_fuellen()
        self.wahl_maschine.currentIndexChanged.connect(lambda _i: self._maschine_gewaehlt())
        self._lage_zeigen()
        titel(tr("ba.rohteil"), tr("ba.rohteil.text"))
        # Ein Quader mit Aufmaß – oder ein Körper aus dem Dokument (W-011 S4; Manuel,
        # 2026-10-02: „Rohteil kann auch ein konstruiertes Teil sein“).
        zeile = QtGui.QWidget()
        knoepfe = QtGui.QHBoxLayout(zeile)
        knoepfe.setContentsMargins(0, 0, 0, 0)
        self.knopf_rohteil_quader = QtGui.QRadioButton(tr("ba.rohteil.quader"))
        self.knopf_rohteil_quader.setToolTip(tr("ba.rohteil.text"))
        self.knopf_rohteil_teil = QtGui.QRadioButton(tr("ba.rohteil.teil"))
        self.knopf_rohteil_teil.setToolTip(tr("ba.rohteil.teil.tooltip"))
        # Ein runder Rohling, stehend wie im Dreibackenfutter (W-021).
        self.knopf_rohteil_zylinder = QtGui.QRadioButton(tr("ba.rohteil.zylinder"))
        self.knopf_rohteil_zylinder.setToolTip(tr("ba.rohteil.zylinder.text"))
        # Ein Quader mit eingegebenen Maßen (W-028).
        self.knopf_rohteil_masse = QtGui.QRadioButton(tr("ba.rohteil.masse"))
        self.knopf_rohteil_masse.setToolTip(tr("ba.rohteil.masse.text"))
        self.knopf_rohteil_quader.setChecked(True)
        knoepfe.addWidget(self.knopf_rohteil_quader)
        knoepfe.addWidget(self.knopf_rohteil_masse)
        knoepfe.addWidget(self.knopf_rohteil_zylinder)
        knoepfe.addWidget(self.knopf_rohteil_teil)
        knoepfe.addStretch()
        ziel[0].addWidget(zeile)
        self.rohteil_erklaerung = grautext(tr("ba.rohteil.text"))
        koerper = _Reihen()
        self.wahl_rohteil = QtGui.QComboBox()
        koerper.reihe(tr("ba.rohteil.koerper"), tr("ba.rohteil.teil.tooltip"), self.wahl_rohteil)
        self.rohteil_koerper = koerper.widget
        self.rohteil_koerper.setVisible(False)
        ziel[0].addWidget(self.rohteil_koerper)
        self.knopf_rohteil_teil.toggled.connect(lambda _an: self._rohteil_art_geaendert())
        self.knopf_rohteil_zylinder.toggled.connect(lambda _an: self._rohteil_art_geaendert())
        self.knopf_rohteil_masse.toggled.connect(lambda _an: self._rohteil_art_geaendert())
        self.wahl_rohteil.currentIndexChanged.connect(lambda _i: self._rohteil_geaendert())
        rohteil = _Reihen()
        self.felder_rohteil = {}
        for feld, text, tooltip in (
            ("oben", tr("ba.rohteil.oben"), tr("ba.rohteil.oben.tooltip")),
            ("seite", tr("ba.rohteil.seite"), tr("ba.rohteil.seite.tooltip")),
            ("unten", tr("ba.rohteil.unten"), tr("ba.rohteil.unten.tooltip")),
        ):
            eingabe = _zahlenfeld(
                self.felder_rohteil, feld, text, tooltip, rohteil, self._rohteil_geaendert
            )
            eingabe.setPlaceholderText(groesse_zeigen(AUFMASS_ROHTEIL, einheiten.LAENGE) or "0")
        self.rohteilfelder = rohteil.widget
        ziel[0].addWidget(self.rohteilfelder)
        masse = _Reihen()
        self.felder_masse = {}
        for feld, text, tooltip in (
            ("x", tr("ba.rohteil.masse.x"), tr("ba.rohteil.masse.x.tooltip")),
            ("y", tr("ba.rohteil.masse.y"), tr("ba.rohteil.masse.y.tooltip")),
            ("z", tr("ba.rohteil.masse.z"), tr("ba.rohteil.masse.z.tooltip")),
        ):
            _zahlenfeld(self.felder_masse, feld, text, tooltip, masse, self._rohteil_geaendert)
        self.wahl_masse_lage = QtGui.QComboBox()
        self.wahl_masse_lage.addItem(tr("ba.rohteil.masse.oben"), "oben")
        self.wahl_masse_lage.addItem(tr("ba.rohteil.masse.unten"), "unten")
        self.wahl_masse_lage.setToolTip(tr("ba.rohteil.masse.lage.tooltip"))
        self.wahl_masse_lage.currentIndexChanged.connect(lambda _i: self._rohteil_geaendert())
        masse.reihe(
            tr("ba.rohteil.masse.lage"), tr("ba.rohteil.masse.lage.tooltip"), self.wahl_masse_lage
        )
        _zahlenfeld(
            self.felder_masse,
            "aufmass",
            tr("ba.rohteil.masse.aufmass"),
            tr("ba.rohteil.masse.aufmass.tooltip"),
            masse,
            self._rohteil_geaendert,
        ).setPlaceholderText(groesse_zeigen(AUFMASS_ROHTEIL, einheiten.LAENGE) or "0")
        self.rohteilmasse = masse.widget
        self.rohteilmasse.setVisible(False)
        ziel[0].addWidget(self.rohteilmasse)
        self.rohteil_warnung = QtGui.QLabel()
        self.rohteil_warnung.setWordWrap(True)
        self.rohteil_warnung.setStyleSheet(f"color: {ROT};")
        self.rohteil_warnung.setVisible(False)
        ziel[0].addWidget(self.rohteil_warnung)
        # Von unten gespannt (S3h, Manuel 2026-10-01): so viel steckt im Schraubstock – auch beim
        # Ändern einstellbar, es verschiebt nichts.
        reihen_spannung = _Reihen()
        self.felder_spannung = {}
        _zahlenfeld(
            self.felder_spannung,
            "gespannt",
            tr("ba.gespannt"),
            tr("ba.gespannt.tooltip"),
            reihen_spannung,
            self._spannung_geaendert,
        ).setPlaceholderText("0")
        self.spannungfelder = reihen_spannung.widget
        ziel[0].addWidget(self.spannungfelder)
        self.nullpunkt_titel = titel(tr("ba.nullpunkt"), tr("ba.nullpunkt.text"))
        self.nullpunkt_text = grautext(tr("ba.nullpunkt.text"))
        nullpunkt = _Reihen()
        self.wahl_nullpunkt = QtGui.QComboBox()
        self.wahl_nullpunkt.addItem(tr("ba.nullpunkt.modell"), 0)
        for nummer, (text, _lage) in enumerate(self._nullpunkte, start=1):
            self.wahl_nullpunkt.addItem(text, nummer)
        gemerkt = _gemerkter_nullpunkt()
        if gemerkt is not None:
            nummer = next(
                (n for n, (_t, lage) in enumerate(self._nullpunkte, start=1) if lage == gemerkt),
                0,
            )
            self.wahl_nullpunkt.setCurrentIndex(self.wahl_nullpunkt.findData(nummer))
        self.wahl_nullpunkt.currentIndexChanged.connect(lambda _i: self._nullpunkt_geaendert())
        nullpunkt.reihe(
            tr("ba.nullpunkt.wahl"), tr("ba.nullpunkt.wahl.tooltip"), self.wahl_nullpunkt
        )
        self.felder_nullpunkt = {}
        for feld, text in (
            ("x", tr("ba.nullpunkt.x")),
            ("y", tr("ba.nullpunkt.y")),
            ("z", tr("ba.nullpunkt.z")),
        ):
            eingabe = _zahlenfeld(
                self.felder_nullpunkt,
                feld,
                text,
                tr("ba.nullpunkt.versatz.tooltip"),
                nullpunkt,
                self._nullpunkt_geaendert,
            )
            eingabe.setPlaceholderText("0")
        self.nullpunktfelder = nullpunkt.widget
        ziel[0].addWidget(self.nullpunktfelder)

        # --- Schritt 2: was soll weg – Flächen, Werkstoff, Ziel, die Strategien im Überblick ---
        ziel[0] = self.seiten[1].layout()
        # Was in Schritt 1 gilt, als eine graue Zeile (ändern: „Zurück“).
        self.rohteil_kurz = grautext()
        titel(tr("ba.flaechen"), tr("ba.flaechen.tooltip"))
        self.flaechen_liste = QtGui.QListWidget()
        self.flaechen_liste.setToolTip(tr("ba.flaechen.liste.tooltip"))
        self.flaechen_liste.itemDoubleClicked.connect(
            lambda eintrag: self.flaeche_umschalten(eintrag.data(QtCore.Qt.UserRole))
        )
        ziel[0].addWidget(self.flaechen_liste)
        self.flaechen_text = grautext()
        zeile = QtGui.QWidget()
        knoepfe = QtGui.QHBoxLayout(zeile)
        knoepfe.setContentsMargins(0, 0, 0, 0)
        knoepfe.addWidget(
            knopf(
                tr("ba.flaechen.oberseite_knopf"),
                tr("ba.flaechen.oberseite_knopf.tooltip"),
                self.oberseite_waehlen,
            )
        )
        knoepfe.addWidget(
            knopf(
                tr("ba.flaechen.aufspannung_knopf"),
                tr("ba.flaechen.aufspannung_knopf.tooltip"),
                self.aus_der_aufspannung,
            )
        )
        knoepfe.addWidget(
            knopf(tr("ba.flaechen.leeren"), tr("ba.flaechen.leeren.tooltip"), self.flaechen_leeren)
        )
        knoepfe.addStretch()
        ziel[0].addWidget(zeile)
        # Nach einem Klick auf eine Rundung, Fase oder einen Boden: alle gleichen dazu (Manuel,
        # 2026-10-16: „gibts auf gleicher höhe auch noch andere radien gleiche radien wenn ja fragen
        # "alle anwählen"“) – ein Knopf, keine Rückfrage.
        self._gleiche = []
        self.gleiche_knopf = knopf("", tr("ba.gleiche.tooltip"), self.gleiche_dazu)
        self.gleiche_knopf.hide()
        ziel[0].addWidget(self.gleiche_knopf, 0, QtCore.Qt.AlignLeft)
        # „Alles aus dieser Aufspannung“: je weitere Richtung eine Zeile in ihrer Farbe mit „Ebene
        # schwenken …“, darunter rot, was in dieser Aufspannung nicht geht (Frage 14).
        self.richtungen_box = QtGui.QWidget()
        self._richtungen_aufbau = QtGui.QVBoxLayout(self.richtungen_box)
        self._richtungen_aufbau.setContentsMargins(0, 0, 0, 0)
        self.richtungen_box.hide()
        ziel[0].addWidget(self.richtungen_box)
        # Eine schräge ebene Fläche gewählt: geschwenkt fräsen (3+2, W-014).
        self.schwenken_zeile = QtGui.QWidget()
        schwenken = QtGui.QVBoxLayout(self.schwenken_zeile)
        schwenken.setContentsMargins(0, 0, 0, 0)
        self.schwenken_text = QtGui.QLabel()
        self.schwenken_text.setWordWrap(True)
        schwenken.addWidget(self.schwenken_text)
        # An einer 3-Achs-Fräse: schräg gespannt fräsen (Manuel, 2026-10-16) – als Haken,
        # angehakt.
        self.gekippt_haken = QtGui.QCheckBox(tr("ba.gekippt.haken"))
        self.gekippt_haken.setToolTip(tr("ba.gekippt.haken.tooltip"))
        self.gekippt_haken.setChecked(True)
        self.gekippt_haken.toggled.connect(lambda _an: self._gekippt_umgeschaltet())
        schwenken.addWidget(self.gekippt_haken)
        self.schwenken_zeile.hide()
        ziel[0].addWidget(self.schwenken_zeile)
        werkstoff = _Reihen()
        self.wahl_werkstoff = QtGui.QComboBox()
        self.wahl_werkstoff.currentIndexChanged.connect(lambda _i: self._werkstoff_gewaehlt())
        werkstoff.reihe(tr("va.werkstoff"), tr("va.werkstoff.tooltip"), self.wahl_werkstoff)
        zeile = QtGui.QWidget()
        knoepfe = QtGui.QHBoxLayout(zeile)
        knoepfe.setContentsMargins(0, 0, 0, 0)
        knoepfe.addWidget(
            knopf(
                tr("va.werkzeugverwaltung"),
                tr("va.werkzeugverwaltung.tooltip"),
                self.werkzeugverwaltung,
            )
        )
        knoepfe.addStretch()
        werkstoff.ganz(zeile)
        ziel[0].addWidget(werkstoff.widget)
        # Das Ziel: wie viel weg muss und wie lange es mindestens dauert (Manuel, 2026-10-02:
        # „dass man erstmal ein Ziel rechnet von der Zeit her“).
        self.ziel_text = grautext()
        self.ziel_text.setToolTip(tr("ba.ziel.tooltip"))
        # Kommt der Fräser von Planfräsen oder Räumen nicht in eine gewählte Fläche: rot, welcher
        # passt, und ein Knopf, ihn zu nehmen (Manuel, 2026-10-17: „ein hinweis an den anwender ..
        # und dann mit einem klick kleinen fräser übernehmen klar !!“) – vorher tauschten sie selbst.
        self.passt_text = QtGui.QLabel()
        self.passt_text.setWordWrap(True)
        self.passt_text.setStyleSheet(f"color: {ROT};")
        self.passt_text.hide()
        ziel[0].addWidget(self.passt_text)
        self.knopf_passt = knopf("", tr("ba.passt.knopf.tooltip"), self.passenden_uebernehmen)
        self.knopf_passt.hide()
        zeile_passt = QtGui.QHBoxLayout()
        zeile_passt.setContentsMargins(0, 0, 0, 0)
        zeile_passt.addWidget(self.knopf_passt)
        zeile_passt.addStretch()
        ziel[0].addLayout(zeile_passt)
        # Der schnellere Fräser aus der Ziel-Zeile mit einem Klick – freiwillig (Manuel,
        # 2026-10-02: „ja, aber man muss nicht – wenn man es mit einem Fräser fräsen will, ist
        # das so“).
        self._schneller = None  # zielzeit.Angebot hinter „Schneller aus der Werkzeugkiste“
        self.knopf_schneller = knopf(
            tr("ba.ziel.uebernehmen"), tr("ba.ziel.uebernehmen.tooltip"), self.schneller_uebernehmen
        )
        self.knopf_schneller.hide()
        zeile_schneller = QtGui.QHBoxLayout()
        zeile_schneller.setContentsMargins(0, 0, 0, 0)
        zeile_schneller.addWidget(self.knopf_schneller)
        zeile_schneller.addStretch()
        ziel[0].addLayout(zeile_schneller)
        # Fragen, wie man vorgehen will (W-039): je Weg ein Satz, seine Zeit und „Vorschau“.
        # Vorbelegt, was der Assistent bisher tat: die Flanke fertig, die Folge wie vorgeschlagen.
        self._weg = {"waende": "flanke", "reihenfolge": "vorgeschlagen"}
        self._wege = {}  # (Frage, Weg) → (Minuten, [Vorschau je Block], woraus gerechnet)
        self._bahnvorschau = None  # gui_bahnvorschau.Bahnvorschau
        self.frage_waende = _Frage(
            tr("ba.frage.waende"),
            [
                ("flanke", tr("ba.frage.waende.flanke"), tr("ba.frage.waende.flanke.satz")),
                (
                    "spirale",
                    tr("ba.frage.waende.spirale"),
                    tr(
                        "ba.frage.waende.spirale.satz",
                        aufmass=groesse_zeigen(FLANKE_VOR_SPIRALE, einheiten.LAENGE, 2) or "0",
                    ),
                ),
            ],
            "flanke",
            lambda weg: self._weg_waehlen("waende", weg),
            lambda weg: self._weg_zeigen("waende", weg),
        )
        self.frage_waende.widget.hide()
        # Wo der Fräser ins Volle eintaucht: vorbohren oder schraubend? (Manuel, 2026-10-25: „hey
        # wie willst du vorgehen sollen wir erst vorborhren … oder sollen wir alles rausschruppen
        # und dann schlichten“) – dieselben Haken wie bei Räumen und Nut („Vorbohren“).
        self.frage_eintauchen = _Frage(
            tr("ba.frage.eintauchen"),
            [
                (
                    "vorbohren",
                    tr("ba.frage.eintauchen.vorbohren"),
                    tr("ba.frage.eintauchen.vorbohren.satz"),
                ),
                ("helix", tr("ba.frage.eintauchen.helix"), tr("ba.frage.eintauchen.helix.satz")),
            ],
            "vorbohren",
            self._eintauchen_waehlen,
            lambda weg: self._weg_zeigen("eintauchen", weg),
        )
        self.frage_eintauchen.widget.hide()
        # Erst alles schruppen, dann alles schlichten? (Manuel, 2026-10-25: „oder sollen wir alles
        # rausschruppen und dann schlichten“; abends: Bohren, Senken und Gewinde dazwischen.)
        self.frage_reihenfolge = _Frage(
            tr("ba.frage.reihenfolge"),
            [
                ("vorgeschlagen", tr("ba.frage.reihenfolge.vorgeschlagen"), ""),
                ("schruppen", tr("ba.frage.reihenfolge.schruppen"), ""),
            ],
            "vorgeschlagen",
            lambda weg: self._weg_waehlen("reihenfolge", weg),
            None,
        )
        self.frage_reihenfolge.widget.hide()
        ziel[0].addWidget(self.frage_reihenfolge.widget)
        ziel[0].addWidget(self.frage_eintauchen.widget)
        ziel[0].addWidget(self.frage_waende.widget)
        # Je Strategie ein Haken mit ihrem Ergebnis – was zur Wahl passt oben, darunter
        # eingeklappt, was (noch) nicht passt (_bloecke_ordnen).
        strategien = QtGui.QWidget()
        self._block_aufbau = QtGui.QVBoxLayout(strategien)
        self._block_aufbau.setContentsMargins(0, 0, 0, 0)
        self._block_anfang = 0
        ziel[0].addWidget(strategien)
        for strategie in STRATEGIEN:
            block = _Block(self, strategie())
            self.bloecke.append(block)
            self._block_aufbau.addWidget(block.widget)
        # Was nicht passt, steht eingeklappt unter einer Zeile mit seiner Zahl; ein Klick zeigt je
        # Strategie, was man dafür im 3D anklicken muss.
        self.passt_nicht = QtGui.QWidget()
        kopf_aufbau = QtGui.QHBoxLayout(self.passt_nicht)
        kopf_aufbau.setContentsMargins(0, 0, 0, 0)
        self.passt_nicht_knopf = _klappknopf("", tr("ba.passt_nicht.tooltip"))
        kopf_aufbau.addWidget(self.passt_nicht_knopf)
        self.passt_nicht_kurz = _grau(tr("ba.passt_nicht.zu"))
        kopf_aufbau.addWidget(self.passt_nicht_kurz, 1)
        self.passt_nicht.hide()
        self._block_aufbau.addWidget(self.passt_nicht)
        self._reihe = [b.widget for b in self.bloecke] + [self.passt_nicht]
        self.passt_nicht_knopf.toggled.connect(self._passt_nicht_aufklappen)

        # --- Schritt 3: die Einstellungen der angehakten Strategien ---
        ziel[0] = self.seiten[2].layout()
        self.nichts_angehakt = grautext(tr("ba.einstellungen.leer"))
        for block in self.bloecke:
            ziel[0].addWidget(block.einstellungen)
            block.zustand_zeigen()
        ziel[0] = aufbau
        for seite in self.seiten:
            seite.layout().addStretch()

        # Unter allen Schritten: rot, welche gewählte Fläche am Ende keine genaue Bahn hätte
        # (Grundsatz 0; Manuel, 2026-10-03: „das Teil sollte danach schon so ausschauen, wie's
        # ausschauen soll“), rot, was nicht geht, und „Zurück“ / „Weiter“.
        self.unfertig = QtGui.QLabel()
        self.unfertig.setWordWrap(True)
        self.unfertig.setStyleSheet(f"color: {ROT};")
        self.unfertig.hide()
        aufbau.addWidget(self.unfertig)
        # Darunter, was die Fläche doch fertig macht, als Knopf (_senken_angebot).
        self.unfertig_angebot = QtGui.QWidget()
        reihe = QtGui.QHBoxLayout(self.unfertig_angebot)
        reihe.setContentsMargins(0, 0, 0, 0)
        self.unfertig_satz = QtGui.QLabel()
        self.unfertig_satz.setWordWrap(True)
        reihe.addWidget(self.unfertig_satz, 1)
        self.unfertig_knopf = knopf("", "", self._unfertig_angebot_nehmen)
        reihe.addWidget(self.unfertig_knopf)
        self.unfertig_angebot.hide()
        aufbau.addWidget(self.unfertig_angebot)
        self._unfertig_aktion = None
        self.hinweis = QtGui.QLabel()
        self.hinweis.setWordWrap(True)
        self.hinweis.setStyleSheet(f"color: {ROT};")
        aufbau.addWidget(self.hinweis)
        zeile = QtGui.QWidget()
        knoepfe = QtGui.QHBoxLayout(zeile)
        knoepfe.setContentsMargins(0, 0, 0, 0)
        self.knopf_zurueck = knopf(tr("ba.zurueck"), tr("ba.zurueck.tooltip"), self.zurueck)
        knoepfe.addWidget(self.knopf_zurueck)
        knoepfe.addStretch()
        self.knopf_weiter = knopf(tr("ba.weiter"), tr("ba.weiter.tooltip"), self.weiter)
        knoepfe.addWidget(self.knopf_weiter)
        # Dasselbe wie „OK“ der Aufgabe: „Anlegen“, beim Ändern „Übernehmen“.
        self.knopf_fertig = knopf(tr("va.anlegen"), tr("ba.anlegen.tooltip"), self.accept)
        self.knopf_fertig.hide()
        from . import gui_rechnet

        self.rad_unten = gui_rechnet.Rad()  # dreht, solange gerechnet wird
        knoepfe.addWidget(self.rad_unten)
        knoepfe.addWidget(self.knopf_fertig)
        aufbau.addWidget(zeile)
        self._seite = 0
        # Die Beschriftungen aller Blöcke gleich breit: die Felder stehen untereinander.
        reihen = [oben, koerper, rohteil, nullpunkt, werkstoff] + [b.reihen for b in self.bloecke]
        breite = max(r.breite_beschriftung() for r in reihen)
        for r in reihen:
            r.raster.setColumnMinimumWidth(0, breite)
        aufbau.addStretch()
        ruhiges_mausrad(form)
        return form

    # --- Die Schritte -----------------------------------------------------------------------

    def seite(self):
        """Der gezeigte Schritt: 0 Aufspannung, 1 was soll weg, 2 Einstellungen."""
        return self._seite

    def seite_zeigen(self, nummer):
        """Zeigt den Schritt `nummer` (0–2): seine Seite, oben „Schritt 2 von 3 – …“, darunter
        die passende Anleitung; „Zurück“ und „Weiter“, wo es sie gibt – weiter erst mit Job."""
        self._seite = max(0, min(int(nummer), len(self.seiten) - 1))
        for i, seite in enumerate(self.seiten):
            seite.setVisible(i == self._seite)
        namen = (
            tr("ba.schritt.aufspannung"),
            tr("ba.schritt.was"),
            tr("ba.schritt.einstellungen"),
        )
        self.schritt_text.setText(
            tr(
                "ba.schritt",
                nummer=self._seite + 1,
                anzahl=len(self.seiten),
                name=namen[self._seite],
            )
        )
        if self.zu_aendern is None:
            if self._job_dazu:
                erste = tr("ba.anleitung.dazu")  # die Zeile darunter sagt, welcher Job
            else:
                erste = tr("ba.anleitung") if self.job is None else tr("ba.anleitung.job")
            anleitungen = (
                erste,
                tr("ba.anleitung.was"),
                tr("ba.anleitung.einstellungen"),
            )
            self.anleitung.setText(anleitungen[self._seite])
        self._rohteil_kurz_zeigen()
        letzte = self._seite == len(self.seiten) - 1
        self.knopf_zurueck.setVisible(self._seite > 0)
        self.knopf_weiter.setVisible(not letzte)
        self.knopf_weiter.setEnabled(self.job is not None and not self.nur_vierachs())
        # Im letzten Schritt steht „Anlegen“ dort, wo vorher „Weiter“ stand (Manuel,
        # 2026-10-02: „als Mensch erwartet man dann den Button unten, wo der Weiter-Button war“).
        self.knopf_fertig.setVisible(letzte)
        self._knoepfe_beschriften()
        self.nichts_angehakt.setVisible(not self.aktive_bloecke())

    def weiter(self):
        if self.job is not None and not self.nur_vierachs():
            self.seite_zeigen(self._seite + 1)

    def zurueck(self):
        self.seite_zeigen(self._seite - 1)

    # --- Schnittstelle zu FreeCAD ---------------------------------------------------------

    def getStandardButtons(self):
        return QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel

    def modifyStandardButtons(self, knoepfe):
        self._knoepfe = knoepfe
        with contextlib.suppress(Exception):  # links neben den Knöpfen: das Rad (gui_rechnet)
            knoepfe.layout().insertWidget(0, self._rechnet.rad())
        oben = knoepfe.button(QtGui.QDialogButtonBox.Ok)
        if oben is not None:
            # Gedrückt kommt vor FreeCADs accept(): So weiß accept(), dass es der Knopf oben war.
            oben.pressed.connect(self._oben_gedrueckt)
        self._knoepfe_beschriften()

    def _oben_gedrueckt(self):
        self._oben_weiter = self.zu_aendern is None and self._vor_anlegen()

    def _vor_anlegen(self):
        """Steht der Knopf oben noch für „Weiter“? Hier vor dem letzten Schritt; die Beta
        (gui_bearbeitung_beta) legt schon ab dem Schruppen an."""
        return getattr(self, "_seite", 0) < len(getattr(self, "seiten", ())) - 1

    def knopf_anlegen(self):
        if self._knoepfe is None:
            return None
        return self._knoepfe.button(QtGui.QDialogButtonBox.Ok)

    def _knoepfe_beschriften(self):
        aendern = self.zu_aendern is not None
        geht = self.job is not None and self._kann_anlegen()
        anzeige = getattr(self, "_rechnet", None)
        if anzeige is not None and anzeige.an:
            geht = False  # solange gerechnet wird (gui_rechnet; Manuel, 2026-10-12)
        unten = getattr(self, "knopf_fertig", None)
        # Vor dem letzten Schritt heißt der Knopf oben „Weiter“ und blättert weiter, wie der unten
        # rechts (Manuel, 2026-10-16: „anklickbar obwohl noch zwei weitere auswahl felder kommen
        # vll sollte man das als "weiter" button deklarieren exakt wie den unten rechts“).
        vorher = not aendern and self._vor_anlegen()
        for knopf_ in (self.knopf_anlegen(), unten):
            if knopf_ is None:
                continue
            if aendern:
                knopf_.setText(tr("va.uebernehmen"))
                knopf_.setToolTip(tr("ba.uebernehmen.tooltip"))
            elif vorher and knopf_ is not unten:
                knopf_.setText(tr("ba.weiter"))
                knopf_.setToolTip(tr("ba.weiter.tooltip"))
                knopf_.setEnabled(self.job is not None and not self.nur_vierachs())
                continue
            elif self._folge_ohne_operation():
                if _FOLGE:
                    knopf_.setText(tr("ba.folge.naechste"))
                    knopf_.setToolTip(tr("ba.folge.naechste.tooltip"))
                else:
                    knopf_.setText(tr("ba.folge.fertig"))
                    knopf_.setToolTip(tr("ba.folge.fertig.tooltip"))
            else:
                knopf_.setText(tr("va.anlegen"))
                knopf_.setToolTip(tr("ba.anlegen.tooltip"))
            knopf_.setEnabled(geht)

    def aktive_bloecke(self):
        return [b for b in self.bloecke if b.aktiv()]

    def _kann_anlegen(self):
        aktive = self.aktive_bloecke()
        if self.hinweis.text():
            return False
        if not aktive:
            # Nur schräge Flächen gewählt: „Anlegen“ legt die Ebene bzw. Aufspannung dafür an.
            if self._folge_ohne_operation():
                return True
            return self.job is not None and self._nur_geschwenkt(vr.modell(self.job).Shape)
        return all(b.kann_anlegen() for b in aktive)

    def _folge_ohne_operation(self):
        """Eine Ebene der Kette (_ebenen_der_aufspannung), in der nichts angehakt ist – oft haben
        die Ebenen davor alles genommen: Der Knopf geht weiter zur nächsten, die Ebene bleibt ohne
        Operation. Sonst bliebe nur „Abbrechen“, und das beendet die Kette (am Geist an der
        5-Achs-Fräse Ebene 6 von 7)."""
        return (
            self.zu_aendern is None
            and bool(getattr(self, "_folge", None))
            and self.job is not None
            and not self.aktive_bloecke()
        )

    def accept(self):
        _FOLGE_FENSTER["klasse"] = type(self)
        if getattr(self, "_oben_weiter", False):
            # Der Knopf oben vor dem letzten Schritt: „Weiter“ (_knoepfe_beschriften).
            self._oben_weiter = False
            self.weiter()
            return False
        if self.job is None:
            return self.reject()
        if self.nur_vierachs():
            QtGui.QMessageBox.information(
                self.form, tr("ba.titel"), _drehmaschine_text(self.maschine())
            )
            return False
        if self._rohteil_uhr.isActive():
            self._rohteil_uhr.stop()
            self._rohteil_anwenden()
        if self._nullpunkt_uhr.isActive():
            self._nullpunkt_uhr.stop()
            self._nullpunkt_anwenden()
        magazin = self.magazin()  # die gewählte Beladung (nur wenn nicht die geltende)
        mg.merken(self.job, None if magazin is None or magazin.gilt else magazin)
        # Rechnet die Vorschau noch (im Takt, oder gleich nach einer Eingabe): erst ganz fertig –
        # der Wettbewerb am Ende setzt noch Haken.
        anzulegen = self._nur_diese_anlegen
        if self.vorschau_laeuft() or any(
            b.vorschau is None for b in anzulegen(self.aktive_bloecke())
        ):
            self._vorschau_rechnen()
        if not self._kann_anlegen() or any(
            b.vorschau is None for b in anzulegen(self.aktive_bloecke())
        ):
            return False  # der Grund steht rot im Fenster
        if self.zu_aendern is not None:
            if not self._aendern():
                return False
        else:
            # Job und Rohteil: ein Schritt Rückgängig. Die Operationen kommen in einem eigenen –
            # in einen gemeinsamen lässt FreeCAD es nicht (_im_befehl).
            if self._job_offen:
                self.doc.commitTransaction()
                self._job_offen = False
                self._job_fest = True
            if not self._anlegen():
                self.doc.openTransaction(tr("ba.titel"))  # für weitere Eingaben
                self._job_offen = True
                return False
        folge = self._folge_vorbereiten() if self.zu_aendern is None else None
        self._vor_dem_schliessen()
        for block in self.aktive_bloecke():
            block.merken()
        if not self._aufspannung_fest():
            nullpunkt_vorgeben(self.nullpunkt())
        dialog_schliessen(self.doc)
        with uhren.still():  # Qt baut das Fenster noch ab
            self.doc.recompute()
        if folge is not None:
            uhren.gleich(folge)
        elif self._folge:
            uhren.gleich(_folge_weiter)
        return True

    def _folge_vorbereiten(self):
        """Was nach „Anlegen“ angelegt wird – eine Funktion ohne Argumente oder None: an einer
        5-Achs-Maschine die Ebenen der weiteren Richtungen aus „Alles aus dieser Aufspannung“
        und der gewählten schrägen Flächen (_ebenen_der_aufspannung); an einer 3-Achs-Fräse die
        gekippten Aufspannungen der schrägen Flächen (_gekippt_anlegen)."""
        grundjob = rw.grundjob_von(self.job)
        schraege = self._schraege_richtungen(vr.modell(self.job).Shape)
        if not self._fuenfachs():
            return (lambda: _gekippt_anlegen(grundjob, schraege)) if schraege else None
        z = self._zugang
        weitere = [r for r in z.richtungen if r.achse[2] <= 1 - 1e-6] if z is not None else []
        for r in schraege:
            gleich = next(
                (
                    w
                    for w in weitere
                    if (FreeCAD.Vector(*w.achse) - FreeCAD.Vector(*r.achse)).Length < zg.GLEICH
                ),
                None,
            )
            if gleich is None:
                weitere.append(r)
            else:
                gleich.flaechen = sorted(
                    set(gleich.flaechen) | set(r.flaechen), key=lambda n: int(n[4:])
                )
        if not weitere:
            return None
        werkzeug, einsatz = self.raeumen.fraeser(), self.raeumen.einsatz()
        waagerecht = self._spindel_quer()
        return lambda: _ebenen_der_aufspannung(grundjob, weitere, werkzeug, einsatz, waagerecht)

    def reject(self):
        if self._folge:
            _FOLGE.clear()  # „Abbrechen“ hört mit der Kette auf – die Ebenen bleiben
        self._vor_dem_schliessen()
        if self._aufspannung_vorher:
            from .gui_schwenken import zeige_wieder

            zeige_wieder(self._aufspannung_vorher)
            self._aufspannung_vorher = []
        if self._job_offen:
            self._sichtbarkeit_zurueck()
            self.doc.abortTransaction()
            self._job_offen = False
        if self._job_fest:  # „Anlegen“ ging nicht, der Job liegt schon als Schritt ab
            self._sichtbarkeit_zurueck()
            while len(self.doc.UndoNames) > self._undo_vorher:
                self.doc.undo()
        dialog_schliessen(self.doc)
        with uhren.still():  # Qt baut das Fenster noch ab
            self.doc.recompute()
        return True

    def _verschwunden(self):
        """Das Fenster ist weg, ohne dass es geschlossen wurde: aufräumen wie beim Schließen."""
        if not self.geschlossen:
            with contextlib.suppress(Exception):
                self._vor_dem_schliessen()
            self.geschlossen = True

    def _vor_dem_schliessen(self):
        BearbeitungPanel.offen = None
        self.geschlossen = True
        if self._bahnvorschau is not None:
            self._bahnvorschau.weg()
        self._rechnet.ende()
        self._vorschau_lauf_beenden()
        self._genau_beenden()
        from .gui_reichweite import job_merken

        job_merken(self.job)  # Prüfen, Bestückung und Programm nehmen ihn ohne Auswahl
        self._vorschau_uhr.stop()
        self._rohteil_uhr.stop()
        self._nullpunkt_uhr.stop()
        self._farben_zurueck()
        if self._beobachter is not None:
            FreeCADGui.Selection.removeObserver(self._beobachter)
            FreeCADGui.Selection.removeSelectionGate()
            self._beobachter = None
        FreeCADGui.Selection.clearSelection()

    # --- Teil, Job, Rohteil ---------------------------------------------------------------

    def angeklickt(self, objekt, unterelement, punkt=None, dokument=None):
        """Eine angeklickte Fläche: ohne Job macht sie ihr Teil zum Teil des Jobs – liegt es in
        einem anderen Dokument (`dokument`, sein Name) oder hinter einem Link dorthin, öffnet sich
        das Fenster dort neu (B-020); mit Job nimmt sie die Fläche dazu oder heraus – wartet „Im
        Bild wählen …“ auf eine Eintauchstelle der Nut, ist der Punkt diese Stelle."""
        if self.geschlossen:
            return
        if self.nut.stelle_waehlt is not None and self.job is not None and punkt is not None:
            FreeCADGui.Selection.clearSelection()
            self.nut.stelle_angeklickt(punkt)
            return
        if self.job is None:
            wo = self.doc
            wahl = gewaehlte_flaeche(wo)
            if wahl is None and dokument and dokument != self.doc.Name:
                wo = FreeCAD.listDocuments().get(dokument)
                wahl = gewaehlte_flaeche(wo) if wo is not None else None
            if wahl is None:
                return
            teil = teil_hinter_link(wahl[0])
            if teil.Document is not self.doc:
                self._im_dokument_neu(teil, wahl[1])
            else:
                self._beginnen(wahl, angeklicktes_teil(wo))
            return
        weg = unterelement.split(".") if unterelement else []
        if weg and weg[-1].startswith("Edge"):
            teil, _flaeche = _entlang(self.doc, self.doc.getObject(objekt), ".".join(weg[:-1]))
            klon = vr.modell(self.job)
            if teil is None or vr.original(teil) is not vr.original(klon):
                return
            FreeCADGui.Selection.clearSelection()
            self.kante_umschalten(weg[-1])
            return
        teil, flaeche = _entlang(self.doc, self.doc.getObject(objekt), unterelement)
        klon = vr.modell(self.job)
        if teil is None or flaeche is None or vr.original(teil) is not vr.original(klon):
            return
        FreeCADGui.Selection.clearSelection()
        if self.knopf_unten_waehlen.isChecked() and not self._aufspannung_fest():
            self.knopf_unten_waehlen.setChecked(False)
            self.unten_waehlen(flaeche)  # „Fläche anklicken …“: die Fläche, die unten liegt
            return
        self.flaeche_umschalten(flaeche)

    # --- Wie das Teil auf dem Tisch liegt -------------------------------------------------

    def unten_waehlen(self, flaeche):
        """Macht die ebene Fläche `flaeche` („Face6“) zur Unterseite: Das Teil im Job dreht sich
        so, dass sie nach unten zeigt, Rohteil und Nullpunkt folgen. None: wie modelliert."""
        if self.job is None or self._aufspannung_fest():
            return
        if flaeche is not None and _aussennormale(self.teil.Shape, flaeche) is None:
            self.hinweis.setText(tr("ba.unten.nicht_eben", name=flaeche))
            return
        self.hinweis.setText("")
        self._unten = flaeche
        self._zugang = None  # eine andere Fläche im Spannmittel – neu fragen
        self._lage_geaendert()

    def x_drehen(self, viertel):
        """Dreht das Teil im Job um Z – X zeigt danach ein Viertel weiter (+1: gegen den
        Uhrzeigersinn, von oben gesehen)."""
        if self.job is None or self._aufspannung_fest():
            return
        self._viertel = (self._viertel + int(viertel)) % 4
        self._lage_geaendert()

    def aufspannung(self):
        """Die Drehung vom Teil, wie es modelliert ist, in den Job: die Unterseite nach −Z, dann
        um Z in Vierteln."""
        drehung = FreeCAD.Rotation()
        if self._unten is not None and self.teil is not None:
            normale = _aussennormale(self.teil.Shape, self._unten)
            if normale is not None:
                drehung = FreeCAD.Rotation(normale, FreeCAD.Vector(0, 0, -1))
        um_z = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), 90.0 * self._viertel)
        return um_z.multiply(drehung)

    def _lage_geaendert(self):
        self._lage_zeigen()
        self._nullpunkt_setzen(self.job)
        if FreeCADGui.ActiveDocument is not None and FreeCADGui.ActiveDocument.ActiveView:
            FreeCADGui.SendMsgToActiveView("ViewFit")  # gedreht liegt das Teil woanders
        self._flaechen_zeigen()
        self._ziel_gemerkt = None  # gedreht kann der Kasten gleich bleiben, das Teil nicht
        self.vorschau_starten()

    def _lage_zeigen(self):
        """„Face6 liegt unten“ / „wie modelliert“, „um 90° gedreht“ – neben den Knöpfen."""
        if self._unten is None:
            self.unten_text.setText(tr("ba.unten.modell"))
        else:
            self.unten_text.setText(tr("ba.unten.flaeche", name=self._unten))
        self.knopf_unten_modell.setEnabled(self._unten is not None)
        if self._viertel == 0:
            self.x_text.setText(tr("ba.x.modell"))
        else:
            self.x_text.setText(tr("ba.x.gedreht", grad=90 * self._viertel))

    def _beginnen(self, wahl, angeklickt=None):
        """Das angeklickte Teil: Hat es schon einen Job, kommen die neuen Operationen dort
        hinein (job_dazu), sonst entsteht ein neuer (teil_waehlen)."""
        teil, flaeche = wahl
        job = None if self._neu else vorhandener_job(self.doc, teil, angeklickt)
        if job is not None:
            self.job_dazu(job, flaeche)
        else:
            self.teil_waehlen(teil, flaeche)

    def job_dazu(self, job, flaeche=None):
        """Ein weiterer Lauf am Teil (W-012 M2): die neuen Operationen in den Job, den es schon
        hat, hinter die vorhandenen – Maschine, Rohteil, Nullpunkt und Lage bleiben, wie sie
        dort stehen (Schritt 1 grau). „Neuer Job …“ legt stattdessen einen neuen an."""
        if self.job is not None or self.geschlossen:
            return
        self.job = job
        self._job_dazu = True
        self.teil = vr.original(vr.modell(job))
        self.teil_text.setText(self.teil.Label)
        # Hat der Job geschwenkte Ebenen (3+2), nur sein Teil und seine Bahnen im Bild.
        from .gui_schwenken import zeige_job

        self._aufspannung_vorher = zeige_job(job)
        self._aufspannung_zeigen()
        ops = [o for o in js.operationen(job) if getattr(o, "Active", True)]
        if not ops:
            text = tr("ba.dazu.keine", job=job.Label)
        elif len(ops) == 1:
            text = tr("ba.dazu.eine", job=job.Label, name=ops[0].Label)
        else:
            text = tr("ba.dazu.mehrere", job=job.Label, n=len(ops), name=ops[-1].Label)
        if self._folge:
            text = f"{self._folge}\n{text}"
        self.dazu_text.setText(text)
        self.dazu_zeile.setVisible(True)
        form = vr.modell(job).Shape
        self.gewaehlte = self._vorwahl_nehmen(form, flaeche)
        self.kanten = [n for n in self._vorwahl or () if n.startswith("Edge")]
        FreeCADGui.Selection.clearSelection()
        self._bearbeitung_fuellen()
        self._flaechen_zeigen()
        self._auffrischen()
        self.seite_zeigen(self._seite)
        self.vorschau_starten()

    def _vorwahl_nehmen(self, form, flaeche):
        """Die Flächen, die zu Beginn gewählt sind: die einer Ebene aus „Alles aus dieser
        Aufspannung“ – sonst die angeklickte –, soweit eine Strategie sie nimmt."""
        if self._vorwahl and self._ist_stl():
            return s3b.freiformflaechen(form, self._vorwahl)
        if self._vorwahl:
            return [n for n in self._vorwahl if self._nimmt_eine(form, n)]
        return [flaeche] if flaeche and any(b.s.passt(form, flaeche) for b in self.bloecke) else []

    def _nimmt_eine(self, form, name):
        """Nimmt eine Strategie die Fläche einer Richtung aus „Alles aus dieser Aufspannung“? Eine
        ebene, zylindrische oder kegelige nicht über die Freiform-Strategien – die Spitze einer
        Bohrung gehört zu ihr, nicht zum 3D-Schlichten."""
        nummer = int(name[4:]) - 1 if name.startswith("Face") and name[4:].isdigit() else -1
        if not 0 <= nummer < ft.anzahl(form):
            return False
        analytisch = (
            not self._ist_stl()  # die Dreiecke eines STL sind eben – und doch Freiform
            and ft.flaeche(form, nummer).Surface.__class__.__name__ in ANALYTISCH
        )
        return any(
            b.s.passt(form, name)
            for b in self.bloecke
            if not (analytisch and b.s.kennung in FREIFORM_STRATEGIEN)
        )

    def _im_dokument_neu(self, teil, flaeche):
        """Das Teil liegt in einem anderen Dokument als das Fenster: Es schließt und öffnet sich
        dort neu, mit Teil und Fläche (ein Aufgabenfenster gehört zu seinem Dokument)."""
        dokument, neu = teil.Document, self._neu
        self.reject()

        def oeffnen():
            _aktivieren(dokument)
            FreeCADGui.Control.showDialog(BearbeitungPanel(dokument, (teil, flaeche), neu=neu))

        QtCore.QTimer.singleShot(0, oeffnen)

    def neuer_job(self):
        """„Neuer Job …“: statt in den vorhandenen Job einen neuen anlegen – eine zweite
        Aufspannung. Dieses Fenster schließt, ein neues öffnet sich mit Teil und Flächen."""
        if not self._job_dazu or self.teil is None:
            return
        dokument, teil = self.doc, self.teil
        flaeche = self.gewaehlte[0] if self.gewaehlte else None
        self.reject()

        fenster = self._neues_fenster(dokument, (teil, flaeche))

        def oeffnen():
            FreeCADGui.Control.showDialog(fenster())

        QtCore.QTimer.singleShot(0, oeffnen)

    def _neues_fenster(self, dokument, wahl):
        """Was „Neuer Job …“ öffnet – die Beta (gui_bearbeitung_beta) öffnet sich selbst."""
        return lambda: BearbeitungPanel(dokument, wahl, neu=True)

    def _aufspannung_fest(self):
        """Stehen Maschine, Rohteil, Nullpunkt und Lage im Job schon fest – beim Ändern einer
        Operation und bei einem weiteren Lauf am selben Job (W-012 M2)?"""
        return self.zu_aendern is not None or self._job_dazu

    def teil_waehlen(self, teil, flaeche=None):
        """Das Teil für den Job – der Job mit dem Rohteil entsteht sofort (eine Transaktion,
        bis „Anlegen“ oder „Abbrechen“). `flaeche`: die angeklickte Fläche („Face6“) – ist sie
        eben nach oben oder eine Wand, ist sie gewählt, sonst die Oberseite."""
        if self.job is not None or teil is None or self.geschlossen:
            return
        self.teil = teil
        self.teil_text.setText(teil.Label)
        if self.wahl_rohteil.count():
            self._rohteil_liste_fuellen()  # das Teil selbst ist kein Rohteil
        try:
            self.job = _im_befehl(self._neuer_job)
        except Exception as fehler:  # CAM meldet vieles nur als Ausnahme
            FreeCAD.Console.PrintError(f"Bearbeitung: {fehler}\n{traceback.format_exc()}")
            kaputt = _fehler_im_modell(teil)
            if kaputt is not None:
                # Statt CAMs „length of box too small“ (Manuels Stifthalter in 1.1.4: die Drehung
                # fand ihre Skizzenfläche nicht – das Modell rechnete beim Anlegen nicht).
                text = tr("ba.fehler.modell", teil=teil.Label, objekt=kaputt[0], fehler=kaputt[1])
            else:
                text = tr("ba.fehler.anlegen", fehler=str(fehler))
            self.hinweis.setText(text)
            self.teil = None
            return
        self._job_offen = True
        self._job_zeigen()
        self._maschine_gewaehlt()  # der neue Job bekommt die gewählte Maschine
        if self.nullpunkt() is not None or self._nullpunkt_versatz().Length > 0:
            self._nullpunkt_setzen(self.job)
        form = vr.modell(self.job).Shape
        self.gewaehlte = self._vorwahl_nehmen(form, flaeche)
        self.kanten = [n for n in self._vorwahl or () if n.startswith("Edge")]
        FreeCADGui.Selection.clearSelection()
        self._bearbeitung_fuellen()
        self._flaechen_zeigen()
        self._auffrischen()
        self.seite_zeigen(self._seite)  # mit dem Job geht „Weiter“
        self.vorschau_starten()

    def _neuer_job(self):
        """Legt den Job an und öffnet dafür die Transaktion des Assistenten – nur in
        _im_befehl (wie gui_vierachs._neuer_job)."""
        import Path.Main.Job as PathJob

        self.doc.openTransaction(tr("ba.titel"))
        FreeCAD.setActiveDocument(self.doc.Name)
        job = PathJob.Create("Job", [self.teil])
        job.Label = tr("ba.job", teil=self.teil.Label)
        self._rohteil_setzen(job)
        spannung.setze(job, self._gespannt())
        self.doc.recompute()
        if _globale_transaktionen():
            FreeCAD.setActiveTransaction(tr("ba.titel"), True)
        return job

    # --- Maschine (W-011 S2) ------------------------------------------------------------------

    def _maschinen_fuellen(self, auswahl=None):
        """Die Maschinen aus der Liste („Maschinen …“) in die Wahl. Vorgewählt `auswahl` (eine
        Datei; "" heißt keine), ohne die des Jobs, sonst die zuletzt benutzte, sonst die
        erste. Ohne Maschine in der Liste steht „keine“ da – der Assistent rechnet dann mit
        einer 3-Achs-Fräse."""
        msp.aufraeumen()  # verschwundene Dateien aus dem temporären Ordner
        eintraege = msp.laden()
        gewollt = auswahl is not None
        if not gewollt:
            auswahl = rw.gemerkte_maschine(self.job)
        index = next(
            (i for i, e in enumerate(eintraege) if msp.gleiche_datei(e.datei, auswahl)), None
        )
        keine = not eintraege or (index is None and gewollt)
        self._maschinen_fuellt = True
        try:
            self.wahl_maschine.clear()
            if keine:
                self.wahl_maschine.addItem(tr("ba.maschine.keine"), "")
            for eintrag in eintraege:
                art = msp.art_text(eintrag)
                text = (
                    eintrag.name
                    if eintrag.name == art
                    else tr("ba.maschine.eintrag", name=eintrag.name, art=art)
                )
                if not eintrag.vorhanden:
                    text = tr("ba.maschine.fehlt", maschine=text)
                self.wahl_maschine.addItem(text, eintrag.datei)
            if index is not None:
                self.wahl_maschine.setCurrentIndex(index + int(keine))
            else:
                self.wahl_maschine.setCurrentIndex(0)
        finally:
            self._maschinen_fuellt = False
        self._maschine_gewaehlt()

    def _fuenfachs(self):
        """Ist eine 5-Achs-Maschine gewählt (für Anstellen und Flanke)?"""
        try:
            eintrag = self.maschine()
        except AttributeError:  # die Wahl der Maschine gibt es noch nicht
            return False
        return eintrag is not None and eintrag.vorhanden and eintrag.art == msp.FRAESE_5

    def restschlichten_mit(self, kennung):
        """„Restschlichten mit T… anhaken“: der Block Restschlichten angehakt, mit dem Fräser
        `kennung`, unter dem Rand wie das 3D-Schlichten."""
        block = self.restschlichten
        kennungen = [w.kennung for w in getattr(block, "_fraeser", [])]
        block.haken.setChecked(True)
        block.von_hand = True
        if kennung in kennungen:
            block.wahl_fraeser.setCurrentIndex(kennungen.index(kennung))
            block.fraeser_von_hand = True
        kasten = block.haken_felder.get("hinterschnitt")
        if kasten is not None and kasten.isEnabled():
            kasten.setChecked(True)
        self.vorschau_starten()

    def werkzeugaufnahme(self):
        """Die Werkzeugaufnahme der Spindel der gewählten Maschine („SK40“ …; maschine.
        werkzeugaufnahme) aus ihrem offenen Dokument, gemerkt je Maschine; "" ohne (dann SK40)."""
        from . import gui_reichweite
        from . import maschine as m

        eintrag = self.maschine() if hasattr(self, "wahl_maschine") else None
        datei = os.path.abspath(getattr(eintrag, "datei", "") or "") if eintrag else ""
        gemerkt = getattr(self, "_aufnahme_merk", None)
        if gemerkt is not None and gemerkt[0] == datei:
            return gemerkt[1]
        aufnahme = ""
        try:
            for assembly, maschine in gui_reichweite.offene_maschinen():
                if datei and os.path.abspath(assembly.Document.FileName or "") == datei:
                    aufnahme = m.werkzeugaufnahme(maschine)
                    break
        except Exception:  # noqa: BLE001 – ohne Dokumente: SK40
            aufnahme = ""
        self._aufnahme_merk = (datei, aufnahme)
        return aufnahme

    def _spindel_quer(self):
        """Steht an der gewählten 5-Achs-Fräse die Spindel in der Grundstellung quer zu Z – waagerecht
        wie an der GROB G550? Dann kommt auch, was von oben gefräst wird, in eine Ebene: Die
        Maschine schwenkt das Teil zur Spindel, das Programm gibt den Schwenk aus (Manuel,
        2026-10-17: „Automatisch Ebene A−90“, „aber im progromm muss das natürlich dann auch
        ausgegeben werden“). Nicht in einer Ebene – die ist schon geschwenkt."""
        from . import schwenken as sw

        if self.job is None or self.zu_aendern is not None or sw.ist_ebene(self.job):
            return False
        if not self._fuenfachs() or self._ist_stl():
            return False  # ein Teil aus einem STL: je Dreieck eine Fläche – bleibt im Grundjob
        eintrag = self.maschine()
        if eintrag.spindel_quer is None:
            eintrag = _spindel_nachrechnen(eintrag)
        return bool(eintrag.spindel_quer)

    def maschine(self):
        """Der Eintrag der gewählten Maschine (maschinenspeicher.Eintrag) – oder None."""
        datei = self.wahl_maschine.currentData() or ""
        return msp.finde(msp.laden(), datei) if datei else None

    def magazin(self):
        """Das gewählte Magazin der gewählten Maschine („Magazin“; sonst das am Job gemerkte,
        sonst das, das gilt – W-002 Stufe H2) – None ohne."""
        wahl = getattr(self, "wahl_maschine", None)  # die Wahl der Maschine gibt es noch nicht
        datei = (wahl.currentData() or "") if wahl is not None else ""
        if not datei or self.bibliothek is None:
            return None
        return mg.des_jobs(None, self.bibliothek, datei, kennung=self._magazin_kennung())

    def _magazin_kennung(self):
        wahl = getattr(self, "wahl_magazin", None)
        kennung = (wahl.currentData() or "") if wahl is not None and wahl.count() else ""
        return kennung or (mg.gewaehlt(self.job) if self.job is not None else "")

    def _magazine_fuellen(self):
        """Die Liste „Magazin“: die Magazine der gewählten Maschine, das geltende zuerst –
        vorgewählt das bisher gewählte, sonst das am Job gemerkte, sonst das geltende; die Zeile
        versteckt ohne Magazin, grau mit nur einem."""
        wahl = getattr(self, "wahl_magazin", None)
        if wahl is None:
            return
        vorher = (wahl.currentData() if wahl.count() else None) or (
            mg.gewaehlt(self.job) if self.job is not None else ""
        )
        maschine = getattr(self, "wahl_maschine", None)
        datei = (maschine.currentData() or "") if maschine is not None else ""
        bibliothek = self.bibliothek if self.bibliothek is not None else mg.bibliothek_laden()
        magazine = bibliothek.magazine_der_maschine(datei) if bibliothek and datei else []
        self._magazine_fuellt = True
        try:
            wahl.clear()
            for magazin in magazine:
                text = tr(
                    "mg.wahl.eintrag",
                    name=magazin.name or tr("mg.ohne_name"),
                    anzahl=len(magazin.eintraege),
                )
                if magazin.gilt:
                    text += " – " + tr("mg.wahl.gilt")
                wahl.addItem(text, magazin.kennung)
            if magazine:
                wahl.setCurrentIndex(max(0, wahl.findData(vorher)))
        finally:
            self._magazine_fuellt = False
        wahl.setEnabled(len(magazine) > 1)
        zeile = getattr(self, "magazin_zeile", None)
        for teil in zeile if isinstance(zeile, (list, tuple)) else (wahl,):
            teil.setVisible(bool(magazine))

    def _magazin_gewaehlt(self):
        """Eine andere Beladung: am Job gemerkt (nur, wenn es nicht die geltende ist), die
        Fräserlisten neu – ihre Plätze."""
        magazin = self.magazin()
        if self.job is not None:  # die Beladung gilt für den Job – auch für einen fertigen
            mg.merken(self.job, None if magazin is None or magazin.gilt else magazin)
        for block in getattr(self, "bloecke", ()):
            if self.bibliothek is not None:
                block.fraeser_fuellen(self.bibliothek, self.werkstoff())
        if self.job is not None and self.gewaehlte:
            self.vorschau_starten()

    def von_vorn_moeglich(self, werkzeug):
        """Kommt `werkzeug` in die Fräserlisten? (von_vorn_moeglich: an der Stange nur axial)"""
        return von_vorn_moeglich(self.job, self.bibliothek, werkzeug)

    def _maschine_gewaehlt(self):
        """Die Wahl gilt: am Job gemerkt (und als zuletzt benutzt), der Satz darunter, die
        graue Zeile in Schritt 2."""
        if getattr(self, "_maschinen_fuellt", False):
            return
        eintrag = self.maschine()
        stange = eintrag is not None and eintrag.vorhanden and eintrag.art in STANGE_ARTEN
        if eintrag is None:
            self.maschine_hinweis.setText(tr("ba.maschine.leer"))
            self.maschine_hinweis.setStyleSheet(f"color: {GRAU_TEXT};")
        elif not eintrag.vorhanden:
            self.maschine_hinweis.setText(tr("ba.maschine.nicht_gefunden"))
            self.maschine_hinweis.setStyleSheet(f"color: {ROT};")
        elif eintrag.art == msp.DREHMASCHINE and self.job is not None and stangen_job(self.job):
            # Von vorn an der Stange der Drehmaschine mit Y oder C (W-025): der 4-Achs-Assistent hat
            # sie eingerichtet, hier kommen die Flächen der Stirnseite dran.
            self.maschine_hinweis.setText(tr("ba.maschine.drehmaschine_stirn"))
            self.maschine_hinweis.setStyleSheet(f"color: {GRAU_TEXT};")
        elif eintrag.art == msp.DREHMASCHINE:
            self.maschine_hinweis.setText(_drehmaschine_text(eintrag))
            self.maschine_hinweis.setStyleSheet(f"color: {ROT};")
        elif stange:
            self.maschine_hinweis.setText(tr("ba.maschine.rundachse"))
            self.maschine_hinweis.setStyleSheet(f"color: {GRAU_TEXT};")
        else:
            self.maschine_hinweis.setText("")
        self.maschine_hinweis.setVisible(bool(self.maschine_hinweis.text()))
        self.maschine_knoepfe.setVisible(eintrag is not None and not eintrag.vorhanden)
        self.knopf_vierachs.setVisible(stange and not self._aufspannung_fest())
        if hasattr(self, "knopf_weiter"):
            self.seite_zeigen(self._seite)  # „Weiter“ geht auf der Drehmaschine nicht
        if eintrag is not None and self.job is not None and not self._aufspannung_fest():
            rw.merke_maschine(self.job, eintrag.datei)
        self._magazine_fuellen()
        for block in getattr(self, "bloecke", ()):
            block.haken_pruefen()  # Anstellen geht nur an einer 5-Achs-Maschine
            if self.bibliothek is not None:  # das Magazin der Maschine (W-002 Stufe H2)
                block.fraeser_fuellen(self.bibliothek, self.werkstoff())
        if hasattr(self, "flanke") and self.job is not None and self.gewaehlte:
            self._flaechen_zeigen()  # die Flanke auch
            self.vorschau_starten()
        self._rohteil_kurz_zeigen()

    def nur_vierachs(self):
        """Ob die gewählte Maschine eine Drehmaschine ist: Dann ist das Rohteil eine Stange, und
        nur der 4-Achs-Assistent passt – „Weiter“ und „Anlegen“ gehen hier nicht."""
        eintrag = self.maschine() if hasattr(self, "wahl_maschine") else None
        return (
            eintrag is not None
            and eintrag.vorhanden
            and eintrag.art == msp.DREHMASCHINE
            and not self._aufspannung_fest()
        )

    def zum_vierachs(self):
        """Drehmaschine oder 4-Achs-Fräse: Dieser Assistent schließt (der Job geht zurück), der
        4-Achs-Assistent öffnet sich mit dem Teil, der angeklickten Fläche und der Maschine –
        ihre Datei ist dann offen, er wählt sie vor."""
        from . import gui_reichweite, gui_vierachs

        eintrag = self.maschine()
        if eintrag is None or not eintrag.vorhanden:
            return
        doc = self.doc
        wahl = self._wahl_anfang or ((self.teil, None) if self.teil is not None else None)
        self.reject()
        try:
            maschine = gui_reichweite.oeffne_datei(eintrag.datei)
        except Exception as fehler:  # nicht mehr lesbar: ohne Maschine weiter
            QtGui.QMessageBox.warning(
                FreeCADGui.getMainWindow(),
                tr("ba.titel"),
                tr("ms.datei_fehler", datei=eintrag.datei, fehler=fehler),
            )
            maschine = None
        gui_reichweite.zeige_dokument(doc)
        FreeCAD.setActiveDocument(doc.Name)
        QtCore.QTimer.singleShot(
            0,
            lambda: FreeCADGui.Control.showDialog(
                gui_vierachs.VierachsPanel(doc, wahl, maschine=maschine)
            ),
        )

    def maschine_suchen(self):
        """„Suchen …“: die Datei der gewählten Maschine liegt nicht mehr dort – die neue wählen,
        der Eintrag zieht mit (wie in „Maschinen …“)."""
        from . import gui_maschinen

        eintrag = self.maschine()
        if eintrag is None:
            return
        datei = gui_maschinen.datei_waehlen(self.form, os.path.dirname(eintrag.datei))
        if not datei:
            return
        try:
            gefunden = gui_maschinen.einlesen(datei)
        except Exception as fehler:  # keine FreeCAD-Datei, kaputt: sagen statt still scheitern
            QtGui.QMessageBox.warning(
                self.form, tr("ba.titel"), tr("ms.datei_fehler", datei=datei, fehler=fehler)
            )
            return
        if gefunden and not msp.gleiche_datei(datei, eintrag.datei):
            msp.entfernen(eintrag.datei)
        self._maschinen_fuellen(gefunden[0].datei if gefunden else eintrag.datei)

    def maschine_entfernen(self):
        """„Aus der Liste nehmen“: der Eintrag ohne Datei verschwindet; eine Datei bleibt."""
        eintrag = self.maschine()
        if eintrag is None:
            return
        msp.entfernen(eintrag.datei)
        self._maschinen_fuellen("")

    def maschinen_oeffnen(self):
        """„Maschinen …“: die Liste zum Hinzufügen und Bauen; danach ist die Wahl neu gefüllt."""
        from . import gui_maschinen

        dialog = gui_maschinen.oeffne()
        dialog.finished.connect(
            lambda _ergebnis: (
                self._maschinen_fuellen(self.wahl_maschine.currentData() or None)
                if not self.geschlossen
                else None
            )
        )

    def _rohteil_liste_fuellen(self):
        """Die Körper, die das Rohteil sein können – der gewählte bleibt, wenn es ihn noch gibt."""
        vorher_name = self.wahl_rohteil.currentData()
        vorher, self._fuellt = self._fuellt, True
        try:
            self.wahl_rohteil.clear()
            for koerper in rohteil_kandidaten(self.doc, self.teil):
                self.wahl_rohteil.addItem(koerper.Label, koerper.Name)
            index = self.wahl_rohteil.findData(vorher_name) if vorher_name else -1
            self.wahl_rohteil.setCurrentIndex(max(index, 0))
        finally:
            self._fuellt = vorher

    def _rohteil_art_geaendert(self):
        """Quader oder Körper aus dem Dokument: die Felder dazu, die Liste der Körper."""
        teil = self.knopf_rohteil_teil.isChecked()
        masse = self.knopf_rohteil_masse.isChecked()
        if teil and self.wahl_rohteil.count() == 0:
            self._rohteil_liste_fuellen()
        if teil and self.wahl_rohteil.count() == 0:
            self.knopf_rohteil_teil.blockSignals(True)
            self.knopf_rohteil_quader.setChecked(True)
            self.knopf_rohteil_teil.blockSignals(False)
            self.rohteil_erklaerung.setText(tr("ba.rohteil.keine_teile"))
            return
        stange = self.job is not None and stangen_job(self.job)
        if stange:
            # Der Stangen-Job der Drehmaschine (W-025): die Stange hat der 4-Achs-Assistent
            # eingerichtet – hier nur gesagt, nicht zu ändern.
            self.rohteil_erklaerung.setText(
                tr("ba.rohteil.stange.text", durchmesser=self._stangen_text())
            )
        elif teil:
            self.rohteil_erklaerung.setText(tr("ba.rohteil.teil.text"))
        elif self.knopf_rohteil_zylinder.isChecked():
            self.rohteil_erklaerung.setText(tr("ba.rohteil.zylinder.text"))
        elif masse:
            self.rohteil_erklaerung.setText(tr("ba.rohteil.masse.text"))
        else:
            self.rohteil_erklaerung.setText(tr("ba.rohteil.text"))
        self.rohteil_koerper.setVisible(teil and not stange)
        self.rohteilfelder.setVisible(not teil and not masse and not stange)
        self.rohteilmasse.setVisible(masse and not stange)
        if not masse:
            self.rohteil_warnung.setVisible(False)
        if masse and not self._fuellt:
            self._masse_vorschlag_zeigen()
            # Der Vorschlag dazu: der Nullpunkt Mitte oben (Manuel: „gut das sind die masse und
            # nullpunkt ist mittig oben“) – nur, solange er „wie im Modell“ steht.
            if not self.wahl_nullpunkt.currentData():
                mitte_oben = next(
                    (
                        n
                        for n, (_t, lage) in enumerate(self._nullpunkte, start=1)
                        if lage == (0, 0, 1)
                    ),
                    0,
                )
                self.wahl_nullpunkt.setCurrentIndex(self.wahl_nullpunkt.findData(mitte_oben))
        self._rohteil_geaendert()

    def _stangen_text(self):
        """„Ø 70 mm“ – die Stange des Jobs (Stock mit Radius)."""
        radius = float(getattr(getattr(self.job, "Stock", None), "Radius", 0.0) or 0.0)
        mm = einheiten.einheit(einheiten.LAENGE)
        return f"Ø {groesse_zeigen(2 * radius, einheiten.LAENGE) or '0'} {mm}"

    def rohteil_koerper_gewaehlt(self):
        """Der Körper aus dem Dokument, der das Rohteil ist – None beim Quader mit Aufmaß."""
        if not self.knopf_rohteil_teil.isChecked():
            return None
        name = self.wahl_rohteil.currentData()
        return self.doc.getObject(name) if name else None

    def _rohteil_original_zeigen(self, koerper):
        """Wie beim Teil: Ist ein Körper das Rohteil, zeigt der Job seinen Klon, das Original
        verschwindet – ein anderer Körper oder der Quader holt das vorige zurück."""
        if self._rohteil_sichtbar_vorher is not None:
            vorher, sichtbar = self._rohteil_sichtbar_vorher
            if vorher is koerper:
                return
            self._rohteil_sichtbar_vorher = None
            with contextlib.suppress(ReferenceError, RuntimeError, AttributeError):
                vorher.ViewObject.Visibility = sichtbar
        if koerper is not None and getattr(koerper, "ViewObject", None) is not None:
            self._rohteil_sichtbar_vorher = (koerper, koerper.ViewObject.Visibility)
            koerper.ViewObject.Visibility = False

    def _zylinder_felder(self, rohteil):
        """Das Aufmaß eines vorhandenen runden Rohteils in die Felder: am Umfang über dem
        kleinsten Kreis um das Teil, oben und unten über seiner Höhe."""
        with contextlib.suppress(Exception):
            form = vr.modell(self.job).Shape
            _x, _y, r, z, hoehe = vr.zylinder_um(form)
            unten = z - float(rohteil.Placement.Base.z)
            werte = {
                "oben": float(rohteil.Placement.Base.z) + _mm(rohteil.Height) - (z + hoehe),
                "seite": _mm(rohteil.Radius) - r,
                "unten": unten,
            }
            for feld, wert in werte.items():
                self.felder_rohteil[feld].setText(
                    groesse_zeigen(max(wert, 0.0), einheiten.LAENGE) or "0"
                )

    def _rohteil_ersetzen(self, job, neu):
        """Setzt `neu` als Rohteil des Jobs und löscht das alte (wie FreeCADs Job-Fenster)."""
        alt = getattr(job, "Stock", None)
        job.Stock = neu
        if alt is not None and alt is not neu:
            self.doc.removeObject(alt.Name)

    def _rohteil_setzen(self, job):
        """Das Rohteil des Jobs: der gewählte Körper aus dem Dokument (ein Klon von ihm, wie bei
        FreeCADs „Rohteil aus vorhandenem Körper“) oder ein Quader um das Teil mit dem Aufmaß aus
        den Feldern."""
        import Path.Main.Job as PathJob
        import Path.Main.Stock as PathStock

        koerper = self.rohteil_koerper_gewaehlt()
        rohteil = getattr(job, "Stock", None)
        self._rohteil_original_zeigen(koerper)
        if koerper is not None:
            if koerper not in (getattr(rohteil, "Objects", None) or []):
                FreeCAD.setActiveDocument(self.doc.Name)
                klon = PathJob.createResourceClone(job, koerper, "Stock", "Stock")
                PathStock.SetupStockObject(klon, PathStock.StockType.Unknown)
                klon.Proxy.execute(klon)
                if klon.ViewObject is not None:
                    klon.ViewObject.Visibility = True
                self._rohteil_ersetzen(job, klon)
            return
        werte = {feld: self._rohteil_wert(feld) for feld in ROHTEIL_FELDER}
        if self.knopf_rohteil_zylinder.isChecked():
            # Stehend um das Teil, wie im Dreibackenfutter (W-021): der kleinste Kreis um den
            # Umriss von oben, Aufmaß am Umfang und in der Höhe.
            x, y, radius, z, hoehe = vr.zylinder_um(
                vr.modell(job).Shape, werte["oben"], werte["seite"], werte["unten"]
            )
            lage = FreeCAD.Placement(FreeCAD.Vector(x, y, z), FreeCAD.Rotation())
            if not hasattr(rohteil, "Radius") or not hasattr(rohteil, "Height"):
                FreeCAD.setActiveDocument(self.doc.Name)
                self._rohteil_ersetzen(job, PathStock.CreateCylinder(job, radius, hoehe, lage))
                return
            if abs(_mm(rohteil.Radius) - radius) > 1e-9:
                rohteil.Radius = radius
            if abs(_mm(rohteil.Height) - hoehe) > 1e-9:
                rohteil.Height = hoehe
            if not rohteil.Placement.isSame(lage, 1e-9):
                rohteil.Placement = lage
            return
        if rohteil is None or not hasattr(rohteil, "ExtZpos"):
            FreeCAD.setActiveDocument(self.doc.Name)
            self._rohteil_ersetzen(job, PathStock.CreateFromBase(job))
            rohteil = job.Stock
        if self.knopf_rohteil_masse.isChecked():
            # Mit Maßen genau: FreeCAD baut das Rohteil um den groben Hüllquader des Modells
            # (Path.Main.Stock.shapeBoundBox, vom Netz abhängig) – die Aufmaße gleichen den
            # Unterschied zum genauen aus, so ist es genau so groß wie eingetragen.
            klon = vr.modell(job).Shape
            genau, grob = klon.optimalBoundingBox(False, False), klon.BoundBox
            ausdehnung, _warnung = self._ausdehnung(genau)
            ausdehnung["ExtXneg"] -= genau.XMin - grob.XMin
            ausdehnung["ExtXpos"] -= grob.XMax - genau.XMax
            ausdehnung["ExtYneg"] -= genau.YMin - grob.YMin
            ausdehnung["ExtYpos"] -= grob.YMax - genau.YMax
            ausdehnung["ExtZneg"] -= genau.ZMin - grob.ZMin
            ausdehnung["ExtZpos"] -= grob.ZMax - genau.ZMax
        else:
            ausdehnung = dict(
                zip(
                    ("ExtZpos", "ExtZneg", "ExtXneg", "ExtXpos", "ExtYneg", "ExtYpos"),
                    (werte["oben"], werte["unten"], *[werte["seite"]] * 4),
                    strict=True,
                )
            )
        for name, wert in ausdehnung.items():
            if abs(_mm(getattr(rohteil, name)) - wert) > 1e-9:
                setattr(rohteil, name, wert)
        self._masse_merken(job)

    def _rohteil_wert(self, feld):
        """Wert eines Rohteil-Felds (mm); leer oder ungültig gilt 1 mm."""
        text = self.felder_rohteil[feld].text()
        try:
            return groesse_lesen(text, einheiten.LAENGE) if text.strip() else AUFMASS_ROHTEIL
        except ValueError:
            return AUFMASS_ROHTEIL

    def _teil_kasten(self, job=None):
        """Der genaue Hüllquader des Teils, wie es auf dem Tisch liegt (mit der Aufspannung
        gedreht; optimalBoundingBox ohne Netz – BoundBox hängt vom angehängten Netz ab und war am
        C-Ring bis 0,04 mm größer) – None ohne Job."""
        job = job if job is not None else self.job
        if job is None:
            return None
        gedreht = vr.original(vr.modell(job)).Shape.copy()
        gedreht.Placement = FreeCAD.Placement(FreeCAD.Vector(), self.aufspannung()).multiply(
            gedreht.Placement
        )
        return gedreht.optimalBoundingBox(False, False)

    @staticmethod
    def _masse_vorschlag(kasten):
        """(x, y, z) – das Teil mit AUFMASS_ROHTEIL je Seite, auf ganze mm aufgerundet."""
        return tuple(
            float(math.ceil(laenge + 2 * AUFMASS_ROHTEIL - 1e-6))
            for laenge in (kasten.XLength, kasten.YLength, kasten.ZLength)
        )

    def _masse_vorschlag_zeigen(self):
        """Der Vorschlag grau in den Feldern Länge, Breite, Höhe."""
        kasten = self._teil_kasten()
        if kasten is None:
            return
        for feld, wert in zip(("x", "y", "z"), self._masse_vorschlag(kasten), strict=True):
            self.felder_masse[feld].setPlaceholderText(groesse_zeigen(wert, einheiten.LAENGE))

    def _masse(self, kasten):
        """(x, y, z, „oben“|„unten“, Aufmaß) des Quaders mit Maßen – leere Felder: der Vorschlag."""
        werte = []
        for feld, vorschlag in zip(("x", "y", "z"), self._masse_vorschlag(kasten), strict=True):
            text = self.felder_masse[feld].text()
            try:
                werte.append(groesse_lesen(text, einheiten.LAENGE) if text.strip() else vorschlag)
            except ValueError:
                werte.append(vorschlag)
        text = self.felder_masse["aufmass"].text()
        try:
            aufmass = groesse_lesen(text, einheiten.LAENGE) if text.strip() else AUFMASS_ROHTEIL
        except ValueError:
            aufmass = AUFMASS_ROHTEIL
        return (*werte, self.wahl_masse_lage.currentData() or "oben", aufmass)

    def _ausdehnung(self, kasten):
        """({ExtXneg: …, …}, Warnung) – so weit reicht das Rohteil über den Hüllquader `kasten` des
        Teils hinaus. Mit Maßen: in X und Y mittig, in der Höhe das Aufmaß oben oder unten, das
        andere ergibt sich aus der Höhe; passt das Teil nicht hinein, der Satz dazu (und das
        Rohteil nie kleiner als das Teil)."""
        namen = ("ExtXneg", "ExtXpos", "ExtYneg", "ExtYpos", "ExtZneg", "ExtZpos")
        if not self.knopf_rohteil_masse.isChecked():
            werte = {feld: self._rohteil_wert(feld) for feld in ROHTEIL_FELDER}
            seite, unten, oben = werte["seite"], werte["unten"], werte["oben"]
            return dict(zip(namen, (seite, seite, seite, seite, unten, oben), strict=True)), ""
        x, y, z, lage, aufmass = self._masse(kasten)
        seite_x = (x - kasten.XLength) / 2
        seite_y = (y - kasten.YLength) / 2
        rest = z - kasten.ZLength - aufmass
        unten, oben = (aufmass, rest) if lage == "unten" else (rest, aufmass)
        warnung = ""
        if min(seite_x, seite_y, unten, oben) < -1e-6:
            mm = einheiten.einheit(einheiten.LAENGE)
            warnung = tr(
                "ba.rohteil.masse.passt_nicht",
                x=groesse_fest(kasten.XLength, einheiten.LAENGE, 2),
                y=groesse_fest(kasten.YLength, einheiten.LAENGE, 2),
                z=groesse_fest(kasten.ZLength + max(aufmass, 0.0), einheiten.LAENGE, 2),
                lage=tr(f"ba.rohteil.masse.{lage}"),
                aufmass=groesse_zeigen(aufmass, einheiten.LAENGE) or "0",
                mm=mm,
            )
        werte = (seite_x, seite_x, seite_y, seite_y, unten, oben)
        return dict(zip(namen, (max(w, 0.0) for w in werte), strict=True)), warnung

    def _masse_merken(self, job):
        """Am Job: die eingegebenen Maße (ROHTEIL_MASSE) – fürs Einrichtblatt und beim nächsten
        Öffnen; ohne Maße leer."""
        text = ""
        if self.knopf_rohteil_masse.isChecked():
            kasten = self._teil_kasten(job)
            x, y, z, lage, aufmass = self._masse(kasten)
            text = ";".join([f"{x:g}", f"{y:g}", f"{z:g}", lage, f"{aufmass:g}"])
        if ROHTEIL_MASSE not in job.PropertiesList:
            if not text:
                return
            job.addProperty("App::PropertyString", ROHTEIL_MASSE, "CAM-Addon", "", 4)
        if getattr(job, ROHTEIL_MASSE) != text:
            setattr(job, ROHTEIL_MASSE, text)

    def _rohteil_kurz_zeigen(self):
        """„Aufmaß 1 mm rundum · Nullpunkt: wie im Modell“ – oben in Schritt 2."""
        if not hasattr(self, "rohteil_kurz") or not hasattr(self, "wahl_nullpunkt"):
            return
        mm = einheiten.einheit(einheiten.LAENGE)
        werte = [self._rohteil_wert(feld) for feld in ROHTEIL_FELDER]
        zahlen = [groesse_zeigen(w, einheiten.LAENGE) or "0" for w in werte]
        koerper = self.rohteil_koerper_gewaehlt() if hasattr(self, "knopf_rohteil_teil") else None
        zylinder = getattr(self, "knopf_rohteil_zylinder", None)
        if self.job is not None and stangen_job(self.job):
            aufmass = tr("ba.rohteil.kurz_stange", durchmesser=self._stangen_text())
        elif koerper is not None:
            aufmass = tr("ba.rohteil.kurz_teil", name=koerper.Label)
        elif zylinder is not None and zylinder.isChecked():
            aufmass = tr(
                "ba.rohteil.kurz_zylinder", oben=zahlen[0], seite=zahlen[1], unten=zahlen[2], mm=mm
            )
        elif self.knopf_rohteil_masse.isChecked() and self.job is not None:
            x, y, z, lage, wert = self._masse(self._teil_kasten())
            aufmass = tr(
                "ba.rohteil.kurz_masse",
                x=groesse_zeigen(x, einheiten.LAENGE),
                y=groesse_zeigen(y, einheiten.LAENGE),
                z=groesse_zeigen(z, einheiten.LAENGE),
                mm=mm,
                lage=tr(f"ba.rohteil.masse.{lage}"),
                wert=groesse_zeigen(wert, einheiten.LAENGE) or "0",
            )
        elif len(set(zahlen)) == 1:
            aufmass = tr("ba.rohteil.kurz_rundum", wert=f"{zahlen[0]} {mm}")
        else:
            aufmass = tr("ba.rohteil.kurz", oben=zahlen[0], seite=zahlen[1], unten=zahlen[2], mm=mm)
        verschoben = any(self.felder_nullpunkt[f].text().strip() for f in VERSATZ_FELDER)
        wahl = self.wahl_nullpunkt.currentText()
        if verschoben:
            nullpunkt = tr("ba.nullpunkt.kurz_verschoben", wahl=wahl)
        else:
            nullpunkt = tr("ba.nullpunkt.kurz", wahl=wahl)
        teile = [aufmass, nullpunkt]
        if self._gespannt() > 0:
            wert = groesse_zeigen(self._gespannt(), einheiten.LAENGE)
            teile.append(tr("ba.gespannt.kurz", wert=f"{wert} {mm}"))
        eintrag = self.maschine() if hasattr(self, "wahl_maschine") else None
        if eintrag is not None:
            teile.insert(0, tr("ba.maschine.kurz", name=eintrag.name))
        self.rohteil_kurz.setText(" · ".join(teile))

    def _gespannt(self):
        """Von unten gespannt (mm) – leer oder ungültig 0."""
        text = self.felder_spannung["gespannt"].text() if hasattr(self, "felder_spannung") else ""
        try:
            return max(groesse_lesen(text, einheiten.LAENGE), 0.0) if text.strip() else 0.0
        except ValueError:
            return 0.0

    def _spannung_geaendert(self):
        self._rohteil_kurz_zeigen()
        if not self._fuellt and self.job is not None and not self.geschlossen:
            spannung.setze(rw.grundjob_von(self.job), self._gespannt())

    def _rohteil_geaendert(self):
        self._rohteil_kurz_zeigen()
        if not self._fuellt and self.job is not None and not self._aufspannung_fest():
            self._rohteil_uhr.start()

    def _rohteil_anwenden(self):
        if self.job is None or self._aufspannung_fest() or self.geschlossen:
            return
        self._rohteil_setzen(self.job)
        self.doc.recompute()
        if self.knopf_rohteil_masse.isChecked():
            self._masse_vorschlag_zeigen()
            _ausdehnung, warnung = self._ausdehnung(self._teil_kasten())
            self.rohteil_warnung.setText(warnung)
            self.rohteil_warnung.setVisible(bool(warnung))
        self._nullpunkt_setzen(self.job)  # die Ecken des Rohteils sind gewandert
        # Mehr oder weniger über den Flächen: Planen oder Schruppen (P-2026-10-02-54).
        self._planeinsatz_waehlen(vr.modell(self.job).Shape)
        self.vorschau_starten()

    # --- Nullpunkt ------------------------------------------------------------------------

    def nullpunkt(self):
        """(sx, sy, sz) des gewählten Punkts am Rohteil-Quader – None: wie im Modell."""
        nummer = self.wahl_nullpunkt.currentData()
        return self._nullpunkte[nummer - 1][1] if nummer else None

    def _nullpunkt_versatz(self):
        """Der Versatz vom gewählten Punkt (mm) – leer oder ungültig 0."""
        werte = []
        for feld in VERSATZ_FELDER:
            text = self.felder_nullpunkt[feld].text()
            try:
                werte.append(groesse_lesen(text, einheiten.LAENGE) if text.strip() else 0.0)
            except ValueError:
                werte.append(0.0)
        return FreeCAD.Vector(*werte)

    def _nullpunkt_geaendert(self):
        self._rohteil_kurz_zeigen()
        if not self._fuellt and self.job is not None and not self._aufspannung_fest():
            self._nullpunkt_uhr.start()

    def _nullpunkt_anwenden(self):
        if self.job is None or self._aufspannung_fest() or self.geschlossen:
            return
        self._nullpunkt_setzen(self.job)
        self.vorschau_starten()

    def _nullpunkt_setzen(self, job):
        """Rückt das Teil im Job (den Klon) mit dem Rohteil so, dass der gewählte Punkt des
        Rohteil-Quaders, um den Versatz verschoben, im Ursprung liegt – „wie im Modell“ legt
        den Klon wieder auf das Original. Der Quader kommt aus dem Original und den
        Aufmaßen der Felder; das Rohteil aus dem Modell merkt sich seine Lage nur beim
        Anlegen (Path.Main.Stock), darum wird es mitgeschoben."""
        klon = vr.modell(job)
        teil = vr.original(klon)
        lage = self.nullpunkt()
        from . import einrichtblatt as eb

        # Für das Einrichtblatt: „Mitte oben“, wie hier gewählt (Manuel, 2026-10-18).
        eb.nullpunkt_merken(
            job, lage, tuple(self._nullpunkt_versatz()) if lage is not None else (0, 0, 0)
        )
        punkt = FreeCAD.Vector()
        drehung = FreeCAD.Placement(FreeCAD.Vector(), self.aufspannung())
        koerper = self.rohteil_koerper_gewaehlt()
        if lage is not None:
            # Die Ecken des Rohteils: der Körper aus dem Dokument – oder Teil plus Aufmaß.
            gedreht = (koerper if koerper is not None else teil).Shape.copy()
            gedreht.Placement = drehung.multiply(gedreht.Placement)
            # Der genaue Hüllquader – wie FreeCAD das Rohteil in der Oberfläche um das angezeigte
            # (vernetzte) Teil baut: BoundBox einer Kopie ohne Netz war an Manuels tiefer Tasche
            # (Loft aus B-Splines) oben 3,32 mm zu hoch, Z0 lag so weit über dem Rohteil.
            bb = gedreht.optimalBoundingBox(False, False)
            if koerper is not None:
                aus = dict.fromkeys(
                    ("ExtXneg", "ExtXpos", "ExtYneg", "ExtYpos", "ExtZneg", "ExtZpos"), 0.0
                )
            else:
                aus, _warnung = self._ausdehnung(bb)
            unten = (bb.XMin - aus["ExtXneg"], bb.YMin - aus["ExtYneg"], bb.ZMin - aus["ExtZneg"])
            oben = (bb.XMax + aus["ExtXpos"], bb.YMax + aus["ExtYpos"], bb.ZMax + aus["ExtZpos"])
            punkt = FreeCAD.Vector(
                *(
                    (u + o) / 2 if s == 0 else (o if s > 0 else u)
                    for s, u, o in zip(lage, unten, oben, strict=True)
                )
            )
            punkt = punkt + self._nullpunkt_versatz()
        neu = (
            FreeCAD.Placement(punkt * -1.0, FreeCAD.Rotation())
            .multiply(drehung)
            .multiply(teil.Placement)
        )
        rohteil = getattr(job, "Stock", None)
        if koerper is not None and koerper in (getattr(rohteil, "Objects", None) or []):
            # Der Klon des Körpers wandert wie das Teil: dieselbe Verschiebung und Drehung.
            neu_rohteil = neu.multiply(teil.Placement.inverse()).multiply(koerper.Placement)
            alt_rohteil = rohteil.Placement
            if (alt_rohteil.Base - neu_rohteil.Base).Length > 1e-9 or not (
                alt_rohteil.Rotation.isSame(neu_rohteil.Rotation, 1e-9)
            ):
                rohteil.Placement = neu_rohteil
                self.doc.recompute()
        alt = klon.Placement
        if (alt.Base - neu.Base).Length < 1e-9 and alt.Rotation.isSame(neu.Rotation, 1e-9):
            return
        klon.Placement = neu
        self.doc.recompute()
        if rohteil is not None and hasattr(rohteil, "ExtZpos"):
            kasten = klon.Shape.BoundBox
            rohteil.Placement = FreeCAD.Placement(
                FreeCAD.Vector(kasten.XMin, kasten.YMin, kasten.ZMin), FreeCAD.Rotation()
            )
            self.doc.recompute()

    def _job_zeigen(self):
        """Anzeige des neuen Jobs wie bei FreeCADs Befehl „Job“ – aber in unserer Transaktion.
        Der Klon ist das Teil im Job, das Original verschwindet solange."""
        import Path.Main.Gui.Job as PathJobGui

        ansicht = self.job.ViewObject
        if ansicht is not None and getattr(ansicht, "Proxy", None) is None:
            ansicht.Proxy = PathJobGui.ViewProvider(ansicht)
            ansicht.addExtension("Gui::ViewProviderGroupExtensionPython")
        klon = vr.modell(self.job)
        if klon.ViewObject is not None:
            klon.ViewObject.Transparency = 0
            if self._ist_stl():
                from .gui_stl import ohne_kanten

                ohne_kanten(klon)
            stl_anzeige.zeigen(klon, True)  # ein Teil aus einem STL als Netz
        if self.teil.ViewObject is not None:
            self._sichtbar_vorher = (self.teil, stl_anzeige.sichtbar(self.teil))
            stl_anzeige.zeigen(self.teil, False)

    def _sichtbarkeit_zurueck(self):
        self._rohteil_original_zeigen(None)
        if self._sichtbar_vorher is None:
            return
        teil, sichtbar = self._sichtbar_vorher
        self._sichtbar_vorher = None
        try:
            if teil.ViewObject is not None:
                stl_anzeige.zeigen(teil, sichtbar)
        except (ReferenceError, RuntimeError):
            pass

    def _aufspannung_zeigen(self):
        """Maschine, Rohteil, Nullpunkt und Lage, wie sie im Job stehen – nur zum Lesen: beim
        Ändern einer Operation und bei einem weiteren Lauf am selben Job (W-012 M2)."""
        rohteil = getattr(self.job, "Stock", None)
        self._fuellt = True
        try:
            original = (getattr(rohteil, "Objects", None) or [None])[0]
            if original is not None:  # ein Körper aus dem Dokument (W-011 S4)
                self.wahl_rohteil.addItem(original.Label, original.Name)
                self.knopf_rohteil_teil.setChecked(True)
                self.rohteil_koerper.setVisible(True)
                self.rohteilfelder.setVisible(False)
            elif rohteil is not None and hasattr(rohteil, "Radius") and hasattr(rohteil, "Height"):
                self.knopf_rohteil_zylinder.setChecked(True)  # ein runder Rohling (W-021)
                self._zylinder_felder(rohteil)
            masse_text = getattr(self.job, ROHTEIL_MASSE, "") if self.job is not None else ""
            if masse_text and original is None:  # ein Quader mit Maßen (W-028)
                teile = masse_text.split(";")
                self.knopf_rohteil_masse.setChecked(True)
                for feld, wert in zip(("x", "y", "z"), teile[:3], strict=False):
                    self.felder_masse[feld].setText(
                        groesse_zeigen(float(wert), einheiten.LAENGE) or "0"
                    )
                if len(teile) >= 5:
                    self.wahl_masse_lage.setCurrentIndex(
                        max(self.wahl_masse_lage.findData(teile[3]), 0)
                    )
                    self.felder_masse["aufmass"].setText(
                        groesse_zeigen(float(teile[4]), einheiten.LAENGE) or "0"
                    )
                self.rohteilmasse.setVisible(True)
                self.rohteilfelder.setVisible(False)
            for knopf_art in (
                self.knopf_rohteil_quader,
                self.knopf_rohteil_masse,
                self.knopf_rohteil_zylinder,
                self.knopf_rohteil_teil,
            ):
                knopf_art.setEnabled(False)
            self.wahl_rohteil.setEnabled(False)
            if rohteil is not None and hasattr(rohteil, "ExtZpos"):
                for feld, name in (("oben", "ExtZpos"), ("seite", "ExtXpos"), ("unten", "ExtZneg")):
                    wert = _mm(getattr(rohteil, name))
                    self.felder_rohteil[feld].setText(groesse_zeigen(wert, einheiten.LAENGE) or "0")
            tiefe = spannung.gespannt(self.job)
            self.felder_spannung["gespannt"].setText(
                groesse_zeigen(tiefe, einheiten.LAENGE) if tiefe > 0 else ""
            )
        finally:
            self._fuellt = False
        self.rohteilfelder.setEnabled(False)
        self.rohteilmasse.setEnabled(False)
        # Die des Jobs – sie bleibt, wie sie im Job steht (ohne: „keine“).
        self._maschinen_fuellen(getattr(self.job, rw.EIGENSCHAFT_MASCHINE, ""))
        self.wahl_maschine.setEnabled(False)
        self.knopf_maschinen.setEnabled(False)
        for widget in (self.nullpunkt_titel, self.nullpunkt_text, self.nullpunktfelder):
            widget.setVisible(False)  # der Nullpunkt bleibt, wie er im Job steht
        # Wie das Teil liegt, bleibt ebenso.
        self.unten_text.setText(tr("ba.lage.job"))
        self.x_text.setText(tr("ba.lage.job"))
        for widget in (
            self.knopf_unten_waehlen,
            self.knopf_unten_modell,
            self.knopf_x_links,
            self.knopf_x_rechts,
        ):
            widget.setEnabled(False)

    def _zum_aendern(self):
        """Mit den Werten der Operation: Teil und Rohteil wie im Job (nicht änderbar), Flächen,
        ihr Block mit Fräser, Einsatz, Werten – die anderen Blöcke bleiben weg; „Übernehmen“
        statt „Anlegen“."""
        op = self.zu_aendern
        self.job = job_von(op)
        if self.job is None:
            return
        block = next((b for b in self.bloecke if b.s.ist(op)), None)
        if block is None:
            return
        self.block_zu_aendern = block
        block.tc_vorher = op.ToolController
        self.teil = vr.original(vr.modell(self.job))
        self.teil_text.setText(self.teil.Label)
        self.anleitung.setText(tr("ba.aendern.text", name=op.Label))
        self._aufspannung_zeigen()
        self._fuellt = True
        try:
            for anderer in self.bloecke:
                if anderer is not block:
                    anderer.widget.setVisible(False)
                    anderer.haken.setChecked(False)
            block.haken.setChecked(True)
            block.haken.setEnabled(False)
            block.von_hand = True
        finally:
            self._fuellt = False
        for b in self.bloecke:
            b.zustand_zeigen()
        namen = list(getattr(op, "Flaechen", ()) or ())
        self.gewaehlte = [n for n in namen if not n.startswith("Edge")]
        self.kanten = [n for n in namen if n.startswith("Edge")]
        self._bearbeitung_fuellen()
        self._fuellt = True
        try:
            werte_der_op = dict(block.s.werte_von(op))
            if "aufloesung" in block.felder:
                werte_der_op["aufloesung"] = au.wert(op, 0.0)
            for feld, wert in werte_der_op.items():
                if feld == "eintauchen_bei":  # die Eintauchstellen der Nut (W-012 E1)
                    block.eintauchen = dict(wert)
                    continue
                if feld in block.haken_felder:
                    block.haken_felder[feld].setChecked(bool(wert))
                    continue
                wert = float(wert)
                if abs(wert - block.vorschlag(feld)) > 1e-6:
                    block.felder[feld].setText(groesse_zeigen(wert, einheiten.LAENGE) or "0")
            if block is self.raeumen:
                block.raeumwahl_von(op)
        finally:
            self._fuellt = False
        self._flaechen_zeigen()
        self._auffrischen()
        self.vorschau_starten()

    # --- Flächen --------------------------------------------------------------------------

    def kante_umschalten(self, name):
        """Nimmt die Kante `name` („Edge12“) dazu – oder heraus, wenn sie schon gewählt ist. Mit
        Kanten arbeitet nur „Entgraten 3D“."""
        if not name or self.job is None:
            return
        if name in self.kanten:
            self.kanten.remove(name)
        else:
            self.kanten.append(name)
        self._flaechen_zeigen()
        self.vorschau_starten()

    def _wahl(self, block):
        """Was der Block bekommt: die gewählten Flächen – „Entgraten 3D“ dazu die Kanten."""
        if self._ist_stl() and block.s.kennung not in FREIFORM_STRATEGIEN:
            return []  # ein Teil aus einem STL: nur Freiform (W-017)
        gewaehlte, kanten = self.gewaehlte, self.kanten
        if self.job is not None and (gewaehlte or kanten):
            # Die schrägen Flächen kommen in einer eigenen Ebene oder Aufspannung dran – an einer
            # Maschine mit waagerechter Spindel auch der Rest samt Kanten (Ebene „von oben“).
            weg = set(self._geschwenkt(vr.modell(self.job).Shape))
            if weg:
                gewaehlte = [n for n in gewaehlte if n not in weg]
                kanten = [k for k in kanten if k not in weg]
        fase = getattr(self, "fase", None)
        if (
            block.s.kennung in FREIFORM_STRATEGIEN
            and gewaehlte
            and fase is not None
            and fase._fraeser
            and self.job is not None
            and not self._ist_stl()
        ):
            # Fasen fräst der Block „Fase“ (W-037) – 3D nicht noch einmal (am Messspitzenhalter
            # standen 3D-Schruppen und -Schlichten mit Ø 12 rot an der Fase).
            form = vr.modell(self.job).Shape
            gewaehlte = [n for n in gewaehlte if not _fase_fuer_block(form, n)]
        if getattr(block.s, "nimmt_kanten", False):
            return list(gewaehlte) + list(kanten)
        return gewaehlte

    def _schraege(self, form):
        """Die gewählten schrägen ebenen Flächen, die „Anlegen“ woanders hinbringt: an einer
        5-Achs-Fräse in eine eigene Ebene (die Maschine schwenkt), an einer 3-Achs-Fräse in eine
        gekippte Aufspannung (_geschwenkt: nur mit dem Haken). Nicht gezeichnete Fasen (die
        macht das Entgraten), an der 5-Achs-Fräse nicht die schrägen Wände der Flanke; beim
        Ändern einer Operation keine. Manuel, 2026-10-16: „das soll doch in der bearbeitung
        anhand des rohteils … ausgerechnet werden das man das schwenken muss“."""
        if self.job is None or self.zu_aendern is not None or not self.gewaehlte:
            return []
        if self._ist_stl():
            return []
        fuenf = self._fuenfachs()
        # Die Lage gehört dazu: „unten“ oder „um Z gedreht“ macht aus einer schrägen Fläche eine
        # waagerechte und umgekehrt.
        schluessel = (id(self.job), tuple(self.gewaehlte), fuenf, _lage_von(form))
        merk = getattr(self, "_schraege_merk", None)
        if merk is not None and merk[0] == schluessel:
            return list(merk[1])
        namen = [
            n for n in self.gewaehlte if _schraeg(form, n) is not None and not _kleine_fase(form, n)
        ]
        if fuenf:
            namen = [n for n in namen if not self.flanke.s.passt(form, n)]
        self._schraege_merk = (schluessel, namen)
        return list(namen)

    def _geschwenkt(self, form):
        """Die gewählten Flächen, die nach „Anlegen“ woanders drankommen (_schraege_gruppen) – an
        der 3-Achs-Fräse nur mit „Bahnen dafür anlegen und im Einrichtblatt notieren“."""
        if not self._schraege(form) and not self._spindel_quer():
            return []
        if not self._fuenfachs() and not self.gekippt_haken.isChecked():
            return []
        return [name for r in self._schraege_gruppen(form) for name in r.flaechen]

    def _unter_dem_rand_an(self):
        """Ist im 3D-Schlichten „Unter dem Rand“ angehakt?"""
        kasten = getattr(self, "schlichten3d", None)
        kasten = kasten.haken_felder.get("hinterschnitt") if kasten is not None else None
        return kasten is not None and kasten.isChecked()

    def _schraege_gruppen(self, form):
        """[zugang.Richtung] – die schrägen Flächen (_schraege) je Richtung, die flachste zuerst,
        mit den Wänden ihrer Tasche: Eine gewählte Fläche, die an eine Fläche der Richtung grenzt
        und quer zu ihr steht (eben mit der Normalen senkrecht zur Richtung, ein Zylinder mit
        der Achse längs – eine Ecke), ist eine Wand dort, auch wenn sie im Grundjob senkrecht
        steht. Sonst bekäme jede schräge Wand der Tasche in der Schräge ihre eigene Ebene, und
        die senkrechten blieben im Grundjob (wie zugang: die Wand geht zu ihrer Tasche)."""
        schraege = self._schraege(form)
        # Nicht „quer“: So heißt unten die Prüfung einer Wand (eine Funktion – immer wahr).
        waagerecht = self._spindel_quer()
        if not schraege and not waagerecht:
            return []
        schluessel = (
            id(self.job),
            tuple(self.gewaehlte),
            tuple(self.kanten),
            tuple(schraege),
            waagerecht,
            _lage_von(form),
            self._unter_dem_rand_an(),
        )
        merk = getattr(self, "_gruppen_merk", None)
        if merk is not None and merk[0] == schluessel:
            return [zg.Richtung(r.achse, list(r.flaechen), r.stellung, r.stirn) for r in merk[1]]
        kanten = {}
        for name in self.gewaehlte:
            nummer = int(name[4:]) - 1 if name.startswith("Face") and name[4:].isdigit() else -1
            if 0 <= nummer < ft.anzahl(form):
                kanten[name] = {k.hashCode() for k in ft.flaeche(form, nummer).Edges}

        def grenzt(name, r):
            return any(kanten.get(name, set()) & kanten.get(f, set()) for f in r.flaechen)

        def quer(name, r):
            achse = FreeCAD.Vector(*r.achse)
            nummer = int(name[4:]) - 1
            flaeche = ft.flaeche(form, nummer)
            if type(flaeche.Surface).__name__ == "Cylinder":
                return abs(abs(FreeCAD.Vector(flaeche.Surface.Axis).dot(achse)) - 1.0) < 1e-6
            n = _aussennormale(form, name)
            return n is not None and abs(n.dot(achse)) < 1e-6

        def darueber(name, r):
            """Steht die Wand über einer ebenen Fläche der Richtung, an die sie grenzt (dem Boden
            einer Tasche darin) – nicht nur darunter wie die Seiten eines Keils unter der Schräge,
            die zum Grundjob gehören? Grenzt sie an keine (eine Ecke zwischen zwei Wänden), gilt
            sie wie diese. Gegen jede angrenzende, nicht gegen die erste Fläche: Sind Boden und
            Schräge darüber gewählt, steht die Wand unter der Schräge, aber über dem Boden."""
            achse = FreeCAD.Vector(*r.achse)
            try:
                mitte = ft.flaeche(form, int(name[4:]) - 1).CenterOfMass
            except Exception:  # noqa: BLE001
                return False
            eben = []
            for f in r.flaechen:
                n = _aussennormale(form, f)
                if n is None or (n - achse).Length >= zg.GLEICH:
                    continue
                if kanten.get(name, set()) & kanten.get(f, set()):
                    eben.append(f)
            if not eben:
                return True
            for f in eben:
                try:
                    unten = ft.flaeche(form, int(f[4:]) - 1).CenterOfMass
                except Exception:  # noqa: BLE001
                    continue
                if (mitte - unten).dot(achse) > 1e-6:
                    return True
            return False

        def wand_von(name):
            return next(
                (r for r in richtungen if quer(name, r) and grenzt(name, r) and darueber(name, r)),
                None,
            )

        richtungen = []
        for name in sorted(schraege, key=lambda n: _schraeg(form, n)):
            n = _aussennormale(form, name)
            if n is None:
                continue
            gleich = next(
                (r for r in richtungen if (FreeCAD.Vector(*r.achse) - n).Length < zg.GLEICH),
                None,
            )
            wand = wand_von(name)
            if gleich is not None:
                gleich.flaechen.append(name)
            elif wand is not None:
                wand.flaechen.append(name)
            else:
                richtungen.append(zg.Richtung(achse=(n.x, n.y, n.z), flaechen=[name], stirn=name))
        # Die übrigen gewählten Wände und Ecken der Taschen dazu – reihum, eine Ecke grenzt oft
        # nur an Wände.
        uebrig = [n for n in self.gewaehlte if n not in schraege and n in kanten]
        weiter = True
        while weiter:
            weiter = False
            for name in list(uebrig):
                r = wand_von(name)
                if r is not None:
                    r.flaechen.append(name)
                    uebrig.remove(name)
                    weiter = True
        if waagerecht:
            # Die Spindel steht waagerecht: Auch was von oben gefräst wird, kommt in eine Ebene –
            # ohne die Flächen der Flanke (die schwenkt simultan) und mit den Kanten.
            fuenf = self._fuenfachs()  # die Flanke gibt es nur an der 5-Achs-Fräse
            # Ebenso die Flächen unter dem Rand, wenn die Kugel sie gekippt schlichtet.
            unter = s3op.hb.ueberdeckte(form, uebrig) if fuenf and self._unter_dem_rand_an() else ()
            oben = [
                n for n in uebrig if not (fuenf and (self.flanke.s.passt(form, n) or n in unter))
            ]
            oben += list(self.kanten)
            if not self.gewaehlte and not self.kanten:
                oben = hf.oberseite(form)  # nichts angeklickt: die Oberseite, wie die Blöcke
            if oben:
                richtungen.insert(0, zg.Richtung(achse=(0.0, 0.0, 1.0), flaechen=oben))
        self._gruppen_merk = (schluessel, richtungen)
        return [zg.Richtung(r.achse, list(r.flaechen), r.stellung, r.stirn) for r in richtungen]

    def _nur_geschwenkt(self, form):
        """Kommen alle gewählten Flächen woanders dran? Dann legt „Anlegen“ hier nichts an. Ohne
        Wahl nur an einer Maschine mit waagerechter Spindel: Die Oberseite kommt in die Ebene
        „von oben“ (_schraege_gruppen)."""
        if not self.gewaehlte and not self.kanten:
            return self._spindel_quer() and bool(self._geschwenkt(form))
        dort = set(self._geschwenkt(form))
        return set(self.gewaehlte) <= dort and set(self.kanten) <= dort

    def _schraege_richtungen(self, form):
        """[zugang.Richtung] der Flächen aus _geschwenkt (_schraege_gruppen) – ihre erste Fläche
        die Stirn; leer, wenn sie hier nicht woanders hingehen."""
        return self._schraege_gruppen(form) if self._geschwenkt(form) else []

    def _gekippt_umgeschaltet(self):
        self._flaechen_zeigen()
        self.vorschau_starten()

    def _ist_stl(self):
        """Ist das Teil im Job ein Körper aus einem STL (stl_teil.daten – je Form gemerkt)? Dann
        ist jedes Dreieck eine Fläche, und der Assistent fragt nicht Fläche für Fläche nach Nut,
        Bohrung, Wand … (P-2026-10-11-103)."""
        if self.job is None:
            return False
        from . import stl_teil

        return stl_teil.daten(vr.modell(self.job).Shape) is not None

    def flaeche_umschalten(self, name):
        """Nimmt die Fläche `name` („Face6“) dazu – oder heraus, wenn sie schon gewählt ist; eine
        Kante („Edge12“) wie kante_umschalten."""
        if name and str(name).startswith("Edge"):
            self.kante_umschalten(name)
            return
        if not name or self.job is None:
            return
        if name in self.gewaehlte:
            self.gewaehlte.remove(name)
            self._gleiche_anbieten(None)
        else:
            self.gewaehlte.append(name)
            self._gleiche_anbieten(name)
        self._flaechen_zeigen()
        self.vorschau_starten()

    def _gleiche_anbieten(self, name):
        """Der Knopf „Alle N gleichen … dazu“ nach einem Klick auf `name` – wenn das Teil weitere
        Flächen derselben Art, desselben Maßes auf derselben Höhe hat (gleiche_flaechen), die
        noch nicht gewählt sind. None: weg."""
        self._gleiche = []
        self.gleiche_knopf.hide()
        if name is None or self.job is None or self._ist_stl():
            return
        art, andere = glf.gleiche(vr.modell(self.job).Shape, name)
        weitere = [n for n in andere if n not in self.gewaehlte]
        if art is None or not weitere:
            return
        von = groesse_zeigen(art.unten, einheiten.LAENGE, 2) or "0"
        bis = groesse_zeigen(art.oben, einheiten.LAENGE, 2) or "0"
        mass = groesse_zeigen(art.mass, einheiten.LAENGE, 2) or "0"
        anzahl = len(weitere)
        if art.art == glf.RUNDUNG:
            text = tr("ba.gleiche.rundung", anzahl=anzahl, radius=mass, von=von, bis=bis)
        elif art.art == glf.ECKRADIUS:
            text = tr("ba.gleiche.eckradius", anzahl=anzahl, radius=mass, von=von, bis=bis)
        elif art.art == glf.FASE:
            winkel = zahl_zeigen(round(art.mass, 1)) or "0"
            text = tr("ba.gleiche.fase", anzahl=anzahl, winkel=winkel, von=von, bis=bis)
        else:
            text = tr("ba.gleiche.boden", anzahl=anzahl, hoehe=bis)
        self._gleiche = weitere
        self.gleiche_knopf.setText(text)
        self.gleiche_knopf.show()

    def gleiche_dazu(self):
        """Nimmt die gleichen Flächen (_gleiche_anbieten) alle dazu."""
        neue = [n for n in self._gleiche if n not in self.gewaehlte]
        self._gleiche_anbieten(None)
        if not neue or self.job is None:
            return
        self.gewaehlte.extend(neue)
        self._flaechen_zeigen()
        self.vorschau_starten()

    def oberseite_waehlen(self):
        if self.job is None:
            return
        self._gleiche_anbieten(None)
        self._zugang = None
        self.gewaehlte = hf.oberseite(vr.modell(self.job).Shape)
        self._flaechen_zeigen()
        self.vorschau_starten()

    def aus_der_aufspannung(self):
        """„Alles aus dieser Aufspannung“ (Frage 14; Manuel, 2026-10-11: „ich gebe eine Fläche an,
        die in dem Spannmittel ist .. und dann wird bearbeitet“): jede Fläche, die in dieser
        Aufspannung erreichbar ist, nach Richtung (zugang) – die von oben gewählt; die anderen je
        Richtung eine Zeile in ihrer Farbe mit „Ebene schwenken …“; was nicht geht, rot mit Grund.
        Ohne 5-Achs-Maschine nur von oben."""
        if self.job is None:
            return
        form = vr.modell(self.job).Shape
        spann = self._unten or zg.spannflaeche_unten(form)
        ergebnis = zg.zugang(form, spannflaeche=spann)
        if not self._fuenfachs():
            ergebnis = zg.ohne_schwenken(ergebnis)
        from . import n_eck as ne

        if ne.ist_n_eck(self.job):
            # Die N-Eck-Stange (W-018): Was hier nicht von oben geht, kommt in einer anderen
            # Aufspannung dran – nicht „die Maschine schwenkt nicht so weit“ oder „ins Spannmittel“.
            anders = {tr("zg.grund.maschine"), tr("zg.grund.spannmittel")}
            neu = tr("zg.grund.aufspannung")
            ergebnis = zg.Zugang(
                ergebnis.richtungen,
                {k: neu if v in anders else v for k, v in ergebnis.unerreichbar.items()},
                ergebnis.spannflaeche,
            )
        self._zugang = ergebnis
        oben = ergebnis.richtungen[0] if ergebnis.richtungen else None
        oben = oben if oben is not None and oben.achse[2] > 1 - 1e-6 else None
        namen = list(oben.flaechen) if oben is not None else []
        if self._ist_stl():  # die Freiform-Dreiecke alle auf einmal
            self.gewaehlte = s3b.freiformflaechen(form, namen)
        else:
            # Keine ebene Fläche nach oben, über der kein Rohteil steht (wand_ohne_rohteil): die
            # Stirn mit Planaufmaß 0 – sonst stand an Manuels Messspitzenhalter (2026-10-23) das
            # Planfräsen mit „steht nichts“ da, und „Anlegen“ ging nicht. Wände bleiben: An ihnen
            # hängt das Räumen bis durch (der Mantel im Rundmaterial, W-034).
            gewaehlte = [
                n
                for n in namen
                if self._nimmt_eine(form, n)
                and not (hf.ebenen_oben(form, [n]) and self._ohne_rohteil(form, n))
            ]
            # Fasen nur angeklickt (Manuel, 2026-10-24, Frage 1: „wenn sie angeklickt ist … wenn
            # nicht wird sie nicht gemacht“) – die Zeile unter der Liste bietet sie an.
            self._ohne_fasen = [n for n in gewaehlte if _fase_fuer_block(form, n)]
            self.gewaehlte = [n for n in gewaehlte if n not in self._ohne_fasen]
        self.kanten = []
        self._flaechen_zeigen()
        self.vorschau_starten()

    def _richtungen_zeigen(self, farben):
        """Die Zeilen unter der Liste (aus_der_aufspannung) und die Farben der Flächen anderer
        Richtungen und der unerreichbaren in `farben` ({Nummer: Farbe}) – gewählte behalten
        ihre."""
        while self._richtungen_aufbau.count():
            widget = self._richtungen_aufbau.takeAt(0).widget()
            if widget is not None:
                widget.deleteLater()
        z = self._zugang
        if z is None:
            self.richtungen_box.hide()
            return
        weitere = [r for r in z.richtungen if r.achse[2] <= 1 - 1e-6]
        gewaehlt = set(self.gewaehlte)  # ein STL hat 68.242 Flächen: nicht je Name die Liste
        for i, r in enumerate(weitere):
            farbe = RICHTUNG_FARBEN[i % len(RICHTUNG_FARBEN)]
            for name in r.flaechen:
                if name not in gewaehlt:
                    farben[int(name[4:]) - 1] = farbe
            zeile = QtGui.QWidget()
            aufbau = QtGui.QHBoxLayout(zeile)
            aufbau.setContentsMargins(0, 0, 0, 0)
            text = QtGui.QLabel(
                dezimal(
                    tr(
                        "ba.richtung.zeile",
                        winkel=f"{r.neigung:.0f}",
                        anzahl=len(r.flaechen),
                        namen=_namen_kurz(r.flaechen),
                    )
                )
            )
            text.setWordWrap(True)
            text.setStyleSheet(f"color: {farbe};")
            aufbau.addWidget(text, 1)
            # Kein Knopf „Ebene schwenken (3+2) …“ mehr je Zeile: „Anlegen“ legt die Ebenen selbst
            # an (Manuel, 2026-10-16: „ich weis nicht für was das da sein soll“).
            self._richtungen_aufbau.addWidget(zeile)
        gruende = {}
        for name, grund in z.unerreichbar.items():
            gruende.setdefault(grund, []).append(name)
            if name not in gewaehlt:
                farben[int(name[4:]) - 1] = ROT
        for grund, namen in gruende.items():
            text = QtGui.QLabel(
                tr("ba.richtung.unerreichbar", namen=_namen_kurz(namen), grund=grund)
            )
            text.setWordWrap(True)
            text.setStyleSheet(f"color: {ROT};")
            self._richtungen_aufbau.addWidget(text)
        if weitere and self._fuenfachs():
            self._richtungen_aufbau.addWidget(_grau(tr("ba.richtung.danach")))
        fasen = [n for n in getattr(self, "_ohne_fasen", []) if n not in gewaehlt]
        if fasen:
            zeile = QtGui.QWidget()
            aufbau = QtGui.QVBoxLayout(zeile)
            aufbau.setContentsMargins(0, 0, 0, 0)
            aufbau.addWidget(_grau(tr("ba.alles.ohne_fasen", namen=_namen_kurz(fasen))))
            aufbau.addWidget(
                knopf(tr("ba.alles.fasen_dazu"), "", self.fasen_dazu), 0, QtCore.Qt.AlignLeft
            )
            self._richtungen_aufbau.addWidget(zeile)
        self.richtungen_box.setVisible(bool(weitere or gruende or fasen))

    def fasen_dazu(self):
        """„Fasen dazu“: die Fasen, die „Alles aus dieser Aufspannung“ ausließ, in die Wahl."""
        dazu = [n for n in getattr(self, "_ohne_fasen", []) if n not in self.gewaehlte]
        if not dazu:
            return
        self.gewaehlte = list(self.gewaehlte) + dazu
        self._flaechen_zeigen()
        self.vorschau_starten()

    def flaechen_leeren(self):
        self._gleiche_anbieten(None)
        self._zugang = None
        self._ohne_fasen = []
        self.gewaehlte = []
        self.kanten = []
        self._flaechen_zeigen()
        self.vorschau_starten()

    def flaechen(self):
        """Die gewählten Flächen („Face6“ …) – leer: die Oberseite."""
        return list(self.gewaehlte)

    def _flaechen_zeigen(self):
        """Die Liste der gewählten Flächen, der Satz darunter, die Farben am Teil – und die
        Haken der Blöcke, wie die Wahl sie nahelegt."""
        self.flaechen_liste.clear()
        self.flaechen_liste.setVisible(bool(self.gewaehlte or self.kanten))
        self.schwenken_zeile.hide()
        if self.job is None:
            self.flaechen_text.setText("")
            return
        form = vr.modell(self.job).Shape
        if self._ist_stl():
            self._flaechen_zeigen_stl(form)
            return
        farben = {}
        geschwenkt = set(self._geschwenkt(form))
        neigung_von = {
            f: r.neigung
            for r in (self._schraege_gruppen(form) if geschwenkt else [])
            for f in r.flaechen
        }
        for name in self.gewaehlte:
            nummer = int(name[4:]) - 1 if name.startswith("Face") and name[4:].isdigit() else -1
            if nummer < 0 or nummer >= ft.anzahl(form):
                text, farbe = tr("ba.flaeche.fehlt", name=name), ROT
            elif name in geschwenkt:
                winkel = f"{neigung_von.get(name, 0.0):.0f}"  # die der Ebene, auch für ihre Wände
                if neigung_von.get(name, 0.0) < 0.5:  # von oben, die Spindel steht waagerecht
                    text = tr("ba.flaeche.spindel_quer", name=name)
                elif self._fuenfachs():
                    text = tr("ba.flaeche.geschwenkt", name=name, winkel=winkel)
                else:
                    text = tr("ba.flaeche.gekippt", name=name, winkel=winkel)
                farbe = GRUEN
            elif self.fase.s.passt(form, name):
                fase = fb.fasen(form, [name])[0]
                text = tr(
                    "ba.flaeche.fase_mass",
                    name=name,
                    winkel=f"{90.0 - fase.winkel:.0f}",
                    breite=groesse_zeigen(fase.breite, einheiten.LAENGE, 2) or "0",
                    z=groesse_zeigen(fase.z_unten, einheiten.LAENGE, 2) or "0",
                )
                farbe = GRUEN
            elif self.nut.s.passt(form, name):
                n = nb.nuten(form, [name])[0]
                breite = groesse_zeigen(2 * n.radius, einheiten.LAENGE, 2) or "0"
                laenge = groesse_zeigen(n.gesamtlaenge, einheiten.LAENGE, 2) or "0"
                if n.ring:
                    z = groesse_zeigen(n.z_unten, einheiten.LAENGE, 2) or "0"
                    innen = groesse_zeigen(2 * (n.bogen[2] - n.radius), einheiten.LAENGE, 2) or "0"
                    aussen = groesse_zeigen(2 * (n.bogen[2] + n.radius), einheiten.LAENGE, 2) or "0"
                    text = tr(
                        "ba.flaeche.ringnut",
                        name=name,
                        breite=breite,
                        innen=innen,
                        aussen=aussen,
                        z=z,
                    )
                elif n.offen:
                    z = groesse_zeigen(n.z_unten, einheiten.LAENGE, 2) or "0"
                    text = tr("ba.flaeche.nut_offen", name=name, breite=breite, laenge=laenge, z=z)
                elif n.durch:
                    text = tr("ba.flaeche.nut_durch", name=name, breite=breite, laenge=laenge)
                else:
                    z = groesse_zeigen(n.z_unten, einheiten.LAENGE, 2) or "0"
                    text = tr("ba.flaeche.nut_grund", name=name, breite=breite, laenge=laenge, z=z)
                farbe = GRUEN
            elif self.plan.s.passt(form, name):
                z = groesse_zeigen(hf.ebenen_oben(form, [name])[0].z, einheiten.LAENGE, 2) or "0"
                text, farbe = tr("ba.flaeche.eben", name=name, z=z), GRUEN
            elif self.bohrung.s.passt(form, name):
                b = bb.bohrungen(form, [bb.bohrung_ueber_boden(form, name) or name])[0]
                d = groesse_zeigen(2 * b.radius, einheiten.LAENGE, 2) or "0"
                if b.durch:
                    text = tr("ba.flaeche.bohrung_durch", name=name, d=d)
                elif b.spitze > 0:
                    z = groesse_zeigen(b.z_unten, einheiten.LAENGE, 2) or "0"
                    text = tr(
                        "ba.flaeche.bohrung_spitze", name=name, d=d, z=z, winkel=f"{b.spitze:.0f}"
                    )
                else:
                    z = groesse_zeigen(b.z_unten, einheiten.LAENGE, 2) or "0"
                    text = tr("ba.flaeche.bohrung_sack", name=name, d=d, z=z)
                farbe = GRUEN
            elif self.kontur.s.passt(form, name):
                z = groesse_zeigen(kb.waende(form, [name])[0].z_unten, einheiten.LAENGE, 2) or "0"
                text, farbe = tr("ba.flaeche.wand", name=name, z=z), GRUEN
            elif self.senken.s.passt(form, name):
                senkung = sk.senkungen(form, [name])[0]
                d = groesse_zeigen(senkung.durchmesser, einheiten.LAENGE, 2) or "0"
                winkel = f"{round(senkung.winkel, 1):g}"
                text, farbe = tr("ba.flaeche.senkung", name=name, d=d, winkel=winkel), GRUEN
            elif self._fuenfachs() and self.flanke.s.passt(form, name):
                z = (
                    groesse_zeigen(ft.flaeche(form, nummer).BoundBox.ZMin, einheiten.LAENGE, 2)
                    or "0"
                )
                text, farbe = tr("ba.flaeche.flanke", name=name, z=z), GRUEN
            elif self.schlichten3d.s.passt(form, name):
                z = (
                    groesse_zeigen(ft.flaeche(form, nummer).BoundBox.ZMin, einheiten.LAENGE, 2)
                    or "0"
                )
                text, farbe = tr("ba.flaeche.freiform", name=name, z=z), GRUEN
            elif eb.ist_fase(form, name):
                text, farbe = tr("ba.flaeche.fase", name=name), GRUEN
            elif _schraeg(form, name) is not None:
                winkel = f"{_schraeg(form, name):.0f}"
                text, farbe = tr("ba.flaeche.schraeg", name=name, winkel=winkel), ROT
            elif hf.ebenen_oben(form, [name]):
                # Der Boden einer Tasche, einer Nut oder eines Absatzes: Das Planfräsen nimmt ihn
                # nicht (es bringt nur rundum offene Flächen auf Maß), das Räumen schon.
                z = groesse_zeigen(hf.ebenen_oben(form, [name])[0].z, einheiten.LAENGE, 2) or "0"
                if hf.eingeschlossen(form, name):
                    text = tr("ba.flaeche.boden", name=name, z=z)
                else:
                    text = tr("ba.flaeche.absatz", name=name, z=z)
                farbe = GRUEN
            else:
                text, farbe = tr("ba.flaeche.nichts", name=name), ROT
            eintrag = QtGui.QListWidgetItem(dezimal(text))
            eintrag.setData(QtCore.Qt.UserRole, name)
            eintrag.setForeground(QtGui.QColor(farbe))
            self.flaechen_liste.addItem(eintrag)
            if nummer >= 0:
                farben[nummer] = farbe
        kanten_farben = {}
        for name in self.kanten:
            nummer = int(name[4:]) - 1 if name[4:].isdigit() else -1
            if 0 <= nummer < form.countElement("Edge") and self.entgraten3d.s.passt(form, name):
                laenge = groesse_zeigen(form.Edges[nummer].Length, einheiten.LAENGE, 2) or "0"
                text, farbe = tr("ba.kante.fase", name=name, laenge=laenge), GRUEN
            else:
                text, farbe = tr("ba.kante.nichts", name=name), ROT
            eintrag = QtGui.QListWidgetItem(dezimal(text))
            eintrag.setData(QtCore.Qt.UserRole, name)
            eintrag.setForeground(QtGui.QColor(farbe))
            self.flaechen_liste.addItem(eintrag)
            if nummer >= 0:
                kanten_farben[nummer] = farbe
        # Die Liste so hoch wie ihre Einträge – höchstens fünf, dann rollt sie.
        zeile = max(self.flaechen_liste.sizeHintForRow(0), 1)
        rand = 2 * self.flaechen_liste.frameWidth() + 4
        self.flaechen_liste.setFixedHeight(
            min(5, max(1, self.flaechen_liste.count())) * zeile + rand
        )
        if not self.gewaehlte and self.kanten:
            self.flaechen_text.setText(tr("ba.flaechen.nur_kanten"))
        elif not self.gewaehlte:
            namen = ", ".join(hf.oberseite(form)) or "–"
            self.flaechen_text.setText(tr("ba.flaechen.oberseite", namen=namen))
        else:
            self.flaechen_text.setText(tr("ba.flaechen.nur"))
        self._schwenken_zeigen(form)
        self._richtungen_zeigen(farben)
        self._farben_zeigen(farben, kanten_farben)
        self._haken_vorschlagen(form)

    def _flaechen_zeigen_stl(self, form):
        """_flaechen_zeigen() für ein Teil aus einem STL: statt einer Zeile je Dreieck zwei – wie
        viele Freiform sind (3D-Schruppen, 3D-Schlichten) und wie viele keine Strategie hat (eben
        nach oben, senkrecht oder nach unten gewandt); die Farben am Teil wie sonst."""
        from . import stl_teil

        daten = stl_teil.daten(form)
        nummern = daten.nummern(self.gewaehlte)
        nz = daten.normale[nummern, 2]
        frei = (nz > s3b.NACH_OBEN) & (nz < 1.0 - hf.GERADE)
        farben = {int(n): GRUEN for n in nummern[frei]}
        farben.update({int(n): ROT for n in nummern[~frei]})
        anzahl = lambda n: f"{int(n):,}".replace(",", "\u202f")  # noqa: E731
        if frei.any():
            z = groesse_fest(float(daten.unten[nummern[frei], 2].min()), einheiten.LAENGE, 1)
            eintrag = QtGui.QListWidgetItem(
                dezimal(tr("ba.stl.freiform", anzahl=anzahl(frei.sum()), z=z or "0"))
            )
            eintrag.setForeground(QtGui.QColor(GRUEN))
            self.flaechen_liste.addItem(eintrag)
        if (~frei).any():
            eintrag = QtGui.QListWidgetItem(tr("ba.stl.ohne", anzahl=anzahl((~frei).sum())))
            eintrag.setForeground(QtGui.QColor(ROT))
            self.flaechen_liste.addItem(eintrag)
        zeile = max(self.flaechen_liste.sizeHintForRow(0), 1)
        rand = 2 * self.flaechen_liste.frameWidth() + 4
        self.flaechen_liste.setFixedHeight(max(1, self.flaechen_liste.count()) * zeile + rand)
        self.flaechen_text.setText(tr("ba.stl.text") if self.gewaehlte else tr("ba.stl.keine"))
        self._richtungen_zeigen(farben)
        self._farben_zeigen(farben, {})
        self._haken_vorschlagen(form)

    def _schwenken_zeigen(self, form):
        """Ist eine gewählte Fläche schräg (_schraege), die Zeile darunter: an einer 5-Achs-Fräse,
        dass „Anlegen“ die Ebene dafür anlegt und dort weitermacht; an einer 3-Achs-Fräse der
        Haken „Bahnen dafür anlegen und im Einrichtblatt notieren“ mit Winkel und Achse."""
        from . import schwenken as sw

        schraege = self._schraege(form)
        self.gekippt_haken.hide()
        if not schraege:
            if self._geschwenkt(form):  # von oben, die Spindel steht waagerecht
                self.schwenken_text.setText(tr("ba.schwenken.spindel_quer"))
                self.schwenken_zeile.show()
            return
        name = schraege[0]
        winkel = f"{_schraeg(form, name):.0f}"
        if self._fuenfachs():
            self.schwenken_text.setText(tr("ba.schwenken.automatisch", name=name, winkel=winkel))
        else:
            _neigung, achse = sw.kippung(_aussennormale(form, name))
            self.schwenken_text.setText(
                tr("ba.gekippt.text", name=name, winkel=winkel, achse=_achse_text(achse))
            )
            self.gekippt_haken.show()
        self.schwenken_zeile.show()

    def _haken_vorschlagen(self, form):
        """Je Block: möglich mit dieser Wahl? Dann der Haken, wie die Wahl ihn nahelegt –
        solange ihn niemand von Hand gesetzt hat."""
        if self.zu_aendern is not None:
            return
        stl = self._ist_stl()
        gerieben = False
        if (
            not stl
        ):  # ein Teil aus einem STL hat nur Freiform – die Werkzeuge dafür wählen die Blöcke
            self._reibahle_waehlen(form)
            gerieben = self._gerieben(form)
            self._bohrer_waehlen(form, gerieben)
            self._gewindebohrer_waehlen(form)
            self._gewindefraeser_waehlen(form)
            self._senker_waehlen(form)
            self._entgratfraeser_waehlen(form)
            self._nutfraeser_waehlen(form)
            self._planeinsatz_waehlen(form)
            self._flaechenfraeser_waehlen(form)
        nur_dort = None
        self._alles_dort = False
        if not stl and self._nur_geschwenkt(form):
            self._alles_dort = True
            # Alles Gewählte kommt in der Ebene (5 Achsen) bzw. gekippt gespannt dran.
            if self._fuenfachs() and not self._schraege(form):
                nur_dort = tr("ba.schwenken.alles_oben")
            elif self._fuenfachs():
                nur_dort = tr("ba.schwenken.alles_dort")
            else:
                nur_dort = tr("ba.gekippt.alles_dort")
        # Nur Kanten hier: keine Fläche gewählt – oder alle kommen woanders dran (geschwenkt,
        # gekippt gespannt); sonst schlügen Planfräsen und Räumen die ganze Oberseite vor.
        weg = set(self._geschwenkt(form)) if self.gewaehlte and not stl else set()
        nur_kanten = bool(self.kanten) and not [n for n in self.gewaehlte if n not in weg]
        fuenfachs = self._fuenfachs()
        # Steht die Spindel waagerecht (GROB G550), fräst der Grundjob nur simultan – sonst führe
        # die Maschine eine Bahn von oben mit der Spindel quer (P-2026-10-25-21: ein „3D-Schruppen“
        # im Grundjob ohne Schwenk). Was von oben gefräst wird, kommt in der Ebene dran.
        quer = not stl and self._spindel_quer() and bool(self.gewaehlte or self.kanten)
        self._fuellt = True
        try:
            for block in self.bloecke:
                if stl and block.s.kennung not in FREIFORM_STRATEGIEN:
                    block.moeglich = False
                    block.haken.setEnabled(False)
                    block.haken.setChecked(False)
                    block.erklaerung.setText(tr("ba.stl.nur_freiform"))
                    block.zustand_zeigen()
                    continue
                if nur_dort:
                    block.moeglich = False
                    block.haken.setEnabled(False)
                    block.haken.setChecked(False)
                    block.erklaerung.setText(nur_dort)
                    block.zustand_zeigen()
                    continue
                if quer and block.s.kennung not in SIMULTAN_IM_GRUNDJOB:
                    block.moeglich = False
                    block.haken.setEnabled(False)
                    block.haken.setChecked(False)
                    block.erklaerung.setText(tr("ba.waagerecht.nur_simultan"))
                    block.zustand_zeigen()
                    continue
                if block is self.flanke and not fuenfachs:
                    # Ohne 5-Achs-Maschine geht die Flanke nie – ihre Mantellinien je Fläche nicht
                    # erst rechnen (am Testteil 1,4 s, in denen das Fenster stand).
                    block.moeglich = False
                    block.haken.setEnabled(False)
                    block.haken.setChecked(False)
                    block.erklaerung.setText(tr("ba.fl.ohne_maschine"))
                    block.zustand_zeigen()
                    continue
                moeglich = block.s.moeglich(form, self._wahl(block))
                grund = None
                if block is self.bohren:
                    moeglich = moeglich and self._bohrer_da(form, gerieben)
                if block is self.reiben:
                    moeglich = moeglich and self._reibahle_da(form)
                if gerieben and block in (self.bohrung, self.kontur) and moeglich:
                    # Geriebene Bohrungen bohrt der Bohrer kleiner vor – gefräst wären sie auf
                    # Maß, die Reibahle hätte nichts zu tun.
                    geriebene = set(self.reiben.s.flaechen_fuer(form, self.gewaehlte))
                    eigene = set(block.s.flaechen_fuer(form, self.gewaehlte))
                    if eigene <= geriebene:
                        moeglich, grund = False, tr("ba.bohrung.gerieben")
                if block is self.gewinde:
                    moeglich = moeglich and self._gewindebohrer_da(form)
                if block is self.gewindefraesen:
                    moeglich = moeglich and self._gewindefraeser_da(form)
                if block in (self.entgraten, self.entgraten3d, self.zentrieren):
                    moeglich = moeglich and bool(block._fraeser)
                if block is self.senken:
                    moeglich = moeglich and self._senker_da(form)
                if block is self.schlichten_danach:
                    # Mit dem Räumen oder der Nut (sie stehen davor in der Liste) – ein Haken von
                    # Hand bleibt.
                    moeglich = self.raeumen.aktiv() or self._nut_laesst_aufmass()
                block.moeglich = moeglich
                block.haken.setEnabled(moeglich)
                block.erklaerung.setText(
                    block.s.text() if moeglich else grund or block.s.unmoeglich_text()
                )
                if not moeglich:
                    block.haken.setChecked(False)
                elif not block.von_hand:
                    vorschlag = block.s.vorgeschlagen(form, self._wahl(block))
                    if block is self.bohrung and self._von_raeumen_geraeumt(form):
                        vorschlag = False  # Räumen + Kontur ist dort die Folge
                    if nur_kanten and block is not self.entgraten3d:
                        vorschlag = False  # nur Kanten gewählt: die sollen eine Fase bekommen
                    block.haken.setChecked(vorschlag)
                block.zustand_zeigen()
        finally:
            self._fuellt = False
        self._restfraeser_waehlen()
        self._rest_vorschlagen(form)
        self._restschlichtfraeser_waehlen()
        self._fase_fraeser_waehlen(form)
        self._bloecke_ordnen()

    def _bloecke_ordnen(self):
        """Die Blöcke, die zur Wahl passen, oben – in ihrer Reihenfolge –, darunter unter einer
        Zeile mit ihrer Zahl, was (noch) nicht passt: eingeklappt, bis man darauf klickt, dann je
        Strategie der Titel und der Satz, was man anklicken muss. Passt nichts, steht alles da."""
        passend = [b.widget for b in self.bloecke if b.moeglich]
        andere = [b.widget for b in self.bloecke if not b.moeglich]
        reihe = passend + [self.passt_nicht] + andere
        if reihe != self._reihe:
            for widget in self._reihe:
                self._block_aufbau.removeWidget(widget)
            for i, widget in enumerate(reihe):
                self._block_aufbau.insertWidget(self._block_anfang + i, widget)
            self._reihe = reihe
        self.passt_nicht.setVisible(bool(andere) and bool(passend))
        dort = getattr(self, "_alles_dort", False)  # alles kommt in der Ebene dran: keine Blöcke
        self.nichts_angehakt.setVisible(not self.aktive_bloecke() and not dort)
        self.passt_nicht_knopf.setText(tr("ba.passt_nicht", anzahl=len(andere)))
        offen = (self.passt_nicht_knopf.isChecked() or not passend) and not dort
        for widget in passend:
            widget.setVisible(True)
        for widget in andere:
            widget.setVisible(offen)

    def _passt_nicht_aufklappen(self, offen):
        """Klappt die Liste auf oder zu, was nicht zur Wahl passt."""
        self.passt_nicht_knopf.setArrowType(QtCore.Qt.DownArrow if offen else QtCore.Qt.RightArrow)
        self.passt_nicht_kurz.setText(
            tr("ba.passt_nicht.offen") if offen else tr("ba.passt_nicht.zu")
        )
        self._bloecke_ordnen()

    def haken_geklickt(self, block):
        if self._fuellt:
            return
        block.von_hand = True
        block.zustand_zeigen()
        self.nichts_angehakt.setVisible(not self.aktive_bloecke())
        if block is self.reiben and self.job is not None:
            # Gerieben: kleiner vorbohren, Bohrung fräsen und Kontur treten dort nicht an.
            self._haken_vorschlagen(vr.modell(self.job).Shape)
        # Gewinde bohren oder fräsen – beides in dieselben Bohrungen schnitte zwei Gänge.
        paar = {self.gewinde: self.gewindefraesen, self.gewindefraesen: self.gewinde}
        anderer = paar.get(block)
        if anderer is not None and block.aktiv() and anderer.aktiv():
            self._fuellt = True
            try:
                anderer.haken.setChecked(False)
                anderer.von_hand = True
                anderer.zustand_zeigen()
            finally:
                self._fuellt = False
        self.vorschau_starten()

    def _farben_zeigen(self, farben, kanten=None):
        """Färbt die Flächen (und die angeklickten Kanten) des Teils im Job (wie
        gui_vierachs._farben_zeigen) – nur die Anzeige; _farben_zurueck() stellt sie wieder her."""
        if (not farben and not kanten) or self.job is None:
            self._farben_zurueck()
            return
        klon = vr.modell(self.job)
        ansicht = klon.ViewObject
        if stl_anzeige.als_netz(klon):  # ein Teil aus einem STL: das Netz trägt die Farben
            stl_anzeige.flaechen_faerben(klon, farben)
            self._farben_vorher = (klon, None, None, None)
            return
        if ansicht is None:
            return
        if not hasattr(ansicht, "DiffuseColor"):  # 26.3: ein Material je Fläche
            if not hasattr(ansicht, "ShapeAppearance"):
                return
            if self._farben_vorher is None:
                linien = getattr(ansicht, "LineColorArray", None)
                self._farben_vorher = (
                    klon,
                    None,
                    list(ansicht.ShapeAppearance),
                    list(linien) if linien is not None else None,
                )
            self._kanten_faerben(ansicht, klon, kanten or {})
            gui_zeigen.flaechen_material(
                ansicht, ft.anzahl(klon.Shape), self._farben_vorher[2], farben
            )
            return
        if self._farben_vorher is None:
            aussehen = getattr(ansicht, "ShapeAppearance", None)
            linien = getattr(ansicht, "LineColorArray", None)
            self._farben_vorher = (
                klon,
                list(ansicht.DiffuseColor),
                list(aussehen) if aussehen is not None else None,
                list(linien) if linien is not None else None,
            )
        self._kanten_faerben(ansicht, klon, kanten or {})
        grund = self._farben_vorher[1]
        anzahl = ft.anzahl(klon.Shape)
        if len(grund) != anzahl:
            grund = [tuple(grund[0]) if grund else tuple(ansicht.ShapeColor)] * anzahl
        alpha = grund[0][3] if grund and len(grund[0]) > 3 else 0.0
        neu = list(grund)
        for nummer, farbe in farben.items():
            if nummer < anzahl:
                neu[nummer] = (*(int(farbe[i : i + 2], 16) / 255 for i in (1, 3, 5)), alpha)
        ansicht.DiffuseColor = neu

    def _kanten_faerben(self, ansicht, klon, kanten):
        """Die angeklickten Kanten in ihrer Farbe (LineColorArray), die anderen wie vorher."""
        if not hasattr(ansicht, "LineColorArray") or self._farben_vorher[3] is None:
            return
        anzahl = klon.Shape.countElement("Edge")
        grund = list(self._farben_vorher[3])
        if len(grund) != anzahl:
            grund = [tuple(grund[0]) if grund else tuple(ansicht.LineColor)] * anzahl
        alpha = grund[0][3] if grund and len(grund[0]) > 3 else 0.0
        neu = list(grund)
        for nummer, farbe in kanten.items():
            if nummer < anzahl:
                neu[nummer] = (*(int(farbe[i : i + 2], 16) / 255 for i in (1, 3, 5)), alpha)
        with contextlib.suppress(TypeError, ValueError):  # ohne Farbe je Kante: wie vorher
            ansicht.LineColorArray = neu

    def _farben_zurueck(self):
        if self._farben_vorher is None:
            return
        klon, farben, aussehen, linien = self._farben_vorher
        self._farben_vorher = None
        try:
            ansicht = klon.ViewObject
            if ansicht is None:
                return
            if farben is None and aussehen is None:  # das Netz (stl_anzeige)
                stl_anzeige.flaechen_faerben(klon, {})
                return
            if linien is not None and hasattr(ansicht, "LineColorArray"):
                ansicht.LineColorArray = linien
            if aussehen is not None:
                ansicht.ShapeAppearance = aussehen
            else:
                ansicht.DiffuseColor = farben
        except (ReferenceError, RuntimeError):  # das Teil ist schon weg (Abbrechen)
            pass

    # --- Werkstoff, Fräser, Einsatz -------------------------------------------------------

    def _bearbeitung_fuellen(self):
        """Werkstoff und Fräser anbieten – die Werkzeugverwaltung frisch gelesen."""
        from .gui_werkzeuge import werkstoffe_anbieten

        vorher = self.werkstoff() if self.bibliothek is not None else None
        self.hinweis.setText("")
        try:
            self.bibliothek = wz.Bibliothek.laden()
        except wz.BeschaedigteDatei as fehler:
            self.bibliothek = wz.Bibliothek()
            self.hinweis.setText(tr("wv.fehler.laden", fehler=fehler, datei=fehler.beiseite))
        tc_vorher = self.block_zu_aendern.tc_vorher if self.block_zu_aendern else None
        self._fuellt = True
        try:
            werkstoffe_anbieten(self.wahl_werkstoff, self.bibliothek)
            if vorher is None:
                alle = self.bibliothek.alle_werkstoffe()
                werkstoff, _gemerkt = js.werkstoff_fuer(self.job, alle, tc_vorher)
                vorher = werkstoff.kennung if werkstoff is not None else wz.ALLE
            self.wahl_werkstoff.setCurrentIndex(max(0, self.wahl_werkstoff.findData(vorher)))
        finally:
            self._fuellt = False
        block = self.block_zu_aendern
        if block is not None and block.tc_vorher is not None and block.vorwahl is None:
            werkzeug = js.werkzeug_von(block.tc_vorher, self.bibliothek)
            block.vorwahl = werkzeug.kennung if werkzeug is not None else ""
        for block in self.bloecke:
            block.fraeser_fuellen(self.bibliothek, self.werkstoff())

    def werkstoff(self):
        return self.wahl_werkstoff.currentData() or wz.ALLE

    def _werkstoff_gewaehlt(self):
        if not self._fuellt:
            for block in self.bloecke:
                block.fraeser_fuellen(self.bibliothek, self.werkstoff())

    def fraeser(self):
        """Der Fräser des Planfräsens – für die Szenarien und zum Lesen."""
        return self.plan.fraeser()

    def einsatz(self):
        return self.plan.einsatz()

    def werkzeugverwaltung(self, nummer=None):
        """Öffnet die Werkzeugverwaltung; speichert man dort, liest der Assistent sie neu."""
        from . import gui_werkzeuge

        dialog = gui_werkzeuge.oeffne(nummer)
        if getattr(self, "_werkzeugdialog", None) is not dialog:
            self._werkzeugdialog = dialog
            dialog.gespeichert.connect(self._werkzeuge_gespeichert)

    def _werkzeuge_gespeichert(self):
        if BearbeitungPanel.offen is self and self.job is not None:
            # Was die Vorschau sich merkte, galt für die Werkzeuge davor – ihr Schlüssel kennt den
            # Platz im Magazin nicht (Manuel, 2026-10-25: „T1 auf 54 mm ausspannen“ – danach kam
            # der alte rote Satz aus dem Merker zurück).
            self.vorschau_merk.clear()
            self.__dict__.pop("_fehler_merk", None)
            self._wege.clear()
            self._bearbeitung_fuellen()

    # --- Werte und Vorschau -----------------------------------------------------------------

    def vorschau_starten(self):
        if self._fuellt or self._ruhig or self.geschlossen:
            return
        self._vorschau_lauf_beenden()  # was noch zur Eingabe davor rechnet, ist veraltet
        for block in self.bloecke:
            block.vorschau = None
        self._vorschau_uhr.start()
        self._knoepfe_beschriften()

    def _vorschau_lauf_beenden(self):
        """Der Lauf im Takt hört auf; rechnet sein Block in einem Nebenrechner, endet der."""
        self._vorschau_lauf = None
        auftrag, self._vorschau_auftrag = self._vorschau_auftrag, None
        if auftrag is not None and not auftrag.erledigt:
            auftrag.abbrechen()

    def vorschau_laeuft(self):
        """Steht eine Vorschau noch aus – die Uhr nach einer Eingabe läuft, oder ein Lauf rechnet
        im Takt?"""
        return self._vorschau_uhr.isActive() or self._vorschau_lauf is not None

    def _vorschau_rechnen(self):
        """Die grobe Bahn je angehaktem Block – und damit „Anlegen“ weiß, ob es geht. Was die
        Strategien mit den gewählten Flächen anfangen können, gilt für den ganzen Lauf
        (_eigene, P-2026-10-03-28: am Testteil 95 Fragen je Lauf). Am Stück – für „Anlegen“;
        nach einer Eingabe rechnet sie Schritt für Schritt (_vorschau_im_takt)."""
        self._vorschau_uhr.stop()
        self._vorschau_lauf_beenden()  # ein Lauf im Takt ist damit erledigt
        if self.geschlossen or self.job is None:
            return
        self._flaechen_merk = {}
        try:
            self._vorschau_rechnen_mit_merk()
        finally:
            self._flaechen_merk = None

    def _vorschau_im_takt(self):
        """Wie _vorschau_rechnen, aber Block für Block aus der Ereignisschleife: Dazwischen nimmt
        das Fenster Klicks an, und eine neue Eingabe (vorschau_starten) macht den Lauf ungültig
        – er hört beim nächsten Schritt auf. Bis P-2026-10-11-16 rechnete die Vorschau am Stück
        im Prozess der Oberfläche: am 3-Achs-Testteil 4 und 9 s nach dem Anklicken der Flächen,
        in denen FreeCAD keinen Klick annahm (Manuel, 2026-10-09: „ein Lag … wo ich nichts
        klicken kann … sowas muss unbedingt vermieden werden“)."""
        self._vorschau_uhr.stop()
        if self.geschlossen or self.job is None:
            return
        lauf = self._vorschau_schritte()
        self._vorschau_lauf = lauf
        QtCore.QTimer.singleShot(0, functools.partial(self._vorschau_schritt, lauf, {}))

    def _vorschau_schritt(self, lauf, merk):
        """Ein Schritt des Laufs; der nächste kommt aus der Ereignisschleife. `merk`: die Flächen
        je Block für diesen Lauf (_eigene) – nur während eines Schritts gesetzt, dazwischen kann
        sich die Wahl ändern."""
        from . import nebenrechner as nr

        if lauf is not self._vorschau_lauf or self.geschlossen:
            lauf.close()
            return
        if uhren.verschachtelt():
            # Mitten in einer anderen Rechnung (eine, die Ereignisse abarbeitet): danach weiter.
            QtCore.QTimer.singleShot(
                UHR_SCHRITT_MS, functools.partial(self._vorschau_schritt, lauf, merk)
            )
            return
        self._flaechen_merk = merk
        try:
            schritt = next(lauf)
        except StopIteration:
            if self._vorschau_lauf is lauf:
                self._vorschau_lauf = None
            return
        except Exception:
            if self._vorschau_lauf is lauf:
                self._vorschau_lauf = None
            raise
        finally:
            self._flaechen_merk = None
        weiter = functools.partial(self._vorschau_schritt, lauf, merk)
        if isinstance(schritt, nr.Auftrag) and not schritt.erledigt:
            # Ein Nebenrechner rechnet den Block: Weiter geht es, wenn er fertig ist – bis dahin
            # ist das Fenster ganz frei.
            self._vorschau_auftrag = schritt
            schritt.bei_fertig = lambda _auftrag: QtCore.QTimer.singleShot(0, weiter)
            return
        # partial, kein lambda: Ein Rahmen aus Python darunter hielte uhren.verschachtelt() für
        # eine laufende Rechnung.
        QtCore.QTimer.singleShot(0, weiter)

    def _vorschau_rechnen_mit_merk(self):
        for schritt in self._vorschau_schritte():
            _abwarten(schritt)

    def _vorschau_schritte(self):
        """Die Vorschau aller Blöcke als Schritte (ein Generator): nach jedem Block, nach dem
        Wettbewerb und vor jedem der letzten Teile ein `yield`."""
        form = vr.modell(self.job).Shape
        self._raeumen_boeden = None
        self._raeumen_bei_nut = False  # alle Gründe des Räumens fräst die Nut (_block_schritte)
        boeden = self._nur_boeden(form)
        gerechnet = {}  # Block → woraus seine Vorschau gerechnet ist (_block_rechnen)
        reihe = list(self.bloecke)
        if self._weg.get("waende") == "spirale":
            # Die Flanke vor dem 3D-Schlichten: Ihr Keil sagt, bis wohin es vorschlichtet
            # (_vorschlichten_zusatz) – sonst rechnete es danach noch einmal.
            reihe.remove(self.flanke)
            reihe.insert(reihe.index(self.schlichten3d), self.flanke)
        for block in reihe:
            yield from self._block_schritte(block, form, boeden, gerechnet)
            yield
        self._wettbewerb(form, nur_bohrung=boeden is not None)
        yield
        # Der Wettbewerb setzt Haken um: Das Planfräsen verliert ihn ans Räumen oder umgekehrt.
        # Wer dahinter gerechnet hat, stand dann auf dem Material des Verlierers („… hat
        # „Planfräsen“ schon weggenommen“ unter dem 3D-Schruppen, obwohl das Räumen angehakt ist –
        # B-009; die Kontur mit „die Tasche räumt das Räumen“ ohne Räumen, P-2026-10-02-17): Er
        # rechnet noch einmal, und der Wettbewerb entscheidet mit den neuen Zeiten. Höchstens
        # zweimal – dann steht es.
        for _runde in range(2):
            neu = []
            for b in self.bloecke:
                if (yield from self._block_schritte(b, form, boeden, gerechnet, True)):
                    neu.append(b)
                    yield
            if not neu:
                break
            self._wettbewerb(form, nur_bohrung=boeden is not None)
            yield
        self._schon_weg_abhaken()
        self._ziel_zeigen(form)
        yield
        self._raeumen_ausgelassen_zeigen()
        self._unfertig_zeigen(form)
        self._fase_angebot()
        self._knoepfe_beschriften()
        yield from self._fragen_schritte(form)
        self._gezeigten_block_erneuern()

    def _gezeigten_block_erneuern(self):
        """Nach dem Rechnen: Zeigte das 3D die Wege eines Blocks, die neuen – hat er keine mehr,
        keine."""
        gezeigt = getattr(self._bahnvorschau, "kennung", None)
        if gezeigt is None or gezeigt[0] != "block":
            return
        block = next((b for b in self.bloecke if b.s.kennung == gezeigt[1]), None)
        if block is None or block.vorschau is None:
            self._bahnvorschau.weg()
        else:
            self._bahnvorschau.zeigen(gezeigt, [block.vorschau], self._job_zum_teil())
        self._vorschau_knoepfe_setzen()

    # --- Fragen: wie willst du vorgehen? (W-039) ----------------------------------------------

    def _weg_waehlen(self, frage, weg):
        if self._weg.get(frage) == weg:
            return
        self._weg[frage] = weg
        if frage == "waende":
            self.schlichten3d.haken_pruefen()  # „Vorschlichten“ nur bei „Flanke grob, Spirale …“
        self.vorschau_starten()

    def _block_zeigen(self, block):
        """„Vorschau“ neben einem Haken: die Werkzeugwege des Blocks im 3D – noch ein Klick nimmt
        sie weg."""
        from . import gui_bahnvorschau as gb

        if self._bahnvorschau is None:
            self._bahnvorschau = gb.Bahnvorschau(self.doc)
        kennung = ("block", block.s.kennung)
        if self._bahnvorschau.kennung == kennung or block.vorschau is None:
            self._bahnvorschau.weg()
        else:
            self._bahnvorschau.zeigen(kennung, [block.vorschau], self._job_zum_teil())
        self._vorschau_knoepfe_setzen()

    def _vorschau_knoepfe_setzen(self):
        """Gedrückt ist nur der Knopf „Vorschau“ dessen, was gerade im 3D zu sehen ist."""
        gezeigt = getattr(self._bahnvorschau, "kennung", None)
        for block in self.bloecke:
            block.knopf_vorschau.blockSignals(True)
            block.knopf_vorschau.setChecked(gezeigt == ("block", block.s.kennung))
            block.knopf_vorschau.blockSignals(False)
        for frage, widget in (("waende", self.frage_waende), ("eintauchen", self.frage_eintauchen)):
            widget.gezeigt(gezeigt[1] if gezeigt and gezeigt[0] == frage else None)

    def _weg_zeigen(self, frage, weg):
        """„Vorschau“: die Werkzeugwege des Wegs im 3D – noch ein Klick nimmt sie weg. Rechnet er
        noch, kommt sie, sobald er fertig ist."""
        from . import gui_bahnvorschau as gb

        if self._bahnvorschau is None:
            self._bahnvorschau = gb.Bahnvorschau(self.doc)
        if self._bahnvorschau.kennung == (frage, weg):
            self._bahnvorschau.weg()
        else:
            eintrag = self._wege.get((frage, weg))
            if eintrag is None or not eintrag[1]:
                self._bahnvorschau.weg()
                self._bahnvorschau.kennung = (frage, weg)  # kommt nach dem Rechnen
            else:
                self._bahnvorschau.zeigen((frage, weg), eintrag[1], self._job_zum_teil())
        self._vorschau_knoepfe_setzen()

    def _job_zum_teil(self):
        """Die Lage, die Punkte im Job ans Teil bringt, wie es in der Ansicht liegt: Der Klon im
        Job ist Lage · Original (vierachs_rohteil.richte_ein) – also Original · Klon⁻¹."""
        if self.job is None:
            return None
        klon = vr.modell(self.job)
        teil = vr.original(klon)
        if teil is klon:
            return None
        return teil.Placement.multiply(klon.Placement.inverse())

    def _waende_woraus(self):
        """Woraus die Wege der Frage „Wände“ gerechnet sind – ändert sich etwas, gelten sie
        nicht mehr."""
        teile = [tuple(self.gewaehlte)]
        for block in (self.flanke, self.schlichten3d):
            teile.append((getattr(block.fraeser(), "kennung", None), repr(block.einsatz())))
            teile.append(repr(sorted(block.werte().items())))
        return repr(teile)

    def _fragen_schritte(self, form):
        """Die Fragen (W-039) nach dem Rechnen der Blöcke: „Eintauchen“, „Wände unter dem
        Rand“, „Reihenfolge“."""
        yield from self._eintauchen_schritte(form)
        yield from self._waende_schritte(form)
        self._reihenfolge_zeigen(form)

    # Die Zeit eines Wegs: alles, was angehakt ist, und die Werkzeugwechsel seiner Folge (W-040).

    def _werkzeugfolge(self, reihe, bohrer=None):
        """Die Werkzeuge der Blöcke in `reihe` nacheinander (Kennungen); vor einem Block die
        Bohrer, die für ihn vorbohren – aus `bohrer` ({Block: [Kennung]}), sonst aus seiner
        Vorschau."""
        bohrer = bohrer or {}
        folge = []
        for block in reihe:
            if block in bohrer:
                folge += bohrer[block]
            else:
                folge += _bohrer_von(getattr(block.vorschau, "vorbohren", None))
            folge.append(getattr(block.fraeser(), "kennung", None))
        return folge

    def _reihe_mit(self, form, frage, weg):
        """Die Folge der angehakten Blöcke im Job, wäre in der Frage `frage` der Weg `weg`
        gewählt."""
        alt, self._weg[frage] = self._weg.get(frage), weg
        try:
            return self._in_anlege_reihe(self.aktive_bloecke(), form)
        finally:
            self._weg[frage] = alt

    def _gesamt(self, teil, bloecke=(), bohrer=None, reihe=None):
        """Die Zeit für alles, was angehakt ist (min), mit dem Weg einer Frage: `teil` die Zeit
        ihrer `bloecke` (mit ihrem Vorbohren), die anderen mit ihrer Zeit und der ihres
        Vorbohrens, dazu je Werkzeugwechsel der Folge (`reihe`, ohne: die im Job; `bohrer` wie
        bei _werkzeugfolge) die Wechselzeit. So zeigen die Fragen je Weg, was am Ende dauert –
        auch wenn ein Weg den Wettbewerb verschiebt (ohne Vorbohren nahm das Räumen am
        Gehäuseunterteil dem Planfräsen die Oberseite ab: nur Räumen gezählt 11 statt 13 min).
        `teil` None (rechnet) und False (geht nicht) bleiben."""
        if teil is None or isinstance(teil, bool):
            return teil
        zeit = teil
        for block in self.aktive_bloecke():
            if block in bloecke or block.zeit is None:
                continue
            zeit += block.zeit
            gebohrt = getattr(block.vorschau, "vorbohren", None)
            if gebohrt is not None:
                zeit += gebohrt.zeit
        if reihe is None:
            reihe = self._in_anlege_reihe(self.aktive_bloecke(), self._form_im_job())
        return zeit + _wechsel_zahl(self._werkzeugfolge(reihe, bohrer)) * self._wechsel_minuten()

    def _form_im_job(self):
        return vr.modell(self.job).Shape if self.job is not None else None

    def _reihenfolge_zeigen(self, form):
        """Die Frage „Reihenfolge“: zeigen, wenn „Erst alles schruppen“ eine andere Folge ergäbe
        als die vorgeschlagene; je Weg die Folge als Satz (die Bahnen sind dieselben – keine
        Vorschau), die Zeit mit den Werkzeugwechseln dieser Folge."""
        frage = self.frage_reihenfolge
        reihen = {weg: self._reihe_mit(form, "reihenfolge", weg) for weg in frage.knoepfe}
        passt = self.zu_aendern is None and reihen["vorgeschlagen"] != reihen["schruppen"]
        self._frage_passt("reihenfolge", frage, passt)
        if not passt:
            return
        frage.waehlen(self._weg["reihenfolge"])
        for weg, reihe in reihen.items():
            frage.zeit_setzen(weg, self._gesamt(0.0, reihe=reihe))
            wechsel = _wechsel_zahl(self._werkzeugfolge(reihe))
            werte = {
                "folge": self._folge_text(reihe),
                "wechsel": (
                    tr("ba.frage.wechsel.eins")
                    if wechsel == 1
                    else tr("ba.frage.wechsel", n=wechsel)
                ),
            }
            if weg == "schruppen":
                satz = tr("ba.frage.reihenfolge.schruppen.satz", **werte)
            else:
                satz = tr("ba.frage.reihenfolge.vorgeschlagen.satz", **werte)
            frage.satz_setzen(weg, satz)

    def _folge_text(self, reihe):
        """Die Folge als Text: „Planfräsen T1 → Vorbohren T24 → Räumen T1 → …“."""
        teile = []
        for block in reihe:
            for kennung in _bohrer_von(getattr(block.vorschau, "vorbohren", None)):
                bohrer = next(
                    (w for w in getattr(self.bibliothek, "werkzeuge", []) if w.kennung == kennung),
                    None,
                )
                teile.append(tr("ba.frage.reihenfolge.vorbohren", t=self._nummer(bohrer)))
            teile.append(f"{block.s.titel()} {self._nummer(block.fraeser())}".strip())
        return " → ".join(teile)

    def _nummer(self, werkzeug):
        """„T3“ – die Nummer im Magazin der Maschine, sonst in der Werkzeugverwaltung."""
        if werkzeug is None:
            return ""
        magazin = self.magazin()
        return mg.genannt(werkzeug, magazin) if magazin else wz.nummer_text(werkzeug)

    def _frage_passt(self, frage, widget, passt):
        """Zeigt die Frage, wenn sie passt – sonst weg, mit ihrer Vorschau im 3D."""
        widget.widget.setVisible(passt)
        gezeigt = getattr(self._bahnvorschau, "kennung", None)
        if not passt and gezeigt is not None and gezeigt[0] == frage:
            self._bahnvorschau.weg()
            self._vorschau_knoepfe_setzen()

    def _gezeigten_weg_erneuern(self, frage, woraus):
        """Zeigte das 3D einen Weg der Frage, die neu gerechneten Wege."""
        gezeigt = getattr(self._bahnvorschau, "kennung", None)
        if gezeigt is not None and gezeigt[0] == frage:
            eintrag = self._wege.get(gezeigt)
            if eintrag is not None and eintrag[2] == woraus and eintrag[1]:
                self._bahnvorschau.zeigen(gezeigt, eintrag[1], self._job_zum_teil())

    def _waende_schritte(self, form):
        """Die Frage „Wände unter dem Rand“: zeigen, wenn es um solche Wände geht; die Zeit des
        gewählten Wegs aus den Blöcken, den anderen im Nebenrechner dazu (grob wie die
        Vorschau)."""
        frage = self.frage_waende
        passt = self.zu_aendern is None and bool(self._waende_unter_rand(form))
        self._frage_passt("waende", frage, passt)
        if not passt:
            return
        woraus = self._waende_woraus()
        jetzt = self._weg["waende"]
        bloecke = (self.flanke, self.schlichten3d)
        reihen = {weg: self._reihe_mit(form, "waende", weg) for weg in frage.knoepfe}
        if all(b.vorschau is not None and b.zeit is not None for b in bloecke):
            zeit = sum(b.zeit for b in bloecke)
            self._wege[("waende", jetzt)] = (zeit, [b.vorschau for b in bloecke], woraus)
        else:
            self._wege[("waende", jetzt)] = (False, [], woraus)  # einer der Blöcke steht rot
        for weg in frage.knoepfe:
            eintrag = self._wege.get(("waende", weg))
            gilt = eintrag is not None and eintrag[2] == woraus
            gesamt = self._gesamt(eintrag[0], bloecke, reihe=reihen[weg]) if gilt else None
            frage.zeit_setzen(weg, gesamt)
        for weg in frage.knoepfe:
            eintrag = self._wege.get(("waende", weg))
            if weg == jetzt or (eintrag is not None and eintrag[2] == woraus):
                continue
            gerechnet = yield from self._weg_rechnen(form, "waende", weg)
            if gerechnet is None:
                gerechnet = (False, [])
            self._wege[("waende", weg)] = (*gerechnet, woraus)
            frage.zeit_setzen(weg, self._gesamt(gerechnet[0], bloecke, reihe=reihen[weg]))
        self._gezeigten_weg_erneuern("waende", woraus)

    def _weg_rechnen(self, form, frage, weg):
        """(Minuten, [Vorschau je Block]) der Blöcke der Frage, gerechnet, als wäre `weg` gewählt
        – im Nebenrechner, wenn es geht (Schritte: ein Auftrag je Block); None, wenn es nicht
        geht."""
        bahnen, zeit = [], 0.0
        for block in (self.flanke, self.schlichten3d):
            werkzeug, einsatz = block.fraeser(), block.einsatz()
            if werkzeug is None or einsatz is None:
                return None
            _n, vorschub, senkrecht = js.werte_im_job(werkzeug, einsatz, self.job)
            alt, self._weg[frage] = self._weg[frage], weg
            try:
                # Das 3D-Schlichten mit der Flanke dieses Wegs (Vorschlichten: ihr Keil).
                zusatz = self._zusatz(block, form, flanke=bahnen[0] if bahnen else None)
                werte = dict(block.werte(), vorschub=vorschub, eintauchen=senkrecht,
                             **(zusatz or {}))  # fmt: skip
                flaechen = self._flaechen(block, form)
            finally:
                self._weg[frage] = alt
            auftrag = block._im_hintergrund(
                self.job, werkzeug, werte, flaechen, vorschub, senkrecht
            )
            if auftrag is not None:
                yield auftrag
                gerechnet = _aus_dem_hintergrund(auftrag)
                if gerechnet is None or gerechnet[0] != "ok":
                    return None
                bahn = gerechnet[1][0]
            else:
                try:
                    bahn = block.s.vorschau(self.job, werkzeug, werte, flaechen)
                except (ValueError, RuntimeError):
                    return None
                yield
            bahnen.append(bahn)
            if vorschub > 0:
                zeit += block.s.zeit(bahn, vorschub, senkrecht)
        return zeit, bahnen

    def _eintauchen_waehlen(self, weg):
        """Die Frage „Eintauchen“: „Vorbohren“ bei Räumen und Nut an oder ab (die Haken bei ihren
        Einstellungen sagen dasselbe), dann neu rechnen."""
        an = weg == "vorbohren"
        for block in (self.raeumen, self.nut):
            haken = block.haken_felder.get("vorbohren")
            if haken is not None and haken.isEnabled() and haken.isChecked() != an:
                haken.blockSignals(True)
                haken.setChecked(an)
                haken.blockSignals(False)
        self.vorschau_starten()

    def _eintauchen_bloecke(self):
        """Räumen und Nut, angehakt und gerechnet, die ins Volle eintauchen und vorbohren könnten
        (ihr Haken „Vorbohren“ geht – ein Bohrer im Magazin): vorgebohrt, oder „Vorbohren“ ist
        abgehakt und es gibt Stellen, an denen sie eintauchen."""
        bloecke = []
        for block in (self.raeumen, self.nut):
            haken = block.haken_felder.get("vorbohren")
            bahn = block.vorschau
            if not block.aktiv() or bahn is None or block.zeit is None:
                continue
            if haken is None or not haken.isEnabled():
                continue
            if getattr(bahn, "vorbohren", None) is not None:
                bloecke.append(block)
            elif not haken.isChecked():
                if block is self.nut:
                    taucht_ein = any(not e[5] for e in (getattr(bahn, "eintauchen", None) or []))
                else:
                    taucht_ein = bool(ra.vorbohr_stellen(bahn))
                if taucht_ein:
                    bloecke.append(block)
        return bloecke

    def _eintauchen_woraus(self, bloecke, form):
        """Woraus die Wege der Frage „Eintauchen“ gerechnet sind – alles außer dem Haken
        „Vorbohren“ selbst (so gilt der andere Weg nach dem Wählen weiter, solange die Blöcke
        dieselben Flächen haben)."""
        teile = [tuple(self.gewaehlte)]
        for block in bloecke:
            werte = {k: v for k, v in block.werte().items() if k != "vorbohren"}
            zusatz = getattr(block, "zusatz_zuletzt", {})
            teile.append(
                (
                    block.s.kennung,
                    tuple(self._flaechen(block, form)),
                    getattr(block.fraeser(), "kennung", None),
                    repr(block.einsatz()),
                    repr(sorted(werte.items())),
                    repr(sorted((k, repr(v)) for k, v in zusatz.items() if k != "materialstand")),
                    getattr(zusatz.get("materialstand"), "kennung", None),
                )
            )
        return repr(teile)

    def _eintauchen_schritte(self, form):
        """Die Frage „Eintauchen“: zeigen, wenn Räumen oder Nut ins Volle eintauchen und
        vorbohren könnten. Ohne Vorbohren aus den Blöcken (vorgebohrt haben sie den Weg ohne
        mitgerechnet: raeumen.Vorbohren.ohne_punkte), mit Vorbohren aus ihnen, wenn sie
        vorgebohrt haben, sonst im Nebenrechner dazu."""
        frage = self.frage_eintauchen
        bloecke = self._eintauchen_bloecke() if self.zu_aendern is None else []
        self._frage_passt("eintauchen", frage, bool(bloecke))
        if not bloecke:
            return
        an = any(b.haken_felder["vorbohren"].isChecked() for b in bloecke)
        frage.waehlen("vorbohren" if an else "helix")
        woraus = self._eintauchen_woraus(bloecke, form)
        zeit, bahnen = 0.0, []
        for block in bloecke:
            gebohrt = getattr(block.vorschau, "vorbohren", None)
            if gebohrt is None:
                zeit += block.zeit
                bahnen.append(block.vorschau)
            elif gebohrt.ohne_frei is not None and gebohrt.ohne_punkte:
                zeit += gebohrt.ohne_frei
                bahnen.append(types.SimpleNamespace(punkte=gebohrt.ohne_punkte))
            else:
                zeit, bahnen = False, []
                break
        self._wege[("eintauchen", "helix")] = (zeit, bahnen, woraus)
        if all(getattr(b.vorschau, "vorbohren", None) is not None for b in bloecke):
            zeit, bahnen = 0.0, []
            for block in bloecke:
                zeit += block.zeit + block.vorschau.vorbohren.zeit
                bahnen += [_Bohrlinien(block.vorschau.vorbohren, block), block.vorschau]
            self._wege[("eintauchen", "vorbohren")] = (zeit, bahnen, woraus)

        def gesamt(weg):
            eintrag = self._wege.get(("eintauchen", weg))
            if eintrag is None or eintrag[2] != woraus:
                return None
            bohrer = {b: [] for b in bloecke}
            for bahn in eintrag[1]:
                if isinstance(bahn, _Bohrlinien) and bahn.block in bohrer:
                    bohrer[bahn.block] += _bohrer_von(bahn.gebohrt)
            return self._gesamt(eintrag[0], bloecke, bohrer)

        for weg in frage.knoepfe:
            frage.zeit_setzen(weg, gesamt(weg))
        eintrag = self._wege.get(("eintauchen", "vorbohren"))
        if eintrag is None or eintrag[2] != woraus:
            gerechnet = yield from self._vorgebohrt_rechnen(form, bloecke)
            eintrag = (*(gerechnet or (False, [])), woraus)
            self._wege[("eintauchen", "vorbohren")] = eintrag
            frage.zeit_setzen("vorbohren", gesamt("vorbohren"))
        frage.satz_setzen("vorbohren", self._vorbohren_satz(eintrag[1]))
        self._gezeigten_weg_erneuern("eintauchen", woraus)

    def _vorgebohrt_rechnen(self, form, bloecke):
        """(Minuten, [Vorschau]) des Wegs „vorbohren“: Blöcke, die schon vorgebohrt haben, wie sie
        sind; die anderen mit „Vorbohren“ gerechnet – im Nebenrechner, wenn es geht, mit dem, was
        der Assistent ihnen zuletzt gab (Materialstand, Bohrer). None, wenn es nicht geht oder
        nirgends vorgebohrt würde."""
        zeit, bahnen = 0.0, []
        for block in bloecke:
            bahn = block.vorschau
            minuten = block.zeit
            if getattr(bahn, "vorbohren", None) is None:
                werkzeug, einsatz = block.fraeser(), block.einsatz()
                _n, vorschub, senkrecht = js.werte_im_job(werkzeug, einsatz, self.job)
                werte = dict(block.werte(), vorschub=vorschub, eintauchen=senkrecht)
                werte.update(getattr(block, "zusatz_zuletzt", {}))
                werte["vorbohren"] = True
                flaechen = self._flaechen(block, form)
                auftrag = block._im_hintergrund(
                    self.job, werkzeug, werte, flaechen, vorschub, senkrecht
                )
                frei = None
                if auftrag is not None:
                    yield auftrag
                    gerechnet = _aus_dem_hintergrund(auftrag)
                    if gerechnet is None or gerechnet[0] != "ok":
                        return None
                    bahn, frei = gerechnet[1]
                else:
                    try:
                        bahn = block.s.vorschau(self.job, werkzeug, werte, flaechen)
                    except (ValueError, RuntimeError):
                        return None
                    yield
                if frei is None and block.s.kennung in IM_FREIEN_SCHNELL:
                    frei = _zeit_im_freien(self.job, werkzeug, werte, bahn, vorschub, senkrecht)
                minuten = frei if frei is not None else block.s.zeit(bahn, vorschub, senkrecht)
            gebohrt = getattr(bahn, "vorbohren", None)
            if gebohrt is not None:
                minuten += gebohrt.zeit
                bahnen.append(_Bohrlinien(gebohrt, block))
            zeit += minuten
            bahnen.append(bahn)
        if not any(isinstance(b, _Bohrlinien) for b in bahnen):
            return None
        return zeit, bahnen

    def _wechsel_minuten(self):
        """Ein Werkzeugwechsel an der gewählten Maschine (min) – ohne Angabe die Vorgabe
        (W-040; Manuel, 2026-10-25: „Je Maschine, vorbelegt 10 s“)."""
        return msp.wechselzeit_von(self.maschine()) / 60.0

    def _wechsel_dazu(self, block, gruppe):
        """Der Werkzeugwechsel, den der Block in den Job bringt (min) – keiner, wenn sein Werkzeug
        schon ein anderer angehakter Block außerhalb der `gruppe` nimmt (W-040: der Wettbewerb
        zählt die Wechsel mit)."""
        werkzeug = block.fraeser()
        if werkzeug is None:
            return 0.0
        for anderer in self.aktive_bloecke():
            if anderer in gruppe:
                continue
            w = anderer.fraeser()
            if w is not None and w.kennung == werkzeug.kennung:
                return 0.0
        return self._wechsel_minuten()

    def _vorbohren_satz(self, bahnen):
        """Der Satz zum Weg „vorbohren“: wie viele Löcher, welcher Ø, wie tief – ohne gerechnete
        Löcher der allgemeine."""
        gebohrt = [b.gebohrt for b in bahnen if isinstance(b, _Bohrlinien)]
        loecher = [lo for g in gebohrt for lo in g.je_loch()]
        if not loecher:
            return tr("ba.frage.eintauchen.vorbohren.satz")
        durchmesser = " / ".join(
            f"Ø {groesse_zeigen(d, einheiten.LAENGE, 1) or '0'}"
            for d in sorted({round(float(lo[3]), 2) for lo in loecher}, reverse=True)
        )
        werte = {
            "n": len(loecher),
            "d": durchmesser,
            "tiefe": groesse_zeigen(max(g.tiefe for g in gebohrt), einheiten.LAENGE, 0) or "0",
        }
        if len(loecher) == 1:
            satz = tr("ba.frage.eintauchen.vorbohren.ein_loch", **werte)
        else:
            satz = tr("ba.frage.eintauchen.vorbohren.loecher", **werte)
        if any(not g.loecher and g.geholfen <= 0 for g in gebohrt):  # das Räumen, adaptiv
            satz += " " + tr("ba.frage.eintauchen.vorbohren.adaptiv")
        if any(g.zu_kurz for g in gebohrt):
            satz += " " + tr("ba.raeumen.vorbohren.zu_kurz")
        return satz

    # --- Das Teil muss herauskommen (Grundsatz 0) -------------------------------------------

    def _fertige_flaechen(self, block, form):
        """Die gewählten Flächen, die der Block mit seinen Werten genau fertig macht – so, wie
        sie gezeichnet sind: ohne Aufmaß, mit seinem Haken „Schlichten“. Schruppen mit Aufmaß
        (Räumen an Wänden, 3D-Schruppen, Rest räumen an Wänden) zählt nicht, auch nicht, was
        nur Ecken (Restmaterial), Kehlen (Bleistift) oder Anbohrungen (Zentrieren) macht."""
        werte = block.werte()
        if block is self.plan:
            if float(werte.get("aufmass", 0.0)):
                return []
            eng = set(self._unerreicht(block, form))
            return [f for f in self._flaechen(block, form) if f not in eng]
        if block in (self.raeumen, self.restraeumen):
            if float(werte.get("aufmass_boden", 0.0)):
                return []
            if block is self.restraeumen:
                return self._flaechen(block, form)
            # Wohin sein Fräser oder seine Bahn nicht kommt (eine Nut enger als er), ist nicht
            # fertig – und Wände, unter denen es bis durch räumt, nur ohne Aufmaß an den Wänden.
            eng = set(self._unerreicht(block, form))
            if float(werte.get("aufmass", 0.0)):
                eng |= {f for f in self._raeumt(form) if ra.durchgehend(form, f)}
            return [f for f in self._raeumt(form) if f not in eng]
        if block is self.schlichten_danach:
            zusatz = self._schlichten_danach_zusatz(form)
            flaechen = list(zusatz.get("boden_flaechen", ())) if werte.get("boden") else []
            if werte.get("waende"):
                flaechen += list(zusatz.get("wand_flaechen", ()))
                flaechen += list(zusatz.get("nut_ring_waende", ()))
            return flaechen
        if block in (self.nut, self.kontur, self.bohrung):
            if werte.get("schlichten") or not float(werte.get("aufmass", 0.0)):
                if block is self.bohrung:
                    # Nicht die, die kleiner sind als der Fräser (Bohrbahn.zu_klein).
                    zu_klein = set(getattr(block.vorschau, "zu_klein", ()) or ())
                    return [f for f in self._flaechen(block, form) if f not in zu_klein]
                return self._flaechen(block, form)
            if block is self.nut:
                # Das Aufmaß bleibt an den Wänden – der Grund ist auf Tiefe (an der Ringnut des
                # Messspitzenhalters hieß es sonst „Nicht fertig: Face7“).
                return [f for f in self._flaechen(block, form) if nb.ist_grund(form, f)]
            return []
        if block in (
            self.bohren,
            self.gewinde,
            self.gewindefraesen,
            self.entgraten,
            self.entgraten3d,
            self.fase,
            self.senken,
            self.reiben,
            self.schlichten3d,
            self.restschlichten,
        ):
            return self._flaechen(block, form)
        if block is self.flanke:
            return self._flaechen(block, form) if not float(werte.get("aufmass", 0.0)) else []
        return []

    def _unfertige(self, form):
        """[(Fläche, [Blöcke, die sie fertig machten])] für jede gewählte Fläche, die am Ende
        keine genaue Bahn hätte – ohne die, mit denen keine Strategie etwas anfangen kann (die
        stehen rot in der Liste)."""
        bloecke = self.bloecke
        stl = self._ist_stl()
        if stl:
            # Ein STL: nur Freiform (wie _wahl) – sonst fragte es jedes Dreieck Kontur, Nut, Wand …
            # (am Geist an der 5-Achs-Fräse 25.577 Dreiecke, das Fenster stand 32 s).
            bloecke = [b for b in bloecke if b.s.kennung in FREIFORM_STRATEGIEN]
        je_block = {
            b: set(self._fertige_flaechen(b, form)) for b in bloecke if b.aktiv() or b.moeglich
        }
        fertig = set().union(*(je_block[b] for b in self.aktive_bloecke()))
        fertig |= set(self._geschwenkt(form))  # die kommen in ihrer Ebene oder Aufspannung dran
        if fertig and not stl:  # ein STL hat keine Bohrungen (nur Dreiecke)
            fertig |= {
                n
                for n in self.gewaehlte
                if n not in fertig and bb.bohrung_ueber_boden(form, n) in fertig
            }
        ergebnis = []
        for name in self.gewaehlte:
            if name in fertig or not any(b.s.passt(form, name) for b in bloecke):
                continue
            if not stl and kb.waende(form, [name]) and self._ohne_rohteil(form, name):
                continue  # kein Rohteil vor der Wand: schon fertig (die Stange im Fertigmaß)
            # Entgraten bricht nur die Kanten: Angehakt zählt die Fläche als bearbeitet, als
            # Vorschlag, sie fertig zu machen, taugt es nicht (an der Stirn einer Welle stand
            # sonst „Dafür anhaken: „Entgraten 3D““). Auch keiner, der eben „nichts zu tun“ fand und
            # den Haken abgab (am Geist in einer Ebene der Kette: „Dafür anhaken: „3D-Schlichten““
            # unter dessen „Auf den gewählten Flächen gibt es nichts zu fräsen“).
            koennten = [
                b
                for b in bloecke
                if not b.aktiv()
                and not b.schon_weg
                and name in je_block.get(b, ())
                and b not in (self.entgraten, self.entgraten3d)
            ]
            ergebnis.append((name, koennten))
        return ergebnis

    def _unfertig_zeigen(self, form):
        """Rot über den Blöcken, welche gewählte Fläche am Ende keine genaue Bahn hätte – ein
        Zapfen aus dem Räumen wäre ein Vieleck im Aufmaß – und welcher Haken sie fertig macht."""
        unfertig = self._unfertige(form) if self.job is not None else []
        if not unfertig:
            self.unfertig.hide()
            self.unfertig_angebot.hide()
            return
        namen = [name for name, _k in unfertig]
        angebot = self._senken_angebot(form, namen)
        if angebot is None:
            self._unfertig_aktion = None
            self.unfertig_angebot.hide()
        else:
            satz, knopf_text, self._unfertig_aktion = angebot
            self.unfertig_satz.setText(satz)
            self.unfertig_knopf.setText(knopf_text)
            self.unfertig_angebot.show()
        flaechen = ", ".join(namen[:4]) + (" …" if len(namen) > 4 else "")
        bloecke = []
        for _name, koennten in unfertig:
            for block in koennten:
                if block not in bloecke:
                    bloecke.append(block)
        if bloecke:
            titel = ", ".join(f"„{b.s.titel()}“" for b in bloecke)
            text = tr("ba.unfertig", flaechen=flaechen, bloecke=titel)
        elif angebot is not None:
            text = tr("ba.unfertig.mit_angebot", flaechen=flaechen)  # der Knopf darunter
        else:
            text = tr("ba.unfertig.keiner", flaechen=flaechen)
        # Warum: Planfräsen oder Räumen ist angehakt, erreicht die Fläche aber nicht ganz.
        for block in (self.plan, self.raeumen):
            if not block.aktiv():
                continue
            unerreicht = {n: a for n, a in self._unerreicht(block, form).items() if n in namen}
            if unerreicht:
                name, anteil = min(unerreicht.items(), key=lambda e: e[1])
                text += " " + tr(
                    "ba.unfertig.erreicht",
                    block=block.s.titel(),
                    flaeche=name,
                    anteil=int(round(100.0 * anteil)),
                    werkzeug=_ziel_werkzeug(block.fraeser()),
                )
        self.unfertig.setText(dezimal(text))
        self.unfertig.show()

    def _block_rechnen(self, block, form, boeden, gerechnet, nur_anders=False):
        """_block_schritte am Stück (wartet auf Nebenrechner); gibt zurück, ob er gerechnet hat."""
        lauf = self._block_schritte(block, form, boeden, gerechnet, nur_anders)
        while True:
            try:
                schritt = next(lauf)
            except StopIteration as ende:
                return ende.value
            _abwarten(schritt)

    def _block_schritte(self, block, form, boeden, gerechnet, nur_anders=False):
        """Die Vorschau eines Blocks, wenn er angehakt ist oder im Wettbewerb steht; sonst leer.
        `gerechnet` merkt je Block, woraus sie gerechnet ist – seine Flächen, was der Assistent
        ihm vorgibt, sein Materialstand. Mit `nur_anders` (nach dem Wettbewerb) rechnet er nur,
        wenn sich daran etwas geändert hat. Gibt zurück, ob er gerechnet hat."""
        if nur_anders and boeden is not None and block in (self.plan, self.raeumen):
            return False  # die Folge (_folge) hat beide gerechnet, mit ihren Sätzen
        dabei = self._dabei(block)
        if block is self.raeumen and boeden is not None and dabei:
            yield from self._folge_schritte(form, boeden)  # setzt die Haken selbst
            return False
        if block is self.restraeumen:
            yield from self._restraeumen_schritte(form)  # nach dem Räumen: was es ausließ
            dabei = block.aktiv() or self._im_wettbewerb(block)
        if block is self.schlichten_danach:
            self._schlichten_danach_einrichten(form)  # mit dem Räumen oder der Nut
            dabei = block.aktiv()
        if not dabei:
            # Nach dem Wettbewerb bleibt stehen, was er dem Verlierer hingeschrieben hat – nur
            # „Rest räumen“ und „Schlichten danach“ ohne Räumen davor haben nichts mehr zu sagen.
            if not nur_anders or block in (self.restraeumen, self.schlichten_danach):
                block.leeren()
                gerechnet.pop(block, None)
            return False
        eigen = zusatz = self._zusatz(block, form)
        stand = None
        if block in (self.plan, self.nut, self.raeumen, self.kontur, self.schruppen3d, self.fase):
            stand = yield from self._materialstand_schritte(block, form)
            zusatz = dict(zusatz or {}, materialstand=stand)
        elif block in (self.restraeumen, self.schlichten_danach):
            # Nach dem Räumen derselben Flächen – sie treten nicht gegen es an.
            stand = yield from self._materialstand_schritte(block, form, flaechen=())
            zusatz = dict(zusatz or {}, materialstand=stand)
        flaechen = self._flaechen(block, form)
        woraus = (tuple(flaechen), eigen, getattr(stand, "kennung", None))
        if nur_anders and gerechnet.get(block) == woraus:
            return False
        if (
            block is self.raeumen
            and not flaechen
            and self.nut.aktiv()
            and self._eigene(block, form)
        ):
            # Alle seine Gründe fräst die angehakte Nut (die Ringnut am Messspitzenhalter, „Alles
            # aus dieser Aufspannung“): Ohne eigene Fläche räumte es sonst die Oberseite – „steht
            # nichts“, und „Anlegen“ ging nicht. Es gibt den Haken ab (_schon_weg_abhaken).
            block.leeren()
            block.hinweis.setText(tr("ba.raeumen.bei_nut"))
            block.schon_weg = True
            self._raeumen_bei_nut = True
            gerechnet[block] = woraus
            return True
        if block is self.kontur and not flaechen and self._eigene(block, form):
            # Ihre Wände räumt das Räumen bis durch, oder vor ihnen steht kein Rohteil – nichts zu
            # tun: Sie gibt den Haken ab wie nach dem Materialstand (_schon_weg_abhaken).
            block.leeren()
            if set(self._eigene(block, form)) & set(self._durch_waende(form)):
                block.hinweis.setText(tr("ba.kontur.beim_raeumen"))
            else:
                block.hinweis.setText(tr("ba.kontur.kein_rohteil"))
            block.schon_weg = True
            gerechnet[block] = woraus
            return True
        yield from block.vorschau_schritte(self.job, flaechen, zusatz)
        gerechnet[block] = woraus
        if block is self.raeumen and block.vorschau is None and self._raeumen_umsonst(form):
            # „Steht nichts“ – und alles, was es hätte, ist ein Grund der Nut oder eine Wand ohne
            # Rohteil davor (der Mantel der Stange im Fertigmaß, Manuels Messspitzenhalter): Es
            # gibt den Haken ab wie nach dem Materialstand, statt rot angehakt zu bleiben.
            block.leeren()
            block.hinweis.setText(tr("ba.raeumen.umsonst"))
            block.schon_weg = True
            if self.nut.aktiv():
                # Dann schlichtet „Schlichten danach“ nach der Nut, mit ihrem Fräser – sonst folgte
                # es dem Räumen, bis es den Haken abgab, und blieb mit dessen Ø 12 stehen
                # („Alles aus dieser Aufspannung“ am Messspitzenhalter; die Wände der Ringnut
                # blieben mit Aufmaß).
                self._raeumen_bei_nut = True
        if block is self.kontur:
            self._kontur_text(form, eigen)
        if block is self.flanke and eigen and block.ergebnis_basis:
            aufmass = groesse_zeigen(eigen["aufmass"], einheiten.LAENGE, 2) or "0"
            block.ergebnis.setText(
                tr("ba.fl.vor_spirale", text=block.ergebnis_basis, aufmass=aufmass)
            )
        if block is self.bohren and (zusatz or {}).get("reiben") and block.ergebnis_basis:
            d = groesse_zeigen(block.fraeser().durchmesser, einheiten.LAENGE) or "0"
            block.ergebnis.setText(tr("ba.bohren.vorbohren", text=block.ergebnis_basis, d=d))
        return True

    def _dabei(self, block):
        """Rechnet der Block mit – angehakt oder im Wettbewerb?"""
        return block.aktiv() or self._im_wettbewerb(block)

    def _raeumt(self, form):
        """Die Flächen, die das Räumen wirklich räumt: seine Flächen ohne die Böden der Taschen,
        in die sein Fräser nicht passt (B-007; raeumen_bahn.Raeumbahn.ausgelassen)."""
        ausgelassen = set(getattr(self.raeumen.vorschau, "ausgelassen", None) or [])
        rest = self.restraeumen
        if rest.aktiv() and rest.vorschau is not None:
            # Was „Rest räumen“ mit dem kleineren Fräser nachholt, ist geräumt.
            ausgelassen &= set(getattr(rest.vorschau, "ausgelassen", None) or [])
        return set(self._flaechen(self.raeumen, form)) - ausgelassen

    def _raeumen_ausgelassen_zeigen(self):
        """Hinter das Ergebnis des Räumens, in welche Taschen sein Fräser nicht passt (B-007,
        Manuels Testteil: die dreieckige Tasche und der Ø 12) – sie bleiben stehen; bisher fiel
        das ohne ein Wort aus."""
        block = self.raeumen
        ausgelassen = list(getattr(block.vorschau, "ausgelassen", None) or [])
        text = block.ergebnis.text()
        if not ausgelassen or not text or block.fraeser() is None:
            return
        d = groesse_zeigen(block.fraeser().durchmesser, einheiten.LAENGE) or "0"
        flaechen = ", ".join(ausgelassen)
        rest = self.restraeumen
        form = vr.modell(self.job).Shape if self.job is not None else None
        if form is not None and not any(hf.ebenen_oben(form, [n]) for n in ausgelassen):
            # Nur Wände: ein Gebiet bis durch hinter einer Engstelle (W-034), keine Tasche.
            if rest.aktiv() and rest.vorschau is not None:
                werkzeug = mg.genannt(rest.fraeser(), self.magazin())
                neu = tr("ba.raeumen.eng.rest", text=text, flaechen=flaechen, d=d, t=werkzeug)
            else:
                neu = tr("ba.raeumen.eng", text=text, flaechen=flaechen, d=d)
            block.ergebnis.setText(neu)
            return
        if rest.aktiv() and rest.vorschau is not None:
            werkzeug = mg.genannt(rest.fraeser(), self.magazin())
            if len(ausgelassen) == 1:
                neu = tr(
                    "ba.raeumen.ausgelassen.rest", text=text, flaeche=flaechen, d=d, t=werkzeug
                )
            else:
                neu = tr(
                    "ba.raeumen.ausgelassen.rest.mehrere", text=text, flaechen=flaechen, d=d,
                    t=werkzeug,
                )  # fmt: skip
        elif len(ausgelassen) == 1:
            neu = tr("ba.raeumen.ausgelassen", text=text, flaeche=flaechen, d=d)
        else:
            neu = tr("ba.raeumen.ausgelassen.mehrere", text=text, flaechen=flaechen, d=d)
        block.ergebnis.setText(neu)

    def _restraeumen_einrichten(self, form):
        """_restraeumen_schritte am Stück (wartet auf die Nebenrechner)."""
        for schritt in self._restraeumen_schritte(form):
            _abwarten(schritt)

    def _restraeumen_schritte(self, form):
        """„Rest räumen“ nach der Vorschau des Räumens (W-013 T3; Manuel: „auch mit mehreren
        Arbeitsschritten“): Lässt das Räumen eine Tasche aus, weil sein Fräser nicht hineinpasst,
        und passt ein kleinerer aus der Werkzeugverwaltung, wird der Block möglich, bekommt den
        größten, der passt, und – solange niemand ihn von Hand gesetzt hat – den Haken. Sonst
        steht er bei dem, was nicht zur Wahl passt. Fährt die Kontur die Wände einer solchen
        Tasche, bekommt auch „Restmaterial“ den Haken: Ihr Fräser kommt dort nicht überall hin.
        Ein Generator wie _block_schritte: Er liefert die Aufträge, auf die er wartet."""
        rest, gross = self.restraeumen, self.raeumen
        ausgelassen = []
        if gross.aktiv() and gross.fraeser() is not None and self.zu_aendern is None:
            ausgelassen = list(getattr(gross.vorschau, "ausgelassen", None) or [])
        passend = None
        if ausgelassen:
            passend = yield from self._restraeumfraeser_schritte(form, ausgelassen)
        moeglich = passend is not None
        geaendert = moeglich != rest.moeglich
        self._fuellt = self._ruhig = True
        try:
            rest.moeglich = moeglich
            rest.haken.setEnabled(moeglich)
            rest.erklaerung.setText(rest.s.text() if moeglich else rest.s.unmoeglich_text())
            if not moeglich:
                rest.haken.setChecked(False)
            elif not rest.von_hand:
                rest.haken.setChecked(True)
            # Der größte, der passt – ein kleinerer, von Hand gewählt, bleibt.
            jetzt = rest.fraeser()
            zu_gross = jetzt is None or (
                moeglich and float(jetzt.durchmesser) > float(passend.durchmesser) + 1e-6
            )
            if moeglich and zu_gross:
                self._fuellt = False  # die Einsätze des neuen Fräsers füllen
                rest.fraeser_setzen(passend)
                self._fuellt = True
            rest.zustand_zeigen()
            wand = self.rest
            an_der_wand = set(_waende_um(form, ausgelassen)) & set(
                self._flaechen(self.kontur, form)
            )
            dazu = rest.aktiv() and self.kontur.aktiv() and bool(an_der_wand)
            if dazu and wand.moeglich and not wand.von_hand:
                wand.haken.setChecked(True)
                wand.zustand_zeigen()
        finally:
            self._fuellt = self._ruhig = False
        if geaendert:
            self._bloecke_ordnen()

    def _nur_eng(self):
        """Was „Rest räumen“ vom Räumen übernimmt: Lässt es enge Gebiete aus, nur sie –
        {"nur_eng": Radius seines Fräsers}; sonst None (die ausgelassenen Taschen ganz)."""
        gross = self.raeumen.fraeser()
        if not self.raeumen.aktiv() or gross is None or not self._kleinerer_raeumfraeser():
            return None
        return {"nur_eng": float(gross.durchmesser) / 2.0}

    def _kleinerer_raeumfraeser(self):
        """Hat „Rest räumen“ einen Fräser, deutlich kleiner als der des Räumens (höchstens drei
        Viertel)? Dann lässt das Räumen enge Gebiete aus (_zusatz, W-034)."""
        gross = self.raeumen.fraeser()
        if gross is None or float(gross.durchmesser) <= 0:
            return False
        grenze = 0.75 * float(gross.durchmesser) + 1e-6
        return any(float(w.durchmesser) <= grenze for w in self.restraeumen._fraeser)

    def _restraeumfraeser_schritte(self, form, ausgelassen):
        """Der größte Fräser der Werkzeugverwaltung, kleiner als der des Räumens, der in alle
        Taschen passt, die es ausließ – None, wenn keiner (ein Generator: Er liefert die Aufträge,
        auf die er wartet). Probiert wird mit der Vorschau, vom größten her; das Ergebnis je Wahl
        gemerkt. Die Vorschauen der Kandidaten rechnen gleichzeitig auf den Nebenrechnern (am
        C-Ring stand das Fenster sonst 1,8 s, unter Last 3,8 s); gewählt wird wie nacheinander."""
        rest, gross = self.restraeumen, self.raeumen
        gross_d = float(gross.fraeser().durchmesser)
        werte = gross.werte()
        schluessel = (
            tuple(ausgelassen),
            round(gross_d, 6),
            round(float(werte["aufmass"]), 6),
            tuple(w.kennung for w in rest._fraeser),
            self.werkstoff(),
        )
        gemerkt = getattr(self, "_restraeumfraeser_gemerkt", None)
        if gemerkt is not None and gemerkt[0] == schluessel:
            return gemerkt[1]
        kandidaten = []
        for werkzeug in sorted(
            (w for w in rest._fraeser if float(w.durchmesser) < gross_d - 1e-6),
            key=lambda w: -float(w.durchmesser),
        ):
            einsaetze = rest._passende_einsaetze(werkzeug, self.werkstoff())
            arten = [e.art for e in einsaetze]
            einsatz = next(
                (einsaetze[arten.index(a)] for a in rest.s.einsatz_reihenfolge if a in arten),
                einsaetze[0] if einsaetze else None,
            )
            if einsatz is not None:
                kandidaten.append((werkzeug, einsatz))
        passend = None
        # Erst einer, der überall bequem hinkommt – ein Gebiet hinter einer Engstelle von außen
        # mit höchstens halb so breitem Fräser (W-034) –, sonst der größte, der überhaupt passt.
        for bequem in (True, False):
            argumente = [
                self._restraeumen_argumente(werkzeug, einsatz, ausgelassen, bequem, werte)
                for werkzeug, einsatz in kandidaten
            ]
            auftraege = [self._restraeumen_auftrag(*a) for a in argumente]
            try:
                for (werkzeug, _einsatz), a, auftrag in zip(
                    kandidaten, argumente, auftraege, strict=True
                ):
                    bahn = None
                    if auftrag is not None:
                        yield auftrag
                        ergebnis = _aus_dem_hintergrund(auftrag)
                        if ergebnis is not None and ergebnis[0] == "fehler":
                            continue  # passt auch nicht
                        if ergebnis is not None:
                            bahn = ergebnis[1][0]
                    if bahn is None:
                        try:
                            bahn = ra.vorschau(self.job, self.job.Model.Group, *a[0], **a[1])
                        except (ValueError, RuntimeError):
                            continue  # passt auch nicht
                    if not bahn.ausgelassen:
                        passend = werkzeug
                        break
            finally:
                _wartende_zurueck(auftraege)
            if passend is not None:
                break
        self._restraeumfraeser_gemerkt = (schluessel, passend)
        return passend

    def _restraeumen_argumente(self, werkzeug, einsatz, ausgelassen, bequem, werte):
        """(Argumente, Schlüsselwörter) für raeumen.vorschau nach Job und Modell – ein Kandidat
        für „Rest räumen“ (_restraeumfraeser_schritte)."""
        rest = self.restraeumen
        return (
            (
                ff.von_werkzeug(werkzeug),
                rest.s.vorschlag("zustellung", werkzeug, einsatz),
                rest.s.vorschlag("zeilenabstand", werkzeug, einsatz),
                float(werte["aufmass"]),
                list(ausgelassen),
            ),
            {
                "schneidenlaenge": float(werkzeug.schneidenlaenge or 0.0),
                "eng_lassen": bequem,
                "nur_eng": (self._nur_eng() or {}).get("nur_eng", 0.0),
            },
        )

    def _restraeumen_auftrag(self, argumente, weiter):
        """Die Vorschau eines Kandidaten für „Rest räumen“ als Auftrag an einen Nebenrechner
        (bearbeitung_vorschau.strategie) – None ohne Nebenrechner, dann rechnet sie hier."""
        from . import nebenrechner as nr

        try:
            pool = nr.pool()
            if not pool.verfuegbar():
                return None
            kopie = pool.kopie(self.job.Document, wiederverwenden=True)
            return pool.auftrag(
                "bearbeitung_vorschau", "strategie", kopie, self.job.Name, "raeumen",
                argumente, weiter, None,
            )  # fmt: skip
        except Exception as fehler:  # noqa: BLE001 – dann rechnet sie hier, wie bisher
            FreeCAD.Console.PrintLog(f"CAM-Addon: Rest räumen im Nebenrechner: {fehler}\n")
            return None

    def _schlichten_danach_einrichten(self, form):
        """„Schlichten danach“ geht, sobald das Räumen angehakt ist und gerechnet hat (nicht beim
        Ändern). Wird es möglich, ist der Fräser des Räumens vorgewählt – mit seinem Einsatz
        „Schlichten“ (einsatz_reihenfolge); einen anderen wählt man von Hand. Angehakt wird es nur
        von Hand: Ob nach dem Räumen geschlichtet wird, entscheidet, wer fräst – außer das Räumen
        räumt bis durch, wo sonst die Kontur die Wände fertig gemacht hätte (Frage 4: „Schlichten
        danach“ macht die Wände)."""
        block = self.schlichten_danach
        # Gibt das Räumen der Nut alle Gründe ab, schlichtet es nach der Nut – mit ihrem Fräser
        # (sonst blieb der Ø 12 des Räumens, der nicht in die Ringnut passt).
        raeumt = self.raeumen.aktiv() and not getattr(self, "_raeumen_bei_nut", False)
        gross = self.raeumen if raeumt else self.nut
        moeglich = self.zu_aendern is None and (raeumt or self._nut_laesst_aufmass())
        geaendert = moeglich != block.moeglich
        self._fuellt = self._ruhig = True
        try:
            block.moeglich = moeglich
            block.haken.setEnabled(moeglich)
            block.erklaerung.setText(block.s.text() if moeglich else block.s.unmoeglich_text())
            if not moeglich:
                block.haken.setChecked(False)
            elif not block.von_hand and gross.fraeser() is not None:
                jetzt = block.fraeser()
                if jetzt is None or jetzt.kennung != gross.fraeser().kennung:
                    self._fuellt = False  # die Einsätze des Fräsers füllen
                    block.fraeser_setzen(gross.fraeser())
                    self._fuellt = True
                waende = set(self._schlichten_danach_zusatz(form).get("wand_flaechen", ()))
                durch = bool(waende & set(self._durch_waende(form)))
                nut = self._nut_laesst_aufmass()
                if (durch or nut) and not block.haken.isChecked():
                    block.haken.setChecked(True)
                    if nut:
                        # Nach der Nut von sich aus mit Messstopp: Schruppen, messen, schlichten
                        # (Manuel, 2026-10-17) – auch neben dem Räumen bis durch (sonst blieben
                        # die Nutwände mit Aufmaß stehen, Gegenleser zu P-41; W-034).
                        block.haken_felder["messstopp"].setChecked(True)
                    geaendert = True
            block.zustand_zeigen()
        finally:
            self._fuellt = self._ruhig = False
        if geaendert:
            self._bloecke_ordnen()

    def _durch_waende(self, form):
        """Die Wände, unter denen das Räumen bis durch räumt (raeumen.durch_ebenen) – leer, wenn
        es nicht angehakt ist."""
        if not self.raeumen.aktiv() or self.raeumen.schon_weg:
            return []  # ohne Räumen – oder es gibt den Haken ab (nichts zu tun)
        return [f for f in self._eigene(self.raeumen, form) if ra.durchgehend(form, f)]

    def _schlichtzug_zeit(self, form):
        """Minuten, die „Schlichten danach“ an den Wänden braucht, unter denen das Räumen bis
        durch räumt – gerechnet, sobald der Block seine Vorschau hat (Auftrag 4, Fable-Aufträge),
        bis dahin geschätzt (_durch_schlichtzug). Gemerkt je Wände, Fräser und Aufmaß: Verliert
        das Räumen mit der gerechneten Zeit, ist der Block nicht mehr möglich und hätte keine –
        mit der Schätzung gewänne das Räumen wieder, der Haken spränge hin und her."""
        durch = tuple(
            sorted(f for f in self._eigene(self.raeumen, form) if ra.durchgehend(form, f))
        )
        werkzeug = self.raeumen.fraeser()
        if not durch or werkzeug is None:
            return 0.0
        schluessel = (durch, werkzeug.kennung, float(self.raeumen.werte().get("aufmass") or 0.0))
        merk = getattr(self, "_schlichtzug_merk", None)
        if merk is None:
            merk = self._schlichtzug_merk = {}
        block = self.schlichten_danach
        zeit = block.zeit if block.aktiv() and block.vorschau is not None else None
        if zeit is not None and zeit > 0 and block.werte().get("waende"):
            zusatz = self._schlichten_danach_zusatz(form)
            waende = tuple(sorted(zusatz.get("wand_flaechen") or ()))
            # Nur die Wände (ein Boden dazu zählte mit): dann ist es die Zeit dieser Wände.
            if waende == durch and not zusatz.get("boden_flaechen"):
                merk[schluessel] = float(zeit)
        if schluessel in merk:
            return merk[schluessel]
        return self._durch_schlichtzug(form)

    def _durch_schlichtzug(self, form):
        """Minuten, die „Schlichten danach“ an den Wänden braucht, unter denen das Räumen bis
        durch räumt – geschätzt: ein Zug an jeder ihrer Unterkanten im Vorschub des Räumens. Im
        Wettbewerb gegen eine Kontur, die selbst schlichtet, kommt das zum Räumen dazu (sonst
        verglich er Schruppen gegen Schruppen und Schlichten). 0 ohne solche Wände."""
        durch = [f for f in self._eigene(self.raeumen, form) if ra.durchgehend(form, f)]
        werkzeug, einsatz = self.raeumen.fraeser(), self.raeumen.einsatz()
        if not durch or werkzeug is None or einsatz is None:
            return 0.0
        _n, vorschub, _senkrecht = js.werte_im_job(werkzeug, einsatz, self.job)
        if vorschub <= 0:
            return 0.0
        laenge = sum(k.Length for w in kb.waende(form, durch) for k in w.kanten)
        return laenge / vorschub

    def _nut_laesst_aufmass(self):
        """Lässt die Nut an ihren Wänden das Aufmaß stehen (angehakt, Aufmaß, kein Schlichtgang
        im selben Durchgang) – dann macht „Schlichten danach“ die Wände fertig?"""
        nut = self.nut
        if not nut.aktiv():
            return False
        werte = nut.werte()
        return float(werte.get("aufmass") or 0.0) > 0 and not werte.get("schlichten")

    def _schlichten_danach_zusatz(self, form):
        """Was „Schlichten danach“ vom Räumen übernimmt: die Böden, die es räumt, die Wände um sie –
        ohne die, die die Kontur schon fährt –, seine Aufmaße und den Gleichlauf. Ohne Räumen von
        der Nut: ihre Wände mit ihrem Aufmaß (der Grund ist auf Tiefe)."""
        raeumen = self.raeumen
        nut_waende, nut_aufmass = [], 0.0
        ringe, ring_waende = [], []
        enge, enge_waende = [], []
        if self._nut_laesst_aufmass():
            werte_nut = self.nut.werte()
            schlicht = self.schlichten_danach.fraeser()
            r_s = float(getattr(schlicht, "durchmesser", 0.0) or 0.0) / 2
            for name in self._flaechen(self.nut, form):
                for n in nb.nuten(form, [name]):
                    if r_s > 0 and nb.verfahren(n, r_s) == "zu_schmal":
                        # Der Fräser des Schlichtens passt nicht hinein: Die Kontur führe an der
                        # einen Wand durch die andere (am C-Ring Ø 12 in der 10 mm breiten Nut,
                        # beide Stege 5 mm tief weg, W-029) – die Wände schlichtet eine Nut „nur
                        # schlichten“ mit dem Fräser der Nut.
                        if name not in enge:
                            enge.append(name)
                        enge_waende += [w for w in n.waende if w not in enge_waende]
                    elif n.ring:
                        # Die Ringnut schlichtet eine Nut „nur schlichten“ – beide Wände, auch
                        # eine Fase außen (die Kontur führe nur die senkrechte).
                        if name not in ringe:
                            ringe.append(name)
                        ring_waende += [w for w in n.waende if w not in ring_waende]
                    else:
                        nut_waende += [w for w in n.waende if w not in nut_waende]
            nut_aufmass = float(werte_nut["aufmass"])
        ring_zusatz = {"nut_ringe": ringe, "nut_ring_waende": ring_waende} if ringe else {}
        if enge:
            nf = self.nut.fraeser()
            ring_zusatz.update(
                nut_eng=enge,
                nut_eng_waende=enge_waende,
                nut_eng_radius=float(nf.durchmesser) / 2,
                nut_eng_schneide=float(getattr(nf, "schneidenlaenge", 0.0) or 0.0),
            )
        if not raeumen.aktiv() or getattr(self, "_raeumen_bei_nut", False):
            if not nut_waende and not ringe and not enge:
                return {}
            return {
                "boden_flaechen": [],
                "wand_flaechen": nut_waende,
                "aufmass_wand": nut_aufmass,
                "aufmass_boden": 0.0,
                "gleichlauf": bool(self.nut.werte()["gleichlauf"]),
                **ring_zusatz,
            }
        werte = raeumen.werte()
        geraeumt = sorted(self._raeumt(form))
        # Wände, unter denen das Räumen bis durch räumt (raeumen.durch_ebenen): selbst Wände.
        durch = [f for f in geraeumt if ra.durchgehend(form, f)]
        boeden = [f for f in geraeumt if f not in durch]
        kontur = set(self._flaechen(self.kontur, form)) if self.kontur.aktiv() else set()
        # Räumen und Nut zusammen (Gegenleser zu P-41): die Wände der Nut dazu, das größere Aufmaß
        # – die Kontur nimmt so viel weg und macht beide auf Maß.
        waende = [w for w in _waende_um(form, boeden) + durch + nut_waende if w not in kontur]
        # Nicht die Wände, vor denen kein Rohteil steht (der Mantel im Rundmaterial, W-034).
        waende = [w for w in dict.fromkeys(waende) if not self._ohne_rohteil(form, w)]
        waende = [w for w in waende if w not in ring_waende and w not in enge_waende]
        return {
            "boden_flaechen": boeden,
            "wand_flaechen": waende,
            "aufmass_wand": max(float(werte["aufmass"]), nut_aufmass),
            "aufmass_boden": float(werte["aufmass_boden"]),
            "gleichlauf": bool(werte["gleichlauf"]),
            **ring_zusatz,
        }

    def _schon_weg_abhaken(self):
        """Wer „Hier ist nichts mehr zu tun“ sagt (Materialstand, W-012), verliert den Haken –
        solange ihn niemand von Hand gesetzt hat; sonst stünde dort ein Haken, und „Anlegen“
        ginge nicht."""
        weg = [b for b in self.bloecke if b.aktiv() and b.schon_weg and not b.von_hand]
        if not weg:
            return
        self._fuellt = True
        try:
            for block in weg:
                block.haken.setChecked(False)
                block.zustand_zeigen()
        finally:
            self._fuellt = False
        self.nichts_angehakt.setVisible(not self.aktive_bloecke())

    def _ziel_zeigen(self, form):
        """Wie viel weg muss und wie lange der Fräser des Räumens (sonst des Planfräsens, der
        Kontur) mit seinen Werten dafür mindestens braucht – mit dem ap, das jede Stelle hergibt
        – und welcher Fräser der Werkzeugkiste schneller wäre (zielzeit; Manuel, 2026-10-02)."""
        self.ziel_text.setText("")
        self._schneller = None
        self.knopf_schneller.hide()
        material = self._ziel_material(form)
        if material is None or material.volumen <= 0:
            return
        volumen = groesse_fest(material.volumen / 1000.0, einheiten.VOLUMEN, 1)
        saetze = [
            tr("ba.ziel.volumen", volumen=f"{volumen} {einheiten.einheit(einheiten.VOLUMEN)}")
        ]
        eigene = None
        # Die angehakten zuerst: Nach „Übernehmen“ räumt oft das Planfräsen allein, und das
        # Räumen behält nur den Fräser für den Rest.
        bloecke = (self.raeumen, self.plan, self.kontur, self.nut)
        for block in sorted(bloecke, key=lambda b: not b.aktiv()):
            werkzeug, einsatz = block.fraeser(), block.einsatz()
            werte = zz.werte(werkzeug, einsatz) if werkzeug and einsatz else None
            if werte is not None and werkzeug.art in zz.WEGNEHMER:
                eigene = (werkzeug, zz.ziel(material, werkzeug.durchmesser / 2, *werte))
                break
        if eigene is not None:
            werkzeug, ziel = eigene
            ap = groesse_zeigen(ziel.ap_wirksam, einheiten.LAENGE, 1) or "0"
            saetze.append(
                tr(
                    "ba.ziel.mit",
                    werkzeug=_ziel_werkzeug(werkzeug),
                    zeit=_ziel_minuten(ziel.zeit),
                    ap=f"{ap} {einheiten.einheit(einheiten.LAENGE)}",
                    anteil=int(round(100.0 * ziel.ap_wirksam / ziel.ap)),
                )
            )
            if ziel.rest > 0.02 * material.volumen:
                rest = groesse_fest(ziel.rest / 1000.0, einheiten.VOLUMEN, 1)
                saetze.append(
                    tr("ba.ziel.rest", rest=f"{rest} {einheiten.einheit(einheiten.VOLUMEN)}")
                )
        angebote = []
        if self.bibliothek is not None:
            # An der Stange der Drehmaschine nur die Fräser, die von vorn gehen (axial, W-025).
            werkzeuge = [w for w in self.bibliothek.werkzeuge if self.von_vorn_moeglich(w)]
            angebote = zz.vergleiche(material, werkzeuge, self.werkstoff())
            # Keiner, der nicht in die gewählten Flächen kommt (_flaechenfraeser_waehlen).
            angebote = [a for a in angebote if self._passt_angebot(form, a)]
        if angebote:
            beste = angebote[0]
            vergleich = None
            if eigene is not None:
                gleich = [a for a in angebote if a.werkzeug.kennung == eigene[0].kennung]
                vergleich = gleich[0].zeit if gleich else eigene[1].zeit
            # Schon in den angehakten Strategien (übernommen): kein Angebot mehr.
            genutzt = {
                b.fraeser().kennung
                for b in (self.plan, self.raeumen, self.kontur, self.rest, self.nut)
                if b.aktiv() and b.fraeser() is not None
            }
            schon = beste.werkzeug.kennung in genutzt and (
                beste.danach is None or beste.danach.werkzeug.kennung in genutzt
            )
            if not schon and (
                eigene is None
                or (beste.werkzeug.kennung != eigene[0].kennung and beste.zeit < 0.8 * vergleich)
            ):
                wer = _ziel_werkzeug(beste.werkzeug)
                if beste.danach is not None:
                    wer = tr(
                        "ba.ziel.danach", werkzeug=wer, rest=_ziel_werkzeug(beste.danach.werkzeug)
                    )
                saetze.append(tr("ba.ziel.schneller", werkzeug=wer, zeit=_ziel_minuten(beste.zeit)))
                if self.zu_aendern is None:
                    self._schneller = beste
                    self.knopf_schneller.show()
        self._passt_zeigen()
        self.ziel_text.setText(" ".join(saetze))
        self._ziel_je_block(form, material)

    def schneller_uebernehmen(self):
        """„Übernehmen“ unter der Ziel-Zeile: die schnelleren Fräser in die Strategien – ein
        Planfräser ins Planfräsen und der für den Rest ins Räumen (das Räumen nimmt dann nur
        die Taschenböden, _folge), ein Schaftfräser ins Räumen und der für den Rest ins
        Restmaterial. Gibt zurück, ob sich etwas geändert hat."""
        angebot = self._schneller
        if angebot is None or self.job is None:
            return False
        erster = angebot.werkzeug
        rest = angebot.danach.werkzeug if angebot.danach is not None else None
        if erster.art == wz.PLANFRAESER:
            paare = ((self.plan, erster), (self.raeumen, rest))
        else:
            paare = ((self.raeumen, erster), (self.rest, rest))
        geaendert = False
        for block, werkzeug in paare:
            if werkzeug is not None and block.fraeser_setzen(werkzeug):
                geaendert = True
        if geaendert:
            self.knopf_schneller.hide()
            self.vorschau_starten()
        return geaendert

    def _ziel_je_block(self, form, material):
        """Hinter die Zeit von Planfräsen und Räumen, wie gut ihr Weg ist (Manuel, 2026-10-02:
        „Ist diese Wegestrategie wirklich gut?“): ihre Zeit geteilt durch die Zielzeit ihres
        Fräsers mit ihren Werten für das, was bis zu ihren Flächen weg muss – „1,03 × Ziel“.
        Räumt das Räumen nach dem Planfräsen nur die Taschenböden, zählt nur die Tasche."""
        for block in (self.plan, self.raeumen):
            werkzeug, einsatz, basis = block.fraeser(), block.einsatz(), block.ergebnis_basis
            text = block.ergebnis.text()
            if None in (block.zeit, werkzeug, einsatz) or not basis or not text.startswith(basis):
                continue
            ebenen = hf.ebenen_oben(form, self._flaechen(block, form))
            if not ebenen:
                continue
            oben = None
            if block is self.raeumen and self._raeumen_boeden is not None:
                plan = hf.ebenen_oben(form, self._flaechen(self.plan, form))
                oben = min(e.z for e in plan) if plan else None
            werte = block.werte()
            try:
                ae, ap = float(werte["zeilenabstand"]), float(werte["zustellung"])
            except (TypeError, ValueError):
                continue
            ziel = zz.ziel(
                material.bis(min(e.z for e in ebenen), oben),
                werkzeug.durchmesser / 2,
                ae,
                ap,
                js.werte_im_job(werkzeug, einsatz, self.job)[1],
            )
            if not (0 < ziel.zeit < math.inf):
                continue
            # Gleich hinter die Zeit – was danach steht (Zeilenrichtung, Vergleich, Folge), bleibt.
            zeit = _zeit_text(block.zeit)
            ende = basis.find(zeit) + len(zeit)
            if ende < len(zeit):
                continue
            faktor = dezimal(f"{block.zeit / ziel.zeit:.2f}")
            neu = tr("ba.ziel.faktor", text=basis[:ende], faktor=faktor)
            if not text.startswith(neu):
                block.ergebnis.setText(neu + text[ende:])

    def _ziel_material(self, form):
        """Das Material zwischen Rohteil (Kasten des Jobs) und Teil (zielzeit.Material) – einmal
        gerechnet je Teil und Rohteil –, darin, was nach den Operationen im Job noch steht (der
        Materialstand, W-012; beim Ändern vor der Operation): Was eine Operation davor schon
        weggenommen hat, muss nicht mehr weg."""
        rohteil = getattr(self.job, "Stock", None)
        if rohteil is None or getattr(rohteil, "Shape", None) is None or rohteil.Shape.isNull():
            return None
        kasten, teil = rohteil.Shape.BoundBox, form.BoundBox
        schluessel = tuple(
            round(w, 6)
            for w in (kasten.XMin, kasten.XMax, kasten.YMin, kasten.YMax, kasten.ZMax)
            + (teil.XMin, teil.XMax, teil.YMin, teil.YMax, teil.ZMin, teil.ZMax, _volumen(form))
        )
        gemerkt = getattr(self, "_ziel_gemerkt", None)
        if gemerkt is not None and gemerkt[0] == schluessel:
            material = gemerkt[1]
        else:
            try:
                material = zz.material(
                    form, (kasten.XMin, kasten.XMax, kasten.YMin, kasten.YMax), kasten.ZMax
                )
            except Exception:  # ein Teil, das sich nicht vernetzen lässt: ohne Ziel
                material = None
            self._ziel_gemerkt = (schluessel, material)
        stand = mst.fuer(self.job, vor=self.zu_aendern) if material is not None else None
        if stand is None:
            return material
        gemerkt = getattr(self, "_ziel_stand", None)
        if gemerkt is None or gemerkt[0] != (schluessel, stand.kennung):
            gemerkt = (
                (schluessel, stand.kennung),
                material.unter(stand.hoehen_an(material.x, material.y)),
            )
            self._ziel_stand = gemerkt
        return gemerkt[1]

    def _kontur_text(self, form, zusatz):
        """Der Satz der Kontur, wenn ein anderer Block vor ihr neben den Wänden räumt."""
        if not zusatz or not self.kontur.ergebnis_basis:
            return
        davor = self._kontur_davor(form)
        if davor == "planen":
            text = tr("ba.kontur.nach_planen", text=self.kontur.ergebnis_basis)
        elif davor == "raeumen":
            text = tr("ba.kontur.nach_raeumen_boden", text=self.kontur.ergebnis_basis)
        else:
            text = tr("ba.kontur.nach_raeumen", text=self.kontur.ergebnis_basis)
        self.kontur.ergebnis.setText(text)

    def _in_anlege_reihe(self, bloecke, form=None):
        """`bloecke` in der Reihenfolge, in der sie in den Job kommen: „Schlichten danach“ hinter
        der Nut gleich nach ihr (und nach dem Räumen, wenn es angehakt ist) – Nut, Messstopp, Nut
        schlichten (P-2026-10-17-41). Dieselbe Reihenfolge gilt für den Materialstand der
        Vorschau (P-2026-10-18-64: sonst stand „Schlichten danach“ vor der Nut, nahm ihr alles weg,
        und die Nut verlor bei jeder Änderung den Haken – „Hier ist nichts mehr zu tun“). Bei
        „Flanke grob, Spirale fertig“ (W-039, mit `form`) die Flanke vor das 3D-Schlichten – in
        STRATEGIEN steht es davor, und die Spirale schlichtete die Wände, bevor die Flanke sie
        schruppt (P-2026-10-25-61). In der Frage „Reihenfolge“ „Erst alles schruppen“ gewählt: je
        Block sein Abschnitt (SCHRUPPEN_ZUERST)."""
        reihe = list(bloecke)
        schruppen_zuerst = self._weg.get("reihenfolge") == "schruppen"
        if schruppen_zuerst:  # stabil: in jedem Abschnitt die Folge von vorher
            reihe.sort(key=lambda b: SCHRUPPEN_ZUERST.get(b.s.kennung, 2))
        if (
            form is not None
            and self.flanke in reihe
            and self.schlichten3d in reihe
            and self._spirale_nach_flanke(form)
        ):
            reihe.remove(self.flanke)
            reihe.insert(reihe.index(self.schlichten3d), self.flanke)
        danach = self.schlichten_danach
        if danach not in reihe or not danach.aktiv() or schruppen_zuerst:
            return reihe  # schruppen zuerst: es steht schon am Anfang des Schlichtens
        # Schruppen – messen – schlichten (Manuel, 2026-10-17): hinter alles, was Wände schruppt –
        # auch hinter die Kontur (am C-Ring kam sie nach Messstopp und Schlichten, W-034).
        quellen = [self.raeumen, self.restraeumen, self.kontur]
        if self.nut.aktiv() and self._nut_laesst_aufmass():
            quellen.append(self.nut)
        quellen = [b for b in quellen if b in reihe and b.aktiv()]
        if quellen:
            reihe.remove(danach)
            reihe.insert(max(reihe.index(b) for b in quellen) + 1, danach)
        return reihe

    def _materialstand(self, block, form, flaechen=None, mit=()):
        """_materialstand_schritte am Stück."""
        return rw.zu_ende(self._materialstand_schritte(block, form, flaechen, mit))

    def _materialstand_schritte(self, block, form, flaechen=None, mit=()):
        """Der Materialstand vor dem Block (W-012): das Rohteil, die Operationen, die im Job
        schon stehen – beim Ändern die vor der Operation –, dazu die Vorschauen der angehakten
        Blöcke davor in diesem Lauf (sie werden vor ihm angelegt; die in `mit` auch ohne Haken).
        Wer dieselben Flächen hat (`flaechen`, ohne: die des Blocks), tritt gegen ihn an und
        kommt nicht davor (Räumen und Planfräsen am Grund der Nut). None ohne Materialstand."""
        if self.zu_aendern is not None:
            return (yield from mst.fuer_schritte(self.job, vor=self.zu_aendern))
        eigene = set(self._flaechen(block, form) if flaechen is None else flaechen)
        dazu = []
        for anderer in self._in_anlege_reihe(self.bloecke, form):
            if anderer is block:
                break
            werkzeug = anderer.fraeser()
            dabei = anderer.aktiv() or anderer in mit
            if not dabei or anderer.vorschau is None or werkzeug is None:
                continue
            if eigene & set(self._flaechen(anderer, form)):
                continue
            fraeser = ff.von_werkzeug(werkzeug)
            if fraeser is not None:
                dazu.append((anderer.s.titel(), anderer.vorschau.punkte, fraeser))
        return (yield from mst.fuer_schritte(self.job, dazu=dazu))

    def _zusatz(self, block, form, flanke=None):
        """Was der Assistent einem Block vorgibt: Räumt das Räumen den Boden einer Tasche, deren
        Wände die Kontur fährt, und ist die Breite der Kontur leer, dann steht neben den Wänden
        nur noch das Aufmaß des Räumens – die Kontur schlichtet nur noch (Räumen + Kontur mit
        Breite = Aufmaß, die schnellste Folge in der Tasche; Spezifikation Abschnitt 11). Fräst
        das Planfräsen die Böden vor allen Wänden (ein Absatz), steht dort höchstens sein Rest
        an der Wand (P-2026-10-02-17). `flanke`: die Bahn der Flanke für das Vorschlichten des
        3D-Schlichtens (_vorschlichten_zusatz) – ohne: ihre Vorschau."""
        if block is self.gewindefraesen:
            return {"werkzeug": block.fraeser()}  # Steigung und Zähne kennt CAM nicht
        if block is self.raeumen:
            # Enge Gebiete lässt es dem kleineren Fräser von „Rest räumen“ (W-034) – nur, wenn die
            # Kiste einen hat; sonst räumt es sie selbst (wie bisher, mit Helix). Dazu der Bohrer
            # fürs Vorbohren, wenn einer passt (_vorbohrer).
            zusatz = {"eng_lassen": True} if self._kleinerer_raeumfraeser() else {}
            bohrer = self._vorbohrer(block.fraeser())
            if bohrer is not None:
                zusatz["vorbohrer"] = bohrer
            return zusatz or None
        if block is self.nut:
            liste = self._vorbohrer_liste(block.fraeser())
            return {"vorbohrer_liste": liste} if liste else None
        if block is self.restraeumen:
            return self._nur_eng()
        if block is self.bohren:
            zusatz = {"reiben": True} if self._gerieben(form) else {}
            neben = self._nebenbohrer_zusatz(form)
            if neben:
                zusatz["nebenbohrer"] = neben
            return zusatz or None
        if block is self.rest:
            if self.rest.felder["davor"].text().strip():
                return None  # von Hand eingetragen
            davor = self._davor_durchmesser()
            return {"davor": davor} if davor else None
        if block is self.restschlichten:
            return self._davor_3d(self.restschlichten, self.schlichten3d)
        if block is self.schlichten3d:
            return self._vorschlichten_zusatz(form, flanke)
        if block is self.flanke:
            if self.flanke.felder["aufmass"].text().strip():
                return None  # von Hand eingetragen
            if self._spirale_nach_flanke(form):
                return {"aufmass": FLANKE_VOR_SPIRALE}
            return None
        if block is self.schlichten_danach:
            return self._schlichten_danach_zusatz(form)
        if block is self.restschruppen:
            return self._davor_3d(self.restschruppen, self.schruppen3d)
        if block is not self.kontur or self.kontur.felder["breite"].text().strip():
            return None  # die Breite von Hand eingetragen
        davor = self._kontur_davor(form)
        if davor in ("tasche", "raeumen"):
            return {"breite": max(float(self.raeumen.werte()["aufmass"]), 0.01)}
        if davor == "planen":
            return {"breite": pfb.rest_an_der_wand(float(self.plan.werte()["zeilenabstand"]))}
        return None

    def _kontur_davor(self, form):
        """Wer vor der Kontur neben ihren Wänden räumt: „tasche“ – das Räumen den Boden einer
        Tasche, deren Wände sie fährt; „raeumen“, „planen“ – das Räumen, das Planfräsen die Böden
        vor allen ihren Wänden (ein Absatz, ein Zapfen); sonst None. An einem Absatz fuhr die
        Kontur sonst alle Bahnen vom Rohteil her noch einmal, durch Luft (P-2026-10-02-17)."""
        if self.raeumen.aktiv():
            waende = self.kontur.s.flaechen_fuer(form, self.gewaehlte)
            boeden = set(rb.taschenboeden(form, waende))
            # Nur, wenn das Räumen jede dieser Taschen auch räumt: In eine, in die sein Fräser
            # nicht passt, führe die Kontur sonst mit „nur das Aufmaß“ ins Volle (B-007) – dann
            # sieht sie selbst nach, was noch steht (Materialstand).
            if boeden and boeden <= self._raeumt(form):
                return "tasche"
            if boeden & set(self._flaechen(self.raeumen, form)):
                return None
        vor = kb.boeden_vor(form, self._flaechen(self.kontur, form))
        if vor:
            if self.raeumen.aktiv() and vor <= self._raeumt(form):
                return "raeumen"
            if self.plan.aktiv() and vor <= set(self._flaechen(self.plan, form)):
                return "planen"
        return None

    def _davor_durchmesser(self):
        """Der Ø des Fräsers vor dem Restmaterial: eingetragen, sonst der der Kontur, sonst der
        des Räumens in diesem Fenster – None, wenn keiner da ist."""
        text = self.rest.felder["davor"].text().strip()
        if text:
            try:
                return groesse_lesen(text, einheiten.LAENGE)
            except ValueError:
                return None
        for gross in (self.kontur, self.raeumen):
            if gross.aktiv() and gross.fraeser() is not None:
                return float(gross.fraeser().durchmesser)
        return None

    def _davor_3d(self, rest, gross):
        """{"davor": Ø, "davor_eck": Eckenradius} des Fräsers vor dem Block `rest`
        (Restschlichten, Restschruppen): ist das Feld leer, der des Blocks `gross` in diesem
        Fenster (mit seiner Form); beim Ändern der Eckenradius der Operation, solange ihr Ø im
        Feld steht – sonst None (von Hand eingetragen: eine Kugel beim Restschlichten, ein
        Schaftfräser beim Restschruppen)."""
        text = rest.felder["davor"].text().strip()
        if not text:
            werkzeug = gross.fraeser() if gross.aktiv() else None
            form = ff.von_werkzeug(werkzeug) if werkzeug is not None else None
            if form is None:
                return None
            return {"davor": float(werkzeug.durchmesser), "davor_eck": s3op.eckenradius(form)}
        op = self.zu_aendern
        if op is None or not rest.s.ist(op):
            return None
        try:
            durchmesser = groesse_lesen(text, einheiten.LAENGE)
        except ValueError:
            return None
        if abs(durchmesser - float(op.DurchmesserDavor)) > 1e-6:
            return None
        return {"davor_eck": float(op.EckenradiusDavor)}

    def _restschlichtfraeser_waehlen(self):
        """Wählt in den Blöcken Restschlichten und Restschruppen den größten Fräser, der kleiner
        ist als der davor – wenn der gewählte es nicht ist."""
        for rest, gross in (
            (self.restschlichten, self.schlichten3d),
            (self.restschruppen, self.schruppen3d),
        ):
            davor = (self._davor_3d(rest, gross) or {}).get("davor")
            if davor is None:
                text = rest.felder["davor"].text().strip()
                try:
                    davor = groesse_lesen(text, einheiten.LAENGE) if text else None
                except ValueError:
                    davor = None
            if not davor:
                continue
            jetzt = rest.fraeser()
            if jetzt is not None and jetzt.durchmesser < davor - 1e-6:
                continue
            kleiner = [
                (w.durchmesser, i)
                for i, w in enumerate(rest._fraeser)
                if w.durchmesser < davor - 1e-6
            ]
            if kleiner:
                rest.wahl_fraeser.setCurrentIndex(max(kleiner)[1])

    def _fase_fasenfraeser(self, form):
        """[Fasenfräser] in der Auswahl des Blocks „Fase“, deren Kegel zu allen angeklickten
        Fasen passt."""
        block = self.fase
        if not block.moeglich:
            return []
        fasen = fb.fasen(form, block.s.flaechen_fuer(form, self._wahl(block)))
        if not fasen:
            return []
        return [
            w
            for w in block._fraeser
            if w.art == wz.FASENFRAESER and all(fb.kegel_passt(f, wf.kegel(w)[2]) for f in fasen)
        ]

    def _fase_fraeser_waehlen(self, form):
        """Der Fräser im Block „Fase“ (W-037; Manuel, 2026-10-24: „A wenns einen gibt … wenn in der
        werkzeugverwaltung ein fasenfräser ist .. sollte man fragen .. hey willst du den haben ?“):
        Steht ein Fasenfräser ihres Winkels im Magazin der Maschine, ist er gewählt – eine Runde.
        Sonst ein Schaftfräser in Stufen, der an die Fase herankommt (_fase_schaftfraeser); steht
        ein Fasenfräser nur in der Werkzeugverwaltung, fragt der Satz darunter, ob man ihn will.
        Von Hand gewählt bleibt, was gewählt ist, beim Ändern der der Operation."""
        block = self.fase
        passende = self._fase_fasenfraeser(form) if block.aktiv() else []
        # Beim Ändern bleibt der Fräser der Operation (er stand nicht im Magazin – der Assistent
        # hätte den Fasenfräser sonst gegen einen Schaftfräser getauscht).
        if block.aktiv() and not block.fraeser_von_hand and self.zu_aendern is None:
            magazin = self.magazin() if passende else None
            im_magazin = [
                w
                for w in (passende if magazin is not None else [])
                if mg.rang(w, magazin) != mg.NICHT_IM_MAGAZIN
            ]
            ziel = im_magazin[0] if im_magazin else self._fase_schaftfraeser(form)
            jetzt = block.fraeser()
            if ziel is not None and (jetzt is None or ziel.kennung != jetzt.kennung):
                block._setzt_selbst = True
                try:
                    block.fraeser_setzen(ziel)
                finally:
                    block._setzt_selbst = False
        self._fase_angebot(passende)

    def _fase_schaftfraeser(self, form):
        """Der Schaftfräser für die Fase: von den Fräsern der angehakten Blöcke davor der größte,
        der an sie herankommt (fase_bahn.fraeser_passt – am Messspitzenhalter der der Nut, kein
        Werkzeugwechsel); sonst der vorgewählte, wenn er passt; sonst der größte, der passt. None,
        wenn keiner passt (dann bleibt der vorgewählte, und der Satz bietet den kleineren an)."""
        block = self.fase
        fasen = fb.fasen(form, block.s.flaechen_fuer(form, self._wahl(block)))
        schaft = [w for w in block._fraeser if w.art != wz.FASENFRAESER]
        if not fasen or not schaft:
            return None
        kennungen = {w.kennung for w in schaft}
        im_job = {}
        for anderer in self._in_anlege_reihe(self.bloecke, form):
            if anderer is block:
                break
            werkzeug = anderer.fraeser() if anderer.aktiv() else None
            if werkzeug is not None and werkzeug.kennung in kennungen:
                im_job[werkzeug.kennung] = werkzeug

        def passt(w):
            return fb.fraeser_passt(form, fasen, float(w.durchmesser) / 2)

        jetzt = block.fraeser()
        reihe = sorted(im_job.values(), key=lambda w: -w.durchmesser)
        if jetzt is not None and jetzt.art != wz.FASENFRAESER:
            reihe.append(jetzt)
        reihe += sorted(schaft, key=lambda w: -w.durchmesser)
        return next((w for w in reihe if passt(w)), None)

    def _fase_angebot(self, passende=None):
        """Der Satz mit Knöpfen im Block „Fase“: Kommt der Schaftfräser nicht an die Fase (die
        Vorschau sagt es rot), der nächstkleinere – „T4 nehmen“ (genommen erst auf Klick, wie bei
        Planfräsen und Räumen); steht ein passender Fasenfräser in der Werkzeugverwaltung und ist
        nicht schon einer gewählt, „In der Werkzeugverwaltung steht T6 … Nehmen?“."""
        block = self.fase
        if passende is None:
            if self.job is None or not block.aktiv():
                passende = []
            else:
                passende = self._fase_fasenfraeser(vr.modell(self.job).Shape)
        jetzt = block.fraeser()
        saetze, knoepfe = [], []
        gescheitert = (
            block.aktiv()
            and block.vorschau is None
            and not block.schon_weg
            and bool(block.hinweis.text())
        )
        if gescheitert and jetzt is not None and jetzt.art != wz.FASENFRAESER:
            kleinere = [
                w
                for w in block._fraeser
                if w.art != wz.FASENFRAESER and w.durchmesser < jetzt.durchmesser - 1e-6
            ]
            if kleinere:
                kleiner = max(kleinere, key=lambda w: w.durchmesser)
                saetze.append(
                    tr(
                        "ba.fase.kleiner",
                        werkzeug=_ziel_werkzeug(jetzt),
                        kleiner=_ziel_werkzeug(kleiner),
                    )
                )
                knoepfe.append(
                    (
                        tr("ba.fase.angebot.knopf", nummer=wz.nummer_text(kleiner)),
                        lambda: self._fase_fraeser_nehmen(kleiner),
                    )
                )
        if passende and (jetzt is None or jetzt.art != wz.FASENFRAESER):
            werkzeug = passende[0]
            winkel = f"{round(wf.kegel(werkzeug)[2], 1):g}"
            saetze.append(tr("ba.fase.angebot", werkzeug=_ziel_werkzeug(werkzeug), winkel=winkel))
            knoepfe.append(
                (
                    tr("ba.fase.angebot.knopf", nummer=wz.nummer_text(werkzeug)),
                    lambda: self._fase_fraeser_nehmen(werkzeug),
                )
            )
        if saetze:
            block.angebot.zeigen(dezimal(" ".join(saetze)), knoepfe)
        else:
            block.angebot.leeren()

    def _fase_fraeser_nehmen(self, werkzeug):
        """„T6 nehmen“: dieser Fräser im Block „Fase“ – der Fasenfräser (eine Runde statt der
        Stufen) oder der kleinere Schaftfräser."""
        block = self.fase
        if block.fraeser_setzen(werkzeug):
            block.fraeser_von_hand = True
            block.angebot.leeren()
            self.vorschau_starten()

    def _restfraeser_waehlen(self):
        """Wählt im Block Restmaterial den größten Fräser, der kleiner ist als der davor – wenn
        der gewählte es nicht ist."""
        davor = self._davor_durchmesser()
        if not davor:
            return
        jetzt = self.rest.fraeser()
        if jetzt is not None and jetzt.durchmesser < davor - 1e-6:
            return
        kleiner = [
            (w.durchmesser, i)
            for i, w in enumerate(self.rest._fraeser)
            if w.durchmesser < davor - 1e-6
        ]
        if kleiner:
            self.rest.wahl_fraeser.setCurrentIndex(max(kleiner)[1])

    def _rest_vorschlagen(self, form):
        """Der Haken bei „Restmaterial“, wenn die Kontur gezeichnete Rundungen innen fährt, die
        kleiner sind als ihr Fräser, und ein kleinerer da ist (Manuel, 2026-10-02: „Ja“) – sonst
        blieb in einer Ecke R 4 nach dem Ø 12 R 6 stehen. Von Hand gesetzt bleibt er, wie er ist."""
        rest = self.rest
        klein = rest.fraeser()
        if rest.von_hand or not rest.moeglich or klein is None or not self.kontur.aktiv():
            return
        gross = self.kontur.fraeser()
        if gross is None or float(klein.durchmesser) >= float(gross.durchmesser) - 1e-6:
            return
        waende = rest.s.flaechen_fuer(form, self.gewaehlte)
        bohrungen = {b.name for b in bb.bohrungen(form, waende)}
        radius = float(gross.durchmesser) / 2
        if any(
            r < radius - 1e-6 and name not in bohrungen
            for name, r in kb.innenrundungen(form, waende)
        ):
            self._fuellt = True
            try:
                rest.haken.setChecked(True)
                rest.zustand_zeigen()
            finally:
                self._fuellt = False

    def _flaechen(self, block, form):
        """Die Flächen des Blocks – beim Räumen ohne die, die das Planfräsen schon fräst
        (_folge: dann nur die Taschenböden); beim Bohrungsfräsen ohne die, die das Bohren
        bohrt, wenn beide nicht um dieselben Bohrungen wetteifern (ein Flansch: der Bohrer die
        Lochkreisbohrungen, der Fräser die große in der Mitte; P-2026-10-02-12)."""
        flaechen = self._eigene(block, form)
        if block is self.raeumen:
            # Die Gründe der Nuten fräst die Nut, wenn sie angehakt ist und nicht um genau dieselben
            # Flächen wetteifert (W-034, wie die Kontur ihre Wände auslässt).
            weg = set()
            if self.nut.aktiv() and not self._gleiche_flaechen(block, form, self.nut):
                weg = {f for f in self._eigene(self.nut, form) if nb.ist_grund(form, f)}
            if self._raeumen_boeden is not None:
                return [f for f in self._raeumen_boeden if f not in weg]
            return [f for f in flaechen if f not in weg]
        if block is self.restraeumen:
            # Nur die Taschen, die das Räumen ausließ (Raeumbahn.ausgelassen).
            if not self.raeumen.aktiv():
                return []
            return list(getattr(self.raeumen.vorschau, "ausgelassen", None) or [])
        if block is self.schlichten_danach:
            # Die Böden, die das Räumen räumt (die Wände um sie: _schlichten_danach_zusatz).
            return sorted(self._raeumt(form)) if self.raeumen.aktiv() else []
        if (
            block is self.bohrung
            and self.bohren.aktiv()
            and not self._gleiche_flaechen(block, form, self.bohren)
        ):
            gebohrt = set(self._eigene(self.bohren, form))
            return [f for f in flaechen if f not in gebohrt]
        if block is self.kontur:
            weg = set()
            if self._gerieben(form):
                weg |= set(self.reiben.s.flaechen_fuer(form, self.gewaehlte))
            # Was ein anderer angehakter Block macht, fährt die Kontur nicht nach – außer er
            # wetteifert mit ihr um genau dieselben Flächen (ein Lagerbock: die gebohrten Ø 9
            # unter den Senkungen nicht, P-2026-10-02-15).
            for anderer in (self.bohren, self.bohrung, self.nut):
                if anderer.aktiv() and not self._gleiche_flaechen(block, form, anderer):
                    weg |= set(self._eigene(anderer, form))
            # Die Wände, unter denen das Räumen bis durch räumt – außer es wetteifert mit ihr um
            # genau dieselben Wände (nur Wände gewählt, Frage 4) –, und die, vor denen kein
            # Rohteil steht (Grundsatz 5; W-033/W-034).
            if self.raeumen.aktiv() and not self._gleiche_flaechen(block, form, self.raeumen):
                weg |= set(self._durch_waende(form))
            weg |= {f for f in flaechen if f not in weg and self._ohne_rohteil(form, f)}
            return [f for f in flaechen if f not in weg]
        if block is self.schlichten3d and self._spirale_nach_flanke(form):
            # Die Flanke schruppt die Wände unter dem Rand mit Aufmaß, die Spirale macht sie fertig.
            return flaechen + [f for f in self._spirale_nach_flanke(form) if f not in flaechen]
        if (
            block is self.schlichten3d
            and self.flanke.aktiv()
            and not self._gleiche_flaechen(block, form, self.flanke)
        ):
            # Die schrägen Wände fräst die Flanke – das 3D-Schlichten den Rest (eine Kuppel).
            flanke = set(self._eigene(self.flanke, form))
            return [f for f in flaechen if f not in flanke]
        return flaechen

    def _vorschlichten_zusatz(self, form, flanke=None):
        """{"vorschlichten_bis": z} für das 3D-Schlichten bei „Flanke grob, Spirale fertig“: bis
        dort hinauf lässt die Flanke (`flanke`, ohne: ihre Vorschau) an der Wand mehr als
        schlichten3d.VORSCHLICHTEN_AB – Aufmaß und Keil, wo sie weiter angestellt ist (Manuel,
        2026-10-30, Frage 1: „vorschlichten“). Sonst None."""
        if not self._spirale_nach_flanke(form):
            return None
        bahn = flanke if flanke is not None else self.flanke.vorschau
        if not getattr(bahn, "keil_stellen", None):
            return None
        werte = dict(self.flanke.werte(), **(self._zusatz(self.flanke, form) or {}))
        bis = flb.vorschlichten_bis(bahn, float(werte.get("aufmass", 0.0)), s3op.VORSCHLICHTEN_AB)
        return {"vorschlichten_bis": round(bis, 1)} if bis is not None else None

    def _spirale_nach_flanke(self, form):
        """Die Wände der Flanke, die danach das 3D-Schlichten als Spirale unter dem Rand fertig
        macht – die Flanke schruppt sie dann mit FLANKE_VOR_SPIRALE (Manuel, 2026-10-25, Frage 7:
        „Flanke grob, Spirale fertig“, dann: „bau einfach beides .. und lass den user entscheiden“):
        nur, wenn in der Frage dieser Weg gewählt ist (_weg) – sonst []."""
        if self._weg.get("waende") != "spirale":
            return []
        return self._waende_unter_rand(form)

    def _waende_unter_rand(self, form):
        """Die Wände der Flanke, um die es in der Frage „Wände unter dem Rand“ geht: beide
        angehakt, das 3D-Schlichten mit einer Kugel „Unter dem Rand“ und „als Spirale“, und alle
        Wände der Flanke liegen unter dem Rand (hinterschnitt_bahn.ueberdeckte) – sonst []."""
        if not (self.flanke.aktiv() and self.schlichten3d.aktiv()):
            return []
        werte = self.schlichten3d.werte()
        if not (werte.get("hinterschnitt") and werte.get("spirale")):
            return []
        kugel = (
            ff.von_werkzeug(self.schlichten3d.fraeser()) if self.schlichten3d.fraeser() else None
        )
        if kugel is None or not kugel.nur_kugel:
            return []
        waende = list(self._eigene(self.flanke, form))
        if not waende or not set(waende) <= set(s3op.hb.ueberdeckte(form, waende)):
            return []
        return waende

    def _ohne_rohteil(self, form, name):
        """wand_ohne_rohteil mit dem Rohteil des Jobs – je Rohteil, Teil und Fläche gemerkt."""
        rohteil = getattr(getattr(self.job, "Stock", None), "Shape", None)
        if rohteil is None or rohteil.isNull():
            return False
        bb = rohteil.BoundBox
        schluessel = (
            name,
            round(rohteil.Volume, 3),
            tuple(round(w, 3) for w in (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax)),
            round(form.Volume, 3),
        )
        merk = self.__dict__.setdefault("_ohne_rohteil_merk", {})
        if schluessel not in merk:
            merk[schluessel] = wand_ohne_rohteil(form, name, rohteil)
        return merk[schluessel]

    def _bohrer_da(self, form, gerieben=False):
        """Hat die Werkzeugverwaltung einen Bohrer, der wenigstens eine der gewählten Bohrungen
        bohrt – durchgehend oder mit seiner Spitze darunter, mit seinem Durchmesser (`gerieben`:
        um die Reibzugabe kleiner)? Die anderen fräst „Bohrung fräsen“ (P-2026-10-02-12)."""
        return any(self._bohrbare(form, w, gerieben) for w in self.bohren._fraeser)

    def _bohrbare(self, form, werkzeug=None, gerieben=False):
        """Die gewählten Bohrungen, die der Bohrer `werkzeug` – ohne: der im Block Bohren –
        bohrt (bohren.kann)."""
        werkzeug = werkzeug or self.bohren.fraeser()
        if werkzeug is None:
            return []
        winkel = werkzeug.spitzenwinkel or bh.SPITZENWINKEL
        ergebnis = []
        for name in self.gewaehlte:
            if not bb.ist_bohrung(form, name):
                continue
            liste = bb.bohrungen(form, [name])
            if liste and all(bh.kann(b, werkzeug.durchmesser, winkel, gerieben) for b in liste):
                ergebnis.append(name)
        return ergebnis

    def _nebenbohrer(self, form, haupt=None):
        """{Fläche: Bohrer} – gewählte Bohrungen, die der Bohrer von „Bohren“ nicht bohrt, in die
        der Fräser von „Bohrung fräsen“ nicht kommt, und die ein anderer Bohrer des Blocks bohrt
        (der mit dem nächsten Ø). Sonst blieben sie rot bei „Bohrung fräsen“ stehen, und
        „Anlegen“ ging nicht (Manuels Federhalter umgedreht: Ø 3,2 mit T5, die Ø 6,5 mit T21 aus
        der Werkzeugverwaltung). Wo der Fräser hineinkommt, bleibt es beim Wettbewerb. `haupt`:
        statt des Bohrers im Block (_bohrer_waehlen zählt so je Bohrer)."""
        haupt = haupt or self.bohren.fraeser()
        if haupt is None or not self.gewaehlte:
            return {}
        fraeser = self.bohrung.fraeser()
        werte = self.bohrung.werte()
        aufmass = float(werte.get("aufmass", 0.0) or 0.0) if werte.get("schlichten") else 0.0
        schluessel = (
            id(form),
            tuple(self.gewaehlte),
            haupt.kennung,
            getattr(fraeser, "kennung", None),
            aufmass,
            tuple(w.kennung for w in self.bohren._fraeser),
        )
        merk = self.__dict__.setdefault("_nebenbohrer_merk", {})
        if schluessel in merk:
            return dict(merk[schluessel])
        ergebnis = {}
        eigene = set(self._bohrbare(form, haupt, gerieben=self._gerieben(form)))
        andere = [w for w in self.bohren._fraeser if w.kennung != haupt.kennung]
        for name in self.gewaehlte if eigene and andere else ():
            if name in eigene or not bb.ist_bohrung(form, name):
                continue
            liste = bb.bohrungen(form, [name])
            if not liste:
                continue
            if fraeser is not None and any(
                b.radius - fraeser.durchmesser / 2 - aufmass >= -1e-3 for b in liste
            ):
                continue  # die fräst „Bohrung fräsen“ (oder der Wettbewerb entscheidet)
            passende = [
                w
                for w in andere
                if all(
                    bh.kann(b, w.durchmesser, w.spitzenwinkel or bh.SPITZENWINKEL, False)
                    for b in liste
                )
            ]
            if passende:
                d = 2.0 * liste[0].radius
                ergebnis[name] = min(passende, key=lambda w, d=d: abs(w.durchmesser - d))
        if len(merk) > 32:
            merk.clear()
        merk[schluessel] = dict(ergebnis)
        return ergebnis

    def _nebenbohrer_zusatz(self, form):
        """Für die Vorschau von „Bohren“: [{werkzeug, vorschub, flaechen}] je weiterem Bohrer."""
        gruppen = {}
        for name, werkzeug in self._nebenbohrer(form).items():
            gruppe = gruppen.get(werkzeug.kennung)
            if gruppe is None:
                einsaetze = self.bohren._passende_einsaetze(werkzeug, self.werkstoff())
                vorschub = float(js.werte(werkzeug, einsaetze[0])[1]) if einsaetze else 0.0
                gruppe = {"werkzeug": werkzeug, "vorschub": vorschub, "flaechen": []}
                gruppen[werkzeug.kennung] = gruppe
            gruppe["flaechen"].append(name)
        return list(gruppen.values())

    def _eigene(self, block, form):
        """Die Flächen, mit denen der Block bei dieser Wahl arbeitet: beim Bohren nur die
        Bohrungen, die sein Bohrer bohrt, sonst alle, mit denen er etwas anfangen kann."""
        if block is self.bohren:
            eigene = self._bohrbare(form, gerieben=self._gerieben(form))
            return eigene + [n for n in self._nebenbohrer(form) if n not in eigene]
        merk = getattr(self, "_flaechen_merk", None)
        if merk is None:
            return block.s.flaechen_fuer(form, self._wahl(block))
        if id(block) not in merk:
            merk[id(block)] = list(block.s.flaechen_fuer(form, self._wahl(block)))
        return list(merk[id(block)])

    def _gerieben(self, form):
        """Wird gerieben – Reiben angehakt, und eine Reibahle passt zu den gewählten Bohrungen?"""
        return self.reiben.haken.isChecked() and self._reibahle_da(form)

    def _reibahle_da(self, form):
        """Hat die Werkzeugverwaltung eine Reibahle für alle gewählten Bohrungen?"""
        liste = bb.bohrungen(form, [n for n in self.gewaehlte if bb.ist_bohrung(form, n)] or [""])
        return bool(liste) and any(
            all(rbn.kann(b, w.durchmesser) for b in liste) for w in self.reiben._fraeser
        )

    def _reibahle_waehlen(self, form):
        """Wählt im Block Reiben die Reibahle mit dem Durchmesser der gewählten Bohrungen – wenn
        die gewählte nicht passt."""
        liste = bb.bohrungen(form, [n for n in self.gewaehlte if bb.ist_bohrung(form, n)] or [""])
        if not liste:
            return
        jetzt = self.reiben.fraeser()
        if jetzt is not None and all(rbn.kann(b, jetzt.durchmesser) for b in liste):
            return
        for i, w in enumerate(self.reiben._fraeser):
            if all(rbn.kann(b, w.durchmesser) for b in liste):
                self.reiben.wahl_fraeser.setCurrentIndex(i)
                return

    def _bohrungs_durchmesser(self, form):
        """Der Durchmesser der gewählten Bohrungen – None, wenn keine oder verschiedene."""
        namen = [n for n in self.gewaehlte if bb.ist_bohrung(form, n)]
        durchmesser = {round(2 * b.radius, 3) for b in bb.bohrungen(form, namen or [""])}
        return durchmesser.pop() if len(durchmesser) == 1 else None

    def _gewindebohrer_da(self, form):
        """Hat die Werkzeugverwaltung einen Gewindebohrer, dessen Kernloch alle gewählten
        Bohrungen haben?"""
        d = self._bohrungs_durchmesser(form)
        return d is not None and any(
            abs(gw.kernloch(w.durchmesser, w.steigung) - d) <= gw.GLEICH_D
            for w in self.gewinde._fraeser
        )

    def _gewindebohrer_waehlen(self, form):
        """Wählt im Block Gewinde den Gewindebohrer, dessen Kernloch die gewählten Bohrungen
        haben – wenn der gewählte nicht passt."""
        d = self._bohrungs_durchmesser(form)
        if d is None:
            return
        jetzt = self.gewinde.fraeser()
        if jetzt is not None and abs(gw.kernloch(jetzt.durchmesser, jetzt.steigung) - d) <= (
            gw.GLEICH_D
        ):
            return
        for i, w in enumerate(self.gewinde._fraeser):
            if abs(gw.kernloch(w.durchmesser, w.steigung) - d) <= gw.GLEICH_D:
                self.gewinde.wahl_fraeser.setCurrentIndex(i)
                return

    def _gewindefraeser_passt(self, werkzeug, liste):
        """Fräst `werkzeug` in alle Bohrungen `liste` ein Gewinde (gewinde_bahn.stelle)?"""
        werte = gf.aus_werkzeug(werkzeug)
        w = gfb.Gewindewerte(
            fraeser_radius=werte["fraeser_radius"],
            steigung=float(werkzeug.steigung or 0.0),
            oben=max((b.z_oben for b in liste), default=0.0),
            sicher=0.0,
            zaehne=gf.zaehne_von(werkzeug),
            flankenwinkel=werte["flankenwinkel"],
            spitze=werte["spitze"],
            hals_radius=werte["hals_radius"],
            reichweite=werte["reichweite"],
        )
        if w.steigung <= 0:
            return False
        try:
            for b in liste:
                gfb.stelle(b, w)
        except ValueError:
            return False
        return True

    def _gewindefraeser_liste(self, form):
        namen = [n for n in self.gewaehlte if bb.ist_bohrung(form, n)]
        return bb.bohrungen(form, namen) if namen else []

    def _gewindefraeser_da(self, form):
        """Hat die Werkzeugverwaltung einen Gewindefräser, der in alle gewählten Bohrungen ein
        Gewinde fräst – seine Steigung zu ihrem Kernloch, klein genug?"""
        liste = self._gewindefraeser_liste(form)
        return bool(liste) and any(
            self._gewindefraeser_passt(w, liste) for w in self.gewindefraesen._fraeser
        )

    def _gewindefraeser_waehlen(self, form):
        """Wählt im Block Gewinde fräsen einen Gewindefräser, der zu den gewählten Bohrungen
        passt – wenn der gewählte es nicht tut."""
        liste = self._gewindefraeser_liste(form)
        if not liste:
            return
        jetzt = self.gewindefraesen.fraeser()
        if jetzt is not None and self._gewindefraeser_passt(jetzt, liste):
            return
        for i, w in enumerate(self.gewindefraesen._fraeser):
            if self._gewindefraeser_passt(w, liste):
                self.gewindefraesen.wahl_fraeser.setCurrentIndex(i)
                return

    @staticmethod
    def _entgrat_passt(werkzeug, fasen_):
        """Fräst `werkzeug` alle gezeichneten Fasen und Rundungen `fasen_` – ein Fasenfräser mit
        ihrem Winkel, ein Radienfräser mit ihrem Radius?"""
        for f in fasen_:
            if f.radius > 0:
                if werkzeug.art != wz.RADIENFRAESER:
                    return False
                profil, _spitze, _hoehe = wf.radienprofil(werkzeug)
                if abs(profil - f.radius) > eb.RADIUS_GLEICH:
                    return False
            else:
                if werkzeug.art != wz.FASENFRAESER:
                    return False
                _spitze, _hoehe, winkel = wf.kegel(werkzeug)
                if abs(winkel / 2 - f.winkel) > eb.FASE_WINKEL:
                    return False
        return True

    def _entgratfraeser_waehlen(self, form):
        """Wählt im Block Entgraten den Fräser für die gezeichneten Fasen und Rundungen der Wahl
        – wenn der gewählte sie nicht kann."""
        fasen_ = eb._gewaehlte_fasen(form, self.gewaehlte)
        if not fasen_:
            return
        jetzt = self.entgraten.fraeser()
        if jetzt is not None and self._entgrat_passt(jetzt, fasen_):
            return
        for i, w in enumerate(self.entgraten._fraeser):
            if self._entgrat_passt(w, fasen_):
                self.entgraten.wahl_fraeser.setCurrentIndex(i)
                return

    def _senker_passt(self, werkzeug, liste):
        winkel = float(werkzeug.spitzenwinkel or sk.SPITZENWINKEL)
        spitze = float(werkzeug.spitzen_d or 0.0)
        return all(
            abs(s.winkel - winkel) <= sk.GLEICH_WINKEL
            and s.durchmesser <= werkzeug.durchmesser + sk.GLEICH_D
            and (s.unten <= 0 or spitze <= s.unten + sk.GLEICH_D)
            for s in liste
        )

    def _senken_angebot(self, form, namen):
        """(Satz, Knopf, Aktion) unter „Nicht fertig“ – oder None: Sind darunter Senkungen, für die
        kein Kegelsenker in der Werkzeugverwaltung steht, aber ein Fasenfräser mit ihrem Winkel,
        dessen Spitze in die Bohrung passt (_senker_passt): „… T6 kann sie senken. Nehmen?“."""
        block = self.senken
        if block.s.mit_fasenfraeser or self.bibliothek is None:
            return None
        senkungen = [n for n in namen if sk.ist_senkung(form, n)]
        if not senkungen or self._senker_da(form):
            return None
        liste = sk.senkungen(form, senkungen)
        werkstoff = self.werkstoff()
        passende = [
            w
            for w in mg.sortiert(self.bibliothek.werkzeuge, self.magazin(), self.bibliothek)
            if w.art == wz.FASENFRAESER
            and self._senker_passt(w, liste)
            and block._passende_einsaetze(w, werkstoff)
        ]
        if not passende:
            # Auch kein Fasenfräser: sagen, was fehlt, und ihn anlegen (Manuel: der nächste
            # Schritt als Knopf) – an seinem Messspitzenhalter stand nur „nicht fertig“.
            unten = min((x.unten for x in liste if x.unten > 0), default=0.0)
            winkel = round(liste[0].winkel, 1)
            satz = tr(
                "ba.senken.fehlt",
                d=groesse_zeigen(max(x.durchmesser for x in liste), einheiten.LAENGE),
                winkel=f"{winkel:g}",
                spitze=groesse_zeigen(unten, einheiten.LAENGE),
            )
            senker = self._senker_fuer(liste, unten)
            if senker is None:
                return dezimal(satz), tr("va.werkzeugverwaltung"), self.werkzeugverwaltung
            knopf_text = tr(
                "ba.senken.senker_anlegen",
                winkel=f"{winkel:g}",
                d=groesse_zeigen(senker[0], einheiten.LAENGE, 1) or "0",
            )
            return dezimal(satz), knopf_text, lambda: self._senker_anlegen(*senker, winkel)
        werkzeug = passende[0]
        satz = tr(
            "ba.senken.angebot",
            werkzeug=_ziel_werkzeug(werkzeug),
            winkel=f"{float(werkzeug.spitzenwinkel or sk.SPITZENWINKEL):g}",
        )
        knopf_text = tr("ba.fase.angebot.knopf", nummer=wz.nummer_text(werkzeug))
        return dezimal(satz), knopf_text, lambda: self._senken_mit_fasenfraeser(werkzeug)

    def _senker_fuer(self, liste, unten):
        """(Ø, Ø der Spitze, Schaft-Ø) des kleinsten Kegelsenkers aus KEGELSENKER_REIHE, der alle
        Senkungen der `liste` abdeckt und dessen Spitze in die engste Bohrung (`unten`, 0: keine)
        passt – None, wenn keiner der Reihe das kann."""
        groesste = max(x.durchmesser for x in liste)
        for d, spitze, schaft in KEGELSENKER_REIHE:
            if d + sk.GLEICH_D < groesste:
                continue
            if unten > 0 and spitze > unten + sk.GLEICH_D:
                continue
            return d, spitze, schaft
        return None

    def _senker_anlegen(self, durchmesser, spitze, schaft, winkel):
        """„Kegelsenker 90° Ø 6,3 anlegen“ (_senken_angebot): HSS, drei Schneiden, mit
        Richtwerten in die Werkzeugverwaltung und ins Magazin; dann die Haken neu – „Senken“
        senkt (wie „T6 nehmen“)."""
        if self.bibliothek is None:
            return
        senker = wz.Werkzeug(
            nummer=self.bibliothek.naechste_nummer(),
            name=tr("ba.senken.senker_name", winkel=f"{winkel:g}", d=f"{durchmesser:g}"),
            art=wz.KEGELSENKER,
            durchmesser=float(durchmesser),
            schneiden=3,
            spitzenwinkel=float(winkel),
            spitzen_d=float(spitze),
            schaft=float(schaft),
            schneidstoff=wz.HSS,
        )
        self._werkzeug_anlegen(senker)
        self.unfertig_angebot.hide()
        if self.job is not None:
            self._haken_vorschlagen(vr.modell(self.job).Shape)
        self.vorschau_starten()

    def _senken_mit_fasenfraeser(self, werkzeug):
        """„T6 nehmen“: der Block „Senken“ nimmt auch Fasenfräser, dieser ist gewählt, der Haken
        an – dann rechnet die Vorschau neu."""
        block = self.senken
        block.s.mit_fasenfraeser = True
        block.fraeser_fuellen(self.bibliothek, self.werkstoff())
        if block.fraeser_setzen(werkzeug):
            block.fraeser_von_hand = True
        self.unfertig_angebot.hide()
        if self.job is not None:
            self._haken_vorschlagen(vr.modell(self.job).Shape)
        self.vorschau_starten()

    def _unfertig_angebot_nehmen(self):
        if self._unfertig_aktion is not None:
            self._unfertig_aktion()

    def _senker_da(self, form):
        """Hat die Werkzeugverwaltung einen Kegelsenker für alle gewählten Senkungen – ihr
        Winkel, mindestens ihr Ø?"""
        liste = sk.senkungen(form, [n for n in self.gewaehlte if sk.ist_senkung(form, n)] or [""])
        return bool(liste) and any(self._senker_passt(w, liste) for w in self.senken._fraeser)

    def _senker_waehlen(self, form):
        """Wählt im Block Senken den Kegelsenker, der zu den gewählten Senkungen passt – den
        kleinsten, wenn der gewählte nicht passt."""
        liste = sk.senkungen(form, [n for n in self.gewaehlte if sk.ist_senkung(form, n)] or [""])
        if not liste:
            return
        jetzt = self.senken.fraeser()
        if jetzt is not None and self._senker_passt(jetzt, liste):
            return
        passend = [
            (w.durchmesser, i)
            for i, w in enumerate(self.senken._fraeser)
            if self._senker_passt(w, liste)
        ]
        if passend:
            self.senken.wahl_fraeser.setCurrentIndex(min(passend)[1])

    def _bohrer_waehlen(self, form, gerieben=False):
        """Wählt im Block Bohren den Bohrer mit dem Durchmesser der gewählten Bohrungen – wenn
        der gewählte nicht passt; `gerieben`: den größten, der um die Reibzugabe kleiner ist."""

        def bohrt(w):  # mit den weiteren Bohrern dazu (_nebenbohrer)
            return len(self._bohrbare(form, w, gerieben)) + len(self._nebenbohrer(form, w))

        anzahl = [bohrt(w) for w in self.bohren._fraeser]
        if not anzahl or max(anzahl) == 0:
            return
        jetzt = self.bohren.fraeser()
        if jetzt is not None and bohrt(jetzt) == max(anzahl):
            return
        passend = [i for i, n in enumerate(anzahl) if n == max(anzahl)]
        wahl = max(passend, key=lambda i: self.bohren._fraeser[i].durchmesser)
        self.bohren.wahl_fraeser.setCurrentIndex(wahl if gerieben else passend[0])

    def _planeinsatz_waehlen(self, form):
        """Wählt im Planfräsen den Einsatz, mit dem der Fräser schneller ist (Grundsatz 0;
        P-2026-10-02-54): „Planen“ – großes ae bei kleinem ap – für eine dünne Schicht,
        „Schruppen“ mit der ganzen Schneide für tiefes Material. Je Einsatz die Zielzeit bis zu
        seinen Flächen (zielzeit.ziel), die kürzere gewinnt. Neu gewählt wird nur, wenn sich das
        ändert – sonst bleibt, was von Hand gewählt ist."""
        block = self.plan
        werkzeug = block.fraeser()
        material = self._ziel_material(form) if werkzeug is not None else None
        ebenen = hf.ebenen_oben(form, self._flaechen(block, form)) if material is not None else []
        if not ebenen:
            return
        bis = material.bis(min(e.z for e in ebenen))
        zeiten = {}
        for einsatz in block._einsaetze:
            werte = zz.werte(werkzeug, einsatz) if einsatz.art in zz.WEGNEHMEN else None
            if werte is not None and einsatz.art in (wz.PLANEN, wz.SCHRUPPEN):
                zeit = zz.ziel(bis, werkzeug.durchmesser / 2, *werte).zeit
                zeiten[einsatz.art] = min(zeit, zeiten.get(einsatz.art, math.inf))
        if len(zeiten) < 2:
            return
        tief = zeiten[wz.SCHRUPPEN] < zeiten[wz.PLANEN]
        if tief != block.s.tief:
            block.s.tief = tief
            block.einsatz_fuellen(self.werkstoff())

    def _flaechenzellen(self, form, namen):
        """{Fläche: (z, Maske)} – die ebenen Flächen nach oben unter `namen` auf dem Raster der
        Zielzeit (_ziel_material, zielzeit.zellen_der_flaeche), je Teil und Rohteil gemerkt."""
        material = self._ziel_material(form)
        if material is None:
            return None, {}
        gemerkt = getattr(self, "_zellen_gemerkt", None)
        if gemerkt is None or gemerkt[0] is not material.boden:
            gemerkt = (material.boden, {}, {})  # Boden, Zellen je Fläche, Stirn je Radius
            self._zellen_gemerkt = gemerkt
        zellen = gemerkt[1]
        fehlen = [n for n in namen if n not in zellen]
        if fehlen:
            ebenen = {e.name: e for e in hf.ebenen_oben(form, fehlen)}
            for name in fehlen:
                ebene = ebenen.get(name)
                if ebene is None:
                    zellen[name] = None
                    continue
                try:
                    flaeche = form.getElement(name)
                    zellen[name] = (ebene.z, zz.zellen_der_flaeche(material, flaeche, ebene.z))
                except Exception:  # eine Fläche, die sich nicht prüfen lässt: gilt als erreicht
                    zellen[name] = None
        return material, {n: zellen[n] for n in namen if zellen.get(n) is not None}

    def _erreicht(self, form, namen, werkzeug, spiel=0.0):
        """{Fläche: Anteil, den `werkzeug` von ihr erreicht} – für die ebenen Flächen nach oben
        unter `namen` (zielzeit.anteile_erreicht); leer ohne Ziel-Material."""
        if werkzeug is None or werkzeug.durchmesser <= 0:
            return {}
        material, zellen = self._flaechenzellen(form, list(namen))
        if material is None or not zellen:
            return {}
        radius = werkzeug.durchmesser / 2 + spiel
        stirnen = self._zellen_gemerkt[2]
        if radius not in stirnen:
            stirnen[radius] = zz.stirn(material, radius)
        return zz.anteile_erreicht(material, radius, zellen, stirn=stirnen[radius])

    def _zu_eng(self, block, form, werkzeug=None):
        """Die Flächen des Blocks, in die sein Fräser (oder `werkzeug`) nicht hineinkommt: Er
        erreicht weniger als ZU_ENG von ihnen – nur Planfräsen und Räumen."""
        if block not in (self.plan, self.raeumen) or self.job is None:
            return []
        werkzeug = werkzeug or block.fraeser()
        anteile = self._erreicht(form, self._flaechen(block, form), werkzeug)
        return [name for name, anteil in anteile.items() if anteil < ZU_ENG]

    def _unerreicht(self, block, form):
        """{Fläche: Anteil, den der Block von ihr erreicht} für die gewählten ebenen Flächen, die
        er nicht fertig macht – Planfräsen und Räumen: sein Fräser kommt nicht hinein (_zu_eng),
        oder seine Bahn (die Vorschau) überstreicht in ihrer Höhe weniger als PASST von ihr; was
        davor schon weg ist (der Materialstand), zählt als erreicht. Manuel (2026-10-16): Am
        C-Ring räumte das Räumen mit Ø 6 nur zwei Drittel der 10 mm breiten Ringnut – im Raster
        ist der Streifen für die Mitte keine zwei Zellen breit – und galt als „die schnellste“.
        „Bohrung fräsen“: die Bohrungen, in die sein Fräser nicht kommt (Bohrbahn.zu_klein) – es
        war nur schneller, weil es sie liegen ließ (Manuels Messspitzenhalter von unten: die Ø 2,5
        bekamen gar keine Operation)."""
        if block is self.bohrung:
            zu_klein = getattr(block.vorschau, "zu_klein", None) if block.vorschau else None
            return dict.fromkeys(zu_klein or (), 0.0)
        if block not in (self.plan, self.raeumen) or self.job is None:
            return {}
        werkzeug = block.fraeser()
        namen = self._flaechen(block, form)
        # Ein gewolltes Aufmaß am Boden: Die Bahn fährt um so viel höher – erreicht ist die Fläche
        # trotzdem (szenario_raeumen_schlichten: 0,5 am Boden, „Schlichten danach“ macht ihn fertig).
        werte = block.werte()
        hoeher = float(
            werte.get("aufmass_boden" if block is self.raeumen else "aufmass", 0.0) or 0.0
        )
        ergebnis = {}
        for name, anteil in self._erreicht(form, namen, werkzeug).items():
            if anteil < ZU_ENG:
                ergebnis[name] = anteil
        vorschau = block.vorschau
        punkte = getattr(vorschau, "punkte", None) if vorschau is not None else None
        if not punkte or werkzeug is None:
            return ergebnis
        material, zellen = self._flaechenzellen(form, namen)
        if material is None:
            return ergebnis
        merk = getattr(self, "_ueberstrichen_merk", None)
        if merk is None or merk[0] is not vorschau or merk[1] is not material.boden:
            merk = (vorschau, material.boden, {})
            self._ueberstrichen_merk = merk
        for name, (z, maske) in zellen.items():
            if name in ergebnis or not maske.any():
                continue
            if name not in merk[2]:
                strecken = [
                    (a.x, a.y, b.x, b.y)
                    for a, b in zip(punkte, punkte[1:], strict=False)
                    if not b.eilgang and a.z <= z + hoeher + 0.05 and b.z <= z + hoeher + 0.05
                ]
                ueber = zz.ueberstrichen(material, strecken, werkzeug.durchmesser / 2)
                # Ohne den Rand der Fläche: An der Wand bleibt das Aufmaß, und dort misst das
                # Raster auf eine Zelle ungenau (an der offenen Nut 16 breit sonst nur 88 %).
                kern = zz.innen(maske)
                merk[2][name] = zz.anteil_frei(material, ueber, z, kern if kern.any() else maske)
            if merk[2][name] < PASST:
                ergebnis[name] = merk[2][name]
        return ergebnis

    def _flaechenfraeser_waehlen(self, form):
        """Planfräsen und Räumen: Kommt ihr Fräser in eine gewählte ebene Fläche nicht hinein
        (_zu_eng – eine Nut, enger als er), bieten sie den größten ihrer Fräser an, der mit
        PASST_SPIEL Luft je Seite überall hinkommt (_passt_zeigen, „… übernehmen“) – genommen wird
        er erst auf Klick (Manuel, 2026-10-17; bis dahin tauschten sie selbst). Manuel
        (2026-10-16) an zwei Teilen: Ø 12 in 10 mm breiten Nuten – das Planfräsen gewann ohne ein
        Wort, der Nutgrund blieb stehen. Merkt sich je Block, was getauscht wurde
        (_getauscht) und was ganz ohne passenden Fräser bleibt."""
        self._getauscht = {}
        for block in (self.plan, self.raeumen):
            jetzt = block.fraeser()
            eng = self._zu_eng(block, form, jetzt)
            if not eng:
                continue
            passen = []
            for i, werkzeug in enumerate(block._fraeser):
                if werkzeug.durchmesser >= jetzt.durchmesser:
                    continue
                anteile = self._erreicht(form, eng, werkzeug, PASST_SPIEL)
                if anteile and min(anteile.values()) >= PASST:
                    passen.append(i)
            if not passen:
                self._getauscht[block] = (jetzt, None, eng)
                continue
            wahl = max(passen, key=lambda i: (block._fraeser[i].durchmesser, -i))
            self._getauscht[block] = (jetzt, block._fraeser[wahl], eng)  # nur angeboten
        self._bohrungsfraeser_anbieten(form)

    def _bohrungsfraeser_anbieten(self, form):
        """„Bohrung fräsen“: Kommt sein Fräser in keine der gewählten Bohrungen, bietet die Zeile
        wie bei Planfräsen und Räumen den größten seiner Fräser an, der in wenigstens eine passt
        („… übernehmen“) – die kleineren nennt seine Zeile dann für den Bohrer (Bohrbahn.zu_klein).
        Manuels Messspitzenhalter (2026-10-23): T3 Ø 12 in der Ø 8,5 und den Ø 2,5 – rot, ohne
        Weg; der T4 Ø 6 fräst die Ø 8,5."""
        block = self.bohrung  # angehakt oder nicht: Das filtern _getauscht_text und das Angebot
        jetzt = block.fraeser()
        namen = self._flaechen(block, form)
        liste = bb.bohrungen(form, namen) if namen and jetzt is not None else []
        if not liste:
            return
        werte = block.werte()
        aufmass = float(werte.get("aufmass", 0.0) or 0.0) if werte.get("schlichten") else 0.0

        def passt_in(werkzeug, bohrung):
            return bohrung.radius - werkzeug.durchmesser / 2 - aufmass >= -1e-3

        if any(passt_in(jetzt, b) for b in liste):
            return
        eng = [b.name for b in liste]
        passen = [
            i
            for i, w in enumerate(block._fraeser)
            if w.durchmesser > 0
            and w.durchmesser < jetzt.durchmesser
            and any(passt_in(w, b) for b in liste)
        ]
        if not passen:
            self._getauscht[block] = (jetzt, None, eng)
            return
        wahl = max(passen, key=lambda i: (block._fraeser[i].durchmesser, -i))
        self._getauscht[block] = (jetzt, block._fraeser[wahl], eng)  # nur angeboten

    def _passt_zeigen(self):
        """Der rote Satz zu den Fräsern, die nicht hineinkommen (_getauscht_text), und der Knopf
        „„T3 …“ übernehmen“, wenn ein kleinerer passt."""
        text = self._getauscht_text() if self.zu_aendern is None else ""
        self.passt_text.setText(text)
        self.passt_text.setVisible(bool(text))
        angebot = self._passendes_angebot()
        if angebot is not None:
            self.knopf_passt.setText(tr("ba.passt.knopf", werkzeug=_ziel_werkzeug(angebot)))
        self.knopf_passt.setVisible(angebot is not None)

    def _passendes_angebot(self):
        """Der kleinere Fräser, der passt (bei Planfräsen und Räumen derselbe: der erste) – None."""
        if self.zu_aendern is not None:
            return None
        bedeckt = self._von_aktiven_bedeckt()
        for block, (_vorher, nachher, eng) in getattr(self, "_getauscht", {}).items():
            if not block.aktiv() and eng and set(eng) <= bedeckt:
                continue
            if nachher is not None and (block.aktiv() or block.moeglich):
                return nachher
        return None

    def _raeumen_umsonst(self, form):
        """Hat das Räumen nichts zu tun, das nicht schon andere tun oder fertig ist: Jede seiner
        Flächen ist ein Grund, den die angehakte Nut fräst, oder eine Wand ohne Rohteil davor
        (wand_ohne_rohteil)? Nur, wenn sein Satz „steht nichts“ sagt."""
        if tr("ra.fehler.nichts") not in self.raeumen.hinweis.text():
            return False
        eigene = self._eigene(self.raeumen, form)
        if not eigene:
            return False
        nut = set()
        if self.nut.aktiv():
            nut = {f for f in self._eigene(self.nut, form) if nb.ist_grund(form, f)}
        return all(f in nut or self._ohne_rohteil(form, f) for f in eigene)

    def _von_aktiven_bedeckt(self):
        """Die gewählten Flächen, die angehakte Blöcke schon nehmen – leer ohne Job."""
        if self.job is None:
            return set()
        try:
            form = vr.modell(self.job).Shape
        except (AttributeError, IndexError):
            return set()
        bedeckt = set()
        for block in self.aktive_bloecke():
            try:
                bedeckt |= set(self._flaechen(block, form))
            except Exception:  # noqa: BLE001 – ein Block ohne Flächen: nichts
                continue
        return bedeckt

    def _fehlende_bohrer(self, block, flaechen):
        """[(Ø, Spitzenwinkel, Tiefe, [Flächen])] der Bohrungen unter `flaechen`, in die der
        Fräser von `block` („Bohrung fräsen“) nicht hineinkommt (wie _bohrungsfraeser_anbieten)
        und die kein Bohrer der Werkzeugverwaltung bohrt (bohren.kann: Ø, bei einer Sackbohrung
        auch die Spitze – Manuels Federhalter von unten: Ø 6,5 mit 140°); je Ø und Winkel einmal,
        die tiefste zählt. Ein ebener Grund braucht keinen Bohrer."""
        fraeser = block.fraeser()
        if fraeser is None or not flaechen or self.bibliothek is None or self.job is None:
            return []
        try:
            liste = bb.bohrungen(vr.modell(self.job).Shape, list(flaechen))
        except Exception:  # noqa: BLE001 – ohne Bohrungen nichts anzubieten
            return []
        werte = block.werte()
        aufmass = float(werte.get("aufmass", 0.0) or 0.0) if werte.get("schlichten") else 0.0
        bohrer = [
            (float(w.durchmesser), float(w.spitzenwinkel or bh.SPITZENWINKEL))
            for w in self.bibliothek.werkzeuge
            if w.art == wz.BOHRER
        ]
        fehlend = {}
        for b in liste:
            if b.radius - fraeser.durchmesser / 2 - aufmass >= -1e-3:
                continue  # die fräst er
            if not b.durch and b.spitze <= 0:
                continue  # ein ebener Grund: kein Bohrer
            if any(bh.kann(b, d, winkel) for d, winkel in bohrer):
                continue
            d = round(2.0 * b.radius, 3)
            winkel = float(bh.SPITZENWINKEL if b.durch else round(b.spitze))
            tiefe = b.z_oben - b.z_unten + bh.spitze(d, winkel)
            vorher = fehlend.get((d, winkel), (0.0, []))
            fehlend[(d, winkel)] = (max(vorher[0], tiefe), [*vorher[1], b.name])
        return [
            (d, winkel, tiefe, namen) for (d, winkel), (tiefe, namen) in sorted(fehlend.items())
        ]

    def _bohrer_anlegen(self, fehlend):
        """„Bohrer Ø … anlegen“ unter „Bohrung fräsen“: je Durchmesser aus _fehlende_bohrer ein
        Bohrer wie fürs Vorbohren (_vorbohrer_anlegen); dann die Haken neu – „Bohren“ übernimmt
        die Bohrungen (wie „T6 nehmen“)."""
        for d, winkel, tiefe, _namen in fehlend:
            self._vorbohrer_anlegen(d, tiefe, winkel)
        if self.job is not None:
            self._haken_vorschlagen(vr.modell(self.job).Shape)
        self.vorschau_starten()

    def passenden_uebernehmen(self):
        """„„T3 …“ übernehmen“: der angebotene Fräser in Planfräsen und Räumen, wo er dort steht.
        Gibt zurück, ob sich etwas geändert hat."""
        geaendert = False
        for block, (_vorher, nachher, _eng) in list(getattr(self, "_getauscht", {}).items()):
            if nachher is not None and block.fraeser_setzen(nachher):
                geaendert = True
        if geaendert:
            self._getauscht = {}
            self.passt_text.hide()
            self.knopf_passt.hide()
            self._flaechen_zeigen()
            self.vorschau_starten()
        return geaendert

    def _getauscht_text(self):
        """Der Satz zur Ziel-Zeile, wenn ein Fräser nicht in die gewählten Flächen kam
        (_flaechenfraeser_waehlen) – Planfräsen und Räumen mit demselben Tausch in einem Satz;
        sonst ""."""
        gruppen = {}
        bedeckt = self._von_aktiven_bedeckt()
        for block, (vorher, nachher, eng) in getattr(self, "_getauscht", {}).items():
            if not block.aktiv() and not block.moeglich:
                continue
            if not block.aktiv() and eng and set(eng) <= bedeckt:
                continue  # angehakte nehmen die Flächen schon (die Ringnut: die Nut mit T4)
            schluessel = (vorher.kennung, nachher.kennung if nachher else None, tuple(eng))
            gruppen.setdefault(schluessel, (vorher, nachher, eng, []))[3].append(block.s.titel())
        saetze = []
        for vorher, nachher, eng, titel in gruppen.values():
            flaechen = ", ".join(eng[:3]) + (" …" if len(eng) > 3 else "")
            werte = {
                "werkzeug": _ziel_werkzeug(vorher),
                "flaechen": flaechen,
                "block": (
                    tr("ba.passt.und", erster=titel[0], zweiter=titel[1])
                    if len(titel) > 1
                    else titel[0]
                ),
            }
            if nachher is None:
                saetze.append(tr("ba.passt.keiner", **werte))
            else:
                saetze.append(tr("ba.passt.angebot", neu=_ziel_werkzeug(nachher), **werte))
        return " ".join(saetze)

    def _passt_angebot(self, form, angebot):
        """Kommt der erste Fräser eines Angebots der Ziel-Zeile in die Flächen des Blocks, in den
        „Übernehmen“ ihn setzt (ein Planfräser ins Planfräsen, sonst ins Räumen)?"""
        block = self.plan if angebot.werkzeug.art == wz.PLANFRAESER else self.raeumen
        if (
            block is self.raeumen
            and self.nut.aktiv()
            and (
                getattr(self, "_raeumen_bei_nut", False)
                or (self._eigene(block, form) and not self._flaechen(block, form))
            )
        ):
            # Die Nut nimmt dem Räumen alle Gründe (oder es gibt den Haken ab, weil vor den Wänden
            # kein Rohteil steht): dort hätte er nichts zu tun.
            return False
        return not self._zu_eng(block, form, angebot.werkzeug)

    def _nutfraeser_waehlen(self, form):
        """Wählt im Block Nut einen Fräser, der in die gewählten Nuten passt, wenn der gewählte es
        nicht tut – am liebsten den größten, der Bögen fährt, sonst den größten, der hineinpasst;
        und den Einsatz dazu: „Vollnut“ zuerst, wenn er sie in voller Breite fräst."""
        namen = [n for n in self.gewaehlte if nb.ist_nut(form, n)]
        liste = nb.nuten(form, namen) if namen else []
        if not liste:
            return
        block = self.nut
        aufmass = block.wert("aufmass")

        def arten(w):
            return {nb.verfahren(n, w.durchmesser / 2, aufmass) for n in liste}

        geht = {"boegen", "vollnut"}
        wahl = block.wahl_fraeser.currentIndex()
        jetzt = block.fraeser()
        if jetzt is None or not arten(jetzt) <= geht:
            boegen = [i for i, w in enumerate(block._fraeser) if arten(w) == {"boegen"}]
            passen = [i for i, w in enumerate(block._fraeser) if arten(w) <= geht]
            if boegen or passen:
                wahl = max(boegen or passen, key=lambda i: block._fraeser[i].durchmesser)
        if not 0 <= wahl < len(block._fraeser):
            return
        vollnut = "vollnut" in arten(block._fraeser[wahl])
        anders = vollnut != block.s.vollnut
        block.s.vollnut = vollnut
        if wahl != block.wahl_fraeser.currentIndex():
            block.wahl_fraeser.setCurrentIndex(wahl)  # füllt die Einsätze neu
        elif anders:
            block.einsatz_fuellen(self.werkstoff())

    def _von_raeumen_geraeumt(self, form):
        """Räumt das Räumen die Böden aller gewählten Bohrungen (Sackbohrungen, deren Wände
        gewählt sind – rb.taschenboeden)? Dann ist dort Räumen und danach die Kontur mit dem
        Aufmaß die Folge (Spezifikation Abschnitt 11), und „Bohrung fräsen“ tritt nicht an –
        es würde die ganze Bohrung fräsen, die Kontur nur das Aufmaß (auf Manuels Platte:
        „Bohrung fräsen wäre 1741 % langsamer“)."""
        if not self.raeumen.aktiv():
            return False
        bohrungen = self.bohrung.s.flaechen_fuer(form, self.gewaehlte)
        if not bohrungen:
            return False
        geraeumt = set(self._flaechen(self.raeumen, form))
        for name in bohrungen:
            boeden = rb.taschenboeden(form, [name])
            if not boeden or not set(boeden) <= geraeumt:
                return False
        return True

    def _gleiche_flaechen(self, block, form, andere=None):
        """Löst `andere` – ohne: einer der Gegner des Blocks (_gegner) – dieselbe Aufgabe, genau
        dieselben Flächen?"""
        eigene = set(self._eigene(block, form))
        gegner = [andere] if andere is not None else self._gegner(block)
        return any(set(self._eigene(g, form)) == eigene for g in gegner)

    def _nur_boeden(self, form):
        """Die Taschenböden, die nur das Räumen kann – wenn außer ihnen auch ebene Flächen
        gewählt sind, die das Planfräsen könnte; sonst None."""
        if self.zu_aendern is not None or not self.plan.moeglich or not self.raeumen.moeglich:
            return None
        flach = self.plan.s.flaechen_fuer(form, self.gewaehlte)
        alle = self.raeumen.s.flaechen_fuer(form, self.gewaehlte)
        if not flach or not set(flach) < set(alle):
            return None
        # Die Gründe, die die angehakte Nut fräst, nicht: An Manuels Klemmung waren alle drei
        # Taschen Nuten – das Räumen rechnete sie trotzdem vor („3 Lagen, etwa 6 min“) und legte
        # dann eine leere Operation an („Hier ist nichts mehr zu tun“).
        nut = set()
        if self.nut.aktiv():
            nut = {f for f in self._eigene(self.nut, form) if nb.ist_grund(form, f)}
        boeden = [f for f in alle if f not in flach and f not in nut]
        return boeden or None

    def _folge(self, form, boeden):
        """Ebene Flächen und Taschenböden gewählt: Entweder räumt das Räumen alles, oder das
        Planfräsen fräst die ebenen Flächen und das Räumen nur die Böden – die schnellere Folge
        bekommt die Haken (Grundsatz 0), solange niemand sie von Hand gesetzt hat. Sind beide
        angehakt, räumt das Räumen nur die Böden: keine Fläche zweimal."""
        for schritt in self._folge_schritte(form, boeden):
            _abwarten(schritt)

    def _folge_schritte(self, form, boeden):
        """_folge als Schritte (ein Generator): nach jeder der bis zu drei Vorschauen ein `yield` –
        im Takt (_vorschau_im_takt) wäre die Folge am Stück einer der längsten Schritte."""
        plan, raeumen = self.plan, self.raeumen
        flaechen = raeumen.s.flaechen_fuer(form, self.gewaehlte)

        def mit_stand(eigene, mit=()):  # der Materialstand vor dem Räumen dieser Flächen
            stand = self._materialstand(raeumen, form, eigene, mit)
            return dict(self._zusatz(raeumen, form) or {}, materialstand=stand)

        if not plan.aktiv() and (plan.von_hand or not plan.moeglich):
            yield from raeumen.vorschau_schritte(self.job, flaechen, mit_stand(flaechen))
            return
        if plan.vorschau is None:
            eben = plan.s.flaechen_fuer(form, self.gewaehlte)
            yield from plan.vorschau_schritte(
                self.job, eben, {"materialstand": self._materialstand(plan, form, eben)}
            )
            yield
        yield from raeumen.vorschau_schritte(self.job, flaechen, mit_stand(flaechen))
        # Mit „schon weg“: Sonst behielte das Räumen den Merker des zweiten Laufs – am C-Ring
        # („Alles aus dieser Aufspannung“, W-034) ging der mit dem Ø 12 nicht in die Ringnut, und
        # _schon_weg_abhaken nahm dem Räumen über alles den Haken.
        alles = (raeumen.vorschau, raeumen.zeit, raeumen.ergebnis_basis, raeumen.hinweis.text())
        alles_weg = raeumen.schon_weg
        yield
        # Nur die Böden: Das Planfräsen fräst davor die ebenen Flächen – es gehört dazu.
        yield from raeumen.vorschau_schritte(self.job, boeden, mit_stand(boeden, (plan,)))
        nur = (raeumen.vorschau, raeumen.zeit, raeumen.ergebnis_basis, raeumen.hinweis.text())
        nur_weg = raeumen.schon_weg
        if nur[0] is None and alles[0] is not None:
            # Die Böden allein gehen nicht (der Fräser passt nicht in die Tasche – am Testteil T1
            # in der dreieckigen): keine Folge, das Räumen nimmt alles wie ohne sie. Sonst stand
            # das Räumen angehakt ohne Bahn da, und der Assistent wartete auf sie.
            if not plan.von_hand:
                self._fuellt = True
                try:
                    plan.haken.setChecked(False)
                    plan.zustand_zeigen()
                finally:
                    self._fuellt = False
            raeumen.vorschau, raeumen.zeit, raeumen.ergebnis_basis, hinweis = alles
            raeumen.schon_weg = alles_weg
            raeumen.ergebnis.setText(raeumen.ergebnis_basis)
            raeumen.material.setText(_material_text(raeumen.vorschau))
            raeumen.hinweis.setText(hinweis)
            return
        zeiten = (plan.zeit, alles[1], nur[1])
        # Bringt das Planfräsen ein eigenes Werkzeug, zählt sein Wechsel zur Folge (W-040).
        gleich = getattr(plan.fraeser(), "kennung", None) == getattr(
            raeumen.fraeser(), "kennung", None
        )
        wechsel = 0.0 if gleich else self._wechsel_dazu(plan, (plan, raeumen))
        if not (plan.von_hand or raeumen.von_hand) and all(z and z > 0 for z in zeiten):
            folge_schneller = plan.zeit + nur[1] + wechsel < alles[1]
            self._fuellt = True
            try:
                plan.haken.setChecked(folge_schneller)
                raeumen.haken.setChecked(True)
                plan.zustand_zeigen()
                raeumen.zustand_zeigen()
            finally:
                self._fuellt = False
        if plan.aktiv():
            self._raeumen_boeden = list(boeden)
            raeumen.vorschau, raeumen.zeit, raeumen.ergebnis_basis, hinweis = nur
            raeumen.schon_weg = nur_weg
        else:
            raeumen.vorschau, raeumen.zeit, raeumen.ergebnis_basis, hinweis = alles
            raeumen.schon_weg = alles_weg
        raeumen.ergebnis.setText(raeumen.ergebnis_basis)
        raeumen.material.setText(_material_text(raeumen.vorschau))
        raeumen.hinweis.setText(hinweis)
        if not all(z and z > 0 for z in zeiten):
            return
        folge, ganz = plan.zeit + nur[1] + wechsel, alles[1]
        prozent = int(round((max(folge, ganz) / min(folge, ganz) - 1.0) * 100.0))
        if plan.aktiv():
            plan.ergebnis.setText(
                tr("ba.wettbewerb.folge", text=plan.ergebnis_basis, prozent=prozent)
            )
            raeumen.ergebnis.setText(tr("ba.wettbewerb.nur_boeden", text=nur[2]))
        else:
            plan.ergebnis.setText(
                tr("ba.wettbewerb.folge_langsamer", text=plan.ergebnis_basis, prozent=prozent)
            )
            raeumen.ergebnis.setText(tr("ba.wettbewerb.alles", text=alles[2], prozent=prozent))

    def _gruppen(self):
        """Die Strategien, die dieselbe Aufgabe lösen: Planfräsen, Räumen und Nut auf ebenen
        Flächen (dem Grund einer Nut); Bohren, Bohrung fräsen, Kontur, Nut und Räumen an Wänden
        (Räumen an solchen, die durch das Teil gehen: bis durch). Nut und Räumen stehen in beiden
        – sie treten dort an, wo ihre Flächen dieselben sind."""
        return (
            (self.plan, self.raeumen, self.nut),
            (self.bohren, self.bohrung, self.kontur, self.nut, self.raeumen),
            (self.schlichten3d, self.flanke),
        )

    def _gegner(self, block):
        """Die Strategien, die dieselbe Aufgabe lösen wie `block` – aus allen seinen Gruppen."""
        gegner = []
        for gruppe in self._gruppen():
            if block in gruppe:
                gegner.extend(b for b in gruppe if b is not block and b not in gegner)
        return gegner

    def _im_wettbewerb(self, block):
        """Rechnet der Block mit, obwohl er nicht angehakt ist – weil sein Gegner auf denselben
        Flächen angehakt ist und niemand seinen Haken von Hand genommen hat (Grundsatz 0: die
        Zeit entscheidet)?"""
        if self.zu_aendern is not None or not block.moeglich or block.von_hand:
            return False
        gegner = [g for g in self._gegner(block) if g.aktiv()]
        if not gegner:
            return False
        form = vr.modell(self.job).Shape
        if block is self.raeumen and self._nur_boeden(form) is not None:
            return True  # die Folge mit den Taschenböden (_folge)
        if block is self.bohrung and self._von_raeumen_geraeumt(form):
            return False
        return any(self._gleiche_flaechen(block, form, g) for g in gegner)

    def _wettbewerb(self, form, nur_bohrung=False):
        """Je Gruppe (_gruppen: Planfräsen gegen Räumen; Bohren, Bohrung fräsen und Kontur) auf
        denselben Flächen: die schnellste bekommt den Haken, jede Zeile sagt, um wie viel –
        solange niemand einen Haken der Gruppe von Hand gesetzt hat. `nur_bohrung`: die erste
        Gruppe rechnet die Folge (_folge)."""
        if self.zu_aendern is not None:
            return
        for gruppe in self._gruppen():
            if nur_bohrung and self.plan in gruppe:
                continue
            self._wettbewerb_gruppe(form, gruppe)

    def _wettbewerb_flaechen(self, block, form):
        """Die Flächen, um die der Block antritt: seine eigenen – beim Räumen ohne die Gründe, die
        die angehakte Nut fräst (die räumt es nicht; Manuels Klemmung: sonst traten Planfräsen
        und Räumen auf denselben ebenen Flächen nicht gegeneinander an, beide blieben angehakt,
        und das Räumen legte eine leere Operation an)."""
        eigene = self._eigene(block, form)
        if block is not self.raeumen or not self.nut.aktiv():
            return eigene
        if self._gleiche_flaechen(block, form, self.nut):
            return eigene
        nut = {f for f in self._eigene(self.nut, form) if nb.ist_grund(form, f)}
        return [f for f in eigene if f not in nut] or eigene

    def _wettbewerb_gruppe(self, form, gruppe):
        """Die schnellste der Gruppe bekommt den Haken; wer nicht geht (rot), verliert ihn, wenn
        eine andere auf denselben Flächen geht – sonst ginge „Anlegen“ nicht (ein Ø 12 passt
        nicht in die Bohrung Ø 8,5, die der Bohrer bohrt)."""
        mit = [b for b in gruppe if b.zeit is not None and b.zeit > 0 and b.moeglich]
        if not mit:
            return
        teile = {}
        for b in gruppe:
            eigene = frozenset(self._wettbewerb_flaechen(b, form))
            if eigene:
                teile.setdefault(eigene, []).append(b)
        if len(teile) > 1:
            # Verschiedene Flächen (ein Flansch: der Bohrer die kleinen Bohrungen, der Fräser
            # alle; ein Deckel: die Kontur auch die Wände der Tasche) – je gleiche Flächen ein
            # eigener Wettbewerb; wer allein steht, bleibt; wer dort rot ist, verliert den Haken.
            for teil in teile.values():
                if len(teil) > 1:
                    self._wettbewerb_gruppe(form, teil)
            return
        # Auf dem Grund einer Nut schnitten Planfräsen und Räumen zuerst in voller Breite – mehr
        # als ae, nur scheinbar schneller (an der offenen Nut 0,19 statt 0,85 min, mit Eilgang
        # ins Material). Kann die Nut sie fräsen, treten sie nicht an (P-2026-10-01-47).
        # Hält das Räumen die Last auch in der Nut („adaptiv“ in einer breiten, seit 0.126.0),
        # tritt es an wie jede andere, die Zeit entscheidet.
        voll = []
        if self.nut in mit and self._nur_nutgruende(form):
            bahn = self.raeumen.vorschau
            haelt = getattr(bahn, "variante", "") in ("adaptiv", rb.STICHE) and getattr(
                bahn, "haelt", False
            )
            voll = [b for b in mit if b is self.plan or (b is self.raeumen and not haelt)]
            for b in voll:
                b.ergebnis.setText(tr("ba.wettbewerb.vollschnitt", text=b.ergebnis_basis))
            mit = [b for b in mit if b not in voll]
        # Wer die Flächen nicht erreicht (_unerreicht: der Fräser passt nicht hinein, die Bahn
        # überstreicht sie nicht), ist nur scheinbar schneller – er tritt nicht an, wenn ein
        # anderer sie erreicht (Manuel, 2026-10-16, C-Ring: Räumen „die schnellste“ mit einem
        # Drittel der Ringnut).
        luecke = {b: self._unerreicht(b, form) for b in mit}
        if any(luecke.values()) and not all(luecke.values()):
            for b in [b for b in mit if luecke[b]]:
                name, anteil = min(luecke[b].items(), key=lambda e: e[1])
                b.ergebnis.setText(
                    tr(
                        "ba.wettbewerb.erreicht_nicht",
                        text=b.ergebnis_basis,
                        flaeche=name,
                        anteil=int(round(100.0 * anteil)),
                    )
                )
                voll.append(b)
            mit = [b for b in mit if not luecke[b]]
        zusatz = 0.0
        if self.raeumen in mit and self.kontur in mit and self.kontur.werte().get("schlichten"):
            zusatz = self._schlichtzug_zeit(form)
        zusatz_nut = 0.0
        if self.nut in mit and self.kontur in mit and self.kontur.werte().get("schlichten"):
            # Die Nut lässt das Aufmaß stehen, „Schlichten danach“ macht die Wand (P-2026-10-17-41)
            # – gegen die Kontur, die gleich schlichtet, zählt seine Zeit dazu.
            block = self.schlichten_danach
            if block.aktiv() and block.vorschau is not None and self._nut_laesst_aufmass():
                # Neben dem Räumen teilt die Nut sich den Block mit ihm: grob seine ganze Zeit.
                zusatz_nut = block.zeit
        zeit = {
            b: b.zeit
            + (zusatz if b is self.raeumen else zusatz_nut if b is self.nut else 0.0)
            + self._wechsel_dazu(b, gruppe)
            for b in mit
        }
        mit.sort(key=lambda b: zeit[b])
        rot = [
            b
            for b in gruppe
            if b not in mit
            and b.aktiv()
            and b.hinweis.text()
            and self._gleiche_flaechen(mit[0], form, b)
        ]
        if len(mit) < 2:
            if rot or voll:  # allein in dieser Gruppe – entschieden wird, wo sie Gegner hat
                self._haken_setzen(gruppe, mit[0], rot + voll)
            return
        schnellste, zweite = mit[0], mit[1]

        def prozent(block):
            return int(round((zeit[block] / zeit[schnellste] - 1.0) * 100.0))

        # Unter 1 % nicht „0 % langsamer“, sondern „weniger als 1 %“ – den Haken hat trotzdem die
        # schnellere (P-2026-10-02-53: die Nut in Bögen und die Kontur liegen oft gleichauf).
        basis, andere = schnellste.ergebnis_basis, zweite.s.titel()
        if prozent(zweite) < 1:
            text = tr("ba.wettbewerb.schnellste_knapp", text=basis, andere=andere)
        else:
            text = tr(
                "ba.wettbewerb.schnellste", text=basis, andere=andere, prozent=prozent(zweite)
            )
        schnellste.ergebnis.setText(text)
        for langsamer in mit[1:]:
            basis, andere = langsamer.ergebnis_basis, schnellste.s.titel()
            if prozent(langsamer) < 1:
                text = tr("ba.wettbewerb.langsamer_knapp", text=basis, andere=andere)
            else:
                text = tr(
                    "ba.wettbewerb.langsamer", text=basis, andere=andere, prozent=prozent(langsamer)
                )
            langsamer.ergebnis.setText(text)
        self._haken_setzen(gruppe, schnellste, mit[1:] + rot + voll)

    def _nur_nutgruende(self, form):
        """Sind die Flächen der Nut in dieser Wahl nur Gründe von Nuten (keine Wand)?"""
        flaechen = self.nut.s.flaechen_fuer(form, self.gewaehlte)
        return bool(flaechen) and all(
            nb.ist_grund(form, n) and nb.ist_nut(form, n) for n in flaechen
        )

    def _haken_setzen(self, gruppe, schnellste, andere):
        """Der Haken bei `schnellste`, nicht bei `andere` – solange niemand einen Haken der
        Gruppe von Hand gesetzt hat."""
        if any(b.von_hand for b in gruppe):
            return
        self._fuellt = True
        try:
            for b in [schnellste, *andere]:
                b.haken.setChecked(b is schnellste)
                b.zustand_zeigen()
        finally:
            self._fuellt = False

    def _auffrischen(self):
        self._knoepfe_beschriften()

    # --- Anlegen und Ändern -----------------------------------------------------------------

    def _genau_abholen(self, bloecke):
        """Was die Nebenrechner für die angehakten Räumen-Blöcke schon genau gerechnet haben
        (_Block._genau_starten): Rechnen sie noch, wartet es (das Fenster zeichnet dabei neu) –
        so lange rechnete „Anlegen“ es sonst selbst; die Ergebnisse des Adaptiv-Kerns kommen in
        dessen Merker (raeumen_bahn.adaptiv_merken), das Räumen trifft sie. Alle: Welcher passt,
        weiß erst die Operation (am Testteil rechnete die Folge danach noch Planfräsen und Räumen
        der Böden – angelegt wurde das Räumen über alles, der erste)."""
        from . import nebenrechner as nr

        auftraege = [a for b in bloecke for a in getattr(b, "genau", []) if not a.abgebrochen]
        if not auftraege:
            return
        offen = [a for a in auftraege if not a.erledigt]
        if offen:
            with contextlib.suppress(nr.Fehler):
                nr.pool().warten(offen, zwischendurch=nr.ereignisse_ohne_eingaben)
        for auftrag in auftraege:
            if auftrag.fertig and auftrag.fehler is None and not auftrag.abgebrochen:
                if isinstance(auftrag.ergebnis, hsb.Bahn):  # unter dem Rand (_genau_unter_dem_rand)
                    hsb.geplant_merken(auftrag.ergebnis)
                elif isinstance(auftrag.ergebnis, dict):
                    rb.adaptiv_merken(auftrag.ergebnis)

    def _genau_beenden(self):
        """Beim Schließen: Was an genauen Bahnen (_Block._genau_starten) noch wartet, fällt weg;
        was schon rechnet, rechnet zu Ende (abbrechen beendete seinen Arbeiter)."""
        from . import nebenrechner as nr

        for block in getattr(self, "bloecke", []):
            for auftrag in getattr(block, "genau", []):
                if not auftrag.erledigt and getattr(auftrag, "arbeiter", None) is None:
                    with contextlib.suppress(Exception):
                        nr.pool().abbrechen(auftrag)
            block.genau = []

    def _nur_diese_anlegen(self, aktive):
        """Welche der angehakten Blöcke „Anlegen“ wirklich anlegt – hier alle; die Beta
        (gui_bearbeitung_beta) nur die der Schritte, die man gesehen hat."""
        return aktive

    def _anlegen(self):
        """Werkzeug-Controller und die angehakten Operationen in den Job – ein eigener Schritt
        Rückgängig, in einem Befehl (_im_befehl). Geht es nicht, steht der Grund rot im
        Fenster: False."""
        self._genau_abholen(self.aktive_bloecke())
        form = vr.modell(self.job).Shape
        aktive = self._nur_diese_anlegen(self._in_anlege_reihe(self.aktive_bloecke(), form))
        if self.raeumen in aktive and not self._flaechen(self.raeumen, form):
            # Alle seine Flächen nimmt schon ein anderer (die Gründe der Nut) – ohne Fläche
            # räumte die Operation das ganze Teil.
            aktive.remove(self.raeumen)

        folge = []  # die weiteren Operationen eines Blocks (Schlichten danach: Boden und Wände)

        def anlegen():
            self.doc.openTransaction(tr("ba.transaktion.anlegen"))
            ops = []
            try:
                ue.uebergeben(self.bibliothek)
                if not self._job_dazu:  # im vorhandenen Job bleibt, was dort steht
                    fremde = js.unbenutzte_fremde_controller(self.job, self.bibliothek)
                    js.controller_weg(self.doc, fremde)
                tc_davor = None
                # Derselbe Fräser mit demselben Einsatz: ein Controller (am C-Ring legten Räumen T3
                # und Nut T3 je einen „T3 VHM 6 – Schruppen“ an).
                controller = {}
                for block in aktive:
                    schluessel = (
                        getattr(block.fraeser(), "kennung", None),
                        getattr(block.fraeser(), "magazin_nummer", None),  # sein Platz (je_platz)
                        repr(block.einsatz()),
                        self.werkstoff(),
                    )
                    tc = controller.get(schluessel)
                    if tc is None:
                        tc = js.controller_ohne_transaktion(
                            self.doc, self.job, block.fraeser(), block.einsatz(), self.werkstoff()
                        )
                        if schluessel[0] is not None:
                            controller[schluessel] = tc
                    flaechen = self._flaechen(block, form)
                    werte = dict(block.werte(), **(self._zusatz(block, form) or {}))
                    werte["eintauchwinkel"] = _eintauchwinkel(block.fraeser())
                    if block is self.schlichten_danach:
                        neue = self._schlichten_danach_anlegen(tc, tc_davor or tc, werte)
                        ops.append(neue[0])
                        folge.extend(neue[1:])
                    else:
                        if block is self.raeumen or block is self.nut:
                            folge.extend(self._vorbohren_anlegen(block, werte))
                        neue_op = block.s.lege_an(self.job, tc, werte, flaechen)
                        au.setze(neue_op, werte.get("aufloesung", 0.0))
                        ops.append(neue_op)
                        if block is self.bohren:
                            folge.extend(self._nebenbohrer_anlegen(werte))
                    tc_davor = tc
                    uhren.atmen()
                    # Gleich rechnen: Die nächste rechnet mit dem Material, das diese lässt
                    # (Materialstand, W-012) – FreeCAD rechnete sie sonst in beliebiger Folge.
                    self.doc.recompute()
                self.doc.recompute()
                # Was nach dem Rechnen nichts fräst – ein 3D-Schruppen, dem das genaue Räumen
                # keinen Rest ließ (W-038) –, kommt nicht in den Job: Unnötiges weg.
                for liste in (ops, folge):
                    for k, op in enumerate(liste):
                        if op is not None and pp.ohne_arbeit(op):
                            weg.append(op.Label)
                            self.doc.removeObject(op.Name)
                            liste[k] = None
                folge[:] = [op for op in folge if op is not None]
            except Exception:
                self.doc.abortTransaction()
                raise
            self.doc.commitTransaction()
            return ops

        weg = []  # die Operationen, die nichts fräsen – wieder entfernt
        try:
            self.operationen = _im_befehl(anlegen)
        except Exception as fehler:  # CAM meldet vieles nur als Ausnahme
            FreeCAD.Console.PrintError(f"Bearbeitung: {fehler}\n{traceback.format_exc()}")
            self.operationen = []
            self.operation = None
            self.hinweis.setText(tr("ba.fehler.anlegen", fehler=str(fehler)))
            self._knoepfe_beschriften()
            return False
        for block, op in zip(aktive, self.operationen, strict=False):
            block.operation = op
        self.operationen = [op for op in self.operationen if op is not None]
        self.operation = self.operationen[0] if self.operationen else None
        self.operationen += folge
        if weg:
            FreeCAD.Console.PrintMessage(tr("ba.leer_weg", namen=", ".join(weg)) + "\n")
        return True

    def _nebenbohrer_anlegen(self, werte):
        """Nach „Bohren“ die Bohrungen der weiteren Bohrer (_nebenbohrer): je Bohrer FreeCADs
        Bohren mit eigenem Controller. In der Transaktion von _anlegen; gibt die neuen
        Operationen zurück."""
        ops = []
        for gruppe in werte.get("nebenbohrer") or []:
            werkzeug = gruppe["werkzeug"]
            einsaetze = self.bohren._passende_einsaetze(werkzeug, self.werkstoff())
            tc = js.controller_ohne_transaktion(
                self.doc, self.job, werkzeug, einsaetze[0] if einsaetze else None, self.werkstoff()
            )
            ops.append(bh.lege_an(self.job, tc, gruppe["flaechen"], werte["hub"]))
        return ops

    def _vorbohren_anlegen(self, block, werte):
        """Vor dem Räumen oder der Nut das Vorbohren: FreeCADs Bohren an den Stellen, an denen ihre
        Vorschau ins Volle eintauchte (raeumen.Vorbohren.je_loch) – je Bohrer eine Operation (die
        Nuten verschieden breit: verschiedene Bohrer). Danach rechnen sie mit den Löchern
        (Materialstand) und tauchen dort senkrecht ein. In der Transaktion von _anlegen; gibt die
        neuen Operationen zurück."""
        vorbohren = getattr(block.vorschau, "vorbohren", None)
        if not werte.get("vorbohren") or vorbohren is None:
            return []
        vorgabe = (werte.get("vorbohrer") or {}).get("kennung", "")
        je_bohrer = {}
        for x, y, z, _d, kennung in vorbohren.je_loch():
            je_bohrer.setdefault(kennung or vorgabe, []).append((x, y, z))
        ops = []
        for kennung, stellen in je_bohrer.items():
            werkzeug = next((w for w in self.bibliothek.werkzeuge if w.kennung == kennung), None)
            if werkzeug is None:
                continue
            einsaetze = self.bohren._passende_einsaetze(werkzeug, self.werkstoff())
            tc = js.controller_ohne_transaktion(
                self.doc, self.job, werkzeug, einsaetze[0] if einsaetze else None, self.werkstoff()
            )
            ops += bh.an_stellen_anlegen(
                self.job, tc, stellen, tr("ba.raeumen.vorbohren.name", werkzeug=f"T{tc.ToolNumber}")
            )
        if ops:
            self.doc.recompute()  # das Räumen und die Nut rechnen mit den Löchern
        return ops

    def _vorbohrer_liste(self, fraeser):
        """Die Bohrer fürs Vorbohren der Nut – [{kennung, durchmesser, spitzenwinkel,
        schneidenlaenge, vorschub}]: im Magazin der Maschine (ohne Magazin aus der
        Werkzeugverwaltung), mit Schnittwerten, Ø zwischen dem Fräser und doppelt so groß; welcher
        in welche Nut passt, sagt ihre Vorschau (nut.vorschau)."""
        if fraeser is None or self.bibliothek is None or fraeser.durchmesser <= 0:
            return []
        d = float(fraeser.durchmesser)
        magazin = self.magazin()
        liste = []
        for w in self.bibliothek.werkzeuge:
            if w.art != wz.BOHRER or not d - 1e-6 <= w.durchmesser <= 2.0 * d:
                continue
            if magazin is not None and mg.rang(w, magazin) == mg.NICHT_IM_MAGAZIN:
                continue
            einsaetze = self.bohren._passende_einsaetze(w, self.werkstoff())
            if einsaetze:
                liste.append(
                    {
                        "kennung": w.kennung,
                        "durchmesser": float(w.durchmesser),
                        "spitzenwinkel": float(w.spitzenwinkel or wz.SPITZENWINKEL_BOHRER),
                        "schneidenlaenge": float(w.schneidenlaenge or 0.0),
                        "vorschub": float(js.werte(w, einsaetze[0])[1]),
                    }
                )
        return sorted(liste, key=lambda b: b["durchmesser"])

    def _vorbohrer_anlegen(self, durchmesser, tiefe, winkel=None):
        """„Bohrer Ø … anlegen und vorbohren“: ein Bohrer (HSS, 118°, Schneide mindestens 8 × D und
        5 mm mehr als `tiefe`) mit Richtwerten in die Werkzeugverwaltung – steht eine Maschine mit
        Magazin da, auch ins Magazin –, gespeichert; der Assistent liest es neu, das Vorbohren
        geht."""
        if self.bibliothek is None:
            return
        # Eine andere Spitze als 118° (`winkel`, eine Sackbohrung): ab 130° ein VHM-Bohrer – 140°
        # ist ihre übliche Spitze.
        winkel = float(winkel or wz.SPITZENWINKEL_BOHRER)
        name = tr("ba.raeumen.vorbohren.bohrer_name", d=f"{durchmesser:g}")
        if abs(winkel - wz.SPITZENWINKEL_BOHRER) > bh.GLEICH_WINKEL:
            name = f"{name} {winkel:g}°"
        bohrer = wz.Werkzeug(
            nummer=self.bibliothek.naechste_nummer(),
            name=name,
            art=wz.BOHRER,
            durchmesser=float(durchmesser),
            schneiden=2,
            schneidenlaenge=float(math.ceil(max(8.0 * durchmesser, tiefe + 5.0))),
            spitzenwinkel=winkel,
            schneidstoff=wz.VHM if winkel >= 130.0 else wz.HSS,
        )
        self._werkzeug_anlegen(bohrer)

    def _werkzeug_anlegen(self, werkzeug):
        """Ein Werkzeug, das ein Knopf anbietet, mit Richtwerten in die Werkzeugverwaltung – steht
        eine Maschine mit Magazin da, auch ins Magazin –, gespeichert; der Assistent liest es
        neu."""
        from . import werkzeugkiste as wk

        wk.richtwerte_eintragen(werkzeug)
        self.bibliothek.werkzeuge.append(werkzeug)
        magazin = self.magazin()
        if magazin is not None:
            mg.uebernehmen(self.bibliothek, magazin, werkzeug, self.job)  # speichert
        else:
            self.bibliothek.speichern()
        self._werkzeuge_gespeichert()

    def _vorbohrer(self, fraeser):
        """Der Bohrer fürs Vorbohren zum Räumfräser `fraeser` – {kennung, durchmesser,
        spitzenwinkel, schneidenlaenge, vorschub} – oder None: ein Bohrer zwischen dem Fräser und
        VORBOHRER_HOECHSTENS mal ihm, im Magazin der Maschine (ohne Magazin aus der
        Werkzeugverwaltung), mit Schnittwerten; am liebsten VORBOHRER_LUFT größer, dann der
        kleinste."""
        if fraeser is None or self.bibliothek is None or fraeser.durchmesser <= 0:
            return None
        d = float(fraeser.durchmesser)
        magazin = self.magazin()
        kandidaten = []
        for w in self.bibliothek.werkzeuge:
            if w.art != wz.BOHRER or not d - 1e-6 <= w.durchmesser <= d * VORBOHRER_HOECHSTENS:
                continue
            if magazin is not None and mg.rang(w, magazin) == mg.NICHT_IM_MAGAZIN:
                continue
            einsaetze = self.bohren._passende_einsaetze(w, self.werkstoff())
            if einsaetze:
                kandidaten.append((w, js.werte(w, einsaetze[0])[1]))
        if not kandidaten:
            return None
        w, vorschub = min(
            kandidaten, key=lambda k: (k[0].durchmesser < d + VORBOHRER_LUFT, k[0].durchmesser)
        )
        return {
            "kennung": w.kennung,
            "durchmesser": float(w.durchmesser),
            "spitzenwinkel": float(w.spitzenwinkel or wz.SPITZENWINKEL_BOHRER),
            "schneidenlaenge": float(w.schneidenlaenge or 0.0),
            "vorschub": float(vorschub),
        }

    def _schlichten_danach_anlegen(self, tc, tc_davor, werte):
        """Die Operationen von „Schlichten danach“ – auf Wunsch der Messstopp (mit dem Controller
        davor, `tc_davor`), dann der Boden (ein Räumen ohne Aufmaß am Boden), dann die Wände (eine
        Kontur mit Breite = Aufmaß, nur der Zug an der Wand) – so viel davon, wie die Vorschau
        fand. In der Transaktion von _anlegen; gibt die neuen Operationen zurück."""
        bahn = self.schlichten_danach.vorschau
        werkzeug = f"T{tc.ToolNumber}"
        ops = []
        if werte.get("messstopp"):
            ops.append(ms.lege_an(self.job, tc_davor, tc))
        if getattr(bahn, "boden", None) is not None:
            ops.append(
                ra.lege_an(
                    self.job, tc, werte["zustellung"], werte["zeilenabstand"],
                    werte["aufmass_wand"], 0.0, werte["gleichlauf"],
                    name=tr("ba.schlichten_danach.boden_name", werkzeug=werkzeug),
                    flaechen=werte["boden_flaechen"],
                )  # fmt: skip
            )
            self.doc.recompute()  # die Wände rechnen mit dem fertigen Boden
        if getattr(bahn, "kontur_waende", None):
            aufmass = werte["aufmass_wand"]
            name = (
                tr("ba.raeumen.schlichten_name", werkzeug=werkzeug)
                if self.raeumen.aktiv()
                else tr("ba.nut.schlichten_name", werkzeug=werkzeug)
            )
            ops.append(
                ko.lege_an(
                    self.job, tc, werte["zustellung"], aufmass, aufmass, True, aufmass, name,
                    flaechen=bahn.kontur_waende,
                )  # fmt: skip
            )
        if getattr(bahn, "ring", None) is not None:
            ops.append(
                nu.lege_an(
                    self.job, tc, werte["zustellung"],
                    werte["zeilenabstand"] or tc.Tool.Diameter / 2, 0.0, schlichten=True,
                    gleichlauf=werte["gleichlauf"],
                    name=tr("ba.nut.schlichten_name", werkzeug=werkzeug),
                    flaechen=bahn.ringe, nur_schlichten=True,
                )  # fmt: skip
            )
        if getattr(bahn, "eng", None) is not None:
            tc_eng = self._nut_schlichtcontroller()
            ops.append(
                nu.lege_an(
                    self.job, tc_eng, werte["zustellung"], tc_eng.Tool.Diameter / 2, 0.0,
                    schlichten=True, gleichlauf=werte["gleichlauf"],
                    name=tr("ba.nut.schlichten_name", werkzeug=f"T{tc_eng.ToolNumber}"),
                    flaechen=bahn.enge, nur_schlichten=True,
                )  # fmt: skip
            )
        if not ops or (len(ops) == 1 and werte.get("messstopp")):
            raise ValueError(tr("ba.schlichten_danach.nichts"))
        return ops

    def _nut_schlichtcontroller(self):
        """Der Controller für das Schlichten der engen Nuten (_Schlichtbahn.eng): der Fräser der
        Nut mit seinem Einsatz fürs Schlichten – hat er keinen, mit dem der Nut. In der
        Transaktion von _anlegen."""
        werkzeug = self.nut.fraeser()
        einsaetze = self.nut._passende_einsaetze(werkzeug, self.werkstoff())
        einsatz = next((e for e in einsaetze if e.art == wz.SCHLICHTEN), None)
        return js.controller_ohne_transaktion(
            self.doc, self.job, werkzeug, einsatz or self.nut.einsatz(), self.werkstoff()
        )

    def _aendern(self):
        """Die Operation bekommt Fräser, Einsatz, Werte und Flächen aus ihrem Block – ein
        eigener Schritt Rückgängig; den alten Controller nimmt es heraus, wenn ihn keine
        Operation mehr benutzt. Geht es nicht, steht der Grund rot im Fenster: False."""
        op = self.zu_aendern
        block = self.block_zu_aendern
        self._genau_abholen([block])
        form = vr.modell(self.job).Shape
        flaechen = block.s.flaechen_fuer(form, self.gewaehlte)
        werte = block.werte()
        werte["eintauchwinkel"] = _eintauchwinkel(block.fraeser())
        if block is self.gewindefraesen:
            werte["werkzeug"] = block.fraeser()  # Steigung und Zähne kennt CAM nicht

        def aendern():
            self.doc.openTransaction(tr("ba.transaktion.aendern"))
            try:
                ue.uebergeben(self.bibliothek)
                bisher = op.ToolController
                tc = js.controller_fuer(
                    self.doc, self.job, block.fraeser(), block.einsatz(), self.werkstoff(), op
                )
                block.s.aendere(op, tc, werte, flaechen)
                au.setze(op, werte.get("aufloesung", 0.0))
                frei = bisher is not None and not js.operationen_mit(bisher, self.job)
                if frei and bisher is not tc:
                    js.controller_weg(self.doc, [bisher])
                self.doc.recompute()
            except Exception:
                self.doc.abortTransaction()
                raise
            self.doc.commitTransaction()

        try:
            _im_befehl(aendern)
        except Exception as fehler:  # CAM meldet vieles nur als Ausnahme
            FreeCAD.Console.PrintError(f"Bearbeitung: {fehler}\n{traceback.format_exc()}")
            self.hinweis.setText(tr("ba.fehler.aendern", fehler=str(fehler)))
            self._knoepfe_beschriften()
            return False
        return True
