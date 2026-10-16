# SPDX-License-Identifier: LGPL-2.1-or-later
"""„Einrichtblatt …“ (W-019): das Einrichtblatt des gewählten Jobs (einrichtblatt.py) als Vorschau –
dazu als PDF speichern, drucken oder als HTML speichern. Je Aufspannung ein Bild aus der 3D-Ansicht
des Dokuments (Teil und Rohteil, schräg von oben)."""

import datetime
import os
import tempfile

import FreeCAD
import FreeCADGui
from PySide import QtGui

from . import VERSION, einheiten, symbol
from . import einrichtblatt as eb
from .gui_zahlen import dezimal, groesse_zeigen
from .sprache import tr

BILD_BREITE, BILD_HOEHE = 160, 280  # Pixel – das Bild von Halter und Werkzeug, doppelt so groß
# wie in der Halterverwaltung, damit es gedruckt nicht verschwimmt


def _drucken_modul():
    try:
        from PySide6 import QtPrintSupport
    except ImportError:  # FreeCAD mit PySide2
        from PySide2 import QtPrintSupport
    return QtPrintSupport


def _laenge(mm):
    return groesse_zeigen(mm, einheiten.LAENGE, 2) or "0"


def _minuten(minuten):
    return dezimal(f"{minuten:.1f} min")


