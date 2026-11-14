# „Dichtnut hobeln“ (hobeln, hobeln_bahn; Spezifikation Strategien 13.10) am Beispielteil
# beispiele/dichtnut_deckel.FCStd: Deckel 120 × 90 × 12, O-Ring-Nut 3,6 × 2,7 (Mittellinie Rechteck
# 84 × 59 mit R 12), vier Bohrungen Ø 6,6. In der Werkzeugverwaltung nur die Testkiste (kein Fräser
# passt in die Nut). Angeklickt: der Grund der Nut und die Bohrungen.
# Aus dem Vollen (Manuel, 2026-11-14: „das hobeln sollte auch bei nicht vor gefraeseter Nut
# funktionieren oder?? Also das ja Sinn der Sache das man es nicht fräst“): Die Nut wird so nicht
# fertig, unten steht der Knopf „Stoßwerkzeug b 3,5 × 0,8 anlegen“ – vorher ist „Dichtnut hobeln“
# nie von sich aus angehakt, der Knopf hakt es an. Dann fräst nichts in der Nut (Räumen tritt nicht
# an), die Zustellung kommt vom Werkzeug, die Zeit steht im Block. Der Haken „Vorher fräsen, Rest
# hobeln“ gibt dem Räumen die Nut zurück (mit Rest am Grund), aus wieder nicht. „Anlegen“: Hobeln
# ab der Oberkante des Rohteils, keine Operation fräst in der Nut, die Bohrungen gehen durch.
# Programm Siemens: SPOS je Satz, beim Hobeln keine Spindel an.
# Bilder: 1_angebot (der Knopf), 2_hobeln (der Block), 3_vorschau (die Bahn im Teil),
# 2b_vorfraesen (mit dem Haken), 4_uebersicht, 5_angelegt.
# ZEITLIMIT: 1500
import os
import re

