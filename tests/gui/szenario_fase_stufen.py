# Der Block „Fase“ (W-037) an Manuels Messspitzenhalter-Oberteil (nachgebaut wie in
# szenario_stirn_bund): vorn der Bund Ø 15 0,8 hoch, der Ringgrund bei −0,8 bis Ø 31,8, außen die
# Fase 45° hinauf bis Ø 33 bei −0,2. Manuel, 2026-10-24 (Frage 1): „A wenns einen gibt … genau
# wenn sie angeklickt ist und man nur einen schaftfräser hat dann muss der das in stufen machen ...
# wenn nicht wird sie nicht gemacht .. wenn in der werkzeugverwaltung ein fasenfräser ist .. sollte
# man fragen .. hey willst du den haben ?“ In der Werkzeugverwaltung: T3 Ø 12 und T4 Ø 6 axial,
# dazu T6, ein Fasenfräser 90° Ø 10.
# Soll: „Alles aus dieser Aufspannung“ nimmt die Fase nicht mit – darunter die Zeile „Ohne die
# Fasen …“ mit dem Knopf „Fasen dazu“; kein 3D-Block, kein Block „Fase“ angehakt. „Fasen dazu“: Die
# Fase steht in der Liste („Fase 45°, 0,6 breit“), der Block „Fase“ ist angehakt mit T4 – dem Fräser
# der Nut daneben – in Stufen, 13 Lagen; darunter die Frage nach T6 mit dem Knopf „T6 nehmen“; die
# Nut bleibt mit T4. Nur die Fase angeklickt: keine Nut, kein 3D; der Block „Fase“ mit T4 (T3 Ø 12
# kommt neben dem Bund nicht heran), 13 Lagen. Ring und Fase, „T6
# nehmen“: eine Lage. „Anlegen“: „Fase T6“ hinter der Nut – die Spitze auf −0,8, die Achse auf
# r 15,65 (Kegel 90° auf der Fase). Zum Ändern geöffnet bleibt T6.
# ZEITLIMIT: 900
import math
import os
import tempfile

import FreeCAD
import FreeCADGui as Gui
import Part


def _liste(dialog):
    return [dialog.flaechen_liste.item(i).text() for i in range(dialog.flaechen_liste.count())]


