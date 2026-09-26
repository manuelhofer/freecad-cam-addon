# SPDX-License-Identifier: LGPL-2.1-or-later
"""Befehl und Aufgabenfenster „Auf der Maschine prüfen“ (W-001, Stufe 4a).

Oben der Job, die Maschine, die Werkstückaufnahme und der Nullpunkt des Jobs;
darunter das Ergebnis: „Alle Achsen bleiben in ihren Grenzen.“ oder je
Überschreitung ein Satz. Ein Klick auf einen Satz fährt die Maschine dorthin –
die Achse am Anschlag. Darunter grau, was die Bahn je Achse braucht, und die
Hinweise. Gerechnet wird in reichweite.py, beim Öffnen und nach jeder
Änderung.

Zwischen Ergebnis und grauen Zeilen der Bereich „Abfahren“ (Stufe 4b,
gui_abfahren.py): Die Maschine fährt die Bahn ab, mit Werkzeug, Rohteil und
Bahn in der 3D-Ansicht. Ein Klick auf eine Überschreitung stellt auch den
Abspieler dorthin.

Das Fenster öffnet sich im Dokument der Maschine, damit man sie fahren sieht:
Im Wochen-Build gehört ein Aufgabenfenster zu dem Dokument, in dem es aufging,
und verschwindet beim Wechsel (ausprobiert, P-2026-09-26-85). Deshalb wählt der
Befehl die Maschine vorher – bei mehreren fragt er einmal. Schließen fährt die
Maschine zurück, merkt sich den Nullpunkt am Job und kehrt zum Dokument des
Jobs zurück.
"""

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import abfahren as ab
from . import einheiten, gui_abfahren, symbol
from . import job_schnittwerte as js
from . import maschine as m
from . import reichweite as rw
from . import werkzeuge as wz
from .gui_hilfe import kopfzeile
from .gui_teile import GRAU, ROT, mit_einheit, ruhiges_mausrad
from .gui_zahlen import Zahlenpruefer, groesse_lesen, zahlenformat
from .sprache import tr

VERZOEGERUNG = 300  # ms nach der letzten Eingabe, dann rechnet das Fenster neu
GRUEN = "#2e7d32"
ACHSEN = ("X", "Y", "Z")


class BefehlAufMaschinePruefen:
    """Befehl in der Werkzeugleiste: prüft die Bahnen eines Jobs auf einer Maschine."""

    def GetResources(self):
        return {
            "Pixmap": symbol("reichweite.svg"),
            "MenuText": tr("befehl.reichweite.titel"),
            "ToolTip": tr("befehl.reichweite.tooltip"),
        }

    def IsActive(self):
        return not FreeCADGui.Control.activeDialog()

    def Activated(self):
        hauptfenster = FreeCADGui.getMainWindow()
        jobs = js.jobs(FreeCAD.ActiveDocument)
        if not jobs:
            QtGui.QMessageBox.information(hauptfenster, tr("rw.titel"), tr("rw.kein_job"))
            return
        job = gewaehlter_job(jobs) or jobs[0]
        maschinen = offene_maschinen(job.Document)
        if not maschinen:
            QtGui.QMessageBox.information(hauptfenster, tr("rw.titel"), tr("rw.keine_maschine"))
            return
        gewaehlt = maschinen[0] if len(maschinen) == 1 else waehle_maschine(maschinen)
        if gewaehlt is None:
            return
        assembly, maschine = gewaehlt
        zeige_dokument(assembly.Document)
        FreeCADGui.Control.showDialog(PruefPanel(jobs, job, assembly, maschine))


def offene_maschinen(zuerst=None):
    """[(Assembly, Maschinenobjekt)] aus allen offenen Dokumenten – die im Dokument
    `zuerst` vorn."""
    ergebnis = []
    for dokument in FreeCAD.listDocuments().values():
        for objekt in dokument.Objects:
            if objekt.TypeId == "Assembly::AssemblyObject":
                maschine = m.finde_maschine(objekt)
                if maschine is not None:
                    ergebnis.append((objekt, maschine))
    return sorted(ergebnis, key=lambda e: e[0].Document is not zuerst)


