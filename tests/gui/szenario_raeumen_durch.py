# Frage 4 (Manuel, 2026-10-17: „Ja, Räumen tritt an“): Am C-Ring (Beispiel c_ring_nut_3achs, eine
# Kopie) Mantel, Bohrung und Schlitz anklicken – Wände, die durch das Teil gehen. „Bearbeitung“,
# „Weiter“: Kontur und Räumen treten an; Räumen räumt bis an die Unterkante (z −11) und ist
# schneller – es bekommt den Haken, die Kontur nicht, die Zeile sagt „die schnellste“.
# „Schlichten danach“ macht die Wände fertig. „Anlegen“: „Räumen …“ mit den vier Wänden, Endtiefe
# −11, und eine Bahn bis −11; das Schlichten danach mit den Wänden.
# ZEITLIMIT: 600
import os
import shutil
import tempfile

import FreeCAD
import FreeCADGui as Gui

ADDON = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WAENDE = ["Face1", "Face6", "Face3", "Face5"]  # Mantel, Bohrung, die zwei Wände des Schlitzes


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import gui_bearbeitung
    from camaddon import raeumen as ra
    from camaddon import werkzeuge as wz

    wz.Bibliothek(wz.testkiste()).speichern()
    ordner = tempfile.mkdtemp()
    datei = os.path.join(ordner, "cring.FCStd")
    shutil.copy(os.path.join(ADDON, "beispiele", "c_ring_nut_3achs.FCStd"), datei)
    doc = FreeCAD.openDocument(datei)
    Gui.activateWorkbench("CAMWorkbench")
    Gui.activeDocument().activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.clearSelection()
    for name in WAENDE:
        Gui.Selection.addSelection(doc.Name, "Body", name)
    yield 500
    Gui.runCommand("CamAddon_Bearbeitung")
    yield from h.warte_auf(
        lambda: getattr(gui_bearbeitung.BearbeitungPanel.offen, "job", None) is not None, 20000
    )
    yield 1000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Job")
    if panel is None or panel.job is None:
        return
    for name in WAENDE:
        if name not in panel.gewaehlte:
            panel.flaeche_umschalten(name)  # wie ein Klick im Modell
    yield 500
    h.pruefe(sorted(panel.gewaehlte) == sorted(WAENDE), f"gewählt: {panel.gewaehlte}")
    panel.knopf_weiter.click()
    yield 500
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 180000)
    yield 1500
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 180000)
    raeumen, kontur = panel.raeumen, panel.kontur
    form = panel.job.Model.Group[0].Shape
    h.pruefe(
        sorted(raeumen.s.flaechen_fuer(form, panel.gewaehlte)) == sorted(WAENDE),
        f"Räumen nimmt: {raeumen.s.flaechen_fuer(form, panel.gewaehlte)}",
    )
    with open(os.path.join(os.environ["CAMADDON_AUSGABE"], "wettbewerb.txt"), "w") as d:
        for b in panel.bloecke:
            if b.aktiv() or b.zeit is not None:
                d.write(f"{b.s.kennung}: aktiv {b.aktiv()} zeit {b.zeit} – {b.ergebnis.text()}\n")
    h.pruefe(
        raeumen.aktiv() and not kontur.aktiv(),
        f"Haken: Räumen {raeumen.aktiv()}, Kontur {kontur.aktiv()}",
    )
    h.pruefe(
        raeumen.zeit is not None and kontur.zeit is not None and raeumen.zeit < kontur.zeit,
        f"Zeit: Räumen {raeumen.zeit}, Kontur {kontur.zeit}",
    )
    h.pruefe("die schnellste" in raeumen.ergebnis.text(), f"Räumen: {raeumen.ergebnis.text()!r}")
    h.pruefe(panel.schlichten_danach.aktiv(), "„Schlichten danach“ ohne Haken")
    zusatz = panel._schlichten_danach_zusatz(form)
    h.pruefe(
        set(WAENDE) <= set(zusatz.get("wand_flaechen", ())),
        f"Schlichten danach, Wände: {zusatz.get('wand_flaechen')}",
    )
    panel.knopf_weiter.click()
    yield 800
    h.bild("1_wettbewerb", panel.form)
    job = panel.job
    vorher = len(job.Operations.Group)
    h.pruefe(panel.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    neue = list(job.Operations.Group)[vorher:]
    h.pruefe(bool(neue), "nichts angelegt")
    geraeumt = [o for o in neue if ra.ist_raeumen(o)]
    h.pruefe(len(geraeumt) == 1, f"Operationen: {[o.Label for o in neue]}")
    if geraeumt:
        op = geraeumt[0]
        h.pruefe(sorted(op.Flaechen) == sorted(WAENDE), f"Flächen: {op.Flaechen}")
        h.pruefe(abs(float(op.FinalDepth) + 11.0) < 1e-6, f"Endtiefe {op.FinalDepth}")
        zs = [c.Parameters["Z"] for c in op.Path.Commands if "Z" in c.Parameters]
        h.pruefe(bool(zs) and abs(min(zs) + 11.0) < 0.01, f"tiefster Punkt {min(zs, default=None)}")
    Gui.Selection.clearSelection()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("2_angelegt")
