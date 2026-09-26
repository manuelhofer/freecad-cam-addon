# „Abfahren“ im Fenster „Auf der Maschine prüfen“ (W-001, Stufe 4b): Die
# Beispiel-Fräse in einem Dokument, ein Teil mit Job in einem zweiten – zwei
# Operationen: eine Kontur 2 mm tief um die Oberseite und ein Bohrzyklus. Das
# Fenster öffnen: In der 3D-Ansicht der Maschine liegen Rohteil (durchscheinend)
# und Teil auf dem Tisch, die Bahn darauf (Vorschub blau, Eilgang rot), das
# Werkzeug steckt in der Spindel. Der Abspieler steht am Anfang: „„Kontur“ ·
# Satz 3 von 11 · 0:00,0 von …“ (FreeCAD rahmt die Bahn mit drei Kommentaren). Mitten auf die zweite Gerade gestellt, sitzt
# die Werkzeugspitze genau auf dem Punkt der Bahn; „Hinsehen“ (Lupe) holt
# Werkstück und Werkzeug heran. Abspielen (×100) läuft bis
# zum Ende und hält an; „Punkt zurück“ geht eine Station zurück; die zweite
# Operation anwählen springt an ihren Anfang. Mit Nullpunkt X 300 fährt X1 über
# die Grenze: Ein Klick auf den Satz stellt den Abspieler an die Stelle, X1 steht
# rot „am Anschlag“. Schließen nimmt die Körper aus der Ansicht und fährt
# zurück. Das Werkzeug T1 (Ø 5, 50 mm) steht in der Werkzeugverwaltung mit einem
# Halter ER16 (70 mm, 20 gespannt): Gerechnet wird mit 100 mm, der Hinweis sagt
# es, und in der Ansicht steckt es in seinem Halter.
import math

import FreeCAD
import FreeCADGui as Gui
from PySide import QtCore

