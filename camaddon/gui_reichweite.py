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

import contextlib
import functools
import html
import os
import time

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import abfahren as ab
from . import (
    beispielmaschine,
    einheiten,
    farben,
    gui_abfahren,
    gui_kollision,
    gui_neue_maschine,
    gui_werkzeuge,
    spannung,
    symbol,
    uhren,
)
from . import job_schnittwerte as js
from . import magazin as mg
from . import maschine as m
from . import reichweite as rw
from . import werkzeuge as wz
from .gui_hilfe import kopfzeile
from .gui_job_schnittwerte import dokument_mit_job
from .gui_teile import GRAU, ROT, blaettere_zu, mit_einheit, ruhiges_mausrad
from .gui_zahlen import Zahlenpruefer, groesse_fest, groesse_lesen, zahlenformat
from .sprache import tr

VERZOEGERUNG = 300  # ms nach der letzten Eingabe, dann rechnet das Fenster neu
GRUEN = farben.GRUEN
ACHSEN = ("X", "Y", "Z")


def balken_stellen(von, bis, minimum, maximum):
    """(Anfang, Ende der Grenzen; Anfang, Ende des Gebrauchten; reicht es?) als Anteile 0…1 der
    Balkenbreite: Der Balken zeigt die Grenzen und, wo die Bahn darüber hinaus will, auch das. Ohne
    endliche Grenzen (eine endlos drehende Achse) füllen die Grenzen den Balken, das Gebrauchte
    steht in seiner Mitte."""
    import math

    von, bis = min(von, bis), max(von, bis)
    endlich = (
        minimum is not None
        and maximum is not None
        and math.isfinite(minimum)
        and math.isfinite(maximum)
        and maximum > minimum
    )
    if not endlich:
        return 0.0, 1.0, 0.4, 0.6, True
    links, rechts = min(minimum, von), max(maximum, bis)
    spanne = rechts - links
    anteil = lambda wert: (wert - links) / spanne  # noqa: E731
    reicht = von >= minimum - 1e-6 and bis <= maximum + 1e-6
    return anteil(minimum), anteil(maximum), anteil(von), anteil(bis), reicht


class Zeitanteile(QtGui.QWidget):
    """Die Zeit des Jobs als ein Balken: je Operation ein Stück in ihrer Farbe, so breit wie ihr
    Anteil – wer die Zeit frisst, sieht man, statt es aus einer Kette von Namen und Zahlen zu
    lesen (Zeigen statt sagen; bis 0.364 „… · „Räumen T1“ 9,8 min · „Räumen T3“ 22 s · …“ über drei
    Zeilen). Im Stück steht, was hineinpasst (Name und Zeit, sonst die Zeit); unter der Maus beides.
    Ein Klick springt im Abspieler an den Anfang der Operation."""

    geklickt = QtCore.Signal(int)
    HOEHE = 18
    LUECKE = 1  # Pixel zwischen zwei Stücken

    def __init__(self):
        super().__init__()
        self._teile = []  # [(Name, Sekunden)]
        self.setFixedHeight(self.HOEHE)
        self.setMouseTracking(True)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.hide()

    def setzen(self, teile):
        """`teile`: [(Name, Sekunden)] je Operation in ihrer Reihenfolge – mit nur einer bleibt
        der Balken weg (die Zahl daneben sagt schon alles)."""
        self._teile = [(name, max(float(s), 0.0)) for name, s in teile]
        self.setVisible(len(self._teile) > 1 and sum(s for _n, s in self._teile) > 0)
        self.update()

    def texte(self):
        """[„Räumen T1 9,8 min“, …] – was unter der Maus steht, je Operation."""
        return [f"{name} {ab.dauer_text(s)}" for name, s in self._teile]

    def _grenzen(self):
        """[(links, rechts)] der Stücke in Pixeln."""
        gesamt = sum(s for _n, s in self._teile)
        breite = self.width()
        grenzen, bisher = [], 0.0
        for _name, s in self._teile:
            links = int(round(breite * bisher / gesamt)) if gesamt > 0 else 0
            bisher += s
            rechts = int(round(breite * bisher / gesamt)) if gesamt > 0 else 0
            grenzen.append((links, max(rechts, links + 2)))
        return grenzen

    def nummer_bei(self, x):
        """Die Operation unter der Stelle `x` (Pixel) – −1 daneben."""
        for nummer, (links, rechts) in enumerate(self._grenzen()):
            if links <= x < rechts:
                return nummer
        return -1

    def mouseMoveEvent(self, ereignis):  # noqa: N802 – Qt-Name
        nummer = self.nummer_bei(ereignis.pos().x())
        self.setToolTip(self.texte()[nummer] if nummer >= 0 else "")

    def mousePressEvent(self, ereignis):  # noqa: N802 – Qt-Name
        nummer = self.nummer_bei(ereignis.pos().x())
        if nummer >= 0:
            self.geklickt.emit(nummer)

    def paintEvent(self, _ereignis):  # noqa: N802 – Qt-Name
        if not self._teile:
            return
        from . import gui_bahnvorschau as gv

        maler = QtGui.QPainter(self)
        maler.setRenderHint(QtGui.QPainter.Antialiasing)
        masse = maler.fontMetrics()
        for nummer, ((links, rechts), (name, s)) in enumerate(
            zip(self._grenzen(), self._teile, strict=True)
        ):
            farbe = QtGui.QColor(gv.farbe_hex(nummer))
            breite = max(rechts - links - self.LUECKE, 1)
            maler.setPen(QtCore.Qt.NoPen)
            maler.setBrush(farbe)
            maler.drawRoundedRect(links, 0, breite, self.height(), 3, 3)
            zeit = ab.dauer_text(s)
            text = next(
                (t for t in (f"{name} {zeit}", zeit) if masse.horizontalAdvance(t) + 8 <= breite),
                "",
            )
            if text:
                hell = 0.299 * farbe.redF() + 0.587 * farbe.greenF() + 0.114 * farbe.blueF()
                maler.setPen(QtGui.QColor("#000000" if hell > 0.55 else "#ffffff"))
                maler.drawText(
                    QtCore.QRect(links, 0, breite, self.height()), QtCore.Qt.AlignCenter, text
                )
        maler.end()


