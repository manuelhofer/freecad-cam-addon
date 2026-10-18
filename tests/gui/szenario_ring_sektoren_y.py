# Manuels Ring auf der Beispiel-Drehmaschine mit Y (W-026, P-2026-10-17-48; Manuel: „segmente, wo
# die y achse hinkommt … man kann die c achse sperren“): „Rundum schruppen“ mit der Querachse und
# „Sektoren in Zeilen mit Y – C steht“, darunter angehakt „Schlitze in Wellen von außen“ (Manuel,
# 2026-10-18: „Wellen, als Haken vorbelegt“), T1 Schaftfräser Ø 4 im Halter „VDI30 angetrieben
# radial“, ap 3, ae 1. „Anlegen“ → die Operation fährt in den Schlitzen bei stehendem C mit Y, dort
# in Bögen (Sätze mit stehendem C, deren Versatz quer hin und her läuft, ohne Eilgang dazwischen). „Auf der
# Maschine prüfen“: „Alle Achsen bleiben in ihren Grenzen.“, „Kollision prüfen“ → „Nichts berührt
# sich“ – der echte Halter gegen die Segmente –, der Abspieler am Ende „nirgends ins Teil“.
# ZEITLIMIT: 900
import os
import shutil
import tempfile

import FreeCAD
import FreeCADGui as Gui
from PySide import QtCore, QtGui

