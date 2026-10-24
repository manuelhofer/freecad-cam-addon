# SPDX-License-Identifier: LGPL-2.1-or-later
# „Fertigteil als Rohteil“ für eine Aufspannung mit Ebenen (3+2, W-029): Rohteil 60 × 26 × 20,
# ein Grundjob, eine Ebene von links (A 90, C 180: das Werkzeug längs −X). In ihr taucht der
# Standardfräser Ø 12 bei y 13, z 6 von außen 8 mm tief ein, fährt auf z 14 und wieder hinaus –
# das Teil ist das Rohteil ohne genau diese Bahn (ein Langloch in der linken Stirn). Der Befehl an
# der Ebene: „Teil – Aufspannung 1 – Fertigteil“ im Dokument, die Meldung nennt das räumliche
# Raster und kein „Achtung“; ein gültiger Körper, so groß wie das Teil (es bleibt nichts stehen),
# das Teil ganz darin, das Langloch offen. Noch einmal: dasselbe Objekt.
# ZEITLIMIT: 600
import FreeCAD as App
import FreeCADGui as Gui
import Part
import Path
from PySide import QtCore, QtGui

V = App.Vector


def _langloch():
    """Was der Fräser nimmt: im Schnitt y–z ein Langloch (Ø 12 von z 6 bis 14) – längs X von
    außen bis 8 tief."""
    unten = Part.makeCylinder(6, 9, V(-1, 13, 6), V(1, 0, 0))
    oben = Part.makeCylinder(6, 9, V(-1, 13, 14), V(1, 0, 0))
    return unten.fuse(oben).fuse(Part.makeBox(9, 12, 8, V(-1, 7, 6))).removeSplitter()


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.accept()
    yield 500
    from Path.Main import Job as PathJob

    from camaddon import fertigteil as ft
    from camaddon import gui_fertigteil
    from camaddon import job_schnittwerte as js
    from camaddon import raum_material as raum
    from camaddon import schwenken as sw
    from camaddon import uebergabe_werkzeuge as ue
    from camaddon import werkzeuge as wz

    standard = wz.standardwerkzeug()
    ue.uebergeben(wz.Bibliothek([standard]))
    einsatz = next(e for e in standard.schnittwerte[wz.ALLE] if e.art == wz.SCHRUPPEN)
    doc = App.newDocument("Langloch")
    rohteil = Part.makeBox(60, 26, 20)
    teil = doc.addObject("Part::Feature", "Teil")
    teil.Shape = rohteil.cut(_langloch()).removeSplitter()
    roh = doc.addObject("Part::Feature", "Rohteil")
    roh.Shape = rohteil
    grund = PathJob.Create("Job", [teil])
    grund.Stock = roh
    doc.recompute()
    ebene = sw.lege_an(grund, "", winkel=(90, 180))
    tc = js.controller_ohne_transaktion(doc, ebene, standard, einsatz)
    doc.recompute()
    op = doc.addObject("Path::Feature", "Langloch")
    op.addProperty("App::PropertyLink", "ToolController")
    op.ToolController = tc
    op.addProperty("App::PropertyBool", "Active")
    op.Active = True
    inv = ebene.Ebene.inverse()
    wege = [
        ("G0", V(-20, 13, 6)),
        ("G1", V(8, 13, 6)),
        ("G1", V(8, 13, 14)),
        ("G1", V(-20, 13, 14)),
    ]
    op.Path = Path.Path(
        [Path.Command(g, dict(zip("XYZ", inv.multVec(p), strict=True))) for g, p in wege]
    )
    ebene.Operations.Group = [op]
    doc.recompute()
    rest = raum.nach_allen(ebene)
    h.pruefe(rest is not None, "kein räumlicher Rest nach allen Ebenen")
    if rest is not None:
        h.pruefe(not rest.belegt([[4, 13, 10]]).any(), "das Langloch ist im Rest nicht weg")
    Gui.activateWorkbench("CAMWorkbench")
    Gui.Selection.clearSelection()
    yield 300

    def anlegen():
        QtCore.QTimer.singleShot(0, lambda: gui_fertigteil.ausfuehren(ebene))
        yield from h.warte_auf(lambda: isinstance(h.modal(), QtGui.QMessageBox), 300000)
        meldung = h.modal()
        return meldung, (meldung.text() if isinstance(meldung, QtGui.QMessageBox) else "")

    meldung, text = yield from anlegen()
    h.bild("1_meldung", meldung)
    h.pruefe("räumlich nach allen Ebenen" in text, f"Meldung: {text[:300]!r}")
    h.pruefe("Achtung" not in text, f"ins Teil: {text[:200]!r}")
    if isinstance(meldung, QtGui.QMessageBox):
        meldung.accept()
    yield 500
    fertig = ft.vorhanden(grund)
    h.pruefe(fertig is not None, "kein Fertigteil im Dokument")
    if fertig is None:
        return
    h.pruefe(fertig.Label.endswith("Aufspannung 1 – Fertigteil"), f"Name: {fertig.Label}")
    form = fertig.Shape
    h.pruefe(form.isValid() and len(form.Solids) == 1, f"Körper: {form.ShapeType}")
    innen = teil.Shape.common(form).Volume
    h.pruefe(innen > 0.999 * teil.Shape.Volume, f"Teil nicht ganz darin: {innen:.0f}")
    h.pruefe(
        abs(form.Volume - teil.Shape.Volume) < 0.005 * teil.Shape.Volume,
        f"Volumen {form.Volume:.0f} statt {teil.Shape.Volume:.0f} mm³",
    )
    h.pruefe(not form.isInside(V(4, 13, 10), 0.01, True), "das Langloch ist zu")
    print(
        ascii(
            f"Fertigteil 3+2: {form.Volume:.0f} mm³ (Teil {teil.Shape.Volume:.0f}), {len(form.Faces)} Flächen"
        )
    )
    meldung, _text = yield from anlegen()  # noch einmal: dasselbe Objekt, neue Form
    if isinstance(meldung, QtGui.QMessageBox):
        meldung.accept()
    yield 500
    gleich = [o for o in doc.Objects if getattr(o, "AusJob", None) == grund.Name]
    h.pruefe(len(gleich) == 1, f"Fertigteile: {[o.Label for o in gleich]}")
    for o in doc.Objects:
        if o.ViewObject is not None:
            o.ViewObject.Visibility = o is fertig
    Gui.getDocument(doc.Name).activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("2_fertigteil_3d")
    Gui.getDocument(doc.Name).Modified = False
    App.closeDocument(doc.Name)
    yield 300
