# SPDX-License-Identifier: LGPL-2.1-or-later
"""„Programm schreiben“ – der Postprozessor des Addons mit seinem Fenster (W-005, S1–S3).

Manuel (2026-10-03): „ich möchte nicht den Postprozessor-Generator von FreeCAD nutzen … ich
hätte gern einen guten Postprozessor-Manager“; FreeCADs „Nachbearbeitung“ brach in 1.1.4 mit
„Post processor not identified“ ab. Das Fenster: Job, die Maschine des Jobs mit dem, was der
Postprozessor von ihr weiß, die Steuerung (gemerkt am Job und je Maschine), links ihre
Einstellungen in Gruppen – Haken mit einem Satz Erklärung, die Befehle zum Ändern, gelb, was der
Maschinenhersteller festlegt (gemerkt je Steuerung; Manuel, 2026-10-03: „die Optionen im
Postprozessor besser beschreiben, darstellen, mit Haken machen“) –, rechts die Vorschau der
ersten Sätze, unten „Speichern“. Die Maschine ist wählbar – jede offene, auch ungespeichert, und
die gemerkten (Manuel, 2026-10-03: seine neue Drehmaschine war offen, aber nicht gespeichert,
und das Fenster schrieb „Keine Maschine am Job“).
"""

import json
import os

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import PARAMETER_PFAD, symbol
from . import job_schnittwerte as js
from . import maschinenspeicher as msp
from . import postprozessor as pp
from . import reichweite as rw
from .gui_hilfe import kopfzeile
from .gui_teile import GRAU, knopf, ruhiges_mausrad
from .gui_zahlen import zahlenformat
from .sprache import tr

EIGENSCHAFT_STEUERUNG = "CamAddonSteuerung"  # am Job: die Kennung der Steuerung
EIGENSCHAFT_DATEI = "CamAddonProgrammdatei"  # am Job: wohin sein Programm zuletzt kam
VORSCHAU_SAETZE = 300  # so viele Bewegungssätze zeigt die Vorschau
GELB = "#c4a000"

# Die Gruppen der Einstellungen: (Gruppe, Anker in der Hilfe, Haken und Befehle darin).
GRUPPEN = (
    (
        "programm",
        "programm",
        (
            "kommentare",
            "nur_ascii",
            "satznummern",
            "kopf",
            "kopf_drehmaschine",
            "kopf_drehen",
            "rohteil",
            "rohteil_fraesen",
            "rohteil_drehen",
            "durchmesser_ein",
            "radius_ein",
            "ende",
        ),
    ),
    (
        "wechsel",
        "wechsel",
        (
            "wechsel_fraesen",
            "laenge_ein",
            "wechsel_drehen",
            "laenge_ein_drehen",
            "wechselpunkt",
            "wechselpunkt_mks",
            "wechselpunkt_wks",
            "laenge_wieder",
        ),
    ),
    (
        "spindel",
        "spindel",
        (
            "spindel_ein",
            "spindel_aus",
            "angetrieben_ein",
            "angetrieben_aus",
            "kuehlung",
            "kuehlung_flut",
            "kuehlung_nebel",
            "kuehlung_aus",
        ),
    ),
    ("c_achse", "c_achse", ("c_achse", "c_ein", "c_aus")),
    ("rundachse", "rundachse", ("rundachse_plus", "rundachse_minus")),
    ("vorschub", "vorschub", ("g93", "vorschub_zeit", "vorschub_minute", "vorschub_minute_drehen")),
    ("schwenken", "schwenken", ("schwenkzyklus", "schwenken", "schwenken_aus")),
    ("simultan", "simultan", ("tcpm", "tcpm_ein", "tcpm_aus")),
    (
        "bohren",
        "bohren",
        ("bohren", "bohren_verweilen", "tiefbohren", "spaenebrechen", "reiben"),
    ),
    ("glaetten", "glaetten", ()),
)
# Was nur an der Drehmaschine bzw. nur an der Fräse gilt – sonst nicht gezeigt.
NUR_DREHEN = {
    "rohteil_drehen",
    "durchmesser_ein",
    "radius_ein",
    "kopf_drehmaschine",
    "kopf_drehen",
    "wechsel_drehen",
    "laenge_ein_drehen",
    "angetrieben_ein",
    "angetrieben_aus",
    "vorschub_minute_drehen",
    "c_achse",
    "c_ein",
    "c_aus",
}
NUR_FRAESEN = {
    "rohteil_fraesen",
    "tcpm",
    "tcpm_ein",
    "tcpm_aus",
    "wechsel_fraesen",
    "laenge_ein",
    "vorschub_minute",
    "schwenkzyklus",
    "schwenken",
    "schwenken_aus",
    "bohren",
    "bohren_verweilen",
    "tiefbohren",
    "spaenebrechen",
    "reiben",
}
# Was es im Heidenhain-Klartext nicht gibt (die Satznummern schreibt er immer, die Länge nimmt
# TOOL CALL mit, G93 und die Bohrzyklen übersetzt er selbst; 3+2 dort gerechnet) – nicht gezeigt.
NUR_GCODE = {
    "rohteil",
    "rohteil_fraesen",
    "rohteil_drehen",
    "satznummern",
    "g93",
    "vorschub_zeit",
    "vorschub_minute",
    "vorschub_minute_drehen",
    "laenge_ein",
    "laenge_ein_drehen",
    "laenge_wieder",
    "kopf_drehmaschine",
    "schwenkzyklus",
    "schwenken",
    "schwenken_aus",
    "bohren",
    "bohren_verweilen",
    "tiefbohren",
    "spaenebrechen",
    "reiben",
}
# Befehle, die nur mit ihrem Haken gelten.
HAKEN_VON = {
    "rohteil_fraesen": "rohteil",
    "rohteil_drehen": "rohteil",
    "laenge_wieder": "wechselpunkt",
    "wechselpunkt_mks": "wechselpunkt",
    "wechselpunkt_wks": "wechselpunkt",
    "kuehlung_flut": "kuehlung",
    "kuehlung_nebel": "kuehlung",
    "kuehlung_aus": "kuehlung",
    "c_ein": "c_achse",
    "c_aus": "c_achse",
    "vorschub_zeit": "g93",
    "vorschub_minute": "g93",
    "vorschub_minute_drehen": "g93",
    "schwenken": "schwenkzyklus",
    "schwenken_aus": "schwenkzyklus",
    "tcpm_ein": "tcpm",
    "tcpm_aus": "tcpm",
}


