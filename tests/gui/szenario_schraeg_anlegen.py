# Schräge Fläche ohne Umweg (Manuel, 2026-10-16, am Schwenkteil auf der GROB: „das soll doch in der
# bearbeitung anhand des rohteils … ausgerechnet werden das man das schwenken muss … klar kann ich
# die tasche auch auf einer 3 achs maschine bearbeiten .. aber dann muss ich das ding schräg
# einspannen in den schraubstock … sollen wir dafür die werkzeugwege erstellen und das im
# einstellblatt notieren ?“): das Schwenkteil, nur der Boden der Tasche in der 30°-Schräge
# angeklickt.
# - 5-Achs-Fräse Tisch/Tisch: Schritt 2 sagt, „Anlegen“ legt die Ebene an; kein 3D-Schruppen, kein
#   Knopf „Ebene schwenken“. „Anlegen“: Die Ebene entsteht (mit Rundachsen), der Assistent öffnet
#   dort mit dem Boden – „Boden einer Tasche … – Räumen“, Räumen angehakt; „Anlegen“ räumt die
#   Tasche in der Ebene.
# - Ohne Maschine (3 Achsen): der Haken „Schräg gespannt fräsen“, angehakt, „30° gekippt um X“.
#   Ohne den Haken wie bisher: Freiform (3D). „Anlegen“: eine Aufspannung, von Hand umgespannt,
#   der Assistent dort mit dem Boden; das Einrichtblatt nennt „30° gekippt um X“.
import math
import os
import shutil
import tempfile

import FreeCAD
import FreeCADGui as Gui

