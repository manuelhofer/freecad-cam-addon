# Magazine in der Werkzeugverwaltung (W-002 Stufe H; Manuel, 2026-10-05: „das Paket sollte in der
# Werkzeugverwaltung geschnürt werden“, „beliebig viele Magazine“, „die Maschine muss aber schon
# bestehen“): eine Drehmaschine mit Revolver im Maschinenspeicher, drei Werkzeuge (T1, T2, eins
# ohne Nummer). Werkzeugverwaltung → „Magazine …“ → „Neu“: ein Magazin für die Maschine, mit ihrem
# Namen, „Gilt für diese Maschine“ angehakt, die Plätze vom Revolver; „Aus den Nummern“: T1 und T2,
# „Werkzeug dazu“: das ohne Nummer als T3. T2 auf T1 gestellt: unten rot „T1 steht zweimal“;
# zurück. T1 beladen auf P4. Schließen, OK: gespeichert – frisch gelesen ist alles da.
import os
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

    from camaddon import beispielmaschine, gui_magazine, gui_werkzeuge
    from camaddon import maschinenspeicher as msp
    from camaddon import werkzeuge as wz

    ordner = tempfile.mkdtemp()
    asm, _maschine = beispielmaschine.lade(beispielmaschine.DREHMASCHINE)
    pfad_maschine = os.path.join(ordner, "clx550.FCStd")
    asm.Document.saveAs(pfad_maschine)
    msp.merken_datei(pfad_maschine)
    eintrag = msp.finde(msp.laden(), pfad_maschine)
    h.pruefe(eintrag is not None and eintrag.revolver, f"Maschine im Speicher: {eintrag}")
    yield 300
    fraeser = wz.Werkzeug(nummer=1, name="VHM 12", durchmesser=12, schneiden=3)
    anbohrer = wz.Werkzeug(nummer=2, art=wz.NC_ANBOHRER, durchmesser=10)
    ohne = wz.Werkzeug(nummer=0, name="Fase", art=wz.FASENFRAESER, durchmesser=10)
    wz.Bibliothek([fraeser, anbohrer, ohne]).speichern()

    Gui.runCommand("CamAddon_Werkzeugverwaltung")
    yield 1000
    d = gui_werkzeuge.WerkzeugDialog.offen
    h.pruefe(d is not None, "Werkzeugverwaltung öffnet nicht")
    if d is None:
        return
    m = d.magazine_zeigen()
    yield 600
    h.pruefe(gui_magazine.MagazinDialog.offen is m, "„Magazine …“ öffnet kein Fenster")
    magazin = m.magazin_anlegen()
    yield 300
    h.pruefe(
        magazin.maschine == pfad_maschine and magazin.gilt and magazin.name == eintrag.name,
        f"neues Magazin: {magazin.name}, {magazin.maschine}, gilt {magazin.gilt}",
    )
    h.pruefe(
        m.haken_gilt.isChecked() and str(eintrag.plaetze) in m.plaetze_text.text(),
        f"Plätze: {m.plaetze_text.text()!r}",
    )
    h.pruefe(m.aus_nummern() == 2, "„Aus den Nummern“ nicht zwei")
    dazu = m.werkzeug_dazu()
    yield 300
    h.pruefe(
        dazu is not None and dazu.werkzeug == ohne.kennung and dazu.nummer == 3,
        f"Werkzeug dazu: {dazu}",
    )
    h.pruefe(m.tabelle.rowCount() == 3, f"Zeilen: {m.tabelle.rowCount()}")
    # T2 auf T1: rot, zweimal – und zurück.
    m.tabelle.cellWidget(1, gui_magazine.SPALTE_T).setValue(1)
    yield 300
    h.pruefe("T1" in m.probleme.text(), f"doppelte Nummer nicht gemeldet: {m.probleme.text()!r}")
    m.tabelle.cellWidget(1, gui_magazine.SPALTE_T).setValue(2)
    yield 300
    h.pruefe(not m.probleme.text(), f"rot: {m.probleme.text()!r}")
    m.tabelle.cellWidget(0, gui_magazine.SPALTE_PLATZ).setValue(4)
    m.tabelle.cellWidget(1, gui_magazine.SPALTE_NAME).setText("ANBOHRER_D10")
    m.tabelle.cellWidget(1, gui_magazine.SPALTE_NAME).textEdited.emit("ANBOHRER_D10")
    yield 300
    h.bild("1_magazin", m)
    m.accept()
    yield 300
    d.accept()
    yield 500
    gelesen = wz.Bibliothek.laden()
    gilt = gelesen.magazin_fuer(pfad_maschine)
    h.pruefe(gilt is not None and len(gilt.eintraege) == 3, "Magazin nicht gespeichert")
    if gilt is not None:
        t1 = gilt.mit_nummer(1)
        t2 = gilt.mit_nummer(2)
        h.pruefe(
            t1 is not None
            and t1.werkzeug == fraeser.kennung
            and t1.platz == 4
            and t2 is not None
            and t2.name == "ANBOHRER_D10"
            and t2.platz == 0,
            f"Einträge: {gilt.eintraege}",
        )
    FreeCAD.closeDocument(asm.Document.Name)
    yield 300
