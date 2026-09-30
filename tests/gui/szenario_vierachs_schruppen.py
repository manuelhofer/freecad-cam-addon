# „4-Achs-Bearbeitung“ mit „Rundum schruppen“ (W-003 Stufe V3d, Manuels Wunsch
# 2026-09-27: „was willste machen .. schruppen“). Die Beispiel-Drehmaschine ist
# offen, in der Werkzeugverwaltung steht ein Schaftfräser T1 Ø 12 mit dem Einsatz
# „Schruppen“ (ae 4,8, ap 2) im Halter „VDI30 angetrieben radial“ – der stellt ihn
# radial zur Stange (W-002 Stufe E). Welle Ø 60, Stirnfläche angeklickt, Stange Ø 80:
# Unten heißt der Knopf „Weiter“. Danach Schritt 2 „Was willst du machen?“ –
# „Rundum schruppen“ angehakt, T1 und „Schruppen“ vorgewählt, grau „→ 5 Lagen
# (Ø 80,0 mm → Ø 60,…)“ und „Die Stange muss 140,0 mm aus dem Futter ragen: Planaufmaß
# 1,0 + Teil 100,0 + Überlauf 6,5 + Halter über die Werkzeugachse 27,5 + Abstand zum
# Futter 5,0.“ (V3f; der Kopf des Halters reicht weiter als der Fräser); der Knopf heißt
# „Anlegen“. „Anlegen“: Die Stange ist 170,0 mm lang (30 im Futter), die
# Bahn endet 6,5 mm hinter dem Teil. Im Job stehen der
# Controller „T1 Schruppen“ (FreeCADs Vorgabe-Controller ist weg) und „Rundum
# schruppen T1“ mit fünf Lagen und G93. „Auf der Maschine prüfen“ (V3e, T1 mit 125 mm
# ab Spindelnase): „Alle Achsen bleiben in ihren Grenzen.“, kein Hinweis zur
# Werkzeuglage; mitten in der ersten Lage steht C gedreht, die Spitze außen am Teil;
# „Kollision prüfen“ → „Nichts berührt sich …“. Ohne den Haken „Bahn“ ist die Bahn weg, mit
# ihm wieder da; am Ende mit den Farben sind Bahn und Teil aus. Das erste Strg+Z nimmt
# Controller und Operation zurück, das zweite Job und Stange.
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

    from camaddon import beispielmaschine, gui_vierachs
    from camaddon import vierachs_operation as vo
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    fraeser = wz.Werkzeug(
        nummer=1, durchmesser=12, schneiden=3, schneidenlaenge=26, laenge_spindelnase=125
    )
    fraeser.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=4.8, ap=2, vc=150, fz=0.08)]
    bibliothek = wz.Bibliothek([fraeser])
    fraeser.halter = bibliothek.neuer_halter("vdi30_radial").kennung
    bibliothek.speichern()

    asm, _maschine = beispielmaschine.lade(beispielmaschine.DREHMASCHINE)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    yield 300

    doc = FreeCAD.newDocument("Welle")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Welle")
    teil.Shape = Part.makeCylinder(30, 100, FreeCAD.Vector(), FreeCAD.Vector(1, 0, 0))
    doc.recompute()
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    stirn = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if vr.ist_eben(f) and (vr.aussennormale(f) - FreeCAD.Vector(1, 0, 0)).Length < 1e-9
    )
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, stirn)
    yield 500

    Gui.runCommand("CamAddon_Vierachs")
    yield 1500
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    panel.feld_stange.setText("80")
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 3000)
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    ok = panel.knopf_anlegen()
    h.pruefe(ok is not None and ok.text() == "Weiter", f"Knopf in Schritt 1: {ok and ok.text()!r}")
    h.pruefe(panel.buchstabe() == "C", f"Rundachse {panel.buchstabe()}")

    # --- Weiter: Schritt 2 ------------------------------------------------------------
    h.pruefe(panel.accept() is False, "„Weiter“ schließt das Fenster")
    yield 300
    h.pruefe(panel.seite == 2 and panel.seiten.currentIndex() == 1, f"Seite {panel.seite}")
    h.pruefe("Schritt 2" in panel._kopf_text.text(), f"Kopf: {panel._kopf_text.text()!r}")
    h.pruefe(ok.text() == "Anlegen", f"Knopf in Schritt 2: {ok.text()!r}")
    h.pruefe(panel.mit_schruppen.isChecked(), "„Rundum schruppen“ nicht angehakt")
    h.pruefe(panel.fraeser() is not None and panel.fraeser().nummer == 1, "T1 nicht gewählt")
    h.pruefe(panel.einsatz() is not None and panel.einsatz().art == wz.SCHRUPPEN, "Schruppen fehlt")
    h.pruefe(
        panel.felder_schruppen["zustellung"].placeholderText() == "2"
        and panel.felder_schruppen["steigung"].placeholderText() == "4,8",
        "Vorschläge: "
        + ", ".join(f"{k}={f.placeholderText()!r}" for k, f in panel.felder_schruppen.items()),
    )
    yield from h.warte_auf(lambda: panel.vorschau is not None, 15000)
    ergebnis = panel.ergebnis.text()
    h.pruefe(ergebnis.startswith("→ 5 Lagen (Ø 80,0 mm → Ø 60,"), f"Vorschau: {ergebnis!r}")
    h.pruefe(not panel.hinweis_bearbeitung.text(), f"Hinweis: {panel.hinweis_bearbeitung.text()!r}")
    soll = (
        "Die Stange muss 140,0 mm aus dem Futter ragen: Planaufmaß 1,0 + Teil 100,0 + "
        "Überlauf 6,5 + Halter über die Werkzeugachse 27,5 + Abstand zum Futter 5,0."
    )
    h.pruefe(panel.ausspannen.text() == soll, f"Ausspannen: {panel.ausspannen.text()!r}")
    h.pruefe(ok.isEnabled(), "„Anlegen“ gesperrt")
    h.pruefe(not panel.radius_hinweis.isHidden(), "Hinweis „X ist der Radius“ fehlt")
    # Die Beispiel-Drehmaschine zählt X im Durchmesser (P-2026-09-30-54): Der graue Satz sagt,
    # was das für FreeCADs eigene Postprozessoren heißt.
    h.pruefe(
        panel.radius_hinweis.text().startswith("Die Maschine zählt X im Durchmesser"),
        f"Hinweis zu X: {panel.radius_hinweis.text()!r}",
    )
    h.bild("1_was_willst_du_machen", panel.form)

    # Zurück und wieder vor: Die Wahl bleibt.
    panel.zeige_seite(1)
    yield 200
    h.pruefe(ok.text() == "Weiter" and panel.seite == 1, "Zurück geht nicht")
    panel.zeige_seite(2)
    yield 200
    h.pruefe(panel.fraeser() is not None and panel.fraeser().nummer == 1, "T1 nach Zurück weg")
    yield from h.warte_auf(lambda: panel.vorschau is not None, 15000)

    # --- Anlegen -------------------------------------------------------------------------
    job = panel.job
    panel.accept()
    yield 1500
    h.pruefe(gui_vierachs.VierachsPanel.offen is None, "Fenster noch offen")
    controller = job.Tools.Group
    h.pruefe(
        [tc.Label for tc in controller] == ["T1 Schruppen"],
        f"Controller: {[tc.Label for tc in controller]}",
    )
    ops = [o for o in job.Operations.Group if vo.ist_rundum(o)]
    h.pruefe(len(ops) == 1, f"Operationen: {[o.Label for o in job.Operations.Group]}")
    if ops:
        op = ops[0]
        namen = [b.Name for b in op.Path.Commands]
        h.pruefe(op.Label == "Rundum schruppen T1", f"Name: {op.Label!r}")
        h.pruefe(op.Lagen == 5 and "G93" in namen and namen[-1] == "G94", f"Bahn: {op.Lagen}")
        hinten = min(b.Parameters["Z"] for b in op.Path.Commands if b.Name == "G1")
        h.pruefe(abs(hinten + 106.5) < 1e-6, f"Bahn endet bei Z {hinten}")
        h.pruefe(abs(job.Stock.Height.Value - 170.0) < 1e-6, f"Stange: {job.Stock.Height}")
        h.pruefe(abs(op.HalterZumFutter.Value - 27.5) < 1e-9, f"Halter: {op.HalterZumFutter}")
        h.pruefe(op.ToolController is controller[0], "Operation ohne den neuen Controller")
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("2_bahn_um_die_welle")

    # --- Auf der Maschine prüfen (V3e): ohne TCPM, C dreht, nichts stößt an ------------------
    from camaddon import gui_reichweite

    FreeCAD.setActiveDocument(doc.Name)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400  # siehe szenario_reichweite.py: 1.1.3 verarbeitet die Auswahl verzögert
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None)
    pruef = gui_reichweite.PruefPanel.offen
    h.pruefe(pruef is not None, "„Auf der Maschine prüfen“ öffnet kein Fenster")
    if pruef is not None:
        yield 800
        h.pruefe(
            pruef.urteil.text() == "Alle Achsen bleiben in ihren Grenzen.",
            f"Urteil: {pruef.urteil.text()!r}",
        )
        hinweise = pruef.hinweise.text()
        h.pruefe(
            "radial aus" not in hinweise and "längs Z" not in hinweise, f"Hinweise: {hinweise!r}"
        )
        spieler = pruef.abspieler
        fahrt = spieler.abfahrt
        mitte = fahrt.stationen[len(fahrt.stationen) // 10]
        spieler.setze_zeit(mitte.zeit)
        spieler.knopf_hinsehen.click()
        yield 500
        h.pruefe(mitte.rund.get("C", 0.0) < -90, f"C mitten in der Lage: {mitte.rund}")
        h.pruefe("C1" in spieler.achswerte.text(), f"Achswerte: {spieler.achswerte.text()!r}")
        spitze = spieler.spitze.text()
        h.pruefe(
            spitze.startswith("Spitze im Programm: X Ø ")
            and ", C −" in spitze
            and "soll" not in spitze,
            f"Spitze: {spitze!r}",
        )
        h.pruefe("X1 Ø " in spieler.achswerte.text(), f"X1 im Ø: {spieler.achswerte.text()!r}")
        h.bild("3_abfahren_c_gedreht")
        h.bild("3b_pruefen_fenster", pruef.form)
        # Der Haken „Bahn“ blendet die Bahn aus und wieder ein (Manuel, 2026-09-30).
        bild = pruef.bild
        h.pruefe(spieler.haken_bahn.isChecked(), "Haken „Bahn“ nicht gesetzt")
        h.pruefe(bild.bahn_schalter.whichChild.getValue() == 0, "Bahn nicht zu sehen")
        spieler.haken_bahn.setChecked(False)
        yield 300
        h.pruefe(bild.bahn_schalter.whichChild.getValue() == -1, "Bahn ohne Haken zu sehen")
        h.bild("3c_ohne_bahn")
        spieler.haken_bahn.setChecked(True)
        yield 200
        h.pruefe(bild.bahn_schalter.whichChild.getValue() == 0, "Bahn mit Haken weg")
        k = pruef.kollision
        pruef.urteil_kollision.linkActivated.emit("kollision:pruefen")
        yield from h.warte_auf(lambda: not k.laeuft and k.ergebnis is not None, 180000)
        yield 300
        h.pruefe(
            k.urteil.text().startswith("Nichts berührt sich, nichts kommt näher"),
            f"Kollision: {k.urteil.text()!r} {[b.text() for b in k.ergebnis.befunde][:2]}",
        )
        h.bild("4_kollision_frei", pruef.form)
        # Rohteil und Fertigteil (V3g): mitten in der ersten Lage ist die Stange vorne dünner;
        # am Ende steht der Vergleich in Farben und als Satz.
        h.pruefe(
            spieler.rest.text().startswith("Die Stange wird beim Abspielen abgetragen"),
            f"beim Abtragen: {spieler.rest.text()!r}",
        )
        spieler.setze_zeit(fahrt.dauer)
        yield 500
        rest = spieler.rest.text()
        h.pruefe(
            rest.startswith("Am Ende bleiben 0,3") and "nirgends ins Teil" in rest,
            f"Restmaterial: {rest!r}",
        )
        h.pruefe(bild.bahn_schalter.whichChild.getValue() == -1, "am Ende Bahn zu sehen")
        h.pruefe(bild.modell_schalter.whichChild.getValue() == -1, "am Ende Teil zu sehen")
        Gui.SendMsgToActiveView("ViewFit")
        spieler.knopf_hinsehen.click()
        yield 500
        h.bild("5_rest_farben")
        h.bild("5b_rest_satz", pruef.form)
        pruef.reject()
        yield 500

    # Zwei Schritte Rückgängig: zuerst Controller und Operation, dann Job und Stange.
    h.pruefe(
        doc.UndoNames == ["Rundum schruppen anlegen", "4-Achs-Bearbeitung"],
        f"Rückgängig-Schritte: {doc.UndoNames}",
    )
    doc.undo()
    doc.recompute()
    yield 300
    h.pruefe(
        not [o for o in doc.Objects if vo.ist_rundum(o)]
        and [tc.Label for tc in job.Tools.Group] != ["T1 Schruppen"],
        f"nach einem Strg+Z: {[tc.Label for tc in job.Tools.Group]}",
    )
    doc.undo()
    doc.recompute()
    yield 300
    uebrig = [o.Name for o in doc.Objects if o.Name != teil.Name]
    h.pruefe(not uebrig, f"nach zwei Strg+Z noch da: {uebrig}")
    for name in list(FreeCAD.listDocuments()):
        FreeCAD.closeDocument(name)
    yield 300
