# SPDX-License-Identifier: LGPL-2.1-or-later
"""Befehl „Fertigteil als Rohteil“ (W-029): das Teil nach allen Operationen eines Jobs als Körper –
im Dokument dort, wo das Teil liegt, und als eigene Datei im Ordner des Dokuments. In der
nächsten Aufspannung nimmt „Bearbeitung“ ihn als Rohteil („Teil aus dem Dokument“).

Den Körper rechnet ein Nebenrechner (fertigteil.koerper_rechnen, am Testteil 3,5 s) – das Fenster
zeichnet sich dabei weiter; ohne Nebenrechner rechnet es hier. Für die Stange (4 Achsen) rechnet
erst „Auf der Maschine prüfen“ den Abtrag: Dort am Ende der Knopf „Fertigteil als Rohteil …“
(fertigteil.radien_rechnen); der Befehl im Menü verweist für einen solchen Job dorthin.
"""

import math

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


def _meldung(text, bearbeitung=False, warnung=False, speichern=None, pruefen=None):
    """Eine Meldung; `bearbeitung`: Fehlt erst ein Job oder eine Operation, bietet sie
    „Bearbeitung“ gleich als Knopf an; `speichern` (das Fertigteil): Fehlt die eigene Datei, weil
    das Dokument nie gespeichert wurde, „Dokument speichern …“ (_speichern_und_datei; Manuel: der
    nächste Schritt als Knopf)."""
    kasten = QtGui.QMessageBox(FreeCADGui.getMainWindow())
    kasten.setWindowTitle(tr("befehl.fertigteil.titel"))
    kasten.setIcon(QtGui.QMessageBox.Warning if warnung else QtGui.QMessageBox.Information)
    kasten.setText(text)
    knopf = sichern = zum_pruefen = None
    if pruefen is not None:
        zum_pruefen = kasten.addButton(tr("befehl.reichweite.titel"), QtGui.QMessageBox.AcceptRole)
    if bearbeitung:
        knopf = kasten.addButton(tr("befehl.bearbeitung.titel"), QtGui.QMessageBox.AcceptRole)
    if speichern is not None:
        sichern = kasten.addButton(tr("ft.speichern"), QtGui.QMessageBox.AcceptRole)
    mit_knopf = bearbeitung or speichern is not None or pruefen is not None
    kasten.addButton(QtGui.QMessageBox.Close if mit_knopf else QtGui.QMessageBox.Ok)
    kasten.exec()
    if zum_pruefen is not None and kasten.clickedButton() is zum_pruefen:
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(pruefen)
        QtCore.QTimer.singleShot(0, lambda: FreeCADGui.runCommand("CamAddon_AufMaschinePruefen"))
    if knopf is not None and kasten.clickedButton() is knopf:
        FreeCADGui.runCommand("CamAddon_Bearbeitung")
    if sichern is not None and kasten.clickedButton() is sichern:
        _speichern_und_datei(speichern)


def _speichern_und_datei(objekt):
    """„Dokument speichern …“: fragt nach dem Ort, speichert das Dokument dort und dann die eigene
    Datei des Fertigteils daneben (ft.datei_speichern) – und sagt, wo sie liegt."""
    fenster = FreeCADGui.getMainWindow()
    dokument = objekt.Document
    vorschlag = (dokument.Label or "Dokument") + ".FCStd"
    pfad, _filter = QtGui.QFileDialog.getSaveFileName(
        fenster, tr("ft.speichern"), vorschlag, "FreeCAD (*.FCStd)"
    )
    if not pfad:
        return
    if not pfad.lower().endswith(".fcstd"):
        pfad += ".FCStd"
    dokument.saveAs(pfad)
    datei = ft.datei_speichern(objekt)
    QtGui.QMessageBox.information(
        fenster, tr("befehl.fertigteil.titel"), tr("ft.datei", pfad=datei or "")
    )


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


