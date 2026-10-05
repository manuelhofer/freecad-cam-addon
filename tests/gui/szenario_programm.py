# „Programm schreiben“ (W-005, P-2026-10-03-10): eine Welle Ø 60 mit „Rundum schruppen T1“ auf
# der Beispiel-Drehmaschine (gespeichert, der Job merkt sie sich). Das Fenster nennt die
# Maschine – Drehmaschine, X im Durchmesser, „Hauptspindel S1, C-Achse C1“, „T1…T12 → S3 (C3)“.
# Siemens 840D: in der Vorschau „T1 D1“, „SPOS[1]=0“, „M3=3 S3=…“, die Rundachse „C1=…“. Fanuc:
# gelb der Hinweis, dass der Maschinenhersteller das angetriebene Werkzeug festlegt. Links die
# Einstellungen in Gruppen (P-2026-10-03-27): Haken mit Erklärung, bei Fanuc die Befehle zum
# Glätten aus (Optionen); „C-Achse ein“ geändert steht in der Vorschau, „Zurücksetzen“ holt die
# Vorbelegung. Siemens: G64, G642, CTOL, SOFT an, COMPCAD aus; „Satznummern“ angehakt → N10 …;
# COMPCAD angehakt → gelb, dass es eine Option sein kann. „Speichern“ schreibt die Datei, der Job merkt sich die Steuerung. Dann wie
# Manuels Drehmaschine (P-2026-10-03-25): eine zweite, nicht gespeichert, Hauptspindel S4/C4,
# angetriebene Werkzeuge S1/C1 – in der Liste „… – nicht gespeichert“; gewählt: „SPOS[4]=0“,
# „M1=3 S1=…“, „C4=…“, unter der Maschine der Satz, dass der Job sie sich erst merkt, wenn sie
# gespeichert ist.
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

    from camaddon import beispielmaschine, gui_programm
    from camaddon import job_schnittwerte as js
    from camaddon import reichweite as rw
    from camaddon import uebergabe_werkzeuge as ue
    from camaddon import vierachs_achsen as va
    from camaddon import vierachs_operation as vo
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    ordner = tempfile.mkdtemp()
    asm, _maschine = beispielmaschine.lade(beispielmaschine.DREHMASCHINE)
    pfad_maschine = os.path.join(ordner, "drehmaschine.FCStd")
    asm.Document.saveAs(pfad_maschine)
    yield 300
    meine, _ma = beispielmaschine.drehmaschine(
        beispielmaschine.DrehmaschinenMasse(
            name="Meine Drehmaschine", hauptspindel=4, werkzeugantrieb=1
        )
    )
    yield 300

    t1 = wz.Werkzeug(nummer=1, durchmesser=12, schneiden=3, schneidenlaenge=26)
    t1.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=4.8, ap=2, vc=120, fz=0.05)]
    bibliothek = wz.Bibliothek([t1])
    bibliothek.speichern()
    ue.uebergeben(bibliothek)
    doc = FreeCAD.newDocument("Welle")
    welle = doc.addObject("Part::Feature", "Welle")
    welle.Shape = Part.makeCylinder(25, 40, FreeCAD.Vector(), FreeCAD.Vector(1, 0, 0))
    doc.recompute()
    stirn = next(
        f
        for f in welle.Shape.Faces
        if vr.ist_eben(f) and (vr.aussennormale(f) - FreeCAD.Vector(1, 0, 0)).Length < 1e-9
    )
    achse = va.zugewiesen("C")
    lage = vr.berechne(welle.Shape, stirn, achse, durchmesser=60)
    job = vr.richte_ein(
        doc, welle, lage, vr.Stange(60.0, frei_hinten=50.0), achse, beschriftung="W"
    )
    tc = js.controller_ohne_transaktion(doc, job, t1, t1.einsaetze(wz.ALLE)[0])
    vo.lege_an(job, tc, achse, zustellung=2.0, steigung=4.8, aufmass=0.3)
    doc.recompute()
    rw.merke_maschine(job, pfad_maschine)
    doc.saveAs(os.path.join(ordner, "welle.FCStd"))
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, job.Name)
    yield 300

    Gui.runCommand("CamAddon_ProgrammSchreiben")
    yield 1500
    d = gui_programm.ProgrammDialog.offen
    h.pruefe(d is not None, "„Programm schreiben“ öffnet kein Fenster")
    if d is None:
        return
    maschine = d.maschine_text.text()
    h.pruefe(
        "Drehmaschine" in maschine
        and "X im Durchmesser" in maschine
        and "Hauptspindel S1, C-Achse C1" in maschine
        and "T1…T12 → S3 (C3)" in maschine
        and "C1 nach DIN 66217" in maschine,  # wie die Rundachse zählt (2026-10-05)
        f"Maschine: {maschine!r}",
    )
    eintraege = [d.wahl_maschine.itemText(k) for k in range(d.wahl_maschine.count())]
    h.pruefe(
        "Meine Drehmaschine – nicht gespeichert" in eintraege, f"Maschinen zur Wahl: {eintraege}"
    )
    d.wahl_steuerung.setCurrentIndex(d.wahl_steuerung.findData("siemens"))
    yield 800
    text = d.vorschau.toPlainText()
    for soll in ("T1 D1", "SPOS[1]=0", "M3=3 S3=", "G93", "C1="):
        h.pruefe(soll in text, f"Siemens-Vorschau ohne {soll!r}: {text[:400]!r}")
    h.bild("1_siemens", d)
    d.wahl_steuerung.setCurrentIndex(d.wahl_steuerung.findData("fanuc"))
    yield 800
    h.pruefe(
        d.hinweise.isVisible() and "Maschinenhersteller" in d.hinweise.text(),
        f"Fanuc-Hinweis: {d.hinweise.text()!r}",
    )
    h.pruefe("T0101" in d.vorschau.toPlainText(), "Fanuc: T0101 fehlt")
    haken = {"kommentare", "satznummern", "wechselpunkt", "kuehlung", "c_achse", "g93"}
    h.pruefe(haken <= set(d.haken), f"Haken: {sorted(d.haken)}")
    h.pruefe(
        set(d.glaetten_haken) == {"g08", "g051"}
        and not any(x.isChecked() for x in d.glaetten_haken.values()),
        f"Fanuc glätten: {sorted(d.glaetten_haken)}",
    )
    d.befehl_setzen("c_ein", "M18 (C EIN)")
    yield 500
    h.pruefe("M18 (C EIN)" in d.vorschau.toPlainText(), "geänderter Befehl nicht in der Vorschau")
    h.bild("2_fanuc_befehle", d)
    d.zuruecksetzen()
    yield 300
    h.pruefe("M18" not in d.vorschau.toPlainText(), "Zurücksetzen wirkt nicht")
    d.wahl_steuerung.setCurrentIndex(d.wahl_steuerung.findData("siemens"))
    yield 500
    an = sorted(k for k, x in d.glaetten_haken.items() if x.isChecked())
    h.pruefe(an == ["ctol", "g64", "g642", "soft"], f"Siemens glätten an: {an}")
    h.pruefe("CTOL=0.010" in d.vorschau.toPlainText(), "CTOL fehlt in der Vorschau")
    d.haken["satznummern"].setChecked(True)
    d.glaetten_haken["compcad"].setChecked(True)
    yield 500
    text = d.vorschau.toPlainText()
    h.pruefe("N10 G17 G71 G90 G40" in text and "COMPCAD" in text, f"Haken: {text[:300]!r}")
    h.pruefe("COMPCAD" in d.hinweise.text(), f"Hinweis COMPCAD: {d.hinweise.text()!r}")
    h.bild("2b_siemens_einstellungen", d)
    leiste = d.einstellungen.verticalScrollBar()
    leiste.setValue(leiste.maximum())
    yield 300
    h.bild("2c_siemens_glaetten", d)
    d.zuruecksetzen()
    yield 300
    h.pruefe(
        "N10" not in d.vorschau.toPlainText() and not d.haken["satznummern"].isChecked(),
        "Zurücksetzen nimmt die Satznummern nicht weg",
    )
    ziel = os.path.join(ordner, "welle.mpf")
    d.feld_datei.setText(ziel)
    gespeichert = d.speichern()
    yield 300
    h.pruefe(gespeichert == ziel and os.path.isfile(ziel), f"nicht gespeichert: {gespeichert}")
    h.pruefe(d.ergebnis.text().startswith("Gespeichert:"), f"Ergebnis: {d.ergebnis.text()!r}")
    h.pruefe(getattr(job, gui_programm.EIGENSCHAFT_STEUERUNG, "") == "siemens", "Steuerung am Job")
    with open(ziel, encoding="utf-8") as datei:
        zeilen = datei.read().splitlines()
    h.pruefe(
        zeilen[-1] == "M30" and len(zeilen) > 100, f"Datei: {len(zeilen)} Zeilen, {zeilen[-1:]}"
    )
    h.bild("3_gespeichert", d)

    # Wie Manuels Maschine: S4/C4 die Hauptspindel, S1/C1 die angetriebenen Werkzeuge.
    h.pruefe(d.maschine_waehlen("Meine Drehmaschine"), "„Meine Drehmaschine“ nicht zur Wahl")
    yield 800
    maschine = d.maschine_text.text()
    h.pruefe(
        "Hauptspindel S4, C-Achse C4" in maschine
        and "T1…T12 → S1 (C1)" in maschine
        and "speichere sie" in maschine,
        f"Meine Drehmaschine: {maschine!r}",
    )
    text = d.vorschau.toPlainText()
    for soll in ("SPOS[4]=0", "M1=3 S1=", "C4="):
        h.pruefe(soll in text, f"S4/C4-Vorschau ohne {soll!r}: {text[:400]!r}")
    h.pruefe("C1=" not in text and "C3=" not in text, "die C-Achse des Antriebs in der Bahn")
    h.pruefe(
        getattr(job, rw.EIGENSCHAFT_MASCHINE, "") == pfad_maschine,
        "ungespeicherte Maschine am Job gemerkt",
    )
    h.bild("4_meine_drehmaschine", d)
    d.reject()
    yield 300
