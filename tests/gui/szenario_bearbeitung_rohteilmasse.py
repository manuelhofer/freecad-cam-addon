# Rohteil als Quader mit Maßen (W-028; Manuel, 2026-10-18: „rohteil quader 60.93x61.96 ist natürlich
# quatsch … wo ich einfach die werte des rohteils reinpacke“; „unterm nullpunkt is das teil direkt
# wenn oben aufmass 0 ist .. wenn oben aufmass 1 ist liegts 1mm drunter ... und unten aufmass brauchts
# dann ja eigentlich nicht ... auser man will es eingeben dann ergibt sich aber das obere aufmass durch
# die höhe .. also ein switch wäre gut ... wenn das teil dann nicht ins rohteil past muss es eine
# warnung geben“). Manuels C-Ring (58,93 × 59,96 × 10) ohne Job, „Bearbeitung“ auf der 3-Achs-Fräse.
# „Quader mit Maßen“: grau der Vorschlag 61 × 62 × 12 (1 mm je Seite, auf ganze mm), der Nullpunkt
# geht auf „Mitte oben“; das Rohteil 61 × 62 × 12, mittig, seine Oberseite im Ursprung, das Teil 1 mm
# darunter. Länge 58: rot „Das Teil passt nicht ins Rohteil …“, das Rohteil nie kleiner als das Teil.
# Länge 62, „Aufmaß unten“ 2, Höhe 16: die Unterseite des Teils 2 mm über der des Rohteils, oben 4.
# Oben in Schritt 2 „Rohteil 62 × 62 × 16 mm, Aufmaß unten 2 mm“; der Job merkt sich die Maße, das
# Einrichtblatt schreibt „Quader 62 × 62 × 16 mm – das Teil mittig, seine Unterseite 2 mm über der
# des Rohteils“.
import os
import shutil
import tempfile

import FreeCAD
import FreeCADGui as Gui

ADDON = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine, gui_bearbeitung
    from camaddon import einrichtblatt as eb
    from camaddon import maschinenspeicher as ms
    from camaddon import werkzeuge as wz
    from camaddon.sprache import tr

    wz.Bibliothek([wz.standardwerkzeug()]).speichern()
    ms.speichern([])
    ordner = tempfile.mkdtemp()
    asm, _maschine = beispielmaschine.lade(beispielmaschine.FRAESE_3)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    asm.Document.saveAs(os.path.join(ordner, "Fraese.FCStd"))
    yield 300
    datei = os.path.join(ordner, "cring.FCStd")
    shutil.copy(os.path.join(ADDON, "beispiele", "c_ring_nut_3achs.FCStd"), datei)
    doc = FreeCAD.openDocument(datei)
    koerper = doc.getObject("Body")
    bleibt = {koerper.Name, *(o.Name for o in koerper.OutListRecursive)}
    for job in [o for o in doc.Objects if hasattr(o, "Operations")]:
        weg = [o.Name for o in job.OutListRecursive if o.Name not in bleibt]
        doc.removeObject(job.Name)
        for name in weg:
            if doc.getObject(name) is not None:
                doc.removeObject(name)
    doc.recompute()
    yield 500
    Gui.activateWorkbench("CAMWorkbench")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, "Body", "Face4")
    yield 500
    gui_bearbeitung.nullpunkt_vorgeben(None)
    Gui.runCommand("CamAddon_Bearbeitung")
    yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not None)
    yield 1500
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    teil = panel.job.Model.Group[0]

    def kaesten():
        doc.recompute()
        return panel.job.Stock.Shape.BoundBox, teil.Shape.BoundBox

    panel.knopf_rohteil_masse.setChecked(True)
    yield 500
    grau = [panel.felder_masse[f].placeholderText() for f in ("x", "y", "z")]
    h.pruefe(grau == ["61", "62", "12"], f"Vorschlag: {grau}")
    h.pruefe(panel.nullpunkt() == (0, 0, 1), f"Nullpunkt: {panel.nullpunkt()}")
    h.pruefe(panel.rohteilmasse.isVisible() and not panel.rohteilfelder.isVisible(), "Felder")
    panel._rohteil_anwenden()
    yield 800
    roh, bb = kaesten()
    h.pruefe(
        abs(roh.XLength - 61) < 1e-6
        and abs(roh.YLength - 62) < 1e-6
        and abs(roh.ZLength - 12) < 1e-6,
        f"Rohteil {roh.XLength:.3f} × {roh.YLength:.3f} × {roh.ZLength:.3f}",
    )
    h.pruefe(
        abs(roh.ZMax) < 1e-6 and abs(bb.ZMax + 1.0) < 1e-6, f"oben: {roh.ZMax}, Teil {bb.ZMax}"
    )
    h.pruefe(
        abs(roh.XMin + roh.XMax) < 1e-6 and abs(roh.YMin + roh.YMax) < 1e-6,
        f"nicht mittig: {roh}",
    )
    h.pruefe(not panel.rohteil_warnung.isVisible(), "Warnung, obwohl es passt")

    panel.felder_masse["x"].setText("58")
    panel._rohteil_anwenden()
    yield 800
    warnung = panel.rohteil_warnung.text()
    roh, bb = kaesten()
    h.pruefe(
        panel.rohteil_warnung.isVisible()
        and warnung.startswith("Das Teil passt nicht ins Rohteil"),
        f"Warnung: {warnung!r}",
    )
    h.pruefe(roh.XLength >= bb.XLength - 1e-6, f"Rohteil kleiner als das Teil: {roh.XLength}")
    h.bild("1_passt_nicht", panel.form)

    panel.felder_masse["x"].setText("62")
    panel.wahl_masse_lage.setCurrentIndex(panel.wahl_masse_lage.findData("unten"))
    panel.felder_masse["aufmass"].setText("2")
    panel.felder_masse["z"].setText("16")
    panel._rohteil_anwenden()
    yield 800
    roh, bb = kaesten()
    h.pruefe(not panel.rohteil_warnung.isVisible(), f"Warnung: {panel.rohteil_warnung.text()!r}")
    h.pruefe(
        abs(roh.ZLength - 16) < 1e-6 and abs(bb.ZMin - roh.ZMin - 2.0) < 1e-6,
        f"unten: Rohteil {roh.ZMin:.3f} … {roh.ZMax:.3f}, Teil {bb.ZMin:.3f} … {bb.ZMax:.3f}",
    )
    h.pruefe(abs(roh.ZMax) < 1e-6 and abs(bb.ZMax + 4.0) < 1e-6, f"oben: Teil {bb.ZMax:.3f}")
    panel._rohteil_kurz_zeigen()
    kurz = panel.rohteil_kurz.text()
    h.pruefe("Rohteil 62 × 62 × 16 mm, Aufmaß unten 2 mm" in kurz, f"kurz: {kurz!r}")
    h.pruefe(
        getattr(panel.job, "CamAddonRohteilMasse", "") == "62;62;16;unten;2",
        f"am Job: {getattr(panel.job, 'CamAddonRohteilMasse', None)!r}",
    )
    text = eb.rohteil_text(panel.job, tr)
    h.pruefe(
        text
        == "Quader 62 × 62 × 16 mm – das Teil mittig, seine Unterseite 2 mm über der des Rohteils",
        f"Einrichtblatt: {text!r}",
    )
    h.bild("2_masse", panel.form)
