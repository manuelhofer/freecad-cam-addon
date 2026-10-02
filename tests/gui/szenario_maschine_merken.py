# Die Maschine merken (Durchsicht W-004, D-20): Die Beispiel-Fräse, als Datei
# gespeichert, und ein Teil mit Job. Prüfen und schließen: Der Job merkt sich
# die Datei der Maschine (verborgen), das Addon auch als „zuletzt benutzt“.
# Maschine zu, wieder prüfen: Sie öffnet sich selbst, das Fenster kommt ohne
# Frage – über den Job und, hat der nichts gemerkt, über „zuletzt benutzt“.
# Nichts gemerkt: Die Meldung hat „Maschine öffnen …“ und „Neue Maschine …“.
# „Neue Maschine …“ baut die gewählte Bauart und prüft gleich auf ihr; eine
# ungespeicherte merkt sich nichts. „Maschine öffnen …“ mit einer Datei ohne
# Maschine sagt das; mit der Datei der Maschine prüft es auf ihr. Sind zwei
# Maschinen offen und hat der Job seine, gilt sie ohne Frage (W-011 S2); hat er
# keine, fragt das Addon – die zuletzt benutzte steht vorn.
import os
import shutil
import tempfile

import FreeCAD
import FreeCADGui as Gui
from PySide import QtCore, QtGui

BAHN = ["G0 X0 Y0 Z10", "G1 Z-5 F100", "G1 X50 Y20", "G0 Z10"]
OEFFNEN = "Maschine öffnen …"
NEU = "Neue Maschine …"


