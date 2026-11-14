# „Dichtnut hobeln“ (hobeln, hobeln_bahn; Spezifikation Strategien 13.10) am Beispielteil
# beispiele/dichtnut_deckel.FCStd: Deckel 120 × 90 × 12, O-Ring-Nut 3,6 × 2,7 (Mittellinie Rechteck
# 84 × 59 mit R 12), vier Bohrungen Ø 6,6. In der Werkzeugverwaltung die Testkiste und ein
# Schaftfräser Ø 3 (T5) für die Nut. Angeklickt: der Grund der Nut und die Bohrungen. Das Räumen
# bekommt den Ø 3, „Schlichten danach“ macht die Wände fertig. Ohne Stoßwerkzeug steht unten der
# Knopf „Stoßwerkzeug b 3,5 × 1,1 anlegen“; danach ist „Dichtnut hobeln“ angeboten, aber nicht
# angehakt (Strategiewahl nur von Hand) – der Haken von Hand. „Anlegen“: Das Räumen lässt am Grund
# der Nut 0,2 stehen (nur dort), die Kontur der Wände endet 0,2 über dem Grund, die Bohrungen gehen
# durch, das Hobeln kommt zuletzt. Programm Siemens: SPOS je Satz, beim Hobeln keine Spindel an.
# Ohne „Schlichten danach“ ist der Block rot (Aufmaß an den Wänden) mit dem Verweis, der es anhakt.
# Bilder: 1_angebot (der Knopf), 2_hobeln (der Block), 3_vorschau (die Bahn im Teil), 2b_waende,
# 4_uebersicht, 5_angelegt.
# ZEITLIMIT: 900
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
    from camaddon import postprozessor as pp
    from camaddon import raeumen as ra
    from camaddon import werkzeuge as wz

    kiste = list(wz.testkiste())  # T1–T4 wie immer, dazu der Ø 3
    klein = wz.Werkzeug(nummer=5, name="VHM 3", durchmesser=3.0, schneiden=3, schneidenlaenge=8.0,
                        eintauchwinkel=3.0)  # fmt: skip
    klein.schnittwerte[wz.ALLE] = [
        wz.Einsatz(art=wz.SCHRUPPEN, ae=0.3, ap=3.0, vc=85.0, fz=0.02),
        wz.Einsatz(art=wz.SCHLICHTEN, ae=0.1, ap=3.0, vc=85.0, fz=0.02),
    ]
    wz.Bibliothek(kiste + [klein]).speichern()
    datei = os.path.join(camaddon.ADDON_ORDNER, "beispiele", "dichtnut_deckel.FCStd")
    doc = FreeCAD.openDocument(datei)
    doc.UndoMode = 1
    yield 1500
    teil = doc.getObject("Deckel")
    nuten = hb.hobelnuten(teil.Shape)
    h.pruefe(len(nuten) == 1, f"Dichtnuten im Beispielteil: {[n.name for n in nuten]}")
    nut = nuten[0]
    waende = [f for f in nut.flaechen if f != nut.name]
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
    # Das Räumen bekommt den Ø 3 (der Ø 12 passt nicht in die Nut).
    d3 = next((w for w in panel.raeumen._fraeser if w.durchmesser == 3.0), None)
    h.pruefe(d3 is not None, "kein Ø 3 fürs Räumen")
    if d3 is not None:
        panel.raeumen.fraeser_setzen(d3)
        yield 1500
        yield from h.warte_auf(fertig_gerechnet, 300000)
        yield 1500
    # Die Wände haben das Aufmaß des Räumens: „Nicht fertig“ bietet „Schlichten danach“ an.
    if not panel.schlichten_danach.aktiv() and "Schlichten danach" in panel.unfertig_knopf.text():
        panel.unfertig_knopf.click()
        yield 1500
        yield from h.warte_auf(fertig_gerechnet, 300000)
        yield 1500
    h.pruefe(panel.schlichten_danach.aktiv(), "Schlichten danach nicht angehakt")
    # Kein Stoßwerkzeug: der Knopf, der eins anlegt.
    satz, knopf = panel.unfertig_satz.text(), panel.unfertig_knopf.text()
    print("HOBELN Angebot", repr(satz), repr(knopf), flush=True)
    h.pruefe(not panel.unfertig_angebot.isHidden(), "kein Angebot unten")
    h.pruefe("Stoßwerkzeug" in satz, f"Satz: {satz!r}")
    h.pruefe(knopf == "Stoßwerkzeug b 3,5 × 1,1 anlegen", f"Knopf: {knopf!r}")
    h.bild("1_angebot", panel.form)

    panel.unfertig_knopf.click()
    yield 1500
    yield from h.warte_auf(fertig_gerechnet, 300000)
    yield 1500
    stoss = [w for w in panel.bibliothek.werkzeuge if w.art == wz.STOSSWERKZEUG]
    h.pruefe(
        len(stoss) == 1
        and abs(stoss[0].schneidenbreite - 3.5) < 1e-9
        and abs(stoss[0].klingenlaenge - 1.1) < 1e-9,
        f"Stoßwerkzeug: {stoss}",
    )
    h.pruefe(
        bool(stoss) and any(e.art == wz.HOBELN for e in stoss[0].einsaetze("P1")),
        f"Stoßwerkzeug ohne Richtwerte: {stoss[0].schnittwerte if stoss else None}",
    )
    h.pruefe(block.moeglich, f"Dichtnut hobeln nicht möglich: {block.erklaerung.text()!r}")
    h.pruefe(not block.aktiv(), "Dichtnut hobeln von sich aus angehakt")
    h.pruefe(
        panel.unfertig_angebot.isHidden(), f"noch ein Angebot: {panel.unfertig_knopf.text()!r}"
    )
    # Der Haken von Hand.
    block.haken.setChecked(True)
    yield 1500
    yield from h.warte_auf(fertig_gerechnet, 300000)
    yield 1500
    text = block.ergebnis.text()
    print("HOBELN Block", repr(text), repr(block.hinweis.text()), flush=True)
    h.pruefe(nut.name in text and "Umläufe" in text, f"Ergebnis: {text!r}")
    h.pruefe(not block.hinweis.text(), f"rot: {block.hinweis.text()!r}")
    rest = (panel._zusatz(panel.raeumen, form) or {}).get("boden_rest")
    h.pruefe(rest == ((nut.name, hop.REST),), f"Räumen ohne Rest am Grund: {rest}")
    danach = panel._zusatz(panel.schlichten_danach, form) or {}
    h.pruefe(
        {w for w, _r in danach.get("waende_rest", ())} == set(waende),
        f"Schlichten danach: {danach.get('waende_rest')}",
    )
    panel.seite_zeigen(beta.abschnitt(block) + beta.ERSTER_ABSCHNITT)
    yield 800
    h.bild("2_hobeln", panel.form)
    panel._block_zeigen(block)
    yield 1500
    Gui.activeDocument().activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("3_vorschau")

    # Ohne „Schlichten danach“ haben die Wände das Aufmaß des Räumens (0,3): Die Klinge 3,5 passt
    # nicht dazwischen (3,6 − 0,6) – rot, mit dem Verweis, der es wieder anhakt.
    panel.schlichten_danach.haken.setChecked(False)
    yield 1500
    yield from h.warte_auf(fertig_gerechnet, 300000)
    yield 1500
    rot = block.hinweis.text()
    print("HOBELN ohne Schlichten", repr(rot), flush=True)
    h.pruefe("Aufmaß" in rot and "anhaken:schlichtendanach" in rot, f"rot: {rot!r}")
    rest = (panel._zusatz(panel.raeumen, form) or {}).get("boden_rest")
    h.pruefe(not rest, f"Rest am Grund, obwohl nicht gehobelt wird: {rest}")
    panel.seite_zeigen(beta.abschnitt(block) + beta.ERSTER_ABSCHNITT)
    yield 800
    h.bild("2b_waende", panel.form)
    block._hinweis_verweis("anhaken:schlichtendanach")
    yield 1500
    yield from h.warte_auf(fertig_gerechnet, 300000)
    yield 1500
    h.pruefe(panel.schlichten_danach.aktiv(), "der Verweis hakt „Schlichten danach“ nicht an")
    h.pruefe(not block.hinweis.text(), f"noch rot: {block.hinweis.text()!r}")

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
    z_rest = nut.z_boden + hop.REST

    def tiefste(op):
        hoehen = [
            float(c.Parameters["Z"])
            for c in op.Path.Commands
            if c.Name in ("G1", "G01", "G2", "G02", "G3", "G03") and "Z" in c.Parameters
        ]
        return min(hoehen) if hoehen else None

    raeumen = [o for o in ops if ra.ist_raeumen(o)]
    h.pruefe(raeumen, f"kein Räumen: {namen}")
    for o in raeumen:
        z = tiefste(o)
        print("HOBELN Räumen", o.Label, list(o.RestFlaechen), float(o.RestBoden), z, flush=True)
        h.pruefe(
            list(o.RestFlaechen) == [nut.name] and abs(float(o.RestBoden) - hop.REST) < 1e-9,
            f"{o.Label}: Rest {list(o.RestFlaechen)} {float(o.RestBoden)}",
        )
        h.pruefe(z is not None and z >= z_rest - 1e-6, f"{o.Label}: unter dem Rest ({z})")
    for o in ops:
        if ko.ist_kontur(o) and set(o.Flaechen) & set(waende):
            z = tiefste(o)
            print("HOBELN Kontur", o.Label, list(o.RestWaende), float(o.RestUnten), z, flush=True)
            h.pruefe(z is not None and z >= z_rest - 1e-6, f"{o.Label}: unter dem Rest ({z})")
    if hobeln:
        h.pruefe(ops.index(hobeln[0]) == len(ops) - 1 or all(
            not (ra.ist_raeumen(o) or ko.ist_kontur(o)) for o in ops[ops.index(hobeln[0]):]
        ), f"Hobeln vor dem Fräsen der Nut: {namen}")  # fmt: skip
    # Die Bohrungen gehen durch – auf Maß, kein Rest.
    durch = [o for o in ops if set(getattr(o, "Flaechen", []) or []) & set(bohrungen)]
    durch += [o for o in ops if "Bohr" in o.Label and o not in durch]
    h.pruefe(durch, f"keine Operation an den Bohrungen: {namen}")
    for o in durch:
        z = tiefste(o)
        print("HOBELN Bohrung", o.Label, z, float(o.FinalDepth), flush=True)
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
        print("HOBELN Programm", zeilen[anfang : anfang + 4], zeilen[spos[0]], flush=True)
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