def _stange_im_hintergrund(a, phi, r, laengs, radial, teil, teil_r, rohteil):
    """(Körper, Fläche ins Teil in mm²) der Stange vom Nebenrechner – None ohne Nebenrechner oder
    wenn er scheiterte (dann rechnet der Aufrufer hier)."""
    from . import nebenrechner as nr

    pool = nr.pool()
    if not pool.verfuegbar():
        return None
    try:
        auftrag = pool.auftrag(
            "fertigteil", "radien_rechnen", a, phi, r, laengs, radial, nr.Form.von(teil), teil_r,
            nr.Form.von(rohteil),
        )  # fmt: skip
        ((form, flaeche),) = pool.warten([auftrag], zwischendurch=nr.ereignisse_ohne_eingaben)
    except nr.NichtVerfuegbar:
        return None
    except nr.Fehler as fehler:
        if fehler.art == "ValueError":
            raise ValueError(fehler.satz or str(fehler)) from fehler
        return None
    return form.form(), flaeche


def _raum_im_hintergrund(grenzen, x, y, z_von, z_bis, schritt, teil_grenzen, teil, rohteil):
    """(Körper, Fläche ins Teil in mm²) aus dem räumlichen Rest vom Nebenrechner – None ohne
    Nebenrechner oder wenn er scheiterte (dann rechnet der Aufrufer hier)."""
    from . import nebenrechner as nr

    pool = nr.pool()
    if not pool.verfuegbar():
        return None
    try:
        auftrag = pool.auftrag(
            "fertigteil", "abschnitte_rechnen", grenzen, x, y, z_von, z_bis, schritt,
            teil_grenzen, nr.Form.von(teil), nr.Form.von(rohteil),
        )  # fmt: skip
        ((form, flaeche),) = pool.warten([auftrag], zwischendurch=nr.ereignisse_ohne_eingaben)
    except nr.NichtVerfuegbar:
        return None
    except nr.Fehler as fehler:
        if fehler.art == "ValueError":
            raise ValueError(fehler.satz or str(fehler)) from fehler
        return None
    return form.form(), flaeche


def _ablegen(job, form, speichern):
    """Legt den Körper als Fertigteil ins Dokument (eine Transaktion), färbt ihn und speichert die
    eigene Datei – (Objekt, Pfad oder None)."""
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
    return objekt, (ft.datei_speichern(objekt) if speichern else None)


def fertigteil_aus_stange(job, abtrag, speichern=True):
    """Das Fertigteil eines Jobs an der Stange aus ihrem Abtrag im Prüffenster
    (restmaterial.Abtrag, am Ende): (Objekt, Pfad oder None, Raster als Text, Fläche ins Teil)."""
    if abtrag._teil is None:
        abtrag.vergleich()  # die Radien des Teils auf den Strahlen
    teil_r = abtrag._teil[1]
    stange = abtrag.stange
    laengs = tuple(float(c) for c in abtrag.laengs)
    radial = tuple(float(c) for c in abtrag.radial)
    teil = vr.modell(job).Shape
    rohteil = job.Stock.Shape
    # An der Rückseite des Teils abgestochen gedacht: Was davor im Futter steckt, gehört nicht zum
    # Rohteil der nächsten Aufspannung (die Stange war am Prüfteil 107 lang, die Welle 40).
    von = ft.erste_stelle(stange.a, teil, laengs)
    werte = (
        stange.a[von:],
        stange.phi,
        stange.r[von:].copy(),
        laengs,
        radial,
        teil,
        teil_r[von:],
        rohteil,
    )
    gerechnet = _stange_im_hintergrund(*werte)
    if gerechnet is None:
        gerechnet = ft.koerper_aus_radien(*werte), ft.im_teil_radien(*werte[:3], teil_r)
    form, flaeche = gerechnet
    objekt, pfad = _ablegen(job, form, speichern)
    schritt_a = float(stange.a[1] - stange.a[0]) if len(stange.a) > 1 else 0.0
    grad = math.degrees(float(stange.phi[1] - stange.phi[0])) if len(stange.phi) > 1 else 0.0
    raster = tr(
        "ft.raster_stange", schritt=dezimal(f"{schritt_a:g}"), grad=dezimal(f"{round(grad, 2):g}")
    )
    return objekt, pfad, raster, flaeche


