# Der Haken „Zum Schluss eine Runde auf dem Teilboden“ am 3D-Schlichten (vorbelegt aus): Eine
# Kuppel R 20, die am Teilboden endet (Kugel um (0, 0, −10), unten bei z 0 abgeschnitten), T3 eine
# Kugel Ø 6. Die Kuppel anklicken, „Bearbeitung“, „Alles vorschlagen“:
# 1. Im Schritt „Schlichten“ steht unter „3D-Schlichten“ → „Werte ändern“ der Haken, nicht
#    angehakt – er erscheint nur, weil an der Unterkante ein Rest bleibt (im Restschlichten nie);
#    der Satz sagt „bis 1,… mm hoch“. Bild 1_ohne.
# 2. Haken setzen: Die Vorschau rechnet neu, die Bahn hat eine Runde mehr (am Fuß, die Spitze auf
#    z 0), der Rest an der Unterkante wird niedriger. Bild 2_mit, dazu 3_teil (die Wege im Teil).
# 3. „Anlegen“: Die Operation „3D-Schlichten T3“ hat Bodenrunde an, ihre Bahn fährt auf Z 0.
# Bilder: 1_ohne, 2_mit, 3_teil, 4_angelegt.
# ZEITLIMIT: 900
import re

import FreeCAD
import FreeCADGui as Gui
import Part

V = FreeCAD.Vector
NEUES_FENSTER = True  # „Bearbeitung“ in Schritten


def _hoehe(text):
    """Die Zahl aus „… bis 1,3 mm …“ – oder None."""
    treffer = re.search(r"bis (\d+(?:,\d+)?) mm", text)
    return float(treffer.group(1).replace(",", ".")) if treffer else None


