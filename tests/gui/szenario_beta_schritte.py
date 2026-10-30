# „Bearbeitung in Schritten“ (Beta; Manuel, 2026-10-30: „die Einzelschritte besser abfragen, und
# zwar einzeln … immer nur dann weiter, wenn auch wirklich alles ausgewählt ist“ – „einen
# Beta-Knopf …, dass wir erstmal das Alte behalten“). Ein Block 100 × 80 × 40 mit einer Tasche
# 60 × 40, 15 tief, Boden gerundet (R 3). Die Beta ist eingeschaltet, eine Wand der Tasche
# angeklickt, „Bearbeitung in Schritten (Beta)“:
# 1. Aufspannung: „Weiter“ gesperrt, bis „Liegt wie im Modell“ geklickt ist.
# 2. Flächen: die eine Wand gehört zu einer Tasche – der Satz dazu, „Weiter“ gesperrt; „Ganze
#    Tasche nehmen“ nimmt Wände, Rundungen und Boden dazu, „Weiter“ geht.
# 3. Schruppen: nur Strategien des Schruppens zu sehen. „Weiter“ zum Schlichten (Löcher gibt es
#    hier nicht – übersprungen), „Zurück“, dann „Anlegen“ im Schruppen: nur das Schruppen kommt in
#    den Job, am Job steht, was gewählt war und bis wohin angelegt ist.
# 4. Job anklicken, „Weiter bearbeiten (Beta)“: das Fenster beginnt beim Schlichten, die Flächen
#    dieselben; „Anlegen“ – das Schlichten kommt dazu.
# ZEITLIMIT: 900
import os
import tempfile

import FreeCAD
import FreeCADGui as Gui
import Part

SCHRUPPEN_MODULE = ("raeumen", "planfraesen", "nut", "kontur", "schruppen3d")


def _art(op):
    return type(getattr(op, "Proxy", None)).__module__.split(".")[-1]


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
    leisten = Gui.getWorkbench("CAMWorkbench").listToolbars()
    h.pruefe(beta.WERKZEUGLEISTE_NAME in leisten, f"keine Beta-Leiste: {leisten}")
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
    h.pruefe(not panel.knopf_weiter.isEnabled(), "„Weiter“ geht, bevor klar ist, was unten liegt")
    h.pruefe(
        panel.knopf_unten_waehlen.isChecked(), "der Klick auf die untere Fläche ist nicht bereit"
    )
    h.bild("1_aufspannung", panel.form)
    panel.wie_modelliert()
    yield 300
    h.pruefe(panel.knopf_weiter.isEnabled(), "„Weiter“ nach „Liegt wie im Modell“ gesperrt")
    panel.knopf_weiter.click()
    yield 800

    # 2. Flächen
    h.pruefe(panel.seite() == 1, f"Seite {panel.seite()}")
    h.pruefe(panel.gewaehlte == [wand], f"gewählt: {panel.gewaehlte}")
    h.pruefe(panel.tasche_box.isVisible(), "kein Satz zur Tasche")
    h.pruefe(not panel.knopf_weiter.isEnabled(), "„Weiter“ geht ohne Antwort zur Tasche")
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
    h.pruefe(panel.knopf_fertig.isVisible(), "kein „Anlegen“ im Schruppen")
    satz = panel.anlegen_text.text()
    print("BETA anlegen_text", repr(satz), flush=True)
    h.pruefe(
        "Räumen (T1" in satz and "zusammen" in satz and "später: 3D-Schlichten" in satz,
        f"was „Anlegen“ anlegt: {satz!r}",
    )
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
    h.bild("3_schruppen", panel.form)
    panel.knopf_weiter.click()
    yield 1000
    h.pruefe(panel.seite() == 2 + beta.SCHLICHTEN, f"nach dem Schruppen Seite {panel.seite()}")
    h.bild("4_schlichten", panel.form)
    panel.knopf_zurueck.click()
    yield 500
    h.pruefe(panel.seite() == 2, f"„Zurück“ auf Seite {panel.seite()}")
    vorher = len(panel.job.Operations.Group)
    panel.accept()
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
    Gui.runCommand("CamAddon_WeiterBearbeitenBeta")
    yield from h.warte_auf(lambda: beta.BearbeitungPanel.offen is not panel, 60000)
    weiter = beta.BearbeitungPanel.offen
    yield from h.warte_auf(lambda: weiter is not None and not weiter.vorschau_laeuft(), 300000)
    yield 1000
    if weiter is None:
        h.pruefe(False, "„Weiter bearbeiten“ öffnet kein Fenster")
        return
    h.pruefe(weiter.job is job, "„Weiter bearbeiten“ in einem anderen Job")
    h.pruefe(weiter.seite() > 2, f"„Weiter bearbeiten“ beginnt auf Seite {weiter.seite()}")
    h.pruefe(sorted(weiter.gewaehlte) == sorted(flaechen), f"Flächen: {weiter.gewaehlte}")
    h.pruefe(
        not weiter.knopf_zurueck.isVisible() or weiter.seite() > 2 + beta.SCHLICHTEN,
        "„Zurück“ ins Schruppen",
    )
    print("BETA weiter angehakt", [b.s.kennung for b in weiter.aktive_bloecke()], flush=True)
    h.bild("5_weiter_bearbeiten", weiter.form)
    vorher = len(job.Operations.Group)
    weiter.accept()
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
    h.bild("6_job", None)
    with __import__("contextlib").suppress(Exception):
        Gui.Control.closeDialog()
    yield 500
