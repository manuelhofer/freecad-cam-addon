# Die zusätzliche Räumwahl am vorhandenen Testteil, mit allen Assertions des Grundszenarios:
# bisherig ist vorgewählt; schneller Freivorschub ändert nur freie Verbindungen, andere
# Bearbeitungen behalten ihre Bahnen; Anlegen, Speichern, Laden und Doppelklick erhalten die
# Wahl. Das Grundszenario prüft weiterhin alle sechs Operationen und den Materialabtrag.
import importlib.util
import os
from dataclasses import replace

import FreeCAD


def schritte(h):
    from camaddon import gui_bearbeitung
    from camaddon import raeumen as ra

    datei = os.path.join(os.path.dirname(__file__), "szenario_testteil.py")
    spec = importlib.util.spec_from_file_location("testteil_grundszenario", datei)
    grund = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(grund)
    gewaehlt = gespeichert = False
    pfad = os.path.join(os.environ["CAMADDON_AUSGABE"], "testteil_freivorschub.FCStd")
    job = None
    for warten in grund.schritte(h):
        panel = gui_bearbeitung.BearbeitungPanel.offen
        if (
            not gewaehlt
            and panel is not None
            and panel.raeumen.vorschau is not None
            and panel.raeumen.vorschau.flaechen == 3
            and all(b.vorschau is not None or not b.aktiv() for b in panel.bloecke)
            and not panel._vorschau_uhr.isActive()  # kein Lauf steht mehr aus
        ):
            block = panel.raeumen
            job = panel.job
            h.pruefe(block.wahl_bahn.currentData() == "automatisch", "bisherig nicht vorgewählt")
            h.pruefe(block.wahl_bahn.count() == 2, "nicht genau zwei Räumwahlen")
            h.pruefe(block.freivorschub_zeile.isHidden(), "Freivorschub bei bisherig sichtbar")
            alt = block.vorschau
            zeit_alt = block.zeit
            andere = {
                b.s.kennung: tuple(b.vorschau.punkte)
                for b in panel.bloecke
                if b is not block and b.vorschau is not None
            }
            panel.seite_zeigen(2)
            yield 500
            h.bild("freivorschub_bisherig", panel.form)
            block.wahl_bahn.setCurrentIndex(block.wahl_bahn.findData(ra.ADAPTIV_FREI))
            yield from h.warte_auf(
                lambda block=block, alt=alt, panel=panel: block.vorschau is not None
                and block.vorschau is not alt
                and not panel._vorschau_uhr.isActive(),
                60000,
            )
            neu = block.vorschau
            h.pruefe(not block.freivorschub_zeile.isHidden(), "Freivorschub fehlt")
            h.pruefe(block.zeit < zeit_alt - 0.1, f"Freivorschub: {block.zeit} statt {zeit_alt}")
            h.pruefe(len(neu.punkte) == len(alt.punkte), "Freivorschub: andere Punktzahl")
            for a, b in zip(alt.punkte, neu.punkte, strict=False):
                h.pruefe(replace(b, anteil=a.anteil) == a, "Freivorschub: Schnittbahn geändert")
                if a.eilgang or a.anteil <= 1.0:
                    h.pruefe(a == b, "Freivorschub: Schnittwerte oder Eilgang geändert")
            for b in panel.bloecke:
                if b.s.kennung in andere:
                    h.pruefe(
                        b.vorschau is not None and tuple(b.vorschau.punkte) == andere[b.s.kennung],
                        f"Andere Bearbeitung geändert: {b.s.kennung}",
                    )
            yield 500
            h.bild("freivorschub_neu", panel.form)
            gewaehlt = True
        if (
            gewaehlt
            and not gespeichert
            and panel is None
            and job is not None
            and len(job.Operations.Group) == 6
            and not job.Document.isTouched()
        ):
            op = job.Operations.Group[0]
            h.pruefe(str(op.Variante) == ra.ADAPTIV_FREI, "Anlegen: Auswahl verloren")
            h.pruefe(
                abs(float(op.Freivorschub) * 60.0 - ra.FREIVORSCHUB) < 1e-6,
                "Anlegen: Freivorschub verloren",
            )
            h.pruefe(
                all(c.Parameters.get("F", 0.0) <= ra.FREIVORSCHUB / 60.0 + 1e-6
                    for c in op.Path.Commands),
                "Anlegen: Freivorschub über Vorgabe",
            )  # fmt: skip
            job.Document.saveAs(pfad)
            gespeichert = True
        yield warten
    h.pruefe(gewaehlt and gespeichert, "Neue Auswahl wurde nicht angelegt und gespeichert")
    if not gespeichert:
        return
    doc = FreeCAD.openDocument(pfad)
    yield 1000
    op = next(o for o in doc.Objects if ra.ist_raeumen(o) and str(o.Variante) == ra.ADAPTIV_FREI)
    h.pruefe(op.ViewObject.Proxy.doubleClicked(op.ViewObject), "Doppelklick öffnet nichts")
    yield 1000
    panel = gui_bearbeitung.BearbeitungPanel.offen
    h.pruefe(panel is not None, "Kein Fenster nach Laden")
    if panel is not None:
        block = panel.raeumen
        h.pruefe(block.wahl_bahn.currentData() == ra.ADAPTIV_FREI, "Doppelklick: Auswahl verloren")
        h.pruefe(abs(block.werte()["freivorschub"] - ra.FREIVORSCHUB) < 1e-6,
                 "Doppelklick: Freivorschub verloren")  # fmt: skip
        yield from h.warte_auf(lambda: block.vorschau is not None, 60000)
        h.bild("freivorschub_geladen", panel.form)
        panel.reject()
        yield 500
    FreeCAD.closeDocument(doc.Name)
    yield 300
