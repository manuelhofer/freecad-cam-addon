# SPDX-License-Identifier: LGPL-2.1-or-later
"""„Einrichtblatt …“ (W-019): das Einrichtblatt des gewählten Jobs (einrichtblatt.py) als Vorschau –
dazu als PDF speichern, drucken oder als HTML speichern. Je Aufspannung ein Bild aus der 3D-Ansicht
des Dokuments (Teil und Rohteil, schräg von oben)."""

import datetime
import os
import tempfile

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import VERSION, einheiten, symbol
from . import einrichtblatt as eb
from .gui_teile import fenster_merken
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
        self._ordner = tempfile.mkdtemp(prefix="einrichtblatt_")
        self._werkzeugbilder(self._ordner)
        self.text = eb.html(self.blatt, tr, _laenge, _minuten)
        aufbau = QtGui.QVBoxLayout(self)
        self.vorschau = QtGui.QTextBrowser()
        self.vorschau.setHtml(self.text)
        aufbau.addWidget(self.vorschau)
        self.stand = QtGui.QLabel()
        self.stand.setStyleSheet("color: gray;")
        self.stand.hide()
        aufbau.addWidget(self.stand)
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
        fenster_merken(self, "Einrichtblatt", (820, 900))
        # Die Bilder der Aufspannungen kommen nach und nach (je eins ~0,75 s; an einer 8-Kant-Kette
        # stand das Fenster sonst 6 s, bevor es aufging): je Takt der Ereignisschleife eins.
        self._ansicht = self._dokument_gui = None
        self._wuerfel = self._geaendert = None
        self._offen_bilder = self._bilder_liste()
        self._gesamt = len(self._offen_bilder)
        self.bilder_fertig = not self._offen_bilder
        self._uhr = QtCore.QTimer(self)
        self._uhr.setSingleShot(True)
        self._uhr.timeout.connect(self._naechstes_bild)
        if self._offen_bilder:
            self._bilder_beginnen()

    def _bilder_liste(self):
        """[(Aufspannung, Lage oder None, Job, mit Backen, Pfad)] – je Aufspannung ihr Bild, je
        geschwenkte Ebene (3+2) ihres: ihr Job, das Teil so gedreht, wie es die Ebene sieht, ohne
        Backen (die stehen im Rahmen des Grundjobs)."""
        liste = []
        for i, aufspannung in enumerate(self.blatt.aufspannungen):
            pfad = os.path.join(self._ordner, f"aufspannung_{i + 1}.png")
            liste.append((aufspannung, None, aufspannung.job, True, pfad))
            for k, (lage, ebene) in enumerate(aufspannung.ebenen.items(), 1):
                pfad = os.path.join(self._ordner, f"aufspannung_{i + 1}_ebene_{k}.png")
                liste.append((aufspannung, lage, ebene, False, pfad))
        return liste

    def _bilder_beginnen(self):
        """Die 3D-Ansicht für die Bilder vorbereiten. Der Navigationswürfel gehört nicht aufs
        Blatt: über die Einstellung aus (und am Ende wieder an) – nicht über `ansicht.getViewer()`,
        das ließ FreeCAD 1.1.4 beim Schließen der Ansicht abstürzen (B-011)."""
        with _ignoriert():
            self._dokument_gui = FreeCADGui.getDocument(self.job.Document.Name)
            self._ansicht = self._dokument_gui.mdiViewsOfType("Gui::View3DInventor")[0]
        if self._ansicht is None:
            self._offen_bilder = []
            self.bilder_fertig = True
            return
        einstellungen = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/View")
        self._wuerfel = einstellungen.GetBool("ShowNaviCube", True)
        if self._wuerfel:
            einstellungen.SetBool("ShowNaviCube", False)
        self._geaendert = getattr(self._dokument_gui, "Modified", None)
        self._stand_zeigen()
        self._uhr.start(0)

    def _stand_zeigen(self):
        fertig = self._gesamt - len(self._offen_bilder)
        self.stand.setText(tr("eb.bilder_stand", fertig=fertig, gesamt=self._gesamt))
        self.stand.setVisible(bool(self._offen_bilder))

    def _naechstes_bild(self):
        """Ein Bild, dann die Seite neu (an derselben Stelle) – und das nächste im nächsten Takt."""
        if not self._offen_bilder:
            return
        self._ein_bild(self._offen_bilder.pop(0))
        balken = self.vorschau.verticalScrollBar()
        stelle = balken.value()
        self.text = eb.html(self.blatt, tr, _laenge, _minuten)
        self.vorschau.setHtml(self.text)
        balken.setValue(stelle)
        if self._offen_bilder:
            self._stand_zeigen()
            self._uhr.start(0)
        else:
            self._bilder_beenden()

    def _ein_bild(self, eintrag):
        aufspannung, lage, job, mit_backen, pfad = eintrag
        with _ignoriert():
            # Das Bild der Aufspannung mit dem Koordinatensystem am Nullpunkt (Manuel,
            # 2026-10-18: „ein bild von dem rohteil mit dem koordinatensystem am richtigen platz“).
            achsen = lage is None
            if self._bild(self._ansicht, job, pfad, mit_backen=mit_backen, mit_achsen=achsen):
                if lage is None:
                    aufspannung.bild = pfad
                    aufspannung.bild_achsen = self._achsen_gezeichnet
                else:
                    aufspannung.ebenen_bilder[lage] = pfad

    def _bilder_beenden(self):
        """Würfel wieder an, das Dokument ungeändert (nur gezeigt und versteckt)."""
        self._uhr.stop()
        if self._wuerfel:
            FreeCAD.ParamGet("User parameter:BaseApp/Preferences/View").SetBool(
                "ShowNaviCube", True
            )
            self._wuerfel = None
        if self._geaendert is False:
            with _ignoriert():
                self._dokument_gui.Modified = False
        self._offen_bilder = []
        self.bilder_fertig = True
        self.stand.hide()

    def _bilder_abschliessen(self):
        """Vor dem Speichern oder Drucken: die übrigen Bilder gleich, dann die Seite neu."""
        if self.bilder_fertig:
            return
        self._uhr.stop()
        while self._offen_bilder:
            self._ein_bild(self._offen_bilder.pop(0))
        self.text = eb.html(self.blatt, tr, _laenge, _minuten)
        self.vorschau.setHtml(self.text)
        self._bilder_beenden()

    def _bild(self, ansicht, job, pfad, mit_backen=True, mit_achsen=False):
        """Teil, Rohteil und Bahnen von `job`, schräg von oben – die anderen Jobs dafür
        ausgeblendet –, mit `mit_backen` dazu die Backen des Spannmittels (spannung.schraubstock).
        Das Bild (saveImage) zeichnet nur Objekte des Dokuments: Die Backen sind dafür kurz eins, in
        einer Transaktion, die danach verworfen wird – nichts bleibt, auch nicht im Rückgängig.
        Läuft schon eine Transaktion (ein offenes Fenster), ohne Backen. Mit `mit_achsen` ebenso kurz
        das Koordinatensystem des Jobs am Nullpunkt (_achsen_koerper: X rot, Y grün, Z blau) –
        `self._achsen_gezeichnet` sagt danach, ob es im Bild ist. Danach steht alles, wie es
        war. Gibt zurück, ob das Bild gespeichert ist."""
        from . import reichweite as rw
        from . import spannung
        from .gui_abfahren import SCHRAUBSTOCK

        if job is None:
            return False
        dok = job.Document
        zeigen = {o.Name for o in getattr(job.Model, "Group", [])}
        if getattr(job, "Stock", None) is not None:
            zeigen.add(job.Stock.Name)
        zeigen |= {op.Name for op in rw._operationen(job)}  # nur seine, nicht die der Ebenen
        backen = spannung.schraubstock(job) if mit_backen else None
        achsen = _achsen_koerper(job) if mit_achsen else []
        transaktion = (backen is not None or bool(achsen)) and not dok.HasPendingTransaction
        self._achsen_gezeichnet = False
        vorher = {}
        try:
            if transaktion:
                dok.openTransaction("Einrichtblatt")
                if backen is not None:
                    hilfe = dok.addObject("Part::Feature", "EinrichtblattBacken")
                    hilfe.Shape = backen
                    if getattr(hilfe, "ViewObject", None) is not None:
                        hilfe.ViewObject.ShapeColor = SCHRAUBSTOCK
                    zeigen.add(hilfe.Name)
                for name, form, farbe in achsen:
                    hilfe = dok.addObject("Part::Feature", name)
                    hilfe.Shape = form
                    if getattr(hilfe, "ViewObject", None) is not None:
                        hilfe.ViewObject.ShapeColor = farbe
                        hilfe.ViewObject.LineColor = farbe
                    zeigen.add(hilfe.Name)
                self._achsen_gezeichnet = bool(achsen)
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
            return os.path.exists(pfad)
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
        self._bilder_abschliessen()
        drucken = _drucken_modul()
        drucker = drucken.QPrinter(drucken.QPrinter.HighResolution)
        drucker.setOutputFormat(drucken.QPrinter.PdfFormat)
        drucker.setOutputFileName(pfad)
        self._dokument().print_(drucker)
        return pfad

    def drucken(self):
        self._bilder_abschliessen()
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
        self._bilder_abschliessen()
        with open(pfad, "w", encoding="utf-8") as datei:
            datei.write(self.text)
        return pfad

    def _dokument(self):
        dokument = QtGui.QTextDocument()
        dokument.setHtml(self.text)
        return dokument

    def done(self, ergebnis):
        if not self.bilder_fertig:  # mitten im Bildermachen geschlossen
            self._bilder_beenden()
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
            # Mehrere Jobs und keiner gewählt (das C-Ring-Beispiel: aus Platte und aus Rundmaterial):
            # fragen, welcher – statt nur zu sagen, dass man erst einen anklicken soll.
            dokument = FreeCAD.ActiveDocument
            jobs = [
                o
                for o in (dokument.Objects if dokument else [])
                if hasattr(o, "Operations") and eb.grundjob(o) is o
            ]
            if len(jobs) > 1:
                name, ok = QtGui.QInputDialog.getItem(
                    FreeCADGui.getMainWindow(),
                    tr("befehl.einrichtblatt.titel"),
                    tr("eb.job_waehlen"),
                    [j.Label for j in jobs],
                    0,
                    False,
                )
                if not ok:
                    return
                job = next(j for j in jobs if j.Label == name)
        if job is None:
            QtGui.QMessageBox.information(
                FreeCADGui.getMainWindow(), tr("befehl.einrichtblatt.titel"), tr("eb.kein_job")
            )
            return
        EinrichtblattDialog(job).show()


