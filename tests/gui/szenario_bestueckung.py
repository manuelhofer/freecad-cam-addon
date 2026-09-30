# Bestückung an der Maschine (W-002 Stufe F; Manuel, 2026-09-30: „berücksichtigung an der
# Maschine“). In der Werkzeugverwaltung T1, T2 und T7; die Beispiel-Drehmaschine mit zwölf
# Plätzen. „Maschine bearbeiten“ hat den Abschnitt „Bestückung“: P1 zeigt T1, P2 T2, P7 T7 –
# nach der Nummer –, die übrigen „– frei –“. T1 auf P5 gesteckt: P1 wird frei, in den anderen
# Listen steht hinter T1 „– auf P5“. P2 „– frei –“ entlädt T2. Nach OK steht das in der
# Maschine, und beim nächsten Öffnen zeigt es sich wieder so. Speichert man in der
# Werkzeugverwaltung ein neues T3, steht es gleich zur Wahl und auf P3. Eine Fräse mit einer
# Spindel hat keinen Abschnitt „Bestückung“.
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

    from camaddon import beispielmaschine, gui_maschine
    from camaddon import kette as kette_modul
    from camaddon import maschine as m
    from camaddon import werkzeuge as wz
    from camaddon.gui_teile import blaettere_zu

    t1 = wz.Werkzeug(nummer=1, durchmesser=12)
    t2 = wz.Werkzeug(nummer=2, art=wz.KUGELFRAESER, durchmesser=6)
    t7 = wz.Werkzeug(nummer=7, art=wz.BOHRER, durchmesser=8)
    wz.Bibliothek([t1, t2, t7]).speichern()

    asm, ma = beispielmaschine.lade(beispielmaschine.DREHMASCHINE)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    doc = asm.Document

    def oeffnen():
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(asm)
        Gui.runCommand("CamAddon_MaschineBearbeiten")

    oeffnen()
    yield from h.warte_auf(lambda: gui_maschine.MaschinenPanel.offen is not None)
    panel = gui_maschine.MaschinenPanel.offen
    h.pruefe(panel is not None, "„Maschine bearbeiten“ geht nicht auf")
    if panel is None:
        return
    plaetze = {p.Platz: p for p in panel.platzwahl}

    def gewaehlt():
        return {n: panel.platzwahl[p].currentData() for n, p in plaetze.items()}

    h.pruefe(len(plaetze) == 12, f"Zeilen der Bestückung: {len(plaetze)}")
    soll = dict.fromkeys(range(1, 13), "")
    soll.update({1: t1.kennung, 2: t2.kennung, 7: t7.kennung})
    h.pruefe(gewaehlt() == soll, f"nach der Nummer: {gewaehlt()}")

    # T1 auf P5: P1 wird frei, die anderen Listen sagen, wo T1 steckt.
    wahl = panel.platzwahl[plaetze[5]]
    index = wahl.findData(t1.kennung)
    wahl.setCurrentIndex(index)
    wahl.activated.emit(index)
    yield 200
    soll.update({1: "", 5: t1.kennung})
    h.pruefe(gewaehlt() == soll, f"T1 auf P5: {gewaehlt()}")
    liste = panel.platzwahl[plaetze[3]]
    text = liste.itemText(liste.findData(t1.kennung))
    h.pruefe(text.endswith("– auf P5"), f"T1 in der Liste von P3: {text!r}")

    # P2 „– frei –“: T2 entladen.
    wahl = panel.platzwahl[plaetze[2]]
    wahl.setCurrentIndex(0)
    wahl.activated.emit(0)
    yield 200
    soll[2] = ""
    h.pruefe(gewaehlt() == soll, f"P2 frei: {gewaehlt()}")
    blaettere_zu(panel.bestueckung)
    yield 300
    h.bild("1_bestueckung")
    liste.showPopup()
    yield 300
    h.bild("1b_liste_mit_platz", liste.view())
    liste.hidePopup()
    yield 100
    panel.accept()
    yield 500

    kette = kette_modul.lies_kette(asm)
    bib = wz.Bibliothek.laden()
    auf = {p.Platz: getattr(w, "kennung", "") for p, w in m.bestueckung(ma, kette, bib).items()}
    h.pruefe(auf == soll, f"in der Maschine: {auf}")
    h.pruefe(doc.UndoCount >= 1, "OK ergibt keinen Schritt Rückgängig")

    # Wieder öffnen: dieselbe Bestückung. Ein neues T3 aus der Werkzeugverwaltung steht gleich
    # zur Wahl – und nach der Nummer auf P3.
    oeffnen()
    yield from h.warte_auf(lambda: gui_maschine.MaschinenPanel.offen not in (None, panel))
    panel = gui_maschine.MaschinenPanel.offen
    if panel is None:
        h.pruefe(False, "„Maschine bearbeiten“ geht beim zweiten Mal nicht auf")
        return
    plaetze = {p.Platz: p for p in panel.platzwahl}
    h.pruefe(gewaehlt() == soll, f"beim nächsten Öffnen: {gewaehlt()}")
    dialog = panel.werkzeugverwaltung()
    yield 500
    t3 = wz.Werkzeug(nummer=3, art=wz.TORUSFRAESER, durchmesser=10, eckradius=1)
    bib = wz.Bibliothek.laden()
    bib.werkzeuge.append(t3)
    bib.speichern()
    dialog.gespeichert.emit()
    yield 500
    plaetze = {p.Platz: p for p in panel.platzwahl}
    soll[3] = t3.kennung
    h.pruefe(gewaehlt() == soll, f"T3 nach dem Speichern: {gewaehlt()}")
    dialog.reject()
    yield 300
    blaettere_zu(panel.bestueckung)
    yield 300
    h.bild("2_neues_werkzeug")
    panel.reject()
    yield 500
    FreeCAD.closeDocument(doc.Name)
    yield 300

    # Eine Fräse mit einer Spindel hat nichts zu bestücken: kein Abschnitt.
    asm, _ma = beispielmaschine.lade(beispielmaschine.FRAESE_3)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    alt = gui_maschine.MaschinenPanel.offen
    oeffnen()
    yield from h.warte_auf(lambda: gui_maschine.MaschinenPanel.offen not in (None, alt))
    panel = gui_maschine.MaschinenPanel.offen
    if panel in (None, alt):
        h.pruefe(False, "„Maschine bearbeiten“ geht an der Fräse nicht auf")
        return
    h.pruefe(
        not panel.bestueckung.isVisible() and not panel.knopf_werkzeugverwaltung.isVisible(),
        "Fräse mit Abschnitt „Bestückung“",
    )
    panel.reject()
    yield 500
    FreeCAD.closeDocument(asm.Document.Name)
    yield 300