def knopf(meldung, text):
    if not isinstance(meldung, QtGui.QMessageBox):
        return None
    return next((k for k in meldung.buttons() if k.text() == text), None)


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

    from camaddon import PARAMETER_PFAD, beispielmaschine, gui_neue_maschine, gui_reichweite
    from camaddon import reichweite as rw

    einstellungen = FreeCAD.ParamGet(PARAMETER_PFAD)
    ordner = tempfile.mkdtemp()
    asm, _maschine = beispielmaschine.lade(beispielmaschine.FRAESE_3)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    asm.Document.saveAs(os.path.join(ordner, "Fraese.FCStd"))
    datei = asm.Document.FileName  # so, wie FreeCAD den Pfad schreibt
    yield 300

    teil = FreeCAD.newDocument("Teil")
    quader = teil.addObject("Part::Box", "Quader")
    quader.Length, quader.Width, quader.Height = 100, 60, 20
    teil.recompute()
    job = PathJob.Create("Job", [quader])
    op = PathCustom.Create("Eigene")
    op.Gcode = BAHN
    teil.recompute()
    teil.saveAs(os.path.join(ordner, "Teil.FCStd"))
    yield 500

    def gemerkt_am_job():
        return getattr(job, rw.EIGENSCHAFT_MASCHINE, None)

    def pruefen():
        """Wie ein Benutzer: den Job wählen, den Knopf drücken. Wartet, bis das Fenster
        oder eine Meldung da ist."""
        FreeCAD.setActiveDocument(teil.Name)
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(job)
        yield 400
        QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
        yield from h.warte_auf(
            lambda: gui_reichweite.PruefPanel.offen is not None or h.modal() is not None, 15000
        )
        yield 300

    def schliessen():
        panel = gui_reichweite.PruefPanel.offen
        if panel is not None:
            panel.reject()
        yield 800

    def maschinen_zu():
        for name, dokument in list(FreeCAD.listDocuments().items()):
            if dokument is not teil:
                FreeCAD.closeDocument(name)
        yield 500

    def ohne_frage(was):
        """Das Fenster ist da, ohne Meldung davor – auf der Maschine aus `datei`."""
        meldung = h.modal()
        h.pruefe(meldung is None, f"{was}: Meldung statt Fenster: {meldung and meldung.text()!r}")
        if meldung is not None:
            meldung.reject()
        panel = gui_reichweite.PruefPanel.offen
        h.pruefe(
            panel is not None and panel.assembly.Document.FileName == datei,
            f"{was}: nicht auf der gemerkten Maschine",
        )

    # --- Prüfen und schließen: gemerkt ----------------------------------------------------
    yield from pruefen()
    h.pruefe(gui_reichweite.PruefPanel.offen is not None, "kein Fenster mit offener Maschine")
    yield from schliessen()
    h.pruefe(gemerkt_am_job() == datei, f"am Job: {gemerkt_am_job()!r}")
    modus = job.getEditorMode(rw.EIGENSCHAFT_MASCHINE) if gemerkt_am_job() else []
    h.pruefe("Hidden" in modus, f"Eigenschaft sichtbar: {modus}")
    zuletzt = einstellungen.GetString(rw.ZULETZT_MASCHINE, "")
    h.pruefe(zuletzt == datei, f"zuletzt benutzt: {zuletzt!r}")

    # --- Maschine zu, wieder prüfen: Sie öffnet sich selbst – über den Job ------------------
    einstellungen.RemString(rw.ZULETZT_MASCHINE)
    yield from maschinen_zu()
    yield from pruefen()
    ohne_frage("über den Job")
    Gui.SendMsgToActiveView("ViewFit")
    yield 300
    h.bild("1_selbst_geoeffnet")
    yield from schliessen()

    # --- … und über „zuletzt benutzt“, wenn der Job nichts gemerkt hat ----------------------
    job.removeProperty(rw.EIGENSCHAFT_MASCHINE)
    yield from maschinen_zu()
    yield from pruefen()
    ohne_frage("über „zuletzt benutzt“")
    yield from schliessen()
    h.pruefe(gemerkt_am_job() == datei, f"nicht wieder am Job: {gemerkt_am_job()!r}")

    # --- Nichts gemerkt: die Meldung; „Neue Maschine …“ baut und prüft gleich ---------------
    job.removeProperty(rw.EIGENSCHAFT_MASCHINE)
    einstellungen.RemString(rw.ZULETZT_MASCHINE)
    yield from maschinen_zu()
    yield from pruefen()
    meldung = h.modal()
    h.pruefe(isinstance(meldung, QtGui.QMessageBox), f"keine Meldung: {meldung}")
    if not isinstance(meldung, QtGui.QMessageBox):
        return
    h.pruefe(meldung.text().startswith("Es ist keine Maschine offen."), f"{meldung.text()!r}")
    neu = knopf(meldung, NEU)
    h.pruefe(knopf(meldung, OEFFNEN) is not None and neu is not None, "Knöpfe fehlen")
    h.bild("2_meldung_ohne_maschine", meldung)
    if neu is None:
        return
    neu.click()
    yield from h.warte_auf(lambda: gui_neue_maschine.NeueMaschineDialog.offen is not None)
    auswahl = gui_neue_maschine.NeueMaschineDialog.offen
    h.pruefe(auswahl is not None, "„Neue Maschine …“ öffnet keine Auswahl")
    if auswahl is None:
        return
    auswahl.liste.setCurrentRow(beispielmaschine.ARTEN.index(beispielmaschine.FRAESE_3))
    auswahl.knoepfe.button(QtGui.QDialogButtonBox.Ok).click()
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None, 15000)
    panel = gui_reichweite.PruefPanel.offen
    h.pruefe(
        panel is not None and not panel.assembly.Document.FileName,
        "nach „Neue Maschine …“ kein Prüffenster auf der neuen Maschine",
    )
    yield from schliessen()
    h.pruefe(gemerkt_am_job() is None, f"ungespeicherte gemerkt: {gemerkt_am_job()!r}")

    # --- „Maschine öffnen …“: erst eine Datei ohne Maschine, dann die richtige --------------
    yield from maschinen_zu()
    gefragt = []

    def waehle(antwort):
        def waehlen(_fenster, start):
            gefragt.append(start)
            return antwort

        return waehlen

    ohne_maschine = teil.FileName
    gui_reichweite.datei_waehlen = waehle(ohne_maschine)
    yield from pruefen()
    meldung = h.modal()
    oeffnen = knopf(meldung, OEFFNEN)
    h.pruefe(oeffnen is not None, f"Knopf „{OEFFNEN}“ fehlt")
    if oeffnen is None:
        return
    oeffnen.click()
    yield from h.warte_auf(
        lambda: isinstance(h.modal(), QtGui.QMessageBox) and h.modal() is not meldung, 5000
    )
    hinweis = h.modal()
    text = hinweis.text() if isinstance(hinweis, QtGui.QMessageBox) else ""
    h.pruefe(
        text == f"In {ohne_maschine} ist keine Maschine eingerichtet. Eine Baugruppe wird zur "
        "Maschine mit „Maschine bearbeiten“.",
        f"Hinweis: {text!r}",
    )
    h.pruefe(gefragt == [os.path.dirname(ohne_maschine)], f"Ordner der Frage: {gefragt}")
    if isinstance(hinweis, QtGui.QMessageBox):
        hinweis.accept()
    yield 500
    h.pruefe(gui_reichweite.PruefPanel.offen is None, "Fenster trotz Datei ohne Maschine")

    gui_reichweite.datei_waehlen = waehle(datei)
    yield from pruefen()
    oeffnen = knopf(h.modal(), OEFFNEN)
    h.pruefe(oeffnen is not None, f"Knopf „{OEFFNEN}“ fehlt beim zweiten Mal")
    if oeffnen is not None:
        oeffnen.click()
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None, 15000)
    ohne_frage("nach „Maschine öffnen …“")
    yield from schliessen()
    h.pruefe(gemerkt_am_job() == datei, f"nach „Maschine öffnen …“: {gemerkt_am_job()!r}")

    # --- Zwei Maschinen offen, der Job hat seine: ohne Frage auf ihr (W-011 S2) ----------------
    zweite, _m2 = beispielmaschine.lade(beispielmaschine.FRAESE_3)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is zweite.Document)
    yield from pruefen()
    ohne_frage("bei zwei Maschinen, der Job hat seine")
    yield from schliessen()

    # --- … hat er keine: Das Addon fragt, die zuletzt benutzte vorn ----------------------------
    job.removeProperty(rw.EIGENSCHAFT_MASCHINE)
    yield from pruefen()
    frage = h.modal()
    h.pruefe(isinstance(frage, QtGui.QInputDialog), f"keine Frage bei zwei Maschinen: {frage}")
    if isinstance(frage, QtGui.QInputDialog):
        gespeichert = next(d for d in FreeCAD.listDocuments().values() if d.FileName == datei)
        eintraege = frage.comboBoxItems()
        h.pruefe(
            len(eintraege) == 2 and eintraege[0].endswith(f"({gespeichert.Label})"),
            f"gemerkte nicht vorn: {eintraege}",
        )
        h.pruefe(frage.textValue() == eintraege[0], f"vorgewählt: {frage.textValue()!r}")
        h.bild("3_frage_gemerkte_vorn", frage)
        frage.accept()
        yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None)
        ohne_frage("bei zwei Maschinen")
    yield from schliessen()

    for name in list(FreeCAD.listDocuments()):
        FreeCAD.closeDocument(name)
    shutil.rmtree(ordner, ignore_errors=True)
    yield 300
