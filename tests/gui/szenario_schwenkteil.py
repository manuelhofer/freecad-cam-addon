# 3+2 an einem ganzen Teil (W-014): beispiele/schwenkteil_5achs.FCStd – Block 120 × 80 × 50 mit
# einer 30°-Schräge vorn (darin eine Tasche 40 × 16), einer 45°-Fläche rechts (darin eine
# Bohrung Ø 8,5) und einer Tasche oben. Auf der 5-Achs-Beispielmaschine Tisch/Tisch: der
# Grundjob räumt oben, die Ebene der Schräge räumt die Schräge und ihre Tasche, die Ebene der
# 45°-Fläche räumt sie und bohrt. Ein Programm für die Aufspannung (Siemens: zweimal CYCLE800),
# „Auf der Maschine prüfen“ fährt alles ab – Bilder je Ebene. Die Maschine hat einen
# Wechselpunkt (Z oben, wie jede echte): Der Bohrer T2 ist 34 mm länger als der Fräser T1 – ohne
# ihn wechselte sie, wo sie steht, und der Bohrer steckte im Teil (das sagt die Kollision dann).
# Zwischen den Ebenen fährt sie hoch, schwenkt und kommt von oben – nichts stößt an.
import math
import os
import tempfile

import FreeCAD
import FreeCADGui as Gui