def _fett(widget, fett):
    """Fett, was der Benutzer geändert hat."""
    schrift = widget.font()
    schrift.setBold(bool(fett))
    widget.setFont(schrift)


def gruppen_titel(gruppe):
    return {
        "programm": tr("pp.gruppe.programm"),
        "wechsel": tr("pp.gruppe.wechsel"),
        "spindel": tr("pp.gruppe.spindel"),
        "c_achse": tr("pp.gruppe.c_achse"),
        "rundachse": tr("pp.gruppe.rundachse"),
        "vorschub": tr("pp.gruppe.vorschub"),
        "schwenken": tr("pp.gruppe.schwenken"),
        "simultan": tr("pp.gruppe.simultan"),
        "bohren": tr("pp.gruppe.bohren"),
        "glaetten": tr("pp.gruppe.glaetten"),
    }[gruppe]


def _erklaerung(text, einruecken=False, farbe=None):
    """Ein Satz Erklärung unter einer Einstellung – grau (oder `farbe`), umbrochen."""
    zeile = QtGui.QLabel(text)
    zeile.setWordWrap(True)
    zeile.setStyleSheet(
        f"color: {farbe or GRAU.name()};" + (" margin-left: 22px;" if einruecken else "")
    )
    return zeile


def _parameter():
    return FreeCAD.ParamGet(PARAMETER_PFAD)


def gespeicherte_aenderungen(kennung):
    """{Feld: Wert} – was der Benutzer an dieser Steuerung geändert hat: Befehle (Text), Haken,
    Toleranz und Glätten (pp.gueltige_aenderungen)."""
    try:
        werte = json.loads(_parameter().GetString(f"Steuerung_{kennung}", "") or "{}")
    except ValueError:
        return {}
    return pp.gueltige_aenderungen(werte) if isinstance(werte, dict) else {}


def aenderungen_merken(kennung, aenderungen):
    _parameter().SetString(f"Steuerung_{kennung}", json.dumps(aenderungen, ensure_ascii=False))


def steuerung_des_jobs(job):
    """Die Kennung der Steuerung: am Job gemerkt, sonst die für seine Maschine zuletzt
    gewählte, sonst die zuletzt gewählte, sonst LinuxCNC."""
    kennung = getattr(job, EIGENSCHAFT_STEUERUNG, "") if job is not None else ""
    if kennung in pp.STEUERUNGEN:
        return kennung
    try:
        je_maschine = json.loads(_parameter().GetString("SteuerungJeMaschine", "") or "{}")
    except ValueError:
        je_maschine = {}
    pfad = rw.gemerkte_maschine(job) if job is not None else ""
    kennung = je_maschine.get(os.path.normcase(pfad)) if pfad else None
    if kennung in pp.STEUERUNGEN:
        return kennung
    kennung = _parameter().GetString("SteuerungZuletzt", pp.VORGABE)
    return kennung if kennung in pp.STEUERUNGEN else pp.VORGABE


def datei_vorschlag(job, s):
    """Wohin das Programm kommt: dorthin, wo es für diesen Job zuletzt gespeichert wurde (mit der
    Endung der Steuerung `s`); sonst in den Ordner, in den zuletzt ein Programm für seine
    Maschine kam (etwa die Freigabe der Maschine); sonst neben das Dokument (pp.dateiname)."""
    vorschlag = pp.dateiname(job, s)
    gemerkt = getattr(job, EIGENSCHAFT_DATEI, "") if job is not None else ""
    if gemerkt and os.path.isdir(os.path.dirname(gemerkt)):
        stamm = os.path.splitext(os.path.basename(gemerkt))[0]
        if s.dialekt == "klartext":  # der Name steht im BEGIN/END PGM
            from . import klartext as kt

            stamm = kt.pgm_name(stamm)
        return os.path.join(os.path.dirname(gemerkt), stamm + s.endung)
    pfad = rw.gemerkte_maschine(job) if job is not None else ""
    ordner = _ordner_je_maschine().get(os.path.normcase(pfad)) if pfad else None
    if ordner and os.path.isdir(ordner):
        return os.path.join(ordner, os.path.basename(vorschlag))
    return vorschlag


def datei_merken(job, pfad):
    """Merkt, wohin das Programm des Jobs gespeichert wurde – am Job (ausgeblendete
    Eigenschaft) und den Ordner je Maschine (datei_vorschlag)."""
    if job is None or not pfad:
        return
    if EIGENSCHAFT_DATEI not in job.PropertiesList:
        job.addProperty(
            "App::PropertyString", EIGENSCHAFT_DATEI, "CAM-Addon", tr("pp.eigenschaft.datei")
        )
        job.setEditorMode(EIGENSCHAFT_DATEI, 2)
    if getattr(job, EIGENSCHAFT_DATEI) != pfad:
        setattr(job, EIGENSCHAFT_DATEI, pfad)
    maschine = rw.gemerkte_maschine(job)
    if maschine:
        ordner = _ordner_je_maschine()
        ordner[os.path.normcase(maschine)] = os.path.dirname(pfad)
        _parameter().SetString("ProgrammOrdnerJeMaschine", json.dumps(ordner))


