# Prüft die Werkzeugformen in CAM (Spezifikation Werkzeugarten, Abschnitt 6):
# Jede Art, die an CAM geht, wird dort ein Körper, wie ihr Bild ihn zeigt –
# ohne dass FreeCADs Skizzen klagen, auch mit Schaft = D und mit einer
# vertippten, zu kurzen Gesamtlänge. Jede bekommt nur Parameter, die ihre Form
# hat, und „Aus CAM übernehmen“ liest dieselben Maße zurück.
import os
import pathlib
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD
from Path.Tool.camassets import cam_assets, user_asset_store

from camaddon import einheiten, sprache
from camaddon import uebergabe_werkzeuge as ue
from camaddon import werkzeuge as wz
from camaddon import werkzeuge_aus_cam as aus_cam
from camaddon import werkzeugform as wf

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


vorher = sprache.gewaehlte_sprache() or ""
sprache.setze_sprache("de")
vorher_mass = einheiten.gewaehltes_masssystem()
einheiten.setze_masssystem(einheiten.METRISCH)
user_asset_store.set_dir(pathlib.Path(tempfile.mkdtemp()))  # nur in diesem Lauf


def muster(art, nummer, **werte):
    """Ein Werkzeug der Art mit ihren Beispielmaßen (als eingetragen), dazu `werte`."""
    w = wz.Werkzeug(nummer=nummer, art=art)
    wz.beispielwerte_setzen(w, neu=True)
    w.beispiel = set()
    for feld, wert in werte.items():
        setattr(w, feld, wert)
    return w


# Die Beispiele aller Arten; dazu mit Schaft = D und mit zu kurzer Gesamtlänge.
beispiele = [muster(art, i + 1) for i, art in enumerate(wz.ARTEN)]
nach_cam = [w for w in beispiele if w.art in ue.FORMEN]
schaft_wie_d = [
    muster(w.art, 100 + w.nummer, schaft=w.durchmesser)
    for w in nach_cam
    if wz.hat_feld(w, "schaft")
]
zu_kurz = [
    muster(w.art, 200 + w.nummer, gesamtlaenge=max(wz.reichweite(w) - 1, 1))
    for w in nach_cam
    if wz.hat_feld(w, "gesamtlaenge")
]
bericht = ue.uebergeben(wz.Bibliothek(beispiele + schaft_wie_d + zu_kurz))
pruefe(
    bericht.ohne_form == ["T23 Drehwerkzeug", "T24 Einstechwerkzeug", "T25 Gewindedrehwerkzeug"],
    f"ohne Form: {bericht.ohne_form}",
)
genaehert = [kurz for kurz, _form in bericht.naeherungen if int(kurz.split()[0][1:]) < 100]
pruefe(
    genaehert
    == [
        "T6 Lollipopfräser",
        "T9 Messerkopf",
        "T11 Formfräser",
        "T14 Zentrierbohrer",
        "T19 Flachsenker",
        "T21 Bohrstange",
        "T22 Ausspindelwerkzeug",
    ],
    f"Näherungen: {bericht.naeherungen}",
)
pruefe(("T6 Lollipopfräser", "Kugelfräser") in bericht.naeherungen, "Lollipop als Kugelfräser")


def mit_konsole(aufruf):
    """(Ergebnis, was FreeCAD dabei auf die Konsole schreibt)."""
    sys.stdout.flush()
    sys.stderr.flush()
    with tempfile.TemporaryFile() as datei:
        alt = os.dup(1), os.dup(2)
        os.dup2(datei.fileno(), 1)
        os.dup2(datei.fileno(), 2)
        try:
            ergebnis = aufruf()
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            os.dup2(alt[0], 1)
            os.dup2(alt[1], 2)
            for kanal in alt:
                os.close(kanal)
        datei.seek(0)
        return ergebnis, datei.read().decode("utf-8", "replace")


# Woran man sieht, dass eine Skizze der Form nicht aufgeht.
KLAGEN = ("sketch", "solver", "edge too small", "could not", "conflicting", "redundant")


