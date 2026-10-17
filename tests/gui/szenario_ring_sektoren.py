# Manuels Ring auf der Beispiel-Drehmaschine, „Rundum schruppen“ ohne Querachse (Auftrag 1,
# P-2026-10-17-26): drei Segmente mit Schlitzen bis zur Bohrung – ab der zweiten Lage steht nur noch
# in den Schlitzen etwas, die Lage fährt Zeilen dort statt der Spirale rundum. T1 Schaftfräser Ø 4
# im Halter „VDI30 angetrieben radial“, ap 3, ae 1. Die Stirnseite des Rings anklicken,
# „4-Achs-Bearbeitung“: Schritt 2, „Mit der Querachse (Y)“ abhaken, „Rundum schlichten“ abhaken –
# die Vorschau fährt unter 25 km (die Spirale 100 km); „Anlegen“ → „Rundum schruppen T1“ mit
# „Folgelagen nur, wo nötig“, Bild der Bahn im 3D.
# ZEITLIMIT: 600
import math
import os
import shutil
import tempfile

import FreeCAD
import FreeCADGui as Gui

ADDON = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine, gui_vierachs
    from camaddon import vierachs_operation as vo
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    bibliothek = wz.Bibliothek()
    halter = bibliothek.neuer_halter("vdi30_radial")
    t1 = bibliothek.neues_werkzeug()
    t1.nummer, t1.name, t1.durchmesser, t1.schneiden = 1, "VHM 4", 4.0, 3
    t1.schneidenlaenge, t1.laenge_spindelnase, t1.halter = 12.0, 110.0, halter.kennung
    t1.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=1.0, ap=3, vc=120, fz=0.03)]
    bibliothek.speichern()

    asm, _maschine = beispielmaschine.lade(beispielmaschine.DREHMASCHINE)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    yield 300

    ordner = tempfile.mkdtemp()
    datei = os.path.join(ordner, "ring.FCStd")
    shutil.copy(os.path.join(ADDON, "beispiele", "ring_4achs_planbearbeitung.FCStd"), datei)
    doc = FreeCAD.openDocument(datei)
    teil = doc.getObject("Body")
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    stirn = max(
        (
            (f.Area, f"Face{i + 1}")
            for i, f in enumerate(teil.Shape.Faces)
            if vr.ist_eben(f) and (vr.aussennormale(f) - FreeCAD.Vector(0, 0, 1)).Length < 1e-9
        ),
    )[1]
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, stirn)
    yield 500

    Gui.runCommand("CamAddon_Vierachs")
    yield 1500
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 3000)
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    panel.knopf_weiter.click()
    yield 300
    h.pruefe(panel.seite == 2, f"Seite {panel.seite}")
    h.pruefe(panel.mit_schruppen.isChecked(), "„Rundum schruppen“ nicht angehakt")
    h.pruefe(panel.schruppen_noetig.isChecked(), "„Folgelagen nur, wo nötig“ nicht angehakt")
    if panel.mit_schlichten.isChecked():
        panel.mit_schlichten.setChecked(False)
    # Mit der Querachse (die Beispiel-Drehmaschine hat Y): „Sektoren in Zeilen mit Y – C steht“
    # ist frei und angehakt (W-026) – die Vorschau fährt auch so unter 25 km, in den Schlitzen
    # steht C, Y fährt quer (bis dahin kreiste die Spirale mit Y alle Lagen rundum: 151 km).
    if panel.schruppen_querachse.isChecked():
        h.pruefe(
            panel.schruppen_sektoren_y.isEnabled() and panel.schruppen_sektoren_y.isChecked(),
            "„Sektoren in Zeilen mit Y“ nicht angehakt",
        )
        yield 500
        yield from h.warte_auf(lambda: not panel.rechnet_noch(), 180000)
        yield from h.warte_auf(lambda: panel.vorschau is not None, 30000)
        bahn_y = panel.vorschau
        weg_y = sum(
            math.hypot(
                math.hypot(n.a - p.a, n.r - p.r),
                math.hypot(n.q - p.q, (p.r + n.r) / 2 * math.radians(n.phi - p.phi)),
            )
            for p, n in zip(bahn_y.punkte, bahn_y.punkte[1:], strict=False)
            if not n.eilgang
        )
        stehend = sum(
            1
            for p, n in zip(bahn_y.punkte, bahn_y.punkte[1:], strict=False)
            if not p.eilgang and not n.eilgang and abs(n.phi - p.phi) < 1e-9 and abs(n.q) > 0.5
        )
        with open(os.path.join(os.environ["CAMADDON_AUSGABE"], "bahn_y.txt"), "w") as d:
            d.write(
                f"sektoren_y {panel.sektoren_y()}, y_weg {panel.y_weg()}, Lagen {bahn_y.lagen}, "
                f"Punkte {len(bahn_y.punkte)}, mit q {sum(1 for p in bahn_y.punkte if abs(p.q) > 0.5)}, "
                f"stehend {stehend}, Weg {weg_y:.0f}\n"
            )
        h.pruefe(weg_y < 25000, f"mit Y: Weg im Vorschub {weg_y:.0f} mm – kreist die Spirale?")
        h.pruefe(stehend > 50, f"mit Y: {stehend} Sätze mit stehendem C und Versatz quer")
        h.bild("0_mit_y", panel.form)
        panel.schruppen_querachse.setChecked(False)
    yield 500
    yield from h.warte_auf(lambda: not panel.rechnet_noch(), 180000)
    yield from h.warte_auf(lambda: panel.vorschau is not None, 30000)
    bahn = panel.vorschau
    h.pruefe(not panel.hinweis_bearbeitung.text(), f"rot: {panel.hinweis_bearbeitung.text()!r}")
    weg = sum(
        math.hypot(math.hypot(n.a - p.a, n.r - p.r), (p.r + n.r) / 2 * math.radians(n.phi - p.phi))
        for p, n in zip(bahn.punkte, bahn.punkte[1:], strict=False)
        if not n.eilgang
    )
    with open(os.path.join(os.environ["CAMADDON_AUSGABE"], "bahn.txt"), "w") as d:
        d.write(f"Lagen {bahn.lagen}, Punkte {len(bahn.punkte)}, Weg im Vorschub {weg:.0f} mm\n")
        d.write(f"Ergebnis: {panel.ergebnis.text()!r}\n")
    h.pruefe(weg < 25000, f"Weg im Vorschub {weg:.0f} mm – fährt die Spirale rundum?")
    h.bild("1_schritt2", panel.form)
    job = panel.job
    yield from h.warte_auf(lambda: panel.knopf_fertig.isEnabled(), 3000)
    panel.knopf_fertig.click()
    yield 2000
    h.pruefe(gui_vierachs.VierachsPanel.offen is None, "Fenster nach „Anlegen“ offen")
    ops = [o for o in job.Operations.Group if vo.ist_rundum(o)]
    h.pruefe([o.Label for o in ops] == ["Rundum schruppen T1"], f"Operationen: {ops}")
    if ops:
        h.pruefe(bool(ops[0].NurNoetig) and not bool(ops[0].Querachse), "Haken an der Operation")
    Gui.Selection.clearSelection()
    FreeCAD.setActiveDocument(doc.Name)
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("2_bahn")
