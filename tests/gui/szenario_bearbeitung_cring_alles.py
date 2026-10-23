# Der C-Ring ohne Job (W-034; Manuel, 2026-10-18, zum Rohteil des Beispiels: „naja es muss beides
# funktionieren .. und auswählbarsein ... wenn rt welle d60 ist muss man ausen nix machen“):
# „Bearbeitung“ auf der 3-Achs-Fräse mit der Testkiste (T1 Ø 12, T2 Plan 50, T3 Ø 6, T4 Ø 20), die
# Oberseite angeklickt, dann „Alles aus dieser Aufspannung“ – einmal als Platte (Quader mit Maßen
# 65 × 65 × 12, Aufmaß oben 1), einmal als Rundmaterial (Zylinder, Aufmaß oben 1, Umfang 0,
# unten 1). Beide Male: Das Räumen bleibt angehakt (es verlor den Haken mit dem Merker „schon weg“
# aus dem zweiten Lauf seiner Folge), die Nut fräst die Ringnut mit T3 (der Ø 12 passt nicht
# hinein, die Nut schlug sich neben anderen Flächen nicht vor – die Ringnut blieb liegen),
# „Schlichten danach“ mit Messstopp davor. Das Räumen räumt über alles bis zur Unterkante (außen
# herum – Grundsatz 5, Manuel: „keine luftfahrten … und wenn rohteil schon fertigteil durchmesser
# hat ... dann muss man da auch nimmer drüber juckeln“), die Kontur hat nichts zu tun; Schlitz und
# Bohrung hinter dem Keil sind für T1 zu eng – „Rest räumen“ mit T3 von außen in Wellen („Ja, dort
# der kleinere“). „Anlegen“: Räumen T1, Räumen T3, „Nut T3“, Messstopp, „Wände schlichten T1“,
# „Nut schlichten T3“ – keine Kontur; beim Rundmaterial schlichtet niemand den Mantel (davor steht
# kein Rohteil). Der Ø 12 passt nicht in die 10 mm breite Nut: Ihre Wände schlichtet T3 mit
# seinem Einsatz fürs Schlichten, nicht die Kontur (sie fuhr bis 0.276.3 an der einen Wand durch
# die andere und nahm beide Stege 5 mm tief mit, W-029). Nach allen Operationen steht im
# Materialstand überall das Teil.
# ZEITLIMIT: 900
import math
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
    h.pruefe(
        not panel.kontur.aktiv() and "nichts zu tun" in panel.kontur.hinweis.text(),
        f"{name}: Kontur {panel.kontur.aktiv()} {panel.kontur.hinweis.text()!r}",
    )
    # Schlitz (Keil 12–18 mm) und Bohrung dahinter: zu eng für T1 Ø 12 – „Rest räumen“ mit T3 von
    # außen in Wellen (Manuel, 2026-10-18: „Ja, dort der kleinere“).
    rest = panel.restraeumen
    h.pruefe(
        "Engstelle" in panel.raeumen.ergebnis.text()
        and rest.aktiv()
        and getattr(rest.fraeser(), "nummer", None) == 3,
        f"{name}: Räumen {panel.raeumen.ergebnis.text()!r}, Rest räumen {rest.aktiv()} "
        f"T{getattr(rest.fraeser(), 'nummer', None)}",
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
    soll_namen = (
        "Räumen T1", "Räumen T3", "Nut T3", "Messstopp", "Wände schlichten T1", "Nut schlichten T3"
    )  # fmt: skip
    for soll in soll_namen:
        h.pruefe(soll in namen, f"{name}: „{soll}“ fehlt in {namen}")
    if all(n in namen for n in soll_namen):
        # Schruppen – messen – schlichten: alles Schruppen (auch die Kontur) vor dem Messstopp.
        h.pruefe(
            namen[namen.index("Messstopp") :]
            == ["Messstopp", "Wände schlichten T1", "Nut schlichten T3"],
            f"{name}: Folge {namen}",
        )
    # Nichts im Teil (W-029 fand es im Beispiel vom 18.10.: „Wände schlichten T1“ Ø 12 fuhr in
    # die 10 mm breite Nut und nahm die Stege mit): Nach allen Operationen steht im Raster des
    # Materialstands überall mindestens das Teil – bis auf die Zellen am Rand des Teils (ihre
    # Mitte liegt mal knapp drinnen, mal draußen) und die, die schon im Rohteil fehlten (der
    # Materialstand zieht ein rundes Rohteil um eine Zelle ein, materialstand._eingezogen).
    import numpy as np

    from camaddon import hoehenfeld as hf
    from camaddon import materialstand as mst
    from camaddon import vierachs_huelle as vh

    stand = mst.fuer(job)
    q = stand.quader
    anfang = mst.fuer(job, vor=job.Operations.Group[0]).quader.h
    oben = hf.hoehen(vh.vernetze(job.Model.Group[0].Shape), q.x, q.y)
    rest = np.where(np.isfinite(q.h), q.h, -1e9)
    unter = (oben > -1e8) & (rest < oben - 0.05) & (anfang >= oben - 0.05)
    innen = unter.copy()
    innen[1:-1, 1:-1] &= (
        (np.abs(oben[2:, 1:-1] - oben[1:-1, 1:-1]) < 0.05)
        & (np.abs(oben[:-2, 1:-1] - oben[1:-1, 1:-1]) < 0.05)
        & (np.abs(oben[1:-1, 2:] - oben[1:-1, 1:-1]) < 0.05)
        & (np.abs(oben[1:-1, :-2] - oben[1:-1, 1:-1]) < 0.05)
    )
    print(
        ascii(f"{name}: {int(unter.sum())} Zellen unter dem Teil, {int(innen.sum())} nicht am Rand")
    )
    h.pruefe(not innen.any(), f"{name}: {int(innen.sum())} Zellen unter der Oberkante des Teils")
    # Räumen T3 und Nut T3 mit demselben Einsatz: ein Controller für T3 (vorher je einer); dazu
    # einer fürs Schlichten der Nut.
    t3 = sorted(tc.Label for tc in job.Tools.Group if tc.ToolNumber == 3)
    h.pruefe(
        t3 == ["T3 VHM 6 – Schlichten", "T3 VHM 6 – Schruppen"], f"{name}: Controller für T3: {t3}"
    )
    schlichten = next((o for o in neue if o.Label == "Wände schlichten T1"), None)
    h.pruefe(not any(n.startswith("Kontur") for n in namen), f"{name}: Kontur in {namen}")
    if schlichten is not None:
        waende = list(getattr(schlichten, "Flaechen", []) or [])
        print(ascii(f"{name}: Wände schlichten {waende}"))
        h.pruefe(
            ("Face1" in waende) == (name == "platte"),
            f"{name}: Mantel beim Schlichten {'fehlt' if name == 'platte' else 'dabei'}: {waende}",
        )
    raeumen = next((o for o in neue if o.Label.startswith("Räumen")), None)
    if name == "rund" and raeumen is not None:
        # Keine Luft (Grundsatz 5): Der Fräser Ø 12 berührt die Stange Ø 60 nur bis R 36 – weiter
        # draußen höchstens das Einfahren von außen in den Schlitz, kein Ring um den Mantel (am
        # Raster gezackt, Manuel: „warum ist der werkeugweg der ausenrum geht so zackig“).
        mantel = job.Model.Group[0].Shape.Faces[0].Surface
        mitte, grenze = mantel.Center, mantel.Radius + 6.0 + 0.5
        draussen = 0
        for befehl in raeumen.Path.Commands:
            werte = befehl.Parameters
            if (
                befehl.Name == "G1"
                and "X" in werte
                and "Y" in werte
                and math.hypot(werte["X"] - mitte.x, werte["Y"] - mitte.y) > grenze
            ):
                draussen += 1
        print(ascii(f"rund: {draussen} Sätze im Vorschub außerhalb R {grenze:.1f}"))
        h.pruefe(draussen < 50, f"rund: {draussen} Sätze im Vorschub außerhalb R {grenze:.1f}")
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
