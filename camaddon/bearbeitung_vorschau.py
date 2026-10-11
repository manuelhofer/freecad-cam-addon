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

from . import freiwege as fw
from . import raeumen as ra


def _job(dokument, name):
    job = dokument.getObject(name)
    if job is None:
        raise ValueError(f"Job „{name}“ fehlt im Dokument {dokument.Name}")
    return job


def raeumen(dokument, job_name, form, zustellung, zeilenabstand, aufmass, flaechen, weiter, zeit):
    """(Raeumbahn, Zeit im Freien oder None) – raeumen.vorschau_fuer_assistent; `weiter` seine
    Schlüsselwörter (mit dem Materialstand `stand`), `zeit` (Vorschub, Eintauchen, Freivorschub)
    für freiwege.zeit_im_freien, None ohne."""
    job = _job(dokument, job_name)
    bahn = ra.vorschau_fuer_assistent(
        job, form, zustellung, zeilenabstand, aufmass, flaechen, **weiter
    )
    frei = None
    if zeit is not None:
        vorschub, eintauchen, freivorschub = zeit
        frei = fw.zeit_im_freien(
            form, weiter.get("stand"), bahn.punkte, vorschub, eintauchen, freivorschub
        )
    return bahn, frei
