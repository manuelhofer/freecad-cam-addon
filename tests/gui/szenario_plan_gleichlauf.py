# Planfräsen nur im Gleichlauf (P-2026-10-02-24, Manuel: „auswählbar, ob er abhebt und wieder von
# vorne anfängt“): Block 60 × 40 × 20 im Rohteil mit 1 mm rundum, T1 der Standardfräser Ø 12. Die
# Oberseite anklicken: Im Block Planfräsen ist „Zeilen von beiden Seiten (alle im Gleichlauf)“
# angehakt (Manuel, 2026-11-13, Frage 2). Ohne den Haken: hin und her. „Anlegen“: „Planfräsen T1“
# mit VonBeidenSeiten, die Zeilen der einen Hälfte in einer Richtung, die der anderen andersherum;
# zwischen ihnen hebt der Fräser ab (G0). (Der Haken „nur im Gleichlauf (abheben, von vorne)“
# von 2026-10-02 bleibt daneben, aus.)
import re

import FreeCAD
import FreeCADGui as Gui
import Part

V = FreeCAD.Vector


def _minuten(text):
    treffer = re.search(r"etwa (\d+(?:,\d+)?) (min|s)", text)
    if treffer is None:
        return None
    zahl = float(treffer.group(1).replace(",", "."))
    return zahl if treffer.group(2) == "min" else zahl / 60.0


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import gui_bearbeitung
    from camaddon import planfraesen as pf
    from camaddon import werkzeuge as wz

    wz.Bibliothek([wz.standardwerkzeug()]).speichern()
    doc = FreeCAD.newDocument("PlanGleichlauf")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Block")
    teil.Shape = Part.makeBox(60, 40, 20)
    doc.recompute()
    oben = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if abs(f.BoundBox.ZMin - 20) < 1e-6 and abs(f.BoundBox.ZMax - 20) < 1e-6
    )
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, oben)
    yield 500
    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    plan = panel.plan
    yield from h.warte_auf(lambda: plan.vorschau is not None, 300000)
    yield 1500
    einzeln = _minuten(plan.ergebnis.text())
    kasten = plan.haken_felder.get("von_beiden")
    # Angehakt (Manuel, 2026-11-13, Frage 2); „hin und her“ bleibt wählbar: Haken weg.
    h.pruefe(kasten is not None and kasten.isChecked(), "Haken fehlt oder ist nicht an")
    if kasten is None:
        return
    # Der Text muss sich nicht ändern (wo von beiden Seiten nicht schneller ist, fährt es mit und
    # ohne Haken gleich) – nur auf die neue Vorschau warten.
    kasten.setChecked(False)
    yield 2500
    yield from h.warte_auf(lambda: plan.vorschau is not None, 300000)
    yield 1500
    hin_und_her = _minuten(plan.ergebnis.text())
    h.pruefe(
        # Der Haken greift nur, wo es schneller ist: nie langsamer als hin und her.
        hin_und_her is not None and einzeln is not None and einzeln <= hin_und_her + 0.02,
        f"Zeit: hin und her {hin_und_her}, von beiden Seiten {einzeln} ({plan.ergebnis.text()!r})",
    )
    kasten.setChecked(True)
    yield 2500
    yield from h.warte_auf(lambda: plan.vorschau is not None, 300000)
    yield 1500
    # Entscheidet die Zeit gegen das Planfräsen, geht der Haken zu Räumen – von Hand wieder an.
    if not plan.aktiv():
        h.pruefe(
            "langsamer als Räumen" in plan.ergebnis.text() and panel.raeumen.aktiv(),
            f"Planfräsen aus, aber warum? {plan.ergebnis.text()!r}",
        )
        plan.haken.setChecked(True)  # wie ein Klick: der Haken von Hand
        yield 1500
    h.pruefe(plan.aktiv() and kasten.isChecked(), "Planfräsen nicht an")
    h.bild("1_haken", panel.form)

    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    ops = [o for o in job.Operations.Group if pf.ist_planfraesen(o)]
    h.pruefe(
        len(ops) == 1 and ops[0].VonBeidenSeiten and not ops[0].NurGleichlauf,
        f"Operationen: {[o.Label for o in ops]}",
    )
    if not ops:
        return
    befehle = list(ops[0].Path.Commands)
    richtungen = set()
    zeilen = []  # (Achse, Lage quer, Richtung) je Zeile
    vorher = None
    for b in befehle:
        if b.Name in ("G0", "G1") and "X" in b.Parameters and "Y" in b.Parameters:
            if vorher is not None and b.Name == "G1":
                dx, dy = b.Parameters["X"] - vorher[0], b.Parameters["Y"] - vorher[1]
                if abs(dy) < 1e-6 and abs(dx) > 20.0:
                    richtungen.add(("x", dx > 0))
                    zeilen.append(("x", vorher[1], dx > 0))
                elif abs(dx) < 1e-6 and abs(dy) > 20.0:
                    richtungen.add(("y", dy > 0))
                    zeilen.append(("y", vorher[0], dy > 0))
            vorher = (b.Parameters["X"], b.Parameters["Y"])
    # Von beiden Seiten (wenn das hier schneller war): die Zeilen der einen Hälfte in einer
    # Richtung, die der anderen andersherum – beides Gleichlauf. Sonst hin und her wie ohne Haken
    # (mit dem Ø 12 und vielen schmalen Zeilen kostet das Abheben je Zeile mehr, als es bringt).
    mitte = (min(z[1] for z in zeilen) + max(z[1] for z in zeilen)) / 2 if zeilen else 0.0
    je_seite = {}
    for achse, quer, richtung in zeilen:
        if abs(quer - mitte) > 1.0:
            je_seite.setdefault((achse, quer > mitte), set()).add(richtung)
    beide = len(je_seite) == 2 and all(len(r) == 1 for r in je_seite.values())
    if einzeln is not None and hin_und_her is not None and einzeln < hin_und_her - 0.02:
        h.pruefe(beide, f"schneller, aber nicht von beiden Seiten: {je_seite}")
    h.pruefe(bool(richtungen), "keine Zeilen im Programm")
    Gui.Selection.clearSelection()
    Gui.activeDocument().activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("2_angelegt")
    FreeCAD.closeDocument(doc.Name)
    yield 300
