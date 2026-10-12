# Schwere Modellklone speichern ihre Form nicht mit (W-017, klone_speichern): Ein Körper mit vielen
# Flächen (wie ein Teil aus einem STL) und sein Klon (Draft, wie das Modell eines Jobs) an anderer
# Lage. Speichern: Die Datei hat die Form des Vorbilds, nicht die des Klons; im Dokument bleibt
# der Klon, wie er war, und das Dokument gilt als gespeichert. Schließen und öffnen: Der Klon hat
# seine Form wieder – gleich viele Flächen, an seiner Lage, die Daten mit dem Vorbild geteilt –,
# und das Dokument gilt als unverändert, ohne Schritt Rückgängig. Abgeschaltet speichert er alles.
import os
import tempfile
import zipfile

import FreeCAD
import FreeCADGui as Gui
import Part


def _gespeichert(pfad):
    return zipfile.ZipFile(pfad).namelist()


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.accept()
    yield 500

    import Draft

    from camaddon import klone_speichern as ks
    from camaddon import nebenrechner as nr

    h.pruefe(ks.an(), "Einstellung nicht vorbelegt an")
    ordner = tempfile.mkdtemp(prefix="camaddon_klone_")
    pfad = os.path.join(ordner, "klone.FCStd")
    doc = FreeCAD.newDocument("Klone")
    viele = doc.addObject("Part::Feature", "Viele")
    viele.Shape = Part.makeCompound(
        [
            Part.makeBox(1, 1, 1, FreeCAD.Vector(2 * i, 0, 0))
            for i in range(nr.KLON_SCHWER_AB // 6 + 1)
        ]
    )
    klon = Draft.make_clone(viele)
    klon.Placement = FreeCAD.Placement(FreeCAD.Vector(0, 50, 7), FreeCAD.Rotation(30, 0, 0))
    doc.recompute()
    flaechen = klon.Shape.countElement("Face")
    kasten = klon.Shape.BoundBox
    name = klon.Name
    yield 300

    # --- Speichern ---------------------------------------------------------------------------
    doc.saveAs(pfad)  # der Dateiname; danach wie Manuel mit „Speichern“ (Strg+S)
    yield 300
    Gui.runCommand("Std_Save", 0)
    yield 300
    h.pruefe(not Gui.getDocument(doc.Name).Modified, "nach dem Speichern „geändert“")
    namen = _gespeichert(pfad)
    h.pruefe(not any(n.startswith(f"{name}.Shape") for n in namen), f"Klon gespeichert: {namen}")
    h.pruefe(any(n.startswith("Viele.Shape") for n in namen), f"Vorbild fehlt: {namen}")
    h.pruefe(klon.getPropertyStatus("Shape") == [], f"Status: {klon.getPropertyStatus('Shape')}")
    h.pruefe(not klon.Shape.isNull(), "Klon im Dokument leer")

    # --- Schließen und öffnen ----------------------------------------------------------------
    FreeCAD.closeDocument(doc.Name)
    yield 300
    doc = FreeCAD.openDocument(pfad)
    yield from h.warte_auf(lambda: not doc.getObject(name).Shape.isNull(), 5000)
    klon = doc.getObject(name)
    h.pruefe(not klon.Shape.isNull(), "Klon nach dem Öffnen leer")
    h.pruefe(
        klon.Shape.countElement("Face") == flaechen, f"Flächen: {klon.Shape.countElement('Face')}"
    )
    neu = klon.Shape.BoundBox
    abweichung = max(
        abs(a - b)
        for a, b in zip(
            (neu.XMin, neu.YMin, neu.ZMin, neu.XMax, neu.YMax, neu.ZMax),
            (kasten.XMin, kasten.YMin, kasten.ZMin, kasten.XMax, kasten.YMax, kasten.ZMax),
            strict=True,
        )
    )
    h.pruefe(abweichung < 1e-9, f"Klon an anderer Stelle: {abweichung}")
    h.pruefe(klon.Shape.isPartner(doc.getObject("Viele").Shape), "Daten nicht geteilt")
    h.pruefe(klon.getPropertyStatus("Shape") == [], f"Status: {klon.getPropertyStatus('Shape')}")
    h.pruefe("Touched" not in klon.State, f"Klon: {klon.State}")
    h.pruefe(not Gui.getDocument(doc.Name).Modified, "nach dem Öffnen „geändert“")
    h.pruefe(not doc.UndoNames, f"Rückgängig: {doc.UndoNames}")
    h.bild("1_geoeffnet")

    # --- Abgeschaltet: alles speichern ---------------------------------------------------------
    ks.setzen(False)
    try:
        ganz = os.path.join(ordner, "ganz.FCStd")
        doc.saveAs(ganz)
        yield 300
        Gui.runCommand("Std_Save", 0)
        yield 300
        h.pruefe(not Gui.getDocument(doc.Name).Modified, "abgeschaltet: „geändert“")
        h.pruefe(
            any(n.startswith(f"{name}.Shape") for n in _gespeichert(ganz)),
            "abgeschaltet: Klon nicht gespeichert",
        )
    finally:
        ks.setzen(True)
    FreeCAD.closeDocument(doc.Name)
