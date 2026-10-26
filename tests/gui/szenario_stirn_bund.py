# Manuels Messspitzenhalter-Oberteil (2026-10-18, mit Bildern; nachgebaut nach
# messpitzenhalteroberteill.FCStd): Drehteil Ø 33 auf der CLX550, vorn ein Bund Ø 15 0,8 hoch,
# der Ringgrund bis Ø 31,8, außen eine Fase 45° bis Ø 33 bei 0,2 hinter dem Bund, drei
# Senkbohrungen Ø 2,5 auf r 10; Stange Ø 33 (= Fertigmaß), Planaufmaß 0. Manuel: „was will er da
# rundum schruppen ??? und schlichten ??? is doch quatsch das teil hat aussen durchmesser schon den
# richtigen“ – und zum Planfräsen im Ring mit dem 6er: „totaler scheissdreck … einfahren wie in
# eine nut und mit wellen rauskauen und dann noch die ränder schlichten“; im Abfahren „kein abtrag
# vom rohteil“.
# Soll: 4-Achs-Assistent, Schritt 2 – „Rundum schruppen“ und „Rundum schlichten“ gehen aus, grau
# steht warum, mit dem Verweis zu „Bearbeitung“ von vorn (Ø 40: zurück; wieder Ø 33: aus; von
# Hand an bleibt an). Von vorn, die Ringfläche gewählt: „Ringnut rundum 8,4 breit“, kein
# Planfräsen, die Nut mit T4 Ø 6 (T3 Ø 12 passt nicht), kein Angebot fürs Räumen ohne Haken, kein
# „Nicht fertig“; „Anlegen“: „Nut T4“, Messstopp, „Nut schlichten T4“ (beide Ränder: r 10,5 und
# 12,9). Abfahren: Die Stange wird abgetragen – im Ring bis −0,8, der Bund bleibt.
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
    # Wie Manuels messpitzenhalteroberteill.FCStd, vorn oben: Bund Ø 15 0,8 hoch, Ringgrund bei
    # Z −0,8 bis Ø 31,8, außen eine Fase 45° bis Ø 33 bei Z −0,2, Bohrung Ø 8,5, drei
    # Senkbohrungen Ø 2,5 (Senkung Ø 4) auf r 10.
    profil = [
        (4.25, -20.2),
        (16.5, -20.2),
        (16.5, -0.2),
        (15.9, -0.8),
        (7.5, -0.8),
        (7.5, 0.0),
        (4.25, 0.0),
        (4.25, -20.2),
    ]
    flaeche = Part.Face(Part.makePolygon([V(r, 0, z) for r, z in profil]))
    form = Part.Solid(Part.Shell(flaeche.revolve(V(0, 0, 0), V(0, 0, 1), 360).Faces))
    import math

    for w in (90, 210, 330):
        x, y = 10 * math.cos(math.radians(w)), 10 * math.sin(math.radians(w))
        form = form.cut(Part.makeCylinder(1.25, 11, V(x, y, -11.8)))
        form = form.cut(Part.makeCone(1.25, 2.0, 0.75, V(x, y, -1.55)))
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
    # Der radiale Ø 12 nimmt nichts weg (oder nur eine Scheibe vor der Stirn).
    h.pruefe(panel._rundum_umsonst in ("nichts", "vor_stirn"), f"Grund: {panel._rundum_umsonst!r}")
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
        and panel._rundum_umsonst in ("nichts", "vor_stirn"),
        f"wieder Ø 33: Schruppen {panel.mit_schruppen.isChecked()}, Schlichten "
        f"{panel.mit_schlichten.isChecked()}, Grund {panel._rundum_umsonst!r}",
    )
    # Von Hand wieder an: Der Assistent lässt den Haken (keine Bevormundung).
    panel.mit_schruppen.setChecked(True)
    yield 300
    yield from h.warte_auf(lambda: panel.vorschau is not None and not panel.rechnet_noch(), 180000)
    yield 300
    h.pruefe(panel.mit_schruppen.isChecked(), "von Hand angehakt – wieder weg")
    h.pruefe(
        ("nichts wegzunehmen" if panel._rundum_umsonst == "nichts" else "Lage")
        in panel.ergebnis.text(),
        f"Lagen: {panel.ergebnis.text()!r}",
    )
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
    # Die Ringnut (Bund innen, Fase außen) ist kein Fall fürs Planfräsen (der niedrige Rand
    # galt bis 0.274.1 nicht als Wand): Die Nut tritt an – mit T4 Ø 6, der T3 Ø 12 passt nicht
    # in 8,4 mm. Kein Angebot „für Räumen passt T4 … übernehmen“ für das Räumen ohne Haken (die
    # Nut nimmt die Fläche schon), kein „Nicht fertig: Face7“ (der Grund ist auf Tiefe).
    passt = dialog.passt_text.text()
    print(ascii(f"passt: {passt!r}"))
    print(ascii(f"Ziel: {dialog.ziel_text.text()!r}"))
    print(ascii(f"unfertig: {dialog.unfertig.text() if dialog.unfertig.isVisible() else ''!r}"))
    print(ascii(f"hinweis: {dialog.hinweis.text()!r}"))
    h.bild("3_bearbeitung_ringnut", dialog.form)
    h.pruefe(not dialog.plan.aktiv(), f"Planfräsen an: {dialog.plan.hinweis.text()!r}")
    h.pruefe(
        dialog.nut.aktiv() and getattr(dialog.nut.fraeser(), "durchmesser", None) == 6.0,
        f"Nut {dialog.nut.aktiv()} mit {getattr(dialog.nut.fraeser(), 'name', None)}: "
        f"{dialog.nut.hinweis.text()!r}",
    )
    h.pruefe(not dialog.knopf_passt.isVisible() and not passt, f"Angebot: {passt!r}")
    h.pruefe("T4" in dialog.ziel_text.text(), f"Ziel: {dialog.ziel_text.text()!r}")
    h.pruefe(not dialog.unfertig.isVisible(), f"unfertig: {dialog.unfertig.text()!r}")
    aktive = [b for b in dialog.bloecke if b.aktiv()]
    print(
        ascii(
            f"angehakt: {[(b.s.kennung, getattr(b.fraeser(), 'nummer', None), b.ergebnis.text()[:120]) for b in aktive]}"
        )
    )
    h.pruefe(
        any(b.s.kennung == "nut" and b.fraeser().durchmesser == 6.0 and b.zeit for b in aktive),
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
    # „Nut schlichten“: beide Ränder der Ringnut – der Bund (Mitte des Fräsers r 10,5) und der
    # Fuß der Fase (r 12,9); die Kontur fuhr bis 0.274.1 nur den Bund.
    import math as m_

    schlichten_ = next((o for o in neue if o.Label.startswith("Nut schlichten")), None)
    h.pruefe(schlichten_ is not None, f"kein „Nut schlichten“: {namen}")
    if schlichten_ is not None:
        radien_ = [
            m_.hypot(c.Parameters["X"], c.Parameters["Y"])
            for c in schlichten_.Path.Commands
            if c.Name in ("G1", "G2", "G3")
            and "X" in c.Parameters
            and "Y" in c.Parameters
            and abs(c.Parameters.get("Z", -0.8) + 0.8) < 0.01
        ]
        print(ascii(f"Nut schlichten: r {min(radien_):.3f}..{max(radien_):.3f}"))
        h.pruefe(
            radien_ and abs(min(radien_) - 10.5) < 0.02 and abs(max(radien_) - 12.9) < 0.02,
            f"Nut schlichten: r {min(radien_) if radien_ else None}..{max(radien_) if radien_ else None}",
        )
    for o in neue:
        if o.Label.startswith(("Nut", "Räumen")):
            zs = [
                c.Parameters["Z"] for c in o.Path.Commands if c.Name == "G1" and "Z" in c.Parameters
            ]
            h.pruefe(
                zs and abs(min(zs) + 0.8) < 0.05, f"{o.Label}: tiefstes Z {min(zs) if zs else None}"
            )
    # Abfahren: Die Stange wird von vorn abgetragen (bis 0.274.1 blieb sie unberührt, Manuel:
    # „kein abtrag vom rohteil“) – im Ring bis −0,8, der Bund bleibt, außen steht nichts.
    from PySide import QtCore, QtGui

    from camaddon import gui_reichweite

    job = dialog.job
    FreeCAD.setActiveDocument(job.Document.Name)
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 400
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None, 60000)
    pruef = gui_reichweite.PruefPanel.offen
    h.pruefe(pruef is not None, "„Auf der Maschine prüfen“ öffnet kein Fenster")
    if pruef is not None:
        yield 800
        abtrag = getattr(getattr(pruef, "bild", None), "abtrag", None)
        h.pruefe(
            abtrag is not None
            and getattr(getattr(abtrag, "quader", None), "anfang", None) is not None,
            f"Abtrag: {type(abtrag).__name__}",
        )
        spieler = pruef.abspieler
        fahrt = spieler.abfahrt
        stationen = [s_ for s_ in fahrt.stationen if not s_.eilgang]
        if stationen:
            spieler.setze_zeit(stationen[len(stationen) // 3].zeit)
            yield from h.warte_auf(lambda: not pruef.bild.abtrag_rechnet(), 60000)
            yield 500
            h.bild("4_abfahren_mittendrin")
        spieler.setze_zeit(fahrt.dauer)
        yield from h.warte_auf(lambda: not pruef.bild.abtrag_rechnet(), 120000)
        yield 800
        rest = spieler.rest.text()
        print(ascii(f"Abfahren am Ende: {rest!r}"))
        if abtrag is not None and hasattr(abtrag, "quader"):
            import numpy as np

            q = abtrag.quader
            X, Y = np.meshgrid(q.x, q.y, indexing="ij")
            r = np.hypot(X, Y)
            ring_ = (r > 9.0) & (r < 14.0) & (np.hypot(X, Y + 10.0) > 2.5)
            ring_ &= np.hypot(X - 8.66, Y - 5.0) > 2.5
            ring_ &= np.hypot(X + 8.66, Y - 5.0) > 2.5
            bund_ = (r > 4.6) & (r < 7.0)
            print(
                ascii(
                    f"Ring h {q.h[ring_].min():.3f}..{q.h[ring_].max():.3f}, Bund h "
                    f"{q.h[bund_].min():.3f}..{q.h[bund_].max():.3f}, außen {q.h[r > 17].max():.1f}"
                )
            )
            vergleich_ = abtrag.vergleich()
            np.savez(
                os.path.join(os.environ["CAMADDON_AUSGABE"], "abfahren_ende.npz"),
                x=q.x,
                y=q.y,
                h=q.h,
                farbe=vergleich_.farbe,
            )
            h.pruefe(
                abs(q.h[ring_].max() + 0.8) < 0.05 and abs(q.h[bund_].min()) < 0.05,
                f"Ring h {q.h[ring_].min():.3f}..{q.h[ring_].max():.3f}, Bund {q.h[bund_].min():.3f}",
            )
        Gui.SendMsgToActiveView("ViewFit")
        spieler.knopf_hinsehen.click()
        yield 500
        h.bild("5_abfahren_am_ende")
        pruef.reject()
        yield 500
    # „Programm schreiben“ mit TRANSMIT (Manuel, 2026-10-26: die CLX550 hat es): die Nut an der
    # Stirnseite in X und Y, X im Radius (DIAMOF), davor TRANSMIT und G17, danach TRAFOOF.
    from camaddon import gui_programm

    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(job)
    yield 300
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_ProgrammSchreiben"))
    yield from h.warte_auf(lambda: gui_programm.ProgrammDialog.offen is not None, 60000)
    d = gui_programm.ProgrammDialog.offen
    h.pruefe(d is not None, "„Programm schreiben“ öffnet kein Fenster")
    if d is None:
        return
    d.wahl_steuerung.setCurrentIndex(d.wahl_steuerung.findData("siemens"))
    yield 800
    haken_t = d.haken.get("transmit")
    h.pruefe(haken_t is not None, "kein Haken „Stirnseite mit TRANSMIT“")
    if haken_t is not None:
        haken_t.setChecked(True)
        yield 1500
        text = d.vorschau.toPlainText().splitlines()
        k = text.index("TRANSMIT") if "TRANSMIT" in text else -1
        h.pruefe(
            k > 0 and text[k - 1] == "DIAMOF" and text[k + 1] == "G17",
            f"Vorschau ohne TRANSMIT: {text[:60]}",
        )
        if k > 0:
            d.vorschau.moveCursor(QtGui.QTextCursor.End)
            cursor = d.vorschau.textCursor()
            cursor.setPosition(
                d.vorschau.document().findBlockByLineNumber(max(0, k - 8)).position()
            )
            d.vorschau.setTextCursor(cursor)
            d.vorschau.ensureCursorVisible()
        d.einstellungen.ensureWidgetVisible(haken_t, 0, 200)
        yield 500
        h.bild("6_programm_transmit", d)
        haken_t.setChecked(False)
        yield 300
    d.reject()
    yield 300
