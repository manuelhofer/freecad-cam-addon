# „Programm schreiben“ für Heidenhain im Klartext (P-2026-10-05-01; Manuel: „Heidenhain muss mit
# rein … vor allem iTNC 530“): ein Klotz 60 × 40 × 20 mit „Planfräsen“ oben und „Kontur“ außen auf
# der 3-Achs-Beispielfräse. Steuerung „Heidenhain iTNC 530 (Klartext)“: die Datei endet auf .h,
# die Vorschau beginnt mit „0 BEGIN PGM … MM“ und dem BLK FORM, ruft „TOOL CALL 1 Z S…“, dann
# „M3“; Geraden „L X+… R0 F…“, Ecken „CC“/„C … DR…“; links keine G-Code-Haken (G93,
# Satznummern), beim Glätten „Zyklus 32“. „Speichern“: darunter „Nachgelesen: nichts gefunden“.
# TNC 640: „FUNCTION TCPM“ statt M128 in den Befehlen.
import os
import tempfile

import FreeCAD
import FreeCADGui as Gui
import Part


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    import Path.Main.Job as PathJob

    from camaddon import beispielmaschine, gui_programm
    from camaddon import job_schnittwerte as js
    from camaddon import kontur as ko
    from camaddon import planfraesen as pf
    from camaddon import reichweite as rw
    from camaddon import uebergabe_werkzeuge as ue
    from camaddon import werkzeuge as wz

    ordner = tempfile.mkdtemp()
    asm, _maschine = beispielmaschine.lade(beispielmaschine.FRAESE_3)
    pfad_maschine = os.path.join(ordner, "fraese.FCStd")
    asm.Document.saveAs(pfad_maschine)
    yield 300
    t1 = wz.Werkzeug(nummer=1, durchmesser=10, schneiden=4, schneidenlaenge=22)
    t1.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=4.0, ap=5.0, vc=150, fz=0.05)]
    bibliothek = wz.Bibliothek([t1])
    bibliothek.speichern()
    ue.uebergeben(bibliothek)
    doc = FreeCAD.newDocument("Klotz")
    teil = doc.addObject("Part::Feature", "Klotz")
    teil.Shape = Part.makeBox(60, 40, 20)
    doc.recompute()
    FreeCAD.setActiveDocument(doc.Name)
    job = PathJob.Create("Klotz", [teil])
    doc.recompute()
    oben = next(
        f"Face{i + 1}" for i, f in enumerate(teil.Shape.Faces) if abs(f.BoundBox.ZMin - 20) < 1e-6
    )
    seiten = [
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if f.BoundBox.ZMax - f.BoundBox.ZMin > 1e-6
    ]
    tc = js.controller_ohne_transaktion(doc, job, t1, t1.einsaetze(wz.ALLE)[0])
    pf.lege_an(job, tc, 2.0, 6.0, flaechen=[oben])
    ko.lege_an(job, tc, 5.0, 4.0, flaechen=seiten)
    doc.recompute()
    rw.merke_maschine(job, pfad_maschine)
    doc.saveAs(os.path.join(ordner, "klotz.FCStd"))
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, job.Name)
    yield 300

    Gui.runCommand("CamAddon_ProgrammSchreiben")
    yield 1500
    d = gui_programm.ProgrammDialog.offen
    h.pruefe(d is not None, "„Programm schreiben“ öffnet kein Fenster")
    if d is None:
        return
    d.wahl_steuerung.setCurrentIndex(d.wahl_steuerung.findData("heidenhain"))
    yield 1000
    name = job.Label  # „Klotz001“ – das Teil heißt schon „Klotz“
    h.pruefe(d.feld_datei.text().endswith(f"{name}.h"), f"Datei: {d.feld_datei.text()!r}")
    text = d.vorschau.toPlainText()
    zeilen = text.splitlines()
    h.pruefe(
        zeilen and zeilen[0] == f"0 BEGIN PGM {name} MM" and "BLK FORM 0.1 Z" in zeilen[1],
        f"Anfang: {zeilen[:3]}",
    )
    for soll in ("TOOL CALL 1 Z S", " M3", " R0 F", " R0 FMAX", "\n", "CC X", " DR"):
        h.pruefe(soll in text, f"Klartext-Vorschau ohne {soll!r}: {text[:600]!r}")
    h.pruefe(
        not any(
            z.split(" ", 1)[1].startswith(("G0", "G1", "G2", "G3")) for z in zeilen if " " in z
        ),
        "G-Code in der Vorschau",
    )
    h.pruefe(
        "g93" not in d.haken and "satznummern" not in d.haken and "zyklus32" in d.glaetten_haken,
        f"Haken: {sorted(d.haken)}, glätten: {sorted(d.glaetten_haken)}",
    )
    h.bild("1_heidenhain", d)
    d.feld_datei.setText(os.path.join(ordner, "Klotz_OP1.h"))
    d._datei_geaendert()
    yield 800
    h.pruefe(
        d.vorschau.toPlainText().startswith("0 BEGIN PGM Klotz_OP1 MM"),
        f"Name nach der Datei: {d.vorschau.toPlainText()[:40]!r}",
    )
    pfad = d.speichern()
    yield 500
    h.pruefe(pfad is not None and os.path.exists(pfad), f"nicht gespeichert: {pfad}")
    ergebnis = d.ergebnis.text()
    h.pruefe("Nachgelesen" in ergebnis and "nichts" in ergebnis, f"Ergebnis: {ergebnis!r}")
    if pfad and os.path.exists(pfad):
        with open(pfad, encoding="utf-8") as datei:
            gespeichert = datei.read().splitlines()
        h.pruefe(gespeichert[-1].endswith("END PGM Klotz_OP1 MM"), f"Ende: {gespeichert[-2:]}")
    h.bild("2_gespeichert", d)
    d.wahl_steuerung.setCurrentIndex(d.wahl_steuerung.findData("heidenhain_tnc640"))
    yield 1000
    h.pruefe(
        d.steuerung().tcpm_ein.startswith("FUNCTION TCPM"),
        f"TNC 640 TCPM: {d.steuerung().tcpm_ein!r}",
    )
    d.reject()
    yield 300
    FreeCAD.closeDocument(doc.Name)
    yield 300
