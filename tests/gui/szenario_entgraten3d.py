# Entgraten 3D (W-015 S5; Manuel, 2026-10-04: „nicht das Werkstück beschädigen“, „nicht nur auf
# den 45-Grad-Fräser“, „auch auf einer Dreiachs-Maschine“): Klotz 60 × 40 × 20 mit 30°-Schräge,
# Nut und Bohrung; die 5-Achs-Maschine Tisch/Tisch als zuletzt benutzte, ein Fasenfräser 90° Ø 10
# und ein Schaftfräser Ø 10. Oberseite und Schräge anklicken → „Bearbeitung“ → Schritt 2: der
# Block „Entgraten 3D“ ist nicht angehakt (welche Kante eine Fase bekommt, sagt die Zeichnung);
# anhaken: der Fasenfräser vorgewählt, „Angestellt (5 Achsen)“ angehakt, unten „→ … Kanten mit
# Fase, etwa …“ und was ohne Fase bleibt (in der Nut zu eng). „Anlegen“: „Entgraten 3D T3“ mit je
# Satz einer Achse, 5 Achsen. Dazu eine Kante angeklickt (Manuel, 2026-10-05: „Kanten anklicken
# muss sein“): die senkrechte vorn links – in der Liste „Edge… Kante, 20 mm – Fase mit
# „Entgraten 3D““, der Block angehakt, in der Operation steht sie unter den Flächen.
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

    from camaddon import PARAMETER_PFAD, beispielmaschine, gui_bearbeitung
    from camaddon import entgraten3d as e3op
    from camaddon import maschinenspeicher as msp
    from camaddon import reichweite as rw
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    ordner = tempfile.mkdtemp()
    asm, _maschine = beispielmaschine.lade(beispielmaschine.TISCH_TISCH)
    pfad_maschine = os.path.join(ordner, "fuenfachs.FCStd")
    asm.Document.saveAs(pfad_maschine)
    msp.merken_datei(pfad_maschine)
    FreeCAD.ParamGet(PARAMETER_PFAD).SetString(rw.ZULETZT_MASCHINE, pfad_maschine)
    yield 300
    fase = wz.Werkzeug(
        nummer=3,
        name="Fase 90",
        art=wz.FASENFRAESER,
        durchmesser=10.0,
        schneiden=2,
        schneidenlaenge=5.0,
        gesamtlaenge=60.0,
        spitzenwinkel=90.0,
        spitzen_d=0.5,
        schneidstoff=wz.VHM,
    )
    fase.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.FASEN, vc=100.0, fz=0.05)]
    t5 = wz.Werkzeug(
        nummer=5,
        name="VHM 10",
        art=wz.SCHAFTFRAESER,
        durchmesser=10.0,
        schneiden=4,
        schneidenlaenge=22.0,
        gesamtlaenge=72.0,
        schneidstoff=wz.VHM,
    )
    t5.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=4.0, ap=10.0, vc=150.0, fz=0.05)]
    wz.Bibliothek([fase, t5]).speichern()

    doc = FreeCAD.newDocument("Entgraten3D")
    doc.UndoMode = 1
    klotz = Part.makeBox(60, 40, 20)
    hoehe = 20 - 21 * math.tan(math.radians(30))
    keil = Part.Face(
        Part.makePolygon(
            [V(40, -1, 20), V(61, -1, hoehe), V(61, -1, 30), V(40, -1, 30), V(40, -1, 20)]
        )
    ).extrude(V(0, 42, 0))
    form = klotz.cut(keil).cut(Part.makeBox(6, 42, 5, V(17, -1, 15)))
    form = form.cut(Part.makeCylinder(5, 30, V(8, 20, -5))).removeSplitter()
    teil = doc.addObject("Part::Feature", "Klotz")
    teil.Shape = form
    doc.recompute()
    FreeCAD.setActiveDocument(doc.Name)

    def normale(f):
        u0, u1, v0, v1 = f.ParameterRange
        return f.normalAt((u0 + u1) / 2, (v0 + v1) / 2)

    oben = next(
        f"Face{i + 1}"
        for i, f in enumerate(form.Faces)
        if abs(f.BoundBox.ZMin - 20) < 1e-6 and abs(f.BoundBox.ZMax - 20) < 1e-6 and f.Area > 300
    )
    schraege = next(
        f"Face{i + 1}"
        for i, f in enumerate(form.Faces)
        if abs(abs(normale(f).z) - math.cos(math.radians(30))) < 1e-6
    )
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, oben)
    yield 500

    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2500
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    eintrag = panel.maschine()
    h.pruefe(eintrag is not None and eintrag.art == msp.FRAESE_5, f"Maschine: {eintrag}")
    panel.flaeche_umschalten(schraege)
    yield 1000
    block = panel.entgraten3d
    h.pruefe(block.moeglich and not block.aktiv(), "„Entgraten 3D“ nicht frei oder schon angehakt")
    # Das Entgraten an der Fräse hält die schmale Schräge für eine gezeichnete Fase (120°) – hier
    # nicht gewollt.
    panel.entgraten.haken.setChecked(False)
    # Eine Kante anklicken – wie im 3D: durch das Tor des Assistenten und seinen Beobachter.
    klon = vr.modell(job)
    ecke = next(
        f"Edge{i + 1}"
        for i, k in enumerate(klon.Shape.Edges)
        if k.BoundBox.XMax < 1e-6 and k.BoundBox.YMax < 1e-6 and abs(k.Length - 20) < 1e-6
    )
    Gui.Selection.addSelection(doc.Name, klon.Name, ecke)
    yield 1000
    eintraege = [panel.flaechen_liste.item(i).text() for i in range(panel.flaechen_liste.count())]
    h.pruefe(panel.kanten == [ecke], f"Kanten: {panel.kanten} statt {ecke}")
    h.pruefe(any(e.startswith(ecke) and "Fase" in e for e in eintraege), f"Liste: {eintraege}")
    h.pruefe(block.aktiv(), "Kante angeklickt – „Entgraten 3D“ nicht angehakt")
    # Im Bild grün – je Kante eine Farbe, die angeklickte anders als die übrigen.
    linien = list(getattr(klon.ViewObject, "LineColorArray", []) or [])
    nummer = int(ecke[4:]) - 1
    h.pruefe(
        len(linien) == len(klon.Shape.Edges)
        and linien[nummer][1] > linien[nummer][0]
        and tuple(linien[nummer]) != tuple(linien[(nummer + 1) % len(linien)]),
        f"Kante nicht gefärbt: {linien[:3]}",
    )
    panel.seite_zeigen(1)
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("0_kante_angeklickt")
    block.haken.setChecked(True)
    yield from h.warte_auf(
        lambda: all(
            b.vorschau is not None or b.hinweis.text() or not b.aktiv() for b in panel.bloecke
        ),
        120000,
    )
    yield 1500
    rot = {b.s.kennung: b.hinweis.text() for b in panel.bloecke if b.aktiv() and b.hinweis.text()}
    h.pruefe(not rot, f"rote Sätze: {rot}")
    fuenf = block.haken_felder.get("fuenf")
    h.pruefe(
        fuenf is not None and not fuenf.isHidden() and fuenf.isChecked(), "„angestellt“ nicht an"
    )
    h.pruefe(block.fraeser() is not None and block.fraeser().nummer == 3, "nicht der Fasenfräser")
    text = block.ergebnis.text()
    h.pruefe(text.startswith("→ ") and "Kanten mit Fase, etwa " in text, f"Ergebnis: {text!r}")
    h.pruefe(not block.hinweis.text(), f"rot: {block.hinweis.text()!r}")
    panel.seite_zeigen(2)
    yield 500
    h.bild("1_einstellungen", panel.form)

    # --- Anlegen ------------------------------------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    ops = [o for o in job.Operations.Group if e3op.ist_entgraten3d(o)]
    h.pruefe(len(ops) == 1, f"Operationen: {[o.Label for o in job.Operations.Group]}")
    if not ops:
        return
    op = ops[0]
    h.pruefe(
        op.Label == "Entgraten 3D T3" and op.FuenfAchsen and op.Kanten >= 5,
        f"{op.Label}, 5 Achsen {op.FuenfAchsen}, {op.Kanten} Kanten",
    )
    h.pruefe(len(op.Werkzeugachsen) == len(op.Path.Commands) > 10, "Achsen je Satz")
    h.pruefe(ecke in list(op.Flaechen), f"Kante nicht in der Operation: {list(op.Flaechen)}")
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("2_angelegt")
    FreeCAD.closeDocument(doc.Name)
    yield 300