def koerper(w):
    """Das ToolBit in CAM: (Eigenschaften, Körper, Klagen auf der Konsole, zurückgelesen).

    Gebaut in einem eigenen Dokument; danach ist das ToolBit mit ihm weg –
    darum hier schon gelesen, was die Prüfung braucht.
    """

    def bauen():
        bit = cam_assets.get(f"toolbit://{ue.PRAEFIX}{w.kennung}")
        eigenschaften = {
            "form": str(bit.obj.ShapeType),
            "schema": set(type(bit._tool_bit_shape).schema()),
            "drehrichtung": str(bit.obj.SpindleDirection),
            "steigung": float(bit.obj.Pitch.getValueAs("mm")) if hasattr(bit.obj, "Pitch") else 0,
        }
        zurueck = aus_cam.werkzeug_aus(bit, w.nummer)
        dokument = FreeCAD.newDocument("formen")
        objekt = bit.attach_to_doc(dokument)
        dokument.recompute()
        kaputt = [o.Name for o in dokument.Objects if {"Invalid", "Error"} & set(o.State)]
        form = objekt.Shape.copy()
        FreeCAD.closeDocument(dokument.Name)
        return eigenschaften, form, kaputt, zurueck

    (eigenschaften, form, kaputt, zurueck), konsole = mit_konsole(bauen)
    klagen = [z for z in konsole.splitlines() if any(k in z.lower() for k in KLAGEN)]
    return eigenschaften, form, kaputt + klagen, zurueck


def radius_bild(teile, y):
    """Wie weit das Bild auf der Höhe y von der Achse reicht."""
    r = 0.0
    for teil in teile:
        punkte = teil.punkte
        for (x1, y1), (x2, y2) in zip(punkte, punkte[1:] + punkte[:1], strict=True):
            if y1 != y2 and (y1 - y) * (y2 - y) <= 0:
                r = max(r, abs(x1 + (x2 - x1) * (y - y1) / (y2 - y1)))
    return r


def radius_cam(form, z):
    """Wie weit der Körper in CAM auf der Höhe z von der Achse reicht."""
    schnitt = form.slice(FreeCAD.Vector(0, 0, 1), z)
    return max((max(-d.BoundBox.XMin, d.BoundBox.XMax) for d in schnitt), default=0.0)


def vergleichsbereich(w):
    """Von wo bis wo CAM genau das Bild zeigen muss (y ab der Spitze)."""
    laenge = wz.laenge_fuer_cam(w)
    if w.art == wz.NUTENFRAESER:  # darüber ist in CAM der Hals der Schaft
        return 0.0, wz.reichweite(w)
    if w.art == wz.GEWINDEFRAESER:  # CAM hat nur einen Zahn
        return wz.mass(w, "schneidenlaenge"), laenge
    if wz.gewindebohrer(w.art):  # CAM: glatt mit 90°-Spitze statt der Zähne
        return wz.mass(w, "schneidenlaenge") + w.durchmesser, laenge
    if w.art == wz.TASTER:  # darüber zeichnet das Bild den Körper des Tasters
        return 0.0, 0.6 * laenge
    return 0.0, laenge


STUFE = 0.05  # mm: so nah an einer Stufe gilt die Höhe darunter oder darüber
GENAU = 0.03  # mm: das Bild ist aus Strecken, CAM rund


def vergleiche(w, form):
    """Das Bild und der Körper in CAM auf 40 Höhen – außer, wo es die Form nicht gibt."""
    teile = wf.teile(w)
    von, bis = vergleichsbereich(w)
    # Den Taster baut CAM von oben nach unten (Spitze bei −Länge).
    versatz = -wz.laenge_fuer_cam(w) if w.art == wz.TASTER else 0.0
    abweichungen = []
    for k in range(1, 40):
        y = von + (bis - von) * k / 40
        if w.art == wz.KEGELSENKER:  # das Bild hat über dem Kegel einen Bund
            _spitze, hoehe, _winkel = wf.kegel(w)
            if hoehe - STUFE < y < hoehe + 0.15 * w.durchmesser + STUFE:
                continue
        bild = [radius_bild(teile, y + d) for d in (-STUFE, 0.0, STUFE)]
        cam = radius_cam(form, y + versatz)
        if not min(bild) - GENAU <= cam <= max(bild) + GENAU:
            abweichungen.append(f"y {y:.2f}: Bild {bild[1]:.3f}, CAM {cam:.3f}")
    return abweichungen