KONTUR = [
    "G0 X0 Y0 Z25",
    "G0 Z21",
    "G1 Z18 F5",
    "G1 X100 F20",
    "G1 Y60",
    "G1 X0",
    "G1 Y0",
    "G0 Z25",
]
BOHREN = ["G0 X50 Y30 Z25", "G81 X50 Y30 Z10 R21 F2", "G80", "G0 Z25"]


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    import Path.Main.Job as PathJob
    import Path.Op.Custom as PathCustom

    from camaddon import beispielmaschine, gui_reichweite
    from camaddon import maschine as m
    from camaddon import verfahren as vf
    from camaddon import werkzeuge as wz

    # T1 wie das Werkzeug des Jobs (Ø 5), mit Halter – so zeigt die Ansicht den Halter.
    bibliothek = wz.Bibliothek([wz.Werkzeug(nummer=1, durchmesser=5.0, gesamtlaenge=50.0)])
    bibliothek.werkzeuge[0].halter = bibliothek.neuer_halter("er16").kennung
    bibliothek.speichern()

    asm, _maschine = beispielmaschine.lade(beispielmaschine.FRAESE_3)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    yield 500
    teile = {o.Name: o for o in asm.Document.Objects if o.TypeId in ("Part::Box", "App::Part")}
    lagen = {n: FreeCAD.Placement(o.Placement) for n, o in teile.items()}

    def bewegt():
        return sorted(n for n, o in teile.items() if not o.Placement.isSame(lagen[n], 1e-6))

    teil = FreeCAD.newDocument("Teil")
    quader = teil.addObject("Part::Box", "Quader")
    quader.Length, quader.Width, quader.Height = 100, 60, 20
    teil.recompute()
    job = PathJob.Create("Job", [quader])
    kontur = PathCustom.Create("Kontur")
    kontur.Gcode = KONTUR
    bohren = PathCustom.Create("Bohren")
    bohren.Gcode = BOHREN
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
    spieler = panel.abspieler
    ansicht = Gui.getDocument(asm.Document.Name).mdiViewsOfType("Gui::View3DInventor")[0]

    def nah():
        """Der Knopf „Hinsehen“: die Kamera auf Werkstück und Werkzeug."""
        spieler.knopf_hinsehen.click()

    def ausschnitt():
        """Wie viel die Kamera zeigt: Höhe (parallel) bzw. Abstand (perspektivisch)."""
        kamera = ansicht.getCameraNode()
        if hasattr(kamera, "height"):
            return kamera.height.getValue()
        return kamera.focalDistance.getValue()

    # --- Geöffnet: die Körper in der Ansicht, der Abspieler am Anfang -----------------------
    h.pruefe(panel.bild is not None, "kein Bild in der 3D-Ansicht")
    h.pruefe(
        panel.bild is not None and ansicht.getSceneGraph().findChild(panel.bild.wurzel) >= 0,
        "Körper nicht in der 3D-Ansicht der Maschine",
    )
    ops = [spieler.wahl_operation.itemText(i) for i in range(spieler.wahl_operation.count())]
    h.pruefe(ops == ["Kontur", "Bohren"], f"Operationen im Abspieler: {ops}")
    h.pruefe(
        spieler.stelle.text().startswith("„Kontur“ · Satz 3 von 11 · 0:00,0 von "),
        f"Stelle am Anfang: {spieler.stelle.text()!r}",
    )
    h.pruefe(spieler.knopf_spielen.text() == "Abspielen", "Knopf heißt nicht „Abspielen“")
    h.pruefe(not spieler.knopf_hinsehen.icon().isNull(), "Knopf „Hinsehen“ ohne Symbol")
    h.pruefe(not bewegt(), f"Maschine bewegt sich schon beim Öffnen: {bewegt()}")
    Gui.SendMsgToActiveView("ViewFit")
    yield 300
    ganz = ausschnitt()
    h.bild("1_geoeffnet")
    nah()
    yield 300
    h.pruefe(ausschnitt() < ganz / 3, f"Hinsehen zoomt nicht: {ganz} → {ausschnitt()}")
    h.pruefe(
        panel.bild.halter[0] is not None and panel.bild.halter[0].name.startswith("Spannzangen"),
        "Halter nicht im Bild",
    )
    h.pruefe(
        "gerechnet mit 100,00 mm, geschätzt aus Halter und Werkzeug" in panel.hinweise.text(),
        f"Hinweis zur Länge: {panel.hinweise.text()!r}",
    )
    h.bild("1b_werkstueck")
    h.bild("1c_fenster", panel.form)

    # --- Mitten auf der zweiten Geraden: die Spitze sitzt auf der Bahn -----------------------
    abfahrt = spieler.abfahrt
    gerade = next(
        i for i, s in enumerate(abfahrt.stationen) if s.punkt == (100.0, 0.0, 18.0)
    )  # Ende von „G1 X100“
    t0, t1 = abfahrt.stationen[gerade - 1].zeit, abfahrt.stationen[gerade].zeit
    spieler.setze_zeit((t0 + t1) / 2)
    yield 300
    spindel = abfahrt.operationen[0].aufnahme
    laenge = abfahrt.operationen[0].laenge
    spitze = m.globale_platzierung(spindel.Lcs).multVec(FreeCAD.Vector(0, 0, -laenge))
    job_lage = m.globale_platzierung(panel.pruefung.werkstueckaufnahme.Lcs).multiply(
        FreeCAD.Placement(panel.nullpunkt(), FreeCAD.Rotation())
    )
    soll = job_lage.multVec(FreeCAD.Vector(50, 0, 18))
    h.pruefe((spitze - soll).Length < 1e-6, f"Spitze {spitze} statt {soll}")
    lage = panel.bild.werkzeug_lage.translation.getValue()
    basis = m.globale_platzierung(spindel.Lcs).Base
    h.pruefe(math.dist(tuple(lage), tuple(basis)) < 1e-3, f"Werkzeug im Bild bei {tuple(lage)}")
    h.pruefe("Tisch" in bewegt(), f"bewegt: {bewegt()}")
    h.pruefe(
        spieler.stelle.text().startswith("„Kontur“ · Satz 6 von 11 · "),
        f"Stelle auf der Geraden: {spieler.stelle.text()!r}",
    )
    h.pruefe(
        spieler.achswerte.text().count("mm") == 3 and "Anschlag" not in spieler.achswerte.text(),
        f"Achswerte: {spieler.achswerte.text()!r}",
    )
    nah()
    yield 300
    h.bild("2_auf_der_geraden")
    h.bild("2b_fenster", panel.form)

    # --- Abspielen mit ×100 bis zum Ende ----------------------------------------------------
    spieler.wahl_tempo.setCurrentIndex(spieler.wahl_tempo.findData(100))
    spieler.anfang()
    spieler.knopf_spielen.click()
    yield 150
    h.pruefe(
        spieler.knopf_spielen.text() == "Anhalten", "Knopf heißt beim Abspielen nicht „Anhalten“"
    )
    h.pruefe(spieler.zeit > 0, f"Zeit läuft nicht: {spieler.zeit}")
    yield from h.warte_auf(lambda: spieler.zeit >= abfahrt.dauer - 1e-9, 5000)
    yield 200
    h.pruefe(abs(spieler.zeit - abfahrt.dauer) < 1e-9, f"nicht am Ende: {spieler.zeit}")
    h.pruefe(spieler.knopf_spielen.text() == "Abspielen", "hält am Ende nicht an")
    h.pruefe(spieler.schieber.value() == spieler.schieber.maximum(), "Schieber nicht am Ende")
    spieler.schritt_zurueck()
    h.pruefe(
        spieler.station == len(abfahrt.stationen) - 2, f"Punkt zurück: Station {spieler.station}"
    )
    spieler.springe_zu_operation(1)
    h.pruefe(
        spieler.stelle.text().startswith("„Bohren“ · Satz 3 von 7 · "),
        f"Zweite Operation: {spieler.stelle.text()!r}",
    )
    yield 300
    h.bild("3_zweite_operation")

    # --- Über der Grenze: ein Klick stellt den Abspieler dorthin ---------------------------
    panel.felder_nullpunkt["X"].setText("300")
    yield 800
    h.pruefe(panel.liste.count() >= 1, "keine Überschreitung mit X 300")
    panel.liste.setCurrentRow(0)
    panel.liste.itemClicked.emit(panel.liste.item(0))
    yield 300
    x1 = next(a for a in panel.pruefung.kette.achsen if vf.namen(panel.maschine, a) == "X1")
    h.pruefe(x1 in spieler.angehalten, "X1 steht nicht am Anschlag")
    h.pruefe(
        abs(panel.pruefung.verfahren.stellung(x1) + 250) < 1e-6,
        f"X1: {panel.pruefung.verfahren.stellung(x1)}",
    )
    h.pruefe(
        "X1 −250,00 mm (am Anschlag)" in spieler.achswerte.text(),
        f"Achswerte: {spieler.achswerte.text()!r}",
    )
    nah()
    yield 300
    h.bild("4_am_anschlag")
    h.bild("4b_fenster", panel.form)

    # --- Schließen beim Abspielen: Körper weg, Maschine zurück, nichts läuft weiter ---------
    wurzel = panel.bild.wurzel
    panel.felder_nullpunkt["X"].setText("")
    spieler.wahl_tempo.setCurrentIndex(spieler.wahl_tempo.findData(1))
    spieler.anfang()
    spieler.knopf_spielen.click()
    yield 200
    panel.reject()
    yield 800
    h.pruefe(gui_reichweite.PruefPanel.offen is None, "Fenster noch offen")
    h.pruefe(ansicht.getSceneGraph().findChild(wurzel) < 0, "Körper nach dem Schließen noch da")
    h.pruefe(not bewegt(), f"Schließen fährt nicht zurück (oder es läuft weiter): {bewegt()}")
    for name in list(FreeCAD.listDocuments()):
        FreeCAD.closeDocument(name)
    yield 300
