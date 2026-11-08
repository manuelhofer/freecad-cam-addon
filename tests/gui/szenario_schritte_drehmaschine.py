# Die Drehmaschine in den Schritten – „Bearbeitung“ ist seit 0.350.0 der Assistent in Schritten
# (Manuel, 2026-11-07: „definitiv“). Wie in szenario_bearbeitung_maschine (dort das alte Fenster):
# Drehmaschine und 3-Achs-Fräse gespeichert, ein Block, die Oberseite angeklickt, „Bearbeitung“.
# Schritt 1 hat die Drehmaschine vorgewählt: rot der Satz, dass das Rohteil dort eine Stange ist,
# der Knopf zum 4-Achs-Assistenten; „Weiter“ geht nicht, auch nicht mit „Liegt wie im Modell“.
# Die Fräse gewählt: Satz und Knopf weg, „Weiter“ geht.
import os
import tempfile

import FreeCAD
import FreeCADGui as Gui
import Part

NEUES_FENSTER = True  # „Bearbeitung“ in Schritten


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine, gui_bearbeitung
    from camaddon import gui_bearbeitung_beta as beta
    from camaddon import hoehenfeld as hf
    from camaddon import maschinenspeicher as ms
    from camaddon import werkzeuge as wz

    wz.Bibliothek([wz.standardwerkzeug()]).speichern()
    ms.speichern([])
    ordner = tempfile.mkdtemp()
    for art, name in ((beispielmaschine.DREHMASCHINE, "Drehmaschine"),
                      (beispielmaschine.FRAESE_3, "Fraese")):  # fmt: skip
        asm, _maschine = beispielmaschine.lade(art)
        yield from h.warte_auf(lambda asm=asm: FreeCAD.ActiveDocument is asm.Document)
        asm.Document.saveAs(os.path.join(ordner, name + ".FCStd"))
        yield 300
    for dokument in list(FreeCAD.listDocuments().values()):
        FreeCAD.closeDocument(dokument.Name)
    yield 500

    doc = FreeCAD.newDocument("Teil")
    teil = doc.addObject("Part::Feature", "Block")
    teil.Shape = Part.makeBox(100, 60, 20)
    doc.recompute()
    oben = next(e.name for e in hf.ebenen_oben(teil.Shape) if abs(e.z - 20.0) < 1e-6)
    Gui.activateWorkbench("CAMWorkbench")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, oben)
    yield 500
    gui_bearbeitung.nullpunkt_vorgeben(None)
    Gui.runCommand("CamAddon_Bearbeitung")
    yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not None, 60000)
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(isinstance(panel, beta.BetaPanel), f"nicht in Schritten: {type(panel).__name__}")
    if panel is None or panel.job is None:
        return
    h.pruefe(panel.nur_vierachs(), "die Drehmaschine ist nicht vorgewählt")
    h.pruefe(
        panel.maschine_hinweis.isVisible() and panel.knopf_vierachs.isVisible(),
        "kein Hinweis auf die Stange bei der Drehmaschine",
    )
    panel.wie_modelliert()
    yield 500
    h.pruefe(not panel.knopf_weiter.isEnabled(), "„Weiter“ geht an der Drehmaschine")
    h.bild("1_drehmaschine", panel.form)
    panel.wahl_maschine.setCurrentIndex(1)  # die Fräse
    yield 800
    panel.wie_modelliert()
    yield 500
    h.pruefe(
        not panel.maschine_hinweis.isVisible() and not panel.knopf_vierachs.isVisible(),
        "der Hinweis auf die Stange bleibt bei der Fräse",
    )
    h.pruefe(panel.knopf_weiter.isEnabled(), "„Weiter“ geht an der Fräse nicht")
    h.bild("2_fraese", panel.form)
    panel.reject()
    yield 800
    FreeCAD.closeDocument(doc.Name)
    yield 300