def _ordner_je_maschine():
    try:
        return json.loads(_parameter().GetString("ProgrammOrdnerJeMaschine", "") or "{}")
    except ValueError:
        return {}


def steuerung_merken(job, kennung):
    """Merkt die Steuerung am Job (ausgeblendete Eigenschaft), je Maschine und als letzte."""
    if job is not None:
        if EIGENSCHAFT_STEUERUNG not in job.PropertiesList:
            job.addProperty(
                "App::PropertyString", EIGENSCHAFT_STEUERUNG, "CAM-Addon", tr("pp.eigenschaft")
            )
            job.setEditorMode(EIGENSCHAFT_STEUERUNG, 2)
        if getattr(job, EIGENSCHAFT_STEUERUNG) != kennung:
            setattr(job, EIGENSCHAFT_STEUERUNG, kennung)
        pfad = rw.gemerkte_maschine(job)
        if pfad:
            try:
                je_maschine = json.loads(_parameter().GetString("SteuerungJeMaschine", "") or "{}")
            except ValueError:
                je_maschine = {}
            je_maschine[os.path.normcase(pfad)] = kennung
            _parameter().SetString("SteuerungJeMaschine", json.dumps(je_maschine))
    _parameter().SetString("SteuerungZuletzt", kennung)


class BefehlProgrammSchreiben:
    """Befehl: das NC-Programm eines Jobs mit dem Postprozessor des Addons schreiben."""

    def GetResources(self):
        return {
            "Pixmap": symbol("programm.svg"),
            "MenuText": tr("befehl.programm.titel"),
            "ToolTip": tr("befehl.programm.tooltip"),
        }

    def IsActive(self):
        return True

    def Activated(self):
        from .gui_job_schnittwerte import dokument_mit_job
        from .gui_reichweite import job_fuer

        dokument = dokument_mit_job(tr("pp.titel"), tr("pp.kein_job"))
        if dokument is None:
            return
        jobs = js.jobs(dokument)
        dialog = ProgrammDialog(jobs, job_fuer(jobs))
        dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        dialog.show()


def abschnitte_mit_maschine(job, gewaehlt):
    """pp.abschnitte des Jobs – hat er Ebenen (3+2), mit der gewählten Maschine `gewaehlt`
    ((Name, Pfad, Dokument) aus pp.maschinen_zur_wahl): Ohne Schwenkzyklus rechnet das Programm
    die Rundachsen und Punkte aus ihrer Kette, je Werkzeug mit seiner Länge, wie „Auf der
    Maschine prüfen“. Liegt sie nur in ihrer Datei, wird sie dafür verborgen geöffnet und wieder
    geschlossen. Ohne Maschine mit zwei Rundachsen wie bisher (Tisch A, C um den Nullpunkt)."""
    return _abschnitte_und_kette(job, gewaehlt)[0]


def _rohteil(job):
    """((xmin, ymin, zmin), (xmax, ymax, zmax)) des Rohteils im Job – fürs BLK FORM im Klartext;
    None ohne."""
    try:
        box = job.Stock.Shape.BoundBox
    except AttributeError:
        return None
    if not box.isValid():
        return None
    return (box.XMin, box.YMin, box.ZMin), (box.XMax, box.YMax, box.ZMax)


def _abschnitte_und_kette(job, gewaehlt):
    """(abschnitte_mit_maschine, ohne Kette): ob eine Ebene ohne die Kette einer Maschine mit
    zwei Rundachsen gerechnet ist – dann gilt der gedachte Tisch A, C um den Nullpunkt.
    Operationen mit Werkzeugachse je Satz (Kugelfräser angestellt, Flanke) brauchen die Maschine
    auch – ohne sie sagt das Programm selbst, was es schreibt."""
    from . import schwenken as sw
    from . import simultan_operation as so

    if not (sw.ist_ebene(job) or sw.ebenen_von(job) or so.im_job(job)):
        return pp.abschnitte(job), False
    if gewaehlt is None:
        return pp.abschnitte(job), True
    _name, pfad, dok = gewaehlt
    verborgen = None
    if dok is None:
        try:
            dok = verborgen = FreeCAD.openDocument(pfad, True)
        except Exception:  # nicht lesbar: wie ohne Maschine
            return pp.abschnitte(job), True
    try:
        fuer = _maschine_je_operation(job, dok)
        if fuer is None:
            return pp.abschnitte(job), True
        ohne = []

        def gemerkt(op):
            maschine = fuer(op)
            if maschine is None and not so.ist_simultan(op):
                ohne.append(op)
            return maschine

        return pp.abschnitte(job, gemerkt), bool(ohne)
    finally:
        if verborgen is not None:
            FreeCAD.closeDocument(verborgen.Name)


