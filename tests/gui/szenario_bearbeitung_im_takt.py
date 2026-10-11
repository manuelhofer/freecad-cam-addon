# Die Vorschau des Assistenten „Bearbeitung“ im Takt (P-2026-10-11-16): Nach einer Eingabe
# rechnet sie Block für Block aus der Ereignisschleife – dazwischen nimmt das Fenster Eingaben an.
# Am 3-Achs-Testteil (die vier ebenen Flächen): anklicken, mitten im Lauf die Zustellung des
# Räumens ändern – der Lauf hört auf, ein neuer rechnet mit dem neuen Wert; mitten im nächsten
# Lauf „Anlegen“ – er rechnet am Stück fertig, und die Operationen entstehen. Eine Uhr des Fensters
# zählt mit, wie oft die Ereignisschleife während des Laufs drankam (takt.txt: auch die längste
# Pause – ein Block, der lange rechnet, hält sie so lange an).
import os
import time

import FreeCAD
import FreeCADGui as Gui
from PySide import QtCore


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    import camaddon
    from camaddon import gui_bearbeitung
    from camaddon import hoehenfeld as hf
    from camaddon import werkzeuge as wz

    wz.Bibliothek(wz.testkiste()).speichern()
    datei = os.path.join(camaddon.ADDON_ORDNER, "beispiele", "testteil_3achs_fraese.FCStd")
    doc = FreeCAD.openDocument(datei)
    doc.UndoMode = 1
    yield 1500
    teil = doc.getObject("Body")
    ebenen = {round(e.z): e.name for e in hf.ebenen_oben(teil.Shape) if e.x_bis - e.x_von > 1.0}
    Gui.activateWorkbench("CAMWorkbench")
    Gui.Selection.addSelection(doc.Name, teil.Name, ebenen[10])
    yield 500
    Gui.runCommand("CamAddon_Bearbeitung")
    yield 2500
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    job = panel.job

    # Wie oft kommt die Ereignisschleife dran, während die Vorschau rechnet?
    takte = []
    uhr = QtCore.QTimer()
    uhr.setInterval(20)
    uhr.timeout.connect(lambda: takte.append(time.perf_counter()))
    uhr.start()

    for name in (ebenen[22], ebenen[32], ebenen[27]):
        panel.flaeche_umschalten(name)
    yield from h.warte_auf(lambda: panel._vorschau_lauf is not None, 20000, 10)
    erster_lauf = panel._vorschau_lauf
    h.pruefe(erster_lauf is not None, "die Vorschau rechnet nicht im Takt")
    # Mitten im Lauf eine Eingabe: Er ist veraltet und hört auf.
    yield 50
    panel.raeumen.felder["zustellung"].setText("10")
    h.pruefe(panel._vorschau_lauf is None, "der alte Lauf rechnet nach der Eingabe weiter")
    h.pruefe(panel.vorschau_laeuft(), "nach der Eingabe steht keine Vorschau aus")
    beginn = time.perf_counter()
    yield from h.warte_auf(
        lambda: not panel.vorschau_laeuft()
        and all(b.vorschau is not None or not b.aktiv() for b in panel.bloecke),
        300000,
    )
    dauer = time.perf_counter() - beginn
    h.pruefe(
        abs(panel.raeumen.werte()["zustellung"] - 10.0) < 1e-9
        and panel.raeumen.vorschau is not None,
        f"Räumen nicht mit der neuen Zustellung: {panel.raeumen.werte().get('zustellung')}",
    )
    # Während des Laufs kam die Uhr des Fensters immer wieder dran – die längste Pause zwischen
    # zwei Takten ist ein Schritt, nicht der ganze Lauf.
    im_lauf = [t for t in takte if t >= beginn]
    pausen = [b - a for a, b in zip(im_lauf, im_lauf[1:], strict=False)]
    h.pruefe(len(im_lauf) >= 5, f"die Ereignisschleife kam während {dauer:.1f} s kaum dran")
    with open(os.path.join(os.environ["CAMADDON_AUSGABE"], "takt.txt"), "w") as f:
        f.write(
            f"Lauf {dauer:.1f} s, Takte {len(im_lauf)}, längste Pause {max(pausen or [0]):.2f} s\n"
        )
    h.bild("1_neu_gerechnet", panel.form)

    # Mitten im nächsten Lauf „Anlegen“: Er rechnet am Stück fertig, die Operationen entstehen.
    panel.raeumen.felder["zustellung"].setText("11")
    yield from h.warte_auf(lambda: panel._vorschau_lauf is not None, 20000, 10)
    h.pruefe(panel._vorschau_lauf is not None, "zweiter Lauf rechnet nicht im Takt")
    vorher = len(job.Operations.Group)
    h.pruefe(panel.accept() is True, "Anlegen mitten im Lauf ging nicht")
    uhr.stop()
    yield 1500
    h.pruefe(
        len(job.Operations.Group) > vorher and gui_bearbeitung.BearbeitungPanel.offen is None,
        f"keine Operationen angelegt ({vorher} → {len(job.Operations.Group)})",
    )
    h.bild("2_angelegt")
