# Der Block „Fase“ (W-037) an der 3-Achs-Fräse: Platte 70 × 40 × 10 mit einem Zapfen 20 × 20 × 10,
# oben rundum 1 × 45° gefast (wie szenario_fase). T1 der Standardfräser Ø 12, T3 ein Fasenfräser 90°,
# T4 einer mit 60°. Die vier Fasen des Zapfens angeklickt: Die Liste sagt „Fase 45°, 1 breit,
# Fuß 19“; der Block „Fase“ ist angehakt mit T1 in Stufen – 21 Lagen (1 mm hoch, Stufe 0,05) –,
# Entgraten nicht, kein „Nicht fertig“; darunter die Frage nach T3 (90°, passend), nicht nach T4
# (60°). „T3 nehmen“: eine
# Lage. „Anlegen“: „Fase T3“, die Spitze auf 19 (der Fuß der Fase).
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

    from camaddon import gui_bearbeitung
    from camaddon import werkzeuge as wz

    t1 = wz.standardwerkzeug()

    def fasenfraeser(nummer, winkel):
        w = wz.Werkzeug(
            nummer=nummer,
            name=f"Fase {winkel:g}",
            art=wz.FASENFRAESER,
            durchmesser=10.0,
            schneiden=2,
            schneidenlaenge=5.0,
            spitzenwinkel=winkel,
            spitzen_d=0.5,
            schneidstoff=wz.VHM,
        )
        w.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.FASEN, vc=100.0, fz=0.05)]
        return w

    wz.Bibliothek([t1, fasenfraeser(3, 90.0), fasenfraeser(4, 60.0)]).speichern()

    doc = FreeCAD.newDocument("FaseQuader")
    teil = doc.addObject("Part::Feature", "Platte")
    form = Part.makeBox(70, 40, 10).fuse(Part.makeBox(20, 20, 10, V(10, 10, 10))).removeSplitter()
    oben = [
        k
        for k in form.Edges
        if abs(k.BoundBox.ZMin - 20) < 1e-6 and abs(k.BoundBox.ZMax - 20) < 1e-6
    ]
    teil.Shape = form.makeChamfer(1.0, oben)
    doc.recompute()
    fasen = []
    for i, f in enumerate(teil.Shape.Faces):
        u0, u1, v0, v1 = f.ParameterRange
        if 0.1 < f.normalAt((u0 + u1) / 2, (v0 + v1) / 2).z < 0.9:
            fasen.append(f"Face{i + 1}")
    h.pruefe(len(fasen) == 4, f"Fasen: {fasen}")
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.clearSelection()
    for name in fasen:
        Gui.Selection.addSelection(doc.Name, teil.Name, name)
    yield 500
    gui_bearbeitung.nullpunkt_vorgeben(None)  # die Koordinaten im Modell
    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    if panel.knopf_weiter.isEnabled() and panel.knopf_weiter.isVisible():
        panel.knopf_weiter.click()
        yield 500
    for name in fasen:  # das Fenster nimmt beim Öffnen die erste – die übrigen dazu
        if name not in panel.gewaehlte:
            panel.flaeche_umschalten(name)
            yield 200
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 120000)
    yield 1500
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 120000)
    liste = [panel.flaechen_liste.item(i).text() for i in range(panel.flaechen_liste.count())]
    h.pruefe(
        len(liste) == 4 and all("Fase 45°, 1 breit, Fuß 19" in z for z in liste), f"Liste: {liste}"
    )
    fase = panel.fase
    h.pruefe(fase.aktiv() and fase.fraeser().nummer == 1, f"Fase: {fase.aktiv()}, {fase.fraeser()}")
    h.pruefe("21 Lagen" in fase.ergebnis.text(), f"Fase: {fase.ergebnis.text()!r}")
    h.pruefe(not panel.entgraten.aktiv(), "Entgraten angehakt")
    # Die Fasen macht der Block fertig – kein rotes „Nicht fertig“ (bis 0.279.0 stand es da).
    unfertig = panel.unfertig.text() if panel.unfertig.isVisible() else ""
    h.pruefe(not unfertig, f"unfertig: {unfertig!r}")
    knoepfe = [k.text() for k in fase.angebot.knoepfe()]
    h.pruefe(knoepfe == ["T3 nehmen"], f"Angebot: {fase.angebot.text()!r} {knoepfe}")
    h.bild("1_fasen_t1_stufen", panel.form)
    fase.angebot.knoepfe()[0].click() if knoepfe else None
    yield 500
    yield from h.warte_auf(
        lambda: not panel.vorschau_laeuft() and fase.vorschau is not None, 120000
    )
    yield 800
    h.pruefe(
        fase.fraeser().nummer == 3 and "1 Lage" in fase.ergebnis.text(),
        f"T3: {fase.fraeser().nummer} {fase.ergebnis.text()!r}",
    )
    h.bild("2_fasen_t3", panel.form)
    job = panel.job
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 2500
    ops = [o for o in job.Operations.Group if o.Label.startswith("Fase")]
    h.pruefe(
        [o.Label for o in ops] == ["Fase T3"],
        f"Operationen: {[o.Label for o in job.Operations.Group]}",
    )
    if ops:
        zs = [
            c.Parameters["Z"]
            for c in ops[0].Path.Commands
            if c.Name == "G1" and "Z" in c.Parameters
        ]
        h.pruefe(zs and abs(min(zs) - 19.0) < 0.01, f"Spitze bei {min(zs) if zs else None}")
    Gui.getDocument(doc.Name).Modified = False
    FreeCAD.closeDocument(doc.Name)
    yield 300