V = FreeCAD.Vector


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    import Path.Main.Job as PathJob
    from PySide import QtCore

    from camaddon import beispielmaschine, gui_reichweite
    from camaddon import bohren as bh
    from camaddon import bohrung_bahn as bb
    from camaddon import hoehenfeld as hf
    from camaddon import job_schnittwerte as js
    from camaddon import postprozessor as pp
    from camaddon import raeumen as ra
    from camaddon import reichweite as rw
    from camaddon import schwenken as sw
    from camaddon import uebergabe_werkzeuge as ue
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    ordner = tempfile.mkdtemp()
    from camaddon import maschine as mm

    asm, _maschine = beispielmaschine.lade(beispielmaschine.TISCH_TISCH)
    for ba in mm.betriebsarten(_maschine):
        if ba.Art == mm.ART_LINEAR and ba.NcName == "Z1":
            ba.Wechsel, ba.WechselAn = 150.0, True  # Z ganz oben
    pfad_maschine = os.path.join(ordner, "fuenfachs.FCStd")
    asm.Document.saveAs(pfad_maschine)
    yield 300
    fraeser = wz.standardwerkzeug()
    bohrer = wz.Werkzeug(
        nummer=2, name="HSS 8,5", art=wz.BOHRER, durchmesser=8.5, schneiden=2,
        schneidenlaenge=60.0, spitzenwinkel=118.0, schneidstoff=wz.HSS,
    )  # fmt: skip
    bohrer.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.BOHREN, vc=25.0, fz=0.1)]
    bibliothek = wz.Bibliothek([fraeser, bohrer])
    bibliothek.speichern()
    ue.uebergeben(bibliothek)
    schruppen = next(e for e in fraeser.einsaetze(wz.ALLE) if e.art == wz.SCHRUPPEN)

    addon = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    doc = FreeCAD.openDocument(os.path.join(addon, "beispiele", "schwenkteil_5achs.FCStd"))
    doc.saveAs(os.path.join(ordner, "schwenkteil.FCStd"))
    teil = doc.getObject("Schwenkteil")
    FreeCAD.setActiveDocument(doc.Name)
    grundjob = PathJob.Create("Job", [teil])
    grundjob.Label = "Job Schwenkteil"
    grundjob.Stock.ExtZpos = 1.0
    doc.recompute()
    rw.merke_maschine(grundjob, pfad_maschine)
    klon = vr.modell(grundjob)

    def flaeche(normale, z=None):
        n = V(*normale)
        n.normalize()
        for i, f in enumerate(klon.Shape.Faces):
            a = sw.aussennormale(f)
            if a is None or (a - n).Length > 1e-6:
                continue
            if z is None or abs(f.BoundBox.ZMax - z) < 1e-6:
                return f"Face{i + 1}"
        return None

    s30 = math.sin(math.radians(30.0))
    schraege = max(
        (f"Face{i + 1}" for i, f in enumerate(klon.Shape.Faces)
         if sw.aussennormale(f) is not None
         and (sw.aussennormale(f) - V(0, -s30, math.cos(math.radians(30.0)))).Length < 1e-6),
        key=lambda n: klon.Shape.getElement(n).Area,
    )  # fmt: skip
    rechts = flaeche((1, 0, 1))
    tc1 = js.controller_ohne_transaktion(doc, grundjob, fraeser, schruppen)
    doc.recompute()
    oben = [e.name for e in hf.ebenen_oben(klon.Shape)]
    ra.lege_an(grundjob, tc1, schruppen.ap, schruppen.ae, flaechen=oben)
    doc.recompute()
    yield 300

    # --- Ebene 1: die Schräge mit ihrer Tasche --------------------------------------------------
    maschine = None
    from camaddon.gui_schwenken import maschine_fuer

    maschine, _name = maschine_fuer(grundjob)
    h.pruefe(maschine is not None, "keine Maschine für die Rundachsen")
    ebene1 = sw.lege_an(grundjob, schraege, maschine)
    tc = js.controller_ohne_transaktion(doc, ebene1, fraeser, schruppen)
    doc.recompute()
    k1 = vr.modell(ebene1).Shape
    in_ebene1 = [e.name for e in hf.ebenen_oben(k1)]
    ra.lege_an(ebene1, tc, schruppen.ap, schruppen.ae, flaechen=in_ebene1)
    doc.recompute()
    # --- Ebene 2: die 45°-Fläche, räumen und bohren -----------------------------------------------
    ebene2 = sw.lege_an(grundjob, rechts, maschine)
    tc = js.controller_ohne_transaktion(doc, ebene2, fraeser, schruppen)
    doc.recompute()
    k2 = vr.modell(ebene2).Shape
    ra.lege_an(ebene2, tc, schruppen.ap, schruppen.ae, flaechen=[rechts])
    loecher = [b.name for b in bb.bohrungen(k2)]
    h.pruefe(len(loecher) == 1, f"Bohrungen in der 45°-Ebene: {loecher}")
    if loecher:
        tc2 = js.controller_ohne_transaktion(doc, ebene2, bohrer, bohrer.schnittwerte[wz.ALLE][0])
        bh.lege_an(ebene2, tc2, loecher)
    doc.recompute()
    yield 500
    h.pruefe(
        ebene1.Rundachsen == "A−30 C0" and ebene2.Rundachsen.startswith("A"),
        f"Rundachsen: {ebene1.Rundachsen}, {ebene2.Rundachsen}",
    )
    for job in (ebene1, ebene2):
        fehlerhaft = [o.Label for o in job.Operations.Group if not o.Path.Commands]
        h.pruefe(not fehlerhaft, f"ohne Bahn: {fehlerhaft}")

    # --- Das Programm der Aufspannung ---------------------------------------------------------
    teile = pp.abschnitte(grundjob)
    siemens = pp.programm(teile, pp.steuerung("siemens"), pp.Maschineninfo("5-Achs"), "Schwenkteil")
    zyklen = [z for z in siemens.zeilen if z.startswith("CYCLE800(1")]
    h.pruefe(len(zyklen) == 2, f"CYCLE800: {zyklen}")
    with open(
        os.path.join(os.environ.get("CAMADDON_AUSGABE", ordner), "schwenkteil.mpf"), "w"
    ) as d:
        d.write(siemens.text)

    # --- „Programm schreiben“ ohne Schwenkzyklus: mit der Kette der Maschine gerechnet -----------
    # (je Werkzeug mit seiner Länge, wie „Auf der Maschine prüfen“) – nicht wie ein gedachter
    # Tisch A, C um den Nullpunkt: Der Nullpunkt liegt nicht im Drehpunkt der Maschine.
    from camaddon import gui_programm

    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, grundjob.Name)
    yield 300
    Gui.runCommand("CamAddon_ProgrammSchreiben")
    yield 1500
    d = gui_programm.ProgrammDialog.offen
    h.pruefe(d is not None, "„Programm schreiben“ öffnet kein Fenster")
    if d is not None:
        d.wahl_steuerung.setCurrentIndex(d.wahl_steuerung.findData("linuxcnc"))
        yield 800
        text = d._programm().text
        gewaehlt = (asm.Document.Name, pfad_maschine, asm.Document)
        mit = pp.programm(
            gui_programm.abschnitte_mit_maschine(grundjob, gewaehlt), d.steuerung(), d.info,
            grundjob.Label,
        ).text  # fmt: skip
        ohne = pp.programm(pp.abschnitte(grundjob), d.steuerung(), d.info, grundjob.Label).text
        h.pruefe(
            text == mit and text != ohne, "das Fenster rechnet die Ebenen nicht mit der Maschine"
        )
        h.pruefe("G0 A-30.000 C0.000" in text, "LinuxCNC: Rundachsen der Schräge fehlen")
        with open(
            os.path.join(os.environ.get("CAMADDON_AUSGABE", ordner), "schwenkteil.ngc"), "w"
        ) as datei:
            datei.write(text)
        h.bild("0_programm", d)
        d.reject()
        yield 300

    # --- Auf der Maschine prüfen ------------------------------------------------------------------
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(grundjob)
    yield 400
    QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("CamAddon_AufMaschinePruefen"))
    yield from h.warte_auf(lambda: gui_reichweite.PruefPanel.offen is not None, 30000)
    pruefung = gui_reichweite.PruefPanel.offen
    h.pruefe(pruefung is not None, "„Auf der Maschine prüfen“ öffnet kein Fenster")
    if pruefung is None:
        return
    yield 1500
    spieler = pruefung.abspieler
    fahrt = spieler.abfahrt
    namen = [o.name for o in fahrt.operationen] if fahrt is not None else []
    h.pruefe(len(namen) >= 4, f"Operationen im Abspieler: {namen}")
    h.bild("1_fenster", pruefung.form)
    for k, (job, bild) in enumerate(((ebene1, "2_schraege"), (ebene2, "3_45_grad"))):
        op = job.Operations.Group[0]
        if op.Label not in namen or fahrt is None:
            h.pruefe(False, f"{op.Label} nicht im Abspieler")
            continue
        nummer = namen.index(op.Label)
        stationen = [
            i for i, s in enumerate(fahrt.stationen) if s.operation == nummer and not s.ziel
        ]
        if stationen:
            spieler.springe_zu_station(stationen[len(stationen) // 3])
        yield 600
        spieler.knopf_hinsehen.click()
        yield 600
        h.bild(bild)
        del k
    Gui.SendMsgToActiveView("ViewFit")
    yield 500
    h.bild("4_ganz")
    # Kollision: Werkzeug, Halter, Maschine gegen Teil und Spannmittel – auch beim Schwenken.
    from camaddon import gui_kollision

    bereich = getattr(pruefung, "kollision", None)
    if bereich is not None and hasattr(bereich, "pruefen"):
        bereich.pruefen()  # rechnet bis zum Ende (mit processEvents)
        yield 500
        urteil = pruefung.urteil_kollision.text()
        with open(
            os.path.join(os.environ.get("CAMADDON_AUSGABE", ordner), "kollision.txt"), "w"
        ) as d:
            d.write(
                urteil + "\n" + bereich.liste.toPlainText()
                if hasattr(bereich.liste, "toPlainText")
                else urteil
            )
        h.bild("5_kollision", pruefung.form)
        h.pruefe(urteil.startswith("Nichts berührt sich"), f"Kollision: {urteil}")
        del gui_kollision
