# Das Magazin der Maschine im 4-Achs-Assistenten (W-002 Stufe H2; Manuel, 2026-10-05: „E3 a ja,
# E7 a ja“): die Beispiel-Drehmaschine gespeichert und offen; im Magazin der VHM 12 als T11
# beladen auf P4 und der Kugelfräser als T12 (nicht beladen); der Schaftfräser Ø 10 nicht.
# Welle, Stirn angeklickt, „4-Achs-Bearbeitung“, Schritt 2: In „Fräser“ steht oben „P4 · T11 …“
# (beladen, der Platz im Job vorn), dann „P1 · T12 …“, unten „P1 · – … – nicht im Magazin“ –
# nicht auf P4, da ist der VHM 12 beladen. Den Ø 10 gewählt: gelb „… steht nicht im Magazin …“ mit dem Verweis „Ins
# Magazin übernehmen“; angeklickt: Er steht als T1 im Magazin, der Satz zum Magazin ist weg.
import os
import tempfile

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

    from camaddon import beispielmaschine, gui_vierachs
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    bibliothek = wz.Bibliothek()
    halter = bibliothek.neuer_halter("vdi30_radial")
    vhm12 = bibliothek.neues_werkzeug()
    vhm12.nummer, vhm12.durchmesser, vhm12.schneiden, vhm12.schneidenlaenge = 1, 12.0, 3, 26.0
    vhm12.name, vhm12.laenge_spindelnase, vhm12.halter = "VHM 12", 125.0, halter.kennung
    vhm12.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=4.8, ap=2, vc=150, fz=0.08)]
    kugel = bibliothek.neues_werkzeug()
    kugel.nummer, kugel.art, kugel.durchmesser, kugel.schneiden = 2, wz.KUGELFRAESER, 6.0, 2
    kugel.laenge_spindelnase, kugel.halter = 110.0, halter.kennung
    kugel.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=1.0, ap=6, vc=150, fz=0.04)]
    d10 = bibliothek.neues_werkzeug()
    d10.nummer, d10.durchmesser, d10.schneiden, d10.laenge_spindelnase = 3, 10.0, 3, 90.0
    d10.name, d10.halter = "D10", halter.kennung
    d10.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=4.0, ap=2, vc=150, fz=0.08)]

    asm, _maschine = beispielmaschine.lade(beispielmaschine.DREHMASCHINE)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    pfad = os.path.join(tempfile.mkdtemp(), "clx550.FCStd")
    asm.Document.saveAs(pfad)
    yield 300
    magazin = bibliothek.neues_magazin("CLX 550", pfad)
    magazin.hinzufuegen(vhm12, 11).platz = 4
    magazin.hinzufuegen(kugel, 12)
    bibliothek.speichern()

    doc = FreeCAD.newDocument("Welle")
    teil = doc.addObject("Part::Feature", "Welle")
    welle = Part.makeCylinder(25, 25, FreeCAD.Vector(15, 0, 0), FreeCAD.Vector(1, 0, 0))
    welle = welle.fuse(Part.makeCylinder(18, 15, FreeCAD.Vector(), FreeCAD.Vector(1, 0, 0)))
    teil.Shape = welle.removeSplitter()
    doc.recompute()
    Gui.activateWorkbench("CAMWorkbench")
    stirn = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if vr.ist_eben(f)
        and (vr.aussennormale(f) - FreeCAD.Vector(1, 0, 0)).Length < 1e-9
        and f.Area > 1500
    )
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, stirn)
    yield 500

    Gui.runCommand("CamAddon_Vierachs")
    yield 1500
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    panel.feld_stange.setText("60")
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 3000)
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    panel.knopf_weiter.click()
    yield 500
    h.pruefe(panel._magazin() is not None, f"kein Magazin zu {panel._maschinen_datei()!r}")
    zeilen = [panel.wahl_fraeser.itemText(i) for i in range(panel.wahl_fraeser.count())]
    h.pruefe(
        len(zeilen) == 3
        and zeilen[0].startswith("P4 · T11  VHM 12")
        and zeilen[1].startswith("P1 · T12  Kugelfräser")
        and zeilen[2].startswith("P1 · –  D10")
        and zeilen[2].endswith("nicht im Magazin"),
        f"Liste: {zeilen}",
    )
    h.pruefe(panel.fraeser() is vhm12 or panel.fraeser().kennung == vhm12.kennung, "nicht VHM 12")
    yield from h.warte_auf(lambda: panel.vorschau is not None, 30000)
    h.pruefe("Magazin" not in panel.lage_schruppen.text(), panel.lage_schruppen.text())

    # Der D10 – nicht im Magazin: gelb, mit dem Verweis zum Übernehmen.
    panel.wahl_fraeser.setCurrentIndex([w.kennung for w in panel._fraeser].index(d10.kennung))
    yield from h.warte_auf(lambda: panel.vorschau is not None, 30000)
    gelb = panel.lage_schruppen.text()
    h.pruefe(
        not panel.lage_schruppen.isHidden()
        and "steht nicht im Magazin „CLX 550“" in gelb
        and f'href="magazin:{d10.kennung}">Ins Magazin übernehmen</a>' in gelb,
        f"gelb beim D10: {gelb!r}",
    )
    h.bild("1_nicht_im_magazin", panel.form)
    panel.lage_schruppen.linkActivated.emit(f"magazin:{d10.kennung}")
    yield from h.warte_auf(lambda: panel.vorschau is not None, 30000)
    gelesen = wz.Bibliothek.laden().magazin_fuer(pfad)
    eintrag = gelesen.eintrag_von(d10) if gelesen is not None else None
    h.pruefe(eintrag is not None and eintrag.nummer == 1, f"übernommen: {eintrag}")
    h.pruefe(panel.fraeser() is not None and panel.fraeser().kennung == d10.kennung, "nicht D10")
    h.pruefe("Magazin" not in panel.lage_schruppen.text(), panel.lage_schruppen.text())
    h.pruefe(
        panel.wahl_fraeser.currentText().startswith("P1 · T1  D10"),
        f"Zeile: {panel.wahl_fraeser.currentText()!r}",
    )
    h.bild("2_uebernommen", panel.form)
    panel.reject()
    yield 500
    FreeCAD.closeDocument(doc.Name)
    yield 300
