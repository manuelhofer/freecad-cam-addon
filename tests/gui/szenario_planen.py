# Der Einsatz „Planen“ am Ø 12 (P-2026-10-02-54; Manuel, 2026-10-02: „der Ø 12 darf bei kleinem
# ap ein größeres ae fahren … Werte im Netz“): Block 100 × 60 × 20, T1 Manuels Standardfräser
# (Planen ae 8,4, ap 1,2, fz 0,07; Schruppen ae 1,5, ap 25, fz 0,1). Die Oberseite anklicken –
# über ihr steht 1 mm Rohteil: Das Planfräsen nimmt „Planen“, eine Lage mit ae 8,4, und ist
# schneller als das Räumen. Aufmaß oben 10: Jetzt ist „Schruppen“ schneller (eine Lage mit der
# ganzen Schneide statt neun dünner) – das Planfräsen wechselt den Einsatz von selbst.
import FreeCAD
import FreeCADGui as Gui
import Part


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import gui_bearbeitung
    from camaddon import hoehenfeld as hf
    from camaddon import werkzeuge as wz

    t1 = wz.standardwerkzeug()
    wz.Bibliothek([t1]).speichern()

    doc = FreeCAD.newDocument("Planen")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Block")
    teil.Shape = Part.makeBox(100, 60, 20)
    doc.recompute()
    oben = next(e.name for e in hf.ebenen_oben(teil.Shape) if abs(e.z - 20.0) < 1e-6)
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, oben)
    yield 500

    gui_bearbeitung.nullpunkt_vorgeben(None)
    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    plan, raeumen = panel.plan, panel.raeumen
    panel.knopf_weiter.click()  # Schritt 2: die Strategien mit ihrer Zeit
    yield from h.warte_auf(
        lambda: plan.vorschau is not None and raeumen.vorschau is not None, 120000
    )
    yield 1500

    # 1 mm über der Oberseite: Planen, eine Lage, schneller als das Räumen.
    einsatz = plan.einsatz()
    text = plan.ergebnis.text()
    print(ascii(f"1 mm: {einsatz.art if einsatz else None} | {text}"))
    print(ascii(f"Räumen: {raeumen.ergebnis.text()}"))
    print(ascii(f"Ziel: {panel.ziel_text.text()}"))
    h.pruefe(einsatz is not None and einsatz.art == wz.PLANEN, f"1 mm: {einsatz}")
    h.pruefe(text.startswith("→ 1 Lage,"), f"1 mm: {text!r}")
    h.pruefe(
        plan.aktiv() and not raeumen.aktiv() and "die schnellste" in text,
        f"1 mm: Planfräsen nicht vorn – {text!r} / {raeumen.ergebnis.text()!r}",
    )
    h.bild("1_planen", panel.form)
    panel.knopf_weiter.click()  # Schritt 3: Fräser, Einsatz, Felder
    yield 300
    h.bild("1b_planen_einstellungen", panel.form)
    panel.knopf_zurueck.click()
    yield 300

    # Aufmaß oben 10: Schruppen ist schneller – der Einsatz wechselt von selbst.
    panel.felder_rohteil["oben"].setText("10")
    yield from h.warte_auf(lambda: not panel._rohteil_uhr.isActive(), 3000)
    yield from h.warte_auf(lambda: plan.einsatz() is not None, 3000)
    yield from h.warte_auf(lambda: plan.vorschau is not None, 120000)
    yield 1500
    einsatz = plan.einsatz()
    text = plan.ergebnis.text()
    print(ascii(f"10 mm: {einsatz.art if einsatz else None} | {text}"))
    h.pruefe(einsatz is not None and einsatz.art == wz.SCHRUPPEN, f"10 mm: {einsatz}")
    h.pruefe(text.startswith("→ 1 Lage,"), f"10 mm: {text!r}")
    h.bild("2_schruppen", panel.form)
    panel.reject()
    yield 800
    FreeCAD.closeDocument(doc.Name)
    yield 300
