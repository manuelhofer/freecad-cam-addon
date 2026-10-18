# Manuels Ring (2026-10-12: „die nuten in dem bauteil werden garnicht bearbeitet face 28 face 6
# face 17“): der Grund einer Ringnut auf der Stirn (Face6) angeklickt, „4-Achs-Bearbeitung“ auf
# der Beispiel-Drehmaschine, Schritt 2. Rot steht, dass Face6 längs der Achse schaut (Stirnseite)
# und in „Bearbeitung“ von vorn gehört – mit dem Verweis „„Bearbeitung“ von vorn öffnen …“. Der
# Verweis schließt den Assistenten, die Stange bleibt im Job (W-025, P-2026-10-17-43), und
# „Bearbeitung“ öffnet sich auf diesem Job mit Face6 gewählt: graue Zeile „Von vorn an der Stange
# der Drehmaschine …“, eine Strategie angehakt, dazu „Schlichten danach“ mit Messstopp (wenn
# angeboten); „Anlegen“ legt die Operationen in den Stangen-Job. Von vorn fräst nur T2 im axialen
# Halter – T1 sitzt radial und zeigt auf die Achse der Stange (Manuel, 2026-10-18: „das bearbeitet
# man doch von vorne“); in keiner Fräserliste steht T1. Das Siemens-Programm der
# Drehmaschine: Y im Rahmen, das angetriebene Werkzeug mit seinem Befehl, im Messstopp sein Antrieb
# aus statt „M5“.
# ZEITLIMIT: 600
import os
import shutil
import tempfile

import FreeCAD
import FreeCADGui as Gui