import FreeCAD
import FreeCADGui as Gui

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
    from camaddon import gui_bearbeitung
    from camaddon import gui_bearbeitung_beta as beta
    from camaddon import hobeln as hop
    from camaddon import hobeln_bahn as hb
    from camaddon import kontur as ko
    from camaddon import planfraesen as pf
    from camaddon import postprozessor as pp
    from camaddon import raeumen as ra
    from camaddon import werkzeuge as wz

    wz.Bibliothek(list(wz.testkiste())).speichern()  # T1–T4 wie immer
    datei = os.path.join(camaddon.ADDON_ORDNER, "beispiele", "dichtnut_deckel.FCStd")
    doc = FreeCAD.openDocument(datei)
    doc.UndoMode = 1
    yield 1500
    teil = doc.getObject("Deckel")
    nuten = hb.hobelnuten(teil.Shape)
    h.pruefe(len(nuten) == 1, f"Dichtnuten im Beispielteil: {[n.name for n in nuten]}")
    nut = nuten[0]
    bohrungen = [
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if f.Surface.__class__.__name__ == "Cylinder" and f.BoundBox.ZLength > 11.0
    ]
    h.pruefe(len(bohrungen) == 4, f"Bohrungen: {bohrungen}")
    Gui.activateWorkbench("CAMWorkbench")
    for name in [nut.name] + bohrungen:
        Gui.Selection.addSelection(doc.Name, teil.Name, name)
    yield 500
    gui_bearbeitung.nullpunkt_vorgeben(None)
    Gui.runCommand("CamAddon_Bearbeitung")
    yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not None, 60000)
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(isinstance(panel, beta.BetaPanel), f"nicht in Schritten: {type(panel).__name__}")
    if panel is None or panel.job is None:
        return
    job = panel.job
    form = teil.Shape

    def fertig_gerechnet():
        return not panel.vorschau_laeuft() and all(
            b.vorschau is not None or not b.aktiv() for b in panel.bloecke
        )

    yield from h.warte_auf(fertig_gerechnet, 300000)
    yield 1500
    block = panel.hobeln
    h.pruefe(not block.moeglich, "Dichtnut hobeln ohne Stoßwerkzeug möglich")
    h.pruefe(not block.aktiv(), "Dichtnut hobeln von sich aus angehakt")
    # Kein Fräser passt in die Nut, kein Stoßwerkzeug: der Knopf, der eins anlegt.
    satz, knopf = panel.unfertig_satz.text(), panel.unfertig_knopf.text()
    print("HOBELN Angebot", repr(satz), repr(knopf), flush=True)
    h.pruefe(not panel.unfertig_angebot.isHidden(), "kein Angebot unten")
    h.pruefe("Stoßwerkzeug" in satz, f"Satz: {satz!r}")
    h.pruefe(knopf == "Stoßwerkzeug b 3,5 × 0,8 anlegen", f"Knopf: {knopf!r}")
    h.bild("1_angebot", panel.form)

    panel.unfertig_knopf.click()
    yield 1500
    yield from h.warte_auf(fertig_gerechnet, 300000)
    yield 1500
    stoss = [w for w in panel.bibliothek.werkzeuge if w.art == wz.STOSSWERKZEUG]
    oben = float(pf.rohteil_von_oben(job)[4])
    tiefe = oben - nut.z_boden
    h.pruefe(
        len(stoss) == 1
        and abs(stoss[0].schneidenbreite - 3.5) < 1e-9
        and abs(stoss[0].klingenlaenge - 0.8) < 1e-9
        and stoss[0].stechtiefe >= tiefe + hop.STECHTIEFE_SICHER,
        f"Stoßwerkzeug: {stoss}, Nut {tiefe:.2f} tief ab dem Rohteil",
    )
    h.pruefe(
        bool(stoss) and any(e.art == wz.HOBELN for e in stoss[0].einsaetze("P1")),
        f"Stoßwerkzeug ohne Richtwerte: {stoss[0].schnittwerte if stoss else None}",
    )
    h.pruefe(block.moeglich, f"Dichtnut hobeln nicht möglich: {block.erklaerung.text()!r}")
    h.pruefe(block.aktiv(), "der Knopf hakt „Dichtnut hobeln“ nicht an")
    h.pruefe(not block.haken_felder["vorfraesen"].isChecked(), "Vorfräsen von sich aus an")
    h.pruefe(
        panel.unfertig_angebot.isHidden(), f"noch ein Angebot: {panel.unfertig_knopf.text()!r}"
    )
    # Aus dem Vollen: In der Nut fräst nichts – das Räumen hat keine Fläche mehr.
    print("HOBELN Räumen", panel.raeumen.moeglich, panel.raeumen.aktiv(),
          repr(panel.raeumen.erklaerung.text()), flush=True)  # fmt: skip
    h.pruefe(not panel.raeumen.aktiv(), "Räumen fräst in der Nut")
    for b in (panel.raeumen, panel.schlichten_danach, panel.kontur):
        h.pruefe(
            not set(panel._flaechen(b, form)) & set(nut.flaechen),
            f"{b.s.titel()}: {panel._flaechen(b, form)}",
        )
    # Die Zustellung vom Werkzeug: das ap seines Einsatzes „Hobeln“ (Richtwert 0,08 × fz-Faktor).
    ap = float(getattr(block.einsatz(), "ap", 0.0) or 0.0)
    print("HOBELN Zustellung", block.wert("zustellung"), ap, flush=True)
    h.pruefe(ap > 0 and abs(block.wert("zustellung") - ap) < 1e-9, f"Zustellung {ap}")
    text = block.ergebnis.text()
    print("HOBELN Block", repr(text), repr(block.hinweis.text()), flush=True)
    h.pruefe(nut.name in text and "Umläufe" in text, f"Ergebnis: {text!r}")
    h.pruefe(not block.hinweis.text(), f"rot: {block.hinweis.text()!r}")
    if block.vorschau is not None:
        umlaeufe = block.vorschau.je_nut[0]["umlaeufe"]
        soll = int(-(-round(tiefe, 6) // ap)) + 2  # bis zum Grund, eben, ein Leerumlauf
        print("HOBELN Umläufe", umlaeufe, soll, block.vorschau.zeit, flush=True)
        h.pruefe(umlaeufe == soll, f"Umläufe {umlaeufe} statt {soll}")
    h.pruefe(not panel.unfertig.isVisible(), "noch „Nicht fertig“")
    panel.seite_zeigen(beta.abschnitt(block) + beta.ERSTER_ABSCHNITT)
    yield 800
    h.bild("2_hobeln", panel.form)
    panel._block_zeigen(block)
    yield 1500
    Gui.activeDocument().activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("3_vorschau")

    # „Vorher fräsen, Rest hobeln“: Das Räumen bekommt die Nut zurück und lässt den Rest am Grund.
    block.haken_felder["vorfraesen"].setChecked(True)
    yield 1500
    h.pruefe(nut.name in panel._flaechen(panel.raeumen, form), "Vorfräsen: Räumen ohne die Nut")
    # Der Rest am Grund nur zwischen fertigen Wänden: Ohne „Schlichten danach“ haben sie das
    # Aufmaß des Räumens – dann kein Rest (der Block ist rot und bietet es an).
    rest = panel._hobel_reste(form)
    wand = panel._hobel_wand_aufmass(form)
    print("HOBELN Vorfräsen", rest, wand, flush=True)
    h.pruefe(
        rest == ((nut.name, hop.REST),) if wand <= 0 else rest == (),
        f"Vorfräsen: Rest {rest}, Wandaufmaß {wand}",
    )
    panel.seite_zeigen(beta.abschnitt(block) + beta.ERSTER_ABSCHNITT)
    yield 800
    h.bild("2b_vorfraesen", panel.form)
    block.haken_felder["vorfraesen"].setChecked(False)
    yield 1500
    yield from h.warte_auf(fertig_gerechnet, 300000)
    yield 1500
    h.pruefe(not panel.raeumen.aktiv(), "nach dem Vorfräsen fräst das Räumen weiter in der Nut")

    panel.seite_zeigen(beta.UEBERSICHT)
    yield 1500
    h.pruefe("Dichtnut hobeln" in panel.uebersicht_text.text(), "Hobeln fehlt in der Übersicht")
    h.bild("4_uebersicht", panel.form)
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    yield from h.warte_auf(lambda: not doc.isTouched(), 300000)
    ops = list(job.Operations.Group)
    namen = [o.Label for o in ops]
    print("HOBELN Operationen", namen, flush=True)
    hobeln = [o for o in ops if hop.ist_hobeln(o)]
    h.pruefe(len(hobeln) == 1 and hobeln[0].Nuten == 1, f"Operationen: {namen}")
    if hobeln:
        o = hobeln[0]
        print("HOBELN Operation", float(o.StartDepth), bool(o.Vorgefraest), float(o.Zustellung),
              flush=True)  # fmt: skip
        h.pruefe(
            not o.Vorgefraest
            and abs(float(o.StartDepth) - oben) < 1e-6
            and abs(float(o.Zustellung) - ap) < 1e-9,
            f"Operation: ab {float(o.StartDepth)}, vorgefräst {o.Vorgefraest}, {o.Zustellung}",
        )
    # In der Nut fräst nichts.
    for o in ops:
        if ra.ist_raeumen(o) or ko.ist_kontur(o):
            h.pruefe(not set(o.Flaechen) & set(nut.flaechen), f"{o.Label} fräst in der Nut")

    def tiefste(op):
        hoehen = [
            float(c.Parameters["Z"])
            for c in op.Path.Commands
            if c.Name in ("G1", "G01", "G2", "G02", "G3", "G03") and "Z" in c.Parameters
        ]
        return min(hoehen) if hoehen else None

    # Die Bohrungen gehen durch – auf Maß.
    durch = [o for o in ops if set(getattr(o, "Flaechen", []) or []) & set(bohrungen)]
    durch += [o for o in ops if "Bohr" in o.Label and o not in durch]
    h.pruefe(durch, f"keine Operation an den Bohrungen: {namen}")
    for o in durch:
        print("HOBELN Bohrung", o.Label, tiefste(o), float(o.FinalDepth), flush=True)
        h.pruefe(float(o.FinalDepth) <= 1e-6, f"{o.Label}: nicht durch ({float(o.FinalDepth)})")

    # Das Programm für Siemens: je Satz SPOS, beim Hobeln keine Spindel an.
    programm = pp.programm(pp.abschnitte(job), pp.steuerung("siemens"), None, "Deckel")
    zeilen = programm.zeilen
    spos = [i for i, z in enumerate(zeilen) if "SPOS=DC(" in z]
    h.pruefe(len(spos) > 100, f"nur {len(spos)} SPOS")
    if spos:
        wechsel = [i for i, z in enumerate(zeilen) if "M6" in z.split()]
        anfang = max([i for i in wechsel if i < spos[0]], default=0)
        ende = min([i for i in wechsel if i > spos[0]], default=len(zeilen))
        hobel = zeilen[anfang:ende]
        an = [z for z in hobel if {"M3", "M03", "M4", "M04"} & set(z.split())]
        s_wort = [z for z in hobel if re.search(r"(^|\s)S\d", z)]
        print("HOBELN Programm", len(zeilen), zeilen[anfang : anfang + 4], zeilen[spos[0]],
              flush=True)  # fmt: skip
        h.pruefe(not an and not s_wort, f"Spindel beim Hobeln: {(an + s_wort)[:3]}")

    fertig = beta.FertigFenster.offen
    if fertig is not None:
        yield from h.warte_auf(lambda: fertig.fertig, 120000)
        fertig.close()
    Gui.Selection.clearSelection()
    Gui.activeDocument().activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("5_angelegt")
    FreeCAD.closeDocument(doc.Name)
    yield 300
