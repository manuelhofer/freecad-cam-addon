# Die Flanke mit zu kurzem Werkzeug (legros im Forum, 2026-10-10: ein Kegel mit „Flanke“, der ER16
# steckte in den unteren Lagen im Kegel; Manuel, 2026-10-11: „es hilft nichts wenn der halter dann
# in den kegel reinballert“): ein Kegel Ø 50 → Ø 30, 30 hoch, auf einer Platte, die 5-Achs-Maschine
# Tisch/Tisch, ein Schaftfräser Ø 10 mit 12 mm Schneide in einem ER16 (er steht 32 mm heraus, die
# Wand ist 31,6 mm lang) und ein Kugelfräser Ø 6. Den Mantel anklicken → „Bearbeitung“: Die Flanke
# ist rot – Halter oder Schaft führen in die Wand, mindestens 41 mm bräuchte es, und T5 ist dafür zu
# kurz (Gesamtlänge 50) –, den Haken hat das 3D-Schlichten. Dann ist T5 in der Werkzeugverwaltung
# länger (80 mm, derselbe Überstand 32): Hinter dem roten Satz steht „T5 auf 42 mm ausspannen“; ein
# Klick setzt die Länge ab Spindelnase, der Assistent rechnet neu, und die Flanke hat ihre Bahn
# (P-2026-10-11-65). Seit „Schaft frei“ (0.313.0) kippt die Flanke in der unteren Lage etwas weiter
# von der Wand weg – der Halter braucht 1 mm weniger (vorher 42/43).
import os
import re
import tempfile

import FreeCAD
import FreeCADGui as Gui
import Part

V = FreeCAD.Vector


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import PARAMETER_PFAD, beispielmaschine, gui_bearbeitung
    from camaddon import flanke_bahn as fb
    from camaddon import halter as hl
    from camaddon import maschinenspeicher as msp
    from camaddon import reichweite as rw
    from camaddon import werkzeuge as wz

    ordner = tempfile.mkdtemp()
    asm, _maschine = beispielmaschine.lade(beispielmaschine.TISCH_TISCH)
    pfad_maschine = os.path.join(ordner, "fuenfachs.FCStd")
    asm.Document.saveAs(pfad_maschine)
    msp.merken_datei(pfad_maschine)
    FreeCAD.ParamGet(PARAMETER_PFAD).SetString(rw.ZULETZT_MASCHINE, pfad_maschine)
    yield 300
    er16 = hl.aus_vorlage("er16")
    t5 = wz.Werkzeug(
        nummer=5,
        name="VHM 10 kurz",
        art=wz.SCHAFTFRAESER,
        durchmesser=10.0,
        schneiden=4,
        schneidenlaenge=12.0,
        gesamtlaenge=50.0,
        schneidstoff=wz.VHM,
    )
    t5.ausspannlaenge = 32.0  # wie vorher: 32 mm heraus
    t5.halter = er16.kennung
    t5.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=10.0, vc=150.0, fz=0.04)]
    t3 = wz.Werkzeug(
        nummer=3,
        name="Kugel 6",
        art=wz.KUGELFRAESER,
        durchmesser=6.0,
        schneiden=2,
        schneidenlaenge=12.0,
        gesamtlaenge=60.0,
        schneidstoff=wz.VHM,
    )
    t3.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=0.3, vc=150.0, fz=0.05)]
    bibliothek = wz.Bibliothek([t5, t3])
    bibliothek.halter = [er16]
    bibliothek.speichern()

    doc = FreeCAD.newDocument("Kegel")
    doc.UndoMode = 1
    teil = doc.addObject("Part::Feature", "Kegel")
    teil.Shape = (
        Part.makeBox(80, 80, 10).fuse(Part.makeCone(25, 15, 30, V(40, 40, 10))).removeSplitter()
    )
    doc.recompute()
    FreeCAD.setActiveDocument(doc.Name)
    mantel = [
        f"Face{i + 1}"
        for i in range(len(teil.Shape.Faces))
        if fb.ist_wand(teil.Shape, f"Face{i + 1}")
    ]
    h.pruefe(len(mantel) == 1, f"Wände: {mantel}")
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.addSelection(doc.Name, teil.Name, mantel[0])
    yield 500

    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2500
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    flanke, s3 = panel.flanke, panel.schlichten3d
    yield from h.warte_auf(
        lambda: not panel.vorschau_laeuft()
        and all(b.vorschau is not None or b.hinweis.text() or not b.aktiv() for b in panel.bloecke),
        300000,
    )
    yield 1500
    rot = flanke.hinweis.text()
    h.pruefe(
        "in die Wand" in rot and "32 mm heraus" in rot and "mindestens" in rot,
        f"Flanke: {rot!r}",
    )
    h.pruefe("T5 ist dafür zu kurz (Gesamtlänge 50 mm)" in rot, f"zu kurz? {rot!r}")
    h.pruefe(flanke.vorschau is None, "die Flanke hat trotzdem eine Bahn")
    h.pruefe(not flanke.aktiv() and s3.aktiv(), f"Haken: Flanke {flanke.aktiv()}, 3D {s3.aktiv()}")
    panel.seite_zeigen(1)
    yield 500
    h.bild("1_flanke_halter", panel.form)

    # T5 länger, derselbe Überstand (Länge ab Spindelnase gesetzt): jetzt mit dem Verweis.
    laenge, _quelle = rw.laenge_des_werkzeugs(t5, bibliothek)
    t5.gesamtlaenge, t5.laenge_spindelnase = 80.0, laenge
    bibliothek.speichern()
    panel._werkzeuge_gespeichert()
    yield 500
    flanke = panel.flanke
    yield from h.warte_auf(
        lambda: not panel.vorschau_laeuft() and "ausspannen" in flanke.hinweis.text(), 300000
    )
    rot = flanke.hinweis.text()
    verweis = re.search(r'href="(ausspannen:[^"]+)"', rot)
    h.pruefe(verweis is not None and "T5 auf 42 mm ausspannen" in rot, f"Verweis: {rot!r}")
    yield 300
    h.bild("2_ausspannen_angeboten", panel.form)
    if verweis is None:
        return
    flanke.hinweis.linkActivated.emit(verweis.group(1))
    yield 500
    gespeichert = next(w for w in wz.Bibliothek.laden().werkzeuge if w.nummer == 5)
    h.pruefe(
        # die Länge ab Spindelnase, die der Verweis setzt („ausspannen:5:112.000:42“)
        abs(gespeichert.laenge_spindelnase - float(verweis.group(1).split(":")[2])) < 1e-3,
        f"Länge ab Spindelnase {gespeichert.laenge_spindelnase} (vorher {laenge})",
    )
    flanke = panel.flanke
    yield from h.warte_auf(
        lambda: not panel.vorschau_laeuft() and flanke.vorschau is not None, 300000
    )
    h.pruefe(
        flanke.vorschau is not None and not flanke.hinweis.text(),
        f"nach dem Ausspannen: {flanke.hinweis.text()!r}",
    )
    yield 500
    h.bild("3_ausgespannt", panel.form)
    panel.reject()
    yield 800
    FreeCAD.closeDocument(doc.Name)
    yield 300