class Achsbalken(QtGui.QWidget):
    """Eine Achse als Balken: grau der Weg zwischen ihren Grenzen, darauf grün, was die Bahn davon
    braucht – rot, wenn es über eine Grenze hinausgeht; dann steht darüber, wie weit („220,00 mm
    zu weit“), und ein Klick fährt die Maschine an die Stelle. Links ihr Name; alle Zahlen stehen
    im Tooltip (Bereich.text)."""

    NAME = 34  # Pixel für den Namen der Achse
    geklickt = QtCore.Signal()

    def __init__(self, bereich):
        super().__init__()
        self.bereich = bereich
        self.zu_weit = self._zu_weit()
        self.setFixedHeight(30 if self.zu_weit > 0 else 16)
        self.setToolTip(bereich.text())
        if self.zu_weit > 0:
            self.setCursor(QtCore.Qt.PointingHandCursor)

    def _zu_weit(self):
        """Um wie viel die Bahn über eine Grenze der Achse hinaus will (mm oder Grad; 0: reicht)."""
        import math

        b = self.bereich
        minimum, maximum = b.achse.minimum, b.achse.maximum
        if minimum is None or maximum is None:
            return 0.0
        if not (math.isfinite(minimum) and math.isfinite(maximum)) or maximum <= minimum:
            return 0.0
        von, bis = min(b.von, b.bis), max(b.von, b.bis)
        ueber = max(minimum - von, bis - maximum, 0.0)
        return ueber if ueber > 1e-6 else 0.0

    def zu_weit_text(self):
        """„220,00 mm zu weit“ – leer, wenn die Achse reicht. Im Durchmesser gezählt (X einer
        Drehmaschine) das Doppelte, wie die Steuerung es zeigt."""
        if self.zu_weit <= 0:
            return ""
        b = self.bereich
        if b.achse.art != rw.LINEAR:
            weg = rw.winkel_text(self.zu_weit)
        else:
            weg = rw.weg_text(self.zu_weit * (2.0 if b.durchmesser else 1.0))
        return tr("rw.zu_weit", weg=weg)

    def mousePressEvent(self, _ereignis):  # noqa: N802 – Qt-Name
        if self.zu_weit > 0:
            self.geklickt.emit()

    def paintEvent(self, _ereignis):  # noqa: N802 – Qt-Name
        from . import verfahren as vf

        b = self.bereich
        g0, g1, v0, v1, reicht = balken_stellen(b.von, b.bis, b.achse.minimum, b.achse.maximum)
        if vf.programm_vorzeichen(b.achse) < 0:  # an der Steuerung andersherum gezählt
            g0, g1, v0, v1 = 1 - g1, 1 - g0, 1 - v1, 1 - v0
        maler = QtGui.QPainter(self)
        maler.setRenderHint(QtGui.QPainter.Antialiasing)
        maler.setPen(self.palette().color(QtGui.QPalette.WindowText))
        unten = 16  # so hoch ist die Zeile mit dem Balken, unten im Feld
        feld = QtCore.QRect(0, self.height() - unten, self.NAME, unten)
        maler.drawText(feld, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, b.name)
        breite = max(10, self.width() - self.NAME - 4)
        stelle = lambda anteil: self.NAME + int(round(breite * anteil))  # noqa: E731
        maler.setPen(QtCore.Qt.NoPen)
        maler.setBrush(QtGui.QColor(GRAU.name()))
        mitte = self.height() - unten // 2
        maler.drawRoundedRect(stelle(g0), mitte - 2, max(4, stelle(g1) - stelle(g0)), 4, 2, 2)
        maler.setBrush(QtGui.QColor(GRUEN if reicht else ROT))
        maler.drawRoundedRect(stelle(v0), mitte - 4, max(5, stelle(v1) - stelle(v0)), 8, 3, 3)
        text = self.zu_weit_text()
        if text:
            # Über dem Stück, das über die Grenze hinausragt – links oder rechts der Grenzen.
            maler.setPen(QtGui.QColor(ROT))
            masse = maler.fontMetrics()
            weit = masse.horizontalAdvance(text)
            # Über dem Ende, das weiter übersteht – sind beide Grenzen überschritten, gehört die
            # Zahl (das Größere, _zu_weit) dorthin, nicht immer nach links.
            links_ueber = (g0 - v0) > (v1 - g1)
            x = stelle(v0) if links_ueber else stelle(v1) - weit
            x = min(max(x, self.NAME), max(self.NAME, self.width() - weit - 2))
            maler.drawText(
                QtCore.QRect(x, 0, weit + 2, self.height() - unten),
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
                text,
            )
        maler.end()


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
        dokument = dokument_mit_job(tr("rw.titel"), tr("rw.kein_job"))
        if dokument is None:
            return
        jobs = js.jobs(dokument)
        job = job_fuer(jobs)
        gewaehlt = maschine_fuer(job, hauptfenster)
        if gewaehlt is None:
            return
        assembly, maschine = gewaehlt
        zeige_dokument(assembly.Document)
        FreeCADGui.Control.showDialog(PruefPanel(jobs, job, assembly, maschine))


def maschine_fuer(job, hauptfenster):
    """Die Maschine, auf der der Job geprüft wird: (Assembly, Maschine) oder None.

    Hat der Job seine Maschine (Schritt 1 des Assistenten, die letzte Prüfung – W-011 S2),
    gilt sie ohne Frage: offen oder aus ihrer Datei geöffnet. Sonst: Ist keine offen, öffnet
    sich die zuletzt benutzte (D-20), und fehlt auch die, fragt eine Meldung. Ist eine offen,
    gilt sie; sind mehrere offen, fragt das Addon, die zuletzt benutzte vorgewählt."""
    eigene = _maschine_des_jobs(job)
    if eigene is not None:
        return eigene
    fehlt = _fehlende_maschine(job)
    if fehlt:
        return _ohne_maschine_des_jobs(job, hauptfenster, fehlt)
    gemerkt = rw.gemerkte_maschine(job)
    maschinen = offene_maschinen(job.Document)
    if not maschinen and gemerkt and os.path.isfile(gemerkt):
        with contextlib.suppress(Exception):  # nicht mehr lesbar – dann fragen wie ohne
            oeffne_datei(gemerkt)
        maschinen = offene_maschinen(job.Document)
    if not maschinen:
        maschinen = maschine_oeffnen(hauptfenster, job)
    if len(maschinen) > 1:
        # Die gemerkte vorn – dann reicht Enter.
        maschinen.sort(key=lambda e: not gleiche_datei(e[0].Document.FileName, gemerkt))
        return waehle_maschine(maschinen)
    return maschinen[0] if maschinen else None


def _fehlende_maschine(job):
    """Die Datei der Maschine, die am Job steht, wenn es sie nicht mehr gibt (gelöscht,
    verschoben) – sonst ""."""
    datei = getattr(job, rw.EIGENSCHAFT_MASCHINE, "")
    return datei if datei and not os.path.isfile(datei) else ""


def _ohne_maschine_des_jobs(job, hauptfenster, fehlt):
    """Die Maschine des Jobs gibt es nicht mehr (Manuel, 2026-10-12: „was passiert, wenn ich sie
    einfach so als Datei lösche … kommt eine Fehlermeldung?“): Das sagt es, statt still auf der
    zuletzt benutzten zu prüfen. Ist eine Maschine offen, gilt sie, und die Meldung nennt sie;
    sind mehrere offen, fragt es; ist keine offen, bietet die Meldung „Maschine öffnen …“ und
    „Neue Maschine …“ an. Der Job merkt sich danach die neue (rw.merke_maschine)."""
    FreeCAD.Console.PrintWarning(tr("rw.maschine_fehlt_konsole", datei=fehlt) + "\n")
    maschinen = offene_maschinen(job.Document)
    if not maschinen:
        maschinen = maschine_oeffnen(hauptfenster, job, fehlt)
    elif len(maschinen) == 1:
        QtGui.QMessageBox.information(
            hauptfenster,
            tr("rw.titel"),
            tr("rw.maschine_fehlt_offene", datei=fehlt, maschine=maschinen_text(*maschinen[0])),
        )
    if len(maschinen) > 1:
        return waehle_maschine(maschinen)
    return maschinen[0] if maschinen else None


def _maschine_des_jobs(job):
    """(Assembly, Maschine) der Maschine, die am Job steht – offen oder aus ihrer Datei
    geöffnet; None, wenn er keine hat, die Datei fehlt oder keine Maschine enthält."""
    datei = getattr(job, rw.EIGENSCHAFT_MASCHINE, "")
    if not datei or not os.path.isfile(datei):
        return None

    def offen():
        return next(
            (e for e in offene_maschinen(job.Document)
             if gleiche_datei(e[0].Document.FileName, datei)),
            None,
        )  # fmt: skip

    gefunden = offen()
    if gefunden is None:
        with contextlib.suppress(Exception):  # nicht mehr lesbar – dann wie ohne
            oeffne_datei(datei)
        gefunden = offen()
    return gefunden


def maschine_oeffnen(hauptfenster, job, fehlt=""):
    """Keine Maschine offen: Die Meldung bietet „Maschine öffnen …“ (eine Datei wählen) und
    „Neue Maschine …“ (bauen, dann gleich auf ihr prüfen) an; `fehlt`: die Datei der Maschine
    des Jobs, die es nicht mehr gibt – die Meldung nennt sie. Gibt die danach offenen
    Maschinen zurück – leer bei Abbrechen oder ohne Maschine in der Datei."""
    meldung = QtGui.QMessageBox(
        QtGui.QMessageBox.Information,
        tr("rw.titel"),
        tr("rw.maschine_fehlt", datei=fehlt) if fehlt else tr("rw.keine_maschine"),
        QtGui.QMessageBox.Cancel,
        hauptfenster,
    )
    oeffnen = meldung.addButton(tr("rw.maschine_oeffnen"), QtGui.QMessageBox.AcceptRole)
    oeffnen.setToolTip(tr("rw.maschine_oeffnen.tooltip"))
    neu = meldung.addButton(tr("befehl.neue_maschine.titel"), QtGui.QMessageBox.ActionRole)
    neu.setToolTip(tr("rw.neue_maschine.tooltip"))
    meldung.setDefaultButton(oeffnen)
    meldung.exec()
    if meldung.clickedButton() is neu:
        gewaehlt = gui_neue_maschine.waehle(tr("neu.titel"))
        if gewaehlt is None:
            return []
        beispielmaschine.lade(*gewaehlt)
        return offene_maschinen(job.Document)
    if meldung.clickedButton() is not oeffnen:
        return []
    ordner = os.path.dirname(rw.gemerkte_maschine(job) or job.Document.FileName)
    pfad = datei_waehlen(hauptfenster, ordner)
    if not pfad:
        return []
    try:
        oeffne_datei(pfad)
    except Exception as fehler:  # keine FreeCAD-Datei, kaputt: sagen statt still scheitern
        QtGui.QMessageBox.warning(
            hauptfenster, tr("rw.titel"), tr("rw.datei_fehler", datei=pfad, fehler=fehler)
        )
        return []
    maschinen = offene_maschinen(job.Document)
    if not maschinen:
        QtGui.QMessageBox.information(
            hauptfenster, tr("rw.titel"), tr("rw.keine_maschine_in_datei", datei=pfad)
        )
    return maschinen