def _bloecke(dialog):
    return {
        b.s.kennung: (
            getattr(b.fraeser(), "nummer", None),
            b.ergebnis.text()[:160],
            b.hinweis.text()[:160],
        )
        for b in dialog.bloecke
        if b.aktiv()
    }


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
    t3 = bibliothek.neues_werkzeug()
    t3.nummer, t3.name, t3.durchmesser, t3.schneiden = 3, "494W D12", 12.0, 4
    t3.schneidenlaenge, t3.laenge_spindelnase, t3.halter = 26.0, 110.0, axial.kennung
    t3.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=5.4, ap=22, vc=150, fz=0.07)]
    t4 = bibliothek.neues_werkzeug()
    t4.nummer, t4.name, t4.durchmesser, t4.schneiden = 4, "494W D6", 6.0, 4
    t4.schneidenlaenge, t4.laenge_spindelnase, t4.halter = 13.0, 100.0, axial.kennung
    t4.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=2.7, ap=11, vc=150, fz=0.04)]
    t6 = bibliothek.neues_werkzeug()
    t6.nummer, t6.name, t6.art, t6.durchmesser, t6.schneiden = (
        6,
        "Fase 90",
        wz.FASENFRAESER,
        10.0,
        2,
    )
    t6.spitzenwinkel, t6.spitzen_d = 90.0, 0.5
    t6.schneidenlaenge, t6.laenge_spindelnase, t6.halter = 5.0, 90.0, axial.kennung
    t6.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.FASEN, vc=100, fz=0.03)]
    bibliothek.speichern()

    asm, _maschine = beispielmaschine.lade(beispielmaschine.DREHMASCHINE)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    yield 300
    ordner = tempfile.mkdtemp()
    asm.Document.saveAs(os.path.join(ordner, "clx.FCStd"))
    yield 300

    doc = FreeCAD.newDocument("Oberteil")
    V = FreeCAD.Vector
    profil = [(4.25, -20.2), (16.5, -20.2), (16.5, -0.2), (15.9, -0.8), (7.5, -0.8), (7.5, 0.0)]
    profil += [(4.25, 0.0), (4.25, -20.2)]
    flaeche = Part.Face(Part.makePolygon([V(r, 0, z) for r, z in profil]))
    form = Part.Solid(Part.Shell(flaeche.revolve(V(0, 0, 0), V(0, 0, 1), 360).Faces))
    for w in (90, 210, 330):
        x, y = 10 * math.cos(math.radians(w)), 10 * math.sin(math.radians(w))
        form = form.cut(Part.makeCylinder(1.25, 11, V(x, y, -11.8)))
        form = form.cut(Part.makeCone(1.25, 2.0, 0.75, V(x, y, -1.55)))
    teil = doc.addObject("Part::Feature", "Oberteil")
    teil.Shape = form.removeSplitter()
    doc.recompute()
    Gui.activateWorkbench("CAMWorkbench")
    vorn = ring = fase = None
    for i, f in enumerate(teil.Shape.Faces):
        if isinstance(f.Surface, Part.Cone) and abs(f.BoundBox.ZMax + 0.2) < 1e-6:
            fase = f"Face{i + 1}"
        if not vr.ist_eben(f) or (vr.aussennormale(f) - V(0, 0, 1)).Length > 1e-9:
            continue
        if abs(f.BoundBox.ZMin) < 1e-6:
            vorn = f"Face{i + 1}"
        elif abs(f.BoundBox.ZMin + 0.8) < 1e-6:
            ring = f"Face{i + 1}"
    print(ascii(f"vorn {vorn}, Ring {ring}, Fase {fase}"))
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
    panel.knopf_weiter.click()
    yield 500
    yield from h.warte_auf(lambda: not panel.rechnet_noch(), 180000)
    yield 800
    yield from h.warte_auf(lambda: not panel.rechnet_noch(), 180000)
    yield 300
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
    if dialog.knopf_weiter.isEnabled() and dialog.knopf_weiter.isVisible():
        dialog.knopf_weiter.click()
        yield 500

    def rechnen():
        yield from h.warte_auf(lambda: not dialog.vorschau_laeuft(), 300000)
        yield 1500
        yield from h.warte_auf(lambda: not dialog.vorschau_laeuft(), 300000)
        yield 300

    def waehlen(namen):
        for n in list(dialog.gewaehlte):
            dialog.flaeche_umschalten(n)
            yield 200
        for n in namen:
            dialog.flaeche_umschalten(n)
            yield 200
        yield from rechnen()

    # 1. „Alles aus dieser Aufspannung“: ohne die Fase, die Zeile bietet sie an.
    dialog.aus_der_aufspannung()
    yield 1500
    yield from rechnen()
    aktiv = _bloecke(dialog)
    print(ascii(f"Alles: {dialog.gewaehlte} – {aktiv}"))
    h.pruefe(
        fase not in dialog.gewaehlte and ring in dialog.gewaehlte, f"Alles: {dialog.gewaehlte}"
    )
    zeilen = [
        w.text()
        for w in dialog.richtungen_box.findChildren(gui_bearbeitung.QtGui.QLabel)
        if w.isVisible()
    ]
    knoepfe = [
        k
        for k in dialog.richtungen_box.findChildren(gui_bearbeitung.QtGui.QPushButton)
        if k.isVisible() and k.text() == "Fasen dazu"
    ]
    h.pruefe(
        any("Ohne die Fasen" in z and fase in z for z in zeilen) and knoepfe,
        f"keine Zeile zur Fase: {zeilen}",
    )
    h.pruefe(not ({"schruppen3d", "schlichten3d", "fase"} & set(aktiv)), f"Alles angehakt: {aktiv}")
    h.pruefe(aktiv.get("nut", (None,))[0] == 4, f"Nut: {aktiv.get('nut')}")
    h.bild("1_alles_ohne_fase", dialog.form)

    # 2. „Fasen dazu“: der Block „Fase“ mit T4 in Stufen, die Frage nach T6.
    if knoepfe:
        knoepfe[0].click()
        yield 500
        yield from rechnen()
    aktiv = _bloecke(dialog)
    print(ascii(f"Fasen dazu: {_liste(dialog)} – {aktiv}"))
    h.pruefe(fase in dialog.gewaehlte, f"Fase nicht dazu: {dialog.gewaehlte}")
    h.pruefe(
        any(z.startswith(fase) and "Fase 45°" in z and "0,6 breit" in z for z in _liste(dialog)),
        f"Liste: {_liste(dialog)}",
    )
    h.pruefe(
        aktiv.get("fase", (None,))[0] == 4 and "13 Lagen" in aktiv.get("fase", (0, ""))[1],
        f"Fase: {aktiv.get('fase')}",
    )
    h.pruefe(aktiv.get("nut", (None,))[0] == 4, f"Nut: {aktiv.get('nut')}")
    h.pruefe(not ({"schruppen3d", "schlichten3d"} & set(aktiv)), f"3D angehakt: {aktiv}")
    frage = dialog.fase.angebot
    h.pruefe(
        "T6" in frage.text() and [k.text() for k in frage.knoepfe()] == ["T6 nehmen"],
        f"Frage nach T6: {frage.text()!r} {[k.text() for k in frage.knoepfe()]}",
    )
    h.bild("2_fasen_dazu_t4_stufen", dialog.form)

    # 3. Nur die Fase: keine Nut, kein 3D; T3 Ø 12 kommt neben dem Bund nicht heran – vorgewählt
    # ist T4 (fase_bahn.fraeser_passt), sonst böte „T4 nehmen“ ihn an.
    dialog.fase.fraeser_von_hand = False
    yield from waehlen([fase])
    aktiv = _bloecke(dialog)
    print(ascii(f"nur Fase: {aktiv} | {frage.text()!r}"))
    h.pruefe(set(aktiv) == {"fase"}, f"nur Fase angehakt: {aktiv}")
    kleiner = [k for k in frage.knoepfe() if k.text() == "T4 nehmen"]
    if aktiv.get("fase", (None,))[0] == 3 and kleiner:
        h.bild("3_nur_fase_t3", dialog.form)
        kleiner[0].click()
        yield 500
        yield from rechnen()
        aktiv = _bloecke(dialog)
    h.pruefe(
        aktiv.get("fase", (None,))[0] == 4 and "13 Lagen" in aktiv.get("fase", (0, ""))[1],
        f"nur Fase mit T4: {aktiv.get('fase')}",
    )
    h.bild("3_nur_fase", dialog.form)

    # 4. Ring und Fase, „T6 nehmen“: eine Lage; „Anlegen“.
    dialog.fase.fraeser_von_hand = False
    yield from waehlen([ring, fase])
    knopf_t6 = [k for k in frage.knoepfe() if k.text() == "T6 nehmen"]
    h.pruefe(bool(knopf_t6), f"kein „T6 nehmen“: {frage.text()!r}")
    if knopf_t6:
        knopf_t6[0].click()
        yield 500
        yield from rechnen()
    aktiv = _bloecke(dialog)
    print(ascii(f"Ring+Fase mit T6: {aktiv}"))
    h.pruefe(
        aktiv.get("fase", (None,))[0] == 6 and "1 Lage" in aktiv.get("fase", (0, ""))[1],
        f"Fase mit T6: {aktiv.get('fase')}",
    )
    h.pruefe(aktiv.get("nut", (None,))[0] == 4, f"Nut: {aktiv.get('nut')}")
    h.bild("4_ring_fase_t6", dialog.form)
    if dialog.knopf_weiter.isEnabled() and dialog.knopf_weiter.isVisible():
        dialog.knopf_weiter.click()
        yield 800
    h.pruefe(dialog._kann_anlegen(), f"„Anlegen“ geht nicht: {dialog.hinweis.text()!r}")
    job = dialog.job
    vorher = len(job.Operations.Group)
    h.pruefe(dialog.accept() is True, "„Anlegen“ ging nicht")
    yield 3000
    neue = list(job.Operations.Group)[vorher:]
    namen = [o.Label for o in neue]
    print(ascii(f"Operationen: {namen}"))
    op = next((o for o in neue if o.Label.startswith("Fase")), None)
    h.pruefe(op is not None and op.Label == "Fase T6", f"keine „Fase T6“: {namen}")
    h.pruefe(
        op is not None
        and namen.index(op.Label) > max(i for i, n in enumerate(namen) if n.startswith("Nut")),
        f"Fase nicht hinter der Nut: {namen}",
    )
    if op is not None:
        tief = [
            math.hypot(c.Parameters["X"], c.Parameters["Y"])
            for c in op.Path.Commands
            if c.Name in ("G1", "G2", "G3")
            and "X" in c.Parameters
            and "Y" in c.Parameters
            and abs(c.Parameters.get("Z", 99) + 0.8) < 0.01
        ]
        zs = [c.Parameters["Z"] for c in op.Path.Commands if c.Name == "G1" and "Z" in c.Parameters]
        print(
            ascii(
                f"Fase T6: r {min(tief or [0]):.3f}..{max(tief or [0]):.3f}, Z {min(zs or [0]):.3f}"
            )
        )
        h.pruefe(zs and abs(min(zs) + 0.8) < 0.01, f"tiefstes Z {min(zs) if zs else None}")
        h.pruefe(
            tief and abs(max(tief) - 15.65) < 0.02, f"Achse nicht auf r 15,65: {max(tief or [0])}"
        )
    Gui.Selection.clearSelection()
    for o in doc.Objects:
        if o.ViewObject is not None:
            o.ViewObject.Visibility = o is teil
    if op is not None and op.ViewObject is not None:
        op.ViewObject.Visibility = True
    Gui.getDocument(doc.Name).activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    yield 800
    h.bild("5_fase_t6_bahn")

    # Zum Ändern geöffnet: Der Block „Fase“ behält T6 – auch wenn T6 nicht im Magazin steht (sonst
    # tauschte der Assistent ihn gegen den Schaftfräser).
    if op is not None:
        gui_bearbeitung.bearbeiten(op)
        yield 1500
        aendern = gui_bearbeitung.BearbeitungPanel.offen
        h.pruefe(aendern is not None, "„Fase T6“ öffnet nicht zum Ändern")
        if aendern is not None:
            yield from h.warte_auf(lambda: aendern.fase.vorschau is not None, 120000)
            yield 800
            werkzeug = aendern.fase.fraeser()
            h.pruefe(
                getattr(werkzeug, "nummer", None) == 6,
                f"beim Ändern: {getattr(werkzeug, 'nummer', None)}",
            )
            h.pruefe(
                "1 Lage" in aendern.fase.ergebnis.text(),
                f"beim Ändern: {aendern.fase.ergebnis.text()!r}",
            )
            aendern.reject()
            yield 800