def _maschine_je_operation(job, dok):
    """Eine Funktion Operation → schwenken.Maschine (je Werkzeugnummer einmal) für die erste
    Maschine im Dokument – None, wenn es keine gibt; die Funktion gibt None, wenn die Maschine
    für das Werkzeug keine Aufnahme oder keine zwei Rundachsen hat."""
    from . import maschine as m
    from . import schwenken as sw
    from .gui_reichweite import _bibliothek

    gefunden = next(
        (
            (o, m.finde_maschine(o))
            for o in dok.Objects
            if o.TypeId == "Assembly::AssemblyObject" and m.finde_maschine(o) is not None
        ),
        None,
    )
    if gefunden is None:
        return None
    try:
        pruefung = rw.Pruefung(*gefunden)
    except Exception as fehler:  # eine kaputte Maschine: wie ohne
        FreeCAD.Console.PrintLog(f"CAM-Addon: Programm: {fehler}\n")
        return None
    bibliothek = _bibliothek()
    nullpunkt = rw.nullpunkt(job)
    je_nummer = {}

    def fuer(op):
        tc = getattr(op, "ToolController", None)
        nummer = int(getattr(tc, "ToolNumber", 0) or 0)
        if nummer not in je_nummer:
            aufnahme = pruefung.werkzeugaufnahme(nummer) if tc is not None else None
            maschine = None
            if aufnahme is not None:
                laenge = rw.einspannung(tc, bibliothek)
                maschine = sw.Maschine(pruefung, aufnahme, laenge, nullpunkt)
                if len(maschine.rundachsen) < 2:
                    maschine = None
            je_nummer[nummer] = maschine
        return je_nummer[nummer]

    return fuer


