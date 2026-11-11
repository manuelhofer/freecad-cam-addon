# Der kurze Weg (Manuel, 2026-11-11: „ultra easy … ohne gross nachzudenken in freecad sein perfektes
# CAM“): Manuels Testteil für die 3-Achs-Fräse, eine Fläche angeklickt, „Bearbeitung“ – in Schritt 1
# „Alles vorschlagen →“. Ohne eine weitere Antwort steht die Übersicht da: je Bearbeitung Werkzeug
# und Zeit, die Summe. „Anlegen“ legt alles an; das Fenster „Angelegt“ bietet „Programm schreiben …“.
# ZEITLIMIT: 900
import os

import FreeCAD
import FreeCADGui as Gui

NEUES_FENSTER = True  # „Bearbeitung“ in Schritten


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
    from camaddon import gui_bearbeitung_beta as beta
    from camaddon import hoehenfeld as hf
    from camaddon import werkzeuge as wz

    kugel = wz.Werkzeug(nummer=5, name="Kugel 8", art=wz.KUGELFRAESER, durchmesser=8.0, schneiden=2,
                        schneidenlaenge=16.0, schneidstoff=wz.VHM)  # fmt: skip
    kugel.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.3, ap=0.3, vc=150.0, fz=0.05)]
    wz.Bibliothek([*wz.testkiste(), kugel]).speichern()

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
    yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not None, 60000)
    yield 2000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(isinstance(panel, beta.BetaPanel), f"nicht in Schritten: {type(panel).__name__}")
    if panel is None or panel.job is None:
        return
    job = panel.job
    h.pruefe(panel.knopf_alles.isVisible(), "kein Knopf „Alles vorschlagen“ in Schritt 1")
    h.bild("1_schritt_1", panel.form)

    # Ein Klick – ohne zu sagen, wie das Teil liegt, ohne Flächen zu wählen.
    panel.knopf_alles.click()
    yield 1500
    h.pruefe(panel.seite() == beta.UEBERSICHT, f"Seite {panel.seite()} statt der Übersicht")
    h.pruefe(len(panel.gewaehlte) > 10, f"gewählt: {panel.gewaehlte}")
    yield from h.warte_auf(
        lambda: not panel.vorschau_laeuft()
        and all(b.vorschau is not None or not b.aktiv() for b in panel.bloecke),
        600000,
    )
    yield 4000
    text = panel.uebersicht_text.text()
    for wort in ("Räumen", "T1", "Zusammen etwa"):
        h.pruefe(wort in text, f"„{wort}“ fehlt in der Übersicht: {text[:300]!r}")
    h.pruefe(not panel.knopf_alles.isVisible(), "„Alles vorschlagen“ noch in der Übersicht")
    h.pruefe(panel.knopf_zurueck.isVisible() and panel.knopf_fertig.isEnabled(), "Knöpfe")
    h.bild("2_uebersicht", panel.form)

    vorher = len(job.Operations.Group)
    h.pruefe(panel.accept() is True, "„Anlegen“ ging aus der Übersicht nicht")
    yield 3000
    yield from h.warte_auf(lambda: not doc.isTouched(), 600000)
    namen = [o.Label for o in list(job.Operations.Group)[vorher:]]
    print("ALLES", namen, flush=True)
    for name in ("Räumen T1", "Kontur T1", "3D-Schruppen T1", "3D-Schlichten T5"):
        h.pruefe(name in namen, f"„{name}“ fehlt: {namen}")
    yield from h.warte_auf(lambda: beta.FertigFenster.offen is not None, 15000)
    fertig = beta.FertigFenster.offen
    h.pruefe(fertig is not None, "kein Fenster „Angelegt“")
    if fertig is not None:
        yield from h.warte_auf(lambda: fertig.fertig, 120000)
        h.bild("3_angelegt", fertig)
        fertig.close()
    yield 500
    FreeCAD.closeDocument(doc.Name)
    yield 300
