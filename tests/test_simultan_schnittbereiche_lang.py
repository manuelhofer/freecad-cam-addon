# SPDX-License-Identifier: LGPL-2.1-or-later
"""Zeit-/Speichergegenprobe einer langen Teilbahn mit tatsächlicher Tisch/Tisch-Kinematik."""

import hashlib
import json
import os
import pathlib
import runpy
import sys
import time
import tracemalloc

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import FreeCAD as App
import Path

from camaddon import beispielmaschine as bm
from camaddon import reichweite as rw
from camaddon import schwenken as sw
from camaddon import simultan_bereiche as sb
from camaddon import simultan_operation as so


def pruefen():
    """4004 gespeicherte native Bahnstellen mit kleiner innerer Richtungssperre qualifizieren."""
    profil = pathlib.Path(os.environ["FREECAD_USER_HOME"]).resolve()
    assert profil.is_dir() and pathlib.Path(App.getUserAppDataDir()).resolve() == profil
    fixture = runpy.run_path(
        str(ROOT / "tests/test_simultan_schnittbereiche.py"), run_name="schnittbereiche_fixture"
    )
    doc, job, op, bib, _m = fixture["aufbauen"](profil)
    asm, ma = bm.lade(bm.TISCH_TISCH)
    p = rw.Pruefung(asm, ma)
    m = sw.Maschine(p, p.werkzeugaufnahme(1), rw.einspannung(op.ToolController, bib), App.Vector())
    ar = next(
        a for a in m.rundachsen if (m.richtung({a.buchstabe: 30}) - m.richtung({})).Length > 0.1
    )
    axes = [m.richtung({ar.buchstabe: t}) for t in (3, 3, 3, 3, 3, 30, 30, -3, -3, -3, -3, -3)]
    ar.achse.gelenk.EnableAngleMin = ar.achse.gelenk.EnableAngleMax = True
    ar.achse.gelenk.AngleMin, ar.achse.gelenk.AngleMax = -5, 5
    m = sw.Maschine(rw.Pruefung(asm, ma), p.werkzeugaufnahme(1), m.laenge, App.Vector())
    source = list(op.Path.Commands)
    cmds, orient = [source[0]], [axes[0]]
    for i in range(1, len(source)):
        n = 500 if i in (1, 2, 3, 4, 8, 9, 10, 11) else 1
        a, b = source[i - 1].Parameters, source[i].Parameters
        for k in range(1, n + 1):
            xyz = {s: float(a[s]) + (float(b[s]) - float(a[s])) * k / n for s in "XYZ"}
            name = "G0" if i == len(source) - 1 and k == n else "G1"
            if name == "G1":
                xyz["F"] = float(op.ToolController.HorizFeed)
            cmds.append(Path.Command(name, xyz))
            orient.append(axes[i])
    view = sb._Ansicht(op, Path=Path.Path(cmds), Werkzeugachsen=orient)
    tracemalloc.start()
    start = time.perf_counter()
    result = so.programm(view, m)
    seconds = time.perf_counter() - start
    memory = tracemalloc.get_traced_memory()[1] / 1024**2
    tracemalloc.stop()
    assert result.befehle and result.ausgelassen
    assert seconds < 90 and memory < 250, (seconds, memory)
    report = {
        "quellpunkte": len(cmds),
        "nc_saetze": len(result.befehle),
        "sha256": hashlib.sha256(
            "\n".join(c.toGCode() for c in result.befehle).encode()
        ).hexdigest(),
        "sekunden": seconds,
        "python_mib": memory,
    }
    ref = ROOT / "tests/golden/simultan_schnittbereiche_lang.json"
    r = json.loads(ref.read_text())
    for key in ("quellpunkte", "nc_saetze", "sha256"):
        assert report[key] == r[key], key
    assert seconds <= r["sekunden"] * 2 and memory <= r["python_mib"] * 2
    print("SCHNITTBEREICHE_LANG", json.dumps(report), flush=True)
    if out := os.environ.get("CAMADDON_PRUEFAUSGABE"):
        pathlib.Path(out, "schnittbereiche_lang.json").write_text(json.dumps(report, indent=2))
    for d in (doc, ma.Document, _m.pruefung.maschine.Document):
        App.closeDocument(d.Name)


pruefen()
print("OK", pathlib.Path(__file__).name, flush=True)