def datei_waehlen(hauptfenster, ordner):
    """Fragt nach der Datei mit der Maschine; "" bei Abbrechen. Die Szenarien ersetzen
    diese Funktion – einen Dateidialog können sie nicht bedienen."""
    pfad, _filter = QtGui.QFileDialog.getOpenFileName(
        hauptfenster, tr("rw.maschine_oeffnen"), ordner, "FreeCAD (*.FCStd)"
    )
    return pfad


def oeffne_datei(pfad):
    """Öffnet die Datei; ist sie schon offen, bleibt es bei diesem Dokument."""
    for dokument in FreeCAD.listDocuments().values():
        if gleiche_datei(dokument.FileName, pfad):
            return dokument
    return FreeCAD.openDocument(pfad)


def gleiche_datei(a, b):
    """Ob zwei Pfade dieselbe Datei meinen – unter Windows auch mit / statt \\ und in
    anderer Großschreibung; leere Pfade nie."""
    if not a or not b:
        return False
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


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


_ZULETZT = {}  # Name des Dokuments → Name des Jobs, an dem zuletzt gearbeitet wurde


def job_merken(job):
    """Merkt den Job, an dem gerade gearbeitet wird (ein Assistent hat angelegt oder geändert,
    ein Fenster zeigt ihn): Ist keiner gewählt, nehmen „Auf der Maschine prüfen“, „Bestückung“ und
    „Programm schreiben“ ihn (job_fuer) – nicht einfach den ersten im Dokument."""
    if job is not None and getattr(job, "Document", None) is not None:
        _ZULETZT[job.Document.Name] = job.Name


def _zuletzt(jobs):
    """Unter `jobs` der, an dem zuletzt gearbeitet wurde – oder None."""
    for job in jobs:
        if _ZULETZT.get(job.Document.Name) == job.Name:
            return job
    return None


def gewaehlter_job(jobs):
    """Der gewählte Job – auch über eine gewählte Operation oder ihren Controller, in jedem
    offenen Dokument – oder None. Ist ein Teil angeklickt, das in mehreren Jobs steckt (zwei
    Aufspannungen), der davon, an dem zuletzt gearbeitet wurde."""
    for objekt in FreeCADGui.Selection.getSelection("*"):
        treffer = [job for job in jobs if objekt is job or job in objekt.InListRecursive]
        if treffer:
            return _zuletzt(treffer) or treffer[0]
    return None


