# „Alles aus dieser Aufspannung“ in einem Rutsch (Frage 14, Schritt 4; Manuel, 2026-10-11: „ja
# mach“): das Schwenkteil auf der 5-Achs-Fräse Tisch/Tisch, Schritt 2 „Alles aus dieser
# Aufspannung“, „Anlegen“ – die Operationen von oben im Grundjob, dann legt das Addon die Ebenen
# der 30°-Schräge und der 45°-Fase an und öffnet den Assistenten für die erste, ihre Flächen gewählt
# („Ebene 1 von 2 …“); nach „Anlegen“ die zweite; danach nichts mehr. Am Ende drei Jobs, jeder mit
# Operationen.
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

    from camaddon import beispielmaschine, gui_bearbeitung
    from camaddon import job_schnittwerte as js
    from camaddon import maschinenspeicher as ms
    from camaddon import werkzeuge as wz

    wz.Bibliothek([wz.standardwerkzeug()]).speichern()
    ms.speichern([])
    ordner = tempfile.mkdtemp()
    asm, _maschine = beispielmaschine.lade(beispielmaschine.TISCH_TISCH)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    asm.Document.saveAs(os.path.join(ordner, "Fuenfachs.FCStd"))
    yield 300
    for dokument in list(FreeCAD.listDocuments().values()):
        FreeCAD.closeDocument(dokument.Name)
    yield 500

    datei = os.path.join(ordner, "Teil.FCStd")
    shutil.copy(os.path.join(ADDON, "beispiele", "schwenkteil_5achs.FCStd"), datei)
    doc = FreeCAD.openDocument(datei)
    Gui.activateWorkbench("CAMWorkbench")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, "Schwenkteil", "Face4")
    yield 500
    gui_bearbeitung.nullpunkt_vorgeben(None)
    Gui.runCommand("CamAddon_Bearbeitung")
    yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not None)
    yield 1500
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None and panel._fuenfachs(), "kein Fenster")
    if panel is None or panel.job is None:
        return
    grundjob = panel.job
    panel.knopf_weiter.click()
    yield 500
    panel.aus_der_aufspannung()
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 120000)
    h.bild("1_grundjob", panel.form)
    h.pruefe(panel.accept() is True, "„Anlegen“ im Grundjob ging nicht")

    for nummer in (1, 2):
        yield from h.warte_auf(
            lambda p=panel: gui_bearbeitung.BearbeitungPanel.offen not in (None, p)
            or h.modal() is not None,
            120000,
        )
        yield 1500
        meldung = h.modal()
        if meldung is not None:
            h.bild(f"meldung_{nummer}", meldung)
            h.pruefe(False, f"Meldung statt Ebene {nummer}: {meldung.windowTitle()}")
            meldung.accept()
            return
        panel = gui_bearbeitung.BearbeitungPanel.offen
        h.pruefe(
            panel._folge is not None and panel._folge.startswith(f"Ebene {nummer} von 2"),
            f"Ebene {nummer}: {panel._folge!r}",
        )
        h.pruefe(bool(panel.gewaehlte), f"Ebene {nummer}: nichts gewählt")
        panel.knopf_weiter.click()
        yield from h.warte_auf(lambda p=panel: not p.vorschau_laeuft(), 120000)
        Gui.SendMsgToActiveView("ViewFit")
        yield 300
        h.bild(f"{nummer + 1}_ebene_{nummer}")
        h.bild(f"{nummer + 1}_ebene_{nummer}_fenster", panel.form)
        h.pruefe(
            not {"schlichten3d", "schruppen3d"} & {b.s.kennung for b in panel.aktive_bloecke()},
            f"Ebene {nummer}: 3D-Strategie angehakt",
        )
        # Wie ein Mensch: was rot bleibt (die Bohrung Ø 8,5 ist für den Fräser Ø 12 zu klein),
        # abhaken – dann geht „Anlegen“, und die nächste Ebene kommt.
        if panel.accept() is not True:
            for block in panel.aktive_bloecke():
                if not block.kann_anlegen():
                    block.haken.setChecked(False)
            yield 500
            h.pruefe(panel.accept() is True, f"„Anlegen“ in Ebene {nummer} ging nicht")
    yield 3000
    h.pruefe(
        gui_bearbeitung.BearbeitungPanel.offen in (None, panel) and not Gui.Control.activeDialog(),
        "nach der zweiten Ebene noch ein Fenster",
    )
    jobs = [
        o for o in doc.Objects if o.TypeId == "Path::FeaturePython" and hasattr(o, "Operations")
    ]
    ops = {j.Label: len(js.operationen(j)) for j in jobs}
    h.pruefe(len(jobs) == 3 and all(ops.values()), f"Jobs: {ops}")
    h.pruefe(grundjob in jobs, "Grundjob fehlt")
    for dokument in list(FreeCAD.listDocuments().values()):
        FreeCAD.closeDocument(dokument.Name)
    yield 300
