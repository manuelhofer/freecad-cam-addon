# Eine Formplatte auf der 3-Achs-Fräse (P-2026-10-02-14): Platte 100 × 100 × 30, in der Mitte
# eine Kugelmulde R 30 (12 tief), in den Ecken vier Bohrungen Ø 9 durch; T1 der Standardfräser
# Ø 12, T2 ein Bohrer Ø 9, T3 ein Kugelfräser Ø 6. Oberseite, Mulde und die vier Bohrungen
# anklicken. Früher schlug der Assistent 3D-Schruppen und 3D-Schlichten nur vor, wenn allein
# Freiformflächen gewählt waren – hier bekam die Mulde gar keine Operation. Jetzt: Planfräsen
# oder Räumen für die Oberseite, Bohren mit T2, 3D-Schruppen mit T1 und 3D-Schlichten mit T3 für
# die Mulde. „Anlegen“ legt alle an; „Auf der Maschine prüfen“: am Ende nirgends ins Teil.
import re

import FreeCAD
import FreeCADGui as Gui
import Part
from PySide import QtCore

V = FreeCAD.Vector


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine, gui_bearbeitung, gui_reichweite
    from camaddon import bohren as bh
    from camaddon import bohrung_bahn as bb
    from camaddon import hoehenfeld as hf
    from camaddon import schlichten3d as s3op
    from camaddon import schruppen3d as r3op
    from camaddon import werkzeuge as wz

    t2 = wz.Werkzeug(nummer=2, art=wz.BOHRER, durchmesser=9.0, schneiden=2, schneidenlaenge=60.0,
                     spitzenwinkel=118.0, schneidstoff=wz.HSS)  # fmt: skip
    t2.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.BOHREN, vc=25.0, fz=0.1)]
    t3 = wz.Werkzeug(nummer=3, name="Kugel 6", art=wz.KUGELFRAESER, durchmesser=6.0, schneiden=2,
                     schneidenlaenge=12.0, schneidstoff=wz.VHM)  # fmt: skip
    t3.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=0.3, vc=150.0, fz=0.05)]
    wz.Bibliothek([wz.standardwerkzeug(), t2, t3]).speichern()

    doc = FreeCAD.newDocument("Formplatte")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Formplatte")
    form = Part.makeBox(100, 100, 30, V(0, 0, -30)).cut(Part.makeSphere(30, V(50, 50, 18)))
    for x, y in ((10, 10), (90, 10), (10, 90), (90, 90)):
        form = form.cut(Part.makeCylinder(4.5, 30, V(x, y, -30)))
    teil.Shape = form.removeSplitter()
    doc.recompute()
    loecher = [b.name for b in bb.bohrungen(teil.Shape) if abs(b.radius - 4.5) < 1e-6]
    h.pruefe(len(loecher) == 4, f"Bohrungen: {loecher}")
    oben = next(e.name for e in hf.ebenen_oben(teil.Shape) if abs(e.z) < 1e-6)
    mulde = next(
        f"Face{i + 1}" for i, f in enumerate(teil.Shape.Faces) if isinstance(f.Surface, Part.Sphere)
    )
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, oben)
    yield 500

    # Die Koordinaten dieses Szenarios gelten im Modell – nicht an der Mitte oben, die neue
    # Vorgabe (P-2026-10-02-49).
    gui_bearbeitung.nullpunkt_vorgeben(None)
    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job
    for name in [mulde, *loecher]:
        panel.flaeche_umschalten(name)
    yield 1000
    bohren, r3, s3 = panel.bohren, panel.schruppen3d, panel.schlichten3d
    yield from h.warte_auf(
        lambda: all(b.vorschau is not None or not b.aktiv() for b in panel.bloecke), 400000
    )
    yield 3000
    h.pruefe(bohren.aktiv() and bohren.fraeser().nummer == 2, "Bohren: kein Haken oder nicht T2")
    h.pruefe(r3.aktiv() and r3.fraeser().nummer == 1, "3D-Schruppen: kein Haken oder nicht T1")
    h.pruefe(s3.aktiv() and s3.fraeser().nummer == 3, "3D-Schlichten: kein Haken oder nicht T3")
    h.pruefe(panel.plan.aktiv() or panel.raeumen.aktiv(), "Oberseite: kein Haken")
    rot = [(b.s.kennung, b.hinweis.text()) for b in panel.bloecke if b.aktiv() and b.hinweis.text()]
    h.pruefe(not rot, f"rot angehakt: {rot}")
    h.pruefe(bohren.ergebnis.text().startswith("→ 4 Bohrungen"), f"{bohren.ergebnis.text()!r}")
    liste = panel.flaechen_liste
    eintraege = [liste.item(i).text() for i in range(liste.count())]
    h.pruefe(  # die Oberseite auf 0 – vorher „Höhe -5,60364933565e-18“
        f"{oben}  eben nach oben, Höhe 0" in eintraege
        and not any(re.search(r"\de-\d", t) for t in eintraege),
        f"Flächenliste: {eintraege}",
    )
    h.bild("1_formplatte", panel.form)

    # --- Anlegen ------------------------------------------------------------------------------
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 4000
    ops = list(job.Operations.Group)
    namen = [o.Label for o in ops]
    h.pruefe(any(bh.ist_bohren(o) for o in ops), f"kein Bohren: {namen}")
    h.pruefe(any(r3op.ist_schruppen3d(o) for o in ops), f"kein 3D-Schruppen: {namen}")
    h.pruefe(any(s3op.ist_schlichten3d(o) for o in ops), f"kein 3D-Schlichten: {namen}")
    Gui.Selection.clearSelection()
    Gui.activeDocument().activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
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
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None, 120000)
    pruef = gui_reichweite.PruefPanel.offen
    h.pruefe(pruef is not None, "„Auf der Maschine prüfen“ öffnet kein Fenster")
    if pruef is None:
        return
    yield 1000
    spieler = pruef.abspieler
    spieler.setze_zeit(spieler.abfahrt.dauer)
    yield from h.warte_auf(lambda: spieler.rest.text().startswith("Am Ende"), 300000)
    rest = spieler.rest.text()
    h.pruefe(rest.startswith("Am Ende bleiben") and "nirgends ins Teil" in rest, f"{rest!r}")
    Gui.SendMsgToActiveView("ViewFit")
    spieler.knopf_hinsehen.click()
    yield 800
    h.bild("3_pruefen_farben")
    pruef.reject()
    yield 500
    FreeCAD.closeDocument(doc.Name)
    yield 300
