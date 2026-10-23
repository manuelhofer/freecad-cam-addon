# SPDX-License-Identifier: LGPL-2.1-or-later
"""Befehl „Fertigteil als Rohteil“ (W-029): das Teil nach allen Operationen eines Jobs als Körper –
im Dokument dort, wo das Teil liegt, und als eigene Datei im Ordner des Dokuments. In der
nächsten Aufspannung nimmt „Bearbeitung“ ihn als Rohteil („Teil aus dem Dokument“).

Den Körper rechnet ein Nebenrechner (fertigteil.koerper_rechnen, am Testteil 3,5 s) – das Fenster
zeichnet sich dabei weiter; ohne Nebenrechner rechnet es hier.
"""

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

from . import fertigteil as ft
from . import symbol
from . import vierachs_rohteil as vr
from .gui_einrichtblatt import _gewaehlter_job
from .gui_zahlen import dezimal
from .sprache import tr

FARBE = (0.55, 0.75, 0.45)  # hellgrün, durchscheinend: das Teil liegt darin
DURCHSCHEINEND = 70  # %


def _job_waehlen():
    """Der gewählte Job, sonst der einzige; bei mehreren gefragt. None: keiner (gesagt) oder
    abgebrochen."""
    job = _gewaehlter_job()
    if job is not None:
        return job
    dokument = FreeCAD.ActiveDocument
    jobs = [o for o in (dokument.Objects if dokument else []) if hasattr(o, "Operations")]
    if len(jobs) > 1:
        name, ok = QtGui.QInputDialog.getItem(
            FreeCADGui.getMainWindow(),
            tr("befehl.fertigteil.titel"),
            tr("ft.job_waehlen"),
            [j.Label for j in jobs],
            0,
            False,
        )
        return next((j for j in jobs if j.Label == name), None) if ok else None
    _meldung(tr("ft.kein_job"), bearbeitung=True)
    return None


def _meldung(text, bearbeitung=False, warnung=False):
    """Eine Meldung; `bearbeitung`: Fehlt erst ein Job oder eine Operation, bietet sie
    „Bearbeitung“ gleich als Knopf an."""
    kasten = QtGui.QMessageBox(FreeCADGui.getMainWindow())
    kasten.setWindowTitle(tr("befehl.fertigteil.titel"))
    kasten.setIcon(QtGui.QMessageBox.Warning if warnung else QtGui.QMessageBox.Information)
    kasten.setText(text)
    knopf = None
    if bearbeitung:
        knopf = kasten.addButton(tr("befehl.bearbeitung.titel"), QtGui.QMessageBox.AcceptRole)
    kasten.addButton(QtGui.QMessageBox.Close if bearbeitung else QtGui.QMessageBox.Ok)
    kasten.exec()
    if knopf is not None and kasten.clickedButton() is knopf:
        FreeCADGui.runCommand("CamAddon_Bearbeitung")


def _im_hintergrund(x, y, h, unten, teil, anfang, rohteil):
    """(Körper, Zellen im Teil: ft.im_teil) vom Nebenrechner – None ohne Nebenrechner oder wenn
    er scheiterte (dann rechnet der Aufrufer hier, mit der Meldung von hier). ValueError mit dem
    Satz des Nebenrechners."""
    from . import nebenrechner as nr

    pool = nr.pool()
    if not pool.verfuegbar():
        return None
    try:
        auftrag = pool.auftrag(
            "fertigteil", "koerper_rechnen", x, y, h, unten, nr.Form.von(teil), anfang,
            nr.Form.von(rohteil),
        )  # fmt: skip
        ((form, zellen),) = pool.warten([auftrag], zwischendurch=nr.ereignisse_ohne_eingaben)
    except nr.NichtVerfuegbar:
        return None
    except nr.Fehler as fehler:
        if fehler.art == "ValueError":
            raise ValueError(fehler.satz or str(fehler)) from fehler
        return None
    return form.form(), zellen


def fertigteil_anlegen(job, speichern=True):
    """Rechnet das Fertigteil des Jobs, legt es ins Dokument (eine Transaktion) und speichert es
    als eigene Datei – (Objekt, Pfad oder None, Raster in mm, Fläche in mm², auf der die Bahnen
    ins Teil schneiden: ft.im_teil). ValueError mit einem Satz, wenn es keins gibt."""
    stand = ft.stand_des_jobs(job)
    q = stand.quader
    h = ft.hoehen(job, stand)
    teil = vr.modell(job).Shape  # in den Koordinaten des Jobs, wie das Raster
    rohteil = job.Stock.Shape  # wie das Teil in den Koordinaten des Jobs
    anfang = ft.anfang_des_jobs(job)
    gerechnet = _im_hintergrund(q.x, q.y, h, q.z_von, teil, anfang, rohteil)
    if gerechnet is None:
        gerechnet = (
            ft.koerper_aus_hoehen(q.x, q.y, h, q.z_von, teil, rohteil),
            ft.im_teil(q.x, q.y, h, teil, anfang),
        )
    form, zellen = gerechnet
    dokument = job.Document
    dokument.openTransaction(tr("befehl.fertigteil.titel"))
    try:
        objekt = ft.anlegen(job, form)
        dokument.recompute()
    except Exception:
        dokument.abortTransaction()
        raise
    dokument.commitTransaction()
    ansicht = getattr(objekt, "ViewObject", None)
    if ansicht is not None:
        ansicht.ShapeColor = FARBE
        ansicht.Transparency = DURCHSCHEINEND
    pfad = ft.datei_speichern(objekt) if speichern else None
    return objekt, pfad, stand.schritt, zellen * stand.schritt**2


class BefehlFertigteil:
    """Befehl im Menü: das Fertigteil des gewählten Jobs als Rohteil der nächsten Aufspannung."""

    def GetResources(self):
        return {
            "Pixmap": symbol("fertigteil.svg"),
            "MenuText": tr("befehl.fertigteil.titel"),
            "ToolTip": tr("befehl.fertigteil.tooltip"),
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        job = _job_waehlen()
        if job is None:
            return
        fenster = FreeCADGui.getMainWindow()
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        fenster.statusBar().showMessage(tr("ft.rechnet", job=job.Label))
        try:
            objekt, pfad, schritt, ins_teil = fertigteil_anlegen(job)
        except (ValueError, RuntimeError) as fehler:
            QtGui.QApplication.restoreOverrideCursor()
            fenster.statusBar().clearMessage()
            ohne = not list(job.Operations.Group or [])
            _meldung(str(fehler), bearbeitung=ohne, warnung=not ohne)
            return
        QtGui.QApplication.restoreOverrideCursor()
        fenster.statusBar().clearMessage()
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(objekt)
        text = tr("ft.fertig", name=objekt.Label, schritt=dezimal(f"{schritt:g}"))
        text += "\n\n" + (tr("ft.datei", pfad=pfad) if pfad else tr("ft.ohne_datei"))
        text += "\n\n" + tr("ft.weiter", name=objekt.Label)
        if ins_teil > 0:
            text = tr("ft.ins_teil", flaeche=dezimal(f"{ins_teil:.0f}")) + "\n\n" + text
        _meldung(text, warnung=ins_teil > 0)
