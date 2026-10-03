# Dialog „Maschine bearbeiten“ an der Beispiel-Drehmaschine: leer öffnen,
# Betriebsarten (Z1, X1, S4 + C4 an einem Gelenk, Revolver) und Aufnahmen
# anlegen, 12 Revolverplätze verteilen, OK = ein Schritt Rückgängig,
# Abbrechen verwirft. „+ Betriebsart“ schlägt den NC-Namen vor (Z → Z1);
# „Vorschlagen“ gibt der leeren Maschine mit einem Klick S1, Z1, X1 und T
# (D-25). Bei X1 steht der Verfahrweg des Gelenks (0 … 200 mm) zum Ändern,
# darunter, wie weit der Werkzeugplatz dabei von der Werkstückaufnahme weg ist
# (Manuel, 2026-09-29: „man müsste schon auch editieren können … die
# verfahrwege“). Mit dem Haken „zählt im Durchmesser (Ø)“ steht der Verfahrweg
# doppelt da (0 … Ø 400), das Gelenk behält den Radius (P-2026-09-30-54).
import os
import sys

import FreeCADGui as Gui
from PySide import QtGui

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def eintrag(baum, text_anfang):
    it = QtGui.QTreeWidgetItemIterator(baum)
    while it.value():
        if it.value().text(0).lstrip("↔⟳ ").startswith(text_anfang):
            return it.value()
        it += 1
    return None


def betriebsart_waehlen(panel, art_text):
    """„+ Betriebsart“ aufklappen und die Art wählen – wie ein Benutzer."""
    menue = panel.knopf_betriebsart.menu()
    menue.aboutToShow.emit()
    next(a for a in menue.actions() if a.text().startswith(art_text)).trigger()


