# Das Fenster „Maschinen“ (W-011 S1): Die Beispiel-Drehmaschine und die 3-Achs-Fräse bauen und
# speichern – sie stehen von selbst in der Liste (beim Speichern). CAM-Addon → Maschinen …: zwei
# Zeilen, „Drehmaschine mit Revolver (12 Plätze), C, Y“ und „3-Achs-Fräse“. Die Datei der Fräse
# verschoben: ihre Zeile rot, „… – nicht gefunden“, „Suchen …“ an; Suchen mit der neuen Datei –
# der Eintrag zieht mit. „Entfernen“: die Drehmaschine aus der Liste, ihre Datei bleibt.
# „Hinzufügen …“ mit ihrer Datei: wieder drin. „Bearbeiten“ öffnet die Datei und „Maschine
# bearbeiten“.
import os
import shutil
import tempfile

import FreeCAD
import FreeCADGui as Gui


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine, gui_maschine, gui_maschinen
    from camaddon import maschinenspeicher as ms

    ms.speichern([])
    # Nicht im temporären Ordner: Eine Datei, die dort verschwindet, nimmt das Fenster selbst aus
    # der Liste (P-2026-10-10-04) – „nicht gefunden“ und „Suchen …“ gibt es nur woanders
    # (P-2026-10-10-45).
    ordner = tempfile.mkdtemp(prefix="camaddon_szenario_", dir=os.path.expanduser("~"))
    dateien = {}
    for art, name in ((beispielmaschine.DREHMASCHINE, "Drehmaschine"),
                      (beispielmaschine.FRAESE_3, "Fraese")):  # fmt: skip
        asm, _maschine = beispielmaschine.lade(art)
        yield from h.warte_auf(lambda asm=asm: FreeCAD.ActiveDocument is asm.Document)
        asm.Document.saveAs(os.path.join(ordner, name + ".FCStd"))
        dateien[name] = asm.Document.FileName  # so, wie FreeCAD den Pfad schreibt
        yield 300
    eintraege = ms.laden()
    h.pruefe(
        [os.path.basename(e.datei) for e in eintraege] == ["Drehmaschine.FCStd", "Fraese.FCStd"],
        f"nach dem Speichern: {[e.datei for e in eintraege]}",
    )
    for dokument in list(FreeCAD.listDocuments().values()):
        FreeCAD.closeDocument(dokument.Name)
    yield 500

    # --- Die Liste --------------------------------------------------------------------------
    Gui.runCommand("CamAddon_Maschinen")
    yield from h.warte_auf(lambda: gui_maschinen.MaschinenDialog.offen is not None, 5000)
    yield 500
    dialog = gui_maschinen.MaschinenDialog.offen
    h.pruefe(dialog is not None and dialog.isVisible(), "kein Fenster „Maschinen“")
    if dialog is None:
        return
    tabelle = dialog.tabelle

    def spalte(n):
        return [tabelle.item(i, n).text() for i in range(tabelle.rowCount())]

    h.pruefe(
        spalte(1) == ["Drehmaschine mit Revolver (12 Plätze), C, Y", "3-Achs-Fräse"],
        f"Arten: {spalte(1)}",
    )
    h.pruefe(not dialog.leer.isVisible(), "„Noch keine Maschine“ bei voller Liste")
    h.bild("1_liste", dialog)

    # --- Eine Datei verschoben: rot, Suchen … -------------------------------------------------
    woanders = os.path.join(ordner, "woanders")
    os.makedirs(woanders)
    neu = os.path.join(woanders, "Fraese.FCStd")
    shutil.move(dateien["Fraese"], neu)
    dialog.fuellen(auswahl=dateien["Fraese"])
    yield 300
    h.pruefe(spalte(2)[1].endswith("– nicht gefunden"), f"verschoben: {spalte(2)}")
    h.pruefe(
        dialog.knopf_suchen.isEnabled() and not dialog.knopf_bearbeiten.isEnabled(),
        "Suchen aus oder Bearbeiten an bei fehlender Datei",
    )
    h.bild("2_nicht_gefunden", dialog)
    gui_maschinen.datei_waehlen = lambda _eltern, _ordner: neu
    dialog.knopf_suchen.click()
    yield 1500
    eintraege = ms.laden()
    h.pruefe(
        len(eintraege) == 2
        and ms.finde(eintraege, neu) is not None
        and ms.finde(eintraege, dateien["Fraese"]) is None,
        f"nach Suchen: {[e.datei for e in eintraege]}",
    )
    h.pruefe(not any(t.endswith("nicht gefunden") for t in spalte(2)), f"rot: {spalte(2)}")

    # --- Entfernen und wieder hinzufügen ---------------------------------------------------------
    dialog.fuellen(auswahl=dateien["Drehmaschine"])
    dialog.knopf_entfernen.click()
    yield 300
    h.pruefe(
        tabelle.rowCount() == 1 and os.path.isfile(dateien["Drehmaschine"]),
        f"Entfernen: {spalte(0)}",
    )
    gui_maschinen.datei_waehlen = lambda _eltern, _ordner: dateien["Drehmaschine"]
    dialog.knopf_hinzufuegen.click()
    yield 2000
    h.pruefe(
        tabelle.rowCount() == 2 and ms.finde(ms.laden(), dateien["Drehmaschine"]) is not None,
        f"Hinzufügen: {spalte(0)}",
    )
    h.pruefe(not FreeCAD.listDocuments(), f"offen geblieben: {list(FreeCAD.listDocuments())}")
    h.bild("3_wieder_drin", dialog)

    # --- Bearbeiten: die Datei und „Maschine bearbeiten“ ---------------------------------------
    dialog.fuellen(auswahl=dateien["Drehmaschine"])
    dialog.knopf_bearbeiten.click()
    yield from h.warte_auf(lambda: Gui.Control.activeDialog(), 20000)
    yield 1500
    panel = gui_maschine.MaschinenPanel.offen
    h.pruefe(
        panel is not None and ms.gleiche_datei(panel.assembly.Document.FileName,
                                               dateien["Drehmaschine"]),
        "„Maschine bearbeiten“ nicht mit der Drehmaschine offen",
    )  # fmt: skip
    h.pruefe(
        any(ms.gleiche_datei(d.FileName, dateien["Drehmaschine"])
            for d in FreeCAD.listDocuments().values()),
        "Datei nicht geöffnet",
    )  # fmt: skip
    h.bild("4_bearbeiten")
    Gui.Control.closeDialog()
    yield 800
    dialog.close()
    yield 300
    for dokument in list(FreeCAD.listDocuments().values()):
        FreeCAD.closeDocument(dokument.Name)
    yield 300
    shutil.rmtree(ordner, ignore_errors=True)
