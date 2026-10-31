# „Ganze Tasche schruppen, diese Wände schlichten“ (Beta, Plan C1; Manuel, 2026-10-31: „wenn wir
# vorher keinerlei bearbeitung haben .. muss halt erstmal etwas rausgeschruppt werden … vll will er
# wirklich nur die wände geschlichtet haben ... das muss irgendwie unterschieden werden“). Der Block
# mit der Tasche aus szenario_beta_schritte, eine Wand angeklickt, noch keine Operation: Der Satz
# sagt, dass Material in der Tasche steht; der Knopf nimmt die ganze Tasche – die Strategien des
# Schruppens bekommen alle ihre Flächen, die des Schlichtens nur die angeklickte Wand; „Weiter“
# geht. Eine andere Fläche dazu hebt die Teilung auf.
# Dann bis zum letzten Schritt: „Anlegen und Teil umspannen …“ (Plan C4) legt an und öffnet das
# Teil in einer neuen Aufspannung (ein zweiter Job); unten die Oberseite, in Schritt 2 vorgewählt,
# was in der ersten Aufspannung nicht ging und jetzt von oben geht – die alte Unterseite (die
# Rundungen am Taschenboden gehen seit 0.329.1 schon in der ersten Aufspannung von oben).
# ZEITLIMIT: 600
import os
import tempfile

import FreeCAD
import FreeCADGui as Gui
import Part


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

    panel.wie_modelliert()
    yield 300
    panel.knopf_weiter.click()
    yield 1500
    h.pruefe("noch Material" in panel.tasche_text.text(), f"Satz: {panel.tasche_text.text()!r}")
    panel.knopf_tasche_schruppen.click()
    yield 2000
    h.pruefe(len(panel.gewaehlte) == 9, f"ganze Tasche: {panel.gewaehlte}")
    form = panel.job.Model.Group[0].Shape
    schruppen = [b for b in panel.bloecke if beta.abschnitt(b) == beta.SCHRUPPEN and b.moeglich]
    schlichten = [b for b in panel.bloecke if beta.abschnitt(b) == beta.SCHLICHTEN]
    h.pruefe(schruppen, "keine Strategie zum Schruppen")
    for b in schruppen:
        h.pruefe(len(panel._wahl(b)) == 9, f"{b.s.kennung}: {panel._wahl(b)}")
    for b in schlichten:
        h.pruefe(panel._wahl(b) == [wand], f"{b.s.kennung}: {panel._wahl(b)}")
    print(ascii(f"Satz: {panel.tasche_text.text()} | {len(form.Faces)}"))
    h.pruefe(panel.knopf_weiter.isEnabled(), "„Weiter“ gesperrt nach der Wahl")
    h.bild("1_geteilt", panel.form)
    oben = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if abs(f.BoundBox.ZMin - 40) < 1e-6 and abs(f.BoundBox.ZMax - 40) < 1e-6
    )
    panel.flaeche_umschalten(oben)
    yield 1500
    h.pruefe(panel._beta_schlichten is None, "Teilung bleibt nach einer anderen Wahl")
    panel.flaeche_umschalten(oben)
    yield 1500

    # Umspannen
    for _ in range(6):
        if not panel.knopf_weiter.isVisible():
            break
        panel.knopf_weiter.click()
        yield 1500
    h.pruefe(panel.knopf_umspannen.isVisible(), "im letzten Schritt kein „Teil umspannen …“")
    h.bild("2_letzter_schritt", panel.form)
    jobs_vorher = [o for o in doc.Objects if o.TypeId == "Path::FeaturePython" and "Job" in o.Name]
    panel.knopf_umspannen.click()
    yield from h.warte_auf(
        lambda: beta.BearbeitungPanel.offen is not None
        and beta.BearbeitungPanel.offen is not panel,
        120000,
    )
    yield 2000
    neu = beta.BearbeitungPanel.offen
    h.pruefe(isinstance(neu, beta.BetaPanel) and neu is not panel, f"kein neues Fenster: {neu!r}")
    if not isinstance(neu, beta.BetaPanel) or neu is panel:
        return
    vorwahl = list(getattr(neu, "_beta_vorwahl", None) or [])
    unten = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if abs(f.BoundBox.ZMin) < 1e-6 and abs(f.BoundBox.ZMax) < 1e-6
    )
    print(ascii(f"Vorwahl: {vorwahl} | Jobs vorher {len(jobs_vorher)}"))
    h.pruefe(unten in vorwahl and oben not in vorwahl and wand not in vorwahl, f"{vorwahl}")
    neu.unten_waehlen(oben)
    yield 1500
    neu.knopf_weiter.click()
    yield 2000
    h.pruefe(neu.seite() == 1, f"Seite {neu.seite()}")
    h.pruefe(unten in neu.gewaehlte and oben not in neu.gewaehlte, f"vorgewählt: {neu.gewaehlte}")
    h.bild("3_umgespannt", neu.form)
    neu.reject()
