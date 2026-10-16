# Gleiche Flächen auf einmal (Manuel, 2026-10-16: „wenn ich nun aber die radien unten auch mit
# gemacht haben will muss ich die alle anklicken .... was sehr müsam ist“): ein Klotz mit einer
# Tasche, ihre Ecken R 6, ihr Boden rundum R 2. Den Taschenboden angeklickt, „Bearbeitung“: Job da,
# kein Knopf (der Boden ist der einzige auf seiner Höhe). Eine Kehle dazu: Der Knopf „Alle 7
# weiteren Rundungen R 2 dazu (Höhe 20 … 22)“ erscheint – geklickt sind alle 8 Kehlen gewählt, der
# Knopf ist weg. Ein Eckradius: „Alle 3 weiteren Eckradien R 6 dazu“. Den Eckradius wieder
# herausgenommen: der Knopf ist weg.
import FreeCAD
import FreeCADGui as Gui
import Part


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import gleiche_flaechen as glf
    from camaddon import gui_bearbeitung
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    wz.Bibliothek([wz.standardwerkzeug()]).speichern()
    V = FreeCAD.Vector
    tasche = Part.makeBox(60, 40, 10, V(20, 20, 20))
    tasche = tasche.makeFillet(6.0, [k for k in tasche.Edges if k.BoundBox.ZLength > 1e-6])
    tasche = tasche.makeFillet(2.0, [k for k in tasche.Edges if abs(k.BoundBox.ZMax - 20) < 1e-6])
    doc = FreeCAD.newDocument("Tasche")
    teil = doc.addObject("Part::Feature", "Klotz")
    teil.Shape = Part.makeBox(100, 80, 30).cut(tasche)
    doc.recompute()
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    boden = next(
        f"Face{k + 1}"
        for k, f in enumerate(teil.Shape.Faces)
        if (a := glf.art(f)) and a.art == glf.BODEN and abs(a.mass - 20) < 1e-6
    )
    Gui.Selection.addSelection(doc.Name, teil.Name, boden)
    yield 300
    gui_bearbeitung.nullpunkt_vorgeben(None)
    Gui.runCommand("CamAddon_Bearbeitung")
    yield from h.warte_auf(
        lambda: getattr(gui_bearbeitung.BearbeitungPanel.offen, "job", None) is not None, 20000
    )
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Job")
    if panel is None or panel.job is None:
        return
    panel.knopf_weiter.click()  # Schritt 2
    yield 800
    form = vr.modell(panel.job).Shape
    kehlen = [
        f"Face{k + 1}"
        for k, f in enumerate(form.Faces)
        if (a := glf.art(f)) and a.art == glf.RUNDUNG
    ]
    ecken = [
        f"Face{k + 1}"
        for k, f in enumerate(form.Faces)
        if (a := glf.art(f)) and a.art == glf.ECKRADIUS
    ]
    h.pruefe(len(kehlen) == 8 and len(ecken) == 4, f"Kehlen {len(kehlen)}, Ecken {len(ecken)}")
    h.pruefe(not panel.gleiche_knopf.isVisible(), "Knopf schon nach dem Boden")

    panel.flaeche_umschalten(kehlen[0])
    yield 500
    text = panel.gleiche_knopf.text()
    h.pruefe(
        panel.gleiche_knopf.isVisible()
        and text.startswith("Alle 7 weiteren Rundungen R 2 dazu")
        and "20" in text
        and "22" in text,
        f"Knopf nach der Kehle: {panel.gleiche_knopf.isVisible()} {text!r}",
    )
    h.bild("1_kehle_angeklickt", panel.form)
    panel.gleiche_knopf.click()
    yield 800
    h.pruefe(all(k in panel.gewaehlte for k in kehlen), f"gewählt: {panel.gewaehlte}")
    h.pruefe(not panel.gleiche_knopf.isVisible(), "Knopf bleibt nach dem Klick")
    h.bild("2_alle_kehlen", panel.form)
    h.bild("2b_alle_kehlen_3d")

    panel.flaeche_umschalten(ecken[0])
    yield 500
    h.pruefe(
        panel.gleiche_knopf.text().startswith("Alle 3 weiteren Eckradien R 6 dazu"),
        f"Knopf nach dem Eckradius: {panel.gleiche_knopf.text()!r}",
    )
    panel.flaeche_umschalten(ecken[0])  # wieder heraus
    yield 500
    h.pruefe(not panel.gleiche_knopf.isVisible(), "Knopf bleibt nach dem Herausnehmen")
    panel.reject()
    yield 800
