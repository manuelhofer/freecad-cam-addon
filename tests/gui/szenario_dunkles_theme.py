# THEMA: FreeCAD Dark
# Das dunkle Theme von FreeCAD (P-2026-10-10-42; Manuel, 2026-10-10: „Man kann die Schrift nicht
# lesen im dunkel Modus“): „Bearbeitung“ an einem Block mit einer Bohrung Ø 8, 5 tief, ihr Boden
# gewählt – der Standardfräser Ø 12 passt nicht hinein, also steht unter „Räumen“ ein roter
# Hinweis, darüber die grauen Sätze. Die Textfarben sind die hellen für dunklen Grund
# (farben.py), und jeder graue und rote Satz hebt sich deutlich vom Grund des Fensters ab.
import FreeCAD
import FreeCADGui as Gui
import Part

V = FreeCAD.Vector


def _kontrast(a, b):
    """Kontrastverhältnis zweier QColor nach WCAG (1 … 21)."""

    def leucht(farbe):
        def kanal(c):
            c = c / 255.0
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

        return (
            0.2126 * kanal(farbe.red())
            + 0.7152 * kanal(farbe.green())
            + 0.0722 * kanal(farbe.blue())
        )

    hell, dunkel = sorted((leucht(a), leucht(b)), reverse=True)
    return (hell + 0.05) / (dunkel + 0.05)


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500
    from PySide import QtGui

    from camaddon import farben, gui_bearbeitung
    from camaddon import maschinenspeicher as ms
    from camaddon import werkzeuge as wz

    h.pruefe(farben.dunkel(), "dunkles Theme nicht erkannt")
    h.pruefe(
        (farben.GRAU, farben.ROT) == ("#b4b4b4", "#ff7b72"),
        f"Farben für dunklen Grund: {farben.GRAU}, {farben.ROT}",
    )
    wz.Bibliothek([wz.standardwerkzeug()]).speichern()
    ms.speichern([])

    doc = FreeCAD.newDocument("Dunkel")
    block = doc.addObject("Part::Feature", "Block")
    loch = Part.makeCylinder(4.0, 6.0, V(50, 30, 15), V(0, 0, 1))
    block.Shape = Part.makeBox(100, 60, 20).cut(loch).removeSplitter()
    doc.recompute()
    boden = next(
        f"Face{i + 1}"
        for i, f in enumerate(block.Shape.Faces)
        if f.Surface.TypeId == "Part::GeomPlane" and abs(f.CenterOfMass.z - 15.0) < 1e-6
    )
    Gui.activateWorkbench("CAMWorkbench")
    Gui.SendMsgToActiveView("ViewFit")
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, block.Name, boden)
    yield 500
    gui_bearbeitung.nullpunkt_vorgeben(None)
    Gui.runCommand("CamAddon_Bearbeitung")
    yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not None, 15000)
    a = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(a is not None and a.job is not None, "kein Assistent oder kein Job")
    if a is None or a.job is None:
        return
    if boden not in a.gewaehlte:
        a.flaeche_umschalten(boden)
    a.seite_zeigen(1)
    yield 3000

    # Jeder sichtbare graue oder rote Satz hebt sich vom Grund ab, auf dem er im Hauptfenster
    # steht – gemessen am Bild: Die Palette des Fensters bleibt hell, den Grund malt das Theme.
    mw = Gui.getMainWindow()
    bild = mw.grab().toImage()
    gesehen = {"grau": 0, "rot": 0}
    for satz in a.form.findChildren(QtGui.QLabel):
        stil = satz.styleSheet()
        if not satz.isVisible() or not satz.text():
            continue
        for art, farbe in (("grau", farben.GRAU), ("rot", farben.ROT)):
            if farbe in stil:
                gesehen[art] += 1
                ecke = satz.mapTo(mw, satz.rect().topLeft())  # über dem Text: Grund
                grund = QtGui.QColor(bild.pixel(ecke.x() + 1, max(ecke.y() - 1, 0)))
                k = _kontrast(QtGui.QColor(farbe), grund)
                h.pruefe(
                    k >= 4.5, f"{art} auf {grund.name()}: Kontrast {k:.1f} – {satz.text()[:40]!r}"
                )
    h.pruefe(gesehen["grau"] > 0, f"kein grauer Satz gefunden ({gesehen})")
    h.pruefe(gesehen["rot"] > 0, f"kein roter Hinweis gefunden ({gesehen})")
    h.bild("1_bearbeitung_dunkel")
    a.reject()
