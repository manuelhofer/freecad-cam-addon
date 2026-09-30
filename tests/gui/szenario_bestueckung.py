# Bestückung je Job (W-002 Stufe G; Manuel, 2026-09-30: „ja jeder job hat seine eigene
# bestückung“, „die bestückung wird nicht dargestellt auf der maschine“). In der
# Werkzeugverwaltung T1 Schaftfräser Ø 12 und T2 Kugelfräser Ø 6, beide im Halter „VDI30
# angetrieben radial“, und T7 Bohrer Ø 8 ohne Halter; die Beispiel-Drehmaschine mit zwölf
# Plätzen und ein Job mit je einem Controller für T1, T2 und T7. Job wählen → „Bestückung“: Das
# Fenster öffnet sich im Dokument der Maschine, P1 zeigt T1, P2 T2, P7 T7, die übrigen
# „– frei –“; im Revolver stecken die drei Werkzeuge, jeder Platz hat seinen Namen. T1 auf
# P5: Sein Controller heißt „T5 …“ und hat die Nummer 5, in der Liste von P3 steht hinter T1
# „– auf P5“. T1 auf P2: Er tauscht mit T2 (T2 auf P5). „– frei –“ lässt sich auf einem belegten
# Platz nicht wählen. Strg+Z im Job nimmt das Tauschen zurück. Zwei Werkzeuge von Hand auf P7:
# ein roter Satz. Schließen: zurück zum Job. „Maschine bearbeiten“ hat keine Bestückung mehr,
# nur einen Satz, wo sie jetzt ist.
import FreeCAD
import FreeCADGui as Gui
from PySide import QtCore


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    import Part  # noqa: F401 – für „Part::Box“
    from Path.Main import Job as PathJob

    from camaddon import beispielmaschine, gui_bestueckung, gui_maschine
    from camaddon import job_schnittwerte as js
    from camaddon import uebergabe_werkzeuge as ue
    from camaddon import werkzeuge as wz
    from camaddon.gui_teile import blaettere_zu

    bib = wz.Bibliothek()
    halter = bib.neuer_halter("vdi30_radial")
    t1 = wz.Werkzeug(nummer=1, durchmesser=12, schneiden=3, schneidenlaenge=26)
    t2 = wz.Werkzeug(nummer=2, art=wz.KUGELFRAESER, durchmesser=6, schneiden=2)
    t7 = wz.Werkzeug(nummer=7, art=wz.BOHRER, durchmesser=8, schneiden=2)
    t1.halter = t2.halter = halter.kennung
    t1.laenge_spindelnase, t2.laenge_spindelnase = 125.0, 110.0
    for w in (t1, t2, t7):
        art = wz.BOHREN if w is t7 else wz.DYNAMISCH
        w.schnittwerte[wz.ALLE] = [wz.Einsatz(art=art, ae=1, ap=5, vc=100, fz=0.05)]
    bib.werkzeuge += [t1, t2, t7]
    bib.speichern()
    ue.uebergeben(bib)

    asm, _ma = beispielmaschine.lade(beispielmaschine.DREHMASCHINE)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    maschinendok = asm.Document

    jobdok = FreeCAD.newDocument("Welle")
    teil = jobdok.addObject("Part::Box", "Teil")
    jobdok.recompute()
    job = PathJob.Create("Job", [teil])
    tc = {}
    for w in (t1, t2, t7):
        tc[w.nummer] = js.controller_ohne_transaktion(
            jobdok, job, w, w.schnittwerte[wz.ALLE][0], nummer=w.nummer
        )
    jobdok.recompute()
    yield 500

    FreeCAD.setActiveDocument(jobdok.Name)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400  # siehe szenario_reichweite.py: 1.1.3 verarbeitet die Auswahl verzögert
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_Bestueckung"))
    yield from h.warte_auf(lambda: gui_bestueckung.BestueckungsPanel.offen is not None)
    panel = gui_bestueckung.BestueckungsPanel.offen
    h.pruefe(panel is not None, "„Bestückung“ geht nicht auf")
    if panel is None:
        return
    h.pruefe(FreeCAD.ActiveDocument is maschinendok, "nicht im Dokument der Maschine")
    wahlen = {p.Platz: w for p, w in panel.wahlen.items()}

    def gewaehlt():
        """{Platz: Werkzeugnummer aus der Werkzeugverwaltung, 0: frei}"""
        ergebnis = {}
        for nummer, wahl in wahlen.items():
            index = wahl.currentData()
            ergebnis[nummer] = panel.eintraege[index].werkzeug.nummer if index >= 0 else 0
        return ergebnis

    soll = dict.fromkeys(range(1, 13), 0)
    soll.update({1: 1, 2: 2, 7: 7})
    h.pruefe(len(wahlen) == 12, f"Zeilen: {len(wahlen)}")
    h.pruefe(gewaehlt() == soll, f"beim Öffnen: {gewaehlt()}")
    h.pruefe(
        panel.bild is not None and sorted(panel.bild.werkzeuge) == [1, 2, 7],
        f"im Revolver: {sorted(panel.bild.werkzeuge) if panel.bild else None}",
    )
    yield 500
    h.bild("1_revolver")
    h.bild("1b_fenster", panel.form)

    def waehle(platz, werkzeug):
        wahl = wahlen[platz]
        index = next(
            i
            for i in range(wahl.count())
            if wahl.itemData(i) >= 0
            and panel.eintraege[wahl.itemData(i)].werkzeug.kennung == werkzeug.kennung
        )
        wahl.setCurrentIndex(index)
        wahl.activated.emit(index)

    # T1 auf P5: sein Controller heißt jetzt T5.
    waehle(5, t1)
    yield 300
    soll.update({1: 0, 5: 1})
    h.pruefe(gewaehlt() == soll, f"T1 auf P5: {gewaehlt()}")
    h.pruefe(
        tc[1].ToolNumber == 5 and tc[1].Label.startswith("T5 "),
        f"Controller von T1: {tc[1].ToolNumber}, {tc[1].Label}",
    )
    liste = wahlen[3]
    texte = [liste.itemText(i) for i in range(liste.count())]
    h.pruefe(any(t.endswith("– auf P5") for t in texte), f"Liste von P3: {texte}")
    h.pruefe(
        sorted(panel.bild.werkzeuge) == [2, 5, 7], f"im Revolver: {sorted(panel.bild.werkzeuge)}"
    )

    # T1 auf P2: tauscht mit T2, der auf P5 kommt. „– frei –“ geht auf P2 nicht.
    waehle(2, t1)
    yield 300
    soll.update({2: 1, 5: 2})
    h.pruefe(gewaehlt() == soll, f"getauscht: {gewaehlt()}")
    h.pruefe(tc[2].ToolNumber == 5 and tc[1].ToolNumber == 2, "T1/T2 nicht getauscht")
    h.pruefe(not wahlen[2].model().item(0).isEnabled(), "„– frei –“ auf belegtem P2 wählbar")
    h.pruefe(wahlen[3].model().item(0).isEnabled(), "„– frei –“ auf freiem P3 gesperrt")
    wahlen[5].showPopup()
    yield 300
    h.bild("2_liste_p5", wahlen[5].view())
    wahlen[5].hidePopup()
    yield 100

    # Strg+Z im Job: das Tauschen zurück.
    jobdok.undo()
    jobdok.recompute()
    panel.fuellen()
    yield 300
    soll.update({2: 2, 5: 1})
    h.pruefe(gewaehlt() == soll, f"nach Strg+Z: {gewaehlt()}")

    # Zwei Werkzeuge auf P7 (von Hand gesetzt): ein roter Satz.
    tc[2].ToolNumber = 7
    jobdok.recompute()
    panel.fuellen()
    yield 300
    h.pruefe(
        panel.doppelt.isVisible() and panel.doppelt.text().startswith("Auf P7 stecken im Job"),
        f"doppelt: {panel.doppelt.text()!r}",
    )
    blaettere_zu(panel.doppelt)
    yield 200
    h.bild("3_doppelt", panel.form)
    tc[2].ToolNumber = 2
    jobdok.recompute()
    panel.accept()
    yield 500
    h.pruefe(gui_bestueckung.BestueckungsPanel.offen is None, "Fenster bleibt offen")
    h.pruefe(FreeCAD.ActiveDocument is jobdok, "Schließen führt nicht zum Job zurück")

    # „Maschine bearbeiten“: keine Bestückung mehr, ein Satz sagt, wo sie ist.
    from camaddon import gui_reichweite

    gui_reichweite.zeige_dokument(maschinendok)
    yield 300
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(asm)
    Gui.runCommand("CamAddon_MaschineBearbeiten")
    yield from h.warte_auf(lambda: gui_maschine.MaschinenPanel.offen is not None)
    mpanel = gui_maschine.MaschinenPanel.offen
    if mpanel is None:
        h.pruefe(False, "„Maschine bearbeiten“ geht nicht auf")
        return
    h.pruefe(not hasattr(mpanel, "platzwahl"), "„Maschine bearbeiten“ bestückt noch")
    blaettere_zu(mpanel.bestueckung_hinweis)
    yield 300
    h.pruefe(
        mpanel.bestueckung_hinweis.isVisible()
        and "legt jeder Job selbst fest" in mpanel.bestueckung_hinweis.text(),
        f"Satz zur Bestückung: {mpanel.bestueckung_hinweis.text()!r}",
    )
    h.bild("4_maschine_bearbeiten", mpanel.form)
    mpanel.reject()
    yield 500
    FreeCAD.closeDocument(jobdok.Name)
    FreeCAD.closeDocument(maschinendok.Name)
    yield 300
