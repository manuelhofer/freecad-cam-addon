# Manuels Fall (2026-10-16): das Schwenkteil auf der GROB G550 (waagerechte Spindel, Tisch A/B),
# nur der Taschenboden in der 30°-Schräge gewählt (Face27). „Bearbeitung“: Schritt 2 sagt,
# „Anlegen“ legt die Ebene an; „Anlegen“ – die Ebene (A60 B0 oder gleichwertig) entsteht, der
# Assistent dort räumt die Tasche; „Anlegen“. „Auf der Maschine prüfen“ am Grundjob: Achsen in
# ihren Grenzen, „Kollision prüfen“ – nichts berührt sich; Bilder der Maschine mitten in der
# Tasche und das Prüffenster, ohne „so gefahren, passt sie nicht zum Teil“ (Manuel: „was dann die
# grob draus macht ist auch wild .. keine kollsion erkannt ???“).
# ZEITLIMIT: 900
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

    from camaddon import beispielmaschine, gui_bearbeitung
    from camaddon import maschinenspeicher as ms
    from camaddon import schwenken as sw
    from camaddon import werkzeuge as wz

    wz.Bibliothek([wz.standardwerkzeug()]).speichern()
    ms.speichern([])
    ordner = tempfile.mkdtemp()
    asm, _maschine = beispielmaschine.lade(beispielmaschine.GROB_G550)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    asm.Document.saveAs(os.path.join(ordner, "G550.FCStd"))
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
        len(liste) == 1 and "30° schräg – kommt in der geschwenkten Ebene dran" in liste[0],
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
    # --- Auf der Maschine prüfen (der Grundjob mit seiner Ebene) ------------------------------
    from PySide import QtCore, QtGui

    from camaddon import gui_reichweite

    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(grundjob)
    yield 400
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None, 60000)
    pruefung = gui_reichweite.PruefPanel.offen
    h.pruefe(pruefung is not None, "„Auf der Maschine prüfen“ öffnet kein Fenster")
    if pruefung is None:
        return
    yield 2000
    h.pruefe(
        pruefung.urteil.text().startswith("Alle Achsen bleiben"),
        f"Achsen: {pruefung.urteil.text()!r}",
    )
    hinweise = pruefung.form.findChildren(QtGui.QLabel)
    h.pruefe(
        not any("passt sie nicht zum Teil" in w.text() for w in hinweise),
        "Hinweis „passt sie nicht zum Teil“ unter der Ebene",
    )
    h.bild("4_g550_pruefen", pruefung.form)
    spieler = pruefung.abspieler
    fahrt = spieler.abfahrt
    mitte = [i for i, s in enumerate(fahrt.stationen) if not s.ziel and not s.eilgang]
    if mitte:
        spieler.springe_zu_station(mitte[len(mitte) // 2])
        yield 800
        Gui.activeDocument().activeView().viewIsometric()
        Gui.SendMsgToActiveView("ViewFit")
        yield 800
        h.bild("5_g550_in_der_tasche")
    bereich = getattr(pruefung, "kollision", None)
    if bereich is not None and hasattr(bereich, "pruefen"):
        bereich.pruefen()
        yield 500
        urteil = pruefung.urteil_kollision.text()
        with open(os.path.join(os.environ["CAMADDON_AUSGABE"], "kollision.txt"), "w") as d:
            d.write(urteil + "\n")
            for b in (
                getattr(bereich, "ergebnis", None).befunde
                if getattr(bereich, "ergebnis", None)
                else []
            ):
                d.write(b.text() + "\n")
        h.bild("6_g550_kollision", pruefung.form)
        h.pruefe(urteil.startswith("Nichts berührt sich"), f"Kollision: {urteil}")
    pruefung.reject()
    yield 500
