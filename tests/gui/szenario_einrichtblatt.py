# „Einrichtblatt …“ (W-019; Manuel, 2026-10-12: „eine einrichtblatt zum drucken/als pdf“; „für
# JEDE bearbeitung“): Manuels C-Ring mit seinen zwei Jobs (aus Platte und aus Rundmaterial, W-034),
# im Menü „CAM-Addon“ steht „Einrichtblatt …“. Der Job aus Platte angeklickt (ohne Auswahl fragt es,
# welcher). Das Fenster zeigt die Werkzeuge (T1 und T3 Ø 6 aus der Werkzeugverwaltung im
# Schrumpffutter: Ausspannlänge 25, ein Bild von Halter und Fräser), die Aufspannung mit Rohteil,
# Spannmittel und Nullpunkt, ein Bild des Teils und die Schritte „Räumen T1“, „Nut T3“ (D-Bögen von
# der offenen Seite) und „Wände schlichten T1“ mit Zeit.
# „Als PDF speichern“ schreibt eine PDF-Datei, „Als HTML speichern“ eine
# Seite mit denselben Schritten.
import os
import shutil
import tempfile
import time

import FreeCAD
import FreeCADGui as Gui
from PySide import QtGui

ADDON = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500
    from camaddon import gui_einrichtblatt
    from camaddon import halter as hl
    from camaddon import werkzeuge as wz

    # T3 Ø 6 (wie im Job des C-Rings) im Schrumpffutter, 25 mm Ausspannlänge eingetragen.
    kiste = wz.testkiste()
    t3 = next(w for w in kiste if w.nummer == 3)
    futter = hl.aus_vorlage("schrumpf_6")
    futter.kennung = "halter-schrumpf-6-blatt"
    bibliothek = wz.Bibliothek(kiste)
    bibliothek.halter.append(futter)
    t3.halter = futter.kennung
    t3.laenge_spindelnase = float(futter.laenge) + 25.0
    bibliothek.speichern()

    ordner = tempfile.mkdtemp()
    datei = os.path.join(ordner, "cring.FCStd")
    shutil.copy(os.path.join(ADDON, "beispiele", "c_ring_nut_3achs.FCStd"), datei)
    doc = FreeCAD.openDocument(datei)
    yield 1000
    Gui.activateWorkbench("CAMWorkbench")
    Gui.Selection.clearSelection()
    platte = next(
        o
        for o in doc.Objects
        if hasattr(o, "Operations") and o.Label.startswith("C-Ring aus Platte")
    )
    Gui.Selection.addSelection(doc.Name, platte.Name)
    yield 500
    menue = next(
        (
            m
            for m in Gui.getMainWindow().menuBar().findChildren(QtGui.QMenu)
            if m.title() == "CAM-Addon"
        ),
        None,
    )
    texte = [a.text() for a in menue.actions()] if menue is not None else []
    h.pruefe("Einrichtblatt …" in texte, f"Menü: {texte}")
    Gui.runCommand("CamAddon_Einrichtblatt")
    yield from h.warte_auf(lambda: gui_einrichtblatt.EinrichtblattDialog.offen is not None, 30000)
    yield 1000
    dialog = gui_einrichtblatt.EinrichtblattDialog.offen
    if dialog is not None:  # die Bilder der Aufspannungen kommen nach und nach
        yield from h.warte_auf(lambda: dialog.bilder_fertig, 60000)
    h.pruefe(dialog is not None, "kein Fenster")
    if dialog is None:
        return
    text = dialog.vorschau.toPlainText()
    for soll in ("Werkzeuge", "T1", "T3", "Aufspannung 1", "Rohteil", "Spannmittel", "Nullpunkt",
                 "Räumen T1", "Nut T3", "Wände schlichten T1", "min"):  # fmt: skip
        h.pruefe(soll in text, f"„{soll}“ fehlt: {text[:400]!r}")
    w1 = next((w for w in dialog.blatt.werkzeuge if w.nummer == 3), None)
    # T1 (Schruppen und Schlichten: zwei Controller) und T3 – auf dem Blatt je eine Zeile.
    h.pruefe(
        sorted(w.nummer for w in dialog.blatt.werkzeuge) == [1, 3],
        f"Werkzeuge: {dialog.blatt.werkzeuge}",
    )
    h.pruefe(
        w1 is not None
        and w1.nummer == 3
        and abs(w1.ausspannlaenge - 25.0) < 1e-6
        and "Schrumpf" in w1.halter,
        f"T3: {w1}",
    )
    h.pruefe(w1 is not None and os.path.exists(w1.bild), f"kein Bild von T3: {w1 and w1.bild!r}")
    a = dialog.blatt.aufspannungen[0]
    h.pruefe(bool(a.bild) and os.path.exists(a.bild), f"kein Bild: {a.bild!r}")
    h.pruefe("," in a.rohteil, f"Dezimalkomma im Rohteil: {a.rohteil!r}")
    # Werte für die Maschine (Manuel, 2026-10-18): vc und fz am Schritt; im Bild das
    # Koordinatensystem am Nullpunkt, die Pfeile sind danach wieder aus dem Dokument.
    for soll in ("vc ", "fz "):
        h.pruefe(soll in text, f"„{soll}“ fehlt: {text[:600]!r}")
    h.pruefe(a.bild_achsen, "Bild der Aufspannung ohne Koordinatensystem")
    reste = [o.Name for o in doc.Objects if o.Name.startswith("Einrichtblatt")]
    h.pruefe(not reste, f"Hilfskörper geblieben: {reste}")
    if os.environ.get("AUSGABE"):
        shutil.copy(a.bild, os.path.join(os.environ["AUSGABE"], "aufspannung_cring.png"))
    h.bild("1_einrichtblatt", dialog)
    pdf = dialog.als_pdf(os.path.join(ordner, "blatt.pdf"))
    yield 500
    groesse = os.path.getsize(pdf) if pdf and os.path.exists(pdf) else 0
    h.pruefe(groesse > 5000, f"PDF: {groesse} Bytes")
    with open(pdf, "rb") as f:
        h.pruefe(f.read(5) == b"%PDF-", "keine PDF-Datei")
    seite = dialog.als_html(os.path.join(ordner, "blatt.html"))
    with open(seite, encoding="utf-8") as f:
        h.pruefe("Nut T3" in f.read(), "HTML ohne Schritt")
    if os.environ.get("AUSGABE"):
        shutil.copy(pdf, os.path.join(os.environ["AUSGABE"], "einrichtblatt.pdf"))
    dialog.reject()
    yield 500
    h.pruefe(gui_einrichtblatt.EinrichtblattDialog.offen is None, "Fenster nicht zu")
    FreeCAD.closeDocument(doc.Name)

    # Eine 6-Kant-Stange (W-018) mit ihren sechs Aufspannungen: Das Fenster geht sofort auf (die
    # Bilder kommen nach und nach); je Aufspannung ein Abschnitt mit
    # eigenem Bild (die anderen Jobs ausgeblendet, die Backen am Ende der Stange darin); danach
    # ist alles wieder sichtbar wie vorher, das Dokument gilt nicht als geändert, und weder im
    # Rückgängig noch im Baum bleibt etwas.
    import numpy as np
    import Part

    from camaddon import n_eck as ne

    stange_doc = FreeCAD.newDocument("Sechskant")
    teil = stange_doc.addObject("Part::Feature", "Teil")
    teil.Shape = Part.makeCylinder(8, 30).fuse(Part.makeBox(30, 6, 6, FreeCAD.Vector(-15, -3, 24)))
    stange_doc.recompute()
    punkte = np.array([(v.X, v.Y, v.Z) for v in teil.Shape.Vertexes])
    grund, _stange = ne.richte_ein(stange_doc, teil, punkte, n=6, achse="Z")
    ne.aufspannungen_anlegen(grund)
    stange_doc.recompute()
    yield 1000
    Gui.getDocument(stange_doc.Name).Modified = False
    rueckgaengig = stange_doc.UndoCount
    objekte = len(stange_doc.Objects)
    sichtbar = {o.Name: o.ViewObject.Visibility for o in stange_doc.Objects if o.ViewObject}
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(grund)
    beginn = time.time()
    Gui.runCommand("CamAddon_Einrichtblatt")
    h.pruefe(time.time() - beginn < 2.0, f"Fenster erst nach {time.time() - beginn:.1f} s")
    yield from h.warte_auf(lambda: gui_einrichtblatt.EinrichtblattDialog.offen is not None, 30000)
    yield 1000
    dialog = gui_einrichtblatt.EinrichtblattDialog.offen
    if dialog is not None:  # die Bilder der Aufspannungen kommen nach und nach
        yield from h.warte_auf(lambda: dialog.bilder_fertig, 60000)
    h.pruefe(dialog is not None, "kein Fenster für die Stange")
    if dialog is None:
        return
    auf = dialog.blatt.aufspannungen
    h.pruefe(len(auf) == 6, f"{len(auf)} Aufspannungen statt 6")
    h.pruefe(all(a.bild and os.path.exists(a.bild) for a in auf), "nicht je Aufspannung ein Bild")
    if len(auf) >= 2 and all(a.bild for a in auf[:2]):
        with open(auf[0].bild, "rb") as f1, open(auf[1].bild, "rb") as f2:
            h.pruefe(f1.read() != f2.read(), "Aufspannung 1 und 2 im selben Bild")
    h.pruefe(
        all("6-Kant-Stange" in a.rohteil and "Schraubstock am Ende" in a.spannung for a in auf),
        f"Stange: {auf[0].rohteil!r}, {auf[0].spannung!r}",
    )
    h.pruefe(
        "Aufspannung 2 von 6" in auf[1].nullpunkt if len(auf) > 1 else False,
        f"Nullpunkt 2: {auf[1].nullpunkt if len(auf) > 1 else ''!r}",
    )
    nachher = {o.Name: o.ViewObject.Visibility for o in stange_doc.Objects if o.ViewObject}
    h.pruefe(nachher == sichtbar, "Sichtbarkeit nicht wiederhergestellt")
    h.pruefe(not Gui.getDocument(stange_doc.Name).Modified, "Dokument gilt als geändert")
    h.pruefe(
        stange_doc.UndoCount == rueckgaengig and len(stange_doc.Objects) == objekte,
        f"Spuren: Rückgängig {stange_doc.UndoCount}, Objekte {len(stange_doc.Objects)}",
    )
    dialog.vorschau.verticalScrollBar().setValue(700)
    yield 300
    h.bild("2_sechskant", dialog)
    if os.environ.get("AUSGABE"):
        for i, a in enumerate(auf[:2], 1):
            shutil.copy(a.bild, os.path.join(os.environ["AUSGABE"], f"sechskant_{i}.png"))
    dialog.reject()
    yield 500
    FreeCAD.closeDocument(stange_doc.Name)

    # Eine geschwenkte Ebene (3+2, wie schwenken.lege_an sie anlegt: ein Job mit Grundjob, Ebene
    # und Rundachsen, das Teil darin gedreht): In der Aufspannung des Grundjobs ein Bild von ihm und
    # an der Zwischenzeile der Ebene ein eigenes, anderes.
    import Path.Main.Job as PathJob
    import Path.Op.Custom as PathCustom

    from camaddon import schwenken as sw

    eb_doc = FreeCAD.newDocument("Schwenkteil")
    klotz = eb_doc.addObject("Part::Feature", "Klotz")
    klotz.Shape = Part.makeBox(40, 30, 20).cut(Part.makeBox(10, 30, 8, FreeCAD.Vector(30, 0, 12)))
    eb_doc.recompute()
    grund_eb = PathJob.Create("Job", [klotz])
    op_oben = PathCustom.Create("Oben", parentJob=grund_eb)
    op_oben.Gcode = ["G0 X0 Y0 Z25", "G1 Z19 F10", "G1 X30 F10", "G0 Z25"]
    ebene = PathJob.Create("Ebene", [klotz])
    for name, art in (("Grundjob", "App::PropertyLink"), ("Ebene", "App::PropertyPlacement"),
                      ("Rundachsen", "App::PropertyString")):  # fmt: skip
        ebene.addProperty(art, name, "CAM-Addon")
    ebene.Grundjob = grund_eb
    ebene.Rundachsen = "A-90 C0"
    ebene.Label = "Seite vorn"
    ebene.Model.Group[0].Placement = FreeCAD.Placement(
        FreeCAD.Vector(0, 0, 0), FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), 90)
    )
    op_seite = PathCustom.Create("Seite", parentJob=ebene)
    op_seite.Gcode = ["G0 X0 Y0 Z35", "G1 Z29 F10", "G1 X30 F10", "G0 Z35"]
    eb_doc.recompute()
    yield 1000
    h.pruefe(sw.ist_ebene(ebene), "Ebene nicht erkannt")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(grund_eb)
    Gui.runCommand("CamAddon_Einrichtblatt")
    yield from h.warte_auf(lambda: gui_einrichtblatt.EinrichtblattDialog.offen is not None, 30000)
    yield 1000
    dialog = gui_einrichtblatt.EinrichtblattDialog.offen
    if dialog is not None:  # die Bilder der Aufspannungen kommen nach und nach
        yield from h.warte_auf(lambda: dialog.bilder_fertig, 60000)
    h.pruefe(dialog is not None, "kein Fenster für das Schwenkteil")
    if dialog is None:
        return
    auf = dialog.blatt.aufspannungen
    bilder = list(auf[0].ebenen_bilder.values()) if auf else []
    h.pruefe(
        len(auf) == 1 and auf[0].bild and len(bilder) == 1 and os.path.exists(bilder[0]),
        f"Schwenkteil: {len(auf)} Aufspannungen, Ebenen-Bilder {bilder}",
    )
    if auf and auf[0].bild and bilder:
        with open(auf[0].bild, "rb") as f1, open(bilder[0], "rb") as f2:
            h.pruefe(f1.read() != f2.read(), "Ebene im selben Bild wie der Grundjob")
    h.pruefe(dialog.text.count("<img") >= 2, "die Seite zeigt nicht beide Bilder")
    dialog.vorschau.verticalScrollBar().setValue(300)
    yield 300
    h.bild("3_schwenkteil", dialog)
    if os.environ.get("AUSGABE") and bilder:
        shutil.copy(bilder[0], os.path.join(os.environ["AUSGABE"], "ebene_seite_vorn.png"))
    dialog.reject()
    yield 500
    FreeCAD.closeDocument(eb_doc.Name)
