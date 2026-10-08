# SPDX-License-Identifier: LGPL-2.1-or-later
"""Baut das komplexe Testteil und den Job vom Quader bis zum Schlichten.

Nur im vorher angelegten und kontrollierten FreeCAD-Testprofil benutzen.
Die Bibliothek wird ausschließlich dort gespeichert. Der Simultanvergleich
wird separat gestartet, damit sein Ergebnis kein vorgegebenes Ergebnis ist.
"""

import math
import os
from pathlib import Path

import FreeCAD as App
import Part
import Path.Main.Job as PathJob
from Path.Tool.camassets import user_asset_store

from camaddon import halter as hl
from camaddon import job_schnittwerte as js
from camaddon import schlichten3d as s3
from camaddon import schruppen3d as r3
from camaddon import uebergabe_werkzeuge as ue
from camaddon import werkzeuge as wz


def erstellen(ordner):
    """(Job-Dokument, Werkzeugbibliothek) – D12 schruppen, drei Kugelfräser zum Vergleichen."""
    profil = Path(os.environ["FREECAD_USER_HOME"]).resolve()
    assert profil.is_dir() and Path(App.getUserAppDataDir()).resolve() == profil
    ordner = Path(ordner)
    user_asset_store.set_dir(ordner / "assets")
    w = wz.standardwerkzeug()
    w.gesamtlaenge = 85
    w.kennung = "freiform_standard12"
    h = hl.aus_vorlage("er25")
    h.name = "Gerader Beispielhalter (angenähert)"
    w.halter = h.kennung
    kugeln = []
    for nummer, durchmesser in ((2, 12), (3, 6), (4, 4)):
        k = wz.Werkzeug.aus_dict(w.als_dict())
        k.kennung = f"freiform_kugel{durchmesser}"
        k.nummer = nummer
        k.name = f"Kugel {durchmesser}"
        k.art = wz.KUGELFRAESER
        k.durchmesser = durchmesser
        k.eckradius = durchmesser / 2
        kugeln.append(k)
    bib = wz.Bibliothek([w, *kugeln])
    bib.halter = [h]
    bib.speichern()
    ue.uebergeben(bib)
    V = App.Vector
    grid = []
    for i in range(9):
        row = []
        x = 50 * i / 8
        for j in range(9):
            y = 40 * j / 8
            z = (
                20
                + 4 * math.sin((x - 10) / 14) * math.cos(y / 16)
                + 5 * math.exp(-((x - 38) ** 2 + (y - 12) ** 2) / 80)
                - 5 * math.exp(-((x - 15) ** 2 + (y - 27) ** 2) / 70)
            )
            row.append(V(x, y, z))
        grid.append(row)
    surf = Part.BSplineSurface()
    surf.interpolate(grid)
    face = surf.toShape()
    solid = face.extrude(V(0, 0, -40)).common(Part.makeBox(50, 40, 35)).removeSplitter()
    assert solid.isValid() and solid.Volume > 0
    doc = App.newDocument("FreiformSimultan")
    doc.UndoMode = 1
    obj = doc.addObject("Part::Feature", "Freiform")
    obj.Shape = solid
    obj.Label = "Freiform: Mulde, Sattel, Erhebung"
    doc.recompute()
    job = PathJob.Create("Job", [obj])
    job.Label = "Freiform - 5 Achsen vergleichen"
    faces = [
        f"Face{i+1}"
        for i, f in enumerate(solid.Faces)
        if isinstance(f.Surface, Part.BSplineSurface)
    ]
    assert len(faces) == 1, faces
    old = job.Stock
    stock = doc.addObject("Part::Feature", "Rohteil")
    stock.Shape = Part.makeBox(50, 40, 30)
    job.Stock = stock
    doc.removeObject(old.Name)
    doc.recompute()
    t1 = js.controller_ohne_transaktion(
        doc, job, w, next(e for e in w.schnittwerte[wz.ALLE] if e.art == wz.SCHRUPPEN)
    )
    controller = [
        js.controller_ohne_transaktion(
            doc, job, k, next(e for e in k.schnittwerte[wz.ALLE] if e.art == wz.SCHLICHTEN)
        )
        for k in kugeln
    ]
    t2 = controller[0]
    # Gemeinsamer Vergleich bei Manuels vollem ap: 3,5 mm kürzt die ganze Folge;
    # mehr Schlichtrest hält noch die Lastgrenze. 4 mm überlastet das Schruppen.
    # Die Schlichtanfahrten müssen aus diesem Materialstand neu entstehen.
    grob = r3.lege_an(job, t1, 25, 1.5, aufmass=0.3, zwischen=3.5, flaechen=faces)
    grob.Rampenanlauf = True
    grob.Eintauchwinkel = 2.5
    s3.lege_an(job, t2, 0.02, flaechen=faces)
    doc.recompute()
    return doc, bib
