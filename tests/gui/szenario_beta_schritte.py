# „Bearbeitung in Schritten“ (Beta; Manuel, 2026-10-30: „die Einzelschritte besser abfragen, und
# zwar einzeln … immer nur dann weiter, wenn auch wirklich alles ausgewählt ist“ – „einen
# Beta-Knopf …, dass wir erstmal das Alte behalten“). Ein Block 100 × 80 × 40 mit einer Tasche
# 60 × 40, 15 tief, Boden gerundet (R 3). Die Beta ist eingeschaltet, eine Wand der Tasche
# angeklickt, „Bearbeitung in Schritten (Beta)“:
# 1. Aufspannung: oben „Worin gespannt?“ – in der Sammlung ein Schraubstock (Spannweite bis 160) und
#    ein kleiner Zentrischspanner (bis 65): der Schraubstock mit ✓ oben, der andere mit ✗; ihn
#    wählen trägt die Aufspannung am Job ein, die Spanntiefe 10 steht im Feld (Plan C5/C6).
#    „Weiter“ gesperrt, bis „Liegt wie im Modell“ geklickt ist.
# 2. Flächen: die eine Wand gehört zu einer Tasche, in der noch Material steht – der Satz dazu,
#    „Ganze Tasche schruppen, diese Wände schlichten“ vorn, „Weiter“ gesperrt; „Ganze Tasche
#    nehmen“ nimmt Wände, Rundungen und Boden dazu, „Weiter“ geht.
# 3. Schruppen: nur Strategien des Schruppens zu sehen; darüber die Werkzeuge für die Tasche – die
#    eigenen, mit „Was gäbe es im Katalog?“ größere aus dem Katalog mit Link (Plan C2). „Weiter“ zum Schlichten (Löcher gibt es
#    hier nicht – übersprungen), „Zurück“, dann „Anlegen“ im Schruppen: nur das Schruppen kommt in
#    den Job, am Job steht, was gewählt war und bis wohin angelegt ist.
# 4. Job anklicken, „Weiter bearbeiten (Beta)“: die Frage „Womit weiter?“ – vorgewählt der Schritt
#    nach dem Schruppen mit etwas (Löcher gibt es keine: grau), „Schruppen – noch einmal“ wählbar, „Messstopp davor“ an; das Fenster
#    beginnt beim Schlichten, die Flächen dieselben; „Anlegen“ – erst der Messstopp, dann das
#    Schlichten (Plan C3).
# ZEITLIMIT: 900
import os
import tempfile

import FreeCAD
import FreeCADGui as Gui
import Part

SCHRUPPEN_MODULE = ("raeumen", "planfraesen", "nut", "kontur", "schruppen3d")


def _art(op):
    return type(getattr(op, "Proxy", None)).__module__.split(".")[-1]


