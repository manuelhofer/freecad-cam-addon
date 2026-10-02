# Die Art der Maschine entscheidet (W-011 S3; Manuel, 2026-10-02: „Danach kann man bessere
# Entscheidungen treffen … auf einer Drehbank ist das Rohteil selten eckig“): Die
# Beispiel-Drehmaschine gespeichert und zu – sie steht in der Liste. Eine Welle Ø 30 × 80 längs X,
# die Stirnfläche angeklickt, „Bearbeitung“: In Schritt 1 ist die Drehmaschine gewählt, rot
# darunter „Auf der Drehmaschine ist das Rohteil eine Stange …“, der Knopf „Weiter im
# 4-Achs-Assistenten →“; „Weiter“ geht nicht, „Anlegen“ sagt denselben Satz. Der Knopf: Der
# Assistent schließt (kein Job bleibt), der 4-Achs-Assistent öffnet sich mit der Welle, ihrer
# Stirnfläche und der Drehmaschine (ihre Datei ist dafür offen) – Rundachse C.
import os
import shutil
import tempfile

import FreeCAD
import FreeCADGui as Gui
import Part
from PySide import QtCore, QtGui

V = FreeCAD.Vector


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine, gui_bearbeitung, gui_vierachs
    from camaddon import maschinenspeicher as ms
    from camaddon import vierachs_achsen as va
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    t1 = wz.Werkzeug(nummer=1, durchmesser=8, schneiden=3, schneidenlaenge=20,
                     laenge_spindelnase=125)  # fmt: skip
    t1.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=3.2, ap=2, vc=150, fz=0.04)]
    bibliothek = wz.Bibliothek([t1])
    t1.halter = bibliothek.neuer_halter("vdi30_radial").kennung
    bibliothek.speichern()
    ms.speichern([])
    ordner = tempfile.mkdtemp()
    asm, _maschine = beispielmaschine.lade(beispielmaschine.DREHMASCHINE)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    asm.Document.saveAs(os.path.join(ordner, "Drehmaschine.FCStd"))
    drehmaschine = asm.Document.FileName
    FreeCAD.closeDocument(asm.Document.Name)
    yield 500
    h.pruefe(
        [e.art for e in ms.laden()] == [ms.DREHMASCHINE], f"Liste: {[e.art for e in ms.laden()]}"
    )

    doc = FreeCAD.newDocument("Welle")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Welle")
    teil.Shape = Part.makeCylinder(15, 80, V(), V(1, 0, 0))
    doc.recompute()
    stirn = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if vr.ist_eben(f) and (vr.aussennormale(f) - V(1, 0, 0)).Length < 1e-9
    )
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, stirn)
    yield 500

    # --- Schritt 1: die Drehmaschine – rot der Satz, der Knopf, kein „Weiter“ ----------------
    gui_bearbeitung.nullpunkt_vorgeben(None)
    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    h.pruefe(
        panel.wahl_maschine.currentData() == drehmaschine, f"{panel.wahl_maschine.currentText()!r}"
    )
    hinweis = panel.maschine_hinweis.text()
    h.pruefe(
        panel.maschine_hinweis.isVisible()
        and hinweis.startswith("Auf der Drehmaschine ist das Rohteil eine Stange"),
        f"Hinweis: {hinweis!r}",
    )
    h.pruefe(panel.knopf_vierachs.isVisible(), "kein Knopf zum 4-Achs-Assistenten")
    h.pruefe(not panel.knopf_weiter.isEnabled(), "„Weiter“ auf der Drehmaschine")
    h.bild("1_drehmaschine_schritt1", panel.form)

    # „Anlegen“ sagt denselben Satz und legt nichts an.
    QtCore.QTimer.singleShot(0, panel.accept)
    yield from h.warte_auf(lambda: isinstance(h.modal(), QtGui.QMessageBox), 5000)
    meldung = h.modal()
    text = meldung.text() if isinstance(meldung, QtGui.QMessageBox) else ""
    h.pruefe(text == hinweis, f"Meldung bei „Anlegen“: {text!r}")
    if isinstance(meldung, QtGui.QMessageBox):
        meldung.accept()
    yield 500
    h.pruefe(gui_bearbeitung.BearbeitungPanel.offen is panel, "Fenster nach „Anlegen“ zu")

    # --- Der Knopf: weiter im 4-Achs-Assistenten mit Welle, Stirnfläche, Drehmaschine ---------
    panel.knopf_vierachs.click()
    yield from h.warte_auf(lambda: gui_vierachs.VierachsPanel.offen is not None, 20000)
    yield from h.warte_auf(
        lambda: (
            gui_vierachs.VierachsPanel.offen.job is not None
            if gui_vierachs.VierachsPanel.offen is not None
            else False
        ),
        20000,
    )
    yield 1500
    h.pruefe(gui_bearbeitung.BearbeitungPanel.offen is None, "„Bearbeitung“ noch offen")
    vierachs = gui_vierachs.VierachsPanel.offen
    h.pruefe(vierachs is not None, "kein 4-Achs-Assistent")
    if vierachs is None:
        return
    wahl = vierachs.maschinenwahl()
    h.pruefe(
        isinstance(wahl, va.Maschinenwahl)
        and ms.gleiche_datei(wahl.assembly.Document.FileName, drehmaschine),
        f"Maschine: {vierachs.wahl_maschine.currentText()!r}",
    )
    h.pruefe(
        vierachs.teil is teil and vierachs.flaeche == stirn,
        f"Teil {vierachs.teil and vierachs.teil.Label}, Fläche {vierachs.flaeche}",
    )
    h.pruefe(vierachs.buchstabe() == "C", f"Rundachse {vierachs.buchstabe()}")
    jobs = [o for o in doc.Objects if o.Name.startswith("Job")]
    h.pruefe(len(jobs) == 1, f"Jobs: {[o.Label for o in jobs]}")  # nur der des 4-Achs-Assistenten
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("2_vierachs_mit_drehmaschine")
    vierachs.reject()
    yield 800
    for dokument in list(FreeCAD.listDocuments().values()):
        FreeCAD.closeDocument(dokument.Name)
    yield 300
    shutil.rmtree(ordner, ignore_errors=True)
