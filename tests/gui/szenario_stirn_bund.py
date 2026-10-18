# Manuels Messspitzenhalter-Oberteil (2026-10-18, abends, mit Bildern): Drehteil Ø 33 auf der
# CLX550, vorn ein Bund Ø 15, 0,8 hoch, dahinter die Ringfläche mit drei Bohrungen und außen ein
# schmaler Rand; Stange Ø 33 (= Fertigmaß), Planaufmaß 0. Manuel: „was will er da rundum schruppen
# ??? und schlichten ??? is doch quatsch das teil hat aussen durchmesser schon den richtigen“ und
# „beim planfräsen kann ich irgendwie nicht auswählen welchen fräser ich nehmen möchte ... es wird
# mir der 6er vorgeschlagen aber es is ja auch ein 12er im magazin“ – dabei hieß es „Über den
# gewählten Flächen steht nichts“.
# Soll: 4-Achs-Assistent, Schritt 2 – „Rundum schruppen“ und „Rundum schlichten“ gehen aus, grau
# steht „Außen steht nichts: Die Stange hat schon Fertigmaß“ mit dem Verweis zu „Bearbeitung“ von
# vorn; dort, die Ringfläche gewählt: der axiale Ø 12 (T3) kommt zwischen Bund und Rand nicht
# hinein – der Satz sagt das (nicht „steht nichts“) und bietet T4 Ø 6 an; „übernehmen“: Planfräsen
# oder Räumen mit T4 rechnet, „Anlegen“ geht, die Operation nimmt die 0,8 mm.
# ZEITLIMIT: 900
import os
import tempfile

