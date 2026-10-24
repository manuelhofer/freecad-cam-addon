# Senken ohne Kegelsenker (Manuels Messspitzenhalter: „nicht fertig“ blieben nur die Senkungen):
# Platte 100 × 60 × 10 mit einer Bohrung Ø 6,6 und einer 90°-Senkung Ø 12,4 darüber (wie
# szenario_senken); in der Werkzeugverwaltung der Standardfräser, ein Bohrer Ø 6,6 und statt des
# Kegelsenkers ein Fasenfräser T7 Ø 16, 90°, Spitze Ø 0,5. Bohrung und Senkung angeklickt: Rot
# „nicht fertig“ für die Senkung, darunter das Angebot „… T7 … kann sie senken … Nehmen?“ mit dem
# Knopf „T7 nehmen“ – von selbst nimmt das Addon ihn nicht. Geklickt: „Senken“ angehakt mit T7,
# „→ 1 Stelle, …“, nichts mehr rot. „Anlegen“: „Bohren T2“, „Senken T7“, die Spitze 5,95 unter
# der Kante (z 4,05: der Kegel hat oben Ø 12,4).
import FreeCAD
import FreeCADGui as Gui
import Part

V = FreeCAD.Vector


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import bohrung_bahn as bb
    from camaddon import gui_bearbeitung
    from camaddon import senken as sk
    from camaddon import werkzeuge as wz

    t1 = wz.standardwerkzeug()
    t2 = wz.Werkzeug(
        nummer=2,
        name="HSS 6.6",
        art=wz.BOHRER,
        durchmesser=6.6,
        schneiden=2,
        schneidenlaenge=60.0,
        spitzenwinkel=118.0,
        schneidstoff=wz.HSS,
    )
    t2.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.BOHREN, vc=25.0, fz=0.08)]
    t7 = wz.Werkzeug(
        nummer=7,
        name="Fase 16",
        art=wz.FASENFRAESER,
        durchmesser=16.0,
        schneiden=4,
        schneidenlaenge=8.0,
        spitzenwinkel=90.0,
        spitzen_d=0.5,
        schneidstoff=wz.VHM,
    )
    t7.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.FASEN, vc=80.0, fz=0.04)]
    wz.Bibliothek([t1, t2]).speichern()  # erst ohne T7

    doc = FreeCAD.newDocument("SenkenFase")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Platte")
    form = Part.makeBox(100, 60, 10).cut(Part.makeCylinder(3.3, 10, V(25, 30, 0)))
    teil.Shape = form.cut(Part.makeCone(3.3, 6.2, 2.9, V(25, 30, 7.1))).removeSplitter()
    doc.recompute()
    bohrung = next((b.name for b in bb.bohrungen(teil.Shape)), None)
    senkung = next((s.name for s in sk.senkungen(teil.Shape)), None)
    if bohrung is None or senkung is None:
        h.pruefe(False, f"Bohrung {bohrung}, Senkung {senkung}")
        return
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, bohrung)
    yield 500
    gui_bearbeitung.nullpunkt_vorgeben(None)
    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    if panel.knopf_weiter.isEnabled() and panel.knopf_weiter.isVisible():
        panel.knopf_weiter.click()  # „Was soll weg?“
        yield 500
    bohren, senken = panel.bohren, panel.senken
    yield from h.warte_auf(lambda: bohren.vorschau is not None, 60000)
    panel.flaeche_umschalten(senkung)
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 60000)
    yield 800
    h.pruefe(not senken.moeglich and not senken.aktiv(), "Senken ohne Kegelsenker möglich")
    # Ohne Fasenfräser: was fehlt, und der Knopf zur Werkzeugverwaltung.
    satz = panel.unfertig_satz.text()
    h.pruefe(
        panel.unfertig_angebot.isVisible()
        and "Kegelsenker 90° ab Ø 12,4" in satz
        and "Spitze bis Ø 6,6" in satz
        and panel.unfertig_knopf.text() == "Werkzeugverwaltung …",
        f"fehlt: {satz!r} / {panel.unfertig_knopf.text()!r}",
    )
    h.bild("0_was_fehlt", panel.form)
    # T7 kommt dazu – wie nach „Speichern“ in der Werkzeugverwaltung.
    wz.Bibliothek([t1, t2, t7]).speichern()
    panel._werkzeuge_gespeichert()
    yield 500
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 60000)
    yield 800
    unfertig = panel.unfertig.text() if panel.unfertig.isVisible() else ""
    h.pruefe(
        senkung in unfertig and "keine angebotene" not in unfertig, f"nicht fertig: {unfertig!r}"
    )
    satz = panel.unfertig_satz.text()
    h.pruefe(
        panel.unfertig_angebot.isVisible() and "T7" in satz and "kann sie senken" in satz,
        f"Angebot: {satz!r}",
    )
    h.pruefe(panel.unfertig_knopf.text() == "T7 nehmen", f"Knopf: {panel.unfertig_knopf.text()!r}")
    h.bild("1_angebot", panel.form)
    panel.unfertig_knopf.click()
    yield 500
    yield from h.warte_auf(
        lambda: senken.vorschau is not None and not panel.vorschau_laeuft(), 60000
    )
    yield 500
    h.pruefe(
        senken.aktiv() and senken.fraeser() is not None and senken.fraeser().nummer == 7,
        f"Senken: {senken.aktiv()}, {senken.fraeser()}",
    )
    text = senken.ergebnis.text()
    h.pruefe(text.startswith("→ 1 Stelle, "), f"Senken: {text!r}")
    h.pruefe(not panel.unfertig.isVisible(), f"noch rot: {panel.unfertig.text()!r}")
    h.pruefe(not panel.unfertig_angebot.isVisible(), "Angebot bleibt")
    h.bild("2_senken_t7", panel.form)
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 2000
    namen = [o.Label for o in job.Operations.Group]
    h.pruefe(namen == ["Bohren T2", "Senken T7"], f"Operationen: {namen}")
    senk_ops = [o for o in job.Operations.Group if o.Label == "Senken T7"]
    tiefen = [
        round(c.Parameters["Z"], 3) for o in senk_ops for c in o.Path.Commands if c.Name == "G81"
    ]
    h.pruefe(tiefen == [4.05], f"Tiefe: {tiefen}")
    Gui.getDocument(doc.Name).Modified = False
    FreeCAD.closeDocument(doc.Name)
    yield 300