alle_formen = {w.art: w for w in nach_cam}
ergebnisse = {}  # T-Nummer → Eigenschaften des ToolBits in CAM
for w in nach_cam + schaft_wie_d + zu_kurz:
    wer = f"T{w.nummer} {w.art}"
    eigenschaften, form, klagen, zurueck = koerper(w)
    ergebnisse[w.nummer] = eigenschaften
    _datei, typ = ue.FORMEN[w.art]
    pruefe(eigenschaften["form"] == typ, f"{wer}: Form {eigenschaften['form']} statt {typ}")
    parameter = ue.parameter_fuer_cam(w)
    schema = eigenschaften["schema"]
    pruefe(set(parameter) <= schema, f"{wer}: Parameter ohne Form {set(parameter) - schema}")
    pruefe(not klagen and form.isValid(), f"{wer}: Körper in CAM – {klagen[:4]}")
    if w.art not in ue.NAEHERUNGEN and not klagen and w.nummer < 200:
        abweichungen = vergleiche(w, form)
        pruefe(not abweichungen, f"{wer}: CAM zeigt nicht das Bild: {abweichungen[:4]}")
    if w.nummer > 200:
        # Vertippt: Schneide und Hals in CAM bleiben, darüber mindestens 1 mm Schaft.
        unten = max(
            parameter.get("CuttingEdgeHeight", 0) + parameter.get("NeckHeight", 0),
            parameter.get("CuttingEdgeLength", 0),
            parameter.get("NeckLength", 0),
        )
        laenge = form.BoundBox.ZLength
        pruefe(
            parameter["Length"] >= unten + ue.MINDESTSCHAFT - 1e-9,
            f"{wer}: Länge {parameter['Length']} bei Schneide und Hals {unten}",
        )
        pruefe(laenge >= parameter["Length"] - 0.01, f"{wer}: Körper nur {laenge:.2f} lang")

    # Zurück aus CAM: dieselben Maße – was die Form in CAM hat.
    if w.nummer > 100:
        continue
    erwartet = ue.NAEHERUNGEN.get(w.art, w.art)
    erwartet = {wz.KEGELSENKER: wz.FASENFRAESER, wz.NC_ANBOHRER: wz.BOHRER}.get(erwartet, erwartet)
    pruefe(zurueck is not None and zurueck.art == erwartet, f"{wer}: zurück als {zurueck}")
    if zurueck is None or w.art in ue.NAEHERUNGEN:
        continue
    # Was CAM nicht hat: beim Gewindefräser nur ein Zahn, beim Bohrer weder
    # Schneidenlänge noch Schaft, bei der Säge ist der Hals der Schaft, beim
    # Fasenfräser ist die Schneide der Kegel.
    ohne = {
        wz.GEWINDEFRAESER: {"schneidenlaenge", "hals_laenge", "steigung"},
        wz.BOHRER: {"schneidenlaenge", "schaft"},
        wz.NC_ANBOHRER: {"schneidenlaenge", "schaft"},
        wz.NUTENFRAESER: {"schaft"},
        wz.FASENFRAESER: {"schneidenlaenge"},
    }.get(w.art, set())
    gesendet = {"gesamtlaenge": parameter["Length"]}
    for feld in set(wz.artdaten(w.art).felder) & set(wz.artdaten(zurueck.art).felder) - ohne:
        if feld in wz.WINKEL_FELDER:
            vorher_wert, nachher = wz.wert(w, feld), wz.wert(zurueck, feld)
        elif feld in wz.LAENGEN_FELDER:
            vorher_wert, nachher = gesendet.get(feld, wz.mass(w, feld)), wz.mass(zurueck, feld)
        else:
            vorher_wert, nachher = getattr(w, feld), getattr(zurueck, feld)
        if isinstance(vorher_wert, float):
            gleich = abs(vorher_wert - nachher) < 0.002
        else:
            gleich = vorher_wert == nachher
        pruefe(gleich, f"{wer}: {feld} {vorher_wert} → zurück {nachher}")

# Der Linksgewindebohrer dreht in CAM rückwärts (und kommt als linker zurück,
# oben); der Taster dreht nicht.
links = ergebnisse[alle_formen[wz.GEWINDEBOHRER_LINKS].nummer]
pruefe(links["drehrichtung"] == "Reverse", f"links dreht {links['drehrichtung']}")
pruefe(abs(links["steigung"] - 1.5) < 1e-9, f"Steigung {links['steigung']}")
rechts = ergebnisse[alle_formen[wz.GEWINDEBOHRER_RECHTS].nummer]
pruefe(rechts["drehrichtung"] == "Forward", f"rechts dreht {rechts['drehrichtung']}")
taster = ergebnisse[alle_formen[wz.TASTER].nummer]
pruefe(taster["drehrichtung"] == "None", f"Taster dreht {taster['drehrichtung']}")

einheiten.setze_masssystem(vorher_mass)
sprache.setze_sprache(vorher)
if fehler:
    raise AssertionError("\n".join(fehler))
print()  # FreeCADCmd 1.1.3 schreibt Fortschritt ohne Zeilenende davor
print("OK", os.path.basename(__file__))
