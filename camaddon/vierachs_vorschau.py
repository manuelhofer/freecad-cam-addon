# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Vorschau des 4-Achs-Assistenten (gui_vierachs) als Aufträge für die Nebenrechner.

Je Bearbeitung eine Funktion, die aus dem Dokument – der Kopie im Nebenrechner oder dem Dokument
selbst im eigenen Prozess – und dem Namen des Jobs die grobe Bahn rechnet, wie die Operationen
sie rechnen: vierachs_operation.bahn_fuer (Schruppen), vierachs_schlichten.vorschau,
vierachs_plan.vorschau (auch für den Bohrer daneben), vierachs_entgraten.vorschau. Richtungen
kommen als Tupel, die Ergebnisse (Bahn, Schlichtbahn, Planbahn, Entgratbahn) sind reine Daten –
so gehen sie durch die Verbindung. Ein ValueError mit einem Satz für den Menschen kommt, wie bei
den Funktionen dahinter, wenn es nicht geht; der Assistent zeigt ihn.

Warum: Manuel, 2026-10-09 – beim Ändern der seitlichen Zustellung „kommt ein Lag zustande, wo ich
nichts klicken kann … lass das im Hintergrund rechnen, aber so, dass ich die Oberfläche weiter
bedienen kann“. Läuft ohne Oberfläche.
"""

import FreeCAD

from . import vierachs_entgraten as vent
from . import vierachs_operation as vo
from . import vierachs_plan as vplan
from . import vierachs_schlichten as vs


def _job(dokument, name):
    job = dokument.getObject(name)
    if job is None:
        raise ValueError(f"Job „{name}“ fehlt im Dokument {dokument.Name}")
    return job


def schruppen(dokument, job_name, laengs, radial, *args, **kwargs):
    """Die Schruppbahn (vierachs_bahn.Bahn) – vierachs_operation.bahn_fuer."""
    job = _job(dokument, job_name)
    return vo.bahn_fuer(
        job, job.Model.Group, FreeCAD.Vector(*laengs), FreeCAD.Vector(*radial), *args, **kwargs
    )


def schlichten(dokument, job_name, laengs, radial, *args, **kwargs):
    """Die grobe Schlichtbahn (vierachs_bahn.Schlichtbahn) – vierachs_schlichten.vorschau."""
    job = _job(dokument, job_name)
    return vs.vorschau(
        job, job.Model.Group, FreeCAD.Vector(*laengs), FreeCAD.Vector(*radial), *args, **kwargs
    )


def plan(dokument, job_name, laengs, radial, *args, **kwargs):
    """Die grobe Bahn „Plan indexiert“ (vierachs_planbahn.Planbahn) – vierachs_plan.vorschau,
    mit dem Fräser oder dem Bohrer für die Querbohrungen."""
    job = _job(dokument, job_name)
    return vplan.vorschau(
        job, job.Model.Group, FreeCAD.Vector(*laengs), FreeCAD.Vector(*radial), *args, **kwargs
    )


def entgraten(dokument, job_name, laengs, radial, *args, **kwargs):
    """Die grobe Bahn „Rundum entgraten“ (vierachs_entgratbahn.Entgratbahn) –
    vierachs_entgraten.vorschau."""
    job = _job(dokument, job_name)
    return vent.vorschau(
        job, job.Model.Group, FreeCAD.Vector(*laengs), FreeCAD.Vector(*radial), *args, **kwargs
    )
