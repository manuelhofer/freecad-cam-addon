# Home- und Werkzeugwechselpunkt im Prüffenster (W-008, P-2026-10-02-48; Manuel, 2026-10-02:
# „Beim Starten steht der Fräser immer XYZ 0 … Daher muss es einen Home-Punkt geben … und
# vielleicht einen Werkzeugwechselpunkt … damit auch die Simulation korrekt ablaufen kann“):
# die Beispiel-Fräse mit Home-Punkt X1 −150, Y1 0, Z1 0 (oben) und Wechselpunkt X1 150; ein
# Teil mit zwei Operationen, T1 und T2. Der Abspieler steht am Anfang am Home-Punkt:
# „„Kontur“ · Home-Punkt · 0:00,0 von …“, X1 auf −150. Vor der zweiten Operation fährt die
# Maschine zum Wechselpunkt (X1 150), am Ende steht sie wieder am Home-Punkt.
import FreeCAD
import FreeCADGui as Gui
from PySide import QtCore

KONTUR = ["G0 X0 Y0 Z25", "G1 Z18 F5", "G1 X100 F20", "G0 Z25"]
BOHREN = ["G0 X50 Y30 Z25", "G81 X50 Y30 Z10 R21 F2", "G80", "G0 Z25"]
HOME = {"X1": -150.0, "Y1": 0.0, "Z1": 0.0}


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
    from Path.Tool import Controller

    from camaddon import abfahren as ab
    from camaddon import beispielmaschine, gui_reichweite
    from camaddon import maschine as m
    from camaddon import verfahren as vf

    asm, maschine = beispielmaschine.lade(beispielmaschine.FRAESE_3)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    yield 500
    for ba in m.betriebsarten(maschine):
        if ba.Art == m.ART_LINEAR and ba.NcName in HOME:
            ba.Home, ba.HomeAn = HOME[ba.NcName], True
            if ba.NcName == "X1":
                ba.Wechsel, ba.WechselAn = 150.0, True

    teil = FreeCAD.newDocument("Teil")
    quader = teil.addObject("Part::Box", "Quader")
    quader.Length, quader.Width, quader.Height = 100, 60, 20
    teil.recompute()
    job = PathJob.Create("Job", [quader])
    kontur = PathCustom.Create("Kontur")
    kontur.Gcode = KONTUR
    bohren = PathCustom.Create("Bohren")
    bohren.Gcode = BOHREN
    tc2 = Controller.Create("TC2", toolNumber=2)
    job.Proxy.addToolController(tc2)
    bohren.ToolController = tc2
    teil.recompute()
    yield 500

    FreeCAD.setActiveDocument(teil.Name)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None)
    panel = gui_reichweite.PruefPanel.offen
    h.pruefe(panel is not None, "„Auf der Maschine prüfen“ öffnet kein Fenster")
    if panel is None:
        return
    yield 800
    spieler = panel.abspieler
    abfahrt = spieler.abfahrt
    h.pruefe(abfahrt is not None and abfahrt.stationen, "keine Abfahrt")
    if abfahrt is None or not abfahrt.stationen:
        return
    ziele = [s.ziel for s in abfahrt.stationen]
    print(ascii(f"Ziele: {ziele}"))
    h.pruefe(ziele[0] == ab.HOME and ziele[-1] == ab.HOME, f"Anfang/Ende: {ziele[:3]} {ziele[-3:]}")
    h.pruefe(ab.WECHSEL in ziele, "kein Werkzeugwechsel")

    def achsen():
        return {
            vf.namen(panel.maschine, a): round(w, 6)
            for a, w in spieler.werte.items()
            if vf.namen(panel.maschine, a) in HOME
        }

    spieler.anfang()
    yield 300
    h.pruefe(
        spieler.stelle.text().startswith("„Kontur“ · Home-Punkt · 0:00,0 von "),
        f"Stelle am Anfang: {spieler.stelle.text()!r}",
    )
    h.pruefe(achsen() == HOME, f"am Anfang: {achsen()}")
    Gui.SendMsgToActiveView("ViewFit")
    yield 300
    h.bild("1_home")
    h.bild("1b_fenster", panel.form)

    wechsel = max(
        i for i, z in enumerate(ziele) if z == ab.WECHSEL and abfahrt.stationen[i].operation == 0
    )
    spieler.springe_zu_station(wechsel)
    yield 300
    h.pruefe(
        spieler.stelle.text().startswith("„Kontur“ · zum Werkzeugwechsel · "),
        f"Stelle am Wechselpunkt: {spieler.stelle.text()!r}",
    )
    h.pruefe(achsen().get("X1") == 150.0, f"am Wechselpunkt: {achsen()}")
    h.bild("2_wechsel")

    spieler.springe_zu_station(len(abfahrt.stationen) - 1)
    yield 300
    h.pruefe(
        spieler.stelle.text().startswith("„Bohren“ · Home-Punkt · "),
        f"Stelle am Ende: {spieler.stelle.text()!r}",
    )
    h.pruefe(achsen() == HOME, f"am Ende: {achsen()}")
    panel.reject()
    yield 800
    for name in list(FreeCAD.listDocuments()):
        FreeCAD.closeDocument(name)
    yield 300