def gewaehlter_job(jobs):
    """Der gewählte Job – auch über eine gewählte Operation oder ihren Controller – oder None."""
    for objekt in FreeCADGui.Selection.getSelection():
        for job in jobs:
            if objekt is job or job in objekt.InListRecursive:
                return job
    return None


def maschinen_text(assembly, maschine):
    """„3-Achs-Fräse (Beispielmaschine)“ – die Maschine und ihr Dokument."""
    return tr("rw.maschine.eintrag", maschine=maschine.Label, dokument=assembly.Document.Label)


def waehle_maschine(maschinen):
    """Fragt, auf welcher der offenen Maschinen geprüft wird; (Assembly, Maschine) oder None."""
    texte = [maschinen_text(*eintrag) for eintrag in maschinen]
    text, ok = QtGui.QInputDialog.getItem(
        FreeCADGui.getMainWindow(), tr("rw.titel"), tr("rw.maschine.frage"), texte, 0, False
    )
    return maschinen[texte.index(text)] if ok and text in texte else None


def zeige_dokument(dokument):
    """Holt die 3D-Ansicht des Dokuments nach vorn."""
    if dokument is FreeCAD.ActiveDocument:
        return
    gui_dokument = FreeCADGui.getDocument(dokument.Name)
    ansichten = gui_dokument.mdiViewsOfType("Gui::View3DInventor") if gui_dokument else []
    if ansichten:
        FreeCADGui.getMainWindow().setActiveWindow(ansichten[0])


def _bibliothek():
    """Die Werkzeugverwaltung für die Werkzeuglängen – oder None, wenn sie sich nicht lesen
    lässt (dann gilt die Länge der CAM-Werkzeuge, und die Hinweise sagen es)."""
    try:
        return wz.Bibliothek.laden()
    except (wz.BeschaedigteDatei, OSError):
        return None


