# SPDX-License-Identifier: LGPL-2.1-or-later
"""Befehl und Aufgabenfenster „Bestückung“ (W-002 Stufe G).

Welches Werkzeug des Jobs auf welchem Revolverplatz steckt – jeder Job hat seine
eigene Bestückung (Manuel, 2026-09-30: „ja jeder job hat seine eigene bestückung
und man hat einfach die maschine die man ablegt und immer wieder laden kann“).
Oben Job und Maschine, darunter je Platz eine Auswahl der Werkzeuge des Jobs. In
der 3D-Ansicht der Maschine stecken sie im Revolver, jeder Platz mit seinem Namen
(„P3“) – Manuel: „auserdem wird die bestückung nicht dargestellt auf der
maschine“. Gerechnet wird in bestueckung.py: Der Platz ist die Nummer der
Controller; wählt man für einen Platz ein Werkzeug, zieht es dorthin um, und
steckte dort schon eins, tauschen die beiden – ein Schritt Rückgängig im
Dokument des Jobs.

Wie „Auf der Maschine prüfen“ öffnet sich das Fenster im Dokument der Maschine:
die offene, sonst die, die sich der Job gemerkt hat (gui_reichweite.maschine_fuer).
Schließen merkt sie sich am Job und kehrt zu seinem Dokument zurück.
"""

import html

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import bestueckung as bs
from . import gui_abfahren, gui_reichweite, symbol
from . import job_schnittwerte as js
from . import kette as kette_modul
from . import magazin as mg
from . import maschine as m
from . import reichweite as rw
from . import werkzeuge as wz
from .gui_hilfe import kopfzeile
from .gui_job_schnittwerte import dokument_mit_job
from .gui_teile import GRAU, ROT, ruhiges_mausrad
from .gui_zahlen import dezimal
from .sprache import tr

NAME_FARBE = (0.10, 0.25, 0.65)  # die Namen der Plätze („P3“) in der 3D-Ansicht
NAME_GROESSE = 14  # Punkt
HINSEHEN_RAND = 1.3


class BefehlBestueckung:
    """Befehl in der Werkzeugleiste: zeigt und ändert die Bestückung eines Jobs."""

    def GetResources(self):
        return {
            "Pixmap": symbol("bestueckung.svg"),
            "MenuText": tr("befehl.bestueckung.titel"),
            "ToolTip": tr("befehl.bestueckung.tooltip"),
        }

    def IsActive(self):
        return not FreeCADGui.Control.activeDialog()

    def Activated(self):
        hauptfenster = FreeCADGui.getMainWindow()
        dokument = dokument_mit_job(tr("bs.titel"), tr("bs.kein_job"))
        if dokument is None:
            return
        jobs = js.jobs(dokument)
        job = gui_reichweite.job_fuer(jobs)
        gewaehlt = gui_reichweite.maschine_fuer(job, hauptfenster)
        if gewaehlt is None:
            return
        assembly, maschine = gewaehlt
        gui_reichweite.zeige_dokument(assembly.Document)
        FreeCADGui.Control.showDialog(BestueckungsPanel(jobs, job, assembly, maschine))


