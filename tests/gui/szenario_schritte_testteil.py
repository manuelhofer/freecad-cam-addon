# Manuels Testteil für die 3-Achs-Fräse (W-013) in den Schritten – „Bearbeitung“ ist seit 0.350.0 der
# Assistent in Schritten (Manuel, 2026-11-07: „definitiv“). Wie szenario_testteil (dort das alte
# Fenster): beispiele/testteil_3achs_fraese.FCStd, alle Flächen gewählt. Schritt 1 „Liegt wie im
# Modell“, Schritt 2 die Flächen und „Ganze Tasche nehmen“ – das nimmt die runde Wand Face12 und
# ihren Boden dazu, die im alten Szenario nicht gewählt sind. Dann „Weiter“ durch alle Schritte,
# „Anlegen“ am Ende: die Arbeitsschritte des alten Fensters, je Schritt geordnet (erst Schruppen,
# dann Löcher, dann Schlichten), dazu „Bohrung fräsen“ für Face12 – Räumen T1, Räumen T3, Kontur
# T1, 3D-Schruppen T1, Bohrung fräsen T1, Restmaterial T3, 3D-Schlichten T5. „Auf der Maschine
# prüfen“: nirgends ins Teil.
# ZEITLIMIT: 900
import os

import FreeCAD
import FreeCADGui as Gui
import Part
from PySide import QtCore

