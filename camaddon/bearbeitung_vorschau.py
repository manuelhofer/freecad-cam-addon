# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Vorschau des Assistenten „Bearbeitung“ (gui_bearbeitung) als Aufträge für die
Nebenrechner – wie vierachs_vorschau für den 4-Achs-Assistenten: je Strategie eine Funktion, die
aus dem Dokument (der Kopie im Nebenrechner) und dem Namen des Jobs die grobe Bahn rechnet, so wie
der Assistent sie im eigenen Prozess rechnete, und dazu die Zeit mit dem Freivorschub im Freien.
Ergebnisse sind reine Daten (die Bahn, die Zeit) – so gehen sie durch die Verbindung. Ein
ValueError mit einem Satz für den Menschen (auch materialstand.SchonWeg) kommt, wie bei den
Funktionen dahinter, wenn es nicht geht; der Assistent zeigt ihn.

Warum: Das Räumen rechnet am 3-Achs-Testteil im Assistenten 3 bis 14 s (mit kleiner Zustellung);
im Prozess der Oberfläche nahm FreeCAD so lange keinen Klick an (P-2026-10-11-23). Läuft ohne
Oberfläche.
"""

import contextlib
import importlib

from . import freiwege as fw
from . import raeumen as ra


def _job(dokument, name):
    """Der Job in der Kopie – fehlt er, LookupError (kein ValueError: Der Assistent zeigte den als
    Grund; so rechnet er die Vorschau selbst)."""
    job = dokument.getObject(name)
    if job is None:
        raise LookupError(f"Job „{name}“ fehlt im Dokument {dokument.Name}")
    return job


def raeumen(dokument, job_name, form, zustellung, zeilenabstand, aufmass, flaechen, weiter, zeit):
    """(Raeumbahn, Zeit im Freien oder None) – raeumen.vorschau_fuer_assistent; `weiter` seine
    Schlüsselwörter (mit dem Materialstand `stand`), `zeit` (Vorschub, Eintauchen, Freivorschub,
    Materialstand) für freiwege.zeit_im_freien, None ohne."""
    job = _job(dokument, job_name)
    bahn = ra.vorschau_fuer_assistent(
        job, form, zustellung, zeilenabstand, aufmass, flaechen, **weiter
    )
    return bahn, _frei(form, bahn, zeit)


def raeumen_genau(dokument, job_name, form, zustellung, zeilenabstand, aufmass, flaechen, weiter):
    """Die genaue Bahn des Räumens (raeumen.bahn_fuer, wie „Anlegen“ sie rechnet) schon während
    der Vorschau, die adaptiv nur grob rechnet (W-036): Gibt die Ergebnisse des Adaptiv-Kerns
    zurück, die sie brauchte ({Schlüssel: Gebiete}, raeumen_bahn.adaptiv_benutzt). Das Fenster
    nimmt sie auf (raeumen_bahn.adaptiv_merken), und beim „Anlegen“ trifft das Räumen sie – am
    Testteil rechnete der Kern dort 4 s auf einem Kern. Scheitert die Bahn, was bis dahin da ist."""
    from . import raeumen_bahn as rb

    job = _job(dokument, job_name)
    weiter = {k: v for k, v in weiter.items() if k != "vorbohren"}  # das rechnet die Vorschau
    rb.adaptiv_benutzt_beginnen()
    with contextlib.suppress(ValueError):
        ra.bahn_fuer(
            job, job.Model.Group, form, zustellung, zeilenabstand, aufmass, flaechen, **weiter
        )
    return rb.adaptiv_benutzt()


def strategie(dokument, job_name, modul, argumente, weiter, zeit):
    """(Bahn, Zeit im Freien oder None) – `camaddon.<modul>.vorschau(job, Modell, *argumente,
    **weiter)` (Planfräsen, Kontur, 3D-Schruppen und Restschruppen, 3D-Schlichten); das erste der
    `argumente` ist die Form des Fräsers."""
    job = _job(dokument, job_name)
    vorschau = importlib.import_module("camaddon." + modul).vorschau
    bahn = vorschau(job, job.Model.Group, *argumente, **weiter)
    return bahn, _frei(argumente[0], bahn, zeit)


def schlichten3d_wegkippen(dokument, job_name, werkzeug, argumente, weiter, zeit):
    """(Bahn, Zeit im Freien oder None) – das 3D-Schlichten mit dem Bedarf zum Wegkippen
    (wegkippen.bedarf_fuer_bahn: Halter und Länge aus der Werkzeugverwaltung des Profils)."""
    from . import schlichten3d
    from . import wegkippen as wk

    job = _job(dokument, job_name)
    bahn = schlichten3d.vorschau(job, job.Model.Group, *argumente, **weiter)
    if not getattr(bahn, "hinterschnitt", False):  # unter dem Rand kippt die Bahn selbst
        bahn.wegkippen = wk.bedarf_fuer_bahn(job, werkzeug, bahn, argumente[0])
    return bahn, _frei(argumente[0], bahn, zeit)


def empfehlung(dokument, job_name, daten, ecken, kennung, aufnahme):
    """(Empfehlung, Empfehlung für die Ecken) – neben der Vorschau des 3D-Schlichtens unter dem
    Rand, in einem eigenen Auftrag (schlichten3d._empfehlung, _ecken_empfehlung; je None, wenn es
    nichts zu empfehlen gibt). `daten`: {"pruefung", "ausspannen"} der Bahn oder ihres Fehlers
    (unter dem Rand) oder {"flanke", "ausspannen"} (die Flanke, flanke._empfehlung),
    `ecken`: Bahn.ecken, `kennung`: der Fräser in der Werkzeugverwaltung."""
    from . import schlichten3d

    job = _job(dokument, job_name)
    modell = job.Model.Group
    haupt = None
    if daten and daten.get("flanke"):  # die Flanke: Halter oder Schaft führen in die Wand
        from . import flanke

        haupt = flanke._empfehlung(job, modell, daten, kennung, aufnahme)
    elif daten and daten.get("pruefung"):
        haupt = schlichten3d._empfehlung(job, modell, daten, kennung, aufnahme)
    ecke = schlichten3d._ecken_empfehlung(job, modell, ecken, kennung, aufnahme) if ecken else None
    return haupt, ecke


def _frei(form, bahn, zeit):
    """freiwege.zeit_im_freien für die Bahn – None ohne `zeit` (Vorschub, Eintauchen,
    Freivorschub, Materialstand: der des Assistenten, wie gui_bearbeitung._zeit_im_freien; das
    Restschruppen rechnet seine Bahn ohne ihn)."""
    if zeit is None:
        return None
    vorschub, eintauchen, freivorschub, stand = zeit
    return fw.zeit_im_freien(form, stand, bahn.punkte, vorschub, eintauchen, freivorschub)