class Revolverbild:
    """Die Werkzeuge des Jobs auf ihren Plätzen in der 3D-Ansicht der Maschine – dieselben
    Körper wie beim Abfahren (gui_abfahren.werkzeug_knoten) –, dazu an jedem Platz sein Name.
    Mit `magazin` auch, was dort laut Magazin beladen ist und der Job nicht braucht –
    durchscheinend (W-002 Stufe H4: die Kollision prüft es mit). Nichts davon steht im
    Dokument."""

    DURCHSCHEINEND = 0.6  # ein beladenes Werkzeug, das der Job nicht braucht

    def __init__(self, ansicht, plaetze, auf, bibliothek, magazin=None):
        from pivy import coin

        self.ansicht = ansicht
        self.wurzel = coin.SoSeparator()
        self._lagen = []  # [(Platz, SoTransform)]
        self.werkzeuge = {}  # Platznummer → gezeigter Eintrag
        self.beladen = {}  # Platznummer → Werkzeug aus dem Magazin, das der Job nicht braucht
        im_job = {e.werkzeug.kennung for es in auf.values() for e in es if e.werkzeug is not None}
        for platz in plaetze:
            knoten = coin.SoSeparator()
            lage = coin.SoTransform()
            knoten.addChild(lage)
            hier = auf.get(platz.Platz, [])
            dort = _beladen_auf(magazin, bibliothek, platz.Platz, im_job) if not hier else None
            if hier:
                tc = hier[0].controller[0]
                laenge = rw.werkzeuglaenge(tc, bibliothek)[0]
                masse = rw.werkzeugmasse(tc, bibliothek, laenge)
                halter = rw.werkzeughalter(tc, bibliothek)
                knoten.addChild(gui_abfahren.werkzeug_knoten(laenge, masse, halter))
                self.werkzeuge[platz.Platz] = hier[0]
            elif dort is not None:
                laenge = rw.laenge_des_werkzeugs(dort, bibliothek)[0]
                knoten.addChild(
                    gui_abfahren.werkzeug_knoten(
                        laenge,
                        rw.masse_des_werkzeugs(dort),
                        bibliothek.halter_fuer_pruefung(dort),
                        self.DURCHSCHEINEND,
                    )
                )
                self.beladen[platz.Platz] = dort
            knoten.addChild(_name(coin, m.name_von(platz)))
            self.wurzel.addChild(knoten)
            self._lagen.append((platz, lage))
        ansicht.getSceneGraph().addChild(self.wurzel)
        self.folge()

    def folge(self):
        """Jedes Werkzeug dorthin, wo sein Platz gerade steht."""
        for platz, lage in self._lagen:
            ort = m.globale_platzierung(platz.Lcs)
            lage.translation.setValue(ort.Base.x, ort.Base.y, ort.Base.z)
            q = ort.Rotation.Q  # (x, y, z, w) – dieselbe Reihenfolge wie bei Coin
            lage.rotation.setValue(q[0], q[1], q[2], q[3])

    def hinsehen(self):
        """Richtet die Kamera auf den Revolver mit den Werkzeugen."""
        region = gui_abfahren.ausschnitt(self.ansicht)
        self.ansicht.getCameraNode().viewAll(self.wurzel, region, HINSEHEN_RAND)

    def weg(self):
        wurzel = self.ansicht.getSceneGraph()
        if wurzel.findChild(self.wurzel) >= 0:
            wurzel.removeChild(self.wurzel)


def _beladen_auf(magazin, bibliothek, platz, im_job):
    """Das Werkzeug, das laut Magazin auf `platz` beladen ist – None, wenn keins, wenn es der
    Job ohnehin hat (`im_job`: Kennungen) oder wenn es keinen Durchmesser hat (keine Form)."""
    if magazin is None or bibliothek is None:
        return None
    eintrag = magazin.auf_platz(platz)
    werkzeug = bibliothek.werkzeug_mit_kennung(eintrag.werkzeug) if eintrag is not None else None
    if werkzeug is None or werkzeug.kennung in im_job or not werkzeug.durchmesser:
        return None
    return werkzeug


def _name(coin, text):
    """„P3“ am Ursprung des Platzes – obenauf gezeichnet, so steht es auch vor dem Revolver."""
    teil = coin.SoSeparator()
    tiefe = coin.SoDepthBuffer()
    tiefe.test = False
    teil.addChild(tiefe)
    farbe = coin.SoBaseColor()
    farbe.rgb.setValue(*NAME_FARBE)
    teil.addChild(farbe)
    schrift = coin.SoFont()
    schrift.size = NAME_GROESSE
    teil.addChild(schrift)
    name = coin.SoText2()
    name.string = text
    teil.addChild(name)
    return teil