def raeumen_satz_sichtbar(panel):
    block = next(b for b in panel.bloecke if b.s.kennung == "raeumen")
    return block.ergebnis.isVisible() and "<a " not in block.ergebnis.text()


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine
    from camaddon import gui_bearbeitung_beta as beta
    from camaddon import maschinenspeicher as ms
    from camaddon import werkzeuge as wz

    beta.beta_setzen(True)
    t2 = wz.Werkzeug(
        nummer=2,
        name="VHM 6",
        art=wz.SCHAFTFRAESER,
        durchmesser=6.0,
        schneiden=3,
        schneidenlaenge=20.0,
        gesamtlaenge=60.0,
        schneidstoff=wz.VHM,
    )
    t2.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=1.0, ap=6.0, vc=150.0, fz=0.04)]
    wz.Bibliothek([wz.standardwerkzeug(), t2]).speichern()
    from camaddon import spannmittel as sm

    gross = sm.neu(sm.SCHRAUBSTOCK)
    gross.name = "Schraubstock 125"
    klein = sm.neu(sm.ZENTRISCH)
    klein.name = "Zentrisch 46"
    klein.masse["spannweite_max"] = 65.0
    sm.Sammlung([klein, gross]).speichern()
    ms.speichern([])
    ordner = tempfile.mkdtemp()
    asm, _maschine = beispielmaschine.lade(beispielmaschine.FRAESE_3)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    asm.Document.saveAs(os.path.join(ordner, "Fraese.FCStd"))
    yield 300

    V = FreeCAD.Vector
    doc = FreeCAD.newDocument("Tasche")
    teil = doc.addObject("Part::Feature", "Block")
    block = Part.makeBox(100, 80, 40)
    tasche = Part.makeBox(60, 40, 15, V(20, 20, 25))
    form = block.cut(tasche)
    unten = [
        e
        for e in form.Edges
        if abs(e.BoundBox.ZMax - 25) < 1e-6 and abs(e.BoundBox.ZMin - 25) < 1e-6
    ]
    teil.Shape = form.makeFillet(3, unten)
    doc.recompute()
    doc.saveAs(os.path.join(ordner, "tasche.FCStd"))
    wand = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if f.Surface.__class__.__name__ == "Plane"
        and abs(f.normalAt(0, 0).z) < 1e-6
        and f.BoundBox.ZMin > 24
        and abs(f.BoundBox.XMin - 80) < 1e-6
        and abs(f.BoundBox.XMax - 80) < 1e-6
    )
    Gui.activateWorkbench("CAMWorkbench")
    yield 500
    # Der Haken in den Einstellungen und die Leiste „CAM-Addon Beta“.
    from camaddon import gui_sprachwahl, gui_start

    seite = gui_sprachwahl.Einstellungsseite()
    seite.loadSettings()
    h.pruefe(seite.beta_an.isChecked(), "der Haken „Beta-Funktionen zeigen“ ist nicht gesetzt")
    gui_start.beta_umgeschaltet()
    yield 500
    # Seit 0.350.0 sind die Schritte „Bearbeitung“: Ihre Befehle stehen in der gewohnten Leiste,
    # die Beta-Leiste bleibt leer und weg.
    leisten = Gui.getWorkbench("CAMWorkbench").listToolbars()
    h.pruefe(beta.WERKZEUGLEISTE_NAME not in leisten, f"Beta-Leiste da: {leisten}")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, wand)
    yield 500
    Gui.runCommand("CamAddon_BearbeitungBeta")
    yield from h.warte_auf(lambda: beta.BearbeitungPanel.offen is not None, 60000)
    yield 1500
    panel = beta.BearbeitungPanel.offen
    h.pruefe(isinstance(panel, beta.BetaPanel), f"kein Beta-Fenster: {panel!r}")
    if not isinstance(panel, beta.BetaPanel) or panel.job is None:
        h.pruefe(False, "kein Job")
        return

    # 1. Aufspannung
    h.pruefe(panel.seite() == 0, f"Seite {panel.seite()}")
    # „Weiter“ bestätigt die gezeigte Lage (Manuel, 2026-11-11, Frage 1): Es geht ohne Antwort,
    # nichts steht orange da; der nächste Klick ins Teil wäre trotzdem die untere Fläche.
    h.pruefe(panel._weiter_geht() == (True, ""), f"„Weiter“ in Schritt 1: {panel._weiter_geht()}")
    h.pruefe(panel.knopf_weiter.isEnabled(), "„Weiter“ grau in Schritt 1")
    h.pruefe(not panel.warum_text.isVisible(), f"orange in Schritt 1: {panel.warum_text.text()!r}")
    h.pruefe(not panel._beta_unten_klar, "die Lage gilt schon als beantwortet")
    h.pruefe(
        panel.knopf_unten_waehlen.isChecked(), "der Klick auf die untere Fläche ist nicht bereit"
    )
    texte = [panel.wahl_spannmittel.itemText(i) for i in range(panel.wahl_spannmittel.count())]
    print(ascii(f"Spannmittel: {texte} | {panel.spannmittel_text.text()}"))
    h.pruefe(
        len(texte) == 3 and texte[1] == "✓ Schraubstock 125" and texte[2] == "✗ Zentrisch 46",
        f"Auswahl: {texte}",
    )
    panel.wahl_spannmittel.setCurrentIndex(1)
    panel.wahl_spannmittel.activated.emit(1)
    yield 300
    auf = sm.aufspannung(panel.job)
    h.pruefe(auf is not None and auf.spannmittel.name == "Schraubstock 125", "nicht am Job")
    h.pruefe(
        panel.felder_spannung["gespannt"].text() == "10",
        f"Spanntiefe: {panel.felder_spannung['gespannt'].text()!r}",
    )
    h.bild("1_aufspannung", panel.form)
    panel.knopf_weiter.click()  # ohne „Liegt wie im Modell“: „Weiter“ nimmt die gezeigte Lage
    yield 800
    h.pruefe(panel._beta_unten_klar, "„Weiter“ hat die Lage nicht bestätigt")

    # 2. Flächen
    h.pruefe(panel.seite() == 1, f"Seite {panel.seite()}")
    zeilen = [panel.flaechen_liste.item(i).text() for i in range(panel.flaechen_liste.count())]
    h.pruefe(
        not any(z.startswith(("Face", "Edge")) for z in zeilen),
        f"die Liste nennt die Flächen noch beim FreeCAD-Namen: {zeilen}",
    )
    h.pruefe(panel.gewaehlte == [wand], f"gewählt: {panel.gewaehlte}")  # nicht vorbelegt: gewählt
    h.pruefe(panel.tasche_box.isVisible(), "kein Satz zur Tasche")
    # Nicht grau, weil etwas fehlt: Der Klick bleibt im Schritt und rahmt ein, was fehlt (0.351.0).
    # Der orange Satz dazu steht erst nach dem Klick da, nicht als Mahnung von Anfang an.
    h.pruefe(not panel.warum_text.isVisible(), f"orange vor dem Klick: {panel.warum_text.text()!r}")
    panel.knopf_weiter.click()
    yield 300
    h.pruefe(panel.seite() == 1, f"„Weiter“ blättert ohne Entscheidung zur Tasche: {panel.seite()}")
    gerahmt = [
        k.text()
        for k in (panel.knopf_tasche_schruppen, panel.knopf_ganze_tasche, panel.knopf_nur_diese)
        if "border" in k.styleSheet()
    ]
    h.pruefe(
        panel.warum_text.isVisible() and "bold" in panel.warum_text.styleSheet() and bool(gerahmt),
        f"der Klick auf „Weiter“ zeigt nicht, was fehlt: {gerahmt}",
    )
    h.bild("2a_weiter_zeigt_was_fehlt", panel.form)
    yield 2200
    h.pruefe("border" not in panel.knopf_ganze_tasche.styleSheet(), "der Rahmen bleibt stehen")
    # Noch keine Operation: In der Tasche steht Material – der erste Weg ist, sie auszuräumen und
    # nur die angeklickte Wand zu schlichten (Plan C1).
    h.pruefe("noch Material" in panel.tasche_text.text(), f"Satz: {panel.tasche_text.text()!r}")
    h.pruefe(panel.knopf_tasche_schruppen.isVisible(), "kein Knopf „Ganze Tasche schruppen …“")
    h.pruefe(not panel._weiter_geht()[0], "„Weiter“ geht ohne Antwort zur Tasche")
    h.bild("2_flaechen_tasche", panel.form)
    panel.knopf_ganze_tasche.click()
    yield 1000
    flaechen = list(panel.gewaehlte)
    arten = sorted(teil.Shape.Faces[int(n[4:]) - 1].Surface.__class__.__name__ for n in flaechen)
    # 4 Wände, 4 Rundungen, der Boden – und die Ecken der Rundungen (Kugel- oder Torusstücke)
    h.pruefe(len(flaechen) >= 9 and arten.count("Plane") == 5, f"ganze Tasche: {flaechen} {arten}")
    h.pruefe(panel.knopf_weiter.isEnabled(), "„Weiter“ nach „Ganze Tasche“ gesperrt")
    h.bild("2b_ganze_tasche", panel.form)
    panel.knopf_weiter.click()
    yield 500

    # 3. Schruppen
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 300000)
    yield 1000
    h.pruefe(panel.seite() == 2, f"Seite {panel.seite()} statt Schruppen")
    sichtbar = [b.s.kennung for b in panel.bloecke if b.widget.isVisibleTo(panel.form)]
    h.pruefe(
        sichtbar
        and all(
            beta.abschnitt(b) == beta.SCHRUPPEN for b in panel.bloecke if b.s.kennung in sichtbar
        ),
        f"im Schruppen zu sehen: {sichtbar}",
    )
    angehakt = [b.s.kennung for b in panel.aktive_bloecke()]
    print("BETA angehakt", angehakt, "sichtbar", sichtbar, flush=True)
    # „Anlegen“ gibt es nur in der Übersicht (Manuel, 2026-11-11) – im Schritt „Weiter“.
    h.pruefe(not panel.knopf_fertig.isVisible(), "„Anlegen“ steht noch im Schruppen")
    # Im Fenster nur die Summe (die Liste steht als Haken mit Zeitbalken da) – die ganze Liste
    # ist der Tooltip.
    kurz, satz = panel.anlegen_text.text(), panel.anlegen_text.toolTip()
    print("BETA anlegen_text", repr(kurz), repr(satz), flush=True)
    h.pruefe(
        "Räumen (T1" in satz and "zusammen" in satz and "Danach: 3D-Schlichten" in satz,
        f"was „Anlegen“ anlegt: {satz!r}",
    )
    h.pruefe("min" in kurz and "Räumen" not in kurz, f"der kurze Satz: {kurz!r}")
    balken = panel._beta_balken["raeumen"]
    h.pruefe(
        balken.isVisible() and "min" in balken.text() and bool(balken.toolTip()),
        f"Zeitbalken am Räumen: {balken.text()!r} / {balken.toolTip()!r}",
    )
    h.pruefe(not raeumen_satz_sichtbar(panel), "der graue Satz am Räumen steht noch im Schritt")
    # Der Schritt zeigt, was er tut: die Wege der angehakten Strategien im Teil, jede in der Farbe
    # ihres Balkens.
    from camaddon import gui_bahnvorschau as _gbv

    gezeigt = getattr(panel._bahnvorschau, "kennung", None)
    h.pruefe(
        bool(gezeigt) and gezeigt[0] == "uebersicht" and panel._bahnvorschau.wurzel is not None,
        f"im Schritt stehen keine Wege im Teil: {gezeigt}",
    )
    h.pruefe(
        balken._farbe == _gbv.farbe_hex(panel._beta_farben["raeumen"]),
        f"Balken und Wege in verschiedenen Farben: {balken._farbe} / {panel._beta_farben}",
    )
    # Flächen in Sätzen sind Verweise, die die Fläche im Teil aufleuchten lassen.
    from camaddon import gui_bearbeitung as _gb

    satz = _gb.mit_flaechen("In Face27 passt <b>nichts</b>, <a href='x'>Face3</a> & Edge4", "#111")
    h.pruefe(
        'href="flaeche:Face27"' in satz
        and 'href="flaeche:Edge4"' in satz
        and "flaeche:Face3" not in satz,
        f"Verweise auf Flächen: {satz!r}",
    )
    h.pruefe(_gb.mit_flaechen("ohne Namen < 3", "#111") == "ohne Namen < 3", "Satz ohne Fläche")
    probe = _gb._Satz("#111")
    probe.setText("Face2 & mehr")
    h.pruefe(
        probe.text() == "Face2 & mehr" and "flaeche:Face2" in probe.spiegel.text(),
        f"_Satz: {probe.text()!r} / {probe.spiegel.text()!r}",
    )
    panel.flaeche_hervorheben("Face2")
    vorauswahl = Gui.Selection.getPreselection()  # gleich: Neu gefärbt nimmt FreeCAD sie zurück
    h.pruefe(
        "Face2" in tuple(getattr(vorauswahl, "SubElementNames", ()) or ()),
        f"Vorauswahl: {getattr(vorauswahl, 'SubElementNames', None)}",
    )
    panel.flaeche_hervorheben("")
    leer = tuple(getattr(Gui.Selection.getPreselection(), "SubElementNames", ()) or ())
    h.pruefe("Face2" not in leer, f"Vorauswahl bleibt: {leer}")
    # „Nicht dabei“ in der Übersicht: nur der Grund und die Verweise, die ihn beheben.
    from camaddon import gui_bearbeitung_beta as _beta

    kurz = _beta._kurz_mit_verweisen(
        "flanke",
        "Halter oder Schaft führen hier in die Wand: Das Werkzeug steht 48 mm heraus. "
        '<a href="ausspannen:1:161.400:51:">T1 auf 51 mm ausspannen</a>',
    )
    h.pruefe(
        kurz.startswith("Halter oder Schaft führen hier in die Wand – <a ")
        and "block|flanke|ausspannen:1:161.400:51:" in kurz
        and "48 mm" not in kurz,
        f"Nicht dabei, kurz: {kurz!r}",
    )
    # Flächen, die in einer Ebene drankommen: türkis im Teil, der Satz ohne Namen (die im Tooltip).
    echt = panel._geschwenkt
    panel._geschwenkt = lambda _form: ["Face2"]
    try:
        panel._ebene_zeigen()
        satz = panel.ebene_text.text()
        h.pruefe(
            _beta.EBENE_FARBE in satz
            and "Face2" not in satz
            and panel.ebene_text.toolTip() == "Face2"
            and not panel.ebene_text.isHidden(),
            f"Satz zur Ebene: {satz!r} / {panel.ebene_text.toolTip()!r}",
        )
        farben = panel._mit_eigenen_farben({})
        h.pruefe(farben.get(1) == _beta.EBENE_FARBE, f"Farbe der Fläche der Ebene: {farben}")
    finally:
        panel._geschwenkt = echt
        panel._ebene_zeigen()
    h.pruefe(panel.ebene_text.isHidden(), "der Satz zur Ebene bleibt stehen")
    # Der Fräser in der Zeile: dieselbe Wahl wie in den Werten, hin und her.
    raeumen = next(b for b in panel.bloecke if b.s.kennung == "raeumen")
    zeile, _huelle, _klapp = panel._beta_werte["raeumen"]
    from PySide import QtGui

    fraeser = zeile.findChild(QtGui.QComboBox)
    h.pruefe(
        zeile.isVisibleTo(panel.form) and fraeser.count() == raeumen.wahl_fraeser.count() >= 2,
        f"Fräser in der Zeile: {fraeser.count()} / {raeumen.wahl_fraeser.count()}",
    )
    anderer = 1 - raeumen.wahl_fraeser.currentIndex()
    fraeser.activated.emit(anderer)
    yield 500
    h.pruefe(raeumen.wahl_fraeser.currentIndex() == anderer, "die Wahl in der Zeile kommt nicht an")
    raeumen.wahl_fraeser.setCurrentIndex(1 - anderer)
    yield 300
    h.pruefe(
        fraeser.currentIndex() == 1 - anderer, "die Wahl in den Werten kommt nicht in die Zeile"
    )
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 300000)
    yield 500
    # Werkzeuge für die Tasche (Plan C2): die eigenen sofort, der Katalog auf Knopfdruck.
    text = panel.werkzeuge_text.text()
    print(ascii(f"Werkzeuge: {text[:300]}"))
    h.pruefe(panel.werkzeuge_box.isVisible() and "deins: T" in text, f"Werkzeuge: {text!r}")
    h.bild("3_schruppen", panel.form)
    panel.knopf_katalog.click()
    # Der Katalog wird in einem Faden gelesen – das Fenster bleibt frei.
    yield from h.warte_auf(lambda: panel._beta_katalog_an, 60000)
    yield 300
    text = panel.werkzeuge_text.text()
    print(ascii(f"Katalog: {text[:600]}"))
    h.pruefe("im Katalog" in text and "<a href" in text, f"Katalog: {text[:300]!r}")
    # Aus dem Katalog steht „Ø 32 Hoffmann“ da; der ganze Name ist der Tooltip unter der Maus.
    namen = panel._beta_katalog_namen
    h.pruefe(
        bool(namen) and "<table" in text and not any(n in text for n in namen.values()),
        f"Katalog kurz: {len(namen)} Namen",
    )
    h.bild("3c_werkzeuge_katalog", panel.form)
    # Tauchfräsen (Plan C2; Manuel zum Bild: „ja.. so ists ok“): ein Weg zum Anhaken, von sich
    # aus aus – angehakt rechnet er seine Vorschau mit Tauchstellen und Zeit.
    tauchen = next(b for b in panel.bloecke if b.s.kennung == "tauchfraesen")
    h.pruefe(not tauchen.haken.isChecked(), "Tauchfräsen von sich aus angehakt")
    tauchen.haken.setChecked(True)
    yield 500
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 300000)
    yield 800
    satz = tauchen.ergebnis.text()
    print(ascii(f"Tauchfraesen: {satz}"))
    h.pruefe("Tauchstellen" in satz and "min" in satz, f"Tauchfräsen: {satz!r}")
    h.pruefe(tauchen.widget.isVisibleTo(panel.form), "Tauchfräsen nicht im Schritt Schruppen")
    # Der andere Weg für dieselben Böden: Räumen ist aus, die Kontur rechnet mit dem, was das
    # Tauchen weggenommen hat.
    h.pruefe(not raeumen.haken.isChecked(), "Räumen und Tauchfräsen zugleich angehakt")
    h.pruefe(not panel.unfertig.isVisible(), f"mit Tauchfräsen unfertig: {panel.unfertig.text()!r}")
    kontur = next(b for b in panel.bloecke if b.s.kennung == "kontur")
    print(ascii(f"Kontur nach dem Tauchen: {kontur.ergebnis.text()}"))
    h.bild("3d_tauchfraesen", panel.form)
    raeumen.haken.setChecked(True)
    yield 500
    h.pruefe(not tauchen.haken.isChecked(), "Räumen angehakt, Tauchfräsen bleibt an")
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 300000)
    panel.knopf_weiter.click()
    yield 1000
    h.pruefe(panel.seite() == 2 + beta.SCHLICHTEN, f"nach dem Schruppen Seite {panel.seite()}")
    h.bild("4_schlichten", panel.form)
    panel.knopf_zurueck.click()
    yield 500
    h.pruefe(panel.seite() == 2, f"„Zurück“ auf Seite {panel.seite()}")
    vorher = len(panel.job.Operations.Group)
    # In Stufen: nur das Schruppen anlegen (ohne Knopf, accept(bis_hier=True)) – danach „Weiter
    # bearbeiten“ am Job.
    panel.accept(bis_hier=True)
    yield from h.warte_auf(
        lambda: beta.BearbeitungPanel.offen is not panel or panel.geschlossen, 120000
    )
    yield 1500
    job = panel.job
    neu = list(job.Operations.Group)[vorher:]
    print("BETA angelegt", [(op.Label, _art(op)) for op in neu], flush=True)
    h.pruefe(bool(neu), "nichts angelegt")
    h.pruefe(
        all(_art(op) in SCHRUPPEN_MODULE for op in neu),
        f"nicht nur Schruppen: {[_art(o) for o in neu]}",
    )
    h.pruefe(
        list(getattr(job, beta.EIGENSCHAFT_FLAECHEN, [])) == sorted(flaechen)
        and getattr(job, beta.EIGENSCHAFT_ABSCHNITT, None) == beta.SCHRUPPEN,
        f"am Job: {getattr(job, beta.EIGENSCHAFT_FLAECHEN, None)} {getattr(job, beta.EIGENSCHAFT_ABSCHNITT, None)}",
    )

    # 4. Weiter bearbeiten
    Gui.Control.closeDialog()
    yield 500
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400
    h.pruefe(
        Gui.Command.get("CamAddon_WeiterBearbeitenBeta").isActive(), "„Weiter bearbeiten“ grau"
    )
    from PySide import QtCore

    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_WeiterBearbeitenBeta"))
    yield from h.warte_auf(lambda: beta.WeiterFrage.offen is not None, 10000)
    frage = beta.WeiterFrage.offen
    h.pruefe(frage is not None, "keine Frage „Womit weiter?“")
    if frage is None:
        return
    h.pruefe(frage.abschnitt() == beta.SCHLICHTEN, f"vorgewählt: {frage.abschnitt()}")
    h.pruefe(not frage.wahl[beta.LOECHER].isEnabled(), "„Löcher“ wählbar ohne Bohrung")
    h.pruefe(frage.messstopp.isChecked(), "„Messstopp davor“ nicht angehakt")
    h.pruefe("noch einmal" in frage.wahl[beta.SCHRUPPEN].text(), frage.wahl[beta.SCHRUPPEN].text())
    # Was am Messstopp gemessen wird (Plan C3b): die Tasche um das Aufmaß kleiner; an LinuxCNC kein
    # Messzyklus – es hält. Mit einem Zyklus (hier von Hand gesetzt) das Feld für den Taster.
    satz = frage.messen_text.text()
    print(ascii(f"Messen: {satz}"))
    h.pruefe("Tasche 59,4 × 39,4" in satz and "Messzyklus" in satz, f"Messen: {satz!r}")
    h.pruefe(not frage.taster.isVisible(), "Taster-Feld ohne Zyklus")
    frage._zyklus = True
    frage.taster.setText("99")
    yield 200
    satz = frage.messen_text.text()
    h.pruefe(frage.taster.isVisible() and "T99 misst" in satz, f"mit Taster: {satz!r}")
    # „Messzyklus korrigiert den Schlichtfräser selbst“ (Manuel: „ja mach das so“): mit Taster
    # sichtbar, vorbelegt an.
    h.pruefe(
        frage.korrigieren.isVisible()
        and frage.korrigieren.isChecked()
        and "Radius-Verschlei" in satz,
        f"Korrigieren: {frage.korrigieren.isVisible()} {satz!r}",
    )
    h.bild("4b_womit_weiter", frage)
    frage.taster.setText("")
    frage._zyklus = False
    # Das Aufmaß dieses Gangs (3 → 2 → 1 → 0): vorgeschlagen 1 mm weniger als davor, hier 0,5.
    print(ascii(f"Aufmass vorgeschlagen: {frage.aufmass.text()!r}"))
    h.pruefe(frage.aufmass.text() == "0", f"Vorschlag nach 0,3: {frage.aufmass.text()!r}")
    h.pruefe(frage.aufmass.isVisible(), "kein Feld „Aufmaß dieses Gangs“ beim Schlichten")
    frage.aufmass.setText("0,5")
    frage.accept()
    yield from h.warte_auf(lambda: beta.BearbeitungPanel.offen not in (None, panel), 60000)
    weiter = beta.BearbeitungPanel.offen
    yield from h.warte_auf(lambda: weiter is not None and not weiter.vorschau_laeuft(), 300000)
    yield 1000
    if weiter is None:
        h.pruefe(False, "„Weiter bearbeiten“ öffnet kein Fenster")
        return
    h.pruefe(weiter.job is job, "„Weiter bearbeiten“ in einem anderen Job")
    h.pruefe(weiter.seite() > 2, f"„Weiter bearbeiten“ beginnt auf Seite {weiter.seite()}")
    h.pruefe(sorted(weiter.gewaehlte) == sorted(flaechen), f"Flächen: {weiter.gewaehlte}")
    mit_aufmass = [
        b for b in weiter.bloecke if beta.abschnitt(b) == beta.SCHLICHTEN and "aufmass" in b.felder
    ]
    h.pruefe(
        mit_aufmass and all(b.felder["aufmass"].text() == "0,5" for b in mit_aufmass),
        f"Aufmaß im Schlichten: {[(b.s.kennung, b.felder['aufmass'].text()) for b in mit_aufmass]}",
    )
    h.pruefe(
        not weiter.knopf_zurueck.isVisible() or weiter.seite() > 2 + beta.SCHLICHTEN,
        "„Zurück“ ins Schruppen",
    )
    print("BETA weiter angehakt", [b.s.kennung for b in weiter.aktive_bloecke()], flush=True)
    h.bild("5_weiter_bearbeiten", weiter.form)
    vorher = len(job.Operations.Group)
    weiter.accept(bis_hier=True)
    yield from h.warte_auf(
        lambda: beta.BearbeitungPanel.offen is not weiter or weiter.geschlossen, 120000
    )
    yield 1500
    neu = list(job.Operations.Group)[vorher:]
    print("BETA dazu", [(op.Label, _art(op)) for op in neu], flush=True)
    h.pruefe(
        bool(neu) and not any(_art(op) in SCHRUPPEN_MODULE for op in neu),
        f"dazu: {[_art(o) for o in neu]}",
    )
    from camaddon import messstopp as ms

    h.pruefe(
        bool(neu) and ms.ist_messstopp(neu[0]), f"kein Messstopp zuerst: {[o.Label for o in neu]}"
    )
    # Was ein Taster dort messen würde (Plan C3b): die Tasche 60 × 40, um das Aufmaß des Gangs
    # davor kleiner – in Koordinaten des Jobs (der Nullpunkt liegt in der Mitte der Tasche).
    gemessen = ms.merkmal_von(list(neu[0].Gcode)) if neu else None
    print(ascii(f"Messen: {gemessen}"))
    m_ = gemessen[0] if gemessen else None
    h.pruefe(
        m_ is not None
        and m_.art == "tasche"
        and abs(m_.x) < 1e-3
        and abs(m_.y) < 1e-3
        and m_.z_mess < m_.z_oben
        and 55 < m_.laenge_x <= 60
        and abs((60 - m_.laenge_x) - (40 - m_.laenge_y)) < 1e-3,
        f"Messmerkmal: {gemessen}",
    )
    h.bild("6_job", None)

    # 4c. Noch einmal „Weiter bearbeiten“ – jetzt stehen 0,5: „in zwei gleichen Schnitten“ ist
    # angehakt (erst 0,25, dann 0), dazu „Leerfahrt nach jedem Schnitt“ (Manuel, 2026-11-14:
    # „erstes vorschlichten ... nochmal erstes vorschlichten .... dann messsen ... dann
    # vertigschlichten ... und dann nochmal vertig schlichten“). „Anlegen“: Schnitt, Leerfahrt,
    # Messstopp, derselbe Schnitt auf Maß, Leerfahrt.
    from camaddon import leerfahrt as lf

    with __import__("contextlib").suppress(Exception):
        Gui.Control.closeDialog()
    yield 500
    beta.WeiterFrage.offen = None
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_WeiterBearbeitenBeta"))
    yield from h.warte_auf(lambda: beta.WeiterFrage.offen is not None, 10000)
    frage2 = beta.WeiterFrage.offen
    if frage2 is not None:
        frage2.wahl[beta.SCHLICHTEN].setChecked(True)
        yield 200
        h.pruefe(frage2.zwei.isVisible() and frage2.zwei.isChecked(), "„zwei Schnitte“ nicht an")
        h.pruefe(frage2.aufmass.text() == "0", f"Ende: {frage2.aufmass.text()!r}")
        h.pruefe("0,25" in frage2.zwei_text.text(), f"erst/dann: {frage2.zwei_text.text()!r}")
        h.pruefe(not frage2.leerfahrt.isChecked(), "Leerfahrt von selbst an")
        frage2.leerfahrt.setChecked(True)
        yield 200
        h.bild("6b_zwei_schnitte", frage2)
        frage2.accept()
        yield from h.warte_auf(lambda: beta.BearbeitungPanel.offen not in (None, weiter), 60000)
        zweites_fenster = beta.BearbeitungPanel.offen
        yield from h.warte_auf(
            lambda: zweites_fenster is not None and not zweites_fenster.vorschau_laeuft(), 300000
        )
        yield 1000
        vorher = len(job.Operations.Group)
        zweites_fenster.accept(bis_hier=True)
        yield from h.warte_auf(
            lambda: beta.BearbeitungPanel.offen is not zweites_fenster
            or zweites_fenster.geschlossen,
            120000,
        )
        yield 3000
        dazu = list(job.Operations.Group)[vorher:]
        arten = [
            "stopp" if ms.ist_messstopp(o) else "leer" if lf.ist_leerfahrt(o) else "schnitt"
            for o in dazu
        ]
        print("BETA zwei Schnitte", [o.Label for o in dazu], arten, flush=True)
        n = arten.index("leer") if "leer" in arten else 0
        h.pruefe(
            n > 0
            and arten
            == ["schnitt"] * n + ["leer"] * n + ["stopp"] + ["schnitt"] * n + ["leer"] * n,
            f"Folge: {arten}",
        )
        reste = [lf.gang_aufmass(o) for o in dazu if not ms.ist_messstopp(o)]
        h.pruefe(
            all(abs(r - 0.25) < 1e-6 for r in reste[: 2 * n])
            and all(abs(r) < 1e-6 for r in reste[2 * n :]),
            f"Reste der Gänge: {reste}",
        )
        # Das Fenster von Schritt 4 bleibt gehalten (`gehalten`): Fiele sein Python-Objekt hier
        # weg, bräche FreeCAD später in closeDialog ab („double free“).
        gehalten, weiter = weiter, zweites_fenster
        h.pruefe(gehalten is not None, "Fenster von Schritt 4")

    # 5. Neue Aufspannung: derselbe Teil, ein neuer Job, Schritt 1.
    with __import__("contextlib").suppress(Exception):
        Gui.Control.closeDialog()
    yield 500
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400
    h.pruefe(Gui.Command.get("CamAddon_NeueAufspannungBeta").isActive(), "„Neue Aufspannung“ grau")
    jobs_vorher = [o for o in doc.Objects if hasattr(o, "Operations")]
    Gui.runCommand("CamAddon_NeueAufspannungBeta")
    yield from h.warte_auf(lambda: beta.BearbeitungPanel.offen is not weiter, 60000)
    yield 1500
    neu_fenster = beta.BearbeitungPanel.offen
    h.pruefe(isinstance(neu_fenster, beta.BetaPanel), f"kein Beta-Fenster: {neu_fenster!r}")
    if isinstance(neu_fenster, beta.BetaPanel):
        h.pruefe(
            neu_fenster.job is not None and neu_fenster.job not in jobs_vorher,
            "„Neue Aufspannung“ ohne neuen Job",
        )
        h.pruefe(neu_fenster.seite() == 0, f"„Neue Aufspannung“ auf Seite {neu_fenster.seite()}")
        h.pruefe(not neu_fenster._weiter_geht()[0], "„Weiter“ geht vor der Aufspannung")
        h.bild("7_neue_aufspannung", neu_fenster.form)
        neu_fenster.reject()
        yield 1000

    # 6. Ohne Auswahl gestartet: der erste Klick ist die Fläche, die unten liegt.
    zweites = FreeCAD.newDocument("Zweites")
    klotz = zweites.addObject("Part::Feature", "Klotz")
    klotz.Shape = Part.makeBox(60, 40, 20).cut(Part.makeBox(20, 10, 5, V(20, 15, 15)))
    zweites.recompute()
    zweites.saveAs(os.path.join(ordner, "zweites.FCStd"))
    oben_seite = next(
        f"Face{i + 1}"
        for i, f in enumerate(klotz.Shape.Faces)
        if abs(f.BoundBox.ZMin - 20) < 1e-6 and abs(f.BoundBox.ZMax - 20) < 1e-6
    )
    Gui.Selection.clearSelection()
    yield 300
    Gui.runCommand("CamAddon_BearbeitungBeta")
    yield from h.warte_auf(lambda: beta.BearbeitungPanel.offen is not neu_fenster, 60000)
    yield 1000
    leer = beta.BearbeitungPanel.offen
    h.pruefe(isinstance(leer, beta.BetaPanel) and leer.job is None, "ohne Auswahl: schon ein Job?")
    if isinstance(leer, beta.BetaPanel):
        h.pruefe("unten liegt" in leer.anleitung.text(), f"Anleitung: {leer.anleitung.text()!r}")
        Gui.Selection.addSelection(zweites.Name, klotz.Name, oben_seite)
        yield from h.warte_auf(lambda: leer.job is not None, 60000)
        yield 1500
        h.pruefe(leer.job is not None, "der erste Klick legt keinen Job an")
        h.pruefe(leer._unten == oben_seite, f"unten: {leer._unten} statt {oben_seite}")
        h.pruefe(not leer.gewaehlte, f"der Klick auf die Unterseite ist gewählt: {leer.gewaehlte}")
        h.pruefe(
            leer.knopf_weiter.isEnabled(), "„Weiter“ nach dem Klick auf die Unterseite gesperrt"
        )
        h.pruefe(not leer.knopf_unten_waehlen.isChecked(), "„Fläche anklicken …“ bleibt gedrückt")
        h.bild("8_erster_klick_unten", leer.form)
        # „Flächen“ beginnt mit allem, was in dieser Aufspannung von oben geht (Manuel, 2026-11-11,
        # Frage 2: „ja“) – man klickt heraus, was nicht soll.
        leer.knopf_weiter.click()
        yield 1500
        yield from h.warte_auf(lambda: not leer.vorschau_laeuft(), 120000)
        h.pruefe(leer.seite() == 1, f"nach „Weiter“ auf Seite {leer.seite()}")
        h.pruefe(bool(leer.gewaehlte), "„Flächen“ ist nicht vorbelegt")
        h.pruefe(
            leer._weiter_geht()[0], f"vorbelegt, aber „Weiter“ geht nicht: {leer._weiter_geht()}"
        )
        h.bild("9_flaechen_vorbelegt", leer.form)
        # Einmal: Wer die Auswahl leert und zurück- und wieder vorgeht, bekommt sie nicht wieder.
        leer.flaechen_leeren()
        leer.knopf_zurueck.click()
        yield 300
        leer.knopf_weiter.click()
        yield 800
        h.pruefe(not leer.gewaehlte, f"geleert und doch wieder gefüllt: {leer.gewaehlte}")
        leer.reject()
        yield 1000
    with __import__("contextlib").suppress(Exception):
        Gui.Control.closeDialog()
    yield 500
