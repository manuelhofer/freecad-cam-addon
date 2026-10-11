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
    Schlüsselwörter (mit dem Materialstand `stand`), `zeit` (Vorschub, Eintauchen, Freivorschub)
    für freiwege.zeit_im_freien, None ohne."""
    job = _job(dokument, job_name)
    bahn = ra.vorschau_fuer_assistent(
        job, form, zustellung, zeilenabstand, aufmass, flaechen, **weiter
    )
    return bahn, _frei(form, weiter.get("stand"), bahn, zeit)


def strategie(dokument, job_name, modul, argumente, weiter, zeit):
    """(Bahn, Zeit im Freien oder None) – `camaddon.<modul>.vorschau(job, Modell, *argumente,
    **weiter)` (Planfräsen, Kontur, 3D-Schruppen); das erste der `argumente` ist die Form des
    Fräsers."""
    job = _job(dokument, job_name)
    vorschau = importlib.import_module("camaddon." + modul).vorschau
    bahn = vorschau(job, job.Model.Group, *argumente, **weiter)
    return bahn, _frei(argumente[0], weiter.get("stand"), bahn, zeit)


def _frei(form, stand, bahn, zeit):
    """freiwege.zeit_im_freien für die Bahn – None ohne `zeit` (Vorschub, Eintauchen,
    Freivorschub)."""
    if zeit is None:
        return None
    vorschub, eintauchen, freivorschub = zeit
    return fw.zeit_im_freien(form, stand, bahn.punkte, vorschub, eintauchen, freivorschub)