def _ist_raum(job):
    """Gehört der Job zu einer Aufspannung mit Ebenen (3+2) – der Grundjob oder eine Ebene?"""
    from . import raum_material as raum

    return bool(raum.folge_der_aufspannung(job))


def fertigteil_raum(job, speichern=True):
    """Das Fertigteil einer Aufspannung mit Ebenen (3+2) aus dem räumlichen Rest nach allen Ebenen
    (raum_material.nach_allen) – auf den Grundjob: (Objekt, Pfad oder None, Raster als Text,
    Fläche ins Teil). ValueError, wenn sich der Rest nicht sicher nachrechnen lässt."""
    from . import materialstand as mst
    from . import raum_material as raum

    grundjob = raum.folge_der_aufspannung(job)[0]
    material = raum.nach_allen(grundjob, mst.SCHRITT)
    if material is None:
        raise ValueError(tr("ft.fehler.raum"))
    teil = vr.modell(grundjob).Shape  # in den Koordinaten des Grundjobs, wie der Rest
    rohteil = grundjob.Stock.Shape
    werte = (
        material.grenzen,
        material.x,
        material.y,
        material.z_von,
        material.z_bis,
        material.schritt,
        raum.abschnitte(teil, material),
        teil,
        rohteil,
    )
    gerechnet = _raum_im_hintergrund(*werte)
    if gerechnet is None:
        gerechnet = ft.koerper_aus_abschnitten(*werte)
    form, flaeche = gerechnet
    objekt, pfad = _ablegen(grundjob, form, speichern)
    raster = tr("ft.raster_raum", schritt=dezimal(f"{round(material.schritt, 3):g}"))
    return objekt, pfad, raster, flaeche


def _ist_stange(job):
    """Fräst der Job rundum an der Stange (eine Operation dreht die Rundachse)?"""
    from . import vierachs_operation as vo

    return any(vo.ist_rundum(op) for op in (job.Operations.Group or []))


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
    objekt, pfad = _ablegen(job, form, speichern)
    return objekt, pfad, stand.schritt, zellen * stand.schritt**2


def ausfuehren(job, abtrag=None):
    """Das Fertigteil des Jobs rechnen, ablegen und melden – aus dem Abtrag der Stange
    (`abtrag`, aus dem Prüffenster), sonst aus dem Materialstand. Ein Job an der Stange ohne
    Abtrag: der Verweis aufs Prüffenster, als Knopf."""
    if abtrag is None and _ist_stange(job):
        _meldung(tr("ft.stange_pruefen"), pruefen=job)
        return
    QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
    statuszeile = FreeCADGui.getMainWindow().statusBar()
    statuszeile.showMessage(tr("ft.rechnet", job=job.Label))
    try:
        if abtrag is not None:
            objekt, pfad, raster, ins_teil = fertigteil_aus_stange(job, abtrag)
        elif _ist_raum(job):
            objekt, pfad, raster, ins_teil = fertigteil_raum(job)
        else:
            objekt, pfad, schritt, ins_teil = fertigteil_anlegen(job)
            raster = tr("ft.raster", schritt=dezimal(f"{schritt:g}"))
    except (ValueError, RuntimeError) as fehler:
        QtGui.QApplication.restoreOverrideCursor()
        statuszeile.clearMessage()
        ohne = not list(job.Operations.Group or [])
        _meldung(str(fehler), bearbeitung=ohne, warnung=not ohne)
        return
    QtGui.QApplication.restoreOverrideCursor()
    statuszeile.clearMessage()
    FreeCADGui.Selection.clearSelection()
    FreeCADGui.Selection.addSelection(objekt)
    text = tr("ft.fertig", name=objekt.Label, raster=raster)
    text += "\n\n" + (tr("ft.datei", pfad=pfad) if pfad else tr("ft.ohne_datei"))
    text += "\n\n" + tr("ft.weiter", name=objekt.Label)
    if ins_teil > 0:
        text = tr("ft.ins_teil", flaeche=dezimal(f"{ins_teil:.0f}")) + "\n\n" + text
    _meldung(text, warnung=ins_teil > 0, speichern=None if pfad else objekt)


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
        ausfuehren(job)
