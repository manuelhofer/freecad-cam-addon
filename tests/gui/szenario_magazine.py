# Magazine in der Werkzeugverwaltung (W-002 Stufe H; Manuel, 2026-10-05: „das Paket sollte in der
# Werkzeugverwaltung geschnürt werden“, „beliebig viele Magazine“, „die Maschine muss aber schon
# bestehen“): eine Drehmaschine mit Revolver im Maschinenspeicher, drei Werkzeuge (T1, T2, eins
# ohne Nummer). Werkzeugverwaltung → „Magazine …“ → „Neu“: ein Magazin für die Maschine, mit ihrem
# Namen, „Gilt für diese Maschine“ angehakt, die Plätze vom Revolver; „Aus den Nummern“: T1 und T2,
# „Werkzeug dazu“: das ohne Nummer als T3. T2 auf T1 gestellt: unten rot „T1 steht zweimal“;
# zurück. T1 beladen auf P4. Links ein Baum: die Maschine, aufklappbar, darunter ihre Magazine;
# die Maschine gewählt, legt „Neu“ eins für sie an. Schließen, OK: gespeichert – frisch gelesen
# ist alles da. Dann
# die Rüstliste am Revolver, „Nummern aus dem Magazin“ und das Beladene im Bild (unten).
import os
import tempfile