ADDON = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _taschenboden(form):
    """Der Boden der Tasche in der 30°-Schräge: eben, 30° geneigt, die kleinste solche Fläche."""
    kandidaten = []
    for i, f in enumerate(form.Faces):
        if f.Surface.__class__.__name__ != "Plane":
            continue
        u0, u1, v0, v1 = f.ParameterRange
        n = f.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
        if abs(math.degrees(math.acos(max(-1.0, min(1.0, n.z)))) - 30.0) < 0.5:
            kandidaten.append((f.Area, f"Face{i + 1}"))
    return min(kandidaten)[1] if kandidaten else None


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine, einrichtblatt, gui_bearbeitung
    from camaddon import maschinenspeicher as ms
    from camaddon import schwenken as sw
    from camaddon import werkzeuge as wz
    from camaddon.sprache import tr

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

    def oeffnen(name):
        """Das Schwenkteil (eine Kopie), der Taschenboden in der Schräge angeklickt, „Bearbeitung“
        offen, Schritt 2."""
        datei = os.path.join(ordner, name + ".FCStd")
        shutil.copy(os.path.join(ADDON, "beispiele", "schwenkteil_5achs.FCStd"), datei)
        doc = FreeCAD.openDocument(datei)
        Gui.activateWorkbench("CAMWorkbench")
        Gui.activeDocument().activeView().viewIsometric()
        Gui.SendMsgToActiveView("ViewFit")
        boden = _taschenboden(doc.getObject("Schwenkteil").Shape)
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(doc.Name, "Schwenkteil", boden)
        yield 500
        gui_bearbeitung.nullpunkt_vorgeben(None)
        Gui.runCommand("CamAddon_Bearbeitung")
        yield from h.warte_auf(
            lambda: getattr(gui_bearbeitung.BearbeitungPanel.offen, "job", None) is not None,
            20000,
        )
        yield 1000
        panel = gui_bearbeitung.BearbeitungPanel.offen
        panel.knopf_weiter.click()
        yield 800
        oeffnen.boden = boden

    def zeilen(panel):
        return [panel.flaechen_liste.item(i).text() for i in range(panel.flaechen_liste.count())]

    def naechster(vorher):
        """Wartet auf den Assistenten nach „Anlegen“ (die Kette, _folge_weiter)."""
        yield from h.warte_auf(
            lambda: gui_bearbeitung.BearbeitungPanel.offen not in (None, vorher)
            and gui_bearbeitung.BearbeitungPanel.offen.job is not None,
            30000,
        )
        yield 1500
        return gui_bearbeitung.BearbeitungPanel.offen

    # --- 5-Achs-Fräse: die Ebene ----------------------------------------------------------------
    yield from oeffnen("Teil1")
    boden = oeffnen.boden
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel._fuenfachs(), f"keine 5-Achs-Fräse: {panel.wahl_maschine.currentText()}")
    h.pruefe(panel.gewaehlte == [boden], f"gewählt: {panel.gewaehlte} statt {boden}")
    liste = zeilen(panel)
    h.pruefe(
        len(liste) == 1 and "kommt in der um 30° geschwenkten Ebene dran" in liste[0],
        f"Liste: {liste}",
    )
    h.pruefe(
        panel.schwenken_zeile.isVisible()
        and "„Anlegen“ legt dafür eine Ebene an" in panel.schwenken_text.text()
        and not panel.schwenken_knopf.isVisible()
        and not panel.gekippt_haken.isVisible(),
        f"Zeile: {panel.schwenken_text.text()!r}",
    )
    h.pruefe(
        not panel.aktive_bloecke(), f"angehakt: {[b.s.kennung for b in panel.aktive_bloecke()]}"
    )
    # Mit den Wänden und Ecken der Tasche: eine Ebene für alle, auch die im Grundjob senkrechten.
    from camaddon import vierachs_rohteil as vr

    form = vr.modell(panel.job).Shape
    flaeche = form.Faces[int(boden[4:]) - 1]
    kanten = {k.hashCode() for k in flaeche.Edges}
    waende = [
        f"Face{i + 1}"
        for i, f in enumerate(form.Faces)
        if f"Face{i + 1}" != boden and kanten & {k.hashCode() for k in f.Edges}
    ]
    for name in waende:
        panel.flaeche_umschalten(name)
    yield 500
    gruppen = panel._schraege_richtungen(form)
    h.pruefe(
        len(gruppen) == 1 and set(gruppen[0].flaechen) == {boden, *waende},
        f"Tasche mit Wänden: {[(round(r.neigung), r.flaechen) for r in gruppen]} – Wände {waende}",
    )
    h.pruefe(not panel.aktive_bloecke(), "mit den Wänden etwas im Grundjob angehakt")
    for name in waende:
        panel.flaeche_umschalten(name)
    yield 500
    h.pruefe(panel._kann_anlegen(), "„Anlegen“ geht nicht")
    h.bild("1_fuenfachs_schritt2", panel.form)
    grundjob = panel.job
    panel.accept()
    ebene_panel = yield from naechster(panel)
    meldung = h.modal()
    h.pruefe(
        ebene_panel is not None and ebene_panel is not panel,
        f"kein Assistent in der Ebene – {getattr(meldung, 'text', lambda: '')()!r}",
    )
    if ebene_panel is None or ebene_panel is panel:
        return
    ebene = ebene_panel.job
    h.pruefe(sw.ist_ebene(ebene) and ebene.Grundjob == grundjob, f"keine Ebene: {ebene.Label}")
    h.pruefe(bool(getattr(ebene, "Rundachsen", "")), "Ebene ohne Rundachsen")
    h.pruefe(ebene_panel.gewaehlte == [boden], f"in der Ebene gewählt: {ebene_panel.gewaehlte}")
    liste = zeilen(ebene_panel)
    h.pruefe(
        len(liste) == 1 and "Boden einer Tasche" in liste[0] and "Räumen" in liste[0],
        f"Liste in der Ebene: {liste}",
    )
    h.pruefe(ebene_panel.raeumen.aktiv(), "Räumen in der Ebene nicht angehakt")
    h.bild("2_fuenfachs_ebene", ebene_panel.form)
    h.bild("3_fuenfachs_ebene_3d")
    ebene_panel.accept()
    yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not ebene_panel, 60000)
    yield 1500
    ops = list(ebene.Operations.Group)
    h.pruefe(bool(ops), "in der Ebene nichts angelegt")
    h.pruefe(not list(grundjob.Operations.Group), "im Grundjob angelegt")
    for dokument in list(FreeCAD.listDocuments().values()):
        FreeCAD.closeDocument(dokument.Name)
    yield 800

    # --- 3 Achsen: schräg gespannt --------------------------------------------------------------
    ms.speichern([])
    yield from oeffnen("Teil2")
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(not panel._fuenfachs(), "eine 5-Achs-Fräse ohne Maschine?")
    liste = zeilen(panel)
    h.pruefe(
        len(liste) == 1 and "kommt um 30° gekippt gespannt dran" in liste[0],
        f"Liste 3 Achsen: {liste}",
    )
    h.pruefe(
        panel.gekippt_haken.isVisible()
        and panel.gekippt_haken.isChecked()
        and "30° gekippt um X spannen" in panel.schwenken_text.text(),
        f"Haken/Zeile: {panel.schwenken_text.text()!r}",
    )
    h.bild("4_dreiachs_schritt2", panel.form)
    panel.gekippt_haken.setChecked(False)
    yield 500
    liste = zeilen(panel)
    h.pruefe("Freiform" in liste[0], f"ohne Haken (3D wie bisher): {liste}")
    panel.gekippt_haken.setChecked(True)
    yield 500
    grundjob = panel.job
    panel.accept()
    gekippt_panel = yield from naechster(panel)
    h.pruefe(gekippt_panel is not None, "kein Assistent in der Aufspannung")
    if gekippt_panel is None:
        return
    gekippt = gekippt_panel.job
    h.pruefe(sw.ist_umspannen(gekippt) and gekippt.Grundjob == grundjob, f"{gekippt.Label}")
    h.pruefe(gekippt_panel.gewaehlte == [boden], f"gekippt gewählt: {gekippt_panel.gewaehlte}")
    h.pruefe("30° gekippt um X spannen" in gekippt_panel._folge, f"Satz: {gekippt_panel._folge!r}")
    spannung = einrichtblatt.spannung_text(gekippt, tr)
    h.pruefe("30° gekippt um X" in spannung, f"Einrichtblatt: {spannung!r}")
    h.bild("5_dreiachs_aufspannung", gekippt_panel.form)
    h.bild("6_dreiachs_aufspannung_3d")
    gekippt_panel.accept()
    yield from h.warte_auf(
        lambda: gui_bearbeitung.BearbeitungPanel.offen is not gekippt_panel, 60000
    )
    yield 1500
    h.pruefe(bool(list(gekippt.Operations.Group)), "in der Aufspannung nichts angelegt")