def job_fuer(jobs):
    """Der Job, den ein Fenster zeigt: der gewählte, sonst der, an dem zuletzt gearbeitet wurde,
    sonst der erste."""
    return gewaehlter_job(jobs) or _zuletzt(jobs) or jobs[0]


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
        self._lauf = None  # ein großer Job rechnet im Takt (_lauf_starten); None: keiner
        self._vorrechnen = {}  # Schlüssel -> Auftrag: 5-Achs-Programme auf den Nebenrechnern
        self._vorrechnen_gescheitert = set()  # … die dort nicht gingen: dann hier
        self.bild = None  # gui_abfahren.Bild: Werkzeug und Werkstück in der 3D-Ansicht
        self._bild_fuer = None  # (Job, Prüfung), für die das Bild gebaut ist
        self._bewegt = False  # hat das Fenster die Maschine verfahren?
        # {Name: (Transparency, Visibility)} der Körper der Maschine, bevor die Auswahl „Maschine“
        # im Abspieler sie durchsichtig machte oder ausblendete – beim Schließen zurück.
        self._ansicht_vorher = {}
        self._marke_behalten = False  # die rote Kugel eines Befunds bleibt beim nächsten Fahren
        self._job = None  # der Job, dessen Nullpunkt in den Feldern steht
        self._werkzeugdialog = None  # die Werkzeugverwaltung, deren Speichern hier ankommt
        self.bibliothek = _bibliothek()
        if self.bibliothek is not None:  # die Halter aus dem Magazin dieser Maschine (W-024)
            mg.des_jobs(job, self.bibliothek, assembly)
        self.vergleiche = []  # js.Vergleich je Controller – Schnittwerte im Job (D-28)
        self.werkstueckaufnahmen = [
            a for a in m.aufnahmen(maschine) if a.Art == m.AUFNAHME_WERKSTUECK and a.Lcs is not None
        ]
        self._uhr = QtCore.QTimer()
        self._uhr.setSingleShot(True)
        self._uhr.setInterval(VERZOEGERUNG)
        self._uhr.timeout.connect(uhren.aus_der_schleife(self._uhr, self.pruefe))
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
        self._lauf_beenden()
        self.kollision.abbrechen()
        self.abspieler.anhalten()
        self._zurueckfahren()
        self._bild_weg()
        self._ansicht_zurueck()
        self._nullpunkt_merken()
        self._maschine_merken()
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
        kopf = kopfzeile(tr("rw.titel"), "reichweite")
        # Was das Fenster tut, sagt sein Titel; der Satz dazu ist sein Tooltip (wenig Text im
        # Fenster, Arbeitsregeln Abschnitt 8) – darunter stehen gleich die Urteile.
        kopf.setToolTip(tr("rw.erklaerung"))
        aufbau.addWidget(kopf)

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
        # Dreht der Job um eine Rundachse, die diese Maschine nicht hat (ohne Maschine angelegt):
        # ein Satz und der Knopf zum Umstellen (_achse_zeigen).
        self.achse_anders = QtGui.QWidget()
        zeile_achse = QtGui.QHBoxLayout(self.achse_anders)
        zeile_achse.setContentsMargins(0, 0, 0, 0)
        self.achse_satz = QtGui.QLabel()
        self.achse_satz.setWordWrap(True)
        self.achse_satz.setStyleSheet(f"color: {ROT};")
        self.knopf_achse = QtGui.QPushButton()
        self.knopf_achse.setAutoDefault(False)
        self.knopf_achse.clicked.connect(lambda: self.achse_umstellen())
        zeile_achse.addWidget(self.achse_satz, 1)
        zeile_achse.addWidget(self.knopf_achse)
        self.achse_anders.hide()
        self._achse_neu = None
        aufbau.addWidget(self.achse_anders)

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

        # Oben je Prüfung ein Urteil, ohne Blättern zu sehen (Durchsicht W-004, D-10); die
        # Einzelheiten stehen darunter, die Verweise führen hin.
        urteile = QtGui.QGridLayout()
        urteile.setColumnStretch(1, 1)
        self.urteil = QtGui.QLabel()
        self.urteil_kollision = QtGui.QLabel()
        self.urteil_kollision.linkActivated.connect(self._kollision_verweis)
        self.urteil_laenge = QtGui.QLabel()
        self.urteil_laenge.linkActivated.connect(lambda _ziel: blaettere_zu(self.hinweise))
        self.urteil_schnittwerte = QtGui.QLabel()
        self.urteil_schnittwerte.setToolTip(tr("rw.schnittwerte.tooltip"))
        self.urteil_schnittwerte.linkActivated.connect(self.schnittwerte_uebernehmen)
        # Wie lange der Job rechnerisch dauert (Manuel, 2026-10-03: „ja, die Bearbeitung dauert
        # rechnerisch … min“) – aus dem Abfahren: Vorschub, Eilgang, je Operation.
        self.urteil_zeit = QtGui.QLabel()
        self.urteil_zeit.setToolTip(tr("rw.zeit.tooltip"))
        # Von unten gespannt (S3h): nur, wenn am Job eingetragen.
        self.urteil_spannung = QtGui.QLabel()
        self.urteil_spannung.setToolTip(tr("sn.eigenschaft"))
        self.urteil_spannung.linkActivated.connect(lambda _ziel: blaettere_zu(self.hinweise))
        self._beschriftung = {}
        for zeile, (text, urteil) in enumerate(
            (
                (tr("rw.urteil.achsen"), self.urteil),
                (tr("rw.urteil.kollision"), self.urteil_kollision),
                (tr("rw.urteil.laenge"), self.urteil_laenge),
                (tr("rw.urteil.schnittwerte"), self.urteil_schnittwerte),
                (tr("rw.urteil.spannung"), self.urteil_spannung),
                (tr("rw.urteil.zeit"), self.urteil_zeit),
            )
        ):
            urteil.setWordWrap(True)
            self._beschriftung[urteil] = QtGui.QLabel(text)
            urteile.addWidget(self._beschriftung[urteil], zeile, 0, QtCore.Qt.AlignTop)
            urteile.addWidget(urteil, zeile, 1)
        # Unter der Zeit: wer sie braucht, als Balken (Zeitanteile) – ein Klick springt dorthin.
        self.zeitanteile = Zeitanteile()
        self.zeitanteile.geklickt.connect(self._zur_operation)
        urteile.addWidget(self.zeitanteile, urteile.rowCount(), 1)
        aufbau.addLayout(urteile)
        # Gleich weiter zum Programm dieses Jobs – ohne ihn noch einmal zu wählen.
        self.knopf_programm = QtGui.QPushButton(tr("befehl.programm.titel"))
        self.knopf_programm.setToolTip(tr("rw.programm.tooltip"))
        self.knopf_programm.clicked.connect(self.programm_schreiben)
        # Worin das Rohteil auf dem Tisch steckt (W-042) – nach OK rechnet das Fenster neu.
        self.knopf_spannmittel = QtGui.QPushButton(tr("befehl.spannmittel.titel"))
        self.knopf_spannmittel.setToolTip(tr("rw.spannmittel.tooltip"))
        self.knopf_spannmittel.clicked.connect(self.spannmittel_zeigen)
        knoepfe = QtGui.QHBoxLayout()
        knoepfe.addWidget(self.knopf_programm)
        knoepfe.addWidget(self.knopf_spannmittel)
        knoepfe.addStretch()
        aufbau.addLayout(knoepfe)
        self.liste = QtGui.QListWidget()
        self.liste.setWordWrap(True)
        # So hoch wie ihre Sätze, nicht höher – sonst schöbe sie die Bereiche und
        # Hinweise aus dem Aufgabenbereich.
        self.liste.setSizeAdjustPolicy(QtGui.QAbstractScrollArea.AdjustToContents)
        self.liste.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Maximum)
        self.liste.setToolTip(tr("rw.liste.tooltip"))
        self.liste.itemClicked.connect(lambda _eintrag: self.fahre_hin(self.liste.currentRow()))
        aufbau.addWidget(self.liste)
        self.abspieler = gui_abfahren.Abspieler(self._fahre, self._hinsehen)
        self.abspieler.bei_station = self._abtragen
        self.abspieler.bei_bahn = self._bahn_zeigen
        self.abspieler.bei_teil = self._teil_zeigen
        self.abspieler.bei_maschine = self._maschine_ansicht
        self.abspieler.bei_kollision = self._kollision_hin
        self.abspieler.bei_fertigteil = self._fertigteil
        aufbau.addWidget(self.abspieler)
        self.kollision = gui_kollision.KollisionsBereich(
            self._kollision_daten,
            self._kollision_hin,
            self._sperren,
            self._kollision_gemeldet,
            self._werkzeug_ausspannen,
        )
        aufbau.addWidget(self.kollision)
        self.bereiche = QtGui.QLabel()
        self.bereiche.setWordWrap(True)
        self.bereiche.setStyleSheet(f"color: {GRAU.name()};")
        self.bereiche.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        aufbau.addWidget(self.bereiche)
        # Gezeigt statt aufgezählt (Manuel, 2026-11-11: zu viel Text): je Achse ein Balken – grau
        # ihre Grenzen, grün, was die Bahn braucht (rot, wo es nicht reicht). Der Satz mit den
        # Zahlen ist der Tooltip des Balkens; das Etikett darüber behält ihn zum Kopieren, bleibt
        # aber verborgen.
        self.bereiche.hide()
        self.bereiche_titel = QtGui.QLabel()
        self.bereiche_titel.setStyleSheet(f"color: {GRAU.name()};")
        self.bereiche_titel.hide()
        # Gleich unter den Urteilen und dem Satz zur Überschreitung – „wo, steht darunter“.
        stelle = aufbau.indexOf(self.liste) + 1
        aufbau.insertWidget(stelle, self.bereiche_titel)
        self.bereiche_bild = QtGui.QWidget()
        bild = QtGui.QVBoxLayout(self.bereiche_bild)
        bild.setContentsMargins(0, 0, 0, 0)
        bild.setSpacing(2)
        aufbau.insertWidget(stelle + 1, self.bereiche_bild)
        self.hinweise = gui_kollision.hinweis_label()
        aufbau.addWidget(self.hinweise)
        for hinweise in (self.hinweise, self.kollision.hinweise):
            hinweise.linkActivated.connect(self._werkzeug_oeffnen)
        aufbau.addStretch()
        return ruhiges_mausrad(form)

    # --- Job und Nullpunkt ----------------------------------------------------------

    def programm_schreiben(self):
        """„Programm schreiben …“ für den Job dieses Fensters; dieses bleibt offen. Gibt das
        Fenster zurück."""
        from .gui_programm import ProgrammDialog

        dialog = ProgrammDialog(self.jobs, self.job())
        dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        dialog.show()
        return dialog

    def spannmittel_zeigen(self):
        """„Spannmittel …“ auf der Seite „Aufspannung im Job“ für den Job dieses Fensters; nach
        OK zeigt es den neuen Nullpunkt und prüft neu. Gibt das Fenster zurück."""
        from . import gui_spannmittel

        dialog = gui_spannmittel.oeffne(rw.grundjob_von(self.job()))
        dialog.accepted.connect(self._nach_spannmittel)
        return dialog

    def _nach_spannmittel(self):
        if PruefPanel.offen is not self:
            return
        if not rw.eingetragener_nullpunkt(self.job()):  # das Spannmittel sagt jetzt, wo es liegt
            for feld in self.felder_nullpunkt.values():
                feld.blockSignals(True)
                feld.clear()
                feld.blockSignals(False)
        self._job_gewechselt()

    def job(self):
        return self.jobs[self.wahl_job.currentIndex()]

    def werkstueckaufnahme(self):
        if not self.werkstueckaufnahmen:
            return None
        return self.werkstueckaufnahmen[max(self.wahl_aufnahme.currentIndex(), 0)]

    def _achse_zeigen(self):
        """Dreht der gewählte Job (ein 4-Achs-Job des Assistenten) um eine Rundachse, die diese
        Maschine nicht hat, aber eine, die positionieren kann: der Satz und der Knopf, ihn auf
        sie umzustellen (Manuel, 2026-10-12: ohne Maschine angelegt – A längs X –, dann die
        CLX550 mit C; die Stange lag quer auf dem Tisch, beide Operationen ausgelassen)."""
        from . import vierachs_achsen as va
        from . import vierachs_operation as vo
        from . import vierachs_rohteil as vr

        self._achse_neu = None
        job = self.job()
        buchstaben = {
            getattr(op, "Rundachse", "")
            for op in js.operationen(job)
            if vo.ist_rundum(op) and getattr(op, "Rundachse", "")
        }
        if len(buchstaben) != 1:
            self.achse_anders.hide()
            return
        (buchstabe,) = buchstaben
        try:
            achsen = va.von_maschine(self.assembly, self.maschine)
        except Exception:  # noqa: BLE001 – ohne lesbare Achse kein Vorschlag
            achsen = []
        if not achsen or any(a.buchstabe == buchstabe for a in achsen):
            self.achse_anders.hide()
            return
        if vr.einstellung(job) is None:
            self.achse_anders.hide()
            return
        self._achse_neu = achsen[0]
        self.achse_satz.setText(
            tr("rw.achse.anders", job=buchstabe, maschine=self._achse_neu.buchstabe)
        )
        self.knopf_achse.setText(tr("rw.achse.umstellen", maschine=self._achse_neu.buchstabe))
        self.knopf_achse.setToolTip(tr("rw.achse.umstellen.tooltip"))
        self.achse_anders.show()

    def achse_umstellen(self):
        """Stellt den Job auf die Rundachse dieser Maschine um (vierachs_rohteil.
        auf_achse_umstellen) – ein Schritt Rückgängig – und prüft neu."""
        from . import vierachs_rohteil as vr

        achse, job = self._achse_neu, self.job()
        if achse is None:
            return
        dokument = job.Document
        self._zurueckfahren()
        dokument.openTransaction(tr("rw.achse.umstellen", maschine=achse.buchstabe))
        try:
            with uhren.still():
                vr.auf_achse_umstellen(job, achse)
        except ValueError as grund:
            dokument.abortTransaction()
            QtGui.QMessageBox.warning(self.form, tr("rw.titel"), str(grund))
            return
        dokument.commitTransaction()
        self.pruefung = None
        self._achse_zeigen()
        self.pruefe()

    def _job_gewechselt(self):
        """Merkt Nullpunkt und Maschine des bisherigen Jobs, zeigt den Nullpunkt des neuen
        und rechnet."""
        self._zurueckfahren()
        self._nullpunkt_merken()
        self._maschine_merken()
        self._job = self.job()
        job_merken(self._job)
        eingetragen = rw.eingetragener_nullpunkt(self._job)
        aufnahme = self.werkstueckaufnahme()
        if self.pruefung is None or self.pruefung.werkstueckaufnahme is not aufnahme:
            # Wie pruefe(): Der Vorschlag braucht die Maschine (eine Stange auf ihrer Rundachse).
            self._zurueckfahren()
            self.pruefung = rw.Pruefung(self.assembly, self.maschine, aufnahme)
        vorschlag = rw.vorschlag_nullpunkt(self._job, self.pruefung)
        stellen = einheiten.stellen(einheiten.LAENGE, 3)
        for achse, feld in self.felder_nullpunkt.items():
            feld.blockSignals(True)
            feld.setText(_zahl(eingetragen[achse], stellen) if achse in eingetragen else "")
            feld.blockSignals(False)
            feld.setPlaceholderText(_zahl(getattr(vorschlag, achse.lower()), stellen))
        self._achse_zeigen()
        self.pruefe()

    def eingetragen(self):
        """Die eingetragenen Werte in mm: {"X": …} – leere Felder fehlen, ebenso eines, in dem
        noch keine Zahl steht („-“ am Anfang einer negativen)."""
        werte = {}
        for achse, feld in self.felder_nullpunkt.items():
            if feld.text().strip():
                with contextlib.suppress(ValueError):
                    werte[achse] = groesse_lesen(feld.text(), einheiten.LAENGE)
        return werte

    def nullpunkt(self):
        """Der Nullpunkt, mit dem gerechnet wird: eingetragen, sonst der Vorschlag (eine Stange
        quer zu Z auf der Rundachse dieser Maschine, B-037)."""
        vorschlag = rw.vorschlag_nullpunkt(self.job(), self.pruefung)
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

    def _maschine_merken(self):
        """Merkt die Maschinendatei am Job und als zuletzt benutzte – so öffnet das Addon sie
        beim nächsten Mal selbst (D-20). Ändert sich der Job, ist das ein Schritt Rückgängig
        in seinem Dokument."""
        job = self._job
        pfad = self.assembly.Document.FileName
        if not pfad or job is None or job.Document.Name not in FreeCAD.listDocuments():
            return  # eine nie gespeicherte Maschine lässt sich nicht wieder öffnen
        if getattr(job, rw.EIGENSCHAFT_MASCHINE, "") == pfad:
            rw.merke_maschine(job, pfad)  # nur noch „zuletzt benutzt“
            return
        job.Document.openTransaction(tr("rw.maschine.schritt"))
        rw.merke_maschine(job, pfad)
        job.Document.commitTransaction()

    # --- Rechnen und zeigen ---------------------------------------------------------

    def pruefe(self):
        """Rechnet mit dem, was eingestellt ist, und zeigt das Ergebnis – einen großen Job
        (IM_TAKT_AB Sätze) im Takt der Ereignisschleife (_lauf_starten): Das Fenster nimmt
        dazwischen Eingaben an, eine neue Eingabe beginnt von vorn."""
        self._uhr.stop()
        self._lauf_beenden()
        aufnahme = self.werkstueckaufnahme()
        if self.pruefung is None or self.pruefung.werkstueckaufnahme is not aufnahme:
            self._zurueckfahren()
            self.pruefung = rw.Pruefung(self.assembly, self.maschine, aufnahme)
        job, nullpunkt = self.job(), self.nullpunkt()
        if self._fuenfachs_vorrechnen(job, nullpunkt):
            return  # die Nebenrechner rechnen die 5-Achs-Programme; danach noch einmal
        if _saetze(job) >= IM_TAKT_AB:
            self._lauf_starten(job, nullpunkt)
            return
        # Reichweite und Abfahren lesen dieselben Bahnen: einmal (P-2026-10-11-26). Am Stück, aber
        # das Fenster zeichnet dabei neu (an der Nocke in RC1 2,7 s; P-2026-10-11-82).
        with self.pruefung.schritte_teilen(), uhren.atmend():
            self.ergebnis = self.pruefung.pruefe_job(job, nullpunkt, self.bibliothek)
            self._zeige()
            self._abfahrt_rechnen(job, nullpunkt)
        self.kollision.veraltet()

    # --- Im Takt (P-2026-10-11-41) --------------------------------------------------------

    def rechnet(self):
        """Rechnet gerade ein großer Job im Takt – oder rechnen die Nebenrechner seine
        5-Achs-Programme vor?"""
        return self._lauf is not None or bool(self._vorrechnen)

    def _fuenfachs_vorrechnen(self, job, nullpunkt):
        """Die Programme der 5-Achs-Operationen (simultan_operation.programm) – das Teuerste beim
        Öffnen, an der Bahn des Szenarios „Wegkippen“ 12 s am Stück – rechnen die Nebenrechner vor,
        je Operation einer; bis sie da sind, steht oben „rechnet …“, und das Fenster bleibt
        bedienbar. Danach prüft es mit ihnen aus dem Speicher (P-2026-10-11-70). True, solange es
        auf sie wartet; False ohne Nebenrechner oder wenn nichts fehlt."""
        from . import kollision as kb
        from . import nebenrechner as nr
        from . import schwenken as sw
        from . import simultan_operation as so

        fehlen = []
        for op, ebene in rw.operationen_mit_ebene(job):
            if ebene is not None or not so.ist_simultan(op):
                continue
            tc = getattr(op, "ToolController", None)
            aufnahme = self.pruefung.werkzeugaufnahme(getattr(tc, "ToolNumber", 0)) if tc else None
            if aufnahme is None:
                continue
            eingespannt = rw.einspannung(tc, self.bibliothek)
            m = sw.Maschine(self.pruefung, aufnahme, eingespannt, nullpunkt)
            schluessel = so._inhalt(op, m, False, False)
            if (
                schluessel is None
                or schluessel in so._PROGRAMME
                or schluessel in self._vorrechnen_gescheitert
            ):
                continue
            fehlen.append((schluessel, op, aufnahme, eingespannt))
        if not fehlen:
            return False
        neu = [f for f in fehlen if f[0] not in self._vorrechnen]
        if neu:
            pool = nr.pool()
            if not pool.verfuegbar():
                return False
            try:
                job_kopie = pool.kopie(job.Document, wiederverwenden=True)
                maschine_kopie, maschine = kb._maschinendaten(pool, self.pruefung)
                for schluessel, op, aufnahme, eingespannt in neu:
                    auftrag = pool.auftrag(
                        "simultan_operation",
                        "programm_im_arbeiter",
                        job_kopie,
                        op.Name,
                        maschine_kopie,
                        maschine,
                        aufnahme.Name,
                        float(eingespannt.laenge),
                        kb.lage_als_daten(eingespannt.lage),
                        tuple(nullpunkt),
                    )
                    auftrag.bei_fertig = functools.partial(self._vorgerechnet, schluessel)
                    self._vorrechnen[schluessel] = auftrag
            except (nr.Fehler, kb.NichtTeilbar):
                return False
        self._rechnet_zeigen(True)
        return True

    def _vorgerechnet(self, schluessel, auftrag):
        """Ein 5-Achs-Programm vom Nebenrechner: in den Speicher (simultan_operation.merken) – sind
        alle da, prüft das Fenster (über seine Uhr, nicht mitten in einer Rechnung)."""
        from . import simultan_operation as so

        if self._vorrechnen.get(schluessel) is not auftrag:
            return
        del self._vorrechnen[schluessel]
        if auftrag.fertig and auftrag.ergebnis is not None:
            so.merken(schluessel, *auftrag.ergebnis)
        else:
            self._vorrechnen_gescheitert.add(schluessel)  # dann rechnet pruefe() es hier
        if self._vorrechnen or PruefPanel.offen is not self:
            return
        self._rechnet_zeigen(False)
        self._uhr.start()

    def _lauf_starten(self, job, nullpunkt):
        """Reichweite und Abfahren als Schritte (pruefe_job_schritte, abfahrt_schritte), je
        TAKT_MS am Stück aus der Ereignisschleife – am Nasen-Testteil (330 000 Schritte) stand
        das Fenster beim Öffnen und nach jeder Eingabe des Nullpunkts 6,5 s still (Manuel,
        2026-10-09: „ein Lag … wo ich nichts klicken kann … sowas muss unbedingt vermieden
        werden“)."""
        stapel = contextlib.ExitStack()
        stapel.enter_context(self.pruefung.schritte_teilen())
        lauf = self._pruefen_schritte(job, nullpunkt, stapel)
        self._lauf = lauf
        self._rechnet_zeigen(True)
        QtCore.QTimer.singleShot(0, functools.partial(self._lauf_schritt, lauf))

    def _pruefen_schritte(self, job, nullpunkt, stapel):
        try:
            self.ergebnis = yield from self.pruefung.pruefe_job_schritte(
                job, nullpunkt, self.bibliothek
            )
            self._zeige()
            abfahrt = yield from ab.abfahrt_schritte(self.pruefung, job, nullpunkt, self.bibliothek)
            yield from abfahrt.am_werkstueck_schritte()  # für das Bild, im Takt (P-66)
            self._abfahrt_zeigen(job, nullpunkt, abfahrt)
            self.kollision.veraltet()
        finally:
            stapel.close()

    def _lauf_schritt(self, lauf):
        """Rechnet höchstens TAKT_MS am Lauf; der nächste Schritt kommt aus der Ereignisschleife.
        Ein veralteter Lauf (neue Eingabe, Fenster zu) hört auf."""
        if lauf is not self._lauf or PruefPanel.offen is not self:
            lauf.close()
            return
        if uhren.verschachtelt():
            # Mitten in einer anderen Rechnung (eine, die Ereignisse abarbeitet): danach weiter.
            QtCore.QTimer.singleShot(TAKT_MS, functools.partial(self._lauf_schritt, lauf))
            return
        ende = time.perf_counter() + TAKT_MS / 1000.0
        try:
            while time.perf_counter() < ende:
                next(lauf)
        except StopIteration:
            if self._lauf is lauf:
                self._lauf = None
                self._rechnet_zeigen(False)
            return
        except Exception:
            if self._lauf is lauf:
                self._lauf = None
                self._rechnet_zeigen(False)
            raise
        QtCore.QTimer.singleShot(0, functools.partial(self._lauf_schritt, lauf))

    def _lauf_beenden(self):
        """Ein Lauf im Takt hört auf (sein Block schritte_teilen mit)."""
        lauf, self._lauf = self._lauf, None
        if lauf is not None:
            lauf.close()
            self._rechnet_zeigen(False)

    def _rechnet_zeigen(self, an):
        """Solange ein großer Job rechnet: oben grau „rechnet …“; Abspielen und „Kollision
        prüfen“ warten, bis er fertig ist."""
        self.abspieler.setEnabled(not an)
        self.kollision.knopf.setEnabled(not an)
        if an:
            self._urteil(tr("rw.rechnet"), GRAU.name())
            self.liste.setVisible(False)
            self.abspieler.stelle.setText(tr("rw.rechnet"))

    def _abfahrt_rechnen(self, job, nullpunkt):
        """Die Stationen fürs Abfahren und die Körper in der 3D-Ansicht (_abfahrt_zeigen)."""
        self._abfahrt_zeigen(
            job, nullpunkt, ab.abfahrt(self.pruefung, job, nullpunkt, self.bibliothek)
        )

    def _abfahrt_zeigen(self, job, nullpunkt, abfahrt):
        """Zeigt die Abfahrt und die Körper in der 3D-Ansicht. Steht die Maschine schon auf der
        Bahn, fährt sie an dieselbe Zeit – passend zum neuen Nullpunkt."""
        zeit = self.abspieler.zeit if self._bewegt else None
        self.abfahrt = abfahrt
        fuer = self._bild_fuer
        if fuer is None or fuer[0] is not job or fuer[1] is not self.pruefung:
            self._bild_weg()
            ansicht = gui_abfahren.ansicht_von(self.assembly.Document)
            if ansicht is not None and self.pruefung.werkstueckaufnahme is not None:
                self.bild = gui_abfahren.Bild(
                    ansicht, self.abfahrt, job, nullpunkt, self.bibliothek
                )
                self.bild.zeige_bahn(self.abspieler.haken_bahn.isChecked())
                self.bild.zeige_teil(self.abspieler.haken_teil.isChecked())
                self._maschine_ansicht(self.abspieler.maschine_ansicht())
                self._bild_fuer = (job, self.pruefung)
        elif self.bild is not None:
            self.bild.nullpunkt = FreeCAD.Vector(nullpunkt)
            self.bild.folge()
        self.abspieler.zeige(self.abfahrt, zeit)
        self._zeit_zeigen()

    def _zeit_zeigen(self):
        """„Rechnerisch 2 h 40 min – Vorschub 2 h 31 min, Eilgang 9 min“, darunter der Balken mit
        dem Anteil jeder Operation (Zeitanteile) – ohne Bahn ein Strich."""
        abfahrt = self.abfahrt
        if abfahrt is None or not abfahrt.stationen:
            self.urteil_zeit.setText("–")
            self.zeitanteile.setzen([])
            return
        vorschub, eilgang = abfahrt.anteile()
        text = tr(
            "rw.zeit",
            dauer=ab.dauer_text(abfahrt.dauer),
            vorschub=ab.dauer_text(vorschub),
            eilgang=ab.dauer_text(eilgang),
        )
        wechsel = len(abfahrt.wechsel_vor)
        if abfahrt.wechselzeit > 0 and wechsel:
            text = tr(
                "rw.zeit.wechsel",
                text=text,
                anzahl=wechsel,
                je=ab.dauer_text(abfahrt.wechselzeit),
            )
        # Je Operation: als Balken darunter, nicht als Kette von Namen und Zahlen.
        self.zeitanteile.setzen(abfahrt.dauer_je_operation())
        self.urteil_zeit.setText(text)

    def _zur_operation(self, nummer):
        """Ein Klick auf ein Stück des Zeitbalkens: im Abspieler an den Anfang der Operation."""
        if (
            self.abspieler is not None and self.abspieler.isEnabled()
        ):  # nicht, solange gerechnet wird
            self.abspieler.springe_zu_operation(nummer)

    def _abtragen(self, station):
        """Rohteil und Fertigteil (W-003 V3g): die Stange bis zu dieser Station abgetragen;
        gibt den Satz dazu zurück („“, wenn der Job keine runde Stange mit „Rundum schruppen“
        hat)."""
        if self.bild is None:
            return ""
        satz = self.bild.abtragen(station, fertig=self._abtrag_angekommen)
        if self.abspieler is not None:
            self.abspieler.knopf_fertigteil.setVisible(self._fertigteil_moeglich())
        return satz

    def _abtrag_angekommen(self, satz):
        """Der Abtrag im Takt ist gerechnet (Bild.abtragen): sein Satz unter den Abspieler – nicht
        mehr, wenn das Fenster inzwischen zu ist."""
        if self.abspieler is None or PruefPanel.offen is not self:
            return
        self.abspieler.rest_setzen(satz)
        self.abspieler.knopf_fertigteil.setVisible(self._fertigteil_moeglich())

    def _fertigteil_moeglich(self):
        """Am Ende des Abspielens: Geht aus dem Abtrag ein Fertigteil – die Stange (4 Achsen) oder
        der Quader von oben (3 Achsen; dort rechnet es wie der Befehl aus dem Materialstand)?"""
        from . import restmaterial as rm

        bild = self.bild
        abtrag = getattr(bild, "abtrag", None) if bild is not None else None
        return bool(getattr(bild, "_am_ende", False)) and type(abtrag) in (
            rm.Abtrag,
            rm.QuaderAbtrag,
        )

    def _fertigteil(self):
        """„Fertigteil als Rohteil“ (W-029): aus dem Abtrag des Jobs – die Stange aus ihren Radien,
        sonst wie der Befehl im Menü."""
        from . import gui_fertigteil
        from . import restmaterial as rm

        abtrag = getattr(self.bild, "abtrag", None)
        gui_fertigteil.ausfuehren(self.job(), abtrag if type(abtrag) is rm.Abtrag else None)

    def _bahn_zeigen(self, an):
        """Der Haken „Bahn“ im Abspieler: die Bahn in der 3D-Ansicht ein- oder ausblenden."""
        if self.bild is not None:
            self.bild.zeige_bahn(an)

    def _maschine_ansicht(self, modus):
        """Die Auswahl „Maschine“ im Abspieler: die Körper der Maschine wie gebaut, durchsichtig
        oder ausgeblendet – Werkzeug und Halter (Knoten des Bilds) bleiben, ebenso Teil und
        Rohteil. Wie sie vorher waren, merkt sich das Fenster und stellt es beim Schließen
        wieder her (_ansicht_zurueck)."""
        for objekt in self._maschinenkoerper():
            sicht = objekt.ViewObject
            if objekt.Name not in self._ansicht_vorher:
                self._ansicht_vorher[objekt.Name] = (
                    int(sicht.Transparency),
                    bool(sicht.Visibility),
                )
            durchsicht, sichtbar = self._ansicht_vorher[objekt.Name]
            if modus == gui_abfahren.MASCHINE_AUS:
                sicht.Visibility = False
                continue
            sicht.Visibility = sichtbar
            if modus == gui_abfahren.MASCHINE_DURCHSICHTIG:
                sicht.Transparency = max(durchsicht, gui_abfahren.maschine_durchsicht())
            else:
                sicht.Transparency = durchsicht

    def _maschinenkoerper(self):
        """Die Körper der Maschine mit Ansicht – was in der Assembly eine Form zeigt."""
        if not FreeCAD.GuiUp or self.assembly is None:
            return []
        try:
            objekte = self.assembly.OutListRecursive
        except Exception:  # die Maschine ist schon zu
            return []
        return [
            o
            for o in objekte
            if o.TypeId.startswith("Part::")
            and getattr(o, "ViewObject", None) is not None
            and hasattr(o.ViewObject, "Transparency")
        ]

    def _ansicht_zurueck(self):
        """Die Körper der Maschine wieder so, wie sie vor der Auswahl „Maschine“ waren."""
        if not self._ansicht_vorher:
            return
        for objekt in self._maschinenkoerper():
            vorher = self._ansicht_vorher.get(objekt.Name)
            if vorher is not None:
                objekt.ViewObject.Transparency, objekt.ViewObject.Visibility = vorher
        self._ansicht_vorher = {}

    def _teil_zeigen(self, an):
        """Der Haken „Teil“ im Abspieler: das fertige Teil auch am Ende zeigen."""
        if self.bild is not None:
            self.bild.zeige_teil(an)

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
        bild = self.bereiche_bild.layout()
        while bild.count():
            alter = bild.takeAt(0).widget()
            if alter is not None:
                alter.deleteLater()
        for bereich in e.bereiche:
            balken = Achsbalken(bereich)
            balken.geklickt.connect(functools.partial(self._zur_ueberschreitung, bereich.name))
            bild.addWidget(balken)
        self.bereiche_titel.setText(tr("rw.bereiche.bild", anzahl=e.punkte))
        self.bereiche_titel.setToolTip("\n".join(zeilen))
        self.bereiche_titel.setVisible(bool(e.bereiche))
        self.bereiche_bild.setVisible(bool(e.bereiche))
        gui_kollision.hinweise_setzen(self.hinweise, e.hinweise)
        self.hinweise.setVisible(bool(e.hinweise))
        geschaetzt = e.geschaetzte_laengen()
        if geschaetzt:
            werkzeuge = ", ".join(f"T{nummer}" for nummer in geschaetzt)
            warum = f'<a href="abschnitt:hinweise">{tr("rw.urteil.warum")}</a>'
            text = f"{tr('rw.laenge.geschaetzt', werkzeuge=werkzeuge)} – {warum}"
            _zeige_urteil(self.urteil_laenge, text, gui_kollision.GELB)
        else:
            _zeige_urteil(self.urteil_laenge, tr("rw.laenge.gemessen"), GRUEN)
        for widget in (self.urteil_laenge, self._beschriftung[self.urteil_laenge]):
            widget.setVisible(bool(e.laengen))
        if e.spannung:
            namen = ", ".join(f"„{b.operation}“" for b in e.spannung)
            warum = f'<a href="abschnitt:hinweise">{tr("rw.urteil.warum")}</a>'
            text = f"{tr('rw.spannung.rein', operationen=namen)} – {warum}"
            _zeige_urteil(self.urteil_spannung, text, ROT)
        elif e.gespannt > 0:
            gespannt = rw.weg_text(e.gespannt)
            if e.stange:  # die N-Eck-Stange (W-018)
                frei = tr("rw.spannung.frei_stange", gespannt=gespannt)
            elif spannung.rund(getattr(rw.grundjob_von(self.job()), "Stock", None)) is not None:
                frei = tr("rw.spannung.frei_futter", gespannt=gespannt)  # W-021
            else:
                frei = tr("rw.spannung.frei", gespannt=gespannt)
            _zeige_urteil(self.urteil_spannung, frei, GRUEN)
        for widget in (self.urteil_spannung, self._beschriftung[self.urteil_spannung]):
            widget.setVisible(e.gespannt > 0)
        self._schnittwerte_zeigen()

    def _schnittwerte_zeigen(self):
        """Das Urteil „Schnittwerte“: Passen Drehzahl und Vorschub im Job zur
        Werkzeugverwaltung? Sonst je Controller ein Satz mit „übernehmen“ (D-28)."""
        job = self.job()
        self.vergleiche = js.vergleiche(job, self.bibliothek) if self.bibliothek else []
        veraltet = [v for v in self.vergleiche if v.veraltet]
        if veraltet:
            zeilen = [_veraltet_satz(v) for v in veraltet]
            if len(veraltet) > 1:
                zeilen.append(f'<a href="schnittwerte:*">{tr("rw.schnittwerte.alle")}</a>')
            # Nicht fett: Es sind Sätze mit Zahlen, keine Überschrift.
            text = "<br>".join(zeilen)
            _zeige_urteil(self.urteil_schnittwerte, text, gui_kollision.GELB, fett=False)
        else:
            _zeige_urteil(self.urteil_schnittwerte, tr("rw.schnittwerte.passen"), GRUEN)
        for widget in (self.urteil_schnittwerte, self._beschriftung[self.urteil_schnittwerte]):
            widget.setVisible(bool(self.vergleiche))

    def schnittwerte_uebernehmen(self, ziel):
        """„schnittwerte:<Name des Controllers>“ setzt dessen Drehzahl und Vorschub wie in
        der Werkzeugverwaltung, „schnittwerte:*“ die aller veralteten – ein Schritt
        Rückgängig im Dokument des Jobs (D-28)."""
        name = ziel.split(":", 1)[1]
        veraltet = [v for v in self.vergleiche if v.veraltet and name in ("*", v.tc.Name)]
        if not veraltet:
            return
        self._zurueckfahren()  # dessen offener Schritt gehört nicht zum Übernehmen
        js.uebernimm(self.job().Document, veraltet, tr("rw.schnittwerte.schritt"))
        self.pruefe()

    def _urteil(self, text, farbe):
        _zeige_urteil(self.urteil, text, farbe)

    def _kollision_gemeldet(self, text, farbe, fett):
        """Das Urteil der Kollision, oben im Fenster – und ihre Berührungen für den Abspieler
        (er hält dort an; „Zur nächsten Kollision“)."""
        _zeige_urteil(self.urteil_kollision, text, farbe, fett)
        ergebnis = self.kollision.ergebnis if hasattr(self, "kollision") else None
        self.abspieler.kollisionen_setzen(ergebnis.befunde if ergebnis is not None else [])

    def _werkzeug_oeffnen(self, ziel):
        """„werkzeug:1“: die Werkzeugverwaltung bei T1. Speichert man dort, rechnet das
        Fenster mit den neuen Werten – etwa mit dem gewählten Halter (D-11)."""
        dialog = gui_werkzeuge.oeffne(int(ziel.split(":", 1)[1]))
        if dialog is not self._werkzeugdialog:
            self._werkzeugdialog = dialog
            dialog.gespeichert.connect(self._werkzeuge_gespeichert)

    def _werkzeuge_gespeichert(self):
        if PruefPanel.offen is not self:
            return
        self.bibliothek = _bibliothek()
        if self.bibliothek is not None:
            mg.des_jobs(self.job(), self.bibliothek, self.assembly)
        self._bild_weg()  # Werkzeug und Halter in der Ansicht neu
        self.pruefe()

    def _werkzeug_ausspannen(self, nummer, laenge, heraus, platz=None):
        """„T1 auf … mm ausspannen“ unter den Befunden (gui_kollision): T`nummer` in der
        Werkzeugverwaltung auf `laenge` mm ab Spindelnase (rw.ausspannen_setzen), gespeichert; das Fenster rechnet mit
        ihr neu (wie nach dem Speichern in der Werkzeugverwaltung). Gibt den Satz dazu zurück."""
        if self.bibliothek is None:
            return ""
        werkzeug = rw.ausspannen_werkzeug(self.bibliothek, nummer, platz)
        if werkzeug is None:
            return ""
        rw.ausspannen_setzen(werkzeug, laenge, heraus, self.bibliothek)
        self.bibliothek.speichern()
        satz = rw.ausgespannt_text(werkzeug, heraus, laenge) + " " + tr("kb.ausgespannt_pruefen")
        self._werkzeuge_gespeichert()
        return satz

    def _kollision_verweis(self, ziel):
        """Die Verweise im Urteil „Kollision“: „kollision:pruefen“ prüft, „kollision:wo“ zeigt
        den Bereich."""
        if ziel == "kollision:pruefen":
            self.kollision.pruefen()
        else:
            blaettere_zu(self.kollision)

    # --- Die Maschine ---------------------------------------------------------------

    def _zur_ueberschreitung(self, name):
        """Ein Klick auf den roten Balken der Achse `name`: an die Stelle, an der sie am weitesten
        über ihre Grenze müsste (fahre_hin)."""
        if self.ergebnis is None:
            return
        treffer = [
            (abs(u.stellung - u.grenze), nummer)
            for nummer, u in enumerate(self.ergebnis.ueberschreitungen)
            if u.name == name
        ]
        if treffer:
            nummer = max(treffer)[1]
            self.liste.setCurrentRow(nummer)
            self.fahre_hin(nummer)

    def fahre_hin(self, nummer):
        """Fährt die Maschine an die Stelle der Überschreitung Nummer `nummer` – so weit
        die Achsen kommen, die überschreitende steht an ihrer Grenze. Der Abspieler steht
        danach dort."""
        if self.ergebnis is None or not 0 <= nummer < len(self.ergebnis.ueberschreitungen):
            return
        if not self.abspieler.isEnabled():
            # Solange neu gerechnet wird, gehört die Abfahrt im Fenster noch zur abgelösten
            # Prüfung: Ihre Achsen kennt die neue Kette nicht (KeyError in verfahren.setze_alle,
            # nachgestellt am 2026-11-13). Balken und Liste fahren erst wieder, wenn sie fertig ist.
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
            if not self._marke_behalten:
                self.bild.markiere(None)
        return angehalten

    # --- Kollision ------------------------------------------------------------------

    def _kollision_daten(self):
        """Für den Bereich „Kollision“: (Abfahrt, Job, Nullpunkt, Werkzeugverwaltung)."""
        return self.abfahrt, self.job(), self.nullpunkt(), self.bibliothek

    def _kollision_hin(self, befund):
        """Stellt den Abspieler auf die Stelle eines Befunds; eine rote Kugel zeigt sie."""
        self.abspieler.anhalten()
        self._marke_behalten = True
        try:
            self.abspieler.setze_zeit(befund.zeit)
        finally:
            self._marke_behalten = False
        if self.bild is not None and befund.stelle is not None:
            stelle = self.assembly.Placement.multVec(befund.stelle)
            self.bild.markiere(stelle)
            self.bild.zeige_stelle(stelle)
        zeige_dokument(self.assembly.Document)

    def _sperren(self, gesperrt):
        """Solange die Kollision rechnet, lässt sich sonst nichts ändern."""
        for widget in (
            self.wahl_job,
            self.wahl_aufnahme,
            *self.felder_nullpunkt.values(),
            self.liste,
            self.abspieler,
        ):
            widget.setEnabled(not gesperrt)

    def _hinsehen(self):
        if self.bild is not None:
            self.bild.hinsehen()
            zeige_dokument(self.assembly.Document)

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


