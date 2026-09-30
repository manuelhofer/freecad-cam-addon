# „Maschine verfahren“ wie im Programm (W-001, Stufe 3b, Schritt 4): Die
# Beispiel-Drehmaschine mit schräger Achse (Y-Führung 30° gekippt, Eintrag
# „Schräge Achse Y1 – gleicht aus: X1“). Das Fenster steht zuerst auf „wie im
# Programm“: Regler X und Y statt X1 und Y1. X1 steht gebaut auf 275 (X zählt ab der
# Spindelachse, P-2026-09-30-50). Y auf 10 fährt beide Schlitten (X1 269,23, Y1 11,55 –
# grau darunter). X auf 415, dann Y auf −40: Y hält bei −17,32, und eine rote Zeile
# sagt, dass X1 an seiner Grenze 425 mm steht.
# „der Maschine“ zeigt wieder je Schlitten einen Regler und grau, wo das
# Werkzeug im Programm steht. Abbrechen fährt alles zurück. Vorher in
# „Maschine bearbeiten“: Verweilen auf dem Eintrag fährt ein Y des Programms
# hin und her – beide Schlitten bewegen sich, danach steht alles wie vorher.
import FreeCAD
import FreeCADGui as Gui
from PySide import QtGui


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine, gui_maschine, gui_verfahren
    from camaddon import kette as kette_modul
    from camaddon import maschine as m
    from camaddon import schraege_achse as sa
    from camaddon import verfahren as vf

    asm, ma = beispielmaschine.lade(beispielmaschine.DREHMASCHINE)
    yield 800
    doc = asm.Document
    ba = {b.NcName: b for b in m.betriebsarten(ma)}
    trafo = m.neue_schraege_achse(ma, ba["Y1"], ba["X1"])
    sa.drehe_fuehrung(asm, kette_modul.lies_kette(asm), ma, trafo, 30)
    doc.recompute()
    teile = {o.Label: o for o in doc.Objects if o.TypeId in ("Part::Box", "App::Part")}
    lagen = {n: FreeCAD.Placement(o.Placement) for n, o in teile.items()}

    def bewegt():
        return sorted(n for n, o in teile.items() if not o.Placement.isSame(lagen[n], 1e-6))

    # --- „Maschine bearbeiten“: Verweilen auf dem Eintrag -------------------------------
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(asm)
    Gui.runCommand("CamAddon_MaschineBearbeiten")
    yield from h.warte_auf(lambda: gui_maschine.MaschinenPanel.offen is not None)
    panel = gui_maschine.MaschinenPanel.offen
    h.pruefe(panel is not None, "„Maschine bearbeiten“ geht nicht auf")
    if panel is not None:
        panel.zeige(("transformation", trafo))
        yield 250  # mitten in der Bewegung
        unterwegs = bewegt()
        h.pruefe(
            "XSchlitten" in unterwegs and "YSchlitten" in unterwegs,
            f"beim Verweilen bewegt: {unterwegs}",
        )
        yield 900  # die Bewegung ist vorbei
        h.pruefe(not bewegt(), f"nach dem Verweilen nicht zurück: {bewegt()}")
        panel.accept()
        yield 500

    # --- „Maschine verfahren“ wie im Programm --------------------------------------------
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(asm)
    Gui.runCommand("CamAddon_MaschineVerfahren")
    yield from h.warte_auf(lambda: gui_verfahren.VerfahrPanel.offen is not None)
    panel = gui_verfahren.VerfahrPanel.offen
    h.pruefe(panel is not None, "„Maschine verfahren“ geht nicht auf")
    if panel is None:
        return
    h.pruefe(panel.programm is not None, "keine schräge Achse erkannt")
    if panel.programm is None:
        return
    h.pruefe(panel.knopf_programm.isChecked(), "steht nicht zuerst auf „wie im Programm“")
    namen = sorted(vf.namen(panel.maschine, a) for a in panel.zeilen)
    h.pruefe(namen == ["C1", "T", "Werkzeugantrieb", "Z1"], f"Achsen der Maschine: {namen}")
    h.pruefe(sorted(panel.programmzeilen) == ["x", "y"], f"Programm: {list(panel.programmzeilen)}")
    beschriftungen = [w.text() for w in panel.raster.findChildren(QtGui.QLabel)]
    h.pruefe("X" in beschriftungen and "Y" in beschriftungen, f"Namen: {beschriftungen}")

    # Y auf 10: beide Schlitten fahren.
    _regler, feld_y = panel.programmzeilen["y"]
    feld_y.setValue(10)
    yield 400
    x1, y1 = panel.programm.schlitten()
    h.pruefe(abs(x1 - 275 + 5.773503) < 1e-4 and abs(y1 - 11.547005) < 1e-4, f"Y 10: {x1}, {y1}")
    h.pruefe(
        panel.info.text() == "Schlitten: X1 269,23 mm, Y1 11,55 mm", f"grau: {panel.info.text()!r}"
    )
    h.pruefe(not panel.anschlag.isVisible(), "rote Zeile ohne Anschlag")
    h.bild("1_programm_y10")

    # X auf 415, dann Y auf −40: X1 stößt bei 425 an, Y hält bei −17,32.
    _regler, feld_x = panel.programmzeilen["x"]
    feld_x.setValue(415)
    yield 300
    feld_y.setValue(-40)
    yield 400
    x, y = panel.programm.stellung()
    h.pruefe(abs(y + 17.320508) < 1e-3 and abs(x - 415) < 1e-3, f"gehalten bei {x}, {y}")
    h.pruefe(abs(feld_y.value() + 17.32) < 1e-6, f"Feld Y: {feld_y.value()}")
    h.pruefe(panel.anschlag.isVisible(), "keine rote Zeile am Anschlag")
    h.pruefe(
        panel.anschlag.text() == "Weiter geht Y hier nicht: X1 steht an seiner Grenze 425,00 mm.",
        f"rote Zeile: {panel.anschlag.text()!r}",
    )
    h.bild("2_anschlag_x1")

    # „der Maschine“: je Schlitten ein Regler, grau das Programm.
    panel.waehle_modus(False)
    yield 400
    namen = sorted(vf.namen(panel.maschine, a) for a in panel.zeilen)
    h.pruefe("X1" in namen and "Y1" in namen, f"der Maschine: {namen}")
    h.pruefe(not panel.programmzeilen, "Programmzeilen bleiben")
    h.pruefe(
        panel.info.text() == "Im Programm: X 415,00 mm, Y −17,32 mm", f"grau: {panel.info.text()!r}"
    )
    h.bild("3_der_maschine")
    # Y1 von Hand auf 0: das Programm-Y geht mit auf 0.
    y1_achse = panel.achse("Y1")
    panel.zeilen[y1_achse][1].setValue(0)
    yield 300
    h.pruefe(panel.info.text().endswith("Y 0,00 mm"), f"nach Y1 = 0: {panel.info.text()!r}")

    # Zurück zu „wie im Programm“ und Grundstellung.
    panel.waehle_modus(True)
    yield 300
    panel.grundstellung()
    yield 300
    x1, y1 = panel.programm.schlitten()
    h.pruefe(abs(x1 - 275) < 1e-6 and abs(y1) < 1e-6, f"Grundstellung: {x1}, {y1}")
    feld_y = panel.programmzeilen["y"][1]
    feld_y.setValue(20)
    yield 300
    panel.reject()
    yield 500
    h.pruefe(not bewegt(), f"Abbrechen fährt nicht zurück: {bewegt()}")
    for name in list(FreeCAD.listDocuments()):
        FreeCAD.closeDocument(name)
    yield 300
