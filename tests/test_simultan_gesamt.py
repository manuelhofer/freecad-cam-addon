# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die ganze Richtungsfolge mit dem vollständigen Freiform-Prüfstand und eigener Referenz."""

import os
import pathlib
import runpy
import tempfile

schluessel = ("SIMULTAN_TEST_ANSTELLUNG", "SIMULTAN_TEST_DOKUMENT", "SIMULTAN_NC_DOKUMENT")
vorher = {k: os.environ.get(k) for k in schluessel}
os.environ["SIMULTAN_TEST_ANSTELLUNG"] = "frei_gesamt"
datei = os.environ.get("SIMULTAN_TEST_DOKUMENT") or str(
    pathlib.Path(tempfile.mkdtemp()) / "freiform_ganzebahn.FCStd"
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
