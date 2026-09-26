# Prüft Maßsystem, Dezimalzeichen und das Lesen von Eingaben (Stufe B): Die
# Wahl wird gespeichert und lässt sich vergessen; umgerechnet wird
# verlustfrei (½" bleibt 0,5 in); Eingaben nehmen Punkt und Komma, alles
# andere ist keine Zahl; tr() setzt die Einheiten in die Texte.
import os
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

from camaddon import einheiten, sprache
from camaddon.sprache import tr

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

# Maßsystem: ohne Wahl FreeCADs (hier metrisch), gewählt Zoll.
vorher_mass = einheiten.gewaehltes_masssystem()
vorher_sprache = sprache.gewaehlte_sprache() or ""
sprache.setze_sprache("de")
einheiten.setze_masssystem(None)
pruefe(einheiten.masssystem() == einheiten.METRISCH, "ohne Wahl nicht metrisch")
pruefe(einheiten.anzeige(12.7, einheiten.LAENGE) == 12.7, "metrisch umgerechnet")
pruefe(tr("wv.eingriff.ae", ae="1,2", ae_d="10") == "ae 1,2 mm = 10 % von D", "Text metrisch")
pruefe(einheiten.runden(9.525, einheiten.LAENGE, 2) == 9.53, "metrisch auf 0,01 mm")
pruefe(einheiten.abrunden(0.0508, einheiten.SPAN, 3) == 0.05, "metrisch ab auf 0,001 mm")
einheiten.setze_masssystem(einheiten.ZOLL)
pruefe(einheiten.in_zoll() and einheiten.einheit(einheiten.LAENGE) == "in", "Zoll gewählt")
pruefe(einheiten.gerundet(12.7, einheiten.LAENGE) == 0.5, "½ Zoll nicht 0,5 in")
pruefe(abs(einheiten.metrisch(0.5, einheiten.LAENGE) - 12.7) < 1e-12, "0,5 in nicht 12,7 mm")
for groesse, metrisch, zoll in (
    (einheiten.SCHNITT, 121.92, 400),
    (einheiten.SPAN, 0.0508, 0.002),
    (einheiten.VORSCHUB, 762, 30),
    (einheiten.ABTRAG, 16.387064, 1),
):
    ist = einheiten.gerundet(metrisch, groesse)
    pruefe(abs(ist - zoll) < 1e-9, f"{groesse}: {metrisch} ergibt {ist} statt {zoll}")
pruefe(
    [einheiten.einheit(g) for g in (einheiten.SCHNITT, einheiten.VORSCHUB, einheiten.ABTRAG)]
    == ["SFM", "ipm", "in³/min"],
    "Einheiten in Zoll",
)
pruefe(abs(einheiten.vergleichsvolumen() - 5 * 16.387064) < 1e-9, "Vergleichsvolumen 5 in³")
# Runden, wie gezeigt: in Zoll auf Zoll-Stellen, metrisch zurück.
pruefe(abs(einheiten.runden(9.525, einheiten.LAENGE, 2) - 9.525) < 1e-12, "3/8 in gerundet")
pruefe(abs(einheiten.abrunden(0.0508, einheiten.SPAN, 3) - 0.0508) < 1e-12, "0,002 in abgerundet")
pruefe(
    einheiten.gerundet(einheiten.abrunden(0.05, einheiten.SPAN, 3), einheiten.SPAN) == 0.00196, "ab"
)
pruefe(tr("wv.eingriff.ae", ae="0.05", ae_d="10") == "ae 0.05 in = 10 % von D", "Text in Zoll")
pruefe(tr("wv.strategie.zeit") == "Zeit für 5 in³", f"ohne Werte: {tr('wv.strategie.zeit')!r}")
einheiten.setze_masssystem(vorher_mass)
sprache.setze_sprache(vorher_sprache)
if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