class EinrichtblattDialog(QtGui.QDialog):
    """Die Vorschau mit den Knöpfen zum Speichern und Drucken."""

    offen = None  # für die Szenarien

    def __init__(self, job, eltern=None):
        super().__init__(eltern or FreeCADGui.getMainWindow())
        EinrichtblattDialog.offen = self
        self.job = job
        self.setWindowTitle(tr("eb.fenster", job=job.Label))
        self.blatt = eb.blatt(job, datetime.date.today().isoformat(), VERSION)
        self._bilder_machen()
        self.text = eb.html(self.blatt, tr, _laenge, _minuten)
        aufbau = QtGui.QVBoxLayout(self)
        self.vorschau = QtGui.QTextBrowser()
        self.vorschau.setHtml(self.text)
        aufbau.addWidget(self.vorschau)
        knoepfe = QtGui.QHBoxLayout()
        self.knopf_pdf = QtGui.QPushButton(tr("eb.pdf"))
        self.knopf_pdf.clicked.connect(lambda: self.als_pdf())
        self.knopf_drucken = QtGui.QPushButton(tr("eb.drucken"))
        self.knopf_drucken.clicked.connect(self.drucken)
        self.knopf_html = QtGui.QPushButton(tr("eb.html"))
        self.knopf_html.clicked.connect(lambda: self.als_html())
        schliessen = QtGui.QPushButton(tr("eb.schliessen"))
        schliessen.clicked.connect(self.reject)
        for knopf in (self.knopf_pdf, self.knopf_drucken, self.knopf_html):
            knoepfe.addWidget(knopf)
        knoepfe.addStretch()
        knoepfe.addWidget(schliessen)
        aufbau.addLayout(knoepfe)
        self.resize(820, 900)

    def _bilder_machen(self):
        """Die Bilder der Werkzeuge (_werkzeugbilder) und je Aufspannung eins der 3D-Ansicht
        (_bild_der_aufspannung). Der Navigationswürfel gehört nicht aufs Blatt: über die
        Einstellung aus und wieder an – nicht über `ansicht.getViewer()`, das ließ FreeCAD 1.1.4
        beim Schließen der Ansicht abstürzen (B-011)."""
        ordner = tempfile.mkdtemp(prefix="einrichtblatt_")
        self._werkzeugbilder(ordner)
        dokument = ansicht = None
        with _ignoriert():
            dokument = FreeCADGui.getDocument(self.job.Document.Name)
            ansicht = dokument.mdiViewsOfType("Gui::View3DInventor")[0]
        if ansicht is None:
            return
        ansicht_einstellungen = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/View")
        wuerfel = ansicht_einstellungen.GetBool("ShowNaviCube", True)
        geaendert = getattr(dokument, "Modified", None)
        try:
            if wuerfel:
                ansicht_einstellungen.SetBool("ShowNaviCube", False)
            for i, aufspannung in enumerate(self.blatt.aufspannungen):
                pfad = os.path.join(ordner, f"aufspannung_{i + 1}.png")
                with _ignoriert():
                    self._bild_der_aufspannung(ansicht, aufspannung, pfad)
        finally:
            if wuerfel:
                ansicht_einstellungen.SetBool("ShowNaviCube", True)
            if geaendert is False:  # nur gezeigt und versteckt: das Dokument bleibt ungeändert
                with _ignoriert():
                    dokument.Modified = False

    def _bild_der_aufspannung(self, ansicht, aufspannung, pfad):
        """Teil, Rohteil und Bahnen des Jobs der Aufspannung, schräg von oben – die anderen Jobs
        dafür ausgeblendet –, dazu die Backen des Spannmittels (spannung.schraubstock). Das Bild
        (saveImage) zeichnet nur Objekte des Dokuments: Die Backen sind dafür kurz eins, in einer
        Transaktion, die danach verworfen wird – nichts bleibt, auch nicht im Rückgängig. Läuft
        schon eine Transaktion (ein offenes Fenster), ohne Backen. Danach steht alles, wie es war.
        """
        from . import reichweite as rw
        from . import spannung
        from .gui_abfahren import SCHRAUBSTOCK

        job = aufspannung.job
        if job is None:
            return
        dok = job.Document
        zeigen = {o.Name for o in getattr(job.Model, "Group", [])}
        if getattr(job, "Stock", None) is not None:
            zeigen.add(job.Stock.Name)
        zeigen |= {op.Name for op, _ebene in rw.operationen_mit_ebene(job)}
        backen = spannung.schraubstock(job)
        transaktion = backen is not None and not dok.HasPendingTransaction
        vorher = {}
        try:
            if transaktion:
                dok.openTransaction("Einrichtblatt")
                hilfe = dok.addObject("Part::Feature", "EinrichtblattBacken")
                hilfe.Shape = backen
                if getattr(hilfe, "ViewObject", None) is not None:
                    hilfe.ViewObject.ShapeColor = SCHRAUBSTOCK
                zeigen.add(hilfe.Name)
            for o in dok.Objects:
                ansicht_o = getattr(o, "ViewObject", None)
                if (
                    ansicht_o is None
                    or hasattr(o, "Operations")
                    or o.isDerivedFrom("App::DocumentObjectGroup")
                ):
                    continue  # Jobs und Gruppen bleiben – sie schalten ihren Inhalt mit
                soll = o.Name in zeigen
                if bool(ansicht_o.Visibility) != soll:
                    vorher[o.Name] = ansicht_o.Visibility
                    ansicht_o.Visibility = soll
            ansicht.viewIsometric()
            ansicht.fitAll()
            ansicht.saveImage(pfad, 840, 560, "White")
            aufspannung.bild = pfad
        finally:
            for name, sichtbar in vorher.items():
                o = dok.getObject(name)
                if o is not None and getattr(o, "ViewObject", None) is not None:
                    o.ViewObject.Visibility = sichtbar
            if transaktion:
                dok.abortTransaction()

    def _werkzeugbilder(self, ordner):
        """Je Werkzeug mit Halter das Bild aus der Halterverwaltung (gui_halter.HalterBild):
        Halter und Werkzeug maßstäblich, daneben die Ausspannlänge – auf Weiß, auch im dunklen
        Farbschema."""
        from .gui_halter import HalterBild

        for w in self.blatt.werkzeuge:
            h, werkzeug = w.halter_objekt, w.werkzeug_objekt
            if h is None or werkzeug is None or h.gewinkelt or w.laenge <= h.laenge:
                continue
            with _ignoriert():
                bild = HalterBild()
                bild.setFixedSize(BILD_BREITE, BILD_HOEHE)
                farben = bild.palette()
                farben.setColor(QtGui.QPalette.Base, QtGui.QColor("white"))
                bild.setPalette(farben)
                bild.zeige(h, werkzeug, w.laenge)
                pfad = os.path.join(ordner, f"werkzeug_t{w.nummer}.png")
                if bild.grab().save(pfad):
                    w.bild = pfad

    def als_pdf(self, pfad=None):
        """Speichert das Blatt als PDF – ohne `pfad` fragt es, wohin. Gibt den Pfad zurück."""
        if pfad is None:
            vorschlag = os.path.join(os.path.dirname(self.job.Document.FileName or ""),
                                     f"{self.job.Label}_einrichtblatt.pdf")  # fmt: skip
            pfad, _filter = QtGui.QFileDialog.getSaveFileName(
                self, tr("eb.pdf"), vorschlag, "PDF (*.pdf)"
            )
        if not pfad:
            return None
        drucken = _drucken_modul()
        drucker = drucken.QPrinter(drucken.QPrinter.HighResolution)
        drucker.setOutputFormat(drucken.QPrinter.PdfFormat)
        drucker.setOutputFileName(pfad)
        self._dokument().print_(drucker)
        return pfad

    def drucken(self):
        drucken = _drucken_modul()
        drucker = drucken.QPrinter(drucken.QPrinter.HighResolution)
        dialog = drucken.QPrintDialog(drucker, self)
        if dialog.exec():
            self._dokument().print_(drucker)

    def als_html(self, pfad=None):
        """Speichert das Blatt als HTML (die Bilder bleiben, wo sie liegen). Gibt den Pfad zurück."""
        if pfad is None:
            vorschlag = os.path.join(os.path.dirname(self.job.Document.FileName or ""),
                                     f"{self.job.Label}_einrichtblatt.html")  # fmt: skip
            pfad, _filter = QtGui.QFileDialog.getSaveFileName(
                self, tr("eb.html"), vorschlag, "HTML (*.html)"
            )
        if not pfad:
            return None
        with open(pfad, "w", encoding="utf-8") as datei:
            datei.write(self.text)
        return pfad

    def _dokument(self):
        dokument = QtGui.QTextDocument()
        dokument.setHtml(self.text)
        return dokument

    def done(self, ergebnis):
        EinrichtblattDialog.offen = None
        super().done(ergebnis)


