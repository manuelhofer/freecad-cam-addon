# „Kollision“ im Fenster „Auf der Maschine prüfen“ (W-001, Stufe 4c): Die
# Beispiel-Fräse (mit zwei Spanneisen) und ein Teil mit Tasche; T1 in der
# Werkzeugverwaltung ist kurz (25 mm). Die Bahn fährt neben dem Teil so tief,
# dass die Spindel auf das rechte Spanneisen setzt – in den Grenzen der
# Achsen. Oben im Fenster stehen, ohne Blättern, die drei Urteile (D-10):
# Achsen, „Kollision: Noch nicht geprüft – jetzt prüfen“, „Werkzeuglänge: Für
# T1 geschätzt – warum?“. „jetzt prüfen“ → oben und unter „Kollision“ rot „Es
# stößt etwas an“ und der Satz „In „Eigene“ berühren sich „Spindel“ und
# „Spanneisen_rechts“ (Satz 4, …)“; „wo?“ blättert zum Abschnitt. Ein Klick
# auf den Satz stellt den Abspieler dorthin, eine rote Kugel zeigt die Stelle.
# Mit Warnabstand 10 mm kommen gelbe Sätze dazu. Ein anderer Nullpunkt macht
# das Ergebnis ungültig. Der Hinweis „T1: ohne Halter geprüft …“ hat „T1 öffnen
# …“ (D-11): Die Werkzeugverwaltung zeigt T1, Halter ER16 wählen, OK – das
# Prüffenster rechnet mit dem Halter, der Hinweis ist weg. Schließen nimmt
# Kugel und Körper weg.
import FreeCAD
import FreeCADGui as Gui
from PySide import QtCore, QtGui


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    import Part
    import Path.Main.Job as PathJob
    import Path.Op.Custom as PathCustom
    from pivy import coin

    from camaddon import beispielmaschine, gui_reichweite, gui_werkzeuge
    from camaddon import kollision as kb
    from camaddon import werkzeuge as wz

    # T1 wie das Werkzeug des Jobs (Ø 5), nur 25 mm lang, ohne Halter; ein ER16 liegt bereit.
    bibliothek = wz.Bibliothek(
        [wz.Werkzeug(nummer=1, durchmesser=5.0, schneidenlaenge=5.0, gesamtlaenge=25.0)]
    )
    er16 = bibliothek.neuer_halter("er16").kennung
    bibliothek.speichern()

    asm, _maschine = beispielmaschine.lade(beispielmaschine.FRAESE_3)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    yield 500
    h.pruefe(asm.Document.getObject("Spanneisen_rechts") is not None, "keine Spanneisen")

    teil = FreeCAD.newDocument("Teil")
    koerper = teil.addObject("Part::Feature", "Taschenteil")
    koerper.Shape = Part.makeBox(100, 60, 20).cut(
        Part.makeBox(40, 30, 15, FreeCAD.Vector(30, 15, 5))
    )
    teil.recompute()
    job = PathJob.Create("Job", [koerper])
    op = PathCustom.Create("Eigene")
    op.Gcode = ["G0 X110 Y30 Z70", "G1 Z20 F10", "G0 Z70"]
    teil.recompute()
    yield 500

    FreeCAD.setActiveDocument(teil.Name)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400  # siehe szenario_reichweite.py: 1.1.3 verarbeitet die Auswahl verzögert
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None)
    panel = gui_reichweite.PruefPanel.offen
    h.pruefe(panel is not None, "„Auf der Maschine prüfen“ öffnet kein Fenster")
    if panel is None:
        return
    yield 500
    k = panel.kollision
    h.pruefe(
        k.urteil.text()
        == "Noch nicht geprüft – „Kollision prüfen“ fährt die Bahn ab und sieht nach.",
        f"vor dem Prüfen: {k.urteil.text()!r}",
    )
    h.bild("1_vorher", panel.form)

    # Die drei Urteile oben – ohne Blättern zu sehen (D-10).
    oben = panel.urteil_kollision.text()
    h.pruefe(oben.startswith("Noch nicht geprüft") and "jetzt prüfen" in oben, f"oben: {oben!r}")
    laenge = panel.urteil_laenge.text()
    h.pruefe(laenge.startswith("Für T1 geschätzt") and "warum?" in laenge, f"Länge: {laenge!r}")
    for urteil in (panel.urteil, panel.urteil_kollision, panel.urteil_laenge):
        h.pruefe(not urteil.visibleRegion().isEmpty(), f"nicht zu sehen: {urteil.text()!r}")
    h.bild("0_urteile_oben")
    # „warum?“ blättert zu den Hinweisen.
    panel.urteil_laenge.linkActivated.emit("abschnitt:hinweise")
    yield 300
    h.pruefe(not panel.hinweise.visibleRegion().isEmpty(), "„warum?“: Hinweise nicht zu sehen")

    # --- Prüfen – über „jetzt prüfen“ oben: die Spindel setzt auf das Spanneisen -------------
    panel.urteil_kollision.linkActivated.emit("kollision:pruefen")
    yield from h.warte_auf(lambda: not k.laeuft and k.ergebnis is not None, 30000)
    yield 300
    h.pruefe(k.urteil.text() == "Es stößt etwas an:", f"Urteil: {k.urteil.text()!r}")
    oben = panel.urteil_kollision.text()
    h.pruefe(oben.startswith("Es stößt etwas an") and "wo?" in oben, f"oben: {oben!r}")
    panel.urteil_kollision.linkActivated.emit("kollision:wo")
    yield 300
    h.pruefe(not k.urteil.visibleRegion().isEmpty(), "„wo?“: Abschnitt Kollision nicht zu sehen")
    saetze = [k.liste.item(i).text() for i in range(k.liste.count())]
    h.pruefe(
        len(saetze) == 1
        and saetze[0].startswith(
            "In „Eigene“ berühren sich „Spindel“ und „Spanneisen_rechts“ (Satz 4, bei X 110, "
            "Y 30, Z "
        ),
        f"Sätze: {saetze}",
    )
    h.pruefe(k.knopf.text() == "Kollision prüfen", "Knopf heißt nach dem Prüfen nicht mehr so")
    h.pruefe(panel.wahl_job.isEnabled(), "Fenster nach dem Prüfen noch gesperrt")
    h.pruefe(panel.urteil.text() == "Alle Achsen bleiben in ihren Grenzen.", "Grenzen?")

    # Ein Klick: Der Abspieler steht dort, die rote Kugel zeigt die Stelle.
    k.liste.setCurrentRow(0)
    k.liste.itemClicked.emit(k.liste.item(0))
    yield 400
    befund = k.ergebnis.befunde[0]
    h.pruefe(abs(panel.abspieler.zeit - befund.zeit) < 1e-9, "Abspieler nicht an der Stelle")
    h.pruefe(panel.bild is not None and panel.bild._marke is not None, "keine rote Kugel")
    # Die Ansicht rückt die Stelle in die Mitte.
    ansicht = Gui.getDocument(asm.Document.Name).mdiViewsOfType("Gui::View3DInventor")[0]
    kamera = ansicht.getCameraNode()
    blick = kamera.orientation.getValue().multVec(coin.SbVec3f(0, 0, -1))
    mitte = kamera.position.getValue() + blick * kamera.focalDistance.getValue()
    stelle = asm.Placement.multVec(befund.stelle)
    h.pruefe(
        (FreeCAD.Vector(*mitte.getValue()) - stelle).Length < 1e-3,
        f"Ansicht nicht auf der Stelle: {mitte.getValue()} statt {stelle}",
    )
    yield 300
    h.bild("2_kollision")
    h.bild("2b_fenster", panel.form)

    # --- Warnabstand 10 mm: gelbe Sätze dazu --------------------------------------------------
    panel.kollision.feld_warnabstand.setText("10")
    k.knopf.click()
    yield from h.warte_auf(lambda: not k.laeuft, 30000)
    yield 300
    saetze = [k.liste.item(i).text() for i in range(k.liste.count())]
    h.pruefe(len(saetze) >= 2, f"mit 10 mm: {saetze}")
    h.pruefe(any("kommen sich" in s and "nahe" in s for s in saetze), f"keine Warnung: {saetze}")
    h.bild("3_warnabstand", panel.form)
    # Nur ein Komma: geprüft wird mit der Vorgabe (1 mm) – kein Fehler.
    panel.kollision.feld_warnabstand.setText(",")
    k.knopf.click()
    yield from h.warte_auf(lambda: not k.laeuft, 30000)
    yield 300
    h.pruefe(
        k.ergebnis is not None and k.ergebnis.warnabstand == kb.WARNABSTAND,
        f"mit „,“: {k.ergebnis.warnabstand if k.ergebnis else None}",
    )
    h.pruefe(k.liste.count() == 1, f"mit „,“: {k.liste.count()} Sätze")
    panel.kollision.feld_warnabstand.setText("")

    # --- Ein anderer Nullpunkt: das Ergebnis gilt nicht mehr ----------------------------------
    panel.felder_nullpunkt["Z"].setText("5")
    yield 800
    h.pruefe(k.ergebnis is None and not k.liste.isVisible(), "Ergebnis nach neuem Nullpunkt")
    h.pruefe(k.urteil.text().startswith("Noch nicht geprüft"), f"{k.urteil.text()!r}")

    # --- „T1 öffnen …“: Halter wählen, OK – das Fenster rechnet mit ihm (D-11) --------------
    panel.felder_nullpunkt["Z"].setText("")
    yield 800
    panel.urteil_kollision.linkActivated.emit("kollision:pruefen")
    yield from h.warte_auf(lambda: not k.laeuft and k.ergebnis is not None, 30000)
    yield 300
    h.pruefe('href="werkzeug:1"' in k.hinweise.text(), f"kein Verweis: {k.hinweise.text()!r}")
    h.pruefe("T1 öffnen …" in k.hinweise.text(), f"Verweistext: {k.hinweise.text()!r}")
    k.hinweise.linkActivated.emit("werkzeug:1")
    yield from h.warte_auf(lambda: gui_werkzeuge.WerkzeugDialog.offen is not None)
    wv = gui_werkzeuge.WerkzeugDialog.offen
    h.pruefe(
        wv is not None and wv.werkzeug is not None and wv.werkzeug.nummer == 1,
        "Werkzeugverwaltung nicht bei T1",
    )
    if wv is not None:
        wv.feld_halter.setCurrentIndex(wv.feld_halter.findData(er16))
        yield 300
        h.bild("4_werkzeugverwaltung_halter", wv)
        wv.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield 800
    h.pruefe(k.ergebnis is None, "Kollision nach dem Speichern nicht veraltet")
    t1 = panel.bibliothek.werkzeuge[0] if panel.bibliothek else None
    h.pruefe(t1 is not None and t1.halter == er16, "Prüffenster kennt den Halter nicht")
    panel.urteil_kollision.linkActivated.emit("kollision:pruefen")
    yield from h.warte_auf(lambda: not k.laeuft and k.ergebnis is not None, 30000)
    yield 300
    hinweise = k.ergebnis.hinweise if k.ergebnis else []
    h.pruefe(not any("ohne Halter" in s for s in hinweise), f"mit Halter: {hinweise}")
    h.bild("5_mit_halter", panel.form)

    # --- Schließen: Kugel und Körper weg ------------------------------------------------------
    wurzel = panel.bild.wurzel
    panel.felder_nullpunkt["Z"].setText("")
    panel.reject()
    yield 800
    h.pruefe(gui_reichweite.PruefPanel.offen is None, "Fenster noch offen")
    h.pruefe(ansicht.getSceneGraph().findChild(wurzel) < 0, "Körper nach dem Schließen noch da")
    for name in list(FreeCAD.listDocuments()):
        FreeCAD.closeDocument(name)
    yield 300