class ProgrammDialog(QtGui.QDialog):
    """Job, Maschine, Steuerung, Befehle, Vorschau, Datei – und „Speichern“."""

    offen = None  # für die Szenarien

    def __init__(self, jobs, job, eltern=None):
        super().__init__(eltern or FreeCADGui.getMainWindow())
        ProgrammDialog.offen = self
        self.jobs = list(jobs)
        self.job = job
        self.info = pp.Maschineninfo()
        self._maschinen = []  # [(Name, Pfad, Dokument)] – pp.maschinen_zur_wahl()
        self._ungespeichert = False  # die gewählte Maschine liegt in keiner Datei
        self.gespeichert = ""  # die zuletzt gespeicherte Datei – für „Ordner öffnen“
        self._teile = None  # die Abschnitte des Jobs, je gewählter Maschine einmal gerechnet
        self._ohne_kette = False  # eine Ebene ohne die Kette einer 5-Achs-Maschine gerechnet
        self._fuellt = False
        self.haken = {}  # Haken der Einstellungen: Feld → QCheckBox (Szenarien)
        self.felder = {}  # Befehle: Feld → (Name, Eingabe)
        self.glaetten_haken = {}  # Kennung → QCheckBox
        self.feld_toleranz = None
        self.setWindowTitle(tr("pp.titel"))
        self.resize(1180, 840)
        aufbau = QtGui.QVBoxLayout(self)
        aufbau.addWidget(kopfzeile(tr("pp.titel"), "programm"))
        erklaerung = QtGui.QLabel(tr("pp.erklaerung"))
        erklaerung.setWordWrap(True)
        aufbau.addWidget(erklaerung)

        raster = QtGui.QGridLayout()
        self.wahl_job = QtGui.QComboBox()
        for j in self.jobs:
            self.wahl_job.addItem(j.Label)
        self.wahl_job.currentIndexChanged.connect(self._job_gewaehlt)
        raster.addWidget(QtGui.QLabel(tr("pp.job")), 0, 0)
        raster.addWidget(self.wahl_job, 0, 1)
        self.wahl_maschine = QtGui.QComboBox()
        self.wahl_maschine.setToolTip(tr("pp.maschine.wahl.tooltip"))
        self.wahl_maschine.currentIndexChanged.connect(self._maschine_gewaehlt)
        self.maschine_text = QtGui.QLabel()
        self.maschine_text.setWordWrap(True)
        spalte = QtGui.QVBoxLayout()
        spalte.addWidget(self.wahl_maschine)
        spalte.addWidget(self.maschine_text)
        raster.addWidget(QtGui.QLabel(tr("pp.maschine")), 1, 0, QtCore.Qt.AlignTop)
        raster.addLayout(spalte, 1, 1)
        self.wahl_steuerung = QtGui.QComboBox()
        for kennung, s in pp.STEUERUNGEN.items():
            self.wahl_steuerung.addItem(s.name, kennung)
        self.wahl_steuerung.setToolTip(tr("pp.steuerung.tooltip"))
        self.wahl_steuerung.currentIndexChanged.connect(self._steuerung_gewaehlt)
        raster.addWidget(QtGui.QLabel(tr("pp.steuerung")), 2, 0)
        raster.addWidget(self.wahl_steuerung, 2, 1)
        raster.setColumnStretch(1, 1)
        aufbau.addLayout(raster)

        # Links die Einstellungen der Steuerung in Gruppen, rechts die Vorschau.
        teiler = QtGui.QSplitter(QtCore.Qt.Horizontal)
        links = QtGui.QWidget()
        links_aufbau = QtGui.QVBoxLayout(links)
        links_aufbau.setContentsMargins(0, 0, 0, 0)
        self.einstellungen = QtGui.QScrollArea()
        self.einstellungen.setWidgetResizable(True)
        self.einstellungen.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        links_aufbau.addWidget(self.einstellungen, 1)
        self.knopf_zuruecksetzen = knopf(
            tr("pp.zuruecksetzen"), tr("pp.zuruecksetzen.tooltip"), self.zuruecksetzen
        )
        links_aufbau.addWidget(self.knopf_zuruecksetzen, 0, QtCore.Qt.AlignRight)
        teiler.addWidget(links)
        rechts = QtGui.QWidget()
        rechts_aufbau = QtGui.QVBoxLayout(rechts)
        rechts_aufbau.setContentsMargins(0, 0, 0, 0)
        self.hinweise = QtGui.QLabel()
        self.hinweise.setWordWrap(True)
        self.hinweise.setStyleSheet(f"color: {GELB};")
        rechts_aufbau.addWidget(self.hinweise)
        rechts_aufbau.addWidget(QtGui.QLabel(tr("pp.vorschau")))
        self.vorschau = QtGui.QPlainTextEdit()
        self.vorschau.setReadOnly(True)
        schrift = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
        self.vorschau.setFont(schrift)
        self.vorschau.setLineWrapMode(QtGui.QPlainTextEdit.NoWrap)
        rechts_aufbau.addWidget(self.vorschau, 1)
        teiler.addWidget(rechts)
        teiler.setStretchFactor(0, 5)
        teiler.setStretchFactor(1, 6)
        aufbau.addWidget(teiler, 1)

        zeile = QtGui.QHBoxLayout()
        zeile.addWidget(QtGui.QLabel(tr("pp.datei")))
        self.feld_datei = QtGui.QLineEdit()
        # Klartext: der Name im BEGIN/END PGM folgt der Datei – die Vorschau zeigt ihn neu.
        self.feld_datei.editingFinished.connect(self._datei_geaendert)
        zeile.addWidget(self.feld_datei, 1)
        zeile.addWidget(knopf("…", tr("pp.datei.waehlen"), self._datei_waehlen))
        aufbau.addLayout(zeile)
        self.ergebnis = QtGui.QLabel()
        self.ergebnis.setWordWrap(True)
        aufbau.addWidget(self.ergebnis)
        knoepfe = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Close)
        # Nach dem Speichern: der Ordner im Dateimanager – zum Kopieren auf Stick oder Freigabe.
        self.knopf_ordner = knoepfe.addButton(tr("pp.ordner"), QtGui.QDialogButtonBox.ActionRole)
        self.knopf_ordner.setToolTip(tr("pp.ordner.tooltip"))
        self.knopf_ordner.clicked.connect(self.ordner_oeffnen)
        self.knopf_ordner.hide()
        self.knopf_speichern = knoepfe.addButton(
            tr("pp.speichern"), QtGui.QDialogButtonBox.ActionRole
        )
        self.knopf_speichern.setToolTip(tr("pp.speichern.tooltip"))
        self.knopf_speichern.clicked.connect(self.speichern)
        knoepfe.rejected.connect(self.reject)
        aufbau.addWidget(knoepfe)
        ruhiges_mausrad(self)
        self.wahl_job.setCurrentIndex(max(0, self.jobs.index(job) if job in self.jobs else 0))
        self._job_gewaehlt(self.wahl_job.currentIndex())

    # --- Job, Maschine, Steuerung ---------------------------------------------------------

    def _job_gewaehlt(self, index):
        if not 0 <= index < len(self.jobs):
            return
        self.job = self.jobs[index]
        from .gui_reichweite import job_merken

        job_merken(self.job)
        self._fuellt = True
        try:
            self._maschinen_fuellen()
            kennung = steuerung_des_jobs(self.job)
            self.wahl_steuerung.setCurrentIndex(max(0, self.wahl_steuerung.findData(kennung)))
        finally:
            self._fuellt = False
        self._steuerung_gewaehlt()

    def _maschinen_fuellen(self):
        """Die Maschinen zur Wahl – gewählt die, die sich der Job gemerkt hat; hat er keine, die
        erste offene (auch ungespeichert); sonst „keine“."""
        self._maschinen = pp.maschinen_zur_wahl()
        pfad = rw.gemerkte_maschine(self.job)
        gewaehlt = next(
            (k for k, (_n, p, _d) in enumerate(self._maschinen) if msp.gleiche_datei(p, pfad)),
            None,
        )
        if gewaehlt is None and pfad and os.path.isfile(pfad):
            self._maschinen.append((os.path.splitext(os.path.basename(pfad))[0], pfad, None))
            gewaehlt = len(self._maschinen) - 1
        if gewaehlt is None:
            gewaehlt = next(
                (k for k, (_n, _p, d) in enumerate(self._maschinen) if d is not None), None
            )
        self.wahl_maschine.blockSignals(True)
        try:
            self.wahl_maschine.clear()
            self.wahl_maschine.addItem(tr("pp.maschine.keine_wahl"))
            for name, pfad_, dok in self._maschinen:
                if dok is not None and not pfad_:
                    name = f"{name} – {tr('pp.maschine.nicht_gespeichert')}"
                self.wahl_maschine.addItem(name)
            self.wahl_maschine.setCurrentIndex(0 if gewaehlt is None else gewaehlt + 1)
        finally:
            self.wahl_maschine.blockSignals(False)
        self._maschine_gewaehlt()

    def maschine_waehlen(self, name):
        """Wählt die Maschine mit diesem Namen (wie in der Liste, ohne Zusatz) – für die
        Szenarien; gibt zurück, ob es sie gibt."""
        for k, (n, _p, _d) in enumerate(self._maschinen):
            if n == name:
                self.wahl_maschine.setCurrentIndex(k + 1)
                return True
        return False

    def _maschine_gewaehlt(self, *_):
        """Was der Postprozessor von der gewählten Maschine weiß; gewählt mit Datei, merkt sich
        der Job sie (wie beim Prüfen)."""
        k = self.wahl_maschine.currentIndex() - 1
        self._ungespeichert = False
        self._teile = None
        if 0 <= k < len(self._maschinen):
            _name, pfad, dok = self._maschinen[k]
            if dok is not None:
                self.info = pp.maschineninfo_dokument(dok)
            else:
                self.info = pp.maschineninfo_datei(pfad)
            self._ungespeichert = not pfad
            if pfad and not self._fuellt and self.job is not None:
                rw.merke_maschine(self.job, pfad)
        else:
            self.info = pp.Maschineninfo()
        self.maschine_text.setText(self._maschine_beschreiben())
        if not self._fuellt:
            self._einstellungen_bauen()
            self.vorschau_rechnen()

    def _maschine_beschreiben(self):
        i = self.info
        if not i.name:
            return tr("pp.maschine.keine")
        teile = [tr("pp.maschine.drehen") if i.drehmaschine else tr("pp.maschine.fraesen")]
        if i.drehmaschine:
            teile.append(tr("pp.maschine.x_d") if i.x_durchmesser else tr("pp.maschine.x_r"))
        rundachsen = dict(i.rundachsen)
        if i.drehmaschine and (i.hauptspindel_name or "C" in rundachsen):
            teile.append(
                tr(
                    "pp.maschine.hauptspindel",
                    s=i.hauptspindel_name or "–",
                    c=rundachsen.pop("C", "–"),
                )
            )
        for buchstabe, name in sorted(rundachsen.items()):
            teile.append(tr("pp.maschine.rundachse", buchstabe=buchstabe, name=name))
        # Wie die Rundachsen zählen (Manuel, 2026-10-05: „dass die Leute die Möglichkeiten
        # haben, die sie benötigen, um richtig einstellen zu können“).
        nach_din = [n for b, n in sorted(i.rundachsen.items()) if i.nach_din.get(b, True)]
        gegen_din = [n for b, n in sorted(i.rundachsen.items()) if not i.nach_din.get(b, True)]
        if nach_din:
            teile.append(tr("pp.maschine.nach_din", achsen=", ".join(nach_din)))
        if gegen_din:
            teile.append(tr("pp.maschine.gegen_din", achsen=", ".join(gegen_din)))
        if i.angetrieben:
            je_antrieb = {}
            for t, n in sorted(i.angetrieben.items()):
                je_antrieb.setdefault(n, []).append(t)
            plaetze = ", ".join(
                (f"T{t[0]}" if len(t) == 1 else f"T{t[0]}…T{t[-1]}")
                + f" → S{n}"
                + (f" ({i.antrieb_c[n]})" if n in i.antrieb_c else "")
                for n, t in je_antrieb.items()
            )
            teile.append(tr("pp.maschine.angetrieben", plaetze=plaetze))
        if i.wechselpunkt:
            punkt = " ".join(
                f"{b} {(w * 2.0 if b == 'X' and i.drehmaschine and i.x_durchmesser else w):g}"
                for b, w in sorted(i.wechselpunkt.items())
            )
            bezug = "WKS" if i.wechsel_wks else "MKS"
            teile.append(tr("pp.maschine.wechselpunkt", punkt=punkt, bezug=bezug))
        else:
            teile.append(tr("pp.maschine.ohne_wechselpunkt"))
        text = f"{i.name} – " + " · ".join(teile)
        if self._ungespeichert:
            text += "\n" + tr("pp.maschine.ungespeichert")
        return text

    def kennung(self):
        return self.wahl_steuerung.currentData() or pp.VORGABE

    def steuerung(self):
        return pp.steuerung(self.kennung(), gespeicherte_aenderungen(self.kennung()))

    def _steuerung_gewaehlt(self, *_):
        if not self._fuellt:
            steuerung_merken(self.job, self.kennung())
        self._einstellungen_bauen()
        self.feld_datei.setText(datei_vorschlag(self.job, self.steuerung()))
        self.vorschau_rechnen()

    # --- Einstellungen ------------------------------------------------------------------

    def _zeigen(self, feld):
        """Gilt die Einstellung an der gewählten Maschine? Drehmaschine oder Fräse, der
        Wechselpunkt in MKS oder WKS."""
        drehen = self.info.drehmaschine
        if (feld in NUR_DREHEN and not drehen) or (feld in NUR_FRAESEN and drehen):
            return False
        if feld in NUR_GCODE and self.steuerung().dialekt == "klartext":
            return False
        if feld == "wechselpunkt_mks":
            return not self.info.wechsel_wks
        if feld == "wechselpunkt_wks":
            return self.info.wechsel_wks
        return True

    def _einstellungen_bauen(self):
        """Die Einstellungen der gewählten Steuerung, in Gruppen – neu je Steuerung und
        Maschine (nur, was dort gilt)."""
        s = self.steuerung()
        geaendert = gespeicherte_aenderungen(self.kennung())
        self.haken, self.felder, self.glaetten_haken = {}, {}, {}
        self.feld_toleranz = None
        inhalt = QtGui.QWidget()
        aufbau = QtGui.QVBoxLayout(inhalt)
        titel = QtGui.QLabel(f"<b>{tr('pp.einstellungen', steuerung=s.name)}</b>")
        aufbau.addWidget(titel)
        aufbau.addWidget(_erklaerung(tr("pp.einstellungen.erklaerung")))
        for gruppe, anker, felder in GRUPPEN:
            sichtbar = [f for f in felder if self._zeigen(f)]
            if gruppe != "glaetten" and not sichtbar:
                continue
            kasten = QtGui.QFrame()
            kasten.setFrameShape(QtGui.QFrame.StyledPanel)
            kasten_aufbau = QtGui.QVBoxLayout(kasten)
            kasten_aufbau.addWidget(kopfzeile(gruppen_titel(gruppe), "programm", anker))
            if gruppe == "glaetten":
                self._glaetten_bauen(kasten_aufbau, s, geaendert)
            for feld in sichtbar:
                if feld in pp.HAKEN:
                    self._haken_bauen(kasten_aufbau, feld, s, geaendert)
                else:
                    self._feld_bauen(kasten_aufbau, feld, s, geaendert)
            aufbau.addWidget(kasten)
        aufbau.addWidget(_erklaerung(tr("pp.befehle.hinweis")))
        aufbau.addStretch(1)
        self.einstellungen.setWidget(inhalt)
        ruhiges_mausrad(inhalt)
        self._abhaengige_schalten()

    def _haken_bauen(self, aufbau, feld, s, geaendert):
        name, erklaerung = pp.haken_text(feld)
        haken = QtGui.QCheckBox(name)
        haken.setChecked(bool(getattr(s, feld)))
        _fett(haken, feld in geaendert)
        haken.toggled.connect(lambda an, f=feld: self.option_setzen(f, bool(an)))
        aufbau.addWidget(haken)
        aufbau.addWidget(_erklaerung(erklaerung, einruecken=True))
        self.haken[feld] = haken

    def _feld_bauen(self, aufbau, feld, s, geaendert):
        name, erklaerung = pp.feld_text(feld)
        titel = QtGui.QLabel(name)
        _fett(titel, feld in geaendert)
        farbe = None
        if feld in s.vom_hersteller:
            titel.setStyleSheet(f"color: {GELB};")
            erklaerung = f"{erklaerung} {tr('pp.feld.hersteller')}"
            farbe = GELB
        text = getattr(s, feld).replace("\n", " | ")
        schrift = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
        if feld == "wechselpunkt_mks" and s.wechselpunkt_vorschlaege:
            # Zur Wahl, was die Steuerung dafür hat (Siemens: SUPA, F_HOME, G75), frei änderbar.
            eingabe = QtGui.QComboBox()
            eingabe.setEditable(True)
            eingabe.addItems(list(s.wechselpunkt_vorschlaege))
            eingabe.setEditText(text)
            eingabe.lineEdit().setFont(schrift)
            eingabe.activated.connect(
                lambda _i, f=feld, e=eingabe: self._eingabe_fertig(f, e.currentText())
            )
            eingabe.lineEdit().editingFinished.connect(
                lambda f=feld, e=eingabe: self._eingabe_fertig(f, e.currentText())
            )
        else:
            eingabe = QtGui.QLineEdit(text)
            eingabe.setFont(schrift)
            eingabe.editingFinished.connect(
                lambda f=feld, e=eingabe: self._eingabe_fertig(f, e.text())
            )
        eingabe.setToolTip(erklaerung)
        aufbau.addWidget(titel)
        aufbau.addWidget(eingabe)
        aufbau.addWidget(_erklaerung(erklaerung, farbe=farbe))
        self.felder[feld] = (titel, eingabe)

    def _glaetten_bauen(self, aufbau, s, geaendert):
        if not s.glaetten_angebot:
            aufbau.addWidget(_erklaerung(tr("pp.glaetten.keine")))
            return
        an = {g.kennung for g in s.glaetten_an()}
        for g in s.glaetten_angebot:
            name, erklaerung = pp.glaetten_text(s.kennung, g.kennung)
            haken = QtGui.QCheckBox(name)
            haken.setChecked(g.kennung in an)
            _fett(haken, "glaetten" in geaendert and (g.kennung in an) != g.an)
            haken.toggled.connect(lambda _an: self._glaetten_umgeschaltet())
            aufbau.addWidget(haken)
            aufbau.addWidget(_erklaerung(erklaerung, einruecken=True))
            if g.option:
                aufbau.addWidget(_erklaerung(tr("pp.option.erklaerung"), True, GELB))
            self.glaetten_haken[g.kennung] = haken
        if any("{toleranz}" in g.befehl for g in s.glaetten_angebot):
            zeile = QtGui.QHBoxLayout()
            beschriftung = QtGui.QLabel(tr("pp.glaetten.toleranz"))
            _fett(beschriftung, "toleranz" in geaendert)
            zeile.addWidget(beschriftung)
            feld = QtGui.QDoubleSpinBox()
            feld.setLocale(zahlenformat())
            feld.setDecimals(3)
            feld.setRange(*pp.TOLERANZ_BEREICH)
            feld.setSingleStep(0.005)
            feld.setSuffix(" mm")
            feld.setValue(s.toleranz)
            feld.valueChanged.connect(lambda wert: self.option_setzen("toleranz", float(wert)))
            zeile.addWidget(feld)
            zeile.addStretch(1)
            aufbau.addLayout(zeile)
            aufbau.addWidget(_erklaerung(tr("pp.glaetten.toleranz.erklaerung")))
            self.feld_toleranz = feld

    def _abhaengige_schalten(self):
        """Befehle, deren Haken aus ist, sind grau – sie stehen dann nicht im Programm."""
        for feld, (titel, eingabe) in self.felder.items():
            haken = self.haken.get(HAKEN_VON.get(feld))
            an = haken is None or haken.isChecked()
            titel.setEnabled(an)
            eingabe.setEnabled(an)

    def _eingabe_fertig(self, feld, text):
        text = text.replace(" | ", "\n")
        if text != getattr(self.steuerung(), feld):
            self.befehl_setzen(feld, text)

    def _glaetten_umgeschaltet(self):
        self.option_setzen(
            "glaetten", [k for k, haken in self.glaetten_haken.items() if haken.isChecked()]
        )

    def befehl_setzen(self, feld, text):
        """Ändert einen Befehl der gewählten Steuerung (gemerkt je Steuerung)."""
        self.option_setzen(feld, text)
        if feld in self.felder:
            titel, eingabe = self.felder[feld]
            _fett(titel, feld in gespeicherte_aenderungen(self.kennung()))
            gezeigt = getattr(self.steuerung(), feld).replace("\n", " | ")
            if isinstance(eingabe, QtGui.QComboBox):
                eingabe.setEditText(gezeigt)
            elif eingabe.text() != gezeigt:
                eingabe.setText(gezeigt)

    def option_setzen(self, feld, wert):
        """Ändert eine Einstellung der gewählten Steuerung – Befehl, Haken, Toleranz oder die
        Liste der Befehle zum Glätten; gleich wie vorbelegt: nicht gemerkt."""
        vorgabe_s = pp.STEUERUNGEN[self.kennung()]
        if feld == "glaetten":
            vorgabe = [g.kennung for g in vorgabe_s.glaetten_angebot if g.an]
            gleich = sorted(wert) == sorted(vorgabe)
        elif feld == "toleranz":
            gleich = abs(float(wert) - vorgabe_s.toleranz) < 1e-9
        else:
            gleich = wert == getattr(vorgabe_s, feld)
        aenderungen = gespeicherte_aenderungen(self.kennung())
        if gleich:
            aenderungen.pop(feld, None)
        else:
            aenderungen[feld] = list(wert) if feld == "glaetten" else wert
        aenderungen_merken(self.kennung(), aenderungen)
        if feld in self.haken:
            _fett(self.haken[feld], not gleich)
        self._abhaengige_schalten()
        self.vorschau_rechnen()

    def zuruecksetzen(self):
        """Alle Einstellungen der gewählten Steuerung wie vorbelegt."""
        aenderungen_merken(self.kennung(), {})
        self._einstellungen_bauen()
        self.vorschau_rechnen()

    # --- Vorschau und Speichern ---------------------------------------------------------

    def _programm(self, vorschau=None):
        if self._teile is None:
            k = self.wahl_maschine.currentIndex() - 1
            gewaehlt = self._maschinen[k] if 0 <= k < len(self._maschinen) else None
            self._teile, self._ohne_kette = _abschnitte_und_kette(self.job, gewaehlt)
        s = self.steuerung()
        programm = pp.programm(
            self._teile,
            s,
            self.info,
            self.job.Label,
            vorschau,
            datei=self.feld_datei.text().strip(),
            rohteil=_rohteil(self.job),
        )
        if self._ohne_kette and not (s.schwenkzyklus and s.schwenken):
            # Sonst stillschweigend: der gedachte Tisch A, C um den Nullpunkt (schwenken).
            programm.hinweise.append(tr("pp.hinweis.ebene_ohne_kette"))
        return programm

    def vorschau_rechnen(self):
        if self.job is None:
            return
        programm = self._programm(VORSCHAU_SAETZE)
        self.vorschau.setPlainText(programm.text)
        self.hinweise.setText("\n".join(programm.hinweise))
        self.hinweise.setVisible(bool(programm.hinweise))
        self.ergebnis.setText("")

    def _datei_waehlen(self):
        s = self.steuerung()
        pfad, _filter = QtGui.QFileDialog.getSaveFileName(
            self, tr("pp.datei.waehlen"), self.feld_datei.text(), f"*{s.endung};;*"
        )
        if pfad:
            self.feld_datei.setText(pfad)
            self._datei_geaendert()

    def _datei_geaendert(self):
        if self.job is not None and self.steuerung().dialekt == "klartext":
            self.vorschau_rechnen()

    def speichern(self):
        """Schreibt das ganze Programm in die Datei; gibt den Pfad zurück (None, wenn es nicht
        ging – der Grund steht im Fenster)."""
        pfad = self.feld_datei.text().strip()
        if not pfad:
            self._datei_waehlen()
            pfad = self.feld_datei.text().strip()
            if not pfad:
                return None
        programm = self._programm()
        try:
            with open(pfad, "w", encoding="utf-8", newline="\n") as datei:
                datei.write(programm.text)
        except OSError as fehler:
            self.ergebnis.setText(tr("pp.fehler.speichern", fehler=str(fehler)))
            self.ergebnis.setStyleSheet("color: #cc0000;")
            return None
        steuerung_merken(self.job, self.kennung())
        datei_merken(self.job, pfad)
        self.gespeichert = pfad
        self.knopf_ordner.show()
        # Nachgelesen, wie die Steuerung es läse: Werkzeuglänge, Spindel, Vorschub, Kreise.
        befunde, saetze = pp.nachlesen(programm, self.steuerung(), self.info)
        self.ergebnis.setStyleSheet("color: #cc0000;" if befunde else "")
        self.ergebnis.setText(
            tr("pp.gespeichert", datei=pfad, saetze=programm.saetze, zeilen=len(programm.zeilen))
            + "\n"
            + pp.nachgelesen_text(befunde, saetze)
            + "".join("\n" + x for x in [pp.groesse_text(programm, self.steuerung())] if x)
        )
        return pfad

    def ordner_oeffnen(self):
        """Der Ordner der zuletzt gespeicherten Datei im Dateimanager des Systems."""
        ordner = os.path.dirname(self.gespeichert or self.feld_datei.text().strip())
        if ordner and os.path.isdir(ordner):
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(ordner))

    def done(self, ergebnis):
        ProgrammDialog.offen = None
        super().done(ergebnis)
