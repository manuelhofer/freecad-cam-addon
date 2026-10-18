# Der C-Ring ohne Job (W-034; Manuel, 2026-10-18, zum Rohteil des Beispiels: „naja es muss beides
# funktionieren .. und auswählbarsein ... wenn rt welle d60 ist muss man ausen nix machen“):
# „Bearbeitung“ auf der 3-Achs-Fräse mit der Testkiste (T1 Ø 12, T2 Plan 50, T3 Ø 6, T4 Ø 20), die
# Oberseite angeklickt, dann „Alles aus dieser Aufspannung“ – einmal als Platte (Quader mit Maßen
# 65 × 65 × 12, Aufmaß oben 1), einmal als Rundmaterial (Zylinder, Aufmaß oben 1, Umfang 0,
# unten 1). Beide Male: Das Räumen bleibt angehakt (es verlor den Haken mit dem Merker „schon weg“
# aus dem zweiten Lauf seiner Folge), die Nut fräst die Ringnut mit T3 (der Ø 12 passt nicht
# hinein, die Nut schlug sich neben anderen Flächen nicht vor – die Ringnut blieb liegen),
# „Schlichten danach“ mit Messstopp davor. „Anlegen“: das Schruppen (Räumen, „Nut T3“, die
# Kontur), dann Messstopp und „Wände schlichten T1“ zuletzt; beim Rundmaterial schlichtet niemand
# den Mantel (davor steht kein Rohteil).
# ZEITLIMIT: 900
import os
import shutil
import tempfile

import FreeCAD
import FreeCADGui as Gui

ADDON = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _rohteil_platte(panel):
    panel.knopf_rohteil_masse.setChecked(True)
    panel.wahl_masse_lage.setCurrentIndex(panel.wahl_masse_lage.findData("oben"))
    for feld, wert in (("x", "65"), ("y", "65"), ("z", "12"), ("aufmass", "1")):
        panel.felder_masse[feld].setText(wert)


def _rohteil_rund(panel):
    panel.knopf_rohteil_zylinder.setChecked(True)
    for feld, wert in (("oben", "1"), ("seite", "0"), ("unten", "1")):
        panel.felder_rohteil[feld].setText(wert)


def _ein_rohteil(h, ordner, name, rohteil_setzen):
    from camaddon import gui_bearbeitung

    datei = os.path.join(ordner, f"cring_{name}.FCStd")
    shutil.copy(os.path.join(ADDON, "beispiele", "c_ring_nut_3achs.FCStd"), datei)
    doc = FreeCAD.openDocument(datei)
    # Ohne seinen Job: Der Assistent legt einen neuen an (Schritt 1 offen).
    koerper = doc.getObject("Body")
    bleibt = {koerper.Name, *(o.Name for o in koerper.OutListRecursive)}
    for job in [o for o in doc.Objects if hasattr(o, "Operations")]:
        weg = [o.Name for o in job.OutListRecursive if o.Name not in bleibt]
        doc.removeObject(job.Name)
        for n in weg:
            if doc.getObject(n) is not None:
                doc.removeObject(n)
    doc.recompute()
    yield 500
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, "Body", "Face4")
    yield 500
    gui_bearbeitung.nullpunkt_vorgeben(None)
    Gui.runCommand("CamAddon_Bearbeitung")
    yield from h.warte_auf(lambda: gui_bearbeitung.BearbeitungPanel.offen is not None)
    yield 1500
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None and panel.job is not None, f"{name}: kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    rohteil_setzen(panel)
    panel._rohteil_anwenden()
    yield 1000
    panel.knopf_weiter.click()
    yield 800
    panel.aus_der_aufspannung()
    yield 1500
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 300000)
    yield 1500
    yield from h.warte_auf(lambda: not panel.vorschau_laeuft(), 300000)
    h.pruefe(panel.raeumen.aktiv(), f"{name}: Räumen ohne Haken: {panel.raeumen.ergebnis.text()!r}")
    nut = panel.nut
    h.pruefe(
        nut.aktiv() and getattr(nut.fraeser(), "nummer", None) == 3,
        f"{name}: Nut {nut.aktiv()} mit T{getattr(nut.fraeser(), 'nummer', None)}",
    )
    danach = panel.schlichten_danach
    h.pruefe(
        danach.aktiv() and danach.haken_felder["messstopp"].isChecked(),
        f"{name}: Schlichten danach {danach.aktiv()}, Messstopp "
        f"{danach.haken_felder['messstopp'].isChecked()}",
    )
    h.bild(f"1_{name}", panel.form)
    panel.knopf_weiter.click()
    yield 800
    job = panel.job
    vorher = len(job.Operations.Group)
    h.pruefe(panel.accept() is True, f"{name}: „Anlegen“ ging nicht")
    yield 3000
    neue = list(job.Operations.Group)[vorher:]
    namen = [o.Label for o in neue]
    print(ascii(f"{name}: {namen}"))
    h.pruefe(any(n.startswith("Räumen") for n in namen), f"{name}: kein Räumen in {namen}")
    for soll in ("Nut T3", "Messstopp", "Wände schlichten T1"):
        h.pruefe(soll in namen, f"{name}: „{soll}“ fehlt in {namen}")
    if "Messstopp" in namen and "Wände schlichten T1" in namen:
        # Schruppen – messen – schlichten: alles Schruppen (auch die Kontur) vor dem Messstopp.
        h.pruefe(
            namen.index("Messstopp") == namen.index("Wände schlichten T1") - 1
            and namen.index("Wände schlichten T1") == len(namen) - 1,
            f"{name}: Folge {namen}",
        )
    schlichten = next((o for o in neue if o.Label == "Wände schlichten T1"), None)
    if name == "rund" and schlichten is not None:
        waende = list(getattr(schlichten, "Flaechen", []) or [])
        h.pruefe("Face1" not in waende, f"rund: Mantel geschlichtet: {waende}")
    FreeCAD.closeDocument(doc.Name)
    yield 500


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine
    from camaddon import maschinenspeicher as ms
    from camaddon import werkzeuge as wz

    wz.Bibliothek(wz.testkiste()).speichern()
    ms.speichern([])
    ordner = tempfile.mkdtemp()
    asm, _maschine = beispielmaschine.lade(beispielmaschine.FRAESE_3)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    asm.Document.saveAs(os.path.join(ordner, "Fraese.FCStd"))
    yield 300
    Gui.activateWorkbench("CAMWorkbench")
    yield from _ein_rohteil(h, ordner, "platte", _rohteil_platte)
    yield from _ein_rohteil(h, ordner, "rund", _rohteil_rund)
