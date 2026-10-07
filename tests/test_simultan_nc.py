# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die ausgeschriebenen Siemens-Achswerte des gespeicherten Freiformjobs nachfahren.

Die frühere Ausgabe mit drei Stellen schneidet hier 0,0019 mm ins Teil und lässt
sechs Flächenzellen ungeprüft. Sechs Stellen müssen zusammen mit dem reservierten
Glättungsbudget bestehen. Schreiben nur ausdrücklich nach sämtlichen Prüfungen.
"""

import hashlib
import json
import math
import os
import pathlib
import re
import sys
from dataclasses import asdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import FreeCAD as App
import Path
from Path.Tool.camassets import user_asset_store

from camaddon import abfahren as ab
from camaddon import postprozessor as pp
from camaddon import reichweite as rw
from camaddon import schwenken as sw
from camaddon import simultan_abtrag as sa
from camaddon import simultan_operation as so
from camaddon import simultan_planung as sp
from camaddon import sprache
from camaddon import vierachs_schlichten as vs
from camaddon import werkzeuge as wz


def pruefung():
    profil = pathlib.Path(os.environ["FREECAD_USER_HOME"]).resolve()
    assert profil.is_dir() and pathlib.Path(App.getUserAppDataDir()).resolve() == profil
    sprache.setze_sprache("de")
    out = ROOT / "beispiele/grob_g550_freiform"
    user_asset_store.set_dir(out / "assets")
    bib = wz.Bibliothek.laden(str(out / "beispiel_werkzeuge.json"))
    bib.speichern()
    doc = App.openDocument(
        os.environ.get("SIMULTAN_NC_DOKUMENT", str(out / "freiform_5achs.FCStd"))
    )
    md = App.openDocument(str(out / "g550_winkelaufnahme.FCStd"))
    p = rw.Pruefung(md.Assembly, md.Maschine)
    op = doc.Schlichten3D
    virtuell = sp._Ansicht(op, _pruefmaterial=[])

    def maschine(operation):
        tc = operation.ToolController
        return sw.Maschine(
            p, p.werkzeugaufnahme(tc.ToolNumber), rw.einspannung(tc, bib), rw.nullpunkt(doc.Job)
        )

    mas = maschine(op)
    quelle = so.befehle(virtuell, mas)
    if str(op.Kippachse) == "frei_gesamt":
        import numpy as np

        from camaddon import angestellt as an

        referenz = json.loads((ROOT / "tests/golden/freiform_simultan_gesamt.json").read_text())
        punkte = an.punkte(list(op.Path.Commands), [tuple(a) for a in op.Werkzeugachsen], 2)
        geladene_werte = np.round(
            np.array([(*p.spitze, *p.achse, int(p.eilgang)) for p in punkte]), 6
        )
        # FreeCAD speichert Path/VectorList mit begrenzter Stellenzahl. Die geladene
        # Darstellung bekommt nach der vollständigen NC-Prüfung ihre eigene exakte Referenz.
        # Die rohe Rechenreferenz bleibt im Planungsprüfstand unverändert streng.
        assert len(geladene_werte) == referenz["punkte"]
        assert np.max(np.abs(geladene_werte[::97] - np.asarray(referenz["stichprobe"]))) <= 0.000002
        bisher = json.loads((ROOT / "tests/golden/freiform_simultan.json").read_text())
        assert referenz["zeit_s"] <= bisher["zeit_s"] * 1.005
        assert referenz["rechenzeit_s"] <= bisher["rechenzeit_s"] * 2
        assert referenz["spitzenspeicher_python_mb"] <= bisher["spitzenspeicher_python_mb"] * 2
    virtuell._pruefprogramm = (so.pruefschluessel(mas), tuple(quelle))
    # Erst nur diese Operation schreiben, ohne Wechselpunkt: jeder Fahrsatz kommt
    # aus der Quelle. Die gelesenen Wörter, nicht die originalen Doublewerte, nachfahren.
    abschnitt = pp.abschnitte(sp._job_mit(doc.Job, op, virtuell), maschine)[-1]
    steuerung = pp.steuerung("siemens")
    info = pp.maschineninfo_dokument(md)
    einzeln = pp.programm(
        [abschnitt],
        steuerung.ersetzt(wechselpunkt=False, marken=False),
        info,
        "NC_PRUEFUNG",
    )
    assert "CTOL=0.000100" in einzeln.zeilen
    quellsaetze, vorher = [], None
    for c, d in zip(quelle, virtuell._pruefmaterial, strict=True):
        if c.Name not in ("G0", "G1"):
            vorher = None
            continue
        koordinaten = {k: round(float(v), 6) for k, v in c.Parameters.items() if k in "XYZABC"}
        if c.Name == "G0" and vorher == ("G0", koordinaten):
            continue  # der Postprozessor entfernt direkt aufeinanderfolgende identische G0
        quellsaetze.append((c, d))
        vorher = c.Name, koordinaten
    gelesen, daten, stand, index = [], [], {}, 0
    for zeile in einzeln.zeilen:
        name = zeile.split()[0] if zeile.split() else ""
        if name in ("G93", "G94"):
            gelesen.append(Path.Command(name))
            daten.append((True, 0.0))
        elif name in ("G0", "G1"):
            c, d = quellsaetze[index]
            index += 1
            assert name == c.Name
            werte = {}
            for wort in zeile.split()[1:]:
                match = re.fullmatch(r"([XYZABCIFJKR])(?:\d+=|=)?([-+]?\d+\.\d+)", wort)
                modulo = re.fullmatch(r"([ABC])\d*=AC([PN])\(([-+]?\d+\.\d+)\)", wort)
                if modulo:
                    achse, richtung, zahl = modulo.groups()
                    wert = float(zahl)
                    # Der einzelne Abschnitt enthält absichtlich keinen Home-Anlauf.
                    # Seine erste Moduloachse legt nur die Phase fest, keine vorherige
                    # Umdrehung; sie auf die Quelle beziehen, danach die echte Folge lesen.
                    vorher = stand.get(achse, round(float(c.Parameters[achse]), 6)) * (
                        -1 if achse in info.umgekehrt else 1
                    )
                    wert += math.floor(vorher / 360) * 360
                    while richtung == "P" and wert < vorher - 1e-10:
                        wert += 360
                    while richtung == "N" and wert > vorher + 1e-10:
                        wert -= 360
                    werte[achse] = wert
                elif match:
                    achse, zahl = match.groups()
                    werte[achse] = float(zahl) / 60 if achse == "F" else float(zahl)
            werte = {k: -v if k in info.umgekehrt else v for k, v in werte.items()}
            stand.update({k: v for k, v in werte.items() if k in "XYZABC"})
            for k, v in c.Parameters.items():
                if k in "XYZABC":
                    assert abs(stand[k] - float(v)) < 1e-6, (
                        index,
                        zeile,
                        k,
                        stand[k],
                        v,
                        quellsaetze[index - 2][0].Parameters if index > 1 else {},
                    )
            gelesen.append(Path.Command(name, werte))
            daten.append(d)
    assert index == len(quellsaetze), (index, len(quellsaetze))
    virtuell._pruefprogramm = (so.pruefschluessel(mas), tuple(gelesen))
    job = sp._job_mit(doc.Job, op, virtuell)
    fahrt = ab.abfahrt(p, job, rw.nullpunkt(job), bib)
    if str(op.Kippachse) == "frei_gesamt":
        assert (
            fahrt.dauer <= referenz["zeit_s"] * 1.005
        ), "Zeitbestmarke nach NC-Rundung überschritten"
    nummer = next(i for i, o in enumerate(rw._operationen(job)) if o is virtuell)
    bahn = sa.maschinenbahn(fahrt, nummer, 2, materialdaten=daten)
    stand_material = sa.Pruefstand(job, virtuell, bib)
    # NC-Reserve einschließlich CTOL, dazu 0,00025 mm für die Interpolation.
    m = stand_material.messen(
        bahn,
        vs.form_des_controllers(op.ToolController),
        sa.einsatz_von(op.ToolController, bib),
        float(op.Grathoehe) - sa.NC_RESERVE,
        float(op.Aufmass),
    )
    print("NC_MATERIAL", json.dumps(asdict(m)), flush=True)
    assert not m.gruende, m.gruende
    reserve = 0.00025 + sa.NC_RESERVE
    abstand = sa.einschnitt(stand_material.form, bahn, 2, grenze=reserve)
    print("NC_BREP", abstand, flush=True)
    assert abstand >= reserve, abstand
    # Ganzen Job mit denselben gelesenen Achswerten schreiben und nachlesen.
    if str(op.Kippachse) == "frei_gesamt":
        # Den tatsächlichen Export referenzieren, nicht einen zweiten Export bereits
        # gelesener Wörter; dessen Geometrie wurde direkt darüber unabhängig geprüft.
        virtuell._pruefprogramm = (so.pruefschluessel(mas), tuple(quelle))
    programm = pp.programm(
        pp.abschnitte(job, maschine), steuerung, pp.maschineninfo_dokument(md), "G550_FREIFORM"
    )
    if str(op.Kippachse) == "frei_gesamt":
        assert (
            "B1=ACN(320.869207)" in programm.text
        ), "Erste Anstellung von Home in falscher Drehrichtung"
    befunde, saetze = pp.nachlesen(programm, steuerung, pp.maschineninfo_dokument(md))
    assert not befunde, befunde
    ist = {"sha256": hashlib.sha256(programm.text.encode()).hexdigest(), "nc_saetze": saetze}
    if str(op.Kippachse) == "frei_gesamt":
        ist["geladene_punkte_sha256"] = hashlib.sha256(
            geladene_werte.astype("<f8").tobytes()
        ).hexdigest()
        ist["geladene_befehle_sha256"] = hashlib.sha256(
            json.dumps(
                [
                    (c.Name, sorted((k, round(float(v), 6)) for k, v in c.Parameters.items()))
                    for c in quelle
                ]
            ).encode()
        ).hexdigest()
    golden = ROOT / (
        "tests/golden/freiform_simultan_gesamt_nc.json"
        if str(op.Kippachse) == "frei_gesamt"
        else "tests/golden/freiform_simultan_nc.json"
    )
    schreiben = os.environ.get("GOLDENE_BAHNEN_SCHREIBEN") == "1"
    if schreiben:
        golden.write_text(json.dumps(ist, indent=2) + "\n")
    else:
        assert ist == json.loads(golden.read_text()), "Ausgeschriebenes NC-Programm verändert"
    if os.environ.get("SIMULTAN_BEISPIEL_SCHREIBEN") == "1":
        (out / "freiform_5achs.mpf").write_text(programm.text)
        (out / "nc_pruefung.json").write_text(
            json.dumps(ist | {"material": asdict(m), "brep_abstand_mm": abstand}, indent=2) + "\n"
        )
    App.closeDocument(doc.Name)
    App.closeDocument(md.Name)


pruefung()
print("OK", os.path.basename(__file__))
