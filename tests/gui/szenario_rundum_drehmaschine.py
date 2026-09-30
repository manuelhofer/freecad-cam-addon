# Rundum schruppen und schlichten auf der Beispiel-Drehmaschine (W-002 Stufe E4 und
# W-003 V5e – der offene Klickweg; Manuel 2026-09-30: „die Beispiel Maschinen so bauen, dass
# das alles funktioniert“). In der Werkzeugverwaltung T1 Schaftfräser Ø 12 („Schruppen“) und
# T2 Kugelfräser Ø 6 („Schlichten“, ae 1 mm), beide im Halter „VDI30 angetrieben radial“,
# 125 und 110 mm ab Bezugspunkt. Welle Ø 50 mit Absatz auf Ø 36, 40 mm lang, Stange Ø 60.
# „4-Achs-Bearbeitung“ mit der Beispiel-Drehmaschine: Schritt 2 hat beide Haken, die Stange
# ragt so weit heraus, wie der Kopf des Halters braucht („Halter über die Werkzeugachse
# 27,5“). „Anlegen“ → „Auf der Maschine prüfen“: alle Achsen in ihren Grenzen, kein Hinweis
# zur Werkzeuglage; T1 und T2 stehen beim Abspielen radial am Teil; „Kollision prüfen“:
# nichts berührt sich; am Ende der Vergleich – nirgends ins Teil. Dann T2 ohne Halter: Das
# Prüffenster sagt, dass T2 auf P2 nicht radial sitzt, und nennt den Halter, der fehlt.
import FreeCAD
import FreeCADGui as Gui
import Part
from PySide import QtCore


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
    from camaddon import vierachs_schlichten as vs
    from camaddon import werkzeuge as wz

    bibliothek = wz.Bibliothek()
    halter = bibliothek.neuer_halter("vdi30_radial")
    t1 = bibliothek.neues_werkzeug()
    t1.nummer, t1.durchmesser, t1.schneiden, t1.schneidenlaenge = 1, 12.0, 3, 26.0
    t1.laenge_spindelnase, t1.halter = 125.0, halter.kennung
    t1.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=4.8, ap=2, vc=150, fz=0.08)]
    t2 = bibliothek.neues_werkzeug()
    t2.nummer, t2.art, t2.durchmesser, t2.schneiden = 2, wz.KUGELFRAESER, 6.0, 2
    t2.laenge_spindelnase, t2.halter = 110.0, halter.kennung
    t2.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=1.0, ap=6, vc=150, fz=0.04)]
    bibliothek.speichern()

    asm, _maschine = beispielmaschine.lade(beispielmaschine.DREHMASCHINE)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    yield 300

    doc = FreeCAD.newDocument("Welle")
    teil = doc.addObject("Part::Feature", "Welle")
    welle = Part.makeCylinder(25, 25, FreeCAD.Vector(15, 0, 0), FreeCAD.Vector(1, 0, 0))
    welle = welle.fuse(Part.makeCylinder(18, 15, FreeCAD.Vector(), FreeCAD.Vector(1, 0, 0)))
    teil.Shape = welle.removeSplitter()
    doc.recompute()
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    stirn = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if vr.ist_eben(f)
        and (vr.aussennormale(f) - FreeCAD.Vector(1, 0, 0)).Length < 1e-9
        and f.Area > 1500  # die Stirn Ø 50 vorne, nicht die Schulter
    )
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, stirn)
    yield 500

    # --- Der Assistent: Maschine, Stange, beide Bearbeitungen ------------------------------
    Gui.runCommand("CamAddon_Vierachs")
    yield 1500
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    h.pruefe(panel.buchstabe() == "C", f"Rundachse {panel.buchstabe()}")
    panel.feld_stange.setText("60")
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 3000)
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    panel.accept()  # Weiter
    yield 300
    h.pruefe(panel.seite == 2, f"Seite {panel.seite}")
    h.pruefe(panel.mit_schruppen.isChecked(), "„Rundum schruppen“ nicht angehakt")
    h.pruefe(panel.mit_schlichten.isChecked(), "„Rundum schlichten“ nicht angehakt")
    h.pruefe(panel.fraeser() is not None and panel.fraeser().nummer == 1, "Schruppen: nicht T1")
    schlicht = panel.schlichtfraeser()
    h.pruefe(schlicht is not None and schlicht.nummer == 2, "Schlichten: nicht T2")
    yield from h.warte_auf(
        lambda: panel.vorschau is not None and panel.vorschau_schlichten is not None, 30000
    )
    ausspannen = panel.ausspannen.text()
    h.pruefe(
        "Überlauf 6,5 + Halter über die Werkzeugachse 27,5 + Abstand zum Futter 5,0" in ausspannen,
        f"Ausspannen: {ausspannen!r}",
    )
    h.pruefe(not panel.hinweis_bearbeitung.text(), f"rot: {panel.hinweis_bearbeitung.text()!r}")
    h.bild("1_schruppen_und_schlichten", panel.form)
    job = panel.job
    panel.accept()  # Anlegen
    yield 1500
    h.pruefe(gui_vierachs.VierachsPanel.offen is None, "Fenster nach „Anlegen“ offen")
    namen = [o.Label for o in job.Operations.Group if vo.ist_rundum(o)]
    h.pruefe(namen == ["Rundum schruppen T1", "Rundum schlichten T2"], f"Operationen: {namen}")
    for op in job.Operations.Group:
        if vo.ist_rundum(op):
            h.pruefe(abs(vo.halter_zum_futter(op) - 27.5) < 1e-9, f"{op.Label}: Halter")
    schlichten = next((o for o in job.Operations.Group if vs.ist_schlichten(o)), None)
    h.pruefe(schlichten is not None and schlichten.Umdrehungen > 10, "Schlichten ohne Umdrehungen")

    # --- Auf der Maschine prüfen: radial, in den Grenzen, nichts stößt an -----------------
    FreeCAD.setActiveDocument(doc.Name)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400  # siehe szenario_reichweite.py: 1.1.3 verarbeitet die Auswahl verzögert
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None)
    pruef = gui_reichweite.PruefPanel.offen
    h.pruefe(pruef is not None, "„Auf der Maschine prüfen“ öffnet kein Fenster")
    if pruef is None:
        return
    yield 800
    h.pruefe(
        pruef.urteil.text() == "Alle Achsen bleiben in ihren Grenzen.",
        f"Urteil: {pruef.urteil.text()!r}",
    )
    hinweise = pruef.hinweise.text()
    h.pruefe("radial aus" not in hinweise, f"Hinweise: {hinweise!r}")
    spieler = pruef.abspieler
    fahrt = spieler.abfahrt
    for nummer, name in ((0, "2_t1_am_teil"), (1, "3_t2_am_teil")):
        stationen = [s for s in fahrt.stationen if s.operation == nummer and not s.eilgang]
        h.pruefe(len(stationen) > 100, f"Operation {nummer}: {len(stationen)} Stationen")
        if not stationen:
            continue
        mitte = stationen[len(stationen) // 3]
        spieler.setze_zeit(mitte.zeit)
        spieler.knopf_hinsehen.click()
        yield 500
        h.bild(name)
    k = pruef.kollision
    pruef.urteil_kollision.linkActivated.emit("kollision:pruefen")
    yield from h.warte_auf(lambda: not k.laeuft and k.ergebnis is not None, 300000)
    yield 300
    h.pruefe(
        k.urteil.text().startswith("Nichts berührt sich, nichts kommt näher"),
        f"Kollision: {k.urteil.text()!r} {[b.text() for b in k.ergebnis.befunde][:2]}",
    )
    spieler.setze_zeit(fahrt.dauer)
    yield 500
    rest = spieler.rest.text()
    h.pruefe(rest.startswith("Am Ende bleiben") and "nirgends ins Teil" in rest, f"{rest!r}")
    Gui.SendMsgToActiveView("ViewFit")
    spieler.knopf_hinsehen.click()
    yield 500
    h.bild("4_am_ende_farben")
    h.bild("4b_pruefen_fenster", pruef.form)
    pruef.reject()
    yield 500

    # --- T2 ohne Halter: Der Hinweis nennt T2, P2 und den Halter, der fehlt -----------------
    t2.halter = ""
    bibliothek.speichern()
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None)
    pruef = gui_reichweite.PruefPanel.offen
    h.pruefe(pruef is not None, "Prüffenster öffnet nicht wieder")
    if pruef is not None:
        yield 800
        hinweise = pruef.hinweise.text()
        h.pruefe(
            "T2 sitzt auf P2 aber anders" in hinweise and "VDI30 angetrieben radial" in hinweise,
            f"Hinweis ohne Halter: {hinweise!r}",
        )
        h.bild("5_t2_ohne_halter", pruef.form)
        pruef.reject()
        yield 500
    for name in list(FreeCAD.listDocuments()):
        FreeCAD.closeDocument(name)
    yield 300
