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
import numpy as np

from . import vierachs_entgraten as vent
from . import vierachs_operation as vo
from . import vierachs_plan as vplan
from . import vierachs_schlichten as vs
from . import voxelstange as vx

REST_VOXEL = 1.0  # mm: so fein rechnet rest() die Stange nach


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


def rest(
    dokument,
    job_name,
    laengs,
    schruppen,
    schrupp_form,
    schlichten,
    schlicht_form,
    schwelle,
    h=REST_VOXEL,
):
    """Was nach dem Schruppen für die Kugel stehen bleibt (Manuel, 2026-10-11, Frage 8:
    „vorher sagen, wenn viel stehen bleibt“): die Stange als Voxel, erst die Schruppbahn, dann
    die Schlichtbahn nachgefahren (auf den Nebenrechnern) – `schruppen`, `schlichten`: (Sätze
    (n, 4) aus voxelstange.als_feld, Eilgänge [bool]). Der Fräser des Modells liegt ganz im
    echten (voxelstange.fraeser): Das Schruppen nimmt eher weniger, die Zahl hält nach oben.
    {hoechstens, a, a_von, a_bis, strecke, volumen}: das Meiste, was die Kugel je mm Weg nimmt
    (mm³/mm, über JE_MM_STRECKE gemittelt) und wo längs; von wo bis wo sie mehr als `schwelle`
    nimmt und auf wie viel Weg (mm); was sie insgesamt nimmt (mm³). None, wenn ein Fräser nicht
    ins Voxelmodell passt."""
    job = _job(dokument, job_name)
    schrupp_fraeser, schlicht_fraeser = vx.fraeser(schrupp_form), vx.fraeser(schlicht_form)
    if schrupp_fraeser is None or schlicht_fraeser is None:
        return None
    achse, radius, _a_vorne, _a_futter = vs._stange(job, FreeCAD.Vector(*laengs))
    teil = vs._teil(job.Model.Group)
    a_teil = [v.Point.dot(achse) for v in teil.Vertexes]
    stange = vx.Voxelstange(radius, min(a_teil) - h, max(a_teil) + h, h)
    stange.fahre(schruppen[0], *schrupp_fraeser, je_satz=False)
    saetze, eilgang = schlichten
    weg = stange.fahre(saetze, *schlicht_fraeser)
    last, a = vx.je_mm(saetze, weg, h, eilgang)
    if not len(last):
        return None
    am_meisten = int(np.argmax(last))
    viel = last > schwelle
    d = np.diff(np.asarray(saetze, dtype=float), axis=0)
    r_mitte = np.abs(saetze[1:, 1] + saetze[:-1, 1]) / 2
    laenge = np.sqrt((d[:, :3] ** 2).sum(axis=1) + (r_mitte * np.radians(d[:, 3])) ** 2)
    return {
        "hoechstens": float(last[am_meisten]),
        "a": float(a[am_meisten]),
        "a_von": float(a[viel].min()) if viel.any() else None,
        "a_bis": float(a[viel].max()) if viel.any() else None,
        "strecke": float(laenge[viel].sum()),
        "volumen": float(np.sum(weg)) * h**3,
    }
