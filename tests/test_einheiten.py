# Prüft Dezimalzeichen und das Lesen von Eingaben (Stufe B): Die Wahl wird
# gespeichert und lässt sich vergessen; Eingaben nehmen Punkt und Komma,
# alles andere ist keine Zahl.
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

from camaddon import einheiten

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


vorher = einheiten.gewaehltes_dezimalzeichen()
for zeichen in (".", ","):
    einheiten.setze_dezimalzeichen(zeichen)
    pruefe(einheiten.gewaehltes_dezimalzeichen() == zeichen, f"{zeichen!r} nicht gespeichert")
einheiten.setze_dezimalzeichen(None)
pruefe(einheiten.gewaehltes_dezimalzeichen() is None, "Wahl nicht vergessen")

for text, soll in (
    ("12,5", 12.5),
    ("12.5", 12.5),
    ("", 0.0),
    (" 7 ", 7.0),
    (",5", 0.5),
    ("12.", 12.0),
    ("-3,25", -3.25),
):
    try:
        ist = einheiten.zahl_aus_text(text)
    except ValueError:
        ist = None
    pruefe(ist == soll, f"{text!r} ergibt {ist} statt {soll}")
# Das andere Zeichen als Tausendertrennzeichen: nur, wo es danach aussieht.
for text, zeichen, soll in (
    ("35.000", ",", 35000.0),
    ("120.000", ",", 120000.0),
    ("1.250", ",", 1250.0),
    ("12.5", ",", 12.5),
    ("0.125", ",", 0.125),
    ("35,000", ",", 35.0),
    ("1,500", ".", 1500.0),
    ("12,5", ".", 12.5),
    ("1.500", ".", 1.5),
):
    ist = einheiten.zahl_aus_text(text, zeichen)
    pruefe(ist == soll, f"{text!r} bei {zeichen!r}: {ist} statt {soll}")
for text in ("1.000,5", "12,5,1", "abc", "1e5", ".", "-", "12 5"):
    try:
        einheiten.zahl_aus_text(text)
        fehler.append(f"{text!r} als Zahl gelesen")
    except ValueError:
        pass

einheiten.setze_dezimalzeichen(vorher)
if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