class PruefPanel:
    """Das Aufgabenfenster. FreeCAD ruft `getStandardButtons`, `accept` und `reject` auf."""

    offen = None  # das gerade offene Fenster – für die Oberflächen-Szenarien

    def __init__(self, jobs, job, assembly, maschine):
        PruefPanel.offen = self
        self.jobs = jobs
        self.assembly = assembly
        self.maschine = maschine
        self.zurueck_zu = job.Document if job.Document is not assembly.Document else None
        self.pruefung = None  # reichweite.Pruefung für die gewählte Werkstückaufnahme
        self.ergebnis = None
        self.abfahrt = None  # abfahren.Abfahrt zum Ergebnis
        self.bild = None  # gui_abfahren.Bild: Werkzeug und Werkstück in der 3D-Ansicht
        self._bild_fuer = None  # (Job, Prüfung), für die das Bild gebaut ist
        self._bewegt = False  # hat das Fenster die Maschine verfahren?
        self._job = None  # der Job, dessen Nullpunkt in den Feldern steht
        self.bibliothek = _bibliothek()
        self.werkstueckaufnahmen = [
            a for a in m.aufnahmen(maschine) if a.Art == m.AUFNAHME_WERKSTUECK and a.Lcs is not None
        ]
        self._uhr = QtCore.QTimer()
        self._uhr.setSingleShot(True)
        self._uhr.setInterval(VERZOEGERUNG)
        self._uhr.timeout.connect(self.pruefe)
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
        PruefPanel.offen = None
        self._uhr.stop()
        self.abspieler.anhalten()
        self._zurueckfahren()
        self._bild_weg()
        self._nullpunkt_merken()
        FreeCADGui.Control.closeDialog()
        if self.zurueck_zu is not None and self.zurueck_zu.Name in FreeCAD.listDocuments():
            zeige_dokument(self.zurueck_zu)
        return True

    # --- Aufbau ---------------------------------------------------------------------

    def _baue(self):
        form = QtGui.QWidget()
        form.setWindowTitle(tr("rw.titel"))
        form.setWindowIcon(QtGui.QIcon(symbol("reichweite.svg")))
        aufbau = QtGui.QVBoxLayout(form)
        aufbau.addWidget(kopfzeile(tr("rw.titel"), "reichweite"))
        erklaerung = QtGui.QLabel(tr("rw.erklaerung"))
        erklaerung.setWordWrap(True)
        aufbau.addWidget(erklaerung)

        raster = QtGui.QGridLayout()
        raster.setColumnStretch(1, 1)
        self.wahl_job = QtGui.QComboBox()
        for job in self.jobs:
            self.wahl_job.addItem(job.Label)
        self.wahl_job.currentIndexChanged.connect(lambda _i: self._job_gewechselt())
        raster.addWidget(QtGui.QLabel(tr("rw.job")), 0, 0)
        raster.addWidget(self.wahl_job, 0, 1)
        maschine = QtGui.QLabel(maschinen_text(self.assembly, self.maschine))
        maschine.setWordWrap(True)
        maschine.setToolTip(tr("rw.maschine.tooltip"))
        raster.addWidget(QtGui.QLabel(tr("rw.maschine")), 1, 0)
        raster.addWidget(maschine, 1, 1)
        self.wahl_aufnahme = QtGui.QComboBox()
        for aufnahme in self.werkstueckaufnahmen:
            self.wahl_aufnahme.addItem(m.name_von(aufnahme))
        self.wahl_aufnahme.currentIndexChanged.connect(lambda _i: self.pruefe())
        beschriftung = QtGui.QLabel(tr("rw.werkstueckaufnahme"))
        raster.addWidget(beschriftung, 2, 0)
        raster.addWidget(self.wahl_aufnahme, 2, 1)
        # Nur zu wählen, wenn es mehr als eine gibt.
        for widget in (beschriftung, self.wahl_aufnahme):
            widget.setVisible(len(self.werkstueckaufnahmen) > 1)
        aufbau.addLayout(raster)

        nullpunkt = QtGui.QLabel(tr("rw.nullpunkt"))
        nullpunkt.setWordWrap(True)
        nullpunkt.setToolTip(tr("rw.nullpunkt.tooltip"))
        aufbau.addWidget(nullpunkt)
        zeile = QtGui.QHBoxLayout()
        self.felder_nullpunkt = {}
        for achse in ACHSEN:
            feld = QtGui.QLineEdit()
            feld.setValidator(Zahlenpruefer(feld, mit_minus=True))
            feld.setToolTip(tr("rw.nullpunkt.tooltip"))
            feld.textChanged.connect(lambda _text: self._uhr.start())
            zeile.addWidget(QtGui.QLabel(achse))
            zeile.addWidget(mit_einheit(feld, einheiten.einheit(einheiten.LAENGE)), 1)
            self.felder_nullpunkt[achse] = feld
        aufbau.addLayout(zeile)

        self.urteil = QtGui.QLabel()
        self.urteil.setWordWrap(True)
        aufbau.addWidget(self.urteil)
        self.liste = QtGui.QListWidget()
        self.liste.setWordWrap(True)
        # So hoch wie ihre Sätze, nicht höher – sonst schöbe sie die Bereiche und
        # Hinweise aus dem Aufgabenbereich.
        self.liste.setSizeAdjustPolicy(QtGui.QAbstractScrollArea.AdjustToContents)
        self.liste.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Maximum)
        self.liste.setToolTip(tr("rw.liste.tooltip"))
        self.liste.itemClicked.connect(lambda _eintrag: self.fahre_hin(self.liste.currentRow()))
        aufbau.addWidget(self.liste)
        self.abspieler = gui_abfahren.Abspieler(self._fahre)
        aufbau.addWidget(self.abspieler)
        self.bereiche = QtGui.QLabel()
        self.bereiche.setWordWrap(True)
        self.bereiche.setStyleSheet(f"color: {GRAU.name()};")
        self.bereiche.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        aufbau.addWidget(self.bereiche)
        self.hinweise = QtGui.QLabel()
        self.hinweise.setWordWrap(True)
        self.hinweise.setStyleSheet(f"color: {GRAU.name()};")
        self.hinweise.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        aufbau.addWidget(self.hinweise)
        aufbau.addStretch()
        return ruhiges_mausrad(form)

    # --- Job und Nullpunkt ----------------------------------------------------------

    def job(self):
        return self.jobs[self.wahl_job.currentIndex()]

    def werkstueckaufnahme(self):
        if not self.werkstueckaufnahmen:
            return None
        return self.werkstueckaufnahmen[max(self.wahl_aufnahme.currentIndex(), 0)]

    def _job_gewechselt(self):
        """Merkt den Nullpunkt des bisherigen Jobs, zeigt den des neuen und rechnet."""
        self._zurueckfahren()
        self._nullpunkt_merken()
        self._job = self.job()
        eingetragen = rw.eingetragener_nullpunkt(self._job)
        vorschlag = rw.vorschlag_nullpunkt(self._job)
        stellen = einheiten.stellen(einheiten.LAENGE, 3)
        for achse, feld in self.felder_nullpunkt.items():
            feld.blockSignals(True)
            feld.setText(_zahl(eingetragen[achse], stellen) if achse in eingetragen else "")
            feld.blockSignals(False)
            feld.setPlaceholderText(_zahl(getattr(vorschlag, achse.lower()), stellen))
        self.pruefe()

    def eingetragen(self):
        """Die eingetragenen Werte in mm: {"X": …} – leere Felder fehlen."""
        return {
            achse: groesse_lesen(feld.text(), einheiten.LAENGE)
            for achse, feld in self.felder_nullpunkt.items()
            if feld.text().strip()
        }

    def nullpunkt(self):
        """Der Nullpunkt, mit dem gerechnet wird: eingetragen, sonst der Vorschlag."""
        vorschlag = rw.vorschlag_nullpunkt(self.job())
        werte = self.eingetragen()
        return FreeCAD.Vector(
            *(werte.get(achse, getattr(vorschlag, achse.lower())) for achse in ACHSEN)
        )

    def _nullpunkt_merken(self):
        """Schreibt die Felder an den Job, dessen Nullpunkt sie zeigen – wenn sich etwas
        geändert hat; ein Schritt Rückgängig im Dokument des Jobs."""
        job = self._job
        if job is None or job.Document.Name not in FreeCAD.listDocuments():
            return
        werte = self.eingetragen()
        if werte == rw.eingetragener_nullpunkt(job):
            return
        job.Document.openTransaction(tr("rw.nullpunkt.schritt"))
        rw.setze_nullpunkt(job, werte)
        job.Document.commitTransaction()

    # --- Rechnen und zeigen ---------------------------------------------------------

    def pruefe(self):
        """Rechnet mit dem, was eingestellt ist, und zeigt das Ergebnis."""
        self._uhr.stop()
        aufnahme = self.werkstueckaufnahme()
        if self.pruefung is None or self.pruefung.werkstueckaufnahme is not aufnahme:
            self._zurueckfahren()
            self.pruefung = rw.Pruefung(self.assembly, self.maschine, aufnahme)
        job, nullpunkt = self.job(), self.nullpunkt()
        self.ergebnis = self.pruefung.pruefe_job(job, nullpunkt, self.bibliothek)
        self._zeige()
        self._abfahrt_rechnen(job, nullpunkt)

    def _abfahrt_rechnen(self, job, nullpunkt):
        """Die Stationen fürs Abfahren und die Körper in der 3D-Ansicht. Steht die Maschine
        schon auf der Bahn, fährt sie an dieselbe Zeit – passend zum neuen Nullpunkt."""
        zeit = self.abspieler.zeit if self._bewegt else None
        self.abfahrt = ab.abfahrt(self.pruefung, job, nullpunkt, self.bibliothek)
        fuer = self._bild_fuer
        if fuer is None or fuer[0] is not job or fuer[1] is not self.pruefung:
            self._bild_weg()
            ansicht = gui_abfahren.ansicht_von(self.assembly.Document)
            if ansicht is not None and self.pruefung.werkstueckaufnahme is not None:
                self.bild = gui_abfahren.Bild(
                    ansicht, self.abfahrt, job, nullpunkt, self.bibliothek
                )
                self._bild_fuer = (job, self.pruefung)
        elif self.bild is not None:
            self.bild.nullpunkt = FreeCAD.Vector(nullpunkt)
            self.bild.folge()
        self.abspieler.zeige(self.abfahrt, zeit)

    def _bild_weg(self):
        if self.bild is not None:
            self.bild.weg()
        self.bild = None
        self._bild_fuer = None

    def _zeige(self):
        e = self.ergebnis
        self.liste.clear()
        for ueberschreitung in e.ueberschreitungen:
            self.liste.addItem(ueberschreitung.text())
        self.liste.setVisible(bool(e.ueberschreitungen))
        if e.ueberschreitungen:
            self._urteil(tr("rw.nicht_in_grenzen"), ROT)
        elif e.punkte:
            self._urteil(tr("rw.in_grenzen"), GRUEN)
        else:
            self._urteil(tr("rw.keine_punkte"), GRAU.name())
        zeilen = [b.text() for b in e.bereiche]
        if zeilen:
            zeilen.insert(0, tr("rw.bereiche", anzahl=e.punkte))
        self.bereiche.setText("\n".join(zeilen))
        self.bereiche.setVisible(bool(zeilen))
        self.hinweise.setText("\n".join(e.hinweise))
        self.hinweise.setVisible(bool(e.hinweise))

    def _urteil(self, text, farbe):
        self.urteil.setText(text)
        self.urteil.setStyleSheet(f"color: {farbe}; font-weight: bold;")

    # --- Die Maschine ---------------------------------------------------------------

    def fahre_hin(self, nummer):
        """Fährt die Maschine an die Stelle der Überschreitung Nummer `nummer` – so weit
        die Achsen kommen, die überschreitende steht an ihrer Grenze. Der Abspieler steht
        danach dort."""
        if self.ergebnis is None or not 0 <= nummer < len(self.ergebnis.ueberschreitungen):
            return
        ueberschreitung = self.ergebnis.ueberschreitungen[nummer]
        station = self.abfahrt.station_von(ueberschreitung) if self.abfahrt else None
        if station is not None:
            self.abspieler.springe_zu_station(station)
        else:
            self.abspieler.anhalten()
            self._fahre(ueberschreitung.stellungen, None)
        zeige_dokument(self.assembly.Document)

    def _fahre(self, stellungen, operation):
        """Fährt die Achsen auf `stellungen` ({Achse: Stellung}) und zeigt das Werkzeug
        der Operation `operation` (Index in der Abfahrt; None: wie bisher). Gibt die
        Achsen zurück, die an einer Grenze halten."""
        if not self._bewegt:
            # Ein Schritt für alles Verfahren; Schließen verwirft ihn.
            self.assembly.Document.openTransaction(tr("rw.titel"))
            self._bewegt = True
        angehalten = self.pruefung.verfahren.setze_alle(stellungen)
        if self.bild is not None:
            if operation is not None:
                self.bild.zeige_operation(operation)
            self.bild.folge()
        return angehalten

    def _zurueckfahren(self):
        """Die Maschine wieder so, wie sie beim Öffnen stand."""
        if not self._bewegt:
            return
        self._bewegt = False
        self.abspieler.anhalten()
        self.pruefung.verfahren.grundstellung()
        self.assembly.Document.abortTransaction()
        self.assembly.Document.recompute()
        if self.bild is not None:
            self.bild.folge()


def _zahl(wert, stellen):
    """Zahl für ein Feld, ohne Nullen am Ende: „−50“, „12,5“ – auch 0 als „0“."""
    text = zahlenformat().toString(float(einheiten.anzeige(wert, einheiten.LAENGE)), "f", stellen)
    zeichen = zahlenformat().decimalPoint()
    if zeichen in text:
        text = text.rstrip("0").rstrip(zeichen)
    return "0" if text in ("-0", "") else text
