# 4. Achse auf der 3-Achs-Fräse (Manuel, 2026-11-15: „die 4te achse würde es eher in ein drei
# backenfutter horizonal entlang der x oder y achse so das die z achse vertikal von oben drauf schaut
# spannen ! und vll sogar mit einem reitstock stützen ..“): die Beispielmaschine „3-Achs-Fräse mit
# 4. Achse“ – Teilapparat A längs X mit Dreibackenfutter, gegenüber der Reitstock. Rohr Ø 60/50 × 150
# längs X mit einer Kurvennut 12 breit über 200° (wie tests/test_vierachs_vierte_achse.py), T1
# Schaftfräser Ø 8, ER32 an SK40. Die Stirn anklicken, Stange Ø 60: Rundachse A, der Haken „Mit
# Reitstock“ steht da (aus: das Rohr ragt nur 154 mm heraus, weniger als 3 × Ø) – anhaken, die
# Stange wird vorn 10 mm länger. „Weiter“, „Rundum schruppen/schlichten“ aus, die Randkante der Nut
# angeklickt: „Plan indexiert“ mit T1; „Anlegen“: die Bahn dreht A. „Auf der Maschine prüfen“: Der
# Reitstock steht an der Stirn der Stange, „Alle Achsen bleiben in ihren Grenzen.“, „Nichts berührt
# sich“, am Ende „nirgends ins Teil“. Bilder von vorn: das Rohr liegt im Futter, rechts der
# Reitstock, das Werkzeug kommt von oben.
# ZEITLIMIT: 900
import math

import FreeCAD
import FreeCADGui as Gui
import numpy as np
import Part
from PySide import QtCore

V = FreeCAD.Vector
RA, RI, LANG = 30.0, 25.0, 150.0
BREITE, WINKEL, A0, A1 = 12.0, 200.0, 55.0, 95.0


def _mitte(phi_grad):
    return A0 + (A1 - A0) * 0.5 * (1.0 - math.cos(math.pi * phi_grad / WINKEL))


def _strahl(phi_grad):
    p = math.radians(phi_grad)
    return V(0, math.cos(p), math.sin(p))


def _rohr():
    rohr = Part.makeCylinder(RA, LANG, V(), V(1, 0, 0)).cut(
        Part.makeCylinder(RI, LANG, V(), V(1, 0, 0))
    )
    schnitte = [
        Part.makeCylinder(
            BREITE / 2.0, 11.0, V(_mitte(f), 0, 0) + _strahl(f) * (RI - 3.0), _strahl(f)
        )
        for f in np.linspace(0.0, WINKEL, 101)
    ]
    return rohr.cut(schnitte[0].fuse(schnitte[1:]))