class _ignoriert:
    """Fängt Fehler beim Bild ab – ohne Bild geht das Blatt trotzdem."""

    def __enter__(self):
        return self

    def __exit__(self, art, fehler, spur):
        if fehler is not None:
            FreeCAD.Console.PrintLog(f"CAM-Addon: Einrichtblatt-Bild: {fehler}\n")
        return True


def _gewaehlter_job():
    """Der gewählte Job (oder der eines gewählten Objekts im Job) – sonst der einzige im Dokument;
    None, wenn es keinen eindeutigen gibt."""
    for objekt in FreeCADGui.Selection.getSelection():
        if hasattr(objekt, "Operations") and hasattr(objekt, "Stock"):
            return objekt
        for oben in objekt.InListRecursive:
            if hasattr(oben, "Operations") and hasattr(oben, "Stock"):
                return oben
    dokument = FreeCAD.ActiveDocument
    jobs = [o for o in (dokument.Objects if dokument else []) if hasattr(o, "Operations")]
    return jobs[0] if len(jobs) == 1 else None


class BefehlEinrichtblatt:
    """Befehl im Menü: das Einrichtblatt des gewählten Jobs."""

    def GetResources(self):
        return {
            "Pixmap": symbol("programm.svg"),
            "MenuText": tr("befehl.einrichtblatt.titel"),
            "ToolTip": tr("befehl.einrichtblatt.tooltip"),
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None and EinrichtblattDialog.offen is None

    def Activated(self):
        job = _gewaehlter_job()
        if job is None:
            QtGui.QMessageBox.information(
                FreeCADGui.getMainWindow(), tr("befehl.einrichtblatt.titel"), tr("eb.kein_job")
            )
            return
        EinrichtblattDialog(job).show()
