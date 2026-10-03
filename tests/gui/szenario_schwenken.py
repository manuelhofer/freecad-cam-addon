# „Ebene schwenken (3+2) …“ (W-014 F5): ein Block 100 × 60 × 40 mit einer 30°-Schräge vorn
# oben, gespannt im Grundjob, die 5-Achs-Beispielmaschine Tisch/Tisch gespeichert und am Job.
# Die Schräge angeklickt, der Befehl: Das Fenster nennt Grundjob und Maschine und grün „Face…:
# 30° geschwenkt → A−30 C0“. „OK“ legt den Job der Ebene an und öffnet den Assistenten
# „Bearbeitung“ darin, die Schräge gewählt; „Anlegen“ fräst sie. Das Programm des Grundjobs hat
# die Ebene mit CYCLE800 (Siemens) und mit „G0 A-30.000 C0.000“ ohne Zyklus (LinuxCNC).
import math
import os
import tempfile

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

    import Path.Main.Job as PathJob

    from camaddon import beispielmaschine, gui_bearbeitung, gui_schwenken
    from camaddon import postprozessor as pp
    from camaddon import reichweite as rw
    from camaddon import schwenken as sw
    from camaddon import uebergabe_werkzeuge as ue
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    ordner = tempfile.mkdtemp()
    asm, _maschine = beispielmaschine.lade(beispielmaschine.TISCH_TISCH)
    pfad_maschine = os.path.join(ordner, "fuenfachs.FCStd")
    asm.Document.saveAs(pfad_maschine)
    yield 300
    bibliothek = wz.Bibliothek([wz.standardwerkzeug()])
    bibliothek.speichern()
    ue.uebergeben(bibliothek)

    t = math.tan(math.radians(30.0))
    keil = Part.Face(
        Part.makePolygon(
            [
                V(-1, -1, 25 - t),
                V(-1, 27, 25 + 27 * t),
                V(-1, 27, 60),
                V(-1, -1, 60),
                V(-1, -1, 25 - t),
            ]
        )
    ).extrude(V(102, 0, 0))
    doc = FreeCAD.newDocument("Schraege")
    block = doc.addObject("Part::Feature", "Block")
    block.Shape = Part.makeBox(100, 60, 40).cut(keil).removeSplitter()
    doc.recompute()
    FreeCAD.setActiveDocument(doc.Name)
    grundjob = PathJob.Create("Job", [block])
    grundjob.Label = "Job Block"
    grundjob.Stock.ExtZpos = 1.0
    doc.recompute()
    rw.merke_maschine(grundjob, pfad_maschine)
    doc.saveAs(os.path.join(ordner, "schraege.FCStd"))
    klon = vr.modell(grundjob)
    schraege = next(
        f"Face{i + 1}"
        for i, f in enumerate(klon.Shape.Faces)
        if sw.aussennormale(f) is not None and abs(sw.aussennormale(f).y + 0.5) < 1e-6
    )
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, klon.Name, schraege)
    yield 300

    # --- Das Fenster ---------------------------------------------------------------------------
    Gui.runCommand("CamAddon_Schwenken")
    yield 1000
    panel = gui_schwenken.SchwenkenPanel.offen
    h.pruefe(panel is not None, "„Ebene schwenken“ öffnet kein Fenster")
    if panel is None:
        return
    h.pruefe(panel.grundjob is grundjob, "Grundjob")
    h.pruefe("Tisch/Tisch" in panel.maschine_text.text() or "5-Achs" in panel.maschine_text.text(),
             f"Maschine: {panel.maschine_text.text()!r}")  # fmt: skip
    text = panel.ergebnis.text()
    h.pruefe(text == f"{schraege}: 30° geschwenkt → A−30 C0", f"Ergebnis: {text!r}")
    h.bild("1_fenster")

    # --- OK: der Job der Ebene, der Assistent darin ---------------------------------------------
    h.pruefe(panel.accept() is True, "„OK“ ging nicht")
    yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not None, 15000)
    ebenen = sw.ebenen_von(grundjob)
    h.pruefe(len(ebenen) == 1, f"Ebenen: {[e.Label for e in ebenen]}")
    if not ebenen:
        return
    planjob = ebenen[0]
    h.pruefe(planjob.Rundachsen == "A−30 C0", f"Rundachsen am Job: {planjob.Rundachsen!r}")
    assistent = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(assistent is not None and assistent.job is planjob, "Assistent nicht im Job der Ebene")
    if assistent is None:
        return
    h.pruefe(assistent.gewaehlte == [schraege], f"gewählt: {assistent.gewaehlte}")
    yield from h.warte_auf(lambda: assistent.raeumen.vorschau is not None, 60000)
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("2_assistent_in_der_ebene")
    h.pruefe(assistent.accept() is True, "„Anlegen“ ging nicht")
    yield 2000
    ops = list(planjob.Operations.Group)
    h.pruefe(ops, "keine Operation in der Ebene")
    h.pruefe(
        vr.modell(planjob).ViewObject.Visibility and not block.ViewObject.Visibility,
        "nicht das Modell der Ebene sichtbar",
    )
    h.pruefe(planjob.getPropertyByName(rw.EIGENSCHAFT_MASCHINE) == pfad_maschine, "Maschine")
    Gui.Selection.clearSelection()
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("3_angelegt")

    # --- Das Programm des Grundjobs ----------------------------------------------------------------
    teile = pp.abschnitte(grundjob)
    siemens = pp.programm(teile, pp.steuerung("siemens"), pp.Maschineninfo("5-Achs"), "Block").text
    h.pruefe('CYCLE800(1,"",0,27,' in siemens and "CYCLE800()" in siemens, "Siemens ohne CYCLE800")
    lcnc = pp.programm(teile, pp.steuerung("linuxcnc"), pp.Maschineninfo("5-Achs"), "Block").text
    h.pruefe("G0 A-30.000 C0.000" in lcnc and "G0 A0.000 C0.000" in lcnc, "LinuxCNC ohne A, C")

    # --- Auf der Maschine prüfen: der Grundjob mit der Ebene auf der 5-Achs-Fräse --------------------
    from PySide import QtCore

    from camaddon import gui_reichweite

    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(grundjob)
    yield 400
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None, 30000)
    pruefung = gui_reichweite.PruefPanel.offen
    h.pruefe(pruefung is not None, "„Auf der Maschine prüfen“ öffnet kein Fenster")
    if pruefung is None:
        return
    yield 1000
    spieler = pruefung.abspieler
    # In der Auswahl steht bei einer Operation der Ebene „… – Ebene A−30 C0“; gesucht wird nach
    # dem Namen in der Abfahrt.
    namen = [o.name for o in spieler.abfahrt.operationen]
    texte = [spieler.wahl_operation.itemText(i) for i in range(spieler.wahl_operation.count())]
    h.pruefe(ops and ops[0].Label in namen, f"Operation der Ebene nicht im Abspieler: {namen}")
    h.pruefe(ops and f"{ops[0].Label} – Ebene A−30 C0" in texte, f"Auswahl ohne die Ebene: {texte}")
    h.bild("4c_pruefen_fenster", pruefung.form)
    if ops and ops[0].Label in namen:
        spieler.springe_zu_operation(namen.index(ops[0].Label))
        yield 300
        fahrt = spieler.abfahrt if hasattr(spieler, "abfahrt") else None
        nummer = namen.index(ops[0].Label)
        stationen = (
            [i for i, s in enumerate(fahrt.stationen) if s.operation == nummer and not s.ziel]
            if fahrt is not None
            else []
        )
        if stationen:
            spieler.springe_zu_station(stationen[len(stationen) // 2])
            yield 500
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("4_auf_der_maschine")
    spieler.knopf_hinsehen.click()
    yield 500
    h.bild("4b_auf_der_maschine_nah")

    # --- Im Assistenten des Grundjobs: die Schräge gewählt → „Ebene schwenken (3+2) …“ -----------
    # Die Liste sagt „30° schräg“, darunter die Zeile mit dem Knopf; er schließt den Assistenten
    # und öffnet „Ebene schwenken“ mit der Fläche.
    pruefung.reject()
    yield 800
    Gui.Control.showDialog(
        gui_bearbeitung.BearbeitungPanel(doc, (block, schraege), angeklickt=klon)
    )
    yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not None, 15000)
    a = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(a is not None and a.job is grundjob, "Assistent nicht im Grundjob")
    if a is None:
        return
    if schraege not in a.gewaehlte:
        a.flaeche_umschalten(schraege)
    a.seite_zeigen(1)
    yield 800
    h.pruefe(
        not a.schwenken_zeile.isHidden() and not a.schwenken_knopf.isHidden(),
        "Assistent: keine Zeile „geschwenkt fräsen“",
    )
    h.pruefe("30° schräg" in a.schwenken_text.text(), f"Assistent: {a.schwenken_text.text()!r}")
    # Im Grundjob nur sein Teil und seine Bahnen – die Ebene hat ihr Teil anders gedreht.
    h.pruefe(
        klon.ViewObject.Visibility
        and grundjob.Operations.ViewObject.Visibility
        and not vr.modell(planjob).ViewObject.Visibility
        and not planjob.Operations.ViewObject.Visibility,
        "Assistent im Grundjob: das Teil der Ebene im Bild",
    )
    Gui.SendMsgToActiveView("ViewFit")
    yield 300
    h.bild("5_assistent_schraeg")
    a.schwenken_knopf.click()
    yield from h.warte_auf(lambda: gui_schwenken.SchwenkenPanel.offen is not None, 15000)
    zweites = gui_schwenken.SchwenkenPanel.offen
    h.pruefe(
        zweites is not None
        and zweites.flaeche == schraege
        and "A−30 C0" in zweites.ergebnis.text()
        and "gibt es schon" in zweites.ergebnis.text()
        and zweites.vorhanden is planjob,
        "„Ebene schwenken“ aus dem Assistenten: "
        + (zweites.ergebnis.text() if zweites is not None else "kein Fenster"),
    )
    h.bild("6_schwenken_aus_assistent")
    # OK legt keinen zweiten Job an, sondern öffnet den Assistenten in der vorhandenen Ebene.
    if zweites is not None:
        zweites.accept()
        yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not None, 15000)
        h.pruefe(len(sw.ebenen_von(grundjob)) == 1, f"Ebenen: {len(sw.ebenen_von(grundjob))}")
        dritter = gui_bearbeitung.BearbeitungPanel.offen
        h.pruefe(dritter is not None and dritter.job is planjob, "Assistent nicht in der Ebene")
        if dritter is not None:
            dritter.reject()
            yield 500

    # --- Bestückung: Grundjob und Ebene sind eine Aufspannung, ein Programm ---------------------
    from camaddon import gui_bestueckung

    yield 500
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, grundjob.Name)
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_Bestueckung"))
    yield from h.warte_auf(lambda: gui_bestueckung.BestueckungsPanel.offen is not None, 15000)
    b = gui_bestueckung.BestueckungsPanel.offen
    h.pruefe(b is not None, "Bestückung öffnet kein Fenster")
    if b is not None:
        yield 500
        h.pruefe(
            not b.aufspannung.isHidden() and planjob.Label in b.aufspannung.text(),
            f"Bestückung: {b.aufspannung.text()!r}",
        )
        h.bild("7_bestueckung", b.form)
        b.reject()

    # --- Ebene aus Winkeln: 15° geneigt, der Kopf nach +Y (angestellter Kugelfräser) -----------
    Gui.Control.showDialog(gui_schwenken.SchwenkenPanel(grundjob))
    yield 500
    w = gui_schwenken.SchwenkenPanel.offen
    h.pruefe(w is not None, "„Ebene schwenken“ ohne Fläche öffnet nicht")
    if w is not None:
        w.feld_neigung.setValue(15.0)
        w.feld_richtung.setValue(90.0)
        w.winkel_nehmen()
        yield 300
        h.pruefe(
            w.ergebnis.text() == "15° nach 90°: 15° geschwenkt → A15 C0",
            f"aus Winkeln: {w.ergebnis.text()!r}",
        )
        h.bild("8_aus_winkeln", w.form)
        w.haken_bearbeiten.setChecked(False)
        h.pruefe(w.accept() is True, "„OK“ aus Winkeln ging nicht")
        yield 800
        neu = [e for e in sw.ebenen_von(grundjob) if e.Flaeche == ""]
        h.pruefe(
            len(neu) == 1 and neu[0].Rundachsen == "A15 C0", f"Ebenen: {[e.Label for e in neu]}"
        )