def _achsen_koerper(job):
    """[(Name, Form, Farbe)] – drei Pfeile X, Y, Z vom Nullpunkt des Jobs (dem Ursprung, auf den der
    Assistent den gewählten Punkt des Rohteils legt), so lang wie 0,4 Rohteildiagonalen (mindestens
    15 mm – neben Backen und Spannmittel sonst kaum zu sehen); leer ohne Rohteil."""
    import FreeCAD
    import Part

    rohteil = getattr(getattr(job, "Stock", None), "Shape", None)
    if rohteil is None or rohteil.isNull():
        return []
    laenge = max(15.0, rohteil.BoundBox.DiagonalLength * 0.4)
    dicke = laenge / 30
    ergebnis = []
    for name, richtung, farbe in (
        ("EinrichtblattX", FreeCAD.Vector(1, 0, 0), (0.85, 0.1, 0.1)),
        ("EinrichtblattY", FreeCAD.Vector(0, 1, 0), (0.1, 0.65, 0.1)),
        ("EinrichtblattZ", FreeCAD.Vector(0, 0, 1), (0.1, 0.25, 0.9)),
    ):
        schaft = Part.makeCylinder(dicke, laenge * 0.8, FreeCAD.Vector(), richtung)
        spitze = Part.makeCone(dicke * 3, 0, laenge * 0.2, richtung * (laenge * 0.8), richtung)
        ergebnis.append((name, schaft.fuse(spitze), farbe))
    return ergebnis