class BestueckungsPanel:
    """Das Aufgabenfenster. FreeCAD ruft `getStandardButtons`, `accept` und `reject` auf."""

    offen = None  # das gerade offene Fenster – für die Oberflächen-Szenarien

    def __init__(self, jobs, job, assembly, maschine):
        BestueckungsPanel.offen = self
        self.jobs = jobs
        self.job = job
        self.assembly = assembly
        self.maschine = maschine
        self.zurueck_zu = job.Document if job.Document is not assembly.Document else None
        self.bibliothek = _bibliothek()
        self.plaetze = m.revolverplaetze(maschine, kette_modul.lies_kette(assembly))
        self.eintraege = []  # bestueckung.Eintrag des Jobs, in der Reihenfolge der Auswahlen
        self.wahlen = {}  # Platz → QComboBox
        self.bild = None
        self.form = self._baue()
        self.wahl_job.setCurrentIndex(jobs.index(job))
        self._job_gewechselt()

    def getStandardButtons(self):
        return QtGui.QDialogButtonBox.Close

    def accept(self):
        return self._schliessen()

    def reject(self):
        return self._schliessen()

    def _schliessen(self):
        BestueckungsPanel.offen = None
        self._bild_weg()
        self._maschine_merken()
        FreeCADGui.Control.closeDialog()
        if self.zurueck_zu is not None and self.zurueck_zu.Name in FreeCAD.listDocuments():
            gui_reichweite.zeige_dokument(self.zurueck_zu)
        return True

    # --- Aufbau ---------------------------------------------------------------------

    def _baue(self):
        form = QtGui.QWidget()
        form.setWindowTitle(tr("bs.titel"))
        form.setWindowIcon(QtGui.QIcon(symbol("bestueckung.svg")))
        aufbau = QtGui.QVBoxLayout(form)
        aufbau.addWidget(kopfzeile(tr("bs.titel"), "bestueckung"))
        erklaerung = QtGui.QLabel(tr("bs.erklaerung"))
        erklaerung.setWordWrap(True)
        aufbau.addWidget(erklaerung)

        raster = QtGui.QGridLayout()
        raster.setColumnStretch(1, 1)
        self.wahl_job = QtGui.QComboBox()
        for job in self.jobs:
            self.wahl_job.addItem(job.Label)
        self.wahl_job.currentIndexChanged.connect(lambda _i: self._job_gewechselt())
        raster.addWidget(QtGui.QLabel(tr("rw.job")), 0, 0)
        raster.addWidget(ruhiges_mausrad(self.wahl_job), 0, 1)
        maschine = QtGui.QLabel(gui_reichweite.maschinen_text(self.assembly, self.maschine))
        maschine.setWordWrap(True)
        raster.addWidget(QtGui.QLabel(tr("rw.maschine")), 1, 0)
        raster.addWidget(maschine, 1, 1)
        aufbau.addLayout(raster)
        # Ein Grundjob mit geschwenkten Ebenen (3+2): ein Programm, eine Bestückung.
        self.aufspannung = _satz(GRAU)
        aufbau.addWidget(self.aufspannung)

        self.hinweis = _satz(GRAU)
        aufbau.addWidget(self.hinweis)
        plaetze = QtGui.QWidget()
        gitter = QtGui.QGridLayout(plaetze)
        gitter.setContentsMargins(0, 0, 0, 0)
        gitter.setColumnStretch(1, 1)
        for zeile, platz in enumerate(self.plaetze):
            wahl = QtGui.QComboBox()
            wahl.setToolTip(tr("bs.wahl.tooltip"))
            wahl.activated.connect(lambda index, p=platz, w=wahl: self._gewaehlt(p, w, index))
            gitter.addWidget(QtGui.QLabel(m.name_von(platz)), zeile, 0)
            gitter.addWidget(ruhiges_mausrad(wahl), zeile, 1)
            self.wahlen[platz] = wahl
        aufbau.addWidget(plaetze)
        self.doppelt = _satz(ROT)
        aufbau.addWidget(self.doppelt)
        self.ohne_platz = _satz(ROT)
        aufbau.addWidget(self.ohne_platz)
        # Die Rüstliste (W-002 Stufe H3): je Werkzeug, was an der Maschine zu tun ist – mit dem
        # Magazin der Maschine; „Nummern aus dem Magazin“ nummeriert den Job danach (E4).
        self.ruest_titel = QtGui.QLabel()
        schrift = self.ruest_titel.font()
        schrift.setBold(True)
        self.ruest_titel.setFont(schrift)
        aufbau.addWidget(self.ruest_titel)
        self.ruestliste = QtGui.QLabel()
        self.ruestliste.setWordWrap(True)
        self.ruestliste.setTextFormat(QtCore.Qt.RichText)
        aufbau.addWidget(self.ruestliste)
        self.knopf_nummern = QtGui.QPushButton(tr("bs.nummern_aus_magazin"))
        self.knopf_nummern.setToolTip(tr("bs.nummern_aus_magazin.tooltip"))
        self.knopf_nummern.clicked.connect(self.nummern_aus_magazin)
        aufbau.addWidget(self.knopf_nummern)
        self.ohne_magazin = _satz(GRAU)
        aufbau.addWidget(self.ohne_magazin)
        self.knopf_hinsehen = QtGui.QPushButton(tr("bs.hinsehen"))
        self.knopf_hinsehen.setToolTip(tr("bs.hinsehen.tooltip"))
        self.knopf_hinsehen.clicked.connect(self.hinsehen)
        aufbau.addWidget(self.knopf_hinsehen)
        aufbau.addStretch(1)
        return form

    # --- Job, Auswahl, Umlegen ------------------------------------------------------

    def _job_gewechselt(self):
        self.job = self.jobs[max(self.wahl_job.currentIndex(), 0)]
        gui_reichweite.job_merken(self.job)
        self.fuellen()
        self.hinsehen()

    def fuellen(self):
        """Die Auswahlen nach der Bestückung des Jobs, die Sätze darunter, das Bild."""
        self.eintraege = bs.eintraege(self.job, self.bibliothek)
        jobs = bs.aufspannung(self.job)
        self.aufspannung.setText(
            tr("bs.aufspannung", jobs=", ".join(f"„{j.Label}“" for j in jobs))
            if len(jobs) > 1
            else ""
        )
        self.aufspannung.setVisible(len(jobs) > 1)
        auf = bs.auf_plaetzen(self.job, self.bibliothek, self.eintraege)
        nummern = {platz.Platz for platz in self.plaetze}
        magazin = self.magazin()
        im_job = {e.werkzeug.kennung for e in self.eintraege if e.werkzeug is not None}
        for platz, wahl in self.wahlen.items():
            hier = auf.get(platz.Platz, [])
            wahl.blockSignals(True)
            wahl.clear()
            # Frei für den Job – laut Magazin steckt dort vielleicht eins, das er nicht braucht.
            beladen = magazin.auf_platz(platz.Platz) if magazin is not None else None
            dort = self.bibliothek.werkzeug_mit_kennung(beladen.werkzeug) if beladen else None
            if dort is not None and dort.kennung not in im_job:
                frei = tr("bs.frei_beladen", werkzeug=dezimal(wz.kurz(dort)))
            else:
                frei = tr("bs.frei")
            wahl.addItem(frei, -1)
            # Frei machen geht nur, wo nichts steckt – jedes Werkzeug des Jobs braucht einen Platz.
            wahl.model().item(0).setEnabled(not hier)
            for index, eintrag in enumerate(self.eintraege):
                text = dezimal(bs.text(eintrag))
                woanders = [n for n in eintrag.nummern if n != platz.Platz]
                if eintrag not in hier and woanders:
                    n = woanders[0]
                    if n in nummern:
                        text = tr("bs.auf", werkzeug=text, platz=f"P{n}")
                    else:
                        text = tr("bs.ohne_platz", werkzeug=text, nummer=n)
                wahl.addItem(text, index)
            wahl.setCurrentIndex(self.eintraege.index(hier[0]) + 1 if hier else 0)
            wahl.blockSignals(False)
        if not self.plaetze:
            name = self.maschine.Label
            if self.magazin() is not None:
                self.hinweis.setText(tr("bs.kein_revolver_magazin", maschine=name))
            else:
                self.hinweis.setText(tr("bs.kein_revolver", maschine=name))
        elif not self.eintraege:
            self.hinweis.setText(tr("bs.keine_werkzeuge"))
        else:
            self.hinweis.setText("")
        self.hinweis.setVisible(bool(self.hinweis.text()))
        saetze = [
            tr(
                "rw.bestueckung.doppelt",
                platz=f"P{n}",
                werkzeuge=", ".join(dezimal(bs.kurz(e)) for e in es),
            )
            for n, es in bs.doppelt(self.job, self.bibliothek)
        ]
        self.doppelt.setText("\n".join(saetze))
        self.doppelt.setVisible(bool(saetze))
        ohne = [
            f"{dezimal(bs.kurz(e))} (T{e.nummer})"
            for e in self.eintraege
            if self.plaetze and not any(n in nummern for n in e.nummern)
        ]
        self.ohne_platz.setText(tr("bs.nicht_im_revolver", werkzeuge=", ".join(ohne)))
        self.ohne_platz.setVisible(bool(ohne))
        self._ruestliste_fuellen()
        self._bild_neu(auf)

    # --- Rüstliste (W-002 Stufe H3) ------------------------------------------------------

    def magazin(self):
        """Das Magazin, das für die Maschine des Fensters gilt – None ohne."""
        pfad = self.assembly.Document.FileName
        if not pfad or self.bibliothek is None:
            return None
        return mg.des_jobs(None, self.bibliothek, pfad)

    def _nummern(self):
        """Die Plätze des Revolvers – leer an einer Maschine ohne Revolver."""
        return [platz.Platz for platz in self.plaetze]

    def ruestzeilen(self):
        """[(Nummer, Eintrag, Art, Satz)] – die Werkzeuge des Jobs nach Nummer, mit dem, was an
        der Maschine zu tun ist (magazin.ruesten). Leer ohne Magazin."""
        magazin = self.magazin()
        if magazin is None:
            return []
        revolver = bool(self.plaetze)
        zeilen = []
        for eintrag in sorted(self.eintraege, key=lambda e: e.nummer):
            art, satz = mg.ruesten(eintrag.werkzeug, magazin, eintrag.nummer, revolver)
            zeilen.append((eintrag.nummer, eintrag, art, satz))
        return zeilen

    def _ruestliste_fuellen(self):
        from .gui_kollision import GELB

        magazin = self.magazin()
        farben = {
            mg.GERUESTET: GRAU.name(),
            mg.EINSETZEN: GELB,
            mg.ANLEGEN: GELB,
            mg.UMNUMMERIEREN: ROT,
        }
        zeilen = []
        for nummer, eintrag, art, satz in self.ruestzeilen():
            werkzeug = html.escape(dezimal(bs.text(eintrag)), quote=False)
            zeilen.append(
                f"T{nummer}&nbsp;&nbsp;{werkzeug} – "
                f'<span style="color: {farben[art]};">{html.escape(satz, quote=False)}</span>'
            )
        mit = magazin is not None and bool(self.eintraege)
        self.ruest_titel.setText(
            tr("bs.ruestliste", magazin=magazin.name or tr("mg.ohne_name")) if mit else ""
        )
        self.ruest_titel.setVisible(mit)
        self.ruestliste.setText("<br>".join(zeilen))
        self.ruestliste.setVisible(mit)
        self.knopf_nummern.setVisible(mit)
        if mit:
            ziel = bs.nummern_nach_magazin(self.eintraege, magazin, self._nummern())
            self.knopf_nummern.setEnabled(any(e.nummern != [ziel[id(e)]] for e in self.eintraege))
        self.ohne_magazin.setText(
            tr("bs.ohne_magazin") if magazin is None and self.eintraege else ""
        )
        self.ohne_magazin.setVisible(bool(self.ohne_magazin.text()))

    def nummern_aus_magazin(self):
        """„Nummern aus dem Magazin“ (E4): der Job nummeriert wie das Magazin
        (bestueckung.nummern_aus_magazin) – ein Schritt Rückgängig. Gibt die geänderten
        Controller zurück."""
        magazin = self.magazin()
        if magazin is None:
            return []
        dokument = self.job.Document
        dokument.openTransaction(tr("bs.nummern_aus_magazin"))
        try:
            geaendert = bs.nummern_aus_magazin(self.job, self.bibliothek, magazin, self._nummern())
        except Exception:
            dokument.abortTransaction()
            raise
        dokument.commitTransaction()
        dokument.recompute()
        self.fuellen()
        return geaendert

    def _gewaehlt(self, platz, wahl, index):
        """Das gewählte Werkzeug zieht auf `platz` um – ein Schritt Rückgängig."""
        nummer = wahl.itemData(index)
        if nummer is None or not 0 <= nummer < len(self.eintraege):
            self.fuellen()  # „– frei –“ auf einem belegten Platz: bleibt, wie es war
            return
        self.lege_um(self.eintraege[nummer], platz.Platz)

    def lege_um(self, eintrag, nummer):
        """Legt das Werkzeug `eintrag` auf den Platz `nummer` (bestueckung.lege_um)."""
        if eintrag.nummern == [nummer]:
            return
        dokument = self.job.Document
        dokument.openTransaction(tr("bs.schritt"))
        try:
            bs.lege_um(self.job, eintrag, nummer, self.bibliothek)
        except Exception:
            dokument.abortTransaction()
            raise
        dokument.commitTransaction()
        dokument.recompute()
        self.fuellen()

    # --- 3D-Ansicht -----------------------------------------------------------------

    def _bild_neu(self, auf):
        self._bild_weg()
        ansicht = gui_abfahren.ansicht_von(self.assembly.Document)
        if ansicht is None or not self.plaetze:
            return
        self.bild = Revolverbild(ansicht, self.plaetze, auf, self.bibliothek, self.magazin())

    def _bild_weg(self):
        if self.bild is not None:
            self.bild.weg()
            self.bild = None

    def hinsehen(self):
        if self.bild is not None:
            self.bild.hinsehen()

    def _maschine_merken(self):
        """Merkt die Maschinendatei am Job (D-20) – ein Schritt Rückgängig, wenn es eine
        andere ist als bisher."""
        job = self.job
        pfad = self.assembly.Document.FileName
        if not pfad or job is None or job.Document.Name not in FreeCAD.listDocuments():
            return
        if getattr(job, rw.EIGENSCHAFT_MASCHINE, "") == pfad:
            rw.merke_maschine(job, pfad)  # nur noch „zuletzt benutzt“
            return
        job.Document.openTransaction(tr("rw.maschine.schritt"))
        rw.merke_maschine(job, pfad)
        job.Document.commitTransaction()


def _bibliothek():
    """Die Werkzeugverwaltung – oder None, wenn sie sich nicht lesen lässt: Dann heißen die
    Werkzeuge wie in CAM, und ihre Halter fehlen im Bild."""
    try:
        return wz.Bibliothek.laden()
    except (wz.BeschaedigteDatei, OSError):
        return None


def _satz(farbe):
    """Ein Satz in `farbe` (QColor oder „#rrggbb“), erst verborgen."""
    satz = QtGui.QLabel()
    satz.setWordWrap(True)
    satz.setStyleSheet(f"color: {farbe.name() if hasattr(farbe, 'name') else farbe};")
    satz.hide()
    return satz