import FreeCAD
import FreeCADGui as Gui
import Part


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500
    from camaddon import beispielmaschine, gui_bearbeitung, gui_vierachs
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    bibliothek = wz.Bibliothek()
    radial = bibliothek.neuer_halter("vdi30_radial")
    axial = bibliothek.neuer_halter("vdi30_axial")
    t1 = bibliothek.neues_werkzeug()
    t1.nummer, t1.name, t1.durchmesser, t1.schneiden = 1, "494W D12", 12.0, 4
    t1.schneidenlaenge, t1.laenge_spindelnase, t1.halter = 26.0, 110.0, radial.kennung
    t1.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=5.4, ap=22, vc=150, fz=0.07)]
    t2 = bibliothek.neues_werkzeug()
    t2.nummer, t2.name, t2.art, t2.durchmesser, t2.schneiden = (
        2,
        "207125 D12",
        wz.KUGELFRAESER,
        12.0,
        2,
    )
    t2.schneidenlaenge, t2.laenge_spindelnase, t2.halter = 20.0, 110.0, radial.kennung
    t2.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHLICHTEN, ae=0.5, ap=1, vc=200, fz=0.05)]
    t3 = bibliothek.neues_werkzeug()
    t3.nummer, t3.name, t3.durchmesser, t3.schneiden = 3, "494W D12", 12.0, 4
    t3.schneidenlaenge, t3.laenge_spindelnase, t3.halter = 26.0, 110.0, axial.kennung
    t3.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=5.4, ap=22, vc=150, fz=0.07)]
    t4 = bibliothek.neues_werkzeug()
    t4.nummer, t4.name, t4.durchmesser, t4.schneiden = 4, "494W D6", 6.0, 4
    t4.schneidenlaenge, t4.laenge_spindelnase, t4.halter = 13.0, 100.0, axial.kennung
    t4.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=2.7, ap=11, vc=150, fz=0.04)]
    bibliothek.speichern()

    asm, _maschine = beispielmaschine.lade(beispielmaschine.DREHMASCHINE)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    yield 300
    ordner = tempfile.mkdtemp()
    asm.Document.saveAs(os.path.join(ordner, "clx.FCStd"))
    yield 300

    doc = FreeCAD.newDocument("Oberteil")
    V = FreeCAD.Vector
    form = Part.makeCylinder(16.5, 19.2, V(0, 0, -20))
    form = form.fuse(Part.makeCylinder(7.5, 0.8, V(0, 0, -0.8)))
    # ein Rand außen, 0,3 hoch: die Ringfläche ist eingeschlossen (so sieht Manuels Teil aus)
    rand = Part.makeCylinder(16.5, 0.3, V(0, 0, -0.8)).cut(
        Part.makeCylinder(15.5, 0.3, V(0, 0, -0.8))
    )
    form = form.fuse(rand)
    form = form.cut(Part.makeCylinder(4.0, 30, V(0, 0, -25)))
    import math

    for k in range(3):
        a = math.radians(90 + 120 * k)
        form = form.cut(Part.makeCylinder(2.5, 12, V(11.5 * math.cos(a), 11.5 * math.sin(a), -12)))
    teil = doc.addObject("Part::Feature", "Oberteil")
    teil.Shape = form.removeSplitter()
    doc.recompute()
    Gui.activateWorkbench("CAMWorkbench")
    vorn = ring = None
    for i, f in enumerate(teil.Shape.Faces):
        if not vr.ist_eben(f) or (vr.aussennormale(f) - V(0, 0, 1)).Length > 1e-9:
            continue
        if abs(f.BoundBox.ZMin) < 1e-6:
            vorn = f"Face{i + 1}"
        elif abs(f.BoundBox.ZMin + 0.8) < 1e-6:
            ring = f"Face{i + 1}"
    print(ascii(f"vorn {vorn}, Ring {ring}"))
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, vorn)
    yield 500
    Gui.runCommand("CamAddon_Vierachs")
    yield 1500
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    panel.feld_stange.setText("33")
    panel.feld_stange.editingFinished.emit()
    panel.felder_laenge["planaufmass"].setText("0")
    panel.felder_laenge["planaufmass"].editingFinished.emit()
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 3000)
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    yield 500
    print(ascii(f"Urteil: {panel.urteil.text()!r}"))
    h.bild("1_schritt1", panel.form)
    panel.knopf_weiter.click()
    yield 500
    yield from h.warte_auf(lambda: not panel.rechnet_noch(), 180000)
    yield 800
    # Die Haken gingen heraus (vierachs_flaechen.rundum_nichts: Der radiale Ø 12 kommt zwischen
    # Bund und Rand nicht hinein, die Spirale führe nur durch die Luft) – ohne Haken rechnet
    # keine Vorschau mehr; der Assistent merkt sich den Grund.
    yield from h.warte_auf(lambda: not panel.rechnet_noch(), 180000)
    yield 300
    print(ascii(f"umsonst: {panel._rundum_umsonst!r} bei {panel._umsonst_bei!r}"))
    h.pruefe(panel._rundum_umsonst == "nichts", f"Grund: {panel._rundum_umsonst!r}")
    h.pruefe(
        not panel.mit_schruppen.isChecked() and not panel.mit_schlichten.isChecked(),
        f"Rundum an: Schruppen {panel.mit_schruppen.isChecked()}, Schlichten {panel.mit_schlichten.isChecked()}",
    )
    h.pruefe(
        "Fertigmaß" in panel.erklaerung_schruppen.text()
        and 'href="bearbeitung:' in panel.erklaerung_schruppen.text()
        and "Fertigmaß" in panel.erklaerung_schlichten.text(),
        f"grau: {panel.erklaerung_schruppen.text()!r} / {panel.erklaerung_schlichten.text()!r}",
    )
    h.bild("2_schritt2_umsonst", panel.form)
    # Eine dickere Stange (Ø 40): Der Grund ist weg – die Haken kommen zurück, das Schruppen
    # rechnet Lagen; zurück auf Ø 33 gehen sie wieder heraus.
    panel.knopf_zurueck.click()
    yield 500
    panel.feld_stange.setText("40")
    panel.feld_stange.editingFinished.emit()
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 3000)
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    yield 500
    panel.knopf_weiter.click()
    yield 500
    yield from h.warte_auf(lambda: not panel.rechnet_noch(), 180000)
    yield 800
    yield from h.warte_auf(lambda: panel.vorschau is not None and not panel.rechnet_noch(), 180000)
    yield 300
    print(ascii(f"Ø 40: Schruppen {panel.mit_schruppen.isChecked()} – {panel.ergebnis.text()!r}"))
    h.pruefe(
        panel.mit_schruppen.isChecked()
        and panel.mit_schlichten.isChecked()
        and panel._rundum_umsonst == ""
        and "Lage" in panel.ergebnis.text()
        and "Fertigmaß" not in panel.erklaerung_schruppen.text(),
        f"Ø 40: Schruppen {panel.mit_schruppen.isChecked()}, Schlichten "
        f"{panel.mit_schlichten.isChecked()}, Grund {panel._rundum_umsonst!r}, "
        f"{panel.ergebnis.text()!r}, {panel.erklaerung_schruppen.text()!r}",
    )
    panel.knopf_zurueck.click()
    yield 500
    panel.feld_stange.setText("33")
    panel.feld_stange.editingFinished.emit()
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 3000)
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    yield 500
    panel.knopf_weiter.click()
    yield 500
    yield from h.warte_auf(lambda: not panel.rechnet_noch(), 180000)
    yield 800
    yield from h.warte_auf(lambda: not panel.rechnet_noch(), 180000)
    yield 300
    h.pruefe(
        not panel.mit_schruppen.isChecked()
        and not panel.mit_schlichten.isChecked()
        and panel._rundum_umsonst == "nichts",
        f"wieder Ø 33: Schruppen {panel.mit_schruppen.isChecked()}, Schlichten "
        f"{panel.mit_schlichten.isChecked()}, Grund {panel._rundum_umsonst!r}",
    )
    # Von Hand wieder an: Der Assistent lässt den Haken (keine Bevormundung) – und die Zeile
    # sagt „nichts wegzunehmen“, nicht „1 Lage (Ø 33,0 mm → Ø 15,6 mm)“.
    panel.mit_schruppen.setChecked(True)
    yield 300
    yield from h.warte_auf(lambda: panel.vorschau is not None and not panel.rechnet_noch(), 180000)
    yield 300
    h.pruefe(panel.mit_schruppen.isChecked(), "von Hand angehakt – wieder weg")
    h.pruefe("nichts wegzunehmen" in panel.ergebnis.text(), f"Lagen: {panel.ergebnis.text()!r}")
    panel.mit_schruppen.setChecked(False)
    yield 300
    print(ascii(f"Schruppen an: {panel.mit_schruppen.isChecked()} – {panel.ergebnis.text()!r}"))
    print(
        ascii(
            f"Schlichten an: {panel.mit_schlichten.isChecked()} – {panel.ergebnis_schlichten.text()!r}"
        )
    )
    print(ascii(f"Erklärung Schruppen: {panel.erklaerung_schruppen.text()!r}"))
    print(ascii(f"axial: {panel.axial_hinweis.text()!r}"))
    print(ascii(f"rot: {panel.hinweis_bearbeitung.text()!r}"))
    h.bild("2_schritt2", panel.form)
    job_name = panel.job.Name
    link = panel.axial_hinweis.text().split('href="', 1)[1].split('"', 1)[0]
    panel.axial_hinweis.linkActivated.emit(link)
    yield from h.warte_auf(
        lambda: getattr(gui_bearbeitung.BearbeitungPanel.offen, "job", None) is not None, 20000
    )
    yield 1500
    dialog = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(dialog is not None, "„Bearbeitung“ nicht offen")
    if dialog is None:
        return
    print(
        ascii(f"Bearbeitung gewählt: {dialog.gewaehlte}, Job {dialog.job.Name} (Stange {job_name})")
    )
    if dialog.knopf_weiter.isEnabled() and dialog.knopf_weiter.isVisible():
        dialog.knopf_weiter.click()
        yield 500
    dialog.flaeche_umschalten(ring)
    yield 500
    if vorn in dialog.gewaehlte:
        dialog.flaeche_umschalten(vorn)
        yield 500
    print(ascii(f"gewählt: {dialog.gewaehlte}"))
    yield from h.warte_auf(lambda: not dialog.vorschau_laeuft(), 300000)
    yield 1500
    yield from h.warte_auf(lambda: not dialog.vorschau_laeuft(), 300000)
    for b in dialog.bloecke:
        if b.aktiv() or b.zeit is not None or b.hinweis.text():
            fr = b.fraeser()
            print(
                ascii(
                    f"{b.s.kennung}: aktiv {b.aktiv()} Fräser {getattr(fr, 'name', None)} T{getattr(fr, 'nummer', None)}/{getattr(fr, 'magazin_nummer', None)} – {b.ergebnis.text()[:200]!r} | hinweis {b.hinweis.text()[:200]!r}"
                )
            )
            print(
                ascii(
                    f"   Liste: {[b.wahl_fraeser.itemText(i) for i in range(b.wahl_fraeser.count())]}"
                )
            )
    passt = dialog.passt_text.text()
    h.pruefe(
        "T3 Schaftfräser Ø 12 kommt nicht in" in passt and "T4 Schaftfräser Ø 6" in passt,
        f"passt: {passt!r}",
    )
    h.pruefe(
        "keinen Platz für eine Zeile" in dialog.plan.hinweis.text(),
        f"Planfräsen: {dialog.plan.hinweis.text()!r}",
    )
    print(ascii(f"passt: {passt!r}"))
    print(ascii(f"hinweis: {dialog.hinweis.text()!r}"))
    h.bild("3_bearbeitung_zu_eng", dialog.form)
    # „T4 Schaftfräser Ø 6 übernehmen“: Planfräsen oder Räumen rechnet mit T4, „Anlegen“ geht.
    h.pruefe(dialog.knopf_passt.isVisible(), "kein Knopf zum Übernehmen")
    dialog.passenden_uebernehmen()
    yield 500
    yield from h.warte_auf(lambda: not dialog.vorschau_laeuft(), 300000)
    yield 1500
    yield from h.warte_auf(lambda: not dialog.vorschau_laeuft(), 300000)
    aktive = [b for b in dialog.bloecke if b.aktiv()]
    print(
        ascii(
            f"nach Übernehmen: {[(b.s.kennung, getattr(b.fraeser(), 'nummer', None), b.ergebnis.text()[:120]) for b in aktive]}"
        )
    )
    h.pruefe(
        any(
            b.s.kennung in ("planfraesen", "raeumen") and b.fraeser().durchmesser == 6.0 and b.zeit
            for b in aktive
        ),
        f"mit T4: {[(b.s.kennung, b.zeit) for b in aktive]}",
    )
    if dialog.knopf_weiter.isEnabled() and dialog.knopf_weiter.isVisible():
        dialog.knopf_weiter.click()
        yield 800
    h.pruefe(dialog._kann_anlegen(), f"„Anlegen“ geht nicht: {dialog.hinweis.text()!r}")
    vorher = len(dialog.job.Operations.Group)
    h.pruefe(dialog.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    neue = list(dialog.job.Operations.Group)[vorher:]
    namen = [o.Label for o in neue]
    print(ascii(f"Operationen: {namen}"))
    h.pruefe(any("T4" in n for n in namen), f"keine Operation mit T4: {namen}")
    for o in neue:
        if o.Label.startswith(("Planfräsen", "Räumen")):
            zs = [
                c.Parameters["Z"] for c in o.Path.Commands if c.Name == "G1" and "Z" in c.Parameters
            ]
            h.pruefe(
                zs and abs(min(zs) + 0.8) < 0.05, f"{o.Label}: tiefstes Z {min(zs) if zs else None}"
            )
    from camaddon import materialstand as mst

    stand = mst.fuer(dialog.job)
    if stand is not None:
        import numpy as np

        hh = stand.quader.h
        print(
            ascii(
                f"Materialstand: z {stand.quader.z_von}..{stand.quader.z_bis}, h max {np.nanmax(hh[np.isfinite(hh)]) if np.isfinite(hh).any() else None}, Zellen mit Material {int(np.isfinite(hh).sum())}"
            )
        )
    else:
        print("Materialstand: None")
    rohteil = dialog.job.Stock
    print(
        ascii(
            f"Rohteil: {rohteil.Name} {rohteil.TypeId} {rohteil.Shape.BoundBox} Placement {rohteil.Placement}"
        )
    )
    print(ascii(f"Modell: {dialog.job.Model.Group[0].Shape.BoundBox}"))