def _gerechnet(h, panel):
    def fertig():
        return not panel.vorschau_laeuft() and all(
            b.vorschau is not None or not b.aktiv() for b in panel.bloecke
        )

    yield 1000
    yield from h.warte_auf(fertig, 300000)
    yield 2000


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import gui_bearbeitung
    from camaddon import gui_bearbeitung_beta as beta
    from camaddon import schlichten3d as s3op
    from camaddon import werkzeuge as wz

    t3 = wz.Werkzeug(nummer=3, name="Kugel 6", art=wz.KUGELFRAESER, durchmesser=6.0, schneiden=2,
                     schneidenlaenge=18.0, schneidstoff=wz.VHM)  # fmt: skip
    t3.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=0.3, vc=150.0, fz=0.05)]
    wz.Bibliothek([wz.standardwerkzeug(), t3]).speichern()
    doc = FreeCAD.newDocument("Kuppel")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Kuppel")
    teil.Shape = Part.makeSphere(20, V(0, 0, -10)).common(Part.makeBox(50, 50, 15, V(-25, -25, 0)))
    doc.recompute()
    kuppel = next(
        f"Face{i + 1}" for i, f in enumerate(teil.Shape.Faces) if isinstance(f.Surface, Part.Sphere)
    )
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, kuppel)
    yield 500
    gui_bearbeitung.nullpunkt_vorgeben(None)
    Gui.runCommand("CamAddon_Bearbeitung")
    yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not None, 60000)
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(isinstance(panel, beta.BetaPanel), f"nicht in Schritten: {type(panel).__name__}")
    if panel is None or panel.job is None:
        return
    panel.knopf_alles.click()
    yield 1500
    yield from _gerechnet(h, panel)

    # --- 1. Ohne Haken --------------------------------------------------------------------------
    block = panel.schlichten3d
    kasten = block.haken_felder.get("bodenrunde")
    h.pruefe(kasten is not None, "kein Haken „Runde auf dem Teilboden“")
    if kasten is None:
        return
    h.pruefe(block.aktiv() and block.fraeser().nummer == 3, "3D-Schlichten nicht mit T3")
    h.pruefe(not kasten.isHidden() and kasten.isEnabled(), "Haken verborgen trotz Rest")
    h.pruefe(not kasten.isChecked(), "Haken vorbelegt an")
    h.pruefe(kasten.text() == "Zum Schluss eine Runde auf dem Teilboden", f"{kasten.text()!r}")
    h.pruefe(panel.restschlichten.haken_felder["bodenrunde"].isHidden(), "Haken im Restschlichten")
    ohne = block.vorschau
    h.pruefe(getattr(ohne, "bodenrunden", None) == 0, "ohne Haken eine Runde")
    satz_ohne = block.ergebnis.text()
    vorher = _hoehe(satz_ohne)
    print(ascii(f"ohne: {satz_ohne!r}"), flush=True)
    panel.seite_zeigen(beta.abschnitt(block) + beta.ERSTER_ABSCHNITT)
    yield 800
    panel._beta_werte["schlichten3d"][2].setChecked(True)  # „Werte ändern“ aufklappen
    yield 1500
    h.pruefe(kasten.isVisible(), "Haken unter „Werte ändern“ nicht zu sehen")
    h.bild("1_ohne", panel.form)

    # --- 2. Mit Haken ---------------------------------------------------------------------------
    kasten.setChecked(True)
    yield from _gerechnet(h, panel)
    mit = block.vorschau
    satz_mit = block.ergebnis.text()
    nachher = _hoehe(satz_mit)
    print(ascii(f"mit: {satz_mit!r}"), flush=True)
    h.pruefe(getattr(mit, "bodenrunden", None) == 1, f"Runden: {getattr(mit, 'bodenrunden', None)}")
    if mit is not None and getattr(mit, "bodenrunden", 0):
        tief = min(p.z for p in mit.punkte)
        h.pruefe(abs(tief) < 1e-6, f"tiefste Spitze {tief}")
        print(ascii(f"Zeit: {ohne.zeit:.2f} -> {mit.zeit:.2f} min"), flush=True)
    h.pruefe(
        vorher is not None and nachher is not None and nachher < vorher,
        f"Rest an der Unterkante: {vorher} -> {nachher}",
    )
    h.pruefe(not kasten.isHidden(), "Haken nach dem Anhaken verborgen")
    h.bild("2_mit", panel.form)
    panel.seite_zeigen(beta.UEBERSICHT)
    yield 800
    panel._uebersicht_verweis(beta.ZEIGE + "schlichten3d")
    yield 800
    Gui.activeDocument().activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("3_teil")
    panel._uebersicht_verweis(beta.ZEIGE + "schlichten3d")  # wieder alle
    yield 500

    # --- 3. Anlegen -----------------------------------------------------------------------------
    job = panel.job
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    yield from h.warte_auf(lambda: not doc.isTouched(), 300000)
    ops = [o for o in job.Operations.Group if s3op.ist_schlichten3d(o)]
    h.pruefe(len(ops) == 1, f"Operationen: {[o.Label for o in job.Operations.Group]}")
    if ops:
        op = ops[0]
        h.pruefe(op.Bodenrunde is True, "Operation ohne Runde auf dem Teilboden")
        z, auf_null, tiefste = 99.0, 0, 99.0
        for b in op.Path.Commands:
            z = float(b.Parameters.get("Z", z))
            if b.Name in ("G1", "G01"):
                tiefste = min(tiefste, z)
                auf_null += abs(z) < 1e-3
        print(ascii(f"{op.Label}: {auf_null} Sätze auf Z 0, tiefste {tiefste:.4f}"), flush=True)
        h.pruefe(auf_null > 50 and tiefste > -1e-3, f"{auf_null} Sätze auf Z 0, tiefste {tiefste}")
    fertig = beta.FertigFenster.offen
    if fertig is not None:
        yield from h.warte_auf(lambda: fertig.fertig, 120000)
        fertig.close()
    Gui.Selection.clearSelection()
    Gui.activeDocument().activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("4_angelegt")
    FreeCAD.closeDocument(doc.Name)