ADDON = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine, gui_reichweite, gui_vierachs
    from camaddon import vierachs_operation as vo
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    bibliothek = wz.Bibliothek()
    halter = bibliothek.neuer_halter("vdi30_radial")
    t1 = bibliothek.neues_werkzeug()
    t1.nummer, t1.name, t1.durchmesser, t1.schneiden = 1, "VHM 4", 4.0, 3
    t1.schneidenlaenge, t1.laenge_spindelnase, t1.halter = 12.0, 110.0, halter.kennung
    t1.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=1.0, ap=3, vc=120, fz=0.03)]
    bibliothek.speichern()

    asm, _maschine = beispielmaschine.lade(beispielmaschine.DREHMASCHINE)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    yield 300

    ordner = tempfile.mkdtemp()
    datei = os.path.join(ordner, "ring.FCStd")
    shutil.copy(os.path.join(ADDON, "beispiele", "ring_4achs_planbearbeitung.FCStd"), datei)
    doc = FreeCAD.openDocument(datei)
    teil = doc.getObject("Body")
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    stirn = max(
        (
            (f.Area, f"Face{i + 1}")
            for i, f in enumerate(teil.Shape.Faces)
            if vr.ist_eben(f) and (vr.aussennormale(f) - FreeCAD.Vector(0, 0, 1)).Length < 1e-9
        ),
    )[1]
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, stirn)
    yield 500

    Gui.runCommand("CamAddon_Vierachs")
    yield 1500
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 3000)
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    panel.knopf_weiter.click()
    yield 300
    h.pruefe(panel.seite == 2, f"Seite {panel.seite}")
    if panel.mit_schlichten.isChecked():
        panel.mit_schlichten.setChecked(False)
    h.pruefe(
        panel.schruppen_querachse.isChecked() and panel.schruppen_sektoren_y.isChecked(),
        "Querachse oder „Sektoren in Zeilen mit Y“ nicht angehakt",
    )
    yield 500
    yield from h.warte_auf(lambda: not panel.rechnet_noch(), 180000)
    yield from h.warte_auf(lambda: panel.vorschau is not None, 30000)
    h.pruefe(not panel.hinweis_bearbeitung.text(), f"rot: {panel.hinweis_bearbeitung.text()!r}")
    job = panel.job
    yield from h.warte_auf(lambda: panel.knopf_fertig.isEnabled(), 3000)
    panel.knopf_fertig.click()
    yield 2000
    h.pruefe(gui_vierachs.VierachsPanel.offen is None, "Fenster nach „Anlegen“ offen")
    ops = [o for o in job.Operations.Group if vo.ist_rundum(o)]
    h.pruefe([o.Label for o in ops] == ["Rundum schruppen T1"], f"Operationen: {ops}")
    if not ops:
        return
    op = ops[0]
    h.pruefe(bool(op.Querachse) and bool(op.SektorenY), "Querachse/SektorenY an der Operation")
    h.pruefe(
        bool(getattr(op, "SektorWellen", False)), "„Schlitze in Wellen“ nicht an der Operation"
    )
    stehend = 0
    c_vorher = y_vorher = None
    for befehl in op.Path.Commands:
        werte = befehl.Parameters
        c, y = werte.get("C", c_vorher), werte.get("Y", y_vorher)
        if befehl.Name == "G1" and c == c_vorher and y is not None and y != y_vorher:
            stehend += 1
        c_vorher, y_vorher = c, y
    # Wellen: bei stehendem C wechselt Y die Richtung, ohne dass ein Eilgang dazwischen liegt.
    wenden = 0
    c_vorher = y_vorher = dy_vorher = None
    for befehl in op.Path.Commands:
        werte = befehl.Parameters
        c, y = werte.get("C", c_vorher), werte.get("Y", y_vorher)
        if befehl.Name == "G1" and c == c_vorher and y is not None and y_vorher is not None:
            dy = y - y_vorher
            if dy_vorher is not None and abs(dy) > 1e-6 and dy * dy_vorher < 0:
                wenden += 1
            if abs(dy) > 1e-6:
                dy_vorher = dy
        elif befehl.Name == "G0":
            dy_vorher = None
        c_vorher, y_vorher = c, y
    h.pruefe(wenden > 50, f"{wenden} Wenden in Y bei stehendem C – fahren die Schlitze in Wellen?")
    h.pruefe(stehend > 50, f"{stehend} Sätze mit Y bei stehendem C")

    # --- Auf der Maschine prüfen, Kollision, Abspieler ----------------------------------------
    FreeCAD.setActiveDocument(doc.Name)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
    # Im Ring-Beispiel ist auch eine 3-Achs-Fräse offen: Das Addon fragt, auf welcher – die
    # Drehmaschine.
    yield from h.warte_auf(
        lambda: gui_reichweite.PruefPanel.offen is not None
        or isinstance(h.modal(), QtGui.QInputDialog),
        120000,
    )
    frage = h.modal()
    if isinstance(frage, QtGui.QInputDialog):
        drehmaschine = [e for e in frage.comboBoxItems() if "Drehmaschine" in e]
        h.pruefe(bool(drehmaschine), f"Maschinenwahl ohne Drehmaschine: {frage.comboBoxItems()}")
        if drehmaschine:
            frage.setTextValue(drehmaschine[0])
        frage.accept()
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None, 120000)
    pruef = gui_reichweite.PruefPanel.offen
    h.pruefe(pruef is not None, f"„Auf der Maschine prüfen“ öffnet kein Fenster: {h.modal()!r}")
    if pruef is None:
        h.bild("0_kein_pruefen")
        return
    yield from h.warte_auf(lambda: not pruef.rechnet(), 120000)
    yield 1000
    h.pruefe(
        pruef.urteil.text() == "Alle Achsen bleiben in ihren Grenzen.",
        f"Urteil: {pruef.urteil.text()!r}",
    )
    k = pruef.kollision
    pruef.urteil_kollision.linkActivated.emit("kollision:pruefen")
    yield from h.warte_auf(lambda: not k.laeuft and k.ergebnis is not None, 600000)
    yield 300
    h.pruefe(
        k.urteil.text().startswith("Nichts berührt sich"),
        f"Kollision: {k.urteil.text()!r} {[b.text() for b in k.ergebnis.befunde][:2]}",
    )
    spieler = pruef.abspieler
    spieler.setze_zeit(spieler.abfahrt.dauer)
    yield from h.warte_auf(lambda: spieler.rest.text().startswith("Am Ende"), 300000)
    rest = spieler.rest.text()
    h.pruefe(rest.startswith("Am Ende bleiben") and "nirgends ins Teil" in rest, f"{rest!r}")
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("1_ring_y_am_ende")
    h.bild("1b_pruefen_fenster", pruef.form)
    pruef.reject()
    yield 500
    FreeCAD.closeDocument(doc.Name)
    yield 300