NEUES_FENSTER = True  # „Bearbeitung“ in Schritten


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    import camaddon
    from camaddon import beispielmaschine, gui_bearbeitung, gui_reichweite
    from camaddon import gui_bearbeitung_beta as beta
    from camaddon import hoehenfeld as hf
    from camaddon import kontur as ko
    from camaddon import kontur_bahn as kb
    from camaddon import raeumen as ra
    from camaddon import restmaterial as rm
    from camaddon import schlichten3d as s3op
    from camaddon import schruppen3d as r3op
    from camaddon import werkzeuge as wz

    kugel = wz.Werkzeug(nummer=5, name="Kugel 8", art=wz.KUGELFRAESER, durchmesser=8.0, schneiden=2,
                        schneidenlaenge=16.0, schneidstoff=wz.VHM)  # fmt: skip
    kugel.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=0.3, vc=150.0, fz=0.05)]
    fase = wz.Werkzeug(nummer=6, name="Fase 90", art=wz.FASENFRAESER, durchmesser=10.0, schneiden=2,
                       schneidenlaenge=5.0, spitzenwinkel=90.0, spitzen_d=0.0, schneidstoff=wz.VHM)  # fmt: skip
    fase.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.FASEN, vc=100.0, fz=0.05)]
    wz.Bibliothek([*wz.testkiste(), kugel, fase]).speichern()

    datei = os.path.join(camaddon.ADDON_ORDNER, "beispiele", "testteil_3achs_fraese.FCStd")
    doc = FreeCAD.openDocument(datei)
    doc.UndoMode = 1
    yield 1500
    teil = doc.getObject("Body")
    form = teil.Shape
    ebenen = {round(e.z): e.name for e in hf.ebenen_oben(form) if e.x_bis - e.x_von > 1.0}
    h.pruefe(sorted(ebenen) == [10, 22, 27, 32], f"ebene Flächen: {ebenen}")
    mulde = next(
        f"Face{i + 1}"
        for i, f in enumerate(form.Faces)
        if isinstance(f.Surface, (Part.Toroid, Part.Sphere))
    )
    namen = [f"Face{i + 1}" for i in range(len(form.Faces))]
    waende = [
        w.name for w in kb.waende(form, namen) if w.z_unten > 9.0 and w.z_oben - w.z_unten > 1
    ]
    h.pruefe(len(waende) == 14, f"Wände: {waende}")
    Gui.activateWorkbench("CAMWorkbench")
    Gui.activeDocument().activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("0_teil")
    Gui.Selection.addSelection(doc.Name, teil.Name, ebenen[10])
    yield 500

    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2500
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    h.pruefe(isinstance(panel, beta.BetaPanel), f"nicht in Schritten: {type(panel).__name__}")
    panel.wie_modelliert()
    yield 300
    panel.knopf_weiter.click()
    yield 1500
    h.pruefe(panel.seite() == 1, f"Seite {panel.seite()} statt der Flächen")
    for name in [ebenen[22], ebenen[32], ebenen[27], mulde, *waende]:
        panel.flaeche_umschalten(name)
    yield 1000
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 300000)
    yield 1000
    h.pruefe(panel.tasche_box.isVisible(), "keine Frage nach der ganzen Tasche")
    # Die Frage nach der Reihenfolge gibt es in den Schritten nicht – sie lag quer über der Liste.
    h.pruefe(not panel.frage_reihenfolge.widget.isVisible(), "die Frage „Reihenfolge“ ist zu sehen")
    h.bild("1_flaechen", panel.form)
    if panel.tasche_box.isVisible():
        panel.knopf_ganze_tasche.click()
        yield 1500
    seiten = [panel.seite()]
    for _schritt in range(8):
        if not (panel.knopf_weiter.isVisible() and panel.knopf_weiter.isEnabled()):
            break
        panel.knopf_weiter.click()
        yield 1500
        yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 600000)
        yield 1000
        seiten.append(panel.seite())
        h.bild(f"1_seite_{panel.seite()}", panel.form)
    h.pruefe(seiten == [1, 2, 3, 4, 5], f"Schritte: {seiten}")
    yield from h.warte_auf(
        lambda: not panel.vorschau_laeuft()
        and all(b.vorschau is not None or not b.aktiv() for b in panel.bloecke),
        600000,
    )
    yield 4000
    raeumen, kontur = panel.raeumen, panel.kontur
    r3, s3 = panel.schruppen3d, panel.schlichten3d
    h.pruefe(raeumen.aktiv() and raeumen.fraeser().nummer == 1, "Räumen: kein Haken oder nicht T1")
    h.pruefe(
        raeumen.ergebnis.text().startswith("→ 3 Flächen: 3 Lagen"), f"{raeumen.ergebnis.text()!r}"
    )
    # Die tiefste Fläche zuerst, jede Stelle einmal: unter 13 min (das Ziel sind 8).
    h.pruefe(raeumen.zeit is not None and raeumen.zeit < 13.0, f"Räumen: {raeumen.zeit} min")
    # In die dreieckige Tasche passt der Ø 12 nicht: Das Räumen sagt es (B-007), „Rest räumen“
    # nimmt sie mit dem größten Fräser, der hineinpasst (T3, Ø 6), „Restmaterial“ ihre Wände.
    rest_boden, rest_wand = panel.restraeumen, panel.rest
    satz = f"In die Tasche {ebenen[27]} passt der Ø 12 nicht – die räumt „Rest räumen“ mit T3."
    h.pruefe(satz in raeumen.ergebnis.text(), f"{raeumen.ergebnis.text()!r}")
    h.pruefe(
        rest_boden.aktiv() and rest_boden.fraeser().nummer == 3,
        "Rest räumen: kein Haken oder nicht T3",
    )
    h.pruefe(rest_boden.ergebnis.text().startswith("→ 1 Lage"), f"{rest_boden.ergebnis.text()!r}")
    h.pruefe(kontur.aktiv(), "Kontur: kein Haken")
    h.pruefe(
        rest_wand.aktiv() and rest_wand.fraeser().nummer == 3,
        "Restmaterial: kein Haken oder nicht T3",
    )
    h.pruefe(r3.aktiv() and r3.fraeser().nummer == 1, "3D-Schruppen: kein Haken oder nicht T1")
    h.pruefe(s3.aktiv() and s3.fraeser().nummer == 5, "3D-Schlichten: kein Haken oder nicht T5")
    # Wer davor schon etwas weggenommen hat: das Räumen – nicht das Planfräsen, das im Wettbewerb
    # den Haken verliert (B-009: Die Blöcke dahinter rechneten auf seinem Material).
    h.pruefe(not panel.plan.aktiv(), "Planfräsen: angehakt")
    for block in (rest_boden, r3):
        text = block.material.text()
        h.pruefe("„Räumen“" in text and "Planfräsen" not in text, f"{block.s.kennung}: {text!r}")
    rot = [(b.s.kennung, b.hinweis.text()) for b in panel.bloecke if b.aktiv() and b.hinweis.text()]
    h.pruefe(not rot, f"rot angehakt: {rot}")
    h.bild("1_letzter_schritt", panel.form)
    h.pruefe(panel.knopf_fertig.isEnabled(), f"Anlegen grau: {panel.anlegen_text.text()!r}")

    # --- Anlegen ------------------------------------------------------------------------------
    anlegen_text = panel.anlegen_text.text()
    h.pruefe(panel.accept() is True, f"„Anlegen“ ging nicht: {anlegen_text!r}")
    yield 3000
    for fenster in QtCore.QCoreApplication.instance().topLevelWidgets():
        if type(fenster).__name__ == "FertigFenster" and fenster.isVisible():
            h.bild("2a_angelegt_fenster", fenster)
            fenster.close()
    yield from h.warte_auf(lambda: not doc.isTouched(), 600000)
    yield 3000
    ops = list(job.Operations.Group)
    namen_ops = [o.Label for o in ops]
    bohrung = next((o for o in ops if o.Label.startswith("Bohrung")), None)
    h.pruefe(
        bohrung is not None and list(bohrung.Flaechen) == ["Face12"],
        f"Bohrung fräsen: {list(getattr(bohrung, 'Flaechen', []))}",
    )
    for art, pruefung in (
        ("Räumen", ra.ist_raeumen),
        ("Kontur", ko.ist_kontur),
        ("3D-Schruppen", r3op.ist_schruppen3d),
        ("3D-Schlichten", s3op.ist_schlichten3d),
    ):
        h.pruefe(any(pruefung(o) for o in ops), f"kein {art}: {namen_ops}")
    erwartet = [
        "Räumen T1", "Räumen T3", "Kontur T1", "3D-Schruppen T1", "Bohrung fräsen T1",
        "Restmaterial T3", "3D-Schlichten T5",
    ]  # fmt: skip
    h.pruefe(namen_ops == erwartet, f"Operationen: {namen_ops}")
    raeum_op = next((o for o in ops if ra.ist_raeumen(o)), None)
    if raeum_op is not None:
        h.pruefe(
            (raeum_op.Ebenen, raeum_op.Lagen) == (3, 3), f"{raeum_op.Ebenen}, {raeum_op.Lagen}"
        )
        # Die Höhen in der Reihenfolge der Bahn: die Platte (−23), die Insel (−11), die Stufe (−1).
        hoehen = []
        for befehl in raeum_op.Path.Commands:
            z = befehl.Parameters.get("Z")
            if befehl.Name not in ("G1", "G2", "G3") or z is None:
                continue
            auf_flaeche = any(abs(z - ziel) < 1e-6 for ziel in (-23.0, -11.0, -1.0))
            if auf_flaeche and (not hoehen or abs(hoehen[-1] - z) > 1e-6):
                hoehen.append(round(z, 3))
        h.pruefe(hoehen == [-23.0, -11.0, -1.0], f"Reihenfolge der Höhen: {hoehen}")
    Gui.Selection.clearSelection()
    Gui.activeDocument().activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 1000
    h.bild("2_angelegt")

    # --- Auf der Maschine prüfen ------------------------------------------------------------
    asm, _maschine = beispielmaschine.lade(beispielmaschine.FRAESE_3)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    yield 500
    FreeCAD.setActiveDocument(doc.Name)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400  # 1.1.3 verarbeitet die Auswahl verzögert
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None, 180000)
    pruef = gui_reichweite.PruefPanel.offen
    h.pruefe(pruef is not None, "„Auf der Maschine prüfen“ öffnet kein Fenster")
    if pruef is None:
        return
    yield 1500
    spieler = pruef.abspieler
    h.pruefe(spieler.abfahrt.dauer < 17.0 * 60.0, f"Abfahrt: {spieler.abfahrt.dauer / 60:.1f} min")
    spieler.setze_zeit(spieler.abfahrt.dauer)
    yield from h.warte_auf(lambda: spieler.rest.text().startswith("Am Ende"), 600000)
    rest = spieler.rest.text()
    h.pruefe(rest.startswith("Am Ende bleiben") and "nirgends ins Teil" in rest, f"{rest!r}")
    # Stehen bleiben nur die beiden spitzen Ecken der Tasche, 5 tief – dorthin kommt kein Fräser
    # der Kiste (zusammen 11 mm²). B-008: Zwei Zellen, um ein Haar neben einer Wand, zählten als
    # 12 und 10 mm Rest.
    vergleich = pruef.bild.abtrag.vergleich()
    rot = int((vergleich.farbe == rm.ROT).sum())
    h.pruefe(
        vergleich.groesster < 5.01 and 0 < rot <= 60,
        f"Rest: bis {vergleich.groesster:.2f} mm, {rot} rote Zellen – {rest!r}",
    )
    Gui.SendMsgToActiveView("ViewFit")
    spieler.knopf_hinsehen.click()
    yield 1500
    h.bild("3_pruefen_farben")
    pruef.reject()
    yield 500
    # Das Beispiel bleibt, wie es ist: nichts speichern.
    FreeCAD.closeDocument(doc.Name)
    yield 300