ADDON = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def schritte(h):
    yield 500
    erster = h.modal()
    if erster is not None:  # Sprachwahl beim ersten Start
        erster.liste.setCurrentIndex(erster.liste.findData("de"))
        erster.wahl_dezimalzeichen.setCurrentIndex(erster.wahl_dezimalzeichen.findData(","))
        erster.accept()
    yield 500

    from camaddon import beispielmaschine, gui_bearbeitung, gui_vierachs
    from camaddon import vierachs_rohteil as vr
    from camaddon import werkzeuge as wz

    bibliothek = wz.Bibliothek()
    halter = bibliothek.neuer_halter("vdi30_radial")
    t1 = bibliothek.neues_werkzeug()
    t1.nummer, t1.name, t1.durchmesser, t1.schneiden = 1, "VHM 4", 4.0, 3
    t1.schneidenlaenge, t1.laenge_spindelnase, t1.halter = 12.0, 110.0, halter.kennung
    t1.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=1.0, ap=3, vc=120, fz=0.03)]
    axial = bibliothek.neuer_halter("vdi30_axial")
    t2 = bibliothek.neues_werkzeug()
    t2.nummer, t2.name, t2.durchmesser, t2.schneiden = 2, "VHM 4 axial", 4.0, 3
    t2.schneidenlaenge, t2.laenge_spindelnase, t2.halter = 12.0, 110.0, axial.kennung
    t2.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.SCHRUPPEN, ae=1.0, ap=3, vc=120, fz=0.03)]
    bibliothek.speichern()

    asm, _maschine = beispielmaschine.lade(beispielmaschine.DREHMASCHINE)
    yield from h.warte_auf(lambda: FreeCAD.ActiveDocument is asm.Document)
    yield 300

    ordner = tempfile.mkdtemp()
    datei = os.path.join(ordner, "ring.FCStd")
    shutil.copy(os.path.join(ADDON, "beispiele", "ring_4achs_planbearbeitung.FCStd"), datei)
    doc = FreeCAD.openDocument(datei)
    teil = doc.getObject("Body")
    Gui.activateWorkbench("CAMWorkbench")
    Gui.ActiveDocument.ActiveView.viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
    # Der Grund einer Ringnut auf der Stirn: eben, nach vorn, zwischen den Stirnflächen (z 5)
    nutgrund = next(
        f"Face{i + 1}"
        for i, f in enumerate(teil.Shape.Faces)
        if vr.ist_eben(f)
        and (vr.aussennormale(f) - FreeCAD.Vector(0, 0, 1)).Length < 1e-9
        and 0.05 < f.BoundBox.ZMin < 7.95
    )
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(doc.Name, teil.Name, nutgrund)
    yield 500

    Gui.runCommand("CamAddon_Vierachs")
    yield 1500
    panel = gui_vierachs.VierachsPanel.offen
    h.pruefe(panel is not None and panel.job is not None, "kein Fenster oder kein Job")
    if panel is None or panel.job is None:
        return
    yield from h.warte_auf(lambda: not panel._uhr.isActive(), 3000)
    yield from h.warte_auf(lambda: not (panel.einfahren and panel.einfahren.laeuft()), 3000)
    panel.knopf_weiter.click()
    yield 300
    h.pruefe(panel.seite == 2, f"Seite {panel.seite}")
    if panel.mit_schlichten.isChecked():
        panel.mit_schlichten.setChecked(False)
    panel.flaeche_umschalten(nutgrund)  # wie ein Klick im 3D: nur diese Fläche
    yield 500
    h.pruefe(panel.gewaehlte == [nutgrund], f"gewählt: {panel.gewaehlte} statt {nutgrund}")
    yield from h.warte_auf(lambda: not panel.rechnet_noch(), 180000)
    yield 800
    rot = panel.hinweis_bearbeitung.text()
    h.pruefe(
        nutgrund in rot and "Stirnseite" in rot and 'href="bearbeitung:' in rot,
        f"rot: {rot!r}",
    )
    h.pruefe(not panel.knopf_fertig.isEnabled(), "„Anlegen“ frei trotz Stirnfläche")
    h.bild("1_stirnseite", panel.form)
    job_name = panel.job.Name
    panel.hinweis_bearbeitung.linkActivated.emit(f"bearbeitung:{nutgrund}")
    yield from h.warte_auf(
        lambda: getattr(gui_bearbeitung.BearbeitungPanel.offen, "job", None) is not None, 20000
    )
    yield 1000
    h.pruefe(gui_vierachs.VierachsPanel.offen is None, "4-Achs-Assistent noch offen")
    stange_job = doc.getObject(job_name)
    h.pruefe(stange_job is not None, "der 4-Achs-Job (die Stange) ist weg")
    dialog = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(
        dialog is not None and dialog.gewaehlte == [nutgrund],
        f"„Bearbeitung“ gewählt: {getattr(dialog, 'gewaehlte', None)}",
    )
    if dialog is None:
        return
    h.pruefe(dialog.job is stange_job, "„Bearbeitung“ nicht auf dem Stangen-Job")
    if dialog.maschine() is not None:  # die Beispiel-Drehmaschine ist nicht gespeichert
        h.pruefe(
            "Von vorn an der Stange" in dialog.maschine_hinweis.text(),
            f"Maschinenzeile: {dialog.maschine_hinweis.text()!r}",
        )
    yield from h.warte_auf(lambda: not dialog.vorschau_laeuft() and dialog.aktive_bloecke(), 180000)
    yield 1000
    aktive = [b.s.kennung for b in dialog.aktive_bloecke()]
    print(ascii(f"aktiv auf der Stirnseite: {aktive}"))
    h.pruefe(bool(aktive), "keine Strategie für den Nutgrund angehakt")
    h.pruefe(
        all(getattr(b.fraeser(), "nummer", None) == 2 for b in dialog.aktive_bloecke())
        and not any(w.nummer == 1 for b in dialog.bloecke for w in b._fraeser),
        f"Fräser von vorn: {[(b.s.kennung, getattr(b.fraeser(), 'nummer', None)) for b in dialog.aktive_bloecke()]}",
    )
    # Schruppen – messen – schlichten auch von vorn (Manuel, 2026-10-17): „Schlichten danach“ mit
    # Messstopp, wenn angeboten.
    danach = dialog.schlichten_danach
    yield from h.warte_auf(lambda: danach.vorschau is not None or not danach.moeglich, 120000)
    if danach.moeglich and danach.vorschau is not None:
        danach.haken.setChecked(True)
        danach.haken_felder["messstopp"].setChecked(True)
        yield 500
        yield from h.warte_auf(lambda: not dialog.vorschau_laeuft(), 120000)
    h.bild("2_bearbeitung", dialog.form)
    if dialog.accept() is not True:
        h.pruefe(False, f"„Anlegen“ ging nicht: {dialog.hinweis.text()!r}")
    yield 2500
    ops = [o.Label for o in stange_job.Operations.Group]
    h.pruefe(bool(ops), f"keine Operation im Stangen-Job: {ops}")
    print(ascii(f"Operationen im Stangen-Job: {ops}"))
    h.bild("3_angelegt")

    # --- Das Programm für die Drehmaschine (Siemens, angetriebenes Werkzeug) ------------------------
    # Y im Rahmen der Maschine (±51 von ±60), das Werkzeug mit dem Befehl seines Antriebs; im
    # Messstopp der Antrieb aus („M3=…5“), nicht „M5“ der Hauptspindel, und nach dem Halt kein
    # rohes „M3“ (P-2026-10-18-54).
    from camaddon import postprozessor as pp

    info = pp.maschineninfo_dokument(asm.Document)
    zeilen = pp.programm(pp.abschnitte(stange_job), pp.steuerung("siemens"), info, "Ring").zeilen
    with open(os.path.join(os.environ["CAMADDON_AUSGABE"], "ring_siemens.mpf"), "w") as datei:
        datei.write("\n".join(zeilen) + "\n")
    y_werte = [float(w[1:]) for z in zeilen for w in z.split() if w.startswith("Y")]
    h.pruefe(max((abs(y) for y in y_werte), default=0.0) <= 51.0005, f"Y bis {max(y_werte or [0])}")
    h.pruefe(any("=3 S" in z for z in zeilen), f"kein angetriebenes Werkzeug: {zeilen[:30]}")
    if "Messstopp" in ops:
        k = zeilen.index("; MESSSTOPP") if "; MESSSTOPP" in zeilen else -1
        halt = zeilen.index("M0", k) if k >= 0 and "M0" in zeilen[k:] else -1
        h.pruefe(
            k >= 0
            and halt > k
            and "M5" not in zeilen[k:halt]
            and any(z.startswith("M") and z.endswith("=5") for z in zeilen[k:halt]),
            f"Messstopp: {zeilen[k:halt + 1] if k >= 0 else zeilen[-20:]}",
        )
        h.pruefe(
            not any(z == "M3" or z.startswith("M3 ") for z in zeilen[k:]),
            "nach dem Messstopp ein rohes M3",
        )
