# Die Zielzeit im Assistenten „Bearbeitung (Fräsen)“ (Manuel, 2026-10-02: „Das man erstmal ein
# Ziel rechnet von der Zeit her … ob der 12er Fräser überhaupt Sinn macht … dem Benutzer im
# Zweifelsfall von seiner Werkzeugkiste den besten Fräser vorschlagen“): Manuels Platte 200 × 200
# mit Zapfen und Tasche, die Werkzeugkiste der Tests (werkzeuge.testkiste: T1 Ø 12, T2 Planfräser
# Ø 50, T3 Ø 6, T4 Ø 20). Über den Strategien steht grau, wie viel weg muss und wie lange der
# Fräser des Räumens dafür mindestens braucht – mit dem ap, das die Stellen hergeben; und, weil
# der Planfräser hier viel schneller wäre, dass er es wäre, mit dem Fräser für den Rest. Darunter
# eingeklappt, was nicht zur Auswahl passt.
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
    from camaddon import hoehenfeld as hf
    from camaddon import werkzeuge as wz

    wz.Bibliothek(wz.testkiste()).speichern()

    doc = FreeCAD.newDocument("Zielzeit")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Platte")
    platte = Part.makeBox(200, 200, 30, V(-100, -100, -30))
    zapfen = Part.makeCylinder(10, 20, V(50, 50, 0))
    tasche = Part.makeCylinder(22.5, 20, V(-50, -50, -20))
    teil.Shape = platte.fuse(zapfen).cut(tasche).removeSplitter()
    doc.recompute()
    oben = next(e.name for e in hf.ebenen_oben(teil.Shape) if abs(e.z) < 1e-6)
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
    # Drei Schritte (P-2026-10-02-42): zuerst die Aufspannung, „Weiter“ geht mit dem Job.
    h.pruefe(
        panel.seite() == 0 and panel.seiten[0].isVisible() and not panel.seiten[1].isVisible(),
        f"nicht Schritt 1: {panel.seite()}",
    )
    h.pruefe(panel.knopf_weiter.isEnabled() and not panel.knopf_zurueck.isVisible(), "Knöpfe")
    h.pruefe(panel.schritt_text.text().startswith("Schritt 1 von 3"), panel.schritt_text.text())
    h.bild("0_aufspannung", panel.form)
    panel.knopf_weiter.click()
    yield 300
    h.pruefe(
        panel.seite() == 1 and panel.seiten[1].isVisible(), f"nicht Schritt 2: {panel.seite()}"
    )
    yield from h.warte_auf(lambda: bool(panel.ziel_text.text()), 120000)
    yield 500
    text = panel.ziel_text.text()
    print(ascii(f"Ziel: {text}"))
    # Rohteil 1 mm um das Teil, oben bis 21: über der Platte 21 mm ohne den Zapfen (834 cm³),
    # die Tasche (32), rundum der Rand 1 mm breit und 51 hoch (41) – 906 cm³.
    h.pruefe(text.startswith("Weg müssen 906,"), f"Volumen: {text!r}")
    h.pruefe("Ziel mit T" in text and "seines Zeitspanvolumens" in text, f"Ziel: {text!r}")
    raeumer = panel.raeumen.fraeser()
    if raeumer is not None and raeumer.art != wz.PLANFRAESER:
        h.pruefe(
            "Schneller aus der Werkzeugkiste: T2 Planfräser Ø 50, danach T" in text,
            f"kein schnellerer Fräser: {text!r}",
        )
    h.pruefe(bool(panel.ziel_text.toolTip()), "Ziel ohne Tooltip")
    # Was nicht passt, steht eingeklappt unter einer Zeile mit seiner Zahl; ein Klick klappt auf.
    andere = [b for b in panel.bloecke if not b.moeglich]
    h.pruefe(
        panel.passt_nicht.isVisible() and f"({len(andere)})" in panel.passt_nicht_knopf.text(),
        f"Passt nicht: {panel.passt_nicht_knopf.text()!r}",
    )
    h.pruefe(not any(b.widget.isVisible() for b in andere), "Passt nicht: nicht eingeklappt")
    h.bild("1_ziel", panel.form)
    panel.passt_nicht_knopf.click()
    yield 500
    h.pruefe(
        bool(andere) and all(b.widget.isVisible() and b.kurz.isVisible() for b in andere),
        "Passt nicht: aufgeklappt fehlen Zeilen",
    )
    h.bild("2_passt_nicht", panel.form)
    panel.passt_nicht_knopf.click()
    # Schritt 3: nur die Einstellungen der angehakten Strategien.
    panel.knopf_weiter.click()
    yield 500
    angehakt = panel.aktive_bloecke()
    h.pruefe(
        panel.seite() == 2
        and bool(angehakt)
        and all(b.einstellungen.isVisible() for b in angehakt)
        and not any(b.einstellungen.isVisible() for b in panel.bloecke if not b.aktiv()),
        f"Schritt 3: {[b.s.titel() for b in angehakt]}",
    )
    h.pruefe(not panel.knopf_weiter.isVisible(), "Schritt 3 mit „Weiter“")
    h.bild("3_einstellungen", panel.form)
    panel.knopf_zurueck.click()
    panel.knopf_zurueck.click()
    yield 300
    h.pruefe(panel.seite() == 0, f"zurück: Schritt {panel.seite() + 1}")
    panel.reject()
    yield 500
    FreeCAD.closeDocument(doc.Name)
    yield 300
