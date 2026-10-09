# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die ganze Richtungsfolge („frei – ganze Bahn“) mit Planung und NC-Nachfahren an derselben
Geometrie wie test_simultan_planung – Vorgabe die Kuppel, mit eigener Referenz
(`tests/golden/kuppel_simultan_gesamt.json`, `…_gesamt_nc.json`). `SIMULTAN_TEST_FORM=freiform`
rechnet das Freiformbeispiel: über eine Stunde, von Hand, keine Prüfung (P-2026-10-09-10)."""

import os
import pathlib
import runpy
import tempfile

schluessel = (
    "SIMULTAN_TEST_ANSTELLUNG",
    "SIMULTAN_TEST_DOKUMENT",
    "SIMULTAN_NC_DOKUMENT",
    "SIMULTAN_TEST_FORM",
)
vorher = {k: os.environ.get(k) for k in schluessel}
os.environ["SIMULTAN_TEST_ANSTELLUNG"] = "frei_gesamt"
os.environ["SIMULTAN_TEST_FORM"] = os.environ.get("SIMULTAN_TEST_FORM", "kuppel")
datei = os.environ.get("SIMULTAN_TEST_DOKUMENT") or str(
    pathlib.Path(tempfile.mkdtemp()) / f"{os.environ['SIMULTAN_TEST_FORM']}_ganzebahn.FCStd"
)
os.environ["SIMULTAN_TEST_DOKUMENT"] = datei
try:
    runpy.run_path(
        str(pathlib.Path(__file__).with_name("test_simultan_planung.py")), run_name="__main__"
    )
    os.environ["SIMULTAN_NC_DOKUMENT"] = datei
    runpy.run_path(
        str(pathlib.Path(__file__).with_name("test_simultan_nc.py")), run_name="__main__"
    )
finally:
    for k, wert in vorher.items():
        if wert is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = wert
print("OK", os.path.basename(__file__))