def _von_vorn_nah(asm):
    """Von vorn auf Futter, Stange und Reitstock, so wie sie gerade stehen – links neben dem
    Aufgabenfenster, das rechts über der Ansicht liegt; das Werkzeug von oben ist mit im Bild."""
    from pivy import coin

    from camaddon import maschine as m

    futter = m.globale_platzierung(asm.Document.getObject("Spannflaeche")).Base
    spitze = m.globale_platzierung(asm.Document.getObject("Reitstockspitze")).Base
    ziel = (futter + spitze) * 0.5 + V(200, 0, 60)  # rechts liegt das Aufgabenfenster darüber
    ansicht = Gui.ActiveDocument.ActiveView
    ansicht.viewFront()
    kamera = ansicht.getCameraNode()
    kamera.position.setValue(coin.SbVec3f(*(ziel + V(0, -1500, 0))))
    kamera.pointAt(coin.SbVec3f(*ziel), coin.SbVec3f(0, 0, 1))
    kamera.focalDistance.setValue(1500)
    if hasattr(kamera, "height"):
        kamera.height.setValue(480)


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine, gui_reichweite, gui_vierachs
    from camaddon import reitstock as rs
    from camaddon import vierachs_operation as vo
    from camaddon import vierachs_plan as vplan
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz
    from camaddon.gui_teile import blaettere_zu

    t1 = wz.Werkzeug(nummer=1, durchmesser=8, schneiden=3, schneidenlaenge=25,
                     laenge_spindelnase=125)  # fmt: skip
    t1.schnittwerte[wz.ALLE] = [
        wz.Einsatz(art=wz.SCHRUPPEN, ae=2, ap=4, vc=120, fz=0.04),
        wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=8, vc=150, fz=0.03),
        wz.Einsatz(art=wz.PLANEN, ae=3.2, ap=2, vc=150, fz=0.04),
    ]
    bibliothek = wz.Bibliothek([t1])
    t1.halter = bibliothek.neuer_halter("er32", None, "SK40").kennung
    bibliothek.speichern()

    asm, _maschine = beispielmaschine.lade(beispielmaschine.FRAESE_4)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    yield 300
    Gui.ActiveDocument.ActiveView.viewFront()
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("0_maschine")

    doc = FreeCAD.newDocument("RohrVierteAchse")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Rohr")
    teil.Shape = _rohr()
    doc.recompute()
    stirn = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if vr.ist_eben(f) and (vr.aussennormale(f) - V(1, 0, 0)).Length < 1e-9
    )
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, stirn)
    yield 500

    Gui.runCommand("CamAddon_Vierachs")
    yield 2000
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    panel.feld_stange.setText("60")
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 5000)
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 5000)
    eintraege = [panel.wahl_achse.itemText(i) for i in range(panel.wahl_achse.count())]
    h.pruefe(len(eintraege) == 1 and eintraege[0].startswith("A"), f"Rundachsen: {eintraege}")
    h.pruefe(panel.achse().laengs == V(1, 0, 0), f"gewählt: {panel.achse()}")
    # Der Haken ist da, aber aus: 154 mm heraus sind weniger als 3 × Ø 60.
    h.pruefe(panel.haken_reitstock.isVisible(), "kein Haken „Mit Reitstock“")
    h.pruefe(not panel.haken_reitstock.isChecked(), "„Mit Reitstock“ bei 154 mm aus Ø 60 an")
    panel.haken_reitstock.setChecked(True)
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 5000)
    yield 1000
    job = panel.job
    laenge = float(job.Stock.Height)
    h.pruefe(vr.mit_reitstock(job), "der Job weiß nichts vom Reitstock")
    h.pruefe(abs(laenge - 193.0) < 1e-6, f"Stange {laenge} lang (mit Zapfen 10: 193)")
    h.bild("1_seite1", panel.form)
    h.pruefe(panel.accept() is False, "„Weiter“ schließt das Fenster")
    yield 1500
    h.pruefe(panel.seite == 2, f"Seite {panel.seite}")
    panel.mit_schruppen.setChecked(False)
    panel.mit_schlichten.setChecked(False)
    yield 500

    # --- Die Randkante der Nut anklicken ----------------------------------------------------
    klon = vr.modell(job)
    form = klon.Shape
    laengs = np.array(tuple(panel.achse().laengs), dtype=float)

    def radien(kante):
        q = np.array([[p.x, p.y, p.z] for p in kante.discretize(Number=5)])
        return np.linalg.norm(q - np.outer(q @ laengs, laengs), axis=1)

    r_max = max(float(radien(k).max()) for k in form.Edges)
    rand = next(
        f"Edge{i + 1}"
        for i, k in enumerate(form.Edges)
        if (np.abs(radien(k) - r_max) < 0.02).all() and 0.5 < k.Length < 20.0
    )
    Gui.Selection.addSelection(doc.Name, klon.Name, rand)
    yield 3000
    h.pruefe(len(panel.flaechen()) > 50, f"gewählt: {len(panel.flaechen())} Flächen")
    h.pruefe(panel.mit_plan.isChecked(), "„Plan indexiert“ mit der Randkante aus")
    yield from h.warte_auf(lambda: panel.vorschau_plan is not None, 120000)
    yield 2000
    h.pruefe(panel.planfraeser() is not None and panel.planfraeser().nummer == 1, "nicht T1")
    h.pruefe(not panel.hinweis_bearbeitung.text(), f"rot: {panel.hinweis_bearbeitung.text()!r}")
    blaettere_zu(panel.mit_plan)
    yield 500
    h.bild("2_plan", panel.form)

    # --- Anlegen ------------------------------------------------------------------------------
    panel.accept()
    yield 4000
    ops = [o for o in job.Operations.Group if vo.ist_rundum(o)]
    plan = next((o for o in ops if vplan.ist_plan(o)), None)
    h.pruefe(plan is not None, f"Operationen: {[o.Label for o in job.Operations.Group]}")
    if plan is None:
        return
    achsen = {k for b in plan.Path.Commands for k in b.Parameters}
    h.pruefe("A" in achsen and "C" not in achsen, f"Achsen der Bahn: {achsen}")
    Gui.Selection.clearSelection()
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 1000
    h.bild("3_angelegt")

    # --- Auf der Maschine prüfen -----------------------------------------------------------
    FreeCAD.setActiveDocument(doc.Name)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None, 120000)
    pruef = gui_reichweite.PruefPanel.offen
    h.pruefe(pruef is not None, "„Auf der Maschine prüfen“ öffnet kein Fenster")
    if pruef is None:
        return
    yield 1500
    h.pruefe(
        pruef.urteil.text() == "Alle Achsen bleiben in ihren Grenzen.",
        f"Urteil: {pruef.urteil.text()!r}",
    )
    # Der Reitstock steht an der Stirn der Stange (anstellen beim Öffnen) – beides in der Stellung,
    # in der die Prüfung die Maschine las (das Fenster verfährt sie danach zum ersten Satz).
    p = pruef.pruefung
    spitze = rs.finde(asm)
    reitstock = spitze.lcs.getParentGeoFeatureGroup()
    an_der_spitze = p.verfahren.ausgang[reitstock].multVec(spitze.lcs.Placement.Base)
    # Die Stange ist inzwischen länger: hinten braucht der Halter von T1 Platz (Lücke).
    vorne = job.Stock.Placement.multVec(V(0, 0, float(job.Stock.Height)))
    neben = p._job_lage(pruef.nullpunkt(), {}).multVec(vorne) - an_der_spitze
    h.pruefe(neben.Length < 1e-3, f"die Spitze steht {neben.Length:.2f} mm neben der Stange")
    # Das Urteil „Reitstock“ oben: grün, die Spitze liegt an.
    h.pruefe(
        pruef.urteil_reitstock.isVisible()
        and "liegt an der Stange" in pruef.urteil_reitstock.text(),
        f"Urteil Reitstock: {pruef.urteil_reitstock.isVisible()} {pruef.urteil_reitstock.text()!r}",
    )
    k = pruef.kollision
    pruef.urteil_kollision.linkActivated.emit("kollision:pruefen")
    yield from h.warte_auf(lambda: not k.laeuft and k.ergebnis is not None, 300000)
    yield 500
    h.pruefe(
        k.urteil.text().startswith("Nichts berührt sich"),
        f"Kollision: {k.urteil.text()!r} {[b.text() for b in k.ergebnis.befunde][:2]}",
    )
    spieler = pruef.abspieler
    spieler.setze_zeit(spieler.abfahrt.dauer / 2)
    yield 1500
    _von_vorn_nah(asm)
    yield 500
    h.bild("4_mitten_drin_von_vorn")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("4b_mitten_drin")
    spieler.setze_zeit(spieler.abfahrt.dauer)
    yield from h.warte_auf(lambda: spieler.rest.text().startswith("Am Ende"), 300000)
    rest = spieler.rest.text()
    h.pruefe(rest.startswith("Am Ende bleiben") and "nirgends ins Teil" in rest, f"{rest!r}")
    spieler.knopf_hinsehen.click()
    yield 1000
    h.bild("5_am_ende")
    h.bild("5b_pruefen", pruef.form)
    # Reicht er nicht (wie an einer zu langen Stange): rot, mit „Ohne Reitstock“ als Knopf – der
    # schaltet den Job um, und das Fenster prüft ohne ihn (die Zeile verschwindet).
    pruef._reitstock = rs.Anstellung(0.0, 0.0, "x", 6.42, True, True)
    pruef._reitstock_zeigen()
    yield 300
    text = pruef.urteil_reitstock.text()
    h.pruefe("reicht nicht" in text and "reitstock:ohne" in text, f"Urteil rot: {text!r}")
    h.bild("6_reitstock_reicht_nicht", pruef.form)
    pruef.urteil_reitstock.linkActivated.emit("reitstock:ohne")
    yield from h.warte_auf(lambda: not pruef.rechnet(), 300000)
    yield 1000
    h.pruefe(not vr.mit_reitstock(job), "„Ohne Reitstock“: der Job rechnet noch mit ihm")
    h.pruefe(not pruef.urteil_reitstock.isVisible(), "„Ohne Reitstock“: das Urteil steht noch da")
    pruef.reject()
    yield 500
    FreeCAD.closeDocument(doc.Name)
    yield 300