def tippen(widget, text):
    widget.setText(text)
    widget.editingFinished.emit()


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    import beispielmaschinen

    from camaddon import gui_maschine, gui_verteilhilfe
    from camaddon import maschine as m

    asm = beispielmaschinen.drehmaschine()
    doc = asm.Document
    Gui.activateWorkbench("AssemblyWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(asm)
    yield 500
    undo_vorher = len(doc.UndoNames)

    Gui.runCommand("CamAddon_MaschineBearbeiten")
    yield 1500
    panel = gui_maschine.MaschinenPanel.offen
    h.pruefe(panel is not None, "Dialog öffnet sich nicht")
    if panel is None:
        return
    # Die gewählte Baugruppe leuchtet nicht weiter (D-05).
    h.pruefe(not Gui.Selection.getSelection(), f"noch gewählt: {Gui.Selection.getSelection()}")
    h.bild("1_leer")
    h.pruefe(
        panel.hinweise.count() == 2, f"leere Maschine: {panel.hinweise.count()} Hinweise statt 2"
    )
    h.pruefe(panel.knopf_betriebsart.isEnabled(), "„+ Betriebsart“ ist beim Öffnen nicht bedienbar")
    h.pruefe(panel.knopf_vorschlagen.isEnabled(), "„Vorschlagen“ ist beim Öffnen nicht bedienbar")

    # Betriebsarten anlegen – wie ein Benutzer: Gelenk wählen, Art wählen, Felder füllen.
    for gelenk, art, name, werte in (
        ("Z", m.ART_LINEAR, "Z1", ["30000"]),
        ("X", m.ART_LINEAR, "X1", ["24000"]),
        ("Spindel", m.ART_SPINDEL, "S4", ["4000", None, "7,5"]),  # Nennleistung (D-20)
        ("Spindel", m.ART_POSITIONIEREN, "C4", [None, "100"]),
        ("Revolverachse", m.ART_REVOLVER, "T", []),
    ):
        panel.achsen.setCurrentItem(eintrag(panel.achsen, gelenk))
        betriebsart_waehlen(panel, m.art_text(art))
        yield 100
        if art == m.ART_LINEAR:  # der NC-Name ist schon vorgeschlagen (D-25)
            vorgeschlagen = panel.details.feld(0).text()
            h.pruefe(vorgeschlagen == name, f"{gelenk}: vorgeschlagen {vorgeschlagen!r}")
        tippen(panel.details.feld(0), name)
        for i, wert in enumerate(werte, start=1):
            if wert is not None:
                tippen(panel.details.feld(i), wert)
        yield 100

    s4 = next(b for b in m.betriebsarten(panel.maschine) if b.NcName == "S4")
    h.pruefe(
        (s4.Drehzahl, s4.Leistung) == (4000, 7.5), f"S4: {s4.Drehzahl} U/min, {s4.Leistung} kW"
    )

    panel.achsen.setCurrentItem(eintrag(panel.achsen, "X1"))
    yield 300
    h.bild("2_achsen_x1_gewaehlt")

    # Aufnahmen: Futter als Werkstückaufnahme, angetrieben von S4 gibt es nur bei
    # Werkzeugen; Revolverplätze über die Verteilhilfe.
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.getObject("Spannflaeche"))
    panel.knopf_werkstueck.click()
    yield 200
    tippen(panel.details.feld(0), "Futter")
    rev = next(ba for ba in m.betriebsarten(panel.maschine) if ba.Art == m.ART_REVOLVER)
    dialog = gui_verteilhilfe.VerteilDialog(panel.form, [rev], panel.lcs_im_revolver)
    dialog.show()
    yield 300
    h.bild("3_verteilen", dialog)
    angeboten = [dialog.wahl_lcs.itemText(i) for i in range(dialog.wahl_lcs.count())]
    h.pruefe(
        angeboten == ["Werkzeugplatz"],
        f"Verteilhilfe bietet {angeboten} an statt nur den Werkzeugplatz",
    )
    alle = [o.Label for o in panel.alle_lcs()]
    h.pruefe(
        not any(n.startswith("Origin") for n in alle),
        f"Ursprünge als Koordinatensystem angeboten: {alle}",
    )
    dialog.accept()
    m.verteile_plaetze(panel.maschine, panel.kette, rev, doc.getObject("Werkzeugplatz"), 12)
    doc.recompute()
    panel.neu_aufbauen()
    yield 500

    h.pruefe(
        panel.aufnahmen.topLevelItemCount() == 2,
        f"{panel.aufnahmen.topLevelItemCount()} Einträge oben statt 2 (Revolver-Gruppe, Futter)",
    )
    gruppe = panel.aufnahmen.topLevelItem(0)
    h.pruefe(
        gruppe.childCount() == 12 and "12" in gruppe.text(0),
        f"Revolver-Gruppe: {gruppe.text(0)}, {gruppe.childCount()} Plätze",
    )
    del gruppe  # keine Zeilen-Objekte über einen Neuaufbau der Liste hinweg festhalten
    futter = panel.aufnahmen.topLevelItem(1).text(0)
    h.pruefe(futter.startswith("Futter  ·"), f"Aufnahme heißt nicht „Futter“: {futter}")
    texte = [panel.hinweise.item(i).text() for i in range(panel.hinweise.count())]
    h.pruefe(
        texte == ["Alles vollständig – keine Hinweise."], f"Hinweise nach dem Ausfüllen: {texte}"
    )
    h.pruefe(not panel.knopf_vorschlagen.isEnabled(), "„Vorschlagen“ ohne Gelenk ohne Betriebsart")
    panel.aufnahmen.setCurrentItem(eintrag(panel.aufnahmen, "P3"))
    yield 300
    h.bild("4_vollstaendig_p3_gewaehlt")
    # Ein Platz auf dem Revolver hat das Feld „Revolverplatz“, das Futter nicht.
    platzfeld = panel.details.feld(3)
    h.pruefe(
        platzfeld is not None and platzfeld.text() == "P3",
        f"Revolverplatz bei P3: {platzfeld.text() if platzfeld else None!r}",
    )
    panel.aufnahmen.setCurrentItem(eintrag(panel.aufnahmen, "Futter"))
    yield 100
    h.pruefe(panel.details.formular.rowCount() == 2, "Futter: Felder für Werkzeuge")

    # Verfahrweg von X1: die Begrenzung am Gelenk, zum Ändern; leer = keine Grenze,
    # darum steht die Grenze bei 0 als „0“ da. Der graue Text rechnet nach jeder
    # Änderung neu.
    panel.achsen.setCurrentItem(eintrag(panel.achsen, "X1"))
    yield 100
    gelenk_x = doc.getObject("X") or next(o for o in doc.Objects if o.Label == "X")
    von, bis = panel.details.feld(6), panel.details.feld(7)
    h.pruefe(
        isinstance(von, QtGui.QLineEdit) and isinstance(bis, QtGui.QLineEdit),
        f"Verfahrweg: {von!r} {bis!r}",
    )
    if isinstance(von, QtGui.QLineEdit) and isinstance(bis, QtGui.QLineEdit):
        h.pruefe(von.text() == "0" and bis.text() == "200", f"{von.text()!r} … {bis.text()!r}")
        tippen(von, "-50")
        tippen(bis, "")
        yield 200
        h.pruefe(
            gelenk_x.EnableLengthMin and abs(float(gelenk_x.LengthMin) + 50) < 1e-9,
            f"von: {gelenk_x.EnableLengthMin} {gelenk_x.LengthMin}",
        )
        h.pruefe(not gelenk_x.EnableLengthMax, "bis: Grenze nicht ausgeschaltet")
        erklaerung = panel.details.formular.itemAt(8, QtGui.QFormLayout.SpanningRole)
        text = erklaerung.widget().text() if erklaerung is not None else ""
        h.pruefe(
            "Schlittens, nicht die Werkzeugspitze" in text
            and "Jetzt steht X1 auf 0 mm" in text
            and "85 mm von der Werkstückaufnahme weg (längs X1)" in text
            and "„von“ sind es 35 mm; „bis“ ist nicht begrenzt" in text,
            f"Erklärung: {text!r}",
        )
        h.bild("4b_verfahrweg_x1", panel.form)
        tippen(von, "0")
        tippen(bis, "200")
        yield 100
        h.pruefe(
            gelenk_x.EnableLengthMax and abs(float(gelenk_x.LengthMax) - 200) < 1e-9,
            f"bis: {gelenk_x.EnableLengthMax} {gelenk_x.LengthMax}",
        )

    # X im Durchmesser (P-2026-09-30-54): Mit dem Haken stehen die Verfahrwege doppelt da,
    # mit „Ø“ – eingetippt wird im Durchmesser, das Gelenk bekommt den Radius.
    schalter = panel.details.feld(5)
    h.pruefe(
        isinstance(schalter, QtGui.QCheckBox) and not schalter.isChecked(),
        f"Haken „Durchmesser“: {schalter!r}",
    )
    if isinstance(schalter, QtGui.QCheckBox):
        schalter.setChecked(True)
        yield 300  # die Felder bauen sich neu auf
        x1 = next(b for b in m.betriebsarten(panel.maschine) if b.NcName == "X1")
        h.pruefe(x1.Durchmesser, "X1 nach dem Haken nicht im Durchmesser")
        von, bis = panel.details.feld(6), panel.details.feld(7)
        titel = panel.details.formular.itemAt(6, QtGui.QFormLayout.LabelRole)
        titel = titel.widget().text() if titel is not None else ""
        h.pruefe(
            von.text() == "0" and bis.text() == "400" and "Ø" in titel,
            f"im Durchmesser: {titel!r} {von.text()!r} … {bis.text()!r}",
        )
        tippen(von, "-100")
        yield 200
        h.pruefe(
            abs(float(gelenk_x.LengthMin) + 50) < 1e-9,
            f"von Ø −100: Gelenk {gelenk_x.LengthMin} statt −50",
        )
        erklaerung = panel.details.formular.itemAt(8, QtGui.QFormLayout.SpanningRole)
        text = erklaerung.widget().text() if erklaerung is not None else ""
        h.pruefe(
            "Jetzt steht X1 auf Ø 0 mm" in text and "Ø 170 mm von der Werkstückaufnahme" in text,
            f"Erklärung im Durchmesser: {text!r}",
        )
        h.bild("4c_verfahrweg_durchmesser", panel.form)
        tippen(von, "0")
        yield 100
        panel.details.feld(5).setChecked(False)
        yield 300
        h.pruefe(not x1.Durchmesser, "Haken lässt sich nicht wieder abwählen")
        h.pruefe(
            panel.details.feld(6).text() == "0" and panel.details.feld(7).text() == "200",
            f"wieder im Radius: {panel.details.feld(6).text()!r} … {panel.details.feld(7).text()!r}",
        )

    # Home- und Wechselpunkt (P-2026-10-02-48): unter dem Verfahrweg, leer: keiner bzw. wie
    # Home; eingetippt steht er an der Betriebsart, gelöscht ist er wieder aus.
    panel.achsen.setCurrentItem(eintrag(panel.achsen, "X1"))
    yield 100
    x1 = next(b for b in m.betriebsarten(panel.maschine) if b.NcName == "X1")
    home, wechsel = panel.details.feld(9), panel.details.feld(10)
    h.pruefe(
        isinstance(home, QtGui.QLineEdit)
        and isinstance(wechsel, QtGui.QLineEdit)
        and home.text() == ""
        and home.placeholderText() == "leer: keiner"
        and wechsel.placeholderText() == "leer: wie Home",
        f"Home/Wechsel: {home!r} {wechsel!r}",
    )
    if isinstance(home, QtGui.QLineEdit) and isinstance(wechsel, QtGui.QLineEdit):
        tippen(home, "150")
        tippen(wechsel, "0")
        yield 200
        h.pruefe(
            x1.HomeAn and abs(x1.Home - 150) < 1e-9 and x1.WechselAn and x1.Wechsel == 0,
            f"Home {x1.HomeAn} {x1.Home}, Wechsel {x1.WechselAn} {x1.Wechsel}",
        )
        h.bild("4d_home_wechsel", panel.form)
        tippen(panel.details.feld(9), "")
        tippen(panel.details.feld(10), "")
        yield 200
        h.pruefe(not x1.HomeAn and not x1.WechselAn, "Home/Wechsel lassen sich nicht löschen")

    # „Home und Werkzeugwechsel“ (Manuel, 2026-10-03: „finde in Maschine bearbeiten keinen
    # Werkzeugwechselpunkt … sollte MKS sein … oder wechselbar“): unter den Achsen je
    # Linearachse eine Zeile, darüber der Bezug, ab Werk MKS. In den Wechsel von Z1 getippt,
    # steht er an der Betriebsart; auf WKS gestellt, sagt das leere Feld „bleibt stehen“.
    yield 300
    felder = panel.punkte_felder
    h.pruefe(
        {name for name, _art in felder} >= {"X1", "Z1"}
        and panel.wahl_wechsel_bezug.currentData() == m.WECHSEL_MKS,
        f"Home und Werkzeugwechsel: {sorted(felder)}, {panel.wahl_wechsel_bezug.currentData()}",
    )
    z1 = next(b for b in m.betriebsarten(panel.maschine) if b.NcName == "Z1")
    if ("Z1", "Wechsel") in felder:
        tippen(felder[("Z1", "Wechsel")], "480")
        yield 300
        h.pruefe(z1.WechselAn and abs(z1.Wechsel - 480) < 1e-9, f"Z1 Wechsel {z1.Wechsel}")
    panel.wahl_wechsel_bezug.setCurrentIndex(panel.wahl_wechsel_bezug.findData(m.WECHSEL_WKS))
    yield 300
    h.pruefe(m.wechsel_bezug(panel.maschine) == m.WECHSEL_WKS, "Bezug nicht WKS")
    leer = panel.punkte_felder.get(("X1", "Wechsel"))
    h.pruefe(
        leer is not None and leer.placeholderText() == "leer: bleibt stehen",
        f"WKS leer: {leer.placeholderText() if leer is not None else None!r}",
    )
    # Die Details von X1 darüber sagen es auch.
    unten = panel.details.feld(10)
    h.pruefe(
        isinstance(unten, QtGui.QLineEdit) and unten.placeholderText() == "leer: bleibt stehen",
        f"Details WKS: {unten.placeholderText() if isinstance(unten, QtGui.QLineEdit) else unten!r}",
    )
    h.bild("4e_home_und_werkzeugwechsel", panel.form)
    panel.wahl_wechsel_bezug.setCurrentIndex(panel.wahl_wechsel_bezug.findData(m.WECHSEL_MKS))
    yield 300
    if ("Z1", "Wechsel") in panel.punkte_felder:
        tippen(panel.punkte_felder[("Z1", "Wechsel")], "")
        yield 300
    h.pruefe(not z1.WechselAn, "Z1 Wechsel lässt sich nicht löschen")
    # Wie lange der Wechsel selbst dauert (Spezifikation Simulation 13): „8“ getippt → 8 s an der
    # Maschine; leer → 0.
    tippen(panel.feld_wechselzeit, "8")
    yield 200
    h.pruefe(m.wechselzeit(panel.maschine) == 8.0, f"Wechselzeit {m.wechselzeit(panel.maschine)}")
    tippen(panel.feld_wechselzeit, "")
    yield 200
    h.pruefe(m.wechselzeit(panel.maschine) == 0.0, "Wechselzeit lässt sich nicht löschen")

    # Ein Fehler: S4 ohne größte Drehzahl -> Hinweis erscheint, Klick springt zur Spindel. (Der
    # Eilgang hat seit D-14 eine graue Vorgabe und fehlt nie.)
    panel.achsen.setCurrentItem(eintrag(panel.achsen, "S4"))
    yield 100
    drehzahl_vorher = panel.details.feld(1).text()
    tippen(panel.details.feld(1), "")
    yield 300
    texte = [panel.hinweise.item(i).text() for i in range(panel.hinweise.count())]
    h.pruefe(
        any("S4" in t and "Drehzahl" in t for t in texte),
        f"fehlende Drehzahl nicht gemeldet: {texte}",
    )
    panel.aufnahmen.setCurrentItem(None)
    panel.hinweise.itemClicked.emit(panel.hinweise.item(0))
    aktuell = panel.achsen.currentItem()
    h.pruefe(
        aktuell is not None and aktuell.text(0).startswith("S4"),
        "Klick auf Hinweis springt nicht zu S4",
    )
    del aktuell
    tippen(panel.details.feld(1), drehzahl_vorher or "24000")
    yield 300
    h.bild("5_hinweis_geklickt")

    panel.accept()
    yield 500
    h.pruefe(
        len(doc.UndoNames) == undo_vorher + 1,
        f"OK ergibt {len(doc.UndoNames) - undo_vorher} Rückgängig-Schritte statt 1",
    )
    ma = m.finde_maschine(asm)
    namen = sorted(ba.NcName for ba in m.betriebsarten(ma)) if ma else []
    h.pruefe(namen == ["C4", "S4", "T", "X1", "Z1"], f"nach OK: {namen}")

    # Abbrechen verwirft: X1 umbenennen und abbrechen.
    Gui.runCommand("CamAddon_MaschineBearbeiten")
    yield 1000
    panel = gui_maschine.MaschinenPanel.offen
    panel.achsen.setCurrentItem(eintrag(panel.achsen, "X1"))
    tippen(panel.details.feld(0), "X9")
    panel.reject()
    yield 500
    namen = sorted(ba.NcName for ba in m.betriebsarten(ma))
    h.pruefe("X1" in namen and "X9" not in namen, f"Abbrechen verwirft nicht: {namen}")

    # Rückgängig nimmt die ganze Maschine in einem Schritt zurück.
    doc.undo()
    yield 300
    h.pruefe(m.finde_maschine(asm) is None, "Rückgängig entfernt die Maschine nicht")

    # „Vorschlagen“ an der leeren Maschine: ein Klick, S1, Z1, X1 und T (D-25).
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(asm)
    Gui.runCommand("CamAddon_MaschineBearbeiten")
    yield 1000
    panel = gui_maschine.MaschinenPanel.offen
    h.pruefe(panel is not None, "Dialog öffnet sich zum Vorschlagen nicht")
    if panel is None:
        return
    panel.knopf_vorschlagen.click()
    yield 300
    paare = sorted((ba.Gelenk.Label, ba.Art, ba.NcName) for ba in m.betriebsarten(panel.maschine))
    h.pruefe(
        paare
        == [
            ("Revolverachse", m.ART_REVOLVER, "T"),
            ("Spindel", m.ART_SPINDEL, "S1"),
            ("X", m.ART_LINEAR, "X1"),
            ("Z", m.ART_LINEAR, "Z1"),
        ],
        f"vorgeschlagen: {paare}",
    )
    texte = [panel.hinweise.item(i).text() for i in range(panel.hinweise.count())]
    # Der Eilgang hat seit D-14 eine graue Vorgabe; es fehlt die größte Drehzahl.
    h.pruefe(any("S1" in t and "Drehzahl" in t for t in texte), f"fehlende Drehzahl: {texte}")
    h.pruefe(not any("Eilgang" in t for t in texte), f"Hinweis zum Eilgang trotz Vorgabe: {texte}")
    h.pruefe(not panel.knopf_vorschlagen.isEnabled(), "„Vorschlagen“ nach dem Vorschlag bedienbar")
    h.bild("6_vorgeschlagen")
    panel.reject()
    yield 500
