# Ein Teil aus einem STL und sein Klon als Netz (W-017, stl_anzeige): FreeCADs eigene Anzeige des
# Körpers kostete am Geist 1,7 s je Körper. Eine Kugel aus einem Netz (1.740 Dreiecke) als Körper:
# Er erscheint als Netz, FreeCADs Anzeige bleibt aus. Sein Klon an anderer Stelle ebenso; ein Klick
# auf ein Dreieck des Klons wählt in FreeCAD „FaceN“ des Klons, und das Netz zeigt die Auswahl
# grün. Farben der Flächen zieht das Netz nach (farben_nachziehen). „Abbrechen“ (Transaktion zurück) bringt ein
# ausgeblendetes Netz wieder. Blendet man den Klon in FreeCAD ein (wie mit der Leertaste), zeigt
# FreeCAD ihn selbst, das Netz geht aus. Speichern, schließen, öffnen: das Netz ist wieder da,
# FreeCADs Anzeige aus, das Dokument „unverändert“.
import os
import tempfile

import FreeCAD
import FreeCADGui as Gui
import Mesh


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.accept()
    yield 500

    import Draft
    from pivy import coin

    from camaddon import stl_anzeige as sa
    from camaddon import stl_teil

    doc = FreeCAD.newDocument("Netzanzeige")
    netz = doc.addObject("Mesh::Feature", "Kugel")
    netz.Mesh = Mesh.createSphere(10.0, 30)
    netz.ViewObject.Visibility = False
    doc.recompute()
    teil, _bericht = stl_teil.koerper_aus_netz(doc, netz)
    doc.recompute()
    h.pruefe(not teil.ViewObject.Visibility, "Körper in FreeCAD sichtbar angelegt")
    h.pruefe(sa.zeigen(teil, True), "Körper nicht als Netz")
    h.pruefe(sa.als_netz(teil) and sa.sichtbar(teil), "Netz nicht da")
    klon = Draft.make_clone(teil)
    klon.Placement = FreeCAD.Placement(FreeCAD.Vector(40, 0, 0), FreeCAD.Rotation(0, 0, 0))
    doc.recompute()
    h.pruefe(sa.vorbild(klon) is teil, "Klon nicht erkannt")
    sa.zeigen(klon, True)
    sa.zeigen(teil, False)
    h.pruefe(sa.als_netz(klon) and not klon.ViewObject.Visibility, "Klon nicht als Netz")
    h.pruefe(not sa.sichtbar(teil), "Körper noch zu sehen")
    ansicht = Gui.getDocument(doc.Name).mdiViewsOfType("Gui::View3DInventor")[0]
    ansicht.viewFront()
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("1_klon_als_netz")

    # --- Anklicken: FreeCAD wählt die Fläche des Klons ----------------------------------------
    x, y = ansicht.getPointOnViewport(FreeCAD.Vector(40, -10, 0))  # vorne mitten auf der Kugel
    info = ansicht.getObjectInfo((int(x), int(y)))
    h.pruefe(
        info is not None
        and info.get("Object") == klon.Name
        and str(info.get("Component", "")).startswith("Face"),
        f"angeklickt: {info}",
    )
    if info is not None and info.get("Object") == klon.Name:
        flaeche = info["Component"]
        nummer = int(flaeche[4:]) - 1
        mitte = klon.Shape.getElement(flaeche).CenterOfMass
        h.pruefe(
            mitte.y < -9.0 and abs(mitte.x - 40) < 3 and abs(mitte.z) < 3,
            f"{flaeche} liegt nicht vorne: {mitte}",
        )
        Gui.Selection.addSelection(doc.Name, klon.Name, flaeche)
        yield 200
        marken = sa._knoten(klon.ViewObject).getChild(sa.MARKEN)
        h.pruefe(marken.getNumChildren() == 1, f"Auswahl nicht grün: {marken.getNumChildren()}")
        Gui.Selection.clearSelection()
        yield 200
        h.pruefe(marken.getNumChildren() == 0, "Auswahl bleibt grün")

        # --- Farben -------------------------------------------------------------------------
        # (26.3 kennt DiffuseColor am Klon nicht mehr – der Assistent färbt dort nicht)
        if hasattr(klon.ViewObject, "DiffuseColor"):
            anzahl = klon.Shape.countElement("Face")
            farben = [(0.8, 0.8, 0.8, 0.0)] * anzahl
            farben[nummer] = (1.0, 0.0, 0.0, 0.0)
            klon.ViewObject.DiffuseColor = farben
            # Von Hand an der Anzeige geändert, zieht das Netz erst auf Zuruf nach: Ein
            # Beobachter der Anzeigen brach FreeCADs Assembly (P-2026-10-16-11).
            sa.farben_nachziehen(klon)
            yield 200
            bindung = sa._knoten(klon.ViewObject).getChild(sa.BINDUNG)
            h.pruefe(
                bindung.value.getValue() == coin.SoMaterialBinding.PER_FACE, "Farben nicht im Netz"
            )
            h.bild("2_farbe")

    # --- Abbrechen bringt das Netz wieder --------------------------------------------------------
    doc.openTransaction("Probe")
    sa.zeigen(klon, False)
    h.pruefe(not sa.als_netz(klon), "Netz nicht aus")
    doc.abortTransaction()
    yield from h.warte_auf(lambda: sa.als_netz(klon), 3000)
    h.pruefe(sa.als_netz(klon), "nach Abbrechen kein Netz")

    # --- In FreeCAD eingeblendet: FreeCAD zeigt ihn, das Netz geht aus -----------------------
    klon.ViewObject.Visibility = True
    yield 200
    h.pruefe(not sa.als_netz(klon), "Netz und FreeCADs Anzeige doppelt")
    sa.zeigen(klon, True)
    h.pruefe(sa.als_netz(klon) and not klon.ViewObject.Visibility, "wieder als Netz")

    # --- Speichern, schließen, öffnen --------------------------------------------------------
    pfad = os.path.join(tempfile.mkdtemp(prefix="camaddon_netz_"), "netz.FCStd")
    name, teil_name = klon.Name, teil.Name
    doc.saveAs(pfad)
    yield 200
    Gui.runCommand("Std_Save", 0)
    yield 300
    FreeCAD.closeDocument(doc.Name)
    yield 300
    doc = FreeCAD.openDocument(pfad)
    yield from h.warte_auf(lambda: sa.als_netz(doc.getObject(name)), 5000)
    klon = doc.getObject(name)
    h.pruefe(sa.als_netz(klon), "nach dem Öffnen kein Netz")
    h.pruefe(not klon.ViewObject.Visibility, "nach dem Öffnen zeigt FreeCAD den Klon selbst")
    h.pruefe(not Gui.getDocument(doc.Name).Modified, "nach dem Öffnen „geändert“")
    h.pruefe(not sa.sichtbar(doc.getObject(teil_name)), "nach dem Öffnen der Körper zu sehen")
    ansicht = Gui.getDocument(doc.Name).mdiViewsOfType("Gui::View3DInventor")[0]
    ansicht.viewFront()
    Gui.SendMsgToActiveView("ViewFit")
    yield 300
    h.bild("3_geoeffnet")
    FreeCAD.closeDocument(doc.Name)