import FreeCAD
import FreeCADGui as Gui
import Part  # noqa: F401 – für „Part::Box“
from PySide import QtCore


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

    # Der Baum links (Manuel, 2026-10-05: „dass erstmal die Maschine da steht … mit einem Plus
    # aufklappbar … die verschiedenen Magazine zu der Maschine“): eine Kopie und – die Maschine
    # gewählt – „Neu“ für sie: oben die Maschine mit (3), aufgeklappt darunter die drei Magazine.
    kopie = m.magazin_kopieren()
    yield 200
    oben = m.liste.topLevelItem(0)
    m.liste.setCurrentItem(oben)
    yield 200
    h.pruefe(
        m.magazin is None and not m.rechts.isEnabled() and not m.knopf_loeschen.isEnabled(),
        "Maschine gewählt: rechts noch ein Magazin",
    )
    h.pruefe(m.gewaehlte_maschine() == pfad_maschine, f"gewählt: {m.gewaehlte_maschine()!r}")
    drittes = m.magazin_anlegen()
    yield 300
    oben = m.liste.topLevelItem(0)
    kinder = [oben.child(i).text(0) for i in range(oben.childCount())]
    h.pruefe(
        m.liste.topLevelItemCount() == 1
        and oben.text(0) == f"{eintrag.name} (3)"
        and oben.isExpanded()
        and drittes.maschine == pfad_maschine
        and drittes.name == f"{eintrag.name} 2"
        and not drittes.gilt
        and kinder[0] == f"{eintrag.name} ✓"
        and len(kinder) == 3,
        f"Baum: {oben.text(0)!r} {kinder} offen {oben.isExpanded()}",
    )
    h.bild("1a_baum", m)
    oben.setExpanded(False)
    yield 200
    h.bild("1b_baum_zu", m)
    for weg in (drittes, kopie):
        m.liste.setCurrentItem(
            next(
                oben.child(i)
                for i in range(oben.childCount())
                if oben.child(i).data(0, gui_magazine.ROLLE)[1] == weg.kennung
            )
        )
        yield 100
        m.magazin_loeschen(fragen=False)
        yield 200
        oben = m.liste.topLevelItem(0)
    h.pruefe(oben.childCount() == 1, f"nach dem Löschen: {oben.childCount()} Magazine")
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

    # --- Die Rüstliste am Revolver (Stufe H3) und was im Revolver steckt (H4) ------------------
    # Die Fase beladen auf P6 (der Job braucht sie nicht). Ein Job mit dem Anbohrer (im Magazin,
    # nicht beladen: der erste freie Platz ohne Beladung, P1) und dem VHM 12 als T3 (beladen auf
    # P4). „Bestückung“: T1 „nicht beladen – auf P1 einsetzen“, T3 „beladen auf P4 – Nummern aus
    # dem Magazin“; im Bild der Anbohrer und der VHM 12, die Fase durchscheinend auf P6.
    # „Nummern aus dem Magazin“: der VHM 12 auf P4.
    from Path.Main import Job as PathJob

    from camaddon import bestueckung as bs
    from camaddon import gui_bestueckung
    from camaddon import job_schnittwerte as js
    from camaddon import reichweite as rw
    from camaddon import uebergabe_werkzeuge as ue

    gelesen.magazin_fuer(pfad_maschine).eintrag_von(ohne).platz = 6
    for w in gelesen.werkzeuge:
        w.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.DYNAMISCH, ae=1, ap=5, vc=100, fz=0.05)]
    gelesen.speichern()
    ue.uebergeben(gelesen)
    anbohrer_neu = gelesen.werkzeug_mit_kennung(anbohrer.kennung)
    fraeser_neu = gelesen.werkzeug_mit_kennung(fraeser.kennung)
    jobdok = FreeCAD.newDocument("Welle")
    teil = jobdok.addObject("Part::Box", "Teil")
    jobdok.recompute()
    job = PathJob.Create("Job", [teil])
    rw.merke_maschine(job, pfad_maschine)
    platz = bs.platz_fuer(job, anbohrer_neu, gelesen, list(range(1, 13)))
    h.pruefe(platz == 1, f"Anbohrer: P{platz}")
    for w, nummer in ((anbohrer_neu, platz), (fraeser_neu, 3)):
        js.controller_ohne_transaktion(jobdok, job, w, w.schnittwerte[wz.ALLE][0], nummer=nummer)
    jobdok.recompute()
    yield 300
    FreeCAD.setActiveDocument(jobdok.Name)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400  # 1.1.3 verarbeitet die Auswahl verzögert
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_Bestueckung"))
    yield from h.warte_auf(lambda: gui_bestueckung.BestueckungsPanel.offen is not None)
    yield 800
    panel = gui_bestueckung.BestueckungsPanel.offen
    h.pruefe(panel is not None, "„Bestückung“ geht nicht auf")
    if panel is None:
        return
    liste = panel.ruestliste.text()
    h.pruefe(
        "T1&nbsp;&nbsp;" in liste
        and "nicht beladen – auf P1 einsetzen" in liste
        and "T3&nbsp;&nbsp;VHM 12" in liste
        and "beladen auf P4 – Nummern aus dem Magazin" in liste,
        f"Rüstliste: {liste!r}",
    )
    h.pruefe(
        panel.bild is not None
        and sorted(panel.bild.werkzeuge) == [1, 3]
        and sorted(panel.bild.beladen) == [6],
        f"im Revolver: {panel.bild and sorted(panel.bild.werkzeuge)}, "
        f"beladen {panel.bild and sorted(panel.bild.beladen)}",
    )
    p6 = next(w for p, w in panel.wahlen.items() if p.Platz == 6)
    h.pruefe(
        p6.currentText().startswith("– frei – (laut Magazin beladen: Fasenfräser"),
        f"P6: {p6.currentText()!r}",
    )
    h.bild("2_ruestliste_revolver", panel.form)
    h.bild("3_revolver_beladen")
    panel.knopf_nummern.click()
    yield 800
    nummern = sorted(e.nummer for e in bs.eintraege(job, gelesen))  # ohne FreeCADs eigenen
    h.pruefe(nummern == [1, 4], f"nach „Nummern aus dem Magazin“: {nummern}")
    h.pruefe(
        "T4&nbsp;&nbsp;VHM 12" in panel.ruestliste.text()
        and "beladen auf P4<" in panel.ruestliste.text(),
        f"Rüstliste danach: {panel.ruestliste.text()!r}",
    )
    panel.reject()
    yield 500
    FreeCAD.closeDocument(jobdok.Name)
    FreeCAD.closeDocument(asm.Document.Name)
    yield 300