IM_TAKT_AB = 20000  # Sätze im Job: ab so vielen rechnet das Fenster im Takt (_lauf_starten)
TAKT_MS = 40  # so lange rechnet ein Schritt im Takt am Stück


def _saetze(job):
    """Wie viele Sätze die aktiven Operationen des Jobs haben (auch in geschwenkten Ebenen)."""
    zahl = 0
    for op, _ebene in rw.operationen_mit_ebene(job):
        pfad = getattr(op, "Path", None)
        zahl += len(pfad.Commands) if pfad is not None else 0
    return zahl


def _veraltet_satz(vergleich):
    """„T3 Schruppen dynamisch: im Job 2122 U/min · 318 mm/min, laut Werkzeugverwaltung
    3183 U/min · 477 mm/min – übernehmen“ – nur mit dem, was abweicht; HTML."""
    v = vergleich
    jetzt, neu = [], []
    if v.n_anders:
        jetzt.append(tr("rw.schnittwerte.n", n=zahlenformat().toString(v.n_jetzt, "f", 0)))
        neu.append(tr("rw.schnittwerte.n", n=zahlenformat().toString(float(v.n), "f", 0)))
    if v.vf_anders:
        jetzt.append(tr("rw.schnittwerte.vf", vf=groesse_fest(v.vf_jetzt, einheiten.VORSCHUB, 0)))
        neu.append(tr("rw.schnittwerte.vf", vf=groesse_fest(v.vf, einheiten.VORSCHUB, 0)))
    satz = tr(
        "rw.schnittwerte.veraltet", tc=v.tc.Label, jetzt=" · ".join(jetzt), neu=" · ".join(neu)
    )
    verweis = f'<a href="schnittwerte:{v.tc.Name}">{tr("rw.schnittwerte.uebernehmen")}</a>'
    return f"{html.escape(satz)} – {verweis}"


def _zeige_urteil(label, text, farbe, fett=True):
    label.setText(text)
    gewicht = "font-weight: bold;" if fett else ""
    label.setStyleSheet(f"color: {farbe}; {gewicht}")


def _zahl(wert, stellen):
    """Zahl für ein Feld, ohne Nullen am Ende: „−50“, „12,5“ – auch 0 als „0“."""
    text = zahlenformat().toString(float(einheiten.anzeige(wert, einheiten.LAENGE)), "f", stellen)
    zeichen = zahlenformat().decimalPoint()
    if zeichen in text:
        text = text.rstrip("0").rstrip(zeichen)
    return "0" if text in ("-0", "") else text
